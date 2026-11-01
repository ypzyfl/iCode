# 测试方案：本地统一验收入口（local-verify）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

- **落点**：`aixcoding/tests/tools/test_verify.py`（DIRECTORY.md §5——工具类测试随 tools/ 既有目录）。
- **层级**：全部为行为单元测试。verify.py 将子进程执行封装为模块级执行器（设计约定：
  单一 `_run_process(args, ...) -> CompletedProcess` 风格函数），测试 monkeypatch 该执行器
  返回伪 `CompletedProcess`（记录 argv 供断言），**不真跑** pytest 全量或 chrys_test。
- **上游契约锚定**：本批对上游的依赖是 `scripts/chrys_test.py` 的 **CLI 契约**（subprocess
  边界，无 import 级符号）。锚定方式 = 委托 argv 断言（`--smart`/`--full`/`--paths` 原样
  转发）+ 退出码语义测试（design"对上游隐式行为的假设"表逐条对应，见矩阵）；上游若改
  CLI，CI 双门与本批测试的组合仍能暴露（委托步 exit 2 → failed）。
- **不测**：定制套件与上游套件自身的测试内容（各归其门）；真跑全链路（放手工验证）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口（test_verify.py::用例） | 类型 |
|---|---|---|
| AC1 `--smart` 无条件执行完整定制套件 | `test_smart_also_runs_custom_suite`（委托 0 + 断言定制 pytest argv 出现，整体 0）；`test_smart_forwards_paths`（--paths 原样进委托 argv） | 单元+契约 |
| AC2 `--upstream-smart` 纯委托不跑定制 | `test_upstream_smart_skips_custom`（仅委托 argv，无 aixcoding/tests argv） | 单元+契约 |
| AC3 定制套件失败整体非零（smart/full 两态） | `test_custom_failure_fails_smart`、`test_custom_failure_fails_full` | 单元 |
| AC4 `--full` 两套件始终执行互不短路 + Summary | `test_full_runs_both_when_custom_fails`、`test_full_runs_both_when_upstream_fails`（双向断言两命令均被调用）；`test_both_red_reports_each_and_first_nonzero`（双红：两行均 failed、整体=首个非零 5——钉聚合顺序）；`test_summary_lists_each_suite`（逐套件状态行）；`test_delegate_exit2_is_failed_not_skipped`（argparse exit 2 → failed）；`test_custom_exit5_is_failed`（pytest 5 → failed 非零） | 单元 |
| AC5 无变更：上游 no-changes 0、定制仍跑、整体码=定制码 | `test_no_changes_still_runs_custom`（委托 0 + 定制 0 → 整体 0）；`test_no_changes_custom_red_fails_whole`（定制 1 → 整体 1——整体码随定制套件） | 单元+契约 |
| AC6 R2 零上游文件 | 交付约束（design R2 清单空），手工核对 diff，verification 记录 | 手工 |
| AC7 verify.py 自身测试（即本矩阵全部用例） | 本矩阵 18 用例 + `test_cli_mode_mutex`（五模式互斥、缺模式 exit 2）+ `test_paths_rejected_for_full`（--paths 配 --full 拒绝） | 单元 |
| 单套件模式 argv 正确 | `test_upstream_smart_skips_custom`、`test_custom_full_single_suite`（仅 custom argv）、`test_upstream_full_single_suite`（仅委托 `--full` argv）、`test_smart_forwards_paths`（--paths 原样转发） | 单元+契约 |
| AC8 文档联动四件 | 交付约束，逐项核对 + verification 记录 | 手工 |

## 异常与降级路径

| 路径 | 测试 |
|---|---|
| 套件进程无法启动（spawn 失败） | `test_spawn_failure_reports_not_run`（执行器抛 OSError → Summary 该行 `not run` + 原因，整体非零——**不得**记为跳过/成功） |
| 委托 CLI 契约漂移（上游改参，argparse exit 2） | `test_delegate_exit2_is_failed_not_skipped`（见 AC4） |
| 定制套件零收集（pytest exit 5） | `test_custom_exit5_is_failed`（计 failed，整体非零——与 chrys_test"无选择测试"语义不同：custom 套件零收集属异常） |
| CLI 误用（缺/冲突模式、--paths 配非 smart 模式） | `test_cli_mode_mutex`、`test_paths_rejected_for_full`（argparse exit 2，stderr 提示） |

## 手工验证步骤（结果记入 verification.md）

1. `uv run python aixcoding/tools/verify.py --upstream-smart`——行为与直跑
   `scripts/chrys_test.py --smart` 等价（无定制套件执行）；
2. 临时改动一个 `aixcoding/tests/**` 文件 → `verify.py --smart`——观察委托 + 定制全套
   双执行（AC1 实态证据）；
3. `verify.py --custom-full`——真跑定制全套（预期 324 passed / 2 skipped 量级，11s）；
4. 人为注入定制失败（临时断言）→ `--smart` 非零、Summary 两行各如实（AC3/AC4 实态）；
5. 干净树 `--smart`——上游 no changes 0 + 定制仍执行（AC5 实态）；
6. `--full` 完整链路至少留证一次（上游全量耗时长，可与 3/4 的分项证据组合说明，或完整
   跑一次留 Summary 记录）。
