# 模型并发排队 · 需求文档

> 适用：AIxCoding / iCode 内网版本（`feat/model-concurrency-queue` 分支）
> 读者：需求、开发、测试、内网联调
> 日期：2026-11-20
> 关联实现：`model-queue-client`（客户端契约对接 + 取消排队）、`model-queue-progress`（TUI/CLI/ACP 进度提示）

---

## 1. 背景与问题

内网 LLM 网关（Java 服务，`/api/v3/chat/completions` 等）上线了「按模型全局并发上限 + FIFO 排队」（服务端能力 `model-concurrency-queue`）。

客户端原有行为与网关契约冲突，已实测确认：

1. **排队期间整个流式请求失败**。网关排队时下发 SSE 具名事件 `event:queue_status`，OpenAI SDK 会把它解析成 `choices=None` 的普通 chunk，而客户端的 `raise_invalid_stream_event` 判 `choices` 非数组即失败 → 用户看到 invalid response，而不是「在排队」。
2. **排队超时被当成可重试错误**。`event:queue_rejected` 在 SDK 层表现为裸 `openai.APIError`，客户端把裸 `APIError` 列入可重试类型 → `QUEUE_TIMEOUT` 会触发 10~18 次自动重试，每次重新排队，放大网关负载。
3. **长排队没有反馈**。用户不知道请求是在排队、排第几、是否已放行。
4. **中断后仍占队列**。客户端断开连接并不会让网关自动出队；需要客户端在排队中主动调用 cancel 接口。

---

## 2. 目标

| 编号 | 目标 |
|---|---|
| G1 | 网关下发 `queue_status` 时，流式请求不失败，正常等待放行后继续收流 |
| G2 | `queue_status` 帧不产生任何 `ChatResponseUpdate`，不污染正文与 usage |
| G3 | 排队心跳可续活客户端 stall 看门狗，长排队不因读空闲被误判断流 |
| G4 | `QUEUE_TIMEOUT` / `QUEUE_CANCELLED` 为终态，不做自动重试；`QUEUE_FULL` 保持既有退避重试 |
| G5 | 排队期间 TUI / CLI / ACP 三种形态都能看到可见提示（ACP 由客户端渲染） |
| G6 | 每个请求携带上游 `Chrys-Request-Attempt-Id` 请求头（网关以它为队列元素 ID）；排队中中断时客户端调用 cancel 接口出队 |
| G7 | 内网联调可通过日志判定「网关发了什么、客户端解析成什么、取消发了什么、网关回了什么」 |

---

## 3. 非目标

- 不实现服务端排队逻辑（网关职责）。
- 不新增 `maxConcurrency` / `maxQueueSize` / `maxWaitTime` 等客户端配置（均为服务端配置）。
- 不改变 `QUEUE_FULL` 的既有重试阶梯（3/7/15/30… 秒，比网关建议值更保守）。
- **非流式请求不武装取消**：网关侧非流式不推排队进度，客户端不判定排队态、不调用 cancel；请求头由上游无条件携带，客户端不写请求体字段；网关只用 HTTP `429/408/409` 表达排队结果。
- **子代理与 workflow 节点不注入 UI 回调**：它们走同一模型时也会排队，但只在 detail 日志留痕，不在 TUI/CLI/ACP 显示排队提示（与改造前行为一致）。
- 不在客户端日志中记录模型回答正文、`token` 值或完整请求头。

---

## 4. 用户场景

| 场景 | 网关行为 | 客户端应表现 |
|---|---|---|
| 并发未满 | 直接转发，无新增事件 | 无排队提示，正常回答 |
| 并发已满、队列未满 | 推 `event:queue_status`（入队位置 + 约 20s 心跳） | 显示「当前模型请求量大，请求排队约 N 人」；名次前进时更新；放行后提示消失并开始出字 |
| 排到队首（`position=0`） | 推 `position:0` | 显示「已排到队首，当前为队列第一位」；**此时仍可能排队超时** |
| 队列已满（`QUEUE_FULL`） | `event:queue_rejected`（流式）或 HTTP 429（非流式） | 流式按既有 transient 策略退避重试；非流式报错 |
| 排队超时（`QUEUE_TIMEOUT`） | `event:queue_rejected`（流式）或 HTTP 408（非流式） | 立即结束并透出网关 message，**不自动重试** |
| 排队中用户中断 | 客户端调用 cancel 成功（204） | 立即按「已中断」收尾；网关出队，原流收到 `QUEUE_CANCELLED` 收尾 |
| 已放行后中断 | cancel 返回 409 或客户端不发 | 按普通中断处理，不报错 |
| 定制模块不可用 | — | 回退改造前行为；WARNING 日志可见 |

---

## 5. 功能需求

### FR-1 排队帧吸收

- 识别条件：`choices is None`、无 `id`/`usage`、`model_extra` 同时含整型 `position` 与 `queueSize`。
- 命中后吸收，不产出 `ChatResponseUpdate`；不污染正文、usage、finish reason。
- 不满足条件的 `choices=None` 帧保持原行为（invalid response，fail-loud）。
- 若真实网关在帧中多带 `id`/`usage` 或把 `choices` 写成 `[]`，客户端必须输出**契约漂移 WARNING**，并在 detail 日志记录帧形状（不记录正文）。

### FR-2 心跳续活

- 每吸收一个 `queue_status` 帧，调用一次 `report_wire_progress()`，重置 stall 看门狗的空闲计时。
- 网关心跳约 20s；客户端 `http_read_timeout` 默认 300s，必须大于心跳间隔。
- 若 `http_read_timeout` 被调到小于心跳间隔，长排队会触发 `StreamStall`（配置错误，不是功能缺陷）。

### FR-3 终态拒绝与满队

- `QUEUE_TIMEOUT` / `QUEUE_CANCELLED`：转译为 `ProviderResponseError(retryable=False)`，根因 `APIError` 保留在 `__cause__`。
- `QUEUE_FULL`：原样上抛，保持可重试。
- 非 QUEUE 错误（`UPSTREAM_TIMEOUT`、429、连接错误）分类与重试行为不变。

### FR-4 队列元素 ID（`Chrys-Request-Attempt-Id` 请求头）

- 客户端不写请求体字段：队列元素 ID 用上游每个 HTTP 尝试都会发的 `Chrys-Request-Attempt-Id` 请求头（32 位小写 hex）。
- 网关取值顺序：请求头优先 → 请求体 `request_id` / `requestId` 兜底 → 随机生成（无头的 curl 演练走兜底）。
- 每个 HTTP 尝试一个新值（SDK 重试、重定向各算一次）；网关以**最终尝试**的头值为准。
- 非流式同样带该头（上游无条件附加），但客户端不武装取消。
- profile 不能指定该值（`chrys-` 是保留前缀）；v1.2 的"profile 固定 `request_id`"能力取消。
- cancel 请求体 `{model, request_id}` 中的 `request_id` 填该次尝试的头值。

### FR-5 排队中取消

- 仅当「见过 `position` 帧且尚未放行」时，流关闭（TUI Interrupt / ACP `session/cancel` / CLI Ctrl+C / 异常断开）才调用：

```http
POST <gateway-root>/api/v3/chat/completions/cancel
Content-Type: application/json
token: <凭据>

{"model": "<model_id>", "request_id": "<本次请求 id>"}
```

- 地址由模型 profile 的 `base_url` 推导：去掉尾部 `/api/v3`、`/api/v2`、`/api/v1`、`/v1`，再拼 `/api/v3/chat/completions/cancel`。
- 超时 2 秒；`204` 成功；`404` / `409` 为契约内正常结果；`5xx` / 网络错误只记日志，不阻塞中断、不改变中断结果。
- 已放行（收到首个数据帧）或从未排队时**不发** cancel。
- 取消是幂等的；重复取消返回 `404`。
- TUI 等待行「取消排队」按钮（2026-11-26 v1.8）：排队文案同行右侧显示，点击后 toast「用户已取消排队」
  并走 Interrupt 同一链路——turn 以「已中断」收尾，cancel 由流关闭路径发出（不新增旁路通道）。

### FR-6 进度提示

| 形态 | 呈现 |
|---|---|
| TUI | 转写区等待行（呼吸点同行）显示文案；名次变化更新；首个回答字到达即消失；新一轮开始清空；排队超时重试后再次排队时，重试/错误卡为尾条期间仍显示文案（2026-11-26 v1.8）；文案同行右侧带「取消排队」按钮（2026-11-26 v1.8，见 FR-5） |
| CLI | stderr 追加一行；同一 `position` 只输出一次；`position=0` 为「已排到队首，当前为队列第一位」 |
| ACP | `queue_status` 扩展通知（线上名 `_queue_status`）：三帧、单字段三态 `status`（v1.7：中文值「排队中」/「放行」/「拒绝」）——排队 `{sessionId, requestId, status:"排队中", position, queueSize}`；放行 `{sessionId, requestId, status:"放行"}`；拒绝 `{sessionId, requestId, status:"拒绝", reason, message?, traceId?}`；同 (requestId, position) 不重发，拒绝不去重 |

> `queueSize` 当前不进入 TUI/CLI 文案，但事件与 ACP 载荷仍携带，供客户端自行展示。

### FR-7 回退

- 定制模块导入失败时，上游流式行为回退到改造前（无帧过滤、无 cancel），并输出 WARNING；`Chrys-Request-Attempt-Id` 请求头仍由上游发送，只是不武装取消。
- 回退不得阻断正常请求。

### FR-8 日志与取证

- 关键事件必须可从日志判定：排队帧到达/心跳/放行、拒绝转译、cancel 请求参数与地址、cancel 响应状态与 body、cancel 跳过原因。
- 详细日志写 `aixcoding.detail.llm_queue`（文件专用，CLI/TUI/ACP 都有），路径见《内网验证步骤与说明》。
- 原始 SSE 字节不在客户端 guard 层记录；需要时用 curl 抓取或开启上游 raw HTTP capture。

---

## 6. 验收标准

- [ ] 含 `event:queue_status` 的 SSE 流仍产出完整回复，不抛 invalid response。
- [ ] `queue_status` 帧不产生 update，usage 正常上报。
- [ ] 排队心跳持续期间不触发 `StreamStall`。
- [ ] `QUEUE_TIMEOUT` / `QUEUE_CANCELLED` 经生产入口 `chrys.foundation.errors.is_retryable` 判定为 `False`。
- [ ] `QUEUE_FULL` 保持可重试。
- [ ] 请求头 `Chrys-Request-Attempt-Id` 为 32 位 hex、每次 HTTP 尝试唯一；请求体不带 `request_id`。
- [ ] 排队中中断 → cancel 请求发出，`model` 一致、`request_id` 等于该次尝试的头值，`token` 头正确。
- [ ] 已放行或未排队中断 → 不发 cancel。
- [ ] cancel 204/404/409/5xx/超时都不改变中断结果。
- [ ] TUI / CLI / ACP 三种形态按 FR-6 显示与去重。
- [ ] 定制不可用时回退，且 WARNING 可见。
- [ ] 日志能完整回答「收到什么帧、解析成什么、取消发了什么、网关回了什么」。

---

## 7. 已知限制与风险

| 项 | 说明 |
|---|---|
| cancel 鉴权 | 当前取消请求的 `token` 取 profile `api_key`；若内网走登录态鉴权且 `api_key` 为空，取消会被**静默跳过**（已补 WARNING 日志）。内网必须专项验证，见《内网验证步骤与说明》 |
| 请求头依赖 | 网关未升级/未透传 `Chrys-Request-Attempt-Id` 时，新客户端发出的 cancel 会 404（客户端按契约内正常 no-op 记日志）；上线顺序必须**网关先、客户端后**，联调首项验证该头到达网关 |
| 代理 / TLS | 取消请求使用独立 `httpx.AsyncClient`，不继承 profile 的 `bypass_proxy` / `verify_ssl`；内网代理或自签证书需单独确认 |
| CLI Ctrl+C | 事件循环若在 cancel 发完前关闭，可能漏发一次（已知限制）；取消验证以 TUI/ACP 为主 |
| 非流式 | 不接排队、无进度、无 cancel；请求头仍带尝试 ID，网关按头关联 |
| 子代理 / workflow | 排队只落 detail 日志，不显示 UI |
| 原始 SSE | guard 层拿不到 `event:` / `data:` 原文；日志记录 SDK 解析后的字段 |
| 回答正文 | 故意不记录；正文看 UI 或 session 历史 |
| ACP 通知失败 | 上游 `ext_notification` 失败可能冒泡到整轮（健壮性问题，未在本期处理） |

---

## 8. 术语

| 术语 | 含义 |
|---|---|
| `position` | 前方还有多少个请求；`0` 表示下一个就是自己；`-1` 是客户端内部合成的「已放行」信号 |
| `queueSize` | 当前队列长度（含自己） |
| `queue_status` | 网关排队进度 SSE 具名事件 |
| `queue_rejected` | 网关排队拒绝 SSE 具名事件（`QUEUE_FULL` / `QUEUE_TIMEOUT` / `QUEUE_CANCELLED`） |
| `request_id` | 网关队列元素 ID：客户端不再生成，取上游 `Chrys-Request-Attempt-Id` 请求头（每次 HTTP 尝试一个新值）；cancel 请求体里的 `request_id` 即该值 |
| `QUEUE_FULL` | 队列已满，可退避重试 |
| `QUEUE_TIMEOUT` | 排队超过 `max_wait_time`，终态，不自动重试 |
| `QUEUE_CANCELLED` | 客户端主动取消，按取消收尾 |
