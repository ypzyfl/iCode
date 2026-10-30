# 验证：aixcoding/tests 的 ruff 豁免切换为目录级配置

> R7 落盘形态：命令 + 输出摘要，追加不删旧。

## 2026-10-30 实施批次（本地，CodeBuddy / UV_PYTHON=3.14.3）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run ruff check aixcoding/` | **All checks passed!**（目录行生效，29 个删头/收窄文件零新暴露） |
| 2 | `uv run ruff format --check aixcoding/` | **154 files already formatted**（删行未破坏格式） |
| 3 | `uv run ruff check src/ tests/` | **All checks passed!**（上游豁免格局不变） |
| 4 | `uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q` | **293 passed, 2 skipped, 1 failed**；唯一失败 `test_mock_launcher.py::test_every_starter_round_trips`（WinError 10048 端口占用）为已知环境性失败（本机 7777 被 ArmouryCrate 常驻占用；PR #70 本地预跑同款记录在案，CI Linux 绿） |
| 5 | `uv run python aixcoding/tools/gen_customizations.py`（连跑两次） | 两次输出一致（29 custom points）：幂等 ✓；warning 仅剩 auth 批次既有项（`wire_client.py` designed-not-implemented） |
| 6 | `git diff --stat aixcoding/docs/CUSTOMIZATIONS.md` | 53 行变更：新定制点 C003 插入 + 后续编号顺移（生成产物机制性行为） |
| 7 | `uv run python aixcoding/tools/check_docs.py` | **check_docs: OK**（13 ADR / 13 design / 10 self-review） |
| 8 | `git status --short` + `git diff --stat` 总览 | 上游仅 `pyproject.toml` +2；`aixcoding/tests` 28 文件各 -1、`test_check_import_boundaries.py` ±1（收窄 RUF002）；`CUSTOMIZATIONS.md` 生成产物；管线文档目录未跟踪。**与 R2 清单逐项吻合，无越权文件** |

实施波折记录：①`gen_customizations.py` 首跑拦截 marker 无登记行——`classify_marker_body` 优先取括号内含 `aixcoding` 的路径作 module，原 marker 无括号回退提取 `custom` 无法匹配登记落点；修正 = marker 补 `(aixcoding/tests)` + design 登记落点改 `aixcoding/tests/`（tui 批次同构先例），批准实质零变更（design 实施期修正记录留档）。②首次验证因 `.python-version` 钉 3.14.8 本机无此版本，按本地配方 `set UV_PYTHON=3.14.3` 重跑（既定解法）。

## 待 CI 验证

- PR 创建后 AIxCoding Tests（含 step `ruff check aixcoding/` / `format --check aixcoding/` / pytest）+ Upstream CI 双绿——CI 证据归属 PR checks 本身（DEVELOPMENT.md §7），不回写。

## 2026-10-30 peer review（PR #71）处置追记

评审侧副本复现全部门禁 + 破坏性实验（注释目录行 → 恰 29 文件 772 处违规，恢复复绿——"删头即内建回归锚"实证）+ CI 实况（18 run 全属 head `bcba89a7`，17 success / 1 in_progress）。三项数字候选处置（责任人均裁决按建议）：

- **C1**（表 #2 `154 files` vs head 树 165）：154 为实施时点工作区计数（当时 `ruff-test-exemptions/` 仅 4 件 md、verification/self-review 未落盘）；ruff format 的 files 计数含 md（include 规则），head 树 165 = 52 py + 113 md。时点性文件集差异，exit 0 结论评审已独立复核成立，非结论缺陷。
- **C2**（self-review F2 孤儿注释 10 vs 16）：16 成立（17 个带理由注释文件 − `diagnostics/conftest.py` 无 noqa 头非孤儿；首轮评审 AI 列举不全）——口径修正见 self-review 追加记录。
- **C3**（表 #7 `10 self-review` vs 11）：时序性——#7 落盘时本批 self-review.md 未产出；最新计数 `check_docs: scanned 13 ADR(s), 13 design(s), 11 self-review(s)`，OK（R7 追加机制内，旧计数留痕）。
