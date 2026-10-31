# ADR-0002：产品代码统一进 `src/chrys/aixcoding/` 并按依赖分层

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
-->

- 责任人：周彬
- 状态：被取代（被 ADR-0011 取代）
- 确认日期：2026-10-22
- 确认意见：实际测试验证过，可行

## 背景

进 wheel 的定制代码曾有两个落点：`src/chrys/aixcoding/`（telemetry 适配层）与仓库根 `aixcoding/`（auth/tui，`packages = ["src/chrys", "aixcoding"]` 打包为独立顶层包）。根目录整包进 wheel 导致 docs/tests/mock 泄漏进发布包，且 `chrys.aixcoding` 与 `aixcoding` 两个名字并存易混。目录重组时需裁决统一形态。

## 决策

*（本文为决策时点快照；现行规则以 DEVELOPMENT.md R4/R9 与 DIRECTORY.md §3 为准。）*

1. 进 wheel 的定制代码**只允许 `src/chrys/aixcoding/` 一处**；`pyproject.toml` 的 `packages` 还原为上游原状 `["src/chrys"]`。
2. 子包按**依赖方向**分层（"默认 T1 + 豁免审批"机制）：
   - `telemetry/` 与适配层根模块：tier 1（仅依赖 foundation/kernel，被上游高层向下调用）；
   - `auth/`：tier 1（零 chrys 依赖，纯三方库 + 内部互引）；
   - `tui/`：tier 4 侧（结构性豁免：引用 `chrys.app.tui` 的 UI 基础设施，被 app 接线点同层调用）。
3. 分层由 `tests/architecture/test_layering.py` 的 DAG 机器执行，"DAG 豁免 ↔ 定制清单登记"双向校验。

## 理由

1. **单一规则，零例外**："进 wheel = `src/chrys/aixcoding/`"一句话说清；双落点则打包、import 方向、治理范围每条规则都要写两遍。
2. **上游定制点 -1**：`packages` 还原上游原状，R2 清单少一项、升级少核对一处。
3. **命名空间统一**：全部 `chrys.aixcoding.*`；独立顶层包 `aixcoding` 占据 PyPI 顶层命名空间且与 `chrys` 并列易混。
4. **治理射程统一**：layering 架构测试、ty（目标 `src/chrys`）、i18n 提取（SOURCE_ROOT=`src/chrys`）、compileall 自动覆盖全部产品定制代码——双落点时根目录完全在治理外。
5. 依赖方向由"谁调用谁"决定，不由偏好决定：适配层必须低层（否则上游高层调不到），UI 定制必须引用宿主 UI 体系（`login.py` 继承 `BaseDialog`、复用 `DialogButtonRow`/`localized_binding`，是一致性需求而非偷懒）。一个 tier 装不下双向依赖，按子包分 tier 是如实建模。

## 否决的备选

- **维持双落点（根 `aixcoding/` 进 wheel）**：唯一优点是不迁移；在"从头重建"前提下无意义。且整目录打包泄漏开发资产。
- **强制所有定制仅依赖 T1**（含 tui）：结构性不可行。替代路径（把 UI 基础设施下沉到 foundation/kernel，或裸 Textual 重写对话框）前者本末倒置，后者重复造轮、行为不一致、跟随上游 UI 演进成本更高。
- **tui 就近放 `chrys.app` 树内**：散入上游目录，违背定制集中原则。

## 后果

- import 全量改名：`aixcoding.auth` / `aixcoding.tui` → `chrys.aixcoding.*`。消费方影响面（2026-10-22 逐文件复核）：上游 src 树 `catalog.py`×2（另 docstring 路径文字×3）、`llm/clients.py`、`tui/screens/main/screen.py`×5、`tui/screens/main/login_indicator.py`×2、`tui/app.py`×2；上游 tests 树 `test_catalog_sync.py`、`test_login_indicator.py` 及 `tests/app/aixcoding/` 全部；定制内部 `telemetry/subscriber.py`、`context.py` 的 lazy import。完整清单与执行终验要求见 `batches/restructure/plan.md` P4–P6；
- `tui` 从未被 ty 检查过，迁入后新进射程，重建时预留修复窗口；
- ruff per-file-ignores 的 `aixcoding/tui/*`（RUF001）条目跟随改路径；
- tui 文案处理见 ADR-0010（取代 ADR-0005）。
