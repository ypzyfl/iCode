# 需求：定制 CI 质量门（ci-gate / aixcoding-tests.yml）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

ADR-0004（2026-10-22 签认）定稿"定制质量门用独立 workflow"，DIRECTORY.md §7 标注"过渡期待建"，ROADMAP 阶段二清单第 3 项、batches/restructure/plan.md U3。四工具已落地（ea3650f）但尚无 CI 执行点——门禁只在本地跑等于没有门禁（ADR-0004 背景："请大家记得本地跑"不是机制）。

## 目标与非目标

- 目标：
  - 新建 `.github/workflows/aixcoding-tests.yml`：ADR-0004 四步（ruff check / ruff format --check / check_docs / pytest aixcoding/tests）+ 四工具挂入（check_import_boundaries、gen_customizations 幂等校验、check_r2_diff、check_r3_markers）；
  - R2/R3 门禁 base = `git merge-base origin/main_iCode HEAD`（分叉点 = 上游基线锚点，用户确认 main 已重命名 main_iCode）；
  - 阶段二 DoD 达成项："四工具与诊断包挂入 CI 跑绿"之四工具半。
- 非目标：
  - 不改上游 `ci.yml`（ADR-0004 已否决）；
  - 不做多平台矩阵（ADR-0004：初始单 Linux，平台敏感测试验证后再扩）；
  - 不加 ty（对齐上游惯例只查 src/chrys）；
  - 诊断包挂入（其测试尚不存在，待实施后自然被 `pytest aixcoding/tests` 覆盖）；
  - 分支保护规则配置（GitHub 仓库设置，非仓库资产，另行操作）。

## 用户场景

1. **PR 门禁**：往 `main_aixcoding_cli` 提 PR → 定制门自动跑 → R2/R3/标记/边界/清单一致性全绿方可合并；
2. **push 自检**：直接 push 到 `main_aixcoding_cli` → 同套门禁；
3. **越权拦截**：PR 含未批准上游文件改动 → check_r2_diff 失败，PR 红叉并展示未批准清单。

## 验收标准

- [ ] workflow 文件落地 `.github/workflows/aixcoding-tests.yml`（触发 PR+push 至 main_aixcoding_cli；单 ubuntu-latest；action 版本 SHA pin 对齐上游 ci.yml）；
- [ ] 步骤覆盖：ADR-0004 四步 + check_import_boundaries + gen_customizations 幂等（`git diff --exit-code aixcoding/docs/CUSTOMIZATIONS.md`）+ R2/R3（base=merge-base origin/main_iCode HEAD）；
- [ ] 本地等效命令逐条跑通（verification 留证）；
- [ ] YAML 结构合法（人工审 + push 后 Actions 首跑观察，见 test-plan 未验证事项）。

## 开放问题

- 无（base 锚点 main_iCode 已确认；ADR-0004 已定四步框架与本批扩展口径）。
