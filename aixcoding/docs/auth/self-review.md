# 自评审记录：auth 迁入（src/chrys/aixcoding/auth + LLM token 接线）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-27
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

## 2026-10-27 追加：缩小重构（记录档追加，不触发重签）

- 负责人拍板在 PR #60 内执行"①③ 缩小"（clients.py 退出 R2、token 解析归位 auth 包
  `login_token_header_value()`、wire_client 直接 import auth 包）——design R2 表已重写并
  重签（见 design 缩小重构记录）；本重构的增量 diff 待评审 AI 复审（HOWTO ③ 只复审增量），
  复审结论记入下方。

### 2026-10-27 缩小重构评审轮：通过（2 轮收敛）

- **第 1 轮**（增量评审）：无 blocker，3 findings——F-1（suggestion：
  `test_stamp_survives_import_failure` vacuous，b0375df 既有缺陷，本轮 patch 目标变更后
  依旧：未挂 logged_in_session，import 成功/失败两路径断言均绿）、F-2（nit：0.28
  "engine 构建先于登录"时序论证在 docstring/注释中丢失，申报"已迁入"不实）、F-3（nit：
  design R2 表 +14/−1 vs 实测 +16/−1）。
- 责任人拍板：三条全修。修复：F-1 用例挂 `logged_in_session` + patch 前 sanity arm
  （`assert _stamp()["token"] == TOKEN`——删 except 与 patch 失效两条破坏路径均红）；
  F-2 docstring 逐字补入 0.28 原句（与 wire_client 注释 "Resolved per request" 因果闭环）；
  F-3 R2 表改 +16/−1（numstat 实测 16/1 精确一致）。
- **第 2 轮**（修复增量复审）：**过，无 finding**——两破坏路径验证红、`_login_token`
  全仓零残留、clients.py 对 base 归零、文档/代码/测试三方一致。
