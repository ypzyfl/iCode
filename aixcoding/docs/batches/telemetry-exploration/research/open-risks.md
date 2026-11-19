# 当前开放风险与协议疑问

> 截至 2026-11-17（N1–N6、N9、广义调用及 D1 缺陷登记已完成大方向调查；另一 AI 已完成一轮独立评审。N7 输出要求与桌面 0.28 输入捕获均已确认纳入，workflow 明确退出范围）。
>
> 2026-11-19 增补：OpenAI Codex 技术评审 F1–F6 已按修订口径裁决。F1 异步读取记录级一致性、F2 pass 级执行归属和 F3 当前轮真实压缩构成批次1前置判别 V1–V3；F4 单写/切换/回退是最终替代交付门禁；F5 统一完整性矩阵和 F6 文档清理已落盘。这些发现未验证关闭，最新门禁见 `review-handoff.md` 第 12–13 节。
>
> 总结：在已确认的非实时、best-effort、允许孤儿和缺失降级范围内，**本地正常主链尚未发现被证明无法实现的需求，但五类外部记录尚未形成生产端到端闭环**。另一 AI 已认可主路线；新增重点是 BR-1/5/6 后台前置确认、公共字段 parity、funcId 的模型 toolUseId 对账字段和已确认纳入的 ACP 输入捕获。当前有效总览见 `review-handoff.md`；评审发现收敛后进入实施批次，不再扩大只读调查。

## 1. 可能影响方向成立的重点项

### R1：持久化能力已确认，剩余是 A-final 服务器闭环验证

责任人已确认：客户端上报什么，服务器就记录什么。当前以每次最终成功响应的 raw attempt ID（A-final）为主身份；2026-11-18 原值裁决后，**同一成功模型响应 M** 的原调用记录和 after_turn 独立 LLM 报告统一为 M 的 A-final 原值（32hex，不转 UUID），tool-detail/ai-code 关联实际产生它们的 A1，最终 ACP 通常关联 A2。不再依赖新增 exchange header 或 E↔A 映射。

后台目前没有同一逻辑调用的 create/retrieve、retry 等多 HTTP 记录细节，因此不存在已知的“同一 requestId 多 HTTP 行聚合”需求。服务器按既定业务模型处理：

1. 成功模型调用的原调用记录与独立 LLM 报告按 A-final 原值合并，而不相互替代；
2. tool-detail、ai-code 按同一 A-final 原值关联；
3. 缺少 A-final 时跳过该条并记录原因，不用 exchange 混填；原记录或独立报告缺失时按已确认口径保留孤儿数据。

**影响**：持久化能力已经具备，剩余是开发期验证最终 message 和实际请求 header 的 raw A-final 一致、服务器每请求记录保存自身 attempt 原值（成功由独立报告 join 声明，2026-11-18 BR-1 修订 + ID 原值裁决），并覆盖 retry、redirect、Responses continuation 和流式。若发现严重问题则暂停并回评 exchange；C1/C2 只在该回退分支中重新启用。

### R2：requestId 暂定 A-final，2026-11-18 改为 ID 原值（不转 UUID）

责任人于 2026-11-16 暂定最终成功 attempt 为主 requestId；**2026-11-18 责任人裁决所有 ID 保持原值 32hex、不转 UUID**（此前短暂的外部 UUID 归一化安排作废）。

后台原模型调用记录直接保存 attempt 原值（配合 BR-1 每请求存自身值、成功由独立报告 join 声明）；独立 LLM、tool-detail、ai-code 和 ACP 使用同文本原值，客户端无转换层，内部无需修改 request_tracking.py 或 ids.py；tool/ai-code 关联 A1，ACP 通常关联 A2。缺失/非法 raw 跳过并不另造 ID；后台 32hex 格式接受、与 0.28 UUID 文本历史数据混存、原记录/报告 join、retry/Responses 和 Agent Studio schema 放宽（接受 32hex）仍需确认/落实与联调验收。

后台没有同一逻辑调用的多 HTTP 记录细节，因此“requestId 是否允许多 HTTP 行”的确认项已撤销。这里的多记录关联指原调用记录、独立报告、工具、ai-code 等业务记录。

### R3：工具 funcId 身份已确认，剩余是 final-save 与原子幂等实现

普通本地工具可经 `T.payload.call_item_id → function_call C → assistant M → A-final` 精确关联，T/E 用于交叉校验。provider `call_id` 不能假定唯一；同一响应中重复且未解决的 call_id 还可能共享 T，因此端侧不能只靠 call_id 或 T 区分 occurrence，必须优先使用 C。当前 UI 12hex `_chrys_call_id` 不保证持久化，旧随机 fallback funcId/parentSpanId 的原值也不能恢复。

2026-11-16 旧源码和跨端消费复核进一步确认：旧 CLI 普通工具在 save 时取 `provider_call_id or event.call_id`，record 创建后复用；PENDING 复用 PENDING、终态以 final 全量更新。旧 save 带 requestId/spanId，update 不带，funcName 仅辅助恢复。旧 mock 只校验 funcId 为 1–512 字符串及 PENDING 可更新，不证明真实唯一索引。AIxCoding 桌面侧也把自身 toolCallId 作为 funcId，并以它查 update，说明 funcId 并非只能等于 provider call_id。

因此 **每次工具执行使用新的稳定 funcId**已是当前推荐路线，普通本地工具 funcId=T 原值（32hex，2026-11-18 原值裁决，不做 UUID 格式化）。B4 已明确 turn 是一轮对话，spanId 为当前 turn ID，同一 turn 的模型和工具共用；parentSpanId 只在真实父子对话关系中填写直接父 turn ID。普通 session 对话轮通常独立，无父 turn 时不传该字段，不能把时间上的上一轮或 E/A/T 当作父级。

B2/B3 已由责任人确认：save 是插入新记录，PENDING/final 仅按 `WHERE func_id = ?` 更新，不存在 funcId=provider call_id 的其他消费者；后台曾确认接受 36 字符 UUID、无唯一索引，完全依赖客户端保证全局唯一（原值裁决后 funcId 为 32hex 原值，格式接受列入 BR-5 确认点）。相同 funcId 重复 save 会插入重复行，update 会更新全部重复行。因此 provider 交叉查询和格式风险基本关闭，普通本地工具 funcId 的执行实例契约成立。

B6 已确认现有行为：final-only 失败，重复 final 会改变完成时间/状态等字段，final 后 PENDING 会回退终态，且不宜极短间隔连续三阶段发送。因此 after_turn 不宜机械复制 save→PENDING→final。当前目标是每工具只发送一条包含最终状态/结果的 final snapshot save；后台提出的 requestId+funcId 组合可作为防重增强，但 save 必须做原子唯一/upsert，单改 update WHERE 不足以阻止重复插入。三个执行时间字段已按 B5/P2 裁决全部去掉。

责任人已确认后台可以支持或修改单次 final snapshot save、`(requestId,funcId)` 原子幂等及重复终态语义，目标态不再是能力阻塞；明确后台需求和验收用例见 `backend-change-requests.md`。实现后相同最终报文可安全重试，由组合键去重，不再依赖客户端避免一切传输重试。

相同组合不同内容的冲突策略已由责任人确认：明确冲突（例如 409）、不隐式覆盖并记录原因。B4 概念语义已关闭——parentSpanId 父 turn 语义与 0.28 实际用法（父模型调用 llmSpanId）不同，记为 parity 显式差异项；当前对话模型为平面 turn、无真实嵌套 turn 场景，父 turn ID 持久化仅将来出现该场景时再验证（2026-11-19 澄清）。B5/P2 已通过删除三个执行时间字段关闭。

**影响**：单次 final save 消除 PENDING/final 顺序问题，组合原子幂等消除重复插入风险。T 原值 funcId 仍是执行实例身份，客户端需保证重放报文确定性；后台目标契约可协调不等于现网已实现，联调验收仍必要。

**独立评审新增**：仅使用 funcId=T 原值会使后台失去与模型 toolUseId 直接等值对账的字段，但当前 session 的 function_call/result.call_id 仍保存原值，并非本地证据丢失。BR-8 可选 providerCallId 建议已于 2026-11-19 责任人裁决撤销——协议面向多 AI 工具保持通用，对账由客户端按 T 本地反查完成。

## 2. 有数据或语义缺口，但存在工程路线的重点项

### R4：slash skill 的精确归属与恰好一次尚未闭环

slash 是输入触发，只关联 pass，不带 exchange/attempt。当前 reminder 会在后续请求和压缩中重放，不能按 reminder 数量上报。普通输入、mid-turn injection、retry 的 opening_item→pass 映射是否始终唯一尚未证明。

可选路线：在输入解析点局部补采 `session_id + pass_turn_id + opening_item_id + skill_name`，after_turn 读取；不能回退 session-latest。

**影响**：可能造成 slash 使用次数或归属不准，不影响普通工具/load_skill 主链。

### R5：N9/N7 桌面输入已确认纳入，剩余是实现与公共字段 parity

固定运行时/live session 可覆盖版本、当前用户、workspace 和主 Agent；desktop envelope/selected Agent 必须 ACP 入口捕获。责任人已明确仍需保持桌面端 0.28 能力，因此 Q2 选择纳入实施：selected Agent 1001、desktop channel/IDE/functionName 等不再接受缺失差异。Git 只能选择轮末快照、提前事件时捕获或省略。无 workspace 不回退进程 cwd，无历史依据不猜。

2026-11-17 已确认最终 `PromptResponse._meta` 必须主动携带当前 turn 的 requestId，客户端另查 `session/turns` 不满足要求。暂行在 per-session prompt_lock 内，从 live 主 history + TurnRecord 按 logical turnId 精确选择最后成功主 assistant 的 raw A-final；2026-11-18 原值裁决后 requestId 直接使用 raw 原值（32hex），无转换——配套 Agent Studio schema 放宽接受 32hex。只需 `app/acp/server.py` 上游接缝和定制 helper，无需 request_tracking/ids 或 after_turn/live registry 改动。

**影响**：N7 输入/输出范围均已确认，剩余是接缝实现和真实消费方 envelope 兼容；Git 字段语义仍留实施。独立评审另指出公共字段 parity：原模型记录实际保存的 channel/pluginVersion/projectName/Git 等未知，独立 LLM/tool/ai-code 不得因最小 DTO 静默省略，须逐字段裁决和验收。详见 `nodes/runtime-context.md` 与 BR-6/BR-7。

### R6：interrupted/cancelled 存在两种不同旧错误，且没有已验证的目标协议映射

主 Agent/local child 的部分取消路径没有 Result，只发 PENDING；外部 ACP translator 虽补发 interrupted Result，旧分类器却忽略 interrupted 并归 codeStatus=1 成功（D1 探针实证）。因此不能统一描述为“永久 PENDING”，也不能把 interrupted 一律伪报普通失败。

**影响**：需要后台扩展、协议映射或登记差异；不影响 success/failure/rejected 主路径。现已单列为 BR-9；中间/失败 attempt 的落库和孤儿口径另列 BR-10。逐项证据见 `defect-register.md` L-D04/L-D11。

### R7：N6 大方向已关闭，剩余为实施验证

正常成功 write/edit 可重建旧 blocks、requestId/spanId 和 codeStatus=1/5；PR #69 的 `mutation.tool_operation_id=T` 提供关联，旧 `mutation.tool_call_id` 仍是独立 12hex UI ID，不是桥。失败/拒绝/取消即使留下 mutation 也不上报；PR 前记录、最终参数截断且 digest 不同、所需 blob 缺失或已清理时降级，不猜历史。

**影响**：没有新增方向阻断。2026-11-17 首版 reportId=T 原值（原值裁决后口径）、`(requestId,reportId)` 幂等已由责任人委托 AI 制定为 B8 暂行方案，同 T 多 mutation 跳过，不新增上游 mutationId；后台现网未确认。真实 session 组合样本、CRLF/GBK/golden parity 留实施，详见 `nodes/ai-code.md` 第9节。

### R8：外部 ACP 内部工具仅保留保真边界，不继续调查细节

旧版确实通过本地 translator 将外部 ACP ToolCallStart/Progress 转成工具事件并上报，但那不是远程内部完整审计。当前文件只有 boundary + 有界 translated_updates：可重建部分 toolCallId/title/rawInput/rawOutput/status，不能精确恢复逐项时间/耗时、真实工具名、MCP 类型或远程内部 E/A。旧 requestId 还可能来自 session-latest，不能作为正确语义复制。

责任人于 2026-11-17 明确当前无需关注外部 ACP 内部工具如何上报的细节，P1 改为最终 ACP 响应主动携带 requestId。因此严格跳过、projection 特例或外部协作不再作为当前待裁决分支；仅保留“不能把本地投影冒充远程真值”的边界，除非未来提出内部工具审计需求再重开。详见 `nodes/broad-tool-coverage.md`。

### R9：provider-hosted 不等同于本地 tool operation

hosted call/result、family、provider ID、最终规范化参数和正常成功/失败状态可从事后内容恢复，所在 assistant M 提供各自 E/A-final；没有本地普通 T/C 工具执行链。旧主 Agent/local child hosted Result 都未传 duration_ms，旧报文默认 0，不是 provider 真实耗时；当前 response-level timing 和 hosted observation 时间也不能冒充工具时间。

**影响**：责任人已于 2026-11-17 明确 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs` 全部去掉，适用于所有新版工具记录。hosted 只重建业务字段和 A-final，不复制 0，不补采本地展示时间或 provider 真实执行时间；B5/P2 已关闭，剩余只有 cancelled 协议。

## 3. 已明确的硬边界，不应再当作可修复缺陷

- 崩溃/强杀没有 after_turn，且当前明确不做启动扫描补报。
- save=False、trajectory 激活失败/gap、blob 缺失或 policy skip 时，无法保证完整保真，必须 unknown/降级。
- 无持久化依据时，不能恢复旧随机原值、历史 workspace/Git 或文件历史内容；不能用当前状态猜测。
- 外部 ACP 的真实内部 LLM/工具审计不自动进入本地 session；有界 update 只能支持投影降级。内部明细已退出当前范围，不再把补采或外部协作列为本任务待办。
- workflow 已由责任人明确排除，不在本次 telemetry 范围内。
- 当前 ACP 无 turn 结束前逐次模型调用通知；没有真实消费方时该方向已暂缓。
- Responses 工具生产 attempt 可以是 retrieve GET，不能把它误配给 create POST；证据不足时 unknown。

若需求改成“任何故障下都完整”“必须恢复旧随机原值”“不修改协议却支持旧版没有的取消语义”或“无消费方也立即增加 ACP 流式通知”，则分别与上述边界冲突，需要另作范围或协议裁决。

## 4. 已有充分依据、当前无需重点担忧的部分

- 正常主 Agent 路径存在 save/checkpoint 后的进程内 after_turn 接缝。
- 正常 ACP 响应晚于 after_turn，可为轻量通知入队提供时点；N7 身份则由 prompt_lock 内 live-history 独立选择，不等待 registry。
- trajectory/mutation 默认装配，整个 session 目录联读可覆盖主要关联和 write/edit 输入。
- 普通本地工具、shell、MCP 和 load_skill 可通过两条证据链关联 exchange 和生产响应 attempt；local child 可按 actor 使用自身链。
- 当前 A-final 路线复用现有 attempt header，不依赖新增 exchange header；C1 的两处集中接缝仅在回退时重评。
- N8 有序 best-effort、允许孤儿已确认，不需要引入严格 ACK 依赖。

## 5. 建议优先级（2026-11-17 整体风险重排）

责任人明确 mock 只是 telemetry 的一个环节，要求先发现可能推翻整个方案的阻塞、外部依赖和端到端证据缺口。后续顺序调整如下：

1. **P0：A-final 五类记录最小端到端闭环**。M0/M1-I 已用真实 engine/客户端验证 A1/A2/T、一对多、失败不借旧 A、retry、Responses retrieve、redirect 锚点和并发，共 31 项通过；未发现推翻主路线的身份矛盾。真实服务器落库、生产 reporter、M1-T 原子重放/409 和真实 ACP server 仍未实现，见 `a-final-e2e-closure.md` 与 `../experiments/m1-identity-contract.md`。
2. **P0：真实 session 重建正确性**。仅凭文件的正常两轮精确性、blob/终态 gap 降级、fork 零重报和 save=False expected-turn 守卫已通过，组合 48 项通过；详见 `session-reconstruction.md`。新约束：after_turn 必须带 expected turn/saved，fork 排除 origin；compaction 后不能保证完整历史补报，真实组合样本留实施。
3. **P0：长会话分析成本与正常退出可靠性**。30轮基准显示全量与expected-turn均约7→38ms线性增长，过滤不减少I/O；队列FIFO/跨session并发/有界flush原型通过，组合52项通过，见 `performance-and-lifecycle.md`。默认只处理显式当前轮，不为崩溃补报做持久化高水位。after_turn接缝复核已完成：runner在trajectory激活前已生成并注册logical/pass身份，最小可靠路线是run-owned快照→direct finalizer dispatcher→集中per-session lifecycle drain；候选R2为`turn_state.py`、`runner.py`、`finalizer.py`、`session_lifecycle.py`四个文件，不需要逐TUI/ACP入口接线，也不允许latest TurnRecord回退。主路线未被推翻；详见`nodes/after-turn-lifecycle.md`第14节。**下一方向步骤是实施design/R2呈报裁决，批准后才做真实垂直切片和ACP桌面闭环，完整M1-T矩阵后置。**
4. **P1：真实桌面 ACP schema 闭环**。Agent Studio 已定位到只消费 `agent-studio.dev/final-model-identity`，且要求回显桌面 response-attribution span；这影响 ACP 身份链，不改变 after_turn 和工具主链。真实 fork server × 桌面消费方联合验证接在五类记录最小样本之后。
5. **上线 P0、开发不阻塞：真实后台与数据治理验收**。独立 LLM endpoint、原记录原值保存与 32hex 格式接受、原子幂等、孤儿最终 join，以及代码块/路径/参数的权限和保留口径必须在内网或上线前验收；按既定环境约束，不作为外网开发前置，mock 通过不得宣称现网通过。
6. **P2：局部语义与扩展覆盖**。cancelled/interrupted、slash 恰好一次、hosted/外部 ACP 内部工具和真实嵌套 turn 等保持单列，不与正常主链方向性阻塞混同。
7. **后置实施细节**：单端口 mock 路由、DTO 增强字段、完整 debug 展示和全量异常矩阵在以上方向证据之后展开。B7/B8 暂行契约足以指导最小实验，不再因完善 mock 本身而扩大调查。
