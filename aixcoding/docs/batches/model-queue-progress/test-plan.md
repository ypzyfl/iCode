# 测试计划：排队进度提示（model-queue-progress）

> 活文档（AI 维护，不签认）。实现前起草，实现中按需增补。

## 测试策略

- 事件与回调链：单元测试直接驱动 `guard_queue_frames(chunks, on_status=...)`，断言回调收到 `QueueStatus` 序列、且被吸收的帧不出现在 chunk 流里；回调抛异常时 LLM 流**不中断**（记录后继续）。
- 文案：`src/chrys/kernel/aixcoding/queue_progress/` 的 pure 函数按 position 分支断言（0 / 1-3 / >3），中文断言按既有先例豁免 RUF001。
- TUI：用 `WaitingRow` 单元测试断言设置文案后 `render()` 输出含该文本、`get_content_height` 仍为 1（无 fold gap 时）；完整 pilot 流程留给联调。
- CLI：`TurnProgress.handle` 新 case 驱动去重——连续两帧相同 position 断言只输出一次，position 变化再输出一次；同时断言 `InvocationActivity.handle` 未被调用（锚点防静默）。
- ACP：断言 `ext_notification` 被调用且 method 为 `chrys/queue_status`、payload 含 position/queueSize/sessionId；白名单注册由既有的通知守卫测试覆盖。

## 覆盖矩阵

| 验收标准 | 测试用例 | 层次 |
|---|---|---|
| TUI 显示 position 与 0 文案 | `queue_note(0)` / `queue_note(3)` / `queue_note(9)` 分支断言 | 单元 |
| WaitingRow 文案与高度 | 设置文案后 `render()` 含文本、`get_content_height` == 1 | 单元 |
| 无排队行为不变 | 不调用 setter 时 `render()` 与改造前等价（只有 dot） | 单元 |
| CLI 去重 | 同 position 两帧只输出一次；变化时再输出 | 单元 |
| ACP 通知 | `chrys/queue_status` 方法与字段 | 单元 |
| 回调异常不中断流 | `on_status` 抛 RuntimeError → 仍产出完整回复 | 端到端（真 SDK + MockTransport） |
| 未接线不影响 | `on_queue_status=None` 时流行为与 `model-queue-client` 批次一致 | 端到端 |
| headless 白名单生效（防静默） | 事件在 `_HEADLESS_RUN_EVENT_TYPES` 内时 CLI/ACP stream 收到；把该条目移除（破坏实验）则收不到，以此锚定登记点 `headless-event-type` | 单元 |
| CLI 锚点正确（防静默） | 事件经 `TurnProgress.handle` 输出一行；断言 `InvocationActivity.handle` 未被调用（它收 `InvocationEvent`） | 单元 |
| WaitingRow 跨轮不残留 | 上一轮设置文案 → 轮次开始清空 → `render()` 不含旧文案 | 单元 |
| ACP 心跳去重 | 连续两帧相同 position 只发一次 `chrys/queue_status` | 单元 |
| 子代理/workflow 不展示（边界） | 子代理构建路径不注入回调 → 无事件发出；与改造前一致 | 单元 |

## 异常与降级路径

- 事件构造失败（session_id 缺失）：publish 前校验，缺失则跳过并记 debug，不影响流。
- 订阅方异常：`bus.publish` 已记录并吞掉；guard 再兜一层，双保险。
- 未注册 ACP 通知：白名单缺失时上游会拒绝发送，由守卫测试兜底提醒。

## 上游接触面回归

- `model-queue-client` 的 8 条测试必须继续全绿（guard 签名新增可选参数，默认 None 保持旧行为）。
- `tests/service/llm/test_wire_client.py`、`tests/app/tui` 相关订阅测试全绿。
