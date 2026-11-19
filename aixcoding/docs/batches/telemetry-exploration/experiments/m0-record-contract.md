# M0：五类记录最小目标契约实验

> 2026-11-17。范围：真实 engine、真实 Chrys/OpenAI/httpx 请求管线、真实 write_file、session/trajectory/mutation/blob 持久化；五类 DTO 和 ACP envelope 均为测试态目标契约，不是生产 reporter、真实后台或真实 ACP server 接线。

## 1. 判别标准

一个 turn 使用两个不同成功响应：

- A1 返回 `write_file(path=m0.py, content="alpha\nbeta\n")`；
- 真实工具成功写入并留下一个 settled mutation；
- A2 返回最终文本 `Created m0.py.`。

必须同时满足：

1. 实际 HTTP headers 依次是 raw A1/A2，持久化 assistant message 独立证明相同身份；
2. 原模型和独立 LLM 测试记录各有 UUID(A1)/UUID(A2)；
3. tool-detail 使用 UUID(A1)/UUID(T)，不是 turn 最后的 A2；
4. ai-code 使用 UUID(A1)/UUID(T)，blocks 与最终参数及 after blob 一致；
5. 测试态 ACP `final-model-identity` 使用 UUID(A2) 和独立桌面 attribution span；
6. raw 32hex 只在测试出站边界转 canonical UUID，固定 golden 和无损往返成立；
7. tool/ai-code 不含 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs`。

## 2. 实现位置与最小接触面

只修改 `aixcoding/tests/telemetry/test_tool_identity_persistence.py`：

- 现有测试工具包增加绑定 session runtime 的真实 `FilesystemTools.write_file`；
- 复用现有真实 engine harness、scripted `httpx.MockTransport` 和持久化关联 helper；
- shutdown 后通过 `load_session_transcript()`、`load_session()`、`read_trajectory()` 和 `SnapshotStore.read_blob()` 重读证据；
- 测试内构造五类目标记录，使用 `with_chrys_metadata()` 验证 chrys turn metadata 与 `agent-studio.dev/final-model-identity` 共存；
- 新增严格 raw→UUID helper、共同 golden 和空值/大小写/长度/已格式化 UUID 拒绝用例。

没有修改 `src/`、上游 tests、`aixcoding/mock/` 或 pyproject，没有建设完整 analyzer、HTTP reporter、数据库或 ACP server。

## 3. 实验环境修正与失败留痕

首轮全文件结果：收集 9 项，`1 failed, 8 passed in 36.25s`。M0 在等待 turn 时 30 秒超时，日志显示开发者机器的全局 `security-tool-guard` 被加载；既有 lookup 两项和新增 UUID 项通过。该结果不作为 telemetry 身份关系失败。

随后将 `chrys.orchestration.session_hooks.get_platform()` 的 config_dir 固定到临时空目录，明确使用无 hooks 环境。单独 M0 仍在 30 秒超时，说明还存在无前端人工审批等待，不能把第一次超时全部归因于 hook。

将 harness 的 `default_approval_mode` 设为 `bypass` 后，真实 write_file 在约 2.5 秒内完成；测试继续发现实验假设错误：持久化 `function_call.arguments` 是 JSON 字符串，不是已解码 dict。改用 `json.loads()` 后，单独 M0 为 `1 passed in 2.07s`。上述修正均发生在定制实验代码，没有为通过测试放宽身份断言。

## 4. 最终验证

```cmd
cd /d D:\Tech\Github\huawei\iCode\fork\iCode-fork && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run ruff check aixcoding/tests/telemetry/test_tool_identity_persistence.py && uv run ruff format --check aixcoding/tests/telemetry/test_tool_identity_persistence.py && uv run pytest aixcoding/tests/telemetry -n0
```

结果：ruff `All checks passed!`，格式为 1 file already formatted；pytest 收集 16 项，`16 passed in 2.34s`，退出 0。包括既有 ACP 方向 7 项、工具/rollback 2 项、M0 1 项、UUID golden 1 项和非法输入 5 项。IDE diagnostics 0。

M0 实证了正常 A1→write_file→A2 下五类目标 DTO 可以共享正确身份，不会因取 turn 最后一次 A 而错挂工具/ai-code；真实文件内容、mutation after hash 和 blob 完全一致。

## 5. 未证明事项

- 原模型记录只是从实际 scripted request headers 构造的测试记录，不是 model_catalog/真实后台落库；
- 独立 LLM/tool/ai-code 没有实际 HTTP 发送、endpoint、ACK、SQLite、重放或 409；
- ACP 只有测试态 selector/envelope，没有真实 server attribution 捕获和桌面 `prompt.request_identified`；
- transport 是 `httpx.MockTransport`，没有经过 TCP；
- 本样本是无 hooks、自动审批、简单新文件，不覆盖 modified args、手工批准 codeStatus=5、复杂 edit、缺 blob、save=False、retry/Responses 或并发；
- M0 通过不证明长会话性能、正常退出 flush 或真实内网后台验收通过。

下一阶段为 M1：先做同一 A1 两工具的一对多和失败不借旧 A，再做 retry/redirect/Responses 与并发；真实 ACP server 和桌面联调仍需独立实施 design/R2。
