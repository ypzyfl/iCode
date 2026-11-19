# D1：0.28.0 缺陷、协议限制与新版重建边界登记册

> 基线：旧版为 0.28.0 最终留档，新版为 fork 0.35.2。本文登记的是**已证实行为、影响风险和处理方向**，不表示缺陷已在新版修复，也不授权任何产品代码改动。
>
> 证据路径缩写：`OLD/` = `D:/Coding/aixcoding/aixcoding-cli/aixcoding-cli__0.28.0_final/`，`NEW/` = `D:/Tech/Github/huawei/iCode/fork/iCode-fork/`。实际实施时必须在当时基线重新核对行号和行为。

## 1. 分类与状态口径

| 标记 | 含义 |
|---|---|
| **C** | 客户端可修复缺陷：现有或可增加的本端证据足以修正，不应为 bug-for-bug parity 复制 |
| **P** | 协议、后台、消费方或上游协作限制：仅改客户端无法定义完整正确语义 |
| **D** | 有意设计取舍或已确认硬边界：不能把所有数据损失都当成实现 bug |
| **R** | 新版 after_turn/文件重建边界：可能叠加旧投影限制，但不等于旧版同一缺陷 |

“修复建议，待确认”只表示技术上有建议路线；根据责任人 2026-11-16 明确的约束，旧版缺陷修复和与旧版不一致的变通均须由人确认后才成为实施决定。具体实施仍须进入独立批次并完成 design/R2 签认。“待外部确认”表示还需要后台、桌面消费方或外部 Agent 的输入，继续读客户端源码不能单独闭环。

## 2. 客户端可修复缺陷

| ID | 已证实的旧行为与影响风险 | 分类 | 新版处理方向 | 状态与证据 |
|---|---|---|---|---|
| **L-D01** | provider ID 为空或未命中 registry 时，`resolve_tool_call` 回退 session-latest；tool-detail 和 ai-code 均消费该结果。并发、跨 turn、child/ACP 场景可能错挂，但不能断言每次回退都错误 | C | 普通工具用精确 T/C/M/E/A；证据不足省略/unknown，不恢复 latest | 修复建议，待确认；`OLD/src/chrys/aixcoding/telemetry/llm_telemetry.py:125-138`，`reporters/tool_detail.py:147-171`，`reporters/ai_code.py:240-260` |
| **L-D02** | local sub-agent 普通内部工具 Start/Result 没传已取得的 provider_call_id，reporter 使用内部短 call_id 并触发 latest 回退。不能据此断言后台一定拒绝短 funcId | C | 按 invocation/actor 隔离，使用 child 自身 session call_id、T/C/M/E/A；普通本地工具 funcId=T 原值已由 B2/B3 确认角色 | 精确关联修复建议待确认，funcId 角色不再待定；`OLD/src/chrys/service/agent_middleware/events/sub_agent_events.py:565-566,647-659,898-912` |
| **L-D03** | 独立报文 common_fields 在无 workspace 时以 `Path.cwd()` 填 projectName/Git；可能把 CLI 启动目录冒充工程。cwd 偶尔恰好正确不改变该风险 | C | 无 workspace 省略项目/Git，不以进程 cwd 猜测；事件时 Git 精度另按 N9 处理 | 修复建议，待确认；`OLD/src/chrys/aixcoding/telemetry/reporters/__init__.py:65-108`，`reporters/ai_code.py:281-287` |
| **L-D06** | slash 在模型调用前以空 provider ID 查 latest，可能取得上一轮 span或首轮无 span。requestId 省略本身是 save-only 设计，不是缺陷 | C | 按 B4 使用当前真实 logical turn ID 转 UUID 作为 spanId；requestId 继续省略；pass/opening_item 仅用于执行证据和去重 | 关联修复建议待确认，恰好一次待样本；`OLD/src/chrys/aixcoding/telemetry/reporters/tool_detail.py:256-276`，`orchestration/engine/run/runner.py:581-593` |
| **L-D08** | desktop channel 和 functionName 都是进程级最近值，每次 ACP prompt 覆盖；多 session/client 存在串台风险，实际部署是否并发尚未证明 | C | ACP 入口按 session/turn 捕获，报文从该上下文取值；不读进程级最后写入者 | 修复建议待确认，真实输入契约随 N7 暂缓；`OLD/src/chrys/aixcoding/context.py:58-104`，`telemetry/acp_meta.py:47-58` |

## 3. 混合项：客户端缺陷与协议/设计限制必须拆开

### L-D04：主 Agent/local child 取消没有终态 Result

- **事实**：主 Agent 和 local sub-agent 的若干取消路径在 Start 后不发布 Result，旧 reporter 因而只发出 PENDING，不能据此证明服务器永久保存 PENDING。外部 ACP translator 有 interrupted 补发，不属于此路径，另见 L-D11。
- **分类**：**C + P**。本端可识别 cancelled/interrupted 并避免悬空，但旧 CodeStatus 只有 1/2/3/4/5；虽然存在 `FailureType.CANCELLED` 常量，旧分类器没有消费它，后台是否接受某种取消组合未确认。
- **处理方向**：登记取消终态并停止 PENDING 语义；不得一律伪报普通失败。具体使用扩展状态、既有失败+cancelled，还是保持协议差异，待后台确认。
- **证据**：`OLD/src/chrys/service/agent_middleware/events/tool_events.py:508-519,694-710`，`sub_agent_events.py:723-731,774-775`，`aixcoding/telemetry/types.py:28-44`，`telemetry/outcome.py:36-47`。

### L-D05：投递生命周期、业务响应与 fire-and-forget

- **事实**：无运行 loop 时 submit 丢弃；stop 取消 worker且不 drain；HTTP 只检查状态码，2xx body 不解析。旧 `src` 未找到生产 `wait_drained` 调用点。代码并未显式把业务响应“标记成功”，是否存在 2xx 业务拒绝也未证明。
- **分类**：**C + D**。loop 外静默丢弃、正常退出无 flush、业务拒绝不可见属于可靠性缺陷；不阻塞产品主流程和不做崩溃补报是已确认取舍。
- **处理方向**：明确 worker 生命周期、正常退出有界 flush、失败/业务码可观测和丢弃指标；保持 N8 有序 best-effort，不引入严格 ACK 门槛。
- **证据**：`OLD/src/chrys/aixcoding/http.py:48-112`。

### L-D07：ACP 最终响应只给 session-latest 单值

- **事实**：EndTurn 和 Cancelled 都调用 `telemetry_response_meta`，从 session-latest 取单个 requestId/spanId；final-model-identity 复用该 requestId。取消或跨轮可能取旧值。旧 telemetry envelope 没有 sessionId，requestId 在最终 PromptResponse 而非流式 update 返回。
- **分类**：**C**。turn 归属和取消取旧值是客户端缺陷；单值最终响应 envelope 已由责任人于 2026-11-17 确认为必须保持的消费形态，不再是是否足够的开放协议问题。
- **处理方向**：按 `(session_id,turn_id)` 取当前 turn 的目标成功主模型 A-final，在最终 PromptResponse._meta 主动合并 requestId；上游 session/turns 可作数据源，但仅让客户端另查不满足要求。禁止旧值回退，不新增逐模型调用流式通知。当前 AI 推荐在 prompt_lock 内从 live 主 history 精确选择，不建立 registry；最后成功响应缺 A 时不取更早值。
- **状态**：**输出契约与桌面 0.28 输入捕获均已确认，响应时内存选择继续暂行；2026-11-18 ID 原值裁决（取代此前 UUID 归一化安排）**。内部 selector 取 raw A，requestId 直接用原值（32hex 无转换）；后台原记录原值保存，request_tracking.py/ids.py 不改，Agent Studio schema 需放宽接受 32hex。after_turn/live registry 不得由 AI 擅自改道；Q2 已确认按 session/turn 捕获 selected Agent/desktop 输入并恢复 1001。
- **证据**：`OLD/src/chrys/aixcoding/telemetry/acp_meta.py:20-123`，`aixcoding/telemetry/llm_telemetry.py:80-304`，`app/acp/server.py:331-418`；上游 b4f354d/9cd8031d；当前累计 86 项定向测试通过。

### L-D09：manual 近似用户批准

- **事实**：请求已批准且请求时 mode=manual 就记 5，其余记 1；旧 ApprovalResponse 没有足够 resolver/actor provenance，tracker 也不使用请求中的 judging 信息区分最终回答者。
- **分类**：**C + P**。manual≈用户是客户端启发式；精确区分 user/judge 还依赖事件事实。不能断言所有 manual 都分类错误。
- **处理方向**：新版有明确 decider 时按事实生成 1/5；历史证据不足时 unknown/降级，不把 manual 自动当用户。
- **证据**：`OLD/src/chrys/aixcoding/telemetry/reporters/ai_code.py:161-194`，`foundation/events/types.py:227-233,674-695`；新版输入边界见 `nodes/ai-code.md`。

### L-D10：ai-code 全文回退与 buffer 丢旧

- **事实**：缺参数、定位失败或 replace_all 超过 64 块时可回退完整新文本；BatchBuffer 达 500 条静默丢最旧。全文回退不必然造成错误归因，buffer 实际溢出频率也未测量。
- **分类**：**D + C**。有效参数下的 64 块上限和全文表示是设计取舍；参数/快照不一致仍全文归因属于应限制的风险；静默溢出是可靠性缺陷。
- **处理方向**：参数/快照不一致或 blob 缺失时降级，不造 blocks；有效 replace_all 超 64 块可保留旧全文口径；buffer 增加丢弃指标/告警，容量是否调整留实施。
- **证据**：`OLD/src/chrys/aixcoding/telemetry/reporters/ai_code.py:116-158`，`aixcoding/http.py:115-145`。

### L-D11：外部 ACP interrupted Result 被归为成功

- **事实**：外部 ACP translator 在取消清理时补发 `metadata={"interrupted": True}` 的 Result；旧 `classify_result_metadata` 不读取该键，最终返回 `CodeStatus.SUCCESS`、`failureType=None`。这与 L-D04 的“没有 Result”是不同路径。
- **分类**：**C + P**。把 interrupted 默认归成功是客户端分类缺陷；正确取消报文仍受 L-D04 的后台协议限制。
- **处理方向**：新版必须先识别 interrupted/cancelled，再按已确认取消协议处理；不得归成功，也不得未经确认一律归普通失败。
- **证据**：`OLD/src/chrys/orchestration/invoker/acp_protocol.py:544-602`，`aixcoding/telemetry/outcome.py:36-47`，`foundation/tool_result_metadata.py:230-250`。
- **运行探针**：旧版 `classify_result_metadata({"interrupted": True})` 实际输出 `code_status=CodeStatus.SUCCESS`、`failure_type=None`，退出 0。

## 4. 广义专题新增项：不要误登记为同一种旧缺陷

| ID | 新旧事实 | 分类 | 处理方向与未证明事项 |
|---|---|---|---|
| **B-SHELL** | 0.28.0 shell 明确等待结果且“不提供异步任务句柄”；当前版本才有工具托管的后台 task metadata。用户用 shell 语法自行启动进程不属于该托管能力 | R + D | 当前工具 final 只表示“已转后台”，不是进程最终 exit。只复刻 0.28.0 不需要新增后台进程终态遥测；若新需求要求覆盖，应另行定义，不能复用旧 funcId 伪造第二次 final。证据：`OLD/src/chrys/service/tools/builtins/shell.py:355-364`，`NEW/src/chrys/service/tools/builtins/shell.py:126-162` |
| **B-HOSTED-TIME** | 旧 local sub-agent hosted 投影使用本地事件 timestamp，HostedToolResultOp 未传 duration_ms，事件默认 0；这些不是 provider 真实执行时间。该 duration=0 证据不能推广到所有 hosted 路径 | C + P + R | 已于 2026-11-17 裁决：新版所有工具记录去掉 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`，不复制旧默认 0，不补采本地或 provider 时间；本项不再是字段保真缺口。证据：`OLD/src/chrys/service/agent_middleware/events/sub_agent_events.py:334-356,400-415`，`foundation/events/types.py:473-490` |
| **B-ACP-PROJECTION/RING** | 旧版已经把外部 ACP title/kind/rawInput 投影为本地事件，并已有有界 translated_updates；当前仍按条数/字节裁剪。title 可能恰好等于真实名称，但不保证；ring 淘汰频率未测量 | P + D + R | 外部 ACP 内部明细已退出当前范围；本地投影不冒充远程真值，ring 淘汰数据不可恢复，不再把补采或外部协作列为本任务待办。三个执行时间字段全部去掉。证据：`OLD/src/chrys/orchestration/invoker/acp_protocol.py:296-356,512-588`，`orchestration/sub_agents/tools.py:978-984`；`NEW/src/chrys/service/session/sub_agent_logs.py:489-517` |

## 5. 明确不列为缺陷的行为

- slash skill 不带 requestId、selected Agent 只有 save：属于各自使用记录语义。
- selected Agent 的 funcId 为新 UUID：没有 update 匹配需求，不是旧随机 ID 恢复缺陷。
- N8 允许孤儿、网络失败不影响产品主流程：属于已确认 best-effort 取舍，但应有可观测性。
- 崩溃/强杀不做启动扫描补报：属于本任务明确非目标。
- 文件、blob、workspace 或历史 Git 无证据时 unknown/省略：属于防猜测边界，不应为追求字段齐全而复制旧回退。
- 外部 ACP 的父 trajectory `boundary_only` 和有界 audit：属于资源与边界设计；需要更高保真时应新增明确数据来源，而不是把设计本身称作实现 bug。

## 6. 仍需外部输入的决策清单

1. **后台取消协议**：cancelled/interrupted 应使用什么 codeStatus/failureType，或明确登记不支持；涵盖 L-D04、L-D11。
2. **funcId 身份键已关闭，对账在端侧**：普通本地工具 funcId=T 原值（2026-11-18 原值裁决）已由 B2/B3 确认角色；BR-8 providerCallId 已于 2026-11-19 撤销，模型 toolUseId 对账由客户端按 T 本地反查完成，不回退 funcId。
3. **外部 ACP/hosted 保真已收敛**：三个执行时间字段全部删除；外部 ACP 内部明细退出当前范围，仅保留本地投影非远程真值边界。
4. **N7 输入/输出实现**：最终 PromptResponse 主动携带当前 turn requestId、响应时 live-history 和桌面 0.28 输入捕获均已确认；方向 selector 7 项通过，剩余真实 server、1001、并发/取消/retry 和桌面 envelope 验证。
5. **实施期可靠性指标**：丢弃、ring 淘汰、flush 超时和业务拒绝的日志/指标阈值，不在探索阶段预设数值。

## 7. 证据强度与验证边界

- 本登记册逐项经过旧最终源码静态复核；L-D11 另有纯函数运行探针。没有声称已证明各风险在 production 的发生频率。
- 已继承旧 tool-detail `37 passed, 1 failed`（唯一失败为 Windows 路径分隔符断言冲突）、旧 ai-code `22 passed, 1 skipped`，以及当前广义专题 `216 passed, 8 skipped` + hosted `99 passed` 的行为锚定；这些结果不是缺陷修复验证。
- 本轮没有修改产品代码、没有新增 analyzer，也没有把“建议处理”标成“已修复”。真实故障组合、服务器协议接受度和最终 golden parity 留相应实施批次。
