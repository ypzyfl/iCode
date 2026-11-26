# 验证记录：进程内大模型 HTTP 调用拦截（llm-call-interception）

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-11-25 定制行为与启动组合回归

命令：

```cmd
set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest aixcoding/tests/llm_call_interception aixcoding/tests/diagnostics/test_entry_wiring.py -n 0
```

结果：**111 passed**。覆盖空策略快速路径、session/turn 可空上下文、请求与响应读写改拦、缓冲/真实流、SSE 分帧、异常 containment、异常消息与源码行脱敏、安装降级三通道、raw log 顺序、SDK/Chrys 重试，以及 Chat Completions、Responses、Anthropic 的真实 SDK 解析和流式阻断。

## 2026-11-25 Smart Test 首次运行（环境性失败）

命令：通过 `uv run python scripts/chrys_test.py --smart --paths <本批 20 个代码/测试文件>` 执行。

结果：普通套件 **11039 passed、349 skipped、1 failed**，architecture 未运行。唯一失败为 `test_prepare_probes_the_default_interpreter_and_fingerprints_it`，`uv` 将 `sys.executable` 设为小写盘符，而上游断言要求与显式大写路径一致。随后实测：`uv run` 返回小写解释器路径，直接调用同一 venv 的大写解释器路径返回大写路径。

## 2026-11-25 Smart Test 第二次运行（发现生成物缺失）

命令：改用 `D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe scripts/chrys_test.py --smart --paths <本批 20 个代码/测试文件>`。

结果：普通套件 **11040 passed、349 skipped，exit 0**；architecture **325 passed、1 failed**。唯一失败为新增模块 17 个 wait 节点未登记到 `tests/architecture/trajectory_wait_manifest.json`。

## 2026-11-25 架构生成清单刷新

命令：

```cmd
uv run python -m tests.support.trajectory_wait_inventory
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest tests/architecture/test_trajectory_wait_inventory.py -n 0
```

结果：生成器报告 **2926 waits、17 reopened（全部为本批新模块节点，default unresolved）**；diff 仅在目标 JSON 新增 41 行，没有修改其他模块。wait inventory 专项 **57 passed**。design/ADR 已对此唯一上游生成物例外重新签认。

## 2026-11-25 CI 全目录格式与静态类型检查

命令：

```cmd
uv run ruff check aixcoding/ src/chrys/app/aixcoding src/chrys/kernel/aixcoding src/chrys/service/aixcoding
uv run ruff format --check aixcoding/ src/chrys/app/aixcoding src/chrys/kernel/aixcoding src/chrys/service/aixcoding
uv run ty check --error-on-warning --python-platform linux src/chrys/app/aixcoding src/chrys/kernel/aixcoding src/chrys/service/aixcoding
uv run ty check --error-on-warning --python-platform darwin src/chrys/app/aixcoding src/chrys/kernel/aixcoding src/chrys/service/aixcoding
uv run ty check --error-on-warning --python-platform win32 src/chrys/app/aixcoding src/chrys/kernel/aixcoding src/chrys/service/aixcoding
```

结果：ruff **All checks passed**；format **498 files already formatted**。`ty` 首次发现 `functools.wraps` 泛型赋值与具体工厂签名不匹配；以运行时签名说明和窄化 `ty: ignore[invalid-assignment]` 修正后，Linux、darwin、win32 三平台均 **All checks passed**。

## 2026-11-25 独立代码审查与复审

由独立 `code-explorer` 子代理进行只读审查。首轮发现 1 个 high（标准 traceback 可泄露异常消息）、2 个 medium（客户端安装失败可见性、真实 SDK/流式路径证据）、2 个 low（响应头故障注入、SSE Content-Length）。修复过程中自测又发现 traceback 源码行泄露，改为只输出文件名、行号、函数名和固定 redacted 结尾。

复审结论：原 6 项 finding 全部 closed，未发现新增 blocker/high/medium/low。行为证据见本文首节 111 项回归。

## 2026-11-25 最终验证待收尾

完整 Smart Test 已加入 manifest 路径并转为后台执行，当前没有可记录的最终结果，**不得据此宣称 Smart Test 通过**。完整 `aixcoding/tests`、`check_docs --closure`、导入边界、定制清单、编译和 R2/R3 门禁结果待追加。

## 2026-11-25 最终 Smart Test 与完整定制套件结果

责任人提供的后台 Smart Test 完成输出：

```text
Summary: PASSED (exit 0)
  tests         11040 passed, 349 skipped (exit 0)
  architecture  600 passed, 2 skipped (exit 0)
```

完整定制套件使用大写解释器执行 `python -m pytest aixcoding/tests -m "not integration and not gc_calibration"`，结果 **988 passed、56 skipped，exit 0**。mock update 服务出现客户端中止连接的服务端 traceback 噪音，不影响 pytest 成功结果。

其余已通过门禁：`check_docs`（非 closure）、`check_import_boundaries`、`gen_customizations --strict`（108 rows / 159 markers / 0 warnings）、compileall、ruff、500 文件格式、R2/R3。`check_docs --closure` 仍等待 self-review 责任人签认；design 的 ID 来源补充也按 R10 等待重新签认。

## 2026-11-25 外部评审 B1 独立复现与 Smart Test 证据边界

命令：

```cmd
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest tests/app/cli/test_app.py tests/service/llm/test_route_extension_wire.py tests/service/llm/test_default_http_client_parity.py -n 0
```

结果：**48 passed、2 failed**。两项失败均为 `test_route_hook_adds_nothing_to_the_wire`，实际 hook 清单多了 `build_http_hooks` 的 request/response hook。外部评审的 B1 归因成立，先前 Smart Test 未覆盖此调度顺序，不能视为完整上游 core shard 证明。

B2 经上游 `chat_completions/validation.py:336-344` 与当前 `hooks.py` 对照确认：兼容网关会双向误标 Content-Type，当前定制却只按 Content-Type 分派。批次转为阻塞，需方案裁决、修复和新的上游 core shard 验证。

## 2026-11-25 B1/B2 修复后强制回归

按责任人裁决实现空策略不附 hooks、非空策略先注册后建 Client、实际内容 512 字节 sniff + 同 iterator 回放，以及
Client 安装失败主通道+detail、不写 stderr。结果：

- 真实 startup 的 `test_app.py + test_route_extension_wire.py + test_default_http_client_parity.py`：**50 passed**，
  修复前同命令为 48 passed / 2 failed。
- CI core shard（`-n 4 --dist=worksteal`，排除 TUI/architecture）：**24146 passed、652 skipped，exit 0**。
- 本批与 startup 回归：**125 passed**。覆盖双向 Content-Type 误标、三真实 SDK 误标 SSE、门闩增量交付、缓冲 SSE、
  回调不匹配 detail、512/513 字节边界、BOM/前导空白、超大首 chunk 无损回放和取消前首事件已交付。
- 完整定制套件：**1002 passed、56 skipped，exit 0**。
- 三平台 `ty` 全部通过；精确 `update_wrapper` 签名和动态 setattr 不再需要 `ty: ignore`。ruff、500 文件 format、
  check_docs、导入边界、gen_customizations strict、compileall、R2/R3 全部通过。
- 自适应流新增 wait 节点经官方生成器刷新：2937 waits、15 reopened，wait inventory **57 passed**。

修复后只读复核未发现新的运行时 blocker/high。外部评审实测启动开销约 +12.9ms、16 个模块且未拉入 SDK，作为
数量级参考记录，未冒充本轮独立性能基准。最新 Smart Test 仍单独追加，旧结果不沿用。

## 2026-11-25 B1/B2 修复后的最终 Smart Test

在最新产品代码、125 项本批/startup 测试及刷新后的 wait manifest 上运行 Smart Test，结果：

```text
Summary: PASSED (exit 0)
  tests         11040 passed, 349 skipped (exit 0)
  architecture  600 passed, 2 skipped (exit 0)
```

该结果与上游 core shard 24146 passed / 652 skipped 分别记录，不互相替代。`check_docs --closure` 仍需责任人在
self-review.md 完成签认后执行。

## 2026-11-25 外部增量复审 N1/N2 后最终复验

外部 GLM-5.4 增量复审通过，无新 blocker；N1 extension key 安装期漂移测试和 N2 sniff 未判定期间取消、异常、提前关闭
三条测试已补齐。N3–N7 的注释、文档、缓冲 SSE headers 保存和 self-review 模板处置见 self-review.md。

- 本批与 startup 回归：**129 passed**；真实 startup 的 app/route/default-client 组合：**50 passed**。
- 完整 `aixcoding/tests`：**1006 passed、56 skipped，exit 0**。
- 上游 core shard（排除 TUI/architecture/integration 和在案 flaky install-scripts）：**37256 passed、699 skipped，exit 0**。
- 最新 Smart Test（显式包含全部产品/测试路径和 wait manifest）：

```text
Summary: PASSED (exit 0)
  tests         11040 passed, 349 skipped (exit 0)
  architecture  600 passed, 2 skipped (exit 0)
```

- 三平台 `ty` 全部通过；ruff、format、check_docs、导入边界、定制清单 strict、compileall、R2/R3 均通过。
- 官方 wait 生成器最终报告 **2937 waits、0 reopened**，wait inventory **57 passed**；本批登记 28 节点、+64 行。
- 责任人周彬已于 2026-11-25 签认 self-review（确认意见：无特别意见）；签认后运行
  `uv run python aixcoding/tools/check_docs.py --closure`：**check_docs: OK，exit 0**，无其他闭环阻塞。

## 2026-11-25 PR #153 CI 交叉核对与 wait manifest 节点逐条复核

CI（GitHub API，head `1bb01be3`）：check-runs 28 项 = **27 success + 1 skipped**（`Guard hooks`，仅在触及 guard 路径时
运行，本 PR 未触及，设计内跳过）；`AIxCoding Tests`、`AIxCoding Upstream CI` 两个 workflow 均 success。

wait 节点逐条复核（PR #153 评审 Nit #5）：根 `AGENTS.md` “Refresh generated artifacts” 条要求对刷新列出的每个 reopened
wait 逐个复核，并重新套用仍适用的原有规则；CI 接受 `unresolved` 行。此前只留了生成器计数（2937 waits / 0 reopened），
本节补齐逐条记录。本批 28 个节点全部为新增，reopened 输出中均无原有规则（无可重套项），均非 `sleep(0)`（不适用
`event-loop-yield`）。开发 AI 逐节点对照 `hooks.py` 源码分为三类，**28 行结论均为保持默认 `unresolved`（fail-closed）**，
随评审处置提交呈报责任人确认：

- **A 策略回调路径**：直接或经模块内函数执行策略传入的 handler，等待时长由任意业务代码决定，没有机器可证的
  trajectory 区间。
- **B 底层 I/O**：直接读取、迭代或关闭 httpx 提供的请求体/响应流，与 manifest 中 `chrys.service.llm.raw_http_log` 的
  `await request.aread()`、`async for chunk in self._stream`、`await self._stream.aclose()` 同形态，上游同类节点同为
  `unresolved`。
- **C 模块内转发**：在本模块内部流对象之间转发迭代与关闭，自身无 I/O，等待时长完全取决于下游（A 或 B），无独立可证
  的更窄分类。

| # | 函数 | await 表达式（manifest 原文，长参数以 ... 省略） | 类别 |
|---|---|---|---|
| 1 | `_AdaptiveResponseStream.__aiter__` | `await self._read_prefix()` | C |
| 2 | `_AdaptiveResponseStream.__aiter__` | `async for chunk in prefixed` | C |
| 3 | `_AdaptiveResponseStream.__aiter__` | `async for chunk in processor` | C |
| 4 | `_AdaptiveResponseStream.__aiter__` | `await self.aclose()` | C |
| 5 | `_AdaptiveResponseStream._read_prefix` | `async for chunk in iterator` | B |
| 6 | `_AdaptiveResponseStream.aclose` | `await self._prefixed.aclose()` | C |
| 7 | `_AdaptiveResponseStream.aclose` | `await self._stream.aclose()` | B |
| 8 | `_NormalBodyStream.__aiter__` | `async comprehension for chunk in self._stream` | C |
| 9 | `_NormalBodyStream.__aiter__` | `await self._handler(self._context, ...)` | A |
| 10 | `_NormalBodyStream.__aiter__` | `await self.aclose()` | C |
| 11 | `_NormalBodyStream.aclose` | `await self._stream.aclose()` | C |
| 12 | `_PrefixedStream.__aiter__` | `async for chunk in self._iterator` | B |
| 13 | `_PrefixedStream.aclose` | `await self._stream.aclose()` | B |
| 14 | `_SSEEventStream.__aiter__` | `async for chunk in self._stream` | C |
| 15 | `_SSEEventStream.__aiter__` | `await _process_sse_event(self._response, ...)` | A |
| 16 | `_SSEEventStream.__aiter__` | `await self.aclose()` | C |
| 17 | `_SSEEventStream.aclose` | `await self._stream.aclose()` | C |
| 18 | `_handle_buffered_body` | `await handler(context, ...)` | A |
| 19 | `_handle_buffered_sse` | `await _process_sse_event(response, ...)` | A |
| 20 | `_handle_request` | `await request.aread()` | B |
| 21 | `_handle_request` | `await handler(context, ...)` | A |
| 22 | `_handle_response` | `await _handle_response_headers(response, context, header_handler)` | C |
| 23 | `_handle_response` | `await _handle_buffered_sse(response, context, handler)` | C |
| 24 | `_handle_response` | `await _handle_buffered_body(response, context, handler)` | C |
| 25 | `_handle_response_headers` | `await handler(context, ...)` | A |
| 26 | `_process_sse_event` | `await handler(context, ...)` | A |
| 27 | `build_http_hooks.request_hook` | `await _handle_request(request, ...)` | C |
| 28 | `build_http_hooks.response_hook` | `await _handle_response(response, ...)` | C |

合计 A 7 / B 5 / C 16 = 28。

## 2026-11-25 HttpPolicy docstring 补充与 Accept-Encoding 协商探针

PR #153 评审 Nit #6（SSE 事件终结符契约）与建议 #1（压缩响应直通）处置：在 `HttpPolicy` docstring 补充事件终结符
契约、响应体回调的 identity 前提及 identity 协商写法，零行为变更。落笔前用一次性内联探针核对指引是否成立（未入库；
`httpx` 0.28.1；`MockTransport` + 真实 `build_http_hooks`；策略只改 `before_request`）：

```text
default-accept-encoding: gzip, deflate
negotiated-accept-encoding: gzip, deflate, identity    # dict(headers) 后加驼峰键 Accept-Encoding

keys-seen-by-policy: [accept, accept-encoding, connection, content-length, content-type, host, user-agent]
dict-camel   [gzip, deflate | identity]    # 同名头发送两次
headers-set  [identity]                    # httpx.Headers(headers) 副本上赋值
dict-lower   [identity]                    # dict(headers) 后加小写键 accept-encoding
```

结论：(1) 本环境 httpx 默认 `Accept-Encoding: gzip, deflate`（未装 brotli/zstd 时不追加 `br`/`zstd`），`clients.py`
未覆盖，评审 #1 的事实前提成立；(2) 策略在 `before_request` 协商 identity 可达 wire，但 `headers` 参数的键为小写，
`dict(headers)` 后追加不同大小写的同名键会发送重复头并静默协商失败，须在 `httpx.Headers` 副本上赋值或使用小写键。
两点均写入 docstring。该协商路径目前没有专门测试用例；通用机制由
`test_request.py::test_request_header_and_body_mutation_reaches_transport` 锚定，但该用例只新增头，不覆盖替换已有头。

### 评审处置改动复验（docstring + 文档）

```text
本批 + diagnostics                129 passed
完整 aixcoding/tests               1006 passed / 56 skipped
wait 生成器                        2937 waits / 0 reopened（节点未变）
wait inventory                     57 passed
ruff check                         All checks passed
ruff format --check                500 files already formatted
ty linux / darwin / win32          All checks passed x3
check_docs --closure               OK
gen_customizations --strict        108 rows / 159 markers / 0 warnings
check_import_boundaries            OK
check_r2_diff / check_r3_markers   OK
git diff --check                   通过
```

变更范围 4 文件：`interceptor.py` 仅 docstring（+12/-1），以及 `plan.md`、`self-review.md`、`verification.md`；wait manifest 无
diff。Smart Test 待责任人对 self-review.md 所列待裁决项定稿后执行。

## 2026-11-26 协商 identity 写法补测试（责任人裁决）

责任人裁决核实 #1 时的新发现 (a) 补测试：`test_request.py` 新增 2 例，零产品代码改动。Client 显式指定默认头
`Accept-Encoding: gzip, deflate`，使断言不随环境（是否安装 brotli/zstd）变化；transport 端用 `get_list` 读取全部同名头。

- `test_replacing_accept_encoding_on_headers_copy_negotiates_identity`：策略在 `httpx.Headers` 副本上赋值，wire 仅含
  `identity`。
- `test_dict_with_differently_cased_key_sends_accept_encoding_twice`：策略 `dict(headers)` 后加驼峰键，wire 含两个同名头
  `gzip, deflate` 与 `identity`。此例锚定现状（框架原样转发，不合并，不报告重复头），框架层若加检测需同步修改。

复验：

```text
本批 + diagnostics                131 passed
完整 aixcoding/tests               1008 passed / 56 skipped
wait 生成器                        2937 waits / 0 reopened
ruff check                         All checks passed
ruff format --check                500 files already formatted
ty linux / darwin / win32          All checks passed x3
check_docs --closure               OK
gen_customizations --strict        108 rows / 159 markers / 0 warnings
check_import_boundaries            OK
check_r2_diff / check_r3_markers   OK
git diff --check                   通过
```

变更范围累计 6 文件：`interceptor.py`（仅 docstring）、`test_request.py`（+42）、`plan.md`、`self-review.md`、`test-plan.md`、
`verification.md`。新发现 (b)（框架层是否检测重复头）由责任人裁决本 PR 不做、登记为后续候选（2026-11-26）。

## 2026-11-26 对原有流程的性能影响实测（责任人要求评估）

均为一次性内联探针（未入库），本机开发环境，隔离进程，`time.perf_counter` 计时；对照差值即本方案净增量。评估意见见
self-review.md “对原有流程的影响与性能评估”。

**启动成本（真实 `main()` 入口，`--version`）**：前导把 `chrys.app.aixcoding.startup._TASKS` 设为空元组（对照）或只含
第三个任务（实验），不执行前两个任务，不读写用户配置与日志；预热 1 次后各跑 5 次。

```text
A 无启动任务   main() 0.0 ms          脚本总耗时 48.1–50.7 ms     已加载模块 167
B 仅第三任务   main() 200.5–214.9 ms  脚本总耗时 249.2–270.3 ms   已加载模块 550
```

**冷态分段**：导入安装器约 213 ms / 333 模块（含 httpx 及依赖）；`install_http_interception()` 约 146 ms / 171 模块
（含上游 `chrys.service.llm.clients`、`chrys.kernel.*` 等）；未拉入 openai/anthropic SDK。

**只导入策略持有者**（包 `__init__` 连带导入 `context` 与 `chrys.foundation.trajectory.*`）：85–95 ms / 196 模块，未拉入
httpx 与 `clients`。

**包装层透传**（默认空策略，每次创建 Client）：进程内以上游工厂的空替身安装包装后循环调用 20 万次，0.49 µs。

**运行期热路径**（启用各阶段均返回 `None` 的策略，对比无 event hooks 基线；3 轮取最小；每请求耗时）：

```text
场景                           基线      启用策略    增量
非流式 JSON 2 KB               73 us     88 us      +15 us
非流式 JSON 512 KB             247 us    284 us     +37 us
SSE 5000 事件，每事件一 chunk   2448 us   9494 us    +7046 us
SSE 5000 事件，同一 chunk       121 us    9970 us    +9848 us
```

**单 chunk 多事件按事件数翻倍**（验证 SSE 缓冲前移是否平方级；3 次取平均；每事件耗时）：

```text
5000 事件    240 KB    8.82 us   （首次运行的预热噪音；上一探针同场景取最小为每请求约 10 ms）
10000 事件   480 KB    1.54 us
20000 事件   960 KB    1.49 us
40000 事件  1920 KB    1.70 us
```

结论：每事件耗时稳定，未观察到平方级增长。

### 评审处置改动的最终 Smart Test

对应待提交代码状态（`interceptor.py` docstring、`test_request.py` 新增 2 例）；`--paths` 为本批全部源码、startup、测试与
wait manifest 路径：

```text
Summary: PASSED (exit 0)
  tests         11040 passed, 349 skipped (exit 0)
  architecture  600 passed, 2 skipped (exit 0)
```

文档门禁：`check_docs --closure` OK；`ruff format --check aixcoding/` 452 files already formatted；`git diff --check` 通过。

## 2026-11-26 启动成本测量更正（真实启动路径）

**更正**：上文“启动成本（真实 `main()` 入口，`--version`）”一节的探针把 `_TASKS` 设为空元组或只含第三任务，未执行前两个
启动任务，第三任务于是独自承担了本应由它们分摊的公共依赖（httpx、`chrys.kernel.*` 等）导入。由此得出的“净增 200–215 ms /
383 模块”不代表真实启动路径，“对照差值即本方案净增量”的说明对该项不成立。“只导入策略持有者 85–95 ms / 196 模块”同样是
冷态数字。外部评审最初记录的“+12.9 ms / 16 模块”与此处真实路径结果吻合，此前判其“低估 15 倍”是错的。旧记录按活文档
规则保留不删。

**真实路径复测**：子进程内把 `get_platform()` 的配置目录指向临时目录（跑完即删，不读写用户配置与日志），经真实
`chrys.app.cli.app:main()`（`--version`）执行全部启动任务。`three` 把原安装任务加回为第三任务（惰性化前的等价物），
`check` 加回一个只导入策略持有者并判空的任务。每种 5 次。

```text
模式     main() 范围        最小值      已加载模块   相对现状
two      372.0–435.5 ms    372.0 ms    576         现状（惰性化后，两个任务）
three    390.5–478.1 ms    390.5 ms    594         +18 模块，约 +18–20 ms
check    401.1–474.0 ms    401.1 ms    579         +3 模块，耗时增量在噪音内
```

`main()` 约 370–480 ms 的主体是既有的前两个启动任务（配置加载、日志 sink），波动约 ±40 ms。另两次独立补测（仅导入前两个
任务的依赖模块后再执行原安装）给出 16–21 ms / 19 模块，与 `three` 一致。

**结论**：惰性化前，原启动安装任务在真实启动路径上的净增量约为 **18–20 ms、18 个模块**，不是 200 ms / 383 模块。
“启动期判空”方案在真实路径上只多 3 个模块，此前以其导入成本为由否决不成立；不采用它的正当理由是启动期策略必为空、
该任务恒为空转。

**惰性化后默认启动路径不触碰拦截模块**（此探针把前两个任务替换为空操作，只用于验证 `main()` 分发路径的导入集合，不是
真实启动的绝对耗时）：`main()` 0.0–0.2 ms，已加载模块 167，拦截模块、上游 `clients`、httpx 均未导入。同一冷态进程内首次
注册策略耗时 272–354 ms，同为冷态数字；真实启动路径（前两个任务真实执行后注册，5 次）上首次注册为 **10.8–17.8 ms、
+18 模块**，与原启动安装任务的成本一致。惰性化把这笔成本从“每次启动”挪到“首次注册策略时”：默认（无策略）部署不再
支付，启用策略的部署总成本不变。

**惰性化实施复验**（责任人在更正后裁决保留，2026-11-26）：

```text
本批 + 启动接线          133 passed（131 - 1 个删除的启动安装失败用例 + 3 个新增）
完整 aixcoding/tests     1010 passed / 56 skipped
真实 startup 组合        50 passed
上游 core shard          37256 passed / 699 skipped（12 分 06 秒，exit 0；与惰性化前一致）
Smart Test               Summary: PASSED (exit 0)
                         tests 11040 passed / 349 skipped；architecture 600 passed / 2 skipped
wait 生成器              2937 waits / 0 reopened，manifest 无 diff
ruff check / format      通过
ty linux/darwin/win32    All checks passed x3
check_docs --closure     OK；gen_customizations --strict 108 rows / 159 markers / 0 warnings
导入边界 / R2 / R3       OK（R2：相对主干变更 26 文件，upstream_changed=1 即 manifest）
回退文件相对主干         tasks.py、startup/__init__.py、test_entry_wiring.py 净零
```

实施中修正两处：`tasks.py` 回退时多出的一个末尾空行；`test_block.py::test_final_block_classification_and_exception_hygiene`
原在替换工厂之后才注册策略，注册触发的安装把测试替身又包了一层，导致 `transport` 参数重复，已把注册挪到替换工厂之前
（与同文件另一用例顺序一致）。全部 12 处替换工厂的测试中仅此一处顺序相反。

增量评审 #3 采纳后（守卫由 `glob("*.py")` 改为 `rglob("*.py")`）复跑：`ruff format` 1 file left unchanged、
`ruff check` All checks passed、完整 `aixcoding/tests` 1010 passed / 56 skipped、`check_docs --closure` OK。
Smart Test 不收集 `aixcoding/tests`（此前新增用例后其计数不变），对该改动无覆盖价值，未重跑；上游 core shard
不涉及该文件。上文列出的 Smart Test 与 core shard 结果均在此次改动之前运行。

## 2026-11-26 合并主干与合并后回归（PR #153 二次评审 B1）

命令：`git merge --no-edit origin/main_aixcoding_cli`（责任人逐条授权）；唯一冲突文件
`tests/architecture/trajectory_wait_manifest.json` 先以 `git show origin/main_aixcoding_cli:<path>` 的输出覆盖，再用官方
生成器重写，然后：

```cmd
set "PYTHONPATH=" && set "PYTHONUTF8=1"
uv run python -m tests.support.trajectory_wait_inventory
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest tests/architecture/test_trajectory_wait_inventory.py -n 0
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest aixcoding/tests/llm_call_interception aixcoding/tests/diagnostics/test_entry_wiring.py -n 0
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest tests/app/cli/test_app.py tests/service/llm/test_route_extension_wire.py tests/service/llm/test_default_http_client_parity.py -n 0
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest aixcoding/tests -m "not integration and not gc_calibration"
D:\Tech\Github\huawei\iCode\fork\iCode-fork_2\.venv\Scripts\python.exe -m pytest -q --tb=short --dist=worksteal -n 4 -m "not integration and not gc_calibration" tests --ignore=tests/architecture --deselect tests/app/test_install_scripts.py
```

结果（均 exit 0；合并对象为主干 `b2385928`，合并提交 `b1d1a732`）：

```text
wait 生成器              2950 waits / 28 reopened（全部为本模块节点，默认 unresolved）
manifest 相对主干        +64 行（28 节点），与合并前 R2 行一致
wait inventory           57 passed
本批 + diagnostics       133 passed
上游 50 项组合           50 passed
完整 aixcoding/tests     1094 passed / 56 skipped（合并前 1010；新增 84 项来自主干 aixcoding/tests/llm/）
上游 tests 全量含 TUI     37499 passed / 701 skipped，27 分 42 秒
```

- “上游 tests 全量含 TUI”即最后一条命令（`tests --ignore=tests/architecture --deselect tests/app/test_install_scripts.py`），
  也就是本文件此前各节写作“37256 passed / 699 skipped”的口径；合并后多出的 243 passed / 2 skipped 来自主干 #154
  新增的 TUI 测试。本文件 2026-11-25 一节的“24146 / 652”则是 CI core shard 口径
  （`--ignore=tests/architecture --ignore=tests/app/tui`）。两者范围不同，此前都被称作“上游 core shard”，特此更正
  口径；旧记录按活文档规则保留。
- 环境性说明：本轮曾以 `-W ignore` 与 `-qq` 误跑两组（前者压掉“警告即失败”的严格性，后者使 pytest 省略计数行），
  上表数字均为不带这两个参数的重跑结果。

## 2026-11-26 二次评审处置验证（F1 / F2 / F4 / F5）

**做法**：为使 design R2 行的节点数与最终实现一致（只签认一次），先在仓库外的临时副本（`git archive HEAD` 导出
`src`/`tests`/`aixcoding`/`scripts`/`pyproject.toml`）完成实现与验证，取生成器的确切数字写入 design 修订稿；责任人
确认签认后把同样的编辑应用到工作区，并与副本逐文件比对。

```text
工作区 vs 已验证副本      hooks.py / interceptor.py / test_sse.py / test_installer.py / manifest 均零差异
```

**wait manifest 重生成**：`2952 waits, 5 reopened`；manifest 相对主干 +68 行（30 节点）。5 个 reopened 节点逐条
复核（根 `AGENTS.md` “Refresh generated artifacts” 要求）：

| 节点 | 表达式 | 结论 |
|---|---|---|
| `_SSEEventStream.__aiter__:1` | `async for chunk in self._stream` | 底层网络流读取；因所在函数 wait 数变化而 reopened，保持 `unresolved` |
| `_SSEEventStream.__aiter__:2` | `async for event in self._take_events(buffer, final=False)` | 事件切分（间接等待策略回调），保持 `unresolved` |
| `_SSEEventStream.__aiter__:3` | `async for event in self._take_events(buffer, final=True)` | 流结束后的定案切分，保持 `unresolved` |
| `_SSEEventStream.__aiter__:4` | `await self.aclose()` | 关闭原始流，保持 `unresolved` |
| `_SSEEventStream._take_events:1` | `await _process_sse_event(...)` | 策略回调（原 `__aiter__:2` 迁入），保持 `unresolved` |

5 个节点均非 `sleep(0)`，不适用 `event-loop-yield`，也无原有规则可重套。

**变异验证**（临时副本内进行，验证后恢复）：

```text
回退为旧边界正则       test_sse.py  11 failed / 26 passed（失败项恰为全部含 CR 的用例，LF/CRLF 既有用例不受影响）
去掉“末尾 CR 推迟”      test_sse.py  2 failed / 35 passed（恰为两个跨 chunk 的 CR|LF 用例）
startup 目录之外间接导入  test_startup_never_references_http_interception 通过；
                       test_default_startup_in_a_fresh_process_never_touches_interception 失败并点名被导入的模块
```

**工作区回归**（均 exit 0，不带 `-W ignore`）：

```text
本批 + diagnostics        153 passed（原 133：test_sse.py +19，test_installer.py +1）
wait inventory            57 passed
上游 50 项组合            50 passed
完整 aixcoding/tests      1114 passed / 56 skipped（1094 + 20）
ruff check                All checks passed（aixcoding/ 与三个定制源码目录）
ruff format --check       535 files already formatted
ty linux/darwin/win32     All checks passed x3
compileall / 导入边界      OK
gen_customizations --strict  130 rows / 205 markers / 0 warnings
check_docs --closure      OK
check_r2_diff / check_r3_markers  OK（base = 上游 fork 点 2fd777f6）
Smart Test                Summary: PASSED (exit 0)
                          tests 10719 passed / 332 skipped；architecture 598 passed / 2 skipped
```

Smart Test 的 `--paths` 为本次全部 11 个改动文件，选择 17 个目标（`tests/service` 全目录、TUI 启动导入集合测试及
15 个架构测试文件/用例）。与此前记录的 11040 / 600 的差异来自路径范围：本次不再包含零改动的
`src/chrys/app/aixcoding/startup` 与 `aixcoding/tests/diagnostics/test_entry_wiring.py`。定制测试与上游 50 项不在
Smart Test 的范围内，由上面的单列命令覆盖。

**环境性说明**：临时副本上 `tests/app/cli/test_app.py` 有 7 个读取仓库构建文件（`.github/workflows/*.yml`、
`uv.lock`）的静态扫描用例失败，原因是这些文件未导出到副本；同一组用例在完整仓库中为 50 passed。
