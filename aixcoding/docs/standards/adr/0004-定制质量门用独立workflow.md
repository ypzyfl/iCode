# ADR-0004：定制质量门用独立 workflow

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-22
- 确认意见：符合定制化方案整体方向。在CI/CD时注意需要补充定制测试的运行。

## 背景

定制测试独立收集（ADR-0001）后，CI 必须有定制资产的执行点（规范 §1：语义冲突只能靠定制测试集回归发现，"请大家记得本地跑"不是机制）。同时核查发现存量治理缺口：`ci.yml` 的 lint 路径（`src/ tests/ scripts/chrys_test.py …`）不含根 `aixcoding/` 与 `mock_server/`——部分定制代码在 CI 质量门外。

## 决策

*（本文为决策时点快照；现行规则以 DIRECTORY.md §7 为准。）*

新建 `.github/workflows/aixcoding-tests.yml` 作为定制资产唯一 CI 质量门，四步：

```yaml
- run: uv run ruff check aixcoding/
- run: uv run ruff format --check aixcoding/
- run: uv run python aixcoding/tools/check_docs.py
- run: uv run pytest aixcoding/tests -m "not integration and not gc_calibration"
```

- 触发条件与 `ci.yml` 对齐（PR + push）；初始单 Linux 平台（定制测试大多平台无关），平台敏感测试（tui、auth 加密后端）验证后再扩矩阵。
- ty 对齐上游惯例（只查 `src/chrys`，不查测试与 mock），不额外加。
- mock 的质量门禁**不单独做**：代码规范由 `ruff … aixcoding/` 覆盖（mock 在内）、行为正确性由契约测试（`aixcoding/tests/mock/`）覆盖、类型检查对齐"不查"。mock 与定制测试生命周期完全同步，拆开只会制造"改了但没触发"的缝隙并翻倍环境成本。

产品定制代码（`src/chrys/aixcoding/`）不进这个门——它随上游 `ci.yml` 的 ruff/ty/test 全套射程自动覆盖。

## 理由

**新建独立文件优于改 `ci.yml` 插 job**：

| 维度 | 改 `ci.yml` | 新建独立 workflow |
|---|---|---|
| 升级冲突面 | `ci.yml` 是上游高频调整文件（分片、缓存、action 版本 pin 持续在变） | 上游不会动我们自建的文件名，冲突面 ≈ 0 |
| 演进自由度 | 每次调整都动上游文件 | 超时、并发、未来 job、触发条件独立可控 |
| 先例 | — | `cd.yml`（aixcoding-cli 发布流程）已是自建 workflow |

## 否决的备选

- **改 `ci.yml` 插入 job**：见上表，被冲突面否决。
- **`testpaths` 加入 `aixcoding/tests` 实现默认收集**：CI 分片 `pytest_args` 显式传路径参数会绕过 `testpaths`，根本解决不了 CI 问题；反而污染本地裸跑 `pytest` 的默认行为（`-n 8` 并行混跑、上游计时基准被污染）。
- **mock 单独门禁（单独 workflow/job）**：生命周期同步论 + 成本论，见"决策"节。

## 后果

- `.github/workflows/` 新增文件属上游目录内定制文件（GitHub 硬约束：workflow 必须位于此），走 R2 报批，以新文件形态落地；
- 定制质量门与上游 CI 解耦：上游重组 CI 不影响定制门，反之亦然；
- `check_docs.py`（文档签认校验）随本门执行，本地可先行：`uv run python aixcoding/tools/check_docs.py`。
- **平台矩阵演进注记（2026-11-01）**：决策节"初始单 Linux 平台（定制测试大多平台无关），
  平台敏感测试……验证后再扩矩阵"的预留条款经 windows-matrix 批次兑现——workflow 重构为
  三层（`test` 双 OS 矩阵实际执行 DPAPI 等平台真实用例 / `govern` 单 Linux 治理 / `gate`
  保名 `AIxCoding quality gate` fail-closed 汇总）。决策边界不变：独立 workflow、不改上游
  `ci.yml`、质量门内容（lint/docs/pytest/治理工具）原样保留；详见
  `aixcoding/docs/batches/windows-matrix/design.md`。
