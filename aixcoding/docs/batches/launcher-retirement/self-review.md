# 自评审记录：退役 diagnostics launcher（launcher-retirement）

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-30
- 确认意见：无特别意见
- 评审 AI：Deepseek-V4-Pro（独立会话，两轮：design 态 + 实施态）
- 开发 AI：CodeBuddy（BM:GLM-5.3）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-10-30 评审结论：通过

- 轮次：2 轮（design 评审+修复；实施评审+修复），均无 blocker。
- design 轮 1 blocker + 3 major + 1 minor：
  - Blocker R2 表行号错误（`:220` 为上游原状，误删将破坏 kernel-private 机制）——修，回滚范围精确到行（实测 19 行）；
  - Major 1 logging_support.py docstring 残留——修（中性表述）；
  - Major 2 C005 anchor 顺序依赖——修（先改 batches/diagnostics/design.md 登记表再重跑生成器，已按序执行）；
  - Major 3 auth-logging 依赖软建议升级硬前置——修（后经责任人路径演化三次：实施独立先行 → 合并硬前置 → **2026-10-30 终裁先行合并、空窗接受**，design 风险节已同步终态口径）；
  - Minor ADR-0011 决策 5 导航注记——修（非决策性背景补充）。
- 实施轮 1 major + 2 suggestion + 1 nit：
  - Major C005 anchor 残留 launcher 描述——修，根因为**双登记源**（batches/tier-migration/design.md:92 登记行），事实同步改写后生成器收敛确认；
  - Suggestion C026/C027 tui 登记混入——接受（tui 批次遗留 freshness 缺口，本批次被动补齐，随 PR 提交并在 PR 描述说明）；
  - Suggestion 回滚行数勘误（实测 19）——修（design R2 表 + verification）；
  - Nit UPGRADE-RUNBOOK:53 失效描述——修。
- 验证命令与结果：见 verification.md（架构 1238 passed / 定制 276 passed / 入口消亡 / 生成器幂等 27 点 / 残留净 / ruff+format+ty 全过 / C005 收敛）。
- 未修项：无。

## 2026-10-30 PR #69 peer review 处置（评审 AI：Deepseek-V4-Pro，worktree 副本独立取证）

- **C1（elif 未恢复上游原状）已修**——与 CI `check_r3_markers` 红**双路径交叉验证**同一行：peer review 以 `git show 7bd6d45a~1` 实证上游原状为独立 `if` 并做破坏性实验（行为等价 223 passed）；CI 按上游 merge-base diff 抓获。修复：改回独立 `if`，文件相对上游基线 diff 归零，`tests/architecture` 1238 passed。教训留痕 verification：**恢复原状的完成标准 = 上游基线零差异**（fork 内视角的两轮评审均未发现，属评审盲区）；
- **C2（requirements.md 合并顺序"硬前置"与终裁冲突）已修**——同步漏改的 requirements:37 口径 + 行数两处旧值（~18→19）+ plan:14 残留（17 行→净删除 19 + 形状恢复）；design R2 表补形状恢复记录；
- **非缺陷项确认**：评审副本的 1 failed（test_mock_launcher 端口 10048）与本批无关（mock 模块不在 PR 文件内）；**根因勘误（第 2 轮 peer review 实测修正）**：占用 7778（update mock 端口）的是本机常驻系统服务 ArmouryCrateControlInterface（华硕，PID 5488）——非演示用 auth server（其用 7777，PID 3044 已退出，初版归因错误）；该用例在本机将因 7778 被占而持续红（环境性），CI 干净环境无此问题。历史文档 launcher 引用（快照性质不改写）、conftest aix_logger_state 保留（5 用例在用）等 7 项核验通过。
- **第 2 轮新增候选处置**：C1/C2 复核闭环（双基准零差异实测 + 口径统一实测）；**C4（Upstream CI linux/core attempt 1 红）定论 flaky**——attempt 2 同代码全绿（PR checks 全绿，2026-10-30），与评审倾向一致（elif→if 平台无关、windows/core 两次均绿）；**C3 根因勘误**（见上条）+ design.md 笔误（"d diagnostics"多字）已修。
