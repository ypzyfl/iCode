# ADR-0011：定制代码按 tier 落位 src/chrys 各层 aixcoding 子目录

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-00XX 取代）——括号内即后继编号（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-27
- 确认意见：第 2 轮 N1 修复后重新确认

## 背景

ADR-0002（2026-10-22）决策：定制产品代码统一进 `src/chrys/aixcoding/` 单点；子包按依赖分层，
`tui/` 特判"tier 4 侧（结构性豁免）"；分层由 `tests/architecture/test_layering.py` 的 DAG 机器
执行并附"DAG 豁免 ↔ 定制清单登记"双向校验。

2026-10-27 tui 批次 design 评审暴露该决策的落地死结：

1. "tui tier 4 侧"要落地，必须改上游 `test_layering.py` 的分层判定机制——`_source_top`/
   `_target_top` 只取第一级包名（`:568-575`/`:595-601`），要认出 `chrys.aixcoding.tui` 就得
   为 fork 开二级前缀特判键（联动 `TIER_ORDER`）——上游"第一级包名即 tier"原则被变相修改，
   且该机制 diff 永久占据升级冲突面；
2. 退而求其次走边豁免（diagnostics 先例，`_DAG_EDGE_ALLOWLIST`），豁免表将随每个 UI 批次
   持续膨胀（tui 3 条起步，catalog/update 各续），豁免边 = 永久"违规中"状态；
3. 评审中负责人提出更优路径：与其让上游分层机制为 fork 让路，不如让定制代码自身遵守
   分层——按实际依赖落位到各 tier 的 `aixcoding` 子目录，上游分层测试零改动、零新增豁免。
   （实测支撑：`src/chrys/app/__init__.py` 仅一行 docstring 无包级逻辑；hatchling 递归打包
   `packages=["src/chrys"]` 自动覆盖新目录，`pyproject.toml:88-90,109`；全库无
   `walk_packages` 等扫描 `chrys.app` 的机制。）

**什么变了**（对照 ADR-0002）：

- 落位规则："单点 `src/chrys/aixcoding/` + tui 特判 tier 4" → "按实际依赖落位
  `src/chrys/{tier}/aixcoding/`"；
- `src/chrys/aixcoding/` 目录废弃：存量 auth/diagnostics 回迁
  `src/chrys/kernel/aixcoding/`；`test_layering.py` 删除 `TIER_ORDER` 的 `"aixcoding": 1`
  fork 登记键（diagnostics 批次引入于 `:44-45`；`_source_top`/`_target_top` 本为上游原状）；
- ADR-0002/R9 所称"DAG 豁免 ↔ 定制清单登记"机器双向校验**实为从未实现的承诺**
  （`test_layering.py` 实际仅有豁免边 staleness 检查 `:259-264`，与定制清单无关）——本 ADR
  将该承诺作废，豁免管控以条文"豁免须登记定制清单"执行；
- 不变：仓库根 `aixcoding/` 纯开发资产不进 wheel（ADR-0002 处置延续）；`packages=["src/chrys"]`
  上游原状不动；`aixcoding` 路径段仍是全部定制代码的统一标记。

## 决策

定制产品代码按依赖落位：`src/chrys/{tier}/aixcoding/`（档位 = 四档中能容纳其全部依赖的
最低档，细则见第 2 条），各档目录按需建立。

细则：

1. **档位**：kernel / service / orchestration / app 四档（`src/chrys/kernel/aixcoding/` 等），
   按需建立，不预建空目录。kernel 档为**默认最低档**：零 chrys 依赖与仅依赖 foundation 的
   定制均落此档（foundation 档不设，完整考量见"否决的备选"末条）。
2. **判据——依赖做硬判据，语义做参考**：落位档 = 四档中**能容纳其全部依赖的最低档**
   （如 login.py 依赖 `BaseDialog` → app 基建 → 落 `src/chrys/app/aixcoding/tui/`；auth 仅
   foundation 依赖——`storage.py:52` lazy `get_platform`——→ 落 kernel 档）。判据与执法
   对齐：`test_layering` 只认 import 方向，放错层即红，规则自执行；语义归属作设计期参考，
   与依赖冲突时以依赖为准；依赖上涨 → 测试红 → 挪档，反馈回路闭环。
   **例外（个别结构性挂接边）**：整包档位由**主体依赖**决定；包内个别模块对宿主的
   **向上结构性挂接**（进程入口、钩子注册等"被宿主调用"性质的接线，非业务库依赖）不
   改变整包档位，该边走豁免登记（见第 5 条）。适用条件：①挂接性质（非库依赖）；②包内
   仅个别边向上、主体依赖 ≤ 所落档位；③豁免须登记理由与 anchor。
3. **存量回迁**：`src/chrys/aixcoding/auth/`、`src/chrys/aixcoding/diagnostics/` →
   `src/chrys/kernel/aixcoding/`（两者主体均为 ≤kernel 依赖）。import 改写分两类：**包内
   互引由绝对导入改为相对导入**（`from chrys.aixcoding.auth.client import …` →
   `from .client import …`；kernel 层硬约束：`test_layering.py:552-553` 规定 kernel→kernel
   必须相对导入，绝对导入回迁后立即全量违规——此为回迁实施第一步的红线）；**包外消费方**
   （`wire_client.py` lazy import、定制测试）改前缀
   `chrys.aixcoding.*` → `chrys.kernel.aixcoding.*`。
4. **上游还原**：`test_layering.py` 删除 `TIER_ORDER["aixcoding"]: 1` fork 登记键
   （`:44-45`，2 行）；`_source_top`/`_target_top` 本为上游原状（fork 从未改动），无需还原。
5. **豁免保留与管控**：`_DAG_EDGE_ALLOWLIST` 的 diagnostics launcher → `chrys.app.cli.app`
   条目保留（属决策 2 结构性挂接例外：挂 app 入口注册 crash hook，不改变整包档位；Path
   随回迁跟改）。豁免管控以条文执行：每条豁免须登记定制清单（reason/anchor）；ADR-0002/R9
   所称"机器双向校验"从未实现（实际仅存豁免边 staleness 检查 `:259-264`），该承诺作废。
   （导航注记 2026-10-30：本决策实例已由 ADR-0013 退役——豁免机制整体移除，非本文被取代。）
6. **每级目录须有 `__init__.py`**（hatchling 包识别与 Python import 的硬要求）。

## 理由

1. **上游分层原则零破坏**：不改 `_source_top`/`_target_top`/`TIER_ORDER` 任何一行，净效果为
   **删 2 行既有 fork 登记**——升级冲突面净减。ADR-0002 理由 5 原文"按子包分 tier 是如实
   建模"，但其决策层落地成"单点 + 特判圆回"（特判恰恰不是按子包分 tier）；本决策是该句的
   忠实兑现——tui 子包事实上就是 app 层。
2. **判据可执行**：依赖是 `test_layering` 唯一能验证的事实。语义判据无仲裁机制
   （diagnostics launcher 语义是"全局诊断设施"，不属于任何层，依赖判据下答案唯一）、机器
   不可验证、不随依赖漂移自修正。
3. **ADR-0002 当初否决多落点的两理由不再成立**：①"打包规则写两遍"——hatchling 递归打包，
   `packages` 仍一条；②"命名空间统一"——`aixcoding` 路径段仍是统一标记，glob
   `src/chrys/*/aixcoding/**` 一条说清。当时否决的"双落点"（根 `aixcoding/` 整包泄漏开发
   资产进 wheel）与本案（全部落 `src/chrys` 治理射程内）本质不同。
4. **回迁成本实测最小且时机最优**：上游 src 树消费点仅 1 处（`service/llm/wire_client.py:122`
   lazy import，service(2)→kernel 档(1) 方向依然合法）；定制测试 14 文件前缀替换（auth 9 +
   diagnostics 5，git grep 实测）；包内互引
   绝对→相对导入改写（可脚本化机械执行，但成本高于纯前缀替换——kernel 层相对导入纪律，
   见决策 3）；git mv 本身零逻辑改动。tui/catalog 批次尚未迁入，auth 消费面处于历史最小，
   此后只增不减。
5. **与 ADR-0002 否决备选"tui 就近放 chrys.app 树内"的辨析**：当时否决的是**无标记散放**
   （0.28 形态，塞进 `chrys.app.tui.screens.main/` 等既有上游目录，定制散失可识别性）；
   本决策是**带 `aixcoding` 标记的独立子目录**，定制仍集中、单条 glob 可扫，不落入当时
   否决理由的射程。

## 否决的备选

- **tui 单列 tier 4（改 test_layering 判定机制；ADR-0002 决策 2 / plan.md U2 原路径）**：
  为 fork 开二级前缀特判后门，变相修改上游"第一级包名即 tier"原则；机制 diff（判定函数 +
  特判键 + 双向校验断言，约 +15~25 行）永久占据升级冲突面。否决。
- **tui 边豁免先行（diagnostics 先例推广）**：机制不动但豁免表随每个 UI 批次膨胀，治理债
  持续累积。与决策 2"结构性挂接例外"的区分：tui 的向上边是**主体依赖**（`BaseDialog`
  继承是整包存在的基础，豁免它 = 承认整包错档）；例外只允许主体依赖已落对档位后的个别
  非业务挂接边。否决。
- **保留 `src/chrys/aixcoding/`（两档制：低档留原位 + 高档进 tier 目录）**：`TIER_ORDER`
  永久保留 fork 特判层键，"上游零破坏"不彻底；两种落位形态并存增认知负担。为省一次机械
  回迁留永久特判，不值。否决。
- **无标记散入各 tier 既有目录（0.28 形态）**：ADR-0002 原否决理由依然成立（定制集中可
  识别原则）。否决。
- **foundation 档单设**：三重考量否决——①**判据唯一性**：若设，零依赖定制在 foundation/
  kernel 两档均合法（依赖方向两处都不违规，test_layering 都不红），硬判据出现双合法答案，
  须人裁决消歧，退回语义判据老问题；不设则 kernel 档为唯一最低档，机器判据对任何依赖
  形态无歧义。②**治理无差异**：两档唯一区别场景是"上游 foundation 反向引用定制"
  （foundation(0) 引 kernel 档(1) 违规、引 foundation 档(0) 合法），但上游 foundation 是
  无业务的通用工具层，反向引用 fork 业务定制在任何分层治理中都是反模式（真需增强上游
  foundation 工具走 R2 直改上游，非新建定制模块），该区分场景实际不存在。③**空档成本**：
  按需建原则下该档等不来首个适用场景，预建空目录无意义（git 亦不跟踪空目录）。否决。

## 后果

- **回迁实施**（独立小批次，R2 报批 1 项）：git mv 两包 + import 改写（包内互引绝对→相对
  + 包外消费方前缀替换）——上游 `service/llm/wire_client.py` 1 行、`test_layering.py`
  删登记键 2 行 + 豁免条目 Path 跟改 1 行 + 注释内旧路径 2 处（`:89`/`:245`，`:44` 随键删）
  + 豁免 reason 措辞 1 处（`:94` "R9 exemption" 随 R9 重写跟改，非路径）、定制测试 14 文件、
  **工具脚本路径联动 5 处 + 工具测试夹具 4 文件**
  （见"规范联动"条，漏改则回迁后新路径被工具误判为上游、工具自检测试红）；launcher
  入口命令随之变为
  `python -m chrys.kernel.aixcoding.diagnostics.launcher`（相关文档联动）；验证 =
  `pytest tests/architecture` + `pytest aixcoding/tests`
  + `ty check`（kernel 档新路径）+ wheel 冒烟（`chrys.kernel.aixcoding` 在包内）。
- **规范联动**（规范族文本已随本 ADR 的 PR 同步完成）：DEVELOPMENT.md §2/R1/R3/R4/R9/R11/§9
  （R9 按 tier 重写）、DIRECTORY.md §1-§8、SELF-REVIEW-HOWTO 与 PEER-REVIEW-HOWTO 的
  R4/R9 内嵌摘要、templates/design 落点、README×2、`batches/restructure/plan.md` §1.1 标题 +
  P1/P2/P3 目标路径（P4-P6 为 0.28 钉死的源侧事实不改）与 U1（per-file-ignores 路径）/
  U2（作废留档，R8）。
  **工具脚本路径联动（随回迁批次实施，同 `docs/batches/devtools/design.md`"分类器随实现走"口径）**：
  文件分类/扫描逻辑硬编码于 **5 处**——`_common.py:37 CUSTOM_PATH_PREFIXES`、
  `gen_customizations.py:295,312`、`check_import_boundaries.py:10-13,85-86`、
  `check_r2_diff.py:13`、`docs/batches/devtools/design.md:28`（分类器定义）——统一改为
  `src/chrys/*/aixcoding/` 前缀判定（CUSTOMIZATIONS.md 本身是生成产物，无扫描规则可改）；
  **连带**：`aixcoding/tests/tools/` 的 4 个测试文件以旧路径为夹具
  （test__common / test_check_import_boundaries / test_check_r3_markers /
  test_gen_customizations），分类器改通配后须同步更新夹具路径，否则工具自检红；不改的
  后果：回迁后新路径被 `is_custom()` 误判为上游，B3 规则失效、gen_customizations 漏扫、
  check_r2_diff 误报。
- **进行中批次联动（前瞻，非既成）**：tui design（`aixcoding/docs/batches/tui/design.md`，**草案
  在工作区尚未入库**，随 tui 批次提交）落位**将**改 `src/chrys/app/aixcoding/tui/`，R2
  表 8 号（test_layering 登记）**将**整行删除，表 7 号 per-file-ignores 路径跟改。
- **测试侧不联动目录**：定制测试（`aixcoding/tests/`）维持按特性组织（DIRECTORY.md §5
  既有约定，非本 ADR 新决策），不镜像 tier 落位——tier 是依赖决定的技术落位，测试不受
  分层守卫治理（`test_layering` 射程仅 `src/chrys`）；测试仅 import 路径随回迁前缀替换
  （已计入上述回迁实施项）。
- **ADR-0002 头部状态改"被取代（被 ADR-0011 取代）"**，正文一字不动（§6 快照原则）。
- **已知残留旧路径引用（随各迁入批次改，R8 留档）**：`aixcoding/mock/update/__init__.py:32`
  docstring 引用 `src/chrys/aixcoding/update_detection.py`（随 update 批次迁入时改）；
  `docs/ROADMAP.md:106-107`（旧分支资产盘点，随阶段三迁入完成度更新）；
  `adr/0005-*.md:36`（快照内待执行指令，已被 plan.md U1 新路径取代，正文按 §6 快照原则
  不改）；`docs/batches/auth/*`、`docs/batches/diagnostics/*` 等签认/记录档为历史快照，不回改。
- **代价（如实承认，非一次性）**：定制代码位置从一处变为按 tier 分散（现在 kernel + app，
  将来 service/orchestration 若有定制再加）；找代码要记 N 个位置、升级排查遍历 N 个
  `aixcoding/` 目录、扫描规则随档位增长。以"上游原则零破坏 + 冲突面净减"换，成立。
- **命名空间变长**（`chrys.aixcoding.*` → `chrys.kernel.aixcoding.*` / `chrys.app.aixcoding.*`），
  换来 tier 归属在 import 路径上自明。
- **语义张力（如实提示）**：低依赖业务代码（如 auth 登录会话，仅 foundation 依赖）落入 kernel 层（上游核心
  抽象层所在），并被动继承 kernel 层"层内必须相对导入"的纪律（回迁改写成本的根源，见
  决策 3）；`chrys.kernel.aixcoding` 路径段标记缓解混淆——后来者遇"kernel 目录内有业务
  代码"疑问时，以本 ADR 档位判据（能容纳全部依赖的最低档）为准。
