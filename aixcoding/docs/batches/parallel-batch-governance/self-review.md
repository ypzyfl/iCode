# 自评审记录：并行批次编号与文档热点治理（parallel-batch-governance）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填实际日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-10
- 确认意见：无特别意见
- 开发 AI：Kimi-K3.1-Pro
- 评审 AI：方案阶段为外部交叉评审 AI（两轮，标识见 plan 既有记录）；实施阶段为 GLM-5.3（CodeBuddy 环境，与开发 AI 不同源）

> 方案与 ADR 已完成两轮交叉评审、F1-F5 修复和零阻塞复审，并由责任人签认。
> 实施阶段 GLM-5.3 评审 F1-F5 已处置（见下表），增量复审确认 F1 blocker 清零、评审收敛；本记录已由周彬于 2026-11-10 签认。

## 开发侧复核（2026-11-10，非第二 AI 评审）

- 语义 ID：新旧定制点与 ADR 双格式、批次归属、active+retired 唯一性、旧区间兼容和语义孪生组均有错误注入测试。
- M0/M1/M2：11 项临时 Git 仓库测试覆盖确定性改号、占用后缀、范围外修改、歧义引用、语义差异和合法 M0；`check_id_only.py` 复用 `_common.git`，保持只读。
- closure：16 项测试覆盖草案、六件、ADR 引用、plan 精确状态、最小文件形态、stale/精确豁免、含点号批次键和微改动目录分流；真实诊断能拦截 ADR-0023 草案。
- 导航：6 项测试覆盖全目录、H1 回退、plan-only 存量目录、非 batches 排除、确定性和零写入；真实文档树报告 39 个批次目录。
- 根文档与规范：INDEX/ROADMAP 已物理删除；README、DEVELOPMENT、DIRECTORY、UPGRADE-RUNBOOK、SELF/PEER 和 design/ADR 模板已同步；按 user-manual 批次补齐 `manual/` 目录、force-include 数据例外与升级对账规则；历史 ADR 与历史批次事实记录未批量改写。
- guard：ADR-0023 迁移与引用清零，补做验证 101 项自检、26 项 pytest、64 条部署回放通过；ADR 与 self-review 均由责任人本人签认，GLM 报告已被责任人接受为迁移补件范围的第二 AI 评审，F1/F3 正文与计划矛盾已修复。
- 验证：统一 `verify.py --smart` 已按责任人最新要求实际执行，定制 605 passed / 51 skipped、上游 tests 35854 passed / 737 skipped、architecture 1247 passed / 3 skipped / 1 deselected；closure、ruff/format、strict、import 边界、R2/R3 与 guard 验证全部通过。

## 第二 AI 实施评审（GLM-5.3，2026-11-10）

评审范围：全部工作区 diff、R2/R11、closure、API 存在性、fail-closed、vacuous test、数据边界、验证数字和引用清理。评审确认代码与测试质量无 blocker，strict、docs_report 和测试数字均独立复现。

| finding | 级别 | 处置 |
|---|---|---|
| F1：guard self-review 已确认与正文/计划中的待评审表述矛盾 | blocker | **已按责任人裁决修复**：确认为本人签认，接受 GLM 报告作为 guard 迁移与补件范围的第二 AI 评审；已补记评审、清除正文矛盾并同步两份 plan |
| F2：test-plan 将所有 `legacy-` 前缀都写成非法 | suggestion | **已修复**：仅接受 M1 保留字 `legacy-c###`（可带 `-m1-N`），其他形态报错 |
| F3：guard 已签 design 的 2 处引用迁移与 R10 字面重签要求冲突 | suggestion | **已按责任人裁决闭环**：接受本批已签 design 与 ADR-0024 决策五的明确书面迁移授权，不修改 guard design 签认头 |
| F4：最小形态测试断言实际先触发签认字段错误 | nit | 不修；测试覆盖的拒绝行为正确，仅测试名可进一步精确 |
| F5：ADR-0023 注释沿用真实 ADR-0009 示例 | nit | 不修；遵守 ADR 迁移时决策正文与既有注释不动原则 |

非本批引入的 UPGRADE-RUNBOOK mojibake 顺带项不在本批扩张处理。

## GLM-5.3 增量复审（2026-11-10）

- F1：签认头、正文和两份 plan 四方一致，blocker 清零。
- F2：test-plan 与 `LEGACY_M1_POINT_RE` 及合法 M1 测试一致。
- F3：事前双签认授权 → 最小机械替换 → 裁决落盘的链条完整，无新义务；其他批次不得默认泛化此先例，仍须 design/ADR 明示授权。
- 新增 blocker：无。closure 独立复跑仍只剩本批 self-review 草案 1 项，ruff format 与测试数字复核属实。
- S1：引导语 stale，已按建议修正。
- **复审结论：评审收敛。**周彬已于 2026-11-10 签认本记录；最终 closure 已 OK，剩余事项仅为提交、PR 和双 CI。
