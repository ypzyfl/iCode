# 后台契约人工确认清单

> 状态：B1–B6、P1/P2 已有确认或明确边界；B7/B8 为责任人委托 AI 制定的开发期暂行方案，后台现网未确认。后台源码位于内网且按规定不可获取，不以客户端源码、mock 或跨端证据代替真实后台答案。
>
> 职责（2026-11-18 精简后）：本文保留**问答原文、裁决事实与委托记录**；由回答推导出的现行契约表述以 `backend-change-requests.md`（BR-x）为唯一权威，本文不再复述。
>
> 2026-11-18 ID 原值裁决：所有 ID 保持原值 32hex、不转 UUID——本文问答原文及要点中的 `UUID(T)`/`UUID(A)` 等 UUID 形态表述均按"原值 32hex"理解，现行口径见 `backend-change-requests.md` BR-5。

## 已有口径，不重复询问

- 客户端上报什么，服务器就记录什么；需将这一原则落实到 B1 的具体 requestId 字段。
- 后台没有同一逻辑调用 create/retrieve/retry 多 HTTP 记录细节，不要求新增多 HTTP 行聚合。
- 原模型业务记录与独立 LLM telemetry 报告必须合并，不能相互替代。
- 有序 best-effort、允许孤儿，不等待严格 ACK 才能发送依赖数据。

## A. 请后台确认的六个问题

### B1：原模型调用成功记录的 requestId 到底取自哪里？

请确认原大模型调用接口在成功响应落库时：

1. `requestId` 是否直接使用客户端请求头 `Chrys-Request-Attempt-Id` 的原值；
2. 是否会经过服务端重新生成、格式转换或映射；
3. SDK retry/redirect/Responses retrieve 后，是否保存实际返回最终成功响应的那个 attempt。

提问时的原始期望路线：原成功记录 requestId=A-final，独立 LLM 报告、tool-detail 和 ai-code 使用同一文本；该表述已在后续讨论中细化，不再代表内外部必须同文本。若服务端另造无关联的 requestId，当前 attempt-first 关联前提需要重评。

**B1 回答（2026-11-16，责任人确认）**：0.28.0 从请求体 `telemetry.requestId` 取值，服务器不重新生成或转换；新版可以改为读取 `Chrys-Request-Attempt-Id`，也可按需加工成 UUID。后台此前未关注 SDK retry、redirect、Responses retrieve。

约束结论已提炼入 `backend-change-requests.md` BR-1（2026-11-18 责任人修订：服务器不做成功判定，每条请求记录保存自身 attempt，成功语义由独立 LLM 报告 join 命中声明——本问答原文作为历史记录保留）。

**B1 UUID 表示补充裁决（2026-11-17，责任人确认）**：后台当时可配合 UUID 归一化类改动（客户端内部保持 raw 32hex、后台原模型记录归一化、其他入口按外部 UUID 原值保存）。

> 2026-11-18 ID 原值裁决：所有 ID 保持原值 32hex、不转 UUID，上述归一化安排作废；现行口径见 `backend-change-requests.md` BR-5。

### B2：tool-detail save/update 的实际匹配键和 funcId 外部用途是什么？

先区分三个字段：

| 字段 | 含义 | 为什么不能单独标识一次工具执行 |
|---|---|---|
| requestId | 产生工具调用的成功模型响应；当前暂定为 M 的 A-final | 同一 M 可产生多个工具，全部共享 requestId |
| funcName | 工具名称/展示名称，例如 write、read、load_skill；外部 ACP projection 可能只是 title | 同名工具可执行多次，不是唯一键 |
| funcId | 一次工具执行的外部实例 ID；旧 CLI 为 `provider_call_id or event.call_id` | 是 save/PENDING/final 的匹配候选，但旧 provider ID 可能重复 |

此前“用什么唯一标识工具调用”的客户端结论不变：内部以 C 定位 function_call occurrence、T 标识实际 dispatch，再经 M 获得 A-final；普通本地工具推荐对外 funcId=UUID(T)。B2 是在确认后台是否接受这个外部角色，不重新讨论内部主链。

旧客户端实际流程：

```text
save：携带 requestId + funcName + funcId，创建工具记录
PENDING update：只带 funcName + funcId + 结束时间/耗时，不带 requestId
final update：只带 funcName + funcId + 结果/状态等，不带 requestId
```

旧 mock 先按 funcName 找记录、再校验 funcId；这只是客户端配套 mock 的逻辑，不能据此断言真实后台使用相同索引或 SQL。

示例：同一成功 M 连续执行两次 write，则 requestId 相同、funcName 相同，只有 funcId 不同，所以 funcId 必须区分两次执行。若不同 M 复用同一 provider call_id，旧 funcId 也会重复，而旧 update 又不带 requestId，这就是推荐 UUID(T) 的原因。

请后台把 B2 拆成三个具体答案：

1. **B2a save 创建规则**：save 是始终插入新记录，还是按 requestId+funcName+funcId 等条件查重/覆盖？这些字段哪些必填？
2. **B2b update 定位条件**：PENDING 和 final 实际按什么条件找到待更新记录？请给出等效伪 SQL/WHERE 条件，例如 `funcName+funcId`、仅 `funcId`，还是 `requestId+funcId`。若使用 requestId，新版 update 需要携带它，旧报文则没有。
3. **B2c funcId 是否还有其他消费者**：除同一次执行的 save/update 外，后台/UI 是否用 `funcId = 模型响应 tool_calls[].id/provider call_id` 做交叉查询、卡片合并或结果匹配？

分支判断：若 B2c 为否，funcId 可进入 UUID(T) 的格式/唯一性确认（B3）；若 B2c 为是，不能直接改用 UUID(T)，需要保留 provider call_id、增加独立 providerCallId/映射，或由责任人重新裁决关联协议。

**B2 回答（2026-11-16，责任人确认）**：save 是插入新记录；PENDING/final update 的等效条件均为 `WHERE func_id = ?`；除 save/update 外，没有任何后台/UI 位置要求 funcId 等于模型响应 provider call_id。

**结论**：funcId 外部执行实例角色确认、UUID(T) 无 provider 交叉查询障碍；save 插入语义与全局唯一要求的现行契约见 `backend-change-requests.md` BR-2/BR-3。

### B3：是否接受 UUID(T) 作为 funcId，唯一性和重复语义是什么？

候选 funcId 是普通本地工具 tool operation ID 的 32hex 无损 UUID 文本，每次 dispatch 唯一，save/PENDING/final 和 after_turn 重放保持不变。

请确认：

1. 是否接受与 provider call_id 不同的 36 字符 UUID 文本；长度、字符集、必填约束是什么；
2. 由于 update 仅按 func_id 定位，funcId 必须全局唯一；数据库是否有全局唯一索引，没有索引时如何防止重复；
3. 若仍出现相同 funcId，不同 requestId 的 save/update 会覆盖、拒绝还是产生重复记录；
4. UI/报表是否对 funcId 格式有额外假设。

**B3 回答（2026-11-16，责任人确认）**：后台 funcId 没有格式要求，接受 36 字符 UUID，只要唯一即可；没有全局唯一索引，完全依赖客户端保证全局唯一。相同 funcId 重复 save 会插入新的重复记录；若已有两条相同 funcId，PENDING/final 按 func_id 更新全部。后台全部逻辑的基础都是客户端保证 funcId 全局唯一。

**结论**：`funcId=UUID(T)` 获得格式与角色契约支持（36 字符 UUID、无全局唯一索引、重复 save 插重复行且 update 全部——客户端必须同一 T 至多 save 一次、不盲目重试，不做崩溃/强杀补报与启动扫描重放）。单次 final save + 组合原子幂等的现行契约见 `backend-change-requests.md` BR-2/BR-3。

### B4：spanId 和 parentSpanId 的 turn 归属与父子语义是什么？

**B4 初步回答（2026-11-16，责任人确认）**：后台不强制字段，无值时实践是不传字段；但 spanId 一般不应为空，顶层 turn 的 parentSpanId 可为空，非顶层 turn 不应为空。parentSpanId 无明确 `sp-` 格式规范，目前没有外键、查询关联或 UI 跳转依赖，表现像普通字段。其真实用途是组织 span tree，错误省略会影响统计、筛选或报表。

**B4 概念澄清（2026-11-16，责任人确认）**：

1. turn 是**一轮对话**，包含至少一次模型调用和零次或多次工具调用；turn ID 用于关联属于该轮的全部模型和工具内容。
2. 每条模型或工具记录的 `spanId = 当前对话 turn ID`；同一 turn 的模型和工具共用该值，不为模型或工具另造节点 span ID。
3. `parentSpanId = 当前 turn 的直接父 turn ID`，只在真实存在父子对话关系时提供。真实非顶层 turn 不应省略；独立 turn 及其模型、工具记录均不传该字段。
4. 同一 session 的普通对话轮通常彼此独立，没有父 turn。**时间上的上一轮不是父 turn**，不能仅因存在前一轮就填写 parentSpanId。
5. parentSpanId 不是 E、A-final、T、provider call_id、父模型调用或委派工具 ID；不再需要从这些内部 ID 中选择或派生父节点。

**结论**：B4 概念语义已关闭（spanId=当前对话 turn ID；parentSpanId 仅为真实直接父 turn，独立 turn 不传，不从 E/A/T 派生）；现行契约表述见 `backend-change-requests.md` 第 1 节。**2026-11-19 补充澄清**：该语义与 0.28 实际用法（工具记录 parentSpanId=父模型调用 llmSpanId 的三层 span 结构）不同，记为 0.28 parity 显式差异项；两版对话模型均为平面 turn、当前无真实嵌套 turn 场景，父 turn ID 持久化仅在将来出现该场景时再验证。

### B5：工具起止时间和 duration 是否可省略？（已确认：三个字段全部去掉）

**B5 最终裁决（2026-11-17，责任人确认）**：新版 tool-detail 不再需要 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，三个字段全部去掉。该决定适用于本地工具、provider-hosted、local/外部 ACP 等所有新版工具记录，不只是允许 hosted 缺省。

因此此前“能否为空、与默认 0 的差异、是否补采本地观察时间”三个问题均失效：新版不发送这些字段，不发送 null/0，不补采本地展示时间或 provider 真实执行时间，也不为这些字段增加捕获接缝。旧版报文说明继续作为历史基线保留。P2 的 hosted 产品接受度由本决定一并关闭。

### B6：save/update 的幂等和乱序语义是什么？

after_turn 会对同一持久化事件做有序尝试，但重放、网络失败和 best-effort 仍可能产生重复或缺失。请确认：

1. 相同 funcId 重复 final update 是否幂等；
2. 没有 Start/PENDING、只有 final 时是否接受；
3. final 之后又收到 PENDING 时如何处理；
4. **已由 B3 回答**：相同 funcId 重复 save 插入重复记录，后续 update 更新全部；客户端必须 save-once；
5. 是否要求 Start 和 Result 必须使用不同 HTTP 状态流转，还是允许 after_turn 连续发送。

**B6 当前行为回答（2026-11-16，责任人确认）**：final-only 更新 0 条并返回错误/失败；重复 final 虽写入相同值，但会改变完成时间、状态或其他字段，无审计/计数副作用，因此不是严格幂等；final 后收到 PENDING 会把终态重新改回 PENDING；后台建议避免极短时间内连续 save→PENDING→final，可考虑合并成一个 save。后台另提出 save/update 可改为按 requestId+funcId 组合处理以降低重复可能性。

**AI 推荐**：after_turn 在工具结束后才发送，PENDING 没有实时观测价值——推荐每个工具执行只发送一条包含最终状态和结果的 final snapshot save，消除 final-only、终态回退、重复 final 和短间隔连发问题；`(requestId,funcId)` 组合键是防御性幂等增强，不替代客户端身份纪律。

**目标态回答（2026-11-16，责任人确认）**：三项均可支持（单次终态 save、`(requestId,funcId)` 原子幂等、重复终态语义），"即使现在不可以，也可以修改"；session 事后分析没有必要复制实时状态。相同组合不同最终内容返回明确冲突（409）亦已确认。目标契约与验收用例见 `backend-change-requests.md` BR-2/BR-3/BR-4，不代表现网已实现。

### B7：独立 LLM endpoint、最小 DTO 与幂等键（2026-11-17 暂行采用 AI 方案）

旧搭车报文没有 model/usage/timing/error 字段，旧 mock 也没有独立 LLM endpoint，新增协议不能从旧实现反推。责任人表示相关知识不足、暂时没有能力决断，明确要求按 AI 判断制定方案并记录该情况。开发期暂行契约要点：`POST /csas/telemetry/api/v1/llm-report/save` 单对象；最小 envelope（schemaVersion/sessionId/eventType=llm/eventSubType=success/requestId 必填，span/parent 按真实关系条件携带）；requestId 单键原子幂等（语义重放 200、同键不同内容 409、非法 400）；首版不要求 model/response/usage/timing/outcome/runtime，待原模型成功记录实际覆盖明确后再扩展；golden 复用 BR-5 双向样例。

**边界**：这是责任人委托 AI 制定的开发期技术方案，不证明后台现网支持该路径或存储语义，不构成正式实施/R2 批准；正式契约不同或 mock/客户端实施发现问题时集中回评，不在多个出口各自补丁。完整字段表、最小报文示例与验收见 `nodes/llm-report-transport.md` 第 9 节与 `backend-change-requests.md` BR-6。

### B8：tool-detail/ai-code 最小 final DTO 与 ai-code 幂等键（2026-11-17 暂行采用 AI 方案）

责任人表示与 B7 一样暂时没有能力评审，明确委托 AI 制定。当前 write/edit 每次 dispatch 只有一个 file_mutation，通用 shell/隐式工具可一个 T 多 mutation 且 FileMutation 无 mutation_id——首版不新增上游 mutation 身份。开发期暂行契约要点：ai-code `reportId=T 原值`、`(requestId,reportId)` 原子幂等，同 T 多候选 mutation 全部跳过并记录身份粒度不足；两类最小 final DTO 字段集与严格 allowlist mock（语义重放 200、同键不同内容 409、非法 400，未知字段不静默通过）；tool-detail 成功只报 codeStatus=1、不新增结果正文；BR-8 已撤销（2026-11-19，报文不含 providerCallId），BR-9 cancelled/interrupted、BR-10 中间 attempt 另列。

**边界**：与 B7 相同——委托 AI 制定的开发期暂行契约，不代表现网后台支持，不构成正式实施/R2 批准；实际后台契约返回或实施发现身份粒度/字段兼容性问题时重开，集中调整 mock、客户端和文档。完整字段、golden 示例与负例见 `nodes/ai-code.md` 第 9 节、`nodes/tools-and-skills.md` 11.6 与 `backend-change-requests.md` BR-7。

## B. 请责任人确认的两个产品决策

### P1：ACP requestId 能否仅由客户端查询获得？（已确认）

**不能。**责任人于 2026-11-17 明确必须保持 0.28.0 的形态，在最终 `PromptResponse._meta` 中主动携带 requestId。上游 `session/turns` 可复用为 requestAttemptId/turnId 的数据来源，但不能替代最终响应自包含身份；仍需 ACP 输出接缝。外部 ACP 内部工具明细不再作为 P1 焦点。

### P2：provider-hosted 是否接受省略工具时间？（已确认）

**P2 最终裁决（2026-11-17，责任人确认）**：不仅 hosted 可以省略，新版所有工具记录都去掉 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`。不新增 hosted presentation 或本地 translator 时间捕获接缝，也不请求 provider/上游补时间真值。
