# Mock 专区（aixcoding/mock/）

`aixcoding/mock/` 是纯开发资产（不进 wheel，DIRECTORY.md §6），**按"一个外部服务一个子包"**
组织，每个子包独立模拟一个 AIxCoding 实际依赖的内部后端，让产品代码本地端到端跑通、
被契约测试覆盖，无需打真实环境。

## 注册表与端口

> **2026-11-20 单端口决策**（`docs/batches/mock/design.md` 决策记录，随 telemetry-after-turn-slice 批次1 落地）：launcher 默认起**单端口组合** `:15678`——一个 server 挂载全部子服务路由；旧多端口组合退役。15678 位于 15001-49151 安全区（本机实测 Windows 动态端口范围 1024-15000，7777/7778 均在内且 7778 曾被占；同时避开标准临时区 49152+）。产品端 local 默认随批次1 R2 统一指向 15678。

| 子包 | 模拟目标 | 组合端口 | 独立形态默认端口（调试/契约测试） |
|---|---|---|---|
| `auth/` | 设备码登录认证服务 | 15678（catalog 内嵌路由） | 7777（`--only auth` / 直跑） |
| `model_catalog/` | 服务端下发模型目录（**默认内嵌 auth 路由** + LLM chat `/v1`） | 15678 | 7777 |
| `update/` | 版本更新检测（`/api/v2/releases/check`） | 15678（`/api/v2/` 前缀） | 7778 |
| `telemetry/` | 遥测接收后端（mock 1B：三 save 端点 + `_test/join` + 原模型 attempt 捕获） | 15678（`/csas/telemetry/` 前缀） | 15678 |

**合用端口说明**：组合形态是默认（单 server + 单端口覆盖登录、目录、LLM chat、更新检测）；auth 独立形态保留（纯登录调试/契约测试，与 model_catalog 因共享 auth 路由空间互斥）。`--no-auth` 拆用形态经 catalog 独立 CLI 保留。

**LOCAL 默认不自动同步模型目录**（`[model_catalog] auto_sync`，批次 catalog-auto-sync）：
LOCAL 档模型文件默认由开发者自管（手放 yaml 指向真实端点）；要演练目录同步链路，在
`aixcoding.toml` 显式设 `auto_sync = true`。操作细节见 `model_catalog/README.md`。

## 组合启动器（一键联调）

```bash
uv run python -m aixcoding.mock            # 默认：单端口组合 :15678（model_catalog 含 auth + update）
uv run python -m aixcoding.mock --list     # 列出子服务、端口与路由前缀
uv run python -m aixcoding.mock --only auth           # 纯登录场景（独立 auth，:7777）
uv run python -m aixcoding.mock --only model_catalog  # 只要目录+登录（组合，:15678）
uv run python -m aixcoding.mock --port 16000          # 组合端口覆盖（逃生门）
```

单服务调试（双形态）：

```bash
uv run python aixcoding/mock/auth/server.py            # 直跑（依赖 server.py 内 sys.path hack）
uv run python -m aixcoding.mock.auth.server            # 模块形态（注意：-m 须落到 server.py）
```

### 端口占用处理（fail-fast，不静默换端口）

固定端口是联调可预期的前提；静默换端口会让产品流量打不到 mock。被占时启动器/CLI 明确
报错（服务名 + 端口），人工处理：

```console
netstat -ano | findstr :15678       # 查占用 PID（Windows）
tasklist /fi "PID eq <pid>"         # 看进程名，杀掉残留 mock 后重试
```

逃生门（人工作出端口时）：组合使用 mock 侧 `--port` + 产品端相应 base 配置覆盖（auth
`AIXCODING_AUTH_SERVER_URL`、目录 `aixcoding.toml` 的 `[model_catalog].base_url`、update/
telemetry 随批次1 R2 的 local 默认）；独立形态 CLI 各自 `--port`。

## 目录结构

```
aixcoding/mock/
├── __init__.py             # 命名空间锚点（本包说明）
├── __main__.py             # 组合启动器（python -m aixcoding.mock）
├── README.md               # 本文件：注册表 + 约定 + 新增 mock 步骤
├── auth/
│   ├── __init__.py
│   ├── server.py           # HTTP server、授权状态机、本地验证页
│   └── README.md           # 端点 / 模式 / CLI 用法
├── update/
│   ├── __init__.py
│   ├── server.py           # HTTP server、严格校验、四种模式、debug 端点
│   └── README.md
└── model_catalog/
    ├── __init__.py
    ├── server.py           # HTTP 装配、路由（含内嵌 auth）、CLI
    ├── source.py           # 数据源：config_new.json（缺省）或 --catalog，每请求读
    ├── modes.py            # 故障模式与 payload 构造
    ├── state.py            # 运行时 mode/revision 开关
    ├── config_new.json     # 参考服务端的目录数据
    └── README.md
```

契约测试统一在 `aixcoding/tests/mock/`（`test_<name>_server.py` + `conftest.py` 的
`direct_route` 夹具），显式运行：`uv run pytest aixcoding/tests`。

## 强约束（DIRECTORY.md §6）

- 只绑定 loopback（`127.0.0.1` / `::1`），启动时拒绝其它地址；
- stdlib-only，不 import 产品包（mock 保持黑盒；契约测试可以 import 产品解析器做
  消费者侧验证）；
- 按真实后端的 wire quirks 逐字节复刻；
- 测试直连避开系统代理；
- **每个 mock 必须有契约测试**，无契约测试的 mock 不得合入。

## 新增一个 mock 子包的步骤

1. **挑名字**：无前缀服务名（如 `telemetry`）；目录名描述职责域，不预设实现形态
   （形态由子包内文件表达，当前均为 HTTP server 即 `server.py`；进程内替身不进本专区
   ——测试 fake 归 `aixcoding/tests/`，产品内挂钩归 `src/chrys/{tier}/aixcoding/`（按落位规则，ADR-0011））；
2. **建子包**：
   - `__init__.py`：docstring 列端点与公开 API；
   - `server.py`：`create_server(...)` factory（测试进程内驱动）+ `main()` CLI（独立
     进程）；直跑形态需要时加 `sys.path` hack（参照 `model_catalog/server.py`，注意
     `parents[3]` 索引依赖目录深度）；
   - `README.md`：端点表、故障模式、CLI 用法；
3. **契约测试**：`aixcoding/tests/mock/test_<name>_server.py`，`create_server(port=0)`
   进程内起停、直连避代理；锚定 wire 复刻（信封、状态码语义、故障模式逐条对应）；
4. **登记**：本 README 注册表加行 + launcher `_REGISTRY` 表加条目并在 `combined.py`
   组合层挂载路由（`aixcoding/mock/__main__.py`）；如与既有服务共享路由空间需在
   `_resolve_selection` 加互斥检查；
5. **过门禁**：`pytest aixcoding/tests` 绿 + ruff check/format `aixcoding/` +
   `python aixcoding/tools/check_import_boundaries.py`。

## 命名约定速查

| 用途 | 命名 |
|---|---|
| 目录（子包） | 无前缀服务名：`auth` / `update` / `model_catalog` / `telemetry` |
| 主模块 | `server.py`（目录名已带 service 上下文） |
| 契约测试 | `aixcoding/tests/mock/test_<name>_server.py` |
| 配置/状态类 | `Mock*Config` / `Mock*State`，如 `MockAuthConfig` |
| 入口 | `create_server(...)`（测试）；`main()`（CLI）；组合启动 `python -m aixcoding.mock` |
