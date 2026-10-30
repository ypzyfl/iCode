# 计划：aixcoding/tests 的 ruff 豁免切换为目录级配置

> 活文档：任务清单与状态，AI 每次接手先读。

## 状态（2026-10-30）

- [x] requirements.md 起草
- [x] design.md 起草（**停等签认中**——R2 清单：pyproject.toml +2 行）
- [x] test-plan.md 起草
- [x] design 评前修订（2026-10-30 外部 AI 评审：RUF001 11→8、S106 8→7 数字修正；补组级 vs 规则级取舍标准、RUF001/RUF002 频率边界、S 整组扩展面与 RUF001 混淆字符代价——无 blocker）
- [x] design 签认（2026-10-30，确认意见"无特别意见"）→ 实施：pyproject +2 行、28 文件删头、1 文件收窄 RUF002
- [x] 验证四件套（ruff aixcoding 双命令绿 / ruff src tests 绿 / pytest 293 passed+2 skipped+1 环境性失败[7777 占用在案] / gen 幂等 29 点）
- [x] verification.md 落盘
- [x] 双 AI 自审（评审 AI：Deepseek-V4-Pro，无 blocker，F1 重签/F3 补注已修、F2 留档不修）→ self-review.md 已产出（待责任人签认）
- [ ] PR（feat 分支 feat/ruff_test_exemptions 已建 → add → commit → push，git 操作逐条授权）

## 续接入口

- 方案与 R2 清单：`design.md`（未签认前不动代码）；
- 待办出处：auth-logging 批次 PR #70 CI 修复期间提出（2026-10-30 责任人裁决记录待办）；
- 分支：未建（签认后建 `feat/ruff_test_exemptions`）。
