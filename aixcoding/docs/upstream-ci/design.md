# 设计：上游 CI 桥接（upstream-ci / aixcoding-upstream-ci.yml）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-26
- 确认意见：已知会增加约11-12分钟测试时间，导致PR提交需要多等11-12分钟，但是为了质量，在主分支上这是值得的。

## 方案概述

单文件桥接 workflow `.github/workflows/aixcoding-upstream-ci.yml`：仅 PR 至 `main_aixcoding_cli` 触发，单 job 经 `uses: ./.github/workflows/ci.yml`（workflow_call）复用上游 CI 全套（lint + 多 OS 测试分片 + architecture），不改 `build_ref`（ci.yml 内部 checkout `inputs.build_ref || github.sha`，workflow_call 场景下即桥接触发 commit=PR merge ref，语义正确）。已核实：ci.yml 无 `secrets.` / `environment:` 引用，桥接无需 `secrets: inherit`。

背景：上游 ci.yml 触发条件为 `pull_request: branches: [main]`，PR 目标是 `main_aixcoding_cli` 时上游全套不会跑；阶段三迁入会触碰 `src/chrys` 源码，需要上游全量回归防"改坏上游行为"。本桥接把 DIRECTORY.md §7"产品定制代码 → 上游 ci.yml 全套"的目标状态在开发主线上落实。

## 备选方案对比

| 决策点 | 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| 复用方式 | workflow_call 桥接（cd.yml 同机制） | 零改动上游文件；上游 CI 演进自动跟进 | 多一个 ~30 行文件 | **采用** |
| | 改上游 ci.yml 的 `branches: [main]` | 无新文件 | 动上游文件（R2 报批 + 标记注释 + 每次同步 main_iCode 高冲突面）；push 触发仍缺 | 否 |
| | 复制一份 ci.yml 为定制版 | 独立可控 | 双份维护，上游 CI 演进必漂移 | 否 |
| 触发范围 | 仅 pull_request（对齐上游惯例） | PR 门禁语义一致；合并 push 不重复烧 runner | fork 直接 push 合并后无 CI 记录（PR 已验证，风险低） | **采用** |
| | PR + push 双触发（对齐 aixcoding-tests.yml） | 合并后主干也有全量记录 | 同一提交跑两遍，runner 成本翻倍 | 否 |
| paths 过滤 | 无过滤（对齐上游） | 门禁不开洞；纯 aixcoding 改动也全量验证 | 只改文档的 PR 也烧全套矩阵 | **采用**（先观察成本，痛点出现再收窄） |

ADR 判定：机制级决策（workflow_call 复用、触发对齐上游）均无新的长期约束形态，属 ci-gate（ADR-0004）既定"上游目录内定制文件"框架下的执行层选型——不出新 ADR。

## 上游改动清单（R2；无上游改动则删除本节）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `.github/workflows/aixcoding-upstream-ci.yml` | 新建桥接 workflow（GitHub 硬约束：workflow 必须位于上游目录 `.github/workflows/`）：PR 至 main_aixcoding_cli 触发，workflow_call 复用上游 ci.yml | 约 30 | 不加（同 ci-gate 口径：CUSTOM_EXACT_PATHS 已收录为定制资产，非上游文件改动处） |

R1 自查：GitHub 平台硬约束下无其他落点；文件为纯新增，上游零感知。真正的门禁豁免来自 `CUSTOM_EXACT_PATHS`（`aixcoding/tools/_common.py`），本表为流程层批准留痕（双轨自洽，同 ci-gate 先例）。本批无新增第三方依赖（本地 `uses: ./.github/workflows/ci.yml` 免 pin，守卫 `test_workflow_action_pins.py` 明确豁免本地路径）。

## 对上游隐式行为的假设

| 假设 | 依赖方式 | 失效表现 |
|---|---|---|
| 上游 ci.yml 持续保留 `workflow_call` 触发器且 job 无 secrets 引用 | 桥接 job `uses` 复用 | 上游删除该触发器 → 桥接 job 配置错误，PR 检查失败（显性，fail-fast）；引入 secrets → 调用未传 secrets 的 job 直接失败（显性） |
| ci.yml 内部 checkout 语义（`inputs.build_ref \|\| github.sha`）在 workflow_call 下取调用方 commit | 不传 build_ref | 上游重写该表达式 → checkout 错 ref，测试跑错提交（需同步评估传显式 build_ref） |

无产品代码 anchor（纯开发资产，无运行时行为）。

## 定制点登记预告

不适用：纯开发资产（CI workflow），无上游接触面、无运行时行为，不入 CUSTOMIZATIONS.md（同 ci-gate / devtools 口径）。

## 风险与最坏情况

- **GitHub Actions 远程环境本批不可本地复现**：本地跑守卫测试（action pins / permissions / R2 / R3 / 清单幂等）+ YAML 人工审，首跑验证后置（PR 后观察，失败即修，最坏删除 workflow 文件回滚）；
- 首跑可能爆红：上游全量测试首次在含定制改动的分支上跑，Smart Test 射程外的远端消费者问题会暴露——属预期收益（提前发现，而非阻塞）；处置走正常修复流程；
- runner 时长：多 OS 分片矩阵，PR 总等待 ≈ 上游 ci.yml 关键路径——上游仓库（openJiuwen-ai/iCode）实测成功 run 11 分 02 秒 / 11 分 35 秒、失败 run 16 分 28 秒（2026-10-26 GitHub API 查询）；fork 侧 aixcoding-tests.yml 实测 38-49 秒（uv 缓存热），两 workflow 并行互不阻塞；若成为痛点，按备选表预留的收窄路径加 paths 过滤；
- 回滚：删除 `.github/workflows/aixcoding-upstream-ci.yml` 及 `CUSTOM_EXACT_PATHS` 对应条目即完全回滚。

## ADR 判定

四问：①否决备选——操作层选型已记上表，机制级无新否决；②撤销代价——单文件可即删，低；③约束未来工作模式——无新约束（复用机制即上游惯例）；④依赖上游非公开接口——无（workflow_call 与 ci.yml 的 on 配置均为公开接口）。结论：不出 ADR。
