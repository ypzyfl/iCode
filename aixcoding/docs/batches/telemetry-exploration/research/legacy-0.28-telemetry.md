# 0.28.0 Telemetry 直改源码方案参考

> 状态：旧版最终代码与旧文档的静态对照基线，供新版问题分析使用；不是新版实施方案。
>
> 基线路径：`D:\Coding\aixcoding\aixcoding-cli\aixcoding-cli__0.28.0_final`。这是责任人本机留档位置，其他环境须定位同一 0.28.0 终态副本并重核行号。本文中的“旧副本”均指该目录。

## 1. 范围与总体架构

旧版目标是让服务器将模型请求、工具调用、技能使用、AI 代码和桌面 Agent 使用关联到 session、turn 和逻辑模型调用。上报在事件发生时近实时执行，但 HTTP 发送通过进程内串行队列异步完成。

```text
                    ┌─ LLM ChatMiddleware
                    │   └─ 模型请求 body 顶层 telemetry
                    │
工具/skill/mutation ─┤
                    │   ┌─ tool-detail save/update
EventBus subscriber ┼───┼─ skill funcType=0
                    │   ├─ selected Agent funcType=1001
                    │   └─ ai-code save
                    │
ACP prompt boundary ─┘
  ├─ 读取 desktop _meta/channel/selected-agent/attribution
  └─ PromptResponse 返回 requestId/spanId/final-model-identity
```

主要定制产品代码位于旧副本 `src/chrys/aixcoding/`：

| 模块 | 职责 |
|---|---|
| `config.py` | 配置读取与合法性检查 |
| `context.py` | channel、function name、userId、插件版本 |
| `git_info.py` | 项目 Git 五件套及缓存 |
| `http.py` | 单 worker 串行队列、统一 POST、批量缓冲 |
| `telemetry/llm_telemetry.py` | LLM 搭车、ID 生成、per-call registry |
| `telemetry/subscriber.py` | EventBus 订阅和事件分发 |
| `telemetry/reporters/tool_detail.py` | 工具、技能、selected Agent 上报 |
| `telemetry/reporters/ai_code.py` | AI 代码 blocks、审批状态和缓冲 |
| `telemetry/acp_meta.py` | ACP 输入/输出 envelope |

## 2. 配置

| 配置项 | 语义 |
|---|---|
| `AIXCODING_EXTENSION_PROFILE` | `ONLINE/OFFLINE/LOCAL`，默认 `ONLINE`；非法值禁用并告警 |
| `AIXCODING_EXTENSION_BASE_URL` | 独立 CSAS 服务地址，覆盖 profile |
| `AIXCODING_EXTENSION_TOKEN` | 独立上报 bearer token，优先级高于登录 token |
| `AIXCODING_EXTENSION_TELEMETRY` | 总开关，默认 `true`，`false` 完全禁用 |
| `AIXCODING_EXTENSION_TOOL_DETAIL_MODE` | `full/whitelist`，默认 `full` |
| `AIXCODING_AUTH_SERVER_URL` | 登录服务器地址 |
| `AIXCODING_AUTH_TOKEN` | 登录 token，优先级高于 `~/.aixcoding/auth.json` |
| `AIXCODING_AUTH_ENVIRONMENT` | `internal/online/local`，决定 auth 文件 |
| `AIXCODING_AUTH_ALLOW_SELF_SIGNED` | auth TLS 自签名开关 |

证据：旧副本 `config.py:41-71,93-136`。

## 3. 核心 ID 与关联模型

### 3.1 核心关联 ID

| ID | 旧版生成/来源 | 用途 |
|---|---|---|
| `sessionId` | `current_trajectory().session_id` | 会话级关联 |
| `spanId` | 固定 namespace 下 `uuid5(session_id + ":" + turn_id)` | 一轮 pass 的根 span |
| `requestId` | 每次 ChatMiddleware 调用生成 UUID4 | 逻辑模型调用与工具、ai-code、ACP 的主关联键 |
| `llmSpanId` | 每次 middleware 调用生成随机 `sp-` ID，不出现在 LLM body | 工具上报的 `parentSpanId` |
| `funcId` | tool-detail save 时取 `provider_call_id or event.call_id`，普通本地事件 fallback 为 12hex；同一 `_CallRecord` 后续复用 | save、PENDING、final update 的匹配键，不等于 requestId |

根 span 证据：旧副本 `llm_telemetry.py:46-47,88-90,187-193`。

### 3.2 为什么 requestId 是服务器关联键

1. middleware 在请求前生成 requestId，并写入 `body.telemetry.requestId`。
2. 响应完成后，按 provider tool call ID 登记 `requestId/spanId/llmSpanId`。
3. tool-detail 用 provider call ID 查 per-call registry 找回 requestId，未命中可回退 session-latest；对外 funcId 则独立取 `provider_call_id or event.call_id`，两者不能混为同一字段。
4. ai-code 通过工具调用找回 requestId。
5. ACP 最终响应通过 registry 返回 requestId。

证据：旧副本 `llm_telemetry.py:183-214,240-295`、`tool_detail.py:147-196`、`ai_code.py:240-260`。

### 3.3 两套 registry

- **session registry**：保存当前 turn ID、最新主调用 request/span/llmSpan；最多 8 个 session，带条件等待。
- **per-call registry**：键为 `session_id + provider_call_id`；并发同名工具也按 call ID 分开；4096 条上限。

`local_*` side call 不加入 registry。没有命中的工具会回退到 session-latest，这是后续需要修正的缺陷而非应保留语义。

### 3.4 重试语义

- 旧 requestId 在 middleware 调用前生成，SDK 内 HTTP retry/redirect 复用已构造请求体和 ID。
- 外层重新进入 middleware 会产生新 requestId。
- 根 span 使用当前 pass turn ID，不是跨 retry 的 logical turn ID。

## 4. LLM 请求搭车

### 4.1 注入方式

在 `call_next()` 前将 telemetry 写入 `context.options["extra_body"]["telemetry"]`，位于模型 HTTP JSON 顶层。

body 字段包括：

| 分组 | 字段 |
|---|---|
| 标识与事件 | requestId、sessionId、可选 spanId、eventType、eventSubType |
| channel | channelType、channelName（固定 `icode`）、可选 channelVersion |
| 客户端 | pluginVersion；非 desktop 时可选 agentName |
| 项目与 Git | projectName、gitRemote、gitBranch、gitRevision、gitOwner、gitRepo |

旧版实际 body 不包含 userId/loginUserId、modelId/actualModelId、approvalMode、usage/outcome/timing 或 extensionName/extensionVersion；这些不能被当作旧搭车字段基线。类型声明见旧副本 `telemetry/types.py:53-74`。

流式通过 `stream_result_hooks` 等最终响应钩子完成 registry 登记，不在每个 delta 上登记。证据：旧副本 `llm_telemetry.py:240-284`。

### 4.2 独立报文中的用户 ID

`userId` 在 tool-detail/ai-code 等独立报文的公共字段中，不在 LLM body。最终代码来源为登录会话 `stored_user_id` 优先，未登录或不可用回退配置文件 `userId`。证据：旧副本 `context.py:107-139`、`reporters/__init__.py:65-108`。

## 5. EventBus 到 CSAS 事件映射

证据：旧副本 `subscriber.py:130-180`。

| 上游事件 | 旧版动作 |
|---|---|
| `model.response.received` | 更新 session-latest 主调用 |
| `tool.execution.started` | tool-detail save + PENDING update |
| `tool.execution.finished` | tool-detail 终态 update；写工具成功时生成 ai-code blocks |
| `file_snapshot.captured` | 捕获文件 before/after 文本 |
| `mutation.committed` | 累积变更行数 |
| `approval.requested` | 记录审批模式/超时/resolved-by |
| `approval.resolved` | 判断 auto/user/timeout/rejected |
| `sub_agent.*` | 按 agent 类型映射 selected Agent 或普通工具 |
| slash skill 解析命中 | 额外一条 funcType=0 的 save |

EventBus 采用 subscribe 回调，事件处理器只执行轻计算和入队，网络发送由共享 reporter 串行处理。

## 6. 独立上报报文

### 6.1 tool-detail

#### save

最终代码字段包括：

- funcId、funcName、funcType、sessionId；
- 可关联时带 requestId、spanId、parentSpanId；
- 可选 value、fileName、agentName；
- 公共字段 pluginVersion、userId、channel、project/Git。

`funcType`：技能使用 `0`、MCP `1`、内置工具（含 load_skill 工具维度）`3`、selected Agent `1001`。

full 模式把参数 JSON 放入 `value`；技能工具保留 `skill_name`，`read_file` 不走 value 白名单。`fileName` 适用于 `write_file/edit_file/read_file/view_image`；工作区内相对、工作区外绝对、无 workspace 时不相对化。

#### update

PENDING update 包含 funcId、funcName、codeStatus=3、executionStartedAt。终态 update 包含 funcId、funcName、codeStatus、status、executionDurationMs，并可带 executionStartedAt/executionFinishedAt、failureType、funcErrorMessage 和 originalLines/addedLines/deletedLines。

状态：成功 `1`、失败 `2`、PENDING `3`、拒绝 `4`。旧 tool-detail save/update 均不含 reportId、eventTime 或 funcResponse；reportId 属于 ai-code/save，成功结果正文也不通过 tool-detail 上报。证据为最终 `tool_detail.py:147-276`。

#### selected Agent

CLI 从 selected-agent envelope 以 agentMarketSkillId 为准入条件、agentName 为 funcName；functionName/runner 写入 agentName。每次 prompt 的 ContextVar scope 以 reported 标志去重，首次模型调用确定 requestId/spanId 后发一条 funcType=1001 save，无 update。**funcId 是 reporter 新生成的 UUID，不是内容版本；CLI 最终源码未使用 toolsetId/内容版本作为该 funcId。**证据：`tool_detail.py:278-301`、`llm_telemetry.py:62-85`。

#### 广义调用边界

- 模型 shell 工具按 funcType=3 普通工具处理；普通 slash command 和用户直接终端命令没有独立的通用 tool-detail 埋点，不能虚构 command 类别。
- local/外部 ACP sub-agent 的外层委派都是普通 funcType=3 工具，与 selected Agent 1001 不同。local child 内部工具经 SubAgentEventMiddleware 上报。
- 外部 ACP 内部 ToolCallStart/Progress 也由本地 AcpUpdateTranslator 转成 InvocationToolCallStart/Result 后上报，但只是展示投影；title 不保证真实工具名，ACP kind 会损失 MCP 等类型。provider_call_id 未命中时 requestId 可能回退 session-latest，并非远程内部 exchange 真值。
- provider-hosted 工具同样经 HostedPresentationBridge 进入 reporter；hosted MCP 可按 family 映射 funcType=1，但它没有本地普通 tool operation 语义。

逐类新版重建判断见 `nodes/broad-tool-coverage.md`。

### 6.2 ai-code

来源：`write_file/edit_file` 成功后的 before/after 快照与最终工具参数；只有 save，没有 update。

- `write_file` 上报完整新文件；
- `edit_file` 按 `old_string/new_string/replace_all` 定位变更块，replace_all 每处一个 block，超过 64 个回退全文；
- CRLF/CR 规范化为 LF 后定位；snippet 为 new_string，rangeStart/rangeEnd 从 1 开始；
- 精确定位失败时可尝试唯一片段，否则回退完整新文本；after 为空或纯删除不报。

实际字段：reportId、filepath、blocks、sourceType=edit、inputMethod=ai_generated、sessionId、codeStatus，以及条件 requestId、spanId、agentName、language、remote/branch/Git user 和公共 channel/project/Git 字段。**不含 funcId、parentSpanId、行数、eventTime 或 reportType；original/added/deleted 行数属于 tool-detail update。**

审批映射：manual 请求且有批准响应 `5`，judge/auto/bypass/无审批 `1`。拒绝不会产生 ai-code，4 只落在 tool-detail；旧 ApprovalTracker 以请求时 mode=manual 近似用户批准，不能精确区分 user/judge 代答。证据：最终 `ai_code.py:93-158,161-194,219-278`。

## 7. ACP 输入与输出

### 7.1 输入

旧版在 prompt `_meta` 读取独立 envelope：

- `agent-studio.dev/ide-name`：ideName；
- `agent-studio.dev/ide-version`：ideVersion；
- `agent-studio.dev/function-name`：functionName（runner）；
- `agent-studio.dev/selected-agent`：agentMarketSkillId 为准入条件，agentName 上报为 funcName；
- `agent-studio.dev/response-attribution`：spanId，用于最终模型归因回传。

输入用于桌面 channel、runner、selected Agent 和最终模型归因；它不是桌面端自行上报的替代品。证据：最终 `telemetry/acp_meta.py:21-75`、`acp/server.py:325-394`。

### 7.2 输出

`PromptResponse._meta` 返回：

- `agent-studio.dev/telemetry`：`{schemaVersion:1, requestId, spanId}`；**旧 envelope 实际没有 sessionId**，此前文档把 sessionId 写成输出字段不准确。sessionId 由 ACP 会话上下文和 registry key 提供。
- 可选 `agent-studio.dev/final-model-identity`：`{schemaVersion:1, spanId, requestId, source:"model_request_id"}`。这里的 spanId 是桌面 prompt 提供的归因 span，不是 turn span；无有效归因或本次身份时不发送该扩展键。

模型 middleware 在非流式响应完成、流式完整终结后更新 registry，纯文本响应同样登记。ACP 在 session/turn 完成构建最终 `PromptResponse` 时一次读取 registry 并生成 meta；没有通过流式 `session/update` 逐次发送身份。实际顺序是 save→checkpoint→after_turn→事件 drain→PromptResponse，因此 after_turn 可以准备轻量结果，但仍需响应合并接缝。

旧限制：registry 是 session-latest，不隔离 turn，可能把上一轮 requestId 挂到本轮；多次主模型调用只保留最后一次；失败且无当前 turn 成功身份时可能残留旧值。新版必须按 `(session_id,turn_id)` 隔离并使用 A-final，不能复制旧 UUID4/session-latest。

消费方：Agent Studio `acp-agent-host.ts` 从最终响应 `_meta` 读取 final-model-identity，校验归因 span 与当前 prompt 相同，在 completed 前发出 `prompt.request_identified`。测试表明身份缺失、空白或归因 span 不匹配会返回错误并取消任务，不是可静默省略的装饰字段。

当前上游基础：b4f354d（v0.30.1）已在 turn_started、流式 update、最终响应和 `session/turns` 中提供稳定 turn/request-attempt 数据；9cd8031d（v0.31.0）提供真实流式文本/推理。责任人于 2026-11-17 确认仍需保持“最终 PromptResponse 主动携带 requestId”的旧形态，因此查询接口不能替代薄输出接缝。

证据：旧副本 `telemetry/acp_meta.py:20-123`、`aixcoding/telemetry/llm_telemetry.py:80-304`、`app/acp/server.py:331-418`；Agent Studio `acp-agent-host.ts:1384-1404,3166-3235`。旧 helper 三项同步测试已执行通过；桌面端到端接收联调在旧计划中仍未完成。

## 8. HTTP 与 mock

### 8.1 生产上报

- 单 worker FIFO，保证同一工具的 save → PENDING → final 顺序；
- 默认超时 10 秒，最大队列 8192；
- 网络和 HTTP 错误吞掉，不让 telemetry 影响产品主流程。

端点：

- `/api/external/csas/tool-detail/save`
- `/api/external/csas/tool-detail/update`
- `/api/external/csas/ai-code/save`

mock 另外支持 batch-save、event-reaction/save，但旧版生产 reporter 不调用这些扩展端点。

### 8.2 telemetry mock

旧副本 `aixcoding/mock/` 提供：

- 默认 `127.0.0.1:4321`；
- SQLite 原文存储和 rejected 表；
- `/debug/view`、`/debug/data`、`/debug/stats`、`/debug/faults`；
- http500/http503/slow/envelope_reject/drop_body 故障注入。

注意：LLM body telemetry 发往模型网关，独立 CSAS mock 收不到；旧版通过 raw LLM HTTP log 或模型 mock 观测。

## 9. 旧版已知缺陷与历史限制

本表仅保留概览；逐项分类、证据、影响风险与未证明事项以 [D1 缺陷登记册](defect-register.md) 为准。登记不代表新版已实施修复。

| 编号 | 缺陷/限制 | 影响风险 | 新版处理方向 |
|---|---|---|---|
| L-D01 | provider ID 未命中时回退 session-latest | 并发、sub-agent、跨 turn 可错关联 | 精确 exchange/tool operation 关联，未知不猜测 |
| L-D02 | 本地 sub-agent 事件缺 provider call ID | 回退内部 ID，并发时更易错位 | 使用 session call_id + operation join |
| L-D03 | common_fields 无 workspace 时回退进程 cwd | projectName/Git 可能属于错误项目 | 无 workspace 省略，不以 cwd 冒充 |
| L-D04 | 主 Agent/local child 部分取消路径没有 Result | 客户端只发 PENDING，服务器终态未证明 | 不伪报失败；后端无 cancelled 状态则登记协议限制 |
| L-D05 | 无运行 loop 时 submit 丢弃；stop 取消 worker；不解析 2xx 业务 envelope | 静默丢失或业务拒绝不可见 | 明确生命周期、业务码可观测、正常退出有界 flush；不做崩溃补报 |
| L-D06 | slash skill 从 session-latest 取 span | 可能使用上一轮或无 span | 当前真实 logical turn ID 转 UUID 作为 spanId，requestId 仍省略 |
| L-D07 | ACP 最终响应只有 session 最新 requestId | 取消可取旧值；多调用表达取决于桌面契约 | 已确认最终 PromptResponse 主动携带当前 turn requestId；暂行锁内 live-history 精确选择，不回退旧值 |
| L-D08 | desktop channel/function name 为进程级最近值 | 多 ACP client/session 可互相覆盖 | 按 session/invocation 捕获 |
| L-D09 | manual 审批近似用户批准，旧请求/响应不足以证明最终 decider | 采纳状态可能不精确 | 使用新版明确状态，无法区分时登记 |
| L-D10 | ai-code 定位失败回退完整新文本；buffer 超 500 丢最旧 | 可能扩大代码归因或丢数据 | 参数/快照不一致时降级；有效 replace_all 超 64 块的全文回退可保留，丢弃指标留实施 |
| L-D11 | 外部 ACP interrupted Result 的 metadata 被分类器忽略 | 取消被归 codeStatus=1 成功 | 先识别取消，再按届时经确认的协议处理；不归成功也不一律普通失败 |

## 10. 上游改动成本

旧版主要上游接触面：

- `service/llm/instrumented.py`、`service/llm/clients.py`：middleware 与上下文；
- `service/agent_middleware/events/tool_events.py`、`sub_agent_events.py`：provider ID 和 workspace；
- `orchestration/engine/assembly.py`：subscriber；
- `orchestration/engine/run/runner.py`、`active_injection.py`：slash skill；
- `app/acp/server.py`：ACP 输入/输出；
- `foundation/events/types.py`、`build/builder.py`：事件与 workspace 上下文。

新版探索的核心不是机械照搬这些挂点，而是优先复用 session/trajectory/mutation 持久化，仅保留动态请求、进程内触发、ACP 边界和必要运行时上下文的最小接缝。

## 11. 原始参考

- 旧副本 `aixcoding/docs/telemetry/iCode-数据上报直改源码方案.md`：原始设计。
- 旧副本 `aixcoding/docs/telemetry/plan.md`：M1–M4 实施与验收状态。
- 后增 ACP response-attribution/final-model-identity 以旧副本 `src/chrys/aixcoding/telemetry/acp_meta.py`、`src/chrys/service/llm/final_response_identity.py` 和 `src/chrys/app/acp/server.py` 最终代码为准；selected Agent 以 `telemetry/reporters/tool_detail.py` 和 `telemetry/subscriber.py` 为准。
- 新版对照：`new-version-solution-map.md`、`capability-matrix.md`、`request-identity.md`。
