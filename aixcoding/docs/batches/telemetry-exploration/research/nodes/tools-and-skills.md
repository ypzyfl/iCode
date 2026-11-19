# N5：工具与技能的 exchange/attempt 关联及协议覆盖

> 技术判断：**大方向条件可行，不阻塞 after_turn + session 目录联读。**普通工具和 `load_skill` 可关联正确的 exchange 及实际返回 function_call 的 attempt；slash skill 是输入触发，只关联 pass，不应伪造 exchange/attempt。
>
> 决策状态：采用持久化精确关联，不恢复 session-latest。旧随机 ID 的服务器兼容要求、slash 的特殊去重和逐字段报文映射留外部契约确认或实施，不要求责任人现在裁决。
>
> 范围补充：本文的普通工具链适用于本地真实 function_call。**provider-hosted、local/外部 ACP sub-agent、shell/background、普通 command 和 selected Agent 的分类结论见 [广义调用覆盖](broad-tool-coverage.md)**；外部 ACP 内部工具不能套用本文 E/A 链。
>
> **2026-11-18 ID 原值裁决**：funcId 等全部 ID 保持原值 32hex、不转 UUID（`funcId=T 原值` 而非 `UUID(T)`）；本文中 UUID 形态表述按原值理解，批次1 design 时统一重写。权威口径见 `../backend-change-requests.md` BR-5。

## 1. 工具唯一身份与 A-final 是两个不同问题

工具上报必须先区分“唯一标识哪一次工具执行”和“该执行由哪次成功模型响应产生”。A-final 只回答后者；同一 assistant message 中的多个工具会共享 A-final，仍需各自的工具调用身份。

| 角色 | 当前字段与持久化 | 唯一性和用途 |
|---|---|---|
| **C：call item ID** | function_call 的 `_chrys_analytics_item_id`；`tool.operation.started.payload.call_item_id` | occurrence 级身份，是 T→具体 function_call 的首选键 |
| **T：tool operation ID** | function_call/result 的 `_chrys_operation_id`；tool started/finished 的 `operation_id` | 串联一次本地 dispatch 的 call、result 和生命周期事件；同一响应中重复且未解决的 provider `call_id` 可共享 T，不能单独消除所有重复歧义 |
| **provider call_id** | `function_call.call_id`、对应 `function_result.call_id` | 模型/provider 给出的调用 ID，是旧 funcId 的来源之一；可跨响应或在同一响应重复，不能作为全局或 session 内唯一键 |
| **当前 UI `_chrys_call_id`** | 运行时 12hex，供 UI/hooks/审批等使用 | 不保证持久化到 session，不能作为 after_turn 的稳定主关联键 |
| **E：model exchange ID** | M 的 `_chrys_operation_id`；T 的 `parent_model_operation_id` | 内部父级归属和成功 terminal 校验；一个 E 可有多条 M，不能单独定位具体 function_call |
| **A-final** | M 的 `_chrys_request_attempt_id` | 当前暂定的外部模型 requestId；不是工具唯一 ID，同 M 多工具共享 |

旧后台 funcId 是**上报契约字段**，不应与上述内部 ID 混为一谈：若它只用于 save/update 匹配，可从 T 派生新的稳定值；若必须等于 provider call_id，则保留原值并由服务器明确重复 ID 的消歧规则。客户端内部关联无论选择哪种 funcId，都优先使用 C，再用 T/E 交叉校验。

### 主链：经 session assistant message

```text
tool.operation.started.operation_id = T
tool.operation.started.payload.call_item_id = C
  → function_call._chrys_analytics_item_id = C
  → function_call 属于 M.contents
  → M._chrys_operation_id = E
  → M._chrys_request_attempt_id = A-final

交叉校验：
function_call/result._chrys_operation_id = T
T.parent_model_operation_id = M._chrys_operation_id = E
```

function_result 与 function_call 通常共享 `T`，tool started/finished 也共享 `T`。attempt 只盖在新返回的 message 包装层，不在 content 上，因此不能直接读 function_call 的 additional_properties 代替 M。`parent_model_operation_id` 只表示 E 归属，不能代替 C 定位具体 M。

### 备用链：经成功 exchange terminal

```text
tool.operation.started.parent_model_operation_id = E
  → model.exchange.finished[operation_id=E].payload.request_attempt_id = A-final
```

`model.exchange.finished` 从 landed response 提取 `request_attempt_id`。两条链可互相校验，不需要给 tool operation 新增 attempt 字段。若 M 和成功 terminal 都不能确认 A-final，则按当前裁决跳过该条并记录原因，不用 E 混填，也不取 `attempts[-1]`。

### `session.json` 与整个 session 目录分别能证明什么

- **仅 `session.json`**：正常新记录通常已有 provider call_id、C/T、function_call 与 M 的包含关系、M 的 E/A-final，因此核心消息侧关联存在；但不能独立证明完整 tool started/finished、`call_item_id` 对照、终态/耗时、exchange 成功过程和全部 retry 历史。
- **整个 session 目录**：联读 `trajectory/events.jsonl` 后才能完成 T→C→M→A-final 及 outcome/timing 校验；ai-code 还需 mutation/blob，local child 内部消息还需 child audit。
- trajectory 是 best-effort，保存失败、写入 gap、旧记录缺 metadata 或 run 回滚后，不能把残留事件按 provider call_id/消息顺序拼到新调用；证据不足就跳过或降级。

## 2. attempt 的正确语义

| 场景 | 工具应关联的 attempt |
|---|---|
| SDK retry | 返回 function_call 的成功 attempt，不是此前 429/503 |
| redirect | 返回最终响应的 hop，不是中间 307 |
| Responses create 直接完成 | 最终 create attempt |
| Responses create 后轮询 | **返回 function_call 的 retrieve GET，不是最初 create POST** |
| Chrys wire retry | 最终成功 exchange 的响应 attempt，不属于之前失败 exchange |
| 工具执行期间取消 | assistant 已保存的 A 不变，仍指向产生调用的模型响应 |
| 模型响应未落地 | 没有已产生的 function_call，不存在工具到生产 attempt 的关联 |

`turn_trace.modelCalls[].attempts` 只列出全部 attempts，不能单独指出生产 function_call 的 A。若 session message 和成功 exchange terminal 都不能确认 A-final，必须跳过该条并记录原因，**不能简单取 attempts[-1]或用 E 混填**。

`llm_raw_http.jsonl.exchange_id` 实际存的是 request attempt ID，不是 model exchange E；只能作为 A 的辅助对照。

## 3. trajectory 降级时的边界

| 剩余证据 | 能否恢复 E/A-final |
|---|---|
| function_call 所在 M 仍有 operation/attempt | 可以确认消息侧 E/A-final；完整工具 outcome/timing 仍需 tool events |
| M 缺 attempt，但成功 exchange terminal 有 A 且工具 parent E 存在 | 可由成功 landed response 的 terminal 补证 A-final |
| 只有单 attempt，但没有 M/成功 terminal 证明 | 不能仅凭唯一候选认定它是最终成功 A；跳过并记录原因 |
| 多 attempt，M 和成功 terminal 都缺 A | 不可精确恢复，跳过并记录原因，不取 attempts[-1] |
| 失败 exchange 没有 landed response | 没有工具生产 attempt；不能拿失败前任意 prepared attempt 冒充 |

完整“工具→call→message→attempt→raw HTTP”的单一样本，以及 Responses retrieve 专项断言，留实施期补测；现有测试已分别锚定各段行为。

## 4. 工具协议字段的大方向覆盖

| 字段/能力 | 文件恢复与处理 |
|---|---|
| provider `funcId` | `function_call.call_id` 可恢复但不保证唯一；端侧优先以 C/call_item_id 定位，T/E 交叉校验，不靠 ID 或消息顺序猜位置 |
| 内部 12 位 fallback ID | 旧随机原值通常不可恢复；可从 T 派生新的稳定 fallback，贯穿 save/update，但不能称为恢复原值 |
| requestId | 内部与出站均使用产生 function_call 的 M 的 raw A-final 原值（32hex，无转换），与其他外部记录同文本；缺 A 跳过 |
| 生产 attempt | 就是当前 requestId 的来源；同一 M 的多个工具共享 A-final，由 funcId/T/C 区分工具实例 |
| 根 `spanId` | 当前对话 turn ID；同一 turn 的模型和工具共用。旧版曾由 session_id + 当前 pass turn_id 确定性派生 |
| `parentSpanId` | 仅真实存在父子对话关系时填写直接父 turn ID；普通独立 turn 不传，不从 E/A/T、provider call_id 或时间上一轮派生 |
| 工具参数 | session function_call；trajectory 只有指纹 |
| 审批修改参数 | modified_args 写回 function_call，可恢复 |
| 其他 hook 最终参数 | `_exec_stamp.effective_args` 通常可用，2048 字符截断时降级 |
| 结果/错误 | session function_result 与持久化错误元数据；旧成功 tool-detail 不要求结果正文 |
| 起止时间/耗时（已移除） | 新版所有工具记录均不包含 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`；现有 occurred_at/duration_ms 不再用于出站，不发送 null/0，也不补采 |
| 文件路径 | 从最终可用参数按旧 fileName 口径生成；无 workspace 不用进程 cwd 猜测 |

**旧 `tool-detail` 最终代码不包含 `reportId`；`reportId` 属于 ai-code/save。**旧 mock 的最低校验不能证明真实服务器全部兼容要求。

B4 已关闭 parentSpanId 的概念映射：它表示真实直接父 turn，不要求恢复旧随机 llmSpanId，也不从内部模型/工具 ID 派生。重复 provider funcId 的服务器去重语义已由单次 final save 和 `(requestId,funcId)` 原子幂等目标契约解决，后台实现仍需联调验收。

## 5. 工具状态映射

| 当前事实 | 旧协议处理方向 |
|---|---|
| success | codeStatus=1 |
| failed / errored | codeStatus=2，failureType=error |
| timed_out | codeStatus=2，failureType=timeout |
| rejected | codeStatus=4 |
| interrupted | 旧版没有已验证的取消终态上报路径；保持降级或待协议扩展，不伪报普通失败 |
| started 无 finished | 不完整/unknown，不自行编造终态 |

状态映射、旧 iCode 超集字段的后台容忍度和取消协议属于实施/后台契约事项，不影响正常 success/failure/rejected 的大方向覆盖。

## 6. `load_skill`：普通工具 + 额外技能使用记录

`load_skill` 与普通工具使用同一条 E/A 关联链，并有额外的技能上下文：

- tool operation 提供 parent exchange、call_item_id 和技能上下文；
- `tool_context` 可恢复规范技能名和 revision，未命中时只保留请求名；
- 原始参数/结果仍从 session 获取；
- 额外技能使用记录应以 `tool.operation.started` 存在为证据，避免把审批前取消或未实际开始的 function_call 误报为旧 on_start 技能使用。

旧版一次 load_skill 同时产生：

1. 工具维度 `funcType=3` save/update；
2. 技能使用维度 `funcType=0` 的单条 save，不带 funcId，带产生 `load_skill` 调用的 A-final requestId 和当前 logical turn 的 spanId。

两者不能用同一个 funcId 把技能使用误当成另一次工具 update。

## 7. slash skill：输入触发，不带 exchange/attempt

slash skill 与 load_skill 不是同一种关联模型：

- 它在模型调用前由用户输入触发；
- 旧契约只发一条 `funcType=0` save，无 update、无 funcId；
- **requestId 始终省略，也不存在生产该输入的 request_attempt_id**；
- 只用当前 logical turn 的 spanId 关联。

因此不能要求 slash 也关联 E/A，更不能拿本轮第一次模型调用的 ID 回填。旧实现通过 session-latest 取 span 是缺陷，可能错挂上一轮；新版按 B4 从当前真实 logical turn ID 转换为 UUID，不能用 retry pass ID 或旧 uuid5 公式代替。

当前持久化证据包括原始用户消息、resolved Skill Reference reminder、turn.started.opening_item_id 等。需要注意：

- 只出现 `/xxx` 文本不代表命中已加载技能，不能直接上报；
- reminder 会在后续请求和压缩中重放，不能每看到一个 exchange 就重复记一次技能使用；
- 普通输入、mid-turn injection 和 retry 的 opening_item→turn/pass 唯一映射若不足，可在输入解析点局部补采 `session_id + logical_turn_id + pass_turn_id + opening_item_id + skill_name`；spanId 取 logical turn，pass 仅用于执行证据隔离；
- 无法唯一确定时标 unknown，不回退 session-latest。

这属于局部输入归属与去重问题，不影响 load_skill 和普通工具的主关联链，也不要求恢复全量实时事件挂点。

## 8. 大方向结论与暂缓项

继续采用持久化精确关联：

- 普通工具/load_skill：以 `T.call_item_id=C → C 所在 M → A-final` 为主，T/E 交叉校验，或由 E 的成功 terminal 补证 A-final；
- ai-code 后续沿用 `mutation → T → C/M → A-final`；
- slash：只关联当前 logical turn/span，并用 pass/opening_item 隔离执行证据，不伪造 E/A；
- 工具字段缺失按 unknown/降级；缺 A-final 则跳过该条并记录原因，不按消息顺序、attempts[-1]、session-latest 或 exchange 混填。

### 当前调查与实施期调查的边界（责任人已指示按建议顺序调查）

划分标准是：该问题是否可能推翻 after_turn + 全 session 联读，或引入新的运行时接缝、后台协议和外部 Agent 协作。只影响关联算法、字段映射和测试覆盖率的事项不提前展开。

**顺序调查执行状态：**

1. **funcId 及相关服务器契约**：普通本地工具 funcId=T 原值（2026-11-18 原值裁决）、单次 final save、组合原子幂等及 B4 turn/parent turn 语义均已确认；BR-8 providerCallId 已于 2026-11-19 责任人裁决撤销（协议通用性，对账端侧完成）。B5/P2 已确认三个执行时间字段全部去掉，不再评估 hosted 时间容忍度。
2. **特殊调用的保真级别**：外部 ACP 和 provider-hosted 已完成逐字段对照；hosted 时间字段已全部移除且不补采，外部 ACP 内部保真边界详见 `broad-tool-coverage.md` 第 9 节。
3. **最小主链与孤儿事件判别样本**：普通工具成功主链和真实 rollback 负例已完成，最终 2 passed；实验见 `../experiments/tool-identity.md`，不提前建设完整 analyzer。

**只有要求完整保真或修正旧缺陷时才需提前调查：**

- hook 改写后的最终参数必须完整时，需现在评估新捕获接缝；接受截断降级则留实施。
- cancelled 必须准确上报时，需现在确认后台协议扩展；只对齐旧契约并登记差异则留实施。
- slash 必须保证跨 retry/compaction 恰好一次时，需现在验证 opening_item→pass 映射；接受降级则留实施。

**留到具体实现：**

- 同一 M 多工具的常规组包、UUID(T) 派生和单次 final save/原子幂等；B8 最小 DTO 已是暂行契约，不再按 save/update 两阶段设计；
- SDK retry、redirect、Responses retrieve、外层 retry、并发/多 child 的完整异常矩阵和压力测试；
- 工具参数字段级映射、取消状态详细映射、行数计算和旧报文 golden parity；三个执行时间字段不再计算；
- 完整 mock、故障注入和 Responses 专项端到端覆盖。

## 9. 证据与行为锚定

关键源码：

- `foundation/trajectory/tools.py`：tool operation、parent exchange、call_item_id、状态与耗时；
- `kernel/loop.py`、`foundation/trajectory/metadata.py`：assistant/tool operation/item ID；
- `service/llm/observer.py:219-234,477-493`：成功 exchange/assistant message 的生产 attempt；
- `service/llm/request_tracking.py`：每个 prepared attempt 新 ID；
- `service/skills/provider.py`：技能规范名/revision 上下文；
- `orchestration/engine/run/input_refs.py`、`service/agent_middleware/system_reminder.py`：slash resolved reminder；
- 旧副本 `telemetry/reporters/tool_detail.py:147-276`：工具、load_skill 和 slash 的最终旧契约。

2026-11-14 实际执行：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/service/llm/test_request_tracking.py tests/integration/engine/test_trajectory_events_log.py -n0
```

结果：收集 45 项，`43 passed, 2 skipped in 14.17s`，退出 0。覆盖三协议 request tracking、SDK retry/redirect、assistant attempt、工具 parent exchange 和 call_item_id；skip 为测试自身条件跳过。该结果分别锚定关联链各段，不宣称完整工具→attempt 组合或 Responses retrieve 已专项验证。

2026-11-16 工具身份复核补跑：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/service/session/test_batch_persistence.py::TestPersistBatchIds::test_duplicate_keys_assign_chronologically_never_reversed tests/service/session/test_batch_persistence.py::TestPersistBatchIds::test_multi_call_message_duplicate_same_tool_calls tests/service/session/test_batch_persistence.py::TestPersistBatchIds::test_chrys_uuid_id_never_matches tests/integration/engine/test_trajectory_events_log.py::test_session_items_carry_the_operation_that_produced_them tests/integration/engine/test_trajectory_events_log.py::test_an_executed_call_names_the_item_that_requested_it tests/integration/engine/test_trajectory_events_log.py::test_a_tool_round_records_one_operation_under_its_exchange -n0
```

结果：收集 6 项，`6 passed in 1.64s`，退出 0。锚定重复 provider ID 的分桶行为、UI ID 不作为 provider 匹配键、call/result 共享 operation、`call_item_id` 指向请求项及 tool operation 的 exchange 归属；不证明新 analyzer 的重复 occurrence 组报文已经实现。

## 10. funcId 外部契约与特殊调用顺序调查（2026-11-16）

### funcId 本地证据

旧 CLI 普通工具在 tool-detail save 时取 `provider_call_id or event.call_id`，同一 record 后续复用；Start 先 save+PENDING，终态 final update。旧 save 带 requestId/spanId，update 不带；后台先按 funcName 找记录、再用 funcId 校验，funcId 是 save/update 的关键匹配键。旧 mock 只要求 1–512 字符串，不能证明真实服务器唯一索引或重复消歧。

AIxCoding 桌面侧同样以自身 toolCallId 作为 funcId 查 update，旧 telemetry 设计也把 funcId 定义为工具执行实例 ID。跨端证据不支持“funcId 必须等于 provider call_id”的硬性假设，但真实服务器源码不在本地，最终格式、必填、唯一性/覆盖语义仍需确认。

**当时的 AI 推荐**：每次工具执行使用新的稳定 funcId，贯穿 save/PENDING/final；provider call_id 只用于客户端内部 C/T/M 关联。后续 B2/B3/B6 已确认 UUID(T) 和单次 final save 目标契约，parentSpanId 也已由 B4 明确为真实直接父 turn ID，见第 11.3–11.5 节。

### 特殊调用与最小实验

外部 ACP 和 provider-hosted 的逐字段结论见 `broad-tool-coverage.md` 第 9 节：外部 ACP 内部工具仅保留投影保真边界；hosted 按文件重建业务字段。三个执行时间字段已由责任人明确全部去掉，不再是待裁决建议，也不补采。

普通工具主链和真实 rollback 孤儿拒绝已新增自包含实验 `aixcoding/tests/telemetry/test_tool_identity_persistence.py`，最终 ruff 通过、`2 passed in 4.38s`。详见 `../experiments/tool-identity.md`。

## 11. 工具相关 ID 的角色与建议外部映射

### 11.1 不要把不同层级的 ID 混为一个“工具 ID”

| ID | 回答的问题 | 当前持久化/旧契约角色 | 建议外部用途 |
|---|---|---|---|
| provider `call_id` | 模型/provider 如何命名这次工具调用？ | function_call/result 可保存；旧 funcId 的优先来源，但不保证唯一 | 客户端内部证据；除非后台强制，不直接作为新 funcId |
| C / call item ID | 哪一个 function_call occurrence 实际触发了 dispatch？ | `_chrys_analytics_item_id`；tool.started.call_item_id | 内部 T→C→M 主链，不默认上报 |
| T / tool operation ID | 哪一次本地工具 dispatch？ | 串联 call/result/tool started/finished；PR #69 新增 `mutation.tool_operation_id=T` | 普通本地工具新 funcId 的推荐来源 |
| UI `_chrys_call_id` | 当前 UI/hooks 如何标识卡片？ | 运行时 12hex；可落入 `mutation.tool_call_id`，但不盖到 function_call/result，不能桥接消息 | 不作为 after_turn 主键 |
| M / assistant message | 哪条成功模型响应包含该 function_call？ | session message，保存 E/A-final | requestId 的归属来源，不提供 parent turn |
| E / exchange operation ID | 哪个内部模型 exchange 产生 M？ | M._chrys_operation_id；T.parent_model_operation_id | 仅作内部关联，不作为 parentSpanId 来源 |
| A-final | 哪个实际 HTTP attempt 返回最终成功 M？ | M._chrys_request_attempt_id | 当前暂定 requestId，不是工具执行 ID 或父 turn ID |
| spanId | 记录属于哪一轮对话？ | 当前对话 turn ID；旧版曾由 session_id+turn_id 确定性生成 | 本轮模型和工具共用，不等于 requestId 或 funcId |
| parentSpanId | 当前 turn 是否有真实直接父 turn？ | 旧版工具为 middleware 随机 llmSpanId；新版只表达 turn 间真实父子关系 | 有父 turn 时填其父 ID；普通独立 turn 不传，不从 E/A/T 派生 |

### 11.2 “每次执行新稳定 funcId”的准确含义

“新”是相对旧 `provider_call_id or event.call_id` 的外部取值策略，不是 after_turn 每次重新随机；“稳定”要求同一 tool operation 在 save、PENDING、final 和同一持久化目录重复分析时始终相同。

普通本地工具推荐直接把 T 的 32hex 无损格式化为 UUID 文本作为 funcId，而不是重新 UUID4：

```text
requestId = M.A-final
funcId    = UUID(T)
```

这样不需要新增持久化字段，也不需要 UUID5 再哈希。不同 dispatch 有不同 T；同一 dispatch 的重复分析、PENDING/final 共用 T，自然幂等。工具内部实现若在同一次 dispatch 内重试，不因此产生新的业务 funcId；新的模型 function_call 导致新的 dispatch 时才使用新 T。

同一响应中重复且未解决的 provider call_id 可能让多个 function_call 内容共享一个 T，但它们只触发一次实际 dispatch，所以只应有一个 funcId；C 用来定位实际请求 occurrence，不能为未执行的重复内容再虚构工具执行记录。

### 11.3 为什么推荐执行实例 funcId，而不是继续 provider-first

旧 update 不携带 requestId；责任人已于 2026-11-16 进一步确认真实后台 PENDING/final 都只按 `WHERE func_id = ?` 更新，save 是插入新记录，且不存在 funcId=provider call_id 的其他后台/UI 消费。因此 funcId 必须全局区分执行实例，provider call_id 复用会造成真实错更新风险；UUID(T) 正是合适的全局随机 128-bit 执行实例键，并支持 after_turn 重放稳定性。

B2/B3 已排除 provider 交叉查询和格式障碍：后台接受 36 字符 UUID，不设置唯一索引，完全依赖客户端保证全局唯一；相同 funcId 重复 save 会插入重复行，随后 update 会更新全部重复行。因此 UUID(T) 路线已获契约支持，但稳定 funcId 只保证定位，不保证插入幂等。

B6 已确认 final-only 失败、重复 final 会改字段、final 后 PENDING 会回退终态，且不宜短间隔连续三阶段发送。责任人进一步确认后台可以支持或修改：每工具单次 final snapshot save、`(requestId,funcId)` 原子幂等和重复终态语义。目标契约与验收用例见 `backend-change-requests.md`。

因此新版目标是每次工具执行只发送一个确定性 final save，不发送 PENDING/final update；相同报文可安全重试，由组合键保证不重复插入。相同组合不同内容已确认返回明确冲突；B4 概念语义已关闭，B5/P2 已确认三个执行时间字段全部去掉。后台可修改不等于现网已实现，不做崩溃/强杀补报的客户端边界不变。

### 11.4 spanId/parentSpanId：按对话轮归属，不构造模型/工具父子树

B4 最终澄清：turn 是一轮对话，包含至少一次模型调用和零次或多次工具调用。spanId 是当前对话 turn ID，本轮全部模型和工具记录共用；parentSpanId 只表示当前 turn 的真实直接父 turn ID，用于组织 turn 级 span tree。

```text
独立 turn S0：
  spanId=S0；parentSpanId 不传
  本轮模型 M0：spanId=S0；parentSpanId 不传
  本轮工具 T0：spanId=S0；parentSpanId 不传

真实 child turn S1，直接父 turn 为 S0：
  spanId=S1；parentSpanId=S0
  本轮模型和工具同样使用 spanId=S1、parentSpanId=S0
```

同一 session 的普通对话轮通常彼此独立，时间上的上一轮不是父 turn，因此大多数 parentSpanId 为空/缺省。这是正确语义；只有真实非顶层 turn 缺少直接父 ID 才会破坏树关系并影响统计、筛选或报表。

parentSpanId 不是 E、A-final、T、provider call_id、父模型调用或委派工具 ID，不再存在从这些值中选择或派生父节点的问题。旧版 spanId 的确定性派生只是历史实现背景，不改变上述概念。注意：新版父 turn 语义与 0.28 实际用法（工具 parentSpanId=父模型调用 llmSpanId）不同，记为 parity 显式差异项；当前对话模型为平面 turn、无真实嵌套 turn 场景，父 turn ID 持久化仅将来出现该场景时再验证（2026-11-19 澄清）。

### 11.5 当前已确定与待确定映射

B2/B3 已确认 funcId 的执行实例角色并接受 36 字符 UUID；B4 已确认 turn 归属和真实父 turn 语义，当前映射为：

```text
requestId     = UUID(raw A-final)（内部 raw 32hex，定制出站边界转换，同一成功 M 的相关外部记录同文本）
funcId        = T 原值（每次 dispatch 唯一且确定，32hex）
spanId        = 当前对话 turn ID（本轮模型和工具共用）
parentSpanId  = 真实直接父 turn ID；普通独立 turn 不传，真实非顶层 turn 不应省略
```

新版目标为每工具一个确定性 final save，相同报文可重试并由 `(requestId,funcId)` 原子幂等去重；不同内容已确认返回明确冲突。B4 概念语义已关闭，B5/P2 已确认 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs` 全部去掉且不补采；后台目标能力尚需协调实现，正式实施仍需 design 签认。

### 11.6 普通本地工具 final-save 最小 DTO（2026-11-17 AI 建议）

沿用 `POST /csas/telemetry/api/v1/tool-detail/save`，每次工具执行只发一个终态对象，不新增 final-save 路由，不发 PENDING/final update。

| 字段 | 首版级别 | 规则 |
|---|---|---|
| requestId、funcId | 必填 | 分别为 raw A-final 原值、T 原值（32hex，2026-11-18 原值裁决，无转换） |
| funcName、sessionId、spanId | 必填 | 名称有 call/tool started 证据；session/turn 不用最近值 |
| funcType | 必填 | 本地 MCP=1，其他普通内置工具=3；技能0另走技能记录 |
| codeStatus | 必填 | 只允许终态1成功/2失败或超时/4拒绝；3 PENDING拒绝 |
| parentSpanId | 条件可选 | 仅真实直接父 turn；普通独立 turn 省略 |
| failureType | codeStatus=2 必填 | error/timeout；成功或拒绝不伪造 |
| value | 正常应带，可降级省略 | 最终 modified/effective args；截断且无法恢复时省略并记录 |
| funcErrorMessage | 可选 | 有界持久化错误文本，无可靠正文省略 |
| fileName、行数 | 可选 | 最终路径和真实 before/after；缺证据不猜 |
| agent/channel/project/Git/userId | 待逐字段 parity | 有证据才携带；保留/删除/待确认须显式记录，不能因最小 DTO 静默遗漏 |

BR-8 曾基于"funcId=T 原值后后台失去与模型 toolUseId 等值对账字段"的评审发现，建议报文携带可选 providerCallId；**2026-11-19 责任人裁决撤销**——后台上报协议面向多个 AI 工具，其他工具没有该字段，不为 iCode 特有需求增加协议项；对账在端侧完成（按 funcId=T 在客户端 session/trajectory 反查 provider toolUseId 与工具调用信息），报文不含 providerCallId。

旧 tool-detail 没有 funcResponse，首版成功结果只由 codeStatus=1表达，不上报完整 stdout/result 正文。BR-2 的“成功结果”按终态理解；若将来要求结果正文，必须另立字段、大小和敏感信息契约，不能擅自恢复 funcResponse。

明确不发送：`executionStartedAt`、`executionFinishedAt`、`executionDurationMs`（包括 null/0）、status=0/1、codeStatus=3、reportId、eventTime、funcResponse、PENDING/final update。三个时间字段即使出现也建议 mock 400，而非静默忽略。

mock 使用严格 allowlist和类型校验：requestId/funcId 接受任意 version 的 canonical UUID，不强制 UUID4；funcType/codeStatus 拒绝 bool/float；缺必填、矛盾 failureType、非法终态、时间字段均400。`(requestId,funcId)` 必须有数据库唯一约束或原子等效，不仅先查后插；语义重放200、同键不同内容409、首次记录不变。

debug 按 session/requestId/funcId 查询原模型、LLM、tools、ai-code join及孤儿。mock 只能校验报文形状和幂等，不能证明 requestId 真属于该工具或 funcId 真等于 T；这些仍由客户端真实关联测试证明。cancelled/interrupted 不归成功也不擅自归普通失败，继续单列待裁决。

责任人已于 2026-11-17 明确委托 AI 制定 B8，以上现为开发期暂行契约；不代表现网后台支持，正式实施仍需后续授权，cancelled/interrupted 继续单列。
