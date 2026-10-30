# 任务清单：auth 登录状态埋点（aixcoding.auth logging）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**实施完成（2026-10-30）**：批次恢复（launcher-retirement 后）→ design 重签（2026-10-30，聚合入口版，R2 批准）→ 待实施项①-⑤全部落地并验证全绿。剩余：新 diff 双 AI 评审 → self-review.md 签认 → PR（git 逐条请示）。

时间线：2026-10-29 首轮实施（12 埋点+测试+双 AI 评审）→ 10-30 备份暂存（launcher-retirement PR #69 先行）→ 10-30 恢复 + 补验（architecture 1238 补缺口）+ 外部 AI 评审文档收敛（M1/M2/M3① 处置）→ design 重签 → 实施接线（startup.py / ensure_file_sink / app.py +3 行 / test_entry_wiring 6 用例）→ 五项验证全绿。

## 待办

- [x] design.md 签认（2026-10-29 首签；2026-10-30 重签聚合入口版——含 R2 批准；实施期 marker 措辞/登记行落点格式适配已同步正文）
- [x] test-plan.md 起草
- [x] 实施：session.py 12 条埋点（含评审 A 修复：#9 冻结口径）
- [x] 新增 aixcoding/tests/auth/test_session_logging.py（12 用例 + F5 隔离 fixture + 评审 B/C/D/E 修复）
- [x] 验证：pytest 全绿（12/112/301）；launcher 落盘闭环实证；222 tests 无泄漏；ruff/ty/gen_customizations 全过
- [x] verification.md 落盘（含勘误：波折③ seed store 方向错误）
- [x] 恢复补验（2026-10-30）：auth 112 + architecture 1238（原缺口补上）+ 外部评审 M1/M2/M3① 文档收敛
- [x] 实施聚合入口：app/aixcoding/startup.py + ensure_file_sink + app.py main() 接线（+3 行唯一上游行）
- [x] 新增 aixcoding/tests/diagnostics/test_entry_wiring.py（6 用例）
- [x] 实施验证五条：单测全量 294 / architecture 1238 / 闭环直跑 icode 落盘实证 / gen_customizations 幂等（C003 入产物）/ ruff·format·ty
- [ ] F6 评审处置已随本批次改 DIRECTORY.md §3（相对导入语义澄清；2026-10-30 复核再修正为死锁结论）
- [ ] 新 diff 双 AI 评审（接线四文件）→ self-review.md 更新
- [ ] self-review.md 签认
- [x] #12-16 补录随本 PR 独立 commit（已裁决，内容从 git 43f05a9 找回，落 diagnostics/verification.md，含退役注记）
- [ ] PR（分支 feat/auth_logging，已建；commit 1 a0260250 + 补录 commit）——git 写操作逐条请示

## 挂起与备忘

- 落盘验收依赖 launcher 启动路径（`setup_logging` 仅 launcher 调用，design §假设表）；
- `feat/auth_logging` 分支名曾被旧分支占用后改名 `feat/ai_gates` 释放，建分支时若撞名再议；
- aixcoding/tests/ 下存在历史运行残留（`.pyc`、无扩展名数字文件），与本批次无关，未清理。

## design 阶段双 AI 评审记录（2026-10-29）

- 评审 AI：Deepseek-V4-Pro（独立会话，与开发 AI 不同源）；评审对象 design.md 草案（10 条版）。
- findings 6 条 + ehr PII nit，无 blocker。处置：F1 场景措辞同步 ERROR（修）；F2 假设表补 `install_log_handler` DEBUG 降级机制（修，已核 `screen.py:190-193`）；F3 兜底分支措辞精确化（修）；F4 `complete_login` 失败路径补 #11/#12（责任人裁决选 A）；F5 测试隔离 fixture（修，落 test-plan）；F6 消息全文定稿（修，design 埋点清单）；ehr PII 记录不打码（责任人维持）。
- 按 SELF-REVIEW-HOWTO，独立评审 AI（Deepseek-V4-Pro）+ 开发 AI 已构成双 AI 评审；若责任人另安排第二位评审 AI，结果追加于此。
