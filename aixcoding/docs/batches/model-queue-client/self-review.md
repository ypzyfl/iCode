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

## 2026-11-19 变更单 v1.1（排队中主动取消）评审结论：通过（P1 已清零）

- 轮次：2 轮独立评审（首轮 4 个 P1；复审又发现 1 个 P1 + 2 个 P2）+ 3 项破坏实验
- 评审范围：本地未提交改动 —— 新增 `service/aixcoding/llm_queue/queue_cancel.py`、`aixcoding/tests/llm/test_model_queue_cancel.py`；
  改 `chat_completions/client.py`（+28/−9）、`tests/architecture/trajectory_wait_manifest.json`（+14/−1）、批次文档 5 份
- 首轮 P1 处置：
  1. **`extra_body` 浅拷贝污染**：`build_request` 浅拷贝 options，原地写 `request_id` 会污染调用方；复用 options 时命中旧 id → cancel 恒 `404` 且静默。改为写入前 `dict(extra)` 拷贝再回写 request，新增"不污染调用方""非 mapping 分支"两条锚定。
  2. **取消 task 无强引用**：`ensure_future` 的 task 在取消态可能被回收。加模块级 `_PENDING_CANCELS` 集合 + done 回调移除。
  3. **失败不可观测**：连接失败/超时是"URL 推导错误"的唯一症状，升 `warning`（带 endpoint 与后果）；`404/409` 保持 `debug` 但补 endpoint 便于区分。
  4. **测试空洞**：无一处真实 `task.cancel()`；`204/404/409/500`/连接错误/超时用例无断言。新增 `test_cancelled_task_while_queued_sends_cancel`（持开流 + `task.cancel()`），上述用例补 `len(calls) == 1`。
- 复审 P1 处置：**wait manifest 表达式漂移** —— 修 P2 时把 `shield(ensure_future(...))` 改成 `shield(task)`、`self._endpoint` 改成局部 `endpoint`，清单未刷新；
  该守卫带 `CI_LINUX_ONLY`，本机 win32 不跑，CI 会红。已重跑 `uv run python -m tests.support.trajectory_wait_inventory`（2 条重开，全 `unresolved`），守卫 57 passed。
- 复审 P2 处置：取消态不再 `await shield`（`current.cancelling()` 时提前返回，中断不被拖慢，与 design 一致）；
  `finally` 改嵌套 `try/finally`，流关闭抛错或二次取消时 cancel 仍会发出；design 补"代理按环境变量"的措辞。
- 未修项（保留并登记）：
  - 客户端在收到任何 `position` 帧前断连 → `queued` 为假、不取消，元素留到网关 `QUEUE_TIMEOUT`；与 v1.0 边界同源，属客户端可观测性上限。
  - `_PENDING_CANCELS` 在事件循环关闭时可能残留已死 task 引用（只占内存，无功能影响）。
- 破坏实验（改动-复原，工作区已复原，`grep BREAK-EXPERIMENT src/` 无命中）：

  | 实验 | 改动 | 结果 |
  |---|---|---|
  | A | `cancel_on_close` 判据通过后提前 `return` | `test_interrupt_while_queued_sends_cancel` FAILED |
  | B | `observing` 不置 `_released` | `test_interrupt_after_release_sends_nothing`、`test_released_tracker_is_not_queued` FAILED |
  | C | `cancel_on_close` 恒 `return` | 8 条 FAILED（含真实 `task.cancel()` 用例） |

- 复审证据：`verification.md` 的「独立评审后的修复」「破坏实验」两节；最终 `aixcoding/tests/llm` 47 passed、
  `ruff` 通过、`ty` 三平台通过、`gen_customizations --strict` OK、`check_docs --closure` OK。
- 声明：两轮评审均为独立子代理（只读、独立会话），同一模型族仍可能共盲，终裁在责任人。
