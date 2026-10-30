# 任务清单：退役 diagnostics launcher（launcher-retirement）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**实施与验证完成**（2026-10-30，分支 feat/launcher_retirement）——design 全项落地、验证全绿（见 verification.md）。剩：design 确认日期补填、diagnostics/design.md 重签、self-review（双 AI 评审）、git 提交链（逐条请示）。前置背景：auth-logging 改动已备份至 `D:\Tech\Github\huawei\iCode\fork\temp\auth-logging_backup`（恢复指南 RESTORE.md），本批次合并后恢复。

## 待办

- [x] design.md + ADR-0013 签认（2026-10-30）
- [x] test-plan.md 起草
- [x] 实施：删三件 + 三测试 + conftest 孤儿 fixture + docstring 更新
- [x] 实施：test_layering.py 豁免机制回滚（17 行，评审 Blocker 行号口径）
- [x] 规范联动：DIRECTORY §1/§3、UPGRADE-RUNBOOK:51、ADR-0011 导航注记
- [x] diagnostics/design.md 登记表删三行 + 退役注记（**重签待责任人**）
- [x] 验证：架构 1238 绿 / 定制 276 绿 / 入口消亡 / 生成器幂等（27 点）/ 残留净 / ruff+ty 过
- [ ] design.md 确认日期补填（check_docs 报空日期）
- [ ] self-review.md（双 AI 评审）
- [ ] git 提交链（add → commit → push → PR，逐条请示）；合并顺序：**本批次先行合并（责任人 2026-10-30 终裁，空窗期接受）→ auth-logging 尽快跟进**

## 挂起与备忘

- **【补做义务·勿遗忘】gen_customizations 登记源单一化**（责任人 2026-10-30 裁决：接受本批次治标 + 缺陷登记挂起，ROADMAP §5 同步登记）：生成器从所有 design 登记表聚合 anchor（快照/现行混淆），本批次以 `tier-migration/design.md:92` 事实同步治标；**将来 devtools 小批次改为单一现行登记源**（历史快照退出聚合）——触发时机：devtools 批次排队时主动想起，ROADMAP §5 2026-10-30 条目为权威记录；
- **【补做义务】crash 捕获/环境快照**：ADR-0013 退役（价值取舍），将来需要时按内联接线路径实现（ADR-0013 后果节）或 git 历史复原（revert 本批次即得）；
- 空窗问题：本批次若先于 auth-logging 合并，主干短暂无落盘（能力从未上线，无用户可见影响）——合并窗口由责任人裁决；
- ADR-0013 归全局池（standards/adr/）：豁免通道移除属架构工具变更；ADR-0011 不改状态行（非整体取代），由 0013 背景回指；ADR-0013 两处背景补充（价值取舍澄清 + 内联转向记录，2026-10-30 三方评审后）按"不改变结论的背景补充"原地修正；
- 上游足迹清单（本批次后）：产品代码零 + 测试文件仅剩 screen.py MODULE_ORDER 一行（F6 面板）+ auth-logging 的 app.py 接线（若其先行合并）。
