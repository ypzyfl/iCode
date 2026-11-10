# 技能目录体系说明（skill directories）

> 内部产品文档（R4，落批次目录，不进上游 docs、不进 wheel）。
> 用户侧精简版在本批次实施时按 design R2 清单 6–9 写入 `docs/en|zh-Hans/guides/extensions/skills.md`
> 与 `docs/en|zh-Hans/reference/agent-profile.md`。
> 事实基线：0.34.0 上游 + design v3（2026-11-09，对齐桌面端 `agent_studio_new` 实测布局）实施后；
> 上游信任门维持默认不动。桌面端路径权威：`apps/desktop/src/main/local-skill-layout.ts`。

## 一、总览：扫描哪些目录

技能来源按**扫描次序**排列（次序即同名冲突的优先级，先扫描者胜）：

| # | 来源 | 路径（Linux/macOS） | 路径（Windows） | 作用 | 门控 | 默认可见 |
|---|---|---|---|---|---|---|
| 1 | profile 显式路径 | profile YAML `skills.paths` 中逐条配置 | 同左 | 用户/团队自定义技能位置，相对路径按当前工作区解析 | 无（显式配置即加载；缺失的**绝对**路径产生 `skill_path_missing` 警告，相对路径视为临时目录常态不告警） | 是 |
| 2 | chrys 用户目录 | `~/.chrys/skills` | `%APPDATA%\chrys\skills` | 产品自有全局技能（CLI 自身生态） | 无，永远加载（目录缺失也进列表，为会话中途新增技能留位） | 是 |
| 3 | aixcoding 工作区根 | `<cwd>/.aixcoding/skills` | `<工作区>\.aixcoding\skills` | **与桌面客户端共享**的项目专属技能，随工作区切换 | 仅 profile 开关 `auto_load_aixcoding_cwd_skills`（默认开）；**不受**项目信任门管控（ADR-0001 决策二） | 是 |
| 4 | aixcoding 用户级全树 | `~/.aixcoding/skills` → `~/.aixcoding/market-skills` → `~/.aixcoding/team-skills/<team>` | `%USERPROFILE%\.aixcoding\…`（字面 HOME） | **与桌面客户端共享**：手工技能 → 技能市场安装 → 团队空间分发（每个 team 子目录各为一个技能根） | profile 开关 `auto_load_aixcoding_user_skills`（默认开） | 是 |
| 5 | aixcoding IDE 镜像树 | `~/.aixcoding_intellij/{skills,market-skills,team-skills/<team>}` | `%USERPROFILE%\.aixcoding_intellij\…` | IDE（IntelliJ 插件）管理的同构技能树，与第 4 类完全同构 | 同上（`auto_load_aixcoding_user_skills`） | 是 |
| 6 | agents 用户目录 | `~/.agents/skills` | `%USERPROFILE%\.agents\skills`（字面 HOME） | 跨 CLI 编码工具共享的全局技能（`.agents` 为多工具通用约定） | profile 开关 `auto_load_user_agents_skills`（默认开） | 是 |
| 7 | agents 工作区目录 | `<cwd>/.agents/skills` | `<工作区>\.agents\skills` | 跨工具共享的项目专属技能，随仓库分发（git clone 即得） | **双重门**：全局设置 `project.skills_enabled`（**默认关**）**且** profile 开关 `auto_load_cwd_agents_skills`（默认开）；开关关且有内容时 TUI 提示休眠来源 | **否**（唯一例外，上游安全设计，维持不动） |

补充来源（非目录）：

- profile YAML `skills.inline`：内联技能直接写在 profile 文件里，无目录概念；与文件技能合并去重时**文件技能优先**（`adapter.py` merge 规则）。
- 桌面端拉起的 CLI 会话另有 profile 注入链路：桌面端把启用的技能**物化**为 profile
  `skills.paths` 传入（`chrys-agent-profile.ts`），第 3–5 类根在桌面端会话中经由该链路同样生效；
  本批次补的是 **CLI 独立会话**（用户直接运行 `aixcoding-cli`）下的自动识别。

## 一a、账号安装存储（明确不扫描）

`~/.aixcoding/<环境>/users/<directoryKey>/private/skills/`（如 `~/.aixcoding/production/users/u-<52位编码>/private/skills/`，
实际第二段是 `u-` 前缀 + 52 位 base32 的**匿名目录键**，非明文用户 ID；`system/` 子目录是团队技能
的安装命名空间前缀 `system/team-<工作区ID>-<名称>`）。

这是桌面端 `FileSystemSkillRegistry` 的**安装存储区**（市场/团队/捆绑包安装的技能包，含
staged 与已禁用状态，`runtime-composition.ts:1083`），与上表「本地技能根」是两套互斥体系：

- 桌面端会话：该存储中的**已启用**技能经 profile 物化链路注入 CLI，已识别；
- CLI 独立会话：**不扫描、也不应扫描**——直接扫会绕过桌面端启用/禁用状态；路径含 per-user
  编码键与环境分段，CLI 无法可靠定位当前账号 scope。跨端共享该批技能的正确通道是
  profile 注入（已有），不是文件系统扫描。

## 二、识别与优先级规则

1. **扫描次序 = 优先级**：技能发现按上表 1→7 次序进行；同名技能（名字按大小写不敏感比较）
   **先扫描者胜**，后到者跳过并记录 warning（`loader.py:501-503` 实证）。因此：
   - profile 显式路径 > 一切自动目录；
   - 工作区 aixcoding 根胜过用户级 aixcoding 树（对齐桌面端 `runtime-composition.ts:1151`
     的 `unshift` 实测次序：项目专属覆盖全局，v3 修正——0.28 次序当年未与桌面端对过代码）；
   - aixcoding 各根胜过对应 `.agents` 目录（产品目录优先于跨工具目录，D3 决策）。
2. **目录可以不存在或为空**：仍会进入扫描列表（每次技能刷新重查），会话中途往里放技能
   无需重启即可被发现。
3. **技能识别形态**：目录内按 `SKILL.md` 识别（frontmatter 提供名称与描述；`skill.json`
   非必需，与桌面端一致）；资源与脚本随技能目录一同暴露，脚本经 `run_skill_script` 执行、
   统一走 approval 审批。
4. **工作区目录跟随软重启**：`/chdir` 或文件选择器切换工作区时 agent 以新
   `SessionEnvironment` 重建，第 3 类目录自动切换到新工作区（不取 `os.getcwd()`）。
5. **team-skills 枚举行为**（与桌面端 `userTeamSkillRoots` 一致）：`team-skills` 的每个立即
   子目录视为一个团队、各自作为独立技能根；隐藏目录（`.` 前缀）与符号链接跳过，按名排序；
   枚举失败（容器不存在/不可读）得空集，不阻塞会话。

## 三、信任模型（上游默认，维持不动）

上游 0.34 对「工作区带来的东西」整体默认不信任，「Project trust」设置分区三开关全部默认关：

| 开关 | 管什么 | 默认 |
|---|---|---|
| `project.config_enabled` | 项目设置文件 | 关 |
| `project.hooks_enabled` | 项目 hooks | 关 |
| `project.skills_enabled` | `<workspace>/.agents/skills` | 关 |

三处均为 `ProjectMerge.DENY`：项目自己的配置文件**无权**打开自己层，只能由用户在用户级
设置或 TUI 显式开启。本批次决策（ADR-0001）：

- `~/.aixcoding/skills` 与 `<cwd>/.aixcoding/skills` 为**产品自有目录**，信任级对齐用户目录
  （类比 `~/.chrys/skills`），不引入新门，默认可见；
- `<cwd>/.agents/skills` 维持上游双重门与默认关——内容是仓库作者放进 git 的，保持
  「提示 + 一键开启」的既有体验；
- 脚本执行的安全底线不变：所有技能脚本统一经 approval 审批，技能发现无门不等于执行无审批。

## 四、平台路径速查

| 名称 | Linux / macOS | Windows |
|---|---|---|
| chrys 配置目录（`config_dir`） | `~/.chrys` | `%APPDATA%\chrys`（即 `...\Roaming\chrys`） |
| aixcoding 用户目录 | `~/.aixcoding` | `%USERPROFILE%\.aixcoding` |
| aixcoding IDE 镜像目录 | `~/.aixcoding_intellij` | `%USERPROFILE%\.aixcoding_intellij` |
| agents 用户目录 | `~/.agents` | `%USERPROFILE%\.agents` |

注意：aixcoding / aixcoding_intellij / agents 目录是**字面 HOME 目录**（`Path.home()`），
Windows 上不在 `%APPDATA%` 下——桌面客户端共享契约即字面 HOME，勿混淆。

## 五、与其他批次文档的关系

- 决策依据与备选取舍：本目录 `design.md`（v2.1，已签认）、`adr/0001-aixcoding-skill-dirs-trust-and-contract.md`；
- 行为锚定测试：`test-plan.md` 覆盖矩阵第 3、2a 行（次序与信任门例外）；
- 实施时用户文档改写以本文第一、二节为依据（R2 清单 6–9）。
