# 验证记录：检查域模型与定制域按需触发

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-11-12 本地验证（实施完成后）

环境：Windows 11 工作区，大写盘符，`PYTHONPATH=` 清空 + `PYTHONUTF8=1`。

| 命令 | 结果摘要 |
|---|---|
| `uv run pytest aixcoding/tests/tools/test_ci_impact.py -q -n0` | **88 passed**（既有 38 upstream 零回归 + 新增 50：规则矩阵 R1-R12 全案例、并集语义 R5+R11/R7+R11、`--domains` CLI 精确输出、F6 AST 双形态扫描） |
| F6 提取集合人工核对 | 20 个真实消费路径，与评审三轮核实消费面完全吻合（9 个"文档即验证输入" + scripts 全家 + cd.yml + release 脚本 + guard 链路 + pyproject），全部被规则表覆盖 |
| `uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q` | **734 passed, 51 skipped** in 24.50s（全量套件，较上游批 +50） |
| `uv run python -c "import yaml; yaml.safe_load(...aixcoding-tests.yml)"` | YAML-OK |
| `uv run pytest tests/architecture/test_workflow_action_pins.py -n0 -q` | **27 passed** |
| `uv run ruff check aixcoding/ && ruff format --check aixcoding/` | All checks passed（RUF003 歧义字符 4 处已修 + format 自动重排 2 文件） |
| `uv run python aixcoding/tools/gen_customizations.py --strict` | check OK（本批零 marker 改动） |
| `uv run python aixcoding/tools/check_docs.py` | OK（新 ADR 草案计入 27 ADR） |

实施过程修复记录（测试侧自纠）：①R3 期望值修正——guard 树同时命中 R4（定制产品代码），
并集语义下为双域（design R3 行字面单域的表述偏差，测试矩阵按并集语义修正）；②F6 扫描根
路径 parents 层级错误（`aixcoding/aixcoding/tests` 幽灵目录→提取空集）；③F6 提取器收紧——
任意 Call 参数会把断言字符串（如 `is_upstream("tests/support/ci.py")`）当路径，收紧为
"REPO_ROOT 根 Div 链 + `_read` 调用"两真实消费形态 + 仓库真实存在过滤后，噪音清零。

## 2026-11-12 远程验证结果（PR #123，双 CI 全绿）

- **AIxCoding Tests**（run #200，`4a3bdc5e`）：**8/8 jobs 全 success**——`filter` 33s
  success（R1 FORCE 命中：`aixcoding-tests.yml` + `ci_impact.py` 改动 → 双域 touched=true；
  python3≥3.14 版本门限探测与 setup-python 步骤实际执行成功）；`govern`（16 业务步骤含 ty
  三平台/compileall）success；`Custom tests` 双 OS success；`Guard hooks` 三 OS success（安装/
  自检/MANUAL_TESTS 语料回放全链路）；`AIxCoding quality gate` success——**R1 FORCE 自证与
  gate 逐域状态机首次远程实证**。
- **Upstream CI**（run #130）：**success**（attempt 2）——`ci_impact.py` 命中 upstream 门
  FORCE（两门共用判定器）→ 全量真实执行；attempt 1 失败后重跑转绿（同 PR #121 macOS flaky
  先例模式，具体失败 job 未细核，如实留痕）。
- PR #123 双 required check 全绿，可合并。

## 2026-11-12 跳过链路真实验证（PR #124，docs/ci-gate-domains-backfill）

PR #123 合并（`800bb778`）后，以纯文档回填 PR 实证**定制双域跳过三件套**（批次验收最后一
条实证项）：

- **AIxCoding Tests**（run #202，`f26644a1`）：**success，总耗时 48 秒**（PR #123 全量时约
  7 分钟）——`filter` 33s success（判双域 touched=false）→ `Custom tests`/`Guard hooks`
  matrix job **skipped**（零 runner 分配、零步骤；PR checks 列表显示未展开的
  `${{ matrix.os }}` 模板占位属 GitHub 对未实例化 matrix job 的平台显示行为，实际执行的
  run 中名字正常展开，required check 为恒跑 gate 不受影响）→ `govern` 38s 照跑 →
  `AIxCoding quality gate` **7s 直绿**。
- **Upstream CI**（run #131）：success，49 秒（filter=false / ci skipped / gate 直绿，同
  PR #122 先例）。
- 两个 run 并行，纯文档 PR 总门禁等待**约 1 分钟**（优化前双 CI 全量约 23 分钟）。
- 验收标准"真实纯文档 PR 端到端"达成，无需额外临时验证 PR。

## 2026-11-12 push run 恒全跑实证（双证；范围=定制双域，不含 upstream）

- **Tests #201**（push，PR #123 合并触发，`800bb778`）：success，约 2.5 分钟——首证。
- **Tests #204**（push，PR #124 合并触发，`2d998f34`）：**8/8 jobs 全 success**——filter 40s
  判非 PR 事件 → 双域恒 true → `Custom tests` 双 OS（43/67s）+ `Guard hooks` 三 OS
  （24/41/28s）+ `govern`（27s）全量执行 → gate 8s success；总耗时约 9.5 分钟（macos
  runner 排队占大头，各 job 实际执行均数十秒）。
- 双证成立：**push 至主干 → 定制双域恒全跑**（纯文档合并同样全跑 test/guard/govern，兜住
  PR 阶段射程漏判）。**范围注意**：upstream 域不在 push 兜底内——桥接无 push 触发器
  （upstream-ci 批次设计：不为合并重复烧上游矩阵），上游套件的兜底仅 nightly/dispatch
  （24h 执行上界 + 观察责任，ADR 兜底层次原意）。

## 2026-11-13 首个 nightly 双绿（批次收官实证）

- **AIxCoding Tests #207**（schedule，2026-11-12 22:58 UTC 执行——GitHub schedule 高峰延迟
  近 5 小时，cron 定义仍为 UTC 18:00，平台已知行为）：**success，2m37s**——定制双域全量
  （非 PR 事件直全跑，主干 tip `d9e261f1`）。
- **Upstream CI #134**（schedule，23:08 UTC）：**success，13m11s**——upstream 域 nightly
  唯一防线的首次执行，全量含 build + wheel 探测。
- **user-manual 口径核销**：首个 nightly 的 build+wheel 覆盖完成（check_wheel 对
  `aixcoding/manual` 逐文件核对在 #134 内执行），user-manual 批次"等 nightly 兜底，首次
  覆盖后回填"的遗留口径同步核销（其 verification.md 本轮回填）。
- **批次全部验收项闭环**：FORCE 全量自证（PR #123）、纯文档跳过三件套（PR #124，~1 分钟）、
  push 恒全跑双证（#201/#204，范围=定制双域）、nightly 三域覆盖（#207/#134）。

## 待远程验证（已全部完成，无遗留项）

- ~~本批 PR（R1 FORCE 自证）~~ **完成**：PR #123 双 CI 全绿（见"远程验证结果"节——Tests
  #200 8/8 含 filter/gate 各域状态；Upstream #130）。
- ~~closure 前置~~ **完成**：新 ADR 已签认，closure 转绿（本地复跑 OK）。
- ~~合并后三项~~ **全部完成**：①纯文档回填 PR 三件套（PR #124，见"跳过链路真实验证"节）；
  ②push run 恒全跑双证（#201/#204，见"push run 恒全跑实证"节）；③首个 nightly 双绿
  （#207/#134，见"首个 nightly 双绿"节）。
