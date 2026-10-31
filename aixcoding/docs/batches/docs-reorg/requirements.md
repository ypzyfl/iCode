# 需求：docs 目录分层组织（docs-reorg）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

2026-10-31 团队会议反馈：`aixcoding/docs/` 下每个批次/专项各建一个目录直接平铺在顶层，
数量持续增长（当前 18 个目录 + 2 个根文件；17 个非模板 design.md 中 16 个已签认、
1 个为本批次草案），不便于浏览与定位。核心痛点有二：

1. 顶层堆积的是大量"现行效力载体"（design.md 仍是 R2 审批池、定制点登记对账、
   MARKER_EXEMPTIONS 豁免依据的持续输入）而非死档案——它们不是可清理的归档物；
2. 顶层堆积无收敛机制：新批次（含每次追上游新增的 `upstream-merge-vX.Y.Z`）一律落
   顶层，顶层视图随开发进度持续膨胀。批次目录总数本身仍会增长（开发活动的自然产物，
   本需求不消除它），需要的是不污染顶层的稳定承载 + 导航。

## 目标与非目标

- 目标：
  - docs 顶层收敛且有稳定结构：**除 `standards/` 外全部批次/专项目录统一入住 `batches/`
    平铺**（顶层仅 `standards/`、`batches/` 与根文件），路径一次性迁移后永久稳定
    （新批次落点确定，后续零迁移，不再为任何分类维度增加目录层——分类信息归 INDEX 列）；
  - 提供导航索引 `INDEX.md`（纯静态：一行一目录，类型 + 一句话简介），与 `ROADMAP.md`
    （管路线与进度）分工明确；不承载批次状态、PR 号、日期等任何动态事实数值
    （这些以各批次文档为单一事实源）；
  - 同步改造治理工具（`find_design_docs` 扫描面）、更新全部活引用（代码字符串、
    文档交叉引用、仓外待办）、修订 `DEVELOPMENT.md` §6 与 `DIRECTORY.md` 布局条文。
- 非目标：
  - 不做文档内容清理、合并或删减（历史文档保留原样随目录迁移）；
  - 不做按技术域分组（类别边界会漂移，已在方案对比中否决）；
  - 不改任何上游文件（零 R2 项）；
  - 不移动 `standards/`、`ROADMAP.md`、`versioning.md`（含未来 `CHANGELOG.md` 落点）。

## 用户场景

1. 新成员/AI 打开 `aixcoding/docs/` 想知道"这几十个目录各是什么"：读 `INDEX.md`
   一屏即得（目录 + 类型 + 一句话）；阶段进度与路线读 `ROADMAP.md`，批次验收事实
   读各目录 `verification.md`；
2. 成员检索某批次签认记录：`batches/<feature>/` 目录名与 INDEX 简介列直接对应；
3. AI 按规范开新批次：§6 修订后落点唯一确定为 `aixcoding/docs/batches/<feature>/`，
   治理工具自动覆盖。

## 验收标准

- [ ] `aixcoding/docs/` 顶层目录仅 `standards/` 与 `batches/`（+ INDEX.md / ROADMAP.md /
      versioning.md 根文件），18 个批次/专项目录全部位于 `batches/` 下平铺（无中间分类层）；
- [ ] 四工具本地全绿：`check_docs.py`、`gen_customizations.py --strict`（登记对账
      29 定制点不变）、`check_r2_diff.py`、`check_r3_markers.py`；
- [ ] **R2 审批池等价**：迁移前后各输出一次 `r2_approved_upstream_files()` 的 approved
      集合并逐字比较，完全一致（含 `AGENTS.md` 等 agents-md-note 批准项；本批次零上游
      diff，`check_r2_diff.py` 绿不构成池等价证据）；
- [ ] `aixcoding/tests/` 定制测试套件全绿（夹具随 `find_design_docs` 改造同步）；
- [ ] 全仓复扫旧路径零命中，豁免清单（见 design §4.3）除外——复扫口径：枚举 18 个
      迁移目录名，`aixcoding/docs/<name>/` 与 `aixcoding/docs/<name>`（无尾斜杠）
      两种形式，覆盖仓内全部路径 + 仓外 `temp/aixcoding-todos/` 整目录；
- [ ] `INDEX.md` 落地：18 个目录条目齐全（目录 / 类型 / 一句话简介三列），含与
      ROADMAP 的分工声明，不承载任何动态事实数值（零漂移维护点）；
- [ ] `DEVELOPMENT.md` §6、`DIRECTORY.md`（目录树/判定树/命名表）修订完成，新增布局
      ADR 一篇（编号顺延 standards/adr/）；
- [ ] CI（`aixcoding-tests.yml`，PR 至 main_aixcoding_cli）全绿。

## 开放问题

- ~~`restructure/`、`agents-md-note/`、`docs-reorg/`（本批次自身）是否随迁 `batches/`~~
  已决（责任人 2026-10-31）：全部迁入 `batches/` 平铺，顶层仅留 `standards/` 与根文件——
  该裁决同时修复了"异类留顶层会漏扫 `batches/agents-md-note/design.md` 承载的 C001 登记行"的实证缺陷；
- 历史叙述性旧路径处理原则：design §4.3-G② 已收敛为**统一替换**定案建议（三轮 AI
  评审收敛 + 规范依据闭环：ADR 失效链接修正由 `DEVELOPMENT.md:180` 明示授权、
  self-review 记录档 / verification 活文档按 `:64` 天然跟随现状、R10 豁免收窄至
  17 个 design.md 且机械性可 diff 证明、tag `docs-pre-reorg` 降低溯源成本）——
  待责任人随 design 签认一并终裁。
