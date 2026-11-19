# 需求：Telemetry 方案探索（telemetry-exploration）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

0.28.0 的 AIxCoding telemetry 通过直改上游源码实现，功能完整但定制点分散，跟随上游升级成本较高。当前基线已追至 0.35.2，需要评估以 session 文件分析为主的实现方式，并逐项回答：哪些能力可以纯文件重建，哪些必须保留 fork 上游接缝，哪些适合建议 iCode 提供通用能力，哪些只能接受差异或降级。

截至 2026-11-19，主要方向性问题、独立评审/复审和最小身份样本均已收敛，责任人已裁决实施组织（三批次+集成分支）并完成探索批次签认（2026-11-17）；当前有效结论汇总在 `research/review-handoff.md`。探索批次独立 PR 合并后进入批次1 requirements/design/R2；本批次不直接实施正式 telemetry 或授权 R2。

## 目标与非目标

- 目标：
  - 以旧版由 iCode/aixcoding-cli 实际产生的上报和 ACP 输出为对照基线，建立完整能力矩阵。
  - 对每项能力给出证据、差异、必要上游接缝和可替代方案，不以功能名称相似推断等价。
  - 区分逻辑模型调用、HTTP attempt、turn/pass、工具 operation 等 ID 语义，保证后续关联设计有统一口径。
  - 记录旧版已知缺陷及处理意见，兼容字段、ID 粒度和关联语义，不默认 bug-for-bug 复现。
  - 形成符合通用 AI 工具定位的 iCode 上游改进建议，避免提出 AIxCoding 专属能力。
  - 为主要问题收敛后的实施批次划分提供依据。
- 非目标：
  - 本批次不实施正式 telemetry 功能，不授权任何 R2 上游改动。
  - 不补桌面端原本自行上报的内容，不新增旧版 CLI 没有的上报类别。
  - 不要求实时上报，不设计崩溃或强杀后的启动扫描补报。
  - 不把纯 session 文件、绝对零上游改动或此前提出的四批次实施拆分当作不可变前提；方案排序仍必须遵循下述零上游优先、必要改动少而集中的纪律。
  - 不提前决定新增 ACP 流式模型调用通知；先确认消费方需求和通用性。

## 探索约束与方案推进纪律（2026-11-16 责任人明确）

以下七条是本批次的强制约束，优先级高于 AI 对方案或实施便利性的判断：

1. **需求来源与不猜测**：主要从 0.28.0 定制最终版提取需求。事实或需求意图不确定时记录疑问并向责任人询问，不用技术推测替代需求确认。
2. **上游改动最小化**：优先不改上游源代码的方案；确实不能不改时，选择改动尽量少且集中的方案。技术可行不代表可以绕过该优先级。
3. **按顺序探索方案**：记录候选方向，从最符合“零上游 → 最小集中上游改动”原则的方案开始，一个方案一个方案探索。先判断大方向是否存在阻塞和重大问题，非阻塞性细节留到实际实施。
4. **阻塞与停止条件**：优先调查阻塞点、风险点和存疑点；必须先明确的先调查或询问。确认当前方案不可行时停止该分支，记录证据、影响和可重开条件，不继续投入其细节。
5. **旧缺陷由人裁决**：0.28.0 中确定的问题和不合理实现可以提出修复建议，但必须由人确认后才成为实施决定；不要求 bug-for-bug 复制明确有问题的行为。
6. **一致性与差异裁决**：新版尽量保持旧版字段、关联和使用语义一致，允许少量有依据的变通；每项做不到一致或建议不一致的地方都要明确提出、经人确认并记录在案。
7. **上游工作分类**：所有上游接触点按“可建议上游 iCode 团队修改”“需要我们自己定制化”“现有条件下无法做到”等分类记录；同时注明适用方案、最小 fork 过渡、重开条件和是否需外部协作。

执行口径：

- 当前倾向的 after_turn + 全 session 目录联读仍是探索路线，不是正式实施授权。
- 2026-11-17 责任人补充环境约束：aixcoding-cli 在外网开发、真实服务器在内网，无法简单前后端联调；开发期以 mock server 的目标契约闭环为准，真实后台仅作后续内网验收，不能作为外网开发前置。mock 通过不得宣称现网后台通过。
- 2026-11-16 责任人暂定：以最终成功响应的 attempt ID 作为主 requestId；失败/pending/部分流不上报，缺 A-final 时跳过并记录原因，不用 exchange 混填。C1/C2 仅保留为开发期严重问题后的 exchange 回退通道。
- B1 已确认并经两次修订（**2026-11-18 BR-1**：每请求存自身 `Chrys-Request-Attempt-Id` 原值、不做成功判定、成功由独立报告 join 声明；**2026-11-18 ID 原值裁决**：所有 ID——requestId/funcId/reportId/spanId/parentSpanId——保持原值 32hex、不转 UUID；客户端不引入转换 helper、后台原值保存；配套需后台接受 32hex 并与 0.28 UUID 文本历史数据混存、Agent Studio `ModelRequestIdSchema` 放宽接受 32hex）。tool/ai-code 关联 A1，ACP 通常关联 A2，不跨 A1/A2 混填，服务器不另造主 ID。中间 attempt 的记录/孤儿口径另由 BR-10 确认。
- 进程内 after_turn 没有满足现有时序的纯外部零上游替代；若采用，需选择最小 finalizer 接缝或通用 EventBus 接缝，并在实施前单独 R2 裁决。
- 2026-11-17 性能/生命周期复核：当前真实 after_turn payload 不含稳定 turnId/saved，无 hooks 时 early return；生产 dispatcher 必须显式补这两项并自行纳入 shutdown/delete flush。expected-turn 只保证报文正确，不减少完整文件读取；默认只处理显式当前轮、不做启动历史回放，持久化高水位不是已排除崩溃补报的前置。后续身份复核确认 runner 在 trajectory 激活前已生成 logical/pass，最小可靠路线需经 run-owned 快照传给 finalizer；trajectory disabled 不再默认接受身份缺失，任何路径均禁止 latest `TurnRecord` 回退。集中 lifecycle drain 可覆盖 TUI/ACP/delete/EOF，具体四文件 R2 候选见 N3 节点第14节，尚未批准实施。
- 2026-11-17 责任人确认 ACP 输出硬要求：必须保持 0.28.0 的形态，在最终 `PromptResponse._meta` 中主动携带当前 turn 的 requestId；让客户端另行调用上游 `session/turns` 查询不算满足。上游 b4f354d 已有 session/turn/request-attempt 关联，9cd8031d 已有标准流式文本/推理输出，需复用这些事实，不重新生成 ID；最终响应仍需薄输出接缝，且禁止 session-latest 跨轮取值。
- 2026-11-17 N7 路线继续按暂行 AI 建议采用响应时 live-history 精确选择；UUID 表示历经生成点 UUID 化、UUID 归一化两版暂行后，由 2026-11-18 ID 原值裁决定案：`request_tracking.py` 和 `ids.py` 均不改，全部 ID 原值直用、无转换层。执行中出现问题继续分析讨论，不擅自切换路线；具体实施仍需 design/R2。
- 2026-11-17 责任人明确：新版所有工具记录均去掉 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，不发送 null/0，不补采本地或 provider 时间；B5/P2 同时关闭。独立评审后再次确认，该裁决最终关闭。
- 2026-11-17 独立评审后的责任人裁决：Q2 选择保持桌面端 0.28 能力，N7 必须纳入按 session/turn 的 ACP 输入捕获，恢复 selected Agent 1001 和 desktop channel/IDE/functionName 等上下文；禁止进程级最近值，输入缺失显式降级。该子项不阻塞首个 after_turn 垂直切片。Q4 明确 workflow 不属于本次 telemetry 范围。
- Q5 处理原则：首个 mock 切片期间并行确认 BR-1/5/6；后台关键前提失败时重新评审 N1-A 完整成本。不得把 N1-A 简化为“整体只改 1–2 个上游文件且后台零改动”——它只替代 LLM 搭车通道，final-only、funcId/ai-code、ACP 与公共字段契约仍需单独评估。
- 独立评审新增契约缺口：funcId 以工具执行 ID（T 原值）保留执行实例身份；BR-8 可选 providerCallId 建议已于 2026-11-19 责任人裁决撤销（协议面向多 AI 工具保持通用，模型侧对账由客户端按 T 本地反查完成）；BR-9/BR-10 分别补 cancelled/interrupted 和中间 attempt 口径。B7/B8 最小 DTO 不是字段豁免，须形成 0.28 全字段 parity（含公共字段、parentSpanId 语义、agentName、fileName/value、行数、failureType/funcErrorMessage、language、gitUserName/Email 等）；失败模型零上报/eventSubType=success 的统计差异也须明确。M1-T 必须产出完整矩阵并与 BR-1/5/6 同批确认，未关闭不得判真实联调/上线通过，但不前置阻塞外网 mock 开发。
- D1 和其他文档中的修复/差异描述在未获逐项确认前一律是**建议**，不得因标注“客户端可修复”或“方向明确”而视为责任人已同意。
- N2-E2 近期实验只用于排除 A-final 身份和协议层的方向性阻塞，不扩展为逐字段报文或完整 analyzer 的实现；E3 middleware 仅在回退 exchange 时恢复。
- 2026-11-18 责任人新增上报过滤需求：仅上报 catalog 下发模型（`synced_from_server` 标记）的调用；用户自定义模型的调用及其关联记录（tool/ai-code 按关联 A1、ACP 最终响应按 A2、1001 按首个成功主模型）一律跳过并留 detail 日志，判断 fail-closed（不可判定按自定义）。过滤在各 reporter 出站边界统一实现，纳入批次1范围；分析详见 `research/model-source-filtering.md`。

## 用户场景

1. 责任人提出一个 telemetry 疑问或候选方向，AI 将稳定问题、调查证据、实验结果和开放事项归入对应研究文档，后续会话可直接续接。
2. 与 iCode 团队沟通前，从 `research/upstream-proposals.md` 获取通用性论证、现有机制证据和建议 API 边界，而非提交内部专属字段需求。
3. 某个实施方向收敛后，新实施批次引用本批研究结论，并在自身 design 中重述实际假设、R2 清单、风险和回滚，独立签认和实施。

## 验收标准

- [x] `research/legacy-0.28-telemetry.md` 固化旧版 CLI 的架构、ID 关联、报文、ACP、mock、上游接触面和已知缺陷，供问题分析对照。
- [x] `research/new-version-solution-map.md` 分类新版候选方向、纯文件能力、fork 必要接缝、上游通用建议和降级边界，并链接详细证据。
- [x] `research/solution-space.md` 以可扩展节点/分支图记录技术可行性、责任人裁决、当前倾向、未知项、依赖和下一判别动作，避免将方案空间误当线性路线。
- [x] `research/capability-matrix.md` 覆盖旧版 CLI 的 LLM 搭车/独立报告、tool-detail、技能、ai-code、selected Agent 和 ACP 输出，并同步 A1/A2、B7/B8、run-owned 四文件接缝和当前证据边界。
- [x] `research/request-identity.md` 明确旧 requestId、exchange operation ID、request attempt ID、turn/pass ID 和工具 operation/call ID 的关系，纠正“attempt ID 不能唯一标识模型请求”的过度表述。
- [ ] 所有关键结论区分“源码/测试已核实”“运行实验已核实”“方案建议”“责任人决定”，聊天讨论不冒充正式授权。
- [ ] 每个候选上游建议均有通用使用场景、现有机制不足和不建议的内部专属替代方案。
- [x] 旧版已知缺陷有登记、影响和处理建议；协议限制与可客户端修复缺陷分开，逐项修复/差异仍待责任人确认。
- [ ] 实验记录包含判别标准、实际命令或样本、结果和未证明事项；失败实验同样保留。
- [ ] 当前有效结论已汇总至 `research/review-handoff.md`；待另一 AI 评审后，再由责任人裁决首个 after_turn 垂直切片、后续 ACP 切片的批次边界和 R2。

## 开放问题

- attempt 服务器闭环（2026-11-18 原值裁决）：内外均为最终成功 A-final 的 raw 32hex 原值，原模型记录由后台直接原值保存，独立 LLM 报告、工具和 ai-code 同文本原值关联，无转换层。后台没有多 HTTP 记录细节，不假设 create/retrieve/retry 多行聚合。B7 因责任人暂无法技术决断而委托 AI 制定，开发期暂行采用最小关联 envelope、候选 save 路径和 requestId 单键幂等；后台现网未确认，model/usage/timing 等扩展字段不列为首版必需，实施问题再集中回评。
- requestId 原值口径已裁决（2026-11-18）：所有 ID 保持 raw 32hex 不转换，内部 header/session/trajectory/message 与全部出站同文本，tool/ai-code 的 A1 与 ACP 的 A2 不混用；缺失/非法 A 跳过并不另造 ID。后台 32hex 格式接受/新旧混存与桌面 schema（放宽接受 32hex）验收见 BR-5。
- 工具内部关联已由真实落盘样本验证：call_item_id→C/M→A-final，T/E 交叉校验；rollback 后旧 C 可拒绝。B2/B3 已确认普通本地工具 funcId 的执行实例角色（2026-11-18 原值裁决后 funcId=T 原值 32hex，格式接受列入 BR-5）。B4 已确认 spanId=当前对话 turn ID，本轮模型和工具共用；parentSpanId 仅在真实父子对话关系中填写直接父 turn ID，普通独立 turn 不传，不能取时间上的上一轮或 E/A/T——该父 turn 语义与 0.28 实际用法（父模型调用 llmSpanId）不同，记为 parity 显式差异项；当前对话模型为平面 turn、无真实嵌套 turn 场景，父 ID 持久化仅将来出现该场景时再验证（2026-11-19 澄清）。后台目标需求与验收见 `research/backend-change-requests.md`：单次 final save、组合原子幂等；相同组合不同内容已确认返回明确冲突、不隐式覆盖。B5/P2 已确认三个执行时间字段全部去掉，后台可修改不等于现网已实现。
- B8 暂行采用 AI 方案：责任人表示与 B7 一样暂时没有能力评审并明确委托。首版 ai-code 复用 reportId=T 原值、`(requestId,reportId)` 原子幂等，同 T 多 mutation 跳过，不新增上游 mutationId；tool/ai-code 最小 final DTO、成功不报完整结果正文和严格 mock allowlist 作为开发期契约，后台现网未确认，cancelled/interrupted 继续单列。
- slash 在普通输入、mid-turn、retry/compaction 下如何保证 pass 归属和恰好一次？必要时允许局部输入补采，不使用 session-latest。
- 外部 ACP 内部工具明细已退出当前关注重点；只保留“本地投影不等于远程内部审计”的边界，不据此扩展实施。provider-hosted 按文件重建业务字段，`executionStartedAt`、`executionFinishedAt`、`executionDurationMs` 与其他工具类别一样全部去掉，不再评估时间补采。
- interrupted/cancelled 是扩展后台协议、映射既有状态还是登记差异？不得伪报普通失败。
- ai-code 大方向已关闭：成功 write/edit 可重建 blocks，outcome/参数/blob 边界明确；组合样本和逐字段一致性留实施。
- N9 字段来源已核清：固定运行时/live session/ACP 捕获分工可行，无依据省略；Git 轮末或事件时语义留实施。
- N7 输出已确认：最终 PromptResponse._meta 主动携带当前 turn 的 requestId；复用上游身份与流式支持，禁止 session-latest。责任人暂按 AI 建议采用响应时 prompt_lock 内 live 主 history 精确选择（1 个上游 server 文件+定制 helper），不依赖 N3 registry；执行有问题再分析讨论。Q2 已确认真实桌面输入捕获纳入，恢复 selected Agent 1001/desktop 上下文。
- D1 已完成缺陷、协议限制和设计边界分类；各项修复建议及与旧版不一致的变通需逐项由责任人确认，未确认前不进入实施基线。

详见 `research/open-risks.md`。N3 触发机制和 N5 普通工具/load_skill 的 exchange/attempt 关联不再作为大方向开放问题。
