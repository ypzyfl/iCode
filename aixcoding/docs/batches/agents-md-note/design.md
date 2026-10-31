# 设计：AGENTS.md 定制规范入口段补登记（agents-md-note）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：目前方案没有大问题

## 方案概述

追溯性补登记：新分支建立时在 `AGENTS.md` 插入的 "AIxCoding customization" 入口段（第 5–12 行：`<!-- AIxCoding ... -->` 标记注释 + 指向 `aixcoding/docs/standards/DEVELOPMENT.md` 的治理说明）系对上游文件的既有定制改动，当时未走 R2。本设计即该改动的批准落盘；签认后 `gen_customizations.py` 将其合法收录进 CUSTOMIZATIONS.md。纯文档登记，无任何代码改动。

## 备选方案对比

唯一合理路径：既成改动的补正只有"补登记"或"回退改动"两条路，回退会移除 AI 代理的规范入口（R2 流程提示），不可取。

## 上游改动清单（R2；无上游改动则删除本节）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `AGENTS.md` | 正文头部插入 AIxCoding customization 段：HTML 注释标记（`<!-- AIxCoding entry point ... -->`）+ 两段治理说明（定制资产范围、R2/R11 停等要求，指向 aixcoding/docs/standards/） | 8 | 段首 HTML 注释（AGENTS.md:5） |

R1 自查：纯导航文档段，无业务逻辑可外置；上游 AGENTS.md 是该说明唯一自然落点。

## 对上游隐式行为的假设

无（静态文档，不参与任何运行时行为）。

## 定制点登记预告

点级登记（customization-registry 批次起；C001 现行登记收敛于此——ai-gates 批次曾同落点登记，已声明迁移）：

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C001 | AGENTS.md | AIxCoding entry point | | AGENTS.md 文档结构（正文段落，无符号依赖） | 低 | 〔常驻〕随 fork 定制体系存续，仅改址/退役时提请裁决 |

## 风险与最坏情况

上游重写 AGENTS.md 时该段产生 merge 冲突——正是清单登记它的目的（升级 runbook 逐点核对）。回滚：删除该段即可。

## ADR 判定

四问均否：无否决备选（见上）、撤销代价低（删段即回滚）、不约束未来工作模式、不依赖上游非公开接口。不出 ADR。
