# 桌面端 ↔ iCode 交互全景

> 只覆盖 **agent_studio 桌面端与 iCode 之间**的交互，不含 iCode 自带 TUI 的场景。
> 从 `model-catalog-sync-gap-analysis.md` 中提取并补充了进程/环境契约。
> `【Dn】`= 待决策，`【Cn】`= 待确认（未查证）。

---

## 0. 速览

桌面端把 iCode 当作 **ACP over stdio 的子进程引擎**来用，一共 6 个交互面：

| # | 交互面 | 方向 | 通道 |
|---|---|---|---|
| 1 | 进程与传输 | 桌面端 → iCode | spawn + stdio + env |
| 2 | 凭证 / 登录 | 桌面端 → iCode | 环境变量（委托 + provider） |
| 3 | 模型**列表** | 桌面端 → iCode | 私有 HOME 下的 profile 文件 |
| 4 | 模型**选择** | 桌面端 → iCode | `CHRYS_MODEL_PROFILE` / `set_session_model` |
| 5 | Agent Profile | 桌面端 → iCode | profile 文件 + 启动参数 |
| 6 | 会话期调用 | 双向 | ACP 方法 / 通知 |

**核心设计约束（贯穿全文）**：

> 配置归宿主（桌面端）所有。iCode 不主动向服务端要配置 —— 它只读宿主给它的目录和环境变量。

---

## 1. 进程与传输契约

`StdioAcpConnectionFactory`（`runtime-composition.ts:2148`），native ACP，无适配器：

```js
// runtime-composition.ts:2148-2171
new StdioAcpConnectionFactory({
  command: icodeLaunch.command,                 // icode
  args: chrysAcpArgs(icodeLaunch.args, chrysAgent.name),
  environment: { ... },
  maxFrameBytes: 48 * 1024 * 1024,
  chrysDisabledToolNames: chrysAgent.disabledToolNames,
})
```

### 1.1 环境变量契约

按合并顺序（`runtime-composition.ts:2153-2165`）：

| 变量 | 来源 | 作用 |
|---|---|---|
| `icodeLaunch.environment` | 启动配置 | 基础 env |
| `connection.value.environment` | provider 凭证 | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`（`desktop-agent-connection-service.ts:32-37`） |
| `HOME` | `homeDirectory` | **账号私有 HOME**，iCode 从这里解析 `~/.chrys` |
| `APPDATA` | 同上（仅 Windows） | Windows 引擎无 config-root 开关，硬编码 `%APPDATA%\chrys` |
| `CHRYS_MODEL_PROFILE` | `capabilityModelProfileId` | 启动/协商用的模型 |
| `PYAPP_INSTALL_DIR_CHRYS` | prewarm 就绪时 | 指向共享 runtime，避免每个账号各自解包 |

**注意：env 里没有任何 catalog URL / token** —— iCode 在桌面端场景不拉 catalog 的配置前提。

### 1.2 私有 HOME 机制

`chrys-model-profile.ts:64-74` 的注释解释了原因：

> Chrys 没有 configuration-root 开关，POSIX 从 `$HOME` 解析 `~/.chrys`，Windows 引擎
> 硬编码 `%APPDATA%\chrys`，所以同一个目录在 Windows 上要额外用 `APPDATA` 传一次。

目录结构：`<account-private>/chrys-home/.chrys/models/*.yaml`

**profile 文件里不带凭证**（`api_key: ''`），凭证只通过环境变量给子进程
（`chrys-model-profile.ts:89-93`、`runtime-composition.ts:2144-2145`）。

---

## 2. 凭证与登录

### 2.1 委托凭证（delegation）

iCode 侧 `aixcoding/auth/delegation.py` 从环境变量识别"父进程已登录"：

| 优先级 | 变量 | 说明 |
|---|---|---|
| 主 | `CHRYS_AUTH_DELEGATED_TOKEN`（+ `_EHR` / `_NAME`） | 较新桌面端构建 |
| 兼容 | `AIXCODING_USER_EHR` + `OPENAI_API_KEY` | 旧构建（<= fix-1008） |

命中后 `get_login_session().stored_token` 直接返回委托的 token
（`aixcoding/auth/session.py:114-129`），iCode 视作"已登录"，不再跑自己的 device-code 流程。

### 2.2 ⚠️ 一个隐式的耦合

桌面端注入的 **provider 凭证恰好命中兼容分支**：

- `desktop-agent-connection-service.ts:32-33`：`AIxCoding` / `openai` provider → `OPENAI_API_KEY`
- `runtime-composition.ts:812`：`AIXCODING_USER_EHR`

两个变量同时存在 → `detect_delegation()` 返回委托凭证（`delegation.py:82-85`）。

也就是说：**桌面端是为了给 iCode 传「模型调用凭证」才注入这些变量的，副作用是 iCode 同时把它当成了「账号登录凭证」。**

这本身无害（当前 ACP 入口不拉 catalog，用不到这个 token），但它意味着：
**一旦有人给 ACP 入口打开 `sync_model_catalog`，iCode 会立刻用这个 token 去拉 catalog 并整表替换** ——
凭证是现成的，拦不住。

---

## 3. 模型目录交互（核心）

### 3.1 完整流程

| 步 | 谁 | 动作 | 代码 |
|---|---|---|---|
| 1 | 桌面端 | 拉账号模型列表 `POST /csas/web/model/myModelList` | `account-model-catalog.ts:14`；调用点 `index.ts:560` / `1164` |
| 2 | 桌面端 | `applyChrysModelCatalog()` 更新内存 catalog，清空 profile 缓存 | `runtime-composition.ts:1969-1972` |
| 3 | 桌面端 | 建会话时算指纹 `chrysProfilesFingerprint(input)`：命中缓存就复用磁盘文件，未命中才重写 | `runtime-composition.ts:1936-1967` |
| 4 | 桌面端 | 具化：每个模型写 `<private>/chrys-home/.chrys/models/<id>.yaml`；删掉已下线模型的 profile | `chrys-model-profile.ts:95-186`、`180` |
| 5 | 桌面端 | spawn，传 `HOME` + `CHRYS_MODEL_PROFILE` + provider env | `runtime-composition.ts:2146-2171` |
| 6 | **iCode** | 启动时把 `models/*.yaml` 加载进内存注册表 | `load_registries()`，**只此一次** |
| 7 | — | 运行期刷新列表 → 只影响**新建**会话，老会话保持启动时的快照 | `runtime-composition.ts:1934-1935` |

指纹（内容寻址）的作用：列表没变就不重写文件，避免每次建会话都动磁盘。

### 3.2 谁拥有模型目录

**模型列表归宿主所有，iCode 不主动拉取。** 已正确实现：

- `sync_model_catalog` 是 opt-in：`bootstrap_runtime` 默认 `False`（`startup.py:204`），
  **只有 TUI 传 `True`**（`app.py:1298`），ACP 入口不拉
- `startup.py:222-229` 注释写明原因：整表替换只对自己拥有该目录的前端安全；宿主
  （桌面应用、编辑器插件）自己写 profile，*"would lose them to the first sync"*

### 3.3 运行期刷新只对新建会话生效

| 时机 | 桌面端动作 | iCode 感知 |
|---|---|---|
| spawn 之前 | 写 profile、删已下线的 profile | ✅ 进程启动时加载 |
| 会话运行中 | 列表变了，重写文件 | ❌ 内存注册表不更新（`load_registries()` 只加载一次） |

桌面端注释明确接受了这个行为（`runtime-composition.ts:1931-1935`）：

> ... a refreshed account model list makes the next iCode session rewrite them while an
> unchanged list reuses the files already on disk. **Sessions already running keep the
> profiles their own process loaded at startup; Chrys never re-reads them.**

**这是设计选择，不是缺陷。**

**唯一残留的边界情况**：已下线模型的 profile 文件被 `removeStaleChrysModelProfiles` 删了，
但老会话的 iCode **内存里仍在、仍可被 `set_session_model` 选中**，调用会以账号侧错误失败
—— 这正是 `chrys-model-profile.ts:177-179` 注释担心的风险，它只清理文件，管不到已运行
子进程的内存。

### 3.4 若要让老会话也生效：解法现成

`profiles/models/write`（`server.py:695`）与 `profiles/models/delete`（`server.py:701`）
会同步更新内存注册表：

```python
# src/chrys/app/acp/session_manager.py:437-441
self.load_registries()
deleted = delete_model_profile(profile_id)
if deleted:
    self._model_registry.remove(profile_id)
```

所以运行期改调这两个 ACP 方法即可，不需要 `settings/reload`、不需要重启进程。

（`settings/reload` 也能刷新 —— `session_manager.py:1099-1100` 的 `load_all()` —— 但它是
完整 runtime mutation，注释写着 "awaits the rebuild"，太重，不作为常规路径。）

---

## 4. 模型选择

| 机制 | 用途 | 状态 |
|---|---|---|
| `CHRYS_MODEL_PROFILE` env | **启动/协商**用哪个模型；必须挑一个 vision 模型（若有），否则 `initialize` 阶段 `promptCapabilities.image` 会被冻结成 false | 桌面端在用（`runtime-composition.ts:2161`） |
| `set_session_model`（`server.py:453`） | 会话运行中切换模型 | 桌面端**似乎未用** |

`chrys-model-profile.ts:81-86` 解释了为什么启动 profile 必须是 vision 模型：

> Chrys 在 `initialize` 时冻结 `promptCapabilities.image`，所以启动 profile 必须是支持视觉的
> （当账号有时），否则即使会话模型支持视觉，图片 prompt 也会被拒。

【C1】桌面端切换已运行会话的模型时，是否走了 `set_session_model`？若只靠
`CHRYS_MODEL_PROFILE`，则对已在跑的会话不生效（该变量只在进程启动时读）。

---

## 5. Agent Profile 交互

- 启动参数带 agent 名：`chrysAcpArgs(icodeLaunch.args, chrysAgent.name)`（`runtime-composition.ts:2150-2152`）
- 工具禁用清单：`chrysDisabledToolNames`（`runtime-composition.ts:2170`）
- 重写时机（`runtime-composition.ts:1973-1978`）：会话首次创建时，以及 **memory 开关或
  MCP 注册变化时**再重写一次 —— 保证引擎读到的 profile 是最新的

> 注意：Agent Profile 与 Model Profile 的重写策略不同 —— agent 侧明确会在运行中重写，
> model 侧不会。

---

## 6. 会话期 ACP 交互

iCode `src/chrys/app/acp/server.py` 已提供的扩展方法（已查证部分）：

| 方法 | 行 |
|---|---|
| `session/new` / `session/load`（响应带 `models` 快照） | 248 / 305 |
| `set_session_model` | 453 |
| `settings/reload` | 600 |
| `settings/options` | 614 |
| `session/set_config_option` | 623 |
| `profiles/models/list` | 690 |
| `profiles/models/read` | 692 |
| `profiles/models/write` | 695 |
| `profiles/models/delete` | 701 |
| `profiles/agents/delete` | 681 |
| `profiles/agents/reset` | 684 |
| `mcp/test` | 707 |

`session/update` 的变体（ACP 标准）：

```
message / thought / tool_call / plan / commands / mode / usage / session_info / config_option
```

**没有 models** —— 所以模型变更无法从 iCode 主动推送给桌面端。对桌面端影响不大：
变更发起方就是桌面端自己。

【C2】桌面端实际调用了其中哪些？`profiles/*` 系列是否完全未被使用（当前靠写文件）。

---

## 7. 设计约束汇总

1. **配置归宿主**：iCode 不向服务端要配置，只读宿主给的目录 + env
2. **profile 文件不带凭证**：凭证只走环境变量
3. **子进程不重读配置**：`load_registries()` 只加载一次，运行期改文件无效

---

## 8. 待决策 / 待确认

| 编号 | 内容 | 类型 |
|---|---|---|
| 【D1】 | 运行期刷新是否要让老会话也生效？<br>A（推荐）桌面端改调 ACP `write`/`delete`；B respawn 子进程；C 写文件 + `settings/reload` | 产品决策 |
| 【D2】 | 是否加防护，防止有人给 ACP 入口误开 `sync_model_catalog`（一旦开，桌面端注入的 profile 会被首次同步清空） | 防回归 |
| 【C1】 | 桌面端切换已运行会话的模型是否走 `set_session_model`？ | 待查证 |
| 【C2】 | 桌面端实际用了哪些 ACP 扩展方法？`profiles/*` 是否完全没用？ | 待查证 |
| 【C3】 | `OPENAI_API_KEY` 被当成账号凭证的隐式耦合是否有意？（见 2.2） | 待确认 |

**没有必修的功能缺口。** 若【D1】维持现状，桌面端↔iCode 可以不改任何代码。

---

## 附录：代码索引

### iCode

| 关注点 | 文件:行 |
|---|---|
| `sync_model_catalog` opt-in（默认 False） | `src/chrys/orchestration/startup.py:204` |
| 仅 TUI 传 True | `src/chrys/app/tui/app.py:1298` |
| 设计约束注释（宿主拥有目录） | `src/chrys/orchestration/startup.py:222-229` |
| 注册表整表替换 | `src/chrys/service/profiles/models/registry.py:112-121` |
| `profiles/models/list` | `src/chrys/app/acp/server.py:690` |
| `profiles/models/write` / `delete` | `src/chrys/app/acp/server.py:695` / `701` |
| `set_session_model` | `src/chrys/app/acp/server.py:453` |
| write/delete 同步更新内存注册表 | `src/chrys/app/acp/session_manager.py:400`、`435-442` |
| `settings/reload` | `src/chrys/app/acp/server.py:600` |
| reload 时 `load_all()` | `src/chrys/app/acp/session_manager.py:1099-1100` |
| 委托凭证检测（env） | `aixcoding/auth/delegation.py:64-86` |
| `stored_token`：委托优先于 store | `aixcoding/auth/session.py:114-129` |

### agent_studio_new

| 关注点 | 文件:行 |
|---|---|
| spawn `icode acp`（含 env 契约） | `apps/desktop/src/main/runtime-composition.ts:2146-2171` |
| 指纹缓存与 profile 具化调度 | `apps/desktop/src/main/runtime-composition.ts:1931-1972` |
| Agent Profile 重写时机 | `apps/desktop/src/main/runtime-composition.ts:1973-1978` |
| 具化 Model Profile 到私有 HOME | `apps/desktop/src/main/chrys-model-profile.ts:95-186` |
| 清理已下线模型 profile | `apps/desktop/src/main/chrys-model-profile.ts:180`、`193-208` |
| 私有 HOME 命名（POSIX/Windows） | `apps/desktop/src/main/chrys-model-profile.ts:64-74` |
| 账号模型列表来源 | `apps/desktop/src/main/account-model-catalog.ts:14` |
| provider 凭证 env 映射 | `apps/desktop/src/main/desktop-agent-connection-service.ts:32-37` |
