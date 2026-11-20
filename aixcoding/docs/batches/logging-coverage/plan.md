# 计划：定制功能日志覆盖补全（logging-coverage）

> 结构化任务清单（check_docs --closure 校验最小形态）；AI 每次接手先读本文件。

## 状态

- 2026-11-19：requirements 完成；design 签认（三轮 AI 评审收敛，裁决 A/B/C 已落实）；test-plan 完成。
- 2026-11-20：分支 `feat/logging-coverage`；**T1-T7 实施完成，T8 机器验证全绿**（verify --smart PASSED：custom 865 / upstream 16621 / architecture 326；gen_customizations --strict 0 warning；R2 空表核实）。两处实施级偏离落 verification.md 实施注记。**当前阶段：手工三抽验 + self-review（双 AI 评审）→ PR。**

## 任务清单

- [x] T1 auto-update 迁树：`client.py`（成功路径 detail 中文化 + 五失败分支主通道 WARNING 双写 + 204/304 不打）、`flow.py`（CONFIRM/SKIP INFO、:199/:275 detail 中文化）、`runner.py`（:150 ERROR 双写、:152 detail）、`state.py`（detail 中文化）——实施偏离：unbuildable params detail-only（"未检查"非"失败"），见 verification 实施注记 1
- [x] T2 skills：`skill_paths.py`（detail 域 logger + 成功清单 + 函数级异常 detail+re-raise + `_team_skill_dirs` FileNotFoundError 区分）
- [x] T3 guard：`guard_install.py`（`aixcoding.detail.guard` + `aixcoding.guard` 单点：四路径打点，`_replace_unparsable` 主通道 WARNING 双写，行级 RUF001 noqa）
- [x] T4 catalog：`catalog.py` 重新启用 `_log`，`:1023` 覆盖（含 `_join_bounded` 截断）与 `:986` 清空两处主通道 WARNING 双写，`:84-88` 定调注释修订
- [x] T5 config：`loader.py` `_warn` 三通道（九处统一，中文文案；既有 6 处英文断言随批中文化）
- [x] T6 startup：`startup/__init__.py:32` 三通道（行级 noqa；既有 1 处断言中文化）
- [x] T7 测试：集中新文件 `aixcoding/tests/logging_coverage/test_coverage.py`（25 用例）+ `test_flow.py`(+2) + `test_catalog_sync.py`(+3)；test-plan 组织表实施形态为"集中为主、catalog 复用既有设施"（活文档偏差，用例覆盖矩阵行不变）
- [x] T8 验证（机器部分）：verify --smart / aixcoding/tests / architecture / gen_customizations --strict / ruff check+format 全绿，证据落 verification.md
- [x] T8 验证（手工部分）：三抽验完成（2026-11-20，四条 WARNING 主卷命中 + 三通道统一中文 + PII 双卷 + first-run 边界实证，证据落 verification.md 手工节）
- [x] T9 文档：self-review.md 起草完毕（四轮评审记录 + F1 blocker 处置 + F2/F3 呈报，待责任人签认记录档）；overview.md:21 过时表述已修订（2026-11-20）

## 续接入口

- 读 design.md（已签认 2026-11-19）"逐条定案"节实施 T1-T6；行号为 2026-11-19 基线 098b66f1，实施时以符号定位为准；
- R13 豁免两处（guard_install.py、startup/__init__.py 行级 noqa）随 T3/T6 落；
- 提交流程：特性分支 + PR（用户逐步授权 git 写操作）。
