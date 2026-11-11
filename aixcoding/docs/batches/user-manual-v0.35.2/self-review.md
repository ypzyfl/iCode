# 自评审记录：0.35.2 手册内容同步（user-manual-v0.35.2）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：赵阔
- 状态：已确认
- 确认日期：2026-11-11
- 确认意见：无
- 开发 AI：CodeBuddy（Auto 模型，IDE 内代理）
- 评审 AI：Claude Code（GLM-5.3-flash 后端）——与开发 AI 不同工具、不同模型

## 2026-11-11 评审结论：通过（第 1 轮 blocker 已处置，待复审增量确认）

- 轮次：第 1 轮（评审 + 修复；复审增量待执行）
- 评审范围：未提交工作区变更（manual 树 + docs 树 + 六件套，git status 全量）
- 总体结论（评审原文摘要）：核心内容（官方 6 处同步、口径、版本、门禁）全部核实为真且可复现；
  越权范围/R11/官方一致性/口径/zh↔en 对应/build-info/版本口径/幻觉引用抽查/签认合规 全部"过"；
  2 条抽查由评审 AI 独立复现（捆绑 64=64 + MD5 零差异 + 关键词命中；audit 基准自动切换输出逐字吻合）。

- blocker 处置：
  - **F1｜blocker｜工作区 diff 超出批次登记范围 23 个文件（en 侧），违反 ADR-0012/R8**
    → **已修复（责任人拍板"扩围"）**：22 个 en 整文件 + 本批次 en 5 文件内混入的追平 hunk +
    zh getting-started 的 CHANNEL 处，全部如实登记进六件套——requirements 目标/验收、
    design「en 侧追平收尾」节与 R2 邻接说明、verification「en 侧追平清单」节（逐文件）、
    plan 待办与裁决记录；requirements/design 随责任人重签（本批次为事后补录模式）。
    证据：verification.md「en 侧追平清单」节；`git status` manual 树 zh 5 + en 27 全部有承载。
    说明：该批改动为 user-manual 批次 en 对齐的未提交延续 + ACP 清扫，方向与本批次
    "禁用词 0（含 ACP）"验收门一致，内容由 audit zh+en 双语章级比对背书；驳回拆批方案
    （en 追平是审计绿前提，窄口径提交则审计不绿）。
- suggestion 处置：
  - **F2｜suggestion｜verification.md 内部自相矛盾（清单漏记 CHANNEL 处）** → **已修复**：
    同步清单 zh getting-started 补注"官方 3 段 + 1 处 ICODE_CHANNEL→AIXCODING_CHANNEL"。
- nit 处置：
  - **F3｜nit｜品牌残留为链接文件名（en sessions.md:62、en python-extensions.md:99 的
    ../running/icode-run.md）** → **不修**（manual 树文件名系既有结构，改链破坏相对链接；
    彻底改名应另立批次评估——责任人 2026-11-11 拍板登记不修）。
  - **F4｜nit｜verification 版本行转述不精确** → **已修复**：如实抄录
    `版本 v0.35.2 ｜ 本手册撰写于2026年11月11日`。
  - **F5｜nit｜未跟踪文件 aixcoding-launch.py 位于仓库根（不满足 R4 落位）** →
    **不修**（本地 SAC 规避辅助，user-manual 批次已裁定永不提交 git；提交时显式排除，
    勿被顺带 git add——责任人 2026-11-11 拍板）。

- 未修项（次要问题，责任人拍板不修）：
  - en sessions.md:62 / en python-extensions.md:99 | 链接文件名含 icode-run | 既有结构，改链破坏相对链接，另立批次评估 |
  - 仓库根 aixcoding-launch.py（未跟踪）| 不满足 R4 落位 | 本地辅助永不提交，提交时显式排除 |

## 2026-11-11 第二轮复审结论：通过（收敛）

- 轮次：第 2 轮（复审增量，同一评审 AI：Claude Code / GLM-5.3-flash）
- 复审范围：六件套补录增量 + docs/ 镜像追平 8 文件（staged）
- 结论：**第一轮 5 条 findings 全部处置到位**（F1 扩围登记与 git status en 27 逐一对名吻合；
  F2/F4 修正如实；F3/F5 登记不修在案）；docs/ 追平经独立复核：归零断言实跑通过、
  `git diff --cached --stat` = 8 files 12+/12- 与官方改动量一致、镜像纯净（0 处定制字样）、
  R2/R13 授权登记链完整、SKILL 长期口径实改、门禁实跑全绿、manual 树未变。**无 blocker**。
- 新增 findings 处置（第 2 轮）：
  - **N1｜suggestion｜INDEX 登记行未随扩围更新** → **已修复**：登记行改为"官方 6 处落
    manual zh/en + en 侧追平收尾 + docs/ 镜像追平官方 0.35.2 + 桌面三件套重出"。
  - **N2｜nit｜plan.md 自相矛盾（SKILL §八.8 改写状态）** → **已修复**：挂起行改为
    "已改写，并新增 §十 评审后处置规则"。
  - **N3｜nit｜test-plan.md 未随扩围同步** → **已修复**：覆盖矩阵补 "docs/ 镜像追平归零"
    断言行；manual 同步行改为本批次官方改动 + zh CHANNEL + en 追平类 22 文件口径。
  - **N4｜nit｜self-review 引述笔误（且含品牌字样）** → **已修复**：改为"官方 3 段 + 1 处
    ICODE_CHANNEL→AIXCODING_CHANNEL"。
- 规则沉淀（SKILL §十.3，按"下批会重犯吗"判定）：N1+N3 → 新增"扩围/口径变更必须横扫
  六件套全部件 + INDEX 登记行"；N2 → 并入 F2 规则（矛盾检查扩到其他件）；N4 → 并入 F4
  规则（批次文档自身同样品牌零豁免）。
- 评审 AI 更正：第一轮报告"en 侧 28 文件"系笔误，实际 en = 27（33 = 32 manual + INDEX），
  六件套登记口径（en 27 = 本批 5 + 追平 22）正确。
- 责任人待办：签认 design.md（R2 批准的书面落盘，含 docs 8 文件）与本记录；提交通知后
  按显式路径提交（排除 `aixcoding-launch.py`；docs 8 文件当前为 staged 状态，系
  `git checkout v0.35.2 -- <paths>` 的副作用，内容为官方原文）。
