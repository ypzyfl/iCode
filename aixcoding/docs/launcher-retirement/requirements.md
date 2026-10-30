# 需求：退役 diagnostics launcher（launcher-retirement）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

auth-logging 批次确立全模式落盘接线（`app.py main()` 调 `ensure_file_sink()`）后，launcher 的落盘职责被取代。launcher 及其独占组件（crash 捕获、环境快照）在上游 `test_layering.py` 留有约 18 行 DAG 豁免机制登记——是定制层在上游测试文件的**唯一**足迹。责任人价值取向：**最小上游足迹优先于可选能力**（2026-10-30 裁决），选择退役 launcher 换取足迹清零。

## 目标与非目标

- 目标：
  - 删除 `launcher.py` / `crash.py` / `snapshot.py` 及其测试（定制层 ~220 行产品代码）；
  - 回滚 `test_layering.py` 的 `_DAG_EDGE_ALLOWLIST` 豁免机制（~18 行）——上游足迹清零；
  - 规范与文档联动（DIRECTORY / UPGRADE-RUNBOOK / ADR-0011 处置 / diagnostics design 重签 / CUSTOMIZATIONS）。
- 非目标：
  - 不删 `config.py` / `logging_support.py` / `test_config.py` / `test_logging_support.py` / `test_panel_anchor.py`（落盘与面板基建，全模式接线依赖）；
  - 不做 crash 捕获的替代方案（放弃该能力，ADR-0013 记录取舍；将来需要时按 git 历史重建）；
  - 不动 auth-logging 批次已实施内容（两批次正交）。

## 用户场景

1. 上游升级时，`test_layering.py` 零冲突面（豁免机制不存在）——升级摩擦进一步降低；
2. 全模式落盘由 `app.py` 接线承担，用户无感知变化。

## 验收标准

- [ ] 三文件 + 三测试删除；`config.py`/`logging_support.py` 及其测试、`test_panel_anchor.py` 保留完好；
- [ ] `test_layering.py` 豁免机制回滚后 `uv run pytest tests/architecture` 绿；
- [ ] `python -m chrys.kernel.aixcoding.diagnostics.launcher` 入口不复存在；
- [ ] `uv run pytest aixcoding/tests` 全绿；
- [ ] `gen_customizations.py` 产物更新（launcher/crash/snapshot 登记行消失）且幂等；
- [ ] 规范联动完成：DIRECTORY §1/§3、UPGRADE-RUNBOOK:51、ADR-0011 处置（0013 回指）、diagnostics/design.md 重签；
- [ ] ADR-0013 落盘签认。

## 开放问题

- 无（合并顺序已定为**硬前置**：本批次实施与合并均须在 auth-logging（含全模式接线）落地之后——退役后落盘唯一来源是入口接线）。
