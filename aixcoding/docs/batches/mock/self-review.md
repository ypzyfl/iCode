# 自评审记录：mock 基建迁入

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
- 开发 AI：CodeBuddy · GLM-5.3
- 评审 AI：CodeBuddy · Deepseek-V4-Pro（独立会话，与开发 AI 不同源）

## 2026-10-26 评审结论：通过

- 轮次：1 轮评审 + 1 轮增量复审（评审 AI：Claude / CodeBuddy 独立会话，与开发 AI 不同源）
- 流程：① 全量评审（findings：B1 blocker + S1-S3 suggestion + N1-N3 nit）→ ② 负责人
  逐条拍板 → ③ 修复 + 同一评审 AI 增量复审（B1/S1/S2/S3/N1 全过，blocker 清零）→
  ④ 收敛成立 → ⑤ 本报告签认。
- blocker 处置：
  - B1 launcher stop 调不存在的 `running.server`（Ctrl+C 退出与端口占用回滚两条路径
    必抛 AttributeError）→ 已修复：stop 改 `running.close()` + `test_mock_launcher.py`
    全 starter 真实回环（stop 不抛 + 端口释放断言）锚定回归；验证：pytest
    **158 passed + 2 skipped**、ruff check / format / import 边界全绿
    （verification.md 评审修复轮节）；
  - 复审新增 F1（`urllib.error` 隐式依赖）→ 已修复：显式 import（复审 AI 建议直接补，
    成本一行），修后门禁重跑绿（158 passed + 2 skipped 维持）。
- suggestion 处置：S1 补内嵌 auth 契约测试（复审过：签名错位必抛 TypeError）；S2 两处
  state 类 docstring 声明无锁有意（负责人拍板：注释级对齐零行为改动）；S3 skipif
  reason/docstring 明示"unskip 时断言随消费方 design 重核"（复审过）。
- N1（真实工号）：负责人确认为真实 PII，亲自改为虚构值；开发 AI 同步 fixture 注释
  （复审过：虚构值 + no real PII 声明）。
- 未修项（次要问题，负责人拍板不修）：
  - N2 `_is_auth_route` 前缀过宽（`/device` 误匹配 `/devicexyz`）| loopback mock
    无误路由后果 | 不修；
  - N3 `aa` 残留字段被断言固化 | 有意选择——"未知顶层键透传"行为探针 | 保留（清理
    reference 数据时需同步断言）。

## 2026-10-26（二）peer review 轮（PR #56，同事 + 独立评审 AI，追加记录）

8 候选 + 2 专项 + 1 冲突点，负责人裁决（候选 1/2/4 + PR 号笔误修正实施；其余不修）：

- **候选 1（Windows fail-fast 失效）已修**：`HTTPServer.allow_reuse_address`（SO_REUSEADDR）
  在 Windows 允许第二实例重叠绑定活跃端口——恰是"残留 mock 进程"最常见占用场景，
  双实例并存、fail-fast 失效。修复：三 server 平台感知 `server_bind`（Windows 用
  `SO_EXCLUSIVEADDRUSE`，其他平台保持 SO_REUSEADDR 供 Linux TIME_WAIT 重启），配
  三份"双实例拒绝"回归测试。作者冒烟未暴露的原因：其占用者是裸 socket（无
  REUSEADDR），Windows 重叠绑定需双方均设——冲突点由此澄清，两结论针对不同占用者
  类型均成立；
- **候选 2（catalog keep-alive body 残留）已修**：HTTP/1.1 下 405/404 拒绝应答前
  `_drain_body()`（auth/update 默认 HTTP/1.0 close 无此问题）；配 keep-alive 连接
  拒绝后复用测试；
- **候选 4（`float(delay)` 未捕获）已修**：control 的 delay 前置校验（防 set_mode
  半应用状态），非数值转 400；配测试（400 + revision 不变断言）；
- 不修（负责人裁决）：候选 3（auth form body 无上限，loopback 无现实触发）、
  候选 6/7（竞态/计数非原子，S2 已声明取舍且赋值顺序核验正确）、专项 1（skipif
  仅测模块存在性——符号改名时测试快速红即信号）、专项 2（PEP 758 无括号 except
  为 py3.14 合法语法且仓内惯例在案）；
- PR 号笔误：早前草稿把 run 号 #8 误记为 PR 号，已在文档提交前更正为
  **PR #56**（随文档 commit 一并入库）。

### 修复清单（增量，供复审定位）

| finding | 修复 |
|---|---|
| B1 launcher stop 调不存在的 `running.server` | `__main__.py` stop 改 `running.close()`；新增 `test_mock_launcher.py`（selection 5 用例 + 全 starter start→stop 真实回环含端口释放断言——B1 回归锚定） |
| S1 内嵌 auth 形态零契约测试 | `test_model_catalog_server.py` 补 `test_embedded_auth_routes_share_the_catalog_origin`（auth 路由同 origin + 信封断言） |
| S2 并发防护不一致 | auth `MockAuthState` 与 catalog `CatalogMockState` docstring 声明"无锁是有意的"（注释级，零行为改动） |
| S3 skipif 措辞误导 | docstring 与 reason 改明示"unskip 时断言需随消费方特性 design 重核"，reason 收敛为 `_SKIP_REASON` 常量 |
| N1 真实工号 | 负责人亲自改虚构值（ehr/name/deptName）；开发 AI 同步 fixture 注释（不再声明 byte-for-byte，标注虚构无 PII） |
| 自查（评审期发现） | test-plan 声明的 launcher 单元测试原未写——`test_mock_launcher.py` 一并补齐（R8 文档一致） |

修复期技术波折（如实记录）：launcher 测试初名 `test_launcher.py` 与 diagnostics 同名撞
pytest 无包收集（已改名 `test_mock_launcher.py`）；探测 404 被 urllib 抛 `HTTPError`
（已捕获同为有效响应）。

### 未修项（负责人拍板不修）

- N2 `_is_auth_route` 前缀过宽（`/device` 误匹配 `/devicexyz`）| loopback mock 无误路由
  后果 | 不修；
- N3 `aa` 残留字段被断言固化 | 有意选择——"未知顶层键透传"行为探针，reference 数据中
  真实存在的未知键恰好可用 | 保留（清理 reference 数据时需同步该断言）。

### 评审范围说明（供评审 AI 定位）

- 变更全部在 `aixcoding/` 内（零上游文件改动、pyproject 零改动，R2/R11 应对名清空）：
  - 新增：`aixcoding/mock/`（三子包 + 包根 `__init__.py`/`__main__.py` launcher/README）、
    `aixcoding/tests/mock/`（4 文件）、`aixcoding/docs/batches/mock/`（六件套）、
    `aixcoding/docs/standards/adr/0009-*.md`；
  - 修改：`aixcoding/docs/ROADMAP.md`、`aixcoding/docs/batches/restructure/plan.md`、
    `aixcoding/docs/standards/DIRECTORY.md`（§5 命令修正、§6 两段登记）；
- 注意：新增目录为 untracked，不在 `git diff` 输出内——评审时以 `git status --short`
  定位后逐文件读取；
- 特性文档：`aixcoding/docs/batches/mock/design.md`（已签认）与 `test-plan.md`。

### 开发 AI 实施记录（供评审参考，非评审结论）

- 迁移采用一次性脚本（复制 + 最长优先替换 + grep 残留清零）而非逐字重写，替换完备性
  由 ruff / pytest / 边界工具三道门禁兜底；临时脚本已删除；
- 实施期发现并处置：旧分支 catalog 契约测试与实现本就不配套（5 个断言锚旧一代
  version/items 形态）→ 以实现为准重写；2 个 parse_catalog 对拍测试改 `skipif
  (find_spec(...))` 自动跳过（design 假设 1 降级预案，消费方迁入自动恢复）；
- launcher 冒烟三项过（占用 fail-fast / 默认组合起停探测 / 互斥码）；Ctrl+C 干净退出
  未强测（留日常联调自然验证，verification.md 已记）；
- 设计期三轮外部 AI 评审（两轮文档 + 一轮源码核验，经负责人转述）针对 design.md，
  blocker/major 均已闭环——属设计评审记录，不构成本节要求的实施 diff 评审。
