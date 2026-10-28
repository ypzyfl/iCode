# 自评审记录：ADR-0011 存量定制包按 tier 回迁 kernel 档

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-28
- 确认意见：无特别意见
- 开发 AI：CodeBuddy (BM:GLM-5.3)
- 评审 AI：Deepseek-V4-Pro（CodeBuddy 环境）

## 2026-10-28 评审结论：通过

- 轮次：1 轮（评审 5 findings + 处置 + 增量复审通过），复审附 2 个非 blocker 尾项已按建议修复
- blocker 处置：
  - F1（R2 清单遗漏 `trajectory_wait_manifest.json` +33）→ 已修复：design R2 表补录 2 行
    （manifest +33；另实跑 `check_r2_diff` 发现并补录 `src/chrys/aixcoding/__init__.py`
    删除 −8——分类器通配化后旧路径 diff 形态按上游判，静态评审遗漏、实跑门禁暴露）；
    联动清单回写第 8 条。验证：`check_r2_diff --base main_aixcoding_cli` OK
    （approved_pool=8），见 verification.md。
  - F2（4 文档重签真实性，裁决项）→ 责任人签认本记录即确认为本人操作
    （auth/diagnostics/devtools/tier-migration 四 design 确认日期 2026-10-28）。
- 复审尾项处置（非 blocker，按评审建议修复）：
  - S1（wire_client 标记行末残留 "The"）→ 已修：标记独立成行放注释块末尾；
  - S2（AGENTS.md:8 行内标记拆断 "is governed"）→ 已修：标记移至句末。
  - 修复后复验：gen_customizations（7 条目）、check_r2_diff OK、check_r3_markers OK
    （exempt=1）、工具自检 53 passed，见 verification.md。
- 未修项（次要问题，责任人拍板不修）：
  - aixcoding/docs/auth/design.md 登记 `wire_client.py::RequestHeaders.stamp()` 行无匹配
    标记的既有 warning（回迁前已存在，auth 标记无路径括号所致）| 留待 auth 批次后续维护
    或标记格式演进时统一处理 | 本批次不扩面。
