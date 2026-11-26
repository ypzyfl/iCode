# 测试方案：进程内大模型 HTTP 调用拦截（llm-call-interception）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

- 测试全部落在 `aixcoding/tests/llm_call_interception/`，并修改既有
  `aixcoding/tests/diagnostics/test_entry_wiring.py`；不修改上游手写测试，不 import `tests/support/`。唯一例外是
  官方生成器刷新 `tests/architecture/trajectory_wait_manifest.json`，该生成物不是手写测试。
- 单元测试覆盖策略调度、结果归一化、报文替换、SSE 分帧、异常 containment 和流关闭；契约测试使用真实
  HTTPX、OpenAI/Anthropic SDK、Chrys `create_client()` 与 `classify_error()`，传输端仅使用 `httpx.MockTransport`
  或自建 `AsyncByteStream`，不访问外部模型服务。
- 默认空策略与业务能力分别验证：空策略必须走快速路径；读取、修改、阻断能力由测试专用策略驱动，不把测试
  业务规则写入产品默认策略。
- 每个上游私有锚点必须真调被测符号，禁止 mock 锚点本身：
  1. `clients._build_profile_http_client`：保持同步签名与全部参数转发；空策略保持原始 hooks，非空策略在 Client
     创建前注册后返回的共享 Client 才被安装 hooks；
  2. `clients.create_client`：当前六种 provider/API style 组合及 Responses retrieve/poll/恢复流均使用同一 Client；
  3. `build_request_tracking_hooks`：真实写入 trajectory context 与 attempt ID，redirect/retry 每跳更新；
  4. HTTPX event hook 时序、缓冲 `_content` 与真实流：普通 body 在 SDK 解析前处理，两种响应形态分别覆盖；
  5. raw HTTP log：组合真实 hooks，验证修改后请求与原始网络响应的记录顺序；
  6. OpenAI/Anthropic 基础异常和公开 `classify_error()`：对实际抛出的最终异常断言不重试、非 transient。
- 并发与资源测试使用同一 Client 的不同 trajectory scope、可控 chunk 流和取消/提前关闭，不依赖时序 sleep。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型（单元/契约/端到端/行为锚定） |
|---|---|---|
| 首次模型 Client 创建前安装；重复启动/安装不重复包装和注册；extension 漂移在安装期失败 | `test_installer.py::test_install_is_idempotent_and_preserves_factory_signature`；`test_installer.py::test_tracking_extension_drift_fails_during_installation`；`diagnostics/test_entry_wiring.py::test_startup_task_order_and_single_snapshot` | 单元、行为锚定 |
| 空策略保持上游原始 hooks、不读 body、不换流、无固定 hook 开销 | `test_installer.py::test_empty_policy_factory_preserves_upstream_hooks`；`test_empty_policy.py::test_request_fast_path_never_reads_or_copies`；`test_empty_policy.py::test_response_fast_path_preserves_stream_identity` | 单元、契约 |
| 真实 startup 后同进程精确 hooks 不受全局包装污染 | `test_installer.py::test_empty_policy_factory_preserves_upstream_hooks` + `verification.md` 中真实 `cli_app.main()` 50 项串行组合及上游 core shard | 契约、上游回归 |
| 非空策略仅影响其后创建的 Client；既有未附 hooks Client 不追溯覆盖 | `test_installer.py::test_nonempty_policy_only_applies_to_clients_created_after_registration` | 契约 |
| OpenAI Chat、Responses（含 retrieve/poll）和 Anthropic 普通/流式均经过拦截器 | `test_provider_contracts.py::test_create_client_uses_installed_http_client`；`test_provider_contracts.py::test_provider_wire_calls_pass_through_interceptor` | 契约、行为锚定 |
| 请求/响应获得真实 session、可空 turn、cycle/exchange/attempt、actor、provider/model | `test_context.py::test_request_and_response_context_from_real_tracking_extensions` | 契约、行为锚定 |
| 派生路由 header 不冒充真实 session | `test_context.py::test_route_session_header_does_not_replace_trajectory_session` | 契约 |
| 无 turn 调用保持 `None`，actor role 可过滤 | `test_context.py::test_request_and_response_context_from_real_tracking_extensions`（`turn_id=None` 参数） | 单元、契约 |
| 多 attempts 关联同一非空 cycle；Chrys 重试和 redirect 使用对应新 ID | `test_context.py::test_redirect_attempt_ids_and_cycle_correlation`；`test_provider_contracts.py::test_sdk_retry_attempt_ids_and_cycle_correlation`；`test_provider_contracts.py::test_chrys_retry_changes_exchange_and_attempt_ids` | 契约、行为锚定 |
| 请求 headers/body 修改在实际 wire 可见，Content-Length 一致 | `test_request.py::test_request_header_and_body_mutation_reaches_transport` | 契约 |
| 请求 Block 不到达网络，SDK/Chrys 不重试 | `test_block.py::test_block_does_not_retry_and_has_clean_classification`；`test_block.py::test_final_block_classification_and_exception_hygiene` | 契约、行为锚定 |
| 普通响应 headers/body 修改对 SDK 解析可见 | `test_provider_contracts.py::test_response_mutation_is_visible_to_sdk_parsed_result` | 契约 |
| 响应 Block 不进入正常解析且不发生重试 | `test_block.py::test_block_does_not_retry_and_has_clean_classification` | 契约、行为锚定 |
| 真实网络流与带 `_content` 的缓冲响应均覆盖，异常重放原 body | `test_response.py::test_buffered_and_stream_responses_fail_open_with_original_body` | 单元、契约、行为锚定 |
| 双向 Content-Type 误标按实际内容分派，512 字节前缀回放且 SSE 保持增量 | `test_response.py::test_content_sniff_dispatches_mislabelled_json_to_body_policy`；`test_sse.py::test_content_sniff_dispatches_mislabelled_sse_incrementally` | 单元、真实 SDK 契约 |
| 缓冲 SSE 按事件处理，不因 `_content` 跳过 | `test_sse.py::test_buffered_sse_events_are_processed` | 单元、契约 |
| 实际响应与唯一内容回调不匹配时直通并记录一次 detail，不全缓冲 SSE | `test_sse.py::test_handler_mismatch_logs_and_preserves_incremental_stream` | 单元、契约 |
| 跨 chunk SSE、单 chunk 多事件可完整读取和修改 | `test_sse.py::test_split_and_coalesced_events_are_processed_as_complete_events` | 单元、契约 |
| 跨 chunk SSE 可阻断，已转发内容不撤回、不重放 | `test_sse.py::test_event_block_stops_remaining_stream_without_replay` | 单元、契约 |
| 当前事件策略异常只回退当前事件，后续事件继续处理 | `test_sse.py::test_event_failure_passes_current_event_through_and_continues` | 单元 |
| 正常结束、底层异常、取消、提前关闭均关闭原始流且不重复提交，含 sniff 未判定阶段 | `test_sse.py::test_underlying_stream_error_is_not_swallowed`；`test_sse.py::test_early_close_closes_original_stream`；`test_sse.py::test_cancellation_is_not_contained_and_closes_original_stream`；`test_sse.py::test_cancellation_during_sniff_closes_original_stream`；`test_sse.py::test_underlying_error_during_sniff_closes_original_stream`；`test_sse.py::test_early_close_during_sniff_closes_original_stream`；正常结束由事件读写用例覆盖 | 单元、契约 |
| 各阶段 ValueError、RuntimeError、自定义异常均不外溢，原报文继续 | `test_failure_containment.py::test_business_exceptions_fail_open_at_every_stage` | 单元、契约 |
| 非法返回类型与修改应用失败回退原始报文并写 detail | `test_failure_containment.py::test_invalid_results_fail_open`；`test_failure_containment.py::test_mutation_application_failure_restores_original` | 单元 |
| 日志自身失败不再次外溢；宿主取消和控制信号不吞 | `test_failure_containment.py::test_logging_failure_does_not_escape`；`test_failure_containment.py::test_cancellation_is_not_contained` | 单元 |
| 最终 Block 非 retryable/transient，异常链、固定文本和 reason 隔离正确 | `test_block.py::test_final_block_classification_and_exception_hygiene` | 契约、行为锚定 |
| 启动安装失败有 stderr、主通道和 detail；Client 安装失败有主通道+detail、无 stderr | `diagnostics/test_entry_wiring.py::test_llm_http_install_failure_is_contained_and_logged`；`test_installer.py::test_client_hook_install_failure_is_visible_and_fail_open` | 单元 |
| 运行期异常有 detail，认证信息、prompt、工具参数和正文不落日志 | `test_failure_containment.py::test_detail_log_redacts_payload_and_credentials` | 单元 |
| 真实 `create_client()` 契约不 mock `_build_profile_http_client` | `test_provider_contracts.py::test_create_client_uses_installed_http_client` | 契约、行为锚定 |
| raw log 记录修改后请求和网络原始响应 | `test_raw_log_composition.py::test_raw_log_sees_mutated_request_and_original_response` | 契约、行为锚定 |
| 非 identity 压缩报文不能安全处理时原样直通并记录 detail | `test_response.py::test_encoded_response_passes_through`；`test_sse.py::test_encoded_stream_passes_through` | 单元 |
| 替换已有请求头的写法契约：在 `httpx.Headers` 副本上赋值可协商 `Accept-Encoding: identity`；`dict` 加不同大小写的键会发送重复头（现状锚定，框架层若加检测需同步修改） | `test_request.py::test_replacing_accept_encoding_on_headers_copy_negotiates_identity`；`test_request.py::test_dict_with_differently_cased_key_sends_accept_encoding_twice` | 契约 |
| 单组合策略原子替换、并发调用不串扰，hooks 不持锁等待 | `test_context.py::test_concurrent_contexts_and_profiles_do_not_cross_talk`；`test_installer.py::test_policy_snapshot_is_atomic` | 单元、契约 |
| 零上游手写行为文件、仅官方 wait manifest 生成物例外、零新增依赖，全部定制测试与质量门通过 | `verification.md` 记录 `git diff --name-only`、生成器输出、依赖清单复核及本文件末节命令结果 | 静态检查、质量门 |

## 异常与降级路径

1. **分阶段故障注入**：request、response headers、普通 body、SSE event 分别注入 `ValueError`、`RuntimeError`、
   自定义业务异常、非法返回类型和修改应用失败；断言宿主收到当前原始报文，detail 含阶段、provider/model、
   可得的调用 IDs 和异常类型，不含报文正文或敏感 headers。
2. **Block 与故障分离**：`Block` 不被 fail-open 捕获；OpenAI Chat、Responses、Anthropic 在 `max_retries > 0`
   下均只发生一次实际 HTTP 请求。SDK 直接透传的阻断异常断言固定 `args`、`__cause__ is None` 和
   `__suppress_context__ is True`；wire 重包装后的最终异常另行沿链调用 `classify_error()`，不得错误要求最终
   包装异常也没有 cause。
3. **SSE 边界**：覆盖 LF/CRLF、事件分隔符跨界、UTF-8 多字节字符和 JSON 任意位置拆分、单 chunk 多事件、
   结尾不完整事件原始字节仅转发一次；解析器无法继续时关闭自定义处理并直通剩余原始字节。
4. **流资源**：正常耗尽、底层读取异常、任务取消、提前 `aclose()`、事件 Block 均只关闭底层流一次语义所需的
   关闭路径，不重复 yield 缓冲事件，不重复提交 raw log 结束记录。
5. **启动与 Client 降级**：启动安装器抛错后继续执行后续任务；单个 Client 安装失败只写主通道 WARNING +
   detail，不写 stderr；运行期策略技术事件仅写 `aixcoding.detail.llm_call_interception`，不污染主通道。
6. **宿主异常不吞**：网络/transport 原异常保持宿主语义；`asyncio.CancelledError`、进程退出与键盘中断不按
   普通业务异常 containment。

## 手工验证步骤（若需）

本批以真实 SDK + 本地 MockTransport 契约测试作为端到端报文证据，不要求访问真实外部模型。实现后执行：

```bat
set "PYTHONPATH="
set "PYTHONUTF8=1"
uv run pytest aixcoding/tests/llm_call_interception aixcoding/tests/diagnostics/test_entry_wiring.py -n 0
uv run ruff check src/chrys/service/aixcoding/llm_call_interception src/chrys/app/aixcoding/startup aixcoding/tests/llm_call_interception aixcoding/tests/diagnostics/test_entry_wiring.py
uv run ruff format --check src/chrys/service/aixcoding/llm_call_interception src/chrys/app/aixcoding/startup aixcoding/tests/llm_call_interception aixcoding/tests/diagnostics/test_entry_wiring.py
uv run python scripts/chrys_test.py --smart --paths src/chrys/service/aixcoding/llm_call_interception src/chrys/app/aixcoding/startup aixcoding/tests/llm_call_interception aixcoding/tests/diagnostics/test_entry_wiring.py tests/architecture/trajectory_wait_manifest.json
uv run pytest tests/app/cli/test_app.py tests/service/llm/test_route_extension_wire.py tests/service/llm/test_default_http_client_parity.py -n 0
uv run pytest -q --tb=short --dist=worksteal -n 4 -m "not integration and not gc_calibration" tests --ignore=tests/architecture --ignore=tests/app/tui
uv run python aixcoding/tools/gen_customizations.py --strict
uv run python aixcoding/tools/check_docs.py
```

预期：上述命令退出码均为 0；Smart Test 读取末尾 `Summary:` 判断，不能以管道命令退出码代替。命令、环境、
实际计数和任何环境性失败记入 `verification.md`；若实际执行范围调整，以 verification 中真实命令为准。
