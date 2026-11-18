# 需求：客户端对接模型并发排队（model-queue-client）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

内网 LLM 网关（Java 服务，`/api/v3/chat/completions` 等）上线「按模型全局并发上限 + FIFO 排队」（服务端能力 `model-concurrency-queue`）。对接文档见会话附带的 `ModelQueueFrontend.md` / `LlmRequestFlow.md`。

iCode 作为客户端，现状与网关契约冲突两处（均已实测确认）：

1. **排队期间整个流式请求失败**。网关在排队时下发 SSE 具名事件 `event:queue_status`，`openai==2.54.0` 把未知具名事件按普通 `data:` 解析成 chunk（`choices=None`，`position/queueSize` 落入 `model_extra`），而 `chat_completions/stream.py` 的 `raise_invalid_stream_event` 判 `choices` 非数组即失败 → 用户看到 invalid response，而不是"在排队"。
2. **排队超时被当成可重试错误**。`event:queue_rejected` 在 SDK 层表现为裸 `openai.APIError`（`status_code=None`，`body={'code','message','traceId'}`），`foundation/errors/_legacy.py` 把裸 `APIError` 列入 `RETRYABLE_TYPE_NAMES` → `QUEUE_TIMEOUT` 会被 wire 层自动重试 10~18 次，每次重新排队，正是网关文档警告的雪崩放大。

## 目标与非目标

- 目标 1：网关下发 `queue_status` 时，流式请求**不失败**，正常等待放行后继续收流。
- 目标 2：`queue_rejected` 按 `error.code` 分流——`QUEUE_FULL` 保持现有可退避重试语义；`QUEUE_TIMEOUT` / `QUEUE_CANCELLED` 为终态，不做自动重试。
- 目标 3（第二批，本设计不含实现）：排队期间在 TUI/CLI 上给出"排队中，前方 N 个请求"的可见提示。

- 非目标：不实现服务端排队逻辑（网关职责）；不对接 `POST /api/v3/chat/completions/cancel`（客户端中断即断连、断连即出队，见网关文档 FAQ Q3）；不新增 `maxConcurrency/maxQueueSize/maxWaitTime` 等客户端配置字段（均为服务端配置）；不改 `QUEUE_FULL` 的重试阶梯（现有 3/7/15…更保守，文档建议值非硬要求）。

## 用户场景

1. 模型并发已满：用户发起提问，请求进入网关队列；iCode 保持连接、不报错、不重排队，放行后正常输出。
2. 排队超时：网关下发 `QUEUE_TIMEOUT`；iCode 立即结束该次请求并给出一句可读失败原因，不再自动重试。
3. 队列已满：网关下发 `QUEUE_FULL`；iCode 沿用现有 transient 重试阶梯退避后重试。

## 验收标准

- [ ] 含 `event:queue_status` 帧的 SSE 流，客户端仍产出完整回复，不抛 invalid response。
- [ ] `queue_status` 帧不产生任何 `ChatResponseUpdate`，不污染回复内容与 usage。
- [ ] guard 捕获 `openai.APIError(body={'code':'QUEUE_TIMEOUT'})` 后转译出的 `ProviderResponseError(retryable=False)`（根因 `APIError` 在 `__cause__` 上），经生产入口 `chrys.foundation.errors.is_retryable`（classify 版）判定为 `False`。
- [ ] `QUEUE_CANCELLED` 同上，转译后判定为 `False`。
- [ ] `openai.APIError(body={'code':'QUEUE_FULL'})` **不经转译**、原样上抛，经同一入口保持 `True`。
- [ ] 排队期间持续收到 `queue_status` 心跳（间隔小于 stall 超时、总时长大于超时）时，不触发 `StreamStall`。
- [ ] 非 QUEUE 错误（`UPSTREAM_TIMEOUT`、普通 429、连接错误）分类与重试行为不变。
- [ ] 定制模块导入失败时，上游流式行为回退到改造前（不因定制缺失而阻断）。

## 开放问题

- 第二批 UI 的呈现形态（转写区一行状态 vs 状态栏）与事件载体，待第二批设计确定。
