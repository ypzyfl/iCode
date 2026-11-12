# 验证记录：PR 门禁按需触发分层

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-11-12 本地验证（实施完成后）

环境：Windows 11 工作区，大写盘符，`PYTHONPATH=` 清空 + `PYTHONUTF8=1`（仓库测试配方）。

| 命令 | 结果摘要 |
|---|---|
| `uv run pytest aixcoding/tests/tools/test_ci_impact.py -q -n0` | **38 passed** in 3.90s（test-plan 单元矩阵全案例） |
| `uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q` | **684 passed, 51 skipped** in 34.40s（定制套件全量） |
| `uv run ruff check aixcoding/ src/chrys/{kernel,service,app}/aixcoding` | Found 2 errors（2 fixed, 0 remaining）——pyproject fix=true 自动修复新文件两处格式项，修复后 0 error |
| `uv run ruff format --check aixcoding/ src/chrys/{kernel,service,app}/aixcoding` | 417 files already formatted |
| `uv run ty check --error-on-warning --python-platform linux/darwin/win32 <定制产品路径>` | 三平台各 **All checks passed!** |
| `uv run python -m compileall -q <定制产品路径>` | OK（exit 0） |
| 真实 diff 数据点：`git diff --name-only --no-renames HEAD`（工作区 8 文件，含桥接自身）喂 `ci_impact.py` | stdout `upstream_touched=true`，**进程退出码 10**（子进程实测；cmd `%errorlevel%` 解析期展开假象已排除） |
| `uv run python aixcoding/tools/gen_customizations.py --strict` | check OK（114 rows / 159 markers / 18 designs / 0 warning；本批零 marker 改动） |
| `uv run python aixcoding/tools/check_docs.py` | OK（26 ADR / 43 design / 41 self-review） |
| `uv run pytest tests/architecture/test_workflow_action_pins.py -n0 -q` | **27 passed**（workflow 改动的 pins 守卫） |

## 待远程验证（本批 PR 与合并后，到点回填）

- **本批 PR（FORCE 全量自证）**：触及桥接 workflow → 预期 filter 判 touched=true、上游全套
  真实执行、gate 成功；filter 日志记录 `ubuntu-slim` 的 python3 探测结果（missing=false 预期，
  若 true 则 setup-python 兜底分支生效亦属预期路径）；govern 日志核对 L1 补位四检查实际执行。
- **closure 前置**：新 ADR（草案）须责任人签认、upstream-ci/ci-gate design 追加修订记录须重签、
  self-review 须签认——否则 PR 的 `check_docs --closure` 拒绝草案。
- **合并后**：① `workflow_dispatch` 手动全量一次（非 PR 事件分支实证）；② 临时验证 PR
  （doc+定制混合）观察 touched=false 三件套（filter=false / ci skipped / gate 直绿可合并）后
  关闭（design 验收时点说明，F4）；③ 首个 nightly 到点观察，build/wheel 覆盖结果回填
  user-manual verification（D2）；④ nightly 失败通知通道实测。
