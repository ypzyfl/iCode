# 计划：轻量决策记录（MADR——决策记录双档制）

> 活文档：任务清单/状态/续接入口，AI 每次接手先读。

| # | 任务 | 状态 |
|---|---|---|
| 1 | requirements.md 起草 | 完成 |
| 2 | design.md 起草 + 五次责任人修正 + 外部评审（3B+3S）+ 复审（3F）闭环 | 完成 |
| 3 | design 签认（责任人） | 完成（2026-11-12） |
| 4 | test-plan.md | 完成 |
| 5 | 实施 9 处联动：ADR 正文 / DEVELOPMENT×3 / PEER-REVIEW-HOWTO / SELF-REVIEW-HOWTO / DIRECTORY×2 / README×2 / madr 目录（README，首条条目设计已撤销——见 design 六次修正） | 完成 |
| 6 | 验证：check_docs（普通+closure）+ gen_customizations --strict + 结构一致性人工核对 | 完成（三重门禁全绿，verification.md 最终轮） |
| 7 | ADR-decision-log--dual-tier-decision-records 签认（责任人本人编辑头部） | 完成（2026-11-12） |
| 8 | 双 AI 自审（换评审 AI，SELF-REVIEW-HOWTO）+ self-review.md 落盘签认 | 完成（3 轮：4B+2S+2N → 增量 B3 残留+B5 → 通过；已签认） |
| 9 | PR（描述按 §7 格式）+ 授权 git 操作 | 待办 |

## 续接入口

- 当前停等点：任务 8（双 AI 评审安排）——责任人动作。design 与 ADR 均已签认（含六/七/八次修正与 ADR 模板行一致性修正的重签，2026-11-12）。
- closure 全绿条件：任务 8 落盘 self-review.md 后清零。
- 挂起无。
