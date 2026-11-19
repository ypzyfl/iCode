# N6：ai-code 报文与代码块重建

> 技术判断：**大方向条件可行，不阻塞 after_turn + session 目录联读。**正常、成功完成的文本 `write_file/edit_file` 数据足以重建旧 `ai-code/save` 的逐次 before/after、blocks、requestId/spanId 和 codeStatus=1/5。
>
> 决策状态：采用“工具 outcome 闸门 + 最终参数校验 + mutation/blob 内容证据”。缺参数、缺 blob、失败/取消等边界必须省略或降级，不为追求旧报文数量而猜测。组合样本和逐字节一致性留实施。
>
> **2026-11-18 ID 原值裁决**：reportId/requestId/spanId 等全部 ID 保持原值 32hex、不转 UUID（`reportId=T 原值` 而非 `UUID(T)`）；本文中 UUID 形态表述与 golden 按原值理解，批次1 design 时统一重写。权威口径见 `../backend-change-requests.md` BR-5。

## 1. 旧最终契约纠正

旧 `ai-code` 只有 save，没有 update；只处理 `write_file/edit_file`，shell 隐式写不进入该 reporter。

实际 save 字段：

- 固定：`reportId`、`filepath`、`blocks`、`sourceType="edit"`、`inputMethod="ai_generated"`、`sessionId`、`codeStatus`；
- 条件：`language`、`requestId`、`spanId`、`agentName`、remote/branch/Git user 及公共 channel/project/Git 字段；
- 每个 block：`snippet`、`rangeStart`、`rangeEnd`。

**ai-code 不携带 funcId、parentSpanId、originalLines/addedLines/deletedLines、changeLines 或 eventTime。**行数属于 tool-detail 终态 update，reportId 是 ai-code 报文自身 UUID4，不是工具 ID。

证据：旧最终 `reporters/ai_code.py:43-44,116-158,243-278`。此前旧版参考中把行数/eventTime 混入 ai-code 的描述应以此为准。

## 2. blocks 的重建输入

| 场景 | 旧算法 | 当前数据是否足够 |
|---|---|---|
| write create | 整个 after 一个 block | 足够：create、无 before、after blob |
| write overwrite | 仍是整个新文件，不是差异片段 | 足够：before/after blob；blocks 只需 after |
| edit 单次 | before/after + old/new 定位实际替换片段 | 足够，需最终参数 |
| edit `replace_all` | 每处替换一个 block，rangeEnd 按实际 new_string 行数 | 足够；不是按替换次数固定一行 |
| 同文件多次调用 | 每次调用独立一条 save、独立 reportId | 足够：每条 mutation 独立 before/after 和 tool_operation_id |
| 纯删除/after 为空 | 无生成代码，不报 ai-code | 可判定并跳过 |
| 成功但内容未变化 | 旧 reporter 不按 file_bytes_changed 抑制 | 不应自行增加 no-change suppression |

`replace_all` 超过 64 个 block 时，旧算法有意回退为单个全文 block，可保留。若最终参数与 before/after 不一致，则不能借“唯一片段/全文 fallback”猜测正确归因；新版应降级，而不是 bug-for-bug 生成伪精确内容。

连续编辑必须逐条处理：`m1.after_hash == m2.before_hash`，不能使用 turn/session 折叠摘要或最终文件状态代替每次调用。

## 3. ID 与 exchange/attempt 关联

```text
mutation.tool_operation_id = T
  → function_call/result = T
  → 所在 assistant message M
      M._chrys_operation_id = E
      M._chrys_request_attempt_id = A

备用：tool.started[T].parent_model_operation_id = E
  → model.exchange.finished[E].request_attempt_id = A
```

字段判断：

- **PR #69 桥接字段是 `mutation.tool_operation_id=T`**；旧 `mutation.tool_call_id` 仍保留 12hex Chrys/UI ID，既不等于 T 也不等于 provider call_id，不能用作消息关联键。PR 前历史记录缺 tool_operation_id 时降级，不按时间/顺序猜测；
- `requestId`：使用产生实际 write/edit 工具调用的 M 的 A-final，与其他上报面保持同文本；缺 A-final 跳过并记录原因，不用 E 混填；
- `spanId`：使用当前对话 turn ID，与本轮模型和工具记录一致；旧版曾由 session_id + 当前 pass turn_id 确定性派生；
- 生产 attempt A：普通工具 N5 的同一证据链可用于扩展诊断，但旧 ai-code 原本没有 attempt 字段；
- 旧随机 parentSpanId 不可恢复，但旧 ai-code 本就不携带它，不是缺口；
- reportId：旧版是报文自身随机 UUID；2026-11-17 首版幂等建议改为确定性的 UUID(T)，仅限当前 write/edit 单 mutation 域，详见第9节和 B8，不恢复随机重放。

`filepath` 和 `language` 可从最终 path 得出；workspace 相对化、agentName、channel/Git 等文件外上下文仍归 N7/N9，不能用当前 cwd/Git 猜历史。

## 4. 工具 outcome 是 ai-code 的闸门

**mutation ledger 记录文件变化，不证明工具成功，也不证明应该上报 AI 代码。**拒绝、失败、取消均可能留下 mutation 和 after blob。

| 当前事实 | ai-code 处理 |
|---|---|
| success，无审批/auto/judge/bypass/reuse | 有 blocks 时上报，codeStatus=1 |
| success，manual 请求且明确 decider=user 批准 | 有 blocks 时上报，codeStatus=5 |
| failed / errored / timed_out | 不上报，即使 partial write 留下 mutation |
| rejected | 不上报；codeStatus=4 属于 tool-detail |
| interrupted | 不上报；旧 ai-code 没有取消终态路径 |
| started 无 finished | 不上报 |
| 尚未执行/参数校验失败 | 不上报 |

当前 trajectory 的 approval requested/resolved 提供 target tool operation、approval_mode、decision 和 decider，比旧 `_approval.status` 更能区分 user 与 judge。只有事实充分时才标 5；trajectory 缺失时不能仅凭 user_approved 猜用户或 judge。

`settled` 只表示 after endpoint 是否最终，不表示工具成功；不能代替 outcome 闸门。

## 5. 最终参数与 snapshot 一致性

### 审批修改

审批 modified_args 会写回 function_call；before hook 先于 mutation prepare，mutation 使用最终路径。正常完整数据下，审批参数、mutation 和执行结果可以对应。

### 其他 hook 修改

普通 hook 改写不一定写回 function_call，result 的 `_exec_stamp` 提供最终参数文本和 digest，但文本可能截断。

建议的判别顺序：

1. 用 T 绑定 mutation/call/result，不靠 path 或 provider call ID 猜；
2. effective_args 完整时使用最终参数；
3. 文本截断时比较 digest：
   - 与 function_call 参数 digest 相同，可继续使用完整持久化参数；
   - digest 不同，说明最终参数已变化且完整值缺失，edit 必须降级；
4. 校验最终 path 与 mutation.path 一致；
5. edit 应用 old/new/replace_all 后应与 before/after 一致；write 内容经相同转换后应与 after 一致；
6. 校验 blob 内容 SHA-256，损坏则省略。

参数 digest 和 snapshot hash 是不同证据，不能直接互相比值。

## 6. blob 与历史内容的降级

不能直接使用 `get_file_edit_snapshots()` 作为安全分析输入：它会把缺 hash/blob 读成 `""`。新版必须基于原始 ledger/refs 区分“不存在”“真实空文件”“skip”“hash 存在但 blob 缺失”。

| 情况 | write | edit |
|---|---|---|
| create 的 before 不存在 | 正常 | 通常不是成功 edit 的正常输入 |
| before 缺失/skip，after 可用 | ai-code 全文 block 仍可生成；tool-detail 行数不能伪造 | 省略/降级 |
| after 缺失/skip/blob 消失 | 省略 | 省略 |
| blob 与 hash 不符 | 省略 | 省略 |
| rollback/remove_turn/clear 后 | 历史可能不可恢复，不补猜 | 同左 |

默认二进制跳过、单文件 50 MiB 等策略会导致合法的内容缺口。不得读取当前工作区文件冒充历史，也不得扫描无 ledger 的孤儿 blob 猜归属。

tool-detail 的 original/added/deleted 行数同样必须来自真实 before/after；缺所需端点时省略，不能按空文件计算伪精确行数。

## 7. 大方向结论与暂缓项

继续采用当前路线，无需恢复旧实时 EventBus 挂点：

- 正常成功 write/edit 的 blocks 输入充分；
- mutation→T→E/A 关联充分；
- requestId/spanId 可重建；
- codeStatus=1/5 有审批事实来源；
- 失败、拒绝、取消、缺参数和缺 blob 有可检测的安全降级规则。

以下不影响大方向，留实施。2026-11-17 M0 已完成一条真实 A1→write_file→A2 的 session/mutation/blob 组合和测试态 DTO，因此“一份真实组合样本”不再是零覆盖；仍需扩大场景和 golden parity：

- 更多真实 session 目录组合与独立 reader 样本；
- create→单次 edit→replace_all→overwrite 的逐条 blocks 对照；
- manual modified_args + hook 改写、重试后生产 attempt；
- hook 截断且 digest 不同、失败/取消 partial write、缺 blob 的负例；
- CRLF/GBK、末尾换行、64 块和报文 golden parity。

## 8. 证据与行为锚定

旧最终源码与 oracle：

- `reporters/ai_code.py:93-158,197-278`：blocks、字段、outcome 跳过和 1/5；
- `reporters/tool_detail.py:102-133`：行数来自 before/after 全文 diff；
- `aixcoding/tests/test_ai_code.py`：create/edit/replace_all/CRLF/删除/审批用例。

当前源码与测试：

- `service/mutations/{types,tracker,store,pipeline}.py`：逐次快照、缺 blob 与清理；
- `service/trajectory/approvals.py`：审批 target/mode/decider；
- `service/agent_middleware/events/tool_events.py`：最终参数与 mutation 顺序；
- `foundation/tool_execution_stamp.py`：digest 与 2048 截断。

2026-11-14 实际执行当前测试：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/service/session/test_history_approval.py tests/service/agent_middleware/test_tool_operation_stamps.py tests/service/agent_middleware/test_mutation_exits.py tests/service/mutations/test_pipeline.py -n0
```

结果：收集 113 项，`113 passed in 1.90s`，退出 0。覆盖审批写回、hook stamp、拒绝/失败/取消 mutation 和 blob 缺失；不证明新 ai-code 组合重建器已实现。

旧版最终测试命令：

```cmd
cd /d "D:\Coding\aixcoding\aixcoding-cli\aixcoding-cli__0.28.0_final" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run --with pytest-asyncio --with pytest-timeout pytest -o addopts="" aixcoding/tests/test_ai_code.py
```

结果：收集 23 项，`22 passed, 1 skipped in 14.89s`，退出 0。此前 `-n0` 和默认 `-n` 因旧环境缺 xdist 无法启动，随后两个异步用例因缺 pytest-asyncio 报插件错误；临时补齐 pytest-asyncio/pytest-timeout 并清空默认 addopts 后全部正常执行，无代码断言失败。

## 9. final-save 幂等身份专项（2026-11-17）

### 9.1 真实身份粒度

当前 write/edit 的 `MutationContext` 只有单数 `file_mutation`，prepare 每次 dispatch 记录一次，因此首版可依赖：**一个实际工具 dispatch T 最多对应一条 ai-code mutation**。通用 shell/隐式工具则可能一个 T 记录多条 mutation，不在 ai-code 首版范围。

`call_item_id` 是请求项身份，path 是文件身份，provider call_id 可重复；三者都不能区分一次 T 内的多 mutation。当前 `FileMutation` 没有 mutation_id，新增并持久化通用 mutation ID 会扩大上游改动，首版不采用。

### 9.2 首版 AI 推荐：复用 reportId=UUID(T)

在当前 write/edit 单 mutation 约束下：

```text
requestId = UUID(raw A-final)
reportId  = UUID(T)
幂等键    = (requestId, reportId)
```

这样无需新增 mutationId DTO 或上游 FileMutation 字段，且避免旧 reporter 每次 uuid4() 导致 after_turn 重放报文变化。物理唯一键可直接使用 `(requestId,reportId)`，逻辑含义是“该模型调用产生的这次 write/edit dispatch”。

硬边界：分析器发现同一 T 有多条候选 mutation 时，**该 T 的 ai-code 全部跳过并记录 identity_granularity_insufficient**，不得合并、覆盖或共用同一键。若未来支持 shell/隐式多 mutation，再评估创建时持久化 mutation_id；届时才考虑 `(requestId,mutationId)` 通用键，首版不为此改上游。

### 9.3 最小 final DTO 建议

| 字段 | 首版建议 | 规则 |
|---|---|---|
| `reportId` | 必填 | canonical UUID(T)，同一 dispatch 重放不变 |
| `requestId` | 必填 | UUID(raw A-final)，与其他外部记录同文本 |
| `sessionId` | 必填 | 当前 session，不用 session-latest |
| `spanId` | 正常主 turn 必填 | 当前真实 turn ID；缺失/非 turn 降级，不伪造 |
| `filepath` | 必填 | 最终参数 path 经工作区规则相对化；无 workspace 不回退进程 cwd |
| `blocks` | 必填、非空 | 成功 write/edit 的 snippet/rangeStart/rangeEnd，缺 blob或无法验证则跳过 |
| `sourceType` | 必填 | 固定 `edit` |
| `inputMethod` | 必填 | 固定 `ai_generated` |
| `codeStatus` | 必填 | 普通成功 1；仅明确用户批准证据时 5 |
| `language`、agent/runtime/Git | 可选 | 有历史/运行时证据才携带，不参与幂等或闭环前置 |

首版不增加 funcId、mutationId、parentSpanId、行数或 eventTime。旧 ai-code 本就不含这些字段；span 的父 turn 信息不擅自发明到新 DTO。

### 9.4 mock 幂等与内容一致性

沿用 `POST /csas/telemetry/api/v1/ai-code/save`，以 `(requestId,reportId)` 建数据库唯一约束或原子 insert-if-absent：

- 首次 200并保存；
- 相同键、规范化 JSON 值相同：200不新增；
- 相同键、不同 blocks/filepath/codeStatus/任意已校验字段：409不覆盖并记录冲突；
- 缺必填、非法 UUID、空 blocks、非法 block range：400并记录 rejected；
- 同 requestId 不同 reportId：是合法的同模型多次 write/edit，必须分别保存；
- 同 reportId 不同 requestId：身份异常，客户端应阻止，mock debug 标记碰撞。

语义比较忽略 JSON key 顺序/空白，但 block 顺序、snippet、range 和 filepath 是业务内容，不做折叠。reportId 不得重新 UUID4，动态 Git/channel 不得因重放时读取当前状态而变化。

### 9.5 必测边界

1. 同 M 两次写同一路径：T 不同、reportId 不同，两条均保留。
2. 同一次 after_turn 重放：一条记录，报文完全一致。
3. 同 T 多 mutation：该 T 无 HTTP ai-code，记录身份粒度不足。
4. create→edit→replace_all→overwrite：每次独立 reportId 和正确 before/after。
5. 失败/拒绝/取消/partial mutation：无 ai-code；对应 tool-detail 可有终态。
6. 同键不同 blocks：409且首次不变；响应丢失后相同报文重试不重复。
7. 缺 T/A/blob、非法 path、真实空文件与缺 blob 区分：按降级，不猜。

2026-11-17 执行 mutation operation/path identity、pipeline、mutation exits 和定制真实工具关联测试，收集 73项，55 passed、18 skipped。跳过集中于 mutation path identity 环境条件，未把跳过计为通过；这些证据锚定身份和 outcome，不证明新 ai-code DTO/mock 已实现。责任人随后明确委托 AI 制定 B8，本方案现为开发期暂行契约，后台现网未确认。
