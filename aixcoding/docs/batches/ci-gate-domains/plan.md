# 任务清单：检查域模型与定制域按需触发

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

批次主体已合并（PR #123 → `800bb778`，2026-11-12）；收尾阶段——纯文档回填 PR 进行中
（兼作定制双域跳过三件套验证载体），push run 与首个 nightly 观察待完成。

## 待办

- [x] `ci_impact.py` 扩展 `--domains` 模式与规则表 R1-R12（域集合累积、并集语义、R7 双域 M1）
- [x] `test_ci_impact.py` 扩展：50 新例（规则矩阵/并集/R12/F6 AST 双形态）+ 38 例零回归 = 88 绿
- [x] `aixcoding-tests.yml`：filter job + test/guard 条件 + gate 状态机 + schedule/dispatch + concurrency event 分组
- [x] 新 ADR `standards/adr/ci-gate-domains--check-domains-model.md`（草案，待签认）
- [x] DIRECTORY §7/§1 改检查域口径
- [x] verification.md + self-review.md 初稿（本地证据已录；CI 日志待回填）
- [x] 本地验证：88+734 测试、YAML/pins/ruff/strict/check_docs 全绿；closure 5 errors 均为 ADR 草案挂账（签认即绿）
- [x] 外部 AI 评审实施 diff：**完成**（评审 AI Kimi-K3.1-Pro × 实施开发 GLM-5.3，不同源
      合规——0 技术 blocker，S1/S2 已修并经增量复审闭环；评审标识误标根因=初稿抄错实施
      开发 AI，责任人澄清分阶段事实后已更正记录）
- [x] 签认（责任人）：design 重签（三处正文修订）、self-review、新 ADR——均已完成
      （2026-11-12），closure 复跑 OK
- [x] PR 流程（逐条授权）：add/commit/push → PR #123 → 双 CI 全绿（Tests #200 8/8：filter
      FORCE/版本门限/三 OS guard/gate 状态机全实证；Upstream #130 attempt 2 success）→
      verification 已回填；待合并
- [ ] 合并后收尾（PR #123 已合并）：纯文档回填 PR 三件套验证（分支已建、进行中）；push run
      恒全跑观察；首个 nightly（UTC 18:00）观察与 user-manual 口径核销

## 挂起与备忘

- 旧 ADR（upstream-ci-tiering--pr-gate-tiering）快照不回改；新 ADR 四行映射表收尾。
- 静态契约测试新增消费仓库文件时须同步登记分类器（ADR 维护义务；F6 扫描自动防漏）。
- 桥接 workflow 的 concurrency 经核查无 push/nightly 同 ref 问题，不随本批改。
