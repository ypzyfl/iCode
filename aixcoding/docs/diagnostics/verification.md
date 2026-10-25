# 验证证据：本地诊断包（aixcoding diagnostics）

> 活文档：命令 + 输出摘要（R7 落盘形态，追加不删旧）。

## 2026-10-25 实施完成验证

环境：Windows，`PYTHONPATH=`、`PYTHONUTF8=1`、`UV_PYTHON=3.14.3`。

| # | 命令 | 结果摘要 |
|---|---|---|
| 1 | `uv run pytest aixcoding/tests -n0 -q` | **82 passed**（tools 53 + diagnostics 29：config 6 / logging 6 / 面板锚定 4 / crash 6 / snapshot 5 / launcher 2） |
| 2 | `uv run python scripts/chrys_test.py --smart --paths src/chrys/app/tui/screens/logs/screen.py` | 上游常规 **10172 passed, 76 skipped**（7:26）+ 架构 433 中 1 failed → 触发 R2 扩表（见 #4） |
| 3 | （R2 扩表批准后）`uv run pytest tests/architecture/test_layering.py -n0 -q` | **223 passed**（TIER_ORDER 注册 + DAG 边豁免 + stale 检测三机制生效） |
| 4 | `uv run ty check --error-on-warning --python-platform {linux,win32,darwin} src/chrys/aixcoding` | 三平台 All checks passed（修复 3 个诊断：getLevelName 弃用重载→_LEVEL_BY_NAME 映射；args.thread None 联合→显式判空；_fh_target object→IO[bytes] 类型化） |
| 5 | `uv run ruff check src/chrys/aixcoding aixcoding` / `ruff format --check` | All checks passed |
| 6 | `gen_customizations.py` | **5 custom points, 0 warnings**：C001 AGENTS.md / C002 screen.py:67 / C003-C005 test_layering.py 三处标记（tier 注册、边豁免表、豁免接线）——diagnostics 5 条"缺标记"警告全部收敛 |
| 7 | 四工具分叉点门禁（`--base 3104004`） | R2：upstream_changed=2（AGENTS.md+screen.py）⊆ approved_pool=3 ✓；R3：2 文件均带标记 ✓；import 边界：1066 文件 OK |

实施要点：
- `src/chrys/aixcoding/diagnostics/` 五模块（config / logging_support / crash / snapshot / launcher）+ 包锚点，全部 stdlib；
- `screen.py` MODULE_ORDER 一行（R3 标记在行尾）；`test_layering.py` ~20 行登记（R2 扩表批准：tier=1 注册 + `_DAG_EDGE_ALLOWLIST` 边豁免含 stale 检测）；
- **stale 检测首战立功**：launcher 原以变量传模块名（`import_module(module_name)`），DAG 采集器只见字符串常量 → 豁免边对不上 → 改为显式常量调用（依赖对架构检测诚实可见）；
- launcher→app 依赖为 R9 登记豁免（design 登记预告表 launcher 行，anchor=入口签名）。

## 2026-10-25 双 AI 评审修复轮

评审 0 blocker / 1 suggestion / 5 nit，修 1 留 5（处置见 self-review.md）：

| # | 命令 | 结果摘要 |
|---|---|---|
| 8 | F2 修复后 `ruff format/check src/chrys/aixcoding` + `ty check linux` + `pytest aixcoding/tests -n0 -q` | All checks passed ×3 / **82 passed** |

## 2026-10-25 提交与 CI（push 7bd6d45）

- commit `7bd6d45`（21 files，+900/-17）推送；**Aixcoding Tests completed/success**（第五连胜，含本批 diagnostics 29 用例、R2/R3 对 screen.py+test_layering.py 标记的分叉点门禁核对、清单幂等 C001-C005）。

## 2026-10-25 试运行期人工项（阶段二收官后补做）

| # | 命令 | 结果摘要 |
|---|---|---|
| 9 | `uv run python -m chrys.aixcoding.diagnostics.launcher --version` | 输出 `0.31.0`，干净退出——**launcher 真实启动冒烟通过**（装钩子→调上游入口 dispatch→无干扰） |
| 10 | 产物核验 | `%APPDATA%\chrys\aixcoding-diagnostics\20261025T090305Z-28268\` 产生 `faulthandler.txt` + `snapshot.txt`（Windows 平台 config_dir 为 `%APPDATA%\chrys`，platform 层定义）——钩子与快照全链路真实工作 |

## 2026-10-25 F6 面板目视（责任人实测，最后一项闭环）

| # | 操作 | 结果 |
|---|---|---|
| 11 | TUI（`uv run icode`，UV_PYTHON=3.14.3）按 F6 | **aixcoding tab 存在（chrys 之后），空态渲染正常**——MODULE_ORDER 白名单接线目视通过；空态符合预期（无业务消费者，与 httpx 空请求时空 tab 行为一致；内容链路由 test_tui_handler_buffers_aixcoding_record 行为锚定机检覆盖，阶段三 telemetry 接入后自动有实时日志）。运行环境注记：uv 0.13.x 下载清单无 3.14.8，本机以 UV_PYTHON=3.14.3 等价运行。 |

## 未验证事项

- （清零——阶段二全部验证项闭环。）
