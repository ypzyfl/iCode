# 验证记录：客户端对接模型并发排队（model-queue-client）

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-11-18 实施验证（N1）

命令：

```
uv run pytest aixcoding/tests/llm/test_model_queue_frames.py -m "not integration and not gc_calibration" -n0
```

结果：`8 passed in 1.63s`。覆盖：排队帧被吸收且回复完整、usage 正常、`choices:null` 无排队字段仍判 invalid、`QUEUE_TIMEOUT`/`QUEUE_CANCELLED` 转译后 `is_retryable` 为 False、`QUEUE_FULL` 保持 True、非 QUEUE 异常原样上抛且分类不变、心跳帧触发 `report_wire_progress`、定制 import 失败时回退原流。

命令：

```
uv run ruff check src/chrys/service/aixcoding/llm_queue src/chrys/service/llm/chat_completions/client.py aixcoding/tests/llm/test_model_queue_frames.py
uv run ruff format --check <同上路径>
```

结果：`All checks passed!` / `4 files already formatted`。

命令：

```
uv run ty check --error-on-warning --python-platform win32 src/chrys
```

结果：`All checks passed!`（win32 单平台；darwin/linux 未跑，本地无对应平台）。

命令：

```
uv run python aixcoding/tools/gen_customizations.py
```

结果：`check OK — 117 registration row(s) / 162 marker(s) across 20 design(s), 7 retired id(s), 0 warning(s)`。首轮曾报 `client.py:250` 第二个 marker 未登记，已把 except 块说明改为普通注释（同文件相邻改动共用一个 marker，R3 粒度）。

命令：

```
uv run python scripts/chrys_test.py --smart --paths src/chrys/service/llm/chat_completions/client.py src/chrys/service/aixcoding/llm_queue/__init__.py src/chrys/service/aixcoding/llm_queue/queue_frames.py aixcoding/tests/llm/test_model_queue_frames.py
```

结果：`11 failed, 7042 passed, 126 skipped`（exit 1）。失败全部落在 `tests/orchestration/workflows/test_package_trust.py`、`test_session_lifecycle_boundaries.py`、`tests/orchestration/invoker/test_operation_close.py`、`test_pause_persistence.py`、`tests/service/agent_middleware/test_injection.py`，与本次改动无调用关系。

既有性取证（HEAD 基线对照）：备份改动版 `client.py`，用 `git show HEAD:src/chrys/service/llm/chat_completions/client.py` 覆盖后跑同样 5 个文件，再恢复：

```
uv run pytest <上述 5 个文件> -m "not integration and not gc_calibration" -n4
```

结果：`11 failed, 57 passed`，失败集合与改动后**完全一致**（含 `UnicodeDecodeError: 'gbk' codec` — 本机 Windows 默认 locale 所致）。结论：这 11 个失败是环境既有问题，不是本批次引入。architecture 套件因上游套件失败未执行（Smart Test 行为）。

命令：

```
uv run python aixcoding/tools/check_docs.py
```

结果：`check_docs: OK`（28 ADR / 48 design / 46 self-review）。

## 2026-11-18 上游行为取证（设计阶段，真实 SDK）

以 `httpx` 假 SSE 服务驱动 `openai==2.54.0`：

- `event:queue_status` + `{"position":2,"queueSize":5}` → 解析为 `choices=None` 的 chunk，两字段进入 `model_extra`；
- `event:queue_rejected` + `{"error":{...}}` → 抛裸 `openai.APIError`，`status_code=None`，`body={'code','message','traceId'}`。

该取证是方案 E' 的立论基础，记录于此以备升级时复核（见 design 假设 1/3）。
