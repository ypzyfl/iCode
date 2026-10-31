# 设计：定制点登记机制改造（customization-registry）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：无特别意见

## 方案概述（C+ 终局形态：点级登记 + ID 降级保留 + 产物退役 + 对账命令化）

三层机制一次重构（四合一：登记源单一化 / 稳定 ID / 膨胀治理 / removal_condition 回填）：

```
登记层（design.md「定制点登记预告」表）        工具层（gen_customizations.py 改造）         产物层
批次/落点级 11 行 → 点级/孪生组级 29 行；  →   落盘生成退役；check（对账门禁，    →   CUSTOMIZATIONS.md
id 降级为沟通标识（主键=落点+marker锚）；        CI strict）+ report（stdout 全景视图）     文件退役删除
tombstone 退役记录保高水位                       同一内存模型，零文件写入
```

问题 → 解法对应：

| 问题 | 解法 |
|---|---|
| 登记源多源混淆 | 每定制点唯一登记行（唯一 design）；点级精确匹配消解前缀包含聚合 |
| C 编号零持久化 | id 显式落登记行（分配规则见下），与扫描排序解耦 |
| 结构性膨胀 | 产物文件退役——衍生物不再 git 受控，freshness 铁律整个退役（PR #65/#67 类摩擦根除） |
| removal_condition 待补 | 登记表点级字段一次回填；判据语义双轨进 runbook 附录 |

### 评审收敛记录（三轮，2026-10-31）

- 讨论材料：fork 仓外 `temp/2026-10-31-customization-registry-discussion.md`；
- 评审 AI-2：方向 C 采纳；其「砍 ID」经责任人终裁**否决**（留+降级定位）；其 removal_condition
  双轨、错误注入验收门槛**采纳**；
- 评审 AI-3：C+ 四缺口**全部采纳**——①R3 豁免依赖（`check_r3_markers.py:57` 实证）→ 豁免源迁
  `_common.py`；②CI strict；③id 高水位矛盾 → tombstone；④孪生行序换绑 → 孪生组+预期计数；
  其 check/report 双命令、升级时点快照附 verification、fail-closed 测试清单**采纳**；
  其「marker 内写 id」列为未来 marker 规范演进候选，本轮不做（零上游改动约束）。
- AI-2 关键认知修正（采纳为设计依据）：对账能力**今天已存在**（`match_markers_to_regs()`
  双向校验 + CI freshness 步骤实际在跑）——本设计不是新建信任根，是剥离落盘让既有校验直接充当门禁。
- 评审第四轮（design 定稿前，事实抽查全过）：M1 孪生组身份边界（显式声明入契约）、
  M2 id「引用继续有效」承诺过强（降格写实 + stale 实例标注）、M3 引用面清单补
  `upstream-merge-v0.32.2/design.md`——**全部采纳修订**；m1 锚算法 test-plan 钉死、
  m2 孪生组精确盘点（2 组）、m4 改写定稿先呈报逐字核对——**采纳**；m3 机制与语义回填
  分步签认——**维持一次签认**（拆分致登记表二次动+二次重签，违背「一次改到位」初衷；
  以签认呈报时分节审阅指引 + 条件草案对照表补偿），责任人裁决权保留。

## 登记表新格式（契约核心）

```markdown
## 定制点登记预告

> 批次锚注（可选）：本批次共享的上游依赖符号/风险语境一段，行内 anchor/risk 可写「（批次锚注）」引用。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C021 | src/chrys/service/llm/wire_client.py | AIxCoding auth: send-time | 1 | （批次锚注） | 低 | 〔上游等价〕上游 wire_client 原生支持登录会话凭据注入请求头，且满足内部凭据管理需求（对比确认后提请裁决） |

### 退役记录（仅有点退役时存在）

| id | 原落点 | 退役日期 | 依据 |
```

字段与规则：

- **id**：`C###` 三位，**降级定位**——登记行沟通标识（PR/评审/跨文档/升级交付物紧凑引用），
  **非匹配主键**（主键=落点+marker 锚）；升级定位仍以「文件+符号」为主（runbook 现行口径不变）。
  **尽力而为的软标识（评审 M2 写实）**：冻结只保证其后新增引用稳定，**冻结前已漂移的现行
  引用不因此修复**——实例：`upstream-merge-v0.32.2/design.md` 存活核对矩阵中 C002 引作
  `logs/screen.py` 系漂移前旧值（现 C002=`pyproject.toml:206`），随引用面核查（联动清单 ⑧）修正。
  分配：`max(全部登记行 id ∪ 退役记录 id) + 1`（**含退役号的历史高水位**——AI-3 缺口③修复）；
  check 跨 design 全局校验唯一性与格式（违规=error）；并行批次撞号由后并入方调整。
- **落点**：marker 所在上游文件 posix 路径（不含行号——行号漂移不触发登记跟改）。
- **marker 锚**：marker 注释正文前缀，写到同文件内唯一区分（歧义=error）。孪生组共享锚。
  精确匹配算法（前缀定义、空白/大小写归一化、歧义判定规则）在 test-plan 钉死（评审 m1）。
- **预期计数**：该 (落点, 锚) 组预期 marker 数，空 = 1。**精确盘点（评审 m2）**：现行 29 点
  中孪生组仅 2 个——`main/commands.py` 锚 `AIxCoding tui: /login /logout` ×4、
  `main/screen.py` 同锚 ×2（其余 23 点所在文件内锚唯一，均单行登记）。**计数不符 = error**
  （多→未登记 marker；少→marker 丢失或计数错）——AI-3 缺口④修复：换绑静默错被计数校验
  拦截，且不再依赖「行序对应」契约。
- **孪生组身份边界（评审 M1 显式声明）**：孪生组按组登记，**组内成员不可单独寻址**
  （共享锚+落点无行号+单行登记三者叠加的结构性结果）。组内**部分**成员退役的场景
  （如上游重构删除 4 处注册点中的 1 处）：计数校验只能报「计数不符」，**无法区分
  「上游删了一个」与「我方误删了一个」，也无法表达留下的成员是否仍有存在理由**——
  该场景升级处置 = 人工对比分析（升级决策交付物流程，不受本机制自动化承诺覆盖）；
  某成员确需单独退役/分化时，**必须拆组并改写 marker 锚以恢复可寻址性**（拆组依赖
  可改 marker 注释，与「marker 内写 id」未来演进候选合并考虑）。
- **anchor / risk**：依赖符号与风险语境；可引用批次锚注（report 不展开，无复制问题）。
- **removal_condition**：逐组取值（孪生组天然同条件）；格式=〔判据类别〕+ 点specific 补充，
  类别语义见 runbook §5 附录（双轨，见下）。
- **退役记录**：点退役时原行移入该小节（id 保留不复用、不参与匹配、计入高水位）；
  当前 29 点无退役，机制先行。
- marker 措辞改写/文件移动 → 匹配断裂 = error → 跟改登记行（R10 重签）；**id 不随跟改漂移**。

## 工具设计（gen_customizations.py 改造，保留文件名）

保留 `aixcoding/tools/gen_customizations.py` 文件名（CI/规范/文档引用面最小破坏），
docstring 更新为 registry auditor/viewer 语义；`--repo` 考古模式不动。CLI 三形态：

1. **check**（默认）：只读对账——marker↔登记双向 + id 唯一性/格式/高水位 + 锚歧义 +
   预期计数 + 豁免清单核对；**零文件写入**（测试断言）；退出码 0/1/2 对齐仓库惯例。
   `--strict`：孤儿登记（登记组无 marker）从 warning 升级 error——CI 用；
   本地默认宽警告（保「先 design 后代码」工作流）。
2. **report**（`--report`）：同一内存模型的 stdout 全景视图（Markdown：定制点表
   id/落点/marker 摘要/归属模块/removal_condition/来源 + 警告 + 豁免表）——
   新会话 AI / 新人全景入口（入口写进 AGENTS.md AIxCoding 段）；
   **升级时点快照**：追上游批次将 report 输出附入该批 verification.md（明确标注日期的
   不可变证据，无 freshness 义务）。
3. **豁免源迁移**：`MARKER_EXEMPTIONS` 从 gen 硬编码移至 `_common.py`，gen（report 渲染）
   与 `check_r3_markers.py` 共用——消除「gen 渲染→产物文件→R3 读回」间接环（R3 现从
   `CUSTOMIZATIONS.md` 读豁免，文件退役后该路径断裂——AI-3 缺口①）；
   `check_r3_markers.py` 的 `load_exempt_files()` 改读 `_common.py` 清单。

## removal_condition 双轨

- **判据语义**（8 种条件类别定义：上游等价可对接/依赖机制退役/常驻/目录退役等）→
  UPGRADE-RUNBOOK §5 新增附录「淘汰触发条件判据」（升级现场判据在手，静态低频）；
- **逐组取值**→ design 登记表行（随点演进、受 R10 签认绑定）；
- 取值来源 = 回填待办（temp）全景清单 8 种条件草案，随 8 design 重签逐组确认。

## 迁移映射（8 design 重写 + R10 重签 + 产物退役）

| design | 现状 | 迁移后 | 备注 |
|---|---|---|---|
| `tui/design.md` | 1 行摊 22 marker | 点级/孪生组级行（commands.py 孪生组合并行，预期计数 4/2 等） | anchor/risk 用批次锚注；removal_condition 按 4 组条件落值 |
| `auth/design.md` | 2 行（包行+stamp() 噪音行） | C021/C022 两行；anchor 并入 tier 勘误语义；stamp() 行删除 | **顺带核销 auth-stamp 待办**（孤儿登记清零） |
| `tier-migration/design.md` | 2 行 | 登记表清空 + 指向声明 | 勘误语义并入 auth/diagnostics 现行行 |
| `diagnostics/design.md` | 2 行（config/logging） | C007 一行（落点 `logs/screen.py`）；支撑语义并入 anchor | config/logging 行退役；资产清单归 DIRECTORY.md |
| `auth-logging/design.md` | 1 行 | C004 一行 + removal_condition 落值 | 落点 `app/cli/app.py` |
| `agents-md-note/design.md` | 1 行 | C001 一行；removal_condition 取「常驻」 | C001 现行源裁决收敛于此 |
| `ai-gates/design.md` | 1 行（双源） | 登记表清空 + 指向声明 | 双源消解侧 |
| `ruff-test-exemptions/design.md` | 1 行 | C003 一行 + removal_condition 落值 | 落点 `pyproject.toml` |

- `CUSTOMIZATIONS.md` **删除**；人工区信息（上游基线 0.32.2/升级日期/runbook 链接）迁
  UPGRADE-RUNBOOK（活文档，实施时核对既有节位避免重复）；
- 存量 C 编号引用：id 保留故 C0xx 引用**继续有效**；现行文档中 `CUSTOMIZATIONS.md` 文件
  引用改为 check/report 命令口径；历史记录档（verification/self-review/已完结 design）不改写。
- **实施约束（评审 m4）**：8 个登记表改写与 tier-migration 勘误并入（auth 行 anchor 定稿
  文本等）先产出**逐字定稿清单呈报责任人核对**，确认后再落盘改文件——R10 重签审的是
  可逐字核对的结果，非"并入语义正确"的抽象承诺。

## 上游改动清单（R2）

**零新增上游文件改动**。`AGENTS.md` 属既有已获批文件（agents-md-note / ai-gates 批次
R2 池内），本批次仅在其 AIxCoding 段（C001 定制域）追加 check/report 命令入口一句，
不扩 R2 面（联动清单第 7 项）。其余全部落在自有域：`aixcoding/tools/`、`aixcoding/docs/`、
`aixcoding/tests/tools/`、`templates/design.md`、`.github/workflows/aixcoding-tests.yml`
（fork 自有 workflow，非上游 ci.yml）。marker 扫描逻辑（`_common.py` R3 识别/豁免后缀/
品牌串甄别）与考古模式不动。

## 联动清单

1. `gen_customizations.py`：三形态改造（约 +120/−80 行）；`_common.py`：豁免清单迁入 + 登记表新表头解析；
2. `check_r3_markers.py`：豁免源切换 `_common.py`（约 5 行）；
3. `aixcoding-tests.yml:51-56`：freshness 步骤替换为 `gen_customizations.py --strict`（一步）；
4. `aixcoding/docs/standards/templates/design.md`：登记节模板换新格式；
5. `DEVELOPMENT.md`：§5（清单生成条款→对账命令）/§8（升级流程中产物引用）跟改；
6. `UPGRADE-RUNBOOK.md`：§4 验证矩阵（gen 幂等门→strict 对账门）、§5 判据附录（新增）、
   人工区信息迁入、§3 marker 存活核对引用 report；
7. `ROADMAP.md` 补做义务①销项；`AGENTS.md` AIxCoding 段补 check/report 命令入口一句；
8. `CUSTOMIZATIONS.md` 删除 + 引用面核查（现行文档逐个，历史不改写）——**明确列入
   `upstream-merge-v0.32.2/design.md`**（评审 M3：无登记表故不在迁移清单，但其存活核对
   矩阵是现行 C 编号引用最密集处，且含冻结前漂移的 stale 引用，须逐条核对修正）；
9. 仓外 temp 两待办核销：`stable-customization-id.md`（本批次实现即核销）、
   `removal-condition-backfill.md`（双轨落地即核销）。

## 定制点登记预告

不适用：纯开发资产与文档改造（devtools 口径），零上游接触面、零 marker 变化。
本批次**最后一次**触发旧 freshness 义务的场景是删除 `CUSTOMIZATIONS.md` 本身
（删除属产物退役，无重跑义务，提交信息说明即可）。

## 测试与验收（test-plan 展开，此处门槛项）

- `aixcoding/tests/tools/test_gen_customizations.py` 适配 + 新增；**错误注入清单**（三轮评审
  合并，作为验收门槛而非可选）：未登记 marker / 孤儿登记（含 strict 升级）/ 未签认 design
  / id 重复与非法格式 / 锚歧义 / 孪生计数不符 / 表头损坏与文件不可读 fail-closed /
  check 零文件写入 / CLI 退出码 / 豁免清单双消费一致；
- 防漂移回归：删任一 marker → 其余 id 不变；插入新文件改变扫描排序 → 存量 id 不变；
- 全部现行 29 点经 check 绿（含 strict）；report 输出人工核对；
- 定制四门 + 上游测试套全绿；PR 双 CI 绿。

## 风险与最坏情况

- **匹配断裂频率被低估**（marker 措辞/文件移动触发登记跟改+重签）：marker 文本稳定性是
  既有纪律；断裂即 check error 暴露且 id 不丢；代价限于登记行跟改。
- **孪生组部分退役的结构性边界**（评审 M1，契约已显式声明）：组内成员不可单独寻址，
  计数校验无法区分「上游删除」与「我方误删」——该场景依赖升级决策交付物的人工对比
  分析兜底；成员需单独分化时拆组+改写锚（触上游文件，走 R2）。
- **对账命令单点**：信任面继承自既有校验（非新建）；盲区与产物幂等门禁相同（扫描 bug
  双盲），以错误注入测试 + 零写入断言补偿——强于旧门禁（其从未做注入自检）。
- **失去 git 内聚合快照**：演进真相在代码 diff 与 design 登记表 diff（均不受影响）；
  任意历史提交可重跑 report 重建视图；升级时点证据由 verification.md 快照承载；
  新会话全景入口 = report 命令（AGENTS.md 有入口指引）。
- **规范迁移遗漏**（引用面广）：联动清单逐项打钩 + check_docs/CI 门禁兜底；
  遗漏的旧「跑 gen 刷新产物」指引会在下次触碰时暴露（命令语义已变）。
- **回滚**：单 PR revert 恢复（工具/登记表/产物删除/规范同批原子切换，无中间态）。

## ADR 判定（DEVELOPMENT.md §6）

逐项：① 砍 ID（AI-2）/保留旧产物瘦身（B）/集中台账（E）/marker 写 ID 均被认真考虑并否决
（评审收敛记录 + 讨论材料）；② 撤销代价中（8 design 重签+规范迁移，revert 单点可逆）；
③ **约束未来工作模式**——登记表格式契约、对账门禁形态、产物退役决定此后所有批次的
登记与升级范式；④ 无新增上游依赖。**结论：出 ADR-0015「定制点登记点级化与产物退役
（对账命令化）」**。
