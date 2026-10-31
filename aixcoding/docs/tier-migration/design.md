# 设计：ADR-0011 存量定制包按 tier 回迁 kernel 档

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：无特别意见

## 方案概述

执行已签认的 ADR-0011 决策 3/4/5（方案单源在 ADR-0011，本文不重展开论证）：
`git mv` 两包 + import 改写 + 上游还原 + 工具/文档联动。结构变化：

```
src/chrys/aixcoding/                     src/chrys/kernel/aixcoding/
├── __init__.py          ──废弃          ├── __init__.py        （新建）
├── auth/         ────────────────►      ├── auth/              （9 py，包内互引绝对→相对）
└── diagnostics/  ────────────────►      └── diagnostics/       （6 py，同上）
```

命名空间 `chrys.aixcoding.*` → `chrys.kernel.aixcoding.*`；launcher 命令变
`python -m chrys.kernel.aixcoding.diagnostics.launcher`。

## 备选方案对比

唯一合理路径：照已签认 ADR-0011 执行。备选论证（tui 单列 tier 4 / 边豁免先行 / 两档制 /
无标记散放 / foundation 档单设）已在 ADR-0011"否决的备选"完成并否决，本批次为决策执行，
不产生新备选。"何时做"亦已由 ADR-0011 理由 4 钉死（tui 批次迁入前 auth 消费面历史最小）。

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/service/llm/wire_client.py` | lazy import 前缀 `chrys.aixcoding.auth` → `chrys.kernel.aixcoding.auth`，及所在注释块改写 + 新增独立标记行（peer review 实测 +4/−3，C2 勘误：原预估 2 系仅计注释 1 行 + import 1 行，S1 标记行修复后旧侧改写扩为 3 行 + 新增 1 行） | 4（+4/−3） | 新增独立标记行 |
| `tests/architecture/test_layering.py` | `:44-45` 删 `TIER_ORDER` 的 `"aixcoding": 1` fork 登记键及其注释；`:89`/`:245` 注释内旧路径跟改；`:92` 豁免条目 Path 跟改；`:94` reason 措辞 "R9 exemption" 随 R9 重写跟改 | 6 | 既有标记行内跟改 |
| `src/chrys/app/tui/screens/logs/screen.py` | `:67` 注释内旧路径 `src/chrys/aixcoding/diagnostics` 跟改（ADR-0011 清单外发现，清单外发现处置 ①） | 1 | 既有标记行内跟改 |
| `tests/architecture/trajectory_wait_manifest.json` | 生成产物刷新：wait 节点清单随模块路径重生成（`uv run python -m tests.support.trajectory_wait_inventory`），+33 行纯新增（实施中发现，评审 F1 补录） | 33 | 不适用——JSON 无注释位，登记 CUSTOMIZATIONS.md 豁免表 |
| `src/chrys/aixcoding/__init__.py` | 删除旧单点入口——分类器通配化后 diff 中旧路径形态按上游对待（实跑 check_r2_diff 发现，评审外补充） | −8 | 不适用——纯删除，无注释位 |

净效果：上游文件删 2 行既有 fork 登记 + 8 行既有标记行内路径/措辞跟改（peer review 实测，
C2 勘误：原句计 7 漏了 wire_client 注释块扩行）+ 旧单点入口删除
（−8）+ 生成产物刷新（+33），无新增上游逻辑——ADR-0011 理由 1"升级冲突面净减"的兑现。
注记（评审 P3 + peer review C2）：ADR-0011 后果节计 `wire_client.py` "1 行"系仅指 `:122`
import 行；实测含注释块改写与标记行为 +4/−3。ADR 为已签认决策快照，数字勘误不改变结论，
不回改正文（§6 快照原则），以本表实测为准。
注记（peer review C4 裁决澄清）：**"落位即 custom"是 ADR-0011 既定治理口径**——决策 1/2 +
理由 3（"`aixcoding` 路径段仍是全部定制代码的统一标记，glob 一条说清"）+ R4/R9 条文同口径；
工具分类器 `src/chrys/*/aixcoding/` 通配是该条文的机器实现，非副作用。16 个新路径文件
（15 改名 + 1 新建）不入 R2 表正是此语义的执行结果，其批准链落在 ADR-0011 决策本体。

R1 自查（迁移批次）：
- 基线重审（细则一）：回迁目标落位已在 0.31 基线由 ADR-0011 实测审定（hatchling 递归打包、
  无 `walk_packages` 扫描），本批次照执行。**勘误（peer review C1）**：ADR-0011 所称
  "`__init__.py` 空壳"实测对象是 **app 层**（为 tui 落点服务），未验 kernel 层——kernel 层
  事实见假设 3 勘误；
- 逐行归属（细则二）：本批次为纯位置移动，无业务逻辑位置变化，不存在"这行能否挪进定制包"
  的归属问题——R2 表全部行均为既有定制挂点的路径/登记跟改或生成产物刷新，细则二逐行展开
  豁免（评审 F5 确认此形态可豁免）；
- 消费方视野（细则三）：不适用——公共 API 面零变化（仅命名空间前缀）。
- R1 非侵入结论：上游 3 文件全部是既有定制挂点/登记的行内跟改，无新挂点。

## 对上游隐式行为的假设

1. hatchling `packages=["src/chrys"]`（`pyproject.toml:88-90,109`）递归打包新目录 →
   `chrys.kernel.aixcoding` 自动入 wheel。失效表现：wheel 冒烟缺包（ADR-0011 已实测背书）。
2. `test_layering` `_source_top`/`_target_top` 按第一级包名判 tier → `chrys.kernel.*`
   自然落 kernel 档，service→kernel 方向合法。失效表现：architecture 测试红。
3. ~~`src/chrys/kernel/__init__.py` 已存在（上游）且 kernel 档无包级逻辑~~ **勘误（peer
   review C1，实施后实测）**：kernel 门面 `__init__.py` 含大量包级导入（`TELEMETRY_GATE`、
   `LoopRecorder`、`Agent`、client/compaction/images/instrumentation/loop/middleware/
   sessions/types 全家）；`import chrys.kernel.aixcoding.*` 必先执行整个门面（实测闭包：
   `chrys.kernel.agent` 被连带加载，回迁前零加载；冷导入 206ms、拉入 354 模块）。原假设
   系由 app 层实测类推、未验 kernel 层——**方法教训：涉及上游的断言须逐层实测，A 层实测
   不能为 B 层背书**。后果如实入档（接受，无技术绕过路径——改顶层包名违反路径段标记、改
   上游门面 lazy 违反 R1/R2、脚本直跑破坏相对导入）：①launcher 崩溃钩子时序窗口（见风险节）；
   ②auth 独立导入绑定 kernel 门面健康度（登记口径已修正）；③主程序运行时零增量（wire_client
   消费点 kernel 本已加载，import 幂等）。失效表现：kernel 门面导入期异常时崩溃钩子未装、
   无 crash 文件（诊断设施在最需要时缺席）。

## 定制点登记预告

> 节标题须保持标准形态（`gen_customizations.py` 全等匹配）。
> 点级登记已迁移（customization-registry 批次，2026-10-31）：auth 相关现行登记见 `aixcoding/docs/auth/design.md`（C021/C022，含本批次回迁勘误语义——kernel 门面耦合边与删除线勘误原文语义并入其批次锚注）；diagnostics 相关见 `aixcoding/docs/diagnostics/design.md`（C007）。本 design 登记表不再承载现行登记（原包粒度两行至此退役，历史文本见 git 历史）。

## 联动清单（非上游部分）

1. **包内改写**：auth 9 py + diagnostics 6 py——import 语句绝对→相对（kernel 层硬约束，
   `test_layering.py:552-553`）；docstring/`:mod:` 引用写新绝对前缀。
   **负向约束（评审 P1）：logger 名命名空间与 import 路径解耦，不随回迁改**——
   `ROOT_LOGGER_NAME = "aixcoding"`（`logging_support.py:26`）、`MODULE_ORDER`/
   `MODULE_WHITELIST` 成员 `"aixcoding"`（`screen.py:67`，F6 tab 识别的是顶层 logger 名）、
   conftest `AIX` 常量、`aixcoding.*` logger 子树均保持不变。误改后果：F6 日志面板静默失效，
   且 `test_panel_anchor.py` 硬编码字符串断言不 import 常量、改错后测试依然绿（无守卫）；
2. **定制测试 14 文件**前缀替换（auth 9 + diagnostics 5，git grep 实测）。diagnostics
   第 6 个测试文件 `test_panel_anchor.py` **无需改**（只 import 上游 `chrys.app.tui.screens.logs.screen`
   锚定 logger 名，无定制包 import，见上条负向约束）；
3. **工具分类器 4 py 5 处**：`_common.py:37`、`gen_customizations.py:295,312`、
   `check_import_boundaries.py:10-13,85-86`、`check_r2_diff.py:13` → `src/chrys/*/aixcoding/`
   通配判定（根 `aixcoding/` 前缀保留）；`devtools/design.md:28` 分类器定义同步；
4. **工具测试夹具 4 文件**：`aixcoding/tests/tools/`（test__common /
   test_check_import_boundaries / test_check_r3_markers / test_gen_customizations）夹具路径
   更新 + 补 tier 形态判定用例；
5. **CUSTOMIZATIONS.md** 重新生成（gen_customizations.py 扫新路径）；
6. **活文档**：`AGENTS.md:8` 旧单点路径跟改（PR #63 残留，清单外发现处置 ②）、
   `diagnostics/requirements.md:16` launcher 命令跟改；
7. **快照档叙述不回改**（R8 留档）：`diagnostics/design.md:36`、`diagnostics/verification.md:41`、
   `auth/*` 4 件、`mock/design.md`（:130/:175 旧单点路径引用，已签认快照，评审 P5 补入）、
   `adr/0002/0005/0011`（决策快照叙述，含 ADR-0011 自身对旧路径的定义性引用）、
   `archaeology-report-0.28.0.md`、`restructure/plan.md`
   P4-P6（0.28 钉死源侧事实）、`mock/update/__init__.py:32`（随 update 批次）、
   `ROADMAP.md:106-107`（随阶段三完成度）。
   澄清（评审 F3）：上列 `auth/*`、`diagnostics/design.md` 中仅**登记预告表的落点路径行**
   因是生成器语义字段单源（标记↔登记匹配的数据源）而随 R8 同步跟改并重签——属活数据，
   非快照叙述；叙述性正文一字不改；
8. **生成产物刷新**（实施中发现，ADR-0011 未预见，评审 F1/F4 补录）：
   `tests/architecture/trajectory_wait_manifest.json` 随模块路径刷新
   （`uv run python -m tests.support.trajectory_wait_inventory`，+33 行纯新增）；JSON 无
   注释位，豁免登记入 CUSTOMIZATIONS.md 豁免表——数据源为 `gen_customizations.py`
   `MARKER_EXEMPTIONS` 常量（生成区仍全量脚本渲染，§5 禁手工维护不破）。

## 风险与最坏情况

- 最坏情况：工具分类器漏改 → `is_custom()` 将新路径误判为上游，B3 觱控失效 /
  gen_customizations 漏扫 / check_r2_diff 误报（ADR-0011 后果节已列）——工具自检 4 文件
  夹具更新即为此风险的守卫；
- **kernel 门面导入期异常窗口（peer review C1，接受）**：launcher（崩溃钩子入口）的 import
  先于钩子安装执行整个 kernel 门面——门面导入期异常（升级期文件不一致/依赖漂移/上游重构
  引入的导入 bug）时钩子未装、裸 traceback 退出、无 crash 文件。触发概率低（正常发版流程
  该类失败被 CI 拦截），后果为崩溃现场丢失而非功能错误；无技术绕过路径（见假设 3 勘误），
  以入档接受。次要影响：aixcoding 测试 collection 半径扩大（门面坏时全挂而非只挂 auth）；
  独立脚本冷导入 +206ms 一次性；
- 回滚：单分支单 PR，`git revert` 整批回退（纯位置移动 + 机械改写，无数据/格式迁移）。

## ADR 判定

四问全否：①无新备选（论证已在 ADR-0011 完成）；②撤销代价已由 ADR-0011 承担（本批次是其
执行，revert 即回旧位）；③不约束新模式（模式已由 ADR-0011 约束）；④无新增上游非公开接口
依赖（anchor 面不变）。命中反面清单"唯一合理路径的照规范执行"→ 不出 ADR。
