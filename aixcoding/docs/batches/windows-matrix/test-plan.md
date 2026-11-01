# 测试方案：定制测试 Windows 矩阵（windows-matrix）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与首 PR CI 实证保障。

## 测试范围与策略

- **不新增 pytest 测试**（requirements 非目标：不改任何测试内容、不新增测试——本批只改
  执行平台与 job 组织；为 CI 配置文件写结构断言脚本属负收益，拒绝）。
- 验证分两层：
  1. **本地静态核对**（实施后、push 前）：YAML 结构与 design 逐项对照 + 治理步骤
     逐字平移 diff 核对 + 与上游 `test_windows` 适配项对照；
  2. **首 PR CI 实证**（真验收）：DPAPI nodeid 逐名、skip 基线、check 名匹配、各 job
     实测时长——`-rA` short summary 为证据源（评审 F-01 处置）。
- YAML 语法有效性：无本地 actionlint（不引入工具），语法错误由首跑 CI 直接暴露
  （fail-visible，一次 runner 分钟数的代价）。

## 覆盖矩阵

| 验收标准（requirements.md） | 验证方式 | 层 |
|---|---|---|
| AC1 三层结构落盘（test matrix fail-fast:false / govern fetch-depth:0 / gate 保名+always()+双 success） | 本地：新 YAML 与 design 方案概述逐项对照（job 名、needs、if、matrix、timeout）；首 PR：workflow 图三 job + gate 聚合行为 | 静态+CI |
| AC2 pytest 命令逐字相同 + `PYTEST_ADDOPTS: "-rA"` | 本地：与旧 gate job 的 pytest step 文本 diff 级核对（两 OS 同一条目）；env 注入核对 | 静态 |
| AC3 Windows 适配对齐上游（TEMP/TMP checkout 前、.venv cache pin/key 同构共享；无 py39/fetch_rg/prewarm） | 本地：与上游 `ci.yml` `test_windows` 逐项对照（步骤顺序、pin 哈希、key 表达式）；排除项核对（三步均不出现） | 静态 |
| AC4 首 PR DPAPI 逐名（Windows 3 PASSED / Linux 3 SKIPPED） | 首 PR：两 OS shard 的 `-rA` short summary 中逐 nodeid 核对（`TestWindowsDPAPI::test_round_trip` / `::test_wrong_label_fails` / `TestGetBackend::test_real_windows_probe_returns_dpapi`） | CI |
| AC5 skip 基线逐项一致 + 总数 | 首 PR：Linux shard DPAPI 3 项 SKIPPED；两平台 catalog consumer 2 项 SKIPPED（`test_model_catalog_server.py:267/280`）；两平台 collected/passed/skipped 总数记录（预期基线：Linux 342 passed 5 skipped / Windows 345 passed 2 skipped 量级——以实际为准登记） | CI |
| AC6 gate check 名匹配 required check | 首 PR：PR 页 Checks 面板 / Check Runs API 核对 check 名 `AIxCoding quality gate` 且非 "Expected — Waiting"（责任人网页配合，temp 40 号指引） | CI |
| AC7 R2 零上游文件 | 本地：`git status`/diff 路径清单核对——仅 `.github/workflows/aixcoding-tests.yml` + `aixcoding/docs/**`（含随批带入的 local-verify verification.md V3） | 静态 |
| AC8 文档联动（DIRECTORY.md §7、ADR-0004 注记） | 本地：逐项对照修订点；check_docs 通过 | 静态 |

## 本地静态核对清单（实施后逐项过，结果记 verification.md）

1. job 拓扑：`test`（matrix `[ubuntu-latest, windows-latest]`、`fail-fast: false`、
   `timeout-minutes: 15`）、`govern`（`ubuntu-latest`、`timeout-minutes: 15`、checkout
   `fetch-depth: 0`）、`gate`（`name: AIxCoding quality gate`、`needs: [test, govern]`、
   `if: always()`、`runs-on: ubuntu-slim`、env 双断言 shell）；
2. 治理步骤平移：旧 gate job 的 ruff×2 / check_docs / pytest / check_import_boundaries /
   gen_customizations --strict / R2-R3 六组步骤在新结构中逐字对照——pytest 归 `test`，
   其余归 `govern`，参数零改动；
3. Windows 适配：TEMP/TMP 步骤在 checkout **前**且 `if: runner.os == 'Windows'`；
   `.venv` cache pin `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`、key
   `venv-${{ runner.os }}-${{ hashFiles('.python-version', 'uv.lock', 'pyproject.toml') }}`
   与上游逐字一致；全文无 py39 / fetch_rg / prewarm / compileall；
4. pytest step：两 OS 同一 `run:` 文本 + `env: PYTEST_ADDOPTS: "-rA"`；
5. 触发/并发/权限块与旧文件逐字一致（on/concurrency/permissions 不动）；
6. action pin 哈希与旧文件一致（checkout / setup-uv / setup-python）。

## 首 PR CI 验证清单（真验收，结果记 verification.md）

1. Windows shard `-rA`：三个 DPAPI nodeid 逐名 PASSED（AC4）；
2. Linux shard `-rA`：三个 DPAPI nodeid 逐名 SKIPPED（AC4/AC5 平台互斥）；
3. 两平台 skip 总账：catalog consumer 2 项 × 2 平台 SKIPPED；collected/passed/skipped
   总数登记（AC5 基线快照）；出现清单外 skip → 停下按 R13 呈报，不得带过；
4. check 名：`AIxCoding quality gate` 出现且汇总（AC6）；matrix 展开 check 名（如
   `Custom tests (windows-latest)`）不进入 required check（记录实证名）；
5. 各 job 实测时长：Windows 冷/热缓存（首跑+次跑）、govern、gate；对照上游门 ≈11 分钟
   瓶颈（F-03 处置）；
6. govern 六组步骤日志逐条绿（平移无回归）；
7. 失败注入抽查（可选）：PR 分支上临时 `git revert` workflow 改动以外方式不可行——
   以 fail-closed 逻辑评审背书 + gate 首跑绿为验，不人为注入失败。
