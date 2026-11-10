# 验证：并行批次编号与文档热点治理（parallel-batch-governance）

> 追加不删旧。环境：Windows 11，Python 3.14.10；大写盘符进入仓库，清空 `PYTHONPATH`，设置 `PYTHONUTF8=1`。
> 本文件记录本地实际执行结果；PR 双 CI 以 GitHub checks 为证据，不回写仓库。

## V1（2026-11-10 工具与真实文档树验证）

| # | 命令 | 实际结果 |
|---|---|---|
| 1 | `uv run pytest aixcoding/tests/tools/test_gen_customizations.py -n 0` | **40 passed** |
| 2 | `uv run pytest aixcoding/tests/tools/test_parallel_batch_conflicts.py -n 0` | **11 passed in 11.48s** |
| 3 | `uv run pytest aixcoding/tests/tools/test_docs_report.py -n 0` | **6 passed in 0.84s** |
| 4 | `uv run pytest aixcoding/tests/tools/test_check_docs.py -n 0` | 初版 15 项通过；含点号 TOML 键回归与 standards 路径迁移后复跑 **16 passed in 0.82s** |
| 5 | `uv run pytest aixcoding/tests -m "not integration and not gc_calibration"` | **605 passed, 51 skipped in 35.07s** |
| 6 | `uv run ruff check --no-fix aixcoding/` | **All checks passed** |
| 7 | `uv run ruff format --check aixcoding/` | **338 files already formatted** |
| 8 | `uv run python aixcoding/tools/gen_customizations.py --strict` | **109 registration rows / 150 markers / 17 designs / 7 retired ids / 0 warnings** |
| 9 | `uv run python aixcoding/tools/docs_report.py` | **39 batch directories**，真实文档树全部一级目录有可用导航标题，退出 0 |
| 10 | `uv run python aixcoding/tools/check_docs.py` | 默认模式 **OK**；该模式允许本地草案，不作为合并 closure 证据 |

补充：豁免清单经责任人确认迁至 `aixcoding/docs/standards/closure-exemptions.toml` 后，相关两文件 ruff/format 通过，`test_check_docs.py` 16 项再次全绿，旧路径引用扫描为零。

## V2（2026-11-10 guard-switches 存量补做验证）

| # | 命令 | 实际结果 |
|---|---|---|
| 1 | `uv run python -m aixcoding.tests.guard.guard_pack_selftest` | **Ran 101 tests，OK（skipped=1），1.352s** |
| 2 | `uv run pytest aixcoding/tests/guard -n 0 -m "not integration and not gc_calibration"` | **26 passed, 1 skipped in 4.76s** |
| 3 | 在 `tempfile.TemporaryDirectory()` 隔离安装规则包，并通过 `AIXCODING_GUARD_HOOKS_DIR` 运行 `verify_guard_deployed.py` | **共 64 条，失败 0 条**；未触碰用户实际配置 |

guard ADR 已迁为 ADR-0023，requirements/design/plan 的旧路径与旧编号引用扫描为零；plan 已更正 PR #98 合并时缺件的历史事实。详细证据同时落在 `guard-switches/verification.md` V1。

## V3（closure 诊断与最终待办）

- 在 guard ADR/self-review 草案及本批 verification/self-review 尚未落盘时运行 `check_docs.py --closure`，明确检出 ADR-0023 草案、guard self-review 草案、所有指向草案的 ADR-0023 引用及本批两件缺失，共 29 项错误。这次结果仅为**诊断**，不记作最终 closure 通过。
- 本批两件落盘后仍需复跑最终 closure；ADR-0023 和两份 self-review 必须由责任人本人签认，第二 AI 评审未完成前不得将对应草案改为已确认。
- 责任人于 2026-11-10 明确指示跳过 Smart Test；统一入口 `verify.py --smart` 的启动被取消，**未执行、未通过、不列为验证证据**。
- PR 尚未创建，AIxCoding Tests 与 Upstream CI 双 CI 未运行。

## 静态验收核验

- `aixcoding/docs/INDEX.md` 与 `aixcoding/docs/ROADMAP.md` 均已物理删除，无重定向、冻结档案或替代台账；删除前内容可由 `git show HEAD:aixcoding/docs/INDEX.md` 和对应 ROADMAP 路径读取。
- README 两个全景命令相邻，含 GitHub merged PR 的无目录微改动边界说明；UPGRADE-RUNBOOK 不再依赖 ROADMAP 跟踪迁移。
- `guard-switches/adr/0001-guard-write-scope-factory-default.md` 已删除，新文件为全局 `standards/adr/0023-guard-write-scope-factory-default.md`；默认 `check_docs` 已确认无重复 ADR-0001 和功能池位置错误。
- 本批未修改 `src/chrys/`、上游 `tests/`、`AGENTS.md`、上游 `ci.yml` 或其他上游 workflow。

## V4（2026-11-10 六件落盘后的签认前复查）

- 默认 `check_docs.py`：**24 ADR / 37 design / 36 self-review，OK**；仅证明本地草案形态与 ADR 位置/身份合法。
- `check_docs.py --closure`：**35 项预期阻断**，全部直接源于 ADR-0023、guard self-review、本批 self-review 三份草案及其 ADR-0023 引用；六件缺失、豁免配置缺失、stale 豁免和功能池位置错误均已消失。最终通过仍须在第二 AI 评审与责任人签认后复跑。
- 全目录 `ruff check --no-fix aixcoding/`：通过；`ruff format --check aixcoding/`：**340 files already formatted**。
- `gen_customizations.py --strict`：**109 rows / 150 markers / 17 designs / 7 retired ids / 0 warnings**。
- 静态命令确认 INDEX/ROADMAP 在工作树不存在，且 `git show HEAD:<路径>` 均可读，退出 0。

## V5（2026-11-10 manual 目录规范补同步）

- 依据已完成的 `user-manual` 批次，README 结构图与速查、DIRECTORY 总蓝图/落点决策树/根目录章节、DEVELOPMENT §2/R4、UPGRADE-RUNBOOK 冲突层与语义层均已补充 `aixcoding/manual/`。
- 现行口径：manual 是定制用户使用手册源和纯数据资源，经 force-include 进 wheel；`release/` 继续承载安装器与用户安装手册；上游 `docs/` 保持零定制。
- 全目录 `ruff check --no-fix aixcoding/` 通过，`ruff format --check aixcoding/` 为 **340 files already formatted**；默认 `check_docs.py` 为 **24 ADR / 37 design / 36 self-review，OK**；`git diff --check` 通过；四个直接编辑文件无 IDE lint 诊断。
- 本次仅改文档与治理说明，未改 manual 内容、构建配置、产品代码或测试；Smart Test 继续按责任人指示跳过。

## V6（2026-11-10 GLM 实施评审与 F1/F3 处置）

- GLM-5.3 独立复核 R2/R11、closure、API 存在性、fail-closed、测试有效性、数据边界、验证数字和引用清理；代码与测试无 blocker，strict、docs_report 和测试数字均独立复现。
- F2 已修正 test-plan 的 M1 保留字表述；F4/F5 为 nit，按报告建议不修。
- F1 由责任人确认 guard self-review 为本人签认，并接受 GLM 报告作为 guard 迁移与补件范围的第二 AI 评审；正文和两份 plan 已同步。F3 由责任人接受本批已签 design 与 ADR-0024 决策五的书面迁移授权，不修改 guard design 签认头。
- 处置后 `check_docs.py --closure`：仅剩本批 self-review 草案 **1 项预期阻断**；guard、ADR-0023 及其全部引用均已清零。该结果仍不是最终 closure 通过。
- `ruff check --no-fix aixcoding/` 通过，`ruff format --check aixcoding/` 为 **340 files already formatted**；`test_check_docs.py` 与 `test_gen_customizations.py` 合计 **56 passed in 1.53s**；`git diff --check` 通过。Smart Test 未运行。
- 当前等待 GLM-5.3 对 F1/F3 修复进行复审；复审收敛后由责任人签认本批 self-review，再运行最终 closure。

## V7（2026-11-10 GLM 增量复审收敛）

- GLM-5.3 只读复审 F1/F2/F3 相关增量并独立复跑门禁，确认 F1 blocker 清零、F2 与实现一致、F3 书面授权链完整、无新增 blocker，评审收敛。
- 复审确认 closure 仍只剩本批 self-review 草案 1 项预期待签，ruff format 为 340 files already formatted，V6 的 56 passed 与首轮独立复现数字吻合。
- 复审 S1 指出本批 self-review 引导语仍停在 F1/F3 待裁决时点，已修正为“F1-F5 已处置、复审收敛、等待责任人签认”；两份 plan 与 guard self-review 的复审状态同步更新。
- 下一步仅剩责任人签认本批 self-review、最终 closure 和 PR 双 CI；Smart Test 继续按责任人指示跳过。

## V8（2026-11-10 最终本地门禁）

- 周彬本人已于 2026-11-10 签认本批 self-review（确认意见：无特别意见）；签认后仅同步正文中的时点说明，未修改签认字段。
- `uv run python aixcoding/tools/check_docs.py --closure`：**OK**，24 ADR / 37 design / 36 self-review，零错误。这是最终本地 closure 通过证据，不再是诊断性失败。
- `uv run pytest aixcoding/tests -m "not integration and not gc_calibration"`：**605 passed, 51 skipped in 37.24s**。
- `uv run ruff check --no-fix aixcoding/`：通过；`uv run ruff format --check aixcoding/`：**340 files already formatted**。
- `uv run python aixcoding/tools/gen_customizations.py --strict`：**109 rows / 150 markers / 17 designs / 7 retired ids / 0 warnings**；`git diff --check` 通过。
- Smart Test 按责任人指示跳过，未执行。PR 与 AIxCoding Tests / Upstream CI 双 CI 尚未运行，仍以 GitHub checks 为准。

## V9（2026-11-10 PR 前全量复查与 Smart Test 补跑）

责任人随后明确要求再次检查所有该做未做事项，并运行所有该跑测试（包括 Smart Test）；本条取代此前临时跳过指示，V3-V8 的跳过表述仅保留为各时点历史记录。

- 基线：`git fetch origin main_aixcoding_cli` 后，`HEAD...origin/main_aixcoding_cli` 为 **0/0**；工作区仅包含本批 `aixcoding/` 与 fork 自有 workflow 改动，无意外文件。
- `uv run python aixcoding/tools/verify.py --smart`：**Fork verify Summary: PASSED (exit 0)**。
  - custom：**605 passed, 51 skipped in 38.90s**；
  - 上游 tests：**35854 passed, 737 skipped in 743.51s**；
  - architecture：**1247 passed, 3 skipped, 1 deselected in 157.24s**；
  - 上游 Summary：**PASSED (exit 0)**。Smart Test 本次已实际执行并通过，不再属于未跑项。
- CI 等价治理：`ruff check --no-fix aixcoding/` 通过，format **340 files already formatted**；closure **OK**；`check_import_boundaries.py` 扫描 1221 文件 **OK**；strict **109 rows / 150 markers / 17 designs / 7 retired ids / 0 warnings**；`docs_report.py` **39 batch directories**。
- R2/R3：以 CI 同一上游分叉点 `7c423b06e5e408b7a816fa7eb110014d057dc640` 运行，`check_r2_diff` **OK**（85 个上游改动均在批准池；存量“同上/文件”行名警告不阻断），`check_r3_markers` **OK**（marker_checked=82 / exempt=3）。
- guard CI 范围复跑：规则自检 **101 tests OK（skipped=1，2.027s）**；隔离部署回放 **64 条零失败**。
- 文档、代码、测试、评审、签认、生成物和本地门禁均已闭环。剩余只有 add/commit/push、PR 与 AIxCoding Tests / Upstream CI 双 CI。

## V10（2026-11-10 手动 TUI 冒烟）

- 以独立可见窗口启动 `python -m aixcoding.mock`：`model_catalog` 监听 127.0.0.1:7777、`update` 监听 127.0.0.1:7778，端口探测均为 **True**。
- 以独立可见窗口、`AIXCODING_AUTH_ENVIRONMENT=local` 启动 `uv run aixcoding-cli`。
- 责任人手动检查并确认无问题：TUI 启动无崩溃；F6 日志面板 `aixcoding` tab 正常；`/man` 含 `/login`、`/logout`；顶栏登录徽标正常；F4 模型管理保持禁用（catalog 定制预期）。
- 本次未演练 update 检测（未设置 `AIXCODING_EXTENSION_BASE_URL`），不属于本批验收范围；本批未改产品代码，冒烟结论为无回归。
