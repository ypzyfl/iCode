# 设计：排队进度提示（model-queue-progress）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-25
- 确认意见：尽量不改上游，若必须要改，要少而集中的改（可选；审阅中形成的判断、附加条件或保留）确认签订和桌面端ACP通讯

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

| 文件 | 改什么 | 预估行数 | 实测 numstat（2026-11-20） | 标记注释位置 |
|---|---|---|---|---|
| `src/chrys/service/llm/observer.py` | `WireCallObserver` 增加 `on_queue_status` 参数与只读属性 | +10 | +9/−1 | `# AIxCoding queue-progress: observer callback` |
| `src/chrys/service/llm/clients.py` | `create_client(...)` 增加同名参数并传给 observer | +6 | +12/−1 | `# AIxCoding queue-progress: client factory passthrough` |
| `src/chrys/service/llm/chat_completions/client.py` | guard 调用处传 `self._observer.on_queue_status` | +2/−1 | +2/−1（client.py 总计 +38/−5，含 client 批；C2 后） | `# AIxCoding queue-progress: pass queue callback` |
| `src/chrys/orchestration/engine/build/builder.py` | 透传参数到 client 构造 | +3 | +4/−0 | `# AIxCoding queue-progress: build passthrough` |
| `src/chrys/orchestration/engine/build/construction.py` | async 闭包：`await bus.publish(GatewayQueueStatus(...))` | +14 | +15/−1 | `# AIxCoding queue-progress: publish queue status` |
| `src/chrys/orchestration/session_host.py` | `_HEADLESS_RUN_EVENT_TYPES` 元组加入事件类型 + import（否则 CLI/ACP 静默丢弃） | +2 | +4/−0 | `# AIxCoding queue-progress: headless event type` |
| `src/chrys/foundation/events/types.py` | 新增 `GatewayQueueStatus(Event)`（position/queue_size） | +12 | +14/−0 | `# AIxCoding queue-progress: event type` |
| `src/chrys/app/tui/screens/main/subscriptions.py` | 订阅一行 | +1 | +4/−0 | `# AIxCoding queue-progress: TUI subscription` |
| `src/chrys/app/tui/screens/main/event_handlers.py` | `on_queue_status` handler + 轮次开始清等待行文案 | +12 | +15/−0 | `# AIxCoding queue-progress: TUI handler` |
| `src/chrys/app/tui/screens/main/view_adapter.py` | `show_queue_status` / `clear_queue_status`（等待行文案） | +10 | +22/−0 | `# AIxCoding queue-progress: TUI render` |
| `src/chrys/app/tui/screens/main/ports.py` | `MainScreenPresentationView` 协议声明两个方法 | +2 | +3/−0 | `# AIxCoding queue-progress: ports protocol` |
| `src/chrys/app/tui/screens/main/main_screen_presenter.py` | `MainScreenPresenter` 两个转发方法 | +6 | +7/−0 | `# AIxCoding queue-progress: presenter facade` |
| `src/chrys/app/tui/widgets/chat/waiting_row.py` | 等待行增加可选文案（与 dot 同行） | +12 | +16/−1 | `# AIxCoding queue-progress: waiting row note` |
| `src/chrys/app/cli/progress.py` | `TurnProgress.handle` 新 case（**不是** `InvocationActivity.handle`：后者签名收 `InvocationEvent` 且首行取 `event.origin`）+ 名次变化去重 | +14 | +24/−0 | `# AIxCoding queue-progress: CLI line` |
| `src/chrys/app/acp/server.py` | `chrys/queue_status` 通知 + 白名单注册 + 同 position 不重发 | +16 | +28/−0 | `# AIxCoding queue-progress: ACP notification` |
| `tests/app/tui/screens/test_prompt_shortcut_send.py` | 共享测试替身 `Builds.create_client` 接受并忽略新参数（被 ACP/TUI 多层测试复用） | +1 | +2/−0 | `# AIxCoding queue-progress: test double accepts the callback` |
| `tests/architecture/trajectory_wait_manifest.json` | progress 批刷新 wait 清单（生成产物，`MARKER_EXEMPTIONS`） | 未列 | +10/−2（progress 增量；文件总计 +29/−3，含 client 两表） | — |
| `src/chrys/app/acp/doc/frontend-api.md` | Extension notifications 分组列表加 `queue_status`；Notes 补三帧契约（v1.4 D3 落地；v1.5 改方法名、v1.6 补拒绝帧、v1.7 合并为 status 三态） | +10 | +15/−1 | HTML 注释 `<!-- AIxCoding queue-progress: document queue_status (v1.4 D3, v1.5 to v1.7) -->`（`#` 行在 .md 会渲染成标题，故用渲染不可见的 HTML 注释） |

合计 **17 文件**；首版预估约 123 行，实测（numstat）约 **+191/−7**：
15 个专属文件 +179/−4、`client.py` 内 progress 部分 +2/−1、manifest progress 增量约 +10/−2。

> 上表为 v1.0/v1.2 首版快照；现行口径以 v1.3 归位改造变更单为准（含相对 base 的净表与"不移清单"）。

**2026-11-20 回填（评审 C1/C7）**：上表新增 manifest 行并回填实测 numstat；
正文变更按 R10 需责任人重签，AI 未改头部签认行。

**R2 追加记录（2026-11-18 实施中）**：`ports.py` 与 `main_screen_presenter.py` 不在首版清单内，是 TUI 分层（handler → `MainScreenPresenter` → `MainScreenPresentationView` 协议 → `ViewAdapter`）的必然接触面；跳过 facade 直连 `_view` 属穿透私有成员。追加经责任人批准（对 AI「R2 从 13 文件 114 行变为 15 文件 122 行」申请的答复为「design.md 为已确认」），共 +8 行。
**2026-11-20 回填（C1/C7）**：`tests/architecture/trajectory_wait_manifest.json` 为第 17 个文件（progress 批增量），实测行数已入上表；本行为正文变更，需责任人重签。
**2026-11-26 回填（CI R2 门禁）**：v1.4 D3 裁决的 `src/chrys/app/acp/doc/frontend-api.md` 此前只登记在 v1.4–v1.7 变更单各自的 R2 增量表里，而 `check_r2_diff` 只解析本节顶层表，govern 门禁判其 unauthorized；现按已签变更单回填为第 18 个文件。本行为正文变更，需责任人重签，AI 未改头部签认行。

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
| model-queue-progress:build-passthrough | src/chrys/orchestration/engine/build/builder.py | AIxCoding queue-progress: build passthrough | 2 | `build_agent` | 低 | 随 observer-callback |
| model-queue-progress:publish | src/chrys/orchestration/engine/build/construction.py | AIxCoding queue-progress: publish queue status | 2 | `make_queue_status_publisher` 工厂调用（`bus.publish` 内联 await 移入定制包，v1.3） | 中（内联 await 订阅者） | 〔上游等价〕事件总线原生支持 wire 层进度事件 |
| model-queue-progress:headless-event-type | src/chrys/orchestration/session_host.py | AIxCoding queue-progress: headless event type | 2 | `_HEADLESS_RUN_EVENT_TYPES` / `allows_headless_event`（事件类现居 `kernel/aixcoding/queue_progress.py`，v1.3） | 高（漏加即两前端静默失效） | 〔上游等价〕headless 白名单改为按事件基类放行 |
| model-queue-progress:tui-subscription | src/chrys/app/tui/screens/main/subscriptions.py | AIxCoding queue-progress: TUI subscription | 2 | `_sub` | 低 | 随 event-type |
| model-queue-progress:tui-handler | src/chrys/app/tui/screens/main/event_handlers.py | AIxCoding queue-progress: TUI handler | 3 | `MainScreen` handler 表 + 轮次开始 | 低 | 随 event-type |
| model-queue-progress:tui-render | src/chrys/app/tui/screens/main/view_adapter.py | AIxCoding queue-progress: TUI render | 1 | `show_status` 邻域 | 低 | 随 event-type |
| model-queue-progress:ports-protocol | src/chrys/app/tui/screens/main/ports.py | AIxCoding queue-progress: ports protocol | 1 | `MainScreenPresentationView` | 低 | 随 tui-render |
| model-queue-progress:presenter-facade | src/chrys/app/tui/screens/main/main_screen_presenter.py | AIxCoding queue-progress: presenter facade | 1 | `MainScreenPresenter` | 低 | 随 tui-render |
| model-queue-progress:waiting-row | src/chrys/app/tui/widgets/chat/waiting_row.py | AIxCoding queue-progress: waiting row note | 1 | `WaitingRow.render` | 中（高度/换行/跨轮残留） | 〔上游等价〕WaitingRow 自带文案能力 |
| model-queue-progress:cli-line | src/chrys/app/cli/progress.py | AIxCoding queue-progress: CLI line | 6 | `TurnProgress.handle`（含 `TurnStarted` 重置；去重与写行逻辑居 `app/aixcoding/cli/queue_line.py::QueueLineNote`，v1.3） | 中（锚点错即静默） | 〔上游等价〕CLI 提供实时状态行机制 |
| model-queue-progress:acp-notification | src/chrys/app/acp/server.py | AIxCoding queue-progress: ACP notification | 5 | `ext_notification` 白名单 + `_handle_chrys_extension_event`（`TurnStarted` 重置，v1.3；去重与载荷居 `app/aixcoding/acp/queue_notify.py`；计数 5 = import×2/白名单/分支/重置） | 低 | 〔协议变更〕ACP 协议原生提供排队/背压通知 |
| model-queue-progress:test-double | tests/app/tui/screens/test_prompt_shortcut_send.py | AIxCoding queue-progress: test double accepts the callback | 1 | `Builds.create_client` | 低 | 随 factory-passthrough |
| model-queue-progress:frontend-api-doc | src/chrys/app/acp/doc/frontend-api.md | AIxCoding queue-progress: document queue_status | 1 | Extension notifications 分组列表与 Notes 的 `queue_status` 三帧契约（marker 为渲染不可见的 HTML 注释，v1.4 D3 落地、v1.5 随方法名改锚） | 低（纯文档） | 〔上游等价〕上游文档原生收录该通知契约 |

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

---

## 变更单 v1.2（2026-11-24，责任人裁决）：队首文案不再声称已获取模型资源

现象：`position=0` 时显示「正在获取模型资源」，随后仍可能收到 `queue_rejected(QUEUE_TIMEOUT)`。

事实：`position=0` 是"下一个就轮到你"（网关文档 §3.2），不是已拿到并发槽位；占用槽位的请求若一直不结束，
`max_wait_time` 到期仍会超时（§4/§5）。客户端能拿到的唯一放行信号仍是首个数据帧（`RELEASED_POSITION`），
文案不得暗示已获得模型资源。

改动（仅文案，无逻辑变更）：

| 文件 | 改什么 | 实测 numstat |
|---|---|---|
| `src/chrys/kernel/aixcoding/queue_progress.py` | `position == 0` 文案「正在获取模型资源」→「已排到队首，当前为队列第一位」；docstring 说明 position 0 不持有槽位 | `+9/−5`（相对本批 base） |
| `aixcoding/tests/llm/test_model_queue_progress.py` | `queue_note(0)` 断言同步 | 1 行 |

`>0` 文案、`RELEASED_POSITION` 语义、`QUEUE_TIMEOUT` 终态不重试均不变（网关 §3.3 明确重试会重新排队、放大雪崩）。
本批仍只接主 turn，子代理/workflow 不注入回调的边界不变。

已知边界：队首超时是服务端排队语义，客户端不改变其判定；若服务端希望"队首不再超时"，需服务端调整
`max_wait_time` 语义或不再对队首下发 `position:0`。

文档同步：本批 `requirements.md`（验收文案）、`aixcoding/docs/model_concurrency_queue/{requirements,test-cases,intranet-verification}.md`
的 position 0 文案；`verification.md` 为 2026-11-19/20 的历史取证记录，保留原样不改。

本正文增量按 R10 需责任人重签头部，AI 未代填。

**2026-11-24 修订记录（签认后同日）**：队首文案最终定为「已排到队首，当前为队列第一位」；
提交 `737a4a00`。

---

## 变更单 v1.3（2026-11-24，责任人裁决）：事件通道与三端渲染归位改造

> 决策来源：Owen 对话裁决（2026-11-24）：走完整管线，把"利大于弊"的上游改动全部移入定制包，移 Regulation 不动的逐项说明原因；责任人重签本 design 后实施。动因：PR #151 独立评审与签认意见"尽量不改上游"。

### 改动

**A. 事件类移出 `foundation/events/types.py`（撤销 1 个上游文件）**

`GatewayQueueStatus` 移入 `kernel/aixcoding/queue_progress.py`（该模块原承载三端共享文案，现兼载事件类与发布工厂；新增 `dataclasses` 与 `foundation.events.types.Event` 依赖——kernel 档合法，docstring 的"零依赖"表述同步改写）。`types.py` 整体撤销、恢复上游原样。6 处 import 源切换：session_host、construction、subscriptions、event_handlers、cli/progress、acp/server，及 aixcoding/tests 4 处。

- 守卫核验：`tests/architecture/test_event_declaration_guard.py:460-473` 的运行时闭包检查仅对 `__module__` 为 types.py 的 `Event` 子类报错，定制包内子类合法。
- 原结论"事件类型必须落在 foundation"不成立处：kernel/aixcoding 对三方前端与 orchestration 同样可达，且不属上游修改，无需 R2。
- 行为锚定：`test_queue_status_event_passes_the_headless_boundary`（真实调用 `allows_headless_event`）继续有效。
- 风险：session_host / construction 对 kernel/aixcoding 形成顶层 import（结构性接线、失败显式呈现；wheel 同包发布，仅损坏安装可触发）；anchor = `foundation.events.types.Event`（上游加字段经 dataclass 继承自动获得）。

**B. construction.py 闭包工厂化（+15/−1 → 约 +4/−0）**

10 行 publish 闭包移入 `make_queue_status_publisher(bus, session_id)`（kernel/aixcoding/queue_progress.py）；上游留导入一行 + `on_queue_status=make_queue_status_publisher(bus, session.session_id)` 一参。原否决理由"为 14 行引入一层抽象性价比不划算"，按签认意见"尽量不改上游"重估后翻案：净省 11 行、construction 退出升级热点。

**C. ACP 判重入包（+28 → 实测 +18），顺带修复评审缺陷 1**

去重状态（`WeakKeyDictionary` 按服务器实例隔离，测试间不串号）与载荷决策移入新定制模块 `app/aixcoding/acp/queue_notify.py`（非 R2）。上游留：import×2、白名单 2 行、isinstance hook 8 行（`queue_status_payload` 出载荷 → 字面量 `ext_notification` 一行发送 → `confirm_queue_status` 落地确认——钉子测试 `test_server_capabilities.py` 扫描 server.py 通知字面量，发送体不能整体离场）、`_handle_chrys_extension_event` 的 `TurnStarted` 分支加重置 1 行——**即 PR #151 评审问题 1 的修复**（中断后下一轮同名次首帧不再被残留去重值吞掉）。
风险：服务器对象可弱引用（普通类成立；若上游引入无 weakref 的 `__slots__`，回退为上游保留 2 行状态初始化）。

**D. CLI 渲染体入包（+24 → 约 +12）**

名次去重与写行逻辑移入新定制模块 `app/aixcoding/cli/queue_line.py::QueueLineNote`（状态随 `TurnProgress` 实例生命周期）；上游留 import×3、状态初始化 1 行、`case GatewayQueueStatus` / `case TurnStarted` 两个挂点。

### 上游改动清单（R2 净表——相对 base 的最终口径，2026-11-24 实施 numstat 实测）

| 文件 | 现 PR | 归位后（实测） |
|---|---|---|
| `src/chrys/foundation/events/types.py` | +14 | 0（撤销） |
| `src/chrys/orchestration/engine/build/construction.py` | +15/−1 | +6/−3 |
| `src/chrys/orchestration/session_host.py` | +4 | +5/−0 |
| `src/chrys/app/acp/server.py` | +28 | +18/−0 |
| `src/chrys/app/cli/progress.py` | +24 | +15/−0 |
| `src/chrys/app/tui/`（6 文件） | +67/−1 | +69/−1（事件类独立 import 行各 +1 行标记） |
| `src/chrys/service/llm/chat_completions/client.py` | +40/−5 | +30/−1（见 model-queue-client design v1.4） |
| `src/chrys/service/llm/clients.py`、`observer.py`、`build/builder.py` | +25/−2 | 不变（见不移清单） |
| `tests/app/tui/screens/test_prompt_shortcut_send.py` | +2 | +2 |
| `tests/architecture/trajectory_wait_manifest.json` | +29/−3 | +34/−2（生成产物刷新） |

src/chrys 上游合计：15 文件 +217/−9 → **14 文件 +162/−7**；含 tests 总计：17 文件 +248/−12 → **16 文件 +198/−9**（净减 1 个上游文件、约 50 行增改）。

实测与预估的偏差说明（2026-11-24 实施）：① ACP hook 采用 claim/confirm 结构（`queue_status_payload` 出载荷、上游保留字面量 `ext_notification` 一行发送、`confirm_queue_status` 落地后记录）——上游测试 `test_server_capabilities.py` 以 AST 扫描 server.py 的通知字面量并与白名单比对（1566 用例分片实测红→改后绿），发送体不能整体离场，"发送落地才记录"语义原样保留；② client.py `finally` 保留包缺失时的上游关流分支（降级不劣于 v1.3）；③ 事件类独立 import 行比 foundation 块内共享导入多 1 行标记（server.py 对账计数 5）。

### 不移清单（逐项原因）

| 文件 | 原因 |
|---|---|
| `observer.py` / `clients.py` / `builder.py` / `test_prompt_shortcut_send.py`（+25/−2） | 参数接线，是复用上游 `on_intermediate_text` 同构通道的最小形态；替代（全局注册表 / contextvar）即备选 B/D 的"漏包即静默不显示"失效模式，R1 明确反对 |
| `session_host.py`（+4） | `allows_headless_event` 第一道门就是 `_HEADLESS_RUN_EVENT_TYPES` 元组（session_host.py:199-207 实核：不在元组直接 `return False`），白名单行省不掉 |
| TUI 6 文件（+67/−1） | `waiting_row.py` 文案渲染必须改上游 widget 本体；`view_adapter`/`ports`/`presenter`（+32）是 MVP 分层税，消除需事件处理器绕过 presenter 直查 UI 树，属穿透分层，弊大于利 |
| `trajectory_wait_manifest.json`（+29/−3） | 生成产物（`MARKER_EXEMPTIONS`）：包内存在 await 即必须有对应行，逻辑入包行数近似不变 |

### 对上游隐式行为的假设（增量）

8. 事件声明守卫只约束 types.py 内定义的类（`test_event_declaration_guard.py:460-473`）→ 失效表现：守卫扩展为全仓闭包检查 → 定制测试红，届时事件类须迁回 foundation 或另立上游 ADR。
9. ACP 服务器对象可弱引用 → 失效表现：`WeakKeyDictionary` 报 TypeError → 回退为上游保留 2 行状态初始化。

### 定制点登记（增量）

- 删除 `event-type`（marker 随 types.py 撤销）与 `client-passthrough`（marker 并入 client 批 guard 锚）两行。
- `publish` 计数 3→2、anchor 改为工厂调用；`headless-event-type` / `cli-line` anchor 已更新（计数不变，分别 2/6）。
- `acp-notification` 计数 4→5（import×2〔定制模块 + 事件类〕/白名单/分支/`TurnStarted` 重置——实施实测，事件类 import 为独立语义点）。
- 新定制模块（非 R2、无 marker、行为锚定测试随既有 `test_model_queue_progress.py` 走上游真实调用点）：`app/aixcoding/acp/queue_notify.py`、`app/aixcoding/cli/queue_line.py`；`kernel/aixcoding/queue_progress.py` 扩载事件类与工厂（anchor：`Event`、`bus.publish` 内联 await 语义）。
- 中间态提示：design 先行删行、代码后行，`gen_customizations.py --strict` 在实施 commit 前为红（types.py marker 无登记），PR 头恢复绿——批次内预期。

### 验证（实施时执行）

定制测试全量（6 处 import 源更新后 52+ 用例）+ 上游 `test_event_declaration_guard`、`test_session_host`、ACP/CLI/TUI 相关分片 + ruff check/format + ty 三平台 + wait 清单刷新 + `gen_customizations.py --strict` + `check_docs.py`。

---

## 变更单 v1.4（2026-11-25，责任人裁决）：ACP 排队通知携带 requestId

> 决策来源：责任人对话裁决（2026-11-25）。桌面端将同步改造，按请求粒度消费排队状态；ACP 载荷由
> `{sessionId, position, queueSize}` 变为 `{sessionId, requestId, position, queueSize}`。
> 动因：排队的是"某个 HTTP 请求"而非会话——一个 turn 内多次模型调用、各类重试各是不同的请求；
> 会话 id 只能回答"哪个会话在排队"，回答不了"哪个请求在排队"。
> 本变更修改 R2 对象（`server.py` 既有挂点多传一个字段），按 R10 须责任人重签本文件头部后实施；AI 未改头部。
> 现状说明（2026-11-24 实核）：现版桌面端已消费 `_chrys/queue_status` 并渲染排队横幅，本变更不是补透传，
> 而是在已通的通道上加一个字段。

### 裁决记录（2026-11-25 签认时一并裁定）

| # | 事项 | 裁决 |
|---|---|---|
| D1 | 放行通知是否同样携带 `requestId` | **带**：`{sessionId, requestId, released: true}` |
| D2 | ACP 去重键是否加入 `requestId` | **加**：按 (requestId, position) 去重——中断后新请求恰逢同名次也重发，线上 id 不过期 |
| D3 | 是否在 `src/chrys/app/acp/doc/frontend-api.md` 补 `chrys/queue_status` 契约 | **补**（上游文档文件，入下方 R2 增量表）+ 落中文文档 |

### 方案

requestId 的来源与去向——逻辑全部在定制包内，上游只多传一个已在事件上的字段：

```text
raw.http_response.request.headers["Chrys-Request-Attempt-Id"]      ← 应答那次 HTTP 尝试的请求头（client 批 v1.3 既有）
  └─ track_queue_request() → QueueRequestTracker.request_id
       └─ observing().observe：转发前 replace(status, request_id=…)   ← QueueStatus 新增 request_id（默认 None）
            └─ observer.on_queue_status → make_queue_status_publisher
                 └─ GatewayQueueStatus(…, request_id=…)               ← 事件新增 request_id（默认 None）
                      ├─ TUI / CLI：不读该字段，行为不变
                      └─ ACP server.py 挂点：queue_status_payload(…, event.request_id)   ← 上游唯一改动（1 条语句）
                           └─ queue_notify.queue_status_payload：载荷加 "requestId"；未知时省略该键
```

`QueueStatus.request_id` 带默认值，guard 两处构造点不动；只有武装了 tracker 的请求才会被命名。

### 载荷契约（桌面端对接口径）

线上方法名 `_chrys/queue_status`：iCode 代码写 `chrys/queue_status`，Python ACP SDK 发送时自动加 `_` 前缀
（`acp/agent/connection.py:206`，`send_notification(f"_{method}", …)`）。本次不变。

| 通知 | 载荷 | 时机 |
|---|---|---|
| 排队中 | `{"sessionId": "<ACP 会话 id>", "requestId": "<32 位小写 hex>", "position": <int ≥ 0>, "queueSize": <int>}` | 每个 (requestId, position) 首次出现；心跳重复同名次不重发 |
| 放行 | `{"sessionId": "<ACP 会话 id>", "requestId": "<32 位小写 hex>", "released": true}`（D1 裁决：带） | 排队后首个数据帧到达时，一次 |

字段语义：

- `sessionId`：路由键，`session/new` 返回给客户端的会话 id；语义与取值不变。
- `requestId`：应答该次请求的 HTTP 尝试所带的 `Chrys-Request-Attempt-Id` 请求头值 = 网关队列元素键 =
  iCode 调 cancel 接口时 body 里的 `request_id`。每个 HTTP 尝试一个新值（SDK 重试/重定向、wire 重试、
  整轮重试各算一个），一个 turn 内会出现多个。
- `requestId` **可能缺席**：tracker 未武装时（应答尝试没有该请求头、或取消地址无法推导；产品路径不会出现）。
  缺席时其余字段照常发送。
- 键序按上表构造，但桌面端不应依赖 JSON 键序。
- 兼容性：**新 iCode + 现版桌面端**——现版处理器只读已知键（`acp-agent-host.ts:2900-2919`），多出的
  `requestId` 被忽略，横幅照常。**旧 iCode + 新桌面端**——载荷没有 `requestId`，故桌面端须按可选字段处理，
  缺席时退回按 `sessionId` 展示。

### 备选方案对比

| 方案 | 说明 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|
| **E. tracker 转发时回填 + 挂点多传一个字段（本单）** | 显式数据流：id 随状态对象一路带到载荷 | 上游 1 条语句（既有 marker 内）+ 清单刷新 | ✓ 采纳 |
| F. 发布工厂按会话登记"当前请求 id"，`queue_status_payload` 按 sessionId 查旁表 | 上游零改动 | 0（隐式耦合高） | ✗ R1「最小 ≠ 最隐」「直接依赖优于间接」：事件上明明有值却按会话反查，且依赖"每会话单请求在飞"的隐式前提——与本批备选 B 同类失效模式 |
| G. guard 增加 `request_id` 形参，由 `client.py` 传入 | guard 在 `raw` 返回前构造，那时还没有 id，须调整上游接线顺序 | 上游 2–3 行且改动既有接线结构 | ✗ 接触面更大，无额外收益 |

R1 自查（必答）：

- 能否完全不改上游？不能。挂点 `queue_status_payload(self, session_key, event.position, event.queue_size)` 只向
  定制包传两个标量，载荷构造器拿不到事件上的 `request_id`；零上游方案只有 F。
- 业务逻辑是否已全部外置？是。id 来源、回填、载荷构造与省略规则都在定制包；上游只把事件上已有的字段传给定制包。
- 接线点是否已最小化？是。一处、一条语句，落在既有 `acp-notification` 定制块内，不新增冲突面。
- 归属（R1 细则二）：该语句是纯参数透传（挂点）。要挪进定制包只能改为整体传 `event`——须同时改函数签名与
  本行，行数相同，而类型耦合从两个 int 变为事件类；无收益，不挪。

### 上游改动清单（R2，相对 v1.3 净表的增量）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/acp/server.py` | `_handle_turn_event` 的 `GatewayQueueStatus` 分支：`queue_status_payload(...)` 与 `confirm_queue_status(...)` 各末尾多传 `event.request_id`（同一 claim/confirm 结构的两半，确认不传则去重键永远判不等） | 2 条语句，同一物理行改写（113/99 列，不换行）；两行相对 base 本就是新增行，numstat 与 marker 计数均不变 | 既有 `AIxCoding queue-progress: ACP notification`（计数仍 5） |
| `src/chrys/app/acp/doc/frontend-api.md` | D3：扩展通知分组列表加 `chrys/queue_status`；Notes 加一条载荷契约（requestId 可缺席、(requestId, position) 去重、turn_started 重置） | 实测 **+10/−1** | HTML 注释 `<!-- AIxCoding queue-progress: document chrys/queue_status (v1.4 D3) -->`（`#` 行在 .md 会渲染成标题，故用渲染不可见的 HTML 注释；marker 扫描可识别，登记行 `frontend-api-doc` 见定制点登记预告） |
| `tests/architecture/trajectory_wait_manifest.json` | 生成产物刷新：`queue_progress.make_queue_status_publisher.publish`、`queue_cancel.QueueRequestTracker.observing.observe` 两处 await 原文变化；规则均保持默认 `unresolved` | 实测 **+2/−2**（2026-11-25 刷新，仅此两处重开） | 无（`MARKER_EXEMPTIONS`）；命令 `uv run python -m tests.support.trajectory_wait_inventory` |

定制包改动（非 R2，无新增 marker，登记表不变）：

| 文件 | 改什么 |
|---|---|
| `src/chrys/service/aixcoding/llm_queue/queue_frames.py` | `QueueStatus` 新增 `request_id: str \| None = None` |
| `src/chrys/service/aixcoding/llm_queue/queue_cancel.py` | `observing().observe` 转发 `replace(status, request_id=self._request_id)`；docstring 补一句说明 |
| `src/chrys/kernel/aixcoding/queue_progress.py` | `GatewayQueueStatus` 新增 `request_id`；发布工厂传 `request_id=status.request_id` |
| `src/chrys/app/aixcoding/acp/queue_notify.py` | `queue_status_payload` 加 `request_id=None` 形参，两种载荷加 `requestId`（空则省略该键）；去重键改为 (requestId, position)（D2 裁决「加」） |
| `aixcoding/tests/llm/test_model_queue_progress.py` | 新增用例（见验证计划） |

### 对上游隐式行为的假设（增量）

10. tracker 的 `request_id` 就是网关收到的队列元素键（client 批 v1.3 假设 1：`raw.http_response.request` 是最终尝试）
    → 依赖方式：直接复用 `QueueRequestTracker.request_id`，不另读一次 → 失效表现：`requestId` 与网关日志对不上；
    cancel 同源同失，`test_llm_queue_attempt_header.py` 先红。
11. （D2 裁决「加」后不再承载）原假设"每个会话同一时刻只有一个带 UI 回调的请求在飞"曾支撑按会话去重；
    去重键已含 requestId，同名次新请求会重发，本条保留仅作记录。
12. 未改造的桌面端处理器只读已知键、忽略未知键 → 依赖方式：只增键，不删不改既有键
    → 失效表现：桌面端新增严格 schema 拒绝未知键 → 须两端同步上线。

### 风险与最坏情况

- **同名次新请求被去重**：已由 D2 裁决「加」消除——去重键为 (requestId, position)，重试请求即便同名次也重发，
  线上 id 不过期；代价是 `queue_notify.py` 的去重值由 int 变 tuple（仅包内）。
- **桌面端把 `requestId` 当必填**：旧引擎或 tracker 未武装时横幅消失。缓解：契约标明可选；联调覆盖"无 requestId 仍展示"。
- **回滚**：撤销上表 4 个定制文件与测试改动、`server.py` 1 条语句、清单刷新，即回到 v1.3；无持久化、无数据迁移。

### ADR 判定（增量）

四问均否，不出 ADR：① 否决 F/G 属照 R1 规范排除，不是同等份量的设计取舍；② 字段只增不删，现版桌面端不受影响，
撤销代价低；③ 不约束后续工作模式；④ 未新增对上游非公开接口的依赖（tracker 读请求头是 client 批 v1.3 既有假设）。
本变更属既有 `model-queue-progress--observer-callback-channel` 决策 4 的载荷演进，通道与机制不变，ADR 正文不动。

### 验证计划（实施后执行，结果回填 verification.md）

- `aixcoding/tests/llm/test_model_queue_progress.py` 新增用例：
  - tracker 转发的每个状态（position 与放行）都带 `request_id`；未武装（`wire_queue_callback(observer, None)`）时为 `None`；
  - 发布工厂把 `request_id` 带到 `GatewayQueueStatus`；
  - ACP 载荷：排队 `{sessionId, requestId, position, queueSize}`、放行 `{sessionId, requestId, released: true}`、
    未知时没有 `requestId` 键；既有去重与轮次重置用例不改且仍绿；
  - 端到端锚定：生产 profile HTTP 客户端 + MockTransport（排队帧 → 数据帧），`WireCallObserver.on_queue_status`
    收到的 `request_id` 等于网关侧记录到的 `Chrys-Request-Attempt-Id`。
- 回归：`test_model_queue_cancel.py`、`test_llm_queue_attempt_header.py`、上游 `tests/app/acp`、
  `tests/architecture/test_trajectory_wait_inventory.py`。
- 门禁：ruff check/format、ty（三平台）、`check_docs.py`、`gen_customizations.py --strict`。

### 文档同步（随实施）

- 本批 `requirements.md`、`test-plan.md`、`plan.md`、`verification.md`；client 批 `plan.md` 备忘加一行互指。
- `aixcoding/docs/model_concurrency_queue/{requirements,test-cases,intranet-verification}.md` 的 ACP 载荷口径。
- 新增《模型排队桌面端透传说明.md》（同目录，中文名）：链路、载荷契约、桌面端展示口径、联调步骤、排障检查单。

---

## 变更单 v1.5（2026-11-25，责任人裁决）：通知方法名去 chrys 命名空间 + 排队帧补 released:false

> 决策来源：责任人对话裁决（2026-11-25）。该通知将作为**跨引擎标准**发给桌面端与其他引擎团队
> （权威契约：`aixcoding/docs/model_concurrency_queue/模型排队通知协议规范.md` v1.0），方法名不得带
> chrys 品牌；字面 `/queue_status`（无下划线）被否决——Python SDK 的 `ext_notification` 无条件加 `_`
> 前缀，发无下划线名字须伸手 SDK 私有连接，且偏离 ACP 扩展方法约定。定名 **`_queue_status`**
> （代码字面量 `queue_status`，SDK 自动加前缀）。同日裁决：**相位布尔对 `(released, rejected)` 每帧必填**
> （字段尽可能一致）：排队帧 `false,false`、放行帧 `true,false`；`message`/`traceId` 仅拒绝帧
> （v1.6）——无数据来源的字段不造值。本变更修改 R2 对象（`server.py` 字面量
> 与白名单），须责任人重签本文件头部后实施；AI 未改头部。

### 方案

| 位置 | 现状 | 改为 |
|---|---|---|
| `server.py::ACP_EXTENSION_NOTIFICATIONS` 白名单 | `"chrys/queue_status"` | `"queue_status"` |
| `server.py` `ext_notification` 调用字面量 | `"chrys/queue_status"` | `"queue_status"` |
| `queue_notify.py` docstring | `chrys/queue_status` | `queue_status`（线上名 `_queue_status`） |
| `queue_notify.py::queue_status_payload` | 排队帧不带相位布尔 | 三帧统一相位布尔对：排队 `"released": False, "rejected": False`、放行 `"released": True, "rejected": False`（键序 sessionId, requestId, released, rejected, position, queueSize） |
| `frontend-api.md` 契约行（分组列表 + Notes，v1.4 D3 所加） | `chrys/queue_status`；排队帧形无 `released` | `queue_status`（注明线上名带 `_` 前缀）；排队帧形补 `released: false` |
| `test_model_queue_progress.py` | 方法名 `"chrys/queue_status"`；排队载荷无相位布尔 | 方法名 `"queue_status"`；载荷断言补相位布尔对（排队 `released:False, rejected:False`；放行 `rejected:False`） |

定制点登记不变（`frontend-api-doc` 行的 marker 锚不含方法名；`acp-notification` 计数仍 5，
均在既有 marker 块内改写字面量，numstat 与 marker 计数不变）。

### 上游改动清单（R2，相对 v1.4 的增量）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/acp/server.py` | 白名单条目与 `ext_notification` 字面量 `chrys/queue_status` → `queue_status`（同行改写，既有 marker 块内） | 2 行改写（0 净增） | 既有 `AIxCoding queue-progress: ACP notification`（计数仍 5） |
| `src/chrys/app/acp/doc/frontend-api.md` | 契约行方法名 `chrys/queue_status` → `queue_status`（2 处） | 2 行改写（0 净增） | 既有 HTML 注释 marker（计数仍 1） |

### 兼容与迁移（上线顺序）

1. **桌面端先双注册** `_queue_status` 与 `_chrys/queue_status`（先例：其 `chrys/error` 与
   `_chrys/error` 双拼写），现版行为不受影响——排队帧的 `released: false` 现版不读该值，
   落入 position/queueSize 校验分支，天然兼容；
2. **iCode 后切**（本变更单实施）——只认旧名的桌面端从此收不到排队通知（丢横幅），故顺序不可倒；
3. 稳定后桌面端移除旧名注册。其他引擎直接按协议规范发 `_queue_status`。

### 风险与最坏情况

- 桌面端未双注册就发新 iCode：排队横幅消失（通知被忽略），无其他影响；回滚即改回字面量。
- 上游若引入以方法名为键的通知路由/测试：pin test（`test_server_capabilities.py` 扫描 server.py
  通知字面量并与白名单比对）随两处字面量同步改，红即发现。

### ADR 判定（增量）

四问均否，不出 ADR：改名是对外契约演进，撤销代价低（改回字面量）；不依赖新的上游非公开行为；
`_` 前缀约定与 SDK 自动加前缀行为已在 v1.4 假设范围内。

### 验证计划（实施后执行）

- `test_model_queue_progress.py` 方法名与排队载荷（含 `"released": False`）断言更新后全绿；
  `tests/app/acp`（含 pin test）回归；ruff / ty / check_docs / gen_customizations --strict；
  wait 清单不受影响（无 await 变化）。

---

## 变更单 v1.6（2026-11-25，责任人裁决）：第三帧「拒绝」（QUEUE_TIMEOUT / QUEUE_FULL）

> 决策来源：责任人对话裁决（2026-11-25）。契约见
> `aixcoding/docs/model_concurrency_queue/模型排队通知协议规范.md` §2.3/§4.7。现状空缺：队列拒绝
> （超时/队满）被 guard 转译为终态异常 → turn 普通失败 → 桌面端只见笼统错误（`kind:"unknown"`，
> 分类器无 QUEUE_TIMEOUT/QUEUE_FULL 映射，已核 `classify.py`），排队超时专属横幅永不触发。
> 时机语义（责任人已裁）：TIMEOUT 轮次终结即发；FULL 仅重试耗尽、整轮被它终结时发；
> CANCELLED 不发。本变更修改 R2 对象，须责任人重签本文件头部后实施；AI 未改头部。

### 方案（复用既有回调通道，零新增事件接线）

```text
guard_queue_frames 转译点（TIMEOUT/CANCELLED 命中处）
  └─ 先 await _notify(on_status, QueueStatus(rejected=code, …))，再 raise ProviderResponseError
       （顺序固定：通知先于抛出；CANCELLED 命中但不通知——用户主动中断）
wire 重试耗尽上抛处（FULL 最终异常）                    ← 开放项，见下
  └─ lazy import 定制回调 + 全吞错（模式同 client.py 既有接线）
两路共用：QueueStatus 扩展拒绝字段（rejected: str|None 原因码 / reject_message / trace_id，默认 None）
  → observer.on_queue_status（既有回调）→ GatewayQueueStatus 扩展同名字段（既有事件，
  headless 白名单不动）→ server.py 挂点 → queue_notify 第三种载荷
```

- 拒绝帧相位布尔 `released:False, rejected:True`（布尔对规范见协议规范 §3）；**可选携带最后已知
  `position`/`queueSize`**（guard 记住最后一个吸收的位置帧即可，协议规范「字段尽可能一致」条款）；
  放行帧是否补最后已知值由 v1.5 实施——规范标可选，iCode 默认不带（放行即横幅消失，旧值无展示价值）。

- `GatewayQueueStatus` 不另立新事件类：拒绝是排队状态的终态相位，同通道同白名单；
  TUI/CLI 不读新字段，行为不变（iCode 自身仍以普通错误呈现，拒绝文案只约束桌面端渲染）。
- **server.py 挂点 revisit v1.4 归属结论**：逐字段透传在字段增至 6+ 后行数反超，改为整体传
  `event`（`queue_status_payload(self, session_key, event)`）——R1「条件变化可 revisit」；
  此后载荷再加字段，上游挂点零变动。
- 拒绝帧不进 `(requestId, position)` 去重（无 position）；同 requestId 拒绝只发一次由
  发送侧"终态只经过一次"保证，`queue_notify` 对拒绝帧直接放行。

### 上游改动清单（R2，相对 v1.5 的增量）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/acp/server.py` | 挂点改为整体传 `event`（1 行改写，既有 marker 块内） | 1 行改写（0 净增） | 既有 `AIxCoding queue-progress: ACP notification`（计数仍 5） |
| wire 重试层（FULL 耗尽挂点，文件实施时定位：kernel wire retry / attempts 路径） | lazy import 定制回调 + 全吞错 | 约 +6 | `# AIxCoding queue-progress: report queue-full exhaustion` |
| `src/chrys/app/acp/doc/frontend-api.md` | 第三帧契约（排队/放行条目旁补拒绝条目） | 约 +6 | 既有 HTML 注释 marker（计数仍 1） |

**开放项（实施前须定稿）**：FULL 耗尽挂点的最小落点。TIMEOUT 的通知在 guard 转译处即完整；
FULL 在 guard 只见每次失败、不知是否最后一次，"最终上抛"发生在 wire 重试层——实施时定位，
若评估超出上表规模（>1 处上游接线或 >10 行），**停下上报责任人裁决**是否 FULL 延期
（规范已支持 FULL，iCode 暂只发 TIMEOUT，功能不受阻：FULL 耗尽本身极罕见——重试阶梯约 20 分钟）。

定制包改动（非 R2）：`queue_frames.py`（QueueStatus 扩展 + 转译点通知）、`queue_progress.py`
（事件扩展）、`queue_notify.py`（第三种载荷 + 传 event 后签名调整）、
`test_model_queue_progress.py`（新用例：通知先于抛出的顺序、拒绝载荷三字段、CANCELLED 不通知、
FULL 耗尽通知——破坏实验锚定挂点）。

### 对上游隐式行为的假设（增量）

13. wire 重试层最终上抛的是最后一个尝试的原始异常（QUEUE_FULL 的 bare `APIError` 带 `code`）
    → 依赖方式：耗尽挂点读该 code → 失效表现：FULL 通知缺失或误发；破坏实验锚定。
14. `_notify` 在 raise 前被 await 到完成（`bus.publish` 内联 await 订阅者）→ 失效表现：通知可能
    未送达异常已上抛——顺序由测试锚定。

### 风险与最坏情况

- 拒绝通知与 `chrys/error`/prompt 拒绝双通道并存：桌面端既出 rejected 横幅又出错误——消费策略
  归桌面端（规范 §5 已注明两通道职责）；不禁止。
- 现版桌面端丢拒绝帧（无 position 被排队校验拒绝，规范 §7 已注）：改造前的可见行为与现状等价，无回归。
- 通知顺序被破坏（先抛后通知）→ 超时无横幅：测试锚定；回滚删转译点 3 行。
- 回滚：撤销挂点改写与 FULL 挂点、定制包字段与载荷分支，即回 v1.5；无持久化。

### ADR 判定（增量）

四问均否：同通道载荷演进（复用既有 ADR `observer-callback-channel` 的决策范围），撤销代价低，
不新增上游非公开依赖（假设 13/14 均有测试锚定）。

### 验证计划（实施后执行）

- 新用例全绿 + `tests/app/acp` 回归（含 pin test）+ wait 清单刷新（转译点新增 await _notify）；
  ruff / ty / check_docs / gen_customizations --strict。
- 真实网关联调：超时场景（`max_wait_time` 调小）观察桌面端 rejected 横幅与文案。


---

## 变更单 v1.7（2026-11-25，责任人裁决）：相位布尔对合并为单字段 status（三态中文枚举）

> 决策来源：同事反馈 + 责任人裁决（2026-11-25）。`released`/`rejected` 两个布尔合并为一个
> `status` 字段，值为中文枚举 **「排队中」/「放行」/「拒绝」**（责任人 AskUserQuestion 三选一裁决；
> 备选英文 queued/released/rejected 被否）。协议规范升 v1.1（v1.0 已外发给同事）。

### 方案

仅线上映射层变化——内部模型（`QueueStatus`/`GatewayQueueStatus` 的 position/rejected 字段）不动：

| 位置 | 改什么 |
|---|---|
| `src/chrys/app/aixcoding/acp/queue_notify.py` | 载荷构造：两种布尔 → `"status": 常量`（`_STATUS_QUEUED/_RELEASED/_REJECTED` 中文常量） |
| `aixcoding/tests/llm/test_model_queue_progress.py` | 5 组 ACP 载荷断言改 status 形态 |
| `src/chrys/app/acp/doc/frontend-api.md` | 契约条目改 status 三态（同行改写，marker 不变） |

**`server.py` 零改动**（v1.6 整体传 event 的直接红利）；guard/事件/去重键/wait 清单均不动。

### 上游改动清单（R2，相对 v1.6 的增量）

| 文件 | 改什么 | 行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/acp/doc/frontend-api.md` | 契约条目：相位布尔对 → `status` 三态（中文值） | 约 +2/−2（同行改写） | 既有 HTML 注释 marker（计数 1，锚不变） |

### 风险与最坏情况

- 现版桌面端无 `status` 概念：排队帧仍走 position 分支正常显示；**放行帧被丢**（现版认 `released:true`）
  → 横幅随 prompt 结束消失而非即时消失——桌面端改造（本来就要做）消除。
- 中文枚举值：JSON UTF-8 串，无编码歧义（无标点，RUF001 不触发）；桌面端需中文→内部 phase 映射。
- 回滚：`queue_notify.py` 载荷构造改回布尔对即回 v1.6。

### 验证（2026-11-25 实施后，实测）

- `aixcoding/tests/llm/` 81 passed（5 组载荷断言改 status 后）；ruff/format、ty 三平台、check_docs、
  gen_customizations --strict 全绿；wait 清单无变化（无 await 改动）。
