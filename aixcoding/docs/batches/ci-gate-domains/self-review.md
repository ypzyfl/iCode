# 自评审记录：检查域模型与定制域按需触发

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期、确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：无特别意见
- 开发 AI：**分阶段**——需求/设计阶段 CodeBuddy（Kimi-K3.1-Pro）；实施阶段 CodeBuddy
  （BM:GLM-5.3）（责任人 2026-11-12 确认中途切换；初稿曾误沿上文将实施开发 AI 记为 Kimi，
  致评审方误判同模型，已更正）
- 评审 AI：**分阶段**——需求/设计三轮（F1-F6/N1-N4/M1-M2）CodeBuddy（BM:GLM-5.3），经
  责任人转述；实施评审 CodeBuddy（Kimi-K3.1-Pro，评审 GLM 实施的 diff——不同源合规），
  含一轮增量复审

## 2026-11-12 方案与文档评审：收敛（三轮，design 签认前）

- 第一轮（requirements 初稿 + 映射矩阵）：F1（阻塞）豁免清单与静态契约测试消费面冲突
  （scripts/cd.yml/AGENTS.md/UPGRADE-RUNBOOK 被消费）；F2 空集与累积语义未定义；F3 R6 口径
  模糊；F4 concurrency 互取消；F5 gate 实现要点；F6 防再犯机制化。**全部采纳**（F1 经本地
  核实 `test_command_contract.py` 断言面比评审表更宽）。
- 第二轮（修订稿）：N1（阻塞）R11 例外再漏 6 文档（`REPO_ROOT /` 拼接形态：release/INSTALL、
  install-uninstall-support、publishing、rule-pack README/OPERATIONS/PORTING）+ F6 扫描口径
  必须覆盖双形态；N2 编号；N3 旧口径残留；N4 措辞。**全部采纳**（N1 本地核实属实）。
- 第三轮（终审）：M1（阻塞）MANUAL_TESTS.md 双消费（guard 语料 + `test_packaging` 存在性
  断言）与 R7 单域、F6 断言自相矛盾——R7 改双域；M2 计数口径（R11 行 8 + R7 合计 9）。
  **全部采纳**，结论"仅剩 M1 一处修正，修复后即可签认"。
- 登记教训（入 design）：人工枚举连续两轮漏判（两种消费形态各漏一批），AST 全形态扫描是
  必须项而非可选增强。
- 未修项：无。

## 2026-11-12 实施评审：通过（不同源合规，blocker 清零）

- 评审 AI：CodeBuddy（Kimi-K3.1-Pro），评审实施开发 AI（CodeBuddy BM:GLM-5.3）的 diff——
  不同工具/模型满足 SELF-REVIEW-HOWTO 要求（该轮曾因本文件初稿误标实施开发 AI 为 Kimi 而
  自判"同模型"，责任人澄清分阶段事实后重新定性；技术工作不受标识误标影响）。
- 结论：**0 技术 blocker**；2 个文档 suggestions（S1 CLI 输出契约示例过时、S2 R3 单域表述
  与并集语义不一致）**均已修复**，并由同评审 AI 增量复审确认闭环（S1/S2/记录修正三确认，
  无新增技术 finding）。
- 该轮覆盖：R2/R11/幻觉 API/静默吞错/边界条件/过度工程/并发异步全过；非 vacuous 抽查 2 例
  （删 `aixcoding/tests/` 规则与删 UPGRADE-RUNBOOK 登记均致测试红）；F6 提取集合 20 路径
  独立复跑一致；独立复跑 88 passed；补充探索（参数化 `_read`、目录 glob、`inspect.getsource`、
  guard 目录遍历等消费形态）确认无新射程漏判。
- 本地验证证据：见 verification.md 2026-11-12 节（88+734 测试、F6 集合人工核对、
  YAML/pins/ruff/strict/check_docs 全绿；实施过程三处测试侧自纠已记录）。
- 剩余流程事项（非评审项）：design 正文三处修订后的责任人重签；self-review 与新 ADR 签认；
  closure 复跑转绿。
