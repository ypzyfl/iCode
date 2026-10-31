# 任务清单：本地诊断包（aixcoding diagnostics）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**任务完成**（commit 7bd6d45 已推送，CI 第五连胜全绿）：五模块 + 两处上游登记 + 29 测试 + 清单 C001-C005 + 双 AI 评审收敛（self-review 已签认 2026-10-25）。剩余为试运行期人工验证项（F6 面板实测、launcher 真实启动，见 verification 未验证事项）。

## 待办

- [x] test-plan.md 责任人确认（2026-10-25）
- [x] 五模块实施（config / logging_support / crash / snapshot / launcher）
- [x] `screen.py` + `test_layering.py` 上游登记（R2 批准+重签）
- [x] 定制测试 29 用例（含行为锚定）
- [x] 清单收敛（C001-C005，0 警告）
- [x] 双 AI 评审 → self-review 签认 → 提交 7bd6d45 → push → **CI success**
- [ ] 试运行期：F6 面板人工实测 + launcher 真实启动冒烟（不阻塞阶段二 DoD）

## 挂起与备忘

- 面板 anchor 依赖上游 `_TuiLogHandler` 挂 root、`MODULE_ORDER` 派生白名单——design 假设表在案，锚定测试锁定，失效转纯落盘降级；
- 快照脱敏字段清单：白名单式（版本/平台/开关），禁止 env 全量 dump；
- 配置文件是定制层共享基建：后续定制功能的"启动前手动可改设置"扩展 `aixcoding.toml`，不另建配置（design 定位）。
