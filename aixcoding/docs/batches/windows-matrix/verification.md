# 验证：定制测试 Windows 矩阵（windows-matrix）

> 追加不删旧。环境：Windows 本机，配方 = 大写盘符 + `set "PYTHONPATH="`（清空）+
> `set "PYTHONUTF8=1"`（cmd 链式 set 须用引号形式，尾随空格会致 Python Fatal
> preconfig——local-verify V3 环境坑补记）。日期：2026-11-01。

## V1（实施验证：前置实测 + 静态核对 + 治理预跑）

前置验证（立项时，2026-11-01，Windows 本机）：

| # | 项 | 结果 |
|---|---|---|
| 1 | DPAPI 三用例逐项 | `TestWindowsDPAPI::test_round_trip` / `TestWindowsDPAPI::test_wrong_label_fails` / `TestGetBackend::test_real_windows_probe_returns_dpapi` 均 **PASSED**（`-v`，1.23s） |
| 2 | 定制全套 | 342 passed, 2 skipped（11.93s）；skip 明细 = catalog consumer 两项（`test_model_catalog_server.py:267/280`），与基线清单逐项一致；无 darwin-only、无未批准新增 |
| 3 | 依赖复核 | `aixcoding/tests/**` 零 `ripgrep\|fetch_rg` / 零 `CHRYS_PY39\|PY39` 引用（grep） |

静态核对（test-plan"本地静态核对清单"6 项；证据 = `git diff` + `yaml.safe_load` 断言）：

| # | 项 | 结果 |
|---|---|---|
| 1 | job 拓扑 | YAML 解析断言通过：jobs = [test, govern, gate]；matrix os = [ubuntu-latest, windows-latest]、fail-fast = false、timeout 15；govern fetch-depth = 0、timeout 15；gate name = AIxCoding quality gate、needs = [test, govern]、if = always()、runs-on = ubuntu-slim |
| 2 | 治理步骤逐字平移 | `git diff`：ruff×2 / check_docs / check_import_boundaries / gen_customizations --strict / R2-R3 六组步骤均为**未改动上下文行**；pytest 行移至 test job、文本逐字相同；仅两处注释跟随实态（"four steps"→"lint + docs steps"；timeout 尾注释放） |
| 3 | Windows 适配 | TEMP/TMP 重定向步骤在 checkout **前**且 `if: runner.os == 'Windows'`；`.venv` cache pin `55cc834...`、key 表达式与上游 `test_windows` 逐字一致；全文无 py39 / fetch_rg / prewarm / compileall |
| 4 | pytest step | 两 OS 同一 `run:` 文本 + `env: PYTEST_ADDOPTS: "-rA"`（命令文本不变） |
| 5 | 触发/并发/权限 | on / concurrency / permissions 块 diff 中零改动 |
| 6 | action pin | checkout / setup-uv / setup-python 三 pin 哈希与旧文件一致 |

治理六条本地全量预跑（CI 门禁逐条预跑教训在案；其中 R2/R3 基于 git **HEAD**，本批
workflow 改动提交前不在其 diff 内，提交后 CI 重跑将覆盖——`.github/workflows/aixcoding-tests.yml`
在 R2 approved 池内（ci-gate 批），池内文件 diff 已被批准，预期 OK）：

| # | 命令 | 结果 |
|---|---|---|
| 1 | `ruff check aixcoding/` | All checks passed |
| 2 | `ruff format --check aixcoding/` | 193 files already formatted |
| 3 | `check_docs.py` | OK（16 ADR / 19 design / 17 self-review） |
| 4 | `check_import_boundaries.py` | OK（1129 files） |
| 5 | `gen_customizations.py --strict` | OK（25 行 / 29 marker / 0 warning） |
| 6 | `check_r2_diff.py` / `check_r3_markers.py`（base = merge-base origin/main_iCode） | OK（池 25 全 approved）/ OK（17 checked 4 exempt） |

## V2（首 PR CI 实证，2026-11-01，PR #80 已合并）

> 证据分层：①GitHub API 匿名可查（runs / jobs / check-runs）为本节硬证据；②本机同提交
> （ade9e145）同命令等价输出辅助；③CI 日志原文（-rA 逐名行）GitHub 对匿名隐藏、API 需
> admin——两处待责任人登录网页顺手补录（见残留项），不阻塞验收结论（job 级 success +
> skipif 平台互斥语义 + 本机同命令逐名共同闭合证据链）。

| # | 项 | 结果 |
|---|---|---|
| 1 | Windows shard DPAPI 逐名 PASSED（AC4） | **CI 日志原文（run #83 job 124808208965，责任人登录补录 2026-11-01）**：`PASSED aixcoding/tests/auth/test_auth_crypto.py::TestGetBackend::test_real_windows_probe_returns_dpapi`、`PASSED ...::TestWindowsDPAPI::test_round_trip`、`PASSED ...::TestWindowsDPAPI::test_wrong_label_fails` 三行逐名在案；`8 workers [344 items]`；总结 `342 passed, 2 skipped in 25.49s` |
| 2 | Linux shard DPAPI 三项 SKIPPED（AC4/5） | **CI 日志原文（run #83 job 124808209027，责任人登录补录 2026-11-01）**：`SKIPPED aixcoding/tests/auth/test_auth_crypto.py:51: DPAPI is Windows-only`、`:60: DPAPI is Windows-only`、`:126: probe targets the real DPAPI` 三行逐字在案——平台互斥实证 |
| 3 | skip 总账 + 总数（AC5） | **CI 原文（两平台齐）**：Windows `342 passed, 2 skipped in 25.49s`（SKIPPED 仅 catalog `:267/:280` 两行）；Linux `339 passed, 5 skipped in 18.17s`（DPAPI 三行 + catalog 两行，与基线清单逐字一致，无清单外 skip）；两平台 collected 同为 **344 items**——总数对账闭合（344 = 342+2 = 339+5） |
| 4 | check 名匹配（AC6） | Check Runs API（ade9e145）**23 项全 success**：`AIxCoding quality gate` ✓（required check 落点，09:27:27–31Z，非 Expected-Waiting）；matrix 实名 `Custom tests (ubuntu-latest)` / `Custom tests (windows-latest)`、`govern`（不进 required，符合预期）；上游门 `AIxCoding upstream gate` ✓ |
| 5 | 各 job 实测时长（F-03） | govern **23s**；test(ubuntu) **41s**（Windows-only 两步正确 skipped——条件边界实证）；test(windows) **1m44s**（setup-python 44s 占大头；TEMP 步骤 ✓、cache 步骤 ✓ 含 Post 保存）；gate **4s**（ubuntu-slim）；run 总计 **~1m52s ≪ 上游门 ~12m**——F-03 成本结论：三层门未成为 PR 等待瓶颈。**TEMP/TMP 重定向 CI 实证**：Windows job 日志中 pytest tmp 落 `D:\a\_temp\tmp\pytest-of-runneradmin\...`（即 `$RUNNER_TEMP\tmp`，D: 本地盘）——非默认 `C:\Users\...\AppData\Local\Temp`，重定向步骤生效 |
| 6 | govern 平移无回归 | jobs API steps：ruff×2 / check_docs / import_boundaries / gen_customizations --strict / R2-R3 六组**逐条 success** |

验收标准核销：AC1（三层落盘 + workflow 图 4 job 实跑）✓；AC2（命令逐字相同 + `-rA` env
注入）✓；AC3（Windows 适配逐项实跑）✓；AC4（Windows DPAPI 实际执行 + Linux 互斥 skip）
✓；AC5（skip 基线：catalog 2 项×平台，无未批准新增）✓；AC6（`AIxCoding quality gate`
保名实证）✓；AC7（R2 零上游，PR diff 仅 10 文件）✓；AC8（文档联动三件随批合入）✓。

**残留项**：无——CI 日志 `-rA` 逐名原文两平台均已补录（上表 1/2/3/5 行，2026-11-01
责任人登录提取）。V2 六项全部以 CI 原文/API 硬证据闭合。

**required checks 网页核验（操作项 d，2026-11-01 责任人执行）**：通过——ruleset 同时钉
住 `AIxCoding quality gate` 与 `AIxCoding upstream gate`（逐字符核对），无本批新 job 名
误钉、无 workflow 名误钉、规则 Active；**ruleset 零改**（保名设计验证成立，temp 材料
40 号指引收官）。

补记方式：本地追加、挂主干工作区，随下批 PR 搭车带入（先例：local-verify V3 随本批
PR #80 带入；责任人 2026-11-01 确认不开独立 PR）。
