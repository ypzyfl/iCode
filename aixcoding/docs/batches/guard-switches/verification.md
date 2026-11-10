# 验证：安全护栏运行期开关（guard switches）

> 追加不删旧。本文件由 parallel-batch-governance 批次于 2026-11-10 补建；PR #98 合并时
> verification.md 缺失，以下仅为本批实际重跑结果，不回填或伪造 2026-11-05 的历史验证结论。

## V1（2026-11-10 补做验证）

环境：Windows 11，Python 3.14.10；大写盘符进入仓库，清空 `PYTHONPATH`，设置 `PYTHONUTF8=1`。

| # | 命令 | 实际结果 |
|---|---|---|
| 1 | `uv run python -m aixcoding.tests.guard.guard_pack_selftest` | **Ran 101 tests，OK（skipped=1），1.352s** |
| 2 | `uv run pytest aixcoding/tests/guard -n 0 -m "not integration and not gc_calibration"` | **26 passed, 1 skipped in 4.76s** |
| 3 | 用 `tempfile.TemporaryDirectory()` 创建隔离 hooks 目录，调用 `install_guard_hooks(hooks_dir=...)`，再通过 `AIXCODING_GUARD_HOOKS_DIR` 运行 `aixcoding/tests/guard/verify_guard_deployed.py` | **共 64 条，失败 0 条**；临时目录已清理，未触碰用户实际配置 |

补做核销：

- 出厂不限制与 `workspace restrict` 限制态均由规则自检覆盖；
- 安装器、payload、打包和上游锚点由 pytest 覆盖；
- 部署副本的 MANUAL_TESTS 机器用例 64 条全部通过；
- ADR 已迁为全局 ADR-0023。ADR 与 self-review 的第二 AI 评审、责任人补签不属于本验证的已通过事项。

## V2（2026-11-10 评审与签认补记）

- GLM-5.3 完成独立实施评审，确认代码与测试无 blocker；责任人确认 ADR-0023 和 self-review 均为本人于 2026-11-10 签认，并接受该报告作为 guard 迁移与历史补件范围的第二 AI 评审。
- 评审 F1：self-review 头部与正文/计划矛盾，已补记 GLM 评审、清除待评审表述并同步两份 plan。
- 评审 F3：责任人接受 parallel-batch-governance 已签 design 与 ADR-0024 决策五的明确迁移授权作为 R10 书面依据，不修改 guard design 签认头。
- 处置后实际运行 `check_docs.py --closure`：guard、ADR-0023 及其全部引用均无阻断；唯一剩余项是 parallel-batch-governance 自身 self-review 草案，待 GLM 复审与责任人签认。
