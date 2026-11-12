# 任务清单：检查域模型与定制域按需触发

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**收官**（2026-11-13）：批次功能全部上线（PR #123/#124）并经四重真实流量实证——FORCE 全量
自证、纯文档跳过 ~1 分钟（PR #124 三件套）、push 恒全跑双证（#201/#204，范围=定制双域）、
nightly 三域覆盖（Tests #207 + Upstream #134）；user-manual 遗留口径已核销。仅剩本回填
文档的收尾 PR。

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
- [x] 合并后收尾之回填 PR 三件套：**已实证**（PR #124 / Tests #202：filter 33s 判双 false →
      test/guard 零 runner skipped → gate 7s 直绿，run 总 48s；Upstream #131 同款 49s；
      纯文档 PR 总等待 ~1 分钟）
- [x] push run 恒全跑观察（范围=定制双域，upstream 无 push 触发仅 nightly/dispatch 兜底）：
      **双证成立**（#201 约 2.5 分钟 success 首证；#204 8/8 success——filter 判非 PR 事件
      双域全跑，总约 9.5 分钟，macos 排队占大头）
- [x] 首个 nightly 三域覆盖与 user-manual 口径核销：**完成**（Tests #207 success 2m37s +
      Upstream #134 success 13m11s，2026-11-12 深夜执行——schedule 高峰延迟近 5h，平台已知
      行为；user-manual 遗留口径已核销）——**批次全部验收项闭环**

## 挂起与备忘

- 旧 ADR（upstream-ci-tiering--pr-gate-tiering）快照不回改；新 ADR 四行映射表收尾。
- 静态契约测试新增消费仓库文件时须同步登记分类器（ADR 维护义务；F6 扫描自动防漏）。
- 桥接 workflow 的 concurrency 经核查无 push/nightly 同 ref 问题，不随本批改。
