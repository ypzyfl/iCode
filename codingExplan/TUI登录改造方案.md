# iCode TUI 设备码登录改造方案

> 目标：在 `D:\project\iCode`（包 `src/chrys/`，用户端 iCode）从零新增登录能力，协议与接口对齐 `D:\project\ChinaBank\aixcoding-continue`，存储方式对齐 `D:\project\agent_studio_new`。
>
> **外网开发前提**：生产地址 `82.187.34.98` 是行内内网服务，外网不可达，因此本方案**必须先做 Mock 登录服务器**（见第 2 节），否则外网环境下无法联调。
>
> **基线（已锁定）**：`bb45692104bc1d26882729e90fc145e3a114e066`，分支 `lhc/aixcoding_login`，版本 **0.28.0**。本文档所有行号锚点均已按该提交校准；**不再 rebase 到 main**（main 已到 0.29.0，落后本分支 112 个提交之外的方向相反）。
>
> **实施现状（as-built，2026-10-08，方案已落地）**——与原设计有三处不同，阅读下文时以此为准：
> ① 新代码**没有**进 `src/chrys/foundation/auth/`，而是独立包 **`aixcoding/`**（`auth/` 协议+存储+加密，`tui/` 登录对话框），与主包物理隔离便于评审；mock 落在根目录 **`mock_server/aixcoding_auth/server.py`**（不是 `scripts/`）。
> ② **没有**新增 `Settings` 字段：环境切换只靠环境变量 `CHRYS_AUTH_ENVIRONMENT` / `CHRYS_AUTH_SERVER_URL`，由 `aixcoding/auth/environments.py` 在调用期读取（见 §8 修正）。
> ③ 分支后来合并了 main，包版本现为 **0.29.0**（文内行号锚点仍按 0.28.0 标注，仅供参考）。
> ④（2026-10-08 晚补充）`/login`、`/logout` 在 `uv run icode` 下**不能直接用**：`aixcoding/` 未安装进环境，entry point 的 sys.path 不含项目根，直接执行红屏 `ModuleNotFoundError: No module named 'aixcoding'`；开发机临时解法为 `PYTHONPATH=<项目根>`，根治需把 `aixcoding` 加入 pyproject 打包清单（见 §9 已知问题与 §13 收尾④）。
>
> **如何启动**：本地开发 + mock 见 §2.4；生产环境见 §2.5。

---

## 0. 一句话结论

iCode 目前**没有任何 TUI 登录**，所以这不是"改造"而是**新增子系统**。参考项目真正生效的是 **OAuth2 设备码（Device Code）流程**，不是账号密码；凭据由**操作系统加密**（Windows DPAPI / macOS Keychain），明文文件里只存一个引用 ID。

---

## 1. 参考实现速查

### 1.1 登录协议（两个参考项目一致）

不是账号密码。客户端**不收集任何凭据**：取 `device_code` → 打开浏览器由行内统一登录页处理 → 客户端轮询换 token。

> ⚠️ `aixcoding-continue/gui/src/pages/login.tsx` 的邮箱密码表单是**死代码**（`messenger.post("login", ...)` 被注释掉），不要照抄它。

三个接口，全部 `POST` + `application/json`：

| # | 接口                            | 请求体                                                                             | 响应                                                                                            |
| - | ----------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 1 | `{authUrl}/auth/device/code`  | `{"client_id": 78}`                                                             | `{success, result:{interval, device_code, user_code, verification_uri_complete, expires_in}}` |
| 2 | `{authUrl}/auth/device/token` | `{"grant_type":"urn:ietf:params:oauth:grant-type:device_code","device_code":X}` | `{success, result:{error, token, access_token, refresh_token}}`                               |
| 3 | `{dataUrl}/user/info`         | `{"token": T}`                                                                  | 用户信息，`ehr` 是稳定账号标识                                                                            |

轮询状态机：按服务端 `interval`（1–30s）起步；`authorization_pending` 继续等；`slow_down` 则 interval +5s（上限 30s）；`access_denied` / `expired_token` 立即终止；成功取 `result.token ?? result.access_token`；总超时 15 分钟。

**注意**：`aixcoding-continue` 的 `WorkOsAuthProvider.ts:802-851` 用固定 1000ms 轮询、5 分钟超时，而 `agent_studio_new` 用服务端 `interval` + 15 分钟。**本方案取后者**（更规范）。

### 1.2 环境地址

auth 与 data 是**两套不同服务**，host 相同、path 前缀不同：

| 环境                 | authUrl                            | dataUrl                                |
| ------------------ | ---------------------------------- | -------------------------------------- |
| **LOCAL（对接 mock）** | `http://localhost:7777/api/v1`     | `http://localhost:7777/api/v1`         |
| DEV                | `http://81.89.182.150/csas/api/v1` | `http://81.89.182.150/aicoding/api/v1` |
| PROD               | `http://82.187.34.98/csas/api/v1`  | `http://82.187.34.98/aicoding/api/v1`  |

> PROD 已确认取 `82.187.34.98`（agent_studio_new release-flavors.json）。aixcoding-continue 里的 `22.189.54.139` 作为备用保留在常量表注释中。

**LOCAL 档的 `7777` 与参考项目 mockServer 端口完全一致**，所以外网开发时不需要改任何地址，只需把 `auth.environment` 设为 `local`。

覆盖优先级：`auth.server_url`（最高，只替换 protocol+host、保留 path） > 环境变量 `AIXCODING_EXTENSION_AUTH_URL` / `AIXCODING_EXTENSION_DATA_URL`（覆盖 PROD） > 常量表。

### 1.3 存储方式（agent_studio_new）

- 加密后端 = Electron `safeStorage`：Windows **DPAPI**、macOS **Keychain**、Linux **显式明文降级**（`setUsePlainTextEncryption(true)`）
- **双文件设计**：密文信封 `.../private/secrets/<32hex>.json`，明文指针文件只存 `secret:v1:<32hex>` 引用 ID，**不含 token**
- 明文 payload：`{schemaVersion:2, environmentId, userId, purpose:'account_auth', modelCredential, expiresAt}`
- **不解 JWT**：token 不透明，本地自己写 `expiresAt`，TTL 365 天
- 过期主要靠运行时 **HTTP 401 触发登出**
- `refresh_token` 解析了但**从未使用**，无任何 refresh 流程
- 保护不可用时降级**内存态**（不落盘）而非崩溃

### 1.4 ⚠️ 响应字段不一致（联调最容易踩的坑）

参考项目的 mock 与真实后端，**`user/info` 用的是 `data` 字段，另两个接口用 `result` 字段**：

```
device/code  → { success, result: { device_code, ... } }
device/token → { success, result: { error, token, access_token, refresh_token } }
user/info    → { success, data:   { ehr, name, region, deptName, deptId, isStWg, userType } }
```

**客户端必须分开解析**：前两个读 `result`，`user/info` 读 `data`。另外失败是通过 `result.error` / `data` 为 null 表达的，**HTTP 状态码一律 200**（mock 里 token 不匹配时返回的是 `code: 400` 的业务码，HTTP 仍是 200）——所以判断失败不能只看 `response.status_code`。

#### 1.4.1 实测确认的完整信封（照抄 `mockServer/server.js:82-171`）

```jsonc
// device/code —— 成功
{"success": true, "message": null, "code": 200, "timestamp": 1791426132279, "e": null,
 "result": {"interval": 5, "device_code": "...", "user_code": "YX8S-NOHS",
            "verification_uri": "https://www.baidu.com",
            "verification_uri_complete": "https://www.baidu.com?user_code=YX8S-NOHS",
            "expires_in": 600}}

// device/token —— 还在等用户授权（注意 success 仍是 true！）
{"success": true, "message": null, "code": 200, "timestamp": ..., "e": null,
 "result": {"error": "authorization_pending", "token": null, "access_token": null,
            "refresh_token": null, "token_type": null, "expires_in": 0, "scope": null}}

// device/token —— 已授权
{"success": true, ..., "result": {"error": null, "token": "<testToken>",
  "access_token": "这不重要", "refresh_token": null, "token_type": "AICoding",
  "expires_in": 0, "scope": null}}

// user/info —— token 正确
{"success": true, "message": null, "code": 200, "timestamp": ..., "e": null,
 "data": {"ehr": "8769092", "name": "大熊猫", "region": null,
          "deptName": "上海分中心技术平台研发部", "deptId": null, "isStWg": 1, "userType": 1}}

// user/info —— token 错误（⚠️ 连 success 键都没有）
{"message": "用户不存在", "code": 400, "data": null}
```

两条硬结论：

1. **`success` 在 `authorization_pending` 时也是 `true`** —— 轮询成败**只能**看 `result.error`。参考实现 `WorkOsAuthProvider.ts:785` 也确实只看 `result.error` / `result.token`。
2. token 错误的 `user/info` **没有 `success` 键**，只有 `message` / `code` / `data` —— 客户端若写 `body["success"]` 会 KeyError，必须用 `.get()`。

这些形状已 1:1 复刻进根目录 `mock_server/aixcoding_auth/server.py`。

---

## 2. Mock 登录服务器（外网开发必需）

### 2.1 为什么必须有

PROD `82.187.34.98` 与 DEV `81.89.182.150` 都是行内内网地址，**外网直连不可达**。而 `test_network_egress.py` 又禁止测试期非 loopback 出网。所以外网开发必须有一个本地 mock，且这个 mock 在测试里也要能复用（loopback 是放行的）。

### 2.2 参考项目的做法

`D:\project\ChinaBank\aixcoding-continue\mockServer\server.js` —— **真的起了一个本地 HTTP 服务**，不是请求拦截：

- 零框架，只用 Node 原生 `http` 模块
- 端口 `7777`（`:30`），`http.createServer` 在 `:332`，`listen` 在 `:452`
- 用 `Map<RegExp, handler>` 做路由表（`:33`），正则匹配 path
- 未命中返回 404 `{"success":false,"message":"Mock service not found."}`（`:439`）
- 开启方式：`cd mockServer && npm start`；客户端侧把 profile 切成 `LOCAL`（`~/.aixcoding/config.json` 写 `{"profile":"LOCAL"}`，或环境变量 `AIXCODING_EXTENSION_PROFILE`）

它的假数据（`server.js:79-170`）：

```js
device_code: "h824hsdnflsfpoekbdfhuvw2nnhbrgiuwdjlks",
user_code: "YX8S-NOHS",
verification_uri_complete: "https://www.baidu.com?user_code=YX8S-NOHS",
interval: 5, expires_in: 600,
// user/info → data: { ehr:"8769092", name:"大熊猫",
//   deptName:"上海分中心技术平台研发部", isStWg:1, userType:1 }
```

它的轮询状态机是**奇偶交替**（`server.js:31,100-102`）：

```js
const pending = tokenCount % 2 === 0;  // 第 1/3/5 次 pending，第 2/4/6 次成功
tokenCount++;
```

**这个实现的两个问题**（我们不要照抄）：

1. 计数器是全局的，**不按 `device_code` 隔离**，多次登录会互相干扰
2. `verification_uri_complete` 指向 `https://www.baidu.com` —— 外网能开，但点了没用，授权状态不受页面控制，纯靠轮询撞运气

### 2.3 iCode 的 mock 设计

**文件**：`mock_server/aixcoding_auth/server.py`（项目根目录；零新依赖，标准库 `http.server.ThreadingHTTPServer`。2026-10-08 自 `scripts/mock_auth_server.py` 迁出——mock 是联调基础设施，不属于 `src/chrys` 也不属于 `aixcoding` 包）。

**端口**：`7777`，与 LOCAL 档地址对齐，无需额外配置。

**路由**（注意带 `/api/v1` 前缀）：

| Method | Path                        | 说明                                                     |
| ------ | --------------------------- | ------------------------------------------------------ |
| POST   | `/api/v1/auth/device/code`  | 返回 device_code / user_code / verification_uri_complete |
| POST   | `/api/v1/auth/device/token` | 轮询接口                                                   |
| POST   | `/api/v1/user/info`         | 返回 `data` 包裹的用户信息                                      |
| GET    | `/device/verify`            | 本地验证页（仅 manual 模式）                                     |
| POST   | `/device/verify/confirm`    | 验证页点"确认授权"（仅 manual 模式）                                |

**两种模式**（`--mode`）：

| 模式                   | 行为                                                               | 适用场景                         |
| -------------------- | ---------------------------------------------------------------- | ---------------------------- |
| `manual` **（默认，推荐）** | `device/token` 在用户点确认前一直返回 `authorization_pending`，点确认后才返回 token | **外网手工联调**：真实模拟"等用户在浏览器完成登录" |
| `auto`               | 对齐参考项目：奇偶交替，第 1 次 pending、第 2 次成功                                | 自动化测试、冒烟                     |

`manual` 模式相比参考项目的改进：

- 授权状态**按 `device_code` 隔离**（内存 dict），多次登录互不干扰
- `verification_uri_complete` 指向**本地** `http://127.0.0.1:7777/device/verify?user_code=...`，页面是真实可点的确认按钮，形成完整闭环；**不依赖任何外网站点**
- 支持 `--deny` 让下次确认返回 `access_denied`，验证失败分支
- 支持 `--slow-down` 让前 N 次返回 `slow_down`，验证退避逻辑

**响应信封**严格对齐 1.4 节的不一致约定（前两个 `result`、`user/info` 用 `data`），HTTP 状态码一律 200。

**假数据**沿用参考项目（`ehr: "8769092"`、`name: "大熊猫"`、`deptName: "上海分中心技术平台研发部"`），保证与参考项目联调行为一致。

### 2.4 启动本地环境 + mock（外网开发）

两个终端，都在项目根目录：

```bash
# 终端 1：起 mock（默认 manual 模式，127.0.0.1:7777，等待授权页人工点确认）
uv run python mock_server/aixcoding_auth/server.py

# 终端 2：切到 local 档启动 iCode（PYTHONPATH 为 /login 必需，见下方说明）
# bash:       CHRYS_AUTH_ENVIRONMENT=local PYTHONPATH="$PWD" uv run icode
# cmd:        set "CHRYS_AUTH_ENVIRONMENT=local" && set "PYTHONPATH=%CD%" && uv run icode
# PowerShell: $env:CHRYS_AUTH_ENVIRONMENT = "local"; $env:PYTHONPATH = "$PWD"; uv run icode
```

> ⚠️ **`/login` 需要 `PYTHONPATH=<项目根>`（2026-10-08 实测）**：`aixcoding/` 是仓库根源码目录、未安装（pyproject wheel `packages` 只含 `src/chrys`），而 `uv run icode` 是 entry point 启动，sys.path 不含项目根——直接 `/login` 红屏 `ModuleNotFoundError: No module named 'aixcoding'`。`uv run python <项目根脚本>` 不需要（脚本目录自动进 sys.path[0]）。不执行 `/login`、`/logout` 则完全不受影响（启动静默检查吞掉一切异常）。根治见 §9 已知问题。

进 TUI 后输入 `/login`：弹出登录对话框 → 自动打开浏览器授权页（`http://127.0.0.1:7777/device/verify?user_code=...`）→ 点 *Confirm authorization* → 对话框关闭、toast「已登录：大熊猫」。详细人工验证步骤见《启动与登录人工验证指南》。

mock 的失败分支开关：

```bash
uv run python mock_server/aixcoding_auth/server.py --mode=auto      # 轮询奇偶交替 pending/成功（冒烟，无需人工确认）
uv run python mock_server/aixcoding_auth/server.py --deny           # 授权页点确认后返回 access_denied
uv run python mock_server/aixcoding_auth/server.py --slow-down 3    # 前 3 次轮询返回 slow_down（验证退避）
```

> ⚠️ 原方案"在 `~/.chrys/settings.yaml` 里设 `auth.environment: local`"**不可行**——`Settings` 里没有 auth 字段（见 §8 修正），环境切换只有环境变量一条路。会话内 `/login` 走的是**进程启动时**解析的环境档，改环境变量后必须重启 iCode。

### 2.5 启动生产环境（行内内网）

生产档是**默认值**，不做任何配置直接启动即可：

```bash
uv run icode    # CHRYS_AUTH_ENVIRONMENT 未设置时默认 prod
```

- 登录目标：auth `http://82.187.34.98/csas/api/v1`，data `http://82.187.34.98/aicoding/api/v1`——要求**机器在行内内网**（或 VPN 可达）；
- 回内网后建议先验活再进 TUI：

```bash
curl -X POST http://82.187.34.98/csas/api/v1/auth/device/code \
  -H "Content-Type: application/json" -d '{"client_id":78}'
```

- 凭据按环境隔离：prod 档存 `<config_dir>/users/prod/`（Windows `%APPDATA%\chrys\users\prod\`），与 local/dev 互不干扰；
- 显式指定（等价于默认）：`set CHRYS_AUTH_ENVIRONMENT=prod`；临时改指向用 `CHRYS_AUTH_SERVER_URL=http://<host>[:port]`（只替换 protocol+host，保留 `/csas` 与 `/aicoding` path 前缀；非法值被忽略回落默认）；
- 不通时改用备用 `22.189.54.139`：`set CHRYS_AUTH_SERVER_URL=22.189.54.139` 即可，无需改代码；
- 认证请求 `trust_env=False`（`aixcoding/auth/client.py`）：**不走系统/环境代理**——HTTP(S)_PROXY 指向本地代理时不会劫持登录流量（本地代理答 502 明文会被误判为服务端错误、静默登出），内网直连即预期行为；
- **当前发布 wheel 不含 `aixcoding`**（打包只含 `src/chrys`），打包产物上的 `/login` 同样会 `ModuleNotFoundError`——内网验证 `/login` 前需先落地 §9 的打包修复（开发机源码方式则按 §2.4 加 `PYTHONPATH`）；普通对话不受影响。

### 2.6 测试复用

`mock_server/aixcoding_auth/server.py` 除 CLI 外提供可导入 API（`MockAuthConfig` / `MockAuthState` / `create_server`），测试里可起 loopback 实例作为**集成测试桩**（loopback 不被 `test_network_egress` 拦截）。单元测试用 `httpx.MockTransport` 注入 `AuthClient`，集成测试用真 mock server，两层覆盖（见 §11）。

---

## 3. 已确认的决策

| 项             | 决策                                                                 |
| ------------- | ------------------------------------------------------------------ |
| 协议            | 设备码流程，无本地回调端口                                                      |
| 存储            | 参考 agent_studio_new：OS 级加密 + 明文指针 + 降级内存态                          |
| 强制程度          | 参照 aixcoding-continue：启动**静默检查**，未登录不阻断浏览；另提供 `/login` 主动登录        |
| token 用途      | **仅身份展示**（`/user/info` 取 ehr/name/dept），不做模型配置拉取、不做 LLM 注入、不做服务端登出 |
| PROD 地址       | `http://82.187.34.98`（内网，外网联调走 mock）                               |
| refresh_token | 保留字段，不实现自动刷新                                                       |
| 开发期登录         | 自建 `mock_server/aixcoding_auth/server.py`（原 `scripts/mock_auth_server.py`，已迁出），端口 7777，对接 LOCAL 档 |

---

## 4. ~~前置修复（阶段 0）~~ —— ❌ 已作废：这不是 bug

> **本节是踩坑记录，不是待办。原结论错误，已实测推翻。**

原稿件认为 `src/chrys/foundation/platform/__init__.py` 的这两处是「Python 2 语法、HEAD 自带的 bug」：

```python
# :117
except OSError, AttributeError:                                # 不是 bug

# :342
except subprocess.SubprocessError, FileNotFoundError, OSError:  # 不是 bug
```

**错在哪**：当初用**系统 Python 3.13** 做了 `py_compile`，得到

```
SyntaxError: multiple exception types must be parenthesized
```

但项目 `pyproject.toml` 写的是 `requires-python = ">=3.14"`，实际解释器是 **3.14.8**(`.venv/Scripts/python.exe`)。**Python 3.14 新增了 PEP 758：允许 `except` 后跟无括号的多异常类型**。实测：

```bash
# 3.13  → SyntaxError
# 3.14.8 → 编译通过；import 成功；get_platform().config_dir 正常返回
#          C:\Users\lhc\AppData\Roaming\chrys
```

**更关键的反证**：ruff 的 `target-version = "py314"`，`ruff format` 会**主动把 `except (A, B):` 改回 `except A, B:`**。也就是说「给它加上括号」这种"修复"会让 `ruff format --check` **直接失败**。

### 因此

- **不要动这两个文件**，`git diff` 应保持干净（已确认回退后为空）
- **阶段 0 取消**，实施直接从原阶段 1（mock 服务器）开始
- ⚠️ **永远用 3.14 跑本项目**，不要用 3.13 去 import `src/chrys/`，会误报语法错误
- 排查类似"语法错误"时先确认解释器版本：`uv run python -VV`

---

## 5. 模块落点

> **✅ as-built 修正（2026-10-08）**：实现没有落在 `src/chrys/foundation/auth/`，而是独立包 **`aixcoding/`**（`aixcoding/auth/` 七个文件 + `aixcoding/tui/login.py`），与下表一一对应但路径不同，并多出一个原设计没有的 `session.py`（`LoginSession` 门面 + `get_login_session()` 进程单例——MemoryBackend 降级时凭据活在后端实例里，必须全程共享一个 session）。理由：`tests/architecture/test_layering.py` 只扫 `src/chrys`，独立包不受分层 DAG 与 i18n 提取约束，全部新增代码可作为一个单元评审。详见 `aixcoding/README.md` 与 `codingExplan/项目索引.md` §5。

原设计落点（已作废，留作背景）：

新增 `src/chrys/foundation/auth/`。

**为什么放 foundation 而不是 service**：协议客户端与凭据存储是无业务语义的通用原语（HTTP + 加密 + 文件）；httpx 已是主依赖；service 与 app 都可**单向**依赖 foundation（`tests/architecture/test_layering.py:41` 定义 foundation(0) < kernel(1) < service(2) < orchestration(3) < app(4)，禁止反向导入）。UI 全部留在 app 层。

| 文件                                | 职责与关键 API                                                                                                                      |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `foundation/auth/__init__.py`     | re-export 公共 API                                                                                                               |
| `foundation/auth/types.py`        | `Environment(str, Enum)`（LOCAL/DEV/PROD）；`DeviceCode` / `TokenResponse` / `TokenResult` / `AccountInfo` / `StoredCredential`   |
| `foundation/auth/errors.py`       | `AuthError` / `AuthNetworkError` / `DevicePollCancelled` / `DevicePollTimeout` / `ProtectUnavailable`                          |
| `foundation/auth/environments.py` | 三档地址常量表 + 环境变量与 `server_url` 覆盖解析                                                                                              |
| `foundation/auth/crypto.py`       | `ProtectBackend` Protocol（含 `degraded: bool`）；`WindowsDPAPI` / `MacOSSecurity` / `Plaintext` / `MemoryBackend`；`get_backend()` |
| `foundation/auth/storage.py`      | 密文信封 + 明文指针；`load_credential()` / `store_credential()` / `clear()` / 完整性校验                                                     |
| `foundation/auth/client.py`       | `AuthClient(auth_url, data_url, http=None)`：`request_device_code()` / `poll_token()` / `fetch_user_info()`                     |

URL 拼接复用 `foundation/net/url.py` 或 `urllib.parse.urlsplit`，不新增 `foundation/net` 文件。

---

## 6. 加密后端（纯 Python，零新依赖）

`pyproject.toml` **不需要改动** —— 不引入 keyring、不引入 cryptography。

| 平台      | 方案                                                                                        | 理由                                                  |
| ------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Windows | ctypes 直调 `CryptProtectData` / `CryptUnprotectData`（`crypt32.dll` + `DATA_BLOB`）          | 与同包 `_win32_clipboard_api()`（`platform/__init__.py:193`）的 ctypes 风格一致：`WinDLL(..., use_last_error=True)` + 显式赋 `argtypes`/`restype`；零新依赖，不破坏精确 `==` pin 规范 |

> ⚠️ **基线修正**：原稿写「对齐同包 `c_api.py`」，但 `c_api.py` 只存在于 main（0.29.0），**0.28.0 基线的 `foundation/platform/` 下没有该文件**。照 `_win32_clipboard_api()` 写即可。
| macOS   | subprocess 调 `/usr/bin/security add-generic-password` / `get-generic-password`（timeout=2） | 零新依赖；keyring 库的 backend 选择与降级逻辑不可控                  |
| Linux   | 明文文件（`degraded=True`，0600 + `O_NOFOLLOW`）                                                 | 与参考的 `setUsePlainTextEncryption(true)` 一致           |

**失败降级**：任何平台探测失败 → `MemoryBackend`（`degraded=True`，进程内 dict，不落盘，下次启动需重登，状态栏提示）。**绝不因加密不可用而崩溃**。

---

## 7. 凭据存储设计

目录布局（`<config_dir>` = Windows `%APPDATA%/chrys`，macOS/Linux `~/.chrys`）：

```
<config_dir>/users/<environment_id>/
├── current                      # 明文指针，内容仅 "secret:v1:<32hex>"，不含 token
└── private/secrets/<32hex>.json # 密文信封
```

密文信封：

```json
{"schemaVersion": 1, "purpose": "account_auth",
 "ciphertext": "<base64>", "ciphertextSha256": "<hex64>"}
```

信封内明文 payload：

```json
{"schemaVersion": 2, "environmentId": "...", "userId": "...", "ehr": "...",
 "purpose": "account_auth", "token": "...", "refresh_token": "...", "expiresAt": 1234567890}
```

安全细节：

- **原子写**：临时文件 → `os.replace`；写前校验 sha256
- **权限**：目录 0700、文件 0600（Windows 不支持 0600，跳过；目录在用户 `%APPDATA%` 下 ACL 已隔离）
- **防 symlink**：`os.open(..., O_NOFOLLOW)`（仅 posix）
- **完整性**：sha256 不符 → 视为损坏，清指针并要求重登
- **TTL**：本地写 `expiresAt`，365 天，不解 JWT



---

## 8. 配置接入（SettingSpec）

> **✅ as-built 修正（2026-10-08）**：本节**未实施**——`settings.py` 没有新增任何 auth 字段，`auth.environment` / `auth.server_url` 都不是 settings key。环境切换完全由 `aixcoding/auth/environments.py` 在调用期读进程环境变量完成：
>
> | 环境变量 | 作用 | 默认/非法值 |
> |---|---|---|
> | `CHRYS_AUTH_ENVIRONMENT` | 选环境档 `local` / `dev` / `prod` | 默认 `prod`；未知值回落 `prod` |
> | `CHRYS_AUTH_SERVER_URL` | 覆盖两个 URL 的 protocol+host（保留 path 前缀） | 未设不动；非法值忽略 |
>
> 解析时机在 `bootstrap_runtime()` 冻结进程环境之后，调用期读取稳定；改环境变量后需重启 iCode。要"持久化"就写进 shell 启动脚本或用启动器包一层。若未来仍想收编进 Settings 面板，可按原设计补 `ProjectMerge.DENY` 字段。

原设计（已作废，留作背景）：

`src/chrys/foundation/config/settings.py` 的 `Settings`（frozen dataclass，`:761`）新增两个字段：

| 字段 | key | env | Kind | Apply | ProjectMerge | 默认 |
|---|---|---|---|---|---|---|
| `auth_environment` | `auth.environment` | `CHRYS_AUTH_ENVIRONMENT` | ENUM（local/dev/prod） | RESTART | **DENY** | `"prod"` |
| `auth_server_url` | `auth.server_url` | `CHRYS_AUTH_SERVER_URL` | TEXT | RESTART | **DENY** | `""` |

`ProjectMerge.DENY` 的理由：凭据类配置禁止项目层（workspace）设置，避免仓库里的 `.chrys` 配置劫持登录目标。

**不需要额外 .env 支持**：`Source.ENV` 已读进程环境变量，`bootstrap_runtime()` 的 `freeze_process_env()` + `inject_bootstrap_dotenv()` 会自动注入。

---

## 9. TUI 集成

> **✅ as-built（2026-10-08，已实现）**——与原设计的差异：
> - 对话框在 `aixcoding/tui/login.py`：`LoginDialog(BaseDialog[AccountInfo | None])` + `login.tcss`。`on_mount` 起 `asyncio.create_task` 跑完整流程（取码 → 展示 user_code + 验证 URL 并自动开浏览器 → `complete_login` 轮询 → 成功 `dismiss_when_topmost(account)`）；所有失败分支把对话框变成红字错误。文案**内联中文**（i18n 流水线不扫 `aixcoding/`，见 `aixcoding/tui/__init__.py` 说明）；Esc 绑定为 `localized_binding("escape", "cancel", CANCEL_BINDING, priority=True)`，`_before_dismiss` 置 `cancel_event` 让轮询在下一个检查点干净退出。
> - `/login` `/logout` 已注册在 `screens/main/commands.py`：`SlashCommandDef("login"/"logout", ..., allow_while_running=True, man_page=...)`，带 man 帮助页；动作经端口 `SlashCommandActions.open_login / perform_account_logout` 进入 `screens/main/screen.py::_open_login_dialog / _perform_logout`——成功 toast「已登录：{name}」、登出 toast「已退出登录」、未登录警告 toast（这三个走 src i18n，key `tui.login.*`，已入 catalog）。
> - 静默检查在 `app/tui/app.py::on_mount` **末尾**：`self._login_silent_check_task = asyncio.create_task(self._silent_login_check())`，内部 `contextlib.suppress(Exception)` 调 `get_login_session().check_silent()`——离线不算登出（保留凭据）、被服务端拒绝的凭据自清理、任何异常吞掉不弹 UI；`on_unmount` 取消该任务。原设计的 401/状态栏展示未做（登录态目前无状态栏指示，仅 toast）。
> - **⚠️ 已知问题（2026-10-08 实测）**：`_open_login_dialog` / `_perform_logout` 的延迟 `from aixcoding... import ...` 在 `uv run icode` 下红屏 `ModuleNotFoundError: No module named 'aixcoding'`——`aixcoding/` 未安装进 `.venv`（pyproject `[tool.hatch.build.targets.wheel] packages = ["src/chrys"]` 不含它），而 entry point 启动的 sys.path 不含项目根（pytest 与根目录脚本各自靠自身机制把项目根放进 sys.path，所以测试与 `verify_login_dialog.py` 都能跑，掩盖了该洞）。临时解法：启动前 `PYTHONPATH=<项目根>`。根治：`packages` 增加 `"aixcoding"` 并 `uv sync --extra all`，连带修好发布 wheel（当前打包产物上 `/login` 同样崩）。启动静默检查因 `contextlib.suppress(Exception)` 不受影响，未登录浏览不受限。

原设计（背景，行为已按上实现）：

### 9.1 登录对话框

新增 `src/chrys/app/tui/screens/dialogs/login.py`（`LoginDialog`）+ `login.tcss`，继承 `BaseDialog`（`screens/dialogs/base.py:20`）。

两个必须注意的点：

1. **binding 链陷阱**：`base.py:34-36` 注释明确 —— `ModalScreen` 会终止 Textual 非优先 binding 链，所以 Escape 取消必须**自行重复绑定**：`BINDINGS = [*INSERT_CLIPBOARD_BINDINGS, Binding("escape", "cancel_login", "Cancel")]`
2. **`dismiss_on_backdrop=False`**：登录进行中不允许点背景关闭；用 `dismiss_when_topmost()` 处理延迟 dismiss 竞态

界面内容：可复制只读的 `verification_uri_complete` 与 `user_code`、等待 spinner、剩余时间提示。

### 9.2 主动入口

`screens/main/commands.py` 新增 `/login`、`/logout` 斜杠命令（`SlashCommandDef` + `msg()` i18n），与 `/theme`、`/sessions` 同机制。状态栏展示当前用户（ehr 或 name），未登录不显示。

### 9.3 静默检查（不阻断）

在 `app/tui/app.py:916 on_mount` **末尾**追加（不动 `:916-:946` 现有流程，追加点落在 `:946` 之后）：

```python
self._auth_task = asyncio.create_task(self._silent_auth_check())
```

`_silent_auth_check()` 逻辑：`load_credential(active_env)` → 有且未过期 → `fetch_user_info()` 校验 → 成功更新状态栏；失败或 401 → **静默清除内存态，不弹 warning**（与参考的 `silent: true` 一致）。未登录不阻断浏览。

---

## 10. 异步轮询实现要点

- `httpx.AsyncClient` 可注入（测试传 `MockTransport`）
- 轮询本体是**后台 asyncio 任务**，不是 Textual 定时器；定时器只用于 UI 刷新
- **不阻塞 `on_mount`**：沿用项目先例 `asyncio.create_task`（`app.py:944`）
- 取消：`asyncio.Event` + 对话框 `_before_dismiss` 内 `task.cancel()`，任务内 `except asyncio.CancelledError: raise` 干净退出，避免任务泄漏

---

## 11. 测试策略

> **✅ as-built（2026-10-08）**：测试全部落在 **`tests/app/aixcoding/`**（不是原计划的 `tests/foundation/auth/` + `tests/app/`）：`test_auth_{client,crypto,environments,session,storage,types}.py`、`test_login_dialog.py`、`test_login_command_wiring.py` + conftest。协议单测用 `httpx.MockTransport` 注入 `AuthClient`；对话框测试注入假 `LoginSession`/`open_browser`。回归命令：`uv run pytest tests/app/aixcoding -n 0`。
> ⚠️ 已知问题：`test_login_dialog.py::test_login_dialog_cancel_stops_without_storing` 在 Windows 上超时（挂 pilot 屏幕稳定等待，疑似 Windows IOCP 下 asyncio 取消不回卷）；`test_probe_cancel.py` 是定位探针，定位完成后一并删除。

> ⚠️ `tests/architecture/test_network_egress.py` 在 pytest_configure 阶段**硬拦截非 loopback 出网（含 DNS）**，所以要么打桩，要么用 loopback 的 mock server。

原计划覆盖表（背景）：

| 文件 | 覆盖内容 |
|---|---|
| `tests/foundation/auth/test_client.py` | `httpx.MockTransport` + 假时钟；完整流程、pending→success、slow_down 间隔递增、access_denied/expired_token 终止、15 分钟超时、取消、401 登出 |
| `tests/foundation/auth/test_storage.py` | `tmp_path`；原子写、0600、O_NOFOLLOW、sha256 完整性、损坏清理、跨环境隔离、内存态降级不写盘 |
| `tests/foundation/auth/test_crypto.py` | `MemoryBackend` 降级逻辑；DPAPI / macOS security 标 `@pytest.mark.integration` |
| `tests/foundation/auth/test_mock_server.py` | mock server 自身：`result`/`data` 字段约定、manual 模式授权前后状态跃迁、按 device_code 隔离、deny/slow_down 开关 |
| `tests/app/test_login_dialog.py` | Textual `run_test()`；显示 URL/code、Esc 取消、成功后状态栏更新 |

`scripts/chrys_test.py` **无需加 watch** —— smart 模式按 import 图 + 邻近规则自动发现。

---

## 12. 文档与 i18n

> **✅ as-built（2026-10-08）**：i18n 半边已完成——src 侧新 key 全部入了 catalog（`tui.commands.description.login/logout`、`tui.login.succeeded/logged_out/not_logged_in`、`tui.man.login.body/logout.body`，zh-Hans 已翻译并编译）；对话框内部文案因 `aixcoding/` 不在 i18n 扫描范围而**内联中文**（见 §9）。docs 用户手册章节（下表全部条目）**尚未编写**，仍是待办。

> ⚠️ **基线修正**：原稿写的 `docs/en/tui/`、`docs/en/configuration.md` **在本仓库根本不存在**（main 上也没有）。实际文档树是 `docs/{zh-Hans,en}/{start,guides,reference}/`，且新增页面必须同时登记到 `docs/index.yaml` 的 `topics`。

文档树（0.28.0 实际）：

```
docs/index.yaml                        # 导航；新增页面必须在这里登记 id + path（双语共享）
docs/en/start/{what-is-icode,getting-started}.md
docs/en/guides/daily-use/{sessions,workspaces}.md
docs/en/guides/configuration/*.md      # settings.md 是配置主入口
docs/en/reference/settings.md          # 全量配置项参考
docs/en/reference/tui-slash-commands.md# 全量斜杠命令参考
docs/zh-Hans/...                       # 与 en 一一对应
```

本方案要动的：

| 文件 | 动作 | 说明 |
|---|---|---|
| `docs/{en,zh-Hans}/guides/daily-use/login.md` | **新增** | 登录章节（设备码流程、状态栏用户展示、`/login` `/logout`） |
| `docs/{en,zh-Hans}/guides/configuration/settings.md` | 追加 | 面向用户的 `auth.environment` / `auth.server_url` 说明 |
| `docs/{en,zh-Hans}/reference/settings.md` | 追加 | 两个 key 的规格表（含 env 变量、默认值） |
| `docs/{en,zh-Hans}/reference/tui-slash-commands.md` | 追加 | `/login`、`/logout` 条目 |
| `docs/index.yaml` | 追加 | 在 `daily_use` 组下登记 `login` 条目（`id: login`，`path: guides/daily-use/login.md`） |
| 新增开发者文档 | 新增 | mock server 启动与 manual/auto 两模式（参考项目 mockServer 无 README，我们自己补）；可放 `docs/{en,zh-Hans}/guides/running/` 或仓库根的开发者说明 |

- 新增 i18n key（均带 `fallback=`）：`tui.commands.description.login`、`tui.commands.description.logout`、`tui.auth.dialog.*`、`tui.status.user` 等
- 流程：`uv run python scripts/i18n.py extract` → `update` → `translate` → `compile` → `check`
- **双语一致性**：`tests/architecture/test_copy_freshness.py` 会校验 en / zh-Hans 页面对应，两边必须同提交落地

---

## 13. 分阶段实施

**✅ 实施完结（2026-10-08 as-built）**：

| 阶段 | 内容 | 状态 | 说明 |
|---|---|---|---|
| ~~0~~ | ~~修 `platform/__init__.py:117,342`~~ | **❌ 作废** | 3.14 合法语法，不是 bug（见第 4 节） |
| 1 | mock 服务器 | **✅ 完成** | `mock_server/aixcoding_auth/server.py`（manual/auto + 本地验证页 + deny/slow-down），2026-10-08 自 `scripts/` 迁出 |
| 2 | auth 模块 | **✅ 完成** | 落在 `aixcoding/auth/`（types/errors/environments/client/crypto/storage + 新增 `session.py` 门面），非 `src/chrys/foundation/auth/`；测试 `tests/app/aixcoding/` |
| 3 | Settings 字段 | **⛔ 改道** | 不进 settings.py，只用环境变量 `CHRYS_AUTH_ENVIRONMENT` / `CHRYS_AUTH_SERVER_URL`（见 §8） |
| 4 | TUI 集成 | **✅ 完成** | `aixcoding/tui/login.py` + `commands.py` 注册 `/login` `/logout` + `screen.py` 端口动作 + `app.py` 静默检查（见 §9） |
| 5 | docs 双语用户手册 | **⬜ 待做** | i18n catalog 部分已完成；`docs/{en,zh-Hans}/` 的登录章节未写（见 §12 表） |

剩余收尾：① §12 表中的 docs 双语页面 + `docs/index.yaml` 登记；② 删除定位探针 `tests/app/aixcoding/test_probe_cancel.py` 与根目录 `verify_login_dialog.py`（接线完成后即冗余）；③ Windows 上对话框 cancel 测试超时问题定位（§11）；④ **`aixcoding` 未安装**——`uv run icode` 下 `/login` 红屏 `ModuleNotFoundError`，开发机临时靠 `PYTHONPATH`；根治需把 `aixcoding` 加入 `[tool.hatch.build.targets.wheel] packages` 后 `uv sync --extra all`（发布 wheel 目前同样缺该包，见 §9 已知问题）。

启动/验证入口：本地 + mock 见 §2.4，生产见 §2.5，人工验证步骤见《启动与登录人工验证指南》。

### 阶段 1 实测记录（mock 服务器，已落地；文件现位于 `mock_server/aixcoding_auth/server.py`）

文件：`mock_server/aixcoding_auth/server.py`（零新依赖，标准库 `http.server.ThreadingHTTPServer`）。

已验证通过：

| 用例 | 结果 |
|---|---|
| `POST /api/v1/auth/device/code` | 返回 `result.{interval,device_code,user_code,verification_uri,verification_uri_complete,expires_in}` |
| manual 模式：确认前轮询 | `result.error = "authorization_pending"`，且 **`success` 仍为 `true`** |
| manual 模式：验证页点确认 → 再轮询 | 返回 `result.token`，`access_token` = `这不重要`、`token_type` = `AICoding`（对齐参考 mock） |
| `POST /api/v1/user/info`（正确 token） | `data = {ehr:"8769092", name:"大熊猫", region:null, deptName:"上海分中心技术平台研发部", deptId:null, isStWg:1, userType:1}` |
| `POST /api/v1/user/info`（错误 token） | `{message:"用户不存在", code:400, data:null}` —— **无 `success` 键**，HTTP 仍 200 |
| auto 模式 + `--slow-down 2` | poll1/2 = `slow_down`，poll3 = `authorization_pending`，poll4/5 = token |
| `--deny` | 确认后轮询返回 `access_denied` |
| 未知 `device_code` | `expired_token` |
| 未知路由 | `{"success": false, "message": "Mock service not found."}` |
| `--port 0`（测试用随机端口） | `verification_uri_complete` 正确回填真实端口（初版有 bug，已修） |
| `ruff check` + `ruff format --check` | 全部通过 |

响应形状已**逐字段对齐**参考项目 `mockServer/server.js`：含 `message` / `code` / `timestamp` / `e` 四个外壳字段，以及 `result` 与 `data` 的字段不一致。

> ⚠️ **实施阶段 2 时必须记住**：`device/token` 的 `success` 在 pending 时也是 `true`，判断成败**只能**看 `result.error`；参考实现 `WorkOsAuthProvider.ts:785` 正是这么做的（只读 `result.error` 与 `result.token`，完全不看 `success`）。

**阶段 1 优先于阶段 2** —— 先有 mock 才能在外网联调，避免对着内网地址盲写客户端。

每阶段单独跑 ruff / format / ty gate。提交用 `--no-verify`，**绝不用 `git add -A`**。

---

## 14. 风险清单

| # | 风险 | 规避 |
|---|---|---|
| 1 | **内网不可达导致无法联调** | 阶段 1 先做 mock，全程用 `local` 环境开发；回内网后再验 PROD |
| 2 | **`user/info` 用 `data` 而非 `result`**，与另两个接口不一致 | 客户端分开解析；mock 严格复刻该不一致，测试断言字段路径 |
| 3 | **HTTP 恒 200、错误靠 `result.error` 表达** | 不依赖 `status_code` 判断成败，必须解析信封 |
| 3a | **`success` 在 `authorization_pending` 时也是 `true`** | 轮询分支只看 `result.error`，不看 `success`（参考实现也是这么做的） |
| 3b | **token 错误时 `user/info` 没有 `success` 键** | 取值一律 `.get()`，禁止 `body["success"]` |
| 3c | **用 3.13 去 import `src/chrys/` 会误报 SyntaxError**（PEP 758 无括号多异常 3.14 才合法） | 一律走 `uv run`（3.14.8）；`ruff format` 甚至会把 `(A, B)` 改回 `A, B`，别"修"它 |
| 4 | DPAPI 在无头会话（RDP/CI）失败 | `get_backend()` 内 try，失败降级 `MemoryBackend`，状态栏提示 |
| 5 | macOS `security` 首访弹 GUI keychain 授权框 | timeout=2，失败降级内存态 |
| 6 | `server_url` 覆盖语义错误 | 只替换 protocol+host 保留 path；`urlsplit` 校验失败视为 unset，回落常量表 |
| 7 | 测试打到真实行内地址 | 全部 MockTransport 或 loopback 桩 |
| 8 | Textual 任务泄漏 | `_auth_task` / 轮询 task 在 on_unmount 与 `_before_dismiss` 内取消 |
| 9 | 轮询取消与 dismiss 竞态 | `dismiss_when_topmost()` + `cancel_event` |
| 10 | Windows 不支持 0600 | posix 上 chmod，Windows 跳过（目录在 `%APPDATA%` 下 ACL 已隔离） |
| 11 | `Settings` 新字段破坏持久化测试 | 用 `ProjectMerge.DENY`，跑 settings 相关既有测试 |
| 12 | i18n key 缺失导致崩溃 | 所有新文案 `msg(..., fallback=...)` |
| 13 | trajectory manifest 漂移 | `foundation/auth/client.py` 的 await 可能触发 `trajectory_wait_manifest.json` 检测；若报漂移按其提示重新生成，不手改 |
| 14 | refresh_token 未实现刷新 | 长会话 token 可能中途失效 → 靠 401 静默清除后重登 |
| 15 | **PROD host 两个参考项目不一致** | 已选 `82.187.34.98`。回内网后先验活一次： |
| 16 | **`aixcoding/` 未安装：`uv run icode` 与发布 wheel 都缺它** → `/login`、`/logout` 红屏 `ModuleNotFoundError: No module named 'aixcoding'` | 临时 `PYTHONPATH=<项目根>`；根治 = pyproject `[tool.hatch.build.targets.wheel] packages` 增加 `aixcoding` + `uv sync --extra all`（见 §9 已知问题、§13 收尾④） |

```bash
curl -X POST http://82.187.34.98/csas/api/v1/auth/device/code \
  -H "Content-Type: application/json" -d '{"client_id":78}'
```

若不通，改用备用 `22.189.54.139`（改 `environments.py` 一行常量即可）。
