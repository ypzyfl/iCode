# 0.35.2 Telemetry 方案方向与改动分类图

> 状态：方案导航和沟通索引，不是实施授权；2026-11-17 当前有效汇总见 `review-handoff.md`，节点/分支以 `solution-space.md` 为准。当前暂定最终成功 attempt 为主 requestId，推荐原模型接口+独立 LLM 报告、run-owned after_turn 四文件接缝和响应时 ACP live-history。

## 1. 需求边界

- 对照旧版由 iCode/aixcoding-cli 实际发出的上报和 ACP 输出，不补桌面端自己的上报。
- 以 session 文件分析为主，接受 after_turn/session_end 的非实时性，不要求逐事件实时上报。
- after_turn 分析希望在 aixcoding-cli 进程内运行，不接受每轮启动外部 Python hook 进程。
- 不做崩溃/强杀后的启动扫描补报。
- 保持字段、ID 粒度和关联语义，不默认复制旧版缺陷。
- 上游建议必须符合通用 AI 工具定位，不要求 iCode 内置 AIxCoding 后台协议。

旧版能力基线见 `legacy-0.28-telemetry.md`，逐项证据见 `capability-matrix.md`。

## 2. 可选总体方向

| 方向 | 工作方式 | 优点 | 不能解决/代价 | 当前评价 |
|---|---|---|---|---|
| A. 纯文件、零上游改动 | 外部 after_turn hook 分析文件 | 无 R2，理论升级接触最少 | 动态 LLM telemetry、进程内分析、ACP 输入/输出均无法完整实现 | 不满足完整需求 |
| B. 请求注入 + 文件分析 | 请求前 middleware/header + 进程内 after_turn 文件分析 + ACP 边界 | 接近旧服务器契约，复用持久化数据 | 仍需模型请求链接缝；只有请求时字段 | 备选，对应 N1-A/N1-B |
| C. 旧式运行时事件方案 | 恢复 LLM、工具、EventBus、ACP 多处实时挂点 | 最容易复制旧细节 | 上游改动多，追版本冲突面大 | 仅作必要精确字段的备选，不作为默认路线 |
| D. 上游能力先行 | 先推动通用 middleware/lifecycle/exchange header，再基于新上游实现 | 长期 fork 接缝最少，API 更稳定 | 受上游排期和版本约束；仍需定制分析与报文 | 按所选分支与其他方向组合 |
| E. 原调用接口 + 独立 telemetry 接口 + 文件分析 | after_turn 独立上报 LLM telemetry，与原调用记录合并，再有序上报工具/ai-code | 保留原请求业务数据，消除 body telemetry 侵入，可包含最终 outcome/usage | 直接复用最终成功 attempt header；仍需 run-owned 身份、进程内触发和 ACP 边界；B7 独立接口为暂行契约 | 当前推荐，对应 N1-C；C1/C2 仅作开发期回退备选 |

## 3. 纯 session 目录可以承担的能力

此处的“session 目录”不仅是 `session.json`，还包括 `trajectory/events.jsonl`、`mutations/`、turn trace 等持久化材料。N4 已核清：正常 SessionHost/ACP 默认装配这些数据源，联读可支撑 LLM 独立报告、工具 exchange 关联和 write/edit ai-code 主要输入；trajectory/blob 降级不推翻大方向。详见 `nodes/session-data.md`。

| 能力 | 主要数据源 | 边界 |
|---|---|---|
| sessionId | session meta、trajectory envelope | 基本精确 |
| logical turn/spanId | TurnRecord/ActiveTurnTrace/run-owned 快照（ID 原值直用，2026-11-18 原值裁决不转 UUID） | B4 已确认 spanId=真实 logical turn ID 原值；retry 复用 logical，pass 仅作本次执行身份，不恢复旧 uuid5 公式 |
| 成功模型调用 ID | 最终成功 assistant message 的 `_chrys_request_attempt_id` | 暂定为服务器主 requestId；缺失时跳过并记录原因，不用 exchange 混填 |
| exchange/HTTP attempt 诊断 | exchange operation ID、model.request.*、turn trace | exchange 用于内部关联和回退；全部 attempts 仅作诊断，不作为当前业务主键 |
| 工具生产 attempt | call_item→function_call→assistant message，或成功 exchange finished | 关联实际返回 function_call 的 attempt；多 attempt 缺直接字段时不能取 attempts[-1] |
| 工具 funcId | 真实 tool operation ID 原值（不转 UUID） | 普通本地工具 funcId=T 原值（32hex），不是恢复 provider call_id；provider ID 仅用于内部 join，缺失时不伪造 |
| 工具名称、原始参数、状态 | session + tool operation events | 审批改写后的最终参数另行分类；仅适用于本地普通工具，不能套到所有广义调用；三个执行时间字段全部去掉 |
| 技能使用 | skill reminder、load_skill 工具上下文 | 关联语义需避免旧 session-latest 缺陷 |
| local sub-agent 内部工具 | 父 trajectory 的 child actor + 独立 child audit | 按 child 自身 E/A；不得挂父 E0/A0 |
| provider-hosted 工具 | hosted call/result + assistant M + hosted.call.observed | 主要业务字段可恢复；三个执行时间字段全部去掉，无需实时 presentation 时间或耗时 |
| 文件 before/after | chrys_mutations + mutations/blob | 缺失、二进制、超大时降级 |
| 审批状态 | approval events、trajectory envelope | 执行时间和耗时不再映射或上报 |

## 4. 分支相关的 fork 上游接缝

下表表示“当前 0.35.2 在相应分支没有正式组合入口”，不代表所有路线都必须修改这些文件。最终行数和 R2 由实施批次 design 重新核定。

| 上游文件 | 适用分支 | fork 接线及原因 |
|---|---|---|
| `src/chrys/service/llm/clients.py` | N1-A | 统一组栈安装 ChatMiddleware；动态 body 必须在请求前写入。N1-C 不需要 |
| `src/chrys/orchestration/engine/run/turn_state.py` | 当前 N3 完整身份推荐 | 持有并清理 run-owned logical/pass/turn_number/is_retry 快照 |
| `src/chrys/orchestration/engine/run/runner.py` | 当前 N3 完整身份推荐 | pre_run 清旧值，在 trajectory await 前写入当前身份；disabled 也不丢 pass/logical |
| `src/chrys/orchestration/engine/run/finalizer.py` | N3，适用于 N1-A/N1-B/N1-C 的进程内事后分析 | 保存尝试/checkpoint 后、外部 after_turn 前 direct dispatch，显式携带 saved/status；完整身份来自上述快照 |
| `src/chrys/orchestration/engine/session_lifecycle.py` | 当前 N3/N8 推荐 | 正常 teardown 和 active delete 前集中 per-session 有界 flush/close；不逐 TUI/ACP 入口接线 |
| `src/chrys/app/acp/server.py` | 保留旧 ACP `_meta` 契约的分支 | 捕获桌面输入并合并最终输出；当前入口丢弃 kwargs且响应无旧 envelope |
| `src/chrys/orchestration/engine/build/builder.py` | N1-A/N1-B 或选择请求链补采上下文 | 为 middleware 传 workspace/Agent 等；N1-C 可改用 after_turn/ACP 补采，不默认需要 |

当前 N1-C 直接复用现有 attempt header，不需要 body middleware 或 exchange header。只有开发期回退 N1-B/N1-C1 时才涉及 `Chrys-Exchange-Id` wire stamping；N1-A 和 C2 也仅作为备选。

## 5. 适合向 iCode 提出的通用改动

详细通用性论证见 `upstream-proposals.md`。

| 优先级 | 建议 | 通用价值 | 可消除的 fork 成本 |
|---|---|---|---|
| P0 | 正式 ChatMiddleware 注册与稳定只读上下文 | 审计、脱敏、安全、缓存、流量治理、第三方观测 | `clients.py` 组栈及内部上下文耦合 |
| P0 | 进程内 AfterTurn/SessionEnded 生命周期 API | 轻量指标、缓存、内部分析、本地审计；载荷含 logical/pass/retry/status/saved，明确轻量同步、后台 worker 与有界 flush | fork 自行维护 run-owned 身份快照、direct finalizer 耦合和外部进程开销；是否用 EventBus 是 API 选择，不改变身份职责 |
| P1 | 公共 exchange context helper | 通用 tracing、日志关联、调试 | 对 ChatContext.kwargs 内部结构的依赖 |
| P1 | 正式 `Chrys-Exchange-Id` header | 网关追踪、retry/redirect 去重、跨 HTTP 请求关联 | 自定义 header/wire stamping；与 attempt header 并存 |
| P1 | 可选结构化 tool invocation audit | 权限审计、最终参数分析、执行调试 | final args/internal ID 的文件缺口；须脱敏和限长 |
| P2 | ACP model-call notification | 客户端逐调用展示、诊断和实时观测 | 仅在有真实消费方时考虑，非当前默认 |

### 不建议向上游提出

- AIxCoding 专属 telemetry envelope、内部后台字段或 CSAS 端点；
- 改变 `request_attempt_id` 的 per-HTTP-attempt 语义；
- 把 exchange ID 塞进 `Chrys-Request-Attempt-Id`；
- 为兼容旧缺陷提供 session-latest 猜测或取消伪报失败；
- 为本需求明确排除的崩溃补报增加持久化机制。

## 6. 只能降级、运行时补采或另行裁决的能力

| 缺口 | 为什么文件不够 | 可选处理 |
|---|---|---|
| 审批/hook 改写后的最终工具参数 | 审批 modified_args 会写回 function_call；其他 hook/执行阶段改写未必持久化，trajectory 只有最终指纹 | 审批改写从 session 恢复；其余按证据降级、运行时补采或建议通用 audit |
| 内部工具 12 位 fallback ID | 多数不持久化 | 当前 final-only 路线可从 T 派生稳定 UUID 并在重放中复用；不需要 save/update 两阶段，也不能冒充恢复旧随机原值 |
| 历史 channel/workspace/Git | 当前进程 cwd/HEAD 和最终 session cwd 不代表事件时事实 | 运行时捕获；无 workspace 省略，不猜测 |
| blob 缺失、过大、二进制 | before/after 内容不可用 | ai-code 降级/省略并记录，不造 blocks |
| 外部 ACP 子代理内部过程 | 父 trajectory 只有边界，独立 audit 只有有界 update 投影 | **当前已退出范围**；本地投影不冒充远程内部真值，不再以补采/外部协作作为本任务待办，三个执行时间字段同样删除 |
| provider-hosted 实时时间/耗时（已移除） | hosted 内容不是本地 tool operation，实时 presentation 字段未全部持久化 | 主要业务字段文件重建；三个执行时间字段全部去掉，无需本地或 provider 补采，不强套 T/C |
| 工具取消终态 | 新版有 interrupted，旧后台 codeStatus 无 cancelled | 不伪报失败；登记协议限制，待后端扩展 |
| 崩溃/强杀当轮 | hook 未发生，部分数据未落盘 | 本任务不做补报，接受边界 |

## 7. 旧功能到新版机制的映射

| 旧版功能 | 新版主要来源/机制 | 仍需运行时接缝 |
|---|---|---|
| 原模型业务记录 + LLM body telemetry | 原成功请求保留现有 attempt header；after_turn 另发独立 LLM 报告 | 当前 N1-C 不需要 ChatMiddleware 请求前注入；B7 独立 endpoint 为暂行契约 |
| tool-detail save/update | tool operation + session function_call + after_turn analyzer | 改为单次 final save，requestId=A1 原值、funcId=T 原值，无 PENDING/update；final args 视保真要求降级 |
| local sub-agent 内部工具 | 父 trajectory child actor + child audit | 按 invocation/actor 隔离，使用 child 自身 E/A |
| provider-hosted 工具 | hosted call/result + assistant M + hosted observation | 三个执行时间字段全部删除，不补采，不能套本地 T/C |
| 外部 ACP 内部工具 | 有界 translated_updates 投影 | 当前退出范围；本地投影不等于远程内部审计，不再列补采待办 |
| slash/load skill | Skill Reference reminder + tool context | 当前 logical turn/span 与精确归属；slash 恰好一次留实施 |
| selected Agent funcType=1001 | ACP selected-agent 输入 + prompt scope | ACP 输入捕获和 reporter |
| ai-code | mutation ledger/blob + tool operation + approval | after_turn 单次 final 分析；requestId=A1 原值、reportId=T 原值，同 T 多 mutation 跳过 |
| ACP request/span | live 主 history + TurnRecord + 精确 logical turnId；上游身份直接复用 | 暂行在 prompt_lock 内选择 raw A-final，requestId 直接用原值（无转换）；只改 ACP server+新增定制 helper，无需 registry或 request_tracking/ids 改动 |
| mock | 单端口组合为当前评估目标，1A 现有骨架/1B telemetry 为 AI 分步建议 | 无需产品上游改动；telemetry 存储/幂等尚未实现，不长期维护双组合 |

## 8. Request ID 当前研究状态

责任人于 2026-11-16 暂定 N2-B-final：**以实际产生最终成功响应的 request attempt ID（A-final）作为服务器主 requestId**。只记录成功模型响应，不再要求维持旧版“一次端侧逻辑调用一个主 ID”的粒度；开发期发现严重问题时暂停并回评 exchange，不承担上线后历史迁移。

```text
服务器主 requestId = 最终成功 assistant message._chrys_request_attempt_id（A-final）【暂定】
exchange ID         = 内部关联、retry 边界和开发期回退证据
失败/pending/部分流 = 不上报；缺 A-final 跳过并记录原因，不用 exchange 混填
```

session/trajectory 已提供内部双 ID 关联：

```text
assistant message._chrys_operation_id = E
assistant message._chrys_request_attempt_id = A-final
工具 parent_model_operation_id → assistant message 的 E/A-final
mutation → tool operation → parent exchange / assistant message
```

当前 N1-C 可直接复用现有 raw `Chrys-Request-Attempt-Id`：2026-11-18 原值裁决后，后台原成功记录直接保存 raw A-final 原值，after_turn 独立报告、tool-detail、ai-code 和 ACP 使用同一原值文本，无转换层，无需新增 exchange header 或 E↔A 映射。C1/C2 仅作为开发期回退 exchange 的备选通道；N1-A/N1-B 不再承担当前主键上传。

2026-11-18 原值裁决（此前短暂的后台归一化配合作废）：内部 header/session/trajectory/message 与所有外部记录使用同一 32hex 原值；request_tracking.py 与 ids.py 不改。配套需后台接受 32hex 格式并与 0.28 UUID 文本历史数据混存，Agent Studio schema 放宽接受 32hex；联调是验收前提。

详见 `nodes/request-id.md`、`request-identity.md` 和 `../experiments/request-identity.md`。主键方向和缺失处理已暂定，A-final 原值服务器闭环及上传通道细节仍需开发期验证。

## 9. 后续讨论与沟通顺序

1. 主要节点已收敛：独立评审/复审已完成，责任人已裁决实施组织并经 2026-11-19 修订为长期根分支模式，探索批次已签认且 commit 已落分支；OpenAI Codex 技术评审 F1–F6 已裁决，F1–F3 对应 V1–V3 是批次1前置判别。剩余 R2 授权待批次1 requirements/design 签认后启动，不以本导航代替批次 design。
2. 首个开发切片建议为真实 after_turn→reader→reporter→mock；共同 golden、外部 requestId 存储 join、工具/ai-code final DTO 与原子幂等在实现中验证。
3. 随后完成真实 ACP server×桌面闭环：按 session/turn 输入捕获、selected Agent 1001/desktop 上下文、prompt_lock 内 live-history 选择、A2 原值、attribution 和 `final-model-identity`（桌面 schema 放宽接受 32hex）；Git 精度语义继续留实施。
4. funcId 与 B4 已确认，B5/P2 三个执行时间字段已全部删除；slash 去重、cancelled/interrupted 和真实嵌套父 turn 按实际场景留实施/联调。
5. 上游建议仍需逐项通用性评审；fork 是否等待上游由责任人另行裁决，不因技术建议自动开工。
