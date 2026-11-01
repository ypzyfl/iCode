# 需求：本地统一验收入口（local-verify）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
> 修订记录：2026-11-01 外部 AI 评审处置（F-01/F-02）——验收标准第 1/2/5 条与用户场景 1/3
> 随"撤回条件探测、smart 无条件双跑"方案变更重写，原条件触发两条删除。

## 背景与问题

定制测试独立收集（ADR-0001）后，本地验证形成了两套互不相通的入口：

- 上游侧：`uv run python scripts/chrys_test.py --smart/--full`——但 Smart Test 的选择器
  （`_python_paths`/`_module_for_path`/`_is_test_file` 三处硬编码）对 `aixcoding/` 域完全盲区，
  `--full` 也只跑 `tests/` + `tests/architecture`；
- 定制侧：`uv run pytest aixcoding/tests ...`——须手动记得另跑。

由此产生两类已核实的假信号：

1. **改定制测试自身**（`aixcoding/tests/**`）：Smart Test 选出 0 个测试、exit 0 全绿——刚改的
   测试根本没跑，工具却报告验证通过。对"以 Smart Test 通过为完成依据"的 AI 开发流程尤其危险。
2. **改定制产品代码**（`src/chrys/*/aixcoding/**`）：其直接消费者（定制测试）不在 Smart Test 的
   import 图内，选出的少量上游间接测试与验证主体错位。

根本问题是**验收语义不闭环**：工具与文档表达"完整本地验证"，实际完成的只是"完整上游验证"。
CI 双门（aixcoding-tests.yml + aixcoding-upstream-ci.yml）在 PR 上兜底，但不能消除本地开发中的
假绿。经多轮双 AI 讨论（2026-10-31/11-01）收敛的定性：定制测试独立收集的总体方案成立，需
修正的是"目录独立"被误当成"验证体系已闭环"——测试设施隔离与验收口径统一必须分开处理。

## 目标与非目标

- 目标：
  - 提供 fork 统一本地验收入口（`aixcoding/tools/verify.py`），内部委托上游 `chrys_test.py`，
    零上游文件改动；
  - smart 模式**无条件**执行完整定制套件（整域追加，不做变更探测、不做精细选择——套件
    <1 分钟，正确性优先于约 30 秒节省；纯上游高频开发用 `--upstream-smart` 显式跳过）；
  - full 语义闭环：`--full` = 上游套件 + 定制套件都执行、任一失败非零退出（fork-full），
    并提供 `--upstream-full` / `--custom-full` 单套件变体；
  - 双套件始终执行、互不短路，Summary 真实分列每套件结果（含未运行原因）；
  - 文档口径同步修正（P2 并入本批）：DIRECTORY.md §5 conftest 职责与实现对齐、
    "唯一检测器"措辞收敛、UPGRADE-RUNBOOK/DEVELOPMENT.md 验证命令联动登记。
- 非目标：
  - 不改 `scripts/chrys_test.py`（上游文件）、不改 `pyproject.toml` `testpaths`（ADR-0004 已
    否决且 CI 显式传路径下无效）；
  - 不做定制测试的精细依赖选择，也不做变更探测（评审 F-01：条件探测存在已核实的漏跑
    反例——共享配置变更不触发、rename 旧端丢失、`--paths` 归一化、白名单维护；无条件双跑
    以约 30 秒代价全部消除）；
  - 不扩平台矩阵（P1 批次）、不补组合测试（P1 批次）、不加 auth 窄域防呆（P1 批次，见
    temp 材料 30 号修订预案）；
  - 不把 ruff/check_docs/gen_customizations 等非 pytest 门纳入入口（CI 门与批次流程职责）。

## 用户场景

1. **AI 定制批次日常开发**：改了 `aixcoding/tests/auth/test_x.py` 与配套实现后，跑
   `uv run python aixcoding/tools/verify.py --smart --paths <改动文件>`——上游受影响测试与
   完整定制套件都执行，任一失败即非零；
2. **追上游后本地全量**：升级批次验证跑 `uv run python aixcoding/tools/verify.py --full`——
   上游完整套件 + 定制套件一次跑完（先定制后上游、互不短路），Summary 分列两套件结果；
3. **纯上游高频开发**：改 `src/chrys/kernel/xxx.py`（非 aixcoding 域）且只关心上游反馈时，
   跑 `--upstream-smart` 显式跳过定制套件（默认 `--smart` 仍会双跑，多花 <1 分钟）。

## 验收标准

- [ ] `--smart` 无条件执行完整定制套件（命令与 CI 门同构：
      `pytest aixcoding/tests -m "not integration and not gc_calibration"`），不依赖任何
      变更探测（实测：干净树上仅改一个上游文件，定制套件仍执行）；
- [ ] `--upstream-smart` 纯委托 `chrys_test.py --smart`，不执行定制套件；
- [ ] 定制套件失败时整体退出码非零（smart 与 full 两种模式下实测）；
- [ ] `--full` 执行上游 + 定制两套件；**两套件始终执行、互不短路**——一红一绿、双红组合
      实测两套件均有结果记录，整体非零；Summary 逐套件报告 passed/failed/not run 与原因
      （argparse exit 2 计为 failed，不得记为跳过或成功）；
- [ ] 无变更时（工作树干净且无 --paths）：上游侧打印 no changes 并 exit 0，定制套件仍执行
      （本地基线确认语义），整体退出码以定制套件为准；
- [ ] 上游零文件改动（R2 清单为空）；
- [ ] verify.py 自身测试落 `aixcoding/tests/tools/test_verify.py`，覆盖：五模式参数转发
      （mock subprocess，不真跑全量）、退出码聚合组合（upstream fail/custom pass、
      custom fail/upstream pass、双 fail、pytest exit 5、委托 CLI exit 2）、Summary 状态
      枚举与 not run 原因；
- [ ] 文档联动完成：DIRECTORY.md §5、DEVELOPMENT.md §4.2-4（自检）、UPGRADE-RUNBOOK.md
      验证命令块、ADR-0001 修订注记（措辞收敛 + conftest 口径）。

## 开放问题

- GitHub required checks 核验（责任人网页操作项，非本批代码交付物）：确认分支保护同时钉住
  `AIxCoding quality gate` 与 `AIxCoding upstream gate` 两个汇总 check；workflow/job 改名后需
  重核（temp 材料 40 号指引）。
- ~~本地 Windows 环境项（mock 7778 端口被占用致 test_mock_launcher 红）~~——**已核销**
  （2026-11-01 前置微改动批次 auth-isolation-mock-ports：launcher 测试改 `port=0` 动态端口，本机原红
  环境下定制全量 324 passed / 2 skipped 实测通过）。
