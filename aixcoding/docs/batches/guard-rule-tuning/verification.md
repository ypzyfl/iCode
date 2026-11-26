# 验证记录：护栏规则包调优（guard-rule-tuning）

> 活文档：命令 + 输出摘要（R7 的落盘形态，追加不删旧）。

## 2026-11-26 应用后全量回归（分支 feat/guard-rule-tuning，17 文件＋2 处 note 修正后）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run python -m aixcoding.tests.guard.guard_pack_selftest` | `Ran 106 tests in 2.238s` / `OK (skipped=1)` ✓ |
| 2 | `uv run pytest aixcoding/tests/guard -q` | `27 passed, 1 skipped, 2 warnings in 4.33s` ✓ |
| 3 | 临时目录部署验证（`AIXCODING_GUARD_HOOKS_DIR` 指向 `%TEMP%` 临时目录，`install_guard_hooks(hooks_dir=…)` 后跑 `verify_guard_deployed.py`） | `共 67 条，失败 0 条：[]` ✓ |
| 4 | `uv run ruff check src/ tests/ scripts/chrys_test.py scripts/check_wheel.py scripts/calibrate_gc_freeze.py scripts/gc_freeze_calibration_math.py scripts/chat_panel_workloads.py hatch_build.py scripts/i18n_mo.py` | `All checks passed!` ✓ |
| 5 | `uv run ruff format --check`（同上全集） | `2768 files already formatted` ✓ |
| 6 | `uv run ty check --error-on-warning --python-platform win32 src/chrys`（linux、darwin 各重复） | 三平台均 `All checks passed!` ✓ |
| 7 | `uv run python aixcoding/tools/check_docs.py` | `check_docs: OK`（31 ADR / 52 design / 50 self-review 扫描） ✓ |

## 2026-11-26 本机安装与开启态确认（用户要求：合入后保持护栏开启）

安装命令：`uv run python -c "from chrys.kernel.aixcoding.guard.guard_install import install_guard_hooks; install_guard_hooks()"`

`guardctl.cmd status`（`%APPDATA%\chrys\hooks\guard\`）：

```
安全护栏总开关：开
写入范围：不限工作区
Hook 安装：已安装
规则：33 条 · 开 32 · 关 1
```

- 安装后 `hooks.yaml` 两个受管条目均 `enabled: true`（第 49 / 72 行）✓
- `guardctl.cmd show IN-05` → `"disposition": "confirm"` ✓
- `guardctl.cmd show T-NET-01` → `"disposition": "block"` ✓

对照《iCode 安全护栏测试用例》§2 自动化回归五项全部通过（2.1 自检 106、2.2 pytest
27+1skip、2.3 部署验证 67、2.4 ruff/format、2.5 ty 三平台）；§1 前置条件抽查两项一致。

未执行项：§3 手工用例组（A/B/C/D/E）留待发布前按 test-plan §手工验证步骤抽测。
引擎 ask 兜底已补端到端实测（见下节 B16）。

## 2026-11-26 B16 headless 兜底实测（独立评审后补）

```
$ uv run aixcoding-cli run "看看 ../../../../etc/passwd" -a Code
• Code Agent ready · Default · session 7866838ea4d7 · D:\project\iCode
Error: hook 'security-prompt-guard' asked for confirmation (检测到较高风险操作，是否继续？); no one can confirm it in this session
```

无任何交互提示，请求被拦截（引擎 `unavailable` → fail-closed），与测试用例 B16 期望一致。
注：拦截文案为引擎 `_ask_refusal` 组合（含 hook id 与中英混排），非 `block_message`——
该文案差异为评审 findings F1（blocker），已修正 rule-pack README/MANUAL_TESTS 与本批
requirements 的拒绝路径描述，增量复审通过（2026-11-26）。

## 2026-11-26 适配改动包 (4)（F2 裁决：回环完全豁免）后全量回归

F2 裁决由责任人经改动包 (4)＋《测试用例(4)》拍板：回环（`127.0.0.0/8`、`::1`、
`localhost`、`*.localhost`）最先完全豁免——危险端口也不例外；危险端口对非回环目标恒拦。
适配面：`_guard_core.py`（`_is_loopback_target`＋`_detect_url` 顺序调整）、自检（+1 → 107）、
部署验证（+N12/N13 → 69）、README/OPERATIONS/MANUAL_TESTS 文档；`rules.json` 无变化
（包 (4) 与包 (2) 相同，保留本仓两处 note 修正）；README/MANUAL_TESTS 重放 F1 修复。

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run python -m aixcoding.tests.guard.guard_pack_selftest` | `Ran 107 tests in 2.349s` / `OK (skipped=1)` ✓（测试用例(4) §2.1 期望一致） |
| 2 | `uv run pytest aixcoding/tests/guard -q` | `27 passed, 1 skipped` ✓（§2.2 一致） |
| 3 | 临时目录部署验证 | `共 69 条，失败 0 条：[]` ✓（§2.3 一致） |
| 4 | `uv run ruff check` ＋ `ruff format --check`（guard 路径） | `All checks passed!` / `13 files already formatted` ✓ |
| 5 | `uv run ty check --error-on-warning`（win32 / linux / darwin） | 三平台 `All checks passed!` ✓（§2.4/2.5 一致） |

本机重装（`install_guard_hooks()`）后开启态与行为探针（真实安装副本，payload/result 走临时文件）：

```
安全护栏总开关：开 / Hook 安装：已安装 / 规则：33 条 · 开 32 · 关 1
F2探针 127.0.0.1:6379  -> (放行)          ← 测试用例(4) D3
F2探针 localhost:6379  -> (放行)          ← 测试用例(4) D3
对照   10.1.2.3:3389   -> block（操作不合规，请修改后重试。） ← D4
```

B16 headless 兜底复测（引擎文件更新后）：

```
$ uv run aixcoding-cli run "看看 ../../../../etc/passwd" -a Code
Error: hook 'security-prompt-guard' asked for confirmation (检测到较高风险操作，是否继续？); no one can confirm it in this session
```

无交互、请求被拦截——fail-closed 兜底在包 (4) 引擎下保持成立。

第 2 轮复审（F2 适配增量）通过后，按其 finding F2-R1 修正 `rules.json` T-NET-01 note
（「危险端口…始终生效」→「对非回环目标始终生效（回环完全豁免，含 localhost / *.localhost）」），
自检重跑 `Ran 107 tests in 2.191s / OK (skipped=1)`；本机安装副本同步后
`guardctl.cmd show T-NET-01` 核验为新文案 ✓。评审 AI 第 2 轮独立重跑：自检 107 OK、
部署验证 69 条 0 失败，与开发侧一致。
