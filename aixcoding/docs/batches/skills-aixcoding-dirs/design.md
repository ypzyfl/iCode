# 设计：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-23
- 确认意见：无特殊意见

> v2（2026-11-09 自审修订）：推翻 v1 的测试隔离方案——0.28 的「裸 `Path.home()` + 上游测试散点
> 关开关」形态改为「`aixcoding_dir` 挂进 platform 单例」，借上游既有的 config-dir 重定向机制
> 获得机制性测试隔离；上游测试散点改动（5 文件）收敛为 conftest 一处 + platform 字段一处。
> 同名冲突先到先得由推断升级为实证（`loader.py:501` / `adapter.py:373`）。

> v3（2026-11-09 桌面端对齐修订）：对桌面端 `agent_studio_new` 代码实证（R12 记录③）后，
> 识别范围从 0.28 的 2 个根扩展为桌面端 `local-skill-layout.ts` 定义的**全部 7 类根**
>（`market-skills`、`team-skills/<team>`、`.aixcoding_intellij` 镜像树此前漏识别）；扫描次序
> 改为对齐桌面端 `runtime-composition.ts` 的实测次序（工作区根优先于用户级根，0.28 次序
> 当年未与桌面端对过代码）。**R2 清单（文件 × 行数）不变**——全部扩展落在定制包内部，
> 按 R10 不触发重签。

> v4（2026-11-18 需求变更，待责任人重签）：新增**第 8 个来源**（`skill-directories.md` 表中 5a）——桌面端已安装技能存储
> `<appData>/AIxCoding/<环境>/users/<用户>/private/skills/system`（R12 记录④）。上游增
> `PlatformInfo.app_data_dir` 字段（`aixcoding_dir` 之外的第二处 platform 接触面）与
> conftest 同步 patch 行——**R2 清单与登记计数变化，按 R10 必须重签**；本文件已转「草案」，
> 签认字段由责任人本人填写。

> v5（2026-11-23 阻塞裁决，待责任人重签）：2026-11-18 备案的「扫得到、用不了」阻塞落地为
> 方案 E1——上游 `loader.py` Agent Skills 规范门字符集加大写（裁决过程见 R12 记录⑤）。
> R2 清单增第 12 项、登记表增 `skills-aixcoding-dirs:loader-name-charset`——**R2 清单与
> 登记计数变化，按 R10 必须重签**；本文件已转「草案」，签认字段由责任人本人填写。

## 目标与验收条件

把 0.28 分支（`origin/main_aixcoding_cli_0.28.0_final`，提交 `a7631f26` + `c174727b` + `2b055caf`）
的 SKILL 定制迁移到 0.34 基线，并对齐桌面端 `agent_studio_new` 的技能布局
（本地根权威 `apps/desktop/src/main/local-skill-layout.ts`，安装存储权威
`runtime-composition.ts:1079-1083` + `file-system-skill-registry.ts:2237-2239`）：自动加载
桌面端全部本地技能根（v3 扩展）与已安装技能存储（v4 扩展），与 AIxCoding 桌面客户端
及 IntelliJ 插件端（`aixcoding-continue@75407294`）共享技能目录。

验收条件：

1. `~/.aixcoding` 用户级全树（开关 `auto_load_aixcoding_user_skills`，默认 True）被自动扫描：
   `skills/`、`market-skills/`、`team-skills/<team>/`（team 子目录逐个枚举，跳过隐藏目录与
   符号链接，与桌面端 `userTeamSkillRoots` 行为一致），以及 `.aixcoding_intellij` 镜像树的
   同构三根；
2. `<cwd>/.aixcoding/skills/`（开关 `auto_load_aixcoding_cwd_skills`，默认 True）被自动扫描，
   绑定 `runtime.cwd`（跟随 `/chdir` 软重启），**不受 `project.skills_enabled` 约束**（责任人裁决，见 R12 记录①）；
3. 扫描次序对齐桌面端 `runtime-composition.ts:1104-1157` 实测次序（工作区根优先于用户级根，
   v3 修订，替代 0.28 次序；v4 插入安装存储）：
   `~/.chrys/skills` → `<cwd>/.aixcoding/skills` → `~/.aixcoding/{skills → market-skills →
   team-skills/<team>}` → `~/.aixcoding_intellij/{同构三根}` →
   **桌面端安装存储（全部环境 × 全部账号，按名排序）** → `~/.agents/skills` →
   `<cwd>/.agents/skills`（aixcoding 同名技能优先于对应 `.agents` 目录，D3 保持；先到先得
   已实证：`loader.py:501-503`、`adapter.py:373-380`）；
4. 两个开关可经 agent profile YAML 配置，旧 0.28 用户配置文件无需改动（开关语义按目录树
   归属：user 开关管两棵 HOME 树**与桌面端安装存储**，cwd 开关管工作区根）；
5. 三条 build 路径（主 agent / 子代理 / 工作流节点）行为一致（共用 `_collect_skill_paths`，天然一致）；
6. 开发机 HOME 下存在真实 `~/.aixcoding/skills/` 内容（本机实况：`hanhai-h5`）**或桌面端
   安装存储内容（本机实况：`%APPDATA%\AIxCoding\development\users\u-vdhddg…\private\skills\system`
   下 3 个技能）**时，上游测试套件不因定制变红——由 platform 重定向机制**机制性**保证，
   不依赖逐测试关开关；
7. CLI 独立会话（不经桌面端拉起）能发现桌面端放入任一本地根的技能，实现双向共享；
8. （v4）桌面端已安装技能存储 `<appData>/AIxCoding/<环境>/users/<用户>/private/skills/system`
   被自动扫描：**全部环境目录 × 全部账号目录**逐个枚举（数据根自身也作为一个容器尝试，
   兼容无环境层级的旧布局），只认 `SKILL.md` 所在目录；隐藏目录、符号链接跳过，
   环境与账号均按名排序，目录缺失不报错；
9. （v4）**安装 ≠ 启用**：桌面端禁用（`enabled: false`）的技能同样可被发现（责任人
   2026-11-18 裁决，理由见 R12 记录④）；不解析桌面端 `skill.json` / `active-candidates.json`
   等内部状态文件；
10. （v5）桌面端安装技能的大写驼峰名（本机实况 `React-Code-Standard` 等 3 个）通过 Agent
    Skills 规范门被正常加载；其余非法形态（上游测试反例 `Bad_Name` 的下划线、首尾/连续
    连字符、超 64 字符）仍被拒——上游 `tests/service/skills/test_loader.py` 语义不变，
    本批不改任何上游测试文件。

## 方案概述（B1：函数体下沉定制包，上游留挂点；目录根挂 platform 单例）

```
_collect_skill_paths（上游 adapter.py，仅两处挂点）
    chrys_user_dir          （上游，原样：get_platform().config_dir/skills）
    ┌─ 挂点1: cwd_aixcoding_skill_paths(config, runtime) ← 定制包（工作区根，对齐桌面端 project 优先）
    │      <cwd>/.aixcoding/skills  [auto_load_aixcoding_cwd_skills]
    ├─ 挂点2: user_aixcoding_skill_paths(config) ← 定制包（HOME 两棵树 + 桌面端安装存储）
    │      ~/.aixcoding/skills → ~/.aixcoding/market-skills → ~/.aixcoding/team-skills/<team>…
    │      → ~/.aixcoding_intellij/skills → …/market-skills → …/team-skills/<team>…
    │      → <appData>/AIxCoding/<环境>/users/<用户>/private/skills/system（v4）
    │      [auto_load_aixcoding_user_skills]
    ├─ .agents user 分支      （上游，原样：user_agents_dir()/skills）
    └─ .agents cwd 分支       （上游，原样，project_skills_enabled 门保留）

定制包 src/chrys/service/aixcoding/skill_paths.py（新文件，service 档）
    user_aixcoding_dir() -> Path            # get_platform().aixcoding_dir（薄封装，monkeypatch 锚）
    desktop_app_data_dir() -> Path          # get_platform().app_data_dir（v4 薄封装，monkeypatch 锚）
    user_aixcoding_skill_paths(config)          # 开关1 + 两棵 HOME 树全根枚举（team 子目录运行时
                                                # readdir，跳过隐藏目录与符号链接，对齐桌面端
                                                # userTeamSkillRoots；expanduser().resolve()）
                                                # + 末尾追加 desktop_installed_skill_paths()
    desktop_installed_skill_paths() -> list[str]  # v4：<appData>/AIxCoding 下 环境 × 账号 枚举
                                                # private/skills/system（跳隐藏/符号链接、按名排序、
                                                # 只返回真实存在目录），不读桌面端状态文件
    cwd_aixcoding_skill_paths(config, runtime)  # 开关2 + runtime.cwd；不读 project_skills_enabled

platform：PlatformInfo 增两字段
    aixcoding_dir  默认 Path.home()/".aixcoding"（平台无关，v2）
    app_data_dir   默认 _conventional_app_data_dir()（v4，OS 应用数据根：
                   %APPDATA% / ~/Library/Application Support / $XDG_CONFIG_HOME|~/.config）
上游 tests/conftest.py：两处 replace（_detect_with_pinned_config_dir / _pin_config_dir，
per-test fixture 复用后者）同步 patch 两字段
```

要点：

1. **挂点形态**：函数内 lazy import，`try/except` 全吞错 + `logger.debug` 留痕——定制目录合并属
   可降级增强（失败仅损失 aixcoding 技能，核心技能功能不受损），符合 R1「lazy + 全吞错（降级可接受时）」。
2. **两处挂点而非一处，且工作区挂点在前**：挂点 1（cwd 根）紧跟 chrys 目录之后、挂点 2
   （HOME 全树）在 `.agents` user 之前——既保持 D3（aixcoding 同名优先于对应 `.agents`
   目录：aix cwd 先于 `.agents` cwd、aix user 先于 `.agents` user），又对齐桌面端
   `runtime-composition.ts:1151` 的 `roots.unshift({origin:'project',…})` 实测次序
   （工作区根优先于用户级根，同名工作区技能覆盖全局）。一处挂点一次性插入无法同时满足
   这两个约束，不做。
3. **目录根挂 platform 单例（对 0.28 形态的 R12 改进，本设计的核心优化）**：0.28 的
   `user_aixcoding_dir()` 裸返回 `Path.home()/".aixcoding"`，绕过了上游测试的 config-dir 重定向
   机制（`_arm_config_dir_redirect` / `_pin_config_dir` / `_isolate_platform_config_dir`，
   `tests/conftest.py:503-543`，上游 `~/.chrys/skills` 正靠它隔离），被迫在 tests/support 与
   各测试散点关开关、且仍防不住 `test_adapter.py` 十余处 `skill_names() == [...]` 精确断言
   （本机实测 HOME 存在真实技能 `hanhai-h5`，污染是现实）。0.34 下把 `aixcoding_dir` 做成
   `PlatformInfo` 字段（`default_factory=Path.home()/".aixcoding"`，`detect_platform()` 调用点
   零改动），上游测试重定向机制 patch 该字段一次，所有上游测试自动隔离——上游测试散点改动
   （v1 的 5 文件 8 行）收敛为 conftest 一处 +2 行，并覆盖未来上游新增测试。
4. **开关进 `SkillsConfig`**（B1）：与 `auto_load_user_agents_skills` 同构，profile YAML 可配，
   0.28 用户配置零迁移成本。
5. **TUI 面板不改**：`SkillsConfigPanel` 硬编码渲染两个既有开关，新开关不出现在 TUI（与 0.28
   一致，仅 YAML 可配）；面板保存时构造 `SC(...)` 不带新字段 → dataclass 默认 True 生效，行为
   与 0.28 相同（用户 YAML 显式 false 会被面板保存重置——0.28 已存在的行为，备案，见风险 3）。
6. **i18n 零触碰**：不改任何 `msg()` 文案与 `SKILLS_STATIC_PROMPT`，无需刷新 catalogs。
7. **0.28 的 64 行中文操作指南不迁移上游**（R12 优化）：属定制产品文档，改放本批次目录
   `aixcoding/docs/batches/skills-aixcoding-dirs/`，上游 `docs/` 行数归零（旧版 +64）。
8. **v4 的桌面端安装存储追加在同一 user 挂点内**：`desktop_installed_skill_paths()` 由
   `user_aixcoding_skill_paths()` 末尾调用，**不新增上游挂点**（挂点仍 2 处）；开关沿用
   `auto_load_aixcoding_user_skills`（不新增公开配置键）。根目录经 `PlatformInfo.app_data_dir`
   解析（OS 应用数据根属通用平台知识，`AIxCoding` 产品名留在定制包），以便 conftest 既有
   config-dir 重定向机制**机制性隔离**——本机实存 3 个已安装技能，裸推算会污染上游
   `test_adapter.py` 精确断言。只读、只认 `SKILL.md`、不解析桌面端状态文件（见 R12 记录④）。

## R12 迁移方案重审（必答专题）

| 维度 | 旧实现（0.28） | 目标基线（0.34）方案 | 对比结论 |
|---|---|---|---|
| 结构 | 直接改 3 个上游文件，扫描分支硬编码在 `_collect_skill_paths` 函数体内（+31 行）；目录根裸 `Path.home()` | 函数体全部下沉定制包，上游仅两处挂点；目录根挂 platform 单例 | 收敛；上游升级接触面从 40 行业务代码缩到挂点接线 + 1 个 platform 字段 |
| 挂点 | 无挂点概念，逻辑内联 | 两处 lazy import + merge 循环 | 与 auth 批次「1 文件 +16/−1」同形态的默认形态（R1 细则二） |
| 上游行数 | 代码 40 行/3 文件 + 上游测试约 238 行/4 文件 + 上游文档约 90 行/6 文件 + 64 行新上游文档 | 代码约 27 行/4 文件 + 上游测试约 4 行/1 文件 + 上游文档约 40 行/6 文件 | 大幅收敛；旧版 238 行测试全部改落 `aixcoding/tests/`，测试隔离由机制兜底 |

**R12 记录①（行为决策，责任人已裁决 2026-11-09）**：`<cwd>/.aixcoding/skills/` **不受**
`project.skills_enabled` 约束（保持 0.28 行为）。已核实在 0.34 上该门只是 `_collect_skill_paths`
的一个扫描门（`adapter.py:292`），执行侧仅有统一的 `run_skill_script` approval 审批
（`provider.py:775-777`），无按目录来源的二次信任检查——不受限不会被暗门拦截。代价：克隆恶意
仓库时 `.agents/skills` 不自动加载（信任门默认关）而 `.aixcoding/skills` 会自动加载，信任面比
上游宽。动机：桌面端开箱即用；产品自有目录与跨工具目录信任分级不同。需在 skills.md 文档中
明写「`.aixcoding/skills` 不受 Load project skills 开关管控」（TUI 开关 hint 文案不在此批改动）。

**R12 记录②（v2 修订，推翻 v1 结论）**：v1 按 0.28 先例平移「tests/support 三处 + parity 一处
关 aixcoding 开关」。自审发现该形态在 0.34 下**既不必要也不充分**：不必要——上游已有 platform
config-dir 重定向机制，`aixcoding_dir` 入单例后自动隔离；不充分——`test_adapter.py` 有十余处
不走 support 默认的 `skill_names() == [...]` 精确断言（`:252`、`:865`、`:1191` 等），散点开关
防不住（本机 HOME 实存 `~/.aixcoding/skills/hanhai-h5`，必然污染）。同构跟随 = 让定制目录根
享受与 `~/.chrys` 同级的机制性隔离，而非复制 0.28 时代的散点补丁。

**R12 记录③（v3，桌面端目录全景实证）**：对桌面端 `agent_studio_new` 代码核实
（`apps/desktop/src/main/local-skill-layout.ts` 为路径权威，`runtime-composition.ts:1104-1157`
为消费点），桌面端本地技能根共 **7 类**：`<workspace>/.aixcoding/skills`、
`~/.aixcoding/skills`、`~/.aixcoding/market-skills`、`~/.aixcoding/team-skills/<team>`（每个
team 子目录各为一个根，跳过隐藏目录与符号链接）、以及 `.aixcoding_intellij` 镜像树的同构
三根（IDE 管理技能）。0.28 定制只覆盖其中 2 根，**漏识别 5 类**（`market-skills`、
`team-skills`、`.aixcoding_intellij` 三树）；桌面端拉起的 CLI 会话不受影响（桌面端经
`chrys-agent-profile.ts:254-321` 把启用技能物化为 profile `skills.paths` 传入），漏识别只发生在
**CLI 独立会话**场景。补充识别全部落在定制包内部（挂点机制、开关、R2 清单零变化）；
team 子目录由定制包运行时枚举而非把容器根交给 loader——不依赖上游 `MAX_SEARCH_DEPTH=2`
常量，且与桌面端 `userTeamSkillRoots` 的「跳隐藏目录、跳符号链接、按名排序」行为严格一致。
另发现 0.28 次序（user 先于 cwd）与桌面端实测次序（project `unshift` 到最前）相反——
共享语义的正确实现应与桌面端一致，v3 据此修正验收条件 3。

**R12 记录④（v4，桌面端安装存储纳入共享；推翻 `skill-directories.md §一a` 旧结论）**：
原结论「CLI 不扫描、也不应扫描桌面端安装存储」的三条理由中，「绕过桌面端启用/禁用状态」
与「正确通道是 profile 注入」两条对**桌面端拉起的会话**成立，对 **CLI 独立会话**不成立
（后者根本没有 materialized profile）。插件端已在 `aixcoding-continue@75407294` 以
`externalPersonalSkillRoots.ts` 建立同构契约：解析
`<appData>/AIxCoding/<环境>/users/<用户>/private/skills/system`（全部环境 × 全部账号、
跳隐藏目录与符号链接、按名排序、只认 `SKILL.md`），插件自身技能同名优先。责任人 2026-11-18
裁决：**桌面端禁用与否不关心，目录下有就扫**——即「安装 ≠ 启用」，禁用只是桌面端会话内的
选择；据此 CLI 侧做同样的事，并接受「禁用技能在独立会话中可见」这一语义（桌面端
`SetCandidateEnabledRequest` 仅翻转索引里的 flag，`system/` 内容目录不动，见
`file-system-skill-registry.ts:1660-1710`；`#contentDirectory` 的注释亦为
"availability is not authority"）。被否决的替代方案：解析 `active-candidates.json` 的
`enabled` 过滤（耦合另一产品的版本化内部状态文件，格式漂移即误杀/漏过，插件端已明确避开）、
桌面端把启用技能镜像到共享目录（语义最干净，但需跨仓改动与桌面发版协同，本轮不可交付）。

**R12 记录⑤（v5，2026-11-23 阻塞裁决：技能名字符集放宽，责任人已裁决方案 E1）**：v4 交付的
路径层让桌面端安装技能「扫得到」，但 Agent Skills 规范门（`loader.py` 的 `VALID_NAME_RE`，
仅小写 kebab）把桌面端市场/团队技能的大写驼峰名全部拒收（本机实况 3 个：`React-Code-Standard`、
`Vue-Migration-Guide`、`Prompt-Engineering-Handbook`）——「扫得到、用不了」；同一道门也拦
桌面端拉起的会话（profile 物化目录名 = SKILL.md 名）。插件端 `parseSkillMarkdown` 不校验
字符集，CLI 是唯一严格执行上游规范门的端，放宽后三端口径实际收敛。安全性核实：技能名不进
LLM 工具名（仅 `load_skill` / `read_skill_resource` / `run_skill_script` 三个固定工具），
只进 catalog 系统提醒文本（`xml_escape` 后），放宽字符集无协议面风险；`name == 目录名` 门
（`loader.py:444`）不动，驼峰目录名与驼峰 `name` 一致即可过。三方案对比见「备选方案对比」
E1–E3；责任人 2026-11-23 裁决 E1（正则字符集加 `A-Z`，其余约束不动，上游测试文件不改）。
E2（桌面端安装时规范化）留作长期方向，落地后本点按登记表 `removal_condition` 提请退役。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面 | 结论 |
|---|---|---|---|---|
| A 形态平移（照搬 0.28 补丁） | 与旧版逐行一致 | 40 行业务代码进上游 3 文件；裸 HOME 导致测试散点隔离且防不住漏点 | 大 | 否 |
| B1-v1（逻辑下沉 + 裸 HOME + 散点测试隔离） | 逻辑归定制包 | 测试隔离 5 文件散改仍防不住 `test_adapter.py` 漏点 | 中 | 否（v2 取代） |
| **B1-v2 逻辑下沉 + 目录根挂 platform 单例（选定）** | 核心逻辑归定制包；测试隔离机制化、一处 patch 全覆盖；YAML 可配、0.28 配置兼容 | platform dataclass 增 1 字段、conftest 增 2 行 patch | 小 | **是** |
| B2 开关走定制包自有配置（环境变量） | 上游少动 schema/loader | 0.28 用户 YAML 键失效；开关语义脱离 profile 体系 | 更小 | 否（配置兼容性优先） |
| C 完全不动上游 | 零 R2 | `_collect_skill_paths` 为模块私有、`create_skills_provider` 内部直调，只能 monkeypatch；R1 明文「显式小 diff 优于静默 patch」 | — | 否（不可行） |
| **D1（v4 选定）安装存储全量扫描（插件同构）** | 三端口径一致；零新增配置键；所有环境/账号一次覆盖 | 「已禁用」技能在独立会话可见（责任人已接受）；platform/conftest 各增 1 处 | 小 | **是**（R12 记录④） |
| D2 按 `active-candidates.json` 的 `enabled` 过滤 | 尊重桌面端禁用语义 | 解析他产品版本化内部状态文件；格式漂移即误杀/漏过；跨环境/账号合并规则随之变复杂 | 小 | 否（脆弱的隐式契约） |
| D3 桌面端把启用技能镜像到共享目录 | 语义最干净、CLI 侧零上游改动 | 跨仓改动 + 桌面发版协同，本轮不可交付；镜像目录本身还需清理/同步策略 | 零（CLI 侧） | 否（本轮不可行，留作长期方向） |
| **E1（v5 选定）上游规范门字符集加大写** | 单点约 5 行；三端口径实际收敛；fork 行为锚可机检 | 与 Agent Skills 规范（小写 kebab）口径分叉，升级时单点对照 | 小（`loader.py` 低频演进区，0.26 以来未变动该正则） | **是**（R12 记录⑤） |
| E2 桌面端安装时规范化 `name` | 源头统一三端、CLI 零改动 | 跨仓排期；存量已装技能不受益；规范化改变用户可见标识 | 零（CLI 侧） | 否（本轮不可交付，E1 的长期退役通道） |
| E3 fork 宽松 fallback loader | 不动上游 | 重写/绕过上游 load 循环，重复建设；升级锚不稳 | 大（上游重构即漂移） | 否（过度设计） |

## 上游改动清单（R2）

| # | 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|---|
| 1 | `src/chrys/service/skills/adapter.py` | `_collect_skill_paths` 两处挂点（lazy import `user_/cwd_aixcoding_skill_paths` + merge 循环 + try/except logger.debug）；两函数 docstring 的自动加载清单补行（`_collect_skill_paths` 与 `create_skills_provider` 的 `project_skills_enabled` 参数说明） | 约 +15 | 两处挂点上方各一行 `# AIxCoding skills: … (src/chrys/service/aixcoding/skill_paths)` |
| 2 | `src/chrys/foundation/platform/__init__.py` | `PlatformInfo` 增 `aixcoding_dir: Path = field(default_factory=lambda: Path.home()/".aixcoding")`（v2）与 `app_data_dir: Path = field(default_factory=_conventional_app_data_dir)`（v4，OS 应用数据根）+ 一个 `_conventional_app_data_dir()` 辅助函数（win32 `%APPDATA%` / macOS `~/Library/Application Support` / linux `$XDG_CONFIG_HOME\|~/.config` 三分支）+ docstring；`detect_platform()` 调用点零改动 | v2 +3 → **v4 合计约 +12** | 两处上方各一行标记 |
| 3 | `tests/conftest.py` | 两处 `dataclasses.replace(...)` 同步 patch `aixcoding_dir` 与 `app_data_dir`（`_detect_with_pinned_config_dir` 与 `_pin_config_dir`；per-test fixture 复用 `_pin_config_dir`，无需单独改）随 config_dir 重定向 | v2 +6 → **v4 合计 +8**（每处 2 行 patch，含格式化换行） | 两行上方各一行标记 |
| 4 | `src/chrys/service/profiles/agents/schema.py` | `SkillsConfig` 增 `auto_load_aixcoding_user_skills` / `auto_load_aixcoding_cwd_skills`（默认 True）+ 字段 docstring | +7 | 字段块上方一行标记 |
| 5 | `src/chrys/service/profiles/agents/loader.py` | `_parse_skills` 增两行解析 | +2 | 两行上方一行标记 |
| 6 | `docs/en/guides/extensions/skills.md` | 自动加载目录清单补两目录 + 「不受 project.skills_enabled 管控」说明 | 约 +8 | ~~文档不加 marker~~ 改口径：gate 说明段后 `<!-- AIxCoding skills: … -->` 1 处（check_r3_markers 门禁要求 docs diff 新增行带 marker，登记 C167） |
| 7 | `docs/zh-Hans/guides/extensions/skills.md` | 同上（中文） | 约 +8 | 同 C167 口径（登记 C168） |
| 8 | `docs/en/reference/agent-profile.md` | skills 配置键表补两开关 | 约 +8 | 同 C167 口径（登记 C169） |
| 9 | `docs/zh-Hans/reference/agent-profile.md` | 同上（中文） | 约 +8 | 同 C167 口径（登记 C170） |
| 10 | `src/chrys/service/hooks/docs/configuration.md` | 信任模型段补 `.aixcoding/skills/` 提及 | 改 1 行 | 同上 |
|    | **实施备案**：0.34 已重构该段（仅描述 hooks 自身信任门，不再列举技能目录清单），无可补位置——该项自然取消，上游接触面净减少 | | | |
| 11 | `src/chrys/service/hooks/docs/project-hooks.md` | 两处目录清单补提及 | 约 +4 | 同 C167 口径（Goals 列表提及处注释行，登记 C171） |
| 12 | `src/chrys/service/skills/loader.py`（v5） | `VALID_NAME_RE` 字符集加 `A-Z`（结构不变）+ 上方注释与 `validate_skill_metadata` 错误文案同步（"lowercase letters" → "letters"）；其余约束（64 长度、首尾/连续连字符、`name == 目录名`）与上游测试文件不动 | 约 +5 | 正则定义上方 1 行 + 错误文案上方 1 行 `# AIxCoding skills: …` |

**R1 细则二（逐行归属，必答）**：

- 清单 1 挂点行：接线行，无法外置（定制包不能自己被发现，须上游调用）；逻辑已全部外置定制包。
- 清单 2 `aixcoding_dir` / `app_data_dir` 字段：目录根是「测试隔离机制」与「生产路径」的交汇点，
  必须活在 platform 单例里才能被既有 redirect 机制 patch；定制包只是消费方。`app_data_dir`
  只承载 **OS 应用数据根**这一通用平台知识（`%APPDATA%` / `Application Support` / `XDG_CONFIG_HOME`），
  `AIxCoding` 产品目录名与 `private/skills/system` 布局仍留在定制包（归属正确优先于行数最小）。
  **可接受折中**：上游 dataclass 增两个自描述字段，`detect_platform()` 构造点零改动。
- 清单 3 conftest patch 行：隔离机制的组成行，与该机制其他字段的 patch 同址，无法外置。
- 清单 4/5 开关字段与解析：属 aixcoding 产品目录的领域知识，但 `SkillsConfig` 是上游 dataclass、
  由上游 loader 解析并按类型安全传给三条 build 路径——字段只能定义在上游。**可接受折中**：
  与既有 `auto_load_user_agents_skills` 同构，语义内聚于 skills 配置面。
- 清单 6–11 文档：`docs/` 描述上游+定制整体用户可见行为，用户只读上游 docs，无法外置。
- 清单 12 正则与文案（v5）：两处均为 `validate_skill_metadata` 函数体内容，上游无校验挂点
  机制可外置；外置只能 E3 全量接管 load 循环（已否决）。**可接受折中**：与上游规范门同址
  放宽字符集，行为分叉面限定为一个正则字符类 + 一句文案。

合计：约 43 行代码（挂点 15 + platform 12 + conftest 2 + schema 7 + loader 2 + 规范门 5（v5））/ 6 文件
+ 约 37 行文档 / 6 文件（v4 起不动文档清单）。上游测试文件从 v1 的 5 个散点收敛为 conftest 1 处；
对比旧版（40 行代码 + 238 行测试 + 约 90 行文档 + 64 行新上游文档）。

## 定制包新增（R4/R9）

| 文件 | 内容 | 档位判定 |
|---|---|---|
| `src/chrys/service/aixcoding/skill_paths.py`（新） | `user_aixcoding_dir()`（`get_platform().aixcoding_dir` 薄封装）+ `user_aixcoding_skill_paths()` + `cwd_aixcoding_skill_paths()`；v4 增 `desktop_app_data_dir()`（`get_platform().app_data_dir` 薄封装）+ `desktop_installed_skill_paths()`（环境 × 账号枚举） | 依赖：`SkillsConfig`（service）、`SessionEnvironment`（foundation）、`get_platform`（foundation）、标准库——最低容纳档 = service；`test_layering` 绿 |
| `src/chrys/service/aixcoding/__init__.py` | docstring 补记 skill_paths（定制文件，随改） | — |

定制测试（`aixcoding/tests/skills/test_aixcoding_skill_paths.py`，新；按 `aixcoding/tests` 既有主题目录惯例，无 `service/` 层级）：
迁移旧版 `test_adapter.py` aixcoding 部分（+180 行中相关者）与 `test_loader.py` aixcoding 解析
测试（+58 行），形态：monkeypatch `chrys.service.aixcoding.skill_paths.user_aixcoding_dir`
隔离，成员断言；覆盖——七类根加载/开关关（v3：market、team、intellij 各根的成员断言）、
team 子目录枚举（隐藏目录与符号链接跳过、按名排序）、与 `.agents` 的次序（D3）、工作区根
先于用户级根（v3，对齐桌面端）、cwd 绑定 runtime.cwd、`project_skills_enabled=False` 时
aixcoding cwd 仍加载（决策记录的行为锚定）、缺目录不报错、与 chrys/agents 目录去重、
`platform.aixcoding_dir` 重定向后 helper 跟随（隔离机制的回归锚）。
v4 增：桌面端安装存储的环境 × 账号枚举（排序、跳隐藏目录与符号链接）、无环境层级布局兼容、
缺目录得空集、开关关断后整组不出现、次序落在 intellij 树之后与 `.agents` 之前、
**禁用技能同样被扫**（`enabled: false` 的行为锚，防后续误加过滤）、
`platform.app_data_dir` 重定向后 helper 跟随（第二处隔离回归锚）。
测试隔离形态：monkeypatch `skill_paths.desktop_app_data_dir` / `user_aixcoding_dir`（文件系统层），
机制回归则 `dataclasses.replace` platform 单例（与 conftest 同形态）。
另按 R2 表核对 `aixcoding/tools/gen_customizations.py --strict` 登记。

## 对上游隐式行为的假设

1. **`_collect_skill_paths` 是技能目录唯一汇聚点**（三条 build 路径都经 `create_skills_provider`
   → 该函数）→ 挂点一处生效三处 → 失效表现：某 build 路径技能缺失；锚＝`adapter.py:326` 唯一调用点。
2. **发现顺序即同名冲突优先级**（已实证：`loader.py:501-503`「Duplicate skill names keep the
   first discovered skill」、`adapter.py:373-380` merge 同规则）→ 挂点次序决定 D3 语义 →
   失效表现：同名技能加载错源。
3. **测试隔离机制覆盖 `aixcoding_dir`（实现级已核实）**：隔离的 patch 形态是
   `dataclasses.replace(platform, config_dir=…, data_dir=…)`（`tests/conftest.py` 的
   `_detect_with_pinned_config_dir` 与 `_pin_config_dir` 两处）——replace 保留未指定字段，故
   `aixcoding_dir` **必须**在每处 replace 显式同步（清单 3），漏一处即真实 HOME 泄入该层级测试
   → 失效表现：本机 HOME 污染 `test_adapter.py` 精确断言（本地红 CI 绿）；另 `_pin_config_dir`
   经 `_cached_get_platform` 缓存重填兜底全部按值导入，定制包按上游同形态 lazy import
   `get_platform` 即被覆盖。
4. **`SC(...)` dataclass 缺省字段取默认值** → TUI 面板保存不丢定制开关的默认 True →
   失效表现：面板保存后开关变 False（仅当上游改用显式全字段构造）；锚＝`panels/skills.py:510`。
5. **`append_unique` 以 resolve 后字符串去重** → 定制包返回 `expanduser().resolve()` 后的字符串
   才能正确去重 → 定制包实现遵循同一规范。
6. **`PlatformInfo` 为 frozen dataclass、`detect_platform()` 是唯一生产构造点（已核实）**：
   全仓显式构造仅 `detect_platform()`（`__init__.py:175`）与 4 处测试 fixture 关键字构造
   （`reminder_inputs.py:42` 等）——`default_factory` 字段对关键字构造零破坏；duck-typed fake
   platform（如 `test_adapter.py:279`）无该属性 → AttributeError 走挂点全吞错路径静默跳过
   aixcoding 分支，上游 `_collect_skill_paths` 测试语义不变（其本就不关心 aixcoding）→
   失效表现：debug 日志出现 AttributeError（无害）；`test_layering` 与平台测试兜底。
7. **桌面端本地技能布局契约（v3，已对源码核实）**：桌面端以
   `apps/desktop/src/main/local-skill-layout.ts` 为路径权威（`.aixcoding` /
   `.aixcoding_intellij` 两棵 HOME 树 × `skills`/`market-skills`/`team-skills` 三类 +
   `<workspace>/.aixcoding/skills`，技能形态 = `<skill-name>/SKILL.md`，`skill.json` 非必需）；
   CLI 侧按同一布局枚举即可双向共享 → 失效表现：桌面端改布局时 CLI 静默漏识别（无告警）；
   缓解：`aixcoding/tests` 锚定本文档化的布局清单，桌面端布局变更时锚定测试在联调中暴露。
8. **team 目录枚举与桌面端行为一致（v3）**：定制包运行时 `os.scandir` 枚举
   `team-skills` 子目录，跳过隐藏目录（`.` 前缀）与符号链接、按名排序——镜像
   `userTeamSkillRoots`（`local-skill-layout.ts:76-87`）；不依赖上游 `MAX_SEARCH_DEPTH`。
9. **桌面端安装存储布局契约（v4，已对源码与本机实况核实，与插件端 75407294 同构）**：
   `rootDirectory = <账号目录>/private/skills`（`runtime-composition.ts:1079-1083`），内容目录
   `system`（`file-system-skill-registry.ts:2237-2239`）；账号目录 = `users/<key>`，
   环境目录 = `<appData>/AIxCoding/<dataNamespace>`，命名空间集合
   `production|staging|preview|development`（`release-flavor.ts:425-458`），
   `<appData>` 由 `prepareDesktopDataRoot(app.getPath('appData'))` 固定拼 `AIxCoding`
   （`desktop-data-root.ts:5-7`）→ 失效表现：桌面端改布局时 CLI 静默漏识别；
   缓解：定制测试锚定本文档化的层级清单，联调时暴露。
   枚举口径与插件端 `getDesktopInstalledSkillRoots` 逐条一致：**用户容器 = 数据根 + 数据根的
   每个真实子目录**（后者通常就是环境），每个容器下再取 `users/` 的真实子目录，账号下
   `private/skills/system` 为真实目录（非符号链接）即收入；环境与账号均按名排序。
   注 1：遗留迁移形态下 `<appData>/AIxCoding` 可能是指向 `AgentStudio` 的 junction/symlink
   （`desktop-data-root.ts:29-30`），解析用 `is_dir()`（跟随链接）+ `resolve()`，不对**数据根**
   本身做符号链接拒绝；枚举出的环境/账号/`system` 目录仍拒绝链接（插件 `isRealDirectory`
   用 lstat 同判）。
   注 2：插件端的 `AIXCODING_DESKTOP_DATA_ROOT` 环境变量覆盖是它的测试钩子，CLI 侧**不复制**
   （避免多一个隐式配置面）；CLI 的测试改用 monkeypatch `desktop_app_data_dir` / platform 字段。
10. **桌面端「禁用」只翻索引 flag、内容目录保留（v4，已核实）**：
    `SetCandidateEnabledRequest` 仅改 `active-candidates.json` 里的 `enabled`
    （`file-system-skill-registry.ts:1660-1710`），`system/` 下的包不移动不删除 —
    → 扫 `system/` 必然包含禁用技能；这是 2026-11-18 责任人明确接受的语义（R12 记录④），
    不是缺陷。若上游/桌面端改为「禁用即删目录」，行为自然收敛，无需改代码。
11. **技能名不进 LLM 工具名（v5，已核实）**：技能面只暴露三个固定工具（`load_skill` /
    `read_skill_resource` / `run_skill_script`），技能名仅进 catalog 系统提醒文本
    （`xml_escape` 后）与警告消息 → 字符集放宽无工具名协议约束风险 → 失效表现：若上游未来
    把技能名物化为 per-skill 工具名，驼峰名可能撞上游工具名正则；缓解：本条 + 行为锚测试
    在升级时暴露。

## 定制点登记预告

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C163-C166 | src/chrys/service/skills/adapter.py | AIxCoding skills: | 4 | `_collect_skill_paths` 挂点×2 + 降级注释×2 | 低：上游重写 `_collect_skill_paths` 函数体时挂点漂移（`--strict` 报计数不符） | 〔上游等价〕上游原生提供桌面共享技能目录的合并机制 |
| C158 | src/chrys/foundation/platform/__init__.py | AIxCoding skills: | 2 | `PlatformInfo` 字段区（v2 `aixcoding_dir` + v4 `app_data_dir`） | 低：上游演进 `PlatformInfo` 字段集时冲突，diff 面小 | 〔上游等价〕`PlatformInfo` 原生提供等价产品目录字段 |
| C159-C160 | tests/conftest.py | AIxCoding skills: | 2 | config-dir 重定向两处 `dataclasses.replace` | 中：上游改 redirect 机制形态时需跟随（该机制 0.32→0.34 稳定） | 〔上游等价〕重定向机制原生覆盖新增字段 |
| skills-aixcoding-dirs:conftest-app-data-dir | tests/conftest.py | AIxCoding skills: keep the desktop app-data root inside the pinned sandbox | 2 | 两处 `dataclasses.replace` 的 `app_data_dir` patch 行（v4） | 中：随 C159-C160 | 随 C159-C160 |
| C161 | src/chrys/service/profiles/agents/schema.py | AIxCoding skills: | 1 | `SkillsConfig` 开关字段区 | 低：上游重排字段区时冲突面小 | 〔配置契约变更〕本 design ADR 判定决策一反转（开关撤离 profile schema） |
| C162 | src/chrys/service/profiles/agents/loader.py | AIxCoding skills: | 1 | `_parse_skills` 解析块 | 低：随 C161 | 随 C161 |
| skills-aixcoding-dirs:loader-name-charset | src/chrys/service/skills/loader.py | AIxCoding skills: | 2 | `VALID_NAME_RE` 定义 + `validate_skill_metadata` 错误文案（v5，R12 记录⑤） | 低：上游演进该正则/文案时冲突面 ≤5 行（0.26 以来未变动）；`--strict` 报计数不符 | 〔政策变更〕桌面端安装时规范化 `name`（E2）落地后提请退役；〔上游等价〕上游自身放宽规范门时以上游为准 |

<!-- 2026-11-11 备案：原 C167-C171（docs/en、docs/zh-Hans 四页与 project-hooks.md 的
     marker 登记）随文档改动整体还原而撤销——该批改动与 main_aixcoding_cli 上并行
     的文档更新冲突，实施改为不动任何既有文档；手册缺口由并行的文档更新批次补齐。 -->


## 风险与最坏情况

1. **信任面宽于上游**（R12 记录①，责任人已接受）：工作区 `.aixcoding/skills` 的 SKILL.md 指令
   无信任门直接进上下文，脚本仍受 approval 审批。缓解：文档明示；回滚＝两开关 YAML 置 false
   或未来补门（另批）。
2. **挂点静默降级**：try/except 吞错后仅 `logger.debug`，现场定制包损坏时表现为"aixcoding 技能
   不出现"。可观测性：debug 日志；wheel 完整性由 `check_wheel.py` 与 CI 保障。
3. **TUI 面板保存重置开关**（0.28 已存在行为，平移）：YAML 显式 `auto_load_aixcoding_*_skills: false`
   的用户经 TUI 保存 profile 后开关回 True。备案：如需面板开关，另批走 R2。
4. **`aixcoding_dir` / `app_data_dir` 进 platform 单例的语义漂移风险**：上游未来若在 redirect 之外
   再引 config_dir/app-data 派生逻辑（如 sandbox 路径），需确认覆盖两个字段；
   `gen_customizations.py --strict` 的 marker 计数与 `aixcoding/tests` 回归锚（假设 3）双保险。
5. **上游 0.35+ 重排 `_collect_skill_paths`**：挂点漂移由 `--strict` CI 门侦测。
6. **回滚路径**：两开关置 false 即用户级回滚；代码级单 commit revert（挂点 + 字段 + 定制包互不纠缠）。
   v4 单独回滚 = 删 `desktop_installed_skill_paths` 调用 + 两处 platform/conftest 字段行。
7. **最坏情况**：`~/.aixcoding/skills` 存在同名恶意技能且用户机器装了桌面端——技能发现无门，
   靠 approval 拦脚本。与 0.28 现网行为一致，非本批引入的新形态。
8. **（v4）桌面端禁用技能在独立会话可见**（责任人已接受，R12 记录④）：桌面端 UI 的"禁用"
   只影响桌面端会话，CLI 独立会话仍可发现并加载其 SKILL.md 指令。缓解：`skill-directories.md`
   写清「安装 ≠ 启用」；整组可用 `auto_load_aixcoding_user_skills: false` 关闭；脚本执行
   仍经 approval。若后续产品口径反转，正道是 D3（桌面端镜像启用技能），不是解析状态文件。
9. **（v4）跨环境/跨账号合并**：同一机器多个环境（development/production）或多个账号安装同名
   技能时按枚举次序先到先得（环境目录按名排序、账号目录按名排序），可能加载"另一个账号"
   的技能。缓解：属同一 OS 用户的可读数据，不构成新的越权面；文档明示合并规则。
10. **（v5）与 Agent Skills 规范口径分叉**：上游按规范（小写 kebab）实现，fork 放宽为同时接受
    大写——上游未来收紧或改写规范门时需单点对照（登记 anchor + fork 行为锚测试双保险）。
    回滚：revert 该约 5 行即恢复上游规范门（被拒技能回到 `skill_load_error`，与 0.35.2 现状一致）。

## ADR 判定

- ① 有被认真考虑但否决的备选 → **是**（A / B1-v1 / B2 / C，含两处挂点 vs 一处挂点的次序取舍、
  裸 HOME vs platform 单例的隔离取舍；v4 增 D1/D2/D3 的扫描范围与禁用语义取舍，见
  「备选方案对比」与 R12 记录④）。
- ② 撤销代价高 → **是**：`auto_load_aixcoding_*_skills` 是对外配置契约（用户 YAML 可写），
  撤销即破坏 0.28 迁移用户的配置；目录语义一旦被桌面端与用户技能投放大规模使用，删除代价高；
  v4 的安装存储一旦被当作"安装即可用"承诺，撤除会造成桌面端装好的技能在 CLI 突然消失。
- ③ 约束未来工作模式 → **是**：后来者必问「为什么 `.aixcoding/skills` 不受 Load project skills
  管而 `.agents/skills` 受」（R12 记录①）、「为什么 `aixcoding_dir` / `app_data_dir` 是 platform
  字段」（v2/v4 的隔离机制依赖）、以及「为什么扫到桌面端禁用技能也算正确行为」（v4，R12 记录④）。
- ④ 依赖上游非公开接口 → 否（定制包仅依赖公开的 `SkillsConfig` / `SessionEnvironment` /
  `get_platform`；挂点由上游调用定制包，方向相反；conftest patch 属上游测试自身机制）。

结论：①②③ 成立 → 出批次 ADR（2026-11-09 已签认）。

> **2026-11-11 备案（责任人裁决，仿 user-manual 批次先例）**：该 ADR 不再以独立文件存在，
> 已从本批次 `adr/` 撤销——并行批次治理（standards/adr/0024 起）将决策文档收归全局池、
> 批次 `adr/` 池废止，且 0001 号与全局池既有文件重号不可保留。四个决策（配置契约、
> cwd 不受信任门管控、目录根挂 platform 单例、七类根与桌面端同序）的完整记录由本
> design「方案概述」「对上游隐式行为的假设」与「风险与最坏情况」承载，测试行为锚
> `test_cwd_aixcoding_skills_load_despite_project_gate_off` 改指本节。
>
> **2026-11-18 备案（v4 需求变更，同一惯例）**：v4 的决策（安装存储全量扫描、安装 ≠ 启用、
> 复用 user 开关、`app_data_dir` 通用字段）同样不另起 ADR——记录由 R12 记录④、
> 「备选方案对比」D1/D2/D3、「对上游隐式行为的假设」9/10 与风险 8/9 承载，
> 测试行为锚为 `aixcoding/tests/skills` 的禁用技能与地址重定向两条用例。
>
> **2026-11-23 备案（v5 阻塞裁决，同一惯例）**：v5 的决策（规范门字符集加大写、E2/E3 否决）
> 不另起 ADR——记录由 R12 记录⑤、「备选方案对比」E1–E3、「对上游隐式行为的假设」11 与
> 风险 10 承载，测试行为锚为 `aixcoding/tests/skills` 的驼峰名接受与下划线拒绝两条用例。

## 验证方式（实施阶段执行，此处为计划）

- 统一入口：`uv run python aixcoding/tools/verify.py --smart --paths <本批全部改动文件>`；
- 定制套件：`uv run pytest aixcoding/tests/skills -n0`；
- **污染回归（本批特有）**：在 HOME 存在真实 `~/.aixcoding/skills`（实况 `hanhai-h5`）且桌面端
  安装存储存在真实技能（实况 3 个）的本机
  跑 `uv run pytest tests/service/skills/test_adapter.py -n0` 与 `tests/orchestration/workflows/test_agent_parity.py -n0`，
  全绿方证隔离机制生效；
- 冒烟（真实 HOME/工作区）：`uv run aixcoding-cli run "列出可用技能" -a Code` 确认
  `hanhai-h5` 与桌面端安装的 `React-Code-Standard` 等被发现，且 `.agents` 同名时 aixcoding 胜出；
- 门禁：ruff / format / `ty check --error-on-warning`（三平台）；i18n 无需刷新（零 msg 改动）；
- `uv run python aixcoding/tools/gen_customizations.py --strict` 登记核对；
- （v5）`uv run pytest aixcoding/tests/skills -n0`（驼峰接受 + 下划线拒绝锚）与
  `uv run pytest tests/service/skills/test_loader.py tests/service/skills/test_adapter.py -n0`
  （上游语义不变，`Bad_Name` 反例须仍绿）；冒烟确认本机实存 3 个驼峰技能从
  `skill_load_error` 变为可加载。
