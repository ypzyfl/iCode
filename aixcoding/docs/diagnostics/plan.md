# 任务清单：本地诊断包（aixcoding diagnostics）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

实施完成：五模块 + screen.py 一行 + test_layering.py 登记扩表（R2 扩表已获负责人批准 2026-10-25，**design R2 表已扩待重签**）；82 定制测试 + 10172 上游回归 + 223 架构测试 + ty 三平台全绿；清单 5 定制点 0 警告。待：design 重签 → 双 AI 自审 → self-review 签认 → 提交。

## 待办

- [x] test-plan.md 责任人确认（2026-10-25）
- [x] `config.py` / `logging_support.py` / `crash.py` / `snapshot.py` / `launcher.py` 五模块
- [x] `screen.py` MODULE_ORDER 一行 + R3 标记
- [x] `test_layering.py` 登记扩表（tier=1 注册 + DAG 边豁免 + stale 检测）——R2 扩表批准（2026-10-25）
- [x] 定制测试 `aixcoding/tests/diagnostics/`（29 用例，含行为锚定）
- [x] gen 重生成（5 定制点 0 警告：C001-C005）
- [x] verification.md 留证（#1-#7）
- [ ] design.md 重签（R2 表扩行触发，责任人）
- [ ] 双 AI 自审 → self-review.md → 签认 → 提交 → push（CI 全链路第五连胜验证）

## 挂起与备忘

- 面板 anchor 依赖上游 `_TuiLogHandler` 挂 root、`MODULE_ORDER` 派生白名单——design 假设表在案，锚定测试锁定，失效转纯落盘降级；
- 快照脱敏字段清单：白名单式（版本/平台/开关），禁止 env 全量 dump；
- 配置文件是定制层共享基建：后续定制功能的"启动前手动可改设置"扩展 `aixcoding.toml`，不另建配置（design 定位）。
