# ADR-ci-gate-domains--check-domains-model：检查域模型取代数字分层术语

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-<batch-slug>--<decision-slug> 取代）——括号内即后继 ID（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：无特别意见

> 本文为决策时点快照；现行规则以 `DIRECTORY.md §7` 与 `DEVELOPMENT.md §6` 为准。

## 背景

ADR-upstream-ci-tiering--pr-gate-tiering 建立了 L0/L1/L2 数字分层与上游域按需触发。后续把
定制测试/guard 按需化时暴露模型缺陷：数字层号把"触发策略"（恒跑/按需）与"职责域"（合规/
测试/安全/上游）两个正交维度绑死——按需粒度细于层时，被迫在"扩层重编号"（全库改口径）与
"层内嵌套"（层概念空化）之间二选一。PR #122 实测纯文档 PR 的 test+guard 恒跑约 3 分钟，
而其射程只有恒跑的合规检查（26s）。

## 决策

1. **门禁体系表述为四个检查域 + 两个聚合 required check**。"检查域"回答做什么/何时触发，
   "聚合门"回答分支保护等哪个结果，两者不混用；域名描述**被运行的检查套件**，不描述只有
   哪个目录的改动才触发它：

   | 检查域 | 触发策略 | 聚合去向 |
   |---|---|---|
   | `compliance` | 恒跑 | `AIxCoding quality gate` |
   | `aixcoding-tests` | 按射程 | `AIxCoding quality gate` |
   | `guard-deploy` | 按射程 | `AIxCoding quality gate` |
   | `upstream` | 按影响面 | `AIxCoding upstream gate` |

   两个 required check 名称及实现机制不变；分支保护零改动。
2. **旧分层术语映射**（旧 ADR 按快照原则不回改）：

   | 旧表述 | 新表述 | 实质变化 |
   |---|---|---|
   | L0 | `compliance` | 更名 |
   | L1 的 test 部分 | `aixcoding-tests` | 拆分为独立域并按需触发 |
   | L1 的 guard 部分 | `guard-deploy` | 拆分为独立域并按需触发 |
   | L2 | `upstream` | 更名 |
3. **射程规则单点登记于分类器**（`aixcoding/tools/ci_impact.py`，域集合输出、非互斥并集，
   空集规则永不移除已贡献域）；未知路径对三个按需域 fail-closed（已知豁免必须显式登记且有
   代码级依据）；测试域的静态契约测试消费面由 AST 双形态扫描测试自动守护（人工枚举连续
   两轮漏判的教训：`_read(...)` 与 `REPO_ROOT / "..."` 两种消费形态各漏一批）。
4. **兜底层次**：定制双域 = push 至主干恒全跑（每次合并即全量）+ nightly（空窗补充、runner
   环境漂移、时间相关退化、push run 失败/取消后的独立复测）；upstream = nightly/dispatch
   唯一防线（24h 执行上界 + 观察责任）。nightly 与 push 均为合并后兜底，不替代 PR 保守触发；
   concurrency 按 `ref + event_name` 分组避免 push 与 nightly 互相取消。

## 理由

- 数字编号表达严格层级/顺序/成熟度递进，而检查域间是并行命中、分别聚合的关系——编号造成
  语义误导（L2/L3 像依赖或严格度递进）与标识不稳定（插入/拆分即重编号）。
- 语义命名与既有 gate/check 名、测试套件身份对齐，可搜索、自释；域名与目录耦合（aixcoding-tests
  ↔ `aixcoding/tests/`）耦合的是"测试套件身份"，是特性。
- 未知路径 fail-closed 不增加 PR 总等待（upstream 全量已是关键路径，定制双域并行加跑约 3 分钟），
  却消除新目录/新资产类型在 PR 阶段的检查缺席。

被否决备选：四层数字重编号（churn 全库）；三层 + L1 层内射程（层概念空化）；把 L1 并入 L0
（稀释恒跑秒级不变量）；定制域白名单跳过未知路径（push 兜底是合并后检测，不能替代合并前预防）。

## 后果

- 纯文档 PR（除"文档即验证输入"9 文件例外）总门禁等待约 3 分钟 → 约 1 分钟。
- **维护义务**：新增影响定制测试/guard 部署的资产须登记分类器射程；新增静态契约测试消费仓库
  文件由 AST 扫描测试自动拦截（未登记即红）；新豁免须 design 修订并附代码级依据；新增检查域
  登记四件事（职责/触发射程/聚合去向/非 PR 策略）即可，无需重编号。
- 仓库默认分支不再是 `main_aixcoding_cli` 时，定制域 nightly/dispatch 静默失效，须回炉本决策
  （与 upstream 域 ADR 同款条款）。
- "文档即验证输入"例外清单（9 文件）由分类器常量与 F6 扫描测试共同守护；语义变更走 design
  修订重签。
