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

## 未验证事项

- **GitHub Actions 远程执行**：本地不可复现；push 后首跑观察（步骤/语法/runner 环境差异），失败以补丁 commit 修复；
- `uv sync` 在干净 runner 的时长（本地环境已缓存）。
