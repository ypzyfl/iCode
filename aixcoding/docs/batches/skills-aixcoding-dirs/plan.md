# 任务清单：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文
> （DEVELOPMENT.md §4 第 1 步）。2026-11-11 按 PR #107 合规处置终态回写。

## 状态

实施与双 AI 评审均已完成（fork 分支 `lhc/skill同步`，PR #107 → `main_aixcoding_cli`）。
当前在收尾清单阶段处理与并行批次的治理对齐：文档改动整体还原（避开 `fork/user-manual`
后续手册改写的同页冲突）、批次 ADR 撤销、登记表修剪、六件套补齐。

## 待办

- [x] 实施主体（commit 904370db）：`chrys.service.aixcoding.skill_paths` 定制包
  （七类根解析）+ 上游挂点 2 处 + `PlatformInfo.aixcoding_dir` + `SkillsConfig`
  两开关 + `tests/conftest.py` 重定向 patch + `aixcoding/tests/skills` 行为锚
- [x] requirements.md / design.md（v2.1→v3，已签认 2026-11-09）/ test-plan.md /
  skill-directories.md / verification.md / self-review.md（两轮收敛 blocker 清零）
- [x] 双 AI 评审（GLM-5.3 / CodeBuddy 子代理，独立会话）：见 self-review
- [x] R3 标记：6 个上游改动文件均带 `AIxCoding skills:` 单行标记
- [x] 定制点登记：C158-C166（并入 main_aixcoding_cli@9d824cb5 后两度撞号，从 C143-C146 /
  C147-C160 两轮重编而来，见提交 6dd37752 / 1e4be251）
- [x] 合并 main_aixcoding_cli（commit 3fe66906，含 upstream-merge-v0.35.1、logo-branding、
  llm-keyless-sdk-auth、user-manual、parallel-batch-governance）
- [x] **2026-11-11 合规处置（本轮）**：
  - [x] 还原 5 处既有文档改动（docs/en、docs/zh-Hans 各 2 页 + hooks project-hooks.md）——
    避开 `fork/user-manual@67934157`（F8 手册基准切换）后续合入的同页冲突；
    登记表 C167-C171 随之撤销（孤儿登记会被 `--strict` 拒绝）
  - [x] 撤销批次 ADR（原 `adr/0001-aixcoding-skill-dirs-trust-and-contract.md`）——
    ADR-0024 起决策文档收全局池、批次 `adr/` 池废止，且 0001 号与全局池重号；
    决策记录由 design「ADR 判定」节承载，全批次 6 处引用同步改指 design
  - [x] 补齐六件套：plan.md（本文）、requirements.md
- [ ] 收尾门禁总检：`check_docs.py --closure` + `gen_customizations.py --strict` +
  R2/R3 门禁 + `pytest aixcoding/tests`（合并树上全绿后推送）

## 责任人裁决记录（2026-11-11，李海潮）

| # | 事项 | 裁决 | 落地 |
|---|---|---|---|
| 1 | 文档改动与 `fork/user-manual` 手册改写的同页冲突 | **还原，不与同事并行改动抢同一批页面** | 5 处既有文档改动整体还原（PR 侧 diff 归零，合并自动取对方侧）；手册缺口由 user-manual 批次补齐 |
| 2 | 机器门禁要求保留登记表载体 | **保留 design.md 并修剪至与实际一致** | 登记表删 C167-C171、ADR 判定节附撤销备案 |
| 3 | 批次 ADR 与新治理规则冲突 | **撤销，不出独立 ADR** | 仿 user-manual 先例：决策内容留在 design，ADR 文件删除，引用全改 |

## 挂起与备忘

- **手册缺口**：`auto_load_aixcoding_*` 两开关与 `~/.aixcoding` 七类根的用户文档说明，
  随本轮回还原一并空缺——由 `fork/user-manual` 批次（F8 手册基准切换后续）统一补齐；
  若该批次不覆盖 `docs/*/guides/extensions/skills.md` 与 `docs/*/reference/agent-profile.md`
  两页，需另开小批次补登 C167-C170。
- **`project-hooks.md` 披露缺口**：hooks 文档的信任模型提及随还原消失（原 R2 清单第 10 项
  在 0.34 重构后本就无补写位置，此项 2026-11-10 备案自然取消，本轮回到取消态）。
- **撞号教训**：批次 C 编号在签署与合入之间无取号时点锁，main_aixcoding_cli 持续前移时
  必须在 push 前重扫占号（`git grep -o "C1[0-9][0-9]" origin/main_aixcoding_cli -- aixcoding/docs/batches`）。
- **verification.md 历史留痕**：其中记录的 docs 页面改写证据（原 R2 清单 6-9 项）描述的
  改动已在 2026-11-11 还原，读时注意时点——文件为验证历史档案，不回写改写。
