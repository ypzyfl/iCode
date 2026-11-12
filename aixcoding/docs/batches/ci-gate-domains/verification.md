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

## 待远程验证（合并后，到点回填）

- **本批 PR（R1 FORCE 自证）**：触及 `aixcoding-tests.yml` 与 `ci_impact.py` → 定制双域全跑
  + upstream 全量（判定器 FORCE）；filter 日志记录 probe 版本门限与 `--domains` 输出校验；
  gate 输出各域状态。
- **closure 前置**：新 ADR 签认（草案会被 closure 拒绝）→ closure 转绿。
- **合并后**：①纯文档回填 PR 三件套（filter 双 false → test/guard skipped → gate 直绿，各域
  状态输出可见）；②push run 恒全跑观察；③首个 nightly（UTC 18:00）定制域覆盖 + 与桥接同点。
