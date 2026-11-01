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

## V2（首 PR CI 实证——待 PR 后补记）

清单（test-plan"首 PR 验证清单"，逐项补记）：

1. Windows shard `-rA`：三个 DPAPI nodeid 逐名 PASSED（AC4）；
2. Linux shard `-rA`：三个 DPAPI nodeid 逐名 SKIPPED（AC4/AC5 平台互斥）；
3. skip 总账：catalog consumer 2 项 × 2 平台 SKIPPED；两平台 collected/passed/skipped 总数
   登记（基线快照；清单外 skip → 停下按 R13 呈报）；
4. check 名 `AIxCoding quality gate` 实证（非 "Expected — Waiting"）；matrix 展开 check 名
   一并记录（AC6）；
5. 各 job 实测时长：Windows 冷/热缓存（首跑+次跑）、govern、gate；对照上游门 ≈11 分钟
   瓶颈（F-03 处置）；
6. govern 六组步骤日志逐条绿（平移无回归实证）。
