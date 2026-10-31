# 测试方案：退役 diagnostics launcher（launcher-retirement）

> 活文档：随时更新、不签认；质量由双 AI 自审与回归测试保障。

## 测试范围与策略

- **纯删除性批次，无新增行为逻辑**——不新增测试文件（§5 义务针对新增模块，本批次无）；测试重心是"删后不破坏"的回归 + 残留检查。
- 保留测试完好性锚定：`test_config.py` / `test_logging_support.py` / `test_panel_anchor.py` / `aix_logger_state` fixture 全量跑绿即证明保留项无损。
- 上游架构回归：`tests/architecture` 全量（豁免机制回滚 + `:220` kernel-private 机制未触碰的双重验证——若误删 `:220`，kernel-private stale 检测将因观察集合缺失而红）。

## 覆盖矩阵

| 验收标准（requirements.md） | 验证入口 | 类型 |
|---|---|---|
| 三文件+三测试删除、保留项完好 | `uv run pytest aixcoding/tests -n0 -q` 全绿（保留三测试在内跑） | 回归 |
| `test_layering.py` 回滚后架构绿 | `uv run pytest tests/architecture -n0 -q`（含 `:220` kernel-private 机制存活验证） | 回归 |
| launcher 入口消亡 | `uv run python -m chrys.kernel.aixcoding.diagnostics.launcher` → `No module named ... launcher` | 手工 |
| gen_customizations 幂等 | 连跑两次，第二次 `git diff aixcoding/docs/CUSTOMIZATIONS.md` 为空（**顺序前置**：先完成 `batches/diagnostics/design.md` 登记表删三行，C005 anchor 才收敛——评审 Major 2） | 手工 |
| 残留零 | `grep -ri "launcher" src/chrys/kernel/aixcoding aixcoding/tests` 于 diagnostics 语境零命中（`logging_support.py` docstring 已改）；`grep -i "crash\|snapshot"` 同理 | 手工 |
| 规范联动完成 | self-review checklist 逐项核（DIRECTORY/RUNBOOK/ADR-0011 注记/diagnostics design 重签） | 评审 |
| ruff / ty 门禁 | 改动文件过 `ruff check` / `ruff format --check` / `ty check`（win32） | 门禁 |

## 异常与降级路径

本批次无新增逻辑故无新增异常路径；删除后的悬挂引用风险由残留 grep + 全量回归双覆盖（任何 import 残留会在收集期即红）。

## 手工验证步骤（结果记入 verification.md）

1. `set PYTHONPATH=& set UV_PYTHON=3.14.3&& uv run pytest tests/architecture -n0 -q` → 全绿；
2. `set PYTHONUTF8=1&& uv run pytest aixcoding/tests -n0 -q` → 全绿（较退役前少 launcher/crash/snapshot 三文件的用例数）；
3. `uv run python -m chrys.kernel.aixcoding.diagnostics.launcher` → No module named；
4. `gen_customizations.py` 连跑两次 → 第二次 diff 空；`CUSTOMIZATIONS.md` 变更 = launcher/crash/snapshot 登记行消失 + C005 anchor 收敛；
5. 残留 grep（见覆盖矩阵）；
6. `ruff check` 改动文件 + `ty check --python-platform win32 src/chrys`。
