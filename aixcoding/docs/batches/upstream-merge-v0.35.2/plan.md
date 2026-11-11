# 任务清单：追上游 v0.35.2（upstream-merge-v0.35.2）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**实施、验证与签认完成，待 git 授权（2026-11-11）**：全部验证矩阵绿；self-review 已签认；
Deepseek-V4-Pro 收尾独立评审 blocker 0（nit ×3 已处置）；closure / strict / format 复跑绿。
下一步 = 逐条申请 git add → R2/R3 终态复跑 → commit / push / PR。

## 待办

- [x] 开工判定呈报（ADR-0012）：完整管线 + 目标 ref = release tag v0.35.2（`2fd777f`）
- [x] 镜像同步确认（责任人手动：本地/origin `main_iCode` = `3ea2ca2a`，含目标）
- [x] 升级前绿基线（定制 629/51/0 + check_docs closure OK + strict 109/150/7；
      closure OK 时点 = 本批次目录创建前，六件套齐备前红为预期态）
- [x] 干跑 merge-tree（冲突 1 处：`test_program_status_lifecycle.py` C079–C081）
- [x] 上游区间分析（149 文件；marker 交集 10 文件 + 3 豁免产物；`-G iCode` 全筛查）
- [x] 手册解耦口径落活文档（UPGRADE-RUNBOOK §2 + user-manual/plan 备忘）
- [x] requirements.md / design.md（草案）/ test-plan.md / plan.md
- [x] 只读事实复核（code-explorer 子代理，2026-11-11）：无事实错误；git/strict 数字其无法
      执行的部分均以主会话实测输出为证据（38/29、149/+8650/−1381、冲突 1、109/150/7）
- [x] 外部文档评审（2026-11-11）：B1 SHA 硬错 / B2 状态矛盾 / B3 登记描述漂移 +
      建议 7 项；责任人裁决按推荐处置
- [x] 评审处置修订（B1/B2 状态同步 / B3 留痕口径 / worksteal 必做 / runbook §6
      收尾项 / closure 序列 / 淘汰分组载体 / rg-cache 观察）
- [x] 责任人重签 design.md（正文修订后按 R10 重签，2026-11-11）
- [x] 建分支 `chore/merge_upstream_v0.35.2`（自 `main_aixcoding_cli` @d52626f1，逐条授权）
- [x] `git merge 2fd777f` → 解冲突 1 处（`_ERROR` 品牌常量 + marker 迁移，计数 3；
      单文件实跑 8 passed，2026-11-11）
- [x] `uv sync --frozen` 对齐版本行（无解释器变更；包版本 0.35.2）
- [x] i18n 管线（extract → update → compile → check ×3；pot/po hash 逐位一致）
- [x] 定制套件按继承 addopts 首跑 `-n 8 --dist=worksteal`（629 passed / 51 skipped，
      29.35s，2026-11-11；无需 `-n0` 对照）
- [x] 定制四门 + R2/R3 工作树口径（base `2fd777f`；R2 85/93 OK、R3 85/82/3 OK）
  + ruff/format（3099 files already formatted）+ ty 三平台全绿
- [x] R2/R3 add 后终态复跑（R2 changed=561 / upstream=85 / pool=93 OK；
      R3 85/82/3 OK；index 无 UU/RM/MM 残留）
- [x] fork-full `verify.py --full`（CodeBuddy 配方；定制 + 上游 regular worksteal + architecture
      串行全过——责任人确认后台 console，进程正常结束，result 临时文件已自清理）
- [x] `uv build` + `scripts/check_wheel.py dist/icode_tui-0.35.2-*.whl`（67 手册文件 /
      zh-Hans catalog / 安装探测全过）
- [x] UPGRADE-RUNBOOK 头部基线 0.35.1→0.35.2 + 收尾日期（2026-11-11）
- [x] verification.md 落盘（含升级决策清单、淘汰检查、anchor/risk 重评与裁决记录）
- [x] self-review.md 落盘并经责任人签认（2026-11-11；Deepseek-V4-Pro 收尾独立评审
      blocker 0，nit ×3 已处置并追加记录）
- [x] `gen_customizations --report` 完整时点快照存档
      `customizations-snapshot-2026-11-11.md`（SHA-256 76F204…D845）
- [x] 各定制点 anchor/risk 重评（按来源 design 分组，17 组全部维持原登记）
- [ ] `rg-cache-warmer.yml` 定时任务首次运行观察记 verification.md（合并后远端触发）
- [x] `check_docs --closure` 复跑绿（self-review 签认后实测：24 ADR / 39 design /
      38 self-review）
- [x] TUI 冒烟（headless `--version=0.35.2`；F6 / 登录 / F4 / sessions 全局搜索提示五项通过）
- [x] git add -A（2026-11-11 逐条授权；locales 无未暂存内容漂移，staged whitespace OK）
- [ ] commit / push（逐条授权）→ 责任人建 PR → 双 CI 绿后合并

## 挂起与备忘

- **手册跟进（独立批次，不阻塞本升级）**：上游 0.35.2 `docs/` 四篇指南有语义变化
  （会话全局搜索 / 粘贴标签编辑 / skills 两层资源 / shortcuts 编辑器行为）；
  `aixcoding/manual/` 保持 0.35.1 内容，待独立手册批次评估同步并重出 wheel/PDF
  （2026-11-11 责任人裁决，UPGRADE-RUNBOOK §2 已留痕）；
- **目标 tag 对象**：GitHub 直连 443 超时，本地未取回 tag ref；目标 commit 已从本地上游
  原仓按完整 SHA 取回并核验，merge 使用 `2fd777f626649d53d7ccd701e26a1a7ada569ce8`；
- **本批无草案 strict 窗口期**：design 无登记表 / 退役表，`--strict` 预期始终 109/150/7；
- **本机环境噪音历史在案**：WinError 448 junction 族、test_install_scripts 满载 flaky、
  gc_calibration 偶发；本轮升级前基线 0 failed，merge 后同口径对比归因；
- **固定关注文件**：`test_manual_reload.py` / `test_prompt_shortcut_send.py` 单文件单跑；
  本批新增关注：`test_program_status_lifecycle.py`（冲突解后整文件 `iCode` 通查）；
- **C079–C081 anchor 描述漂移（B3(a) 已裁）**：冲突解后形态 = 1 个模块级 `_ERROR`
  常量（2 个测试共用）+ 2 个函数内断言；不改 `branding-and-command/design.md` 登记行，
  verification.md 留痕，marker 计数 3 与 strict 不变。
