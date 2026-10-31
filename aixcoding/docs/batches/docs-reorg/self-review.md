# 自评审记录：docs 目录分层组织（docs-reorg）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-01
- 确认意见：无特别意见
- 开发 AI：BM:GLM-5.3 / CodeBuddy
- 评审 AI：Kimi-K3.1-Pro / CodeBuddy（①②轮）、Deepseek-V4-Pro / CodeBuddy（③轮，签认后追加登记）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-10-31 至 11-01 评审结论：通过

- 轮次：2 轮（① 2026-10-31 全量评审：2 blocker / 4 suggestion / 1 nit；② 2026-11-01 增量复审：一轮修复全过，新增 1 suggestion + 1 nit 并当日修复——该微修复 4 处通配前缀 + 2 行文档口径，量级极简，建议由责任人终裁免第三轮机器复审）
- blocker 处置：
  - F1 ADR-0016 未签认 → 责任人动作（本人编辑 ADR-0016 头部签认），非代码修复；
  - F2 README 两处范围外语义修订（过时注记删除、CUSTOMIZATIONS.md 行改 --report）→ 责任人拍板 ② 追认纳入（评审呈报即回炉闭环，记录于 verification.md 评审处置行）；
- suggestion / nit 处置（全部修复）：
  - F3 布局测试未锁"不递归" → +2 用例（嵌套诱饵 batches/group/demo 断言空返回 + 空目录/缺根断言）；复审实证：改回顶层 glob 或递归 glob 两个方向均真红；
  - F4 INDEX auth 路径错误（`src/chrys/aixcoding/auth`）→ 改 `src/chrys/kernel/aixcoding/auth`（tier 回迁后现状）；
  - F5 规范裸名 ×2 → 修复，并裸名形态全量补扫发现 **85 处/35 文件**（评审所见 2 处为冰山一角）统一机械替换；复扫 pattern 纳入裸名形态；
  - F6 verification 缺可复现命令 → 新增"关键验证复现命令"节（H1/H3/H4/H5 命令与输出摘要）；
  - F7 requirements 残留虚构维度半句 → 删除，保留"现行效力载体"真实约束；
  - F8（复审新增）裸名通配形式 ×4 → `batches/` 前缀（tier-migration design ×2 / verification ×2）；复审指出的防误伤项（test-plan:23 测试目录通配语境）确认未动、列入复扫白名单；
  - F9（复审新增）H4 摘要为修复前口径 → 更新为四形态（全前缀/短形式/裸名/通配）终口径与白名单全集；
- 未修项：无
- 收敛证据：四形态复扫 `RESCAN v4: 0 hit(s)`；`check_docs` OK（16 ADR/17 design/14 self-review）；`gen_customizations --strict` 25 行/29 marker/0 warning；R2 池前后快照 `fc` 逐字一致；`pytest aixcoding/tests` 320 passed/2 skipped（1 环境偶发单独复跑 PASSED 在案）；ruff check + format 全绿。

## 2026-11-01 第三轮评审追加记录（Deepseek-V4-Pro，签认后追加不触发重签）

- 全量独立评审：无 blocker；核心正确性（扫描面等价 17 design、R2 池 25 含 AGENTS.md、零上游改动、85 rename 机械性归一化验证、archaeology-report 豁免文件逐字一致）经其实测全部成立。
- F1' `batches/restructure/plan.md:10` 相对链接三层应为两层（`../../../standards/adr/` → `../../standards/adr/`，实施脚本"加深一层"误写三层，design §4.3-G④ 预扫记录同源笔误）→ **已修复**，勘误留档 verification.md；
- F2' `standards/DIRECTORY.md:7` 原文 `../../restructure/plan.md` 系存量断链（standards/ 一层即达 docs/），本批次机械沿用未察觉 → 随批修正为 `../batches/restructure/plan.md`（失效链接原地修正范畴）→ **已修复**；
- F3' 本文档签认时机提示 → 责任人已于 2026-11-01 签认（本记录即为签认后追加）；
- 修复后复验：`check_docs` OK、四形态复扫 0 命中（见 verification.md）。
