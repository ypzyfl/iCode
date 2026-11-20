# 设计：定制功能日志覆盖补全（logging-coverage）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-20
- 确认意见：无特别意见

## 方案概述

六模块日志补全，全部改动落在 9 个定制层文件、零上游文件改动、零新依赖：auto-update 四文件从 `getLogger(__name__)`（`chrys` 树，不进定制卷）迁入 `aixcoding` 双卷体系（检查失败打点经评审修正落 client.py 失败分支）；skills 目录定制按方案 B 在 `skill_paths.py` 函数内部打点、全 detail-only（上游 `adapter.py` 的吞错 except 保持原样）；guard 安装器补打点——护栏自身状态 detail-only（对用户不可见原则），"备份并重置用户手写配置"单点升主通道 WARNING（2026-11-19 改判）；model catalog 按责任人裁决仅两处"用户自定义模型被覆盖/删除"事件升主通道 WARNING 双写；config 加载与 startup task 的 stderr 警告补主通道双打（stderr 保留）。不引入新机制——propagate/panel 解耦（批次②）、合并工具（批次③）均不在本批。

改动文件与预估行数（2026-11-19 基线 098b66f1，行号随实施可能微移）：

| 文件 | 改动 | 预估行数 |
|---|---|---|
| `src/chrys/app/aixcoding/update/flow.py` | 迁树 + 四打点（确认 INFO / 跳过 INFO / 检查失败 WARNING 频控 / 流程失败 detail） | ~15 行 |
| `src/chrys/app/aixcoding/update/runner.py` | 迁树：wrapper 启动失败主通道 ERROR 双写；启动成功 detail | ~8 行 |
| `src/chrys/service/aixcoding/update/client.py` | 迁树：成功路径 debug → `aixcoding.detail.update` 中文化；**失败分支（超时/网络/状态/解析）升主通道 WARNING 双写**，204/304"无更新"不打 | ~16 行 |
| `src/chrys/service/aixcoding/update/state.py` | 迁树：2 处 debug → detail，中文化 | ~5 行 |
| `src/chrys/service/aixcoding/skill_paths.py` | 新增 detail 域 logger + 成功清单 detail + 函数级异常 detail（含栈）+ re-raise + `_team_skill_dirs` OSError 区分 | ~18 行 |
| `src/chrys/kernel/aixcoding/guard/guard_install.py` | 新增 detail logger（护栏自身）+ `aixcoding.guard` 公共 logger（仅 `_replace_unparsable` 单点）+ 四落点打点（中文，行级 RUF001 noqa） | ~18 行 |
| `src/chrys/service/aixcoding/models/catalog.py` | 重新启用 `_log`（`aixcoding.catalog`）+ 两处主通道 WARNING 双写 + :84 定调注释修订 | ~10 行 |
| `src/chrys/service/aixcoding/config/loader.py` | `_warn` 内部补主通道 WARNING + detail 双写（stderr 保留） | ~8 行 |
| `src/chrys/app/aixcoding/startup/__init__.py` | :32 task 失败补主通道 WARNING + detail 双写（stderr 保留，行级 noqa） | ~4 行 |

配套测试：新增 `aixcoding/tests/` 路由测试（钉域 logger 名、卷归属、频控、双写、主通道 PII 嗣兵），另订 test-plan。

## 域命名与 logger 形态定案

| 域 | 主通道 logger | detail logger | 形态 |
|---|---|---|---|
| auto-update | `aixcoding.update` | `aixcoding.detail.update` | 直写字面名 + 本地 `_DETAIL_LEVEL = 5`（批次① session.py/catalog.py 零依赖先例 + 六域全层一致性；非 tier 边界强制——app 层本可依赖 kernel 的 diagnostics，评审 S5 修正理由表述） |
| skills | **无**（2026-11-19 裁决全 detail-only） | `aixcoding.detail.skills` | 同上 |
| guard | `aixcoding.guard`（仅 `_replace_unparsable` 单点） | `aixcoding.detail.guard` | 同上 |
| catalog | `aixcoding.catalog`（重新启用） | `aixcoding.detail.catalog`（既有） | 既有形态延续 |
| config | `aixcoding.config` | `aixcoding.detail.config` | 同上 |
| startup | `aixcoding.startup` | `aixcoding.detail.startup` | 同上 |

不用 `logging_support.get_logger()` 工厂：直写字面名先例已裁决（批次①开放问题定案），模块级零依赖、pyc 加载期即安全。

## 逐条定案

### ① auto-update 迁树

四文件的 `logger = logging.getLogger(__name__)` 全部替换为域 logger；事件与通道：

| 落点 | 事件 | 主通道 | detail |
|---|---|---|---|
| `runner.py:150` | wrapper 启动失败 | ERROR「自动更新启动失败：更新助手未能启动，本次不会退出程序。」 | 同文案 + 异常栈 |
| `runner.py:152` | wrapper 已启动 | — | 「更新助手已启动（pid %s）：%s」（argv 技术细节仅 detail） |
| `flow.py` CONFIRM 分支（`:229-231` `_start_update` 内） | 用户确认更新 | INFO「已确认自动更新，程序即将退出并安装新版本。」 | 同文案 + 版本号 |
| `flow.py` SKIP 分支（`:234-235` `mark_skipped` 后） | 跳过版本 | INFO「已跳过版本 %s，不再提醒。」 | 同文案 |
| `flow.py:275`（`work` 内） | `asyncio.run` 包装层罕见异常 | — | 「更新检查任务异常。」+ 栈 |
| `client.py` 失败分支（`:180` 参数不可构造 / `:197-198` 超时 / `:200-208` 网络错误 / `:163` 异常状态码 / `_parse_response` 解析失败） | **更新检查失败**（用户最常见：离线/网络抖动） | WARNING「自动更新检查失败，本次跳过。」（统一文案，原因仅 detail） | 同文案 + 各分支技术原因 |
| `client.py:161-162`（204/304） | 无更新（正常） | —（**不打**——None 语义混合"无更新"与"失败"，主通道打点必须落失败分支、不能落 `_flow` 的 None 汇聚点，否则"已是最新版"被误报为失败） | — |
| `client.py` 成功路径（`:189/:209` 等） | manifest 请求/响应细节 | — | 中文化 detail |
| `flow.py:199` | 更新流程整体失败 | —（用户可能从未见过更新框，无感） | 「自动更新流程失败。」+ 栈 |
| `state.py:105,154` | state 读写失败 | — | 中文化 detail |

依据：`_start_update` 失败已有 TUI notice（`flow.py:254` `_LAUNCH_FAILED_NOTICE`）——主通道 ERROR 是跨 UI 场景留痕而非替代；CONFIRM/SKIP 是用户决策动作（§9 用户功能事件）。

**检查失败无频控**（评审二轮一之连带，实证）：`_flow` 中 `found is None → return`（`:245-246`），检查失败后整个 flow 退出——**进程内至多发生一次**，无"多次 fetch 刷屏"场景（原"while 循环内多次 fetch"担忧实为"检查成功→用户 skip→24h 后再查"，与检查失败无关）；初稿 once 频控删除。

**与 catalog 同步失败 detail-only 的一致性论证**（评审二轮二，2026-11-19 责任人裁决维持主通道）：两者产品定位不同——**update 是用户想要的功能**（用户关心新版本），检查失败时用户希望知道并可报工单处理，属用户功能事件；**catalog 同步是强制性基础设施**（模型列表仍可用、功能不缺失），且产品策略上尽量不让用户知道"模型同步"存在，故同步失败归技术事件。通道差异是定位差异的正确映射，非不一致缺陷。

### ② skills（方案 B，`adapter.py` 零改动）

`skill_paths.py` 新增域 logger 与打点：

- **成功清单**：`cwd_aixcoding_skill_paths` / `user_aixcoding_skill_paths` 返回前，结果非空时 detail 各一条：「已登记 aixcoding 技能根目录（工作区/用户）：%s」——空结果（开关关闭/无目录）不打；
- **异常路径**（2026-11-19 责任人裁决：全 detail-only）：两函数体整体包 `try/except Exception`：detail「读取 aixcoding 技能根目录失败。」+ 栈（**每次记**——detail 卷自包含优先），然后 **`raise`**——保持 `adapter.py:296,305` 既有吞错行为与语义零变化。不设主通道打点（评审二轮三之 1：函数体几乎不抛异常——toggle 判断与 `Path.resolve()` 均不抛，该路径触发面近乎零；真缺口"目录枚举失败"由 `_team_skill_dirs` 的 detail 打点覆盖，主通道 WARNING 语义与其脱节）；
- `_team_skill_dirs` 的 `except OSError`（预期容错路径，docstring 明示 broken container 不阻塞）：**区分常态与异常**（评审二轮三之 2）——`FileNotFoundError`（用户从未创建 team-skills 目录，常态）静默不记；其余 OSError（`PermissionError` 等，目录在但读不了）记一条 detail「团队技能目录枚举失败：%s」，不进主通道。

方案 B 的打点位置在 adapter 吞错**之前**（函数内先打再抛），日志必然落卷；adapter 侧既有 debug 语句不动（其记录机会被上游 logger 吞掉成为无害冗余，改它即触上游接触面，不值）。

### ③ guard（护栏自身 detail-only；备份重置用户配置单点公共）

`guard_install.py` 新增 `_detail_log = logging.getLogger("aixcoding.detail.guard")` 与 `_log = logging.getLogger("aixcoding.guard")`（后者**仅** `_replace_unparsable` 单点使用），全中文（行级 RUF001 noqa，见 R13 节）：

| 落点 | 事件 | 主通道 | detail 文案 |
|---|---|---|---|
| `:146-147`（missing assets raise 前） | 规则包资源缺失 | — | 「护栏规则包资源缺失：%s」 |
| `:158-160`（fresh install） | 首次安装 | — | 「首次安装安全护栏：模板写入 %s。」 |
| `_replace_unparsable` 调用路径（`:168/172/174`） | 既有配置无法解析→**备份并重置用户手写配置** | **WARNING**「检测到无法解析的 hooks 配置，已备份至 %s 并以安全护栏模板重置；原配置可从该备份恢复。」 | 同文案双写 |
| `:176-182`（merge 完成） | 更新/幂等重装 | — | 「安全护栏已就绪（合并进既有 hooks 配置；备份 %s）。」——"已就绪"同时覆盖实际变更与幂等无变化两种情形（评审 S3：不用"已更新"，幂等重装每次启动并无变更） |

幂等重装每次启动走 merge 路径产生一条 detail：detail 卷本为全量，接受。`orchestration/startup.py:233` 上游兜底英文 WARNING 保留不动（覆盖 import 失败等函数体打点够不着的场景）。通道口径（两轮裁决终态）：护栏是基础设施，其**自身状态**（安装/更新/幂等/缺失）对用户不可见——仅 detail；**例外**（2026-11-19 责任人改判，两轮 AI 评审一致建议）："备份并重置用户手写 hooks 配置"是**覆盖用户资产**（用户手写的 hook 配置消失，与 catalog 覆盖/清空同类，§9 用户功能事件），升主通道 WARNING 双写——"护栏不可见"原则约束护栏自身状态，不外延到"用户配置被改动"事件；备份文件 `.pre-guard` 保留可恢复性，WARNING 文案含恢复指引。

### ④ model catalog 两处升主通道

重新启用 `_log = logging.getLogger("aixcoding.catalog")`（批次① D 项启用、environment-config 随退役 env 机制移除后首次恢复），仅两处：

- `:1023` 覆盖警告：`_log.warning("以下自定义模型与后端模型 id 相同，已被后端版本覆盖：%s。", _join_bounded(overwritten))` + 既有 detail 语句保留（双写）；`_join_bounded` 对 join 结果做长度截断（评审 S4：防超长自建模型 id 刷屏，阈值实施定，超限以"等 N 个"收尾）；
- `:986` 清空重建（`upgrade_clear` 块内）：`_log.warning("检测到旧版无标记模型目录；已清空 %d 个配置文件，本次按后端目录重建。", cleared)` + detail 双写。

不升主通道的既有项（维持 detail-only）：`:997` 发布失败（raise 为内部控制流，调用方按"已在抛出点打点"口径静默降级，用户无感——已核实；产品定位：模型列表仍可用、用户不应感知同步存在，与 update 检查失败的通道差异见 ① 节论证）；`:1013` 应用成功（F4 列表自身即反馈，非 §9 用户功能事件）。频控判定：覆盖警告每次同步至多一条且仅 id 冲突时触发；清空重建为一次性迁移（第二次同步起 `server_owned` 非空不再触发）——均无需频控。且覆盖警告**持续冲突持续提醒是有意取舍**：用户在改 id 前每次同步都应被提醒（与 update 检查失败"进程内至多一次"不同——此处是跨同步周期的"未解决状态重申"）。

头部定调注释（`:84-88`）同步修订：在既有"catalog records are technical events … detail-only"口径上补充两处公共例外（用户自定义模型被覆盖/删除属用户功能事件）。

既有测试影响预告（评审核实后收窄）：`test_catalog_sync.py:1557-1559/:1770-1771` 对覆盖/清空**仅断言 detail 有记录，无"主通道零记录"断言**——升主通道预计无需反转既有断言（与批次① `:699` 情形不同），实施时核对即可。

### ⑤ config/loader 双通道

`_warn`（`:40`）内部改为三通道：既有 stderr print 保留（时序早于日志就绪，DEVELOPMENT.md §9 observable-degradation 通道）+ 主通道 WARNING + detail 同文案双写。**改造点在 `_warn` 内部，统一覆盖全部 9 处调用点**（评审核实；初稿仅计 model_catalog 3 处系搜索漏检）：

| 调用点 | 场景 | 中文文案草案 |
|---|---|---|
| `:51` | platform config_dir 不可用 | 「无法确定配置目录，改用 ~/.chrys。」 |
| `:65` / `:69` | invalid environment（非字符串/非法值） | 「环境配置无效（%s），已回退默认环境 %s。」 |
| `:97` | invalid [model_catalog] section | 「配置项 [model_catalog] 无效，已回退部署层默认。」 |
| `:104` | invalid model_catalog.base_url | 「配置项 model_catalog.base_url 无效，已回退部署层默认。」 |
| `:108` | invalid model_catalog.auto_sync | 「配置项 model_catalog.auto_sync 无效，已回退默认。」 |
| `:116` | invalid [update] section | 「配置项 [update] 无效，已回退部署层默认。」 |
| `:120` | invalid update.base_url | 「配置项 update.base_url 无效，已回退部署层默认。」 |
| `:136` | cannot parse 配置文件 | 「配置文件无法解析（%s），已回退全部默认。」 |

**文案语言决策（评审 M1 处置）**：stderr / 主通道 / detail 三通道**同一中文文案**（stderr 前缀 `aixcoding.config:` 保留），不采用"stderr 英文 + 主通道中文"分离——同一事件两种语言徒增维护面，且 `service/aixcoding/**` 已有 RUF001 目录豁免，中文化零豁免成本；§9"主卷承载人话信息"由中文统一满足。logging 未就绪时主通道记录经 root `lastResort` 落 stderr——与现状等价，无副作用；就绪后进 `aixcoding.log` 主卷。

### ⑥ startup task 双通道

`startup/__init__.py:32`：既有 stderr print 保留 + 主通道 WARNING「启动任务 %s 失败（%s）；已跳过。」+ detail 双写（中文，行级 noqa）。`ensure_file_sink` 自身失败时 logger 无 handler，lastResort 兜底 stderr——降级链完整。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| skills A：改 `adapter.py` 两行 logger 调用 | 打点与吞错同址 | 触上游接触面（R2 非空） | 1 文件 × 2 行 | 拒绝（责任人裁决 B） |
| skills B：`skill_paths.py` 函数内打点 + re-raise | 零上游改动；日志先于吞错落卷 | adapter 旧 debug 成为无害冗余 | 零 | **采用** |
| update 保留 `__name__` + 中文化 | 改动最小 | 仍不进定制卷（本批立项动机） | 零 | 拒绝 |
| update 仅 detail（无主通道事件） | 最少卷占用 | 确认/跳过/启动失败是用户功能事件（§9） | 零 | 拒绝 |
| update 检查失败 detail-only（评审二轮二：对齐 catalog 口径） | 与 catalog 一致 | 责任人裁决维持主通道：update 是用户想要的功能，失败用户希望知道可报工单；catalog 是强制同步、用户不应感知——定位不同（2026-11-19） | 零 | 拒绝（裁决维持主通道） |
| update 检查失败打点落 `_flow` 的 None 汇聚点 | 单点覆盖全部失败 | None 语义混合"无更新"（204/304 正常）与"失败"——会把"已是最新版"误报为失败（评审一轮一） | 零 | 拒绝，落 client.py 失败分支 |
| guard 主通道 + detail 双写（对齐 §9 默认） | detail 自包含 | 违反"护栏对用户不可见"裁决 | 零 | 拒绝（护栏自身状态 detail-only） |
| guard `_replace_unparsable` 单点升主通道（两轮评审一致建议） | 用户资产被覆盖可自助（备份恢复指引） | 与"一律不进主通道"初裁冲突 | 零 | **采纳**（2026-11-19 责任人改判） |
| skills 主通道 WARNING（函数级异常） | 罕见异常用户可见 | 触发面近乎零、与真缺口语义脱节（评审二轮三之 1） | 零 | 拒绝（裁决全 detail-only） |
| catalog 四处升主通道（含 :997/:1013） | 用户全知 | 发布失败用户无感（静默降级设计）；应用成功有 F4 反馈——非用户功能事件 | 零 | 拒绝（裁决仅两处） |
| catalog 两处升主通道 + 频控 | 防刷屏 | 两处均为低频事件（每次同步至多一条/一次性迁移），频控反致漏报 | 零 | 拒绝频控 |
| loader 仅主通道（删 stderr） | 单一通道 | 时序早于日志就绪，first-run 警告会丢 | 零 | 拒绝 |
| loader "stderr 英文保留 + 主通道中文"分离（评审 M1 建议） | stderr 面向开发者可留英文 | 同一事件两种语言，维护面翻倍；RUF001 已豁免、中文化零成本 | 零 | 拒绝，三通道统一中文 |
| RUF001：pyproject 目录级豁免（guard_install/startup） | 一劳永逸 | **改 pyproject = 上游文件改动**，违背本批零上游承诺 | 1 文件 × 2 行 | 拒绝 |
| RUF001：行级 `# noqa`（批次① session.py 先例） | 零上游改动 | 豁免散落行内 | 零 | **采用** |

## 上游改动清单（R2）

**无上游改动**（九个文件均为定制层文件；R2 清单为空）。R1 自查：无接线点、无上游行为变更，业务逻辑零外溢问题不适用；方案比选以"零上游接触"为硬性项驱动（见备选表 skills/RUF001 两行）。

## 对上游隐式行为的假设

1. **root lastResort 语义**：logging 未配置（或 `ensure_file_sink` task 失败）时，WARNING+ 记录经 `logging.lastResort` 输出 stderr——loader/startup 早期打点依赖此降级不抛错、不丢 stderr；假设失效（Python 行为变更）时表现为早期警告仅剩 print 分支，功能不受损。
2. **detail 子树预置**：`aixcoding.detail.*` 记录落卷依赖 `setup_logging` 预置（ADR-0017 既有机制，非本批引入）；startup 未跑（如测试环境）时 detail 记录无 handler——logging 静默吞，不打断宿主。
3. **`adapter.py` 吞错语义不变**：方案 B 依赖"skill_paths 抛异常 → adapter except 静默"这一既有契约（marker C 系登记行为）；假设失效（上游改 adapter 吞错范围）时打点仍先落卷，无新增风险。
4. **`_start_update` 失败通知**：runner ERROR 与 TUI `_LAUNCH_FAILED_NOTICE` 并存假设两者互不替代；上游 notice 文案变更不影响本打点。
5. **detail 双写在日志未就绪场景的丢失边界（评审二轮五，显式承认）**：detail 子树 `propagate=False` 且 DETAIL 级（5）低于 `lastResort` 门槛（WARNING），sink（`ensure_file_sink`）未建立时 detail 记录**静默丢失**——lastResort 只兜主通道 WARNING+。两个受影响场景：① `startup/__init__.py` 的 task 失败若发生在 `ensure_file_sink` 自身失败/未跑之后，detail 双写丢失、仅 stderr+主通道 lastResort 可见；② `config/loader.py` 的 `load_config` 带 `@cache` 且时序早于 sink 建立，**进程首次**配置错误（first-run）的 detail 双写丢失。这不是缺陷（进程重启后同错误重跑 `load_config` 时 sink 已就绪、detail 落卷——`@cache` 按 per-process 隔离；task 失败是进程内事件）——但"detail 卷自包含"口径在本批**明确不含进程首条路径**。

## 定制点登记预告

不适用：本批零上游接触（R2 空表），无新登记 marker——九个定制文件内的新增 logger 定义与打点不构成上游定制点；`catalog.py:84` 定调注释修订不触及登记锚点（该 marker 未在登记表，文本修订对 `--strict` 零影响——批次①改同注释的实证先例）。

## R13 豁免申请

| 文件 | 规则 | 理由 | 形态 |
|---|---|---|---|
| `src/chrys/kernel/aixcoding/guard/guard_install.py` | RUF001 | 中文打点文案含全角标点（`guard/pack/*` 已有目录级豁免，本文件不在其内；pyproject 不动） | **文件级 `# ruff: noqa: RUF001` 头**（签认后修订：原"行级 noqa"在 PR #141 CI 实证失效——ruff format 按 East Asian 显示宽度折行时，行尾 noqa 被留在闭括号行而脱离字符串行诊断；文件级头结构性免疫，loader.py `noqa: T201` 头同款先例；2026-11-20 责任人裁决方案 A） |
| `src/chrys/app/aixcoding/startup/__init__.py` | RUF001 | 同上（`app/aixcoding/tui/*` 豁免不覆盖 startup） | **并入现有 `# ruff: noqa: T201` 头 → `T201, RUF001`**（同上修订） |

其余文件已有目录级豁免覆盖：`src/chrys/service/aixcoding/**`（catalog/config/skill_paths/update.service）、`src/chrys/app/aixcoding/update/*`。沿批次① RUF001 豁免台账先例登记。

## 风险与最坏情况

- **文案措辞**：主通道文案为草案，签认可改；实施后改文案仅动字符串，无结构风险。
- **频控过严/过松**：update 检查失败与 skills 目录失败均进程级 once——会话级复发仅 detail 可见（C1 同款取舍，防刷屏优先于复发诊断）；调整成本一行。
- **打点自身故障**：所有新打点位于既有 try 语义内或 logging 自身容错（坏 handler 时 stdlib 吞错）；最坏情况为个别记录丢失，宿主功能零影响。
- **既有断言修订**：catalog 两处若被既有测试钉死 detail-only，随批修订（:699 先例）；漏改表现为测试红，无运行时风险。
- **回滚**：单批次 revert 即可，日志是纯输出面——无数据格式、无文件迁移、无配置变更，零残留。

## ADR 判定

按 §6 checklist 四问：①否决备选（skills A/B、RUF001 两路径）均属模块内实现选择（反面清单明示），非架构决策；②撤销代价低（纯输出面，revert 即净）；③不约束未来工作模式（沿用 §9 分层口径与 ADR-0017 既有机制，无新规则）；④零上游依赖。**结论：不出 ADR。**"guard 对用户不可见"原则以本批 requirements/design 固化；若未来上升为规范条款或被挑战，届时按判定②重估出 madr/ADR。
