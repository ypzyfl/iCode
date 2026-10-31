# 需求：追上游 v0.32.2（upstream-merge-v0.32.2）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

上游 iCode 已发布 v0.32.0 / v0.32.1 / v0.32.2（当前最新 release tag 为 v0.32.2 = c54b60cf）。
本 fork 主线 `main_aixcoding_cli` 基线仍为 0.31.0（CUSTOMIZATIONS.md 人工区），落后一个 minor + 两个 patch。
DEVELOPMENT.md §8 升级节奏条款：每次上游发布后评估跟进，长期不升级是需显式决策的风险状态。
区间 `v0.31.0..v0.32.2` 共 55 提交、349 文件、+34282/−2986。

## 目标与非目标

- 目标：`main_aixcoding_cli` 基线追至 **v0.32.2**，全部在册定制点（C001–C029）存活且全绿。
- 非目标：
  - 不追 `origin/main_iCode` 镜像头（918cb599，领先 v0.32.2 共 23 个未发版提交——留待下次升级）；
  - 不借升级顺手做定制功能开发；
  - 旧分支 `main_aixcoding_cli_0.28.0_final` 按冻结条款不随升级（runbook §8）。

## 用户场景

1. 内部用户获得上游 0.32.x 的修复与新特性（TUI、稳定性和 CI 修复等 55 提交内容）。
2. 开发者后续定制开发（ROADMAP 阶段三余量批次）基于新基线，降低三层冲突累积债务。

## 验收标准

- [ ] merge 后 `gen_customizations.py` 重跑幂等（连跑两次 `git diff` 为空），C001–C029 无丢失。
- [ ] runbook §4 验证矩阵全绿：上游全量（chrys_test --full，CodeBuddy 环境配方）、定制四门
      （aixcoding/tests / check_docs / check_import_boundaries / gen_customizations 幂等）、
      R2/R3 以新 merge-base 通过、ty 三平台。
- [ ] CUSTOMIZATIONS.md 人工区更新：当前所基于的上游版本 → 0.32.2、升级完成日期。
- [ ] 行为锚定测试 `aixcoding/tests/diagnostics/test_panel_anchor.py` 绿（anchor 核对机检）。
- [ ] PR 双 CI（aixcoding-tests.yml + 上游 ci.yml 桥接）绿。
- [ ] TUI 冒烟：`uv run icode` 启动正常，F6 可见 aixcoding tab，登录徽标/命令可用。
- [ ] 升级决策清单（冲突点全清单+处理意见、定制化改变清单）已产出，全部决策经责任人裁决并留痕
      （verification.md 追加；淘汰类决策未经裁决不删除任何定制）。

## 开放问题

（两项均已裁决，2026-10-31）

- fork 第四段版本号 → **本次保留上游三段（0.32.2），不启用四段**（责任人 2026-10-31 终裁）：
  四段启用与日构建递增机制独立设计，相关分析已登记独立待办
  （fork 仓外 temp/aixcoding-todos/2026-10-31-four-segment-version.md）。
- `removal_condition` 列回填 → **单独作为独立事项执行，不混入本次升级**（责任人裁决）。本次升级
  期间该列维持"待补"，淘汰检查按"升级决策交付物"要求以人工对比分析执行；回填全景清单
  （29 点 / 6 个源 design / 8 种条件值草案）已登记独立待办（fork 仓外 temp/aixcoding-todos/）。
