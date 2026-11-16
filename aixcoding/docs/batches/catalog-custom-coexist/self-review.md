# 自评审记录：后端同步模型与自定义模型共存

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），
AI 不得代填。签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-16
- 确认意见：知情确认
- 开发 AI：CodeBuddy / Tencent Hunyuan Hy
- 评审 AI：GLM-5.3-Flash

## 2026-11-16 评审结论：通过

- 轮次：1 轮（独立第二 AI 全量评审 → 责任人逐条拍板 → 开发 AI 增量修复 →
  开发 AI 复审增量；findings 全部收敛，无新增）。
- 评审身份：评审 AI 为责任人指定的独立第二 AI（GLM-5.3-Flash），与主力
  开发 AI（CodeBuddy / Tencent Hunyuan Hy）不同源；评审报告声明仍可能共盲，
  终裁在责任人。
- 评审范围：R2/R3/R11 比对、治理门禁、幻觉 API（新引用符号逐一验签）、
  静默吞错、边界条件、两阶段失败语义、vacuous test 抽查（「改坏哪行会红」）、
  并发/资源、数据边界、测试实跑；对照 `requirements.md` 验收标准、
  `design.md` 方案与备选/R8、`test-plan.md` 覆盖矩阵。
- **blocker 处置：0 blocker**（评审结论原文）。三项 suggestion、三项 nit
  全部逐条拍板，无存留 blocker。
- suggestion / nit 处置：
  - **F1**（流程，签认先于评审结论）：**留档 + 责任人知情确认**。记录档允许
    签认后追加评审记录、不触发重签；本文件头部已由责任人 2026-11-16 签认，
    正文补写本节。**确认意见栏（`- 确认意见：`）需责任人本人填写**以自证
    知情（建议措辞：「已知悉签认先于评审结论，评审 0 blocker、findings 已收敛，
    确认通过」）；AI 不代填。`--closure` 在全绿状态下未因追加正文回退。
  - **F2**（边界，显式 id≠stem）：**已修（改代码）**。`_load_custom_profiles`
    返回 `(stem, profile)`，冲突/保留判定改用文件名 stem（`os.replace` 的覆盖
    对象）；新增 `test_conflict_and_preservation_use_filename_not_explicit_id`
    钉死评审列举的两种失真。详见 `verification.md` 增量节。
  - **F3**（覆盖缺口，快照零磁盘 IO）：**已修**。新增
    `test_install_snapshot_stays_in_memory`（写陷阱断言调用前后不触盘）。
  - **F4**（nit，用例计数/名称漂移）：**已修（文档）**。`verification.md`
    与 `test-plan.md` 按实施后实际用例名更正（9 函数/12 收集、合并与改名、失败
    语义由既有 fault-injection 用例承担）。
  - **F5**（nit，except 括号）：**不修**。加括号后 `ruff format --check` 判需
    回退：项目 `requires-python>=3.14`、ruff target py314 formatter 偏好 PEP 758
    无括号形式，保留既有风格；合规已复核。
  - **F6**（nit，每文件双读）：**不修，留档**。目录规模小、开销可忽略，
    引入缓存反增失效一致性风险。
- 未修项（责任人拍板不修/留档）：F1 的确认意见待本人填写、F5、F6；其余无。
- 独立复跑证据（开发 AI，与 `verification.md` 一致）：目录+mock 定向
  103 passed / 2 skipped（2 skip 为既有失效 import，本批零触碰）；ruff
  check + format 全过；`check_docs` 与 `--closure` 均 OK；R2/R3
  `upstream_changed=0`。上节全量 Smart Test 基线（13812 passed / 17 skipped +
  architecture 323 passed）未被本轮增量推翻——增量只改冲突判据与测试，
  未新增依赖或上游接触。
- 终态：评审通过；本文件头部已由责任人签认，追加本节不触发重签；
  唯一待责任人本人动作是填写头部确认意见栏（F1）。`--closure` 实测 OK。
