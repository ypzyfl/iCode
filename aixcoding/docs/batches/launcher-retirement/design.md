# 设计：退役 diagnostics launcher（launcher-retirement）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-30
- 确认意见：豁免机制是升级摩擦的永久来源，在这里代价大于收益

## 方案概述

删除三件（`launcher.py` 59 行 / `crash.py` 110 行 / `snapshot.py` 49 行，launcher 是后两者唯一调用方）+ 三测试（`test_launcher` / `test_crash` / `test_snapshot`）+ conftest 孤儿 fixture（`tests/diagnostics/conftest.py` 的 `restore_hooks`——crash 测试专属 excepthook 隔离，2026-10-30 残留核查发现，连同 `sys`/`threading` import 删；`aix_logger_state` 保留）+ `logging_support.py` docstring 措辞更新（评审 Major 1：`:14` "the launcher is not required" 退役后失真，改为入口接线表述），回滚上游 `test_layering.py` 的 `_DAG_EDGE_ALLOWLIST` 豁免机制（净删除 19 行 = 代码 17 + 空行 2，不留空表——空机制是死代码；行号精确归属见 R2 表），规范与文档联动四处 + 定制清单重生成。保留 `config.py` / `logging_support.py`（全模式落盘接线的依赖）。决策依据与被否备选固化于 **ADR-0013**（standards/adr/，全局池——豁免通道移除与能力退役超出本特性范围）。

```
退役前                                          退役后
diagnostics/                                    diagnostics/
├─ config.py        保留                        ├─ config.py        （落盘配置，接线依赖）
├─ logging_support  保留                        ├─ logging_support  （get_logger/setup/ensure_file_sink）
├─ launcher.py ─────┐ 删除                      └─ __init__.py      （docstring 更新）
├─ crash.py ────────┤ 删除（launcher 独占）    test_layering.py：豁免机制整体回滚（零足迹）
├─ snapshot.py ─────┘ 删除（launcher 独占）    上游入口接线（auth-logging 批次）承担全部落盘
└─ __init__.py      docstring 更新
```

## 备选方案对比

| 方案 | 优点 | 缺点 | 上游足迹 | 结论 |
|---|---|---|---|---|
| **去除（本方案）** | 上游测试文件足迹清零；定制层减 ~220 行维护面 | 放弃 crash 捕获/快照/打包入口（ADR-0013 记录；git 历史可重建） | **归零** | **采用**（责任人 2026-10-30 裁决：最小上游足迹优先） |
| 迁移 app 层 | 消除豁免边（launcher 落 app 正位）；保留全部能力 | 仍需动 `test_layering`（豁免条目/机制处置）+ 挪动改写 + 持续维护挂接 | 测试文件仍有联动 | 否（认真考虑后被否——未达"零足迹"，死因见 ADR-0013） |
| 保留现状 | 零工作量 | 豁免机制长存 | 18 行长存 | 否 |

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `tests/architecture/test_layering.py` | 回滚 `_DAG_EDGE_ALLOWLIST` 机制，**精确到行**（评审 Blocker 修正：`:220` 的 `observed_private_import_exemptions` 是上游原状——服务 kernel-private 豁免的 stale 检测，不得触碰）：字典 `:87-93`（7 行）、观察集合声明 `:221`（1 行，fork 新增的 `observed_dag_edge_exemptions`）、收集点 `:242-244`（3 行）、stale 检测 `:257-262`（6 行），含两处 AIxCoding marker 注释；**另含 `:233` 挂靠形状恢复**（diagnostics 批次曾把上游独立 `if _is_violation` 改为 elif 挂链，回滚时误恢复——CI R3 与 peer review C1 双路径抓获后改回，文件相对上游基线 diff 归零） | -19（净删除；numstat +1/−20，勘误记录见 verification 勘误段） | 无新增 marker |

R1 自查：纯删除性回滚，无新增接线；上游产品代码零接触（此前亦为零）。**实施前按 R2 流程向负责人确认本表（批准落盘 = 签认本文档）。**

## 对上游隐式行为的假设

无新增依赖：本批次只删不改；`config.py`/`logging_support.py` 的既有假设（diagnostics 批次已钉）不变。与 auth-logging 批次的 app.py 接线正交（接线不引用 launcher）。

## 定制点登记预告

`CUSTOMIZATIONS.md` 变更（`gen_customizations.py` 重生成），**顺序依赖**（评审 Major 2）：`C025`（`test_layering.py:87`）/`C026`（`:243`）marker 回滚后自动消失；但 `C005`（`screen.py:67`，保留）的 anchor 字段汇总自 `batches/diagnostics/design.md` 定制点登记预告表（含 launcher/crash/snapshot 描述）——**须先改 `batches/diagnostics/design.md` 登记表（删三行，随其重签）→ 再重跑生成器**，`C005` 的 anchor 才会正确收敛到 config/logging 两项。无新增登记。**有 freshness 义务**（产物变更随提交，连跑两次幂等）。

## 风险与最坏情况

- **对 auth-logging 的时序关系**（责任人三次裁决演化：①2026-10-29"所有模式必须有日志"→②评审 Major 3 升级"实施与合并均硬前置"→③**2026-10-30 终裁：实施独立先行（已完成）+ 本批次先行合并，空窗期接受，auth-logging 尽快跟进**）——空窗期影响评估在案：auth 埋点从未进过主干、无用户可见影响，仅为语义空窗（`aixcoding.log` 在 auth-logging 接线合并前无挂载者）；
- **将来需要 crash 能力**：git 历史可完整找回（本批次为纯删除）；将来结构性挂接边需求出现时需重建豁免通道（ADR-0013 已记录此义务的边界）；
- 回滚本批次 = git revert 纯删除，零残留风险。

## ADR 判定

①被认真考虑但否决的备选（迁移 app 层）——**是**；③约束未来工作模式（"为什么没有 crash 捕获/豁免通道"后来者必问）——**是**；②撤销代价（能力放弃，可重建）边缘。触发 → **出 ADR-0013**（`standards/adr/`，全局池：豁免通道移除属架构工具变更 + 能力取舍属价值取向，超出特性目录归档范围）。ADR-0011 不整体取代（tier 体系不变），其决策 5 的实例消亡由 0013 背景回指说明。

## 验证方式

1. `uv run pytest tests/architecture -n0` 绿（豁免机制回滚后 DAG 断言无 stale 报错）；
2. `uv run pytest aixcoding/tests -n0` 绿（config/logging_support/panel_anchor 保留完好）；
3. `uv run python -m chrys.kernel.aixcoding.diagnostics.launcher` → 报 `No module named ... launcher`（入口消亡确认）；
4. `gen_customizations.py` 连跑两次 `git diff` 第二次为空；
5. ruff/ty 门禁（删除后无悬挂引用：全仓 grep `launcher|crash|snapshot` 于 diagnostics 语境零残留）。
