# 测试计划：排队进度提示（model-queue-progress）

> 活文档（AI 维护，不签认）。实现前起草，实现中按需增补。

## 测试策略

- 事件与回调链：单元测试直接驱动 `guard_queue_frames(chunks, on_status=...)`，断言回调收到 `QueueStatus` 序列、且被吸收的帧不出现在 chunk 流里；回调抛异常时 LLM 流**不中断**（记录后继续）。
- 文案：`src/chrys/kernel/aixcoding/queue_progress/` 的 pure 函数按 position 分支断言（0 / 1-3 / >3），中文断言按既有先例豁免 RUF001。
- TUI：用 `WaitingRow` 单元测试断言设置文案后 `render()` 输出含该文本、`get_content_height` 仍为 1（无 fold gap 时）；完整 pilot 流程留给联调。
- CLI：`TurnProgress.handle` 新 case 驱动去重——连续两帧相同 position 断言只输出一次，position 变化再输出一次；同时断言 `InvocationActivity.handle` 未被调用（锚点防静默）。
- ACP：断言 `ext_notification` 被调用且 method 为 `queue_status`（v1.5 方法名；线上一致 `_queue_status`）、payload 为 `status` 三态形态（v1.7）；白名单注册由既有的通知守卫测试覆盖。

## 覆盖矩阵

| 验收标准 | 测试用例 | 层次 |
|---|---|---|
| TUI 显示 position 与 0 文案 | `queue_note(0)` / `queue_note(1..9)` 分支断言（「约 N 人」+ 操作建议；`queueSize` 不进文案） | 单元 |
| WaitingRow 文案与高度 | 设置文案后 `render()` 含文本、`get_content_height` == 1 | 单元 |
| 无排队行为不变 | 不调用 setter 时 `render()` 与改造前等价（只有 dot） | 单元 |
| CLI 去重 | 同 position 两帧只输出一次；变化时再输出 | 单元 |
| ACP 通知 | `queue_status` 方法与 `status` 三态字段（v1.5/v1.7） | 单元 |
| 回调异常不中断流 | `on_status` 抛 RuntimeError → 仍产出完整回复 | 端到端（真 SDK + MockTransport） |
| 未接线不影响 | `on_queue_status=None` 时流行为与 `model-queue-client` 批次一致 | 端到端 |
| headless 白名单生效（防静默） | 事件在 `_HEADLESS_RUN_EVENT_TYPES` 内时 CLI/ACP stream 收到；把该条目移除（破坏实验）则收不到，以此锚定登记点 `headless-event-type` | 单元 |
| CLI 锚点正确（防静默） | 事件经 `TurnProgress.handle` 输出一行；断言 `InvocationActivity.handle` 未被调用（它收 `InvocationEvent`） | 单元 |
| WaitingRow 跨轮不残留 | 上一轮设置文案 → 轮次开始清空 → `render()` 不含旧文案 | 单元 |
| ACP 心跳去重 | 连续两帧相同 (requestId, position) 只发一次 `queue_status` | 单元 |
| requestId 透传（v1.4） | tracker 转发的排队与放行状态都带 `request_id`；无 tracker 时为 `None`；发布工厂带到事件；端到端（生产 profile HTTP 客户端 + MockTransport）收到的 id 等于网关侧 `Chrys-Request-Attempt-Id` | 单元 + 端到端 |
| ACP 载荷形态（v1.4 起，v1.7 口径） | 排队 `{sessionId, requestId?, status: 排队中, position, queueSize}`、放行 `{sessionId, requestId?, status: 放行}`、拒绝 `{sessionId, requestId?, status: 拒绝, reason, message?, traceId?}`、未知 id 时无 `requestId` 键 | 单元 |
| D2 去重键（v1.4） | 同 session 同 position、不同 requestId 各发一次（重试新请求不被吞） | 单元 |
| 子代理/workflow 不展示（边界） | 子代理构建路径不注入回调 → 无事件发出；与改造前一致 | 单元 |
| 重试后再排队可见（v1.8） | 尾条为 RetryMessage 时 `set_queue_note` → 等待行显示；清空（放行/超时帧）→ 隐藏并清计时器，恢复"状态卡自己说明"的原约定 | TUI（ChatPanelApp） |
| 取消按钮显隐（v1.8） | 文案出现 → 按钮显示；清空 → 隐藏；无文案的裸 dot 无按钮 | TUI（ChatPanelApp） |
| 取消按钮点击接线（v1.8） | 点击 → 消息冒泡出 ChatPanel；MainScreen `@on` 真实派发 → toast「用户已取消排队」+ `action_interrupt` | TUI（make_chrys_app） |

## 异常与降级路径

- 事件构造失败（session_id 缺失）：publish 前校验，缺失则跳过并记 debug，不影响流。
- 订阅方异常：`bus.publish` 已记录并吞掉；guard 再兜一层，双保险。
- 未注册 ACP 通知：白名单缺失时上游会拒绝发送，由守卫测试兜底提醒。

## 上游接触面回归

- `model-queue-client` 的 8 条测试必须继续全绿（guard 签名新增可选参数，默认 None 保持旧行为）。
- `tests/service/llm/test_wire_client.py`、`tests/app/tui` 相关订阅测试全绿。
