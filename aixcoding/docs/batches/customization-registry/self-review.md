# 自评审记录：定制点登记机制改造（customization-registry）

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：无特别意见
- 开发 AI：CodeBuddy（GLM-5.3）
- 评审 AI：Deepseek-V4-Pro（实施评审，2026-10-31）；design 阶段另历四轮外部 AI 评审（收敛记录见本目录 design.md「评审收敛记录」节）

> 记录档：签一次，后续追加不触发重签。

## 2026-10-31 实施自审

### 实施后双 AI 评审（提交流程硬前置）

- 评审指令：SELF-REVIEW-HOWTO §二官方模板（对话内生成，参数 base=main_aixcoding_cli）；
- 评审对象：本批次全部实施 diff（工具改造 / 8 表落盘 / 规范联动 / 测试重写）；
- 教训留档（2026-10-31 责任人拦停）：开发 AI 曾以"design 评审密度已四轮"为由建议豁免
  实施评审并推进提交呈报——design 评审≠实施评审，豁免判定权在责任人，AI 不得夹带
  自我豁免建议推进流程（ADR-0012 精神）。

## 2026-10-31 评审结论：通过

- 评审 AI：Deepseek-V4-Pro（独立评审通道）；
- 轮次：1 轮（评审 + 处置 + 增量复审）；评审结论**无 blocker**，2 suggestion + 3 nit；
- blocker 处置：无 blocker。R2 比对（AGENTS.md 在历史已签认 R2 池，机器门禁不红）、
  幻觉 API、vacuous test（抽 2 用例均为真行为断言）、R11（唯一新 import 为标准库 re）、
  过度工程/数据边界/边界条件/异常资源/并发（N/A）全过；
- findings 处置（责任人 2026-10-31 拍板"按建议处理"，5 条全修）：
  - F1（suggestion，R2 声明口径）→ 已修：design R2 节改"零新增上游文件改动 +
    AGENTS.md 属既有已获批文件仅段内追加"（design 正文小改，随本报告重签）；
  - F2（suggestion，report 静默丢弃对账 error）→ 已修：errors 非空时视图顶部加
    可见提示行 + 测试用例 `test_report_flags_reconciliation_errors`；
  - F3（nit，EXEMPT_SECTION 死代码）→ 已删（本批次改造制造的孤儿）；
  - F4（nit，_reconcile 返回类型过宽）→ 已收紧为具体五元组类型；
  - F5（nit，test-plan 锚歧义表述与最长锚优先实现矛盾）→ 已对齐文字；
  - 修复引入的两处自伤（test 注释全角标点、ISC004 未括号拼接）随手修复；
- 修复后复验：ruff 双检全过 / 工具测试 73 passed / strict 对账 OK（25 行 29 marker
  0 警告）/ check_docs OK（15 ADR、14 self-review）；
- 增量复审（同评审 AI，只复审增量）：**收敛**——5 条修复全部按建议原文正确落地
  （F1 口径精确/F2 提示链路完整/F3 全仓库零残留/F4 类型逐一对应/F5 语义一致）；
  F2 测试经改坏三行（error_count 传参、条件分支、提示文本）逐一定性为真行为锚定；
  ⚠ 字符编码依赖/签名默认参/return 0 语义边界均核验不构成 finding；无新增 blocker/
  suggestion/nit。复审报告留档于批次 PR 描述（对话记录 2026-10-31）。

## 2026-10-31 二轮评审（Kimi-K3.1-Pro，第三源独立评审）处置

- 评审结论：**1 blocker + 3 suggestion + 1 nit**；责任人拍板全修（处置详情见
  verification.md「二轮评审处置与复验」节）：
  - F1（blocker）退役表被活动登记解析吸收、strict 必红——开发 AI 先行独立复现确认
    （strict exit=1），修复=节限定解析（`_registration_section` + `_active_part`），
    复现场景终验 strict 1→0；教训：**退役机制测试初版只跑默认模式，未覆盖 CI strict
    契约**（评审者以"承诺的运行环境"视角补位，值得内化为习惯：每个模式分支都要有用例）；
  - F2/F3/F4/F5 全修（畸形退役可查、规范字段契约对齐、测试承诺落实、口径漂移订正）；
- 修复后复验：工具测试 79 passed（+6 评审回归用例）；strict 对账 OK；ruff 双检过；
  check_docs OK；
- 增量复审（Kimi-K3.1-Pro，只复审增量）：F1 blocker 实质消除、F2/F3 落实确认；
  剩 3 findings（F2-T 诱饵测试空断言——改坏解析器仍绿；F4-T main 层 exit 1 未覆盖；
  F5-D verification 80/79 冲突+双标题残留）——**三 条均即修**（`0 retired id(s)`
  真锚定断言、orphan 夹具断言 `main(["--strict"]) == 1`、文档订正），复验 79 passed +
  strict OK；复审自评"小范围增量修正，无需全量复审"；
- 评审链总计：design 阶段四轮方案评审 + 实施评审两源三轮（Deepseek-V4-Pro 1 轮+复审、
  Kimi-K3.1-Pro 1 轮+增量复审+微调）——blocker 1（已修终验 strict 1→0）、suggestion 5、
  nit 4，全部处置留痕于本文件与 verification.md。

### 实施期发现与处置（自审清单）

1. **解析器围栏缺陷（实战发现，已修）**：customization-registry design 的契约示例
   （```markdown 围栏内 `## 定制点登记预告` / `### 退役记录` + 示例表）被解析器当真节，
   首次真仓 strict 对账报 12 error（duplicate/malformed id、退役表头混入）——根因为
   `parse_table_section` / `_parse_retired_rows` 无代码围栏感知，任何 design 引用示例格式
   均会踩中（非本批次文档写法问题）。修复：双解析器跳过 ``` 围栏（fail-closed）+ 注入
   用例 `test_fenced_example_tables_not_parsed`。属"评审指不出的实战盲区"，价值佐证
   错误注入门禁思路。
2. **孪生组 id 可寻址性补充（呈报定稿前设计补强）**：孪生组单行若只持组首 id，组内成员
   id（C010–C012 等）失去登记承载——补 `expand_ids` 区间展开（`C009–C012`，连字符与
   en dash 均收）+ "区间 id 数==预期计数"一致性校验 + 3 用例；成员 id 全部保沟通价值。
3. **测试断言笔误 ×2（即改）**：report 表设计本无 anchor 列而断言含 anchor 语义（删）；
   区间化后孪生断言未随 demo 常量更新（改）。
4. **ruff 字符纪律**：新增中文行内注释引入全角标点（RUF003 ×31）与 PERF401 ×3——批量
   转半角 / extend 改写；tools/tests 域注释保持英文惯例的既有约束未破。

### 验证证据

见本目录 verification.md（strict 对账 25 行/29 marker/0 警告；工具测试 72；定制全套 313；
check_docs 15 ADR；ruff 双检；Smart Test PASSED 198+2skip）。全部本地全绿，CI 证据归 PR checks。

### 连带核销（temp 待办四处 + ROADMAP 一处）

auth-stamp-registration-cleanup / stable-customization-id / removal-condition-backfill /
2026-10-31-customization-registry-discussion.md（讨论材料，已用毕）/ ROADMAP 补做义务①。
