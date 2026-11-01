# 验证：本地统一验收入口（local-verify）

> 追加不删旧。环境：Windows 本机，配方 = 大写盘符 + `PYTHONPATH=`（清空）+ `PYTHONUTF8=1`。
> 日期：2026-11-01。

## V1（实施验证：单测 + 部分手工实测——各步骤实测/单测钉住口径见下表注）

单元/行为测试（`aixcoding/tests/tools/test_verify.py`，mock subprocess seam，test-plan 覆盖
矩阵 15 用例 + 变体）：

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run ruff check aixcoding/` + `ruff format --check aixcoding/` | All checks passed / 188 files formatted |
| 2 | `uv run pytest aixcoding/tests/tools/test_verify.py -q` | **17 passed in 1.43s** |

实施期测试抓到真 bug 一枚并修复：`_aggregate` 原实现 `if suite.returncode:` 对 `None`
（not run）判假——spawn 失败的套件会被当成通过；`test_spawn_failure_reports_not_run`
暴露后改为显式 `None→exit 2` 判定（not run 用例的价值实证）。

手工验证（test-plan"手工验证步骤"；**口径如实**：部分场景真实子进程实测、部分由单测
钉住逻辑——评审 F-03 处置后校准，原"全项实测"表述过强已改）：

| 步骤 | 命令 | 结果 |
|---|---|---|
| 3 | `verify.py --custom-full` | **341 passed, 2 skipped in 10.84s**（341=存量 324+本批 17）；exit 0；Summary `custom passed`，result line 完整捕获 |
| 2 | `verify.py --smart`（分支带 untracked 批次文档的场景） | **双跑实测**：custom 341 passed（10s）+ 委托上游 smart；委托侧因分支对上游分叉点 diff 含全局配置触发 full 升级——上游全量 **33222 passed, 613 skipped（8:23）+ architecture 1237 passed（2:10）**；双层 Summary 如实叠加，整体 exit 0。顺带真实验证了委托 full 升级路径与流式输出（注：此场景≠no-changes 场景，AC5 不据此核销） |
| 4 | 注入失败测试 → `verify.py --smart --paths README.md` → 删除（评审 F-03 补测，--paths 限定上游选择范围） | **--smart 双套件失败实测**：custom 342 passed + 1 error（注入）→ failed exit 1（13.5s）；upstream 委托选择 1 目标（test_chrys_test.py，README watch）→ 168 passed exit 0（16.3s）；**Fork verify Summary: FAILED (exit 1)**，custom failed / upstream passed 两行如实（注入经 cmd echo 转义产生收集错误，效果等价） |
| 4′ | 注入失败测试 → `verify.py --custom-full` → 删除（实施期首测） | **FAILED (exit 1)**、custom failed——单套件失败聚合正确（cmd 回显 exit=0 系 `%ERRORLEVEL%` 解析时展开假象，实际码以 Summary 为准） |
| 1 | `verify.py --upstream-smart` 纯委托路径 | 委托半边行为已在步骤 2/4 真实执行 + 单测 `test_upstream_smart_skips_custom` 钉住"不跑定制"；独立全模式实测由外部评审 AI 补做（`--upstream-smart --paths aixcoding/tools/verify.py`：选择 0 个适用测试，upstream passed exit 0） |
| 5 | no-changes 场景（干净树 `--smart`） | **未在本地实测**（当前工作区含本批全部变更，无法构造干净树）——逻辑由单测 `test_no_changes_still_runs_custom` / `test_no_changes_custom_red_fails_whole` 钉住；**提交后干净树可自然复验**（PR 后任何人可跑） |

验收标准核销（requirements.md 8 条）：AC1（步骤 2 双跑+单测）✓；AC2（单测）✓；AC3（步骤 4
--smart 实测 + 4′ + 单测）✓；AC4（单测 6 用例：互不短路双向、双红聚合顺序、exit2/exit5
语义；+ 步骤 4 实态）✓；AC5（单测 2 用例钉逻辑；干净树实测留 PR 后，如实登记→已由
V3 核销）✓；
AC6（R2 零上游文件——本批变更全在 aixcoding/，见 V2 评审对名）✓；AC7（=18 个单测）✓；
AC8（文档联动四件）✓。

备注：fork 分支场景下 `chrys_test --smart` 的变更基线是 `origin/HEAD → origin/main`
（纯上游镜像），分支 diff 恒为"自上游分叉点以来的全部定制"（实测 566 路径，常触发 full
升级）——这是上游工具在本仓库的既有表现（直跑同样如此），非本批引入；`--paths` 显式
传参不受影响。

## V2（双 AI 自审处置，2026-11-01）

评审 AI：Kimi-K3.1-Pro（按 SELF-REVIEW-HOWTO §二 模板，独立实测通过：17 用例 / lint /
check_docs / `--custom-full` 341 passed / `--upstream-smart --paths` 委托真实运行）。
findings 4 条，责任人裁决"按处置意见"全修：

| Finding | 级别 | 处置 | 复验 |
|---|---|---|---|
| F-01 `noqa: S603` 无 R13 批准指向 | blocker | 责任人批准（2026-11-01，正当后备：argv 本地构造无 shell，规则与场景结构性冲突）；注释补批准指向 `(R13 approved: local-verify design, 2026-11-01)` | ruff 通过 |
| F-02 双红组合无测试（"首个非零"未钉住——反转聚合顺序现测试仍绿） | suggestion | 新增 `test_both_red_reports_each_and_first_nonzero`（custom 5 + upstream 2 → 两行 failed、整体 5） | 18 passed |
| F-03 verification"手工全项"表述过强（步骤 5 场景被顶替/步骤 4 命令形态不符/步骤 1 组合论证） | suggestion | V1 手工表改如实口径（见上，逐步骤注明实测/单测钉住/留 PR 后）；**补测步骤 4 原计划命令形态**：注入失败 + `--smart --paths README.md`——custom failed(1) + upstream passed(168 passed)，整体 FAILED(1)，Summary 两行如实 | 输出见 V1 表步骤 4 |
| F-04 test-plan 数量 15≠17、三用例未逐名 | nit | 矩阵更新：18 用例逐名（含 F-02 新增），新增"单套件模式 argv 正确"行 | 文档 |

终验（处置后全量）：

| # | 命令 | 结果 |
|---|---|---|
| 1 | `ruff check aixcoding/` + `ruff format --check aixcoding/` | All checks passed / 189 files |
| 2 | `pytest aixcoding/tests/tools/test_verify.py -q` | **18 passed in 1.60s** |
| 3 | `pytest aixcoding/tests -q -m "not integration and not gc_calibration"` | **342 passed, 2 skipped in 11.59s** |
| 4 | CI 定制门治理工具四条逐条预跑（提交前补，教训在案）：`check_import_boundaries.py` / `gen_customizations.py --strict` / `check_r2_diff.py --base <merge-base>` / `check_r3_markers.py --base <merge-base>` | OK / OK（25 行 29 marker 0 warning）/ OK（池 25 全 approved，本批零上游文件）/ OK（17 checked 4 exempt） |

增量复审（同评审 AI，只审增量）：F-02/F-04 通过（双红用例击败聚合顺序反例、18 用例矩阵
逐名完整）；F-01/F-03 各一处文档收尾残留并已修：①noqa 批准指向由 design 改为**本文件
V2 F-01**（批准记录实际落点，可解析）；②V1 标题"手工步骤全项"改"部分手工实测"（消除
与正文口径的残留冲突）。未发现新的代码行为问题（评审 AI 独立复跑 18 passed）。blocker
清零，评审收敛。

## V3（PR 后 AC5 实态复验，2026-11-01）

> PR #79 合并后主干（47a2a87a，含前置批 PR #78）复验，核销 V1 步骤 5 留的"PR 后待办"。
> 回写方式经责任人裁决：本地追加、随下批 PR 带入主干。

| # | 命令 | 结果 |
|---|---|---|
| 1 | `verify.py --smart --paths aixcoding/tools/verify.py`（主干 47a2a87a 干净树） | **AC5 实态核销**：委托侧 `Final execution scope: 0 targets / 0 of 35075 collected`（no applicable pytest tests）exit 0；定制 342 passed, 2 skipped（14.03s）exit 0；`Fork verify Summary: PASSED (exit 0)`，custom/upstream 两行如实 |

**口径修正（V1 步骤 5 原预期）**："提交后干净树可自然复验"在 fork 仓不成立——
`chrys_test.py` 的变更基线取 `origin/HEAD`（本仓指向上游镜像 `origin/main`，见
`_resolve_default_branch` 与 `merge-base HEAD <default>` 逻辑），主干干净树上不带
`--paths` 的 `--smart` 仍把自分叉点以来的全部定制算作分支变更、触发上游 full 升级——
V1 备注"fork 分支场景"在**主干**同样成立（基线代码核实 + V1 备注分支实证同因；未实跑
约 11 分钟全量，非必要）。"委托 0"场景须以 `--paths <与 watch 无关文件>` 构造（同 V1
步骤 1 外部评审先例）。

**AC5 三验收点**：上游 no-changes 0 ✓（0 targets / 0 tests）；定制仍跑 ✓（342 全套）；
整体码=定制码 ✓（两套件均 0 → 整体 0；"定制红→整体非零"另一半由单测
`test_no_changes_custom_red_fails_whole` 钉住）。

**环境坑补记**：cmd 链式 `set PYTHONUTF8=1 &&` 会把尾随空格收进变量值
（`Fatal Python error: preconfig_init_utf8_mode`），须用引号形式 `set "PYTHONUTF8=1"`、
清空 `set "PYTHONPATH="`。
