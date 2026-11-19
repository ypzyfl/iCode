# 测试方案：Telemetry 方案探索（telemetry-exploration）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

本批验证对象是“研究结论是否有充分证据”，不是正式功能交付。证据强度从低到高分为：静态源码与文档、上游测试语义、Git 历史、针对性测试执行、真实 session/mock 端到端样本。实施批次的单元、契约和端到端测试不在本批预先声明通过。

优先复用现有上游测试；本探索的 M0/M1/session/queue 采用 test-local 真实文件与上游 API harness，尚未接 `aixcoding/mock/`。新增实验代码仅允许落在定制目录并登记；生产实现才复用/扩展 mock。涉及上游 anchor 时，实施批次必须真调上游符号做行为锚定测试，禁止只 mock 锚点本身。当前评审入口见 `research/review-handoff.md`。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试/调查入口 | 类型 |
|---|---|---|
| 完整能力矩阵 | `research/capability-matrix.md` + 各专题源码证据 | 静态调查，逐专题补充运行样本 |
| request/attempt/exchange/turn/tool ID 语义 | `research/request-identity.md`、`experiments/request-identity.md`、`tests/service/llm/test_request_tracking.py` | 静态 + 行为锚定 + 契约样本 |
| 结论状态可区分 | 各 research 文档的“事实/建议/开放问题”节 | 文档审查 |
| 上游建议具备通用性 | `research/upstream-proposals.md` 的通用场景与反向审查 | 方案评审 |
| 旧版缺陷有处置 | 后续 `research/defect-register.md` | 静态对照 + 针对性样本 |
| 实验可复现且失败留痕 | `experiments/`、`verification.md` | 命令、输出摘要、样本核对 |
| 收敛后再拆实施批次 | `plan.md` 的开放问题清零/保留裁决记录 | 责任人裁决，不设机械完成时间 |

## request-identity 判别矩阵

| 场景 | 必须区分的预期 | 证据状态 |
|---|---|---|
| SDK 内 HTTP retry | 一个逻辑 exchange，可有多个 request attempt；最终 message 只带最后 attempt | E1 10 passed，stream=False/True 均覆盖最终 A |
| Chrys wire retry | 新逻辑 exchange、新 request attempt | 上游集成测试已静态定位，待执行/样本复核 |
| redirect | 每个 hop 新 attempt，不能覆盖原 exchange ID | 上游测试已静态定位 |
| 非流式/流式 | attempt 在 prepared 产生，流终结由 exchange 表达，不能以 headers 代替完成 | 本轮流式相关 6 项现有行为测试通过；新 analyzer 组合待验证 |
| Responses create/retrieve | 二者均可有 attempt header；retrieve GET 无 create body；当前每次 poll 新建 E | 源码已核实，E/A-final 组合待样本核对 |
| 模型失败且全部 retry 耗尽 | session.json 无本次成功 M；trajectory 可有 E 和失败 A；attempt-only 不上报 | 待开发期 analyzer 验证，不取最后失败 A |
| 前次成功、本次失败/部分流取消 | 不借用历史 M 的旧 A；不产生本次成功关联 | 待开发期 analyzer 验证，属严重错关联拦截项 |
| 模型成功、工具失败或后续 turn 失败 | 成功 M 的 A-final 仍有效；工具 outcome 独立，ai-code 仍按成功写入条件 | 待开发期组合验证 |
| middleware body 注入（仅回退分支） | exchange operation ID 可在 body 构造前读取，attempt ID 尚未生成 | 调用链已核实；当前 A-final 路线不执行，回退时再做三协议实验 |
| 无 ExchangeTrace / 缺 A-final | 有可信成功 A 时可使用；缺 A-final 跳过并记录原因，不用 exchange 或 UUID4 混填 | 待开发期验证 |
| 后台 ID 格式 | 内外均为 raw 32hex 原值，不转 UUID；后台原值保存，客户端无转换层（2026-11-18 原值裁决） | 32hex 格式接受/新旧混存待后台确认；桌面 schema 放宽待落实 |

## A-final 五类记录最小闭环矩阵

详细现有能力和源码证据见 `research/a-final-e2e-closure.md`。五类记录不能机械断言全取同一个 A：A1 产生工具调用，A2 产生工具后的最终文本；tool/ai-code 取 A1，最终 ACP 通常取 A2。

| 场景 | 必须区分的预期 | 证据状态 |
|---|---|---|
| M0 原模型与独立 LLM | A1/A2 各有原成功记录和独立报告；两者均为 raw 原值 32hex，无转换 | 测试态目标 DTO 通过；真实 mock/analyzer/reporter/落库未实现 |
| M0 tool-detail | requestId=A1 原值而非A2，funcId=T 原值 | 真实 write_file 关联和测试报文通过，生产报文/存储未实现 |
| M0 ai-code | requestId=A1 原值，reportId=T 原值，blocks与最终参数/after blob一致 | 真实 mutation/blob 与测试报文通过，生产重建器/存储未实现 |
| M0 ACP | 最终身份=A2 原值，回显桌面 response-attribution span；不产生身份时 fail closed | 测试态 selector/envelope 通过；真实 server、attribution 捕获和桌面闭环未实现 |
| 桌面 envelope | 使用 `agent-studio.dev/final-model-identity`，requestIdentified先于complete；schema 需放宽接受 32hex 原值 | 静态源码已核实；桌面 vitest 因缺模块未运行，telemetry key 不足以触发消费 |
| M1 严重错关联 | 两工具共享A1但funcId不同；失败/pending/部分流不生成成功记录，不借旧A；并发不串号 | 两工具、400失败turn和两scope并发联合实验通过；pending/部分流仍由底层锚点与实现矩阵覆盖 |
| M1 retry/redirect/Responses | 每请求记录存自身A，成功由独立报告join声明；Responses场景报告带retrieve A而非create A | 429→A1→A2、Responses POST pending→GET completed及上游redirect联合复跑通过 |
| 遥测重放 | 语义重放不新增，同键不同内容409，组合键原子唯一 | 目标契约明确，存储待实现；不得与模型SDK retry混同 |
| 模型 toolUseId 对账（端侧） | BR-8 已于 2026-11-19 撤销，报文不含 providerCallId；需要时由客户端按 funcId=T 本地反查 function_call.call_id 完成 | 责任人已裁决；端侧反查实现留批次1 |
| 0.28全字段 parity | 公共字段及parentSpanId语义、agentName、fileName、value、行数、failureType/funcErrorMessage、language、gitUserName/Email等逐项有保留/删除/待确认结论 | M1-T必须产出完整矩阵并与BR-1/5/6同批确认；未关闭不得判真实联调/上线通过，不前置阻塞外网mock开发 |
| cancelled与中间attempt（BR-9/10） | 取消不伪报普通失败；中间/失败attempt的落库、标记、保留与孤儿口径明确，成功关联仍取A-final | 待后台确认和故障注入 |

## Session 文件重建正确性矩阵

详细实验见 `research/session-reconstruction.md` 与 `experiments/session-reconstruction.md`。当前方向 reader 只接收 session_dir/session_id 和可选 expected logical turn，不使用 live message 或已知 A/T；F2 裁决要求生产 reader 增加 expected pass 契约，V2 完成前不得声称已具备 pass 隔离。2026-11-19 F5 裁决保留既有精确数量断言，并统一标记完整支持、批准降级和待判别场景；空结果不得替代正常场景的完整性验收，也不设虚构覆盖率百分比。

| 场景 | 分类 | 预期数量、必需字段与允许跳过 | 当前证据 |
|---|---|---|---|
| 正常两轮/三模型响应 | 完整支持 | 3 LLM/1 tool/1 ai-code；requestId/spanId/funcId/reportId及必要内容齐全，tool/ai-code取第二轮A1/T，不允许跳过 | 真实文件组合通过，重复分析完全一致 |
| 工具终态 gap | 批准降级 | 原样本2 LLM/0 tool/0 ai-code；记录trajectory-untrusted和outcome unknown，不从function_result猜成功 | 删除真实finished事件+verify_accounted_prefix通过 |
| after blob缺失 | 批准降级 | 原样本2 LLM/1 tool/0 ai-code；记录blob/args原因，不读当前工作区补历史 | read_blob=None降级通过 |
| save=False | 批准降级 | 当前turn/pass为0 LLM/0 tool/0 ai-code并记录expected-turn-not-saved；不得把旧session当本轮 | suppressed save组合通过；无guard只返回旧轮，风险已实证 |
| fork继承 | 完整防重 | 继承turn为0 LLM/0 tool/0 ai-code；无本地events记录trajectory-absent，不以新sessionId重报父历史 | 真实fork文件通过 |
| trajectory absent/disabled | 批准降级（异常路径） | 可归属成功LLM按实际M计数；当前reader为0 tool/0 ai-code并记录缺失/不可信原因，不伪造终态 | absent已有局部证据；完整disabled组合待做 |
| V1 延迟读取×下一轮保存 | 待判别 | 前一pass记录数等于其实际成功执行数，A/T/mutation/blob关联及必需字段完整；不得混入下一pass | 第一批前置，未执行 |
| V1 延迟读取×回滚/压缩 | 待判别 | 不跨pass、A/T或mutation错配；逐项列出恢复与跳过记录，跳过是否足够由责任人裁决 | 第一批前置，未执行 |
| V2 同logical两个pass | 待判别 | 首任务pending/running/completed时新pass均不丢失；同pass纯重放不重复，前序来源仅用于关联，旧工具不重报；1001仍一条 | 第一批前置，未执行 |
| V3 当前轮真实压缩 | 待判别 | 同turn早期A1/T/代码修改经实际压缩后，恢复数量、关联和必需字段满足完整或经批准降级；不能恢复则停止扩张回评 | 第一批扩大开发前，未执行；完整矩阵留批次3 |
| 全量edit/真实脱敏会话 | 待实施/授权样本 | edit blocks准确、逐场景预期数量和必需字段明确；真实样本覆盖率可量化 | 不宣称完成 |

## 性能与队列生命周期矩阵

详细数据见 `research/performance-and-lifecycle.md` 和 `experiments/performance-and-queue.md`。计时只记录增长，不设任意阈值；5/15/30 轮累计/量级已通过，不做严格 CI 性能门禁。队列是测试态原型，不冒充真实 engine 接线。

| 场景 | 必须区分的预期 | 当前证据 |
|---|---|---|
| 全量 vs expected-turn | 当前轮报文完全一致；expected过滤不应当作I/O优化 | 30轮等价断言通过，两者均约7→38ms线性增长 |
| 通知去重 | 普通通知按session/logical turn/pass合并同pass重复，新pass在pending/running/completed均不丢弃；1001仍按logical turn一条；记录级幂等作第二道防线 | 2026-11-19 F2裁决的设计口径；生产dispatcher未实现，V2待执行 |
| 持久化高水位 | 仅为性能缓存，不为已排除的崩溃补报服务 | 不作为正常正确性前置 |
| 同session FIFO | 前项阻塞时后项不开始，释放后有序 | 队列原型通过 |
| 跨session并发 | 两session reporter可同时执行 | 队列原型通过 |
| flush/close | 永久阻塞时有界返回，close取消且幂等，无pending警告 | 20ms超时原型3项通过 |
| 真实after_turn/退出 | 通知带turnId/saved；TUI/ACP/delete追踪owner并有界flush | 当前payload缺字段、engine不追踪worker；最小四文件接缝与集中owner已静态收敛，留实施design/R2 |
| queue depth/大blob | 慢后台不无界积压，大blob不重复读全历史 | 未验证，生产design必须给出丢弃/日志与性能口径 |

## N3 进程内 after_turn 判别矩阵

| 场景 | 必须区分的预期 | 证据状态 |
|---|---|---|
| 正常/retry/失败/普通用户取消 | 轻量内部通知在真实 ACP PromptResponse 前完成；logical turn 与 pass ID 不混用，N7 不等待 registry | 正常静态调用链已核实，组合待 N3-E1 |
| retry × trajectory enabled/disabled | 两种配置均从run-owned快照取得身份；retry时pass不同/logical相同，disabled不借旧trace或latest TurnRecord | runner/recorder调用顺序已静态核实；快照与组合行为待实施N3-E1/E3 |
| pre_run身份分配前失败 | 旧快照已清空，无当前身份则skip；不得沿用上一轮 | 候选接缝已静态明确，行为待实施测试 |
| save=False | 通知携带保存失败；不读取旧 session 冒充本轮，saved 与 status 不混淆 | 源码已核实，行为待 N3-E2 |
| 普通异常与 CancelledError | 普通异常不改变 turn outcome；CancelledError 传播，不吞、不假定后续 handler 继续 | EventBus 普通异常已有测试，direct dispatcher组合与取消待 N3-E2 |
| 强制取消 run task | 保存/checkpoint 与 after_turn/drain 的保证分别判断，不宣称每轮必通知 | 源码与现有 finalizer 测试已核实，矩阵待 N3-E3 |
| 两个 session 并发结束 | 进程级 reporter 按 session 键隔离；不依赖 per-host EventBus 提供全局串行 | 队列原型跨 session 并发已通过；真实 engine/owner 组合仍待 N3-E4 |
| ACP EOF/close/delete | 集中lifecycle对对应session有界flush+close；active delete在物理删除前完成，不销毁进程owner | 调用汇聚路径已静态核实，新增flush待N3-E5 |
| TUI new/restore/clear/delete | 旧session在切换前flush；active delete失败rearm后可重建worker，再次入队/flush可用 | 现有删除/重arm测试锚定，新增flush待N3-E5 |
| TUI/headless 正常退出、无 hooks | 不依赖HookManager存在；session close幂等，超时可观测，不假设fire-and-forget自动drain | 集中lifecycle接缝已静态核实，新增flush待N3-E5 |
| 轻量入队 vs 完整文件分析 | 分别测量耗时；N7 不等待 after_turn 分析或网络 ACK | 待 N3-E6 |

2026-11-17 已执行 EventBus、finalizer、session close/shutdown、runtime metadata、ACP manager/transport、headless run 和 TUI startup 九组现有测试，共 241 passed；这不是新增 dispatcher、AfterTurn/SessionEnded、worker 或 flush 已实现的证据。此前 23 项为同一探索较早批次，不能与 241 项简单相加。

## N7 最终 ACP 身份与流式矩阵

| 场景 | 必须区分的预期 | 证据状态 |
|---|---|---|
| 正常 turn 最终响应 | 最终 PromptResponse._meta 主动携带当前 turn 的 requestId，客户端无需另查；不得取 session-latest | 责任人已确认输出要求；定制实现待后续 design/测试 |
| 响应时 live-history 选择（暂行方案） | prompt_lock 内用 turn_slices+opening_item_id 精确匹配 logical turn，选最后非 marker 主 assistant 自身的 A；只读元数据，不读磁盘/序列化正文 | 新增方向实验 7 passed；真实 server/锁内接线未实现 |
| 上游身份数据源 | turn_started/session-update/PromptResponse 有 turnId，session/turns 有 modelCalls.attempts.requestAttemptId | b4f354d 源码/历史已核实；当前 0.35.2 相关测试通过 |
| 流式文本与推理 | 标准 agent_message_chunk/agent_thought_chunk 实时发送增量，附 turnId/turnNumber；最终响应不重复全文 | 9cd8031d 已核实；现有测试通过，无需新增逐模型调用通知 |
| 同一 session 多 turn/并发 | 精确匹配 turnId，锁释放前取局部结果；不同 session 不共享可变 registry，当前 turn 无成功身份不借上一轮 | 两 turn 方向实验通过；真实并发 server 行为待实现测试 |
| 多主模型调用/retry/redirect | 当前 logical turn 最后成功主模型响应的 A-final；最后响应缺 A 时不取更早 A，失败 hop 不覆盖 | 多调用、缺 A、injected retry 实验通过；redirect 由现有 request tracking 锚定 |
| side/sub-agent/压缩/旧历史 | 主 history 排除 side/sub-agent；opener 无法精确对齐时跳过，不按末尾猜测 | opener 缺失实验通过；真实压缩和旧历史降级仍需新增测试 |
| 桌面归因 span 与 ID 表示 | final-model-identity.spanId 回显桌面归因 span，turn span 另算；requestId 直接使用内部 raw A 原值（32hex，无转换，2026-11-18 原值裁决） | 桌面 schema 需放宽接受 32hex；后台格式接受/混存待确认 |
| ACP 输入与 selected Agent 1001（Q2） | 输入形成不可变turn上下文供after_turn；1001按(sessionId,logicalTurnId)去重一条、无T，关联当前turn首个成功主模型A-final；无成功/缺输入跳过，跨session不串值 | 责任人已确认保持0.28桌面能力；真实输入捕获/reader/reporter/桌面组合待实现 |
| save=False/取消/强制关闭 | save=False 读 live 内存而非旧磁盘；取消可带当前 logical turn 已有成功身份，无证据不伪造；强制关闭不保证响应 | 选择器无文件实验+finalizer/retry 锚点通过；真实 save=False ACP 端到端待实现 |
| Responses pending/放弃流 | pending poll 不是最终身份，放弃/半截流不进入成功完成 | 3 项现有 wire 行为测试通过 |
| 性能 | 响应时选择为 O(全 history 消息数) 元数据扫描，无磁盘 I/O；实测不达标才升级 registry | 复杂度由源码确定，尚无性能阈值或 benchmark，不预设问题 |

2026-11-17 首轮当前基线 29 项及后续 57 项，累计 **86 passed**。新增 `aixcoding/tests/telemetry/test_acp_response_identity.py` 首轮 4 passed/3 failed，修正实验自身的 tool role、INJECTED_KEY 和 metadata API 假设后 **7 passed**；定制 telemetry 目录连同既有工具身份实验 **9 passed**。UUID 影响面 `test_ids.py`、`test_request_tracking.py`、`test_turn_trace.py` **96 passed**，生产探针证明 canonical UUID4 当前校验为 False、旧 32hex 为 True。该结果促成了当时的归一化安排：内部保持 raw，后台原记录归一化，客户端定制出站边界转换，不再修改生成器或校验器。（2026-11-18 注记：该安排已被 ID 原值裁决取代——所有 ID 保持 32hex 原值不转换，桌面 schema 放宽接受 32hex；本段为历史验证记录保留。）

旧版 ACP helper 3 项同步测试通过；旧版两项异步 registry 测试因旧环境缺 pytest-asyncio 未运行，Agent Studio 单测因当前工作副本缺 vitest 模块未启动，均不记为行为通过或失败。上述结果不证明真实 ACP server 选择器接线、并发/save=False 端到端、最终 envelope 或桌面 UUID 闭环已实现。

## N4 session 目录数据覆盖矩阵

| 场景 | 大方向预期 | 证据状态 |
|---|---|---|
| exchange/pass/attempt | trajectory 正常时可恢复完整关联；session 只保留成功 assistant exchange 和最终 attempt | 源码与 turn trace 行为测试已核实 |
| 工具 parent exchange | 首选 tool operation 的 parent_model_operation_id；trajectory 降级时只能有限使用 assistant transcript fallback | 关联测试已核实，降级组合留实施 |
| 重复 provider call ID | 优先以 call_item_id 定位 occurrence，T/E 交叉校验；重复未解决 call_id 可共享 T，不靠 provider ID 或消息顺序猜测 | 源码与重复 ID 行为测试已核实 |
| write/edit 多次修改 | chrys_mutations + blob 提供逐次 before/after 和 hash 链 | mutation 行为测试已核实 |
| 大小/二进制/skip/缺 blob | 内容可检测并降级，不读当前磁盘冒充历史 | 策略测试已核实，完整 analyzer 留实施 |
| save=False/trajectory gap | 不把旧 session 或不完整日志冒充完整本轮 | 静态边界已核实，组合样本留实施 |

已执行 `test_mutation_operation_identity.py`、`test_traces.py`、`test_turn_trace_projection.py`、`test_mutation_tracker.py`、`test_snapshot_policy.py` 共 179 项并通过。这是现有持久化与投影行为锚定，不证明新 telemetry analyzer 或旧报文逐字段一致。

## N1/N10 独立 LLM 最小契约矩阵

| 场景 | 暂行预期（B7 委托 AI 制定） | 证据状态 |
|---|---|---|
| 最小成功 envelope | schemaVersion=1、sessionId、llm/success、requestId=A-final 原值（32hex）；span/parent 按真实 turn | 开发期暂行采用，来源已核实，现网未确认 |
| 原模型/独立报告 join | 原模型记录与独立报告均存 raw 原值，按 requestId 单键 join，无转换 | mock 实现待做 |
| 相同语义重放 | JSON key 顺序/空白不同仍 200且不新增，规范化值不变 | mock 实现待做 |
| 同键不同内容 | 409、不覆盖、保留 rejected/冲突原因 | mock 实现待做 |
| 缺字段/非法 UUID/缺 A | 400或客户端跳过并记录，不重新生成、不借历史 A | mock/客户端实现待做 |
| 无 model/usage/timing | 最小 envelope 仍可 join，不强制未确认业务字段 | 暂行契约明确，mock 实现待做 |
| golden | 双方对 00112233445566778899aabbccddeeff 等固定 raw 向量逐字节保存相同 32hex 原值（2026-11-18 原值裁决，无 UUID 转换） | B7 已登记，双方/桌面实现待验 |
| exchange/usage/attempt 来源 | outcome/usage/attempt 与最终成功 M 一致 | 现有三组测试 45 passed |

本暂行方案不证明独立 LLM 生产 endpoint 已存在，实施遇问题或后台正式契约不同则集中回评。首次测试命令引用了不存在的两个文件名，退出 4且未运行；改用实际 `test_exchange_and_validation.py`、`test_items_fork_and_usage.py`、`test_request_tracking.py` 后为 45 passed，不计入失败测试。

## N5/N6/N10 final DTO 与 ai-code 幂等矩阵

| 场景 | 暂行预期（B8 委托 AI 制定） | 证据状态 |
|---|---|---|
| tool 最小 final save | 七项必填、终态1/2/4、无 PENDING/update、三时间字段缺席 | 暂行采用，字段来源已核实，mock 待实现 |
| tool 重放/冲突 | `(requestId,funcId)` 唯一；语义重放200不新增，同键不同内容409 | 目标已确认，存储待实现 |
| tool 成功正文 | 仅 codeStatus=1，不新增 funcResponse/完整 stdout | 暂行采用，旧契约事实支持 |
| ai-code 幂等 | reportId=T 原值，`(requestId,reportId)` 唯一，重放确定 | 暂行采用，当前单 mutation 源码支持 |
| 同 M 同路径多次 write/edit | T/reportId 不同，多条保存，不按 path/requestId 误合并 | mock/组合待实现 |
| 同 T 多候选 mutation | 该 T 全部跳过并记录身份粒度不足，不共用键 | 负例待实现 |
| ai-code 内容冲突 | 同 `(requestId,reportId)` 不同 blocks/path/status 409不覆盖 | mock 待实现 |
| outcome 闸门 | failed/rejected/cancelled/partial mutation 无 ai-code；tool 可有终态 | 现有 mutation exits 测试锚定 |
| blob/参数缺失 | 缺 T/A/blob/最终参数无法验证时跳过，不读当前磁盘补猜 | 现有 pipeline/关联测试锚定 |
| 身份与 mutation 行为 | T/C/M/A、单 mutation、失败/取消边界稳定 | 73 collected：55 passed、18 skipped |

严格 mock 需另测非法 UUID、bool/float 数字、缺必填、空 blocks、非法 range、旧字段/时间字段400和 debug 碰撞。跳过测试不计为通过，也不证明新 DTO/存储已实现。

## N5 工具与技能关联矩阵

| 场景 | 大方向预期 | 证据状态 |
|---|---|---|
| 普通工具/load_skill → exchange | tool operation parent E，或 function_call 所在 assistant M 的 E | 现有行为测试已核实 |
| 普通工具/load_skill → 生产 attempt | call_item→function_call→M._chrys_request_attempt_id，或成功 exchange terminal 的 A | 真实 engine/scripted HTTP 最小主链已通过；完整组合留实施 |
| 同一 M 多个工具/重复 call_id | 多工具共享 A-final，以 C/call_item_id 区分 occurrence；重复未解决 call_id 可共享 T，不能只靠 call_id/T | 源码与 6 项定向测试已核实，完整报文留实施 |
| run 回滚/重试后的残留工具事件 | 旧 C 与当前 session 不匹配时拒绝关联，不按 provider call_id/顺序拼到新 M | 真实 rollback+相同 provider call_id 负例已通过；完整回滚矩阵留实施 |
| SDK retry/redirect | A 是最终返回 function_call 的 attempt，不是失败/中间 hop | request tracking 测试已核实；完整组合留实施 |
| Responses retrieve | A 是返回 function_call 的 retrieve GET，不是 create POST | 静态链已核实，专项样本留实施 |
| 多 attempt 但 M/terminal 均缺 A-final | 跳过该条并记录原因，不取 attempts[-1]、不用 exchange 混填 | 缺失处理实现留实施 |
| slash skill | 输入触发，仅当前 pass；无 requestId/attempt；reminder 重放不重复计数 | 旧契约和当前来源已核实，归属/去重样本留实施 |

已执行 `test_request_tracking.py` 与 `test_trajectory_events_log.py`：43 passed、2 skipped。2026-11-16 补跑重复 provider ID、UI ID 非匹配键、call/result operation、call_item_id 和 tool/exchange 归属 6 个节点，`6 passed in 1.64s`。随后新增定制自包含实验 `aixcoding/tests/telemetry/test_tool_identity_persistence.py`，真实 engine/scripted HTTP 主链和真实 rollback 负例最终 `2 passed in 4.38s`，详见 `experiments/tool-identity.md`。这些结果锚定关联链，不证明完整异常矩阵、最终报文或 Responses retrieve 组合已专项验证。

## N5 扩展：广义调用覆盖矩阵

| 场景 | 大方向预期 | 证据状态 |
|---|---|---|
| 本地内置 tool/shell/MCP/load_skill | 普通工具链可覆盖主要旧字段；MCP 按 kind=1，shell 转后台不等于进程最终 exit；三个执行时间字段不出现在 final DTO | 当前执行 stamp、shell output/background 测试已核实；字段缺席断言留实施 |
| provider-hosted 工具 | hosted call/result + assistant E/A 可提供主要业务字段，不强套本地 T/C；三个执行时间字段全部去掉且不补采 | hosted tools + loop cycle close 99 passed；字段缺席断言留实施 |
| local sub-agent 外层/内部 | 外层普通工具；内部按 invocation/actor 使用 child 自身 E/A，独立 audit 辅助；三个执行时间字段全部去掉 | trace、transcript 测试已核实；字段缺席断言留实施 |
| 外部 ACP 外层/内部 | 外层普通工具；内部仅有界 update 投影，名称/类型/E/A 缺失时降级或补采；三个执行时间字段不再属于需求 | translator/persistence 测试已核实；保真级别待裁决 |
| slash/普通 command/selected Agent | slash 只有 pass；普通 command 无旧独立埋点；selected Agent 必须 ACP 捕获且 save-only | 旧 tool-detail 37 项通过；路径断言 1 项失败单独留痕 |

当前广义专项命令与完整结果见 `research/nodes/broad-tool-coverage.md`：首轮 216 passed、8 skipped，hosted 补测 99 passed。旧 `aixcoding/tests/test_tool_detail.py` 为 37 passed、1 failed；失败仅是 Windows 工作区外路径分隔符断言与实现及同文件规范化用例冲突，未修改或跳过。上述均不证明新 analyzer、真实 session 组合或 golden parity 已完成。

## N6 ai-code 重建矩阵

| 场景 | 大方向预期 | 证据状态 |
|---|---|---|
| create/overwrite/edit/replace_all | 逐次 before/after + 最终参数可重建旧 blocks；连续编辑不折叠 | 旧算法与当前 mutation 输入已核实 |
| mutation→T→E/A | 使用 PR #69 的 mutation.tool_operation_id=T；旧 tool_call_id 是独立 12hex UI ID，不是桥 | 当前源码与 PR 相关 4 项测试已通过；N5 关联链已核实 |
| manual/user 与 auto/judge | 成功有 blocks 时分别 5/1；decider 不足不能猜 5 | 当前审批事件来源已核实 |
| rejected/failed/interrupted/partial write | 即使 mutation 存在也不生成 ai-code | 当前 mutation 反例测试已核实 |
| hook 截断且 digest 不同 | 最终 edit 参数不可恢复，降级 | 判定规则已核实，组合样本留实施 |
| 缺 blob/skip/rollback | 不把缺失当空文件，不读当前磁盘或孤儿 blob 猜历史 | 当前策略与清理测试已核实 |

已执行当前 `test_history_approval.py`、`test_tool_operation_stamps.py`、`test_mutation_exits.py`、`test_pipeline.py`：113 passed。旧 `aixcoding/tests/test_ai_code.py` 在临时补齐 pytest-asyncio/pytest-timeout、清空默认 xdist addopts 后取得 22 passed、1 skipped，无代码断言失败。组合报文与 golden parity 留实施。

## N9 运行时上下文矩阵

| 场景 | 大方向预期 | 证据状态 |
|---|---|---|
| 版本/当前 auth | 当前运行时读取；委派无 EHR、未登录或历史用户省略 | 当前 auth 测试已核实 |
| 当前轮 workspace/profile | live/finalizer 可取；meta 辅助，不能用 session-latest 填历史 | 持久化与 recorder 测试已核实 |
| projectName | 可由当前 cwd 约定派生；无 workspace 不回退进程 cwd | 静态边界已核实 |
| desktop channel/functionName/selected Agent | 必须 ACP 入口按 session/turn 捕获；历史未捕获只能省略 | 当前丢弃行为已核实，真实输入样本待 N7 |
| Git 轮末/事件时 | finalizer 只能轮末；事件时精度需更早捕获，否则省略 | 静态边界已核实，语义/样本留实施 |
| CLI surface/channel | 启动形态可辅助，deployment/installer channel 不冒充 telemetry channel | 静态边界已核实 |

已执行 persistence、session_writer、trajectory_recorder、ACP server/session_manager 和 auth session/delegation 共 205 项并通过；不证明 desktop envelope 捕获或事件时 Git 已实现。

## D1 缺陷登记与分类验证

- 对 L-D01–L-D10 逐项复核旧最终源码，将客户端缺陷、协议/消费方限制、设计取舍和新版重建边界分开；登记册中的处理方向不等于已实施修复。
- 新增 L-D11：外部 ACP translator 的 interrupted Result 被旧分类器忽略并归成功。执行旧版纯函数探针 `classify_result_metadata({"interrupted": True})`，实际返回 `CodeStatus.SUCCESS`、`failureType=None`，退出 0。
- 纠正 shell 基线：0.28.0 无工具托管后台句柄，当前后台终态是新增边界，不是旧 parity 缺陷。
- 纠正 hosted 基线：旧 local sub-agent hosted Result 的 duration_ms 默认 0，不能作为真实 provider 耗时复制。
- 静态复核和探针不证明生产风险频率、服务器取消映射或新 analyzer 已验证；完整登记见 `research/defect-register.md`。

## 异常与降级路径

- 文件缺失、旧版本记录、损坏 JSON、压缩/回滚后 ID 缺失：按“未知”处理，不按顺序猜测。
- 无 workspace、Git 状态变化、审批修改参数、blob 缺失：分别验证是否只能降级，禁止以进程 cwd 或当前状态冒充历史事实。
- 取消、失败、拒绝、unknown/invalid/filtered 工具：先确定旧版是否有对应事件，再决定新版映射，避免新增旧版没有的数据。
- 实验失败或证据冲突：保留原始结果，将结论退回“待确认”，不得只记录支持推荐方案的证据。

## 手工验证步骤（若需）

每项实验的完整命令、环境前置和预期判别标准写入对应 `experiments/<topic>.md`；实际结果追加到 `verification.md`。Windows 本地测试遵循仓库既有大写盘符、清空 `PYTHONPATH`、引号形式设置 `PYTHONUTF8=1` 等环境约束，不把环境噪音当成功能结论。
