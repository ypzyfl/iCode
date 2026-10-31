# ADR-0016：docs 批次目录单层平铺 batches 与静态导航索引

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-0009 取代）——括号内即后继编号（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py

命名与编号：NNNN-标题.md，取目录现有最大编号+1；编号被引用后不改号；
并行撞号罕见且必然被 git 同名冲突暴露，暴露早期重新编号即可。

ADR 判定 checklist（出 ADR 的门槛，任一"是"；粒度是决策不是功能）：
① 有被认真考虑但否决的备选方案
② 撤销代价高（依赖方向/目录落点/数据格式/对外契约）
③ 约束未来工作模式，后来者会问"为什么"
④ 依赖上游非公开接口或行为（另登记定制清单 anchor）
反面清单（不出）：模块内实现选择、唯一合理路径的照规范执行、纯文档修正。

自包含快照原则：决策节完整记录当时定的机制内容，写定不改；规范演进不回改本文——
重大规则变更出新 ADR，本文标"被取代"。指向规范的引用仅作导航注记
（"本文为决策时点快照；现行以 <规范条款> 为准"），不作为决策内容。

决策更新处理：决策实质变更 → 新建 ADR 取代（背景须引用旧 ADR 并说明"什么变了"），
旧 ADR 仅改头部状态、正文不动、不触发重签；原地修改仅限错别字/链接/背景补充等
非决策性修正。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-01
- 确认意见：无特别意见

> 本文为决策时点快照；现行规则以 `DEVELOPMENT.md §6` 与 `DIRECTORY.md §1/§2/§9` 为准。

## 背景

2026-10-31 团队会议反馈：`aixcoding/docs/` 下每个批次/专项各建一个目录直接平铺顶层，
数量持续增长（当时 18 目录 + 2 根文件），顶层堆积无收敛、缺目录级导航入口。

关键约束：批次 design.md 是**现行效力载体**而非死档案——它是 R2 审批池、定制点登记
对账（`gen_customizations.py --strict`）、MARKER_EXEMPTIONS 豁免依据的持续输入；其中
`batches/agents-md-note/design.md` 承载 C001 现行登记行（落点根 `AGENTS.md`）与 R2 批准表，
`batches/diagnostics/design.md` 承载 C002–C005，`batches/tui/design.md` 为 23 点登记主体。任何布局
方案的扫描面（`_common.find_design_docs` 的 glob）都必须完整覆盖它们。

## 决策

除 `standards/` 与根文件（ROADMAP.md / versioning.md / CHANGELOG.md 预留 / INDEX.md）
外，**全部批次/专项目录单层平铺于 `aixcoding/docs/batches/`**，不在 `batches/` 内再按
任何分类维度分层；治理工具扫描面为精确单层 glob `batches/*/design.md`；新增顶层
`INDEX.md` 作**纯静态导航索引**（目录/类型/一句话简介三列，目录列为相对链接），不承载
状态、PR 号、日期等任何动态事实数值；创建批次目录时同步在 INDEX 登记一行
（DEVELOPMENT.md §6 流程落点）。

## 理由

核心原则：**易变属性不编码进物理路径，分类信息一律放 INDEX 信息列**——路径只承载
"这是一个批次"这一个事实，一次性迁移后永久稳定（新批次落点唯一、完结后零移动）。

被否决备选及死因（R8）：

1. **`archive/` 状态分层**（完结批次迁入归档区）：语义冲突（现行效力载体放 archive
   名不副实）；持续成本（每完结一批 = git mv + 全链引用更新 + CI 验证，永久性重复
   劳动）；"何时算完结"成为新流程判定点。
2. **按技术域分组**（auth 域 / infra 域…）：类别边界模糊且随时间漂移
   （auth-logging 归 auth 还是独立？）。
3. **`batches/<类型>/<feature>/` 多类型层**（features/governance/upgrades/…）：逐批
   归类裁决且未来每批次重复；类型目录增殖；归错类跨类移动 = 弱化版 archive 问题；
   glob 需递归（契约弱化）或枚举前缀（每新增类型改工具）。
4. **`batches/features/` 中间层 + 异类平铺 batches 顶层**：实证缺陷——glob
   `batches/features/*/design.md` 漏扫 batches 顶层目录，`batches/agents-md-note/design.md`
   的 C001 登记行脱管，`--strict` 对账红（本 ADR 背景约束的直接违反）。
5. **仅 INDEX 不分层**：不解决顶层堆积与落点规则（新批次仍落顶层，持续膨胀）。
6. **INDEX 状态列（活跃/已完结）与生成式 INDEX**：状态维度并非团队诉求（2026-10-31
   责任人澄清，系方案演进中被叠加引入的虚构维度）；手工状态列与 ADR-0015 退役
   CUSTOMIZATIONS.md 的双源漂移教训同构；生成式只能产出目录名/链接骨架（零信息量），
   且"提交产物 + freshness 门禁"模式与 ADR-0015 结论冲突。

**为何 `batches/` 内只做一层 + 索引、不再分层**：本决策解决顶层堆积无收敛与目录级
导航入口缺失，**不消除批次目录总数随开发活动的自然增长**（升级批次
`upstream-merge-vX.Y.Z` 等 each-merge 一个，是开发活动的自然产物）——若为视觉分组
再引入类型层，即回到备选 3 的全部死因。单层平铺同时使扫描面契约最精确：
`batches/*/design.md` 恰好覆盖全部承载登记行/R2 表的 design.md。

## 后果

- 新批次落点唯一：`aixcoding/docs/batches/<feature>/`；创建时同步 INDEX 登记
  （DEVELOPMENT.md §6、DIRECTORY.md 判定树已随本决策修订）。
- `batches/` 内目录数持续增长是预期状态，导航靠 INDEX，不再讨论内部分层
  （推翻本决策需新 ADR）。
- 批次 design.md 与根 `AGENTS.md` 等现行效力载体的授权/登记语义不受位置影响；
  R2 审批池与登记对账扫描面经 glob 前缀平移保持严格等价。
- 历史文档中的旧路径按 docs-reorg 批次定案统一机械替换（规范依据：ADR 失效链接
  修正授权 / self-review 记录档 / verification 活文档），迁移前快照锚点为 git tag
  `docs-pre-reorg`。
