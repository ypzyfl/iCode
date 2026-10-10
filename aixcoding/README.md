# aixcoding

AIxCoding 二开定制专区。此目录为**不进 wheel 发布包**的定制内容（wheel 仅打包 `src/chrys`，另有 `docs/` 用户指南经 force-include 随包分发，与本目录无关）。

- `docs/`：内部设计文档，纯中文、无双语义务，按功能分子目录（如 `telemetry/` 数据上报）
- `telemetry-mock/`：数据上报 mock server（Python 标准库零依赖，仅供开发调试；M1 时创建）

进包的定制源码在 `src/chrys/aixcoding/`，定制测试在 `tests/aixcoding/`。

# iCode TUI 登录改造 —— 增量代码目录

本目录承载本次登录改造的**全部新增代码**，与 `src/chrys` 主包物理隔离，便于增量管理与代码评审。

分支：`lhc/aixcoding_login`（从 `main` 切出）

## 目录约定

```
aixcoding/
├── auth/    协议客户端、凭据存储、OS 级加密后端
└── tui/     Textual 登录对话框
```

本地 mock 登录服务器位于 `mock_server/aixcoding_auth/server.py`
（2026-10-08 自 `scripts/mock_auth_server.py` 迁出并并入 `mock_server/` dev-mock 注册表，不放在 aixcoding 内）。

**对 `src/chrys` 的改动仅限于"接线"**，不含业务逻辑：

| 文件 | 改动性质 |
|---|---|
| `src/chrys/app/tui/screens/main/commands.py` | 注册 `/login`、`/logout` 斜杠命令（几行） |
| `src/chrys/app/tui/app.py` | `on_mount` 末尾挂静默检查任务（几行） |

业务逻辑一律放本目录，`src/chrys` 只做最小侵入调用。

## 与架构测试的边界

已核实：`tests/architecture/test_layering.py` 的分层 DAG 扫描范围是 `SRC_ROOT / "chrys"`（即 `src/chrys`），本目录不在扫描范围内，因此：

- ✅ 不受 foundation < kernel < service < orchestration < app 的反向导入约束
- ✅ 不会触发 `unregistered first-party top-level package` 检查
- ⚠️ 但 `scripts/i18n.py` 的 `SOUCE_ROOT` 同样是 `src/chrys`，本目录内的 `msg()` **不会被提取到 i18n catalog** —— 所以 TUI 文案应保持极小，或由 `src/chrys` 侧的调用方持有文案

## 参考实现

| 项目 | 借鉴内容 |
|---|---|
| `D:\project\ChinaBank\aixcoding-continue` | 设备码协议三接口、`client_id: 78`、`mockServer/server.js` 的假数据 |
| `D:\project\agent_studio_new` | 凭据存储（OS 级加密 + 明文指针引用 + 降级内存态） |

改造方案全文见 `codingExplan/TUI登录改造方案.md`。