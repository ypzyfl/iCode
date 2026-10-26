# 验证证据：定制 CI 质量门（ci-gate / aixcoding-tests.yml）

> 活文档：命令 + 输出摘要（R7 落盘形态，追加不删旧）。

## 2026-10-25 实施完成（CI 步骤本地等效验证）

环境：Windows，`PYTHONPATH=`、`PYTHONUTF8=1`、`UV_PYTHON=3.14.3`；R2/R3 base 与 CI 同语义（`git merge-base origin/main_iCode HEAD` = 3104004）。

| # | CI 步骤（本地等效命令） | 结果摘要 |
|---|---|---|
| 1 | `uv run python aixcoding/tools/check_docs.py` | 8 ADR + 4 design + 1 self-review / OK |
| 2 | `uv run ruff check aixcoding/` | All checks passed |
| 3 | `uv run ruff format --check aixcoding/` | 53 files already formatted |
| 4 | `uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -n0 -q` | **53 passed** in 5.22s（含新增中文路径锁定用例） |
| 5 | `uv run python aixcoding/tools/check_import_boundaries.py` | scanned 1052 / OK |
| 6 | gen_customizations + `git diff --exit-code aixcoding/docs/CUSTOMIZATIONS.md` | **GEN-IDEMPOTENT-OK**（清单新鲜度幂等） |
| 7 | `check_r2_diff --base 3104004` | changed=55 / **upstream_changed=1**（AGENTS.md，已批准）/ approved_pool=2 / OK |
| 8 | `check_r3_markers --base 3104004` | upstream_changed=1 / marker_checked=1（AGENTS.md:5 有标记）/ OK |

实施中发现并修复的真 bug：**git `core.quotepath` 默认把中文文件名转义为八进制+引号包裹**，导致 `is_custom()` 对中文命名文档（standards/adr/ 全部 ADR）判定失效、分叉点 base 下 8 个 ADR 被误报"未授权上游改动"。修复：`git()` 统一 `-c core.quotepath=off`（`_common.py`）；锁定测试 `test_chinese_filenames_not_misrouted_by_quotepath`（52→53 passed）。该 bug 只在 base 拉出中文文档全量 diff 时暴露——CI 门禁的 merge-base base 语义正是首个触发场景，门禁自身抓住了门禁工具的 bug。

## 2026-10-25 远程首跑（push c926e81 触发）

**AIxCoding Tests #1：completed / success**，run 40174583158，job 28s（workflow 32s，uv 缓存与上游 CI 同仓库共享命中）。

步骤级确认（GitHub API `/actions/runs/40174583158/jobs`）：环境 4 步 + ruff check / format / check_docs / pytest / check_import_boundaries / 清单幂等 / R2·R3 分叉点门禁——**12 个核心步骤全部真实执行、全部 success、无 skipped**。`-n 8` 并行下 53 用例同样通过（本地 `-n0` 串行无差异问题）。

结论：阶段二 DoD 之"四工具挂入 CI 跑绿"达成；下方未验证事项全部闭环。

## 未验证事项

- （首跑后清空；后续新增未验证事项在此登记）
