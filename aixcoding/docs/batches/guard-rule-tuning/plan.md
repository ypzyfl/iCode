# 任务清单：护栏规则包调优（guard-rule-tuning）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文。

## 状态

适配改动包 (4)（F2 裁决：回环完全豁免，含 localhost/*.localhost）；全量验证重跑中。
ADR 已由责任人签认（2026-11-26）。**停等责任人：self-review.md 签认、F8 归属确认。**

## 待办

- [x] 责任人签认 `design.md`（2026-11-26）
- [x] 应用 17 文件改动包＋rules.json 两处 note 修正
- [x] 回归验证：自检 106 / pytest 27+1skip / 部署验证 67 / ruff＋format / ty 三平台——全绿
- [x] 本机安装护栏并确认开启态（33 条 · 开 32 · 关 1；B16 headless 实测通过）
- [x] verification.md 落盘验证证据
- [x] 双 AI 自审（评审→F1 修复→增量复审通过）→ `self-review.md` 产出
- [ ] 责任人签认 `self-review.md`
- [x] 责任人签认 ADR（2026-11-26）
- [x] F2 裁决：回环完全豁免（含危险端口与 localhost/*.localhost）——责任人经改动包 (4) 拍板
- [ ] 责任人确认 F8（`aixcoding/docs/pr/` 归属）
- [ ] PR 描述（§7 结构）；git 提交/推送按逐条授权执行
- [ ] 发布前手工抽测（A/B/C/D/E 组）视需要执行

## 挂起与备忘

- 黑名单出厂条目（`*.bocsys.cn`、`22.122.49.168/32`）为业务给定的禁止攻击目标，
  维护义务由 ADR 承载。
- 改动包源：`D:\Ai\iCode-guard-hooks-changes(2)`（桌面 zip 展开版，已逐文件审计）。
- 评审未修项与理由见 `self-review.md`（F3-F7 责任人拍板不修；marshal/exec 残留未拍板）。
- 用户要求已落实：合入后本机护栏保持开启。
- 提交纪律：显式路径 stage；`aixcoding/docs/pr/`（F8，归属未确认）不带上。
