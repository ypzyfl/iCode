# 计划：本地统一验收入口（local-verify）

> 活文档：任务清单 / 状态 / 续接入口。AI 每次接手先读本文件。

## 状态

**实施与文档联动完成；双 AI 自审首轮处置完毕（2026-11-01）**：verify.py（五模式，~190 行）
+ 18 个行为测试全绿 + 手工验证（部分实测部分单测钉住，如实记录于 verification V1/V2）+
四件文档联动 + 终验 342 passed / 2 skipped。**停等增量复审**（Kimi-K3.1-Pro 复审 F-01~
F-04 修复增量，只审增量）→ self-review.md 签认 → PR。

**前置依赖（2026-11-01 复审 R-03 裁决；同日已完成）**："窄 auth 防呆 + launcher 动态端口"
前置微改动批次 `auth-isolation-mock-ports` 已实施并验证（定制全量 324 passed / 2 skipped，含第三轮
复审 S-01/S-04 收尾修复）——R-03/R-04 的放大效应已消除，本批无未决前置。

## 任务清单

| # | 任务 | 状态 |
|---|---|---|
| 1 | requirements.md | 完成（活文档，已随 F-01/F-02 联动修订） |
| 2 | design.md 起草 → 外部 AI 评审（8 findings）→ 处置修订 → 责任人签认（2026-11-01，"无特别意见"——ADR 判定③与 --full 取舍随签认接受） | 完成 |
| 3 | test-plan.md（覆盖矩阵 15 用例 + 异常路径 + 手工步骤） | 完成 |
| 4 | 实施：`aixcoding/tools/verify.py` + `aixcoding/tests/tools/test_verify.py`（实施期单测抓到 `_aggregate` 对 None 判假的真 bug 并修复） | 完成 |
| 5 | 文档联动：DIRECTORY.md §5 / DEVELOPMENT.md §4.2-4 / UPGRADE-RUNBOOK / ADR-0001 修订注记 | 完成 |
| 6 | 验证：verification.md V1（单测 + 手工全项，8 条验收标准逐条核销） | 完成 |
| 7 | 双 AI 自审 → self-review.md → 责任人签认 | **停等（评审 AI 待发起）** |
| 8 | 特性分支 feat/local_verify + PR（目标 main_aixcoding_cli，双 CI 门） | 待办（git 操作逐条授权） |

## 责任人操作项（非本批代码交付物）

- GitHub 网页核验分支保护 required checks 同时钉住 `AIxCoding quality gate` 与
  `AIxCoding upstream gate`（ruleset 不在仓库内，workflow/job 改名后需重核）。

## 续接入口

- 设计与背景：本目录 `requirements.md` / `design.md`；
- 讨论收敛过程（2026-10-31/11-01 双 AI 讨论，定制测试运行机制 + Smart Test 盲区定性）：
  见会话记录，要点已沉淀进 requirements"背景与问题"；
- 已知关联批次：ci-gate（CI 侧双门）、mock（定制套件内容）、upstream-merge-v0.32.2
  （升级验证口径消费方）。
