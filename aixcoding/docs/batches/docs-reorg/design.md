# 设计：docs 目录分层组织（docs-reorg）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：先实践

## 方案概述

**除 `standards/` 外，全部批次/专项目录（18 个）平铺迁入 `aixcoding/docs/batches/`**，
顶层只留 `standards/`、`batches/` 与根文件。只增加 `batches/` 一层，之后不再为任何分类
维度（管线内外/功能治理升级）增加目录层——分类信息一律作为 `INDEX.md` 的信息列表达。
路径一次性迁移后永久稳定（新批次落点唯一：`batches/<feature>/`，完结后零移动）。

本方案解决的是**顶层堆积无收敛**与**目录级导航入口缺失**（团队原始反馈："每个功能
单独建目录直接放 docs 下，越来越多，不方便看"），不消除批次目录总数随开发活动的自然
增长——`batches/` 内目录数仍会增加，这是刻意接受的（分类维度放索引不放路径，理由见
备选方案对比与 ADR-0016 要求）。

同步改造治理工具扫描面（`find_design_docs` glob 前缀平移）、更新全部活引用（代码
字符串/文档交叉引用/CI 注释/仓外待办）、修订规范条文并补一条布局 ADR。

**本批次零上游文件改动**（全部改动位于 `aixcoding/` 定制专区、`src/chrys/*/aixcoding/`
定制文件的 docstring、仓外待办文档；R2 表为空，R11/R2 节按模板删除）。

目标布局：

```
aixcoding/docs/
├── standards/            # 规范族 + 全局 ADR + 模板 + 评审 HOWTO（不动）
├── batches/              # 【新增】全部批次/专项目录平铺（18 个；§6 修订后新批次落点）
│   ├── mock/  auth/  auth-logging/  tui/  ai-gates/  ci-gate/
│   ├── upstream-ci/  upstream-merge-v0.32.2/  tier-migration/
│   ├── launcher-retirement/  customization-registry/  devtools/
│   ├── diagnostics/  exemption-governance/  ruff-test-exemptions/
│   ├── restructure/      # 改造专项（考古参考，无 design.md，不参与登记扫描）
│   ├── agents-md-note/   # 注记（design.md 承载 C001 现行登记 + R2 批准，必须入扫描面）
│   └── docs-reorg/       # 本批次自身（随迁）
├── INDEX.md              # 【新增】目录导航索引（纯静态三列，见 §4.4）
├── ROADMAP.md            # 不动（路线权威，仅更新其中引用）
└── versioning.md         # 不动（含未来 CHANGELOG.md 落点）
```

顶层目录 18 → 2（+INDEX.md）。批次目录（含其内 `adr/`）整体 `git mv`，内部文件结构
不变。

**结构裁决记录（责任人 2026-10-31）**：除 `standards/` 等全局内容外其余全部归入
`batches/`。该裁决同时修复一个实证缺陷：`batches/agents-md-note/design.md:39` 承载 C001 现行
登记行（落点根 `AGENTS.md`）、`:21-25` 为其 R2 批准表——任何"agents-md-note 不进
`batches/`"的布局（含本草案 v1 的"异类留顶层"与"`features/` 中间层"变体）在
`glob("batches/*/design.md")` 下都会漏扫 C001，导致 `gen_customizations.py --strict`
对账红。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| `archive/` 状态分层（完结批次迁入） | 顶层只余活跃批次 | ①语义冲突：design.md 是 R2 审批池/登记对账/MARKER_EXEMPTIONS 依据的现行载体，`archive` 之名暗示失效；②持续成本：每完结一批 = git mv + 全链引用更新 + CI 验证，永久性重复劳动；③"何时算完结"成为新流程判定点 | 同 batches/（一次性），但×每批次重复 | 否决（两轮 AI 评审一致） |
| 按技术域分组（auth 域/infra 域…） | — | 类别边界模糊且随时间漂移（auth-logging 归 auth 还是独立？）；工具/引用改动成本同 batches/ 而收益更差 | 同 batches/ | 否决 |
| `batches/<类型>/<feature>/` 多类型层（features/governance/upgrades/…） | 文件管理器视觉分组 | ①逐批归类裁决（10 个非典型批次每类归属都要裁，未来每新批次重复）；②类型目录增殖；③归错类跨类型移动 = 弱化版 archive 问题；④工具 glob 需递归（契约弱化）或枚举前缀（每新增类型改工具） | 同 batches/ | 否决 |
| `batches/features/` 中间层 + 异类平铺 batches 顶层 | 分组较轻 | **实证缺陷：漏扫 `batches/agents-md-note/design.md` 的 C001 登记行**（glob `batches/features/*/design.md` 不覆盖 batches 顶层平铺目录）；"走没走管线"判定在本批次自身即模糊 | 同 batches/ | 否决 |
| 仅 INDEX.md 不分层 | 零自动化风险、半天 | 不解决顶层堆积与结构收敛（新批次无稳定落点规则，顶层持续膨胀），痛点只缓解一半 | 零 | 否决（团队已接受分层，索引并入本批次一次到位） |
| **`batches/` 单层平铺全部 18 目录 + INDEX（本方案）** | 路径永久稳定、后续零迁移、零归类判定；glob 前缀平移后扫描面与现状严格等价（17 design.md 原样覆盖）；`upstream-merge-vX.Y.Z` 类目录（天然建后不动）最大受益；分类信息全在 INDEX 列 | 一次性引用更新面较大（实测 67 文件 + CI 注释 3 处，见 §4.3，机械替换为主） | 零上游文件；工具 2 处 + 测试夹具 1 组 + 文档/注释约 70 文件 | **采纳** |

## 实施清单

### 4.1 逐目录去留清单（裁决已定：全部平铺迁入 batches/）

| # | 目录 | 性质 | 去向 | 备注 |
|---|---|---|---|---|
| 1 | `mock/` | 功能批次（PR #56） | `batches/` | verification+self-review 齐全 |
| 2 | `auth/` | 功能批次（PR #60） | `batches/` | 同上 |
| 3 | `auth-logging/` | 功能批次（PR #70） | `batches/` | 同上 |
| 4 | `tui/` | 功能批次（PR #67） | `batches/` | MARKER_EXEMPTIONS 依据 ×3；23 点登记主体 |
| 5 | `ai-gates/` | 功能批次（PR #68） | `batches/` | verification+self-review 齐全 |
| 6 | `ci-gate/` | 治理批次（CI 门禁） | `batches/` | 同上 |
| 7 | `upstream-ci/` | 治理批次（PR #58，CI 桥接） | `batches/` | verification 齐全（self-review 无，以 verification 记录为准） |
| 8 | `upstream-merge-v0.32.2/` | 升级批次（2026-10-31 合并） | `batches/` | verification+self-review 齐全 |
| 9 | `tier-migration/` | 功能批次（PR #64） | `batches/` | MARKER_EXEMPTIONS 依据 ×1；唯一现行登记行 |
| 10 | `launcher-retirement/` | 退役批次（ADR-0013） | `batches/` | design 内含退役登记行 |
| 11 | `customization-registry/` | 治理批次（ADR-0015） | `batches/` | verification+self-review 齐全 |
| 12 | `devtools/` | 阶段二四工具批次 | `batches/` | 同上（内含考古报告，引用更新豁免见 §4.3-G） |
| 13 | `diagnostics/` | 阶段二诊断包批次 | `batches/` | C002–C005 定制点登记承载 |
| 14 | `exemption-governance/` | 治理批次 | `batches/` | verification+self-review 齐全 |
| 15 | `ruff-test-exemptions/` | 治理批次 | `batches/` | 同上 |
| 16 | `restructure/` | 管线外改造专项 | `batches/` | 考古参考（DIRECTORY.md/ROADMAP 引用随迁更新）；无 design.md，不参与登记扫描 |
| 17 | `agents-md-note/` | 注记（管线外，design 已签认） | `batches/` | **C001 现行登记 + R2 批准承载，必须入扫描面**（结构裁决的实证依据） |
| 18 | `docs-reorg/`（本批次） | 治理专项 | `batches/` | 草案期建于顶层（循现行 §6），实施时随批次迁入 |
| — | `standards/` | 规范族 | 顶层不动 | 全局 ADR/模板的稳定锚点 |
| — | `ROADMAP.md` / `versioning.md` | 根文件 | 不动 | 仅更新其中引用（§4.3-F） |

### 4.2 工具与测试改造

| 改动 | 位置 | 内容 |
|---|---|---|
| 扫描面前缀平移 | `aixcoding/tools/_common.py:357-359` | `find_design_docs`：`docs_root.glob("*/design.md")` → `docs_root.glob("batches/*/design.md")`。仍是精确单层 glob，不递归；扫描面 = 现状严格等价（17 个 design.md 原样平移：15 批次 + agents-md-note（C001）+ docs-reorg；`restructure/` 无 design.md 自然不参与）。`gen_customizations.py --strict` 对账与 `check_r2_diff.py` R2 审批池经此自动覆盖，全部登记行（C001–C029）与 R2 池不变。**池等价性的显式验证方法见风险节**（`check_r2_diff.py` 在本批次零上游 diff 时对空池同样通过，其绿不构成池等价证据） |
| 豁免依据字符串 | `aixcoding/tools/_common.py:87,92,97,102` | MARKER_EXEMPTIONS 4 条依据路径加 `batches/` 前缀（tier-migration ×1、tui ×3；报告渲染用，无磁盘校验，但须指向有效路径） |
| 帮助文本 | `aixcoding/tools/__init__.py:2`、`_common.py:7`、`check_r3_markers.py:10`、`check_import_boundaries.py:22` | 4 处 `aixcoding/docs/batches/devtools/design.md` 文本更新 |
| 测试夹具 | `aixcoding/tests/tools/test_gen_customizations.py`（`aixcoding/docs/demo/design.md` 夹具 31 处及 :4 docstring）、`test_check_r2_diff.py:38,46`、`test__common.py`（r2_approved_upstream_files 夹具） | 夹具路径同步 `batches/` 布局（如 `aixcoding/docs/batches/demo/design.md`），并补一个布局用例（batches 之外的 design.md 不被扫描） |
| 兼容确认（不改） | `check_docs.py` | 递归 glob（`**/design.md`，排除 templates）天然覆盖 `batches/`；ADR"同目录后继"约束不受影响（全局 ADR 在 `standards/adr/`，批次 ADR 随目录整体迁移） |
| 兼容确认（不改逻辑，注释要改） | `.github/workflows/aixcoding-tests.yml`、`aixcoding-upstream-ci.yml` | 四工具命令不变；doc-only 跳过按 `^aixcoding/docs/` 前缀（`:51`），`batches/` 在其下不受影响；**但其中 3 处注释引用需更新**（§4.3-C） |
| marker 契约确认 | `src/chrys/kernel/aixcoding/auth/session.py:3,56` 等注释 | 这些 design 路径注释不含 `AIxCoding` 前缀关键字，非登记 marker；docstring 更新不触 R3 校验 |

**实施原子性约束**：目录 `git mv`（18 个）、工具 glob 改造（上表前两行）、引用更新
（§4.3 全部）三者必须**单次提交原子完成**——任意拆分都产生红中间态（先迁移后改工具：
旧 glob `*/design.md` 顶层扫空，`--strict` 报零登记；先改工具后迁移：新 glob
`batches/*` 扫空）。本地验证同样在三者齐变后一次运行四工具。仓外待办更新（§4.3-F）
无法纳入仓内提交，在 push 前同步完成即可。

**替换执行方式与溯源锚点**：①引用替换以脚本执行**纯路径前缀替换**
（`aixcoding/docs/<name>` → `aixcoding/docs/batches/<name>`，带/不带尾斜杠两种形式），
替换后 `git diff` 每一处改动必须**仅路径前缀变化**——任何超出即视为越出 R10 豁免、
回到逐文档重签流程（机械性可 diff 证明，不靠自觉）；②迁移实施前打 git tag
`docs-pre-reorg` 作为溯源锚点（`git diff docs-pre-reorg..HEAD -- aixcoding/docs`
一条命令可得迁移原貌），定位为**降低史实溯源成本**。

### 4.3 引用更新清单（活引用必更；历史叙述处理原则见 §4.3-G）

规模：实测全仓 `aixcoding/docs/` 模式命中 67 文件 + `.github` 2 文件 3 处注释，机械
替换为主；下列分类为结构化清单，**实施时以全仓复扫输出为准**逐处清零（豁免仅 G 项白名单）。

- **A. 产品代码 docstring（12 处，均为定制文件，非上游文件）**：`src/chrys/kernel/aixcoding/diagnostics/{__init__,logging_support,config}.py`（diagnostics ×3：`__init__`/`logging_support`/`config` 各 1；launcher-retirement ×1：`__init__` 尾注）、`src/chrys/kernel/aixcoding/auth/{types,session,errors}.py`（auth ×2：`types`/`errors`；auth-logging ×2：`session:3,56`）、`src/chrys/app/aixcoding/tui/{__init__,login,login_actions}.py`（tui ×3）、`src/chrys/app/aixcoding/startup.py`（auth-logging ×1）。`app/aixcoding/__init__.py:7` 引用 `standards/adr/0011`，不动。
- **B. 治理工具**：§4.2 所列 5 文件 9 处。
- **C. CI workflow 注释（3 处，2026-10-31 评审补充）**：`.github/workflows/aixcoding-tests.yml:5`（`aixcoding/docs/batches/ci-gate/design.md`）、`:48`（`aixcoding/docs/batches/devtools` 段注释）、`aixcoding-upstream-ci.yml:10`（`aixcoding/docs/batches/upstream-ci/design.md`）加 `batches/` 前缀；`aixcoding-upstream-ci.yml:51` 的 doc-only 前缀判断不改。
- **D. 定制测试**：`aixcoding/tests/conftest.py`、`tests/auth/{conftest,test_session_logging,test_llm_token_wiring}.py`、`tests/tools/`（§4.2 夹具项）、`tests/diagnostics/test_entry_wiring.py:4`——具体行实施时以复扫输出为准逐处更新。
- **E. docs 内部交叉引用（约 30 文件，风格 A 仓库根相对路径为主）**：各批次 design/self-review/verification/requirements 及 `standards/`（DEVELOPMENT.md、DIRECTORY.md、UPGRADE-RUNBOOK.md、两 HOWTO、ADR-0011/0012/0015）中的 `aixcoding/docs/<feature>/` 活引用，批量加 `batches/` 前缀。
- **F. 根文件与仓外引用**：`ROADMAP.md:23`（`batches/diagnostics/design.md`）、`:43-44`（`devtools/` 考古报告与工具）、`:5/:63`（`batches/restructure/plan.md` 文本引用）加前缀；仓外待办对 `D:\Tech\Github\huawei\iCode\fork\temp\aixcoding-todos\` **整目录复扫**后逐处更新（已知命中：`2026-10-31-removal-condition-backfill.md:19`（tui）、`2026-10-31-auth-stamp-registration-cleanup.md:5`（auth）；`four-segment-version.md` 中 versioning/CHANGELOG 路径不变）。
- **G. 豁免与原则**：①`batches/devtools/archaeology-report-0.28.0.md` 为历史快照，其中 `../` 均为**上游文档的引用文本**，不随迁移修改（豁免项，复扫白名单）；②其余文件（含 verification/变更记录中的旧路径）**统一更新**——2026-10-31 三轮评审后由"建议"升为"定案建议"，逐类授权依据：**ADR 正文路径** = 失效链接原地修正，`DEVELOPMENT.md:180` 明示授权（不触发取代/重签）；**self-review** = 记录档"签一次追加不重签"（`:64`）；**verification/requirements/test-plan/plan** = 活文档不签认（`:64`）；**唯一需豁免声明的仅 17 个 design.md**（决策档）——本批次 design 签认即一并批准"仅限纯路径前缀替换、语义零变更、不触发逐文档重签"，机械性以替换脚本 + git diff 逐处仅前缀变化证明（§4.2）。**否决二分备选**（历史叙述保留原貌）：判定标准模糊（"登记行迁移自 X"既是事件叙述又指向现存文件）致复扫验收从零命中退化为人工判定，核心机器防线失效；ADR 上无解——按冻结惯例保留旧路径 = 故意留失效链接，违反 `:180` 授权；且 self-review/verification 的记录档/活文档语义本就是"跟随现状的定位符"，路径更新不损害日期/版本/命令输出等真史实。**副作用披露义务**：统一替换使历史验证记录呈现为新路径（仿佛当时在新路径执行），本批次 verification.md 须声明"历史文档路径经机械迁移改写，不代表重新执行"；史实溯源以 tag `docs-pre-reorg` 降低成本（§4.2）；③`AGENTS.md`（仅 standards 引用，预计不动）与 `aixcoding/README.md`（导览提及）列为实施时核查项；④docs 内 markdown 相对链接：预扫仅 `DIRECTORY.md:7 → ../../restructure/plan.md` 与 `batches/restructure/plan.md:10 → ../standards/adr/` 两处——restructure 迁入 `batches/` 后，前者改为 `../../batches/restructure/plan.md`，后者深度加深一层（`../../../standards/adr/`）；批目录内无其他相对链接，实施后复扫核验。

### 4.4 INDEX.md 设计（纯静态导航，零漂移维护点）

- 位置 `aixcoding/docs/INDEX.md`；头部声明分工：**ROADMAP 管路线与 DoD（阶段/顺序/进度），INDEX 只管目录导航**；批次验收与签认事实在各目录 `verification.md`，INDEX 一概不复制；
- 表列（三列，全部为一次性人工定性，迁移完成后不随时间变化）：`目录 | 类型 | 一句话简介`。**目录列为 Markdown 相对链接**（如 `[batches/mock](batches/mock/)`），保证从 INDEX 一跳可达；类型为信息维度（功能批次/治理批次/升级批次/退役批次/改造专项/注记），不对应物理子目录；简介为一次性人工撰写；
- **无状态列、无 PR 号/日期等动态事实数值**——决策记录：2026-10-31 责任人澄清，团队从未提出"活跃/完结区分"诉求（原始反馈仅为"目录多、不方便看"），该维度系方案演进中被叠加引入，删除。由此 INDEX 无任何会随时间失效的信息，无双源漂移、无生成需求（生成器只能产出目录名/链接骨架，零信息量）；
- **完整性流程落点**：`DEVELOPMENT.md` §6 修订条文增加"**创建批次目录时同步在 INDEX.md 增加一行（目录/类型/简介）**"（§4.5）——这是创建时的一次性动作（与建目录同动作、无时效性），区别于已否决的状态列（需要完结时回访更新）；无生成器、无门禁；
- 本批次 design §4.1 清单即 INDEX 初稿数据源。

### 4.5 规范修订与 ADR

- `DEVELOPMENT.md` §6：`:155` 落点条文 `aixcoding/docs/<feature>/` → `aixcoding/docs/batches/<feature>/`，并在批次创建要求中增补"创建批次目录时同步在 INDEX.md 增加一行（目录/类型/简介）"；`:177` ADR 分池 `功能级决策 → <feature>/adr/` 同步；其余提及处全文核。
- `DIRECTORY.md`：`:23-24` 目录树改为 `standards/` + `batches/`（全部批次/专项）+ 根文件（含 INDEX.md）；`:47` 判定树"是文档？"分支改为"规范族进 `standards/`，其余一律 `batches/<name>/`"；`:143` 命名表同步；`:7` 过渡期声明相对链接随 restructure 迁移更新（§4.3-G④）。
- 新增 `standards/adr/0016-*.md`（编号顺延现行最大 0015）：记录 docs 布局分层决策及被否决备选（`archive/` 状态分层、按域分组、`batches/<类型>/` 多类型层、`features/` 中间层、仅索引、INDEX 承载动态状态列），属全局布局约定，不随批次消亡；**须正面回答"为何 batches/ 内只做一层平铺 + 索引、不再分层"**——本方案解决顶层堆积无收敛与目录级导航入口缺失，不消除批次总数随开发活动的自然增长，分类维度一律放 INDEX 信息列、不编码进路径（易变属性不进路径，与否决 archive/ 同理）。

## 定制点登记预告

不适用：本批次为纯开发资产重组（文档目录迁移 + 开发工具/测试/规范同步），零上游文件接触、
零产品运行时行为变更、无新增定制点。

## 风险与最坏情况

- **扫描面等价性**（本方案核心正确性，两半并列验证）：
  - *登记行对账*：`gen_customizations.py --strict` 全量对账绿，29 定制点不变（覆盖 C001 `AGENTS.md` marker 与 C002–C005）；
  - *R2 审批池等价*：**迁移前后各输出一次 `r2_approved_upstream_files()` 的 approved 集合并逐字比较，必须完全一致**（含 `AGENTS.md` 等由 `agents-md-note` 批准的文件）。注意 `check_r2_diff.py` 本身不构成此验证——本批次零上游 diff，即使池为空它也通过；
  - 布局测试用例（§4.2）作为工具逻辑兜底。
- **中间态红提交**：实施原子性约束见 §4.2 末（mv/工具/引用单提交原子完成，禁止拆分；仓外待办 push 前同步）。
- **断链遗漏**：引用面 67 文件 + CI 注释 3 处，靠两道防线——实施时以复扫命令（枚举 18 个目录名、**带尾斜杠 `aixcoding/docs/<name>/` 与不带尾斜杠 `aixcoding/docs/<name>` 两种形式**的全仓 grep，覆盖 `aixcoding/tests` 等仓内全部路径 + `temp/aixcoding-todos/` 仓外整目录）驱动逐处清零，豁免仅 §4.3-G 白名单；CI 四门禁兜底。
- **git 历史可溯性**：`git mv` 目录整体迁移，`git log --follow` 可溯；如需整体撤销，单批次 revert 即可（无数据损失，纯位置变更）。
- **决策错了会怎样**：若后续证明分层不合适，反向 `git mv` 成本与本批次相当（一次性），无运行时影响。

## ADR 判定

需要 ADR：目录结构级约定变更（docs 布局分层），且存在明确被否决备选（`archive/` 状态
分层、按域分组、多类型层、`features/` 中间层、INDEX 承载动态状态列）需留档——按 §6
判定出 `standards/adr/0016`（§4.5），记录决策与备选否决理由（含 C001 漏扫实证）。
