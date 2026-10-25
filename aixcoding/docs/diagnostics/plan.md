# 任务清单：本地诊断包（aixcoding diagnostics）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

管线文档齐备（requirements / design[已签认 2026-10-25，R2 生效] / test-plan / plan），实施未启动。test-plan 待责任人确认后开工。

## 待办

- [ ] test-plan.md 责任人确认（活文档，不签认）
- [ ] `config.py`：~/.chrys/aixcoding.toml 解析（tomllib 只读、fail-safe 默认）
- [ ] `logging_support.py`：aixcoding.* logger 工厂 + RotatingFileHandler 落盘恒开 + propagate 开关
- [ ] `crash.py`：faulthandler + sys/threading excepthook + atexit 兜底
- [ ] `snapshot.py`：环境快照（脱敏）
- [ ] `launcher.py`：python -m 装钩子后调 chrys.app.cli.app:main
- [ ] `screen.py` MODULE_ORDER 一行 + R3 标记（R2 已批，行尾注释）
- [ ] 定制测试 `aixcoding/tests/diagnostics/`（见 test-plan 矩阵）
- [ ] 实施后重跑 gen_customizations（5 条"缺标记"警告应收敛为 C002 定制点）
- [ ] verification.md 留证 → 双 AI 自审 → self-review 签认 → 提交

## 挂起与备忘

- 面板 anchor 依赖上游 `_TuiLogHandler` 挂 root、`MODULE_ORDER` 派生白名单——design 假设表在案，锚定测试锁定，失效转纯落盘降级；
- 快照脱敏字段清单：白名单式（版本/平台/开关），禁止 env 全量 dump；
- 配置文件是定制层共享基建：后续定制功能的"启动前手动可改设置"扩展 `aixcoding.toml`，不另建配置（design 定位）。
