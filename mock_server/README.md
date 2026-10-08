# Mock Servers

`mock_server/` 是仓库根目录下的 dev-only 包，**按"一个外部服务一个子包"**组织，
每个子包独立模拟一个 iCode 实际依赖的真实后端，让产品代码能本地端到端跑通、
被测试覆盖，而无需打 staging 或生产。

## 当前子包

| 子包 | 模拟目标 | 端点前缀 |
|---|---|---|
| `aixcoding_auth/` | AIxCoding 设备码登录认证服务 | `/api/v1/auth/...`、`/api/v1/user/info` |
| `chrys_model_catalog/` | 服务端下发的模型目录 | `/model-catalog`、`/llm/api/v1/continue-config/dispatch` |

未来新增（命名遵循下面的约定）：`oauth/`、`llm/`、`update_server/` 等。

## 目录结构

```
mock_server/
├── __init__.py             # 包标识 + 分级约定文档
├── README.md               # 本文件：分级约定 + 新增 mock 的步骤
├── aixcoding_auth/         # AIxCoding 登录认证 mock
│   ├── __init__.py
│   ├── server.py           # HTTP server、授权状态机、本地验证页
│   └── README.md           # 具体端点 / 模式 / CLI 用法（测试在 tests/app/aixcoding/）
├── chrys_model_catalog/    # 服务端模型目录 mock
│   ├── __init__.py
│   ├── server.py           # HTTP 装配、路由、start()/CLI
│   ├── source.py           # 数据源：config_new.json（缺省）或 --catalog，每请求读
│   ├── modes.py            # 故障模式与 payload 构造
│   ├── state.py            # 运行时 mode/revision 开关
│   ├── conftest.py         # pytest 夹具（direct_route）
│   ├── test_server.py      # 集成测试 + 契约验证
│   └── README.md           # 端点 / 故障模式 / CLI 用法
└── <future>/               # 未来 mock，每个都按 chrys_model_catalog/ 的结构
```

## 为什么是 dev-only 顶层包

- **明显性**：仓库根目录下一眼可见，跨团队定位成本最低。
- **自包含**：每个子包"源码 + 测试 + 夹具 + 文档"齐全，迁出/独立测试无需拼
  接。
- **不污染产品包**：`src/chrys/` 受 pyproject 打包规则约束，把 dev 工具放进去
  会意外进入产品 wheel；`tests/` 是产品测试集，混 dev 工具会污染测试目录语义。
- **pytest 收集**：`pyproject.toml` 设了 `testpaths = ["tests", "mock_server"]`，
  `mock_server/` 下任何子目录里的 `test_*.py` 都会被自动发现。

## 新增一个 mock 子包的步骤

1. **挑名字**：用"被模拟的服务/能力"作为目录名，加产品前缀消歧义。避免泛名
   `api`/`backend`。
2. **建子包**：
   - `__init__.py`：子包 docstring，列端点与公开 API
   - `server.py`：HTTP server 实现（提供 `create_server(...)` 给测试用，
     `python mock_server/<pkg>/server.py` 可直接 CLI 起服务）
   - `README.md`：端点表、故障模式、CLI 用法
   - 测试放 `tests/` 对应目录或子包内 `test_*.py`，在 README 里写清位置
3. **强约束**：
   - 只绑定 loopback（`127.0.0.1` / `::1`），启动时拒绝其它地址
   - stdlib-only，不 import 产品包；按真实后端的 wire quirks 逐字节复刻
   - 测试走直连，避开系统代理

## 命名约定速查

| 用途 | 命名 |
|---|---|
| 目录（子包） | `<product>_<service>/`，如 `aixcoding_auth/` |
| 主模块 | `server.py`（目录名已带 service 上下文） |
| 测试 | `test_*.py`（位置在子包 README 里注明） |
| 配置/状态类 | `Mock*Config` / `Mock*State`，如 `MockAuthConfig` |
| 入口 | `create_server(...)`（测试）；模块 `main()`（CLI） |
