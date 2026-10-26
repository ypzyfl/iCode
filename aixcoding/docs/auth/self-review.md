# 自评审记录：auth 迁入（src/chrys/aixcoding/auth + LLM token 接线）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-26
- 确认意见：无特别意见
- 开发 AI：CodeBuddy（BM:GLM-5.3）
- 评审 AI：Deepseek-V4-Pro（CodeBuddy 评审会话）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-10-26 评审结论：通过

- 轮次：1 轮（评审 + 修复 + 复审增量；复审"过，无 finding"，blocker 清零收敛）
- 评审范围：工作区全部未提交变更（11 modified + 3 untracked 目录）对照
  `aixcoding/docs/auth/design.md`（已签认）与旧分支 0.28 平移对照源逐行核验
- 首轮结论：**无 blocker**；标准检查 6 项 + 本批特有重点 A-H 全过；
  findings 5 条（F-1/F-4 suggestion、F-2/F-3/F-5 nit），责任人逐条拍板：

**已修复（4 项）**：

- F-2（nit）：design R2 表两处 marker 措辞 `AIxCoding login:` → `auth:` 同步实现
  （附 module 词修正缘由注记）——`design.md` "上游改动清单（R2）"表
- F-3（nit）：verification/plan 的 ty ignore 计数更正（"17 处=9+7" → "16 错由 14 行覆盖：
  crypto 7 行 9 错含 :158 一行两错 + types 7 行 7 错"）——与 grep 实测一致
- F-4（suggestion）：新增 `aixcoding/tests/auth/conftest.py`（29 行）——autouse fixture
  钳制 `session.detect_delegation → None` 隔离进程 env 兼容通道（`OPENAI_API_KEY` +
  `AIXCODING_USER_EHR` 成对残留时防误分支）；专测 auto-detect 用例以
  `@pytest.mark.allow_delegation_detect` 豁免，marker 经 conftest `pytest_configure` 注册
  （pyproject 上游不可动，R2 零外溢）。实施波折如实记录：首版无豁免误杀正当用例 → 加
  marker → 严格模式需注册 → 补 `import pytest`；修复后全量 263 passed 2 skipped 绿
- F-1 补句（不修代码）：`test-plan.md` 通道 2 定性——"外部依赖行为探针（守护 design
  对比二 hook 切换触发条件），不锚定本批实现；实现半边由通道 1 两例强锚定"

**未修项（次要问题，责任人拍板不修）**：

- `test_llm_token_wiring.py::test_overrides_default_headers_on_wire` | 通道 2 不锚定本批
  实现（改坏 stamp 注入行它不红） | design/test-plan 已钉死该手段且定性到位，实现半边
  通道 1 强锚定，端到端锚定成本 design 已权衡（评审认同）
- `wire_client.py::stamp()` import 失败分支无日志 | 为低概率路径引入新 logger 略重 |
  注释已声明降级语义（§9 合规），上游真改名由 tests/service/llm 2047 例 + CI 兜底暴露
  （评审认同）

**复审（增量）**：conftest 钳制/豁免/命名空间三处关键判断全部核验成立；F-2/F-3 文档同步
与实现/实测一致（代码 marker 2 处、ty ignore 14 处）；`test_update_server` 偶发失败判定
成立（conftest 作用域仅 auth 目录）。结论：**过，无 finding**。
