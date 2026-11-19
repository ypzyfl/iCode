# N1：LLM telemetry 上报通道

> 技术判断：多条路线可行或条件可行。决策状态：**N1-C 当前倾向，直接复用最终成功 attempt ID；C1/C2 仅作开发期回退备选**。B7 已由责任人委托 AI 制定开发期暂行最小契约，详见第8节；不是现网已支持或 R2 批准。
>
> **2026-11-18 ID 原值裁决**：所有 ID 保持原值 32hex、不转 UUID（此前归一化安排作废）；本文历史讨论中的 UUID 转换与 golden 表述按原值理解，批次1 design 时统一重写。权威口径见 `../backend-change-requests.md` BR-5。
>
> 依赖：N2 requestId、N3 触发、N8 投递、N7 ACP、N10 mock；服务器侧接口与记录模型是关键外部依赖。

## 1. 要回答的问题

旧版把 telemetry 混入模型 HTTP body。新版是否仍需在请求发生时上送，还是可以在 after_turn 从 session/trajectory 生成独立 LLM 调用报告，再有序上报其工具和 ai-code？

## 2. 分支总览

| 分支 | 工作方式 | 技术判断 | 决策状态 | 主要代价/前提 |
|---|---|---|---|---|
| **N1-A body middleware** | 请求前把 telemetry/requestId 写入 `extra_body` | 已证可行 | 备选 | clients 组栈或上游 middleware 注册；协议透传和运行时上下文 |
| **N1-B exchange header** | 每个 HTTP attempt 带同一 exchange header | 条件可行 | 备选/上游候选 | wire header 支持；服务器按 header 关联；保留 attempt header |
| **N1-C 原调用接口 + 独立 telemetry endpoint** | after_turn 独立报告与原调用记录合并，再发依赖数据 | 条件可行 | **当前倾向** | 已确认必须合并；暂定 A-final 直接关联；进程内分析；B7 最小契约暂行采用 |
| **N1-D 外部 HTTP 代理** | 代理改写请求 body/header | 技术可做但不满足简洁性 | 排除 | 缺 turn/exchange 上下文、HTTPS/MITM、部署和调试复杂 |
| **N1-E 不上报 LLM 父记录** | 只发工具和 ai-code | 不满足服务器关联需求 | 排除 | 依赖数据缺少逻辑调用父记录 |

## 3. N1-A：模型 body middleware

### 已核实

- 旧版已证明 `extra_body.telemetry` 可在三协议到达 wire。
- 新版 ChatMiddleware 能在 `call_next()` 前修改 options，并读取 ExchangeTrace。
- 当前产品组合层没有正式 middleware 注册入口，需要 fork 组栈或上游通用注册能力。

### 优点

- 与 0.28.0 服务器契约最接近；
- 模型请求发生时即带逻辑 requestId；
- 网关如果依赖 body telemetry 建记录，无需新独立 LLM 接口。

### 代价与未知

- 引入模型请求链侵入和协议兼容测试；
- SDK retry/redirect 重复携带同一 telemetry；
- 只有请求前字段，无法自然包含最终 outcome/usage；
- 文件无法恢复的 channel/Git 等仍需运行时补采。
- 复审补充的关键时序：ChatMiddleware 注入 body 早于 httpx prepared hook 铸造 request_attempt_id，因此搭车时尚无 A-final。0.28 只能在请求前自造随机 requestId，并通过内存 registry 向工具/ACP 传播；该随机值不持久化到 session/trajectory，纯文件 after_turn 无法恢复。故 N1-A 真正回退需复活实时 registry、增加运行时持久化，或重定身份键，不能只按 middleware 装配文件数估算整体成本。

### 适用条件

服务器必须继续在原模型请求中接收 telemetry，或 N1-C 的服务器前提不能满足时。

## 4. N1-B：exchange header

### 已核实

- 现有 attempt header 只标识 HTTP attempt。
- exchange ID 可在请求前获得，但当前不会自动上 wire。
- `Chrys-*` 是保留前缀，正式 `Chrys-Exchange-Id` 需要上游/wire stamping 支持或 fork 接缝。

### 优点

- 同一 exchange 的 SDK retry/redirect 可共享 header；Responses continuation 每次 poll 新建 E，因此 header 也随之变化，不承诺跨 poll 分组；
- 不需要改变模型 body；
- 对通用网关追踪、去重和日志关联有价值。

### 代价与未知

- 每个 attempt 都带 exchange header，网关需定义聚合和 usage 去重；
- 仍只有请求时字段；
- N1-C1 会复用该 header 作为原调用记录与独立 telemetry 的直接合并键；N1-C2 则不需要新增它。

## 5. N1-C：原调用接口 + after_turn 独立 telemetry endpoint

### 核心机制

责任人于 2026-11-14 明确：独立 LLM 报告**不能替代**原大模型调用接口的业务记录，因为原请求还包含其他必须记录的数据。2026-11-16 暂定两者通过最终成功 attempt 直接组合：

```text
原大模型调用接口
  → 保存原有请求/响应等业务数据
  → 最终成功响应的实际 HTTP 请求携带 raw Chrys-Request-Attempt-Id=A-final
  → 后台原成功记录保存 requestId=UUID(A-final)

after_turn 独立 LLM telemetry 报告
  → 内部从最终成功 assistant message 取得 raw A-final，出站时发送 requestId=UUID(A-final)
  → 服务器按外部 UUID 将独立 telemetry 与原成功调用记录合并
  → 缺 A-final 时跳过该条并记录原因，不用 exchange 混填

后续 tool-detail / ai-code
  → 统一使用实际产生它们的成功响应的 UUID(A-final) 关联
```

上报发送延后到 after_turn；内部仍通过 `parent_model_operation_id` 和 assistant message 的 E/A-final 双 ID 精确关联，外部 requestId 由 raw A-final 单点确定性转换。工具记录不携带 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，不再从 exchange/tool 时间构造这些字段。独立接口的候选 save 路径、最小 envelope 和 requestId 单键幂等/409 已按 B7 委托形成暂行契约；model/usage/timing 等扩展字段仍非首版必需。

### 已证支持条件

- exchange started/finished 在工具执行前完成；
- after_turn 在 session save 和 trajectory checkpoint 后触发；
- 工具 parent exchange、session function_call、mutation tool operation 均可持久化关联；
- 原请求已经携带 `Chrys-Request-Attempt-Id`，正常成功 assistant message 已保存最终 attempt；
- request tracking 在 prepared 阶段同时持有 exchange operation ID 和新 attempt ID；只有回退 exchange 时才需要新增 exchange header；
- N7 可在 ACP PromptResponse 返回前从 live history 选择 raw A-final 并在定制出站边界转换，网络 ACK 不必阻塞 ACP；无需 after_turn request registry。

### 当前直接关联与开发期回退分支

| 分支 | 原请求与独立报告如何关联 | 客户端改动 | 服务器处理 | 状态 |
|---|---|---|---|---|
| **N1-C 当前：A-final 直接关联** | 原成功请求沿用现有 raw attempt header，独立报告、工具和 ai-code 出站时使用最终成功 message 的 UUID(A-final) | 不新增 header；after_turn 从 E/A 双 ID 关联模型单点选择 raw A-final，并在出站边界转换 | 后台原记录把 raw A-final 转为 UUID，与独立报告按外部 UUID 合并；缺 A-final 跳过并记录原因 | **暂定采用** |
| **N1-C1 exchange header** | 原请求新增 `Chrys-Exchange-Id=E`，同一 exchange 的 attempts 携带该 E，独立报告也携带 E-final | 上游/wire request tracking 增加 exchange header；不需要 body middleware | 按 E-final 直接合并；业务关联不需要先聚合全部 attempt 或多 HTTP 行 | 开发期回退备选 |
| **N1-C2 attempt 映射** | 原请求沿用现有 attempt header A/B，独立报告携带 E + 全部/最终 attempt IDs | 不新增 header；after_turn 报告增加 attempt 映射信息 | 用任一实际已落库的 A 找到原记录并建立 E 映射，再按 E-final 合并 telemetry、工具和 ai-code | 开发期回退备选 |

2026-11-14 曾确定 C1 优先；该历史决策已被 2026-11-16 的 A-final 暂定方向取代为当前路线，C1/C2 不再是为了逐条兜底而并行使用。只有开发期发现成功路径 A-final 缺失、与服务器记录不一致等严重问题时，才暂停并回评 exchange，再选择 C1 或 C2。

若回退 C1，已核实的 fork 生产接触面是 `chrys_headers.py` 常量和共用 `request_tracking.py` prepared-request hook，正式实施仍需另行 R2 授权。上游建议仍是新增 exchange header 时保留 attempt header，不替换既有逐 attempt 诊断契约。C2 则要求服务器支持 attempt→exchange 映射，且原记录至少实际保留一个报告所携带的 A；这不等于要求后台新增 create/retrieve/retry 多 HTTP 业务行。

当前线上只有 raw attempt header，没有 exchange header。A-final 路线不需要服务器知道完整 E↔A 分组，只需后台原成功记录、独立报告和依赖数据保存同一外部 UUID(A-final)；这与回退 exchange 时的分组需求不能混为一谈。

### 字段保真

- 文件可精确提供 exchange/session/pass turn、actor、request/response model、客户端 outcome/usage/timing 等。
- 旧 body 实际只有 ID/event/channel/plugin/project/Git 等字段；user/model/usage 并非旧 body 基线。
- desktop channel/version/functionName、历史 workspace/Git 仍需 ACP/finalizer 补采或降级。
- 独立接口可增加最终 outcome/usage/timing，但这些是增强字段，不能冒充旧 body 字段。

### 顺序与失败策略（N8 已确认）

责任人于 2026-11-14 确认采用与 0.28.0 类似的 **best-effort、允许孤儿上报**：

- 按成功模型响应的内部 exchange 顺序先调用 LLM 报告，再调用其工具和 ai-code 接口；
- 单一 LLM 父记录上报失败后，依赖数据仍继续发送，允许服务器出现孤儿数据；
- 不要求 LLM 业务 ACK 作为依赖数据的投递门槛；所有 telemetry 接口位于同一服务器，当前接受低失败概率假设；
- 该策略只保证客户端有序尝试，不保证父记录一定存在，服务器可按 A-final 最终关联后到数据；
- B7 已暂定独立 LLM 的 requestId 单键幂等和 200/409/400，tool/ai-code 由 B8/BR-2–BR-7 规定；完整传输重试、故障注入和真实原子行为仍留实施，不作为方向阻塞项；
- ACP 本地 request/span 与网络 ACK 解耦，正常退出 flush 和崩溃不补报的既有边界不变。

### 可取消的改动

若该分支前提成立，本 telemetry 需求可取消：

- LLM body telemetry 和 ChatMiddleware 组栈；
- 为 middleware 传递 exchange/workspace/agent 的 builder 接线；
- 当前 A-final 路线可取消新增 `Chrys-Exchange-Id` 和 C2 映射；只有开发期回退 exchange 时才重评 C1/C2；
- LLM 响应 session-latest/per-call registry；
- 为 registry 反查而补 provider_call_id 的上游改动；
- model_catalog 对 body telemetry 的专门观测。

### 仍保留的改动

- N3 进程内 after_turn；
- N7 最终 ACP 输出必须主动携带 requestId；桌面另查 `session/turns` 已被明确否定，Q2 已确认输入捕获纳入以恢复 1001/desktop 上下文；
- N8 独立 LLM endpoint、有序 best-effort reporter 和新 mock；B7/B8 幂等目标已暂定，真实原子行为和完整故障矩阵留实施；
- N9 缺失上下文的补采或降级；
- N5/N6 特定文件缺口的局部处理。

## 6. 反例与重开条件

- 成功路径 A-final 缺失、与服务器原成功记录不一致或并发串号：属于开发期严重问题，暂停并回评 exchange/C1/C2，不做逐条 exchange 混填。
- trajectory 未开启或 exchange/attempt 事件缺失：不能凭空恢复 A-final；缺 A-final 跳过并记录原因，不借历史 A、不另造 UUID4。
- 外部 ACP 父 trajectory 只有边界，独立 audit 的 update 投影也不含远程内部 exchange 证据：不能声称恢复其内部 LLM 调用；内部工具的字段级降级见 `broad-tool-coverage.md`。
- LLM 父记录失败仍继续发送依赖数据：已确认 best-effort，不声称严格时序。
- 只读 `session.json`：不足以支撑完整 exchange/mutation 重放，必须使用 N4-B 整个 session 目录。

## 7. 下一判别动作

1. 普通/流式成功、SDK retry、Responses retrieve、并发 scope 和 redirect 锚点已由 M1-I 覆盖；实际原记录/独立报告存储 join、共同 golden 和后台原子幂等留 M1-T/联调。
2. 首个生产垂直切片继续验证失败/pending/部分流不借旧 A、模型成功后工具失败关联实际 A-final，以及 A1/A2 不错连。
3. 按 ID 原值口径验证后台原记录与客户端独立报告/工具/ai-code/ACP 全链同文本原值（32hex）；不修改 attempt 生成点或 trajectory 校验，发现严重问题再回评 C1/C2。
4. 旧 body 必需字段的 ACP/finalizer 补采或降级已在 N9 初步核清，真实 ACP 输入与最终响应留对应切片。
5. N7 方向 selector 已有 7 项实验；真实 server 的取消/无成功主调用、并发、save=False 和桌面 schema 仍需实现后验证。N8 不等待严格 ACK 策略裁决。

## 8. 证据入口

- 旧版实现：`../legacy-0.28-telemetry.md`
- ID：`request-id.md`、`../request-identity.md`
- 数据能力：`../capability-matrix.md`
- 上游分支建议：`../upstream-proposals.md`
- 实验：`../../experiments/request-identity.md`

## 9. 独立 LLM endpoint 与最小 DTO 专项（2026-11-17）

### 9.1 旧搭车契约的真实边界

旧 0.28.0 middleware 实际组包只包含 requestId/span、eventType/eventSubType、session、channel、project/Git、approval 和公共 runtime 字段。它没有 model、request/response、usage、exchange timing、error 或 retry attempt 字段。`eventType=llm`，`eventSubType` 携带原始 finish reason（样例包括 stop/tool_calls），失败样例为 error；旧必填主体是 requestId/eventType/eventSubType/sessionId。

旧 telemetry-mock 只有 tool-detail、ai-code 和 event-reaction 等 CSAS 路由，没有模型网关或独立 LLM endpoint，也没有搭车字段校验/golden。旧 mock 接受 tool-detail 未知字段不能证明模型网关或未来独立 LLM 接口接受同样字段。

因此不能从旧搭车报文推出独立 LLM 的 model/usage/timing 契约。新版这些事实可从 exchange/session 获得，但**“客户端能提供”不等于“独立报告必须发送”**：原模型成功记录已保存哪些业务字段仍需后台回答。

### 9.2 当前 AI 建议：先定义最小关联 envelope

以下是最小 mock 闭环建议，不是已确认生产协议；完整字段来源和待确认项见 B7。

| 字段 | 最小闭环建议 | 来源/规则 |
|---|---|---|
| `schemaVersion` | 必需，整数 `1` | 新独立 endpoint 的版本，不冒充旧搭车字段 |
| `sessionId` | 必需，非空字符串 | 当前 session 标识，用于分区、debug 和隔离；不是关联唯一键 |
| `eventType` | 必需，固定 `llm` | 沿用旧语义 |
| `eventSubType` | 必需，首切片固定 `success` | 当前只上报最终成功模型调用，不把原始 finish reason 当 outcome |
| `requestId` | 必需，canonical UUID | `UUID(raw A-final)`，与原模型、tool-detail、ai-code、ACP 同文本 |
| `spanId` | 条件可选，canonical UUID | 当前 turn ID；正常主 turn 应提供，非 turn/降级场景不得伪造 |
| `parentSpanId` | 条件可选，canonical UUID | 仅真实直接父 turn；普通独立 turn 省略 |

首版不需要 `reportId`：一个 A-final 对应一个独立成功报告，`requestId` 已能作为幂等键。sessionId/spanId 不进入组合幂等键，避免同一调用因上下文补全产生重复记录。

### 9.3 暂不列为最小必需的字段

- **模型身份**：provider、apiStyle、requestModel、responseModel、responseId、finishReason；
- **usage**：normalized、providerReported、cache/reasoning breakdown；
- **exchange timing/outcome**：startedAt、endedAt、duration、chunk/stall、outcome；
- **runtime/project**：channel、agentName、pluginVersion、projectName、Git；
- **错误/retry**：errorCode、retryable、attemptIndex、exchange 链。

这些字段在新版多数有来源，但应先由后台说明原成功记录已有内容，再决定独立报告补充哪些。首版 mock 可以保留扩展能力，但不得把 AI 建议的字段清单写成生产必需，也不得为了让 mock 有内容而复制原模型请求/响应。

内部 exchangeOperationId、parentOperationId 和 attempt 可用于客户端分析/debug，不建议仅为外部关联新增到最小 DTO；外部关联仍是 UUID(A-final)。

### 9.4 endpoint 与幂等暂行方案

B7 开发期暂行 endpoint：

```text
POST /csas/telemetry/api/v1/llm-report/save
```

沿用旧 mock 的 CSAS 路径风格和单对象 save 形态；首切片不做 batch。真实 external prefix 由 base URL 配置，不在客户端硬编码多个前缀。该路径已按责任人委托作为开发期暂行方案，但没有独立 LLM 生产 endpoint 或后台现网支持证据。

建议以 **`requestId` 单键原子幂等**：

- 首次接受：HTTP 200，保存一条记录；
- 相同 requestId、规范化 JSON 值相同：HTTP 200，不新增，保留首次记录；
- 相同 requestId、内容不同：HTTP 409，不隐式覆盖，保存 rejected/冲突诊断；
- 缺少必填字段、UUID 非法、eventType/eventSubType 不符：HTTP 400；
- token 校验失败、过大 body 和故障注入沿用现有 mock 风格。

规范化比较应忽略 JSON key 顺序和无意义空白，不要求原始 body 字节完全相同；不得因重放时 key 顺序不同误判冲突。response body 暂不作为客户端 ACK 依赖，HTTP 状态是最小契约。

### 9.5 mock 原模型记录与 join

原模型 mock 只在最终成功响应时读取该实际请求的 raw `Chrys-Request-Attempt-Id`，内部可保留 raw 供 debug，外部记录保存 `UUID(raw)`。失败 attempt 不生成成功业务记录；Responses create/retrieve 按最终成功 A-final 关联。

独立 LLM、tool-detail、ai-code 均按外部 UUID 原值保存。debug 查询至少支持：

1. 按 requestId 查看原模型、独立 LLM、tools 和 ai-code；
2. 查看缺失任一侧的孤儿记录；
3. 查看同键重放计数不增加和不同内容 409原因；
4. 查看原始报文与 rejected 原因，敏感信息只在 loopback mock 中使用。

### 9.6 最小验收样本

1. 完整成功：原模型与独立报告 join，eventType=llm/eventSubType=success，UUID golden 一致。
2. key 顺序不同但语义相同的重放：200且不新增。
3. 完全相同的重放：200且不新增。
4. 同 requestId 不同 session/eventSubType/span：409且不覆盖。
5. 缺 requestId/sessionId、非 canonical UUID、缺 A：400或客户端跳过，绝不重新生成 UUID。
6. 普通 turn 有 span、无 parent；独立 turn 不伪造 parent；真实父 turn 后续专项。
7. 无 usage/model/runtime 的最小 envelope 仍可完成 join，防止 mock 错把未确认字段设为必需。
8. 后续扩展再覆盖 usage、timing、failure/retry 和完整 runtime，不阻塞首切片。

### 9.7 B7 暂行裁决与剩余边界

责任人于 2026-11-17 表示相关知识不足、暂时没有能力决断，明确要求按 AI 判断制定方案并记录。故本节 endpoint、最小 envelope、requestId 单键幂等和首版只做关联闭环现为**开发期暂行采用**，不再等待责任人逐项技术判断。B7 已记录最小 golden 和报文示例。

这不证明后台现网支持，也不构成正式实施/R2批准。原模型成功记录已有字段仍未核清，因此 model/response/usage/timing/outcome/runtime 保持非必需；后续获得真实契约或实施发现问题时，再分析并同步调整 mock、客户端和文档，不在不同出口分别打补丁。单端口 mock 1A 与 B7 无关，telemetry 1B 可按本暂行契约设计严格校验。

新版行为锚定：`test_exchange_and_validation.py`、`test_items_fork_and_usage.py`、`test_request_tracking.py` 共 45 passed，证明 exchange/usage/attempt 现有来源行为，不证明独立 endpoint 或 DTO 已实现。
