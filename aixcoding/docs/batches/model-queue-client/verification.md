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

## 2026-11-18 自审修复与复审

独立评审发现 9 条（2 blocker / 4 suggestion / 3 nit），处置如下。

**blocker 1 — 漏刷新 wait 清单生成产物**。证据（修复前）：

```
uv run pytest tests/architecture/test_trajectory_wait_inventory.py -n0 -q
E  unclassified wait nodes: chrys.service.aixcoding.llm_queue.queue_frames:guard_queue_frames:1
1 failed, 56 passed
```

该守卫带 `CI_LINUX_ONLY`，本机 win32 的 Smart Test 不跑它，首轮验证因此漏项。刷新：

```
uv run python -m tests.support.trajectory_wait_inventory
2910 waits, 1 reopened (new or changed; default rule applied):
  chrys.service.aixcoding.llm_queue.queue_frames:guard_queue_frames:1
```

产物 diff：`tests/architecture/trajectory_wait_manifest.json` +5 行，规则 `unresolved`（fail-closed，CI 接受）。复审：

```
uv run pytest tests/architecture/test_trajectory_wait_inventory.py::test_wait_manifest_matches_source -n0 -q
1 passed in 2.33s
```

**blocker 2 — 回退用例是空洞测试**。原用例只断言 `ChatClientException`：把 `client.py` 的 try/except 整块删掉后，`ModuleNotFoundError` 落进上游 `except Exception` → `_service_error` 同样产出 `ChatClientException`，用例仍绿。已改为断言内层 `ChatClientInvalidResponseException`。

**建议项**：删除无调用方的进程级 `_recorder` / `latest_queue_status`（跨请求串号、请求结束不复位，属过度设计）；降级日志 `debug → warning` 并点明后果；只发排队帧即断流时由定制包记 `logger.info`；`queue_position` docstring 的唯一性措辞降级；`service/aixcoding/__init__.py` 索引补 `llm_queue`。

**破坏性实验（在临时 basetemp 下改动-复原，工作区已复原）**：

| 实验 | 改动 | 结果 |
|---|---|---|
| A | 移除 `report_wire_progress()` 调用 | `test_queue_status_heartbeat_restarts_the_stall_watchdog` FAILED（`len([]) == 0`）→ 锚定成立 |
| B | `retryable=False` → `True` | `test_terminal_queue_codes_are_not_retryable` FAILED → 锚定成立 |
| C | 删掉 `client.py` 的 try/except 回退块 | `test_unavailable_customization_falls_back_to_the_plain_stream` FAILED，内层异常为 `ModuleNotFoundError` 而非 `ChatClientInvalidResponseException` → F2 修复有效 |

修复后复跑：

```
uv run pytest aixcoding/tests/llm/test_model_queue_frames.py -n0 -q
8 passed in 1.70s
uv run ruff check <改动文件>
All checks passed! / 5 files already formatted
```

R2 清单同步更新为 2 文件（`client.py` +10/−0、`trajectory_wait_manifest.json` +5），design 已按 R10 重新签认。
