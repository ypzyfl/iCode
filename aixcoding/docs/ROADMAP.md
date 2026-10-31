# AIxCoding 定制化路线图（ROADMAP）

> 定位：三阶段路线的唯一权威描述——阶段边界、各阶段完成标准（DoD）、双轨期管理。
> 文档分工：`standards/DEVELOPMENT.md` 管"怎么做"（规范）；本文管"按什么顺序做"（路线）；
> `batches/restructure/plan.md` 是阶段三的迁入考古参考（旧分支资产映射与验收骨架）。
> 制定：2026-10-25。

## 1. 背景与动机

第一轮定制化（至旧分支 `main_aixcoding_cli_0.28.0_final`，上游 0.28.0 基线）在无规范状态下进行，
团队各成员做法不一致，追版本维护成本高企。2026-10 重建路线：基于上游最新版本拉新分支
`main_aixcoding_cli`（当前 0.31.0 基线），**不带任何旧功能代码**，仅带入规范体系，按
"规范 → 基础工程 → 功能迁入"三阶段重建定制层。

核心约束（与 DEVELOPMENT.md 一致）：对上游源码改动最少最集中，以降低追版本维护成本。

## 2. 三阶段路线

**"基础工程"的两类范畴**（一词两义，先约定；思考框架：**新建基础工程与旧功能迁移分离讨论**，只基于上游 + 规范的基线做选型）：

- **开发过程类**——服务于开发活动：规范落地校验（四工具）、定制测试 CI 门禁、上游升级 runbook。→ 阶段二主体；
- **产品运行时类**——服务于运行中的产品。其中**本地诊断包**（定制日志落盘、崩溃现场、环境快照；
  设计基线见 `batches/diagnostics/design.md`）为上游空白且零/极小上游改动，**划入阶段二**；遥测上报为旧分支
  既有功能，随阶段三迁入；企业后端对接等按真实痛点排阶段三之后——**是位置安排，不是从清单里删除**。

### 阶段一：定制规范 —— 已就位（2026-10-25）

- 产出：`standards/`（R1–R11 + 8 篇 ADR + 文档模板 + 评审 HOWTO）、`tools/check_docs.py`、`batches/restructure/plan.md`。
- DoD：规范族签认齐全、check_docs.py 通过。

### 阶段二：基础工程 —— **已完成（2026-10-25，DoD 达成）**

**选型论证——为什么不重复建设通用基础工程**：上游已具备 CI（三平台分片）、Smart Test、
测试体系、uv 依赖锁定、ruff + ty、i18n 工具链、构建与 `check_wheel.py` 打包校验、离线打包、
OTel 遥测框架（opt-in）与 trajectory 会话回放——这些定制化直接继承，不重复建设。
定制化要补的是两类：上游空白且 fork 急需的本地诊断能力；上游不会有、只有 fork 才需要的规范落地校验。

内容清单（2026-10-25 与负责人确认，**不扩大**）——完成状态：

1. ✅ **本地诊断包**（`batches/diagnostics/`，design 签认+R2 扩表重签 2026-10-25）：五模块（config /
   logging_support / crash / snapshot / launcher）+ screen.py MODULE_ORDER 一行 +
   test_layering.py DAG 登记（tier=1 + 边豁免含 stale 检测）；29 定制测试含行为锚定；
   清单 C002–C005；试运行期遗留人工项（F6 实测、launcher 冒烟）见 batches/diagnostics/verification；
2. ✅ **规范落地四工具**（`batches/devtools/`）：清单生成（含考古模式，报告
   `batches/devtools/archaeology-report-0.28.0.md` 即 §4 盘点输入）/ R2 比对 / R3 校验 / import 边界；
   双 AI 评审两轮收敛；
3. ✅ **定制 CI 门禁** `aixcoding-tests.yml`（ADR-0004 四步 + 四工具挂入；base=merge-base
   origin/main_iCode；多次运行全绿；实施副产修复 git core.quotepath 中文路径 bug）；
4. ✅ **上游升级 runbook**：`standards/UPGRADE-RUNBOOK.md`（§8 操作展开：镜像纪律、冲突高发区
   对照、工具命令序列、已知坑速查、双轨期注意）；
5. ✅ **版本与发布策略**（`versioning.md`，2026-10-25 定稿：上游三段 + fork 第四段、
   基线升级重置第四位、分发名保持上游、CHANGELOG 约定）。

- DoD 核验（2026-10-25）：四工具与诊断包挂入 CI 跑绿（AIxCoding Tests 多次 success，含
  诊断包 29 用例与 R2/R3 分叉点门禁）✓；runbook 成文 ✓；诊断包 R2 获负责人签认
  （含实施中扩表重签）✓；版本策略定稿不阻塞 ✓。**阶段二 DoD 全项满足。**
- 附带产出：AGENTS.md 既有入口段追溯补登记（`agents-md-note/`，清单 C001）；R3 规范
  YAML 措辞修正；CUSTOMIZATIONS.md 机制全链路五次验证（签认→标记→清单自动收敛）。
- 克制原则执行情况：清单外未建设（遥测后端对接、mock 体系等留阶段三按痛点驱动）。

### 阶段三：旧功能迁入 —— 当前阶段（阶段二 DoD 达成 2026-10-25 起算）

- 输入：§4 盘点清单（工具①落地的首次实战即产出考古扫描）+ `batches/restructure/plan.md` 考古映射
  （其 §3 顺序 / §4 验收骨架仍有效）。
- 原则：
  - 逐特性迁入，每个特性独立走 design + R2 审批 + 验收，迁入是规范的第一次大规模实战；
  - 上游文件定位以 `AIxCoding` 标记在旧分支考古、在新基线重新比对——**不得照抄旧行号**
    （上游 0.28→0.31 已漂移，plan.md 钉死的行号全部失效）；
  - 旧实现与新规范冲突时改实现不改规范；确需改规范走 ADR 推翻。
- 顺序（2026-10-25 负责人确认，调整自 plan.md §3 依赖顺序）：mock 基建 → auth → tui →
  其余按盘点判定 → **telemetry 殿后**。调整原因：telemetry 迁入路线未定——旧直改源码方案
  侵入面大（11+ 上游文件），"迁入后再撤销"的摘除成本为主要顾虑——**撤销 2026-10-08 定稿的
  直改源码方案作为阶段三迁入路径**，降格为双分支候选路线的服役分支实现；其数据口径规格
  不变，仍为各候选路线的对齐目标。候选路线
  （双分支（主干+直改服役分支）/ 最小侵入重实现（上游挂接点或运行时包装+契约测试）/
  session 最小版先行）由两个调研定夺（上游 0.31.0 挂接点调查、session 文件字段覆盖度
  对照）。调研触发点（2026-10-25 评审补写实）：**阶段三部分验收达成，或首次出现追上游
  版本出服需求**（两者先到为准）即启动两个调研；telemetry design 启动以调研结论为前置
  输入。
- DoD（2026-10-25 顺序调整后拆两档）：
  - **部分验收**（非 telemetry 定制迁入完成）：定制点登记对账全绿（`gen_customizations.py
    --strict`，customization-registry 批次起口径，不含
    telemetry 定制点）；定制测试全绿；上游架构测试绿；离线打包冒烟通过。
  - **完整验收**（部分验收 + telemetry）：telemetry 迁入落地，且数据管道切换验收（新旧
    对拍：同一批真实会话下新旧实现上报口径一致比对）通过。
  - 旧分支归档切换点挂完整验收（见 §3）。

## 3. 双轨期管理

- 旧分支 `main_aixcoding_cli_0.28.0_final` 服役至阶段三完成。
- 冻结点（**已确认**，负责人 2026-10-25）：新分支进入阶段三后，旧分支只修阻塞级 bug、不加功能。
  - 生效条件：阶段二 DoD 满足之日自动生效，无需另行宣布；生效前旧分支开发不受限；
  - **冻结已生效（2026-10-25，阶段二 DoD 满足日，见 §2 完成核验）**；
  - "是否阻塞级"由负责人裁决；
  - telemetry 例外（2026-10-25 补）：telemetry 数据管道切换验收前，旧分支 telemetry 相关
    缺陷影响现网数据上报的，按阻塞级 bug 通道修复（属缺陷修复，不违反功能冻结）；
  - 冻结期间新功能需求一律引导至新分支，从源头防止两条分支继续分叉。
- 切换点：阶段三**完整验收**满足之日（DoD 两档定义见 §2），旧分支转归档。telemetry 殿后
  期间：非 telemetry 定制迁完即达部分验收，可先行开展除 telemetry 外的验收核验；旧分支
  最终归档仍以 telemetry 数据管道切换验收为前提——现网数据上报在其完成前持续依赖旧分支
  （0.28.0 基线），若此期间需追上游版本出服，telemetry 路线决策需提前触发。

## 4. 旧功能盘点清单（阶段三考古输入；扫描由工具①落地时产出，逐项判定属阶段三规划）

考古来源：旧分支 `main_aixcoding_cli_0.28.0_final`。2026-10-25 预扫描资产分布：

- 产品代码 `src/chrys/aixcoding/`：根模块 6 py（config / context / git_info / http / update_detection / __init__）+ `telemetry/` 9 py；
- 待迁产品代码：`aixcoding/auth/`（9 py）、`aixcoding/tui/`（含 login.tcss）；
- 文档：活文档 `aixcoding/docs/telemetry/`（9 md）；历史文档 `aixcoding/doc/`（9 md，逐份去向见 plan.md R1）；
- 测试：`aixcoding/tests/`（6 测试 + conftest）、`tests/app/aixcoding/`（11 文件）；
- mock：`aixcoding/telemetry-mock/`、`mock_server/` 下三服务（aixcoding_auth / aixcoding_update / chrys_model_catalog）；
- `src/` 树 `AIxCoding` 标记命中 **39 个文件**——多于既有规范文档记载（`skills/adapter.py`×19、
  `agents/schema.py`×6、`catalog.py`×6、`screens/main/screen.py`×8 等为清单外发现），
  其中含品牌字符串等非注释命中，由工具①甄别为归属标记后方可计入清单。

| 特性 | 旧落点 | 判定（照迁 / 重做 / 废弃） | 依据 / 备注 |
|---|---|---|---|
| （待盘点脚本产出，工具①落地后填充） | | | |

## 5. 变更记录

- 2026-10-25：制定；三阶段顺序经负责人与 AI 评审确认。
- 2026-10-25（二）：阶段二内容重构——确立"新建基础工程与旧功能迁移分离"框架；本地诊断包
  划入阶段二（设计基线 `batches/diagnostics/design.md`）；CI 门禁、升级 runbook 入清单；盘点清单
  剥离回阶段三语境。
- 2026-10-25（三）：**阶段二完成**——五项清单全部落地（四工具 / 诊断包 / CI 门禁 /
  升级 runbook `standards/UPGRADE-RUNBOOK.md` / 版本策略）；DoD 全项核验通过；
  依 §3 条款旧分支冻结自动生效；阶段三启动（迁入顺序待按 §4 盘点表逐项规划）。
- 2026-10-25（四）：**阶段三顺序确认**——telemetry 殿后（mock 基建 → auth → tui → 其余
  按盘点 → telemetry）：撤销 2026-10-08 定稿的直改源码方案作为阶段三迁入路径（降格为
  双分支候选路线的服役分支实现，数据口径规格不变），迁入-撤销成本为主要顾虑，迁入路线
  待两个调研定夺（见 §2 阶段三）；
  DoD 拆两档（部分/完整验收），旧分支归档挂完整验收并补 telemetry 现网缺陷冻结例外（见 §3）。
- 2026-10-30：**diagnostics launcher 退役**（ADR-0013，批次 `launcher-retirement/`）——crash /
  snapshot / launcher 三模块删除、`test_layering.py` 豁免机制回滚，阶段二诊断包由五模块收敛为
  config + logging_support 两模块；上游测试文件足迹归零。
  **补做义务（登记勿遗忘，责任人 2026-10-30 要求明确记录）**：
  ① ~~**gen_customizations 登记源单一化**~~ **已销项（2026-10-31，customization-registry 批次）**：
  登记点级化 + 唯一现行登记行（每定制点唯一 design 承载，tier-migration/ai-gates 双源清空迁移）+
  `CUSTOMIZATIONS.md` 产物退役改对账命令（ADR-0015）；
  ② crash 捕获 / 环境快照能力已按 ADR-0013 退役（价值取舍：足迹清零优先），将来需要时按 ADR-0013
  记录的**内联接线替代路径**实现或从 git 历史复原。
