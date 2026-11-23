# 任务清单：排队进度提示（model-queue-progress）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**实现、自审与实现评审完成（2026-11-18）**，提交 `43b005a5`。R2 首版 16 文件约 126 行；
2026-11-20 按独立评审 C1/C7 回填为 **17 文件，实测约 +191/−7**（含 manifest）。
实现评审的 2 个 blocker（放行后文案不释放、ACP 去重跨会话串号）已修；
2026-11-20 补 5 条前端轮次边界锚定（CLI TurnStarted / ACP 跨会话去重 / TUI handler→presenter / presenter→view / view adapter→WaitingRow）。

## 下一步（接续入口）

1. 责任人重签 `design.md`（R2 表新增 manifest 行并回填实测行数，2026-11-20）
2. 责任人签认 `self-review.md`（若 R2 回填需要）
3. 真实网关联调：TUI 等待行文案、CLI 去重行、ACP `chrys/queue_status` / `released`
4. 可选：完整 Smart Test（已用宽目录集替代覆盖）

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

## 挂起与备忘

- `queueSize` 不进 TUI/CLI 文案（2026-11-19 定案）；事件载荷与 ACP `queueSize` 字段仍保留。
- 若将来需要子代理级排队卡片，须另立事件（本事件刻意不带 origin，见 ADR 后果节）。
- 2026-11-20 独立评审：C2（tracker/guard 导入顺序）已在 client 批修复；C3（profile 固定 request_id 并发共享）已登记为使用约束。
