# 测试方案：追上游 v0.32.2（upstream-merge-v0.32.2）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

升级批次不新增功能代码，测试 = **三层回归 + 流程产物验证**（对应 design「升级决策交付物」与
runbook §3/§4）：

1. **结构层（机检）**：marker 存活 + anchor 行为——`aixcoding/tests` 全套（含
   `diagnostics/test_panel_anchor.py` 行为锚定，禁 mock 锚点本身）+ `gen_customizations.py` 幂等；
2. **语义层（全量）**：上游侧 `scripts/chrys_test.py --full`（CodeBuddy 环境配方：清 PYTHONPATH、
   PYTHONUTF8=1、大写盘符、`--deselect tests/app/test_install_scripts.py`）+ ruff/format/ty 三平台 +
   i18n 管线（extract→update→compile→check 二次幂等）；
3. **流程产物**：升级决策清单（冲突点+处理意见、定制化改变清单）经责任人裁决留痕于
   `verification.md`；CI 证据归属 PR checks 本身（§7）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口 | 类型 |
|---|---|---|
| merge 后 gen 幂等、C001–C029 无丢失 | `aixcoding/tools/gen_customizations.py` 连跑两次 `git diff` 为空；清单 diff 逐点核对 | 工具/结构 |
| runbook §4 矩阵全绿 | `scripts/chrys_test.py --full` + 定制四门（aixcoding/tests / check_docs / check_import_boundaries / gen 幂等）+ R2/R3 以新 merge-base + ty 三平台 | 全量回归 |
| 行为锚定测试绿 | `uv run pytest aixcoding/tests/diagnostics/test_panel_anchor.py -n0 -q` | 行为锚定 |
| CUSTOMIZATIONS 人工区更新 | `git diff aixcoding/docs/CUSTOMIZATIONS.md` 人工区两行（版本→0.32.2、日期） | 人工检查 |
| PR 双 CI 绿 | aixcoding-tests.yml + 上游 ci.yml 桥接（PR checks） | CI 门禁 |
| TUI 冒烟 | `uv run icode`：启动、F6 aixcoding tab、登录徽标/命令 | 手工端到端 |
| 升级决策清单裁决留痕 | verification.md 裁决记录节（追加不删旧） | 流程检查 |

## 异常与降级路径

- **借壳 key 丢失**（oracle 计数 ≠ 2503）→ i18n 管线重走（extract→update→compile）复测；
  仍缺 = 上游 msg 定义处变更 → **暂停呈报**（不自行改上游）；
- **anchor 符号漂移**（ty / 定制测试红）→ 按 design 假设表逐 anchor 核对；适配需触上游文件 →
  停下按 R2 增补报批；
- **auto-merge 语义静默错** → 三层兜底：核对矩阵逐项（design）+ 行为锚定 + 全量；
- **升级引入的失败不属于本批次修复范围**（上游自身回归）→ 记录在案随决策清单呈报，不擅自修上游。

## 手工验证步骤（若需）

1. `uv run icode`（大写盘符）→ 启动正常，无崩溃告警；
2. F6 → 日志面板出现 aixcoding tab；
3. 顶栏徽标显示登录态；`/login` `/logout` 命令可发现（`/man` 索引含二者）；
4. 结果记入 verification.md。
