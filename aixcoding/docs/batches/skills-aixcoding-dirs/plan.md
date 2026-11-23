# 任务清单：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文
> （DEVELOPMENT.md §4 第 1 步）。2026-11-11 按 PR #107 合规处置终态回写。

## 状态

v1–v3 实施与双 AI 评审均已完成并合入 `main_aixcoding_cli`（fork 分支 `lhc/skill同步`，
PR #107，终态提交 `0697ab68`）。

**2026-11-18 第二轮（v4 需求变更）**：桌面端已安装技能存储
（`<appData>/AIxCoding/<环境>/users/<key>/private/skills/system`）纳入共享范围，
口径对齐插件端 `aixcoding-continue@75407294`。当前停在**方案签认**：design v4 已起草、
状态「草案」，等责任人填写签认字段后再动代码（DEVELOPMENT.md 铁律「方案未签，不动代码」）。

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

### v4 待办（2026-11-18 需求变更）

- [x] 方案文档起草：requirements.md / design.md（v4，**草案待重签**）/ test-plan.md /
  skill-directories.md / plan.md（本文）同步更新
- [ ] **责任人签认 design v4**（签认字段由李海潮本人填写；R2 清单与登记计数变更，按 R10 必须重签）
- [ ] 实施：`PlatformInfo.app_data_dir` + `_conventional_app_data_dir()`、
  `tests/conftest.py` 两处补齐 patch、定制包 `desktop_app_data_dir()` +
  `desktop_installed_skill_paths()`（追加进 `user_aixcoding_skill_paths`）
- [ ] 定制测试：`aixcoding/tests/skills` 新增 8–8f 用例（含「禁用技能仍被扫」反向锚）
- [ ] 验证与门禁：`verify.py --smart`、污染回归（本机 3 个已安装技能）、冒烟
  （`React-Code-Standard` 等被发现）、ruff/format/ty 三平台、`--strict` 登记对账
- [ ] 双 AI 自审（换与主力开发不同的 AI）+ `self-review.md` 追加本轮记录 + 交付 PR

## 责任人裁决记录（2026-11-11，李海潮）

| # | 事项 | 裁决 | 落地 |
|---|---|---|---|
| 1 | 文档改动与 `fork/user-manual` 手册改写的同页冲突 | **还原，不与同事并行改动抢同一批页面** | 5 处既有文档改动整体还原（PR 侧 diff 归零，合并自动取对方侧）；手册缺口由 user-manual 批次补齐 |
| 2 | 机器门禁要求保留登记表载体 | **保留 design.md 并修剪至与实际一致** | 登记表删 C167-C171、ADR 判定节附撤销备案 |
| 3 | 批次 ADR 与新治理规则冲突 | **撤销，不出独立 ADR** | 仿 user-manual 先例：决策内容留在 design，ADR 文件删除，引用全改 |

## 责任人裁决记录（2026-11-18，v4，李海潮）

| # | 事项 | 裁决 | 落地 |
|---|---|---|---|
| 4 | 桌面端禁用（`enabled: false`）技能是否在 CLI 独立会话可见 | **不关心，目录下有就扫**（安装即共享，禁用只是桌面端会话内的选择） | design R12 记录④ + 验收 9；不解析 `active-candidates.json`；测试反向锚 `test_desktop_disabled_skill_is_still_discovered` |
| 5 | 其余四项按 AI 建议（全环境×全账号 / 复用 user 开关 / 同批次续做 v4 / `app_data_dir` 通用字段） | 采纳（未提出异议） | design v4 方案概述、R2 清单 2/3 行、登记表 C158 计数 2、C159-C160 计数 4 |

## 挂起与备忘

- **手册缺口**：`auto_load_aixcoding_*` 两开关与 `~/.aixcoding` 七类根的用户文档说明，
  随本轮回还原一并空缺——由 `fork/user-manual` 批次（F8 手册基准切换后续）统一补齐；
  若该批次不覆盖 `docs/*/guides/extensions/skills.md` 与 `docs/*/reference/agent-profile.md`
  两页，需另开小批次补登 C167-C170。v4 的桌面端安装存储说明也只进本文档目录，
  同样并入该缺口。
- **`project-hooks.md` 披露缺口**：hooks 文档的信任模型提及随还原消失（原 R2 清单第 10 项
  在 0.34 重构后本就无补写位置，此项 2026-11-10 备案自然取消，本轮回到取消态）。
- **撞号教训**：批次 C 编号在签署与合入之间无取号时点锁，main_aixcoding_cli 持续前移时
  必须在 push 前重扫占号（`git grep -o "C1[0-9][0-9]" origin/main_aixcoding_cli -- aixcoding/docs/batches`）。
- **verification.md 历史留痕**：其中记录的 docs 页面改写证据（原 R2 清单 6-9 项）描述的
  改动已在 2026-11-11 还原，读时注意时点——文件为验证历史档案，不回写改写。
- **v4 签认前的预期红**：design 为「草案」时 `gen_customizations.py --strict` 不读该登记表，
  既有 6 个上游文件的 marker 会成为「无登记」error，`check_docs.py --closure` 亦要求
  design 已确认——这是重签窗口的正常状态，签认落盘后恢复；不得为过关而跳过重签或改 marker。
- **【2026-11-18 阻塞】桌面端安装技能「扫得到、用不了」**：路径级已交付（本机冒烟扫出
  `…\AIxCoding\development\users\u-…\private\skills\system` 一个根），但上游
  `chrys/service/skills/loader.py` 的 Agent Skills 规范门（`VALID_NAME_RE =
  ^[a-z0-9]([a-z0-9]*-[a-z0-9])*[a-z0-9]*$`，`validate_skill_metadata`）拒收桌面端市场/团队
  技能的大写驼峰名（本机 3 个全部被拒：`React-Code-Standard`、`Vue-Migration-Guide`、
  `Prompt-Engineering-Handbook`，warning 码 `skill_load_error`）。**同一道门也拦桌面端拉起的
  会话**（profile 物化目录的链接名 = SKILL.md 名，字符集规则同样不通过），故这不是本变更引入
  的回归，而是既有的三端命名口径不一致（插件端 `parseSkillMarkdown` 不校验字符集，所以插件
  能用）。放宽/规范化需改上游 `loader.py`（**不在已签 R2 清单内**）或桌面端安装时规范化
  frontmatter `name`（跨仓）——按 §4.2「扩范围停下重新申请」已停等责任人裁决。
  - **【2026-11-23 裁决】**：责任人裁定改上游 `loader.py`（正则字符集加 `A-Z`，其余约束与
    上游测试文件不动；桌面端安装时规范化留作长期方向，落地后该点提请退役）——design 已更新
    v5 草案（R2 第 12 项、登记 `skills-aixcoding-dirs:loader-name-charset`、R12 记录⑤），
    待责任人重签 design 后实施。
