# 设计：排队进度提示（model-queue-progress）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-19
- 确认意见：尽量不改上游，若必须要改，要少而集中的改（可选；审阅中形成的判断、附加条件或保留）

## 方案概述

复用既有的"构造期下推 callable"通道（`on_intermediate_text` 同构），把排队位置从 wire 层送到三个前端；事件为 **session 级**（`Event` 基类带 `session_id`，不需要 `InvocationOrigin`——闭包在 build 期创建，那时没有 invocation 身份）。

```
guard_queue_frames(chunks, on_status)            ← service/aixcoding/llm_queue（定制）
  └─ 先 report_wire_progress()，再 await on_status(QueueStatus)
        ▲                                        （顺序固定：UI 回调不吃 watchdog 预算）
chat_completions/client.py                       ← 取 self._observer.on_queue_status
        ▲ 构造期注入
service/llm/clients.py::create_client(on_queue_status=...)
        ▲
orchestration/engine/build/builder.py → construction.py 的 async 闭包：
    await bus.publish(GatewayQueueStatus(session_id=..., position=..., queue_size=...))
        │
        │  ⚠ 必须同时加入 session_host._HEADLESS_RUN_EVENT_TYPES，
        │    否则 CLI / ACP 两条 stream 会把事件静默丢弃（allows_headless_event）
   ┌────┴──────────────┬──────────────────────┐
   ▼                   ▼                      ▼
TUI subscriptions   CLI TurnProgress.handle  ACP server
→ event_handlers    （非 InvocationEvent，     → ext_notification
→ view_adapter       走 match 的独立 case）     → chrys/queue_status
→ WaitingRow 文案    → 名次变化才输出一行       → 同 position 不重发
```

`bus.publish` 内联 await 订阅者（`events/bus.py:56-71`），故回调必须是 async；handler 只改一行文案，微秒级，对流速影响可忽略。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面 | 结论 |
|---|---|---|---|---|
| A′. 复用 observer 回调链 + session 级事件（本方案） | 与既有 `on_intermediate_text` 同构；装配点明确；失效会抛错不静默 | 13 个上游文件（功能横跨 service → engine → foundation → 三个前端） | 13×~114×低-中 | ✓ 采纳 |
| B. kernel 加带值 contextvar `report_queue_status()` | `service/llm/**` 不动 | 要改 kernel 公开 API；注入点落在 attempt 生命周期，漏包即**静默不显示**；且 loop/attempts 拿不到 emitter，还要向 bindings 借通道 | 12×~100×中 | ✗ 静默失败模式不可观测 |
| C. 复用 `InvocationRetryAttempt` 伪装排队 | 只改 2 处 | 触发「Retrying in Ns」卡片与 CLI `↻`，语义完全错 | 2×~10×高 | ✗ 技术反对 |
| D. service 层直接 publish | 最直接 | 不存在通路：`ChatCompletionsClient.__init__` 无 bus、无单例（`client.py:138-161`） | — | ✗ 不可行（已证） |
| E. 只做 TUI，不做 CLI/ACP | 省 2 个文件 | 插件/桌面端经 ACP，看不到提示 = 该形态没做 | 11 | ✗ 不满足"展示没问题" |
| F. CLI/ACP 各自带外 `bus.subscribe`，绕开 session_host | 不碰白名单 | 两处各改、总行数更多，且把 turn 内进度事实放到带外订阅，语义更绕 | 14×~120×中 | ✗ 分散且语义不纯 |

R1 自查（必答）：
- 业务逻辑已外置？是。位置解析与转译在既有 `src/chrys/service/aixcoding/llm_queue/`；中文文案在 `src/chrys/kernel/aixcoding/queue_progress/`（零依赖 → 按 R9 判据落最低档 kernel，被 app 层 import 合法）；上游每处只留 1–3 行接线。`construction.py` 的 publish 闭包维持内联（14 行，与 `_on_intermediate` 同位同形）——归位定制包需要新的 publisher 工厂接口，属于为 14 行引入一层抽象，性价比不划算。
- 接线点能否更少？不能。功能需穿过 service（wire 回调）→ orchestration（装配与 publish）→ orchestration（headless 白名单）→ foundation（事件类型）→ 三个前端（各自渲染），每层至少 1 点；三个前端渲染无法共用（TUI widget / CLI 追加行 / ACP 协议通知）。
- 能否完全不改上游？不能：service 层无 EventBus 通路，事件类型必须落在三方都可达的 foundation。

**范围边界（显式声明，非回归）**：本批只接主 turn。子代理与 workflow 节点也走 `create_client`（`sub_agents/tools.py:436`、`workflows/agent_node_build.py:213`），但它们不注入 `on_queue_status`，排队提示不显示——与改造前行为一致，验收时不得当缺陷上报。

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/service/llm/observer.py` | `WireCallObserver` 增加 `on_queue_status` 参数与只读属性 | +10 | `# AIxCoding queue-progress: observer callback` |
| `src/chrys/service/llm/clients.py` | `create_client(...)` 增加同名参数并传给 observer | +6 | `# AIxCoding queue-progress: client factory passthrough` |
| `src/chrys/service/llm/chat_completions/client.py` | guard 调用处传 `self._observer.on_queue_status` | +2/−1 | `# AIxCoding queue-progress: pass queue callback` |
| `src/chrys/orchestration/engine/build/builder.py` | 透传参数到 client 构造 | +3 | `# AIxCoding queue-progress: build passthrough` |
| `src/chrys/orchestration/engine/build/construction.py` | async 闭包：`await bus.publish(GatewayQueueStatus(...))` | +14 | `# AIxCoding queue-progress: publish queue status` |
| `src/chrys/orchestration/session_host.py` | `_HEADLESS_RUN_EVENT_TYPES` 元组加入事件类型 + import（否则 CLI/ACP 静默丢弃） | +2 | `# AIxCoding queue-progress: headless event type` |
| `src/chrys/foundation/events/types.py` | 新增 `GatewayQueueStatus(Event)`（position/queue_size） | +12 | `# AIxCoding queue-progress: event type` |
| `src/chrys/app/tui/screens/main/subscriptions.py` | 订阅一行 | +1 | `# AIxCoding queue-progress: TUI subscription` |
| `src/chrys/app/tui/screens/main/event_handlers.py` | `on_queue_status` handler + 轮次开始清等待行文案 | +12 | `# AIxCoding queue-progress: TUI handler` |
| `src/chrys/app/tui/screens/main/view_adapter.py` | `show_queue_status` / `clear_queue_status`（等待行文案） | +10 | `# AIxCoding queue-progress: TUI render` |
| `src/chrys/app/tui/screens/main/ports.py` | `MainScreenPresentationView` 协议声明两个方法 | +2 | `# AIxCoding queue-progress: ports protocol` |
| `src/chrys/app/tui/screens/main/main_screen_presenter.py` | `MainScreenPresenter` 两个转发方法 | +6 | `# AIxCoding queue-progress: presenter facade` |
| `src/chrys/app/tui/widgets/chat/waiting_row.py` | 等待行增加可选文案（与 dot 同行） | +12 | `# AIxCoding queue-progress: waiting row note` |
| `src/chrys/app/cli/progress.py` | `TurnProgress.handle` 新 case（**不是** `InvocationActivity.handle`：后者签名收 `InvocationEvent` 且首行取 `event.origin`）+ 名次变化去重 | +14 | `# AIxCoding queue-progress: CLI line` |
| `src/chrys/app/acp/server.py` | `chrys/queue_status` 通知 + 白名单注册 + 同 position 不重发 | +16 | `# AIxCoding queue-progress: ACP notification` |
| `tests/app/tui/screens/test_prompt_shortcut_send.py` | 共享测试替身 `Builds.create_client` 接受并忽略新参数（被 ACP/TUI 多层测试复用） | +1 | `# AIxCoding queue-progress: test double accepts the callback` |

合计 16 文件、约 123 行。

**R2 追加记录（2026-11-18 实施中）**：`ports.py` 与 `main_screen_presenter.py` 不在首版清单内，是 TUI 分层（handler → `MainScreenPresenter` → `MainScreenPresentationView` 协议 → `ViewAdapter`）的必然接触面；跳过 facade 直连 `_view` 属穿透私有成员。追加经责任人批准（对 AI「R2 从 13 文件 114 行变为 15 文件 122 行」申请的答复为「design.md 为已确认」），共 +8 行。

R1 自查（逐行归属）：上游每处均为"挂点 + 一行调用/一个字段/一个元组条目"，无既有逻辑搬动。

## 对上游隐式行为的假设

1. 假设：`EventBus.publish` 内联 await 每个订阅者，异常被记录并吞掉（`bus.py:56-71`，内联 await 在 `:60-65`）→ 依赖方式：回调用 async，直连 `bus.publish` → 失效表现：若改为 fire-and-forget，文案可能不显示（不报错）；若改为异常上抛，会中断 LLM 流（guard 侧必须兜住回调异常）。
2. 假设：`WireCallObserver.__init__` 的回调在 client 生命周期内固定（`observer.py:366-368`）→ 依赖方式：构造期注入一次 → 失效表现：若改为 per-call 回调，需从 `WireCall` 取。
3. 假设：`WaitingRow` 只有一行高度（`waiting_row.py:62-64`），文案与 dot 同行不改变高度 → 依赖方式：不改 `get_content_height` → 失效表现：文案过长被截断或挤压 fold gap。
4. 假设：CLI 为纯追加行模型、无覆盖行（`progress.py:3-16`）→ 依赖方式：名次变化才输出，自行去重 → 失效表现：若上游改引入 Rich Live，当前实现会与覆盖行冲突。
5. 假设：ACP 通知必须在 `server.py:144-180` 的 `ACP_EXTENSION_NOTIFICATIONS` 白名单注册 → 依赖方式：新增 `chrys/queue_status` 并注册 → 失效表现：未注册时通知被拒/不发送。
6. **假设（评审补入）**：headless 事件必须同时满足两道门——`_HEADLESS_RUN_EVENT_TYPES` 元组（`session_host.py:133-182`，133 为定义行）与 `allows_headless_event`（`:195-203`，非 `InvocationEvent` 自动放行）→ 依赖方式：事件入元组即放行 → 失效表现：**不入元组则 CLI 与 ACP 静默丢弃事件，无任何报错**（本期评审发现的硬伤）。
7. 假设：`TurnProgress.handle` 的 `match` 末尾 `case _: return`（`progress.py:742-743`）是 CLI 的唯一分发点，`InvocationActivity.handle` 只收 `InvocationEvent`（`:355-356` 首行取 `origin`）→ 依赖方式：新 case 加在 `TurnProgress.handle` → 失效表现：加错位置则事件被静默丢弃。

## 定制点登记预告

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| model-queue-progress:observer-callback | src/chrys/service/llm/observer.py | AIxCoding queue-progress: observer callback | 1 | `WireCallObserver.__init__` | 低 | 〔上游等价〕上游提供通用 wire 层回调注册机制 |
| model-queue-progress:factory-passthrough | src/chrys/service/llm/clients.py | AIxCoding queue-progress: client factory passthrough | 4 | `create_client` / `_assemble_stack` | 低 | 随 observer-callback |
| model-queue-progress:client-passthrough | src/chrys/service/llm/chat_completions/client.py | AIxCoding queue-progress: pass queue callback | 1 | `_open_stream` | 低 | 随 observer-callback |
| model-queue-progress:build-passthrough | src/chrys/orchestration/engine/build/builder.py | AIxCoding queue-progress: build passthrough | 2 | `build_agent` | 低 | 随 observer-callback |
| model-queue-progress:publish | src/chrys/orchestration/engine/build/construction.py | AIxCoding queue-progress: publish queue status | 3 | `bus.publish` | 中（内联 await 订阅者） | 〔上游等价〕事件总线原生支持 wire 层进度事件 |
| model-queue-progress:headless-event-type | src/chrys/orchestration/session_host.py | AIxCoding queue-progress: headless event type | 2 | `_HEADLESS_RUN_EVENT_TYPES` / `allows_headless_event` | 高（漏加即两前端静默失效） | 〔上游等价〕headless 白名单改为按事件基类放行 |
| model-queue-progress:event-type | src/chrys/foundation/events/types.py | AIxCoding queue-progress: event type | 1 | `Event` | 低 | 〔上游等价〕上游提供排队/背压类事件 |
| model-queue-progress:tui-subscription | src/chrys/app/tui/screens/main/subscriptions.py | AIxCoding queue-progress: TUI subscription | 2 | `_sub` | 低 | 随 event-type |
| model-queue-progress:tui-handler | src/chrys/app/tui/screens/main/event_handlers.py | AIxCoding queue-progress: TUI handler | 3 | `MainScreen` handler 表 + 轮次开始 | 低 | 随 event-type |
| model-queue-progress:tui-render | src/chrys/app/tui/screens/main/view_adapter.py | AIxCoding queue-progress: TUI render | 1 | `show_status` 邻域 | 低 | 随 event-type |
| model-queue-progress:ports-protocol | src/chrys/app/tui/screens/main/ports.py | AIxCoding queue-progress: ports protocol | 1 | `MainScreenPresentationView` | 低 | 随 tui-render |
| model-queue-progress:presenter-facade | src/chrys/app/tui/screens/main/main_screen_presenter.py | AIxCoding queue-progress: presenter facade | 1 | `MainScreenPresenter` | 低 | 随 tui-render |
| model-queue-progress:waiting-row | src/chrys/app/tui/widgets/chat/waiting_row.py | AIxCoding queue-progress: waiting row note | 1 | `WaitingRow.render` | 中（高度/换行/跨轮残留） | 〔上游等价〕WaitingRow 自带文案能力 |
| model-queue-progress:cli-line | src/chrys/app/cli/progress.py | AIxCoding queue-progress: CLI line | 6 | `TurnProgress.handle`（含 `TurnStarted` 重置） | 中（锚点错即静默） | 〔上游等价〕CLI 提供实时状态行机制 |
| model-queue-progress:acp-notification | src/chrys/app/acp/server.py | AIxCoding queue-progress: ACP notification | 4 | `ext_notification` 白名单 | 低 | 〔协议变更〕ACP 协议原生提供排队/背压通知 |
| model-queue-progress:test-double | tests/app/tui/screens/test_prompt_shortcut_send.py | AIxCoding queue-progress: test double accepts the callback | 1 | `Builds.create_client` | 低 | 随 factory-passthrough |

## 风险与最坏情况

- **headless 白名单漏配**：CLI/ACP 静默收不到（评审发现）。已列为登记点（risk 高）并进测试矩阵。
- **CLI 挂点错位**：`InvocationActivity.handle` 收 `InvocationEvent` 且首行取 `origin`，加错位置会静默丢弃。已把锚点固定为 `TurnProgress.handle` 并进测试。
- **WaitingRow 跨轮残留**：它是持久 widget（`chrome.py` 创建一次复用），不清文案则下个 turn 会带着上一轮的"排队中"。缓解：轮次开始时清空（handler 同文件），测试矩阵覆盖。
- 慢订阅者拖慢流速：`bus.publish` 内联 await。缓解：handler 只改一行文案；guard 侧兜住回调异常并记日志。
- 文案截断：现行文案「当前模型请求量大，请求排队约 N 人」约 18 字（中文约 36 列），80 列终端绰绰有余；2026-11-19 二次调整按要求去掉了尾部的「请稍候或切换至其他模型」建议语。`queueSize` 自同日文案调整起不再进文案，事件与 ACP 载荷仍携带。
- 多会话串号：事件带 `session_id`，各前端按会话过滤；client 按 session 构建，回调同源。
- 回滚：删除 13 处接线与 `GatewayQueueStatus` 即完全恢复（无持久化、无协议破坏）。

## ADR 判定

- ① 有被认真考虑但否决的备选（B/C/D/E/F）：**是**
- ② 撤销代价高：否（删除接线与事件类即回滚）
- ③ 约束未来工作模式：否
- ④ 依赖上游非公开接口或行为（observer 回调固定、bus 内联 await、headless 白名单、WaitingRow 行高、ACP 白名单）：**是**

→ 出 ADR：`standards/adr/model-queue-progress--observer-callback-channel.md`。
