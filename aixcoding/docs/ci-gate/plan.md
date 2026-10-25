# 任务清单：定制 CI 质量门（ci-gate / aixcoding-tests.yml）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

双 AI 评审**收敛**（1 轮：0 blocker，修 6 + F7 单开微改）；53 测试全绿；`self-review.md` 已落盘（草案）。待责任人签认 self-review → 提交（ci-gate 批 + F7 规范微改独立 commit）→ push 后 Actions 首跑观察。

## 待办

- [x] design.md 签认（责任人 2026-10-25）
- [x] 实施workflow（12 步：环境 4 + ADR-0004 四步 + 四工具 5）
- [x] 本地等效命令验证 + verification.md 留证（#1-#8）
- [x] 实施副产：修复 git core.quotepath 中文路径 bug（_common.py）+ 锁定测试
- [x] 双 AI 自审第 1 轮：评审 AI = CodeBuddy·Deepseek-V4-Pro；0 blocker；修 6（F1-F6）+ F7 单开
- [ ] self-review.md 签认（责任人）→ 提交 → push 后 Actions 首跑观察（结果补录 verification）

## 挂起与备忘

- base 锚点：`origin/main_iCode`（当前分叉点 3104004）；**纪律：main_iCode 保持纯上游镜像**（固化进升级 runbook，阶段二第 4 项）；
- action 版本 pin 复用上游 ci.yml 同版本（checkout v7.0.1 / setup-uv v10.3.0 (uv 0.13.1) / setup-python v7.0.0）；
- quotepath bug 教训：门禁工具的 git 输出必须显式禁用转义（已在 `_common.git()` 注释记录）；中文命名资产（ADR/diagnostics 文档）是常态而非常例。
