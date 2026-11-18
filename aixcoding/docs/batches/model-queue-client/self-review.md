# 自评审记录：客户端对接模型并发排队（model-queue-client）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-18
- 确认意见：（可选）
- 评审 AI：CodeBuddy 子代理（独立会话，只读评审；与开发会话上下文隔离）
- 开发 AI：CodeBuddy（本会话）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-11-18 评审结论：通过（blocker 已清零）

- 轮次：1 轮评审 + 1 轮修复 + 1 轮增量复审（复审以破坏性实验与守卫复跑完成）
- 评审范围：commit `7a33a816`，base `659b56e`，10 文件 +687/−0（其中真正上游文件 1 个：`chat_completions/client.py`）
- blocker 处置：
  1. **漏刷新 wait 清单生成产物** → 已修。`tests/architecture/test_trajectory_wait_inventory.py` 修复前报 `unclassified wait nodes: ...llm_queue.queue_frames:guard_queue_frames:1`；执行 `uv run python -m tests.support.trajectory_wait_inventory` 刷新（+5 行，规则 `unresolved`），守卫复跑 `1 passed`。R2 表已增列该文件并重新签认。
  2. **回退用例是空洞测试** → 已修。原用例只断言 `ChatClientException`，删掉 try/except 后 `ModuleNotFoundError` 经上游 `_service_error` 仍产出同类异常，用例不会红。改为断言内层 `ChatClientInvalidResponseException`，破坏实验 C 证实删块即红。
- suggestion 处置：全部采纳（删除跨请求单槽记录器与 `latest_queue_status`、R2 行数按实际 +10/−0 与 +5 更新并披露差异、降级日志升为 warning 且点明后果、test-plan 心跳行改为"单元 + 局限说明"）。
- nit 处置：全部采纳（只发排队帧即断流时定制包记 info、`queue_position` 措辞降级为"按当前网关契约"、service 档 docstring 补 `llm_queue` 索引）。
- 未修项（责任人拍板不修）：
  - 心跳续活的**端到端**用例（评审 F6 给出的备选）未做：连接性语义由上游 `_watchdog_await` 的 progress scope 提供，定制测试无法覆盖其失效；已在 design 假设 5 与 test-plan 中如实标注该局限，不假装端到端。
- 复审证据：见 `verification.md` 的「2026-11-18 自审修复与复审」节（含三项破坏性实验与复跑输出）。
- 声明：本评审为独立第二 AI 评审（子代理独立会话），与开发会话上下文隔离；同一模型族仍可能共盲，终裁在责任人。
