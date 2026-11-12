# 设计：检查域模型与定制域按需触发（compliance / aixcoding-tests / guard-deploy / upstream）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：无特别意见

## 方案概述

放弃数字层号，把门禁表述为**四检查域 + 两聚合 required check**；`aixcoding-tests.yml` 增加
前置 filter（复用 upstream-ci-tiering 全套已验证机制），按射程把 `test`/`guard` 两个 job
改为独立条件触发，`compliance`（govern）恒跑不变，`upstream` 域零改动：

```
PR to main_aixcoding_cli
        │
        ├─ AIxCoding Tests
        │    filter: diff --no-renames → ci_impact.py --domains → {aixcoding-tests, guard-deploy} 域集合
        │    govern（compliance，恒跑）
        │    test（aixcoding-tests 域命中才跑，双 OS）
        │    guard（guard-deploy 域命中才跑，三 OS）
        │    gate「AIxCoding quality gate」恒跑：govern=success ∧ 每域 (命中∧success ∨ 未命中∧skipped)
        │
        └─ AIxCoding Upstream CI（零改动，upstream 域按影响面）

push 至主干 / nightly（schedule，每日 UTC 18:00 与桥接同点）/ dispatch：定制双域恒全跑
```

**纯文档 PR 效果**（除"文档即验证输入"例外——共 9 文件，R7 + R11，评审 F1/N1/M1）：仅
compliance + 两 gate，总等待约 3 分钟 → 约 1 分钟；未知路径全域 fail-closed（upstream 全量
本就是关键路径，并行加跑约 3 分钟不增总等待）。

## 备选方案对比（模型结构，三轮外部讨论定案）

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| A. 四层数字重编号（L0-L3） | 每层单一触发域 | 编号绑死触发策略与职责域；刚签认的 ADR 编号立刻过时，全库改口径；未来加域继续重编号 | 否决 |
| B. 三层 + L1 层内射程 | 零 churn | L1 层概念空化（“两个按需 job 的袋子”）；未来细分嵌套加深 | 否决 |
| C. 四检查域 + 两聚合门（本方案） | 无编号 churn；域名=被运行的检查套件，自释可搜索；与既有 gate/check 名对齐；加域即加行 | 失去数字速记（“恒跑门/测试门/guard 门/上游门”替代） | 选定 |

术语规则：**“检查域”回答做什么/何时触发，“聚合门”回答分支保护等哪个结果**，两者不混用；
域名描述被运行的检查套件，不描述只有哪个目录的改动才触发它。

## 关键决策

### 决策 1：分类器扩展——规则表输出域集合（非互斥），规则表即唯一登记处

`ci_impact.py` 新增 `--domains <changed.txt>` 模式（原 upstream 单域接口与 38 例测试零变）：
规则**顺序无关、域集合累积**（一条路径可命中多域），输出恰好两行布尔
`test_touched=true|false` / `guard_touched=true|false`（exit 0；错误 exit 2）。规则表（design
落盘后文档不再复制，以分类器为单源）：

| # | 路径模式 | 域集合 | 依据 |
|---|---|---|---|
| R1 | `ci_impact.py`、`_common.py`、`aixcoding-tests.yml`、`aixcoding-upstream-ci.yml` | 双域全跑 | 判定基础设施变更从严（FORCE 防自裁；非对 workflow 功能的验证） |
| R2 | `^aixcoding/tests/` | {aixcoding-tests}；`^aixcoding/tests/guard/` 追加 {guard-deploy} | 测试资产；guard 测试双命中 |
| R3 | `^src/chrys/kernel/aixcoding/guard/` | {guard-deploy}（∪ R4 定制产品规则 → 实际双域，并集语义） | guard 安装器/规则包 |
| R4 | `^src/chrys/[^/]+/aixcoding/` | {aixcoding-tests} | 定制产品代码（被测对象） |
| R5 | `^aixcoding/mock/` | {aixcoding-tests} | mock 契约测试射程 |
| R6 | `^aixcoding/tools/` 可执行代码（`.py` 等，纯文档/人工资产除外） | {aixcoding-tests}；`guard_install_merge.py` 追加 {guard-deploy} | 一般规则而非逐文件 FORCE；安装合并工具被自检直接导入（核实） |
| R7 | `aixcoding/docs/batches/guard-hooks/rule-pack/MANUAL_TESTS.md` | {guard-deploy, aixcoding-tests} | 双消费已核实（评审 M1）：guard job 回放语料 + `test_packaging.py:31,49-51` 存在性断言（aixcoding-tests 域） |
| R8 | `pyproject.toml`、`uv.lock`、`.python-version` | 双域 | 两个 job 的共同运行环境（guard job 也 uv sync，核实） |
| R9 | `^src/chrys/` 其余（上游产品源码） | 双域 | 定制层 import 上游符号 + guard 依赖 `foundation.platform`（核实）；不维护上游依赖细表 |
| R10 | 已知上游非源码精确豁免（仅有代码级依据的三项）：`^tests/`、`^docs/`、`^locales/` | 空集 | conftest 不复用 `tests/support`（核实）；`^scripts/`、`hatch_build.py`、其余上游 workflow **不豁免**——`aixcoding/tests/branding/test_command_contract.py` 静态断言 scripts 全家与 `cd.yml`（核实，评审 F1），落 R12 默认双域 |
| R11 | 纯文档：`*.md`、`^aixcoding/docs/`、`^aixcoding/manual/` | 空集；**例外（文档即验证输入范畴，本行 8 个精确文件，加 R7 的 MANUAL_TESTS.md 共 9）**：根 `AGENTS.md`、`aixcoding/docs/standards/UPGRADE-RUNBOOK.md`（`test_command_contract.py` 内容断言）；`aixcoding/release/INSTALL.md`、`aixcoding/docs/install-uninstall-support.md`、`aixcoding/docs/batches/internal-installer/publishing.md`（`test_install_internal_mirror_scripts.py:22-24` 内容断言）；`batches/guard-hooks/rule-pack/` 的 `README.md`/`OPERATIONS.md`/`PORTING.md`（`test_packaging.py:28-30` 存在性断言）——均 → {aixcoding-tests}（评审 F1/N1 两轮核实） | 纯文档射程只有 compliance，被消费文档除外 |
| R12 | **默认（未匹配任何规则）** | 双域（fail-closed） | 新目录/新资产类型防漏判；并行于 upstream 全量不增总等待 |

R10 与 R12 并存即"已知路径精确豁免 + 未知 fail-closed"：豁免必须显式登记且有代码级依据，
新豁免走 design 修订。

**累积语义（评审 F2，钉死）**：域集合 = 所有命中规则域集合的**并集**；空集规则只是"不贡献
域"，**永不移除**其他规则已给出的域（`MANUAL_TESTS.md` 命中 R7+R11 → {guard-deploy}；
`aixcoding/mock/*/README.md` 命中 R5+R11 → {aixcoding-tests}——后者恰是品牌测试消费对象）。
配 R7×R11、R5×R11 两个并集测试案例。

**登记教训（评审 F1/N1）**：射程例外靠人工枚举已连续两轮出现遗漏（`_read(...)` 字面量形态、
`REPO_ROOT / "..."` 拼接形态各漏一批）——**AST 级全形态扫描（F6）是必须项而非可选增强**，
且扫描口径须同时覆盖 Call 实参与 `/` 拼接链两种消费形态。

**R6 口径（评审 F3）**："可执行代码"= 代码后缀（`.py`/`.sh`/`.ps1` 等），其余类型落 R12。

### 决策 2：filter job（复用 upstream-ci-tiering 模式）

- `checkout fetch-depth: 0` → probe（python3 存在且 ≥3.14 版本门限，不可用则仓库 pin 的
  `setup-python` 兜底——run #125 教训内置）→ 分类器 `--domains`。
- 事件分支：非 `pull_request`（push/schedule/dispatch）→ 双域恒 touched=true，不做 diff。
- diff 带 `--no-renames`；空 diff/分类器异常/输出非法 → filter 失败（fail-closed，gate 不放行）。
- 输出 `test_touched` / `guard_touched` 两个布尔。
- concurrency group 改 `aixcoding-tests-${{ github.ref }}-${{ github.event_name }}`（评审 F4）：
  push 与 nightly 同 ref，原 group + cancel-in-progress 会互相取消、削弱"nightly = push 失败/
  取消后的独立复测"定位；加事件名后缀后 PR/push/schedule/dispatch 各自分组。桥接 workflow 经
  核查无此问题（PR 用 pull ref、schedule 用 branch ref，天然不同组），不随本批改动。

### 决策 3：job 条件与 gate 状态机

- `test`：`if: needs.filter.outputs.test_touched == 'true'`；`guard`：同理 guard_touched。
- gate「AIxCoding quality gate」恒跑保名：`govern=success`（恒跑域必成功）∧ 每域满足
  `(touched ∧ success) ∨ (¬touched ∧ skipped)`；filter 失败/输出缺失/cancelled 均红。
  实现要点（评审 F5）：gate 的 `needs` 增加 `filter`，先校验 `filter.result == success` 与
  双 touched 输出合法（true/false 精确匹配，缺失即红），再逐域校验。
- gate 输出列出各域 `success/skipped` 与跳过原因（聚合门全绿可知实际跑了什么）。
- required check 名与分支保护零改动。

### 决策 4：nightly/dispatch 与兜底层次

- `aixcoding-tests.yml` 新增 `schedule`（cron `0 18 * * *`，与桥接同点）+ `workflow_dispatch`：
  非 PR 事件直全跑（决策 2），nightly 覆盖三个按需域。
- 兜底层次（ADR 固化）：定制双域 = push 全跑（每次合并即全量）+ nightly（空窗补充、环境
  漂移、时间相关退化、push run 失败/取消后的独立复测）；upstream = nightly/dispatch 唯一
  防线。**nightly 与 push 均为合并后兜底，不替代 PR 保守触发。**

### 决策 5：新 ADR 与文档联动

- 新 ADR `ci-gate-domains--check-domains-model.md`：检查域模型决策 + 四行映射表
  （L0→compliance / L1-test→aixcoding-tests / L1-guard→guard-deploy / L2→upstream）+
  “两个 required check 名称及实现机制不变”；旧 ADR 正文不回改，按 ADR-0004 先例追加
  append-only 演进注记（头部导航行扩充指向新 ADR + 末尾四行映射注记）。
- DIRECTORY §7 改用检查域口径；本批六件；upstream-ci-tiering 批次文档不回改（快照）。

## 对上游隐式行为的假设

1. 默认分支 = `main_aixcoding_cli`（已核实）：schedule/dispatch 在主干 tip 生效；若变更，
   nightly 静默失效（upstream 域 ADR 已有回炉条款，本 ADR 继承至定制域）。
2. `tests/support` 与 `aixcoding/tests` 隔离（conftest 无引用，核实）：R10 豁免上游测试的
   依据；上游若引入定制测试可感知的共享基建，该豁免须回炉。
3. `aixcoding/tests` 的静态契约测试消费仓库文件，形态不止一种（`_read(...)` 字面量：
   scripts 全家/`cd.yml`/`AGENTS.md`/mock 全树/`UPGRADE-RUNBOOK.md`；`REPO_ROOT / "..."`
   拼接：release/INSTALL.md、install-uninstall-support.md、publishing.md、rule-pack
   README/OPERATIONS/PORTING——两轮核实，评审 F1/N1）：R10/R11 例外与 R5/R7 的依据；
   **新增静态契约测试消费新的仓库文件时，须同步登记分类器射程**（ADR 维护义务），并以
   F6 的 AST 双形态扫描测试机制化防漏。
4. guard 三 OS 部署验证消费真实平台配置目录——R3/R6/R7/R8/R9 共同构成其射程闭包；新 guard
   资产落位须同步登记（ADR 维护义务）。

## 定制点登记预告

不适用：零上游接触（改动全部为定制资产；`gen_customizations.py --strict` 照常零 error/warning）。

## 改动文件清单（全部定制资产，零上游文件）

| 文件 | 改什么 | 预估行数 |
|---|---|---|
| `aixcoding/tools/ci_impact.py` | 新增 `--domains` 模式与规则表（R1-R12，域集合输出） | 约 +80 |
| `aixcoding/tests/tools/test_ci_impact.py` | 规则表全案例矩阵 + 多域命中（含 R7×R11、R5×R11 并集案例）+ 未知 fail-closed + 既有 38 例零回归 + **F6 扫描测试（必须项）**：AST 遍历 `aixcoding/tests` 源码，同时提取 `_read("...")` Call 实参与 `REPO_ROOT / "a" / "b"` 拼接链的字符串常量，重组仓库相对路径，断言每个都被分类器判为 aixcoding-tests 命中——新增静态契约测试消费仓库文件时自动防漏登记 | 约 +170 |
| `.github/workflows/aixcoding-tests.yml` | filter job（probe/setup-python/分类器/事件分支）+ test/guard 条件 + gate 状态机扩展 + schedule/dispatch 触发 | ±55 |
| `aixcoding/docs/standards/adr/ci-gate-domains--check-domains-model.md` | 新 ADR（模型 + 四行映射表 + 兜底层次 + 维护义务） | 约 70（新增） |
| `aixcoding/docs/standards/DIRECTORY.md` | §7 检查域口径；§1 workflow 行补 schedule/dispatch | 约 10 |
| 本批次目录六件 | requirements/design/plan/test-plan/verification/self-review | 约 300（新增） |

R1/R2 自查：零上游文件，无 R2 报批项；workflow 在 CUSTOM_EXACT_PATHS 登记内；新增代码全落
`aixcoding/` 开发资产区；无新增第三方依赖（R11 不适用）。

## 风险与最坏情况

- **射程漏判**（新 guard 资产/新工具未登记）：R6/R12 一般规则 + 默认 fail-closed 兜住大面；
  残余由 push 全跑（每次合并）与 nightly 双层兜底；回滚 = filter 改恒 touched=true 或 revert。
- **域集合规则复杂度**：顺序无关累积设计 + 全案例矩阵测试；规则表单源于分类器，文档不复制。
- **nightly 新增成本**：定制双域每晚约 3 分钟（桥接 11 分钟已有），可忽略。
- **gate 组合数**：3 域 × 命中/未命中 = 逐域独立校验，无组合爆炸。

## ADR 判定

需要新 ADR（**ADR-ci-gate-domains--check-domains-model：检查域模型取代数字分层术语**）：
本批永久改变门禁体系的模型表述（数字层号废弃）、定制双域从恒改变按需、兜底层次扩展至全域，
并新增射程登记维护义务——超出批次执行层选型，且显式修订 ADR-upstream-ci-tiering--
pr-gate-tiering 的分层术语部分（分类器/gate 状态机等既有决策继续有效）。
