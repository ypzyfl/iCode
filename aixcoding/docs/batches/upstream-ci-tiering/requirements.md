# 需求：PR 门禁按需触发分层（零上游改动跳过 Upstream CI）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
>
> 决议留痕（2026-11-12，责任人确认 D1–D5）：README.pypi.md 强制 L2（b1）；manual 跳过 +
> nightly 兜底（b2）；独立批次完整管线 + 新 ADR；七项全量、nightly 不推迟；三细节入档
> （compileall 单评 / nightly 失败可见性 / docs 区口径）。两轮外部 AI 评审收敛，评审意见逐条
> 经本地核实（见 design.md 决策表与验证留痕）。

## 背景与问题

PR #114（catalog-auto-sync 批次）实证：零上游改动——15 个文件全部落在 `aixcoding/` 与
`src/chrys/service/aixcoding/` 定制层——仍全量跑了上游套件约 20 job × 约 11 分钟，纯浪费。

桥接 workflow（`aixcoding-upstream-ci.yml`）现有的唯一按需维度是 **doc-only**（改动全匹配
`\.md$|^docs/|^aixcoding/docs/|^aixcoding/manual/` 即跳过——manual 分支为 2026-11-11 白名单
扩围，评审 F3 修正补记），判定标准错位：应是“**是否影响上游功能**”，而非“是否纯文档”。定制/上游资产归属分流与恒跑轻量合规层（`govern`）已有雏形，缺的是 L2 上游回归
层的按需判定与配套安全网。

### 调查核实的关键事实（本批次的约束前提）

- 定制资产权威口径：`aixcoding/tools/_common.py::is_custom()`（`aixcoding/` 前缀 +
  `src/chrys/{tier}/aixcoding/` + 两个 workflow 的 `CUSTOM_EXACT_PATHS`）——服务 R2/R3
  **所有权治理**；本批次的“上游 CI 影响分类”是不同语义，复用底层路径常量、不共享终判。
- **跳过 L2 会连带走失定制产品代码的静态质量门**：`src/chrys/*/aixcoding/` 的 ruff/format/
  ty/compileall/build/wheel 现状全部由上游 `ci.yml` 承担（DIRECTORY.md §7 明载）；`govern`
  只查根 `aixcoding/`。补位是本批次必做项，不是风险备注。
- 上游套件对定制层的耦合面：直接依赖 2 处（`tests/app/test_installer.py`、
  `test_uninstaller.py` import `chrys.kernel.aixcoding.command_migration`）；间接为上游源文件内的
  定制注入点（运行时执行定制代码）——2026-11-12 实测为 **31 个上游文件 / 52 处** `# AIxCoding`
  标记（src/chrys 下排除定制目录、含行尾注释口径；旧计数 19 为 2026-10-23 时点，随批次增长已
  过时，评审 F2 修正）。
- `workflow_call` 只能整体调用/不调用上游 `ci.yml`；fork 一份 ci.yml 已被否决（双份维护必
  漂移）；workflow 级 paths-ignore 已被否决（required check 为 job 级 run 名，整体 skip 会永久
  卡合并）——跳过决策必须在 job 级（filter + 恒跑 gate）。
- 桥接现状无 push 触发，PR 时是上游套件的唯一防线；合并后无任何兜底重跑。
- `README.pypi.md` 是 wheel 元数据来源（pyproject.toml readme 键，check_wheel 核对描述非空）；
  `aixcoding/manual/` 经 force-include 进 wheel 且 check_wheel 逐文件核对——user-manual 批次
  verification 在案“等桥接自然覆盖”为唯一遗留缺口，manual 跳过后该口径必须同步修订。
- `docs/` 实测 66 个 md + 1 个 `index.yaml`（文档导航索引数据），无脚本/构建文件。

## 目标与非目标

- 目标：
  1. **L2 按需**：`filter` 的判定由 `doc_only` 升级为 `upstream_touched`（影响分类器
     `needs_upstream_ci()` 语义独立）；改动全部落在定制资产 ∪ 纯文档豁免集 → 跳过整套上游
     矩阵，其余全量。
  2. **fail-closed 强化**：diff 加 `--no-renames`（防上游文件移入定制目录的 rename 折叠
     误判）；grep 退出码显式区分（1=无匹配可跳过，2=执行错误必须失败）；gate 状态机仅接受
     `(touched ∧ ci=success) ∨ (¬touched ∧ ci=skipped)`，filter 失败/输出缺失/cancelled 均
     不得直绿。
  3. **L1 质量门补位**：定制门扩展覆盖 `src/chrys/*/aixcoding/` 的 ruff check/format；ty 补位
     （平台覆盖取舍在 design 明示——上游现状三 OS core shard 各跑一次）；compileall 单独评估
     （上游其首要目的为性能预热，补位仅需编译定制产品路径，秒级，倾向采纳）；build/wheel 不
     补位，靠强制触发 + nightly。
  4. **自动兜底**：nightly schedule 对 `main_aixcoding_cli` 当前合并树跑完整上游套件 +
     `workflow_dispatch` 手动全量（发布/升级前、怀疑漏判时用）；两者均绕过 diff 判定、不读
     `pull_request.base.sha`。配套失败可见性机制（通知通道与日常观察责任在 design 定）——
     nightly 只保证“最迟约 24h 内再次执行全量验证”，不等于 24h 内发现。
  5. **强制全量清单**：`README.pypi.md`（b1）、桥接 workflow 自身（真实 workflow_call 路径必须
     被验证）、分类器及其直接数据源（防“新判定器判自己无需验证”）、workflow 白名单仅认精确
     登记路径（不收宽 `aixcoding-*.yml`）。
  6. **manual 按 b2**：纯 `aixcoding/manual/` 改动跳过 L2，nightly 兜底 build/wheel；修订
     user-manual 批次“等桥接自然覆盖”遗留口径为“等 nightly 兜底”，首次 nightly 实际覆盖后
     回填验证结果。
  7. **分类器实现**：优先消除双实现——实施首步实测 `ubuntu-slim` runner 自带 `python3`，可用则
     stdlib 分类器单实现（复用 `_common` 路径常量，单元测试直接覆盖同一实现）；不可用则保留
     shell 判定 + Linux CI 一致性门禁（正反例与边界路径全覆盖）。
  8. **测试矩阵**：两轮评审反例全收录——rename 折叠、桥接自身改动、新增其他 `aixcoding-*.yml`、
     `README.pypi.md`、manual、`docs/index.yaml`（oracle=跳过，受信任文档区现口径延续并显式
     留痕）、`docs/` 下脚本/配置/构建数据假想例、未知路径（`scripts/`、`locales/`、
     `hatch_build.py`、环境文件、其他 workflow）一律全量 fail-closed。
  9. **文档联动**：新 ADR（显式修订 ADR-0004 / DIRECTORY §7 的“产品定制代码 → 上游 ci.yml
     全套”覆盖关系）+ upstream-ci、ci-gate 批次 design 交叉引用 + user-manual 口径修订。
- 非目标：
  - guard job 按需化（三 OS 部署验证是其核心价值，收益有限，留待实测痛点再独立批次）。
  - 上游套件内部 shard 级按需（机制约束，见调查事实）。
  - merge 后每次 push 全量（抵消 runner 节省，且不能阻止问题合并）。
  - 上游 `ci.yml` 及任何上游文件改动（零上游改动原则不变）。
  - 影响分类器与 `is_custom()` 合流（保持两套终判语义独立）。

## 用户场景

1. **纯定制批次 PR**（如 catalog-auto-sync 类）：L0 合规恒跑 + L1 定制测试与静态门，L2 跳过，
   gate 直绿，门禁等待从约 12 分钟降到约 3–4 分钟；上游回归由 nightly 兜底。
2. **上游文件改动 PR**（追上游升级、定制注入点改动、环境文件变更）：L2 全量，与现状一致。
3. **手册批次 PR**（高频、低风险）：跳过 L2；build/wheel 验证由 nightly 覆盖，失败有通知与
   观察责任。
4. **发布前/升级前/怀疑分类漏判**：`workflow_dispatch` 手动触发全量，无需构造假 PR。

## 验收标准

- [ ] 纯定制改动 PR：`filter` 判 `upstream_touched=false`，`ci` 不拉起任何上游 job，gate 直绿
      （required check 语义不变）。
- [ ] 触及上游文件任一（`src/chrys/` 其余、`tests/`、`scripts/`、环境文件、其他 workflow、
      `README.pypi.md`）：L2 全量执行。
- [ ] 上游文件 rename 进定制目录：源路径参与判定，不误判为纯定制。
- [ ] filter 执行错误、空 diff、输出缺失、ci cancelled/failure：gate 失败（fail-closed）。
- [ ] 纯定制 PR 中 `src/chrys/*/aixcoding/` 代码的 ruff/format/ty（及若采纳的 compileall）在
      定制门内实际执行并有失败证据能力。
- [ ] nightly 按计划对主干合并树全量执行；workflow_dispatch 可手动全量；nightly 失败的可见性
      机制经实测确认。
- [ ] 分类器测试矩阵全绿（目标 8 全部案例）；若为双实现，一致性门禁在 Linux CI 生效。
- [ ] manual-only PR 跳过后，首次 nightly 对主干完成 build/wheel 覆盖，结果回填 user-manual
      verification。
- [ ] 新 ADR 合并；DIRECTORY §7、upstream-ci/ci-gate/user-manual 三处文档修订完成。
- [ ] 一个真实纯定制批次 PR 在本门禁下的端到端验证（doc 混合代码的真实场景，复刻 PR #114
      形态）。时点：本批合并后以临时验证 PR 执行——本批 PR 自身触及桥接 workflow 强制全量，
      无法自证跳过路径（评审 F4；方法与步骤见 design 验收时点说明与 test-plan）。

## 开放问题

- `ubuntu-slim` 是否自带可用 `python3`：实施首步实测，决定分类器单实现/双轨（design 留痕）。
- ty 补位的平台覆盖取舍（单 Linux vs 多 OS）：design 定。
- nightly 失败通知通道与日常观察责任的具体形态：design 定。
- `docs/` 受信任文档区口径在 ADR/design 中的显式表述与 index.yaml 案例 oracle 定稿：design 定。
