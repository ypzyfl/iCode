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

## 2026-11-11 第一批实施

- 签认提交为 `a752020b`，开发分支为 `main_aixcoding_cli_0.35.2`。第一批新增独立报文编码和有界发送队列。旧版录制样本的八条记录逐字段一致，覆盖两次编辑、审批前参数、实际快照和旧状态码。发送测试通过 MockTransport 验证请求顺序、发送时凭据、拒绝响应、队列溢出和关闭。
- Python 3.14.9 下执行 `uv run --no-sync --python 3.14.9 pytest aixcoding/tests/telemetry -n0 -q`，5 passed。新增文件的 Ruff 检查和格式检查通过，`check_docs.py` 通过。
- 直接运行轨迹等待清单与分层测试，279 passed，1 failed。失败为 `test_wait_manifest_matches_source`，新增发送模块的 8 个等待需要登记。按仓库生成器计算的差异为 `tests/architecture/trajectory_wait_manifest.json` +18/−0，`git apply --check` 通过。已签 R2 对该文件的 +19/−14 仅包含上游接线。以下为本次申请追加的等待，均使用新条目的默认 `unresolved` 规则。

| 函数 | 新增等待 |
| --- | --- |
| `TelemetryDelivery._run` | 等待队列条目、发送该条报告 |
| `TelemetryDelivery._send` | HTTP POST |
| `TelemetryDelivery._shutdown` | 有界排空、等待队列清空、等待 worker 退出、关闭 HTTP 客户端 |
| `TelemetryDelivery.aclose` | 等待一次性关闭任务 |

候选生成清单在内存中通过原校验器，新增模块通过 Darwin 的 `ty check --error-on-warning`。统一验证入口 `verify.py --smart --paths <本轮改动>` 的完整定制套件为 550 passed、47 skipped、71 failed、17 errors。88 个失败与错误均以 `PermissionError: [Errno 1] Operation not permitted` 结束，涉及现有认证和 mock 测试使用的本地端口绑定。独立埋点测试使用 MockTransport，覆盖发送代码和 HTTP 序列化。

统一入口的上游 Smart Test 为 10952 passed、24 skipped、75 failed，架构阶段因前置失败未执行。日志记录了本地端口绑定和进程枚举被沙箱拒绝，以及相关子进程测试失败。直接运行客户端关闭归属与延迟导入两组架构测试，23 passed。

## 2026-11-11 补充 R2 清单与来源接线

- 责任人明确批准登记发送模块的 8 个等待。以 `a752020b` 和现有未提交实现为基线运行 `uv run --no-sync --python 3.14.9 python -m tests.support.trajectory_wait_inventory`。生成清单差异为 +18/−0，全部为发送模块条目，默认规则为 `unresolved`。其余已签的上游接线清单随对应实现更新。
- 新增公共字段、旧配置兼容和 ai-code 缓冲实现。缓冲通过事件循环定时回调触发，阈值、定时和关闭均逐条入原发送队列。公共字段编码使用已捕获的 Git 与渠道事实。Git 采集另有工作区缓存，接入实际调用方时由生命周期安排 I/O 时点。
- 应用已签逐行附件中的 `kernel/loop.py`、`kernel/middleware.py` 和 `orchestration/invoker/kernel.py` 接线。重复 provider ID 的两个调用在 kernel 分配操作 ID 后分别读回原请求来源。嵌套 pass 退出后恢复父绑定。模型 middleware 和订阅器的实际接线仍待后续实施。
- Python 3.14.9 下直接运行 `pytest tests/architecture/test_trajectory_wait_inventory.py tests/architecture/test_layering.py tests/architecture/test_hygiene_subprocess_stdin.py -n0 -q -p no:cacheprovider`，311 passed。`pytest aixcoding/tests/telemetry -n0 -q`，10 passed。新增模块 Darwin 类型检查和本轮源码 Ruff 检查通过。统一验证的沙箱失败沿用前述记录。

## 2026-11-12 接线审阅与企业报文验证

- 在主工作区核对 `main_aixcoding_cli_0.35.2`、HEAD `a752020b` 和已有未提交文件。对签认附件的 17 个源码 diff 逐块做反向应用检查。上游接线匹配附件，本轮产品修正均在定制模块。
- 接手时埋点测试 20 passed。审阅发现同会话重建会清空已上报的 Start，缺少 Start 缓存时会丢弃旧版仍发送的终态。扩展回归先复现只收到两个 PENDING 的错误，修复后收到各自的终态及无 Start 的独立终态。稳定执行或展示 ID 的重复终态合并为一次。无法确定托管来源时省略关联字段并记录技术日志。
- ACP 响应回调固定使用模型请求发起时的 prompt。正常与取消响应测试用会话替身驱动实际 middleware 和流终态，验证新版 `chrys.turnId`、两个旧 envelope 和流跨作用域完成。另用真实 ACP server、session manager、会话引擎和 SDK 并发两个会话，捕获各自模型请求、选定 Agent 的独立 POST 和 ACP 响应。验证三处 requestId 一致且会话之间不同，标题辅助调用不会覆盖主请求或多发 Agent 使用。标题辅助调用由轨迹中的明确 side_call 身份补充识别，无轨迹且调用方未提供身份的辅助调用仍需核对。

| 报文场景 | 复核结果 |
| --- | --- |
| 两次本地编辑复用 provider ID | 旧录制的八条报文通过编码器逐字段重放。新版真实引擎和 SDK 经 MockTransport 执行 alpha → beta → alpha，实际发送两组 save、PENDING、成功终态及两条 ai-code。各自 requestId 与真实模型请求体一致，行数均为 1/1/1，片段分别为 beta、alpha。 |
| Responses 托管工具 | 流式及阻塞 POST、托管失败、GET 首次观察和 POST 已发 Start 后 GET 完成。后两者均实发 POST → GET，GET 请求体为空。首次观察归续读 ID，已有 Start 归 POST ID。每个 occurrence 只发一组 save、PENDING 和终态。 |
| 托管延迟与同会话交错 | 真实引擎中托管操作经本地工具屏障后发布，保留首次观察的 requestId。事件层复用同一 provider ID 并交错两次工具执行，在同会话再次 Ready 后接收迟到终态，验证来源、独立终态与去重。 |
| 同会话的真实并发子 Agent | 同一 parent turn 同时发起两个同 profile 子调用，两个子模型请求在传输层互等以确认重叠。不同模型路由保留同一企业 sessionId，两个子调用复用相同 provider 工具 ID，各自的文件名和 requestId 在两条 save 中正确对应，并各有 PENDING 和成功终态。 |
| Workflow 跨 attempt | 真实 Workflow 和 SDK 执行本地工具。工具结束后人为触发节点超时，下一 attempt 恢复成功。企业报文只记录一次实际执行，requestId 保留首 attempt 的来源。 |
| 技能 | 真实引擎验证普通 slash 输入和模型 load_skill。输入只有技能 save，缺省 funcId 与 requestId；模型触发另外保存技能维度并关联模型 requestId。 |
| 三种模型协议 | Responses 覆盖上述流式和阻塞请求。Chat Completions 与 Anthropic Messages 的真实 SDK 阻塞请求断言基础 telemetry 字段、会话与工作区、UUID 和缺省字段。尚未覆盖三种协议的完整重试矩阵。 |

### 补充等待清单

负责人口头确认审阅后登记。生成器确认本轮仅重新打开以下九项，实际差异 +21/−2，共 2924 个等待。规则均保留默认 `unresolved`，由 R10 责任人归档批准记录。

| 位置 | 审阅结论 |
| --- | --- |
| `lifecycle.attach` | 注册 `bus.subscribe` 为 awaitable，注册失败回收 `detach(bus)` 为指向 `lifecycle.detach` 的 wrapper。 |
| `lifecycle.detach` | 解订阅 `bus.unsubscribe` 与关闭 `events.delivery.aclose` 为 awaitable，关闭位于清理的 finally。 |
| `TelemetryModelMiddleware.process` | `call_next()` 为 awaitable，保留真实模型调用控制流。 |
| `for_agent_build.create` | `asyncio.to_thread(collect_git_info, workspace_cwd)` 为 thread_pool，原 `factory(*args, **kwargs)` 为 awaitable。 |
| `AgentEngine._release_resources`、`AgentEngine._subscribe_event_handlers` | `detach(self._bus)` 与 `attach(self._bus)` 从 awaitable 重分类为 wrapper，分别指向定制生命周期函数。 |

### 验收缺口

> 本节为当时的历史快照，其中追加输入技能、三种模型协议本地重试矩阵、长会话 Git 刷新及 ACP 取消已由后续记录关闭。当前剩余缺口以本文末尾「2026-11-12 独立代码审阅与当前剩余缺口」为准。

- 实际 ACP 取消、headless/TUI 入口、追加输入技能、历史 fork/rollback 和三种模型协议完整重试矩阵尚未验收。当前测试同时有真实引擎报文、事件层检查和旧样本编码对拍，按各自层级记录。
- 已有定制测试引用上游 `tests/support` 和私有 fixture，后续需按开发规范 §9 收回。Git 采集缓存 TTL 为 300 秒，客户端仍保存构建时快照，长期运行时未复现旧版在请求边界刷新 Git 字段的行为。后端缺省关联字段与幂等仍需现场证据。

### 统一验证和独立对照

- Python 3.14.9 下以本批明确文件清单执行 `uv run --no-sync --python 3.14.9 python aixcoding/tools/verify.py --smart --paths <本批变更>`，退出码 1。此轮在追加三协议及真实 ACP 对拍前执行。完整定制套件 566 passed、47 skipped、71 failed、17 errors，失败和错误均落在既有本地服务端口绑定，`socketserver` 返回 `PermissionError: [Errno 1] Operation not permitted`。
- 上游 Smart Test 26673 passed、89 skipped、154 failed，前置失败后未执行架构阶段。已确认本地端口绑定、macOS 进程枚举 `psutil.pids()` → `sysctl()` 权限错误及其衍生超时。日志另有 TUI xdist worker 异常退出，根因未逐项核实。Workflow 解释器探测用例因 `sys.executable` 的 `/tmp` 和解析后的 `/private/tmp` 文本不等失败。
- 两项非沙箱失败与埋点开启直接相关。模型重载用例比较整个请求体，新增的每请求 requestId 使字节不同。Web 搜索预算用例对整个 HTTP transport 计数，收到 83 次而断言 20 次，其中包括独立埋点上报。单独设 `AIXCODING_TELEMETRY_DISABLED=1` 复跑这两项均通过，用于定位影响。两项保持在上游签认范围外，待 R2 确认如何隔离验证。
- 登记器裸跑的递归文件扫描误纳入范围外的后台旧目录，产生 28 项无关 marker 报错。改用主工作区 Git 文件清单约束同一严格对账逻辑，148 行登记、189 个 marker、0 警告。此次未改登记器或目录。签认附件的源码补丁及本轮等待清单单独复核。
- R2 文件门禁 `check_r2_diff.py --base a752020b` 按主工作区文件复核失败。它只读取签认 design.md 的 R2 表格中名为 `文件` 的列。当前 §7 使用按边界概括的表格，实际路径在附件，导致 17 个匹配附件的源码路径均未进入门禁批准池。R3 marker 严格对账与 R2 文件门禁结果分别记录。请责任人按模板归档同一范围的文件路径和补充等待审批。
- 最终版 `pytest aixcoding/tests/telemetry -n0 -q -p no:cacheprovider` 为 26 passed。连同等待清单、分层、subprocess stdin、Responses whole-run、Workflow retry、ACP prompt 相关测试共 380 passed。Ruff 检查与格式、Darwin ty、`check_docs.py`、`git diff --check` 均通过。最终版 `verify.py --custom-full` 为 571 passed、47 skipped、71 failed、17 errors，失败原因仍是本地端口绑定。沙箱策略保持原样。

## 2026-11-12 本轮门禁和剩余报文验收

- 主工作区仍为 `main_aixcoding_cli_0.35.2`、HEAD `a752020b`，保留已有未提交改动。按本轮授权，把签认附件的 17 个源码路径补入规范 R2「文件」列，另列本轮批准的两个测试路径。保留既有签认字段，由责任人按 R10 落盘确认本轮授权。
- 两项回归先在默认启用埋点时复现失败。重载测试原先直接比较完整请求字节，动态 requestId 导致比较失败。现在比较业务载荷与稳定埋点字段，单独验证两个 requestId 非空且不同以及 spanId 的缺省行为一致。埋点缺省分支保留原字节比较。Web 搜索原始 transport 计数为 83，包含独立上报。给测试的独立上报注入 MockTransport 后，搜索 transport 仍须第一轮恰好 20 次、第二轮累计 21 次，拒绝结果和错误码断言保持原样。两项定向用例连同重载的 Responses 参数共 3 passed。
- 保留既有等待清单 +18/−0 和 +21/−2。Git 缓存刷新增加 `TelemetryModelMiddleware.process` 的 `await asyncio.to_thread(collect_git_info, cwd)`，本轮净增一行 `thread_pool`。生成器重新打开同函数既有 `call_next()`，核对后沿用 `unresolved`，全清单 2925 个等待。
- Git 验收先复现长存活客户端第三次仍发旧 revision。改为每次进入 middleware 从共享 300 秒缓存获取当次事实，Git 读取走线程池。保持同一引擎和客户端，在假时钟下验证前三次工具上报和四次模型请求的过期前后 revision。工具上报与触发其执行的模型请求使用同一快照。
- 追加输入从真实 `UserInject` 事件进入活跃 turn。首个模型请求未返回、已有前一模型响应两种情况下，后续请求均包含注入文本和技能提醒。各自仅发送一次 `funcType=0` 的独立报文，会话、工作区和 Agent 与旧口径一致，无 `funcId` 或 `requestId`。尚无来源时省略 `spanId`，已有来源时沿用同轮 `spanId`。

| 重试边界 | 本地报文对拍 |
| --- | --- |
| SDK 429、kernel 429、连接失败、空响应 | Chat Completions、Responses、Anthropic Messages 三协议使用真实 SDK，经 MockTransport 捕获两次请求。SDK 内重试复用企业 requestId，其余重新分配，轮次 spanId 不变。 |
| 流停顿后的阻塞回退 | Chat Completions 首次流停顿，下一次阻塞请求生成新 requestId，轮次 spanId 不变。 |
| Anthropic thinking-binding 与 overflow | 流式及阻塞两种模式下，thinking-binding 重发沿用各自 requestId，overflow 跨 middleware 边界生成新 requestId。 |
| Responses 服务端存储 | 失败后 POST → POST 分配新 requestId。断流 POST → GET 保持 GET 无请求体，托管工具按首次观察归属。已展示部分答案后的断流仅发送一次请求。 |

- 生产对账仍阻塞。对配置中的生产端点进行无认证、无报文的只读 HEAD 探测，`curl` 返回退出码 7、HTTP 000，连接未建立。未取得生产侧入库或去重数据。
- 最终版 Python 3.14.9 埋点专项 46 passed。合并运行专项、两项受影响上游测试文件、等待清单与分层、Responses whole-run、Anthropic thinking-binding 和 kernel 空响应重试，473 passed。Ruff 检查与格式、Darwin ty、文档校验及 diff 检查通过。
- R2 文件门禁、R3 marker 门禁及点级严格对账使用主工作区 Git 文件列表复核，排除后台工作树。R2/R3 通过，严格对账 150 行登记、191 个 marker、0 警告。
- 统一入口 `verify.py --smart --paths <本轮 9 个文件>` 退出 1。上游 6681 passed、63 skipped、59 failed，架构阶段未进入。已确认本地端口绑定及进程枚举 `sysctl()` 权限拒绝，也观察到 TUI worker 退出和已知的解释器路径 `/tmp` 与 `/private/tmp` 断言差异。最后单跑 `verify.py --custom-full`，591 passed、47 skipped、71 failed、17 errors，失败和错误仍为既有服务的本地端口绑定。沙箱设置未变。

## 2026-11-12 同输入 mock 双版对拍

- 对照为 `019d12b1` 的既有 `/tmp` 隔离副本，目标为主工作区 `a752020b` 上的未提交实现。两版均使用 Python 3.14.9 和各自锁定依赖。模型端与独立上报端都只使用 `httpx.MockTransport`；未绑定端口，未连接或探测生产端点，未使用既有 `.codebuddy/` worktree。
- 探针 `/tmp/icode-telemetry-probe.7glV33/mock_compare_probe.py` 在同一个工作路径依次运行两版。输入固定为一次 SDK 429 后成功的 Chat Completions 流式响应、四个 provider 工具调用、两次 A→B→A 实际编辑、一次失败、一次拒绝、一个无来源调用及一个重复终态。编辑 Start 保留 `new_string=pre-approval`，执行时改为 beta/alpha；时间戳和耗时固定。
- 旧版走真实 instrumented client、`ToolDetailReporter`、`AiCodeReporter`、`TelemetryHttpClient` 和 `BatchBuffer`。新版走真实 `create_client`、模型 middleware、kernel 来源交接、`TelemetryEvents` 和 `TelemetryDelivery`。两版均收集实际 HTTP 方法、路径和 JSON body，不是仅调用编码函数。
- 原始报文为 `mock-compare-old.json` 与 `mock-compare-new.json`，比较器和结果分别为 `compare_mock_reports.py`、`mock-compare-result.json`，均位于上述临时目录。只归一化随机 `requestId`、`parentSpanId`、`reportId` 和自然变化的 `pluginVersion`；字段缺失、状态和错挂不归一化。

### 实际命令

```bash
PYTHONPATH=/tmp/icode-telemetry-probe.7glV33/old/src:/tmp/icode-telemetry-probe.7glV33/old \
  /tmp/icode-telemetry-probe.7glV33/old/.venv/bin/python \
  /tmp/icode-telemetry-probe.7glV33/mock_compare_probe.py old \
  /tmp/icode-telemetry-probe.7glV33/mock-compare/work \
  > /tmp/icode-telemetry-probe.7glV33/mock-compare-old.json
PYTHONPATH=/Users/dada/Projects/iCode/src:/Users/dada/Projects/iCode \
  /tmp/icode-telemetry-probe.7glV33/new-env/bin/python \
  /tmp/icode-telemetry-probe.7glV33/mock_compare_probe.py new \
  /tmp/icode-telemetry-probe.7glV33/mock-compare/work \
  > /tmp/icode-telemetry-probe.7glV33/mock-compare-new.json
python3 /tmp/icode-telemetry-probe.7glV33/compare_mock_reports.py
```

### 对拍结论

| 范围 | 实际结果 |
| --- | --- |
| 模型搭车 | 两版各发出 2 次 SDK HTTP 尝试，重试复用同一企业 `requestId`。归一化后两次 `body.telemetry` 逐字段一致，包含 session、`eventSubType=agent`、渠道、Agent 和项目字段；无轨迹时均省略 `spanId`。 |
| 可确定来源的工具与代码 | 每版 14 条报文逐字段一致：两次成功编辑各有 save/PENDING/成功终态及一条 ai-code，失败和拒绝各有 save/PENDING/终态。状态依次为成功 3→1、失败 3→2、拒绝 3→4；编辑行数均 1/1/1，片段分别 beta、alpha，原始参数、路径、缺省字段和关联 ID 一致。 |
| 重复终态 | 同一个 Result 输入事件在旧版产生 2 条成功终态，新版只发 1 条。因此原始独立 POST 总数为旧 18、新 17；这是新版按 execution/occurrence 去重的有意差异，不是生产后端去重证据。 |
| 无来源工具 | 旧版 save 回退到会话最近请求的 `requestId`、`parentSpanId`；新版省略 `requestId`、`spanId`、`parentSpanId`。其余字段一致。这是设计中已批准的历史错挂修正，不能记作原样一致。 |

结论限于上述场景：**可确定来源的字段、缺省规则、状态、逐次编辑和请求归属统一；存在重复终态去重和无来源关联两项明确差异。** mock 接收成功不等于生产入库成功，生产后端对缺省关联字段的处理及服务端幂等/去重仍未验证。

### 本轮测试

- 未新增产品代码或测试文件；现有契约测试与真实引擎测试覆盖本次探针的持久回归。Python 3.14.9 下运行 `pytest aixcoding/tests/telemetry -n0 -q -p no:cacheprovider`，**46 passed**。
- 同一环境运行 `test_settings_reload.py`、`test_web_search_budget.py`、等待清单、分层、Responses whole-run、Workflow retry、ACP prompt 和 client factory rollback，**367 passed**。合计 **413 passed**，无失败；本轮未重跑统一 `verify.py`，未绕过沙箱。

## 2026-11-12 独立代码审阅与当前剩余缺口

审阅时点为 **2026-11-12 10:25:51（上海，UTC+8）**。本次为当前主工作区的只读审阅，未修改文件，未使用 `.codebuddy/` 下的 worktree，未连接生产端点。

### 审阅结论与证据

- **未发现阻断缺陷，建议进入提交准备。** 该结论不等于全量验收完成，也不代表具备生产发布或最终验收条件。
- 审阅范围为排除 `.codebuddy/` 后的 **45 个未提交文件（23 个已跟踪、22 个未跟踪）**，分支 `main_aixcoding_cli_0.35.2`，HEAD `a752020b`。
- 已批准差异未扩大：重复终态只在具有执行或展示 occurrence 标识时去重；无来源工具不再回退到会话最近请求，只省略 `requestId`、`spanId`、`parentSpanId`，其余工具记录继续发送。
- 本地工具 operation 关联、托管工具实际 Content 来源、Start 原始参数、Result 实际快照、终态分类、ACP 元数据合并及技能记录均未发现越出已签口径的接线。
- Git TTL 刷新的 `await asyncio.to_thread(collect_git_info, cwd)` 合理，已按 `thread_pool / unresolved` 登记；既有 `call_next()` 等待保持原规则。清单共 **2925 个等待，解码无错误**。
- 使用主工作区 Git 文件清单并排除 `.codebuddy/` 后，R2、R3 和点级严格对账通过：**150 行登记、191 个 marker、0 警告**。原生门禁命令会把当前既有 worktree 目录识别为额外未跟踪路径，该结果不纳入本批评判，也不据此修改或删除该目录。

本次实际复跑结果：

- `uv run --no-sync --python 3.14.9 pytest aixcoding/tests/telemetry -n0 -q -p no:cacheprovider` → **46 passed**。
- `uv run --no-sync --python 3.14.9 pytest tests/orchestration/engine/test_settings_reload.py tests/orchestration/engine/test_web_search_budget.py tests/architecture/test_trajectory_wait_inventory.py tests/architecture/test_layering.py tests/service/llm/test_responses_whole_run.py tests/orchestration/workflows/test_agent_node_retry.py tests/app/acp/test_server_prompt_images.py tests/service/llm/test_client_factory_rollback.py tests/service/llm/test_anthropic_thinking_binding.py tests/kernel/test_loop_blank_response_resend.py -n0 -q -p no:cacheprovider` → **467 passed**。
- 上述两项合计 **513 passed**。本批 41 个 Python 文件的 Ruff 检查与格式检查、新增定制模块的 Darwin `ty check --error-on-warning`、`check_docs.py` 和 `git diff --check` 均通过。
- 本次审阅未重跑统一 `verify.py`，未绕过沙箱；统一验证的历史失败和限制仍按下文保持未关闭。

### 当前剩余验收缺口（以此节为准）

早期「验收缺口」保留为历史记录。其中追加输入技能、三种模型协议本地重试矩阵、长会话 Git 刷新和 ACP 取消已由后续记录关闭，不再列为当前缺口。当前仍有以下事项：

| 类别 | 当前缺口 | 关闭所需证据或决策 |
| --- | --- | --- |
| T03 文件与代码报文 | 空文件、纯删除、超过 64 个片段、binary 等边界尚缺持久化行为覆盖。 | 补真实写入/快照及逐字段报文断言，或由责任人明确拍板后续处置。 |
| T05 公共字段与凭据 | token/userId 优先级与切换、remote 选择、detached HEAD 等边界尚缺完整闭环。 | 补配置、凭据和真实 Git 场景的 wire 断言；不能以编码器单测替代全部边界。 |
| T07 生命周期与发送 | 禁用、重复 attach/detach、慢请求、排空超时等尚缺完整覆盖。 | 验证业务结果不受影响、订阅和资源释放、丢弃/失败计数及有界关闭。 |
| 入口与历史执行 | headless/TUI 入口及 fork/rollback/replay 仍缺闭环证据。 | 验证各入口实际接线；历史展示/恢复不重新上报，实际新执行照报。 |
| 测试资产约束 | 既有定制测试仍依赖上游 `tests/support` 和私有 fixture。 | 按开发规范 §9 收回依赖，并保留相同行为断言。 |
| 统一验证 | 既有统一入口仍有沙箱拒绝端口绑定/进程枚举，另观察到 TUI worker 退出和 `/tmp` 与 `/private/tmp` 解释器路径断言差异。 | 在允许的环境中复跑并逐项分类、处置；不得通过绕过沙箱或新增豁免冒充通过。 |
| 生产对账 | 生产入库、缺省关联字段的后端处理、服务端幂等/去重均无证据。 | 经另行授权后，在受控环境取得后台对账证据；本轮不连接生产端点。 |
| T08 升级演练 | 尚未在后续上游基线复用编码器和契约 fixture。 | 记录实际修改文件、行数、语义差异和适配成本；本次不提前执行。 |

上述缺口由后续补测/补证据，或由责任人明确决定延期及其他处置。**本次没有代为延期、豁免或关闭任何缺口。** 如责任人决定延期，应由本人明确记录范围、理由和期限；涉及规则豁免时另按 R13 处理。

### 需要责任人本人签认的文件与位置

以下事项必须由 **兰荣达（荣达）本人** 复核并编辑签认字段。AI 本次未改动任何 `责任人 / 状态 / 确认日期 / 确认意见`，聊天或口头过程批准不替代 R10 落盘。

| 文件 | 字段与对应正文位置 | 本人复核和签认原因 |
| --- | --- | --- |
| `aixcoding/docs/batches/telemetry-migration/design.md` | 头部第 4–7 行的 `状态 / 责任人 / 确认日期 / 确认意见`；对照「上游改动清单（R2）」的「文件」表、生成清单说明，以及「定制点登记预告」新增登记。 | 原签认后又补入 R2 的 17 个显式源码路径、`test_settings_reload.py` 与 `test_web_search_budget.py` 两项上游测试授权，并有补充等待和登记变化。荣达本人须逐项复核这些补充是否均为批准范围，再亲自更新签认；原确认意见只描述早期补充，不能由 AI 扩写为覆盖本轮。 |
| `aixcoding/docs/standards/adr/telemetry-migration--compatibility-adapter.md` | 头部第 3–6 行的 `责任人 / 状态 / 确认日期 / 确认意见`；对照「后果」中 R2 签认覆盖设计及逐行附件的说明。 | 按 DEVELOPMENT.md R10/§4.1，R2 清单变更须重签决策档。本人须确认本轮 R2 补充与 ADR 的兼容适配决策仍一致，并亲自更新签认。 |
| `aixcoding/docs/batches/telemetry-migration/self-review.md`（后续文件，当前不存在） | 将来文件头部的 `责任人 / 状态 / 确认日期 / 确认意见`，以及开发 AI、评审 AI 标识。 | 这是最终评审记录档，须待剩余证据、缺口处置和评审收敛完成后生成，再由责任人本人签认。当前不创建、不签认，也不把本次“未发现阻断缺陷”写成最终“评审结论：通过”。 |

`r2-review.md` 是 R2 范围附件，不设独立签认字段，其内容由上述 design/ADR 签认覆盖。`plan.md`、`verification.md`、`test-plan.md` 和 `requirements.md` 均为活文档，不另设 R10 签认。

### `self-review.md` 的当前处理

本次授权仅为整理待签材料。项目规则要求自评审记录在代码与验证完成、提 PR 前形成，并由责任人确认主要问题已处置；当前验收缺口尚未闭环，因此 **不创建最终 `self-review.md`，也不创建可能被误认为可最终签认的草案**。

后续生成前仍需：明确上述缺口哪些补测、哪些由责任人拍板延期或作其他合法处置；完成统一验证、生产对账和升级演练的应有证据；按双 AI 流程完成评审—处置—复审并记录未修项。责任人届时才决定最终评审是否可签，本次不预判结论。

### 本次文档整理检查

- 本次仅整理 `plan.md` 与 `verification.md`；design/ADR 的签认字段保持原样，未创建 `self-review.md`，未改产品代码、测试或 CodeIsland 相关文件。
- 尝试执行 `uv run --no-sync python aixcoding/tools/check_docs.py`，但当前非交互会话拒绝了 Bash 权限，命令**未执行**，因此不记为检查通过。本次未运行产品测试或统一 `verify.py`，未绕过沙箱。

## 2026-11-12 本轮 design/ADR 补充签认与文档检查

### 当前签认状态

截至 **2026-11-12 11:10（上海，UTC+8）**，design 与 ADR 的本轮补充签认均已由 **兰荣达本人完成（已亲签）**。协调者同时记录用户于该时点表示“已确认，可以继续”。本次仅据此更新活文档的当前状态，未修改 design、ADR 或任何签认字段；10:25 审阅节及上一回“当时仍待签认”“检查未执行”的陈述保留为当时事实。

已重新读取原文，客观字段证据如下：

| 文件 | 行号 | 状态 | 责任人 | 确认日期 | 确认意见 |
| --- | --- | --- | --- | --- | --- |
| `aixcoding/docs/batches/telemetry-migration/design.md` | 4–7 | 已确认 | 兰荣达 | 2026-11-12 | 已复核 |
| `aixcoding/docs/standards/adr/telemetry-migration--compatibility-adapter.md` | 3–6 | 已确认 | 兰荣达 | 2026-11-12 | 已确认 |

因此，plan.md 中仅“复核并更新 design/ADR 签认”对应事项已勾选完成。其余 T03/T05/T07 边界、headless/TUI、fork/rollback/replay、测试依赖收回、统一验证、生产对账、T08 升级演练及后续 `self-review.md` 均保持原状态；本次未关闭任何剩余测试或验收缺口，未创建 `self-review.md`。

### 文档检查（本轮补跑）

本节的实际执行结果在下方逐条记录；上一回权限拒绝导致未执行的历史记录不删除。

- `uv run --no-sync python aixcoding/tools/check_docs.py`：**未执行，无真实退出码**。当前非交互会话再次拒绝 Bash 权限，关键工具输出为 `Permission to use Bash has been denied ... permission prompts are not available in non-interactive mode`。这不是检查通过或失败结果。
- `git diff --check`：**未执行，无真实退出码**；收到相同的非交互 Bash 权限拒绝。
- 两条命令均未启动，因此没有命令自身的 stdout/stderr，也**未产生任何报告文件**。本次未更改权限、sandbox、settings 或 hook，未运行统一 `verify.py`、产品测试或补测，未连接生产端点。后续仍需由协调者在可执行机器 Shell 的环境补跑同一组命令。

#### 协调者机器 Shell 补跑结果（当前状态）

随后，协调者于 **2026-11-12 约 11:18（上海时间）** 在同一台机器、同一仓库 `/Users/dada/Projects/iCode` 使用可审批的机器 Shell 补跑上述命令。未改 CodeBuddy 权限，使用已存在环境并保留 `--no-sync`，未安装依赖、未修改锁文件、未加 `--closure`。上一回 CodeBuddy Bash 被拒且命令未启动的历史记录保留如上；以下为协调者补跑的真实结果。

1. `uv run --no-sync python aixcoding/tools/check_docs.py`
   - **退出码：0**。
   - stdout：

     ```text
     check_docs: scanned 25 ADR(s), 40 design(s), 38 self-review(s) under aixcoding/docs
     check_docs: OK
     ```

   - stderr：

     ```text
     warning: Using incompatible environment (`.venv`) due to `--no-sync` (The project environment's Python version does not satisfy the request: `Python 3.14.10`)
     ```

   - 实际解释器为 `/Users/dada/Projects/iCode/.venv/bin/python`，Python **3.14.8**。环境警告如实保留，不改写为目标解释器版本。
   - 检查工具本身只写 stdout/stderr，**不生成报告文件**。协调者另存的 `/tmp/cb-check-docs.stdout` 与 `/tmp/cb-check-docs.stderr` 只是会话输出捕获，不是检查工具产生的报告。

2. `git diff --check`
   - **退出码：0**；stdout 为空，stderr 为空。
   - 该命令**不生成报告文件**。`/tmp/cb-git-diff-check.stdout` 与 `/tmp/cb-git-diff-check.stderr` 均为空的会话捕获文件，不是命令生成的报告。

检查后批次目录无新增文件，未创建 `self-review.md`，未修改 `uv.lock` 或 `pyproject.toml`，工作区仍仅有既有文档改动。本次补跑只关闭文档检查的执行缺口，不关闭任何剩余测试、验收或生产对账缺口。

## 2026-11-12 文件、凭据、发送与入口恢复边界验证

本轮在 `main_aixcoding_cli_0.35.2` 的 `a752020b` 主工作区续作。新增断言落在 `aixcoding/tests/telemetry/`，共用该目录内的测试 fixture，通过进程内 MockTransport 捕获模型与上报 HTTP 请求。原有上游 fixture 依赖的收回仍是独立待办，本轮测试未新增该类依赖。

| 范围 | 验证证据 |
| --- | --- |
| T03 文件与代码 | 真实文件工具创建空文件时，工具终态行数为 0/0/0，纯删除编辑为 2/0/1，两者均无 ai-code。64 个替换生成 64 个逐行片段，65 个替换生成一个覆盖 1–130 行的全文片段。二进制编辑被拒绝，文件字节不变，无 ai-code。上游提供的解码快照依旧按旧规则报告 1/0/0。另验证编码器收到原始 bytes 快照时省略三个行数字段。 |
| T05 凭据与 Git | 同一 bus 和发送端依次覆盖配置回退、登录、环境 token 覆盖、换用户后恢复登录 token、清除登录后回退。检查实际 HTTP header 与 save 中的 userId。Git 在进程内替换只读 CLI 查询输出，断言 cnb → origin → 首个 remote 顺序，且 detached HEAD 在模型、工具和代码报文中省略分支。Git 配置用户名和邮箱仍进入 ai-code 的对应字段。 |
| T07 发送与生命周期 | 环境开关和配置开关均使模型请求省略 telemetry，且引擎照常完成。并发重复 attach 只建立一套订阅，重复 detach 安全，重新 attach 后恢复单次上报。慢 HTTP 在等待期间不阻塞事件处理。正常放行后按 save → update 发送两条；排空超时取消一条在途并丢弃一条排队记录，计数为 sent=0、failed=0、dropped=2，HTTP 客户端关闭。 |
| Headless 入口 | 通过 CLI 分发器进入真实 `run` 命令、会话 host 和引擎，检查 JSON 结果、首工具和模型的 requestId、sessionId 一致，以及退出前排空四条上报。通过 fixture 提供隔离启动配置和注册表。 |
| TUI 与历史 | 真实 Textual 应用恢复从两轮真实工具执行创建的 fork，挂载两轮历史工具卡。回滚到会话起点后清空历史。fork、恢复、回放和回滚均保持已有的 8 条上报、4 次模型请求。随后通过输入栏提交，实际编辑复用已回滚的 provider call ID，在 fork 会话中获得新 requestId，新增 4 条上报、2 次模型请求。测试隔离了与报文无关的状态栏原生 Git 文件监听。 |

二进制场景实际收到解码快照，经旧版 reporter 源码核对仍应计算行数，故调整了最初的测试预期，产品报文编码没有修改。

曾用同一场景验证 TUI 从 fork 的第二轮回滚到第一轮。该场景单跑通过过，合并回归出现 529 passed、1 failed。诊断确认回滚把 turn_counter=1 的快照实际复制到主文件与备份，发出了 RollbackResult，但随后引擎与界面仍保留两轮。原因未确认，已单列待办，不能用回滚到会话起点的测试替代。早期探针还遇到本机 FSEvents 启动失败及一次 Python Bus error。最终入口用例在测试内隔离原生监听，继续使用真实引擎、持久化、恢复和回放路径。

使用本仓库 `.venv/bin/python`，实际版本 **3.14.8**。所有 `uv run` 命令都带 `--offline --no-sync --no-python-downloads`，复用可写的既有 uv 缓存。uv 提示项目要求 3.14.10，现有 .venv 不兼容，因 `--no-sync` 继续使用。依赖和锁文件没有变动。

- `uv run --offline --no-sync --no-python-downloads pytest aixcoding/tests/telemetry -n0 -q --tb=short -p no:cacheprovider`，退出码 0，**63 passed**。
- 定向合并回归命令如下，退出码 0，**533 passed**。上游 fork/rollback 回归在此范围内，本次 TUI 非零回滚的间歇差异仍需单独复核。

  ```sh
  AIXCODING_EXTENSION_BASE_URL=https://telemetry.invalid \
    uv run --offline --no-sync --no-python-downloads pytest \
    aixcoding/tests/telemetry \
    tests/orchestration/engine/test_settings_reload.py \
    tests/orchestration/engine/test_web_search_budget.py \
    tests/architecture/test_trajectory_wait_inventory.py tests/architecture/test_layering.py \
    tests/service/llm/test_responses_whole_run.py \
    tests/orchestration/workflows/test_agent_node_retry.py \
    tests/app/acp/test_server_prompt_images.py \
    tests/service/llm/test_client_factory_rollback.py \
    tests/service/llm/test_anthropic_thinking_binding.py \
    tests/kernel/test_loop_blank_response_resend.py \
    tests/orchestration/engine/run/test_turn_rollback_fork.py \
    -n0 -q --tb=short -p no:cacheprovider
  ```

- `ruff check --no-fix` 与 `ruff format --check` 对本轮五个测试文件均退出 0，输出分别为 `All checks passed!` 和 `5 files already formatted`。同一 uv 环境运行 `python aixcoding/tools/check_docs.py` 退出 0，输出 `check_docs: OK`。 `git diff --check` 退出 0。
- 本轮没有运行统一验证、T08 或生产对账。这三项及最终 self-review 仍开放。

## 2026-11-12 TUI fork 非零回滚竞态

确认是产品侧持久化竞态。真实 TUI 恢复两轮 fork 并完成回放后，差异面板的后台刷新仍可能调用 `refresh_mutation_attribution()`。自然复现的调用栈从差异面板的 `load_current()` 到 `SessionLifecycle.refresh_mutation_attribution()`，再经 `SessionWriter.save_current_session()` 写入主文件和备份。非零回滚先将 `turn_2.json` 的 `turn_counter=1` 写入两份文件，然后等待轨迹记录，直到进入恢复调用前才启用保存抑制。后台刷新在这个窗口内可以把仍在内存中的 `turn_counter=2` 写回。恢复显式忽略 recovery sidecar，读取到的仍是已被覆盖的主文件。引擎与界面各保留两轮，`RollbackResult` 仍发出，`discarded_turn_count=1`、`superseded_turn_ids=[]`。

只观察调用和磁盘读写的探针曾通过，也连续三次自然复现失败。随后用两道 `asyncio.Event` 控制真实差异面板保存的放行顺序。存储写入、快照替换、轨迹记录、恢复及 TUI 回放都走原路径。以下四组分别执行，埋点开启时由进程内 MockTransport 接收报文，埋点关闭时捕获 0 条报文。

| 差异面板写入时点 | 埋点开启 | 埋点关闭 |
| --- | --- | --- |
| 快照替换前写完 | 通过。磁盘、引擎和 TUI 保留第一轮，结果标记第二轮已退役 | 通过，观察到相同恢复结果 |
| 快照替换后、恢复读取前写完 | 失败。磁盘、引擎和 TUI 各保留两轮，结果未标记第二轮退役 | 失败，观察到相同覆盖和恢复结果 |

在现有 Python **3.14.8** 上运行两次受控探针。命令为 `uv run --offline --no-sync --no-python-downloads pytest aixcoding/tests/telemetry/test_zz_nonzero_probe.py -n0 -q --tb=short -p no:cacheprovider`，其中一次加 `-s` 捕获轨迹。两次均退出 1，各 **2 passed、2 failed**，失败均为快照替换后放行写入的两组。uv 提示项目请求 Python 3.14.10，依照 `--no-sync` 使用现有解释器。临时探针从测试目录移出，保留本机复现证据供补签后的回归使用。

建议在 `src/chrys/orchestration/engine/rollback.py` 与 `src/chrys/orchestration/engine/session_lifecycle.py` 协调非零回滚与改动归属保存。快照替换前等待已在途的归属保存完成，阻止新的旧状态保存，恢复完成后再开放。单纯将保存抑制提前无法拦住已通过检查、正在写盘的保存。补签后用受控时序覆盖在途写入和回滚期间的新刷新，核对保留轮次、退役 ID、TUI 回放和 mock 报文数。两处产品文件均在本批已签 R2 范围之外，待负责人批准具体差异后实施。当前保持该验收项开放。

### 待签范围与验收

兰荣达在监工聊天授权「让codex自主判断吧，我没空把控」。技术方案和测试范围由 Codex 确定。按 AGENTS.md 与 DEVELOPMENT.md §4.1、R2、R10，新增上游修改范围的实施凭据是责任人本人在 design 与 ADR 的落盘签认。既有签认仅覆盖原 R2 清单。以下内容供补签，现有签认正文及字段保持原样。

| 拟新增 R2 路径 | 落点、改动与预估净行数 |
| --- | --- |
| `src/chrys/orchestration/engine/session_lifecycle.py` | 在 `SessionLifecycle` 增加后台归属保存的互斥与暂停范围。在 `refresh_mutation_attribution()` 保存前复核会话代际、tracker/coordinator 身份和原有运行中条件，受暂停或过期的刷新不消费待保存标记。已接纳保存持有互斥，使用现有取消保护确保实际写入结束后才释放，避免 TUI worker 取消时线程仍在写。预计增加约 25–35 行，替换约 5–8 行。 |
| `src/chrys/orchestration/engine/rollback.py` | `on_user_rollback()` 在既有会话转换许可内，仅对 `target_turn > 0` 的执行先暂停后台归属保存，等已接纳写入完成，再执行快照替换和恢复。用上下文退出保证异常或取消后解除暂停。排空完成即释放互斥，先于回滚取文件锁、恢复与发布回滚结果。保留回滚到起点的路径和回滚文件后主动保存的语义。预计增加约 5–8 行接线，另有同一调用块缩进调整。 |
| `tests/architecture/trajectory_wait_manifest.json` | 本路径已在原清单。新增等待或重新打开的等待条目在实现后按实际生成差异逐条复核和报批，当前没有更新或预先登记。 |

这两处协调属于上游会话持久化。现有 telemetry 订阅看见的 `RollbackResult` 已在覆盖和恢复之后，无法为上游写入提供互斥。仅提前启用保存抑制挡不住已开始的写入。将同步文件锁跨异步恢复持有会与恢复所需的同一把锁相冲突。

正式回归放在 `aixcoding/tests/telemetry/`，复用本目录 fixture。第一组在旧状态保存已接纳后启动回滚，在进入排空边界时放行保存，记录写入先于快照替换。该组不能以“已替换快照”作为放行条件，否则会阻塞修复后的正确路径。第二组在替换后、恢复前发起归属刷新，验证它无法写入旧历史。再覆盖保存调用者取消、无竞争的非零回滚和回滚到起点。通过条件是主文件与备份、引擎轮次和 TUI 工具卡一致，退役 ID 只含被丢弃的轮次，回放不增加模型请求或 mock 上报。

本轮增强临时探针，在放行写入前核对主文件与备份均为一轮，并在恢复后同时断言两份文件、引擎轮次、界面、退役 ID、模型调用数和 mock 上报数。以现有 Python 3.14.8 执行 `uv run --offline --no-sync --no-python-downloads pytest aixcoding/tests/telemetry/test_nonzero_rollback_review.py -n0 -q -s --tb=short -p no:cacheprovider`，退出 1，**2 passed、2 failed**。提前写入的两组通过，延后写入的两组均直接观察到主文件与备份恢复成两轮。uv 报告项目要求 3.14.10。复现脚本与日志保留在本机临时目录，定制测试目录未留下失败用例。


### 2026-11-12 14:47 新增 R2 范围授权代为落盘

截至本节写入时，上节「待签范围与验收」所述实施前置条件已按用户明确授权完成落盘。这不是全量验收，也不关闭统一验证、T08、生产对账或最终 self-review。

- 授权人：兰荣达
- 授权依据：2026-11-12 14:47（上海时间，UTC+8）监工聊天原话「我授权你可以去帮我通过签字」
- 记录人：Grok Bot（AI 代理）
- 落盘说明：由 AI 代理经用户明确授权代为写入补充签认段，不是兰荣达本人亲自编辑、手签或数字签名。
- 已落盘位置：
  - `design.md` 新增「2026-11-12 新增 R2 范围补充签认（非零 rollback 与后台保存竞态）」。原文头部 11:06 本人签认字段保持原样。
  - `aixcoding/docs/standards/adr/telemetry-migration--compatibility-adapter.md` 新增同名补充签认段。原文头部 11:10 本人签认字段保持原样。
- 已确认范围仅限：`src/chrys/orchestration/engine/session_lifecycle.py` 与 `src/chrys/orchestration/engine/rollback.py`，用于协调非零 rollback 与后台归属保存竞态。修法意图为暂停新的后台保存、等待已有保存完成、替换快照并恢复后再开放；具体最小实现不在本记录中锁定。
- 不包括：等待清单新增或扩大项、全量验收，以及其他未列明范围。

### 非零回滚修复与定向回归

`RollbackController.on_user_rollback()` 在既有会话转换许可内，为非零回滚暂停后台归属保存。进入暂停后先排空已接纳的写入，再执行原有快照替换与恢复。进入回滚的文件锁和事件发布路径前，已释放用于排空的异步锁。`SessionLifecycle.refresh_mutation_attribution()` 复核代际、tracker、coordinator 与运行状态，再消费待保存标记。后台调用者取消时，保存任务仍由本次刷新等待至完成，释放互斥后才传播取消。已有回滚到起点路径和恢复后按需主动保存保留原有行为。两处产品范围的四个 R3 标记已登记到 design 的定制点表，原签认字段与补充签认段未修改。

正式回归放在 `aixcoding/tests/telemetry/test_entrypoints.py`，复用本目录 fixture。覆盖真实 TUI fork 无竞争非零回滚、回滚到起点、替换快照后强制归属刷新、回滚等待在途保存、保存调用者取消。非零场景同时断言主文件、备份、引擎、TUI、退役轮次 ID 和 mock 上报，并继续验证实际重跑复用旧调用 ID 时归到新的请求。新增「替换快照后刷新」用例在修复前失败（退出 1，1 failed），引擎保留了应退役的第二轮。

使用现有 Python **3.14.8**。以下命令均经 `uv run --offline --no-sync --no-python-downloads`，uv 报告项目要求 3.14.10。测试运行时把未替换的扩展地址设为 `https://telemetry.invalid`。T03/T05/T07 本轮未重跑。

- `pytest aixcoding/tests/telemetry/test_entrypoints.py tests/orchestration/engine/run/test_turn_rollback_fork.py -n0 -q --tb=short -p no:cacheprovider` 退出 0，**9 passed**。
- 扩展定向回归使用下列 pytest 参数，退出 1，**478 passed、1 failed**。唯一失败为 `test_background_tasks_have_declared_owners`，见下节。

  ```sh
  pytest aixcoding/tests/telemetry/test_entrypoints.py \
    tests/orchestration/engine/test_rollback*.py +    tests/orchestration/engine/test_session_restore.py +    tests/orchestration/engine/test_reset_session_to_welcome.py +    tests/orchestration/engine/run/test_turn_rollback*.py +    tests/app/tui/screens/main/test_diff_controller.py +    tests/app/tui/screens/main/test_rollback_controller.py +    tests/architecture/test_layering.py -n0 -q --tb=short -p no:cacheprovider
  ```

- `pytest tests/architecture/test_trajectory_wait_inventory.py -n0 -q --tb=short -p no:cacheprovider` 退出 1，**56 passed、1 failed**。唯一失败为等待清单与源码对账。
- Ruff 检查与格式检查覆盖两个产品文件及入口回归文件，`ty check --error-on-warning --python-platform <darwin|linux|win32> src/chrys` 三平台检查均通过。
- `python aixcoding/tools/check_docs.py` 和 `git diff --check` 均退出 0。首次运行 `gen_customizations.py --strict` 时，工具自动递归读到旧后台工作树，退出 1，28 条错误均指向该目录。没有修改该目录。随后在独立进程用 `git ls-files --cached --others --exclude-standard` 限定主工作区候选路径并排除该目录，调用同一工具的 `run_check(strict=True)`，退出 0，**154 条登记、195 个标记，0 warning**。此结果仅证明主工作区登记匹配。

### 门禁待登记项

当前两项门禁仍开放。用等待清单扫描器在内存比较已登记与实际等待，候选文本差异 **+6/−1**。未写入仓库清单。

| 位置 | 现有登记与候选差异 |
| --- | --- |
| `RollbackController.on_user_rollback:7` | 原 wrapper 替换为 `async with pause_saves`，类型为 async_context |
| `RollbackController.on_user_rollback:8` | 原序号 7 的执行 wrapper 移到序号 8，目标仍是 `_execute_user_rollback_with_permit` |
| `SessionLifecycle.pause_mutation_attribution_saves:1` | 新增 `async with self._attribution_save_lock`，类型为 sync_primitive |
| `SessionLifecycle.refresh_mutation_attribution:2` | 原直接保存 await 替换为同一异步锁，类型为 sync_primitive |
| `SessionLifecycle.refresh_mutation_attribution:3` | 新增受取消保护的保存等待，类型为 wrapper，目标为 `chrys.foundation.util.once_close.finish_close` |

生成器共重新打开 12 个位置，包括上表 5 个位置，以及等待数发生变化的函数内 7 个未变位置（`on_user_rollback:1–6`、`refresh_mutation_attribution:1`）。未变位置的原规则均为 `unresolved`。

任务所有权门禁需要在 `tests/architecture/test_layering.py::test_background_tasks_have_declared_owners` 增加一条记录（预计 4 行），键为 `("session_lifecycle", "SessionLifecycle", "refresh_mutation_attribution")`，计数 1。任务归当前归属刷新所有，保存结束前持有异步锁，取消由 `finish_close` 排空后传播，非零回滚通过同一把锁等待其结束。该上游测试文件超出本轮授权，等待清单条目也未获追加批准。

本轮没有运行统一验证、T08 或生产对账，最终 self-review 仍待开展。

### 2026-11-12 15:07 新增 R2 范围授权代为落盘

截至本节写入时，上节「门禁待登记项」所述两项登记的追加 R2 范围已按用户明确授权完成落盘。登记本身尚未写入仓库。这不是全量验收，也不关闭统一验证、T08、生产对账或最终 self-review。

- 授权人：兰荣达
- 授权依据：2026-11-12 15:07（上海时间，UTC+8）监工聊天原话「授权补任务所有权记录和等待清单，并由你代为落盘确认。」
- 记录人：Grok Bot（AI 代理）
- 落盘说明：由 AI 代理经用户明确授权代为写入补充签认段，不是兰荣达本人亲自编辑、手签或数字签名。
- 已保留未改：design 与 ADR 头部的本人签认字段，以及 14:47 代为落盘的补充签认段与本节之前的验证正文。
- 已落盘位置：
  - `design.md` 新增「2026-11-12 新增 R2 范围补充签认（回滚修复的任务所有权与等待清单登记）」。
  - `aixcoding/docs/standards/adr/telemetry-migration--compatibility-adapter.md` 新增同名补充签认段。
  - `plan.md` 第 76 条已改写为「追加 R2 已确认、登记尚未写入」，该项仍未勾选。
- 已确认范围仅限本轮回滚修复必要的两项登记，并以 2026-11-12 15:08（上海时间）对当前工作区清单的内存对账为准：
  - `tests/architecture/test_layering.py`：`test_background_tasks_have_declared_owners` 增加一条记录，键 `("session_lifecycle", "SessionLifecycle", "refresh_mutation_attribution")`，计数 1。
  - `tests/architecture/trajectory_wait_manifest.json`：候选文本差异 +6/−1，等待条目 2925→2928，仅涉及 `on_user_rollback`（插入 `async with pause_saves` 并将原执行 wrapper 移到序号 8）、新增 `pause_mutation_attribution_saves:1`（`async with self._attribution_save_lock`），以及 `refresh_mutation_attribution` 将原直接保存替换为同一把锁并新增受 `finish_close` 保护的保存等待。对账使用 `tests.support.trajectory_wait_inventory`，仓库清单当时未改。
- 不包括：全量验收、统一验证、T08、生产对账，以及其他未列明范围。实施中若出现额外未知差异，不得捎带登记。

### 回滚修复登记与门禁复跑

- `tests/architecture/test_layering.py` 增加一条任务所有权记录，键为 `("session_lifecycle", "SessionLifecycle", "refresh_mutation_attribution")`，计数 1。刷新持锁直到 `finish_close` 等完写入，非零回滚等待同一把锁再替换快照。原门禁断言未改。R3 标记在 design 的定制点表登记，原签认字段和两段补充签认原文未改。
- `tests/architecture/trajectory_wait_manifest.json` 以官方扫描器 `build_manifest` 和 `encode_manifest` 重新生成。新候选与 15:08 审阅稿逐字节相同。清单 **+6/−1**，等待 **2925→2928**。变更仅在批准的三个函数，涉及 5 个新增或变更位置。共重新打开 12 个位置，其余 7 个位置的表达式与规则保持原值，所有重新打开的位置均为 `unresolved`。写入后用 `cmp` 核对仓库文件与审阅稿一致，退出 0。

测试使用现有 Python **3.14.8**。uv 提示项目要求 **3.14.10**，依照 `--no-sync` 使用现有环境。以下三条 pytest 命令均以 `AIXCODING_EXTENSION_BASE_URL=https://telemetry.invalid` 运行，统一使用 `uv run --offline --no-sync --no-python-downloads`，pytest 参数均为 `-n0 -q --tb=short -p no:cacheprovider`。

| pytest 路径参数 | 结果 |
| --- | --- |
| `tests/architecture/test_layering.py::test_background_tasks_have_declared_owners tests/architecture/test_trajectory_wait_inventory.py` | 退出 0，**58 passed** |
| `aixcoding/tests/telemetry/test_entrypoints.py tests/orchestration/engine/run/test_turn_rollback_fork.py` | 退出 0，**9 passed** |
| 下列扩展回归，沿用上一轮路径 | 退出 0，**479 passed** |

```sh
pytest aixcoding/tests/telemetry/test_entrypoints.py \
  tests/orchestration/engine/test_rollback*.py \
  tests/orchestration/engine/test_session_restore.py \
  tests/orchestration/engine/test_reset_session_to_welcome.py \
  tests/orchestration/engine/run/test_turn_rollback*.py \
  tests/app/tui/screens/main/test_diff_controller.py \
  tests/app/tui/screens/main/test_rollback_controller.py \
  tests/architecture/test_layering.py -n0 -q --tb=short -p no:cacheprovider
```

`ruff check --no-fix` 与 `ruff format --check` 检查任务所有权文件，`python aixcoding/tools/check_docs.py` 和 `git diff --check` 均退出 0。T03/T05/T07 未重跑。统一验证、T08、生产对账、定制测试 fixture 依赖清理和最终 self-review 仍开放。

### 埋点测试依赖清理与统一验证

| 测试 | 收回的依赖与替代实现 |
| --- | --- |
| `test_model_wire.py`、`test_tool_reports.py` | 收回上游 Responses 流式/阻塞报文生成、模型配置、终态等待和整轮执行辅助。进程内报文构造落在 `_responses.py`，复用真实引擎和 SDK 的测试辅助落在 `_engine.py`。两个文件共用该辅助层，不再从另一个测试模块导入执行函数。保留真实 HTTP 请求、独立报文、重试事件和终态的断言。 |
| `test_correlation.py` | 复用自有 Responses 报文和模型配置。以真实 `ChrysSessionHost` 执行并确认工作流，仅用事件控制本场景的节点超时，保留模型调用次数、恢复后工具不重报和请求归属断言。 |
| `test_acp_metadata.py` | 收回上游 ACP host、manager、client 私有替身。用真实 server、manager、host，测试内替换该轮事件输入以覆盖正常和取消终态。保留通知的 JSON 校验，并核对 `chrys/turn_started` 与响应中的轮次 ID。 |

新增两个文件均在 `aixcoding/tests/telemetry/`。按照 DIRECTORY.md §6，进程内测试专用替身与数据构造归定制测试目录。本轮没有新增需要单独启动的 mock 服务。没有修改产品代码、上游测试设施、等待清单或签认文档。AST 扫描 `aixcoding/tests` 与 `aixcoding/mock` 的 78 个 Python 文件，退出 0，发现 0 个对上游 `tests` 包的绝对导入。`uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_import_boundaries.py` 退出 0，扫描 1248 个文件。

使用现有 `.venv` 的 Python **3.14.8**，uv 提示项目要求 **3.14.10**。两次定向和扩展验证均以 `AIXCODING_EXTENSION_BASE_URL=https://telemetry.invalid` 运行，最后一轮结果如下。

```sh
uv run --offline --no-sync --no-python-downloads pytest \
  aixcoding/tests/telemetry/{test_acp_metadata,test_correlation,test_model_wire,test_tool_reports}.py \
  -n0 -q --tb=short -p no:cacheprovider

uv run --offline --no-sync --no-python-downloads pytest \
  aixcoding/tests/telemetry/{test_acp_metadata,test_correlation,test_model_wire,test_tool_reports,test_entrypoints}.py \
  aixcoding/tests/tools/test_check_import_boundaries.py \
  tests/app/acp/test_server_prompt_images.py tests/orchestration/workflows/test_agent_node_retry.py \
  tests/service/llm/{test_responses_whole_run,test_client_factory_rollback,test_anthropic_thinking_binding}.py \
  tests/kernel/test_loop_blank_response_resend.py \
  -n0 -q --tb=short -p no:cacheprovider
```

定向退出 0，**41 passed**。扩展退出 0，**209 passed**。未单独重跑 T03/T05/T07，统一入口按其正常语义运行完整定制套件。

随后运行统一入口，未关闭任何检查。完整输出留在本机 `/tmp/icode-telemetry-probe.7glV33/verify-fixture-cleanup-final.log`。

```sh
AIXCODING_EXTENSION_BASE_URL=https://telemetry.invalid \
  uv run --offline --no-sync --no-python-downloads python aixcoding/tools/verify.py --smart --paths \
  aixcoding/tests/telemetry/{_engine,_responses,test_acp_metadata,test_correlation,test_model_wire,test_tool_reports}.py
```

- 统一入口退出 **1**。完整定制套件退出 **1**，**612 passed、47 skipped、71 failed、17 errors**。88 个失败或错误均在 `socketserver.py:478` 调用 `socket.bind()` 时遇到 `PermissionError: [Errno 1] Operation not permitted`。涉及认证、登录对话框和独立 HTTP mock 服务用例。沙箱未调整。
- 上游 Smart Test 退出 **0**，为分析 fixture 收集了 39492 项候选，按本轮六个定制 Python 文件最终选择 **0 项**，没有执行上游测试。此前的 `sysctl()` 权限拒绝、TUI worker 退出和 `/tmp` 与 `/private/tmp` 断言差异未在本次日志中出现，其对应场景未通过本次上游统一入口复核。实际运行的上游定向范围见前述 209 项扩展命令。
- 六个文件的 Ruff 检查与格式检查、`check_docs.py` 和 `git diff --check` 均退出 0。依赖清理本身无需新增 R2 授权。统一验证继续开放，T08、生产对账和最终 self-review 未启动。

### 2026-11-12 统一验证日志核验与 CodeBuddy 静态复核记录

本节由 Grok Bot 于 2026-11-12 16:18（上海时间，UTC+8）落盘。日志核验使用用户明确授权的本机机器工具完成，不是 CodeBuddy 独立复跑或读取日志。授权依据：用户回答授权卡 t133s752 的原话「允许用本机工具读取本轮两份验证日志，并补写 plan.md 和 verification.md，不扩大其他权限。」未改 settings、CLI permission-mode、CodeIsland、hook，未使用 `-y`，未绕过测试沙箱，未重跑测试、未绑定端口、未安装依赖。原签认字段与此前各节原文未改。

#### 核验的日志

先限定列出 `/tmp/icode-telemetry-probe.7glV33/`，只读取本轮两份统一验证日志，未打开同目录其他文件：

| 路径 | 修改时间（上海时间） | 大小 | SHA-256 | 行数 |
| --- | --- | --- | --- | --- |
| `/tmp/icode-telemetry-probe.7glV33/verify-fixture-cleanup-final.log` | 2026-11-12 15:30:45 | 241587 字节 | `f45e12ef54a3fb43f14d38cb245c262802a6c47ff6de1121823409e983da3c3a` | 4548 |
| `/tmp/icode-telemetry-probe.7glV33/verify-fixture-cleanup.log` | 2026-11-12 15:28:32 | 241587 字节 | `a18a08ed7a77652aae38a9a6b58e23a3cc7d04fc5d6107630aef71d4bf7a98ea` | 4548 |

二者不是同一份拷贝。差异限于 xdist 进度条顺序、对象地址、pytest 临时目录（`pytest-122` 与 `pytest-125`）和耗时（10.78s 与 11.30s）。失败/错误 nodeid 集合与堆栈分类完全一致。verification 此前引用的是 `-final` 日志。下文行号以该文件为准。

两份日志开头均为 uv 提示项目要求 Python **3.14.10**、实际使用现有 `.venv`（第 1 行），以及 `platform darwin -- Python 3.14.8`（第 3 行）。这只能证明 3.14.8，不能写成目标 3.14.10 验收通过。本次未用 3.14.10 复跑。

#### 计数与 88 项堆栈逐条分类

`Fork verify Summary: FAILED (exit 1)`（第 4546 行）。定制套件退出 1（第 4547 行）；进度条字符统计与摘要一致，均为 **612 passed、47 skipped、71 failed、17 errors**，合计 747 项（第 4530、4547 行）。与 Codex 记录的计数一致。

短摘要列出 71 条 `FAILED` 与 17 条 `ERROR`，共 88 项（第 4441–4529 行）。已逐份阅读对应堆栈（`ERRORS` 第 25–868 行，`FAILURES` 第 869–4440 行）：

- 全部 88 项的失败行均为 `>       self.socket.bind(self.server_address)`，终端异常均为 `PermissionError: [Errno 1] Operation not permitted`，标注位置均为 `socketserver.py:478`。日志中 `socket.bind` 出现 88 次。
- 17 项 `ERROR` 均发生在 fixture setup：`test_auth_server.py` 3 项、`test_model_catalog_server.py` 14 项。
- 71 项 `FAILED` 均发生在测试体启动本地 mock HTTP 服务时，同样停在首次 `bind`，不是断言失败或级联的二次异常。
- 按文件：`test_update_server.py` 36 failed；`test_model_catalog_server.py` 14 error + 10 failed；`test_session_logging.py` 8 failed；`test_auth_session.py` 6 failed；`test_auth_server.py` 3 error + 1 failed；`test_auth_delegation.py` 3 failed；`test_login_dialog.py` 3 failed；`test_auth_client.py` 2 failed；`test_composition_lifecycle.py` 1 failed；`test_mock_launcher.py` 1 failed。
- 包括 `test_second_instance_on_a_taken_port_is_refused` 在内，也是第一次 `bind` 即被拒绝，不是 `EADDRINUSE` 或“端口已被占用”的业务断言失败。
- 两份日志中均未出现 `AssertionError`、`TimeoutError`、`ConnectionRefused`、`EADDRINUSE`、`OSError`、`sysctl`、`TUI worker` 或 `/private/tmp`。未见其他根因、级联错误或漏分类项。

因此，Codex 关于「88 个失败或错误均在 `socket.bind()` 处遇到沙箱式 `PermissionError`」的归因，已由本次本机读日志核验确认。这仍是环境/沙箱阻塞，不是这六个埋点测试文件引入的产品缺陷。统一验证入口结果仍为退出 1，不能记为通过，也不应为此放宽或关闭检查。

#### 上游 Smart Test 选中 0 项的含义

第 4532–4544、4548 行：Smart Test 发现上述六个定制 Python 路径，分析了 39492 项非集成候选后，`Initial selection: 0`，最终执行范围 `0 targets / 0 of 39492`，并写明 `Smart Test found no applicable pytest tests for these non-runtime changes.` 上游栏为 `passed  exit 0`。该退出码只表示选择器在没有可运行上游测试时正常结束，**没有执行任何上游测试**，不能当作上游套件通过。历史 `sysctl()`、TUI worker 退出和解释器路径差异未在这两份日志中出现，也因本次上游未选中用例而未被统一入口复核。

#### CodeBuddy 15:38–15:49 静态复核与当时权限阻塞

原 CodeBuddy session `01a1cd80-abc2-7513-8cd4-b0fdcc46e722` 于 15:38:13 以 `--resume -p` 启动，15:49:31 结束。该回合对六个文件做了静态阅读与检索，**未修改任何文档或代码**。其结论仅以当时可读源码为限，且因非交互模式无法弹出批准而未能核日志或复跑命令：

- Bash（只读 `git status`/`diff --stat`）、两份 `/tmp` 日志的 Read 与 Grep、以及向 `verification.md` 追加结论的 Edit，均返回同一句：`this tool requires approval but permission prompts are not available in non-interactive mode`。不是用户点拒绝，也不是审批超时。
- 静态所见：四个测试已切到 `_responses.py` / `_engine.py` 或真实 host；目录枚举 66 个定制测试 Python 文件 + 12 个 mock Python 文件 = 78 个；未发现对上游 `tests` 包或 `tests/support` 的导入，也未发现 `__import__` / `import_module` / `runpy` 等动态引入上游测试设施的文本路径。`check_import_boundaries.py` 本身是 AST 导入检查，不能单独证明所有运行时动态导入不存在。
- 四个测试按参数展开为 3+4+22+12=41 项，与定向 41 项范围吻合。`test_acp_metadata.py` 覆盖的是正常/取消终态的响应元数据，不应扩大解释为完整真实取消请求链验收。
- 因当时无法执行 `git diff` 和动态测试，该回合不宣称逐行差异已完整机器核验，也不把 Codex 的日志结论升级为 CodeBuddy 已证明事实。

T08、生产对账和最终 self-review 仍开放，本次未实施升级，未创建 `self-review.md`。

### 2026-11-12 R2 文件列表同步与主工作区严格对账复跑

本节由 Grok Bot 于 2026-11-12 16:53:32（上海时间，UTC+8）落盘。依据：用户 t125 已授权代为落盘 `rollback.py` / `session_lifecycle.py` 范围（14:47 补充签认段 `design.md` 371–383），t129 授权登记；本次只把同一已授权范围同步进 design「上游改动清单（R2）」的「文件」列，供 `check_r2_diff.py` 读取，不扩大范围，不修改头部本人签认字段，不伪造新的本人签名。活文档补记使用用户已有的文档授权。未改产品、测试、门禁代码，未改 `.codebuddy/`，未安装依赖，未绕过沙箱，未暂存或提交。

#### 表格同步

`design.md` 头部签认字段保持原样：状态「已确认」、责任人「兰荣达」、确认日期「2026-11-12」、确认意见「已复核」。14:47 与 15:07 两段补充签认原文未改。R2 表仅追加两行，行数来自当时工作区相对 `a752020b` 的 `git diff --numstat`：

- `src/chrys/orchestration/engine/rollback.py`：+14/−9。非零回滚（`target_turn > 0`）在快照替换和恢复前暂停新的后台保存，并等待已接纳写入完成。
- `src/chrys/orchestration/engine/session_lifecycle.py`：+32/−7。为后台改动归属保存增加互斥与暂停范围；保存由 `finish_close` 排空。

未追加第三条路径。补表前，官方 `check_r2_diff.py --base a752020b` 将上述两路径列为未授权，另有 `.codebuddy/worktrees/bg-01a1c9d3/` 假阳性。补表后这两路径为 `approved (changed)`，批准池 112→114。

#### 复跑命令与结果

实际解释器为 `.venv` 的 Python 3.14.8，`uv run --no-sync` 提示不满足项目要求的 3.14.10。未因此安装或切换解释器。原始输出在 `/tmp/icode-strict-20261112-1652/`。

| 命令 | 退出码 | 主工作区真实结果 | 原生输出中的已知工作树假阳性 |
| --- | --- | --- | --- |
| `uv run --no-sync python aixcoding/tools/check_docs.py` | 0 | `check_docs: OK`（25 ADR / 40 design / 38 self-review） | 无 |
| `git diff --check -- . ':(exclude).codebuddy'` | 0 | 无空白错误 | 无 |
| `uv run --no-sync python aixcoding/tools/gen_customizations.py --strict` | 1 | 28 条 ERROR 全部位于 `.codebuddy/worktrees/bg-01a1c9d3/`，主工作区 0 条 | 这 28 条即为原生递归扫到后台工作树的已知假阳性，与 `verification.md` 既有记录同类。未改工具、未删该目录 |
| 同一工具 `run_check(strict=True)`，候选路径为 `git ls-files --cached --others --exclude-standard` 并排除 `.codebuddy/`（3416 条） | 0 | `check OK — 155 registration row(s) / 196 marker(s) across 18 design(s), 7 retired id(s), 0 warning(s)` | 不适用（已排除） |
| `uv run --no-sync python aixcoding/tools/check_r2_diff.py --base a752020b` | 1 | 本批两路径已批准且为 changed；排除工作树后无未授权上游改动。`changed=54`（53 批 + 工作树目录），`upstream_changed=24`，`approved_pool=114` | 唯一 ERROR 仍是 `.codebuddy/worktrees/bg-01a1c9d3/`。另有其他批次既有警告（如 `branding-and-command` 的「同上」/「文件」行被忽略），与本批无关 |
| `uv run --no-sync python aixcoding/tools/check_r3_markers.py --base a752020b` | 1 | `upstream_changed=24`，`marker_checked=22`；排除工作树后本批无违规 | 唯一违规是 `.codebuddy/worktrees/bg-01a1c9d3/`（无后缀，扫描器无法核 marker） |

官方原生门禁命令的退出码 1 予以保留记录，不得解释为「门禁已改」或「全量通过」。判断本批机器门禁时，应把上述工作树假阳性与主工作区结果分开。未改登记器或门禁工具去收窄扫描范围。

本记录不表示统一验证通过、不表示上游 Smart Test 已执行、不表示目标 Python 3.14.10 已满足，也不关闭 T08、生产对账或最终 `self-review.md`。统一验证仍为退出 1（沙箱 `socket.bind` 的 `PermissionError`）；上游 Smart Test 仍为选中 0 项。未创建 `self-review.md`，未暂存或提交。
### 2026-11-12 自评审草案创建

本节由 Grok Bot 于 2026-11-12 17:08:19（上海时间，UTC+8）落盘。依据：用户 t142u 原话「可以继续」，授权继续规范流程（创建明确未完成/待签的 self-review 草案，并安排原 CodeBuddy session 补审 HOWTO §二此前未覆盖项）。不扩大 t125/t129 代签，不自动开展 T08 或生产对账，未暂存或提交。

已创建 [self-review.md](self-review.md)，头部状态为「草案」，责任人 / 确认日期 / 确认意见留空，结论为「未完成（待规范补审与责任人签认，不作为最终通过）」。开发 AI 与 16:25–16:39 独立审阅的 CodeBuddy 标识已如实记录。父 bot 核对摘要不是正式第二审。`plan.md` 第 81 项保持未勾选。

统一验证、上游 Smart Test 0 项、Python 3.14.8≠3.14.10、T08 与生产对账等限制仍以本节之前的记录为准，均不得记为通过。本步只增加评审记录与活文档指向，未改产品、测试或门禁代码，未改 `.codebuddy/`。
### 2026-11-12 HOWTO §二补审归档

本节由 Grok Bot 于 2026-11-12 17:28:05（上海时间，UTC+8）落盘。依据：用户 t145u 原话「继续接下来的任务」，授权将 CodeBuddy 补审结论归档到自评与活文档，并在确认 t129 已覆盖同一路径后，把 `test_layering.py` 同步进本批 R2「文件」列。不扩大旧代签，不自动开展 T08 或生产对账，未暂存或提交。

CodeBuddy `kimi-k3.1-pro` 原 session `01a1cd80-abc2-7513-8cd4-b0fdcc46e722` 于 17:10:54–17:22:45 完成 HOWTO §二准确范围补审（完整输出 `/tmp/cb-icode-howto-s2-review.out`）。该回合未发现新的 blocking 代码缺陷；Edit 与只读 Git、`check_docs.py --closure` 均因非交互权限被拒，CodeBuddy **未改任何文件、也未亲自跑出 closure 退出码**。

不得把补审原文里的过时状态写成当前事实：当时引用的「`--closure` 退出 1 / 草案 forbidden / 最终签认仍开放」对应 17:08 草案且签认留空。责任人已于 17:16 将状态改为「已确认」；协调者于 17:17 重跑普通 `check_docs.py` 与 `--closure`，均为退出 0。

补审 N1（nonblocking）：`tests/architecture/test_layering.py` 已在 15:07 / t129 补充签认中批准（`design.md` 该段明确列出同一路径与所有权登记目的），与 `890e2ec7` 中 +8/−0 一致。已把该已授权路径追加进本批 R2「文件」列，未追加其他文件，未改 design 头部本人签认字段。

[self-review.md](self-review.md) 正文已追加上述补审证据，并更正「签认栏留空」等过时当前时态；头部四字段保持责任人填写原样。`plan.md` 第 81 项保持未勾选。统一验证、上游 Smart Test 0 项、Python 3.14.8≠3.14.10、T08 与生产对账仍不得记为通过。

### 本地收尾与验收前置

2026-11-12 收尾由本线程 Codex 执行。核对四份文档及实际差异，确认 N1 仅同步既有 R2 授权，暂存的 `self-review.md` 与 17:28 归档逐字节一致。正常本地提交 `9dd573eb` 归档 design、plan、verification 和 self-review。原签认字段保持原样。 `check_docs.py --closure` 与暂存差异空白检查均退出 0。未推送。

为补足上一轮只传定制测试路径导致上游选中 0 项的缺口，按本批四个直接变更的上游测试及清单路径运行：

```sh
AIXCODING_EXTENSION_BASE_URL=https://telemetry.invalid \
  uv run --offline --no-sync --no-python-downloads python aixcoding/tools/verify.py --upstream-smart --paths \
  tests/architecture/test_layering.py tests/architecture/trajectory_wait_manifest.json \
  tests/orchestration/engine/test_settings_reload.py tests/orchestration/engine/test_web_search_budget.py
```

日志为 `/tmp/icode-telemetry-probe.7glV33/closeout-upstream-smart.log`。统一入口退出 **1**。上游常规 **37 passed**（退出 0），架构 **504 passed、2 failed**（退出 1）。两项失败均为 `tests/architecture/test_chrys_test.py::test_lowered_priority_reaches_the_processes_tests_start`。参数 `15` 在 `os.setpriority()` 遇到 `PermissionError: [Errno 1] Operation not permitted`。参数 `None` 因降优先级失败时的 `Could not lower the CPU priority` 提示混入标准输出，整数解析抛出 `ValueError`。本次未重复已知端口绑定失败的完整定制套件。上一轮定制结果仍为 **612 passed、47 skipped、71 failed、17 errors**，88 项均在绑定处遇到权限拒绝。历史进程枚举、TUI worker 退出和解释器路径差异尚待覆盖对应路径。该上游定向运行不能关闭完整统一验证。

| 待验收项 | 本轮核查与后续条件 |
| --- | --- |
| 目标 Python 与统一验证 | `uv python list --only-installed --offline` 列出 3.14.8 和 3.14.9，未列出目标 3.14.10。仓库 `.venv/bin/python` 仍为 3.14.8。下一次应使用已有 3.14.10 的获准测试 runner，允许本机测试端口绑定、进程优先级调整及进程枚举，以锁定依赖跑 `verify.py --smart --paths`。路径由 `git diff --name-only a752020b..890e2ec7` 获取。验收时须核对定制、上游常规和架构实际运行结果。若只能使用本机，则另行批准在独立位置安装 3.14.10 和准备锁定依赖，不改全局解释器或锁文件。 |
| T08 | 核对本地分支、远端跟踪 refs 和标签。0.35.2 合并的纯上游父提交为 `2fd777f6`，其 `pyproject.toml` 确认为 0.35.2。当前本地 refs 无可用的后续基线。对配置的 `origin` 进行只读 `git ls-remote` 退出 128，GitHub DNS 解析失败。取得后续上游 ref 或源码归档后，先用隔离副本逐文件检查本批 23 个上游变更路径及注册锚点，再复用原编码器与 fixture 跑全量埋点契约。记录实际适配文件、行数、语义差异和耗时。需要扩大上游修改时先走 R2。 |
| 生产对账 | 本轮只准备核对步骤。由有内网只读权限的人员提供同一灰度版本与时间窗中已获准的真实样本，按会话、请求、工具调用关联键与发送侧 mock 对拍口径核对入库条数、缺省字段和重复终态去重。记录采样范围与聚合差异，避免在日志或文档落凭据、原始代码和完整标识。当前未取得生产数据，未进行生产探测或写入。 |

### CI 架构门禁修复

[GitHub Actions 架构任务](https://github.com/ypzyfl/iCode/actions/runs/43204561610/job/131136335692) 报告 3 项失败、1248 项通过。两项来自工具事件的静态和运行时声明检查，一项来自三个包装工厂的客户端所有权检查。用户在看到两文件候选补丁后明确要求「开始修改，然后 git 提交」。本轮按该范围修改两份架构测试并登记标记，签认字段保持原样。

- `tests/architecture/test_event_declaration_guard.py`（+12/−2）按事件类型登记已有的报文关联字段。开始事件允许 `model_source_id` 与 `tool_operation_id`，结果事件允许 `tool_operation_id`。静态与运行时检查继续拒绝额外调用身份并约束 `origin`。
- `tests/architecture/test_hygiene_llm_client_owners.py`（+28/−3）识别同一作用域内包装后实际执行的工厂调用。三个生产调用点沿用现有关闭所有权登记，新增用例验证无登记的包装调用仍会失败。

现有 Python 3.14.8 下，使用 `uv run --offline --no-sync --no-python-downloads` 执行。修复前在原工作区复现 3 项失败。修复后运行 `pytest -n0 -q --tb=short -p no:cacheprovider tests/architecture/{test_event_declaration_guard,test_hygiene_llm_client_owners,test_test_hygiene,test_trajectory_wait_inventory}.py`，退出 0，**307 项通过**。Ruff 检查和格式检查通过。

埋点专项首跑 61 项通过、6 项失败。失败用例读取本机 `~/.chrys` 下的钩子配置，沙箱拒绝相关写入。随后在同一沙箱内通过测试进程的 platform 配置注入，使用独立临时配置和数据目录复跑 `aixcoding/tests/telemetry`，退出 0，**67 项通过**。统一验证、GitHub Actions 复跑及内网对账仍待完成。
