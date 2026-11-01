# 设计：本地统一验收入口（local-verify）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-01
- 确认意见：无特别意见

## 方案概述

新增 `aixcoding/tools/verify.py`（纯开发资产，零上游接触）作为 fork 统一本地验收入口：
subprocess 委托上游 `scripts/chrys_test.py`（只依赖其 CLI 契约），**smart 模式无条件追加完整
定制套件**——不做任何变更探测：定制套件全跑 <1 分钟，正确性优先于约 30 秒的节省。退出码
聚合，任一执行的套件失败即非零。

五个互斥模式（`--paths PATH ...` 仅配 smart 类模式，原样转发给委托方）：

```
--smart            委托 chrys_test.py --smart [--paths ...] + 无条件完整定制套件（默认推荐）
--upstream-smart   纯委托 chrys_test.py --smart（给纯上游高频开发显式跳过定制套件）
--full             fork-full：完整定制套件 + 委托 chrys_test.py --full
--upstream-full    纯委托 chrys_test.py --full
--custom-full      纯定制套件
```

执行与聚合语义（所有双套件模式一致，钉死）：

1. 定制套件命令与 CI 门同构：`[python, -m, pytest, aixcoding/tests, -m,
   "not integration and not gc_calibration"]`（根 `addopts` 的 `-n 8` 自然生效）；
2. **两套件始终执行、互不短路**——任一套件失败后另一套件照常运行（完整验证画面优先于
   快速失败省时）；排序为先定制（快、结果先见）后上游；
3. 分别记录每套件的退出码与 pytest 结果行，整体退出码 = 任一非零即非零（取首个非零）；
4. 末尾 Summary 块逐套件报告 `passed / failed / not run` + 原因——`not run` 仅出现于套件
   自身无法启动（如进程 spawn 失败）；委托方 argparse 报错（exit 2）计为 `failed`，
   不得记为跳过或成功。

## 备选方案对比

| 决策点 | 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|---|
| 入口形态 | 自建 `verify.py` 包装委托 | 零上游改动；升级零摩擦；fork-full 语义自有落点 | 新增命令入口，习惯迁移（缓解：规范登记为标准自检命令） | 0 | **采用** |
| | 直改 `chrys_test.py` 加 watch | 几行 diff，命令习惯不变 | 上游文件（R2 报批）；行为被上游 `test_chrys_test.py` 钉住，改动可能牵连；每轮追上游永久维护 | 文件数 1 × 行数小 × 耦合度高（上游活跃调整该文件） | 否 |
| | shell 别名 / pre-commit / 纯文档要求 | 零代码 | 别名不稳定、Windows 与 AI 执行环境难统一；pre-commit 非全验证场景入口；纪律不是机制（现状即此，已证实有盲区） | 0 | 否 |
| 委托方式 | subprocess 走 CLI 契约 | 只依赖 `--smart/--full/--paths` 公开用法（AGENTS.md 记载）；进程边界清晰，参数错误显性失败 | 参数转发需维护（上游改参即断，失效可见可修） | 0 | **采用** |
| | import `scripts.chrys_test` 内部函数 | 无进程开销 | `main`/`discover_changes` 等非公开契约，上游重构静默破坏 | 耦合上游内部结构 | 否 |
| 定制套件执行时机 | **smart 无条件整域追加** | 零探测代码、零漏跑面、零维护；与"套件小不做精细选择"逻辑自洽 | 纯上游改动多约 30 秒（`--upstream-smart` 显式跳过，不靠隐式猜测） | 0 | **采用** |
| | 自建 git 变更探测 + 定制域命中才跑（原草案） | 纯上游改动省约 30 秒 | 存在已核实的漏跑反例（共享 pytest 配置/依赖变更不触发、rename 旧端丢失、`--paths` 归一化未钉死、`aixcoding/__init__.py` 不在白名单、未来新子目录漏跑——见评审处置记录 F-01）；为省 30 秒引入探测子系统 + fail-safe + 白名单维护，收益成本倒挂；fail-safe 的存在本身证明漏跑不可接受，故其默认化即上一行方案 | 0 | 否（2026-11-01 评审后撤回） |
| | 扩展 Smart Test 精细选择到定制域 | 理论最省 | 需扩展上游选择器三处硬编码 + fixture 收集管道；当前规模收益≈0 | 高 | 否 |
| full 语义 | `--full` = fork-full（默认双套件） | 消除"最大范围验证仍漏定制"的歧义 | 总时长 = 上游全量 + 定制（<1 分钟） | 0 | **采用** |
| | 保持 `--full` = upstream、另名 fork-full | 与上游命令兼容 | 歧义保留：`--full` 字面即"全"，漏跑定制违背本批目标 | 0 | 否 |
| 退出聚合 | 两套件始终执行、分别记录、聚合非零 | Summary 真实分列双结果；失败组合（一红一绿）不被短路掩盖 | 失败时总时长不省 | 0 | **采用** |
| | 首败短路 | 省 | 验证报告失真：第二套件"未跑"与"通过"不可区分（F-02 否决理由） | 0 | 否 |

R1 结论一句话：**默认优先零上游改动；若上游改动能显著降低全生命周期成本，应单独比较而非
预先否决**——本批对比表显示零改动方案同时就是最优方案，无需动上游。

## 上游改动清单（R2）

**无上游改动**。全部产出落 fork 自有资产：`aixcoding/tools/verify.py`（新增）、
`aixcoding/tests/tools/test_verify.py`（新增）、`aixcoding/docs/`（本批次目录 + 规范族联动）。
规范族（`aixcoding/docs/standards/`）为 fork 自建文档，不属上游树。

## 对上游隐式行为的假设

| 假设 | 依赖方式 | 失效表现 |
|---|---|---|
| `chrys_test.py` CLI 契约（`--smart`/`--full`/`--paths`，AGENTS.md 记载的公开用法）稳定 | smart/upstream-full 的参数转发 | 上游改名/移参 → 委托步 argparse 报错（exit 2，计入 failed，可见可修） |
| `chrys_test.py --smart` 在无变更时 exit 0 并打印说明 | 无变更场景的整体退出语义 | 上游改为非零 → verify 在同场景非零（行为可见，人工核对后跟随调整） |
| `chrys_test.py --full` 完整覆盖 `tests/` + `tests/architecture`（fork-full 的 upstream 半边语义） | `--full` 组合 | 上游收窄 full 射程 → fork-full 随之收窄（CI 双门仍兜底；升级 runbook 核对项） |
| 根 `pyproject.toml` pytest 配置（`-n 8` 等 addopts）对 `aixcoding/tests` 生效 | 定制套件执行 | 上游改 addopts → 定制套件并发/收集行为跟随（共享基础配置是明确依赖，见 ADR-0001 修订注记口径；本设计 smart 无条件双跑，配置变更场景天然覆盖定制套件——评审 F-01 反例一的根因已消除） |

## 定制点登记预告

不适用：纯开发资产（本地验证工具），零上游接触面、无运行时行为、无 marker（同 ci-gate/devtools 口径）。

## 风险与最坏情况

- **习惯迁移失败**（最可能的风险）：开发者/AI 仍直跑 `chrys_test.py`，盲区照旧。缓解：
  DEVELOPMENT.md §4.2 自检命令、UPGRADE-RUNBOOK 验证块、DIRECTORY.md §5 全部改为 verify.py
  口径（本批文档联动交付物）；批次流程的验证记录以 verify.py 输出为准。
- **chrys_test CLI 契约漂移**：失效可见（exit 2 → failed），修复 = 对照上游新 CLI 调整转发
  参数，单点维护；最坏情况临时退回直跑两条命令（现状），无功能损失。
- **定制套件时长增长**：当前全跑 <1 分钟（CI 门实测含环境 38s–5min）。不做预先分区；
  在 verify.py 的 Summary 中持续记录 custom 套件实际耗时，触发以下任一预算时再评估分区
  （按执行性质分"快速单元/契约、慢组合/集成、平台专项"，**不**按业务子目录）：
  约定 Windows 开发机上连续多次运行中位数 >1 分钟、或 P95 >2 分钟、或慢测试/外部资源/
  固定端口冲突开始频繁阻断全部定制反馈。
- **回滚**：删除 `verify.py` + `test_verify.py` + 回滚文档改动即完全回滚；上游侧零残留。

## ADR 判定

四问：①否决备选——上表已记（入口形态/委托/执行时机/full 语义/退出聚合均为操作层选型，
含一次草案内撤回的记录）；②撤销代价——单工具文件 + 文档，可即删，低；③约束未来工作
模式——"本地验收统一走 verify.py"为流程协议，由活文档（DEVELOPMENT.md/DIRECTORY.md/
UPGRADE-RUNBOOK）承载，不推翻任何既有 ADR（ADR-0001 独立收集不变、ADR-0004 testpaths
否决结论不变，本批是其"显式管道"路线的延伸；smart 无条件双跑进一步弱化了"协议例外"的
可能性，仍属操作协议范畴）；④依赖上游非公开接口——无（仅 CLI 公开用法）。结论：**不出
ADR**。（③若责任人认为属 ADR 级，可在签认意见中要求补出，实施前裁决。）

## 文档联动（本批交付物清单）

| 文档 | 改动 |
|---|---|
| `standards/DIRECTORY.md` §5 | 运行口径改为 verify.py（原显式 pytest 命令保留为"直接跑"变体）；conftest 职责描述与实现对齐（实际 = sys.path 注入 + 通用 fixtures；`auth/conftest.py` 另有窄域 autouse 先例；config-dir/环境隔离以测试内显式注入为主范式——待 ADR-0001 注记同步） |
| `standards/DEVELOPMENT.md` §4.2-4（自检） | 自检命令登记 verify.py 为统一入口 |
| `standards/UPGRADE-RUNBOOK.md` 验证命令块 | 升级验证整合为 `verify.py --full` + 四门工具（原 `-n0` 定制套件命令保留为求稳变体） |
| `standards/adr/0001` | 追加修订注记（先例：ADR-0010 注记格式）：①"唯一检测器"措辞收敛为"专门的自动语义回归套件，与治理工具/上游测试/人工冒烟互补"；②conftest"等价 config-dir 隔离"表述校准为显式注入范式；③本地验收入口语义（本批） |

## 草案评审处置记录（2026-11-01，外部 AI 评审）

评审输入：`temp/2026-11-01-custom-test-strategy/50-review-prompt.md` 发起的独立评审
（Q1–Q6 + findings F-01–F-08）。责任人已裁决"都按处置意见"（2026-11-01）。核实与处置：

| Finding | 级别 | 核实 | 处置 |
|---|---|---|---|
| F-01 条件探测漏跑反例（5 条） | blocker | 全部成立（共享配置变更不触发 / `--name-only` 丢 rename 旧端 / `--paths` 归一化未钉死 / `aixcoding/__init__.py` 白名单外 / 未来新子目录漏跑） | **撤回自建探测方案**：smart 无条件双跑 + `--upstream-smart` 显式变体（本版方案概述/备选表已改） |
| F-02 双套件执行语义未钉死 | major | 成立（原稿"首个非零"未排除短路） | 钉死：两套始终执行、分别记录、聚合非零、Summary 含 not run+原因（方案概述第 2-4 条） |
| F-03 Windows 矩阵 required check 名不确定性 | major | 成立（matrix 展开影响 check 名，原 10 号材料仅归因方案 B） | temp 10 号材料改三层结构（test 矩阵 + govern + 稳定 gate） |
| F-04 autouse 降级论证事实错误 | major | **成立并修正本仓认知**：`test_auth_session.py:125` / `test_auth_delegation.py:128` 两测试确为默认 `get_login_session()` 构造（真实 config_dir + 真实平台后端）；macOS 探测经 `security add-generic-password` 真实写入且无清理（`crypto.py:212` / `get_backend():254`）；且 `aixcoding/tests/auth/conftest.py` 已存在窄域 autouse 先例（原降级论证漏读此文件，"autouse 与继承上游同构"理由不成立） | temp 30 号材料重写：P1-5 从"降级不做"改为"窄 auth 防呆 + 默认构造隔离"，移交后续批次 |
| F-05 组合测试未钉死生产组装入口 | major | 成立 | temp 20 号材料补验收条件（真实 `create_client(ModelProfile)`、transport seam、同一 client 三次请求、登出断言语义） |
| F-06 "本地 full 等价验证"表述不准确 | major | 成立 | temp 40 号改为"本地补充非替代；上游完整矩阵由 PR merge ref CI 承载" |
| F-07 macOS 平台能力断言未验证 | minor | 成立 | temp 10 号理由改为收益成本比，平台能力另用最小 workflow 查证 |
| F-08 重评阈值不可测量 | minor | 成立 | 本版风险节改为可测量预算（中位数 >1min / P95 >2min / 阻断频繁），分区按执行性质 |
| Q1① "零上游改动"绝对化 | — | 成立（偏离 R1 原义） | 本版 R1 结论句已修正 |
