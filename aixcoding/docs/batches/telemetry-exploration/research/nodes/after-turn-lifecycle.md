# N3：进程内 after_turn 公共生命周期

> 技术判断：正常主 Agent turn 的触发位置和 ACP 时序已由源码证实；运行组合仍需专项实验。
>
> 决策状态：**大方向已证可行；2026-11-17 接缝与 flush 专项已完成，AI 当前推荐 run-owned 身份快照 + N3-A direct finalizer + 进程级 reporter 按 session 隔离/flush。N3-B 留待真实多消费者场景；身份快照、per-session flush 目标和具体上游接缝仍需责任人裁决，本文不构成实施或 R2 批准。**
>
> 适用范围：N1-A/N1-B/N1-C 中所有需要事后分析、审计、缓存或本地投影的方向，不绑定独立 telemetry endpoint。

## 1. 要回答的问题

需要的不是另一套外部 hook 进程，而是一个进程内公共生命周期能力：

1. 在正确的持久化时点通知订阅者；
2. 允许轻量 registry/投影在 ACP 响应前就绪；
3. 不让 subscriber 普通异常改变 turn outcome；
4. 将重文件分析和网络投递移出关键路径，并有明确的退出 flush；
5. 明确保存失败、取消、retry、并发会话和进程退出的边界。

“发出生命周期通知”“分析完成”“网络投递完成”是三个不同保证，不能合并成一个含糊的 after_turn 已执行。

## 2. 已核实的正常时序

正常 fresh/retry 主 Agent 路径：

```text
executor pass 结束
  → terminal history / trajectory turn_finished
  → workspace baseline capture
  → recovery flush + session save 尝试
  → mutation summary + trajectory checkpoint
  → 外部 after_turn fire
  → turn-scope async hooks drain
  → successful-turn callback
  → turn_response_settled
  → run task 完成
  → ACP _run_turn 返回
  → PromptResponse 构造
```

主要证据：

- `src/chrys/orchestration/engine/run/finalizer.py:88-171,372-433`：finalizer、保存/checkpoint、after_turn、drain 和 response fence；
- `src/chrys/orchestration/session_host.py:642-650`：等待 run task 完成后才解析最终 outcome；
- `src/chrys/app/acp/server.py:593-627`：事件流和 `_run_turn` 完成后才构造 PromptResponse。

因此，在 `finalizer.py` 的 `_record_trajectory_after_save()` 之后、外部 `fire_after_turn()` 之前增加受 `await` 的轻量内部通知，即可保证正常 ACP 响应前完成通知入队。**N3 本身不需要修改 ACP server；N7 因最终响应主动携带 requestId 仍需独立输出接缝，但当前从 prompt_lock 内 live-history 选 A2，不依赖 after_turn registry。**

## 3. 不能忽略的既有边界

- `save_current_session()` 返回 `False` 后，当前代码仍继续 checkpoint 和 after_turn；“save 已尝试”不等于“本轮文件已更新”。内部事件必须携带 `saved`，分析器不得把旧文件当成本轮新数据。
- shutdown 强制取消落在 turn close/baseline capture 时，当前分支仍保存和 checkpoint，但跳过 after_turn/drain；崩溃、强杀也不产生本保证。
- 普通 ACP 用户取消通常作为 interrupted outcome 走正常 finalizer，不能与强制取消 run task 混为一谈。
- 外部 blocking hook 会推迟响应；async hook 通过 `drain_turn()` 也会推迟响应；`fire_and_forget` 不受 turn/session drain 保证。
- 普通 hook 子进程失败和超时不改变 turn outcome，但整个 HookManager/finalizer 基础设施调用链并非绝对异常屏障。
- 当前 finalizer 覆盖主 Agent turn；workflow、side question、sub-agent 不能因使用该接缝就被隐式宣称全部覆盖。
- 当前 `session_end` 只是每 session 一次的外部 hook 时点，不会自动执行 telemetry 分析。hook 可以读取仍存在的 session 文件，但 shutdown 顺序是 session_end/drain → trailing save → trajectory close，因此它不能保证看到 trailing save 的最终状态，不能替代逐 turn after_turn 主分析。当前方案只将其对应 lifecycle 时点用于有界 flush，**明确不做最终补扫**。

证据：`finalizer.py:118-169`、`service/hooks/runner.py:169-240`、`service/hooks/manager.py` 的 dispatch/drain 实现及既有 finalizer/hook 测试；`orchestration/engine/session_lifecycle.py:400-423,750-839` 固定 session_end 和 trailing save/close 顺序。上述为静态语义，取消矩阵仍需运行实验。

## 4. 触发机制分支

| 分支 | 工作方式 | 技术判断 | 决策状态 | 评价 |
|---|---|---|---|---|
| **N3-A 直接 finalizer 回调** | 在保存/checkpoint 后直接 await 定制 analyzer/dispatcher | 接缝已静态证实 | 最小 fork 过渡候选 | 触发点只碰 `finalizer.py`；完整身份还需第14节的 run-owned 快照，不是通用公共 API |
| **N3-B EventBus 生命周期事件** | 新增内部 `AfterTurn`，复用现有 per-host bus 的 inline subscribe；另补 `SessionEnded` | 现有传输机制已证实，事件与发布点待实现 | **长期建议；也可作为通用 fork 过渡** | 不另造 subscriber 框架；比直接回调多事件类型定义，session_end 另接 lifecycle |
| **N3-C 扩展 HookManager 支持内部 hook** | 将内部 subscriber 混入外部脚本 hook 管理 | 可做但语义混杂 | 不建议 | 外部进程配置、UI 报告和 drain 概念不等于通用生命周期；无 hooks/early return 也易造成遗漏 |
| **N3-D 复用现有其他机制代替** | `SessionSaved`、successful callback、Python extension 或 stream | 均缺少必要语义 | 排除为唯一触发点 | 分别存在时点过早、仅成功、无 after_turn 能力或只入队不就绪的问题 |
| **N3-E 外部 after_turn 子进程** | 沿用用户脚本 hooks | 已证不满足进程内约束 | 排除为本需求主路线 | 保留给用户扩展，不承担内部分析 |

### 为什么优先 EventBus

`src/chrys/foundation/events/bus.py:29-91` 已提供：

- `subscribe()` 注册 async callback；
- `publish()` 内联逐个 `await` callback，可形成明确的响应前背压；
- 默认捕获普通 `Exception`、记录并继续其他 subscriber；`raise_handler_errors=False` 时不向发布者传播普通异常；
- `unsubscribe()` 生命周期管理。

需要补的是生命周期事件类型、发布点、进程级 owner 和自定义队列 flush，而不是第二个 EventBus。`stream()` 只负责 `put_nowait`，不能保证 publish 返回时消费者已完成处理，不能替代 inline registry 更新。

## 5. 通知、分析和投递应分层

### 第一层：受 await 的轻量同步准备

inline callback 只做：

- 读取事件携带的稳定身份和不可变快照；
- 更新内存 registry；
- 将后续工作放入 subscriber 自有队列。

`await publish()` 返回只表示这些轻量动作完成，不表示文件分析或网络上报完成。普通 subscriber 异常必须隔离，`CancelledError` 不得吞掉。

### 第二层：有界同步准备（按消费契约选择）

如果 N7 最终选择“PromptResponse 必须携带本轮分析得到的 request/span”，则响应前必须完成相应分析或另由事件载荷直接提供这些 ID：

- 可采用有界等待，必要时将文件分析移到 worker thread；
- 会推迟 PromptResponse，必须测量并定义超时/降级；
- 超时后只能省略/标记 pending，不能读取旧 turn registry 冒充本轮。

这与“完全后台、不阻塞响应”不能同时无条件保证，需由 N7 消费契约决定。

### 第三层：后台重分析和网络投递

- 文件全量分析、报文构造和网络 I/O 在 subscriber 自有 worker 中执行；
- 不在 inline callback 中等待网络；
- 后台执行只能保证已入队，不能保证 ACP 响应前分析完成；
- 队列和 worker 需要显式 session/process owner、正常关闭和有界 flush，不能借用 fire-and-forget 的语义推断自动完成。

## 6. 通用事件契约候选

以下是方案建议，不是现有 API。

### `AfterTurn`

至少提供：

- `session_id`；
- `logical_turn_id` 与独立的 `pass_id`，retry 时不得混用；
- `turn_number`、`is_retry`；
- `status = ok | interrupted | failed` 及兼容现有语义的 `failed`；
- `saved: bool`；
- 可选稳定 checkpoint/session 定位信息，不传大型 live state。

trajectory disabled 时应由第14节的 run-owned 快照提供 pass/logical ID，不能从 `finished_turn_context()` 一定存在反推；快照缺失才显式 skip，禁止 latest 回退。

### `SessionEnded`

至少提供：

- `session_id`；
- 受限的结束原因；
- 防重复身份或现有每 session 一次的触发保证。

subscriber 自己执行有界 flush，core 不理解 telemetry 报文。内部 session_end 发布不能藏在外部 `hook_manager is None` 的 early return 后。

## 7. 并发、顺序与所有权

- ACP 同 session 有 turn 互斥和 prompt lock，但不同 session 可并发；EventBus 默认是 per-host，不是进程级全局串行 bus。
- registry 至少按 `session_id + logical_turn_id + pass_id` 隔离，后续 exchange/tool 键继续向下扩展；禁止 session-latest 猜测。
- 进程级共享 registry/reporter 需要自己的所有权、队列或锁，不能依赖 HookManager 的 per-session semaphore。
- N8 的 LLM→tool→ai-code 有序 best-effort 由 reporter/worker 保证，N3 只负责可靠交付生命周期通知，不把二者合并。
- session/process close 必须幂等；正常 EOF、session switch/delete 和 CLI run 的自定义队列 flush 需要专项验证。

## 8. fork 与上游接触面候选

### 最小 N3-A 触发点

- `src/chrys/orchestration/engine/run/finalizer.py`：保存/checkpoint 后调用定制 dispatcher，并传入 `failed/saved/session/turn` 等身份。

不需要仅为触发时序修改 `acp/server.py` 或 coordinator。后续身份复核确认完整 logical/pass 仍需 runner/runtime 快照，不能由本节的单文件触发点代替；完整清单见第14节。

### 通用 N3-B

- `src/chrys/foundation/events/types.py`：定义通用生命周期事件；
- `src/chrys/orchestration/engine/run/finalizer.py`：复用已有 `_bus` 发布 `AfterTurn`；
- 若同期覆盖退出：`src/chrys/orchestration/engine/session_lifecycle.py` 发布 `SessionEnded` 并接入有界 drain；
- 完整身份同样复用第14节的 run-owned 快照；EventBus 只替代通知传输，不替代身份来源。

优先复用 finalizer 已有 `_bus`，避免为新增 subscriber 构造参数再改 coordinator/assembly。以上都是后续实施批次的 R2 候选，当前未修改、未授权。

## 9. 大方向结论与暂缓事项

大方向只需要以下已证实前提：保存/checkpoint 后存在进程内接缝；直接回调和 EventBus 都能承载通知；正常 ACP 响应前可以完成受 await 的轻量处理。因此 N3 不再阻塞当前方案探索。

以下事项均不影响“能否工作”，留到具体实施时分析：

1. N3-A 直接 finalizer 回调或 N3-B EventBus 公共事件：只是耦合适用面、通用性和接缝数量差异，不改变触发时序与数据可得性。
2. 轻量同步、完整分析同步或后台执行：当前需求允许 after_turn 非实时上报，不影响独立 LLM 报告、工具和 ai-code 的工作能力。只有 N7 若要求 PromptResponse 同步携带分析结果时才影响该消费契约，届时再评估有界等待。
3. `saved=False`、强制取消、并发和正常退出 flush：属于失败语义、数据完整性和可靠性实现，不改变正常路径可行性；按已确认 best-effort 和无崩溃补报边界处理。
4. N3-E1–E6 是实施期行为验证，不作为当前大方向的待裁决前置条件。

## 10. 后续实施判别实验

| 实验 | 判别标准 | 当前状态 |
|---|---|---|
| N3-E1 正常/retry/失败/用户取消 | 内部通知在真实 ACP PromptResponse 前完成轻量 registry 更新，pass/logical ID 正确 | 待实验 |
| N3-E2 save=False | 不读取旧 session 冒充本轮；事件和分析降级符合契约 | 待实验 |
| N3-E3 强制取消矩阵 | 明确 save、内部通知、外部 hook、drain、response fence 各取消点的实际保证 | 待实验 |
| N3-E4 两 session 并发 | registry 不串键，reporter 不依赖 per-host bus 提供全局串行 | 待实验 |
| N3-E5 EOF/switch/delete/CLI 退出 | 自定义 worker 有界 flush，close 幂等，无 fire-and-forget 误假设 | 待实验 |
| N3-E6 性能与同步准备 | 测量轻量入队和完整文件分析耗时，为 N7 选择有界等待或后台降级提供数据 | 待实验 |

实验只能使用定制目录中的新增代码或现有上游测试，不得借探索修改未获 R2 批准的上游文件。

## 11. 证据入口

- 总图：`../solution-space.md`
- 上报通道：`llm-report-transport.md`
- ACP/文件能力：`../capability-matrix.md`
- 上游通用建议：`../upstream-proposals.md`
- 现有行为测试：`tests/orchestration/engine/run/test_finalizer.py`、`tests/service/hooks/test_manager.py`、`tests/foundation/events/test_bus.py`、`tests/orchestration/engine/test_shutdown_close.py`

## 12. 2026-11-17 接缝与 flush 专项调查

### 12.1 N3-A/N3-B 的实际接触面

**AI 当前推荐 N3-A direct finalizer，仍属方案建议，不是实施或 R2 批准。**推荐依据不是 EventBus 不能工作，而是内置 telemetry 自动生效时两者的完整接缝不同：

| 项目 | N3-A direct finalizer | N3-B EventBus |
|---|---|---|
| 正常发布点 | `finalizer._save_and_drain_hooks()` checkpoint 后直接 await 定制 dispatcher | 同一位置 publish 新的 `AfterTurn` |
| 新事件类型 | 不需要 | `foundation/events/types.py` 增加通用事件 |
| 自动订阅 owner | dispatcher 自行持有，无构造器注入 | 内置默认启用还需 engine/host 集中注册或各入口注册 |
| EventBus 实现 | 不使用 | 无需修改，现有 inline subscribe/publish 可复用 |
| 后台 flush | 与传输机制无关，仍需显式 owner | 同左，AfterTurn 本身不提供 flush |
| 适用条件 | 当前单一消费方；完整身份使用run-owned快照 | 确有多个内部消费者/公共生命周期 API 需求 |

N3-A 在 finalizer 内 lazy import、dispatcher 自持有 worker且不通过构造器注入时，通知调用本身只需碰 `finalizer.py`；完整生产接缝还包括身份快照和 lifecycle，见第14节。构造器注入会扩散到 coordinator/assembly/session host/ACP/TUI。N3-B 不需要改 `bus.py`，但“定义事件”与“telemetry 默认订阅并 flush”合计通常比 N3-A 多接缝。

EventBus 默认逐个 await，普通 Exception 记录后继续且不向发布者传播；`CancelledError` 会传播并中断后续 handler/stream。N3-A 也必须只隔离普通异常，不能吞取消。`stream()` 入队不等于消费者处理完成。

### 12.2 身份完整性是独立限制

finalizer 可直接取得 session、status、saved、profile、cwd 和 live workspace；`saved` 必须在 `_save_and_drain_hooks()` 局部传递，不能只靠外层 degraded 恢复。status 保持现有 `failed` 优先于 `interrupted` 的顺序。

本节早先曾建议 trajectory disabled 时仅提供 optional 身份并跳过；2026-11-17 后续源码复核已取代该建议。runner 在调用 recorder 之前就独立生成 pass ID、确定并注册 logical turn ID，因此缺口是“身份没有交给 finalizer”，不是“只有 trajectory 才能生成身份”。完整结论和第 14 节的最小 run-owned 快照路线以新复核为准。

`TurnStarted` 只有 logical ID，没有 pass ID；finalizer 直接读 `TrajectoryRecorder.current_turn` 又会在 disabled/activation 失败时缺失。因此不能宣称只改 finalizer 即可覆盖所有配置，也不能用 latest `TurnRecord` 猜测当前轮。N7 锁内 live-history 不依赖本通知或 registry。

### 12.3 flush 的正确语义：排空已生成报文，不做关闭时最终分析

本轮最重要的简化是：**逐 turn after_turn 已完成分析和入队后，session 结束只需排空既有队列，不需要读取 trailing save 或 trajectory close 后的文件。**因此“session_end 早于 trailing save”不妨碍它作为 flush 时点，只是它不能替代逐 turn 分析，也不支持可选最终补扫。

当前不采用关闭时最终补扫，故无需为等待 trajectory close 增加语义。若未来新增 trailing-save 分析，才是另一项需求，不能倒推当前 flush 必须晚于 trajectory close。

外部 `session_end`/HookManager 仍不能直接复用为机制：无 hooks 时 manager 不存在，`fire_session_end_hooks()` 会 early return；drain 只管理用户 hook，不知道定制 worker。需要 per-session flush 时，必须有独立于 hooks 的内部调用。

### 12.4 场景矩阵

| 场景 | 现有路径 | 对“排空既有队列”的判断 |
|---|---|---|
| ACP EOF/连接断开 | connection close → manager shutdown → 每 session host shutdown | 可在 session teardown 做有界 flush；进程最外层只能作补偿 |
| ACP close/delete | ManagedSession.shutdown → host teardown；active delete 后物理删除 | 需要在删除前完成对应 session flush；delete 后不能再读目录 |
| ACP new/load | 多 session 并存，不隐式关闭旧 session | 不能把 ACP“切换”当 flush 边界；以 close/delete/EOF 为准 |
| TUI new/restore | 旧 session teardown → 新 session start | 仅进程退出 flush 会推迟旧 session 投递，不适合及时 per-session flush |
| TUI active clear/delete | session_end → trajectory close → detach/delete/deactivate | flush 必须在 detach/delete 前；删除失败会 rearm，session 继续，flush 不得不可逆关闭其后续投递能力 |
| TUI 正常退出 | on_unmount → engine.shutdown | 正常 teardown 可 flush；前序异常仍可能跳过后续步骤 |
| headless 成功/失败 | run_command finally → host.shutdown | 已构造 host 的正常清理可 flush；构造前失败通常没有本轮队列 |
| 强制取消/崩溃/强杀 | 可能跳过 after_turn或后续 teardown | 不承诺 flush，不做启动扫描补报 |

### 12.5 是否必须改 session_lifecycle.py

- **只做进程最终 flush**：可在 ACP `app/cli/acp.py`、TUI `app/tui/app.py`、headless `app/cli/run.py` 的最外层 finally 实现，不必改 lifecycle；但这是三个应用入口，且漏掉 TUI switch 和 ACP 单 session close/delete 的及时 flush。
- **要求 per-session 正常结束及时 flush**：推荐统一 lifecycle 语义，通常比三个入口更少且覆盖完整。正常 `_teardown()` 和 active `_delete_session_reporting()` 都要覆盖；删除失败要求 flush 幂等、worker 可继续使用。
- **在 TrajectoryRecorder 加 on_closed**：可避开 lifecycle 文件，但仍新增上游接缝并把无关遥测生命周期挂到 trajectory 层，且当前无需等待 trailing close，不推荐。
- **只挂 HookManager/session_end 外部 hook**：无 hooks 时失效，排除。

所以 session_lifecycle 不是任何 flush 的必改文件，但**在当前“逐 session 有界 flush”目标下是较小且语义更直接的候选**。这只是调查结论，未批准任何上游改动。

### 12.6 owner 与当前推荐组合

推荐一个**进程级 reporter owner，按 session 键隔离队列和 flush**，而不是依赖每个 per-host EventBus 提供全局串行或隐式 worker。每 session 内保持 LLM→tool-detail→ai-code，跨 session 可并发；session teardown 只 flush/close 对应 session 的 worker，不销毁整个进程 owner。active delete 失败后再次入队必须可重建 worker，正常 close 幂等。

当前 AI 建议组合为：run-owned 身份快照 + N3-A direct finalizer + 进程级 reporter owner + per-session 有界 flush；不新增 EventBus/SessionEnded 公共事件，不做 trailing-save 最终补扫。是否接受身份快照、per-session flush 目标及具体 lifecycle 接缝，仍需责任人讨论裁决。

### 12.7 本轮行为证据

执行现有 EventBus、finalizer、session lifecycle close/shutdown、runtime metadata active delete、ACP session manager/transport、headless run 和 TUI startup 九组测试，共 **241 passed in 14.53s**。这证明现有行为锚点稳定，不证明新增 dispatcher、worker 或 flush 已实现。后续组合实验仍需覆盖 trajectory enabled/disabled 身份、save=False、取消、并发、无 hooks、删除失败后续用和 flush 超时。

## 13. 2026-11-17 性能与通知契约复核

新增 `../performance-and-lifecycle.md`。30轮真实文件基准中，全量与expected-turn reader均约7→38ms线性增长，证明expected-turn裁剪报文并不等于增量I/O；正常路线应只处理显式当前轮，不做启动历史回放。2026-11-19 F2 裁决后，普通通知按session/logical turn/pass合并同pass重复，新pass不得被吞；后端记录级幂等是第二道防线。1001仍按logical turn一条。不为已排除的崩溃补报引入持久化高水位；文件offset仅是可丢失的性能缓存。

当前真实 `turn_hooks.py` payload 不含稳定turnId/saved，且无hooks时early return；生产finalizer dispatcher必须显式补身份和保存结果。test-local per-session queue已验证FIFO、跨session并发、有界flush和幂等close，但engine不会自动追踪该worker，TUI/ACP/delete的真实flush仍需实施design/R2，不能写成已完成。

## 14. 2026-11-17 稳定身份与最小 R2 接缝复核

### 14.1 关键结论：需要传递已有身份，不需要借 latest 重建

`runner._record_trajectory_turn_started()` 在 `await recorder.turn_started()` 之前完成以下动作：生成 `pass_id`、选择或新建 logical turn ID、写 `TurnRecord`；随后才尝试激活 trajectory 并发布 `TurnStarted`。因此 trajectory disabled/activation 失败不会抹掉 runner 已确定的身份。当前真正缺口只是 finalizer 没有收到这组值。

最小可靠路线是让 `TurnRuntimeState` 持有本次 run 的不可变身份快照，由 runner 在 recorder 调用前一次性写入，finalizer 只读取该快照。快照至少包含 `logical_turn_id + pass_id + turn_number + is_retry`。reader 同时以 logical ID 和 pass ID 界定当前执行：logical ID 用于 turn/span 归属，pass ID 用于区分 retry 新执行并与 trajectory 交叉校验；两者不得互换。为关联当前执行而读取前序来源不属于重报，retry 中只重放或继承的历史内容不得再次形成执行记录。`TurnRecord` 只用于按该 ID 验证持久化记录，禁止取 latest 冒充当前轮。

| 场景 | 可靠来源与处理 |
|---|---|
| 正常 fresh | runner 快照中 logical=pass；finalizer 在 save/checkpoint 后读取同一快照 |
| retry 有 resumed turn | logical 保持原值，pass 新生成；不能用 `logical != pass` 之外的信息反推其他语义 |
| retry 无 resumed turn | runner 新建 logical=pass 的 turn；不能按数值 turn 或 latest 猜测 |
| trajectory disabled/activation 失败 | recorder 可没有 `_turn`，但 runner 快照仍有完整 logical/pass；不依赖 `current_turn` |
| pre_run 在身份分配前失败/取消 | 公共 run 路径通常直接传播而不进入普通 after_turn；即使 finalizer 被直接调用，空快照也必须 skip，不能沿用上一轮 |
| 身份分配后、普通 finalizer 前发生 admission failure | 快照对应当前 run；仍由 saved/status 决定可读范围 |
| save=False | 正常 `_save_and_drain_hooks()` 仍可到 dispatcher，但必须携带 `saved=False` 并直接 skip，不读取旧 session |
| 强制取消落在 turn close/baseline capture | 现有分支保存/checkpoint 后跳过外部 after_turn；本最小方案不擅自扩大为必通知 |

`pre_run()` 开始还应先清空旧快照，避免任何异常路径把上一轮身份留给本轮；session shutdown 的既有 `reset_after_session_shutdown()` 同步清理。身份缺失是显式降级，不是回退到 session-latest 的理由。

### 14.2 推荐通知契约

继续采用 **N3-A direct finalizer dispatcher**。在 `_save_and_drain_hooks()` 的 save/checkpoint 后、外部 hooks 前构造不可变通知；不依赖 HookManager 是否存在。通知复用现有 `session_id/profile/cwd/status` 上下文，并补：

- `session_dir`（或等价的持久化目录定位）、`logical_turn_id`、`pass_id`；
- runner 实际采用的 `turn_number`、`is_retry`，不重新读取可能漂移的数值计数；
- `saved: bool`；status 保持现有 failed 优先于 interrupted 的顺序。

dispatcher 的同步关键路径只校验快照、按 `(session_id, logical_turn_id, pass_id)` 合并同 pass 重复通知并 `put_nowait`；不同 pass 在首任务 pending/running/completed 时均不得静默丢弃。文件分析和网络 I/O 留在 per-session worker。`saved=False` 或身份快照为空时直接记录并跳过。普通异常在定制边界隔离并记录，`CancelledError` 不吞。该通知只保证已入队，不保证 ACP 响应前已分析或已上报；N7 仍走独立的响应时 live-history 路线。

2026-11-19 F1/F2 裁决补充：reader 须区分当前 pass 新执行、关联所需前序来源和 retry 纯重放/继承内容，按原始执行身份上报，不得每 pass 重报整个 logical turn。selected Agent 1001 仍按 `(session_id,logical_turn_id)` 去重一条，跨 pass 稳定选择首个成功主模型 A，不改用最后 A2。异步读取以记录级事实一致和关联正确为目标，不预设全局原子快照；V1/V2 必须覆盖延迟读取、下一轮保存、回滚及新 pass 通知，缺失显式记录并交责任人裁决降级是否足够。

### 14.3 集中 owner 可以覆盖 TUI/ACP/delete/EOF，无需逐入口接线

推荐一个进程级 owner，管理按 session 隔离的 queue/worker；每 session 内 FIFO，跨 session 可并发。最小生命周期语义是：

1. 正常 `_teardown()` 等待 run task 终结后，对当前 session 做有界 flush，再关闭并移除该 session 的 worker；超时记录并丢弃/取消该 session 剩余工作，不阻塞整个进程。
2. TUI active `_delete_session_reporting()` 在 trajectory close/detach/物理删除前执行同一 flush+session close；删除失败后，后续 after_turn 可重新创建 session worker。
3. ACP close/delete/EOF、TUI new/restore/clear 和 headless 正常退出均最终经过上述集中路径；inactive ACP delete 不应还有未关闭的 session worker，因为此前 teardown 已关闭它。
4. flush 只处理已由逐 turn 通知产生的任务，不做 trailing-save 最终补扫；强杀、崩溃和被跳过的强制取消仍不在保证范围。

“关闭 session worker”不等于关闭整个进程 owner。若实施改用需要事件循环内显式关闭的进程共享 HTTP client/其他异步资源，则还必须增加应用最外层 close 接缝；这不是当前最小方案默认包含的改动。

### 14.4 最小 R2 候选清单

以下仅为后续实施 design 的候选，不是 R2 批准；行数是量级估计，正式实施需附 marker 和登记预告。

| 上游文件 | 函数/区域 | 候选改动 | 大致量级 |
|---|---|---|---:|
| `run/turn_state.py` | `TurnRuntimeState`、`reset_after_session_shutdown()` | 增加通用 run-owned 不可变身份快照及清理；不为 telemetry 增加业务字段 | 15–25 行 |
| `run/runner.py` | `pre_run()`、`_record_trajectory_turn_started()` | pre_run 开始清旧值；ID 确定后、recorder await 前一次性写入 logical/pass/turn_number/is_retry | 10–18 行 |
| `run/finalizer.py` | `_save_and_drain_hooks()`，必要时一个小 helper | save/checkpoint 后构造通知并 lazy 调定制 dispatcher，显式传 saved/status；不改现有外部 hook 语义 | 18–30 行 |
| `engine/session_lifecycle.py` | `_teardown()`、`_delete_session_reporting()` | 集中调用定制 per-session 有界 flush+close；active delete 位于 close/detach 前 | 12–24 行 |

定制新增代码放在 ADR-0011 允许的 `src/chrys/*/aixcoding/` 产品层，包括不可变通知、reader/reporter/owner 和队列实现；开发资产与实验仍放根 `aixcoding/`。这些新增文件本身不是上游 R2，但必须随实施 design 列明。

最小路线**不需要**修改 `turn_hooks.py`、EventBus、ACP `server.py/session_manager.py`、TUI app 或 headless entry。`app/acp/server.py` 仍因 N7 最终响应 `_meta` 单独存在上游接缝，不能与本次 after_turn 清单混算。

### 14.5 备选与路线重评条件

- **只改 finalizer+lifecycle，trajectory disabled 时 skip**：上游更少，但产生已知配置性缺报；除非责任人明确接受该缺口，否则不推荐。
- **N3-B EventBus**：适合已有多个内部消费者或决定提供公共生命周期 API 时；当前单一 telemetry 消费方下会增加事件类型和默认订阅 owner，不是最小路线。
- 若要求 pre_run 取消、强制取消或每次保存都必须通知，当前单一 `_save_and_drain_hooks()` 接缝不足，需要重新设计取消路径，而不是从 latest 文件补猜。
- 若需求改为崩溃补报、持久化 exactly-once 或跨重启 ACK，当前无持久化高水位的 best-effort 设计失效，必须重评整个 owner/存储路线。
- 若无法接受 run-owned 身份快照，则 trajectory disabled 下无法保证完整 expected turn；应明确降级或重评 after_turn 文件分析路线，不能隐藏该限制。

本轮结论是：**集中取得稳定 expected turn 的路线成立，after_turn 文件分析主路线无需推翻；代价是从“只改 finalizer”修正为四个上游文件的最小集中接缝。**仍未授权任何上游实施。
