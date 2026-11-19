# 实验：工具身份与 A-final 持久化关联

> 状态：普通工具主链和真实 rollback 孤儿事件两个方向样本已完成；最终 `2 passed`。不覆盖完整 analyzer、最终报文或完整异常矩阵。

## 目的与约束

验证 after_turn + 全 session 联读的两个前提：

1. 普通本地工具能由 `tool.started.call_item_id` 精确找到 function_call、所在 assistant M 和产生它的 A-final；
2. rollback 后仍留在 trajectory 的旧工具事件不能借相同 provider call_id 错连到 replacement 调用。

实验代码只位于 `aixcoding/tests/telemetry/test_tool_identity_persistence.py`。按 DIRECTORY §5，自包含生产 engine、scripted HTTP transport 和本地工具，不修改或 import 上游测试设施，不修改产品代码。

## 样本 A：普通工具主链

真实 engine、OpenAI SDK/Chrys client、session/trajectory writer 运行；仅 HTTP transport 为 scripted。第一次响应返回 `lookup` function_call，工具真实执行成功，第二次响应返回最终文本。

断言：

- `tool.started.payload.call_item_id = C`；
- C 等于当前 session function_call 的 `_chrys_analytics_item_id`；
- function_call/result 的 operation ID 等于 tool started/finished 的 T；
- `T.parent_model_operation_id = M._chrys_operation_id = E`；
- `M._chrys_request_attempt_id = 成功 model.exchange.finished.request_attempt_id = 第一次实际 HTTP 请求的 attempt header`；
- 该 A-final 不等于同 turn 第二次最终文本请求的 attempt，防止误取 `attempts[-1]`；
- 磁盘上同时存在 `session.json` 和 `trajectory/events.jsonl`。

该样本证明的是产生 function_call 的 A-final，不是整个 turn 的最后一次模型调用。

## 样本 B：rollback 孤儿事件

真实执行旧 turn：provider `call_id=shared-call` 的工具成功后，执行 `UserRollback(target_turn=0)`；replacement turn 再次执行同名工具且复用相同 provider call_id。

断言：

- 旧、新 function_call 的 C 不同；
- trajectory 同时保留旧、新 tool started，且 branch 不同；
- 当前 session 只含 replacement C；
- 以当前 session 的 C 集合查找时，旧 C 不存在，必须判 orphan/unmatched；replacement C 正常命中；
- replacement tool started 的 parent E 与 replacement M 一致；
- 存在真实 `session.rollback` 事件。

若按 provider call_id、工具名或事件顺序关联，旧事件会错误命中 replacement；样本直接否定这种 fallback。

## 执行记录

首次执行收集 2 项，结果为 `1 failed, 1 passed`。失败原因是实验 A 的选择器误把 envelope `operation_id` 当成 payload 字段，并非关联数据缺失；修正选择器后重跑通过。lint 又指出轮询等待应使用 `asyncio.Event`，修正后执行最终命令：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run ruff check aixcoding/tests/telemetry/test_tool_identity_persistence.py && uv run ruff format aixcoding/tests/telemetry/test_tool_identity_persistence.py && uv run pytest aixcoding/tests/telemetry/test_tool_identity_persistence.py -n0
```

最终结果：ruff `All checks passed!`，格式化 1 文件；pytest 收集 2 项，`2 passed in 4.38s`，退出 0。

## 未证明事项

- 不证明 SDK retry、redirect、Responses retrieve、外层 retry 的完整矩阵；
- 不证明并发/多 child、多个重复 provider call_id 的最终组包；
- 不证明 funcId 外部服务器契约、外部 ACP 或 provider-hosted 的特殊保真策略；
- 不证明 after_turn analyzer、缺失原因记录和服务器闭环已经实现。
