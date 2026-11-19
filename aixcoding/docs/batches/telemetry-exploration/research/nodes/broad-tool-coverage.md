# N5 扩展：广义工具、技能、命令与智能体调用覆盖

> 技术判断：**不能用一条“所有工具都可按普通 function_call 重建”的结论覆盖全部类别。**本地内置工具、shell、MCP、`load_skill` 以及 local sub-agent 内部工具具备较完整的持久化关联链；slash skill 和 selected Agent 是 save-only 使用记录；provider-hosted 工具与外部 ACP 内部工具只能按各自证据模型重建，其中后者存在明确的字段级保真回退。
>
> 对照基线：0.28.0 最终实现与当前 0.35.2。当前专项测试 216 passed、8 skipped，provider-hosted 补测 99 passed；旧 tool-detail 37 passed、1 failed，唯一失败为 Windows 路径分隔符断言冲突，详见本文第 7 节。未修改产品代码。

## 1. 先区分四种不同事实

1. **本地真实工具执行**：通常有 `save → tool.operation.started(PENDING) → finished`，可由 `T/C → function_call → assistant M → E/A` 关联。
2. **使用记录**：slash skill、load_skill 的额外技能记录、selected Agent 不是同一次本地工具执行的 save/update 链。
3. **委派边界与委派内部**：父 Agent 调用 local/ACP sub-agent 是一个普通外层工具；子 Agent 内部又可能产生自己的模型和工具调用，不能全部挂到父 exchange。
4. **远程/供应商投影**：provider-hosted 内容和外部 ACP `session/update` 是上游执行结果的本地投影，不等价于本地 tool operation，更不等价于远程进程完整内部审计。

因此，“广义调用可覆盖”必须逐类说明字段和关联，不表示所有类别都有相同的 requestId、funcId、funcType、起止时间或终态。

## 2. 逐类覆盖矩阵

| 类别 | 0.28.0 实际上报 | 0.35.2 持久化重建方向 | 当前判断与边界 |
|---|---|---|---|
| 本地内置 tool | `funcType=3`，save + PENDING + final update | 普通 `T/C/M/E/A` 链；参数、结果元数据和状态见 N5，三个执行时间字段全部去掉 | **基本可行**；最终 hook 参数截断、缺失和 cancelled 按既有规则降级，不补采时间 |
| 模型调用的 shell/command | 与普通内置工具相同，`funcType=3`；full 模式可在 value 携带命令等参数；超时可映射 failureType=timeout | shell 仍是普通本地工具，沿用同一关联链；结果元数据包含 exit/timeout/background 等事实 | **旧 tool-detail 所需字段基本可行**；成功 tool-detail 本就不上报完整 stdout/stderr，不能新增“完整原始输出可恢复”的承诺 |
| shell 转后台 | 0.28.0 shell 明确不提供异步任务句柄；旧 reporter 也没有托管后台进程终态上报 | 当前工具 Result 表示“已转后台”并带 task metadata；后台日志记录后续进程输出 | **新版新增边界**；final 不伪称进程最终 exit，后续日志不自动生成第二次模型工具调用。只复刻旧版时无需新增进程终态遥测 |
| 本地 MCP | 按 `tool_kind=KIND_MCP` 判 `funcType=1`，不是按工具名猜测 | tool operation 保留 kind；tool_context 可含 server_name/remote_name；主 Agent 与 local child 都有执行 stamp | **基本可行**；kind/context 缺失时 unknown/降级，不按 `mcp__` 等名称推断 |
| provider-hosted 工具（含 hosted MCP/shell/search） | HostedPresentationBridge 也翻译为 `InvocationToolCallStart/Result` 并进入旧 reporter；hosted MCP 可由 family 映射为 1。旧 local sub-agent hosted Result 的 duration_ms 默认 0，时间只是本地展示事件时间 | session 保存 hosted call/result、provider ID、family、参数和状态；assistant M 可提供 E/A，trajectory 另有 `hosted.call.observed` | **字段级条件可行**；不能强套本地 tool operation 的 T/C 链；三个执行时间字段全部去掉，不复制旧默认 0，不补采本地或 provider 时间 |
| 其他技能工具 | 如 `run_skill_script` 按普通 `funcType=3` 工具上报，不额外生成 funcType=0 | 若属于本地真实工具，沿用普通链 | **基本可行**；不能把所有 skill 相关工具都当成 save-only 技能使用 |
| `load_skill` | 一条 funcType=3 工具 save/update + 一条 funcType=0 技能使用 save | 普通工具链 + tool_context/技能名 | **基本可行**；额外技能记录不带 funcId，不与工具维度共用 update 主键 |
| slash skill | 输入命中后一条 funcType=0 save，无 update、无 funcId；requestId 省略，只关联当前 logical turn span | 原始输入、resolved reminder、opening item 可提供证据，必要时局部输入补采 logical/pass 身份 | **部分可行**；reminder 重放、mid-turn/retry/compaction 的唯一归属和去重仍未闭环 |
| 普通 slash command、用户直接终端命令 | 旧 tool-detail 没有独立 command 类别或通用 slash 埋点 | 不因为名称含 command 就虚构工具执行记录 | **不新增旧版没有的数据**；若命令实际由模型 shell 工具执行，则按 shell 行处理 |
| selected Agent（桌面选择） | 独立 funcType=1001 save-only；agentMarketSkillId 是准入门，agentName 是 funcName，functionName/runner 写入 agentName | 必须 ACP 入口按 session/turn 捕获选择输入与使用去重上下文 | **必须运行时补采**；不是 sub-agent 工具调用，也没有工具 final update |
| local sub-agent 外层委派 | 对父 Agent 而言是普通 funcType=3 工具 | 父 session 的外层 function_call/tool operation 提供完整 T/C/M/E/A | **基本可行**；与 selected Agent 1001 严格区分 |
| local sub-agent 内部工具 | 旧版经 SubAgentEventMiddleware 实时上报；provider ID 缺失时可能回退 session-latest | 子事件以 child actor 内联进父 trajectory，独立 child audit 保存子 messages；按 child 自身 T/C/M/E/A 重建 | **条件可行且可修正旧错关联**；必须按 invocation/actor 隔离，不能挂到父 Agent 的 E0/A0 |
| 外部 ACP sub-agent 外层委派 | 对父 Agent 而言仍是普通 funcType=3 工具 | 与 local 外层相同 | **基本可行**；外层 requestId 是父 Agent 产生该委派 function_call 的 A-final |
| 外部 ACP 内部工具 | 本地 AcpUpdateTranslator 将 ToolCallStart/Progress 翻译成 InvocationToolCallStart/Result，旧 reporter 因而也上报 | 父 trajectory 是 `boundary_only`；独立 ACP audit 只保留有界 `translated_updates`，可重放部分 tool card 投影 | **当前退出范围**；本地投影不冒充远程内部真值，不再把补采/外部协作列为本任务待办 |

## 3. local sub-agent：使用 child 自己的关联链

当前 local child 使用 `TraceCoverage.FULL`：

```text
父外层 tool operation T0
  → sub_agent.started/finished（invocation_id、actor_id、parent_tool_operation_id=T0）
  → child actor 下的 model.exchange / tool.operation（各自 E1/T1/C1/M1/A1）
  → sub_agents/sessions/<child>.json（独立 child transcript/audit）
```

处理规则：

- 先由 invocation_id、actor_id 和 parent_tool_operation_id 确定边界，再只读该 child actor 的事件；并行 child 之间不得按消息先后猜测。
- 内部工具 requestId 应来自**产生该内部 function_call 的 child M1 的 A-final**，不是父 Agent 的 A0；child E1 用于内部关联和成功 terminal 补证，不与 A-final 混填。
- child audit 可提供 function_call/function_result 和 assistant additional_properties 的独立对照；trajectory 缺失时只能恢复其中有证据的字段，工具单调耗时等缺口仍 unknown。
- 旧版 provider ID 未命中后的 session-latest 是已登记的错关联风险，新版不应为了报文相似继续复制。

## 4. 外部 ACP 内部工具：旧版也不是完整远程审计

### 4.1 旧版真正上报的是什么

0.28.0 的链路是：

```text
远程 ACP session/update
  → 本地 AcpUpdateTranslator 合并 ToolCallStart/Progress
  → 本地 InvocationToolCallStart/Result
  → 旧 ToolDetailReporter
```

所以旧版确实会产生外部 ACP 内部工具的 tool-detail，但它上报的是**本地翻译后的展示投影**，不是远程 Agent 的内部 session/trajectory。当前 0.35.2 仍保留翻译事件和有界 audit update；变化在于新方案要 after_turn 读文件，不能直接把旧实时 EventBus 字段视为已持久化。

旧关联也不总是精确：普通 ACP tool update 通常没有本地模型 registry 所需的 provider_call_id，`resolve_tool_call` 会回退 session-latest。该 requestId 可能属于父 session 最近调用，而不是远程内部真正产生工具的模型调用，不能作为新版必须复制的正确语义。

### 4.2 文件可恢复与不可恢复字段

| 字段 | 有界 `translated_updates` 能提供什么 | 降级/补采边界 |
|---|---|---|
| 远程调用标识 | toolCallId、attempt、update 顺序；重复 ID 时本地翻译器另有 occurrence 规则 | 可派生新的稳定 funcId；不能声称恢复旧内部 call_id。若 ring 丢失前序，occurrence 也可能不可精确重建 |
| funcName | title 和 rawInput | title 是展示标题，不保证真实工具名；需要远程 metadata 才能获得可靠名称 |
| funcType | ACP presentation kind 的本地映射 | MCP 经 ACP `other` 后通常变空 kind；不能按 title 猜 MCP=1。旧投影本身就存在此信息损失 |
| 参数/输出 | rawInput/rawOutput/content/locations 的有界投影 | 可能被限长、截断或从 ring 淘汰；成功 tool-detail 旧契约不需要完整结果正文 |
| 状态 | completed/failed 以及未终态记录 | 旧分类器会把 interrupted 误归成功（D1 L-D11）；新版先识别取消，再按届时经确认的协议处理，不归成功也不一律普通失败 |
| requestId/spanId | 没有远程内部 model exchange 证据 | 不能套父外层 E0/A0，也不能恢复旧 session-latest 猜测；省略或另定义明确的外层关联字段 |
| executionStartedAt/FinishedAt/Duration（已移除） | 三个准确字段名为 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs` | 新版所有工具记录全部去掉，不发送 null/0，不在本地 translator 补采，也不要求外部 Agent 提供 |
| 完整性 | 有界 ring 中仍存在的 updates | ring 淘汰意味着缺失可检测但不可补回；不能用最终 tool card 反推所有历史 update |

### 4.3 三档处理路线

1. **接受降级**：after_turn 只上报仍存在的投影字段，requestId、精确名称和 MCP 类型缺失时省略/unknown。这不需要外部 Agent 配合，但不是旧实时报文逐字段等价。
2. **本地 translator 轻量补采**：在本地 InvocationToolCallStart/Result 发布点记录本地 occurrence/call ID，after_turn 再组报文；不再记录时间或耗时。仍不能获得远程真实内部 exchange、工具名或 MCP 类型。
3. **外部 Agent 协作**：通过通用 metadata/审计接口提供真实工具名、kind、内部 requestId，或由外部 Agent 自行上报；不再请求执行时间。只有这一路线能覆盖远程内部真值；不能假设服务器能凭现有 toolCallId 推出这些事实。

2026-11-17 责任人已明确当前无需关注外部 ACP 内部工具如何上报，故第 2/3 档保真不再是本任务开放决策；只保留第 1 档的“投影非真值”边界。它不是普通内置工具主链的阻断项；三个执行时间字段已确定全部去掉。

## 5. shell、后台和 ai-code 的边界

- shell 的 command 参数、执行状态和 timeout 可服务旧 tool-detail；完整原始 stdout/stderr 受 capture/spill 限制，且旧成功 update 不上报结果正文。
- **0.28.0 没有工具托管的后台任务能力**；当前转后台 metadata 属于新版新增事实。转后台是本次工具的结果，后续进程结束不是新的模型 function_call。若新需求要求“后台进程最终退出”遥测，应单独立项，不能复用旧 funcId 再伪造一次工具 final。
- shell 隐式写文件不进入旧 ai-code reporter；不要因广义调用覆盖而扩大 N6 的 write_file/edit_file 范围。
- local sub-agent 内启动的后台命令在 child 结束时有停止/清理语义，不能把父轮末仍在运行的假设套到所有 child。

## 6. 后续实施/联调事项

1. **外部 ACP 内部工具已退出当前范围**：不再询问保真级别，只保留投影非远程真值边界。
2. **funcId 身份已关闭**：普通本地工具 funcId=T 原值（2026-11-18 原值裁决，32hex 不转 UUID）；剩余是 final-save 和 `(requestId,funcId)` 原子幂等的实现/联调。
3. **slash 去重和 cancelled 协议**：沿用 N5 已登记事项，不因本轮矩阵扩展而视为已解决。

provider-hosted 时间字段已退出待确认清单：责任人于 2026-11-17 明确三个执行时间字段全部去掉，不补采本地或 provider 时间。

上述项的缺陷/协议/设计分类见 [D1 缺陷登记册](../defect-register.md)。

除上述字段级事项外，本地内置 tool、shell、MCP、load_skill 和 local sub-agent 的主要路线没有发现新的方向性阻断。

## 7. 行为锚定与未证明事项

当前版本执行：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/service/agent_middleware/test_tool_operation_stamps.py tests/service/tools/test_shell_output_capture.py tests/service/tools/test_shell_background.py tests/orchestration/sub_agents/test_acp_translator.py tests/orchestration/sub_agents/test_acp_persistence.py tests/service/session/test_sub_agent_transcript.py tests/service/trajectory/test_traces.py -n0
```

结果：收集 224 项，`216 passed, 8 skipped in 35.58s`，退出 0。覆盖主/子 Agent 执行 stamp、MCP/skill context、shell 输出与后台、ACP 翻译和有界持久化、child transcript、sub-agent trace；skip 为测试自身平台或条件跳过。

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/service/agent_middleware/test_hosted_tools.py tests/kernel/test_loop_cycle_close.py -n0
```

结果：收集 99 项，`99 passed in 1.32s`，退出 0。锚定 provider-hosted 与本地 function_call 的区分及 hosted observation，不证明 hosted 报文重建器已实现。

旧版执行：

```cmd
cd /d "D:\Coding\aixcoding\aixcoding-cli\aixcoding-cli__0.28.0_final" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run --with pytest-asyncio --with pytest-timeout pytest -o addopts="" aixcoding/tests/test_tool_detail.py
```

结果：收集 38 项，`37 passed, 1 failed in 21.06s`，退出 1。唯一失败 `test_relative_file_name` 在 Windows 上期待工作区外路径保留反斜杠，但实现及同文件 `test_relative_file_name_normalizes_windows_paths` 明确统一为 `/`；旧工作区干净，未修改代码或跳过该用例。其余 37 项覆盖 funcType、shell 参数、load_skill、slash 和 selected Agent 等旧契约。本失败不用于否定这些已通过的分类结论，也不记为全套通过。

以上都是现有行为锚定，不是新 after_turn analyzer 的端到端测试。真实 session 组合样本、ring 淘汰后的降级、provider-hosted/外部 ACP golden parity 和最终报文幂等仍留实施。

## 8. 关键源码证据

- 旧 `telemetry/reporters/tool_detail.py:71-82,147-301`：funcType、普通工具、shell 参数、load_skill、slash、selected Agent。
- 旧 `orchestration/invoker/acp_protocol.py:512-588`：ACP update 翻译为本地工具事件及实时耗时。
- 旧 `telemetry/llm_telemetry.py:125-138`：provider ID 未命中后的 session-latest 回退。
- 当前 `service/trajectory/sub_agents.py:3-12,72-127`：local FULL 与外部 ACP boundary_only、child actor 和外层关联。
- 当前 `orchestration/sub_agents/tools.py:942-963,1461-1517,1560-1582,1722-1725`：外部 ACP 有界 audit、local child trace/audit 与事件 middleware。
- 当前 `orchestration/invoker/acp_protocol.py:107-117,414-480,499-678`：ACP kind 映射、audit 无逐项时间、toolCallId occurrence 和实时事件字段。
- 当前 `service/session/sub_agent_logs.py:193-295,489-517`：kernel/ACP 两类 audit 及 translated_updates ring。
- 当前 `service/agent_middleware/events/hosted_tools.py` 与 `foundation/trajectory/event_types.py`：provider-hosted 投影与 `hosted.call.observed`。
- 当前 `service/tools/builtins/shell.py:126-162` 及 shell 测试：后台 task metadata、成功标记和有界输出。

## 9. 外部 ACP 与 hosted 保真复核（2026-11-16）

### 外部 ACP：旧版也是本地投影，不是远程内部真值

旧链为 ACP update→本地 translator→InvocationToolCallStart/Result→tool-detail。funcName 是展示 title，普通投影 funcType 通常为 3，requestId/spanId 可能由 session-latest 错挂父调用；interrupted 还会被旧分类器误报成功。旧 translator 在终态 ensure-start 可重复 save/PENDING，当前 translator 已改为相同 signature 一次 Start，不能默认逐报文 parity。

当前纯文件可恢复 ring 中幸存的 toolCallId、attempt、occurrence、title/kind/rawInput/status，但没有每个内部工具的远程 E/A-final、真实名称/MCP 类型或精确时间。ACP transport attempt 和 successful_attempt 都不是模型 A-final。

因此按当前“缺 A-final 跳过且不混填”原则，新版只上报能关联父 M/A-final 的外层委派工具，外部 ACP 内部工具保持跳过/降级边界。责任人已于 2026-11-17 明确当前无需继续关注其内部上报细节，故本地 translator 补采、projection 特例或外部 Agent 协作均不再作为本任务待办；恢复旧 session-latest 永远不属于候选。

### provider-hosted：文件可恢复业务字段，执行时间字段全部去掉

当前 hosted call/result 可提供 provider ID、名称、family、最终规范化参数和正常成功/失败状态；所在 assistant M 提供各自 E/A-final，hosted.call.observed 只作辅助，不存在本地普通 T/C 工具执行链。主 Agent 和 local child 分别使用各自 M，不能互挂。

旧主 Agent/local child hosted Result 都未传 duration_ms，旧报文默认 0；Start/FinishedAt 是本地展示桥事件时间，不是 provider 真实执行时间。当前 hosted.call.observed 时间和 response-level timing 也不能冒充工具时间。

**责任人已于 2026-11-17 明确三个执行时间字段全部去掉。**hosted 采用文件重建业务字段 + A-final + 最终参数，不复制 0，不补采 Start/Result 时间、monotonic 或 provider 真实时间；B5/P2 已关闭，剩余 cancelled 协议仍需确认。spanId/parentSpanId 按 B4 的 turn 语义处理：使用当前 turn ID，仅真实父 turn 存在时填写其父 ID，不从 hosted provider ID、E/A 或本地工具 T 派生。
