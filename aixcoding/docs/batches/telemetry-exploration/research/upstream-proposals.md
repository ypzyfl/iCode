# iCode 上游通用能力建议候选

> 状态：探索候选，尚未形成对外提交版本；2026-11-17 当前有效汇总见 `review-handoff.md`。每项必须先证明通用价值，再讨论 API；不请求 AIxCoding 专属 telemetry 字段或内部后台契约。

## 通用性审查门槛

每项建议需回答：

1. 除 AIxCoding telemetry 外，哪些通用 AI 工具用户也需要？
2. 上游现有机制为什么不足，能否仅通过文档化现有 API 解决？
3. 是否能保持上游默认行为不变，并兼顾性能、安全和隐私？
4. 是否扩大长期公开 API 的维护成本，能否用更小 helper 替代？
5. fork 在等待上游期间是否需要最小接缝，未来如何移除？

## 改动与边界分类总表（2026-11-16）

> 分类描述当前探索路线的适配方式，不表示上游已经接受，也不授权 fork 实施。所有“需要我们自己定制化”都必须另行经过最小性比较和 R2 签认。

| 事项 | 分类 | 适用方案与当前边界 |
|---|---|---|
| 进程内 lifecycle subscriber API | 可建议上游 iCode 团队修改 | 通用 AfterTurn/SessionEnded 应携带 logical/pass/retry/status/saved；若上游暂不接受，fork 当前推荐 run-owned 快照+direct finalizer+集中 lifecycle 四文件接缝，N3-B 通用事件留多消费者再评 |
| `Chrys-Exchange-Id` 并保留 attempt header | 可建议上游 iCode 团队修改；上游不接受时需要我们自己定制化 | 当前 A-final 路线不需要；仅开发期回退 C1 时重评 `chrys_headers.py` + `request_tracking.py` 两处集中接缝，C2 不需新增 header |
| ChatMiddleware 注册与 exchange 读取 helper | 可建议上游 iCode 团队修改 | 主要服务 N1-A/N1-B；当前 N1-C 下本 telemetry 不需要，不应提前定制 |
| 结构化 tool invocation audit | 可建议上游 iCode 团队修改 | 只在高保真确有必要时提出；接受字段降级则取消，需先证明现有 hooks 不足 |
| ACP 标准流式内容、turn 身份和 request-attempt 查询 | **上游已有，无需新增建议** | b4f354d（v0.30.1）和 9cd8031d（v0.31.0）已提供；当前 0.35.2 直接复用，不再建议逐模型调用 notification |
| ACP 最终 PromptResponse 的内部 telemetry envelope | 需要我们自己定制化 | 责任人确认最终响应必须主动携带 requestId，并暂按 AI 建议在 fork ACP 输出组合层从 live 主 history 精确选择、组 envelope；只需 server 接缝+定制 helper，无需 registry，不请求上游理解 Agent Studio 专属字段 |
| ACP model-call notification | 不提出 | 当前最终响应契约和上游标准流式输出已覆盖需求，没有新增逐模型调用通知的消费方 |
| ACP 输入的 session/turn 捕获、selected Agent/desktop envelope 消费 | 需要我们自己定制化 | 属于本产品消费契约和入口组装；应集中在 ACP 入口，不请求上游理解内部 envelope。Q2 已确认纳入实施，保持桌面 0.28 能力 |
| 外部 ACP 远程内部 exchange、真实工具名/类型 | 现有输入下无法做到 | 真值需要外部 Agent 协作，不是单靠修改 iCode 上游即可解决；provider 真实执行时间已随三个执行时间字段全部移除而退出需求，不向上游提出 |
| 崩溃/强杀完整补报、无依据恢复历史 Git/文件/旧随机原值 | 当前约束下无法做到，且不列为需求 | 不提出上游建议，不通过当前状态猜测或新增启动扫描绕过 |

## P0：正式 ChatMiddleware 注册与稳定只读上下文

- **适用分支**：N1-A 请求 body 注入，或其他确实需要请求前处理的场景；N1-C 独立 LLM endpoint 下，本 telemetry 不需要该能力。
- **通用场景**：请求审计、脱敏、安全策略、缓存、流量治理、自定义观测和第三方 OpenTelemetry 集成。
- **当前不足**：ChatMiddleware 本身能修改 options，但产品 client 组合层没有正式注册入口；profile extra_body 只能提供静态值。
- **建议方向**：允许应用组合层/扩展注册 middleware，提供 session、turn、exchange、actor/origin、workspace、agent profile 等稳定只读上下文。
- **非目标**：不要求上游理解 AIxCoding telemetry envelope，不要求内置内部后台字段。
- **潜在收益**：消除 fork `clients.py` 组栈接缝，并降低对内部上下文传递结构的依赖。

## P0：进程内 lifecycle subscriber API

- **适用分支**：N1-A/N1-B/N1-C 中所有需要事后分析、状态投影或本地审计的方向，不绑定独立 telemetry endpoint。
- **通用场景**：轻量指标、缓存、内部分析、状态投影和本地审计，不希望每轮启动外部脚本进程。
- **当前不足**：after_turn/session_end 用户 hooks 本体是外部子进程；现有 EventBus 没有对应内部 AfterTurn/SessionEnded 事件。`SessionSaved` 早于 checkpoint 且保存失败不发布，successful-turn callback 仅覆盖成功 turn，均不能单独替代。
- **建议方向**：复用现有 EventBus 的 inline `subscribe()`/`publish()`，在 save 尝试和 trajectory checkpoint 后、外部 after_turn 前发布通用 `AfterTurn`；另在 session lifecycle 提供每 session 一次的 `SessionEnded`。不另造第二套 subscriber 框架。
- **同步语义**：inline callback 只做轻量 registry/不可变快照和入队；publish 返回不代表重文件分析或网络投递完成。若消费者要求 ACP 响应携带分析结果，需另有有界同步准备和超时降级，不能宣称同时完全后台且不阻塞。
- **事件边界**：载荷包含 session/logical turn/pass 身份、turn number、retry、status 和 `saved`；保存失败仍可通知但不得分析旧文件冒充本轮。强制关闭和崩溃不保证 after_turn，网络不在 inline callback 中等待。
- **失败与退出**：普通 subscriber 异常隔离，`CancelledError` 不吞；跨 session 不依赖 per-host bus 提供全局串行。自定义 worker 必须显式接入有界 session/process flush，不能假设 fire-and-forget 自动 drain。
- **非目标**：不替代现有外部 hooks，不赋予遥测插件额外权限，不让 core 理解 AIxCoding 报文。
- **潜在收益**：以通用事件及其身份载荷消除 fork 自行维护 run-owned 快照和直接 analyzer/finalizer 耦合；若只做 fork 过渡，触发点可直接在 finalizer，但完整身份和 lifecycle 仍需 N3 节点第14节的四文件候选。

## P1：公共逻辑模型调用上下文 helper

- **适用分支**：N1-A/N1-B 请求前读取；N1-C 从事后 trajectory 获取 exchange，不需要为该目的新增 helper。
- **通用场景**： tracing、日志关联、调试和 middleware 需要稳定读取逻辑 acquisition ID。
- **当前不足**：ExchangeTrace 已存在，但 middleware 需了解 ChatContext.kwargs 的内部传递结构。
- **建议方向**：文档化或提供只读 helper，固定“逻辑 exchange 一个 ID、body 前可读、SDK retry/redirect 不变、外层 wire retry 新建”的语义。
- **明确不建议**：改变 request_attempt_id 的 per-HTTP-attempt 唯一性或重试行为。

## P1：正式 `Chrys-Exchange-Id` header

- **适用分支**：开发期回退到 N1-B/N1-C1 时按 exchange 合并原调用记录与独立 telemetry，或独立的通用网关追踪需求；当前 N1-C A-final 路线及回退 N1-C2 都复用现有 attempt header，不需要新增 exchange header。
- **通用场景**：网关和客户端需要将 SDK retry、redirect 等多个 HTTP 请求关联为同一 exchange，同时保留每个 attempt 的独立诊断 ID。当前 Responses continuation 每次 poll 都新建 exchange；若上游还希望用同一 E 分组整个 create/retrieve 周期，需要另行改变 exchange 生命周期，单靠新增 header 做不到。当前只关联最终成功响应时没有该分组需求。
- **当前不足**：现有 `Chrys-Request-Attempt-Id` 只标识单次 HTTP attempt；exchange operation ID 已持久化但不会自动上 wire。
- **建议方向**：新增 `Chrys-Exchange-Id`，与 attempt header 并存；同一 exchange 的所有 attempts 使用相同 exchange ID，每个 attempt 继续使用不同的 attempt ID。
- **实现边界**：`Chrys-*` 当前是保留 header 前缀，不能由普通 `extra_headers` 注入，需上游在统一 request metadata/header stamping 层支持。
- **兼容性判断**：不建议把“替换 `Chrys-Request-Attempt-Id`”作为默认提案。替换会删除逐 HTTP attempt 诊断维度并改变既有公开契约；只有上游确认无消费者且明确接受该破坏性变化时，才将替换作为独立决策重评。
- **非目标**：不改变 attempt ID 语义，不要求网关理解 AIxCoding telemetry body，不规定服务器如何聚合业务数据。
- **fork 过渡**：C1 下最小生产改动是在 `foundation/util/chrys_headers.py` 增加常量，并在 `service/llm/request_tracking.py` 的共用 prepared-request hook 写入 `context.exchange_operation_id`；现有 attempt header 保持不变，不需要 body middleware 或逐协议客户端改动。测试需扩展现有 request-tracking 三协议、retry、redirect 和并发用例。body `telemetry.requestId = exchange ID` 和自定义非保留 header 仍是其他分支的备选，长期以通用上游 header 为优。

## P1：可选结构化 tool invocation audit

- **通用场景**：工具权限审计、执行调试、参数改写分析和通用遥测。
- **当前不足**：审批 modified_args 会写回 function_call，可离线恢复；但其他 hook/执行阶段改写未必持久化，trajectory 只保留最终参数指纹，部分内部 ID 也不能可靠离线恢复。
- **建议方向**：以 operation ID 为主键，可选记录 provider call ID、origin、最终执行参数的安全投影、审批改写标记和终态。
- **安全约束**：默认不记录敏感完整参数；需要脱敏、大小限制和明确的启用策略。
- **待证事项**：现有正式 extension/tool hooks 能否以更低成本满足，避免重复建设。

## P2：通用 ACP model-call notification

- **通用场景**：客户端展示每次模型调用、诊断 retry、关联工具调用和实时观测。
- **当前不足**：ACP 有 turn/update identity 和 request tracing 投影，但没有直接对应每次 middleware 调用的实时通知。
- **建议前提**：先找到真实消费方，证明最终 PromptResponse 或现有 turn trace 不足。
- **非目标**：不请求 `agent-studio.dev/telemetry` 等内部专属 envelope 进入上游。

## 当前不建议提交的建议

- 为 AIxCoding 增加专用 requestId、spanId 或 telemetry body 字段。
- 改变 request_attempt_id 的现有 per-attempt 语义。
- 为兼容旧缺陷而增加 session-latest 猜测、取消伪报失败等能力。
- 在无真实消费方时预先增加 ACP 流式通知。
- 为本任务明确排除的崩溃/强杀补报增加上游持久化机制。
