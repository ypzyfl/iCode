# 自评审记录：auth 登录状态埋点（aixcoding.auth logging）

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-30
- 确认意见：无特别意见
- 开发 AI：CodeBuddy（BM:GLM-5.3）
- 评审 AI：Deepseek-V4-Pro（独立会话，design 态 / 实施态 / 聚合入口接线三轮）+ 外部评审 AI（2026-10-30 恢复期文档收敛轮）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-10-29 评审结论：通过

- 轮次：2 轮（design 评审+修复；实施评审+修复），均无 blocker
- design 轮（对 10 条版草案）6 findings + ehr PII nit：
  - F1 场景措辞与分级矛盾（修，requirements 同步 ERROR）；
  - F2 假设表缺 `install_log_handler` DEBUG 降级机制（修，已核 `screen.py:190-193`）；
  - F3 兜底分支措辞精确化（修）；
  - F4 `complete_login` 失败路径缺口（责任人裁决选 A，补 #11/#12，定稿 12 条）；
  - F5 caplog 跨测试污染风险（修，测试隔离 fixture 落地并实证 222 tests 零泄漏）；
  - F6 消息全文未定稿（修，design 表格冻结口径）；
  - ehr PII 打码（责任人维持现状，design 已标注裁决）。
- 实施轮（对 diff）6 findings（A-F）+ 覆盖缺口 nit：
  - A #9 消息偏离冻结口径（修，改回"桌面端"版）；
  - B test_09 vacuous（修，重写为 session 自身 store 预存断言）；
  - C test_02/03 行为断言缺口（修，补 delegation 停止 shadow / 保留断言）；
  - D `plain_session` 冗余（修，删）；
  - E `cause=ConnectError` 平台假设（责任人裁决：保留精确断言 + 注释标记 loopback 假设）；
  - F DIRECTORY.md §3 相对导入语义与 ruff TID252 张力（责任人裁决选 A：规范条文澄清"同包相对/跨子包绝对"）；
  - 覆盖缺口 #11 仅测 `DevicePollDenied`（不补：`exc=类名` 机制对异常子类自动工作，其余失败类型同一代码路径）。
- 验证命令与结果：见 verification.md（12 分支单测 12 passed；auth 目录 112 passed；全量 aixcoding/tests 301 passed/2 skipped；ruff check/format、ty win32 全过；gen_customizations 幂等；launcher 落盘闭环实证；222 tests 无泄漏；零上游改动）。

## 2026-10-29 增量复审：通过（处置 A-F 全到位，无回归）

- 复审范围：仅本轮修复增量（对照上方处置清单 + git diff）。
- 结论：A-F 六项处置全部到位、self-review 清单与 diff 一致、无 blocker/suggestion 新问题；C 项用公开 property `delegated_credential` 优于评审建议的私有属性。
- 唯一 nit（test_09 的 `login_once` 残留：真实登录流冗余 + 依赖 caplog 上下文外 INFO 不捕获的巧合）：**已修**——logout 场景无网络请求，改为任意 token + 去 MockServer + 降为同步测试，顺带消除"游离 `登录成功` 记录"脆弱性。
- 修复后复跑：`uv run pytest aixcoding/tests/auth/test_session_logging.py -n0 -q` → **12 passed in 14.77s**。

至此评审收敛：两轮评审 + 一轮增量复审，blocker 始终为零，全部 findings 处置闭环。

## 2026-10-30 聚合入口接线轮评审结论：通过（零 blocker，3 nit 处置闭环）

- 评审 AI：Deepseek-V4-Pro（独立会话；对象为本轮增量：`startup.py` / `logging_support.py::ensure_file_sink` / `app.py` +3 行 / `test_entry_wiring.py` / 文档联动与 CUSTOMIZATIONS C003）。
- 检查清单 9 项全过：R2 比对（上游仅 app.py +3 行）、架构边界（app→app 同层 + app→kernel 向下 + session.py 解耦零 import）、fail-safe 语义（全吞可观测、不阻断、不外抛）、幂等链（`_Marker` 复用，最短路径不翻倍）、幻觉 API（逐符号核验）、vacuous 专项（六用例逐个"改坏哪行才红"均可答出）、marker↔登记行配对（`module_matches` 走 `m==lnd`，C003 逐字一致）、过度工程、文档一致性。
- 锚定用例有效性专项论证：`main()` 函数内 from-import 每次执行从模块取属性，monkeypatch 源模块属性生效——删接线行即红，真锚定。
- findings 3 nit（责任人 2026-10-30 拍板"按开发 AI 建议"）：
  - N1 `test_main_calls` 依赖函数内 import 形态（**已修**：补注释显式化假设——上游若上提 import 致误红，注释即排查线索）；
  - N2 `ensure_file_sink` 函数内 import 风格（不修：跟随 `setup_logging:72` 既有惯例，风格一致优先于微优化）；
  - N3 `rc == 0` 耦合 `--version` 语义（不修：smoke 级耦合可接受）。
- 修复后复跑：`uv run pytest aixcoding/tests/diagnostics/test_entry_wiring.py -n0 -q` → **6 passed**；ruff/format 过。
- 本批次评审全史：10-29 两轮（design + 实施）+ 增量复审 + 10-30 恢复期文档收敛轮（外部 AI，M1/M2/M3①）+ 本接线轮——blocker 始终为零，全部 findings 处置闭环。

## 2026-10-30 PR #70 CI 修复轮 + peer review 轮：通过（4 候选处置闭环）

- **CI 事件**：run #61 ruff 全目录门禁拦截 `test_session_logging.py` RUF001×30（原实施期单文件 ruff 的验证缺口，测试文件漏豁免）；修复 commit 691c185（noqa 补 RUF001 + ruff 自动修复 3 处等价改动）；本地逐条预跑 CI 门禁后 push，run #62 全绿（16/16）。目录级 per-file-ignores 结构性改进已记 `fork/temp/aixcoding-todos/`。
- **Peer review**（外部 AI，head 691c185）：无 blocker；R2/R11 机器 + 人工双清、幻觉 API 未发现、破坏性实验 A/B 双红、freshness 字节级一致。候选 4 条处置（责任人拍板"按开发 AI 建议"）：C1 `#6` 记录先于 `clear()` → **修复**（调序为先清除后记录，误导性记录比丢失更糟；消息全文/级别不变无需重签）；C2 `--version` 全形态建空目录副作用 → **接受**（design 自然推论，无害）；C3 CI 事件与本轮处置 → **补记**（verification.md 新节）；C4 mock 7778 固定端口存量 → **记 temp 待办**不随本批。
- C1 修复后复跑：见 verification.md 同日新节。
