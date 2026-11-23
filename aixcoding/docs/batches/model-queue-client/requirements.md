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

---

## 追加：排队中主动取消（2026-11-19，责任人裁决）

> 原「非目标」（第 20 行）中"不对接 `POST /api/v3/chat/completions/cancel`"一条**撤销**。
> 责任人澄清"断连即出队"的真实语义：客户端断连后**主动发取消排队通知**（仅当仍在排队中；已放行则无需通知），
> 不是服务端从断连自动感知。契约见 `ModelQueueFrontend.md` §3.6 与 `LlmRequestFlow.md` §5。

### 目标

- 目标 4：流式请求**自传 `request_id`**，使服务端可用它定位排队中的请求。
- 目标 5：用户中断（TUI Interrupt / ACP `session/cancel` / CLI Ctrl+C / 任何导致流关闭的路径）时，
  若该请求**仍在排队**，客户端调用 `POST /api/v3/chat/completions/cancel`（body `{model, request_id}`，
  `token` 头）通知服务端出队，释放并发槽位给队尾。
- 目标 6：**不在排队中则不通知**——已放行（收到首个数据帧）或从未排队（直通）时中断，不发 cancel。

### 非目标

- 非流式请求（网关侧非流式不推排队进度、也无法在客户端侧判定排队态）不接。
- 子代理与 workflow 节点（不注入排队回调，与 v1.0 范围边界一致）不接。
- 取消后的 UI 提示：用户已主动中断，本地按"已中断"收尾，不渲染 `QUEUE_CANCELLED`。
- 不做"取消失败自动重试"：`409/404` 属正常结果，`5xx`/超时只记日志。

### 验收标准

- [ ] 流式请求体带 `request_id`（放入 `extra_body`，不改 OpenAI 命名参数）；每次 wire 请求一个唯一值，
      重试重发即新 id。
- [ ] 排队中中断 → 发出 cancel 请求，`model` 与 `request_id` 与主请求一致，`token` 头为 profile 的 `api_key`。
- [ ] 已收到首个数据帧后中断 → **不**发 cancel。
- [ ] 未排队（直通、从未收到 `queue_status`）时中断 → **不**发 cancel。
- [ ] cancel 返回 `204` / `409` / `404` 时静默通过；`500` / 网络错误 / 超时（2s）只记 warning，
      **不**阻塞、不改变中断行为、不影响后续请求。
- [ ] 定制包导入失败时回退 v1.0 行为（无 `request_id`、无 cancel），流式照常。
- [ ] 非流式路径行为完全不变。

### 已知限制（2026-11-20 评审 C3 登记）

- profile 显式配置 `request_id` 时复用该值；同一 profile 的并发请求会共享同一个 id，
  cancel 与 position 心跳的归属可能交叉。该字段仅用于**单飞行测试**，不作为并发特性；
  detail 日志会提示复用。
