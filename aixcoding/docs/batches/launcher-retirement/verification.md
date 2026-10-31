# 验证记录：退役 diagnostics launcher（launcher-retirement）

> 追加不删旧（R7）。本地验证落盘于此；CI 证据归属 PR checks。

## 2026-10-30 实施验证（Windows 11，本地；分支 feat/launcher_retirement）

环境口径：`PYTHONPATH=` 清空、`UV_PYTHON=3.14.3`、`PYTHONUTF8=1`、大写盘符。

### 1. 架构回归（豁免机制回滚 + `:220` kernel-private 机制存活双验证）

```
uv run pytest tests/architecture -n0 -q
1238 passed, 3 skipped in 122.09s
```

`:220` 的 `observed_private_import_exemptions`（上游原状）未被触碰——kernel-private stale 检测正常工作；`_DAG_EDGE_ALLOWLIST` 机制回滚（净删除 19 行）后 DAG 断言无 stale 报错。

### 2. 定制测试回归（保留项完好）

```
uv run pytest aixcoding/tests -n0 -q
276 passed, 2 skipped in 52.42s
```

较退役前（301 passed）少 25 = launcher/crash/snapshot 三测试文件用例；保留的 test_config / test_logging_support / test_panel_anchor 全绿。

### 3. 入口消亡

```
uv run python -m chrys.kernel.aixcoding.diagnostics.launcher
→ No module named chrys.kernel.aixcoding.diagnostics.launcher
```

### 4. 定制清单收敛 + 幂等（评审 Major 2 顺序依赖已按序执行：先改 batches/diagnostics/design.md 登记表 → 再重跑）

```
gen_customizations.py 连跑两次：均 27 custom point(s)
git diff --stat aixcoding/docs/CUSTOMIZATIONS.md → 1 file changed, 4 insertions(+), 6 deletions(-)
```

（既有 warning：batches/auth/design.md 的 wire_client 登记预告——非本批次引入。）

### 5. 残留检查

```
findstr /S /I /M "launcher" src\chrys\kernel\aixcoding\diagnostics\*.py aixcoding\tests\diagnostics\*.py
→ 仅 __init__.py（退役注记本身："retired 2026-10-30 per ADR-0013"，说明性文字非功能引用）
logging_support.py 零命中（docstring 已更新）
```

### 6. 门禁

```
ruff check（diagnostics/ + test_layering.py + tests/diagnostics/）→ All checks passed
ruff format --check → 8 files already formatted
ty check --error-on-warning --python-platform win32 src/chrys → All checks passed
```

### 7. 实施清单对照（design 全项）

- [x] 删 launcher.py / crash.py / snapshot.py（产品代码三件）
- [x] 删 test_launcher / test_crash / test_snapshot（三测试）
- [x] conftest.py 删 restore_hooks fixture + sys/threading import（aix_logger_state 保留）
- [x] __init__.py / logging_support.py docstring 更新
- [x] test_layering.py 回滚（净删除 19 行 = 代码 17 + 空行 2；:87-93/:221/:242-244/:257-262，elif 链恢复上游原状）
- [x] DIRECTORY.md §1/§3 tier 表/§3 例外条款、UPGRADE-RUNBOOK:51
- [x] ADR-0011 决策 5 导航注记
- [x] batches/diagnostics/design.md 登记表删三行 + 退役注记（**待责任人重签**）
- [x] CUSTOMIZATIONS.md 收敛（+4/-6）

### 待办

- design.md 确认日期补填（check_docs 当前报 `status 已确认 but 确认日期 is empty`——签认时遗漏，R10 用户侧字段）；
- batches/diagnostics/design.md 重签（正文改动：登记表 + 退役注记）；
- self-review（双 AI 评审）→ PR。

## 2026-10-30 双 AI 自审（实施态）处置（评审 AI：Deepseek-V4-Pro，无 blocker）

- **Major 1（C005 anchor 残留 launcher 描述）已修**——根因：C005 的 anchor 拼接自**两个**登记来源（生成器 :225-227 将所有 design 登记表行拼接），`batches/diagnostics/design.md` 已清但 `batches/tier-migration/design.md:92` 的登记行仍含 launcher 括注。处置：batches/tier-migration/design.md 登记行改写为事实同步版（`MODULE_ORDER` + 退役注记）→ 重跑生成器 → C005 收敛确认。batches/tier-migration/design.md 该处属事实同步性修正（登记指向的对象已消亡），提请责任人按非决策性勘误豁免重签；
- **Suggestion 2（C026/C027 tui 登记混入）接受**——两个 marker（`test_catalog_oracle.py:26`、`tui_helpers.py:1172`）在 HEAD 源码已存在但基线 CUSTOMIZATIONS.md 漏登记（tui 批次遗留 freshness 缺口），本批次 gen_customizations 被动补齐（不补则 CI freshness 门禁红）。混入接受，随本批次 PR 一并提交，PR 描述说明；
- **Suggestion 3（行数勘误）已修**——test_layering.py 实测净删除 19 行（含 2 空行），design R2 表已勘误；
- **Nit 4（UPGRADE-RUNBOOK:53 失效描述）已修**——stale 检测核对豁免边句改为"豁免通道已随 launcher 退役移除（ADR-0013），现存仅 kernel-private allowlist 为上游自有机制"。

## 2026-10-30（二）CI R3 抓获与修复：elif 误恢复

CI（PR）`check_r3_markers` 红：`test_layering.py: upstream diff adds 1 content line(s) with no AIxCoding marker`。根因复盘：

- **恢复不彻底**：diagnostics 批次当年除插入豁免块外，还把上游的**独立 `if _is_violation(edge):`** 改成了 `elif` 挂链（豁免边跳过 violation 判定所需）；本批次回滚时误恢复为 elif——两轮评审与开发 AI 均从 fork 内视角确认"elif 链恢复正确"，**无人对上游 merge-base 做零差异验证**（评审盲区，如实留痕）；
- **语义偏离**：挂链版使 kernel-private 豁免边短路 violation 判定，偏离上游"先观察、后独立判定"的双判结构；
- **R3 检查器的价值实证**：它按上游 merge-base diff 工作，恰好抓住 fork 内视角看不到的最后一行；"恢复原状彻底化"（diff 归零）是其天然放行条件——**检查规则无需修改**（责任人质询"是否改规则放行"的结论：不改，抓到的恰是恢复不彻底）。

修复：`elif _is_violation(edge):` → `if _is_violation(edge):`（恢复上游原状）。验证：

```
git diff 3104004947f87c6f5e10cc56824f8c265adc193b -- tests/architecture/test_layering.py
→ 零输出（文件相对上游基线完全一致）
uv run pytest tests/architecture -n0 -q → 1238 passed, 3 skipped in 147.20s
```
