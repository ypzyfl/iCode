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

## 2026-11-19 变更单 v1.1：排队中主动取消

复用 `mock_server/model_concurrency_verify/` 的本地网关（本目录验证资产，已补 cancel 接口与 `request_id` 记录）。

**定制测试**（新增 `test_model_queue_cancel.py`，覆盖注入/判据/取消报文/状态码/超时/URL 推导）：

```text
uv run pytest aixcoding/tests/llm -n0 -q
43 passed in 3.17s    ← 首轮（取消用例 23 条）；补齐评审补测后为 49 passed（29 条）
```

**静态门禁**：

```text
uv run ruff check src/chrys/service/aixcoding/llm_queue src/chrys/service/llm/chat_completions/client.py aixcoding/tests/llm
All checks passed!（format: 2 files reformatted 后复检通过）
uv run ty check --error-on-warning --python-platform {linux,darwin,win32} src/chrys
All checks passed! ×3
uv run python aixcoding/tools/gen_customizations.py --strict
check OK — 134 registration row(s) / 199 marker(s) across 21 design(s)
uv run python aixcoding/tools/check_docs.py --closure
check_docs: OK
```

**wait 清单刷新**：

```text
uv run python -m tests.support.trajectory_wait_inventory
2919 waits, 10 reopened (new or changed; default rule applied):
  …queue_cancel:QueueRequestTracker._post_cancel:1
  …queue_cancel:QueueRequestTracker._post_cancel:2
  …queue_cancel:QueueRequestTracker.cancel_on_close:1
  …queue_cancel:QueueRequestTracker.observing.observe:1
  …chat_completions.client:ChatCompletionsClient._open_stream.updates:1…6（新增第 6 条，前 5 条序号重排）
```

全部保持默认 `unresolved`（fail-closed），无人工规则需重新套用；`tests/architecture/test_trajectory_wait_inventory.py` 57 passed。

**端到端实测（ACP 真实子进程）**：窗口 1 用 CLI 占住唯一槽位，ACP 会话排队 2 秒后发 `session/cancel`，网关日志：

```text
request #1 released (request_id=e02fb345…)
request #2 stream=True request_id=d4b9e6a1…
cancel request model='mock-queue-model' request_id='d4b9e6a1…'
cancel accepted (request_id=d4b9e6a1…)
request #2 cancelled while queued (request_id=d4b9e6a1…)
```

ACP 侧：`stop reason: cancelled`，排队通知仅 `{"position": 1, "queueSize": 2}` 一条（心跳去重），未等待 10 秒队列。
证明"中断 → client `finally` → cancel 接口 → 网关出队"整条链路成立，且 `model`/`request_id` 与主请求一致。

**Smart Test（诚实记录：FAILED）**：

```text
uv run python scripts/chrys_test.py --smart --paths <本次改动>
Summary: FAILED (exit 1)
```

11 个失败用例全部在本次改动范围之外，且均为**本机环境性**（`read_text()` 未指定编码 → 中文 Windows 的 GBK
解码 UTF-8 文件失败；workflow 字节码缓存残留）：

```text
tests/orchestration/workflows/test_package_trust.py::…bytecode_only_in_the_private_cache…
tests/orchestration/workflows/test_session_lifecycle_boundaries.py::…[identity-None-…]
tests/orchestration/invoker/test_operation_close.py::…[pause|returned-(kernel|acp|callback-…)]（6 条）
tests/orchestration/invoker/test_pause_persistence.py::…[kernel|acp]
tests/service/agent_middleware/test_injection.py::test_intermediate_text_stored_as_metadata
```

失败栈均为 `UnicodeDecodeError: 'gbk' codec` / `JSONDecodeError: Invalid \escape`（同一根因），与排队/取消代码无交集；
与本次相关的 `tests/service/llm/*` 全部通过。按 CLAUDE 环境记忆，本机存在同类环境性失败，CI（UTF-8/ASCII 临时目录）不受影响。
**未做 HEAD 对照**，报告时需注明这一局限。

**破坏实验（临时改动后复原，工作区已复原，`grep BREAK-EXPERIMENT src/` 无命中）**：

| 实验 | 改动 | 结果 |
|---|---|---|
| A | `QueueRequestTracker.cancel_on_close` 在判据通过后提前 `return`（不发 cancel） | `test_interrupt_while_queued_sends_cancel` FAILED（`len(cancels) == 0`）→ 端到端锚定成立 |
| B | `observing` 不置 `_released`（把放行帧当普通排队帧） | `test_interrupt_after_release_sends_nothing`、`test_released_tracker_is_not_queued` FAILED → 判据锚定成立 |

复原后复跑：`aixcoding/tests/llm` 47 passed，`ruff check` All checks passed。

**独立评审（只读子代理）后的修复，2026-11-19**：

| 等级 | 问题 | 修复 |
|---|---|---|
| P1 | `_attach_request_id` 原地写 `extra_body`；`build_request` 浅拷贝使该 dict 可能是调用方 options 自己的 → 复用 options 时命中旧 `request_id`，cancel 恒 404 | 写入前 `dict(extra)` 拷贝再回写 request；新增两条锚定用例（不污染调用方、非 mapping 分支） |
| P1 | `asyncio.ensure_future` 无强引用；取消场景下外层 await 立即抛 `CancelledError`，task 可能被回收 | `_PENDING_CANCELS` 集合持强引用 + done 回调移除 |
| P1 | 连接失败/超时与契约 404 同为 debug；而"URL 推导错误"的唯一症状就是连接失败或 404，日志不可见 | `httpx.TransportError` 升 `warning`（带 endpoint 与后果），404 保持 debug 但补 endpoint 便于区分 |
| P1 | 测试没有一处真实 `task.cancel()`；409/404/500、连接错误、超时用例无断言 | 新增 `test_cancelled_task_while_queued_sends_cancel`（`_HeldOpenStream` 保持连接 + `task.cancel()`）；上述用例补 `len(calls) == 1` |
| P2（未改，已登记） | 客户端未收到任何 position 帧就断连 → `queued` 判 False，不取消，元素留到网关 `QUEUE_TIMEOUT`；SDK 内部重试重发同 body（同 `request_id`）二次入队同样不可见 | 与 v1.0 边界一致，属客户端可观测性上限；design 已记同向窗口 |

破坏实验 C（`cancel_on_close` 判据改为恒真提前 return）：8 个用例 FAILED（含新增的 `task.cancel()` 用例）→ 锚定成立；
复原后 `aixcoding/tests/llm` 47 passed，`ruff check` All checks passed，`grep BREAK-EXPERIMENT src/` 无命中。

**收尾（2026-11-19，第三轮评审后）**：补两条 test-plan 承诺但此前缺失的用例 ——
`test_broken_customization_leaves_the_request_untracked`（tracker 工厂抛异常 → 请求体无 `request_id`、不发 cancel、流式照常）、
`test_non_streaming_request_is_never_tracked`（非流式 `_send` 不建 tracker、无 `request_id`）。

```text
uv run pytest aixcoding/tests/llm -n0 -q
49 passed in 3.55s
uv run ruff check aixcoding/tests/llm
All checks passed!
uv run ruff format aixcoding/tests/llm
1 file reformatted（复检通过）
```

## 2026-11-20 内网联调日志补强（仅定制包）

**目的**：内网联调不能只靠猜——排队帧到达/放行、拒绝转译、cancel 跳过原因必须可从日志判定。
**范围**：只改 `service/aixcoding/llm_queue/` 两个定制文件 + 测试，**无上游文件改动、R2 清单不变**。

### 新增日志

| 位置 | 事件 | 通道 / 级别 |
|---|---|---|
| `queue_frames.guard_queue_frames` | 首个排队帧 | 模块 logger INFO：`网关排队：position=N queueSize=M`；detail INFO：`网关排队帧（解析后）：…`（含 `id`/`choices` 形状/`usage`/`model_extra`） |
| 同上 | 心跳 | detail DEBUG：`网关排队心跳：position=N queueSize=M（第 K 帧），解析后：…` |
| 同上 | 放行 | 模块 logger INFO：`网关已放行排队请求（此前收到 N 个排队帧）`；detail DEBUG：`排队放行后收到首个数据帧：…` |
| 同上 | `QUEUE_TIMEOUT` / `QUEUE_CANCELLED` 转译 | 模块 logger INFO：`网关拒绝排队请求：code=… retryable=False`；detail INFO：同一行 + `响应解析`（type/code/message/body/traceId） |
| 同上 | `QUEUE_FULL` 放行 | detail INFO：交给 wire 重试通道 + `响应解析` |
| 同上 | 契约漂移帧（带 `position`/`queueSize` 但不满足判据） | **模块 logger WARNING** + detail WARNING：记录 `choices` 形状、`id`/`usage`、两个队列值、`model_extra`，不记录正文 |
| `queue_frames._notify` | 前端回调失败 | 模块 logger 由 DEBUG 升 **WARNING** + detail WARNING：`排队状态回调失败…` |
| `QueueRequestTracker.observing` | 首帧/放行（带 request_id） | detail INFO：`网关排队：…（request_id=…）` / `网关已放行排队请求（request_id=…）` |
| `queue_cancel.track_queue_request` | tracker 建立 / base_url 不可用 / extra_body 非 mapping | detail DEBUG（含 `endpoint`/`base_url`；v1.5 起含 `token来源`）/ detail WARNING |
| `queue_cancel.cancel_on_close` | 发起 cancel | 模块 logger INFO + detail INFO：`正在离开网关队列：POST <url>，model/request_id` |
| `queue_cancel._post_cancel` | 取消请求报文 | detail INFO：`发送取消排队请求：POST <url>，body={'model':…,'request_id':…}，token=已携带`（不记 token 值） |
| 同上 | 取消响应 | 204 detail INFO；404·409 detail INFO（status + `body` + endpoint）；非 2xx detail WARNING（status + `body` + endpoint） |
| 同上 | **排队中但凭据两源皆空**（v1.5：请求头 `token` 与 `api_key` 均无） | **模块 logger WARNING** + detail WARNING：`网关排队取消跳过：没有可用 token，请求将留在队列中` |

### 日志查看路径（内网操作手册口径）

| 形态 | 详细日志 | 说明 |
|---|---|---|
| TUI | `%APPDATA%\chrys\logs\debug.log`（Linux/macOS：`~/.chrys/logs/debug.log`） | INFO+；DEBUG 需打开 F6 日志面板 |
| CLI / ACP | `%APPDATA%\chrys\aixcoding-logs\aixcoding.detail.log`（Linux/macOS：`~/.chrys/aixcoding-logs/aixcoding.detail.log`） | 文件专用、隔离，DETAIL 级全量；**CLI 没有 INFO 文件日志，必须看这份** |
| 事件发布/TUI 渲染 | 无独立日志 | 以界面/ACP 通知为准；本期不为打包改上游文件 |

> `aixcoding.toml` 的 `[logging] level` 只控制 `aixcoding` 树，不影响 `chrys.service.aixcoding.llm_queue`，不要把它当队列日志开关。

### 验证

```text
uv run pytest aixcoding/tests/llm -n0 -q
62 passed in 4.14s

uv run ruff check <改动文件>
All checks passed!
（ruff format 已执行）

uv run ty check --error-on-warning --python-platform win32 src/chrys
All checks passed!

# detail 通道落盘探针（临时目录 setup_logging 后 emit 一条）
aixcoding.detail.llm_queue: 网关排队：position=1 queueSize=2（request_id=abc）
```

新增用例：首帧/放行 INFO、detail 带 request_id、排队帧解析后的 `model_extra`、终止拒绝
`响应解析`（含 traceId）、契约漂移 WARNING、`QUEUE_FULL` detail、cancel 发起/204、
无 api_key WARNING、404 detail、cancel 请求报文与响应 body、tracker armed detail。

**原始 SSE 边界**：guard 拿到的是 SDK 解析后的 chunk，不是 `event:`/`data:` 原文；因此日志记录
`id`/`choices` 形状/`usage`/`model_extra` 的解析结果。需要逐字节原文时，用 curl 抓取或开启
`log.raw_http_capture`（上游能力，写 `<session>/llm_raw_http.jsonl`），本批次不新增原始流日志。

**同日文案调整（2026-11-20）**：本次 queue 联调的全部日志改为中文
（`code`/`request_id`/`endpoint`/`position`/`queueSize` 等技术标识保留原文），测试断言同步为中文，
避免内网联调同事现场翻译。`chat_completions/client.py` 内两条定制日志
（`aixcoding llm-queue 取消排队不可用` / `aixcoding llm-queue 网关排队帧将导致流失败`）
也改为中文：仅字符串替换、**行数不变**，该文件已在 `model-queue-client` 的 R2 批准池内。
`terminal_queue_rejection` 在网关未给 message 时的兜底文案同步改为
`网关排队拒绝了该请求（<code>）`。

## 2026-11-20 独立评审修复（C2/C3）

- **C2 接线顺序**：`_open_stream` 把 `guard_queue_frames` 与 `track_queue_request` 改为同一次
  lazy import；导入失败时不构造 tracker、不注入 `request_id`。消除「request_id 已发出但 guard
  不可用、流关闭永不取消」的中间态。client.py 相对 base 实测 `+38/−5`。
- **C3 使用约束**：profile 显式 `request_id` 仍复用（单飞行测试依赖），detail 日志提示并发共享；
  design assumption 7 / 风险条与 requirements 已知限制已登记，不改行为。

命令：

```text
uv run pytest aixcoding/tests/llm -n0 -q
67 passed in 8.23s

uv run pytest tests/service/llm -q -n4 -m "not integration and not gc_calibration"
2099 passed in 45.17s

uv run ruff check / format --check <改动文件>
All checks passed!

uv run ty check --error-on-warning --python-platform win32 src/chrys
All checks passed!

uv run python aixcoding/tools/gen_customizations.py --strict
check OK — 134 row(s) / 199 marker(s)
```

**待重签**：`model-queue-client/design.md` 的 C2 行数与 C3 约束属正文 R2 变更，AI 未改头部。

---

## 2026-11-24 v1.4 归位压缩实施验证

```text
uv run pytest aixcoding/tests/llm -m "not integration and not gc_calibration" -q
71 passed（含取消链路 29 条经生产 profile 客户端锚定，签名改 sdk 后全绿）

uv run pytest tests/service/llm 之外的取消相关上游面：
    aixcoding/tests/llm + tests/app/acp/test_server_capabilities.py 合跑 74 passed

wait 清单：uv run python -m tests.support.trajectory_wait_inventory
    6 条重开（close_stream_and_cancel×2 新增、updates×5/6 因 finally 结构变化重锚），
    全部默认 unresolved；tests/architecture/test_trajectory_wait_inventory.py 全绿

净表 numstat（merge-base → 工作区，实测）：client.py 相对 base +30/−1
（v1.4 表已回填；finally 降级分支说明见 v1.4 偏差节）

ruff check（EDITS 面，6 处自动修复后 0 剩余）/ ruff format --check：通过
ty check --error-on-warning 三平台：All checks passed!
gen_customizations.py --strict：check OK
```

**待重签**：v1.4 实测净行数（+30/−1，高于预估的降级分支说明）属正文回填，AI 未改头部。

---

## 2026-11-25 v1.5 cancel 凭据同源实施验证

```text
uv run pytest aixcoding/tests/llm -m "not integration and not gc_calibration" -q
84 passed（v1.4 时 71：新增 13 = 请求头 token 优先 2、无头回退 api_key 1、
登录态端到端中断 1、更名重锚 9）

Smart Test --paths（queue_cancel.py + 3 个测试文件）：
  tests         2749 passed, 27 skipped
  architecture  首跑 1 failed：wait 清单 _post_cancel:2 表达式漂移（token 更名）
                → uv run python -m tests.support.trajectory_wait_inventory 刷新
                  （重开 1 条，旧/新规则同为 unresolved，无需重新套用）
                → 复跑 tests/architecture/test_trajectory_wait_inventory.py 57 passed

ruff check / ruff format --check（本变更文件）：通过。
  注：test_model_queue_progress.py 的 2 处 RUF012（511/542）与格式漂移（411/441）
  为工作区既有未提交状态，非本变更引入，未顺手修改。
ty check --error-on-warning：win32、linux All checks passed!
gen_customizations.py --strict：check OK — 133 行 / 198 标记
  （较 v1.4 记录的 134/199 少 1：6878be6e progress 批所致，本变更未动登记表与 marker）
```

**待重签**：design.md 头部（v1.5 为正文追加，R10 需责任人重签；本变更无 R2 上游改动）。
