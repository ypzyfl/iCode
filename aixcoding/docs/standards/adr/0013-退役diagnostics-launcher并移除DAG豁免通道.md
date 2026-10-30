# ADR-0013：退役 diagnostics launcher 并移除 DAG 豁免通道

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-XXXX 取代）——括号内即后继编号（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-30
- 确认意见：豁免机制是升级摩擦的永久来源，需尽量避免

> 本文为决策时点快照；现行规则以 `DIRECTORY.md §3` 与 `DEVELOPMENT.md §6` 为准。

## 背景

diagnostics 批次（ADR-0011 决策 2/5）为 launcher 在上游 `test_layering.py` 建立 `_DAG_EDGE_ALLOWLIST` 豁免机制（kernel 层 launcher → app 层 CLI 入口的结构性挂接边，约 18 行登记）——是定制层在上游测试文件的唯一足迹。2026-10-30 auth-logging 批次确立全模式落盘接线（上游 CLI 入口 `main()` 调 `ensure_file_sink()`）后，launcher 的落盘职责被取代；其独占能力仅剩 crash 捕获（faulthandler/excepthook，全生命周期）与启动环境快照。

## 决策

**退役 launcher 全家（launcher/crash/snapshot，约 220 行定制代码 + 三个测试文件）并整体移除 `_DAG_EDGE_ALLOWLIST` 豁免机制（不留空表）**，换取上游测试文件足迹归零。落盘能力由入口接线全模式承担；crash 捕获与快照能力放弃（不建替代方案）。

## 理由

责任人价值取向（2026-10-30 裁决）：**最小上游足迹优先于可选能力**——豁免机制是升级摩擦的永久来源，而 crash/快照是尚未有消费者的 opt-in 能力。（评审补注：这是**价值取舍**而非"崩溃捕获价值低"的事实判断——faulthandler 类兜底能力的价值恰在无日常消费者的事发时刻兑现；本决策是该能力在与足迹清零的权衡中让位。）被否备选的死因：

- **迁移 app 层**（launcher 落 `app/aixcoding/` 按 ADR-0011 判据正位、消除豁免边、保留全部能力）：认真考虑后被否——迁移后 `test_layering.py` 仍需联动（豁免机制处置/条目变更），未达"零足迹"目标，且挂接模块需持续维护；正位收益不足以抵消足迹残留。
- **保留现状**：豁免机制长存，与最小足迹取向冲突。

## 后果

- 上游测试文件（`test_layering.py`）恢复定制前原状；上游产品代码足迹保持为零（本就为零）；
- **将来结构性挂接边需求出现时（进程入口/钩子注册类向上 import），无现成豁免通道**——**既定替代路径是内联接线**（挂接模块按 ADR-0011 判据落 app 档，或入口直接调用——auth-logging 批次的 `ensure_file_sink` 入口接线即先例）；豁免通道原则上不再重建，仅当内联确不可行时再从 git 历史复原本决策移除的实现；
- 将来需要 crash 捕获/环境快照时，从 git 历史重建（本决策为纯删除，revert 即得）；
- ADR-0011 的决策 5（豁免保留与管控）实例消亡——tier 落位体系本身不受影响；DIRECTORY.md §3"例外（结构性挂接边）"条款随之改写（通道移除注记）；
- 后续消费者的诊断基线：`config.py` + `logging_support.py`（含 `ensure_file_sink`）为落盘全部基建。
