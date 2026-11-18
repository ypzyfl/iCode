# 任务清单：排队进度提示（model-queue-progress）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**已实现并提交（2026-11-18），验证未全跑**。责任人要求先提交、后续继续。R2 最终 16 文件约 123 行（含追加的 `ports.py`、`main_screen_presenter.py` 与测试替身）。

## 下一步（接续入口）

1. 跑 `tests/app/tui`、`tests/app/cli`、`tests/orchestration/engine` 与完整 Smart Test（本轮被取消）
2. 三平台 `ty` 与 `verify.py --smart`
3. 真实网关联调：TUI 等待行文案、CLI 去重行、ACP `chrys/queue_status`
4. `self-review.md`（双 AI 评审）→ 签认

前置批次 `../model-queue-client/` 已完成并提交（design/ADR/self-review 均已签认），本批次依赖其 `src/chrys/service/aixcoding/llm_queue/queue_frames.py` 与 `chat_completions/client.py` 的接线；续接时先读该批次的 plan.md 与 verification.md。

## 待办

- [x] 数据通道调研（EventBus 不可达；两条既有上行通道）
- [x] 起草 requirements / design / test-plan / plan / ADR
- [ ] 责任人签认 design.md 与 ADR
- [ ] 定制包 `src/chrys/kernel/aixcoding/queue_progress/`（文案分支）
- [ ] 13 处上游接线 + `AIxCoding queue-progress:` 标记
- [ ] 定制测试 `aixcoding/tests/llm/test_model_queue_progress.py`
- [ ] verification.md + self-review.md
- [ ] 本地提交

## 挂起与备忘

- `queueSize` 是否展示待联调确认（当前只用 position）。
- 若将来需要子代理级排队卡片，须另立事件（本事件刻意不带 origin，见 ADR 后果节）。
