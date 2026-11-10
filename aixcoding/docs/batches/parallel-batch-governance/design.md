# 设计：并行批次编号与文档热点治理（parallel-batch-governance）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-10
- 确认意见：无特别意见

## 方案概述

采用“**编号去全局分配、导航去集中维护、共享路线文档删除**”三件套：

```text
定制点：C### 全局高水位 → <batch-slug>:<point-slug> 批次命名空间
ADR：  NNNN 目录最大号 + 1 → ADR-<batch-slug>--<decision-slug>
        旧 ID/区间/取代链保留；唯一性 + tombstone 保留；对账主键不变

批次导航：INDEX 全量人工表 → INDEX 删除 + docs_report.py 按需只读视图
          批次目录自动纳入；复用现有 H1；零生成物、零 freshness 门禁

迁移路线：ROADMAP 共享总账 → 本批实施即物理删除
          迁移项由责任人自行跟踪；历史查 Git；不建设替代台账
```

本批直接原子切换到目标态，不先引入“功能 PR 不写 INDEX、合并后再补 INDEX”的临时流程。新规则签认合并前仍执行现行规则，合并后新批次只写自身目录；INDEX 与 ROADMAP 均物理删除，迁移项由责任人自行跟踪，普通批次事实留在批内 plan/verification。

## 成功标准与冲突分级

“低代价自动解决”在本批定义为：AI 不需要人选择编号或猜测方案，不修改已合并侧和其他批次，不做全库引用替换；修复范围可限定在未合并批次已签 design 变更清单内的文件，且能用工具证明除 ID/引用外语义未变。它不以“Git 无冲突”为唯一目标，也不承诺自动判断业务语义。

| 级别 | 典型情况 | 处置权限与验证 |
|---|---|---|
| M0 自动合并 | 不同批次新增独立目录、语义 ID、ADR 文件；无共享追加行 | Git 直接合并，AI 跑 strict/check_docs；无人工作业 |
| M1 机械冲突 | 旧数字 C/ADR 撞号；同批并行产生不同登记语义的重复局部 ID；纯 ID-only 引用修复 | AI 按本 design 的确定性算法处理，窄口径免重复签认；只允许改未合并批次已签 design 变更清单内的文件 |
| M2 语义冲突 | 同一登记点/ADR 决策/路线优先级/R2 范围出现不同结论，或同一 (落点, 锚) 被重复登记 | 停止自动修复，列出分歧交责任人；禁止靠选一边或换 ID 掩盖 |

本批的优化目标是把常规并行开发尽量留在 M0，把旧机制遗留撞号收敛到 M1，而不是把 M2 强行自动化。

## 决策一：定制点与 ADR 语义 ID

### 格式与匹配

- 新格式：`[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*`，书写为 `<batch-slug>:<point-slug>`，例如 `logo-branding:serve-banner`。
- 批次前缀必须等于登记所在 `batches/<batch>/design.md` 的目录名；point-slug 表达稳定语义，不表达行号、扫描顺序或 PR 号。
- 对账主键仍为 `(落点, marker 锚)` 前缀 + 同文件最长锚优先；`anchor/risk/removal_condition`、预期计数、签认加载和孤儿登记语义均不变。
- 完整语义 ID 在全部已签认 design 的 active + retired 范围全局唯一。批次前缀消除跨分支协调，不放宽重复检查；复制同一完整 ID 仍是 error。
- tombstone 保留，历史 ID 永不复用；删除的是“历史最大号 + 1”和连续区间分配义务，不是退役记录。

### 孪生组与兼容

- 新孪生组登记一个语义组 ID + 预期计数 N，组内成员仍不单独寻址；不再把 `len(ids)` 与计数绑定。
- 旧 `C###`、旧区间和旧 tombstone 原样接受，旧区间继续执行“区间成员数 = 预期计数”。不批量迁移、重编号或改写历史引用。
- `gen_customizations.py` 的 ID 解析拆成 legacy range 与 semantic id 两种形态；唯一性仍对完整 ID 字符串执行，report 保持紧凑展示。
- 新定制测试使用行为名，不把登记 ID 编进测试函数名；存量 `test_c...` 只在相应行为本身变更时按需处理，不做全库机械改名。

### ADR 双格式

- 新 ID：`ADR-<batch-slug>--<decision-slug>`；文件名：`<batch-slug>--<decision-slug>.md`。双连字符分隔批次与决策名，避免 Windows 文件名禁用冒号，也使批次前缀可机械校验。
- **ADR 全部放入 `standards/adr/` 全局池**，不再按“全局/功能”分类，不新建功能池，也不保留存量功能池。存储位置不再承担作用域分类；此后的新 ADR ID 由 batch 前缀记录来源批次，避免分类判断和后续移池/改号。
- 存量 `batches/guard-switches/adr/0001-guard-write-scope-factory-default.md` 随本批实施迁入全局池，并按决策时间线改号为 `standards/adr/0023-guard-write-scope-factory-default.md`（标题 `ADR-0023：护栏出厂写入范围改为不限制`）：该决策发生于 2026-11-05 且已影响产品默认值，早于本治理决策。同步更新 `guard-switches` 批次内 requirements/design/plan **3 个文件内全部路径与编号引用（当前共 6 处）**，另更新 ADR 自身 H1，删除空 `adr/` 目录。
- 本治理决策为 `ADR-0024`。ADR-0023 与 ADR-0024 是语义 ID 规则生效前最后两个旧数字 ADR；此后新 ADR 不再分配数字编号。**0023/0024 已由本批预留，实施窗口内并行批次不得占用**；0023 的 guard 文件在实施时才迁移，预留不以其已存在于全局池为前提，发现占用即停等协调，不自动改号。
- 新语义 ADR 的完整 ID 在全局池范围唯一，重复文件 ID 为 error；batch 前缀须对应现存批次目录。`check_docs.py` 将 `batches/*/adr/` 下出现 ADR 判为位置错误。
- `check_docs.py` 的后继解析扩展为数字/语义双格式：旧数字继续按四位文件查找，新语义按完整文件名查找；`batches/*/adr/` 下出现 ADR 一律报位置错误。新增文件名、批次前缀、位置、唯一性和后继存在性测试。
- 新 ADR 模板和 DEVELOPMENT §6 改用语义命名；ADR-0023/0024 按遗留数字序列保留，不追溯改成语义 ID。

### 旧撞号与机械修复预授权

目标规则下不同批次不会发生编号分配冲突。过渡期或同批并行仍出现重复时，AI 只按以下确定性算法处理，不自由派生语义名；任一输入不满足或无法证明 ID-only 即停等：

1. 已合并主干一侧的 ID、文件和引用全部不动，只处理未合并批次。`occupied` 定义为修复前全景中**所有不属于未合并侧待修复条目的完整 ID**，覆盖 active + retired 定制点、全局 ADR、已合并侧、其他批次和本批未修复条目；待修复条目不预先占位，但已合并侧的同值 ID 仍留在集合中，不得因剔除待修复侧而一并消失。集合之外的历史 ID 永远不占。
2. 单个旧定制点 `Cnnn` 的首选 point-slug 固定为 `legacy-cnnn`（保留三位数字）；旧数字 ADR `NNNN-*.md` 的首选 decision-slug 固定为 `legacy-adr-nnnn`（保留四位数字），新文件为 `<batch>--legacy-adr-nnnn.md`。`legacy-` 前缀保留给机械修复，人工新登记不得使用。旧区间/孪生组因成员寻址模型不同，不在本算法内自动转换，直接停等。
3. 同批重复条目的处理顺序唯一：定制点按 `design.md` 相对路径、原始物理行号、行内列序号升序；ADR 按旧文件相对 POSIX 路径升序。每条记录以此顺序取得从 1 开始的 occurrence index。重复语义 point-slug 的首选 slug 保持原值；旧数字条目使用上一条的保留字 slug。
4. 把候选 slug 展开为本批完整 ID 后判定占用：首选未被 `occupied` 或本轮回填结果占用时直接使用；否则依次尝试 `<首选slug>-m1-<n>`，`n` 从该条 occurrence index 起递增，取第一个空闲候选。同批两个无外部冲突的重复 slug 因而依次得到 `foo`、`foo-m1-2`；所有候选均由修复前快照决定，不由 AI 临时选名。
5. 全库搜索旧 ID 以发现完整引用面，但只修改未合并批次已签 design 变更清单内的文件；不修改 INDEX、ROADMAP、其他批次或已合并历史。发现清单外引用即停止并呈报依赖关系，不得留下已知 stale 引用。相同旧 ID 对应多个新 ID 时，只能修改可由所在登记行/ADR 文件唯一确定归属的引用；其他歧义引用停等。完整 `(落点, 锚)` 重复属于 M2，不走本算法。
6. 新增只读 `aixcoding/tools/check_id_only.py`，对指定修复前 revision 与当前工作树重算上述映射并 fail-closed 校验：登记行去除 ID 列后逐字段相同，R2 表和 ADR 决策节仅规范化声明的 ID/路径后原文相同，其余变更行也只能由声明的 ID/路径映射解释。映射歧义、额外内容差异、范围外文件或门禁失败均非零退出；AI 不得把肉眼 diff 当作语义不变证明。随后运行 strict、check_docs 和相关测试。

满足上述条件的 ID-only 修复视为已签方案的机械冲突处置，不重复签认。其授权边界写入 DEVELOPMENT §4.1/§5 和 ADR-0024；任何落点、锚、计数、R2 文件、行为或 ADR 决策内容变化都退出预授权，按原规则重签或呈报裁决。

不建设通用 renumber 工具：`check_id_only.py` 只读验证、不写文件；AI 以批次目录为边界做小范围编辑，确定性算法和差异证明共同承担验证。

## 决策二：INDEX 删除 + 按需导航

### 目标形态

`aixcoding/docs/INDEX.md` 随本批实施**物理删除**，不保留薄入口或重定向文件。其原有职责全部转移：

| 原 INDEX 职责 | 目标承载 |
|---|---|
| 批次目录全景/一句话简介 | `uv run python aixcoding/tools/docs_report.py` 按需只读视图 |
| 定制点全景指引 | 既有 `uv run python aixcoding/tools/gen_customizations.py --report` |
| standards / 支持手册等固定入口 | `aixcoding/README.md` 速查表与 `DIRECTORY.md` 蓝图；ROADMAP 入口随文件删除 |
| 新批次创建登记义务 | 取消——目录自动进入 `docs_report.py` 扫描面 |

不保留 INDEX 的核心理由：批次目录全景和定制点全景均有实时命令真值后，INDEX 只剩少数静态链接；这些链接由 README 承载更自然。`llm-keyless-sdk-auth` 在 `9d824cb5` 已六件完整并合入主干，却从未登记 INDEX，是“人工登记义务无 freshness 门禁必漏”的直接实证。保留任何形态的 INDEX 都会延续“集中导航文件”的入口惯性，并要求规范持续解释其与命令视图的分工。

### 只读导航工具

新增 `aixcoding/tools/docs_report.py`：

1. 扫描 `aixcoding/docs/batches/` 的全部一级目录，按目录名确定性排序，零文件写入；不按完整管线、微改动豁免或管线外注记分类，凡有目录均纳入。
2. 依次从 `requirements.md`、`design.md`、`plan.md` 取第一个可用 H1 作为导航标题；不要求 front matter，不批量补元数据。封闭清单覆盖的存量微改动目录即使只有 plan/self-review/verification，也可通过 plan H1 导航；这不构成新增缺件目录许可。
3. 输出“批次目录全景”：目录相对链接、现有标题和可用关键文档；类型/人工简介不再作为必备字段。原 INDEX 的策展文字留在 Git 历史，不另建迁移台账。
4. **边界**：批次目录全景不等于全部定制改动全景。只在 PR 描述留痕、没有批次目录的微改动不在展示或统计范围，通过 GitHub merged PR 视图按 PR 描述人工识别；工具不调用 GitHub API、不联网、不猜测微改动分类、不输出其数量，也不要求新增 `micro/` 或精简批次目录。
5. 目录无上述文档、H1 缺失或文件不可读时输出明确警告并非零退出，防止静默漏项；该命令不挂普通功能 PR 的 CI 门禁。
6. 只读视图自动覆盖新目录，因此不存在合并后补 INDEX 的欠账窗口，也不需要 INDEX 缺行报警。

新增 `aixcoding/tests/tools/test_docs_report.py`，覆盖全目录发现、仅有 plan 的豁免目录、非 batches 微改动记录不进入扫描面、回退顺序、确定性、零写入、缺失/不可读源和 CLI 退出码。

### 退役与引用处置

1. 删除 `aixcoding/docs/INDEX.md`；本批实施前按现行 ADR-0016 保留其治理批次登记行，并补登评审发现的 `llm-keyless-sdk-auth` 历史漏行。补登只纠正删除前的现行登记缺口，不转为永久维护义务，实施时随 INDEX 一并删除。
2. 活引用必更：`aixcoding/README.md` 目录图/速查表、`DEVELOPMENT.md §6` 创建登记义务、`DIRECTORY.md` 目录蓝图；改指 `docs_report.py` 或具体稳定文件。
3. ADR-0016 正文不改写，由 ADR-0024 修订其 INDEX 决策；batches 单层平铺与 design 扫描面继续有效。
4. 历史批次 verification/design/self-review 中“已登记 INDEX”的记录不改写——它们描述当时事实；Git 历史可追溯原 INDEX。
5. 不建立重定向占位文件，不提交生成式 INDEX，不增加 freshness 门禁。

### `aixcoding/README.md` 全景入口落点

INDEX 与 ROADMAP 删除后，README 是人和 AI 发现两个全景命令的第一入口。实施时删除「速查」“查三阶段路线”行及头部 ROADMAP 链接，在表中放置下列相邻两行，并把原“查定制点清单”行改为下述最终文案：

```text
| 查批次目录全景（不含无目录微改动） | `uv run python aixcoding/tools/docs_report.py`（按需只读、零写入） |
| 查定制点全景 / 升级地图 | `uv run python aixcoding/tools/gen_customizations.py --report`（实时对账，勿编辑不落盘） |
```

表下补充固定说明：“无目录微改动查 [GitHub merged PR 视图](https://github.com/ypzyfl/iCode/pulls?q=is%3Apr+is%3Amerged)，按 PR 描述人工识别；docs_report 不统计此类改动。”不新增第三个仓库内工具或 `micro/` 文档义务。

同时将 README「结构一图」中 `docs/` 行的 `INDEX.md（目录导航）` 删除，改为 `standards/` 与 `batches/` 的既有说明；不在 README 中复制任何批次清单或定制点表格，避免形成第二份手工全景。`AGENTS.md` 为上游文件，本批零触碰。

### 备选对比

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| A. 保留人工全量 INDEX，集成人单写 | 工具零改动，保留策展列 | 集中文件仍在，有欠账窗口和清账成本 | 否决 |
| B. 薄 INDEX + 现有 H1 只读聚合 | 链接稳定 | 仍保留集中文件与双入口解释成本 | 否决 |
| C. 每批新增元数据，工具聚合三列 | 保留类型/简介且分布写入 | 存量迁移大，新增长期字段维护义务 | 本批不做；真实需要时另评 |
| D. 删除 INDEX，命令视图 + README 固定入口 | 无逐批共享写入、无元数据迁移、无集中文件惯性 | 需一次性更新少量活引用；历史链接不再指向现文件 | **推荐** |

## 决策三：ROADMAP 随本批直接删除

### 决策与边界

责任人于 2026-11-10 明确：ROADMAP 现在就删除，迁移项由责任人自行跟踪；INDEX 与 ROADMAP 均不保留，历史记录从 Git 获取。本批签认后随实施立即执行，不再等待 telemetry 迁入及数据管道对拍、完整验收或旧分支归档，也不设置最终迁移/收尾批次作为删除前置。

- 物理删除 `aixcoding/docs/ROADMAP.md`，不添加退役标记，不保留冻结档案、重定向或占位文件；删除不代表迁移完成或验收通过，也不虚构最终验收记录。
- 不再先做“退役前治理”：§1 基线、§4 A 类行和 §5 路线条目不另行整理、拆分或搬迁，原文件历史版本由 Git 保存。
- 不建设 per-item 文件、聚合系统或仓库内替代台账；责任人自行跟踪迁移项，批次 plan/verification 仍只记录各自执行事实。

### 删除与引用处置

1. 删除 `aixcoding/docs/ROADMAP.md`，与 INDEX 删除在同一治理批次生效。
2. `aixcoding/README.md` 删除头部 `docs/ROADMAP.md` 链接和「速查」“查三阶段路线”行；分支重建的历史事实可保留为简短说明或指向 restructure 考古记录，但不保留现行路线入口。
3. `UPGRADE-RUNBOOK.md` 删除“功能按 ROADMAP 阶段三迁入”的现行依赖，改为迁移项由责任人自行跟踪；旧分支只作考古参考，不虚称已归档。
4. `DEVELOPMENT.md` / `DIRECTORY.md` 移除把 ROADMAP 当作现行迁移进度入口的表述；仍需保留的历史说明改为考古引用，不把“待迁”事项改写成“已完成”。
5. `gen_customizations.py` 不读取 ROADMAP 文件，但 docstring 与报告标题含“ROADMAP §4 输入”；两处改为独立的“考古盘点”表述，并同步相关测试，消除输出层耦合。
6. 历史批次和历史 ADR 中的 ROADMAP 叙述不批量改写——它们记录当时事实，路径失效可接受，需要内容时查 Git 历史；各批次仍承担 R2 审批、现役登记和 tombstone 的 design 不随 ROADMAP 删除或移出扫描面。

## 决策四：文档闭环门禁与 guard-switches 存量修复

### 为什么要加门禁

`guard-switches` 实证暴露了“CI 绿 ≠ 文档闭环”的缺口：ADR 自 `98b30006` 入库至今仍为草案；`plan.md` 声称 self-review/verification 已完成，但两份文件从未存在于任何 Git 引用。现有 `check_docs.py` 只做签认字段格式校验，合法接受 `草案`，也不检查必备文件与引用闭环，因此无法拦截该类合并。

### `check_docs.py --closure`

默认模式仅供本地手动开发使用：允许草案存在，只校验已确认文档的字段格式。新增闭门模式供 CI 合并门禁使用：

1. **决策档零草案**：全部 ADR、design、self-review 的状态不得为 `草案`；已确认文档继续执行现有字段校验。
2. **批次必备六件完整性**：`batches/` 一级批次目录须具备 `requirements.md`、`design.md`、`test-plan.md`、`plan.md`、`verification.md`、`self-review.md`。
3. **ADR 引用闭环**：文档中的精确 `ADR-NNNN` / `ADR-<batch>--<decision>` 引用必须能解析到全局池既有文件，且被引用 ADR 状态为已确认或被取代；模板与占位文本排除。
4. **plan 结构化完成状态及对应文件最小形态**：仅解析表头同时含“任务”“状态”两列的 Markdown 表格；状态单元格去除 Markdown 标记和首尾空白后必须完整匹配 `完成`、`完成（...）` 或 `完成(...)`，且任务或状态单元格匹配独立 token `(?<![A-Za-z0-9_.-])(self-review|verification)(?:\.md)?(?![A-Za-z0-9_.-])` 时，要求同批对应文件存在。`未完成`、`完成前`、`完成度`、自由 prose 和跨行叙述均不按完成状态解析，token 边界排除 `verification-report`、`self-review-helper` 等无关名称。对应 `self-review.md` / `verification.md` 必须可按 UTF-8 读取，含 H1 和至少一行非空白正文；空文件或只有标题均报错。`self-review.md` 另须通过既有签认字段及零草案校验，`verification.md` 不新增签认义务。本门禁只防止结构化完成状态指向缺失/空壳文件，不声称证明实际评审或验证已执行，也不承诺识别所有自然语言虚假陈述。

### 微改动豁免的增量分流

规则生效后，§6 微改动豁免与六件门禁按目录形态唯一分流：

- 获得微改动豁免的改动**不新建 `batches/` 目录**，继续在 PR 描述留痕，由 GitHub merged PR 视图承接；不为每个微改动新增 closure 豁免或 ADR。
- 如改动需要批次目录导航、独立追溯或已形成批次目录，即放弃文档管线豁免，按完整管线准备六件；任何新增 `batches/` 一级目录均适用六件门禁，不因改动规模小或自称微改动而放行缺件目录。
- docs_report 的“有目录微改动纳入”仅指封闭清单覆盖的存量目录，以及自愿走完整管线的新目录；不授权新增只有 plan/self-review/verification 的目录。此类新增缺件目录必须 closure 失败。

闭门模式接入 `aixcoding-tests.yml` 的 `govern` job（fork 自有 workflow，不触碰上游 `ci.yml`）：`pull_request` 与 `push` 到 `main_aixcoding_cli` 均执行 `--closure`；特性分支发起的 PR 同样闭门，不存在“PR 上仍允许草案”的宽模式。

### 存量缺口冻结清单（R13 豁免，签认即批准）

以 `origin/main_aixcoding_cli@95e23add`（2026-11-10）盘点为基线，既有缺失不随本批补齐，进入封闭清单：

- `agents-md-note`：缺 requirements/test-plan/plan/verification/self-review（仅有 design，管线外注记形态）；
- `auth`：缺 requirements；
- `auth-isolation-mock-ports`：缺 requirements/design/test-plan（微改动豁免形态）；
- `restructure`：仅有 plan（管线外考古参考）；
- `upstream-ci`：缺 requirements/test-plan/plan/self-review；
- `branding-and-command`、`catalog-auth-gating`、`customization-registry`、`docs-reorg`、`exemption-governance`、`internal-installer`、`logo-branding`、`upstream-merge-v0.32.2`、`windows-matrix`：均缺 plan。

实施时将上述清单落为 `aixcoding/docs/standards/closure-exemptions.toml`，以批次名和精确缺失文件名数组为唯一运行时豁免输入；文件头注释记录豁免理由与批准指向 `ADR-0024`，满足 R13 就地留痕。初始清单由本 design 与 ADR-0024 签认批准。

清单常态**只减不增**：对应文件补齐后须在同一 PR 删除精确豁免项并附 closure 证据；已不缺文件却仍保留的 stale 豁免同样报错。不得新增批次、增加缺失文件或扩大豁免范围；包括发现基线盘点漏项在内，任何新增/扩大均须另出 ADR 并由责任人签认，不得随功能 PR 顺手加入。纯粹减少错误豁免不属新增 R13 豁免。清单外新批次零豁免。

R13 封闭枚举新增第⑤类“文档闭环存量豁免的新增/扩大”，明确初始批准、TOML 就地注释和后续新增/扩大的 ADR 路径；`DEVELOPMENT.md` 的 R 系列同步义务要求同时更新 `SELF-REVIEW-HOWTO.md` 与 `PEER-REVIEW-HOWTO.md` 评审背景摘要，并在两份模板检查项中加入 closure 豁免清单对账。

### guard-switches 存量修复（本批验收项）

1. ADR 随单池规则迁为 `standards/adr/0023-guard-write-scope-factory-default.md`（ADR-0023），决策正文不因迁移改写，仅标题/编号与引用同步；
2. 批次责任人李海潮本人补签该 ADR，签认日期写实际补签日，不得倒填；AI 不得代填；
3. 补做双 AI 评审与验证并落盘 `self-review.md` / `verification.md`，明确记录“PR #98 合并时缺失、本批补做”，不得伪造历史结论或历史日期；
4. 更正 `guard-switches/plan.md` 中“self-review/verification 留痕完成”的虚假陈述，改为如实描述补做事实；
5. 修复后 `check_docs.py --closure` 对 `guard-switches` 无任何豁免命中。

## 规范与 ADR 联动

- 新增全局 `ADR-0024`：自包含记录两类语义 ID、M0/M1/M2 冲突分级、INDEX 删除/只读导航、ROADMAP 物理删除与迁移项自跟踪、文档闭环门禁。
- 对 ADR-0015 仅修订决策 2 的全局数字分配规则；点级登记、匹配主键、产物退役、check/report 等其余决策继续有效。
- 对 ADR-0016 修订 INDEX 全量人工表、创建时登记义务及根文件预留中的 INDEX/ROADMAP 形态；`batches/` 单层平铺、路径稳定和 design 扫描面继续有效。
- 旧 ADR 正文不改写；现行规范指向 ADR-0024。旧数字 ADR 永久兼容，新 ADR 语义命名及 check_docs 双格式后继校验纳入本批；ADR-0023/0024 为最后两个旧数字编号。
- `DEVELOPMENT.md` §4.1/§5/§6、`DIRECTORY.md`、`UPGRADE-RUNBOOK.md`、`templates/design.md`、`templates/adr.md`、`aixcoding/README.md` 同步目标规则和机械处置边界；§6 明确“豁免微改动不建 batches 目录，建目录即完整管线六件”的增量分流。

## 文件与改动清单（全部为 fork 自有域）

| 区域 | 改动 |
|---|---|
| 本批次文档 | requirements/design/test-plan/plan/verification/self-review 按管线维护 |
| 全局 ADR | 新增 `standards/adr/0024-并行批次语义标识与文档生命周期.md` 草案并随 design 签认；迁移 `guard-switches` 存量功能池 ADR 为 `0023-guard-write-scope-factory-default.md`，更新 3 个文件内全部旧引用（当前共 6 处）及 ADR 自身 H1 |
| 定制点工具 | `tools/gen_customizations.py` 双格式 ID，docstring/报告标题去除 ROADMAP 标签；`tests/tools/test_gen_customizations.py` 增补错误注入、兼容及考古输出测试 |
| ADR 工具 | `tools/check_docs.py` 支持数字/语义后继、语义文件名校验与 `--closure` 闭门模式；新增 `tests/tools/test_check_docs.py` |
| ID-only 证明 | 新增只读 `tools/check_id_only.py`；`tests/tools/test_parallel_batch_conflicts.py` 覆盖确定性分配、语义差异 fail-closed 与临时 Git 仓库 M0/M1/M2 场景 |
| guard-switches 修复 | ADR 单池迁移与补签、补做 self-review/verification、更正 plan 虚假完成陈述 |
| 导航工具 | 新增 `tools/docs_report.py` 与 `tests/tools/test_docs_report.py` |
| 闭环豁免 | 新增 `docs/standards/closure-exemptions.toml` 作为精确缺失文件的机器可读封闭清单，头部注释指向 ADR-0024 |
| 规范/模板 | DEVELOPMENT（含 R13 第⑤类）、DIRECTORY、UPGRADE-RUNBOOK、SELF/PEER 两份评审模板、templates/design、templates/adr 同步 |
| 根文档 | INDEX 与 ROADMAP 均物理删除；aixcoding README 删除旧路线入口并承载固定入口与导航命令；UPGRADE-RUNBOOK 和 gen_customizations 清除 ROADMAP 现行引用/输出标签 |

预计不修改上游 workflow；仅 fork 自有 `.github/workflows/aixcoding-tests.yml` 将 `check_docs.py` 步骤升级为闭门模式。不新增第三方依赖。

## 上游改动清单（R2）

无。本批不修改 `src/chrys/` 上游文件、上游 `tests/`、`AGENTS.md`、`pyproject.toml` 或上游 workflow；既有 marker 和 R2 批准池零变化。

## 定制点登记预告

不适用：纯 fork 自有文档与开发工具治理，零上游接触、零 marker 变化、零新增定制点。

## 验证门槛（test-plan 后补展开）

1. M0 并行演练：临时 Git 仓库从共同基线拉出两个批次分支，分别使用相同局部 point/decision-slug 和各自语义 ID；合并无编号/INDEX/ROADMAP 冲突，合并后 strict 与 ADR 校验通过。
2. M1 确定性：构造旧数字 C/ADR 撞号、同批重复 slug、首选及 `-m1-<n>` 后缀已占用场景，重复运行映射结果逐字节相同；首条保留/后缀序号、旧区间拒绝和 `legacy-` 人工登记拒绝均有测试。
3. M1 差异证明：`check_id_only.py` 对合法 ID/path-only 变更通过且零写入；分别注入落点、锚、计数、anchor/risk/removal_condition、R2、ADR 决策节、范围外文件和无关正文变化均失败；歧义引用 fail-closed。
4. M2 拒绝自动化：同一 `(落点, 锚)` 重复、R2 变化或 ADR 决策分歧不得被 ID 替换掩盖，测试/文档检查清单要求停等。
5. 定制点 ID：合法/非法格式、错误批次前缀、active/retired 重复、跨批同局部名、旧 ID 与新区间共存、语义孪生组计数。
6. ADR ID：旧数字后继、新语义后继、错误文件名、错误批次前缀、缺失后继；旧 ADR 全库 check_docs 不回归。
7. 对账不回归：现有 marker 匹配、最长锚、孤儿 strict、未签认 design、零写入及全量 strict。
8. 导航：全部一级目录自动覆盖、封闭清单中的存量缺件微改动目录可导航、非 batches 记录不进入扫描面、H1 回退、确定性、不可读/缺失可观测、零写入；输出和 README 均明确无目录微改动不属于展示/统计范围，查 GitHub merged PR。
9. 闭环门禁：草案决策档、新批次缺任一必备六件、ADR 精确引用缺失或指向草案均报错；新增缺件微改动目录报错，无目录豁免不触发六件门禁；plan 精确完成状态指向缺失、空白、仅 H1 文件时报错，`未完成`/`完成前`/`完成度`、自由 prose、跨行和无关文件名不误报；合法完成状态与最小文件通过；pull_request 含特性分支 PR 均执行 closure。
10. 豁免清单：清单外缺失和新增/扩大豁免报错，stale 豁免报错，补齐后删除豁免通过；guard-switches 修复后不再命中任何豁免。
11. guard-switches 修复：ADR 已由责任人本人补签（实际日期）、self-review/verification 补做落盘并如实记录历史缺口、plan 虚假陈述更正、3 个文件内当前 6 处旧引用及 ADR 自身 H1 全部更新。
12. 文档与质量门：INDEX 与 ROADMAP 均不存在，README/UPGRADE-RUNBOOK 等现行入口不再引用它们，gen_customizations docstring/报告标题不含 ROADMAP 标签；用 `git show <删除前revision>:aixcoding/docs/ROADMAP.md` 和对应 INDEX 路径证明历史可读，批次 design 的 R2/登记/tombstone 扫描不变。定制工具测试、ruff/format、check_docs（默认 + closure）、strict、定制套件及 PR 双 CI 通过；最终完整 closure 必须在 guard 修复与签认后执行。

## 风险与回滚

- **机械预授权被扩大解释**：以 M0/M1/M2 表、确定性保留字算法、允许修改的文件边界和 `check_id_only.py` 的“除 ID/引用外零变化”证明约束；任何语义字段或额外内容变化自动回到重签/裁决，不能凭 AI 自判放行。
- **混合 ID 长期存在**：是有意的兼容策略；report 和 check_docs 同时支持旧格式，旧引用不失效。
- **语义 ADR 名称较长**：换取免协调和稳定归属；文件名不编码日期、PR 或序号，决策标题仍承载可读主题。
- **导航信息不如人工三列表丰富或被误当作全部改动统计**：以现有 H1 换取零集中维护，输出和 README 明确只覆盖有目录批次；无目录微改动由 GitHub merged PR 视图承接，不为此补文档或联网。若实证不足，再评估可选元数据，不预先全量迁移。
- **物理删除导致历史路径失效**：这是已接受的处置；只清理现行入口，历史叙述不批量返工，验证用 Git 历史读取原文件，不保留重定向或冻结档案。
- **ROADMAP 删除被误读为迁移完成或误伤定制登记**：ADR 明确删除不代表迁移完成/验收通过，迁移项由责任人自行跟踪；批次 design 扫描面、R2 审批和 tombstone 不动。
- **闭环门禁误伤开发中草案或误判 plan 自然语言**：只有本地手动默认模式允许草案；`pull_request`（含特性分支 PR）与 `push` 到 `main_aixcoding_cli` 均执行 closure。plan 只识别精确表格状态，否定/跨行/无关名称测试防误报；自由文本真实性仍由评审和验证证据承担，不夸大工具能力。
- **存量清单被当作常规豁免**：TOML 精确枚举批次与缺失文件，工具拒绝清单外缺失、扩大和 stale 项；常态只减不增，新增/扩大须另出 ADR 并签认，清单外新批次零豁免。
- **guard-switches 补做文档被误解为历史结论**：补做文件必须显式记录缺失事实与补做日期；评审与验证证据不得倒填。
- **工具切换遗漏**：M0/M1 场景测试、全量 strict、check_docs（默认 + closure）、导航错误注入和 PR 双 CI 兜底。
- **回滚**：单 PR revert 即可恢复旧规则和工具；无产品运行时状态、无上游文件、无数据迁移。

## ADR 判定

存在被否决备选（保留数字编号+全库 renumber、人工 INDEX 单写、全量元数据迁移、ROADMAP 原路径冻结/重定向等），并约束未来所有批次的编号、冲突处置、导航和路线文档工作方式，触发 ADR 判定①②③；新增 ADR-0024。无新增第三方依赖。

## 提请签认时重点裁决

1. 新定制点和新 ADR 都采用批次命名空间语义 ID；ADR 全部进入全局池，存量功能池 ADR 随规则生效迁移，不再把 ADR 命名治理后置。
2. 接受 M0/M1/M2 分级及 ID-only 机械修复的窄口径免重复签认；任何语义变化仍停等。
3. INDEX 随本批物理删除：批次目录全景用 `docs_report.py`，固定入口并入 `aixcoding/README.md`；有目录微改动纳入，无目录微改动查 GitHub merged PR，不新增留痕义务。
4. 接受复用现有 H1、取消必备类型/简介列，不做历史元数据迁移。
5. ROADMAP 随本批物理删除，不等完整验收或旧分支归档；迁移项由责任人自行跟踪，不保留冻结档案/重定向/替代台账，历史查 Git。
6. 接受 `check_docs.py --closure` 四项闭环门禁、存量缺口封闭清单、微改动“无目录豁免/有目录六件”的增量分流，以及 guard-switches 存量修复作为本批验收项；特性分支 PR 同样闭门。
7. 本批原子切换，不先引入临时的后置 INDEX 清账流程。
