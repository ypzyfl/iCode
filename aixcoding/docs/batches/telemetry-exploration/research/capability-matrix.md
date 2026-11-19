# Telemetry 能力矩阵

> 当前有效口径（2026-11-18 修订）：主路线为 A-final 原值（32hex，**不转 UUID**）+ after_turn 文件分析；tool/ai-code 关联 A1，最终 ACP 通常关联 A2；B7/B8 已委托 AI 制定暂行最小契约，三个工具执行时间字段全部删除。N3 完整身份采用 run-owned 四文件候选，N7 采用响应时 live-history 单 ACP server 接缝。五类记录目前只有测试态 DTO/关联证据，尚无生产保存和真实桌面闭环。总览见 `review-handoff.md`；“建议上游”不等于已决定向上游提交。

## 分类口径

- **纯文件**：仅分析 session 目录中的持久化数据即可实现。
- **fork 接缝**：当前上游机制足够，但 aixcoding-cli 组合层没有正式配置入口，需要最小上游接线。
- **建议上游**：存在符合通用 AI 工具定位的扩展能力，可消除 fork 接缝或降低内部 API 耦合。
- **只能降级**：所需事实未捕获，事后无法可靠恢复；只能运行时补采、建议上游新增通用记录，或接受差异。

| 能力 | 纯文件初查 | fork/运行时要求 | 可建议的上游通用能力 | 当前状态 |
|---|---|---|---|---|
| sessionId | 可精确取得 | 无 | 无需 | 已静态核实 |
| logical turn/spanId | TurnRecord/ActiveTurnTrace/run-owned 快照提供真实 logical turn ID | `spanId=真实 logical turn ID 原值`（不转 UUID）；retry 复用 logical、pass 新生成，不用 pass 代替 span，不恢复旧 uuid5(session:turn) | 通用 turn identity/层级上下文 | B4 已确认；fresh/retry 身份实验通过；parentSpanId 父 turn 语义与 0.28 父模型调用 span 不同（parity 差异项），当前无嵌套 turn 场景 |
| 成功模型 requestId | 正常成功 assistant message 的 `_chrys_request_attempt_id` 提供 raw A-final；exchange 保留作内部关联 | 内外均为 raw 32hex 原值，无转换层（2026-11-18 原值裁决）；缺 A 跳过 | 无需 request 生成器或 trajectory 校验改动 | **A-final+原值口径已裁决**，32hex 格式接受/混存/服务器/桌面闭环待验证 |
| HTTP attempt 关联 | trajectory 已开启且事件记录完整时，可获取全部已持久化 attempts；session message 只保留最终 attempt | 当前主键只取最终成功 A，不恢复全部 attempts；失败/pending/部分流不上报，trajectory 缺失不得猜测 | 无需改变 attempt 的 per-HTTP 语义 | 核心语义已核实，组合样本待验证 |
| 动态 LLM body telemetry | 事后文件无法修改已发请求 | 请求前 ChatMiddleware 必须存在 | 通用 ChatMiddleware 注册和稳定上下文 | 已静态核实必要接缝；当前 A-final+独立报告路线不需要 |
| 独立 LLM 报告 | after_turn 从成功 assistant/exchange 重建，requestId 出站即为 A-final 原值 | 新增独立 endpoint 与最小 envelope；A1/A2 各自记录，requestId 单键幂等 | 无 | B7 委托 AI 暂行；生产/现网未实现 |
| 工具身份与 funcId | session 保存 provider call_id、call item ID 和 tool operation ID；优先以 call_item_id 定位 occurrence，T/E 交叉校验 | 普通本地工具 `funcId=T 原值`（32hex，不转 UUID）；BR-8 providerCallId 已撤销（2026-11-19），对账由客户端按 T 本地反查；同 T 至多一次 final save | 可选结构化 tool invocation audit | N5 关联链已核实；B2/B3 已确认 funcId 身份（格式按 BR-5 确认） |
| 工具生产 attempt | call_item→function_call→assistant message，或成功 exchange terminal | 多 attempt 且直接字段缺失时 unknown，不取 attempts[-1] | 无需 tool event 新增字段 | N5 关联链各段已行为锚定，完整组合留实施 |
| turn parentSpanId | 仅在真实父子对话关系中取直接父 turn ID；普通独立 turn 无父级 | 本轮模型和工具共用当前 turn ID 作为 spanId；独立 turn 不传 parentSpanId，不从 exchange/A-final/T 或时间上一轮派生 | 通用 turn hierarchy context | B4 概念语义已确认；真实嵌套 turn 的父 ID 持久化留对应场景验证 |
| 内部工具 12 位 fallback ID | 多数不持久化；可由 tool_operation_id 派生新稳定 fallback | 不得称为恢复旧随机原值 | tool invocation audit | N5 已明确替代与协议边界 |
| 工具原始参数 | session function_call 保存，trajectory 只存指纹 | 注意压缩/spill | 可选安全审计投影 | N4/N5 来源已核实，报文映射留实施 |
| 审批/hook 改写后的最终参数 | 审批 modified_args 写回；其他 hook 通常有 `_exec_stamp.effective_args`，但 2048 字符截断 | 截断或缺失时降级，不拿原始参数冒充最终值 | 可选最终执行参数审计，需隐私控制 | N4/N5 输入边界已核实，组合样本留实施 |
| 工具状态 | tool operation events + result/stamp 可重建主要状态 | interrupted 无已验证旧终态；不伪报普通失败；`executionStartedAt`、`executionFinishedAt`、`executionDurationMs` 全部去掉，不补采 | 无 | N5 主状态覆盖可行，取消协议待确认；B5/P2 已关闭 |
| slash skill、load_skill | load_skill 可关联 E/A；slash 只有 pass，无 E/A；reminder/tool context 提供证据 | slash 归属不足时局部输入补采；不用 session-latest，不因 reminder 重放重复计数 | 无 | N5 大方向可行，slash 去重组合留实施 |
| shell/command 与本地 MCP | shell 沿用普通工具链；MCP 按 kind=1，tool_context 可含 server/remote 名 | 转后台 final 不等于进程最终 exit；完整原始输出和缺失 kind 不猜 | 可选通用执行审计 | 广义调用专题已核实，当前相关测试通过 |
| provider-hosted 工具 | session hosted call/result + assistant E/A + hosted.call.observed 可恢复主要业务字段 | 不强套本地 T/C；三个执行时间字段全部去掉，不补采本地或 provider 时间 | 无需 hosted 时间捕获 | 字段级条件可行，99 项相关测试通过；B5/P2 已关闭 |
| local sub-agent 外层/内部 | 外层走父普通工具链；内部按 child actor 的自身 T/C/M/E/A，child audit 辅助 | 必须按 invocation/actor 隔离；不得挂父 E0/A0 或恢复 session-latest | 通用 child audit 关联文档 | 条件可行，trace/transcript 测试通过 |
| 外部 ACP 内部工具 | 有界 translated_updates 只能重建部分本地 tool card 投影，不等于远程内部审计 | 当前范围不要求恢复精确远程名称/MCP 类型/内部 E/A；三个执行时间字段全部删除 | 当前不提出专属上游需求 | **已退出当前范围**，保留保真边界，不再列为待补方向 |
| 普通 slash command/直接终端命令 | 旧 tool-detail 无独立通用记录 | 不新增旧版没有的数据；模型 shell 调用才按 shell 处理 | 无 | 旧基线已核实 |
| ai-code blocks/ID/状态 | 成功 write/edit 可由逐次 before/after + 最终参数重建 blocks；mutation→T→E/A 提供关联，审批事件提供 1/5 | `requestId=A1 原值`、`reportId=T 原值`；同 T 多 mutation 跳过，失败/拒绝/取消不报；参数 digest 不同或所需 blob 缺失时降级 | 通用 mutation/audit 稳定性文档 | B8 暂行契约；M0 测试态 DTO 通过，生产报文/幂等/golden parity 留实施 |
| ACP desktop envelope/selected Agent | 当前入口丢弃后文件不可恢复 | 必须 ACP 边界按 session/turn 捕获；历史未捕获省略 | 通用扩展 metadata 已足够，未必需新上游能力 | N9 已核实，真实输入形态待 N7 |
| ACP 最终 request/session/turn 身份 | 上游 b4f354d 已提供 session/turn 身份及 requestAttemptId 查询；live 主 history + TurnRecord 可按 logical turn 选择 raw A-final | **最终 PromptResponse._meta 主动携带 requestId 已确认**；暂行在 prompt_lock 内选择 raw A，requestId 直接用原值（2026-11-18 原值裁决，无转换）；仅 server+定制 helper，无需 request_tracking/ids 改动 | 复用上游通用身份，不建议上游加入内部专属 envelope | 输出契约已确认，方向 selector 7 项通过；真实 server、格式接受、design/R2 与桌面闭环（schema 放宽）待验证 |
| ACP 流式内容与身份 | 上游 9cd8031d 已提供标准文本/推理 chunk，b4f354d 为 update 附 turn 身份 | 无需新增逐模型调用流式通知；requestAttemptId 不直接随 chunk 发送 | 复用现有标准 ACP 通道 | v0.30.1/v0.31.0 已引入，当前 0.35.2 测试通过 |
| channel/workspace/profile/userId | 固定运行时/live session 可覆盖当前轮；meta 仅最近快照 | 无 workspace 不回退 cwd；历史用户/workspace 不猜；desktop channel 走 ACP | 通用运行时上下文接口可评估 | N9 大方向可行，205 项相关行为通过 |
| Git 字段 | 无事件时持久化；finalizer 只能轮末快照 | 要求 turn/tool 时精度则提前捕获，否则省略 | 通用环境快照接口可按语义评估 | N9 边界明确，精度选择留实施 |
| 进程内 after_turn 分析 | 正常路径在 save 尝试/checkpoint 后通知；save=False 不得读旧文件冒充本轮 | 当前推荐 run-owned 快照 + direct finalizer + 集中 per-session lifecycle drain，最小四文件 R2；EventBus 仅在多消费者时再评 | 通用内部生命周期事件和有界 session/process flush | 现有行为与最小接缝已静态核实；生产 dispatcher/flush 尚未实现 |
| 崩溃/强杀补报 | 未发生 hook 且未落盘数据不可恢复 | 本任务明确不做 | 不提出建议 | 非目标 |

## 证据锚点

当前组合证据：五类记录 `a-final-e2e-closure.md`（M0 16 passed）；身份矩阵同文档（M1-I 31 passed）；文件重建 `session-reconstruction.md`（48 passed）；性能/队列 `performance-and-lifecycle.md`（52 passed）。这些组合存在重叠且不含真实生产保存/桌面闭环。

- sessionId：`src/chrys/service/state/store.py:781-795`（session meta 持久化完整 ID）。
- logical turn/spanId：旧副本 `src/chrys/aixcoding/telemetry/llm_telemetry.py:46-47,88-90,187-193` 仅作旧 uuid5 历史对照；当前 B4 口径为真实 logical turn ID 原值（2026-11-18 原值裁决），身份来源见 `src/chrys/orchestration/engine/trajectory.py:222-269`（每 pass 独立 turn_id，retry 保持 logical_turn_id）。
- 逻辑 requestId、HTTP attempt：`request-identity.md` 及其源码、测试、Git 提交证据。
- 整个 session 目录、工具 parent exchange、mutation/blob：`nodes/session-data.md`（N4 源码调查和 179 项现有行为测试）。
- 工具生产 attempt、协议字段和技能关联：`nodes/tools-and-skills.md`（N5 源码调查和 43 passed、2 skipped）。
- 广义 tool/shell/MCP/hosted/sub-agent/ACP：`nodes/broad-tool-coverage.md`（当前 216 passed、8 skipped + 99 passed；旧 tool-detail 37 passed、1 个 Windows 路径断言失败）。
- ai-code blocks、outcome、最终参数和 blob 降级：`nodes/ai-code.md`（N6 源码调查和 113 项现有行为测试；旧 ai-code 22 passed、1 skipped）。
- 公共字段、workspace/profile、auth、ACP 和 Git 边界：`nodes/runtime-context.md`（N9 源码调查和 205 项现有行为测试）。
- 动态 LLM body telemetry：旧副本 `src/chrys/aixcoding/telemetry/llm_telemetry.py:183-214,240-284`（请求前注入）；当前 `src/chrys/service/llm/clients.py:603-644`（统一组栈无注册参数）及 `src/chrys/service/llm/chat_completions/request.py:47-92`（extra_body 透传）。
- 内部工具 fallback ID：旧副本 `src/chrys/aixcoding/telemetry/reporters/tool_detail.py:147-196`（provider ID 缺失时回退内部 ID）；当前 `src/chrys/service/agent_middleware/events/result_persistence.py:43-79`（结果 metadata 持久化白名单）。
- 审批/hook 改写后的最终参数：`src/chrys/service/session/history.py:1575-1587`（审批 modified_args 写回 function_call）；`src/chrys/foundation/trajectory/tools.py:22-32,48-70`（参数指纹）及 `src/chrys/service/agent_middleware/control/approval.py:656-700`（参数改写链）。
- ACP desktop envelope：`src/chrys/app/acp/server.py:558-566`（当前丢弃 kwargs）；旧副本 `src/chrys/aixcoding/telemetry/acp_meta.py:21-97`（旧输入 envelope 解析）。
- 进程内 after_turn：`src/chrys/orchestration/engine/run/finalizer.py:372-392`（保存/checkpoint 后触发）；`src/chrys/service/hooks/runner.py:169-240`（用户 hook 外部子进程）。

## 使用规则

1. 每行结论必须有证据：专题已建立时链接专题；专题未建立时可暂用上述源码、测试或 Git 提交锚点；无证据行必须标为“待专题”，不得写“已静态核实”。静态初查不得改写成“运行已验证”。
2. “纯文件”区分只读 `session.json + events.jsonl` 与读取整个 session 目录；ai-code 需要后者。
3. “必须修改上游”只表示当前 fork 的最小接线，不代表应要求 iCode 增加内部专属功能。
4. 上游建议必须另过 `upstream-proposals.md` 的通用性审查。
5. 文件缺失时按未知处理，不按消息顺序、当前 cwd、当前 Git HEAD 或 session-latest 猜测。
