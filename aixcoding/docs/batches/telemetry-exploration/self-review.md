# 自评审记录：Telemetry 方案探索（telemetry-exploration）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-17
- 确认意见：暂时按此方案执行。当前还是探索阶段，方案虽然签认，但是，如果具体实施过程中遇到无法解决的问题，方案可能被推翻。
- 开发 AI：Kimi-K3.1-Pro / CodeBuddy
- 评审 AI：GLM-5.3 / CodeBuddy（阶段中评审，独立会话）；Deepseek-V4-Pro / CodeBuddy（阶段中复审，独立会话）；另一 AI（模型标识未提供，报告由责任人转交；独立评审+复审收敛，经责任人 2026-11-17 裁定为最终双 AI 自审轮次）

> 当前时点说明：最终双 AI 自审轮次已经责任人裁定满足（2026-11-17，见文末裁定节）；责任人周彬已于 2026-11-17 完成上方头部签认。签认后追加的评审记录与文档修订不触发重签（头部规则）。
> 签认边界（责任人要求）：当前仍为探索阶段。本 self-review 与探索 design 的签认仅确认探索结论、评审收敛与证据链完整，可作为后续实施批次的证据基线；不构成实施成功的保证，也不冻结方案。具体实施过程中若遇到无法解决的问题（如 A-final 服务器闭环失败、身份关联被证不可行、BR-1/5/6 等关键后台前提失败），方案可能被推翻，届时停止扩张、按既有机制回评（C1/C2 回退备选、N1-A 完整成本重评）并重新设计/评审签认。

## 2026-11-14 阶段中评审：5 项 findings 已裁决并处置

- 独立性：评审 AI 与开发 AI 使用不同模型、不同会话，符合“不同工具或不同模型”要求；本次仅作阶段中评审，不计入最终交付的双 AI 自审轮次。
- F1（流程顺序）：责任人确认首轮静态研究和 E1 属 DEVELOPMENT.md §4.2 只读操作/运行测试免判定范围，合规且无需追认；路径 1 仅授权建立探索文档。已在 `plan.md` 补注记，并明确 E3 新增代码须待 design 签认。
- F2（能力矩阵证据）：采纳“规则澄清 + 补锚点”，已在 `research/capability-matrix.md` 增加初始证据锚点；无证据行必须标“待专题”。
- F3（attempt 前提）：已补充 trajectory 开启、事件记录完整和“全部已持久化 attempts”限定，同时注明 session message 只保留最终 attempt。
- F4（评审独立性/落盘）：按本阶段中评审记录落盘；探索交付前仍须进行最终独立评审。
- F5（E3 落位）：已登记 `aixcoding/tests/telemetry/test_request_identity.py`，限定仅新增定制测试、使用现有 scripted transport/mock、design 签认后实施，且自生成测试不单独证明方案正确。
- 未修项：无。
- 处置后门禁与空白检查：见 `verification.md`“阶段中评审 findings 处置复核”。
- 后续：主要开放问题收敛、形成交付结论后，仍由独立 AI 评审证据充分性、过度推断、能力分类、上游建议通用性和跨批次授权边界，并追加最终评审轮次。

## 2026-11-14 阶段中复审：通过，S1/S2/N1 已处置

- 评审 AI：Deepseek-V4-Pro / CodeBuddy，独立第二 AI、独立会话；与开发 AI 模型不同，满足双 AI 独立性要求。本次仍为阶段中复审，不自动视为长期探索批次的最终交付评审。
- 证据抽查：评审实际核对 request tracking、analytics ID、ExchangeTrace、begin_exchange、旧 LLM 注入、ACP kwargs、after_turn、审批参数改写、client 组栈和 session meta 等锚点，均未发现失真。
- S1（root span 证据）：已在能力矩阵补充旧版固定 namespace、`uuid5(session_id:turn_id)` 公式及调用锚点，并补充当前 pass/logical turn ID 来源。
- S2（旧副本路径可移植性）：已在 design 基线假设和 request-identity 基线中注明本机留档路径非协作者/CI 通用契约，其他环境须定位等价副本并重核行号。
- N1（旧公式术语）：能力矩阵首次出现处已明确为 `root_span_id(session_id, turn_id)` 确定性派生，与 S1 合并修订。
- 未修项：无；blocker：无。
- 处置后验证：见 `verification.md`“阶段中复审 S1/S2/N1 处置复核”。
- 流程提醒保留：若将探索批次作为独立 PR 合并，design 与 self-review 须先由责任人签认以满足 closure；签认后持续追加 research/experiments 不触发重签。

## 2026-11-17 探索收敛与外部评审交接

责任人明确下一步由另一 AI 先评审，再开工实际开发。本轮新增 `research/review-handoff.md` 作为当前有效结论入口，集中呈现已探索/排除方案、当前推荐、五类记录与 A1/A2 分工、四文件 N3 R2 候选、单文件 N7 接缝、证据强度、阻塞/风险、iCode 通用建议、BR-1–BR-7 后台配套、mock 目标和未调查事项。

同步修正当前摘要中的旧口径：capability-matrix 不再标为初始静态评估；backend-change-requests 增加 BR-6/BR-7 并修正 retry/ACP 关联验收；after_turn 不再接受 trajectory disabled 身份降级或声称只改 finalizer；N7 不再依赖 after_turn registry；单端口 mock 与 B7/B8 暂行状态统一到总览。历史 verification、早期实验失败和当时决策保留，不把后续结论回写成当时已知事实。

本次是评审材料整理和一致性审查，不是责任人安排的另一 AI 正式评审，也不构成 self-review 最终签认。后续评审发现应逐条记录、裁决和回写；实施批次、ADR、R2、上游修改和 Git 写操作均未获授权。

## 2026-11-17 另一 AI 独立评审及处置

评审 AI：模型名称未提供，报告由责任人转交。评审独立查证 0.35.2 hook/session/trajectory/ID/ACP/ChatMiddleware 和 0.28 定制终态，并交叉阅读本批专题；总体认可 N1-C、N3-A 四文件、N4 文件分析、A-final、final snapshot 和 fail-closed，无方向性反例，同意作为后续实施基线。

### 认同并已回写的事项

- R1：BR-1/5/6 后台依赖在首个 mock 切片期并行正式确认；现网未证明。
- R2：B7/B8 最小 DTO 不替代 channel/pluginVersion/projectName/Git/userId 等公共字段 parity；原模型记录实际字段需后台确认。
- R3：1001/desktop 输入捕获与“暂缓”存在范围矛盾。责任人已裁决保持 0.28 桌面能力，Q2 纳入 N7 输入捕获和 selected Agent 1001，不接受该差异。
- funcId：评审正确指出后台失去直接与模型 toolUseId 等值对账的字段。只读复核确认原值仍存在于当前 session function_call/result.call_id，不是本地证据丢失；BR-8 建议保留 funcId=UUID(T) 并新增可选 providerCallId，requestId+funcName 不能替代，重复 provider ID 仍需 occurrence。
- R4：真实桌面 Zod/后台 UUID schema 验证保留。
- R5：长会话增长和背压需要实施期实测；不把未经测量的估算当事实。
- R6：slash/sub-agent 归属继续明确；BR-9 单增 cancelled/interrupted，BR-10 单增中间/失败 attempt 记录和孤儿口径。workflow 已由责任人明确排除，不调查。
- 失败模型零上报和 eventSubType=success 属真实统计差异，进入 parity；外部 ACP 内部明细继续退出；三个工具时间字段删除经责任人再次确认最终关闭。

### 对评审表述的限定/分歧

1. **N1-A 回退成本**：不认同“后台关键前提失败即切 N1-A，多改 1–2 文件换后台零改动”的整体表述。N1-A 只替代 LLM 搭车通道；final-only、funcId/ai-code、UUID、ACP 和公共字段配套不会自动消失，逻辑 requestId 向工具/ACP 的传播也需重新设计。Q5 因此定为失败后重评完整成本，不自动切换。
2. **公共字段“永久缺失”**：不认同其必然性。当前最小 envelope 确有缺口，但 N9 可在独立报告/其他 DTO 补采，原记录也可能已有字段；应先查原记录并做 parity，而非判定路线必然后果。
3. **500 轮 600ms**：只认同为外推示例，不认同作为实测证据或验收阈值；现有实测仅到 30 轮。
4. **parentSpanId“未交代”**：不认同。B4/B8/handoff 已明确 parentSpanId 仅表示真实直接父 turn，普通独立 turn 省略，不恢复旧 llmSpanId 作为父级。旧字段语义差异真实存在，但不是文档遗漏。
5. **funcId 的表述边界**：认同外部对账缺口，但不应理解为原始 toolUseId 已无法获得或 UUID(T) 应被回退；两端身份应并存。

以上评审处置仍是探索文档更新，不是实施/R2批准；BR-8–BR-10 均待后台确认。

## 2026-11-17 复审收敛

另一 AI 复审逐项核实修改属实，接受全部五项限定：N1-A 完整成本、公共字段条件性、性能外推、parentSpanId 已有关闭、funcId 上送通道边界。主路线无阻塞的结论不变，plan 中“反馈评审 AI”待办关闭。

复审三项残留建议均已回写：

1. N1-A 分支补充 middleware 早于 attempt 铸造、0.28 随机 requestId 仅靠内存 registry 传播且不持久化的时序证据；回退不能按装配文件数估算。
2. parity 从公共字段扩为 0.28 全字段矩阵，并绑定 M1-T/真实联调关闭门禁，与 BR-1/5/6 同批确认；不前置阻塞外网 mock 开发。
3. N7 明确 1001 的输入捕获→不可变 turn 上下文→after_turn 链：save-only、无 T，按 `(sessionId,logicalTurnId)` 去重一条，关联当前 turn 首个成功主模型 A-final，无成功或输入缺失时跳过。

复审没有新增方向性阻塞；下一步为责任人裁决实施批次 requirements/design/R2。

## 2026-11-17 实施组织与实验资产处置

责任人确认探索批次独立交付，生产实现采用三个开发批次和 `feat/telemetry-session-analysis` 独立集成分支，全面验证后再合并主干；mock 随批次1垂直切片实施。plan 已登记两个 fork workflow 的集成分支 PR 触发前置条件，避免批次 PR 失去双 CI。

> 2026-11-19 注记：上段组织方案已由责任人修订——`feat/telemetry-exploration` 为长期根分支（探索 commit `7f3fe332` 已在其上，不建独立 PR、不提前合并主干），工作块分支做好后 PR 合回，全部完成或确认失败才整体并入；原集成分支名降为工作块分支示例。详见 `plan.md` 实施策略节（修订后）。

`aixcoding/tests/telemetry/` 四个测试态文件全部保留并随探索批次提交，作为可复现证据；不进 wheel、不移入上游 tests。生产实现与等价/更强覆盖合并后，才逐项呈报精简或退役。本轮仅文档落盘，不创建分支、不修改 workflow、不执行 Git 写操作。

## 2026-11-17 plan 专项评审处置

另一 AI 对 plan 的续接能力评审为“合理，可作为续接入口”，五项建议全部采纳：批次1明确包含 1A 单端口骨架与 1B 切片 telemetry，开始前修订 mock design/DIRECTORY；D1 按各批涉及范围签认，upstream-proposals 走独立时间线；探索签认前由责任人裁定现有评审是否满足最终双 AI 自审，不足补一轮；最终复查显式运行全目录 ruff format 和 gen_customizations --strict；批次3的 BR-8 限定为完整对账矩阵/联调，不重复批次1字段实现。

上述记录是 plan 专项评审，不自动等同于最终 self-review 签认；最终签认仍须完成顶部交付门禁和责任人裁定。

## 2026-11-17 最终双 AI 自审裁定与签认边界

责任人裁定（plan「唯一下一步」第 2 步，选项 A）：认定 2026-11-17 另一 AI 独立评审+复审收敛（含 plan 专项评审）为本探索批次的最终双 AI 自审轮次，满足签认前提；GLM-5.3 与 Deepseek-V4-Pro 两轮维持"阶段中"定性，不改变。该最终轮评审 AI 模型标识未提供、报告由责任人转交，头部评审 AI 行已如实记录。最终交付复查（五项门禁全部 exit 0）证据见 verification.md 末节。

签认边界（责任人明确要求记录）：当前仍为探索阶段，本文件与探索 design 的签认仅确认探索结论、评审收敛与证据链完整，可作为后续实施批次的证据基线；不构成实施成功的保证，也不冻结方案。具体实施过程中若遇到无法解决的问题（例：A-final 服务器闭环失败、身份关联被证不可行、BR-1/5/6 等关键后台前提失败），方案可能被推翻；届时应停止扩张、按既有机制回评（C1/C2 回退备选、N1-A 完整成本重评）并重新走设计/评审签认，本签认不排除任何回评或推翻路径。
