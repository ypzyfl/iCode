# 新版 Telemetry 后台协调需求

> 状态：BR-1–BR-5 已确认可支持或协调修改（**BR-1 于 2026-11-18 语义修订**：服务器不做成功判定、每请求存自身 attempt，成功由独立报告 join 声明，后台义务减轻；**BR-5 于 2026-11-18 再修订**：所有 ID 保持原值 32hex、不转 UUID）；BR-6/BR-7 因责任人暂时无能力技术评审而委托 AI 制定开发期暂行契约；**BR-8 已于 2026-11-19 责任人裁决撤销**（协议通用性，对账端侧完成），BR-9/BR-10 为待后台确认项，**均不是后台已确认能力**。本文记录 after_turn + 全 session 分析所需的后台目标契约，不代表现网已经实现。B4 turn/parent turn 概念语义已确认；B5/P2 已确认 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs` 全部去掉，并经责任人再次确认最终关闭。总览见 `review-handoff.md`。

## 1. 适用范围与身份约定

新版客户端在 turn/pass 完成后分析 session 目录，只上报最终事实，不重放工具执行过程中的实时状态。turn 是一轮对话，包含至少一次模型调用和零次或多次工具调用；同一 turn 的模型和工具记录共用该 turn ID。

requestId 采用原值表示（2026-11-18 责任人裁决）：客户端内部与全部上报出口均使用既有 raw 32hex 原值，**不转换 UUID**。后台原模型记录直接保存 attempt header 原值；独立 LLM/tool-detail/ai-code/ACP 使用同文本原值。全局唯一性由客户端 128-bit 随机 ID 保证；配套要求 Agent Studio `ModelRequestIdSchema` 放宽接受 32hex（原 `z.string().uuid()` 会拒绝原值）。不要求修改上游 request 生成器或 trajectory 校验器。

普通本地工具：

```text
requestId    = 产生工具调用的成功 M 的 raw A-final 原值（32hex）
funcId       = tool operation ID 原值（32hex）
spanId       = 当前对话 turn ID 原值（32hex）
parentSpanId = 直接父 turn ID 原值；仅真实存在父子对话关系时提供
              （当前平面 turn 场景总是省略；语义与 0.28 父模型调用 span 不同，见第 7 节差异项）
```

同一 session 的普通对话轮通常彼此独立，独立 turn 及其模型、工具记录均不传 parentSpanId；不能把时间上的上一轮当作父 turn。真实非顶层 turn 必须使用直接父 turn ID，不得改用 E、A-final、T、provider call_id 或委派工具 ID。

后台已确认：funcId 无 provider call_id 交叉查询，接受 36 字符 UUID；2026-11-18 原值裁决后 funcId 为 32hex 原值，格式接受列入 BR-5 确认点。客户端负责生成全局执行实例 ID。后台组合键用于幂等，不替代客户端身份纪律。

## BR-1：原模型调用记录保存每次请求自身的 attempt header（不做成功判定）

> **2026-11-18 语义修订（责任人裁决）**：服务器端无法可靠判定哪次请求"实际成功"（HTTP 200+业务错误、流中断、Responses pending 等场景判定需理解模型 API 业务语义），成功判定权归客户端。本节取代此前"成功记录保存实际成功请求的 attempt"的表述；2026-11-16 的口头确认按本版语义执行。

新版原大模型调用接口不再从请求体 `telemetry.requestId` 取主 ID，而是在每个 HTTP 请求中读取：

```text
Chrys-Request-Attempt-Id
```

要求：

1. 服务器对每个到达的模型调用请求，将该次请求**自身的** attempt header 原值落库到该次请求的记录（格式与原值要求见 BR-5）；**不做"哪次是实际成功"的判定、挑选或聚合**；
2. 服务器不重新生成逻辑 requestId，不跨请求缓存或复用其他请求的 attempt；
3. 不需要识别 SDK retry、redirect、Responses retrieve，不需要聚合全部 attempts；
4. 失败、pending、流中断等中间请求按既有日志规则照常保留，各带自己的 attempt，不参与成功合并，口径归 BR-10；
5. **成功语义由客户端声明**：独立 LLM 报告（BR-6）携带 A-final 原值，查询/分析以 `报告.requestId == 记录 attempt` join，命中的那条记录即该逻辑调用的成功记录。SDK retry 场景 join 命中最终成功请求、Responses 场景 join 命中最终 retrieve，均由客户端报告取值决定，服务器无需理解这些机制；
6. 所有记录使用同一 attempt 原值（32hex），后台原值保存，不转换。

**2026-11-18 原值裁决**：所有 ID 保持原值不转 UUID，客户端不引入转换 helper，后台不承担归一化。

## BR-2：tool-detail 支持单次 final snapshot save

新版 after_turn 每个工具执行只发送一次 save，直接形成终态记录，不再发送 PENDING/final update。

save 需能够接收并保存：

- requestId、funcId、funcName；
- 最终 codeStatus；
- 成功结果或失败信息；
- 新版最终参数及其他 final 字段。

要求：

1. save 后直接得到最终成功/失败等终态，不要求经过 PENDING；
2. 所有新版工具记录均不携带 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，不发送 null/0，也不以 save 接收时间、本地观察时间或 provider 时间替代；
3. 模型成功后工具失败仍是有效终态记录，工具 outcome 与模型 A-final 独立；
4. 新版路径不需要 final-only update，也不存在 final 后 PENDING 回退问题；
5. 后台可保留旧实时三阶段协议兼容其他客户端，本需求不要求废除旧路径。

## BR-3：以 `(requestId, funcId)` 提供原子幂等

目标语义：

```text
第一次 final save：插入一条终态记录
相同组合、相同内容的重复 save：不新增记录，返回成功/已存在
并发收到相同组合：仍只能形成一条记录
```

实现要求：

1. 对 `(requestId, funcId)` 建立数据库唯一约束，或提供等效原子 upsert/insert-if-absent；
2. 不能只先查后插，也不能只把 update 改为组合 WHERE 而保留普通重复插入；
3. 若保留 update，新版 update 报文必须携带 requestId，并按 `(requestId,funcId)` 定位，避免仅 func_id 更新全部重复行；
4. 同一 M 的多个工具共享 requestId、具有不同 funcId，必须分别形成记录。

后台实现幂等后，客户端可对**相同最终报文**进行安全重试；重试不再依赖服务器响应是否恰好到达。业务上仍是一次工具执行，传输上的重复由组合键去重。

## BR-4：重复终态的内容、状态和冲突语义

### 相同组合、相同最终内容

要求：

- 不改变首次确认的最终 codeStatus、结果或其他终态字段；
- 不增加重复审计/计数记录；
- 返回幂等成功或已存在；
- 三个执行时间字段在新版报文和记录中均不存在，不涉及时间保留或覆盖。

### 相同组合、不同最终内容

**责任人已于 2026-11-16 确认采用冲突策略**：返回明确冲突（例如 HTTP 409），不隐式覆盖原记录，并记录可诊断原因。相同 T 的 after_turn 重放应产生确定性报文；不同内容通常意味着客户端分析错误、数据版本变化或人工纠正，应显式处理，而不是静默 first-wins/last-wins。

该策略不允许终态隐式回退，也不允许未经审查修改字段。若将来需要人工纠正数据，应另立协议明确可改字段和审计证据，不属于当前幂等 save 路径。

## BR-5：ID 原值保存（2026-11-18 责任人裁决）

> 2026-11-18 责任人裁决：**所有 ID 保持原值（32hex）、不转 UUID**（此前短暂的 UUID 归一化安排已被取代，演进过程见 `../verification.md`）；原转换规则、golden 双向断言与 UUID4 version 验收作废。

要求：

1. 原模型调用记录直接保存该次请求 `Chrys-Request-Attempt-Id` 的原值（配合 BR-1 每请求存自身值，不做成功判定）；
2. 独立 LLM/tool-detail/ai-code 等入口：requestId/funcId/reportId/spanId/parentSpanId 均为原值 32hex，后台按原值保存，不另造、不转换、不截断；
3. 全局唯一性由客户端保证（上述 ID 均为 128-bit 随机值，工程上满足全局唯一）；
4. 后台确认点：①各入口/库表/校验接受 32hex 文本（无 UUID 格式强制、无长度/字符集限制）；②与既有 0.28 UUID 文本格式历史数据**新旧混存不冲突**（不要求迁移，不要求同格式）；③查询、合并、`(requestId,funcId)`/`(requestId,reportId)` 组合幂等统一使用原值文本；④缺失/非法（非 32hex）输入不另造 ID，按协议错误处理并保留诊断。

### 客户端/其他配合点

- after_turn 内部 C/M/T/E/A join、session/trajectory 存储与全部出站 DTO 使用同一原值，**全程无转换、不引入 UUID helper**；
- N7 从 live history 选得 raw A 后直接用于最终 ACP envelope；`app/acp/server.py` 只承担最终响应合并，不修改 request 生成或 trajectory ID 校验；
- `request_tracking.py`、`foundation/trajectory/ids.py`、通用 `new_analytics_id()` 及 operation/turn/item ID 均不变；
- **桌面配套**：Agent Studio `ModelRequestIdSchema`（现为 `z.string().uuid()`）放宽接受 32hex 原值——ACP 最终响应 `_meta` 携带原值，schema 不改会拒绝（客户端侧自行落实，列入 N7/批次2 范围）。

简化收益：删除整个转换层——无归一化函数、无双重转换与漂移风险、内外同文本。

## BR-6：独立 LLM final 报告 endpoint（B7 暂行契约）

候选 endpoint：`POST /csas/telemetry/api/v1/llm-report/save`。

最小 envelope 为 `schemaVersion/sessionId/eventType/eventSubType/requestId`，span/parent 按真实关系携带；首版不强制 model/response/usage/timing/runtime 等扩展字段。每个成功模型响应形成一条 final 报告，requestId=该响应的 raw A-final 原值（32hex）。**独立报告同时是成功语义的唯一声明源**（2026-11-18 BR-1 修订）：哪条原模型记录被报告 join 命中，哪条即该逻辑调用的成功记录——BR-6 与 BR-1/BR-5 构成 P0 绑定，任一缺失 join 都不成立。最小 envelope 不等于最终字段豁免：须先确认原模型记录实际保存哪些 channel/pluginVersion/projectName/Git 等字段，缺失部分由独立报告或明确的差异决策补齐，并逐字段验收。

幂等要求：requestId 单键原子幂等；相同键相同内容返回 200 且不新增，相同键不同内容返回 409，非法输入返回 400。实现需数据库唯一约束或等效原子 upsert，不能只先查后插。该契约由责任人委托 AI 制定，现网是否支持尚未确认。

## BR-7：ai-code final DTO 与 reportId 幂等（B8 暂行契约）

普通工具按 BR-2–BR-4 使用七项必填 final DTO 与 `(requestId,funcId)` 原子幂等。ai-code 最小字段为 `reportId/requestId/sessionId/spanId/filepath/blocks/sourceType/inputMethod/codeStatus`，其中 requestId=A1 原值、reportId=T 原值（32hex）。两类 DTO 的公共字段/userId 等仍须进入 0.28 逐字段 parity，不因“最小”而默认删除。

后台以 `(requestId,reportId)` 建立数据库唯一约束或等效原子 upsert；同键同内容 200 且不新增，同键不同内容 409，非法输入 400。当前 write/edit 单 T 多 mutation 时客户端跳过整项，不共享幂等键上报多条，也不新增上游 mutationId。严格 allowlist，未知字段和三个执行时间字段不静默通过。该契约同样属于 B8 委托 AI 的开发期暂行方案，现网未确认。

## BR-8：tool-detail 保留模型 toolUseId 对账原值（**2026-11-19 责任人裁决撤销**）

> 曾为独立评审发现后的 AI 建议（新增可选 `providerCallId` 字段）。责任人裁决撤销，理由：后台上报协议面向多个 AI 工具，其他工具没有 providerCallId 这一项，不应为 iCode 特有对账需求增加协议字段；**对账职责在端侧完成**——通过 funcId（T）可在客户端 session/trajectory 中反查对应的 providerCallId 与工具调用信息（function_call 同条保存 call_id 原值与 T），服务器无需该字段。撤销后 tool-detail 报文不含 providerCallId。

## BR-9：cancelled/interrupted 终态映射（待确认）

后台需明确取消的工具记录使用何种 codeStatus/failureType，或明确不支持并登记差异。不得将 interrupted 归成功，也不得未经确认一律映射普通失败。三个执行时间字段仍全部删除，取消协议不重开时间补采。

## BR-10：中间/失败 attempt 的记录与孤儿口径（待确认）

A-final 关联不要求后台聚合全部 HTTP attempts；但若网关本身会保存 SDK retry、redirect、Responses create/pending 或失败 attempt，需明确这些记录是否落库、如何标记、是否保留及如何纳入孤儿分析/清理。该口径不改变成功关联由独立报告 join 声明（BR-1），也不允许客户端把失败 attempt 当成成功 telemetry 上报。

## 5. 验收用例

1. **单次终态**：无 Start/PENDING，直接 final save 后形成正确终态记录。
2. **顺序重复**：同一 final save 重试多次，仅一条 `(requestId,funcId)` 记录，终态字段不变。
3. **并发重复**：并发发送相同 final save，仅一条记录，无先查后插竞态。
4. **响应丢失重试**：首次插入成功但响应丢失，客户端重试相同报文，不产生重复记录。
5. **同模型多工具**：相同 requestId、不同 funcId 形成各自记录，不相互覆盖。
6. **冲突报文**：相同组合但不同终态内容按约定返回冲突或执行明确纠正策略，不隐式改状态或其他终态内容。
7. **A-final retry**：同一 exchange 内 raw A 失败、A-final 成功：失败与成功两条记录各存自身 attempt 原值；独立报告带 A-final 原值，join 只命中成功那条；工具/ai-code 只在它们确由该 A-final 产生时关联它，不能把历史工具改挂到重试后的最终模型响应。
8. **Responses continuation**：create raw A1 pending、retrieve raw A2 成功：两条记录各存 A1/A2 原值；独立报告带 A2 原值，join 命中 retrieve 记录而非 create 记录；任何依赖记录必须按其真实产生模型调用关联，不得机械跟随最后 A。
9. **并发不串号**：不同模型请求和工具并发上报时，requestId/funcId 不跨记录串用，原值文本不串用输入。
10. **ID 原值一致性**：客户端与后台对固定 raw 向量逐字节保存相同 32hex 原值文本，全程无转换；非法输入（非 32hex）被拒绝。
11. **原记录/报告 join**：原模型请求携带 raw header，后台原值落库；独立 LLM/tool-detail/ai-code 上报同一原值，查询能合并为同一模型调用及其实际工具/代码结果，不产生格式不一致的键。
12. **外部入口原值保存**：独立报告和工具/ai-code 入口收到 32hex 原值后不重新生成、不改格式；组合幂等键与查询使用该值。
13. **缺失/非法 raw**：模型请求缺 header 或 raw 非 32hex 时，该请求记录不另造逻辑 requestId，不产生无法关联的随机 ID，返回/记录符合既有协议的明确错误或缺失诊断。
14. **A1/A2 身份分工**：同一 M 的独立报告与其产生的工具/ai-code 使用相同原值；多主模型调用时工具仍挂实际产生它的 A1，最终 ACP envelope 通常使用最后主响应 A2，不被工具关联反向改变。另设 A1=A2 和 A1≠A2 两个 golden，防止偶然同键掩盖错误。
15. **真实桌面 schema**：Agent Studio `ModelRequestIdSchema` 放宽接受 32hex 后，raw 原值通过 `safeParse`，且 request_identified 与后台 requestId 同文本。
16. **执行时间字段缺席**：本地、hosted、local/外部 ACP 各类新版 final DTO 均不包含 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，也不存在对应 null/0 或替代时间字段；重放报文同样不包含。
17. **独立 LLM 幂等**：BR-6 同 requestId 同内容并发/重放仅一条且返回 200；不同内容 409，非法输入 400。
18. **ai-code 幂等**：BR-7 同 `(requestId,reportId)` 同内容仅一条；不同内容 409，同 A 多工具/多合法 ai-code 记录不互相覆盖。
19. **严格 DTO**：tool/ai-code 未知字段、缺必填字段和三个时间字段按约定拒绝或明确降级，不静默吞掉。
20. **模型 toolUseId 对账（端侧）**：BR-8 已撤销，服务器不存 providerCallId；如需核对工具记录与模型响应的对应关系，由客户端按 funcId=T 在本地 session/trajectory 反查 providerCallId 完成（function_call 同条保存 call_id 原值与 T）。
21. **取消协议**：按 BR-9 最终确认的组合验证 cancelled/interrupted，不归成功、不擅自伪报普通失败；若不支持则形成明确差异记录。
22. **中间 attempt 口径**：构造 SDK retry 和 Responses pending/retrieve，核对 BR-10 的落库、标记、保留与孤儿治理；join 声明的成功记录与独立报告使用同一 A-final 原值，失败/中间记录不参与成功关联。
23. **0.28 全字段 parity**：对原模型记录、独立 LLM、tool-detail 和 ai-code 逐项检查 channel/pluginVersion/projectName/Git/userId，以及 parentSpanId 语义、agentName、fileName、value、originalLines/addedLines/deletedLines、failureType/funcErrorMessage、language、gitUserName/Email 等旧字段；所有保留/删除/待确认均有依据，不因最小 envelope 静默缺失。M1-T 必须产出完整矩阵，并与 BR-1/5/6 同批确认；未关闭不得判定真实联调或上线验收通过，但不前置阻塞外网 mock 开发。
24. **桌面输入与 1001**：ACP 输入按 session/turn 捕获 selected Agent 与 desktop 上下文，1001 在 after_turn 以 `(sessionId,logicalTurnId)` 去重发一条 save-only 记录、无 T，并关联当前 logical turn 首个成功主模型 A-final；无成功或输入缺失时跳过。并发 session 不串值，不读进程级最近值。

## 6. 客户端对应义务

- 内部 requestId 始终使用产生工具/代码修改的成功 M 的 raw A-final，缺 A-final 或 raw 非法时跳过并记录原因；
- 独立 LLM/tool-detail/ai-code/ACP 直接使用与内部 join 相同的原值（32hex），全程无转换、不引入 UUID helper（2026-11-18 原值裁决）；
- 普通本地工具 funcId=T 原值（32hex），同一 dispatch 重放保持一致，不同 dispatch 不复用；providerCallId 不入报文（BR-8 撤销），需要时由客户端按 T 本地反查；
- 每次工具执行只构造一个确定性 final snapshot，不发送 PENDING/final update，不构造或发送三个执行时间字段；
- 相同 T 的重试必须保持报文内容一致；不同内容不得冒充相同重放；
- provider-hosted 没有本地 T，外部 ACP 内部工具按 P1 决策处理，不能伪造 T；
- 不修改 `request_tracking.py`、`ids.py` 或通用 analytics ID 生成/校验，不引入任何 ID 双表示；
- 不做崩溃/强杀后的启动扫描补报，不借后台幂等扩大新版覆盖范围；workflow 明确不在本次范围内；
- ACP 按 session/turn 捕获 selected Agent 与 desktop 输入上下文，禁止进程级最近值；输入缺失时显式降级。

## 7. 尚未关闭的事项

- parentSpanId 已按 B4 澄清重定义为"真实直接父 turn ID"语义，与 0.28 实际语义（工具记录挂父模型调用 llmSpanId 的三层 span 结构）不同——记为 0.28 全字段 parity 的**显式差异项**；当前对话模型为平面 turn、无真实嵌套 turn 场景，普通独立 turn 不传该字段，父 turn ID 持久化仅在将来真实出现嵌套对话场景时再验证（2026-11-19 责任人澄清）；
- 2026-11-18 原值裁决（所有 ID 不转 UUID）；BR-5 的 32hex 格式接受、新旧格式混存、原记录/报告 join 和 Agent Studio schema 放宽尚待确认/落实与联调验收；
- BR-6 独立 LLM endpoint/envelope/requestId 幂等和 BR-7 ai-code reportId/组合幂等均为 B7/B8 委托 AI 的暂行契约，后台现网与真实原子行为尚未确认或验证；
- BR-8 providerCallId 已于 2026-11-19 责任人裁决撤销（协议通用性，对账端侧完成）；BR-9 cancelled 映射和 BR-10 中间 attempt 记录口径待后台确认；公共字段 parity 与原模型记录实际字段也未闭环；
- Q2 已确认保持桌面 0.28 能力，ACP 输入捕获/1001 纳入实施；Q4 已确认 workflow 退出范围；N1-C 关键后台前提失败时重新评审 N1-A 完整成本，不预设自动回退；
- P1 已确认：最终 PromptResponse._meta 必须主动携带当前 turn 的 requestId，客户端另查 session/turns 不满足；外部 ACP 内部工具明细不再作为当前开放项；
- B5/P2 已关闭：三个执行时间字段全部去掉，不再有待确认的时间容忍度或产品接受度分支。
