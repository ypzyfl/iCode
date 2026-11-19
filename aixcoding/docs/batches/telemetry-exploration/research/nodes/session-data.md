# N4：整个 session 目录的数据覆盖

> 技术判断：**大方向条件可行，不阻塞当前路线。**正常 SessionHost/ACP、session 保存成功且 trajectory/mutation 正常持久化时，整个 session 目录足以支撑 LLM 独立报告、工具关联和 write/edit ai-code 的主要输入。
>
> 决策状态：采用“整个 session 目录联读”作为当前数据基础；trajectory 降级、blob 缺失和逐字段报文一致性属于实施期降级与验证，不要求责任人现在裁决。

## 1. 大方向需要证明什么

N4 不讨论游标、幂等、报文切块或完整 golden parity，只回答：

1. after_turn 时能否取得本轮 exchange/pass/attempt 和模型 outcome；
2. 工具能否精确关联产生它的 exchange；
3. write/edit 能否取得逐次 before/after 和工具参数；
4. 上述数据是否依赖非常规 opt-in；
5. 数据缺失时是能够检测并降级，还是会让正常路径普遍失效。

结论是：**三类数据必须联读，不能只读 `session.json`，也不能只读 `events.jsonl`。**

```text
session.json
  → session/消息/工具参数与结果/provider call_id/稳定 operation ID/mutation ledger

trajectory/events.jsonl
  → pass/logical turn/exchange 生命周期/全部 attempts/工具 parent exchange/状态与时间

chrys_mutations + mutations/<sha256>
  → 逐次文件 before/after 内容引用与实际 blob
```

## 2. 实际数据来源

| 所需事实 | 主要来源 | 大方向判断 |
|---|---|---|
| 完整 session ID | `session.json.meta.session_id`、event envelope | 可取得 |
| logical turn / pass / retry | trajectory `turn.started` 和事件顶层 `turn_id` | 可取得；session registry 不能独立恢复全部 retry pass |
| exchange ID | trajectory `model.exchange.*.operation_id`；成功 assistant message 的 `_chrys_operation_id` | 可取得 |
| exchange 开始/结束、outcome、usage、timing | trajectory `model.exchange.started/finished` | 正常记录时可取得 |
| 全部 HTTP attempts | trajectory `model.request.*` | 可取得；session 只保留最终响应 attempt |
| 工具名称、参数、provider call_id、结果 | session `function_call/function_result` | 可取得；trajectory 有意不保存原始参数/结果正文 |
| 工具 operation ID | call/result 的 `_chrys_operation_id`、tool operation events | 可取得，不依赖 trajectory 写成功才生成 |
| 工具 parent exchange | `tool.operation.started.parent_model_operation_id` / `parent_operation_id` | trajectory 正常时精确关联 |
| 工具状态与时间 | tool operation events；result timing/execution stamp 可辅助 | 主要输入可取得 |
| 文件逐次 before/after | `session.json.state.chrys_mutations` 的 hash/skip/tool_operation_id + `mutations/` blob | 正常文本且 blob 可用时可取得 |
| 文件修改所属 exchange | PR #69 新增的 mutation.tool_operation_id → tool operation → parent exchange | 可关联；旧 mutation.tool_call_id 是独立 12hex UI ID，不是桥；PR 前记录降级 |

可复用现有 `service/analytics/turn_trace.py` 的只读投影，不需要重新发明 logical turn→pass→exchange→attempt 的关联模型。

## 3. 默认装配与 after_turn 可读性

当前 0.35.2 正常 SessionHost/ACP 路径：

- 默认创建文件 StateStore；
- 有 session_dir 时自动创建 MutationTracker/SnapshotStore；
- trajectory 绑定同一 session_dir，首个事件懒激活；
- 未发现常规 `trajectory.enabled` 或 mutation ledger/blob 用户总开关。

因此该路线**不依赖要求用户额外打开诊断功能**。无 session_dir/state store、保存被抑制或底层 I/O 失败时自然没有完整文件，这是明确的部署/故障边界。

`events.jsonl` 是 write-through；checkpoint 写标记并 fsync，reader 可在 writer 尚未关闭时读取完整行。Windows secure open 允许读/写/delete share。故“必须等 engine/session 关闭才能读 trajectory”不成立。after_turn 位于 save 尝试和 checkpoint 后，与这些数据时点匹配。

注意：`after_turn` 不等于本轮 `session.json` 保存成功；save=False 时不能把旧文件当成本轮事实。

`session_end` 时点文件仍存在，但当前上游只是提供 hook，不会自动执行 telemetry 分析。shutdown 中它早于 trailing save 和 trajectory close；当前路线只把它作为有界 flush 时点，**明确不做关闭时最终补扫**，也不把它描述成比 after_turn 更“最终”的完整保存后时点。

## 4. 正常、失败、取消和 retry

| 场景 | 数据覆盖 |
|---|---|
| 正常完成 | exchange、assistant、工具 parent 和 mutation 可完整关联 |
| LLM 失败 | 依赖 trajectory started/finished；通常没有 assistant message 可携带 exchange ID |
| 用户取消 | provider acquisition 已开始时可由 exchange terminal 关联；尚未开始的调用没有 exchange 是正常语义 |
| SDK retry / redirect | 同一 exchange，多 attempt |
| Chrys wire retry | 新 exchange，可由 retry 事件关联 |
| 用户 retry | 有 resumed 记录时新 pass、同一 logical turn；无 resumed 记录时会新开 logical turn。完整历史依赖 trajectory，reader 还需 archive 去重 |
| 同 turn 同文件多次编辑 | mutation hash 链保留每次中间 before/after |

这些场景的具体 after_turn 组合样本可在实施时验证；现有源码和测试已足以排除“文件模型本身无法表达”的方向性疑虑。

## 5. trajectory 降级不是正常路径阻断项

trajectory 可能因 lease、权限、fingerprint key、只读文件系统、schema/tail 等激活失败，也可能写 ack 超时、事件超预算落入 gap 或出现 torn tail。

此时：

- 成功 assistant message 通常仍有 exchange ID；
- 工具 call/result 通常仍有 tool operation ID；
- 可通过“包含 function_call 的 assistant message”做一层降级关联；
- 但无法保证恢复失败 exchange、全部 attempts、完整 pass 历史及独立 `parent_model_operation_id`。

因此不能把 transcript fallback 宣称为完整替代。正确边界是：

```text
首选：tool operation event → parent_model_operation_id E → 对应 assistant M 的 A-final
降级：function_call 所在 assistant message → 该消息的 E/A-final
无法确定：unknown/省略，不按消息顺序或 session-latest 猜测
```

这是可检测的覆盖率降级，不推翻 trajectory 正常时的主路线。

## 6. write/edit ai-code 的输入覆盖

已静态证实具备以下重建输入：

- `write_file` 创建：before 不存在，after 为完整 blob；
- overwrite：before/after 两个 blob；
- edit 单次替换和 `replace_all`：逐次整体 before/after + 工具参数；
- 同 turn 多次编辑：hash 链保留中间状态；
- 审批 modified_args 写回 function_call；
- 其他 hook 的最终参数通常有 `_exec_stamp.effective_args`，但存在 2048 字符截断边界。

`read_file` 没有 mutation before/after，只能恢复参数和持久化结果。旧 ai-code 本身针对 write/edit，因此这不是旧 ai-code 重建的方向性缺口，也不能把 read_file 描述成有文件快照。

blob 以 SHA-256 去重；清理会计算引用。rollback/clear/delete 后不能假设历史内容仍存在。默认单文件 50 MiB、默认跳过二进制，另有 unreadable/too_large/binary 等 skip 状态。

**blob 缺失、policy skip、不可读或写盘失败时，ai-code 内容必须降级/省略；不得读取当前工作区文件冒充历史，也不得把“不存在/空文件”和“blob 缺失”都当成空字符串。**

## 7. 哪些事项不影响当前大方向

以下均留到 N5/N6 或实施阶段，不需要现在裁决：

- 旧 tool-detail/ai-code 报文逐字段一致和 golden parity；
- 参数截断后的具体降级字段；
- 取消 outcome 到旧后台状态的映射；
- torn tail、缺事件、rollback 等完整样本矩阵；
- 增量游标、幂等和重复分析；
- after_turn 当时的一体化端到端性能测试。

N4 只证明主要输入和关联链存在，不宣称这些工作已经完成。

## 8. N4 不覆盖的其他数据

本节点不证明以下事实可从 session 目录恢复：

- desktop envelope、selected Agent、channel/version 等 ACP 输入；
- 事件时 workspace/Git；
- 全部技能使用语义；
- 外部 ACP 子代理内部过程。

这些分别属于 N5/N7/N9，需要运行时补采或降级，不能反过来扩大 N4 的结论。

## 9. 结论

**继续采用整个 session 目录作为当前数据基础。**正常路径没有发现需要推翻 A-final 当前路线、恢复旧式实时 EventBus 全挂点或增加模型 body telemetry 的缺口；C1 exchange header 仅是开发期回退分支。

trajectory 与 mutation 默认装配、主关联键稳定、write/edit 输入齐全；缺失和故障可检测并降级。2026-11-17 定制 file-only reader 已覆盖正常两轮、gap/blob 降级、fork 零重报和 save=False expected-turn 守卫；compaction×真实 engine、完整 golden parity 和组合报文留实施，当前证据详见 `../session-reconstruction.md` 与 `../review-handoff.md`。

## 10. 证据与行为锚定

关键源码：

- `foundation/trajectory/context.py`：exchange started/finished；
- `foundation/trajectory/tools.py`：工具 parent exchange、状态与时间；
- `kernel/loop.py`、`foundation/trajectory/metadata.py`：assistant/tool operation ID；
- `service/analytics/turn_trace.py`：现有只读投影；
- `service/mutations/types.py`、`tracker.py`、`store.py`、`pipeline.py`：ledger/blob、逐次快照与策略；
- `orchestration/engine/run/finalizer.py`：save/checkpoint 后 after_turn。

2026-11-14 实际执行：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/orchestration/engine/test_mutation_operation_identity.py tests/service/trajectory/test_traces.py tests/integration/engine/test_turn_trace_projection.py tests/service/mutations/test_mutation_tracker.py tests/service/mutations/test_snapshot_policy.py -n0
```

结果：收集 179 项，`179 passed in 8.06s`，退出 0。覆盖重复 provider ID 下 operation 关联、tool traces、turn trace 投影、mutation 链和 snapshot policy；这是现有行为锚定，不是新 telemetry analyzer 或旧报文一致性的验证。

## 11. 2026-11-17 文件重建组合实验

新增 `../session-reconstruction.md` 与 `../../experiments/session-reconstruction.md`。仅凭 session_dir/session_id 的测试 reader 已实证正常两轮 3 LLM/1 tool/1 ai-code 精确且确定性；缺工具终态时保留 LLM、跳过 tool/ai-code，缺 after blob 时仅跳过 ai-code，fork 排除 origin 后不重报父历史。

最重要的新约束是 save=False：无 expected turn 的全扫描会返回旧轮，不能冒充本轮；after_turn 必须携带 expected turn ID/saved 结果。compaction fold 会移除 active 原始消息；Phase 3 archive 可保留 folded 原消息及稳定 ID，但 transcript 不展开它，且 Phase 1/2/4 不保证完整归档，因此只能以 trajectory 为权威、archive 有限去重 fallback，不承诺完整历史补报。补充复核还为 reader 加入目录一致性、sequence hole 和 absent 检查，fork 直接副本实测记录 trajectory-absent。最终定制、request tracking、compaction 与 fork 组合 48 项通过。真实 engine compaction×reader、完整 edit 和授权脱敏真实样本仍待后续。

## 12. 2026-11-17 trajectory 启用/禁用机制补充调查

应责任人要求，对"trajectory 默认启用还是禁用、如何启用/禁用"做只读源码核查。结论：**trajectory 默认启用（best-effort），不存在用户可操作的启停开关；文档所说 trajectory disabled 均为运行时 fail-closed 判定**。

### 默认启用的证据链

- `TrajectoryRecorder` 在 engine 装配时无条件构造（`orchestration/engine/assembly.py:108`），无 enabled 参数；
- 所有生产入口都持有非 None 的 StateStore：TUI 在 `app/tui/app.py:1518` 无条件 `JsonFileStateStore()`；ACP/headless 宿主 `orchestration/session_host.py:356` 为 `state_store or JsonFileStateStore()`；
- session 启动时经 `session_lifecycle.py:532,584` 绑定：`session_dir = session.session_dir if persistence.state_store is not None else None`（`ActiveSession.session_dir` 定义于 `orchestration/session_resources.py:56-67`，state_store 缺席时回退全局 sessions 目录，但 session_lifecycle 这里的显式守卫使 state_store=None 时直接传 None）；
- 绑定后在**第一个事件时懒激活**：打开 `events.jsonl`、取 writer 租约、写 runtime prelude；从不记录事件的会话不创建 `trajectory/` 目录（`engine/trajectory.py:156-161` docstring）。

### 无用户开关

`foundation/config/settings.py` 中 trajectory 组仅有 `trajectory.verify_commands`（969-979 行，rollback 前的验证命令清单，Apply.LIVE），不是启停开关；无环境变量、CLI flag、TUI/ACP 参数控制 trajectory 记录。

### 实际"禁用"= 运行时 fail-closed（`service/trajectory/session.py:73-90` TrajectoryDisabledReason）

| 原因 | 触发条件 | 生产可发生性 |
|---|---|---|
| `NO_SESSION_DIR` | state_store 为 None（engine 未传，`session.py:586-589`） | 生产入口均默认建 store，实际仅测试/嵌入场景 |
| `LEASE_HELD` | writer 租约被其他进程持有（同 session 双开，597） | 可发生 |
| `KEY_UNAVAILABLE` | 指纹密钥不可用（604） | 可发生 |
| `PERMISSION` | owner/mode/ACL/只读拒绝（99-119） | 可发生 |
| `ACTIVATION_FAILED` | 打开日志/写 prelude 失败（540-544，最多重试 2 次） | 可发生 |
| `SCHEMA_TOO_NEW` | 既有日志 schema 比当前版本新（634） | 降级安装旧版本时可发生 |
| `UNREADABLE_TAIL` | 日志尾部不可读（647） | 可发生 |
| `SEQUENCE_EXHAUSTED` | 序列号耗尽（659） | 极端长寿会话 |
| `CLOSED` | 会话已关闭（470） | 正常生命周期终点 |

除 `NO_SESSION_DIR`/`CLOSED` 外（`_UNREPORTED_REASONS`，session.py:93），每个原因经 `on_activation_failed` 发布 `trajectory_activation_failed` Warning（"Trajectory recording could not start and has been disabled for this session."，`session_lifecycle.py:563-582`）。激活成功后另有运行中单向降级：writer 写 ack 超时/写失败转 `TERMINAL_DEGRADED`，排队事件变 gap（`foundation/trajectory/writer.py` docstring）。

### 与既有结论的关系

- 与本节点第 5 节一致并精确化：trajectory 降级是 fail-closed 覆盖率损失，成功 assistant message 的 E/A、工具 operation ID 仍在 session.json，降级关联链不变。
- 与 run-owned 身份结论一致：disabled 时 recorder 无 `_turn`（pass 事件不可写），但 runner 侧 logical/pass 身份照常生成注册，不受影响。
- `save=False`（`ActiveSession.suppress_save`，active_session.py:115,222-227）与 trajectory disabled 是**两个独立层面**：save 抑制只停 `session.json` 保存，不触发 trajectory 禁用（trajectory 独立写 events.jsonl），与本节点第 3 节二者并列的口径一致。

### 批次1复现 trajectory disabled 的实验途径（候选）

1. 不传 state_store 构造 engine → `NO_SESSION_DIR`（测试态最简单）；
2. 预先持有该 session 的 writer 租约 → `LEASE_HELD`（最接近生产被动禁用形态）；
3. session 目录/文件设只读或错误 owner → `PERMISSION`；
4. 预写更高 schema 版本日志 → `SCHEMA_TOO_NEW`；坏尾行 → `UNREADABLE_TAIL`。

具体选用哪种由批次1 test-plan 裁决；本节仅登记机制与途径。

## 13. 2026-11-17 trajectory 性能/空间特征与停用影响

应责任人要求补充两项评估，均为只读核查，未修改产品代码。

### 启用 trajectory 的性能影响

写路径架构决定了常规成本极低，且存在硬性防阻塞保护：

- **单写线程后台写**：每 session 一个 daemon 线程（`chrys-trajectory-writer-<id>`，writer.py:228-232），批量 write-through，生产者只入队；
- **事件循环不被写盘阻塞**：事件循环上的同步调用点用 `emit_soon`（session.py:362-370）——当场只取序列号（保证顺序），有界 ack 等待放后台任务；激活本身也不阻塞 loop；
- **有界等待 + 单向降级**：`await emit` 等待 ack 至多 `DEFAULT_WRITE_ACK_TIMEOUT_SECONDS = 3.0s`（writer.py:69）；超时或写失败把 writer 单向转为 `TERMINAL_DEGRADED`（writer.py:22-27,80-85），此后 emit 不再阻塞、事件只登记为 gap，只剩 gap/收尾记录可写。即最坏情况一次 3 秒有界等待，之后该 session 的 trajectory 停摆但主流程照常（与第 12 节 fail-closed 口径衔接：这是运行中降级，激活失败之外的另一层）；
- **同步成本只有每 turn 一次 checkpoint**：`finalizer.py:433` 在 save/mutation summary 后 `await recorder.checkpoint()`（写 checkpoint 行 + fsync）；会话关闭时一次收尾（gap/coverage/runtime 标记 + fsync，join 超时 2s）；
- **取消安全**：写请求对调用方取消 shielded（writer.py:374-376），被取消生产者的行仍写出。

无 hooks、无网络、无额外进程；事件在进程内产生、本地顺序写。**性能结论：常规路径开销是毫秒级后台顺序写 + 每 turn 一次 fsync；异常路径有 3s 有界上限后永久让路。**当前 0.35.2 上游本身即默认启用运行，未发现因 trajectory 写入阻塞轮次的已知缺陷记录。

### 是否占用大量硬盘空间

不占。`events.jsonl` 是 content-minimized 事件流，体积有结构性上限：

- **单行预算 4096 字节**（`envelope.py:26` LINE_BUDGET_BYTES，含 envelope+换行 UTF-8），超大数组字段按同预算切分为 `event.segment` 分段行（segmented.py docstring），不会出现无界单行；
- **不存正文**：工具原始参数/结果在 `session.json`，文件内容在 `mutations/` blob——trajectory 事件只含身份、状态、时间和小型 facts（exchange facts 见 `engine/trajectory.py:57-80`，均为 profile/provider/id 级字段）；
- **懒创建**：不记录事件的会话没有 `trajectory/` 目录（第 12 节）；
- **量级**：一轮对话事件为 turn 生命周期 + 每 exchange started/finished + 每 attempt model.request + 每工具 operation started/finished 等，数十行、每行远小于 4KB——单轮几 KB 至几十 KB，30 轮会话 MB 级以内。P0-3 实测侧证：30 轮会话**全部 session 目录数据**（session.json+trajectory+mutation 索引）全量联读中位仅 38.409ms（`../performance-and-lifecycle.md`），隐含总体量很小；
- session 目录的真正空间大头是 `mutations/` blob（文件快照，SHA-256 去重、默认单文件 50MiB 上限、默认跳过二进制，见第 6 节）与 `session.json` 正文，均与 trajectory 无关。

未做专项磁盘测量；以上为源码结构+既有实验推得的量级判断，批次1垂直切片可顺带记录实测值。

### 停用 trajectory 对本 telemetry 方案的影响

前提重申（第 12 节）：**无用户开关，"停用"不是可配置选项**，只可能是运行时 fail-closed 故障态；若未来真要主动停用需改代码，属新的 fork R2 改动。

| 影响面 | 状态 | 依据 |
|---|---|---|
| after_turn 触发与 run-owned 身份（N3） | **不受影响** | runner 生成 logical/pass 身份先于且独立于 recorder 记录；disabled 时 recorder 无 `_turn` 但 TurnRuntimeState 快照方案照常（已签认结论） |
| 五类记录的 requestId 主键 A-final | **不受影响（正常成功路径）** | 成功 assistant message 的 `_chrys_request_attempt_id` 在 `session.json`；M0/M1-I 实验主链不读 trajectory 也可构造（P0-2 reader 亦然） |
| spanId（logical turn ID） | **不受影响** | turn ID 持久化于 `session.json` 的 `chrys_trajectory` state registry（`service/trajectory/state.py:25`），非 events.jsonl |
| ai-code 输入（mutation ledger+blob） | **不受影响** | ledger 在 `session.json.state.chrys_mutations`，blob 在 `mutations/`（第 2、6 节） |
| N7 ACP live-history 输出选择、1001/桌面输入捕获 | **不受影响** | 从内存 live history 与 ACP 输入取，不读 trajectory |
| 工具/ai-code 的精确父关联与交叉校验 | **退化** | `parent_model_operation_id`、T→E 交叉证据、rollback 孤儿区分均只在 events.jsonl；降级链为"function_call 所在 assistant message 的 A-final"（第 5 节），但当前实验 reader 实现为缺终态即跳过（fail-closed 不误报，`../session-reconstruction.md`），未实现降级上报——是否实现降级链属批次1/3 test-plan 决策 |
| exchange usage/timing/outcome facts | **丢失** | 唯一来源是 `model.exchange.started/finished`；B7 最小 envelope 不强制这些字段，故最小闭环不塌，但 **M1-T 0.28 全字段 parity 无法达成**（已签认的联调/上线门禁项会缺字段源） |
| 全部 attempts 历史 / pass-retry 全史 | **丢失** | 不影响上报（只报成功 A-final），但异常矩阵（SDK retry、redirect、Responses 轮询、resumed pass）的验证证据不可得 |

**总体定位**：trajectory 停用**不推翻已签认方案**——五类记录主键、span、ai-code 输入、ACP 输出、after_turn 触发在无 trajectory 下仍可工作，且缺失可检测、不产生错误数据（P0-2 实验：缺工具终态时保留 LLM 报告、跳过 tool/ai-code）。实质损失是证据质量与覆盖率：精确父关联、usage/timing 字段、retry/pass/孤儿矩阵退化或不可验，M1-T parity 无法关闭。发生率层面，九类 disabled 原因均为异常条件（第 12 节），正常部署不出现。
