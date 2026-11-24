# 批次1 self-review：telemetry-after-turn-slice

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-23
- 确认意见：无特别意见
- 开发 AI：CodeBuddy / BM:GLM-5.3
- 评审 AI：CodeBuddy / DeepSeek-V4-Pro（责任人中转，三轮——2026-11-23 终审前独立评审轮 + 同日签认后
  补审轮 + 2026-11-24 CI 修复轮独立复审，与开发 AI 不同源）

> 签认前提（按批次流程）：① 六件套齐备（本文件为最后一环）；② verification 证据闭环（判别实验/四步实施/边界矩阵/评审处置全部实际执行，见 verification.md）；③ 双 AI 评审已齐备（2026-11-20 责任人签认 requirements/design=R2 批准；2026-11-23 独立评审 AI 终审前轮**无 blocker**，F1 裁决=A 预留批次2、F2/F3/F4 已修）。**三前提均满足，待责任人签认。**

## 交付摘要

上游 R2 四文件（turn_state/runner/finalizer/session_lifecycle，marker×7 对账）+ 定制包 `service/aixcoding/telemetry/`（notice/owner/reader/analyzer/dto/filtering/client/reporter）+ mock 1A 单端口组合（combined.py，:15678）+ mock 1B telemetry 存储（三 save 幂等+join+BR-1 捕获钩子）+ 产品端配置三处 local 默认统一 15678（定制层文件，R2 批准免 marker）。

## 关键设计输入（判别实验实证，已内建产品实现）

1. reader 过滤键=exchange/操作 ID 归属（turn 编号 rollback 后撞车，V1-b）；
2. Phase 4 后 session-only 不足，A-final 须 trajectory exchange facts 补全（V3）；
3. dispatcher 合并键三元组含 session 维度（V2 实证必要）；
4. 过滤键=model_profile_id（profile 文件名，非 model id——调试实证）。

## 边界与降级（如实声明）

- ai-code blocks 为内容引用形态（B8 逐字段细化留批次3 前复核）；
- 无 state_store 时 session_dir 全局回退（非 None）——skip 由 saved=False 兜底保证，全局目录零 telemetry 写入（边界测试实证）；
- trajectory disabled 的 LEASE_HELD 途径未覆盖（NO_SESSION_DIR 形态已覆盖；见 test-plan §3）；
- mock 通过≠真实后台通过（独立内网门禁不变）；
- 主链外的场景（ACP/parity/compaction 完整矩阵）按计划属批次2/3。

## 验证汇总（详见 verification.md）

判别实验 5 passed；owner/notice 6；mock 契约 94+2 skipped（含 1B 七项）；管线+边界端到端 47 passed（含真流量 BR-1 join 闭环）；上游回归 1401+1675+560 零失败；gen_customizations --strict OK（110 rows/161 markers/0 warning）；check_docs/format/diff 全绿。

## 评审记录

- 2026-11-20：requirements/design 责任人签认（design 签认=R2 批准七文件+D1 清单）。
- **2026-11-23 独立评审 AI 轮（终审前）**：另一 AI（模型标识未提供，报告由责任人转交；按 `SELF-REVIEW-HOWTO.md` §二 三阶段模板执行）。**结论：无 blocker**。第一阶段认可方向（最小垂直切片+mock 契约 oracle）、四项关键决策（单端口 15678/run-owned 快照/同步只入队/fail-closed 过滤）、实现保真（A-final 选取、V1-b 双层防串接、BR-1 语义逐项核对，新增 import 逐一反向验证）；第二阶段扫描无幻觉 API/无静默吞错/测试非 vacuous（反证法抽验）/出站字段与 allowlist 对齐；第三阶段流程合规（临时方案/R2 比对/R1 归属/R11 依赖/closure）全过。Findings 4 条（F1 suggestion：`notice.status` 本批零消费——预留批次2 或本批体现待责任人裁决，已按"预留批次2"加注释标注；F2/F3/F4 nit：marker 注释路径统一为 service 层实际落位、owner docstring 更新为已接线状态、`_pending` 生命周期注释+reporter 类型标注——三项零行为变更已修复，回归通过见 verification）。评审方声明：与开发 AI 不同源、可能共盲、终裁在责任人。
- 双 AI 评审轮次齐备（本节 + 责任人签认链），具备本文件签认条件。
- **F1 裁决（责任人，2026-11-23）：选 A——`notice.status` 预留批次2**（1001/turn 级记录载体；notice.py 注释即此语义，批次2 design 复核后再定消费形态；不删除、本批不另加消费点）。
- **F1 二次裁决（责任人，2026-11-23）：改判——`notice.status` 整个字段移除、记录在案**。理由：turn 终态（failed/interrupted/ok，含"用户中断"）在 0.28.0 定制基线中无此上报、需批次2 新建 turn 级接口（selected-Agent 1001）方能承载；新版本数据上报不需要此信息。处置：①`finalizer.py` 回退 `interrupted` 参数（调用点/签名/status 表达式）与 `status` 字段；②`notice.py` 删除 `status` 字段、注释记录移除理由与再引入条件；③测试 `test_owner_notice.py`/`test_telemetry_fault_tolerance.py` 同步去掉 `status="ok"`。原则：上游改动最小化，非必要不改上游代码。
- **签认后改动补审轮（独立评审 AI，2026-11-23，提示词由开发 AI 出具、责任人转交）**：轻量复审两处签认后改动（F1 二次裁决 status 移除回退 + `trajectory_wait_manifest` 恢复——后者系提交前复查发现的架构守卫缺口，独立评审轮验证范围未覆盖）。**结论：无 blocker，可进入提交流程**；检查点 A-F 全过；1 条 nit（verification.md R2-3 历史记录缺二次裁决交叉标注）已补注处置。评审方与开发 AI 不同源、可能共盲、终裁在责任人；验证数字未重跑，基于静态核对。
- **CI 修复轮独立复审（独立评审 AI DeepSeek-V4-Pro，2026-11-24，报告由责任人转交、标识经其确认）**：对象为 PR #144 第三轮 CI 的 ty 修复（`finalizer.py` / `session_lifecycle.py` 的 `session_id` 为 None 跳过守卫、design.md R2-4 量级 12–26、`trajectory_wait_manifest` 表达式同步）。**结论：Good，无阻塞项**——认可改动符合「宁缺毋错」口径，`session_dir` 类型为 `Path | None` 无需额外守卫，行数估算与实际一致。1 条可选建议（`session_lifecycle.py` 把 `get_telemetry_owner()` 移入 `session_id is not None` 守卫内，避免无 id 时无谓初始化惰性单例）**已采纳**——行数不变、manifest 表达式不变。复审之后的 design.md §2 两小表合并（消除 R2 门禁无害警告，责任人裁决）不在本次复审范围内。报告未说明是否重跑验证。复审之后按责任人裁决补 `test_engine_teardown.py`（经真实 engine 入口断言 teardown 的 telemetry 分支，见 verification.md），同样不在本次复审范围内。
