# 设计：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-09
- 确认意见：能不动上游代码就不动，必须要动要少动，少而集中的动

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

## 目标与验收条件

把 0.28 分支（`origin/main_aixcoding_cli_0.28.0_final`，提交 `a7631f26` + `c174727b` + `2b055caf`）
的 SKILL 定制迁移到 0.34 基线，并对齐桌面端 `agent_studio_new` 的本地技能布局
（`apps/desktop/src/main/local-skill-layout.ts`）：自动加载桌面端全部本地技能根（v3 扩展），
与 AIxCoding 桌面客户端共享技能目录。

验收条件：

1. `~/.aixcoding` 用户级全树（开关 `auto_load_aixcoding_user_skills`，默认 True）被自动扫描：
   `skills/`、`market-skills/`、`team-skills/<team>/`（team 子目录逐个枚举，跳过隐藏目录与
   符号链接，与桌面端 `userTeamSkillRoots` 行为一致），以及 `.aixcoding_intellij` 镜像树的
   同构三根；
2. `<cwd>/.aixcoding/skills/`（开关 `auto_load_aixcoding_cwd_skills`，默认 True）被自动扫描，
   绑定 `runtime.cwd`（跟随 `/chdir` 软重启），**不受 `project.skills_enabled` 约束**（责任人裁决，见 R12 记录①）；
3. 扫描次序对齐桌面端 `runtime-composition.ts:1104-1157` 实测次序（工作区根优先于用户级根，
   v3 修订，替代 0.28 次序）：
   `~/.chrys/skills` → `<cwd>/.aixcoding/skills` → `~/.aixcoding/{skills → market-skills →
   team-skills/<team>}` → `~/.aixcoding_intellij/{同构三根}` → `~/.agents/skills` →
   `<cwd>/.agents/skills`（aixcoding 同名技能优先于对应 `.agents` 目录，D3 保持；先到先得
   已实证：`loader.py:501-503`、`adapter.py:373-380`）；
4. 两个开关可经 agent profile YAML 配置，旧 0.28 用户配置文件无需改动（开关语义按目录树
   归属：user 开关管两棵 HOME 树，cwd 开关管工作区根）；
5. 三条 build 路径（主 agent / 子代理 / 工作流节点）行为一致（共用 `_collect_skill_paths`，天然一致）；
6. 开发机 HOME 下存在真实 `~/.aixcoding/skills/` 内容（本机实况：`hanhai-h5`）时，上游测试
   套件不因定制变红——由 platform 重定向机制**机制性**保证，不依赖逐测试关开关；
7. CLI 独立会话（不经桌面端拉起）能发现桌面端放入任一本地根的技能，实现双向共享。

## 方案概述（B1：函数体下沉定制包，上游留挂点；目录根挂 platform 单例）

```
_collect_skill_paths（上游 adapter.py，仅两处挂点）
    chrys_user_dir          （上游，原样：get_platform().config_dir/skills）
    ┌─ 挂点1: cwd_aixcoding_skill_paths(config, runtime) ← 定制包（工作区根，对齐桌面端 project 优先）
    │      <cwd>/.aixcoding/skills  [auto_load_aixcoding_cwd_skills]
    ├─ 挂点2: user_aixcoding_skill_paths(config) ← 定制包（HOME 两棵树，内部次序对齐 runtime-composition）
    │      ~/.aixcoding/skills → ~/.aixcoding/market-skills → ~/.aixcoding/team-skills/<team>…
    │      → ~/.aixcoding_intellij/skills → …/market-skills → …/team-skills/<team>…
    │      [auto_load_aixcoding_user_skills]
    ├─ .agents user 分支      （上游，原样：user_agents_dir()/skills）
    └─ .agents cwd 分支       （上游，原样，project_skills_enabled 门保留）

定制包 src/chrys/service/aixcoding/skill_paths.py（新文件，service 档）
    user_aixcoding_dir() -> Path            # get_platform().aixcoding_dir（薄封装，monkeypatch 锚）
    user_aixcoding_skill_paths(config)          # 开关1 + 两棵 HOME 树全根枚举（team 子目录运行时
                                                # readdir，跳过隐藏目录与符号链接，对齐桌面端
                                                # userTeamSkillRoots；expanduser().resolve()）
    cwd_aixcoding_skill_paths(config, runtime)  # 开关2 + runtime.cwd；不读 project_skills_enabled

platform：PlatformInfo 增 aixcoding_dir 字段（默认 Path.home()/".aixcoding"，平台无关）
上游 tests/conftest.py：三处 replace（_detect_with_pinned_config_dir / _pin_config_dir /
fixture）同步 patch 该字段
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

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面 | 结论 |
|---|---|---|---|---|
| A 形态平移（照搬 0.28 补丁） | 与旧版逐行一致 | 40 行业务代码进上游 3 文件；裸 HOME 导致测试散点隔离且防不住漏点 | 大 | 否 |
| B1-v1（逻辑下沉 + 裸 HOME + 散点测试隔离） | 逻辑归定制包 | 测试隔离 5 文件散改仍防不住 `test_adapter.py` 漏点 | 中 | 否（v2 取代） |
| **B1-v2 逻辑下沉 + 目录根挂 platform 单例（选定）** | 核心逻辑归定制包；测试隔离机制化、一处 patch 全覆盖；YAML 可配、0.28 配置兼容 | platform dataclass 增 1 字段、conftest 增 2 行 patch | 小 | **是** |
| B2 开关走定制包自有配置（环境变量） | 上游少动 schema/loader | 0.28 用户 YAML 键失效；开关语义脱离 profile 体系 | 更小 | 否（配置兼容性优先） |
| C 完全不动上游 | 零 R2 | `_collect_skill_paths` 为模块私有、`create_skills_provider` 内部直调，只能 monkeypatch；R1 明文「显式小 diff 优于静默 patch」 | — | 否（不可行） |

## 上游改动清单（R2）

| # | 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|---|
| 1 | `src/chrys/service/skills/adapter.py` | `_collect_skill_paths` 两处挂点（lazy import `user_/cwd_aixcoding_skill_paths` + merge 循环 + try/except logger.debug）；两函数 docstring 的自动加载清单补行（`_collect_skill_paths` 与 `create_skills_provider` 的 `project_skills_enabled` 参数说明） | 约 +15 | 两处挂点上方各一行 `# AIxCoding skills: … (src/chrys/service/aixcoding/skill_paths)` |
| 2 | `src/chrys/foundation/platform/__init__.py` | `PlatformInfo` 增 `aixcoding_dir: Path = field(default_factory=lambda: Path.home()/".aixcoding")` 字段 + docstring（平台无关，桌面端共享契约 = 字面 HOME 目录）；`detect_platform()` 调用点零改动 | +3 | 字段上方一行标记 |
| 3 | `tests/conftest.py` | 两处 `dataclasses.replace(...)` 同步 patch `aixcoding_dir`（`_detect_with_pinned_config_dir` 与 `_pin_config_dir`；per-test fixture 复用 `_pin_config_dir`，无需单独改）随 config_dir 重定向 | +6（含格式化换行） | 两行上方各一行标记 |
| 4 | `src/chrys/service/profiles/agents/schema.py` | `SkillsConfig` 增 `auto_load_aixcoding_user_skills` / `auto_load_aixcoding_cwd_skills`（默认 True）+ 字段 docstring | +7 | 字段块上方一行标记 |
| 5 | `src/chrys/service/profiles/agents/loader.py` | `_parse_skills` 增两行解析 | +2 | 两行上方一行标记 |
| 6 | `docs/en/guides/extensions/skills.md` | 自动加载目录清单补两目录 + 「不受 project.skills_enabled 管控」说明 | 约 +8 | ~~文档不加 marker~~ 改口径：gate 说明段后 `<!-- AIxCoding skills: … -->` 1 处（check_r3_markers 门禁要求 docs diff 新增行带 marker，登记 C167） |
| 7 | `docs/zh-Hans/guides/extensions/skills.md` | 同上（中文） | 约 +8 | 同 C167 口径（登记 C168） |
| 8 | `docs/en/reference/agent-profile.md` | skills 配置键表补两开关 | 约 +8 | 同 C167 口径（登记 C169） |
| 9 | `docs/zh-Hans/reference/agent-profile.md` | 同上（中文） | 约 +8 | 同 C167 口径（登记 C170） |
| 10 | `src/chrys/service/hooks/docs/configuration.md` | 信任模型段补 `.aixcoding/skills/` 提及 | 改 1 行 | 同上 |
|    | **实施备案**：0.34 已重构该段（仅描述 hooks 自身信任门，不再列举技能目录清单），无可补位置——该项自然取消，上游接触面净减少 | | | |
| 11 | `src/chrys/service/hooks/docs/project-hooks.md` | 两处目录清单补提及 | 约 +4 | 同 C167 口径（Goals 列表提及处注释行，登记 C171） |

**R1 细则二（逐行归属，必答）**：

- 清单 1 挂点行：接线行，无法外置（定制包不能自己被发现，须上游调用）；逻辑已全部外置定制包。
- 清单 2 `aixcoding_dir` 字段：目录根是「测试隔离机制」与「生产路径」的交汇点，必须活在 platform
  单例里才能被既有 redirect 机制 patch；定制包只是消费方。**可接受折中**：上游 dataclass 增一个
  自描述字段，`detect_platform()` 构造点零改动。
- 清单 3 conftest patch 行：隔离机制的组成行，与该机制其他字段的 patch 同址，无法外置。
- 清单 4/5 开关字段与解析：属 aixcoding 产品目录的领域知识，但 `SkillsConfig` 是上游 dataclass、
  由上游 loader 解析并按类型安全传给三条 build 路径——字段只能定义在上游。**可接受折中**：
  与既有 `auto_load_user_agents_skills` 同构，语义内聚于 skills 配置面。
- 清单 6–11 文档：`docs/` 描述上游+定制整体用户可见行为，用户只读上游 docs，无法外置。

合计：约 29 行代码（挂点 15 + platform 3 + conftest 2 + schema 7 + loader 2）/ 5 文件
+ 约 37 行文档 / 6 文件。上游测试文件从 v1 的 5 个散点收敛为 conftest 1 处；对比旧版
（40 行代码 + 238 行测试 + 约 90 行文档 + 64 行新上游文档）。

## 定制包新增（R4/R9）

| 文件 | 内容 | 档位判定 |
|---|---|---|
| `src/chrys/service/aixcoding/skill_paths.py`（新） | `user_aixcoding_dir()`（`get_platform().aixcoding_dir` 薄封装）+ `user_aixcoding_skill_paths()` + `cwd_aixcoding_skill_paths()` | 依赖：`SkillsConfig`（service）、`SessionEnvironment`（foundation）、`get_platform`（foundation）、标准库——最低容纳档 = service；`test_layering` 绿 |
| `src/chrys/service/aixcoding/__init__.py` | docstring 补记 skill_paths（定制文件，随改） | — |

定制测试（`aixcoding/tests/skills/test_aixcoding_skill_paths.py`，新；按 `aixcoding/tests` 既有主题目录惯例，无 `service/` 层级）：
迁移旧版 `test_adapter.py` aixcoding 部分（+180 行中相关者）与 `test_loader.py` aixcoding 解析
测试（+58 行），形态：monkeypatch `chrys.service.aixcoding.skill_paths.user_aixcoding_dir`
隔离，成员断言；覆盖——七类根加载/开关关（v3：market、team、intellij 各根的成员断言）、
team 子目录枚举（隐藏目录与符号链接跳过、按名排序）、与 `.agents` 的次序（D3）、工作区根
先于用户级根（v3，对齐桌面端）、cwd 绑定 runtime.cwd、`project_skills_enabled=False` 时
aixcoding cwd 仍加载（决策记录的行为锚定）、缺目录不报错、与 chrys/agents 目录去重、
`platform.aixcoding_dir` 重定向后 helper 跟随（隔离机制的回归锚）。
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

## 定制点登记预告

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C163-C166 | src/chrys/service/skills/adapter.py | AIxCoding skills: | 4 | `_collect_skill_paths` 挂点×2 + 降级注释×2 | 低：上游重写 `_collect_skill_paths` 函数体时挂点漂移（`--strict` 报计数不符） | 〔上游等价〕上游原生提供桌面共享技能目录的合并机制 |
| C158 | src/chrys/foundation/platform/__init__.py | AIxCoding skills: | 1 | `PlatformInfo` 字段区 | 低：上游演进 `PlatformInfo` 字段集时冲突，diff 面小 | 〔上游等价〕`PlatformInfo` 原生提供等价产品目录字段 |
| C159-C160 | tests/conftest.py | AIxCoding skills: | 2 | config-dir 重定向两处 `dataclasses.replace` | 中：上游改 redirect 机制形态时需跟随（该机制 0.32→0.34 稳定） | 〔上游等价〕重定向机制原生覆盖新增字段 |
| C161 | src/chrys/service/profiles/agents/schema.py | AIxCoding skills: | 1 | `SkillsConfig` 开关字段区 | 低：上游重排字段区时冲突面小 | 〔配置契约变更〕本 design ADR 判定决策一反转（开关撤离 profile schema） |
| C162 | src/chrys/service/profiles/agents/loader.py | AIxCoding skills: | 1 | `_parse_skills` 解析块 | 低：随 C161 | 随 C161 |

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
4. **`aixcoding_dir` 进 platform 单例的语义漂移风险**：上游未来若在 redirect 之外再引 config_dir
   派生逻辑（如 sandbox 路径），需确认覆盖 `aixcoding_dir`；`gen_customizations.py --strict`
   的 marker 计数与 `aixcoding/tests` 回归锚（假设 3）双保险。
5. **上游 0.35+ 重排 `_collect_skill_paths`**：挂点漂移由 `--strict` CI 门侦测。
6. **回滚路径**：两开关置 false 即用户级回滚；代码级单 commit revert（挂点 + 字段 + 定制包互不纠缠）。
7. **最坏情况**：`~/.aixcoding/skills` 存在同名恶意技能且用户机器装了桌面端——技能发现无门，
   靠 approval 拦脚本。与 0.28 现网行为一致，非本批引入的新形态。

## ADR 判定

- ① 有被认真考虑但否决的备选 → **是**（A / B1-v1 / B2 / C，含两处挂点 vs 一处挂点的次序取舍、
  裸 HOME vs platform 单例的隔离取舍）。
- ② 撤销代价高 → **是**：`auto_load_aixcoding_*_skills` 是对外配置契约（用户 YAML 可写），
  撤销即破坏 0.28 迁移用户的配置；目录语义一旦被桌面端与用户技能投放大规模使用，删除代价高。
- ③ 约束未来工作模式 → **是**：后来者必问「为什么 `.aixcoding/skills` 不受 Load project skills
  管而 `.agents/skills` 受」（R12 记录①）以及「为什么 `aixcoding_dir` 是 platform 字段」（v2 的
  隔离机制依赖）。
- ④ 依赖上游非公开接口 → 否（定制包仅依赖公开的 `SkillsConfig` / `SessionEnvironment` /
  `get_platform`；挂点由上游调用定制包，方向相反；conftest patch 属上游测试自身机制）。

结论：①②③ 成立 → 出批次 ADR（2026-11-09 已签认）。

> **2026-11-11 备案（责任人裁决，仿 user-manual 批次先例）**：该 ADR 不再以独立文件存在，
> 已从本批次 `adr/` 撤销——并行批次治理（standards/adr/0024 起）将决策文档收归全局池、
> 批次 `adr/` 池废止，且 0001 号与全局池既有文件重号不可保留。四个决策（配置契约、
> cwd 不受信任门管控、目录根挂 platform 单例、七类根与桌面端同序）的完整记录由本
> design「方案概述」「对上游隐式行为的假设」与「风险与最坏情况」承载，测试行为锚
> `test_cwd_aixcoding_skills_load_despite_project_gate_off` 改指本节。

## 验证方式（实施阶段执行，此处为计划）

- 统一入口：`uv run python aixcoding/tools/verify.py --smart --paths <本批全部改动文件>`；
- 定制套件：`uv run pytest aixcoding/tests/skills -n0`；
- **污染回归（本批特有）**：在 HOME 存在真实 `~/.aixcoding/skills` 的本机（实况 `hanhai-h5`）
  跑 `uv run pytest tests/service/skills/test_adapter.py -n0` 与 `tests/orchestration/workflows/test_agent_parity.py -n0`，
  全绿方证隔离机制生效；
- 冒烟（真实 HOME/工作区）：`uv run aixcoding-cli run "列出可用技能" -a Code` 确认
  `hanhai-h5` 被发现，且 `.agents` 同名时 aixcoding 胜出；
- 门禁：ruff / format / `ty check --error-on-warning`（三平台）；i18n 无需刷新（零 msg 改动）；
- `uv run python aixcoding/tools/gen_customizations.py --strict` 登记核对。
