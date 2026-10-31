# 需求：aixcoding/tests 的 ruff 豁免切换为目录级配置

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

`aixcoding/tests/`（33 个 py 文件）有 29 个带文件级 `# ruff: noqa` 头，是早期批次"零上游足迹"（R1）权衡的产物。该模式靠人记、必漏：每类新规则、每个新文件都可能漏豁免，直到 CI 全目录扫描（`ruff check aixcoding/`）才暴露。实证：PR #70 首跑 CI 拦截 `test_session_logging.py` RUF001×30（断言冻结口径中文日志消息的全角标点）——S101/S106 是 10-29 抄邻居文件头带上的，RUF001 只有"断言中文消息"的文件需要，漏了。

## 目标与非目标

- 目标：
  - `pyproject.toml` per-file-ignores 增加 `"aixcoding/tests/**"` 目录级豁免（带 R3 marker），一劳永逸、集中可审计；
  - 清理各测试文件的冗余 noqa 头（新测试文件零心智负担）。
- 非目标：
  - 不动 `aixcoding/tests/` 之外任何文件级 noqa（`session.py` 等产品代码的 RUF001 头豁免理由不同，保留）；
  - 不扩 `aixcoding/tools/`、`aixcoding/mock/` 非测试文件（其豁免需求族不同：T201 为主，见 design 备选 C）；
  - 不改上游 `tests/**` 既有豁免行。

## 用户场景

1. 开发者新增 `aixcoding/tests/` 测试文件（断言冻结中文消息 + 假凭证）：零 noqa 配置，直接过 CI 门禁；
2. ruff 升级带来 S/RUF 组新规则码：测试目录自动豁免，无需逐文件补头。

## 验收标准

- [x] `pyproject.toml` per-file-ignores 含 marker 行 + `"aixcoding/tests/**" = ["S", "PERF401", "RUF001"]`；
- [x] 28 个测试文件 noqa 头删除、`tools/test_check_import_boundaries.py` 头收窄为 `# ruff: noqa: RUF002`（S101 由目录行覆盖）；
- [x] `uv run ruff check aixcoding/` 与 `uv run ruff format --check aixcoding/` 绿；
- [x] `uv run pytest aixcoding/tests -m "not integration and not gc_calibration"` 全绿（本地 293 passed / 2 skipped + 1 环境性失败在案：`test_mock_launcher` 7777 端口被 ArmouryCrate 占用，PR #70 同款记录，CI Linux 待 PR checks 确认——评审 F3 补注，R8）；
- [x] `uv run python aixcoding/tools/gen_customizations.py` 产物更新且连跑两次幂等（freshness 义务，随提交）；
- [x] 上游豁免格局不变：`uv run ruff check src/ tests/` 绿。

## 开放问题

- 无（RUF002 单文件保留方案已在 design 定稿；如裁决改为目录行加 RUF002，design 随之修订）。
