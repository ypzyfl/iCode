# 验证记录：企业埋点迁移

## 2026-11-11 设计阶段

- `git rev-parse HEAD` 得到 `10ec90eefc75274ba9b1acd8c25f4a39964234b1`，项目版本 0.35.2。
- 源码核对确认引擎 `start` 和 `prepare` 共用订阅入口，模型有统一组栈点，主/子工具的结果发布前能取得最终参数和内部快照，ACP prompt 使用新版响应元数据。
- 已确认的是数据所在位置和候选挂点。新旧报文、重试粒度、审批时序和并发关联仍需按测试计划验证。
- `uv run --no-sync python aixcoding/tools/check_docs.py` 返回 `check_docs: OK`。现有虚拟环境与目标要求的 Python 3.14.10 不一致，本次结果仅用于文档检查，产品测试待使用目标环境执行。

## 2026-11-11 首组运行探针

- 旧源码由 `git archive 019d12b1` 解包到 `/tmp/icode-telemetry-probe.7glV33/old`，依赖用 `uv sync --locked --extra all` 装入其独立环境。新版依赖以 `uv sync --locked --python 3.14.9` 装入 `/tmp/icode-telemetry-probe.7glV33/new-env`。目标固定的 3.14.10 本机暂不可用，以下结果基于 3.14.9 和各自锁定依赖。
- 分别用两个环境执行 `/tmp/icode-telemetry-probe.7glV33/probe.py`，以 `httpx.MockTransport` 驱动真实 SDK，第一次返回 429，第二次返回含两个 function call 的 SSE。然后逐次调用真实 `ToolEventMiddleware` 与 `MutationTracker`，由探针在执行回调重绑参数并实际写临时文件。旧 reporter 用 `TelemetryHttpClient` 向 loopback 端点发报文。
- **模型**：旧版两次 HTTP 请求带相同 `telemetry.requestId`，流结束后两个 provider 工具 ID 均可反查这个 ID。0.35.2 同场景产生两个不同的 `Chrys-Request-Attempt-Id`，最终流响应保留两个 provider 工具 ID。探针分别调用模型与工具边界，未验证新版 kernel 自动把同次响应的身份传到实际工具。
- **工具与代码**：旧版 loopback 收到 8 条独立上报，两组各含 save、PENDING、成功终态、ai-code。两条终态的 `originalLines/addedLines/deletedLines` 均为 1/1/1，ai-code 分别为 `beta\n` 和 `alpha\n`，即使最终文件恢复原状。0.35.2 的 Start/Result 中 `provider_call_id` 为空，Result 按序保留 `alpha→beta` 和 `beta→alpha` 两份逐次快照。
- **参数**：旧版 `save.value` 在本场景保留 Start 的 `new_string=pre-approval`。旧 ai-code 无法用该参数定位片段，按既有规则回退至实际执行后全文。新版探针同样捕获了 Start 原始参数与最终文件快照。另跑真实引擎审批改参用例，确认 Python 扩展 after hook 能看见最终参数。扩展 `ToolResult` 本身没有文件快照。
- 样本已保存为 `aixcoding/tests/telemetry/fixtures/sdk-retry-and-repeated-edit.json`。其中随机 ID、临时路径和时间已替换，保留 ID 等值关系、记录顺序和字段存在性。此样本为合成会话，未接生产后台。

| 环境 | 实际命令（在对应环境运行） | 结果 |
| --- | --- | --- |
| 0.28.0 | `uv run --no-sync pytest aixcoding/tests/test_llm_telemetry.py aixcoding/tests/test_tool_detail.py aixcoding/tests/test_ai_code.py aixcoding/tests/test_telemetry_mock.py -n0 -q` | 104 passed |
| 0.35.2 | `uv run --no-sync --python 3.14.9 pytest tests/service/llm/test_request_tracking.py tests/service/agent_middleware/test_events.py tests/service/agent_middleware/test_extension_tool_hooks.py -n0 -q` | 68 passed |
| 0.35.2 | `uv run --no-sync --python 3.14.9 pytest tests/integration/engine/test_pipeline_extensions.py::test_the_main_agent_runs_extension_tool_hooks_before_approval_again_on_an_edit_and_after_the_call -n0 -q` | 1 passed |

这组结果钉住 SDK 重试、原始参数和双快照行为。新版尚未接入企业 reporter，不能据此宣称新版报文对拍通过。剩余重点是真实 kernel 循环的关联承载、并发和其他重试分支。

## 2026-11-11 工具关联与重试边界

- 临时探针通过真实 kernel 工具循环运行两个主 Agent 调用和两个并发子 Agent 调用。四次复用相同 provider 工具 ID。模型 exchange、工具 operation 和结果 occurrence 各能区分四次执行，文件快照分别保留 A→B、B→A、A→L、A→R。采到的 8 个 Start/Result 事件都缺少工具 operation、模型 exchange 和原 provider ID。工具轨迹开始记录晚于 Start 发布，实时采集采用执行边界显式传递。归一化观测样本见 `aixcoding/tests/telemetry/fixtures/reused-provider-id.json`。
- 旧版在临时测试进程中装配原 `AixTelemetryMiddleware`，观测实际注入到脚本 wire 的 `body.telemetry.requestId`。已执行成功工具后再遇到 wire retry，流式和非流式均为 3 次脚本发送、3 个企业 ID。stall fallback 共 4 次脚本发送、4 个企业 ID。
- 新版用临时观察 middleware 记录进入次数。wire retry、stall fallback、blank resend 和 overflow resend 分别为 3、4、2、2 次，和脚本 wire 的发送次数对应。Anthropic thinking-binding resend 一次进入触发 2 次实际 SDK HTTP 发送。
- 新版 OpenAI Responses 服务端存储使用真实引擎及 SDK，HTTP 由 MockTransport 提供。响应失败且未执行托管工具时为 POST → POST，断流续读同一响应时为 POST → GET，两种路径均进入 middleware 两次。新版测试的续读终态是文本。旧适配器源码也存在 GET retrieve 路径。
- 旧版补跑真实 Responses SDK + MockTransport，先 POST 创建待完成响应，再 GET 取回含两个工具调用的终态。探针把返回的调用交给真实工具中间件执行，并从 loopback 捕获 8 条上报。GET 没有请求体。所有带 `requestId` 的上报均引用 GET 对应的 middleware 生成的 ID，与创建 POST 中的企业 ID 不同。旧版模型续读由探针显式驱动，未替代新版全轮重试用例。样本见 `aixcoding/tests/telemetry/fixtures/responses-poll-tool-attribution.json`。

| 环境与范围 | 结果 |
| --- | --- |
| 0.35.2 工具元数据对齐、operation 标记和轨迹单测 | 98 passed |
| 0.35.2 wire retry、stall fallback、blank/overflow、Anthropic thinking-binding 观测 | 16 passed |
| 0.35.2 服务端存储首次请求与真实整轮重试观测 | 11 passed |
| 0.28.0 wire retry、stall fallback 与服务端存储首次请求，装配原企业 middleware | 4 passed |

两版均在 Python 3.14.9、各自锁定依赖下运行。新版结果用于确定数据和接线边界，企业 reporter 仍待实施及端到端对拍。

## 2026-11-11 Workflow 和托管工具

- **Workflow 本地工具**。`build_kernel_node()` 使用会话的 bus 装配 `SubAgentEventMiddleware`，传入实际 profile、session 和 workspace。节点执行前 `bind_origin(request.origin)` 绑定本次 attempt。测试驱动节点在读文件后超时，第二次 attempt 从保留的工具结果继续，bus 只收到第一次 attempt 的一次工具 Start。由此可复用子 Agent 的本地工具发布点，采集端保留完整 `origin`。Workflow 的新旧报文对拍仍待实现后验证。
- **托管工具**。主轮 `TurnBindings._publish_hosted_operation()` 和子 Agent / Workflow 的 `SubAgentEventMiddleware._publish_hosted_operation()` 都从托管展示桥发布事件，已有 `provider_call_id` 与展示 occurrence ID。Start/Result 没有源模型 exchange ID，托管工具也不进入本地工具执行中间件。Kernel 的 `HOSTED_CALL_OBSERVED` 轨迹有父 exchange、工具类别和 ordinal，但没有可与 bus 事件直接配对的 provider 或展示 ID。不能据此用轨迹实时补齐工具报文归属。
- **0.28.0 源码对照**。旧订阅器接受两类工具事件。模型 `_record_response()` 只为 `function_call` 建 provider ID 索引，同时更新会话最近请求。`ToolDetailReporter.on_start()` 查不到 provider ID 时回退到会话最近请求。因此托管 `save` 的 `funcId` 可沿用现有 provider ID 或旧内部 ID 缺省，`requestId` / `spanId` / `parentSpanId` 有历史回退行为。并发或失败响应的归属不能仅凭该回退保证，需录制旧报文并明确兼容或修正范围。
- 在既有锁定依赖环境中，以 Python 3.14.9 执行 `uv run --no-sync --python 3.14.9 pytest tests/orchestration/workflows/test_agent_node_retry.py tests/service/llm/test_responses_whole_run.py -n0 -q -p no:cacheprovider`，**38 passed**。覆盖节点超时恢复、模型重试、托管工作已发生时的重试限制和服务端续读。范围为上游行为测试。
- 同一环境执行 `uv run --no-sync --python 3.14.9 python aixcoding/tools/check_docs.py`，报告两处状态格式错误。`design.md` 与 ADR 的头部均为 `状态：确认`，校验器接受的签认值是 `已确认`。R2 表仍是候选预算，需先定稿，再由负责人完成签认。

## 2026-11-11 旧版托管工具报文归属

在 `019d12b1` 的隔离环境执行 `uv run --no-sync python /tmp/icode-telemetry-probe.7glV33/hosted_attribution.py`。探针使用真实旧版 Responses SDK、模型 middleware、`ToolDetailReporter` 和 `TelemetryHttpClient`。模型端和上报端都用 `httpx.MockTransport`，保留真实 HTTP 请求序列化。用合成的托管 Start/Result 控制发布顺序，失败场景在模拟 HTTP 500 后投递失败事件。本探针验证报文及关联规则，托管事件何时发布由上游行为测试覆盖。

| 场景 | 旧版 `tool-detail/save` 的实际归属 |
| --- | --- |
| 正常完成 | `requestId`、`spanId`、`parentSpanId` 都来自本次调用 |
| HTTP 500 后收到失败工具事件 | 三个字段都回退到上一轮已完成的模型调用 |
| POST 创建响应，GET 续读成功 | `spanId` 与创建请求一致。`requestId` 和 `parentSpanId` 来自 GET 对应的 middleware 调用，GET 没有请求体 |
| 同会话并发，A 在 B 之后完成，B 的工具事件随后发布 | B 的三个字段都归到 A。两条工具记录保留同一 provider `funcId` |

捕获 15 条真实序列化的旧版上报，即 5 组 save → PENDING → 终态。失败组保留失败终态，同时重现关联错挂。归一化样本为 `aixcoding/tests/telemetry/fixtures/hosted-tool-attribution.json`。正式接线后仍需用真实托管事件回放验证这些场景。

旧版同一环境运行 `uv run --no-sync pytest aixcoding/tests/test_llm_telemetry.py aixcoding/tests/test_tool_detail.py -n0 -q -p no:cacheprovider`，**56 passed**。文档校验复跑仍报前述两处状态值错误。

## 2026-11-11 R2 本地工具事件出口核对

- `ToolOperationTrace.open()` 依赖活跃轨迹，`begin_exchange()` 依赖活跃 cycle。kernel 的 `_stamp_function_call_operations()` 独立分配工具操作 ID。事件出口方案在审批和执行前读取工具 ID 及已有 exchange，Start 与 Result 共用这组值。无轨迹时的源模型关联仍需验证。
- `ResponseValidationMiddleware` 分别观察流更新、终态和失败响应。托管展示桥可在流结束前发布 Start，也可能延迟发布某次调用的观察结果。托管来源验证须覆盖三条观察路径以及首次在 GET 观察到工具的情形。
- 目标分支以 Python 3.14.9 执行 `uv run --no-sync --python 3.14.9 pytest tests/service/agent_middleware/test_tool_operation_stamps.py tests/service/llm/test_responses_whole_run.py -n0 -q -p no:cacheprovider`，**42 passed**。验证范围为现有操作标记和 Responses 全轮重试。

## 2026-11-11 无轨迹及托管工具来源探针

- 无轨迹探针在真实 kernel 流式循环中执行两次主工具和两个并发子工具。四次均复用同一 provider ID，模型 exchange 均为空。四个 kernel operation ID 彼此独立并和结果内容一一对应。进一步用模型 middleware 的最终响应回调登记函数调用的对象身份，在 kernel 分配 operation ID 时读取登记。四次执行均取回各自的模型来源，且两次主工具执行分别保留 A→B 和 B→A 的快照。临时脚本为 `correlation_without_trajectory.py` 和 `correlation_with_request_source.py`，位于 `/tmp/icode-telemetry-probe.7glV33/`。
- 用临时 pytest 观察插件 `hosted_source_observer` 运行 `tests/service/llm/test_responses_whole_run.py` 及 Workflow 的 `test_a_failed_poll_of_a_background_response_never_creates_its_hosted_work_again`，11 项通过。用真实 Responses SDK 和 MockTransport 再跑两个成功场景。正常 POST 在流结束前发布 Start，最终响应沿用同一展示 ID。POST 断流且 GET 首次返回工具时，Start 与 Result 都来自第二次调用。失败分支中，终态才出现的托管工作从同次请求的失败观察点发布。Workflow 续读已有 Start 时只观察到原 attempt 的那次 Start。
- 独立展示桥探针在本地工具屏障前观察托管工具，释放屏障时已离开模型观察回调。临时标记随排队操作到达发布点，发布时的上下文为空。候选实现应捕获观察来源并随操作携带，另需核验最终重建和恢复路径。
- 探针使用 Python 3.14.9。脚本内包装只用于观测和验证候选交接，企业上报编码及后台对拍仍在实施验收范围内。

## 2026-11-11 签认后文档与对账门禁

- `uv run --no-sync python aixcoding/tools/check_docs.py` → `check_docs: OK`（25 ADR / 40 design / 38 self-review）。前次报告的两处状态值错误已修：design 与 ADR 头部均为 `状态：已确认`。
- 同一命令加 `--closure` → 仅缺 `self-review.md`，属计划任务 5 的交付物，尚未到产出时点。
- `uv run --no-sync python aixcoding/tools/gen_customizations.py` → 通过，39 条 orphan registration warning。按 `DEVELOPMENT.md §5`，登记先于代码在本地姿态是 warning；`--strict`（CI 姿态）会把孤儿登记升为 error，因此本批次的 marker 必须与登记表在同一 PR 落地，否则该 PR 的 `aixcoding-tests.yml` 会红。
- R2 附件复核：`HostedToolView` 的 `model_source_id` 已置于 `metadata` 之后（该 dataclass 的 `metadata` 无默认值，前置会触发 dataclass 定义错误）。实际统计为 17 个源码文件 +179/−19、39 条 marker，与 design §7 一致。
- 三个构建入口改用 `client_factory` 后，等待清单中对应的 `wrapper` 规则降为 `awaitable`，已在 R2 附件内逐条记录并注明约束损失。
- 环境仍为 3.14.9 的 `.venv`（目标 3.14.10 本机不可用）。本轮只执行文档校验与定制点对账，未跑产品测试，不构成实现通过证明。

## 2026-11-11 R2 签认前核对

- 目标提交为 `10ec90eefc75274ba9b1acd8c25f4a39964234b1`。逐行审阅稿有 17 个源码文件 +179/−19、生成清单 +19/−14，以及 39 个源码标记。用 `git apply --check` 校验候选差异可应用于该基线。候选 Python 文本通过 AST 解析与 Ruff 检查，格式由仓库固定版本 Ruff 生成。
- 对候选差异在内存中运行仓库 wait inventory 扫描，重新打开 48 个等待，条目和原规则见逐行审阅稿。候选标记和模拟签认状态在内存中通过 `check_docs.py` 和 `gen_customizations.py --strict` 的校验函数，定制登记检查零警告。
- 基线使用 Python 3.14.9 执行 `uv run --no-sync --python 3.14.9 pytest tests/architecture/test_trajectory_wait_inventory.py tests/architecture/test_layering.py tests/app/acp/test_server_prompt_images.py tests/service/llm/test_client_factory_rollback.py -n0 -q -p no:cacheprovider`，**292 passed**。这是目标基线的回归结果。完整迁移接线及定制实现按 test-plan 验收。
- 实际文档校验当前只剩 `design.md` 的 `状态：确认` 一处格式错误。ADR 的 `状态：已确认` 已通过该项校验。
