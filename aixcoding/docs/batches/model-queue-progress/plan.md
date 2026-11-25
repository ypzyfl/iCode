# 任务清单：排队进度提示（model-queue-progress）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**实现、自审与实现评审完成（2026-11-18）**，提交 `43b005a5`。R2 首版 16 文件约 126 行；
2026-11-20 按独立评审 C1/C7 回填为 **17 文件，实测约 +191/−7**（含 manifest）。
实现评审的 2 个 blocker（放行后文案不释放、ACP 去重跨会话串号）已修；
2026-11-20 补 5 条前端轮次边界锚定（CLI TurnStarted / ACP 跨会话去重 / TUI handler→presenter / presenter→view / view adapter→WaitingRow）。

**2026-11-24 归位改造（design v1.3，已签认后实施）**：事件类移出 types.py、construction 工厂化、ACP 判重入包（claim/confirm）、CLI 体入包；净表实测 **16 文件 +198/−9**（上游 src 14 文件 +162/−7），并修复 PR #151 评审缺陷 1（ACP TurnStarted 重置）。验证见 verification.md 同日节。

**2026-11-25 变更单 v1.4 已签认并实施完成**：ACP 载荷加 `requestId`（D1 带 / D2 加 / D3 补，签认日 2026-11-25）。
id 取 `QueueRequestTracker.request_id`（应答尝试的 `Chrys-Request-Attempt-Id`），tracker 转发时回填
`QueueStatus.request_id` → 事件 → ACP 挂点；去重键 (requestId, position)；`frontend-api.md` 补契约（登记行
`frontend-api-doc`）；新增《模型排队桌面端透传说明.md》。验证：定制 77 + wait 57 + 上游 ACP 683 passed、
ruff/ty 三平台/check_docs/gen_customizations --strict 全绿；实施中修复 confirm 漏传 request_id 的去重失效缺陷。
详见 verification.md 同日节。

## 下一步（接续入口）

1. 真实网关 + 桌面端联调：桌面端同步改造后按 `requestId` 消费；联调须将桌面 `icode.binaries` 指向含本功能的构建
2. 双 AI 自审（self-review 追加一轮）与 PR 组装（§7 交付报告）

前置批次 `../model-queue-client/` 已完成并提交（design/ADR/self-review 均已签认），本批次依赖其 `src/chrys/service/aixcoding/llm_queue/queue_frames.py` 与 `chat_completions/client.py` 的接线；续接时先读该批次的 plan.md 与 verification.md。

## 待办

- [x] 数据通道调研（EventBus 不可达；两条既有上行通道）
- [x] 起草 requirements / design / test-plan / plan / ADR
- [x] 责任人签认 design.md 与 ADR（2026-11-19；2026-11-20 R2 回填后待重签）
- [x] 定制包 `src/chrys/kernel/aixcoding/queue_progress/`（文案分支）
- [x] 13 处上游接线 + `AIxCoding queue-progress:` 标记
- [x] 定制测试 `aixcoding/tests/llm/test_model_queue_progress.py`
- [x] verification.md + self-review.md
- [x] 本地提交（`43b005a5`）
- [x] 2026-11-20 补前端轮次边界锚定（C0）
- [x] 2026-11-20 回填 R2 实测行数 + manifest 行（C1/C7，待重签）
- [x] 2026-11-24 归位改造（design v1.3）：A 事件类出 types.py / B construction 工厂化 / C ACP 判重入包+TurnStarted 重置 / D CLI 体入包；`queue_notify.py`、`cli/queue_line.py` 落位；实测回填净表
- [x] 2026-11-25 v1.4（requestId 透传）：签认（D1带/D2加/D3补）→ 实施 → 验证（77+57+683 passed）→ 文档同步；待联调与双 AI 自审

## 挂起与备忘

- `queueSize` 不进 TUI/CLI 文案（2026-11-19 定案）；事件载荷与 ACP `queueSize` 字段仍保留。
- 若将来需要子代理级排队卡片，须另立事件（本事件刻意不带 origin，见 ADR 后果节）。
- 2026-11-20 独立评审：C2（tracker/guard 导入顺序）已在 client 批修复；C3（profile 固定 request_id 并发共享）已登记为使用约束。
