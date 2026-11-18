# ADR-model-queue-progress--observer-callback-channel：排队进度经 observer 回调链上送

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-<batch-slug>--<decision-slug> 取代）——括号内即后继 ID（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-18
- 确认意见：尽量不改上游，若必须要改，要少而集中的改（可选；审阅中形成的判断、附加条件或保留）
- 待重签说明（2026-11-18 评审后）：新增决策 5（headless 白名单）与决策 4 的 ACP 去重；决策 2 去掉无消费方的 `agent_name`；背景修正 `TurnBindings` 名称漂移。

> 本文为决策时点快照；现行规则以 `DEVELOPMENT.md` R1/R2/R9 为准。

## 背景

`model-queue-client` 批次已吸收网关排队帧，但没有可见反馈：TUI 只有无文案的呼吸点、CLI 无输出、ACP 无通知。要显示"前方 N 个请求"，必须把 `queue_status` 的位置从 wire 层送到三个前端。

约束（已取证）：

- `EventBus` 只活在 `SessionHost`/`TurnBindings`（`session_host.py:353`、`bindings.py:185`），`ChatCompletionsClient.__init__` 无 bus、无全局单例（`client.py:138-161`）。
- 既有上行通道只有两条：构造期下推 callable（`on_intermediate_text`，`observer.py:373-380`）与单比特 contextvar（`report_wire_progress`，`kernel/client.py:46-53`）。
- `bus.publish` 内联 await 订阅者（`events/bus.py:56-71`）。
- `InvocationEvent` 要求 `InvocationOrigin`（`events/types.py:84-99`），而装配期闭包创建时还没有 invocation 身份；`Event` 基类自带 `session_id`（`types.py:66-73`）。
- headless 前端（CLI/ACP）的事件要过两道门：`_HEADLESS_RUN_EVENT_TYPES` 元组（`session_host.py:133-182`，133 为定义行）与 `allows_headless_event`（`:195-203`，非 `InvocationEvent` 自动放行）。

## 决策

1. **通道用 observer 回调链**：`WireCallObserver` 增加 `on_queue_status`，经 `create_client` → `builder` → `construction` 注入；guard 在吸收帧时 `await` 该回调。
2. **事件为 session 级**：新增 `GatewayQueueStatus(Event)`（`session_id`/`position`/`queue_size`），不用 `InvocationEvent`——闭包在 build 期创建，没有 origin 可路由；不设 `agent_name`（三个前端都不消费，YAGNI）。
3. **回调 async，且先报 progress**：`bus.publish` 内联 await 订阅者，同步闭包无法 await；guard 里固定"先 `report_wire_progress()`，再 `await on_status(...)`"，避免 UI 回调吃掉 stall 看门狗的预算；guard 侧兜住回调异常，UI 故障不得中断 LLM 流。
4. **三个前端各自渲染**：TUI（WaitingRow 文案，轮次开始清空）、CLI（名次变化才输出一行）、ACP（`chrys/queue_status` 通知 + 白名单注册 + 同 position 不重发，避免心跳噪声）。
5. **headless 事件白名单同步加条目**：`GatewayQueueStatus` 必须进 `_HEADLESS_RUN_EVENT_TYPES`，否则 CLI 与 ACP 都会静默丢弃（`allows_headless_event` 先按元组过滤）。
6. **中文文案落 kernel 档定制包**（`src/chrys/kernel/aixcoding/queue_progress/`）：零依赖 → R9 最低档判据；按 ADR-0010 不纳入 i18n。

## 理由

- 否决 contextvar 带值通道：要改 kernel 公开 API，且注入点落在 attempt 生命周期，漏包即静默不显示——本批刚因"静默失效"被自审抓过一次。
- 否决复用 `InvocationRetryAttempt`：会弹「Retrying in Ns」卡片并触发 CLI `↻`，语义错。
- 否决 service 直接 publish：无通路，已证。
- 否决只做 TUI：插件/桌面端走 ACP，不做就等于该形态没做。
- 选 session 级事件：`Event` 自带 `session_id`，三个前端都按会话过滤，语义足够；强行用 `InvocationEvent` 需要伪造 origin，更脆。
- 否决 CLI/ACP 各自带外 `bus.subscribe` 绕开白名单：两处各改、总行数更多，而且把 turn 内进度事实放到带外订阅，语义更绕（与 `observe_restore` 那类"会话外状态"不同用途）。

## 后果

- 升级义务：`WireCallObserver` 构造契约、`bus.publish` 的 inline-await 语义、`_HEADLESS_RUN_EVENT_TYPES` 白名单、`TurnProgress.handle` 的分发结构、`WaitingRow` 的行高、ACP 通知白名单，六处变化时复核定制登记 `model-queue-progress:*` 并跑定制测试。其中白名单与 CLI 分发结构两处失效是**静默**的（不报错、不显示），评审时须重点回归。
- 性能边界：排队帧频率 = 名次变化 + 20s 心跳，publish 内联 await 三个轻量 handler，可接受；若将来某前端 handler 变重，需改为队列化。
- 事件归属：排队是传输层状态，不是 invocation 事实；后续若需按 invocation 路由（例如子代理排队卡片），应另立事件而不是给本事件补 origin。
