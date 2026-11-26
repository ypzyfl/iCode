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

- 复审证据：`verification.md` 的「独立评审后的修复」「破坏实验」「收尾」三节；最终 `aixcoding/tests/llm` 49 passed、
  `ruff` 通过、`ty` 三平台通过、`gen_customizations --strict` OK、`check_docs --closure` OK。
- 声明：两轮评审均为独立子代理（只读、独立会话），同一模型族仍可能共盲，终裁在责任人。

## 2026-11-26 补轮（PR #154 独立评审处置）：覆盖 v1.2–v1.6 断档 + 本日修复

- 缘起：PR #154 独立评审 B1 指出本文件最后记录停在 2026-11-19（v1.1），其后 v1.2（请求体
  request_id）→ v1.3（改 `Chrys-Request-Attempt-Id` 请求头、回退上游测试改动）→ v1.4（接线归位
  压缩）→ v1.5（cancel 凭据同源，修纯登录态生产故障）→ v1.6（cancel 传输同源，评审 M1）共
  5 个变更单无自审记录，违反 DEVELOPMENT.md §4.2 步骤 5。本节补档。
- 断档期的第二评审来源如实声明：v1.2–v1.5 的独立评审缺位（各变更单的验证记录与责任人裁决在
  design 变更单内，但无第二 AI 评审）；**PR #154 独立评审（2026-11-26）是这 5 单的第一份独立
  复核**，其上游接触面逐行表、R2/R3 门禁复跑、`aixcoding/tests/llm` 84 passed 复验即本补轮的
  外部证据。
- 该评审对本批的 blocker 裁定：作者自报的 2 项"已修"复核属实（wait 清单含 llm_queue 条目；
  回退用例锚定内层异常）；5 项"责任人不修"同意 reject。
- 本日新增（v1.6，评审 M1 裁决"修"）：`http_kwargs` 通道（observer/clients/chat_client 三处
  既有 marker 块扩容、计数不变）+ `_cancel_client` 构造点提取 + `_preview` 去重 + 不可达分支
  移除；新用例 2 条（构造参数继承、观察者→工厂通路）。**本机无 uv 仅 py_compile；测试与门禁
  以推送后 CI 为准，结果回填 verification.md；推送后另有 AI 复评轮（见 PR 流程），发现将追记本节。**
- 文档面同步（评审 B2/B4/建议项）：新 ADR `model-queue-client--gateway-cancel-required`
  起草（待责任人签认 + 旧 ADR 状态行改被取代）；design 顶层 R2 表 `test_settings_reload.py`
  行标注 v1.3 已回退归零；requirements/test-plan/plan 旧口径更正（token 来源、请求体 request_id
  撤销、状态推进）。
- 声明：本节为开发 AI 补档 + 外部评审引用，非独立子代理评审；独立复核以 PR #154 评审与本 PR
  推送后的 AI 复评为准，终裁在责任人。
