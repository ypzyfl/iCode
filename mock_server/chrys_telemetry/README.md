# Chrys Session Reporting Mock Server

`mock_server/chrys_telemetry/` —— Chrys 会话数据上报后端的本地模拟。**不随产品
分发**，仅用于开发、回归、验证 `chrys.foundation.reporting.collector` 的发送链路。

## 用法

CLI：

```bash
uv run python mock_server/chrys_telemetry/server.py --port 4321
uv run python mock_server/chrys_telemetry/server.py --port 4321 --db /tmp/chrys.db
uv run python mock_server/chrys_telemetry/server.py --port 4321 --require-token secret
```

作为 Python 模块（测试 / 集成代码复用）：

```python
from mock_server.chrys_telemetry import server

running = server.start(port=0, quiet=True)
# ... use running.origin, running.store.query(...) ...
running.close()
```

跑测试：

```bash
uv run pytest mock_server/chrys_telemetry/ -n 8   # 只跑这个 mock
uv run pytest                                       # 产品测试 + 全部 mock 一并跑
```

## 端点

上报（5 个）：

| Method | Path | 用途 |
|---|---|---|
| POST | `/csas/telemetry/api/v1/tool-detail/save` | 工具调用（start 投影） |
| POST | `/csas/telemetry/api/v1/tool-detail/batch-save` | 用户输入触发（turn 开始） |
| POST | `/csas/telemetry/api/v1/tool-detail/update` | 工具执行结果（start→result 配对） |
| POST | `/csas/telemetry/api/v1/ai-code/save` | AI 生成代码（独立响应包络） |
| POST | `/csas/telemetry/api/v1/event-reaction/save` | 预留（桌面 GUI 事件） |

调试（6 个）：

| Method | Path | 用途 |
|---|---|---|
| GET  | `/health` | 健康检查 |
| GET  | `/` 或 `/debug/view` | 零依赖观察页（分表、关键列、展开、过滤、自动刷新） |
| GET  | `/debug/reports?interface=...&sessionId=...&limit=...` | 定向查询 |
| GET  | `/debug/dump` | 全部落库导出 |
| POST | `/debug/clear` | 清空全部表 |
| POST | `/debug/faults` | 故障注入（见下） |

## 故障注入模式

`POST /debug/faults` 的 `mode`：

- `none` —— 关闭故障（默认）
- `http500` / `http503` —— 模拟服务端错误（落库后返回，对齐真实后端"尽力持久化"语义）
- `slow` —— 延迟 `slowMs` 毫秒后响应
- `envelope_reject` —— HTTP 200 但 `success=false` / `code=500`，验证 collector
  对**业务拒绝**的识别（重试不该触发）
- `drop_body` —— 直接断连（TCP RST 或 FIN），模拟断网

可选 `rate`（0-1 概率）、`slowMs`（0-60000）、`interfaces`（限定生效端点列表）。
伪随机以毫秒为种子，**同毫秒同判定**，便于测试断言。

## 契约单一事实源

校验与发送端共用 `chrys.foundation.reporting.schemas`：

- 修改 schema：改 `src/chrys/foundation/reporting/schemas.py` 一处即可，发送端
  与 mock 自动同步。
- 修改 mock 的行为（不涉及契约）：仅改 `mock_server/chrys_telemetry/server.py`。
- 测试同时校验两侧：`tests/foundation/reporting/test_schemas.py`（schema）+
  `mock_server/chrys_telemetry/test_server.py`（mock）+
  `tests/foundation/reporting/test_collector.py`（collector 端到端）。

## 安全

- 仅 loopback 绑定（`127.0.0.1` / `::1`）；启动时即拒绝其它地址。
- 请求体上限 8MB（`413`）。
- 可选 `token` 头校验（`--require-token`，`401`）。
- 落库只含上报原文与诊断元数据，不含任何凭证。
