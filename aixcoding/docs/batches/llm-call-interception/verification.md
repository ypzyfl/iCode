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
