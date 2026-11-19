# PR #69 与当前工具 ID 关联结论对照

> 基线：2026-10-03 的 0.28.0 问题反馈、上游答疑、openJiuwen-ai/iCode PR #69（2026-10-10）和当前 fork 0.35.2。本文用于校正 telemetry-exploration 的字段语义，不是新实施授权。

## 1. 证据来源

- 问题反馈：`D:\Coding\desktop\agent_studio_new-knowledge\iCode-chrys\数据上报新方案\已知待处理问题\iCode(Chrys)-会话分析工具调用ID体系断层问题\Chrys-会话ID体系断层问题反馈.md`。
- 上游答疑：同目录 `iCode-工具调用ID体系断层答疑.md`。
- 上游 PR：https://github.com/openJiuwen-ai/iCode/pull/69 ，GitHub merge commit `803429be4392dc7f58b80a6d2463af634111ec18`；本地上游镜像提交 `8a77a5db9792fab132ecfdf0038b3452b2ea759d`，涉及 26 文件。
- 当前实现：`src/chrys/service/mutations/types.py`、`kernel/loop.py`、tool events/mutation pipeline 及 PR 相关测试。

## 2. 三个时点的关系

### 2026-10-03：原始断层成立

当时：

```text
function_call.call_id = provider ID
mutation.tool_call_id = 12hex Chrys/UI ID
```

二者独立生成，session.json 中没有桥接。`_chrys_operation_id` 和 `_chrys_analytics_item_id` 虽已存在，但 mutation 尚未保存 tool_operation_id，因此不能借它们关联账本。答疑还纠正：短 UI ID 不在 trajectory events.jsonl 中，不能声称事件流天然提供短 ID↔provider ID 映射。

### 上游答疑与最终 PR 不完全相同

答疑优先推荐方向 B：把短 UI ID 写入 function_call/result 的 `_chrys_call_id`，也认可方向 C：mutation 增记 `_chrys_operation_id`。

最终 PR #69 实际采用的是 **operation 桥接**，不是把短 UI ID 盖到消息上：

```text
新增 mutation.tool_operation_id = call/result._chrys_operation_id = T
保留 mutation.tool_call_id = 12hex Chrys/UI ID
保留 function_call.call_id = provider ID
```

同一 PR 还引入 request attempt tracking、attempt header、model.request 事件及成功 message 的 attempt 持久化，构成当前 A-final 分析的基础。

### 当前 0.35.2：规范关联链

```text
mutation.tool_operation_id = T
function_call/result._chrys_operation_id = T
tool.operation.started/finished.operation_id = T
tool.started.payload.call_item_id = C
  → function_call._chrys_analytics_item_id = C
  → 所在 assistant M
  → M._chrys_operation_id = E
  → M._chrys_request_attempt_id = A-final

mutation.tool_call_id = 12hex UI ID，不是上述 join 键
```

## 3. 与此前结论逐项对照

| 此前结论 | 对照结果 |
|---|---|
| provider call_id 不保证唯一，不能单独 join | **一致**，正是 PR #69 要解决的问题之一 |
| 优先以 call_item_id 定位具体 function_call/M/A-final | **一致**，C 是 occurrence 键，T/E 交叉校验 |
| T 串联 call/result/tool started/finished | **一致** |
| `mutation.tool_call_id = T` | **错误，明确纠正**：当前是 `mutation.tool_operation_id = T`；`mutation.tool_call_id` 仍为 12hex UI ID |
| UI 短 ID 不是 after_turn 消息关联主键 | **一致但需补充**：它会落入 mutation.tool_call_id，却未盖到 function_call/result，不能桥接消息 |
| 整个 session 目录可关联 mutation、工具和模型成功响应 | **成立**，正确使用 `mutation.tool_operation_id → T → C/M/A-final`；完整 tool-detail 仍需 events，ai-code 还需 blob |
| PR #69 与当前 attempt 主键讨论相互独立 | **不成立**：该 PR 同时引入 attempt tracking，是当前 A-final 持久化证据的直接来源 |
| 普通本地工具 funcId 推荐 UUID(T) | **身份已由 B2/B3 确认**（2026-11-18 原值裁决后 funcId=T 原值 32hex）：上游也以 T 解决 provider ID 重复和执行实例归属；剩余是 final-save/原子幂等实现，不是 funcId 角色待定 |
| parentSpanId 省略或从 E 派生 | **PR 不直接裁决**；后续 B4 已明确它只表示真实直接父 turn，普通独立 turn 省略，不从 E 派生，不能说成 PR 官方方案 |

## 4. 对当前方案的实际影响

1. 不再把旧 12hex `mutation.tool_call_id` 当作 T 或 provider ID；分析器必须显式读取可选 `tool_operation_id`。
2. PR 前历史 session 没有 `tool_operation_id`，保持 unknown/降级，不用短 ID、provider ID、时间或顺序猜测；这与 PR 的兼容承诺一致。
3. 普通本地工具执行实例 funcId（2026-11-18 原值裁决后为 T 原值 32hex）与上游执行身份语义一致；B2/B3 已确认该角色（原值格式接受列入 BR-5），现网原子幂等仍按 BR-2–BR-4 联调。
4. 普通工具的 C→M→A-final、rollback 孤儿拒绝及 funcId/parentSpan 讨论不需要推翻；只需修正 mutation 字段名和历史版本边界。

## 5. 行为验证

2026-11-16 执行 PR 相关现有测试：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/orchestration/engine/test_mutation_operation_identity.py::test_repeated_provider_call_ids_keep_distinct_persisted_mutations tests/service/agent_middleware/test_tool_operation_stamps.py::test_event_middlewares_record_file_mutations_under_the_tool_operation tests/service/mutations/test_pipeline.py::test_shell_and_calibration_mutations_keep_the_tool_operation -n0
```

结果：收集 4 项，`4 passed in 1.19s`，退出 0。覆盖重复 provider ID 下不同 T 的 mutation 归属、`tool_call_id != T` 及 shell/calibration 的 operation 传递；不证明新 analyzer 已实现。
