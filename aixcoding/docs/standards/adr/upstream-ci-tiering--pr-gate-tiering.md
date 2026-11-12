# ADR-upstream-ci-tiering--pr-gate-tiering：PR 门禁按需触发分层

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

桥接 workflow（`aixcoding-upstream-ci.yml`，upstream-ci 批次）让 PR 至 `main_aixcoding_cli`
能跑上游全套测试，但其唯一按需维度是 doc-only 形式判定。PR #114（catalog-auto-sync）实证：
零上游改动的纯定制批次也全量跑约 20 job × 约 11 分钟，runner 成本与门禁等待双浪费。
同时 `DIRECTORY.md §7` 与 ADR-0004 建立的原覆盖关系——“产品定制代码 → 上游 ci.yml 全套”——
意味着定制产品代码的静态质量门（ruff/ty/compileall）与 build/wheel 探测也全挂在上游套件上，
按影响面跳过上游套件必须同步解决质量门归属与合并后兜底，否则等于开门禁漏洞。

## 决策

1. **PR 门禁分三层**：L0 基础合规层（`govern` 治理检查，恒跑）；L1 定制功能层（定制测试
   双 OS、guard 三 OS，恒跑；`govern` 补位定制产品静态检查）；L2 上游回归层（桥接上游
   `ci.yml` 全套，按影响面按需触发）。判定标准是“**是否影响上游功能**”，不是“是否纯文档”。
2. **影响分类独立于所有权分类**：`aixcoding/tools/ci_impact.py::needs_upstream_ci()` 与
   `_common.is_custom()`（R2/R3 治理）复用底层路径常量但终判语义独立。规则优先级：
   **FORCE**（恒全量：`README.pypi.md`、桥接 workflow 自身、分类器及其数据源 `_common.py`）
   → **DOC**（跳过：`docs/` 受信任文档区、其余 `*.md`）→ **CUSTOM**（跳过：`aixcoding/`
   含 manual、`src/chrys/{tier}/aixcoding/`、精确登记的定制 workflow）→ **默认全量**
   （一切其他与未知路径，fail-closed）。空 diff、分类器异常、输出缺失均 fail-closed；
   diff 必带 `--no-renames`（rename 折叠防御）。
3. **分类器单实现**：stdlib Python 脚本即 CI 实际消费的唯一实现（runner python3 优先、
   仓库既有 pin 的 setup-python 兜底），禁止 shell 镜像轨道；单元测试直接覆盖该实现。
4. **定制产品静态门归属 L1**：`govern` 对 `src/chrys/{tier}/aixcoding/` 执行 ruff
   check/format、ty（单 Linux runner 显式 `--python-platform` 三平台各跑一次，定制层含
   DPAPI/win32 平台分支）、compileall。build/wheel 不补位：由 FORCE（`README.pypi.md`）
   与 nightly 覆盖；`aixcoding/manual/` 改动跳过 L2（高频低风险手册接受延迟验证），其
   build/wheel 验证由 nightly 兜底，user-manual 批次“等桥接自然覆盖”遗留口径同步修订为
   “等 nightly 兜底，首次覆盖后回填”。
5. **自动兜底**：nightly schedule（每日 UTC 18:00，北京 02:00）对 `main_aixcoding_cli`
   当前合并树跑完整上游套件 + `workflow_dispatch` 手动全量；两者绕过 diff 直接全量。
   **可见性责任**：责任人每日/合并前查看 Actions 结果，nightly 失败须当日处置或登记挂账；
   “≤24h”仅指再次执行全量验证的间隔上界，不等于发现上界。
6. **显式修订 ADR-0004 与 DIRECTORY §7 的原覆盖关系**：ADR-0004 以 append-only 注记
   （2026-11-01 先例），DIRECTORY §7 作活文档直接改写为分层口径。

## 理由

- 影响面判定直接表达门禁目的；doc-only 形式判定把“改了定制代码”与“改了上游代码”混为一谈。
- 所有权≠影响面（评审实证：`CUSTOM_EXACT_PATHS` 精确两项 vs 草案 `aixcoding-*.yml` 宽放行
  即漂移实例；manual/README.pypi.md 是 fork 资产却影响 wheel），故终判语义必须独立。
- 静态门补位是跳过的前置条件而非可选项：不补位则纯定制产品 PR 连 ruff/ty 都失去。
- nightly + dispatch 提供有界的自动再验证与随时可用的手动通道；merge 后每次 push 全量会
  抵消节省且不能阻止问题合并，不采用。
- 单实现消除双轨漂移与一致性门禁的长期维护成本；setup-python 兜底成本约 10 秒，可忽略。

被否决备选：

- **workflow 级 paths-ignore**：required check 为 job 级 run 名，整体 skip 会永久卡合并
  （2026-10-28 评审先例）。
- **fork 一份 ci.yml 做 shard 级按需**：双份维护必漂移（upstream-ci design 已否决）；
  workflow_call 只能整体调用。
- **merge 后每次 push 全量**：见上。
- **直接镜像 is_custom()**：所有权/影响面混同（决策 2）。
- **shell + Python 双实现**：漂移风险与一致性门禁维护成本（决策 3）。
- **guard 按需化**：三 OS 部署验证是其核心价值，收益有限，留待实测痛点独立批次。

## 后果

- 纯定制 PR 的上游回归从“合并前阻断”降级为“合并后 nightly 再验证”（执行间隔上界约 24h）；
  合并前覆盖由 L0/L1 与 FORCE 清单保证。这是有意接受的残余风险（上游套件对定制层的耦合面：
  2 处直接 import 测试 + 上游注入点运行时执行定制代码）。
- **维护义务**（后续所有批次）：新增影响上游构建/套件执行的 fork 资产须登记进 FORCE；
  新增定制 workflow 仅在精确登记 `CUSTOM_EXACT_PATHS` 后才可跳过；`docs/` 若出现真实
  脚本/构建文件须回炉修订受信任文档区口径；仓库默认分支若不再是 `main_aixcoding_cli`，
  nightly/dispatch 静默失效，必须回炉本决策。
- gate 名（`AIxCoding upstream gate` / `AIxCoding quality gate`）与恒跑语义不变，分支保护
  零改动。
- user-manual 批次遗留缺口改由 nightly 承接并回填；nightly 观察责任随本决策生效。
