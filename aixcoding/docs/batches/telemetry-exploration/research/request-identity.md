# Request Identity：逻辑调用、HTTP attempt 与旧 requestId

> 状态：责任人于 2026-11-16 **暂定最终成功 attempt ID 作为服务器主 requestId**；实现发现严重问题时回评 exchange。缺 A-final 时跳过并记录原因，不用 exchange 混填。**2026-11-18 ID 原值裁决：所有 ID 保持原值 32hex、不转 UUID**（此前短暂的 UUID 归一化安排已作废），本文正文中出现的 UUID 转换与 golden 表述均为历史讨论记录、按原值理解，批次1 design 时统一重写（权威口径见 backend-change-requests.md BR-5）；**同一成功 M 的相关外部记录同文本，不同 M 的 A1/A2 不得混用**。M0/M1-I 身份证据见 `a-final-e2e-closure.md`，节点状态见 `nodes/request-id.md`，本文保留完整讨论证据。

## 1. 问题

旧版 telemetry 以后台 `requestId` 关联 LLM 搭车、tool-detail、ai-code 和 ACP 输出。0.35.2 已有 `request_attempt_id` 和 `model.exchange.operation_id`，需要判断谁能继承旧语义，以及是否需要建议上游继续改进。

此前曾表述“request_attempt_id 不能作为 requestId”。该说法过度，现修正为：**它能唯一标识一次实际 HTTP 模型请求，但不能在保持旧版逻辑调用粒度、body 注入时机和重试语义不变时直接原位替换旧 requestId。**

## 2. 基线与证据

- 新基线：`iCode-fork` 0.35.2。
- 旧基线：`D:\Coding\aixcoding\aixcoding-cli\aixcoding-cli__0.28.0_final`。该绝对路径是责任人本机留档位置，不是协作者或 CI 的通用路径；其他环境需自行定位同一 0.28.0 终态副本并重核引用行号。
- 上游引入提交：`7a5541b8c6895c61f15869b5e4f4184a2ec5918c`，`feat: correlate HTTP attempts and tool mutations`。
- ACP 后续提交：`b4f354dbf8fb51a75894e57a51cd661ffec58291`，`feat(acp): add stable turn identities and per-turn request tracing`。
- 当前实现：`src/chrys/service/llm/request_tracking.py:37-108`。
- 当前测试：`tests/service/llm/test_request_tracking.py`、`tests/integration/engine/test_turn_trace_projection.py`。
- 旧实现：旧副本 `src/chrys/aixcoding/telemetry/llm_telemetry.py:183-214,240-295`。

## 3. 三种 ID 的语义对比

| ID | 标识对象 | 生成时机与格式 | SDK retry/redirect | 模型请求体 | 持久化与关联 |
|---|---|---|---|---|---|
| 旧 AIxCoding `requestId` | 一次逻辑 ChatMiddleware 调用 | middleware 中 UUID4，body 构造前 | 同一已构造请求重发时复用 | `extra_body.telemetry.requestId` | AIx per-call/session registry，供 tool-detail、ai-code、ACP 使用 |
| `model.exchange.operation_id` | 一次逻辑 Kernel/Wire acquisition | `begin_exchange()` 在调用内层 client 前生成，32 hex | 同一 exchange 内不变 | 不自动发送，但 middleware 可读取并注入 | exchange events、assistant message `_chrys_operation_id`、turn trace `modelCallId` |
| `request_attempt_id` | 一次 httpx prepared HTTP attempt | request hook 生成，128-bit 随机 32 hex | 每次 retry/redirect/协议内 resend 变化 | 不进入 body；写 `Chrys-Request-Attempt-Id` header | 全部 attempts 在 trajectory/turn trace；最终 attempt 在 response/message；raw HTTP log |

典型关系：

```text
一个逻辑 exchange operation_id
  ├─ HTTP attempt A：连接失败或收到响应
  ├─ SDK retry attempt B：新 attempt ID
  └─ redirect hop attempt C：新 attempt ID
```

因此，“一次大模型调用”必须先定义粒度：若指实际 HTTP 请求，attempt ID 合适；若指旧版逻辑调用，exchange operation ID 更一致。

## 4. 已核实事实

1. `request_tracking.py` 模块明确标注 per-HTTP-attempt identity，且每次 prepared 都新生成 ID；不是普通日志随机数。
2. 上游测试静态覆盖 Chat Completions、Responses、Anthropic，非流式/流式、SDK retry、redirect、连接失败和 message 持久化。
3. 一个 exchange 可对应多个 attempt；最终 response/message 只带最后 attempt，完整列表在 trajectory/turn trace。
4. attempt ID 在 SDK 请求构造之后由 httpx hook 生成，仅修改 header/extensions，不读取 body。
5. Responses retrieve 也经过 tracking hooks，但 retrieve 是 GET，没有 create 那样的模型请求 body。
6. 旧 requestId 是 middleware 调用前生成的 UUID4，SDK 内重试复用同一请求体和 ID。
7. `exchange_operation_id` 在 middleware/body 构造前已存在，可由 ChatContext 中的 ExchangeTrace 读取；没有 trajectory cycle 时可能不存在。

## 5. 当前暂定的主 ID 方向

- 责任人于 2026-11-16 暂定：新 telemetry 只关联最终成功模型响应，服务器主 `requestId` 使用最终成功 assistant message 的 `request_attempt_id`（A-final）。实际实现发现严重问题时回评 exchange，不承担上线后迁移场景。
- exchange 保留为内部逻辑调用、retry 边界、工具/mutation 关联和回退证据；不与 A-final 混填同一个 requestId。
- 失败、pending、部分流不上报；模型成功后工具失败不影响模型 A-final 的有效性，工具 outcome 和 ai-code 写入条件独立判断。
- 当前 N1 可直接复用现有 raw attempt header：后台原成功记录将 raw A-final 归一化为外部 UUID，after_turn 独立报告、tool-detail、ai-code 和 ACP 在客户端定制边界用同一规则转换，不需要 C1 exchange header 或 C2 映射；C1/C2 仅为开发期回退备选。
- 缺少 A-final 时跳过该条并记录原因，不使用 exchange、历史 attempt 或另造 UUID4 兜底。
- ID 原值口径（2026-11-18 裁决）：内部 header/session/trajectory/message 与所有外部记录使用同一 raw 32hex 原值，无转换层；不修改 request_tracking.py 或 ids.py。后台 32hex 格式接受/新旧混存与桌面 schema（放宽）留联调验收。

该方向利用现有最终 attempt 持久化和线上 header，消除新增 exchange 传输及 attempts 分组需求；开发期必须验证流式、retry、Responses 和失败防错矩阵。

## 6. 能力分类

| 能力 | 分类 | 理由 |
|---|---|---|
| 从文件取得逻辑 exchange ID 和全部 attempt ID | 纯文件可做 | trajectory/turn trace 已持久化；session message 只保留最终 attempt |
| 用 exchange ID 继承旧 requestId 语义 | 现有通用机制可支持 | middleware 可在 body 前读取；无需上游新增 ID |
| 把动态逻辑 requestId 放入模型 body | 仅 N1-A 需要 fork 组栈或通用 middleware 注册 | 当前产品配置没有 ChatMiddleware 注册入口；N1-C 不需要 |
| 通过 after_turn 独立接口上报 exchange ID | 纯文件可取得，依赖 N3/N8 和服务器 endpoint | 不需要修改已发模型请求 |
| 将每个 attempt 的不同 ID 写入每份 body | 当前机制不支持，且本需求不必要 | attempt 在 body 构造后生成；需要更大的 per-attempt 序列化钩子 |
| 降低对内部 ExchangeTrace 传递结构的依赖 | 仅 N1-A/N1-B 可建议公共只读 helper | N1-C 从事后 trajectory 获取，无此依赖 |

## 7. 不建议向 iCode 提出的改动

- 不建议让 SDK retry/redirect 复用 attempt ID。
- 不建议把 attempt ID 改成整个 exchange 稳定。
- 不建议为了旧 telemetry 兼容而增加 AIxCoding 专属 requestId 字段。
- 不建议在没有真实提供商需求时增加 per-attempt body 序列化钩子。

## 8. 开放问题与下一实验

- 当前暂定主 ID 为最终成功 attempt；全部 attempts 仅内部诊断，不作为服务器关联前提。
- ID 原值裁决（2026-11-18）：内部 raw 32hex 与全部出站同文本，后台原值保存，客户端无转换；后台 32hex 格式接受与真实桌面 schema（放宽）留联调。
- 开发期验证普通/流式、SDK retry、redirect、外层 retry、Responses continuation 的最终 M 与服务器记录同 A；失败/pending/部分流不上报且不借旧 A。
- 缺 A-final 已裁决为跳过并记录原因，不再研究 exchange/UUID4 混填 fallback。
- N1-A/N1-B middleware/body 实验只在回退 exchange 时恢复；当前 N1-C 直接复用 attempt header。

实验计划见 `../experiments/request-identity.md`；实际执行证据追加到 `../verification.md`。

## 9. exchange 与 attempt 的完整语义对照（2026-11-16 讨论落盘）

### 9.1 生成与流转顺序

```text
1. Kernel begin_exchange()
   生成 exchange E1

2. ExchangeTrace 经 client_kwargs 传入模型 client
   middleware 在请求体构造前已经可以读取 E1

3. Chat/Responses/Anthropic 协议层构造请求
   当前 exchange 不自动进入 body 或线上 header

4. HTTPX prepared hook
   新生成 attempt A1
   写 Chrys-Request-Attempt-Id: A1
   以 operation_id=E1 + request_attempt_id=A1 写 trajectory

5. 收到响应头
   记录 A1 的 HTTP status 和可选 provider request ID

6. 非流式响应落地或流式响应消费完成
   exchange E1 记录整个逻辑调用的最终 outcome

7. 新产生的 assistant message
   保存 E1 和最终响应 attempt；不回写历史/echoed message
```

因此 exchange 可以在 body 构造前读取，attempt 在当前机制下不能分别注入每个已构造 body。Responses retrieve 是 GET，也没有 create 那样的模型请求体。

### 9.2 基数、重试和缺失矩阵

| 场景 | exchange | attempt | 关联口径 |
|---|---|---|---|
| 普通单次 HTTP 成功 | E1 | A1 | 一对一，但 E1/A1 是独立随机值，不能互相推导 |
| SDK 内 retry | E1 不变 | A1、A2…… | 同一逻辑调用多个 HTTP attempt；最终 message 只带最后 A |
| redirect | E1 不变 | 每个 hop 新 A | 不复用上一跳 attempt |
| Responses create + retrieve | **每次 poll 新建 E1/E2/E3**；上一 E 在 poll 前已关闭 | create/每次 retrieve 各一个 A | 最终工具属于最后 poll 的 E-final/A-final，不能固定取 create |
| Chrys 外层 wire retry | 新 E2 | 新 A2 | 端侧重新发起逻辑调用；内部 E1/E2 不回并，外部只取最终成功 M 的 A-final |
| 同一用户 turn 多轮模型调用 | E1、E2、E3…… | 每个 E 各有 A | 工具和 ai-code 关联实际产生它们的 E，不统一挂最后调用 |
| 主 Agent 与 local sub-agent 并发 | 各 actor 自己的 E | 各 E 自己的 A | child 工具使用 child 的 E/A，不挂父 exchange |
| prepared 前取消/失败 | E 对象可能已生成；是否有事件取决于是否 started | 可能没有 A | 不从旧 message/session-latest 补 ID |
| HTTP 连接失败 | 可有 E | prepared A 已生成，可能无响应头 | A 的存在不证明到达 provider 或业务成功 |
| 无 ExchangeTrace 的直接 client 调用 | 没有可自动 join 的 E | 仍可生成线上 A | 当前可使用成功 A；缺 A 时跳过并记录原因，不用 exchange 冒充 |
| 流式响应 | 单次 acquisition 一个 E；SDK retry 不变，外层 stream retry 新建 E | 不为 chunk 新建 A；真实 HTTP retry/redirect 才新建 | 响应头收到不等于流完成；最终 M 的 A-final + exchange outcome 共同证明成功关联 |

两者并非必然同时存在：exchange 可以没有 prepared attempt，attempt 也可以在没有 trajectory exchange 的直接调用中存在。

### 9.3 格式相同不代表语义相同

exchange 和 attempt 都通过 `new_analytics_id()` 生成 32hex/128-bit 随机值，但生成次数、生命周期和用途完全不同，二者没有派生关系。当前暂定的 attempt 主键可无损格式化为 UUID 文本，例如：

```text
00112233445566778899aabbccddeeff
→ 00112233-4455-6677-8899-aabbccddeeff
```

该转换保留 128 bit，不保证 UUID4 version，也不需要重新生成。当时的归一化安排要求不能只在 after_turn 或 ACP 单面转换，后台原成功记录与客户端各出站边界必须应用同一确定性规则——该安排整体已由 2026-11-18 原值裁决废止，现行为内外同文本原值、无需任何转换。

另一个命名陷阱：raw HTTP log 的 `exchange_id` 字段在当前实现中优先装的是 request attempt ID，并非 `model.exchange.operation_id`；不能按这个历史字段名误判身份。

### 9.4 与旧 requestId 及 C1/C2 的关系

旧 requestId 在 middleware 中按逻辑调用生成 UUID4，并在 SDK 内 retry 中随同一 body 复用，所以语义更接近 exchange，而非 attempt。当前需求已暂定改为成功响应粒度，因此不再沿用这一旧主键语义。

**当前线上服务器并不知道 attempt 分组**：客户端 trajectory 的 `model.request.*` 同时保存 E 和 A，所以客户端知道 `E1 ↔ {A1,A2}`；但线上请求目前只有 raw attempt header，没有 exchange header，且 A 是无分组语义的随机值，服务器不能从 A1/A2 反推它们属于同一 E。A-final 路线不需要恢复该分组，只需最终成功记录与上报数据使用同一外部 UUID(A-final)。

- **当前路线**：直接复用现有 raw attempt header，后台原记录负责归一化，客户端独立报告、工具和 ai-code 出站时使用最终成功 M 的 UUID(A-final)；缺 A-final 跳过并记录原因，不用 exchange 混填。
- **C1 回退备选**：新增 `Chrys-Exchange-Id`，与现有 attempt header 并存。SDK retry 时 E 不变、A 改变；Responses 每次 poll 新建 E，因此使用 E-final。服务器按 E-final 合并，不要求先聚合全部 A。
- **C2 回退备选**：独立报告携带 E + attempt 映射，服务器用实际已落库 A 找到原记录并建立 E 关联。如果没有可匹配 A，C2 无法闭环。
- 只有回退 exchange 或新增“HTTP 诊断分组”需求时，才需要处理 E↔A 分组；当前 A-final 业务关联不预设该存储需求。
- 回退时也不应用 E 替换现有 attempt header，否则会删除逐 HTTP attempt 诊断维度。

## 10. 上报工具调用、ai-code 时两个 ID 的可获得性

### 10.1 直接结论

**正常成功且已经产生 assistant message 时，exchange ID 和最终 attempt ID 都可以从 `session.json` 获得；全部 attempt IDs 不能只靠 `session.json`，需要联读 trajectory/turn trace。**

这里必须区分“`session.json` 文件”和“整个 session 目录”：

| 数据来源 | exchange E | 最终 attempt A | 全部 attempts |
|---|---|---|---|
| `session.json` 中新产生的 assistant message | 有：`_chrys_operation_id` | 有：`_chrys_request_attempt_id` | **没有**，只保留最终项 |
| trajectory `model.exchange.*` | 有：`operation_id` | 不作为稳定的直接字段来源，联读 request/message | 不直接完整表达 |
| trajectory `model.request.prepared/headers_received` | 有：事件的 `operation_id` 是所属 E | 每条记录各自的 A | 完整日志未缺失时可有 |
| turn trace | 有：`modelCallId` | 最终项可由响应/message 辅助确认 | 有：`attempts[]`，含 status/provider request ID |
| 本地 tool operation | 有：`parent_model_operation_id` | 通常不直接保存 | 不直接保存 |
| mutation/blob | 不直接保存 E | 不直接保存 A | 不保存；经 tool operation 回查 |
| 外部 ACP 内部 update 投影 | 没有远程内部 E 真值 | 没有远程内部 A 真值 | 不能从父 exchange/attempt 冒充 |

### 10.2 普通工具调用

正常本地工具使用：

```text
tool operation T / function_call C
  → 找到产生该 function_call 的 assistant message M
  → M._chrys_operation_id = exchange E
  → M._chrys_request_attempt_id = 最终响应 attempt A
```

所以，对正常工具调用：

- **最终 attempt 可获得**，并暂定为外部主 requestId；
- **exchange 也可获得**，用于内部关联和开发期回退，不与 A-final 混填；
- 如果需要全部 attempts，则再从 E 联读 trajectory，而不是从工具事件或当前 session-latest 猜测；
- 若 assistant metadata 缺失，可用已登记的持久化父链 `T → parent E → 该 E 的成功 terminal/request records` 补证据；证据仍不足时跳过该条并记录原因，不取 `attempts[-1]`。

 Responses create/retrieve 场景中，M 上的 A 通常是实际返回该 function_call 的 retrieve attempt；这正符合“生产响应 attempt”，不能误换成 create attempt。

### 10.3 ai-code

ai-code 的关联多一层：

```text
mutation/blob
  → mutation.tool_operation_id = T
  → T.parent_model_operation_id = E
  → 产生该工具的 assistant M 提供 E 和最终 A
```

因此：

- PR #69 新增的是 `mutation.tool_operation_id=T`；旧 `mutation.tool_call_id` 仍是独立 12hex UI ID，不是 T/provider ID，也不是关联桥；
- mutation/blob 本身没有 E/A，不等于无法关联；
- 正常成功 write/edit 的 E 和最终 A 均可经 T/M 获得；
- 失败、拒绝、取消即使留下 mutation 也不应仅据此上报 ai-code；
- mutation、tool operation、assistant metadata 或 blob 缺失时按 N6 降级，不能用当前文件、当前 exchange 或旧 session-latest 补齐。

### 10.4 哪些情况下 session.json 不能提供

以下情况可能没有“本次新产生的 assistant message”，因此 `session.json` 不能提供本次 E/A：

- 模型请求失败且没有落地响应；
- prepared 前取消；
- 消息尚未 landing；
- 旧记录没有 metadata；
- 当前消息是历史 echoed message，而不是本次新响应。

此时应联读 trajectory：可能仍有 E 和 prepared A，但没有最终 A。当前只记录成功模型调用，因此没有 A-final 时跳过该条并记录原因；不存在的工具/ai-code 记录不能虚构。trajectory 也缺失时，两者都 unknown，同样不混填。

### 10.5 对其他广义调用的限制

- slash skill 是 pass 级 save-only，没有产生它的 exchange/attempt，不能硬关联。
- selected Agent 是 ACP 使用记录，可在已确认的模型调用上下文中携带 E/A，但不能据此把选择动作变成工具 operation。
- local sub-agent 内部工具使用 child 自己的 E/A；外部 ACP 内部工具没有远程内部 E/A，只能使用明确标注的投影字段或降级。
- provider-hosted 工具可由 assistant M 关联 E/最终 A，但它不是本地 tool operation，完整 attempt 仍从 trajectory 获取。

### 10.6 对上报方案的影响

- 当前内部主身份为 raw A-final、外部 requestId=UUID(A-final) 时，**缺 A-final 必须跳过该条并记录原因**，不能用 exchange、历史 A 或新 UUID4 混填。
- 内部仍保留 E 以完成 T/C/M 和 mutation 关联；缺少 E 但成功 M 有可信 A-final 时，不虚构 E。
- 若开发期回退 C1，原记录直接携带 E-final，A 缺失不再阻断 exchange 主键；回退 C2 时 A 同时承担寻找原记录的桥梁，必须另行确认服务器实际保留哪个 A。
- 无论当前或回退分支，都不能仅因 session.json 有最终 A 就声称全部 attempts 可获得，也不能把多个失败/中间 A 当成成功业务 requestId。

## 11. 暂定决策：只关联最终成功模型响应，采用最终 attempt

> 状态：责任人于 2026-11-16 **暂定采用该分支**。不再要求保持“一次逻辑调用一个主 ID”的旧粒度，只要求成功模型调用与其后续工具/ai-code 关联。实际实现发现严重问题时回评 exchange；缺 A-final 时跳过，不混用兜底。

### 11.1 “成功”的精确定义

本分支中的成功应指：**某次模型调用成功产出最终响应并落地为本次新 assistant message**。它不是任意 HTTP 2xx，也不是整个用户 turn 或后续工具全部成功。

Responses 的 create/poll 可能返回 2xx + in_progress，这只是中间状态；只有最终 completed/可用响应才是本分支要关联的成功。模型响应成功后，即使后续工具失败或 turn 取消，工具和 ai-code 仍可与该成功模型响应关联，工具自身 outcome 单独表达。

### 11.2 在该假设下哪个 ID 更合适

| 判断点 | exchange E | 最终成功 attempt A-final |
|---|---|---|
| 标识成功响应 | 标识整个 acquisition，需再定位最终响应 | **直接标识产生最终响应的 HTTP attempt** |
| 工具/ai-code 文件可得性 | 正常 message 有 | 正常 message 也有 |
| 原请求线上关联 | 当前无 exchange header，需要 C1 或 C2 映射 | **已有 `Chrys-Request-Attempt-Id`** |
| 新增上游请求头 | C1 需要 | **不需要** |
| 服务器分组 E↔A | C1/C2 需要处理 | **不需要，直接使用 A-final** |
| retry 语义 | 所有 SDK attempts 共用一个 E | 只选择最终成功 A，失败 A 不进入本 telemetry 范围 |
| 与旧逻辑 requestId 粒度 | 一致 | 有差异，但在本假设下该差异可接受，仍需责任人确认 |

因此，**若上述需求假设成立，最终成功 attempt ID 比 exchange ID 更直接、更小改动**。exchange 可继续作为客户端内部分组和诊断信息，但不再是服务器关联的必要键，C1 新增 exchange header 和 C2 E↔A 映射都可取消。

### 11.3 SDK 什么时候 retry

当前锁定的 OpenAI 和 Anthropic Python SDK 均在以下 HTTP 状态上具备 retry 规则，并受 `max_retries` 等配置限制：

- 408 请求超时；
- 409 lock/冲突类超时；
- 429 限流；
- 500 及以上服务端错误；
- `x-should-retry: true/false` 可由服务端显式覆盖默认判断。

连接失败、请求超时等传输异常也可触发 SDK retry。OpenAI 当前实现还会在 `Retry-After` 超过其允许上限时放弃 retry。具体是否重试及次数以实际 profile 的 `http_max_retries` 和 SDK 版本为准，不能把 retry 当成无限进行。

普通 400 业务参数错误、模型拒绝或用户取消不是这里所说的通用 SDK retry 理由。每次实际 retry 都会生成新的 attempt；exchange 不变。例如：

```text
exchange E1
  ├─ attempt A1 → 429，SDK 决定 retry
  └─ attempt A2 → 最终成功响应
```

在本需求假设下，工具和 ai-code 直接使用 **A2**，无需记录 A1，也无需把 A1/A2 分组给服务器。

### 11.4 什么时候出现 POST create + GET retrieve，以及 exchange 的实际边界

这是 **OpenAI Responses 的 continuation/background 轮询**，不是 SDK retry，也不是 Chat Completions 或 Anthropic 的通用行为：

1. Responses create 请求在支持的有状态/background 模式下发送；普通 foreground 或 stateless 请求不进入该流程。
2. provider 返回尚未完成的响应，客户端解析出 `continuation_token`（其中含 response ID）。典型状态是 in_progress。
3. Kernel 保留该 token，按间隔再次调用 `_call()`。
4. Responses client 见到 continuation token 后调用 `retrieve(response_id)`，产生 GET attempt。
5. 若仍为 pending，则继续 retrieve；直到最终响应不再有 continuation token。

**2026-11-16 源码复核纠正**：当前 `_call()` 每次都执行 `begin_exchange()`，而每轮非流式/流式响应后会先 `close_exchange()` 再检查 continuation token。因此正常多轮 poll 的 exchange 并不共享：

```text
exchange E1
  └─ attempt A1 → POST create，返回 in_progress + continuation token
exchange E2
  └─ attempt A2 → GET retrieve，仍 in_progress
exchange E3
  └─ attempt A3 → GET retrieve，返回最终响应
```

这里 A2/A3 是应用层轮询，不是 SDK 对失败请求的 retry。create 或 retrieve 内部仍可能各自发生 SDK retry：该 poll 内 E 不变、A 增加；下一 poll 则新建 E。若调用开始时就已有 continuation token，也可以只有 GET retrieve，而没有本次 POST create。

当前测试 `test_continuation_token_is_polled_to_terminal_inside_logical_call` 锚定了外层 wire logical call 内轮询到终态，但其名称中的 logical call **不表示共享 exchange**。`test_background_continuation_retrieves_and_preserves_pending_token` 锚定 pending token 的 retrieve 行为。

对当前“只关联最终成功响应”的需求，最终 message 同时属于 E3/A3；使用 A-final 直接关联不受此前 exchange 分组误记影响。若未来要求用同一 E 分组整个 create/retrieve 周期，则需要另改上游 exchange 生命周期，单靠 exchange header 无法实现。

### 11.5 最终 attempt 作为主键的服务器前提与影响

采用 A-final 后，推荐关联变为：

```text
最终成功 HTTP 响应 raw A-final
  → assistant message._chrys_request_attempt_id = raw A-final
  → 客户端独立报告、工具、ai-code 的出站 requestId = UUID(raw A-final)
  → 后台原成功记录读取 raw header，保存 requestId/关联键 = UUID(raw A-final)
```

唯一关键服务器前提是：**每次模型调用请求的记录必须保存该次请求自身的 raw attempt ID（经统一规则转外部 UUID）**。服务器不判定哪次请求"实际成功"——成功语义由客户端独立 LLM 报告声明：报告携带 A-final 的外部 UUID，以 join 命中的那条记录为该逻辑调用的成功记录。如果原记录在 Responses create A1 时建立、最终响应来自 retrieve A3，只要 create 与 retrieve 各存自身 attempt 且报告带 UUID(A3)，join 即命中 A3 记录；服务器无需理解 create/retrieve 语义。

该前提比“服务器对全部 attempts 分组”小得多：每条记录与自身 attempt 的确定性 UUID 一致即可。无需新增 exchange header，无需上传全部 attempts，也无需恢复失败 attempt 数据。若正常成功 message 缺少 A-final，则跳过该条并记录原因；责任人已明确不允许 exchange 混填兜底。

2026-11-16 B1 回答确认 0.28.0 从 body `telemetry.requestId` 取值且服务器不重新生成，新版可改为读取当前请求的 attempt header。**2026-11-18 责任人修订（BR-1）**：服务器侧无法可靠判定"实际成功请求"（200+业务错误、流中断、Responses pending 均需理解模型 API 业务语义），此前"服务器保存实际成功响应的 A-final"的表述由"每请求存自身 attempt + 独立报告 join 声明成功"取代，后台义务减轻；B1 回答中"最终被成功遥测选用的记录保存该次成功响应的 A-final"应按此修订理解。

2026-11-17 的归一化安排曾取代“客户端生成点 UUID、服务器原值透传”暂行建议（两者又均由 2026-11-18 原值裁决取代——所有 ID 原值直用、无转换）。

此分支已取代 2026-11-14 的“逻辑 exchange 为主 requestId”作为当前暂定方向：

1. 当前：最终成功 raw attempt 为内部主 ID，服务器与客户端外部记录统一保存 UUID(A-final)，取消 C1/C2 的额外关联负担；
2. 开发期回退备选：exchange 主 ID，届时再重评 C1/C2；缺少 A-final 时不在当前分支内混用 E。

### 11.6 客户端实际上报的是最终 attempt，流式也一样

当前 `WireCall` 对两种响应形态都在最终响应上执行 `_stamp_request`：

- **非流式**：在 request scope 中 await 最终 response，然后把当前 `RequestTracking.request_attempt_id` 写到 response 和本次新产生 messages 的 additional_properties。
- **流式**：把 request scope 绑定到 stream 的 pull 生命周期，并注册 final-result hook；最终响应完成时同样执行 `_stamp_request`。每个 chunk 不生成新 attempt，只有真实 HTTP retry/redirect 才生成新 attempt。

因此 session analyzer 在正常成功路径读取到的是：

```text
最终 response / stream final result
  → response.additional_properties.request_attempt_id = raw A-final
  → 新 assistant message._chrys_request_attempt_id = raw A-final
  → session.json 持久化该 raw message metadata
  → after_turn 工具/ai-code 出站上报 requestId = UUID(raw A-final)
```

已有 E1 定向测试对 `stream=False/True` 两种形态都验证了：第一次 429、第二次成功时，最终 response 和 message 的 attempt 都等于实际发送列表的 `sent[-1]`，不是第一次失败 attempt；该测试已随 10 项定向测试通过。

Responses 若经历 create/retrieve 轮询，最终 result hook 使用返回最终结果的那次 attempt：上述例子中为最后一次 retrieve A3；若没有轮询、create 直接返回最终响应，则为 A1。流式 Responses 仍按 stream 最终结果 stamp，不为每个 chunk 或每个中间 pending 状态生成业务 requestId。

流式中途失败或取消、没有最终成功 message 时，按“只记录成功模型调用”的新假设不生成对应工具/ai-code 主关联，不回退到部分流的 attempt。若未来要求恢复部分流或逐 chunk 来源，则属于新增需求；A-final 只标识最终结果所在的 HTTP attempt，不表达每个 chunk 的独立来源，但这不影响当前工具/ai-code 关联需求。

责任人已明确：只要客户端以实际最终成功响应的 raw A-final 标识上报，服务器就能正确保存对应记录（2026-11-18 原值裁决后即原值直存）。因此在“最终成功 attempt 主 ID”分支下，服务器侧记录保存该 ID 的前提可满足，不再构成客户端新增 exchange header 的理由。

## 12. attempt-first 后回退 exchange 的成本与可逆性约束

> 结论：**向前切换的成本可以较低，历史数据迁移不是免费的。**关键是 attempt-first 只改变外部 requestId 的选择，不把内部分析模型也缩减成 attempt-only。

### 12.1 哪些部分不需要返工

当前 after_turn 方案本来就需要同时理解 E 和 A-final：E 用于 session/trajectory/tool operation 的内部 join，A-final 用于定位实际成功响应。因此从外部主键 A-final 回退到 E 时，以下主体可复用：

- N3 after_turn 触发和 N4 全 session 目录联读；
- 普通工具 T/C→M、ai-code mutation→T→M 的关联分析；
- retry、Responses、流式中定位最终 M 的逻辑；
- 成功、拒绝、失败和缺失降级规则；
- 工具、ai-code、独立报告、ACP 的报文主体，只替换身份值和格式。

真正变化集中在 N1 传输/服务器关联：attempt-first 不需要 exchange header；回退 E 后仍需在 C1 或 C2 中选一条。

### 12.2 不同阶段的相对成本

| 回退时点 | 客户端成本 | 服务器/数据成本 | 相对判断 |
|---|---|---|---|
| 探索或实现初期，尚未真实上报 | 调整外部键选择和 golden fixtures；内部分析不变 | 修改未上线契约 | **低** |
| 客户端已实现但尚未发布 | 保留双 ID 时主要是单点切换；C1 仍增加两处集中 header 接缝，或 C2 增加映射字段 | 联调 E 的持久化和合并规则 | **低至中** |
| 已发布且已产生 A 主键数据 | 客户端可切换，但需双协议/灰度与兼容测试 | 同时理解历史 A 和新 E；服务器查询、去重、合并需兼容 | **中至高** |
| 要求把历史 A 数据全部改成 E | 需要历史 E↔A 映射；当前任务又不做历史 replay | attempt-first 原请求没有 E header时，服务器不能自行反推历史 E | **可能无法完整做到** |

因此不能用“客户端只改一个字段”概括上线后的全部成本；服务器和历史数据才是主要成本来源。

### 12.3 回退时的两条通道

- **C1 exchange header**：增加常量与共用 prepared hook 两处集中接缝，原请求和独立报告直接按 E 关联。客户端小改、服务器逻辑直接，但重新引入最小上游定制。
- **C2 attempt 映射**：不新增原请求 header，独立报告携带 E 与 A-final/attempt 映射，服务器按已落库 A 找原记录。客户端传输改动小，但服务器映射和 Responses 匹配规则比 C1 多。

回退并不自动意味着 C1；仍需按当时问题选择。若问题就是服务器无法可靠保存/匹配 A-final，C2 仍依赖 A，可能不合适，C1 更稳。

### 12.4 为保持低成本，实施时应遵守的可逆性约束

1. 内部身份对象同时保留 `exchange_id` 和 `final_attempt_id`，不在 analyzer 入口提前丢弃 E。
2. 内部关联继续使用 E/T/M 等稳定关系；**外部 requestId 选择集中在一个小函数/策略中**，不让 tool-detail、ai-code、ACP 各自硬编码 A。
3. 同一份 golden session fixture 至少验证两种外部键选择，确保切换不会改变工具/代码归属。
4. 若服务器愿意增加可选诊断字段，独立报告可同时携带 exchangeId 以保留未来 C2 映射证据；这不是 C1 的替代品，也不是当前必须项，需避免无需求扩展协议。
5. 服务器若要求上线后回退，应支持 A/E 双键过渡或明确只读新数据；不能假设历史 A 自动转换为 E。

**建议**：可以采用 attempt-first，不必因未来可能回退而放弃其零新增 header 优势；但应把“双 ID 内部保留、外部键单点选择”列为实施 design 的可逆性要求。这样未上线回退成本低，上线后也能把额外工作限制在传输和服务器兼容层。

责任人进一步明确：**只会在开发期发现严重问题后回退，不会等上线后才回退**。因此当前决策只需计入开发期低成本回退；上线后双键迁移和历史数据改写不是本方案需要承担的场景，仍保留上述说明仅为解释边界。

## 13. 失败场景的 E/A 记录与 attempt-only 开发期验证

### 13.1 `session.json` 是否记录失败调用的 E/A

通常不会为失败的本次模型调用生成新的最终 assistant message，因此 **`session.json` 没有“本次失败调用”的 E/A message metadata**。它可能仍有历史成功 message 的 E/A，那些属于旧调用，不能当成本次失败调用。

必须区分“模型失败”和“模型成功后的其他失败”：

| 场景 | `session.json` 中本次 E/A | 整个 session 目录/trajectory | attempt-first 处理 |
|---|---|---|---|
| prepared 前失败（如客户端/middleware 提前异常） | 无新 message，故无本次 E/A | 可有 E started/finished；没有 prepared A | 不上报失败模型遥测；不错用旧 A |
| HTTP 请求或 SDK retry 全部失败 | 无最终成功 message | 通常有 E；每个已 prepared HTTP 请求各有 A，可能有 status/error | 失败 A 不作为成功 requestId；不上报 |
| Responses create/retrieve pending 后失败 | 无最终成功 message | 每轮 poll 可有独立 E 和各自 A | pending/failed A 都不是 A-final；不上报 |
| 流式已有部分 chunks 后失败/取消 | 没有本次最终成功 message；历史中可能有旧 message | 可有 E、已 prepared A、部分流/失败事件 | 不把部分流当成功，不使用旧 message A |
| 前一次模型成功、本次模型失败 | **只有前一次的 E/A，没有本次的** | 本次 E/A 事件与旧 message 分开 | 关键防错：不得从 session-latest 取前次 A |
| 模型成功产出 function_call，随后工具失败 | **有成功 message 的 E 和 A-final** | 另有工具失败终态 | 工具仍关联 A-final，工具 outcome=failure；模型成功不因工具失败被抹去 |
| 模型成功并完成代码修改，之后 turn 其他步骤失败 | 有该成功 message 的 E/A-final | 后续失败另行记录 | 已产生且满足 N6 条件的 ai-code 仍可关联 A-final；不能因整个 turn 失败改写模型响应事实 |

trajectory 本身也可能关闭、缺段或保存失败，此时不能声称整个 session 目录必有 E/A。失败场景中是否有 prepared A 取决于失败时点，不能用 exchange 事件反推出必然存在 HTTP attempt。

### 13.2 对 attempt-only 可行性的影响

在“只上报成功模型调用”的需求下，**失败调用没有 A-final 是预期，不是 attempt-only 缺陷**。开发期需要拦截的严重问题是：

1. 正常成功响应没有正确 A-final，或服务器成功记录保存了不同 A；
2. SDK retry、Responses retrieve、流式完成后取到中间/失败 A，而非最终 A；
3. 本次失败后误用历史成功 message 的 A，造成跨调用错关联；
4. 工具或 ai-code 无法从成功 M 定位 A-final；
5. 模型成功、工具失败时被错误跳过或错挂到后续 exchange。

只要成功路径的 A-final 稳定、服务器记录一致，失败路径不上报且不借用旧 A，就不存在需要因此回退 exchange 的方向性阻塞。

### 13.3 开发期最小验证矩阵

| 样本 | 必须观察 | 严重失败判据 |
|---|---|---|
| 前次成功 → 本次 prepared 前失败 | 本次无新 M；即使目录有 E 也无 A | 上报使用旧 A 或伪造本次 A |
| SDK 多次 retry 后全部失败 | E 下多个失败 A；无成功 M | 把最后一个失败 A 当成功 requestId |
| SDK retry 后成功 | 最终 M 的 A=sent[-1] | 使用 A1 或 exchange/attempt 混填 |
| Responses pending 后失败 | 有 create/retrieve A，无最终 M | 把 create/pending retrieve 当成功 |
| Responses pending 后成功 | 最终 M 的 A=最后响应 attempt | 固定使用 create A |
| 非流式/流式部分输出后失败 | 无最终成功 M | 上报部分流并关联旧 A |
| 外层 wire retry 失败后成功 | 旧 E/A 与新 E/A 分开，最终 M 属于新调用 | 使用旧 exchange 的旧 attempt |
| 模型成功 → 工具失败/代码修改失败 | 成功 M 的 A-final 保留；工具/ai-code 按各自 outcome 规则 | 因 turn 未完全成功而错挂或误报 ai-code |

这些是新 analyzer/服务器联调的开发期验收样本，不表示当前已经实现或通过。任一成功主路径无法满足 A-final 一致性，或失败路径持续产生跨调用错关联，才应暂停 attempt-only 并重评 exchange；普通失败场景没有 A-final 本身不触发回退。

### 13.4 失败、retry、create/retrieve 中二者标识能力并不一致

- 最终失败时，E 可标识失败的逻辑调用，A 只标识各失败 HTTP attempt；二者都不是“成功调用 ID”。
- prepared 前失败可有 E 而没有 A，直接证明可得性和标识范围不同。
- SDK retry 中一个 E 可对应多个 A；Responses continuation 则每次 poll 新建 E 和 A，两种机制不能混为一谈。
- retry 最终成功时，E 标识整个逻辑调用；Responses 最终成功时，E-final 只标识最后一次 poll，不再误称它覆盖整个 create/retrieve 周期。最终 A 始终标识实际成功响应。
- 只有在“只关联成功响应”的需求下，E-final/A-final 才都可能充当外部关联键，且 A 更直接。
- 因此当前 attempt-first 的依据不是“失败时二者一致”，而是“失败/中间态不上报，成功时使用最终 A；E 留作内部关联和开发期回退证据”。

## 14. 流式场景中 exchange/attempt 的适用性

### 14.1 正常流式：两者都适用，但 A 不能单独证明成功

正常流式时间线：

```text
begin_exchange → E1
prepared HTTP stream → A1
收到响应头/多个 chunks → A1 不变
stream final result 成功 → 最终 response/message stamp A1
exchange finished=success → E1 记录最终 outcome
session 保存 M(E1,A1) → after_turn 分析工具/ai-code
```

- E1 标识逻辑调用，并通过 exchange finished 表达最终 outcome。
- A1 标识承载最终结果的 HTTP 流，适合作为服务器直接关联键。
- **A1 的 prepared 或 200 响应头只说明请求/流已开始，不说明流成功完成。**attempt-first 必须以最终成功 message 为证据，不能只看到 A 就上报。

**block/chunk 不等于 continuation poll**：

| 事件 | 是否新建 HTTP 请求 | E/A 是否改变 |
|---|---|---|
| 同一 stream 收到一个文本/工具 block 或 SSE chunk | 否 | 不变 |
| 当前 create/retrieve 的 HTTP 响应或 stream 结束 | 当前请求已结束 | 当前 E 会关闭，A 已是本请求固定值 |
| 响应仍 pending，continuation loop 发起下一次 retrieve poll | **是** | 新建 E/A |
| 当前 poll 内部发生 SDK retry | 是，但属于同一 poll | E 不变，A 新建 |

普通流式可以是 `E1/A1 → block1 → block2 → block3 → final`，所有 blocks 共用 E1/A1。Responses 则是 `E1/A1 create 的多个 blocks → pending 结束`、`E2/A2 retrieve 的多个 blocks → pending 结束`、`E3/A3 retrieve 的多个 blocks → final`；是每次 HTTP poll 换 ID，不是每个 block 换 ID。

### 14.2 各流式分支的 ID 变化

| 场景 | exchange | attempt | 成功关联口径 |
|---|---|---|---|
| 普通流式成功 | E1 | A1，chunks 不增加 A | M(E1,A1)，A-final=A1 |
| SDK 在流开始前/响应阶段 retry | E1 不变 | 新 A2 | 最终 M(E1,A2)，不使用失败 A1 |
| mid-stream 失败后允许 Chrys 外层 retry | 旧 E1=error/stalled，新 E2 | 新 A2 | 旧 updates 从最终组装缓冲清理；最终 M(E2,A2) |
| 已交付答案正文后失败 | E1=error | 旧 A1 | 为避免重复展示，当前代码禁止 replay；无最终成功 M 则不上报 |
| 已有 provider-hosted 工作且不能安全 replay | 旧 E 失败关闭 | 旧 A | 当前可 veto retry；不能把 provider 已执行工作冒充新的本地成功响应 |
| Responses 流式 continuation | 每次 poll 新 E | 每次 poll 新 A | 最终 M 属于最后 poll 的 E-final/A-final |
| 流式取消/失败且无 retry 成功 | E 记录 cancelled/error/stalled | 可有 A，但不是成功 A-final | 无最终成功 M，不上报 |
| 两个并发流 | 各自 E | 各自 A | request scope 必须隔离，不能用 session-latest |

mid-stream retry 的“清理”仅针对最终组装所用的缓冲 updates；已经 yield 给消费者的更新不能收回，协议用 retry boundary 标记重启。telemetry 应从最终落地 M 取工具/代码来源，不从已展示的中间 chunk 取。

### 14.3 适用性结论

- **attempt 适用于流式成功响应的外部 requestId**：最终 result hook 会把最后 HTTP attempt 写入新 message，普通、SDK retry、外层 retry、Responses 最终 poll 都遵循这一方向。
- **exchange 适用于流式内部分组和 outcome 判断**：尤其用于区分失败旧流与重试新流，避免跨调用错关联。
- 二者都不提供逐 chunk 唯一标识，也不应在流式失败后为“成功调用上报”创造 ID。
- 因此当前最稳妥的分工仍是：**内部用 E 定位本次成功响应及其边界，外部 requestId 选最终 A**；不是仅凭 attempt 存在或 HTTP 200 判断成功。

### 14.4 已运行行为锚定与开发期剩余验证

本轮实际执行以下现有测试节点：

- `test_sdk_retry_and_stream_keep_request_scope`（stream=False/True）；
- `test_continuation_token_is_polled_to_terminal_inside_logical_call`（stream=False/True）；
- `test_a_retry_before_any_text_emits_a_boundary_before_the_fresh_attempt`；
- `test_abandoned_close_never_finalizes_partial_updates_via_cleanup_hooks`。

结果：收集 6 项，`6 passed in 8.27s`，退出 0。它们证明当前最终 attempt、continuation、部分流重试清理和 abandoned close 行为，**不证明新 analyzer 或服务器 A-final 联调已完成**。

开发期仍需组合验证：流式 retry 后最终 M 的 E/A 与新工具/ai-code 一致；Responses 流式多 poll 后使用最后 E/A；200 后中途失败不上报；前次成功后续流失败不借旧 A；并发流不串号；save=False/保存失败不读旧 session。任一成功主路径无法满足这些条件，才构成 attempt-first 的严重问题。

### 14.5 continuation 何时发生，是否小概率

触发的直接条件是：**OpenAI Responses 返回 `queued` 或 `in_progress`，并且当前存储/变体规则允许由 response ID 生成 continuation token。**客户端随后才通过 retrieve 轮询。

前置路径需要拆开：

- Chat Completions、Anthropic 不走 Responses continuation。
- DeepSeek Responses 当前变体是 stateless，明确拒绝 background/continuation，不走该路径。
- OpenAI Responses `STORES_BY_DEFAULT=True` 只表示默认可使用服务端存储和历史 handle，**不表示自动设置 background=True**。
- 普通 foreground Responses 若直接返回 completed/incomplete/failed 等终态，没有 continuation token，不轮询。
- 有效配置启用 background，或已经持有 continuation token 时，才会进入相应的后台创建/恢复路径；provider 尚未完成时就返回 running 状态并轮询。
- 流式中途获得 token 后断连，也可用 retrieve 恢复同一 provider response；这属于恢复路径，不是 chunk 导致的新 poll。

**是否小概率不能从代码或单元测试判断**：

- 在实际不使用 OpenAI Responses、禁用 background 或使用 stateless 变体的环境中，可以是从不发生。
- 在明确启用 background 的长任务/托管工具场景中，pending + retrieve 是正常的完成机制，可能是该模式的常见路径，而不是异常。
- 总体比例取决于实际模型 profile、provider 是否支持、任务时长和负载；当前没有生产统计或真实 provider 样本，不能给出“小概率”结论。现有 pending 测试只证明机制，不证明频率。

开发期可用 mock 强制 pending 验证正确性，再用实际目标 profile 做小规模样本，记录 Responses 调用数、带 continuation token 的调用数、每次 poll 数和最终状态。频率只影响性能和样本优先级，不影响 A-final 关联必须正确的原则。
