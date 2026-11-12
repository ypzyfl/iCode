# 任务清单：PR 门禁按需触发分层

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

实施与本地验证完成（2026-11-12）；批次六件齐。待外部 AI 评审实施 diff → 收敛后签认
（新 ADR + upstream-ci/ci-gate design 重签 + self-review）→ 走特性分支 PR 流程。

## 待办

- [x] 新增 `aixcoding/tools/ci_impact.py` 分类器（决策 1 规则、退出码约定）
- [x] 新增 `aixcoding/tests/tools/test_ci_impact.py`（38 测试绿）
- [x] 改 `.github/workflows/aixcoding-upstream-ci.yml`：schedule/dispatch 触发 + filter 重写 + gate 状态机
- [x] 改 `.github/workflows/aixcoding-tests.yml`：govern 静态补位（ruff/format/ty 三平台/compileall）
- [x] 新 ADR `standards/adr/upstream-ci-tiering--pr-gate-tiering.md`（草案，待签认）
- [x] ADR-0004 追加注记；DIRECTORY §7/§1 修订
- [x] upstream-ci、ci-gate、user-manual 三批次文档交叉引用/口径修订
- [x] 本地验证（详见 verification.md：38 单元 / 684 套件 / 三平台 ty / strict / pins / check_docs 全绿）
- [x] 外部 AI 评审实施 diff（CodeBuddy BM:GLM-5.3，通过/blocker 清零，14 项检查全过）
- [x] F1/F2 责任人拍板：均不修（2026-11-12）；F3 已回填
- [x] 签认：新 ADR、upstream-ci/ci-gate design 重签、self-review（均 2026-11-12 完成）；
      增量复审通过（CodeBuddy BM:GLM-5.3，无新增 blocker，签认后正文零漂移）
- [ ] 本批 PR（FORCE 全量自证）CI 日志回填 verification
- [ ] 合并后：dispatch 手动全量一次；临时验证 PR 验 touched=false 链路；首个 nightly 回填 user-manual

## 挂起与备忘

- ~~`ubuntu-slim` 的 python3 实测~~ **已闭环**（2026-11-12，run #125 首跑）：系统 python3=3.12
  < 3.14（`_common.py` PEP 758 语法），probe 已改为版本门限，当前 runner 恒走 setup-python
  兜底（+10s）；复跑后 filter 日志将显示 missing=true，与首跑 missing=false 构成正反双证据
  （requirements 开放问题随之闭环）。
- touched=false 真实链路证据：合并后临时验证 PR（design 验收时点说明），不在本批 PR 内完成。
- nightly 失败通知通道实测：合并后首个到点或故障演练。
- git 写操作逐条授权；本批 PR 走特性分支 + PR 流程（目标 main_aixcoding_cli）。
