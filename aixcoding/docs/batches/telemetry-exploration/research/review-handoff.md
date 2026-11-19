# Telemetry 探索当前结论与评审交接

> 截至 2026-11-17。本文是交给后续评审 AI 的**当前有效结论入口**，只汇总已探索方案、推荐路线、风险、外部依赖和未证明事项；详细证据以链接专题为准。
>
> 当前状态（2026-11-19 更新）：主要方向性调查和独立评审/复审已收敛；责任人已裁决实施组织（三个开发批次 + `feat/telemetry-session-analysis` 集成分支，mock 归属批次1，见 `../plan.md` 实施策略节）；探索批次已签认（2026-11-17），后续裁决依次落盘：BR-1 语义修订（服务器不做成功判定）、ID 原值裁决（全部 ID 保持 32hex 不转 UUID）、上报过滤需求（仅报 catalog 下发模型）、BR-8 撤销（不新增 providerCallId）、parentSpanId 语义差异项澄清。当前停等探索批次独立 PR（Git 逐条授权），其后进入批次1 requirements/design/R2。**本文不是实施 design，不授权上游修改或 Git 写操作。**

## 1. 执行结论

在已经确认的非实时、有序 best-effort、允许孤儿、缺证据降级和不做崩溃补报的范围内，**正常主 Agent 主链没有发现被证明无法实现的方向性阻塞**。当前主要缺口是生产实现和端到端证据，而不是还需要继续泛化调查：

- 尚无生产 after_turn dispatcher、reader、reporter、owner 或 telemetry mock 存储；
- 五类外部记录尚未在真实生产中保存并 join；
- 真实 ACP server × Agent Studio 桌面闭环未完成；
- 真实内网后台、数据治理和全量异常矩阵仍是后续验收门禁。

因此建议停止扩大只读调查，先由另一 AI 评审本文及引用证据；评审收敛后按最小垂直切片开工。

## 2. 需求范围与硬边界

### 当前目标

- 以 0.28.0 AIxCoding 实际行为为基线，在 0.35.2 上重建 CLI telemetry 与最终 ACP 身份输出。
- 以整个 session 目录联读为主，业务分析、报文和投递优先放定制目录；上游改动必须少且集中。
- 只记录成功模型调用；失败、pending、部分流不得借历史成功身份。
- 最终 `PromptResponse._meta` 必须主动携带当前 turn 的 requestId，不能要求桌面另查 `session/turns`。
- 责任人已确认保持桌面端 0.28 telemetry：N7 同时纳入 ACP 输入捕获，恢复 selected Agent 1001 及 desktop channel/IDE/functionName 等上下文，不接受缺失差异。
- 2026-11-18 新增上报过滤需求：仅上报 catalog 下发模型的调用（`synced_from_server` 标记判断；自定义模型的调用及其关联记录跳过，fail-closed），过滤在各 reporter 出站边界统一实现、纳入批次1；分析见 `model-source-filtering.md`。

### 明确非目标或退出范围

- 不做崩溃、强杀后的启动扫描补报，不承诺持久化 exactly-once。
- **workflow 不属于本次 telemetry 范围**，不为其扩展 N3 或安排专项调查。
- 不补桌面端原本自行上报的内容，不新增旧版没有的上报类别。
- 外部 ACP 远程 Agent 的内部工具明细退出当前范围；本地有界投影不能冒充远程真值。
- 所有新版工具记录删除 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，不发 null/0，也不补采替代时间；责任人已在独立评审后再次确认，本项最终关闭。
- 不恢复旧随机 ID 原值，不用当前 cwd、Git HEAD、磁盘文件或 session-latest 猜测历史。

## 3. 当前推荐组合

```text
成功模型响应的 raw A-final（原值 32hex，2026-11-18 裁决：不转 UUID）
  ├─ 原模型接口每请求保存自身 attempt 原值，成功由独立报告 join 声明
  └─ after_turn 联读 session + trajectory + mutation/blob
       ├─ 独立 LLM 报告：requestId=A 原值
       ├─ tool-detail：requestId=A1 原值，funcId=T 原值
       └─ ai-code：requestId=A1 原值，reportId=T 原值

N3：run-owned 身份快照 → direct finalizer dispatcher
    → 进程级 owner 按 session FIFO → 集中 lifecycle 有界 flush

N7：ACP prompt_lock 内按 logical turn 从 live 主 history 选择最后成功主响应
    → A2 原值 + 桌面 attribution span → final-model-identity（桌面 schema 需放宽接受 32hex）
```

| 节点 | 当前推荐 | 决策状态 |
|---|---|---|
| N1 LLM 通道 | 原模型调用接口 + after_turn 独立 LLM 报告，两者合并而非替代 | 当前倾向；B7 最小契约为责任人委托 AI 制定的开发期暂行方案 |
| N2 requestId | 最终成功 raw A-final，内外均为原值 32hex 不转 UUID（2026-11-18 裁决） | A-final 采用中；32hex 格式接受/新旧混存待后台确认，桌面 schema 需放宽 |
| N3 分析触发 | run-owned 快照 + direct finalizer + 集中 per-session lifecycle drain | AI 当前推荐，待实施 design/R2 |
| N4 数据源 | 联读 session、trajectory、mutation/blob，而非只读 session.json | 大方向条件可行，文件缺口显式降级 |
| N5/N6 工具与 ai-code | 事后构造单次 final snapshot；严格身份与内容校验 | 主链可行；B8 最小 DTO/ai-code 幂等为开发期暂行方案 |
| N7 ACP | 按 session/turn 捕获桌面输入 + 响应时 live-history 精确选择，不依赖 after_turn registry | 保持桌面 0.28 能力和输出要求均已确认；选择路线暂行采用，真实接线待验 |
| N8 投递 | 同 session 有序 best-effort，跨 session 可并发，允许孤儿 | 已确认；不以严格 ACK 或崩溃恢复为前置 |
| N9 运行时上下文 | 固定运行时/live session/ACP 输入分工，逐字段 parity | 公共字段来源可行；原模型记录实际字段与独立报告补齐责任待后台确认 |
| N10 mock | 单端口为评估目标；1A 单端口骨架与 1B telemetry 已确认归属批次1 | 批次1 design 修订 mock design/DIRECTORY 并签认后实施；mock 只证明目标契约 |
| N11 实施路线 | fork 最小接缝先行（批次1 N3 四文件 + N7 单文件接缝） | 责任人已裁决三批次+集成分支方案（2026-11-17，见 `../plan.md`） |

## 4. 已探索方案及取舍

| 主题 | 已探索方案 | 当前结论 |
|---|---|---|
| 纯文件零上游 | 外部 after_turn hook 读文件 | 不满足进程内分析和 ACP 输出要求，排除为完整方案 |
| 请求体注入 | ChatMiddleware 在请求前写 telemetry | 属 N1-A 备选；当前 A-final + 独立报告路线不需要 |
| exchange 关联 | 新增 `Chrys-Exchange-Id`，或 attempt→exchange 映射 | C1/C2 仅在 A-final 开发期出现严重问题时回评 |
| 旧式实时埋点 | 恢复 LLM、工具、EventBus、ACP 多处实时挂点 | 上游接触面大，不作为默认路线 |
| N3-A direct finalizer | save/checkpoint 后直接轻量 dispatcher | 当前推荐；完整身份还需 run-owned 快照，不是单文件方案 |
| N3-B EventBus | 通用 AfterTurn/SessionEnded + inline subscriber | 多内部消费者或公共 API 需求时再评；当前会增加事件和订阅 owner |
| N7 after_turn registry | ACP 从轮末 registry 取身份 | 状态和生命周期更多；当前由响应时 live-history 方案取代 |
| 工具旧三阶段 | save→PENDING→final update | 不适合事后分析；改为单次 final snapshot save |
| ai-code 新增 mutationId | 为每次 mutation 新增上游身份 | 首版不新增；同 T 多 mutation 全部跳过，未来有硬需求再评 |
| 单/多端口双组合 | 长期同时维护两种 mock 组合 | 责任人认为复杂，不作为目标；当前只评估清晰单端口目标 |

## 5. 身份与报文契约

### A1/A2 不能混用

正常工具 turn 至少可能有：

- `A1`：产生工具调用的成功模型响应；
- `A2`：工具执行后产生最终回答的成功模型响应；
- `T`：一次实际工具 dispatch 的 operation ID。

| 外部记录 | 正确关联 |
|---|---|
| 原模型成功记录 1 + 独立 LLM 报告 1 | A1 原值 |
| tool-detail | requestId=A1 原值、funcId=T 原值 |
| ai-code | requestId=A1 原值、reportId=T 原值 |
| 原模型成功记录 2 + 独立 LLM 报告 2 | A2 原值 |
| 最终 ACP PromptResponse | 通常 A2 原值，并回显桌面 attribution span |

必须覆盖 `A1 != A2` 的样本。“同一 raw A 的所有外部表示相同”不等于“五类记录全部使用同一个 A”。selected Agent 1001 和 desktop 上下文由 N7 输入捕获承载；slash 仅关联当前 logical turn、不带 requestId；local child 内部工具使用 child 自身 E/A，均不套普通主 Agent 的 A1/A2 图。

### ID 表示与 turn/tool 规则（2026-11-18 原值裁决，取代 UUID 转换）

- 所有 ID（requestId/funcId/reportId/spanId/parentSpanId）保持原值 32hex，不转 UUID、不格式化；全局唯一性由客户端 128-bit 随机 ID 保证（原 UUID 转换及 golden 断言作废）；配套要求 Agent Studio `ModelRequestIdSchema` 放宽接受 32hex。
- 缺 A-final 或 raw 非法时跳过并记录，不取 `attempts[-1]`、exchange 或历史 M。
- `spanId=真实 logical turn ID 原值`；`parentSpanId` 只表示真实直接父 turn，普通独立 turn 不传——该语义与 0.28 实际用法（工具记录挂父模型调用 llmSpanId）不同，记为 parity 显式差异项；当前无真实嵌套 turn 场景，父 turn ID 持久化仅将来出现该场景时再验证（2026-11-19 澄清）。
- 普通本地工具 funcId=T 原值；同一 A1 多工具共享 requestId，但 funcId 必须不同。独立评审曾建议可选 `providerCallId` 对账字段，**2026-11-19 责任人裁决撤销**（协议面向多 AI 工具，不为 iCode 特有需求加字段）：对账在端侧完成——按 funcId=T 可在客户端 session/trajectory 反查 provider toolUseId 与工具调用信息，不回退 funcId。
- tool-detail 成功只报最终 codeStatus，不新增完整结果正文；ai-code 同 T 多候选 mutation 时跳过，不共用幂等键。

### B7/B8 开发期暂行契约

- **B7 独立 LLM**：`POST /csas/telemetry/api/v1/llm-report/save`；最小 envelope 为 schemaVersion/sessionId/eventType/eventSubType/requestId，span/parent 按真实关系携带；requestId 单键原子幂等，语义重放 200、不新增，同键不同内容 409，非法输入 400。首版不强制 model/response/usage/timing/runtime，但最小 envelope 不是最终字段豁免：channel/pluginVersion/projectName/Git 等须按 N9 和原记录实际字段完成 parity。
- **B8 tool/ai-code**：tool 使用七项必填 final DTO；ai-code 使用 reportId/requestId/sessionId/spanId/filepath/blocks/sourceType/inputMethod/codeStatus；严格 allowlist，未知字段和三时间字段不静默通过。公共字段/userId 也须进入逐字段保留/删除/待确认矩阵，不能因“最小 DTO”被永久遗漏。

B7/B8 均因责任人表示暂时无能力技术评审而明确委托 AI 制定，**不证明现网后台支持，也不构成 R2 批准**。

## 6. fork 上游接触面候选

### N3 最小完整身份与生命周期：四个文件

| 文件 | 候选职责 |
|---|---|
| `run/turn_state.py` | 保存并清理 run-owned 不可变 logical/pass/turn_number/is_retry 快照 |
| `run/runner.py` | pre_run 清旧值；在 trajectory await 前写入当前身份 |
| `run/finalizer.py` | save/checkpoint 后构造含 saved/status 的通知并 direct dispatch |
| `engine/session_lifecycle.py` | 正常 teardown 和 active delete 前集中 per-session 有界 flush/close |

该路线不需要修改 `turn_hooks.py`、EventBus、ACP manager、TUI app 或 headless entry。空快照、saved=False 直接 skip；pre_run 未完成、强制 shutdown cancel、save/checkpoint 异常和强杀不保证通知。

若采用需要显式关闭的进程共享异步 HTTP client 等资源，可能还需应用最外层 close；不能把 per-session flush 写成自动覆盖全局资源释放。

### N7 ACP 输入与输出接缝

- `app/acp/server.py` 输入侧：按 session/turn 捕获 selected-agent、agentName/agentMarketSkillId、desktop channel、IDE 版本和 functionName 等扩展上下文，供 1001 与各 reporter 使用；禁止进程级最近值，缺失显式降级。输入须形成不可变 turn 上下文传给 after_turn：1001 是 save-only、无 T，按 `(sessionId,logicalTurnId)` 去重一条，并关联当前 logical turn 首个成功主模型 A-final；无成功或选择输入缺失时跳过，不用最终 A2 或旧 turn 替代。
- 同一上游文件输出侧：prompt_lock 内选择当前 logical turn 的 raw A-final，保留桌面 attribution 输入并合并最终 `final-model-identity`。
- 新增定制输入上下文、selector/UUID helper；不改 `request_tracking.py`、`foundation/trajectory/ids.py` 或通用 ID 生成/校验。输入捕获纳入 N7 后续 ACP 切片，不阻塞首个 after_turn 垂直切片。

以上均为后续实施批次的 R2 候选，尚未批准。上游文件实际修改前仍须逐项提醒并获得确认。

## 7. 已有证据

以下计数来自不同组合，存在重叠，**不能相加为总测试数**：

| 主题 | 实际结果 | 证明与未证明 |
|---|---|---|
| M0 五类目标关系 | 16 passed | 真实 engine A1→write_file→A2、mutation/blob 和测试态 DTO 通过；无生产 reporter/存储/真实 ACP |
| M1-I 身份矩阵 | 31 passed | 两工具、失败不借旧 A、SDK retry、Responses retrieve、redirect 锚点、并发 scope；无传输存储幂等 |
| session 文件重建 | 48 passed | 正常两轮、blob/gap 降级、fork 零重报、save=False expected-turn 守卫；真实 compaction 组合未做 |
| 性能与队列 | 52 passed | 30 轮增长、FIFO、跨 session、有界 flush 原型；不是生产 owner 或真实入口闭环 |
| N3/N8 现有行为锚点 | 241 passed | 锚定 EventBus/finalizer/lifecycle/ACP/TUI 现有行为；不证明新增 dispatcher/flush 已实现 |
| N7 方向实验 | 7 项 selector 实验通过，另有上游锚点 | 真实 server、attribution、桌面 Zod 和并发/save=False 组合未完成 |
| 广义工具与 ai-code | 各专题现有测试通过，跳过项未计通过 | 证明来源和边界，不证明新版 DTO/存储已实现 |

性能实证：5/15/30 轮全量中位约 7.307/20.942/38.409ms，expected-turn 约 7.329/18.921/38.439ms；过滤只裁剪报文，不减少完整文件 I/O。默认只处理显式当前轮，不为已排除的崩溃补报增加持久化高水位。

## 8. 阻塞点与风险点

### 当前开工前流程门禁（2026-11-19 更新）

1. ~~另一 AI 完成本轮评审，发现项收敛~~——已完成（评审/复审收敛，最终双 AI 自审经责任人裁定满足）。
2. ~~责任人裁决是否新建实施批次、是否需 ADR，以及推进顺序~~——已裁决（三个开发批次 + 集成分支，无需 ADR，见 `../plan.md` 实施策略节）。
3. 探索批次已签认并待独立 PR 合并；批次1 开工前须完成其 requirements/design/test-plan 并签认 R2（含修订 mock design/DIRECTORY、集成分支 CI 触发登记）。
4. 获授权后才修改上游文件或开始生产/mock 实现——不变。

### 首个实现必须验证的技术风险

- 无 hooks、retry、trajectory disabled、普通 cancel、save=False 下身份与状态是否正确。
- expected-turn reader 是否误读旧文件；fork 是否重报继承历史。
- 工具终态 gap、trajectory torn/corrupt、blob/参数缺失是否 fail closed。
- 同 session 顺序、跨 session 并发、队列积压、flush 超时和 active delete 失败后续用。
- 同 T 多 mutation、同 A 多工具、Responses retrieve、失败/pending/部分流是否错关联。
- 真实长会话、大 blob、慢盘与 N7 O(history) 选择成本；既有 30 轮结果不是性能验收阈值。

### 外部依赖与上线门禁

- **R1 后台依赖前置**：首个 mock 切片期间并行确认 BR-1/5/6；若关键前提失败，重新评审 N1-A 的完整成本，不预设“后台零改动”或自动切换。
- **R2 全字段 parity**：原模型记录实际字段未知；0.28 全字段（公共字段、parentSpanId 语义、agentName、fileName/value、行数、错误、language、Git 用户等）必须逐项标明保留/删除/待确认。M1-T 产出完整矩阵并与 BR-1/5/6 同批确认；未关闭不得判真实联调/上线通过，但不前置阻塞外网 mock 开发。
- **R3 桌面输入已由 Q2 关闭范围争议**：保持 0.28 桌面能力，ACP 输入捕获和 selected Agent 1001 纳入后续 N7 切片。
- 后台是否实际部署 BR-1~BR-7/BR-9/BR-10 目标契约（BR-8 已撤销），孤儿记录最终能否 join；cancelled 和中间 attempt 分别由 BR-9/BR-10 单列。
- Agent Studio 是否真实消费 `agent-studio.dev/final-model-identity`，通用 UUID schema 是否接受非 UUID4 version 的派生值。
- 代码块、文件路径、工具参数的权限、脱敏、保留期限、访问审计和删除语义尚需形成可执行治理验收。
- 长会话需在实施中实测并定义背压/验收目标；评审提到的“500 轮 600ms”是外推而非实测，不作为事实或硬阈值。

## 9. 建议 iCode 的通用改动

| 建议 | 当前定位 |
|---|---|
| 进程内 AfterTurn/SessionEnded 生命周期 API | 最值得评估；应携带 logical/pass/retry/status/saved，并支持轻量 subscriber 与显式 drain，可消除 fork 的身份传递和触发耦合 |
| 正式 ChatMiddleware 注册与稳定只读上下文 | 通用审计/脱敏/治理价值；当前 N1-C 不需要，不列为本次必改 |
| 公共逻辑 exchange 上下文 helper | 通用 tracing 价值；当前从事后 trajectory 获取，不需要为本任务新增 |
| `Chrys-Exchange-Id` 并保留 attempt header | 仅回退 C1 或独立网关需求；当前 A-final 路线不需要 |
| 可选结构化 tool invocation audit | 仅在需要更高保真且证明现有持久化不足时提出，必须脱敏限长 |
| ACP model-call notification | 无真实新增消费方，不提出；上游标准流式内容、turn 身份和 request tracing 已可复用 |

不建议上游理解 AIxCoding/Agent Studio 专属 envelope、内部后台字段或 CSAS endpoint，也不建议改变 attempt ID 语义、增加 session-latest 猜测或为已排除的崩溃补报建设机制。详细论证见 `upstream-proposals.md`。

## 10. 后端服务器配套改动

详细目标与验收见 `backend-change-requests.md`：

| 编号 | 配套需求 | 状态 |
|---|---|---|
| BR-1 | 原模型调用记录保存每次请求自身的 raw `Chrys-Request-Attempt-Id`，不做成功判定；成功由独立报告 join 声明（2026-11-18 修订，不另造逻辑 ID） | 已确认可配合（按修订语义），现网未证明 |
| BR-2 | tool-detail 接受单次 final snapshot save，无需 PENDING/final update | 已确认可协调，现网未证明 |
| BR-3 | `(requestId,funcId)` 数据库唯一约束或原子 upsert，防顺序/并发重复 | 已确认可协调，现网未证明 |
| BR-4 | 语义重放不新增；同键不同内容 409，不隐式覆盖 | 已确认方向，待实现联调 |
| BR-5 | 所有 ID 保持原值 32hex 不转 UUID（2026-11-18 裁决）；后台需接受 32hex 并与 0.28 UUID 文本历史数据混存；桌面 schema 放宽 | 待书面确认 32hex 格式/混存；Agent Studio schema 放宽待落实 |
| BR-6 | 新增独立 LLM save endpoint、最小 envelope 和 requestId 单键幂等 | B7 委托 AI 暂行，后台现网未确认 |
| BR-7 | ai-code final DTO、`reportId=T 原值`、`(requestId,reportId)` 原子幂等与 200/409/400 | B8 委托 AI 暂行，后台现网未确认 |
| BR-9 | cancelled/interrupted 的 codeStatus/failureType 或明确不支持 | 待后台/责任人确认，不伪报普通失败 |
| BR-10 | 网关中间/失败 attempt 是否落库、标记、保留和孤儿治理 | 待后台确认；不影响最终成功记录取 A-final |

后台无需为最终成功关联而识别或聚合 SDK retry、redirect、Responses 的全部 HTTP attempts，也无需判定哪次请求实际成功（2026-11-18 修订）：每条请求记录保存自身 attempt，成功语义由独立报告 join 命中声明；若网关本身保存中间/失败 attempt，必须按 BR-10 明确其记录和孤儿口径。

## 11. mock 当前状态与目标

- 当前 auth+catalog 共用 7777，update 使用 7778；telemetry mock 尚未注册。
- 单端口是当前评估目标，不长期维护单/多端口两套组合；独立 factory/单服务 CLI 仅用于底层测试和调试。
- AI 建议在同一实施环节分 1A 现有服务单端口骨架、1B telemetry，不拆成两套产品组合。
- 新 telemetry 至少需要原模型成功 A 捕获/原值保存、独立 LLM 原值保存、tool/ai-code 严格 final 校验、原子唯一、200/409/400、rejected 诊断和 requestId join。
- mock 不执行模型推理，只返回固定模型响应并接收/保存遥测；mock 通过不等于真实内网后台通过。
- 既有 mock design 的多端口决定与 DIRECTORY 约束必须在实际实施前按流程修订，不能由本探索直接改动。

## 12. 尚未调查或尚未证明

### 留待实施/联调，不再阻塞开工决策

- 生产 after_turn→reader→reporter→mock 最小垂直切片及真实保存/join。
- M1-T：语义重放 200、不新增、同键冲突 409、并发原子唯一、孤儿晚到和 read-your-writes。
- 真实 ACP server、输入捕获、selected Agent 1001、prompt_lock、attribution、`final-model-identity`、桌面 Zod 与并发/save=False。
- 真实 engine compaction×reader、archive 去重、Phase 4、完整 edit 和授权脱敏样本。
- 长会话、大 blob、慢盘、queue depth/背压和真实入口 flush。
- slash 恰好一次、cancelled/interrupted、真实嵌套 turn 父 ID、Git 精度、公共字段 parity 和中间 attempt 后台口径。
- D1 旧缺陷修复建议逐项裁决、上游提案通用性评审和 N11 推进顺序。

### 不应误列为待调查

- 外部 ACP 内部明细：已退出当前范围。
- workflow：责任人已明确退出当前 telemetry 范围。
- 三个工具执行时间字段：已决定全部删除，并经评审后再次确认。
- 崩溃/强杀补报：明确非目标。
- funcId 的角色和 T 原值：B2/B3 已确认角色（2026-11-18 原值裁决后 funcId 为 T 原值 32hex）；BR-8 providerCallId 已于 2026-11-19 撤销，模型侧对账由客户端按 T 本地反查完成。

## 13. 建议的首个开发切片

评审已收敛；实施批次经责任人签认和 R2 批准后，首个开发切片只建议打通：

```text
真实 A1→write_file→A2
  → 真实 after_turn 通知
  → expected-turn 文件 reader
  → per-session reporter
  → mock 保存独立 LLM/tool/ai-code 并 join
```

同时验证无 hooks、save=False、trajectory disabled、正常 flush 和 A1/A2 不错连。真实 ACP×桌面作为紧随其后的独立切片，完整 M1-T 异常矩阵随后展开，不把首个切片扩大成全量功能。

独立评审/复审均已确认主路线无方向性反例，五项分歧全部收敛。实施时必须保留：BR-9/BR-10（BR-8 已于 2026-11-19 撤销）、0.28 全字段 parity 的 M1-T/联调关闭门禁、N7 输入捕获与 1001 去重链、N1-A middleware 时序/registry 完整成本。失败模型零上报和 eventSubType=success 的统计差异同样进入 parity。

### 已确认的实施组织

责任人已于 2026-11-17 确认：探索批次独立交付；生产实现拆为 `telemetry-after-turn-slice`、`telemetry-acp-desktop`、`telemetry-parity-hardening` 三个批次。批次1包含 mock 1A 单端口骨架和 1B 垂直切片 telemetry，开始前须修订既有 mock design/DIRECTORY 并签认；D1 按各批涉及范围签认，不全量阻塞批次1。真实后台与数据治理另作内网门禁。

生产代码先隔离于 `feat/telemetry-session-analysis` 集成分支，三个批次分别从该分支切出并 PR 回合，全面验证后再合并 `main_aixcoding_cli`。批次1实施前必须把集成分支加入 `aixcoding-tests.yml` 和 `aixcoding-upstream-ci.yml` 的 PR 触发并实证双 CI，因为当前只对目标为主干的 PR 自动运行。

`aixcoding/tests/telemetry/` 四个测试态实验文件全部在当前探索批次独立 PR 中提交，不等待实施批次；不进 wheel、不移入上游 tests。正式生产实现及等价/更强覆盖合并后，再逐项裁决精简或退役。完整分支、验收、最终双 AI 自审判定和 CI 约束见 `../plan.md`。

## 14. 证据导航

- 方案空间：`solution-space.md`
- 能力矩阵：`capability-matrix.md`
- 五类记录：`a-final-e2e-closure.md`
- session 重建：`session-reconstruction.md`
- 性能与生命周期：`performance-and-lifecycle.md`
- 风险：`open-risks.md`
- 上游建议：`upstream-proposals.md`
- 后台配套：`backend-change-requests.md`
- 后台问答与委托状态：`backend-contract-questions.md`
- N3 身份/owner：`nodes/after-turn-lifecycle.md`
- N7/公共字段：`nodes/runtime-context.md`
- 实际命令与历史纠错：`../verification.md`
- 批次续接与后续门禁：`../plan.md`
