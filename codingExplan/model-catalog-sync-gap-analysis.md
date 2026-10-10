# 模型目录同步 —— 现状与缺口分析（TUI / 桌面端 ACP）

> 范围：TUI 与 agent_studio（桌面端）两个调用 iCode 的场景。
> 这是**现状盘点**，不含实现方案；方案见 `model-catalog-sync-proposal.md`（iCode 侧，已实现部分）。
> 文末的 `【Dn】` 是待决策项，`【Cn】` 是待确认项。

---

## 0. 结论速览

| 场景 | 结论 |
|---|---|
| iCode 自带 TUI | **已闭环**。服务端改模型，最多等一个轮询周期即生效 |
| 桌面端走 ACP | **架构正确**：iCode 不自己拉，列表由桌面端注入。运行期刷新只对新会话生效，属已知设计（3.3）。真正待决策的只有「要不要让老会话也生效」 |

设计约束：**模型列表归宿主（桌面端）所有，iCode 作为引擎不主动拉取。**
这一点已通过 `sync_model_catalog` 的 opt-in 落地（3.1），整表替换冲突因此不存在。

按现有设计，**桌面端场景没有必须修的功能缺口** —— 只有一个边界情况（3.3 末段）
和一个防回归的保险（第 5 节）。

---

## 1. 已经打通的能力

| 能力 | 代码位置 |
|---|---|
| 启动时同步一次 | `startup.py:277` → `_sync_model_catalog()`，**opt-in：默认 `False`，仅 TUI 传 `True`**（`app.py:1298`） |
| TUI 定时轮询（默认 15 分钟） | `src/chrys/app/tui/app.py:991` → `start_periodic_sync()` |
| 同步后落盘 + 替换内存注册表 | `src/chrys/app/tui/app.py:985-989` → `replace_profiles()` |
| 同步后刷新状态栏模型指示 | `src/chrys/app/tui/app.py:989` → `screen._refresh_model_indicator` |
| 登录后立即拉一次 | `src/chrys/app/tui/screens/main/screen.py:1730` → `start_catalog_sync(immediate=True)` |
| 停止轮询（登出 / 退出） | `src/chrys/app/tui/app.py:996` `stop_catalog_sync()` |
| ACP 侧模型接口 | `src/chrys/app/acp/server.py:690` `profiles/models/list` |
| ACP 侧切换会话模型 | `src/chrys/app/acp/server.py:453` `set_session_model` |
| ACP `session/new` 带模型快照 | `src/chrys/app/acp/server.py:248` / `305` |

配套规则：`start_periodic_sync` 在无 catalog URL 或无凭证时返回 `None`（`catalog.py:722-727`），
所以未登录时不空转线程，登录后才启动。

---

## 2. TUI 场景

### 2.1 完整链路

```
进程启动
  └─ startup.py:277  sync_model_catalog()          拉一次，落盘
TUI 启动
  └─ app.py:991      start_periodic_sync()         起轮询线程
       └─ 每 interval 秒 → sync_catalog_blocking()
            └─ _on_applied → replace_profiles() + 刷新状态栏
登录
  └─ screen.py:1730  start_catalog_sync(immediate=True)
       └─ start_periodic_sync(immediate=True)      先拉一次再进轮询
```

### 2.2 遗留疑点

**`immediate=True` 会被"线程已在运行"吞掉**

```python
# src/chrys/app/tui/app.py:981-983
if self._catalog_sync_stop is not None:
    logger.info("Model catalog sync already running; not starting another.")
    return
```

启动时若已有凭证（`CHRYS_MODEL_CATALOG_TOKEN` 环境变量，或上次登录留下的 token），
轮询线程在启动阶段就已存在。此时登录后的调用直接 return —— 不起新线程，
也**不立即拉一次**，只能等下一个周期。

登录换用户后 `userId` 变化、可见模型不同，语义上必须立刻重拉，静默跳过是不对的。

> 状态：本次未复现（2026-10-09 观察到一次 42 秒延迟，未定位），暂搁置。

验证方式：日志中是否出现 `Model catalog sync already running; not starting another.`，
且该行早于登录完成时间。

---

## 3. 桌面端（ACP）场景

桌面端通过 `apps/desktop` spawn `icode acp`（`runtime-composition.ts:2118`，native ACP，无适配器）。

### 3.0 完整流程

| 步 | 谁 | 动作 | 代码 |
|---|---|---|---|
| 1 | 桌面端 | 拉账号模型列表 `POST /csas/web/model/myModelList` | `account-model-catalog.ts:14`；调用点 `index.ts:560` / `1164` |
| 2 | 桌面端 | `applyChrysModelCatalog()` 更新内存 catalog，清空 profile 缓存 | `runtime-composition.ts:1969-1972` |
| 3 | 桌面端 | 建会话时算指纹 `chrysProfilesFingerprint(input)`：命中缓存复用磁盘文件，未命中才重写 | `runtime-composition.ts:1936-1967` |
| 4 | 桌面端 | 具化：每个模型写 `<private>/chrys-home/.chrys/models/<id>.yaml`；删掉已下线模型的 profile | `chrys-model-profile.ts:95-186`、`180` |
| 5 | 桌面端 | spawn `icode acp`：传 `HOME=chrys-home`、`CHRYS_MODEL_PROFILE`、provider 凭证 env | `runtime-composition.ts:2118`、`2161` |
| 6 | **iCode** | 启动时把 `models/*.yaml` 加载进内存注册表 | `load_registries()`，**只此一次** |
| 7 | — | 运行期刷新列表 → 只影响**新建**会话，老会话保持启动时的快照 | `runtime-composition.ts:1934-1935` |

内容寻址（指纹）的作用：列表没变就不重写文件，变了才重写 —— 避免每次建会话都无谓地
动磁盘。

### 3.1 谁拥有模型目录 —— 设计约束（已正确实现）

**模型列表归宿主所有，iCode 作为引擎不主动拉取。**

- `sync_model_catalog` 是 opt-in：`bootstrap_runtime` 默认 `False`（`startup.py:204`），
  **只有 TUI 传 `True`**（`app.py:1298`），ACP 入口不拉
- `startup.py:222-229` 的注释写明了原因：整表替换只对自己拥有该目录的前端安全；
  TUI 拥有它所以开启；而「通过 ACP 拉起 Chrys 的宿主（桌面应用、编辑器插件）自己写
  profile，*would lose them to the first sync*」，所以做成 opt-in，而不是让每个宿主
  记得关掉
- 桌面端确实自己写：`prepareChrysModelProfiles()` 把账号 `myModelList` 具化为
  `<private>/chrys-home/.chrys/models/<id>.yaml`，并把该目录作为 HOME 交给子进程；
  凭证不进文件（`api_key: ''`），由主进程注入 provider 环境变量
- 传给 iCode 的环境变量里**没有任何 catalog URL / token**，只有
  `CHRYS_MODEL_PROFILE`（`runtime-composition.ts:2161`）

> 结论：原先列出的「断点 ① ACP 进程不轮询」**不成立** —— 这是设计，不是缺陷。

### 3.2 整表替换冲突（已被 opt-in 规避）

若给 ACP 入口打开 `sync_model_catalog=True`，启动时的整表替换会删掉桌面端写入的 profile。
因为默认关闭，该冲突**当前不存在**。

将来若有人为 ACP 入口打开这个开关，会立刻踩到。

### 3.3 运行期刷新只对新会话生效 —— 已知且被接受的设计

| 时机 | 桌面端动作 | iCode 是否感知 |
|---|---|---|
| spawn 之前 | 写 profile 文件、删掉已下线模型的 profile | ✅ 进程启动时加载 |
| 会话运行中 | 账号模型列表变了，重写文件 | ❌ 内存注册表不更新 |

原因：`load_registries()` 只加载一次，之后**外部改文件它不知道**。

桌面端侧**明确接受了这一点**（`runtime-composition.ts:1931-1935`）：

> ... a refreshed account model list makes the next iCode session rewrite them ...
> **Sessions already running keep the profiles their own process loaded at startup;
> Chrys never re-reads them.**

即：刷新只影响**新建**会话，已在跑的会话保持启动时的快照。这是**设计选择，不是缺陷**。

是否要改变它属于产品决策：

- 保持现状：用户刷新模型列表后，要新建会话才能用上新模型
- 若要让老会话也生效：桌面端运行期改走 ACP `profiles/models/write` / `delete`（见 3.4）

**一个仍未消除的边界情况**：已下线模型的 profile 文件被 `removeStaleChrysModelProfiles`
删了，但老会话的 iCode **内存里仍在、仍可被 `set_session_model` 选中**，实际调用会以
账号侧错误失败。这正是 `chrys-model-profile.ts:177-179` 那段注释担心的风险 —— 它只清理了
文件，管不到已运行子进程的内存。

### 3.4 解法现成：运行期改走 ACP 写，而不是写文件

`profiles/models/write`（`server.py:695`）与 `profiles/models/delete`（`server.py:701`）
会同步更新内存注册表：

```python
# src/chrys/app/acp/session_manager.py:437-441
self.load_registries()
deleted = delete_model_profile(profile_id)
if deleted:
    self._model_registry.remove(profile_id)
```

所以桌面端在运行期刷新时，改调这两个 ACP 方法即可 —— 不需要 `settings/reload`，
也不需要重启进程。

`settings/reload` 也能刷新（`session_manager.py:1099-1100` 的 `load_all()`），
但它同时是一次完整 runtime mutation（注释写着 "awaits the rebuild"），太重，
不作为常规路径。

### 3.5 ACP 协议没有模型变更推送

`session/update` 的变体只有：

```
message / thought / tool_call / plan / commands / mode / usage / session_info / config_option
```

**没有 models**。但对桌面端场景影响不大：变更的发起方就是桌面端自己，
它知道何时该推，不需要 iCode 反向通知。

### 数据流方向澄清（易混淆）

| 方向 | 传递的内容 | 机制 |
|---|---|---|
| 服务端 → 桌面端 | 账号模型列表 | `POST /csas/web/model/myModelList` |
| 桌面端 → iCode | 模型**列表** | spawn 前写 profile 文件；运行期应改走 `profiles/models/write｜delete` |
| 桌面端 → iCode | 模型**选择**（当前用哪一个） | `CHRYS_MODEL_PROFILE` / `set_session_model` |
| 服务端 → iCode | 模型列表（**仅 TUI 场景**） | catalog 同步：启动一次 + 轮询 |

**关键点：桌面端场景下，iCode 从不直接跟服务端要模型列表。**

---

## 4. 桌面端不存在「两套数据源」

桌面端 UI 下拉显示的 `myModelList`，和注入 iCode 的 profile，是**同一份数据的两种形态**
—— `prepareChrysModelProfiles()` 把前者具化成后者。iCode 在桌面端场景不自己拉 catalog，
所以没有两份互相打架的列表。

按场景区分只有一张表：

| 场景 | iCode 内模型列表的来源 |
|---|---|
| TUI | iCode 自己的 catalog 接口（整表替换） |
| 桌面端 | 桌面端 `myModelList` → 具化为 profile 注入 |

【D1】**运行期刷新走哪条路？**（对应缺口 3.3）

- **A（推荐）**：桌面端改调 ACP `profiles/models/write` / `delete`
  —— 内存注册表同步更新，无需 reload、无需重启进程
- B：刷新后 respawn 子进程 —— 简单，但丢会话上下文
- C：继续写文件 + 调 `settings/reload` —— 可行，但是完整 runtime mutation，太重

---

## 5. 整表替换风险（当前已规避，见 3.2）

catalog 同步是**整表替换**：不在服务端返回列表里的 profile 会被删除
（`test_replace_profiles_forgets_deleted_profiles` 锁的就是这个行为）。

因为 ACP 入口 `sync_model_catalog=False`，桌面端场景不会触发，冲突不存在。

**遗留风险**：一旦有人为 ACP 入口打开这个开关，桌面端注入的 profile 会被首次同步清空，
而 `CHRYS_MODEL_PROFILE` 指向的 profile 也会随之消失。

【D2】要不要加一道显式防护（例如 ACP 入口硬编码不传该参数，或加断言），
防止后续改动误开？

---

## 6. 待确认项

【C1】**桌面端切换已运行会话的模型是否生效？**

桌面端似乎只用 `CHRYS_MODEL_PROFILE`（写文件 + 环境变量），没有调用
`set_session_model`（`server.py:453`）。若属实，则对**已在跑的会话**切换模型不生效，
必须重启 icode 进程。
需确认 `apps/desktop/src/main/chrys-model-profile.ts` 的调用时机。

---

## 7. 建议的修复优先级

```
【先决策】3.3 运行期刷新是否要让老会话生效  →  5（加防误开防护）  →  2.2（TUI immediate 被吞）
```

理由：

- 3.3 是**产品决策而非缺陷**：现状已被桌面端注释明确接受（"Chrys never re-reads them"）。
  若决定要让老会话也生效，解法是桌面端改走 ACP `write`/`delete`（3.4）
- 5 是防回归，成本极低，顺手做掉
- 2.2 未复现，优先级最低

**没有必修项。** 若 3.3 维持现状，桌面端场景可以不改任何代码。

已确认**不需要**做的：给 ACP 入口开轮询、给 ACP 加 catalog 定时同步 ——
这些与「宿主拥有模型目录」的设计约束冲突。

---

## 附录 A：关键代码索引

### iCode

| 关注点 | 文件:行 |
|---|---|
| 启动一次性同步 | `src/chrys/orchestration/startup.py:277` |
| **opt-in 开关（默认 False）** | `src/chrys/orchestration/startup.py:204` |
| **仅 TUI 传 True** | `src/chrys/app/tui/app.py:1298` |
| **设计约束注释（宿主拥有目录）** | `src/chrys/orchestration/startup.py:222-229` |
| 轮询入口（TUI 唯一调用点） | `src/chrys/app/tui/app.py:991` |
| 同步后回调 | `src/chrys/app/tui/app.py:985-989` |
| "already running" 早退 | `src/chrys/app/tui/app.py:981` |
| 停止轮询 | `src/chrys/app/tui/app.py:996` |
| 登录后立即同步 | `src/chrys/app/tui/screens/main/screen.py:1730` |
| `start_periodic_sync` | `src/chrys/service/profiles/models/catalog.py:689` |
| 无 url / 无凭证返回 None | `src/chrys/service/profiles/models/catalog.py:722-727` |
| `immediate` 先拉一次 | `src/chrys/service/profiles/models/catalog.py:747-748` |
| `catalog_base_url` 按 tier 兜底 | `src/chrys/service/profiles/models/catalog.py:183-198` |
| 凭证读取（实时，无缓存） | `src/chrys/service/profiles/models/catalog.py:440` `_catalog_token` |
| `has_catalog_credential` | `src/chrys/service/profiles/models/catalog.py:465` |
| `fetch_catalog` | `src/chrys/service/profiles/models/catalog.py:507` |
| 注册表整表替换 | `src/chrys/service/profiles/models/registry.py:112-121` |
| `profiles/models/list` | `src/chrys/app/acp/server.py:690` |
| `profiles/models/write` | `src/chrys/app/acp/server.py:695` |
| `profiles/models/delete` | `src/chrys/app/acp/server.py:701` |
| `set_session_model` | `src/chrys/app/acp/server.py:453` |
| write / delete 同步更新内存注册表 | `src/chrys/app/acp/session_manager.py:400`、`435-442` |
| `settings/reload` | `src/chrys/app/acp/server.py:600` |
| reload 时 `load_all()` | `src/chrys/app/acp/session_manager.py:1099-1100` |
| 委托凭证检测（env） | `aixcoding/auth/delegation.py:64-86` |
| `stored_token`：委托优先于 store | `aixcoding/auth/session.py:114-129` |

### agent_studio_new

| 关注点 | 文件:行 |
|---|---|
| spawn `icode acp` | `apps/desktop/src/main/runtime-composition.ts:2118` |
| UI 模型列表来源 | `apps/desktop/src/main/account-model-catalog.ts:14` |
| **具化 profile 到私有 HOME** | `apps/desktop/src/main/chrys-model-profile.ts:95-186` |
| 清理已下线模型的 profile | `apps/desktop/src/main/chrys-model-profile.ts:180`、`193-208` |
| 传 `CHRYS_MODEL_PROFILE` | `apps/desktop/src/main/runtime-composition.ts:2161` |
| 传 `AIXCODING_USER_EHR` | `apps/desktop/src/main/runtime-composition.ts:812` |
| provider 凭证 env 映射 | `apps/desktop/src/main/desktop-agent-connection-service.ts:32-33` |

---

## 附录 B：登录链路（排查延迟时用）

```
浏览器点授权
  → poll_token（1s 一次，DEFAULT_POLL_INTERVAL = 1.0，aixcoding/auth/session.py:51）
      aixcoding/auth/client.py:109
  → fetch_user_info（/user/info，取 userId）   aixcoding/auth/client.py:154
  → store 落盘                                  aixcoding/auth/session.py:211
  → dialog.dismiss_when_topmost(account)        aixcoding/tui/login.py:116
  → _on_login_dismiss → start_catalog_sync(immediate=True)
```

`dismiss_when_topmost` 只在 `self.app.screen is self` 时立即 dismiss
（`src/chrys/app/tui/screens/dialogs/base.py:60`），否则挂起到 `_on_screen_resume`。

mock 服务端：`mock_server/aixcoding_auth/server.py`
- `manual`（默认）：等人在 verify 页面点确认，会打 `confirm user_code=...`
- `auto`：逐次交替 pending/authorized
