# iCode TUI 登录改造 —— 执行计划

> 基线：`bb45692104bc1d26882729e90fc145e3a114e066`（iCode 0.28.0），分支 `lhc/aixcoding_login`，不合并 main。
> 方案全文：`codingExplan/TUI登录改造方案.md`（协议、信封形状、存储设计、风险清单）。
> **本文件是唯一执行跟踪文档**：每完成一个阶段就更新状态与执行日志。
>
> **交付边界（用户确认）**：本计划只做「登录」本身 —— 设备码流程、凭据加密存储、TUI 登录对话框、`/login` `/logout` 命令、启动静默检查。登录完成（token 已存储 + 用户信息已取回）即为交付点；**token 之后如何用于 AI 请求/会话管理由其他同事开发**。给同事的接口边界 = `aixcoding.auth.LoginSession`（`check_silent` / `complete_login` / `logout` / `stored_token` / `environment`）。

---

## 0. 硬约束（已实测核实）

| # | 约束 | 依据 |
|---|---|---|
| 1 | **全部新增代码放 `aixcoding/`**，`src/chrys` 只允许"接线"级改动（commands.py、app.py、pyproject） | 用户指令 + `aixcoding/README.md` 约定 |
| 2 | `tests/` 顶层目录白名单：`{architecture, support, app, orchestration, service, kernel, foundation, integration}` —— **不能建 `tests/aixcoding/`** | `tests/architecture/test_test_layout.py:18-27` |
| 3 | CI 分区测试要求每个测试模块恰好被一个 shard 覆盖 —— 测试放 `tests/app/` 下即自动覆盖，**无需改 CI** | `tests/architecture/test_ci_test_partitions.py:20` |
| 4 | 分层 DAG 只扫 `src/chrys`，`aixcoding/` 不受反向导入约束 | `tests/architecture/test_layering.py:29` |
| 5 | i18n 只扫 `src/chrys`（`scripts/i18n.py:61`）—— `aixcoding/` 内的文案**不会**进 catalog，TUI 文案直接写死；`/login`、`/logout` 命令描述放 `src/chrys` 侧用 `msg(fallback=)` | 实测 + `aixcoding/README.md` |
| 6 | chrys 是 editable 安装，`.pth` 只挂 `D:\project\iCode\src` —— 运行时 `import aixcoding` **不可达**，必须在 `[tool.hatch.build.targets.wheel] packages` 加入 `"aixcoding"` 并重新 `uv sync` | `.venv/Lib/site-packages/_editable_impl_chrys.pth` 实查 |
| 7 | ruff / ty / uv build 门禁只扫 `src/`、`tests/`、`scripts/chrys_test.py` —— `aixcoding/` 需**手动**跑 `uv run ruff check aixcoding/` 与 `format --check` | `scripts/chrys_test.py` 与 AGENTS.md 门禁命令 |
| 8 | 排查语法问题永远用 3.14（PEP 758）；`uv run python -VV` 先确认 | 方案第 4 节踩坑记录 |
| 9 | 测试网络护栏只放行 loopback —— mock server 集成测试必须绑 `127.0.0.1` | `tests/architecture/test_network_egress.py` |

## 1. 目标结构

```
aixcoding/
├── __init__.py            # 已存在
├── README.md              # 已存在
├── auth/
│   ├── __init__.py        # 公共 API re-export
│   ├── types.py           # Environment / DeviceCode / TokenResult / AccountInfo / StoredCredential
│   ├── errors.py          # AuthError / AuthNetworkError / DevicePollCancelled / DevicePollTimeout / ProtectUnavailable
│   ├── environments.py    # LOCAL/DEV/PROD 地址表 + CHRYS_AUTH_ENVIRONMENT / CHRYS_AUTH_SERVER_URL 覆盖
│   ├── crypto.py          # ProtectBackend + WindowsDPAPI / MacOSSecurity / Plaintext / MemoryBackend + get_backend()
│   ├── storage.py         # 密文信封 + 明文指针 + 原子写 + sha256 完整性
│   ├── client.py          # AuthClient：三接口 + 轮询状态机（interval+5 上限 30s / 总超时 15min）
│   └── session.py         # 登录态持有者（静默检查 / 登出 / 用户信息），供 src/chrys 接线调用
├── mock/
│   ├── __init__.py
│   ├── __main__.py        # python -m aixcoding.mock.server 的入口转发
│   └── server.py          # （从 scripts/mock_auth_server.py 迁移）loopback mock 登录服务
└── tui/
    ├── __init__.py
    ├── login.py           # LoginDialog（继承 BaseDialog）
    └── login.tcss

tests/app/aixcoding/       # 单测落点（约束 2/3）
src/chrys 接线（仅 3 处）：
├── pyproject.toml                    # packages 加 "aixcoding"（约束 6）
├── app/tui/screens/main/commands.py  # 注册 /login /logout（msg fallback 文案在此侧）
└── app/tui/app.py                    # on_mount 末尾挂静默检查（try/except ImportError 包裹）
```

**与原方案的差异**（因约束 1 收窄）：
- ~~阶段 0 修 platform 语法~~：作废（方案第 4 节，3.14 合法语法）
- ~~settings.py 新增 auth 字段（原阶段 3）~~：**取消**。配置改为只读环境变量 `CHRYS_AUTH_ENVIRONMENT` / `CHRYS_AUTH_SERVER_URL`，解析逻辑在 `aixcoding/auth/environments.py`，不动 `Settings` schema
- ~~`foundation/auth/`~~：整体移到 `aixcoding/auth/`
- ~~状态栏常驻用户展示~~：MVP 用 toast 通知展示登录/登出结果；常驻状态栏需改 chrome widget（超出接线范围），记为后续项
- ~~`scripts/mock_auth_server.py`~~：迁移到 `aixcoding/mock/server.py`

## 2. 阶段表

| 阶段 | 内容 | 状态 | 验证 |
|---|---|---|---|
| A | mock 迁移 `aixcoding/mock/`，删 `scripts/` 版本 | ✅ | 进程内端到端 + ruff |
| B | `auth/types.py` + `errors.py` + `environments.py` + 单测 | ✅ | pytest + ruff |
| C | `auth/crypto.py` 四后端 + 降级 + 单测 | ✅ | pytest（含 Windows DPAPI 实测） |
| D | `auth/storage.py` 信封/指针/原子写/完整性 + 单测 | ✅ | pytest（tmp_path） |
| E | `auth/client.py` 三接口 + 轮询状态机 + 单测/集成 | ✅ | pytest（MockTransport + loopback mock） |
| F | `tui/login.py` + `login.tcss` LoginDialog + 单测 | ⬜ | pytest（Textual run_test） |
| G | 接线：pyproject + commands.py + app.py | ⬜ | uv sync 后 `import aixcoding` + smart test |
| H | docs 双语 + index.yaml + i18n key + 收尾验证 | ⬜ | i18n check + 手动冒烟 |

每个阶段完成的定义：代码落地 → `uv run ruff check aixcoding/ tests/app/aixcoding/` 与 `format --check` 通过 → 目标 pytest 通过 → **回写本文件**。

## 3. 执行日志（每阶段完成后追加）

### 阶段 A ✅ mock 迁移（2026-10-08）

- `scripts/mock_auth_server.py` → `aixcoding/mock/server.py`（内容不变，docstring 启动命令改为 `python -m aixcoding.mock`）
- 新增 `aixcoding/mock/__init__.py`（re-export）与 `__main__.py`（入口转发）
- **docstring 全改英文**：ruff `RUF002` 禁 docstring 全角标点，主包惯例即"英文 docstring + 中文只进用户可见字符串"（`aixcoding/__init__.py`、`mock/__init__.py` 均已改写）
- 验证：`ruff check` / `format --check` 通过；进程内端到端（manual 全流程 + user/info 大熊猫）PASS

### 阶段 B ✅ auth 数据层（2026-10-08）

- `aixcoding/auth/types.py`：`Environment(StrEnum)`（ruff UP042 要求 StrEnum 而非 `str, Enum`）、`DeviceCode` / `TokenResult`（`token` 优先、`access_token` 兜底）/ `AccountInfo`（camelCase→snake_case 映射 + `display_name`）/ `StoredCredential`（`issued_now` TTL 365 天 + `to_payload`/`from_payload` 往返）
- `aixcoding/auth/errors.py`：`AuthError` 基类 + `AuthNetworkError` / `AuthServerError` / `DevicePollDenied`（携带 `access_denied`/`expired_token`）/ `DevicePollTimeout` / `DevicePollCancelled` / `ProtectUnavailable`
- `aixcoding/auth/environments.py`：三档地址常量表 + `CHRYS_AUTH_ENVIRONMENT`（未知值回落 prod）+ `CHRYS_AUTH_SERVER_URL`（只换 protocol+host 保 path；**urlsplit 会放行 "not a url" 这种 netloc**，已加空白字符校验）
- 测试：`tests/app/aixcoding/test_auth_types.py`（10 例）+ `test_auth_environments.py`（12 例），**30 passed**
- 踩坑：① ruff UP042：py314 下 `str, Enum` 要改 `StrEnum`；② `urlsplit` 对畸形 host 不报错，覆盖逻辑需自校验

### 阶段 C ✅ 加密后端（2026-10-08）

- `aixcoding/auth/crypto.py`：`ProtectBackend` Protocol（`degraded` + `protect`/`unprotect`）四实现
  - `WindowsDPAPI`：ctypes 直调 `crypt32.dll`（`CRYPTPROTECT_UI_FORBIDDEN`，label 作 OptionalEntropy，`LocalFree` 释放出参）——风格对齐主包 `_win32_clipboard_api`
  - `MacOSSecurity`：`/usr/bin/security` add/find-generic-password，timeout=2
  - `PlaintextBackend`：直通（Linux 降级，对齐参考 `setUsePlainTextEncryption`）
  - `MemoryBackend`：进程内 dict（不落盘）
  - `get_backend()`：真实探针往返，失败逐级降级到 MemoryBackend（**绝不崩**），debug 日志记录降级原因
- 测试 `test_auth_crypto.py`：DPAPI 真实往返 + 错 label 拒解（Windows 实测通过）、macOS CLI 参数断言（monkeypatch subprocess）、三种降级路径（构造抛错 / 探针数据损坏 / 真实探针）
- **41 passed**；踩坑：ruff S112 要求 `except: continue` 必须留日志；`PlaintextBackend` 初版过度设计（token+vault），简化为直通

### 阶段 D ✅ 凭据存储（2026-10-08）

- `aixcoding/auth/storage.py`：`CredentialStore(config_dir, backend)`
  - 目录：`<config_dir>/users/<env>/current`（指针 `secret:v1:<32hex>`，**不含 token**）+ `private/secrets/<32hex>.json`（信封 `schemaVersion/purpose/ciphertext/ciphertextSha256`）
  - 原子写：临时文件 + `os.replace`；posix 上 0700/0600 + `O_NOFOLLOW`，Windows 跳过
  - 损坏自愈：sha256 不符 / unprotect 失败 / JSON 残缺 / purpose 不符 → `load()` 返回 None 并**清指针**，下次登录干净重来
  - `MemoryBackend` 走纯内存（不建目录、不落盘）
  - `default_config_dir()` 懒导入 `chrys.foundation.platform.get_platform()`，chrys 不可用时回落 `~/.chrys`
- 测试 `test_auth_storage.py`：往返、指针无 token、信封无明文、sha256 一致、篡改自愈、跨环境隔离、clear、内存态不落盘、无 tmp 残留、purpose 伪造拒绝 —— **54 passed**（累计）
- 踩坑：① ruff SIM105 要求 `contextlib.suppress`；② "错 label 拒解"用 Plaintext 派生测不出来（unprotect 是恒等），改用 unprotect 抛 `OSError` 的死后端

### 阶段 E ✅ 协议客户端（2026-10-08）

- `aixcoding/auth/client.py`：`AuthClient(auth_url, data_url, http=None)`
  - `request_device_code()`：`{"client_id": 78}`，读 `result`
  - `poll_token(device_code, ...)`：状态机 —— 服务端 interval 起步、`slow_down` +5s 封顶 30s、`access_denied`/`expired_token` 即刻终止（`DevicePollDenied` 带 error）、15min 总预算（`DevicePollTimeout`）、`cancel_event` 短路（`DevicePollCancelled`）；sleep/clock 可注入（假时钟测试）
  - `fetch_user_info(token)`：读 `data`（**不是** `result`）；`data` 为 null 或无 `success` 键 → `AuthServerError`（调用方据此判定凭据死亡）
  - 信封原则贯穿：**不看 HTTP status，不看 `success`（pending 时也是 true），只看 `result.error` / `result.token` / `data`**
- `aixcoding/auth/__init__.py` re-export `AuthClient` / `CredentialStore` / `get_backend` / `default_config_dir`
- 测试 `test_auth_client.py`：13 个 MockTransport 单测（信封怪癖全覆盖）+ 2 个 **loopback mock 集成测试**（auto 全流程 / manual 确认前 pending + 未知 device_code → expired_token）—— **69 passed**（累计）
- 踩坑：① httpx `json=` 序列化无空格（`{"client_id":78}`），断言别写 `": "`；② ruff B023：循环内定义 handler 要用 `pytest.mark.parametrize` 而非 `captured = error`；③ slow_down 测试第一次睡眠就已 +5（sleep 发生在 bump 之后）
