# 验证证据：规范落地四工具（devtools）

> 活文档：命令 + 输出摘要（R7 落盘形态，追加不删旧）。

## 2026-10-25 实施完成验证

环境：Windows，`PYTHONPATH=`（脱离 shim）、`PYTHONUTF8=1`、`UV_PYTHON=3.14.3`，仓库 `D:\Tech\Github\huawei\iCode\fork\iCode-fork`（新分支干净基线，工作树改动全在 `aixcoding/` 定制侧）。

| # | 命令 | 结果摘要 |
|---|---|---|
| 1 | `uv run pytest aixcoding/tests/tools -n0 -q` | **48 passed** in 4.67s（exit 0；含 md 甄别、untracked 拦截、四规则违规、签认门禁等用例；6 测试文件 + conftest） |
| 2 | `uv run ruff check aixcoding --no-fix` | All checks passed!（exit 0） |
| 3 | `uv run ruff format --check aixcoding` | 45 files formatted（收尾跑过一次 format 后干净） |
| 4 | `uv run python aixcoding/tools/check_import_boundaries.py` | scanned 1052 files / **OK**（exit 0，真实仓库无边界违规） |
| 5 | `uv run python aixcoding/tools/gen_customizations.py --repo <旧分支副本> --out aixcoding/docs/batches/devtools/archaeology-report-0.28.0.md` | 报告产出：932 命中（**24 注释标记** / 908 非注释命中）+ 57 定制资产文件；24 标记与存量台账（19 源码 + 3 测试 + pyproject 等）规模吻合，含 7 处 md 标题误报已由甄别修复消除 |
| 6 | `uv run python aixcoding/tools/check_r2_diff.py --base HEAD` | changed=19 / upstream_changed=0 / **OK**（exit 0；diagnostics 草案 R2 表被正确忽略并警告） |
| 7 | `uv run python aixcoding/tools/check_r3_markers.py --base HEAD` | upstream_changed=0 / **OK**（exit 0） |
| 8 | `uv run python aixcoding/tools/check_docs.py` | scanned 8 ADR + 2 design / OK |
| 9 | `uv run python aixcoding/tools/gen_customizations.py`（真实仓库） | **预期失败**（exit 1）：`AGENTS.md:5` 标记无登记——门禁正确拦截未登记既有定制点（挂起项①），处置后重跑即应通过 |

## 2026-10-25 AGENTS.md 补登记后回归（挂起项①方案 A 落地）

`batches/agents-md-note/design.md` 签认（周彬 / 已确认 / 2026-10-25 / "目前方案没有大问题"）后：

| # | 命令 | 结果摘要 |
|---|---|---|
| 10 | `uv run python aixcoding/tools/gen_customizations.py` | wrote `aixcoding/docs/CUSTOMIZATIONS.md`（**1 custom point C001 = AGENTS.md:5**；1 warning：diagnostics 草案登记表被忽略——预期） |
| 11 | `uv run python aixcoding/tools/check_docs.py` | scanned 8 ADR + **3 design** / OK |
| 12 | `uv run python aixcoding/tools/check_r2_diff.py --base HEAD` | approved_pool=1（AGENTS.md）/ OK |
| 13 | `uv run python aixcoding/tools/check_r3_markers.py --base HEAD` | OK |
| 14 | `uv run python aixcoding/tools/check_import_boundaries.py` | scanned 1052 / OK |

## 2026-10-25 双 AI 评审修复轮（10 findings，修 7 留 3 + 复审 F-11 修复）

修复内容与锁定测试见 `self-review.md`。验证：

| # | 命令 | 结果摘要 |
|---|---|---|
| 15 | `uv run pytest aixcoding/tests/tools -n0 -q` | **52 passed** in 5.14s（新增 4 个锁定用例：词边界/读失败 fail-closed/列名漂移点名/HTML 尾符） |
| 16 | `uv run ruff check aixcoding --no-fix && uv run ruff format --check aixcoding` | All checks passed / 48 files already formatted |
| 17 | `uv run python aixcoding/tools/gen_customizations.py` | 重生成 OK；C001 标记列已无 `-->` 残留 |
| 18 | `uv run python aixcoding/tools/check_docs.py` | 8 ADR + 3 design / OK |
| 19 | 复审 F-11 修复后：`uv run pytest aixcoding/tests/tools -n0 -q`（+ ruff check/format） | **52 passed** in 5.04s / All checks passed / 49 files already formatted（`added_line_has_marker` 改用 `MARKER_PREFIX_RE` 统一两条路径词边界口径） |

## 未验证事项

- CI 环境执行（aixcoding-tests.yml 未建，U3 任务）；
- `--base` 传真实 PR base / 上游 tag 的场景（本地以 HEAD 代替；微型 git repo 测试覆盖了 ref 解析与失败路径）。
