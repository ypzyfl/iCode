# ADR-0001：aixcoding 技能目录的配置契约、信任分级与目录根落位

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-XXXX 取代）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-09
- 确认意见：能不动上游代码就不动，必须要动要少动，少而集中的动（可选；审阅中形成的判断、附加条件或保留）

> 本文为决策时点快照；现行规则以 `DEVELOPMENT.md` R2/R5 为准。信任分级与配置兼容性
> 是产品决策，无规范对应。批次上下文见 `batches/skills-aixcoding-dirs/design.md`（v2.1，已签认）。

## 背景

0.28 分支（`origin/main_aixcoding_cli_0.28.0_final`）的 SKILL 定制——自动加载
`~/.aixcoding/skills/` 与 `<cwd>/.aixcoding/skills/`（与 AIxCoding 桌面客户端共享技能目录）——
未随 `chore/merge_upstream_v0.34.0` 迁入当前基线。迁移重审（R12）发现三个决策点相互绑定，
撤销代价高，须以 ADR 固化：

1. 开关放哪（配置契约面）；
2. `<cwd>/.aixcoding/skills/` 受不受上游 0.34 新引入的项目信任门（`project.skills_enabled`，
   默认关）管控；
3. 目录根 `~/.aixcoding` 放裸 `Path.home()` 还是 platform 单例（决定上游测试能否被
   既有重定向机制隔离）。

## 决策

**一、开关进 `SkillsConfig`（YAML 对外契约）**：新增 `auto_load_aixcoding_user_skills` /
`auto_load_aixcoding_cwd_skills` 两字段（默认 True），与既有 `auto_load_user_agents_skills`
同构。0.28 用户的 profile YAML 零迁移成本。

**二、cwd 目录不受信任门管控**：`<cwd>/.aixcoding/skills/` 不经过 `project_skills_enabled`
判断（保持 0.28 行为）。已核实 0.34 的信任门只是 `_collect_skill_paths` 的一个扫描门
（`adapter.py:292`），执行侧仅有统一的 `run_skill_script` approval 审批——不受限不会被暗门拦截。

**三、目录根挂 platform 单例**：`PlatformInfo` 增 `aixcoding_dir` 字段
（`default_factory=Path.home()/".aixcoding"`，平台无关，桌面端共享契约 = 字面 HOME 目录），
定制包薄封装消费；上游测试的 config-dir 重定向机制（`_pin_config_dir` /
`_isolate_platform_config_dir`）在既有 replace 点同步 patch 该字段，全部上游测试获得机制性隔离。

**四、识别桌面端全部本地技能根，次序对齐桌面端（v3 补充）**：对桌面端
`agent_studio_new` 源码核实（`local-skill-layout.ts` 路径权威、`runtime-composition.ts:1104-1157`
消费点），CLI 自动扫描扩展为桌面端全部 7 类根——`<workspace>/.aixcoding/skills`、
`~/.aixcoding/{skills,market-skills,team-skills/<team>}`、`~/.aixcoding_intellij` 同构三根；
0.28 只覆盖 2 根，`market-skills`/`team-skills`/`.aixcoding_intellij` 在 CLI 独立会话中漏识别。
扫描次序以桌面端实测为准：工作区根优先于用户级根（`roots.unshift(project)`），0.28 的
「user 先于 cwd」次序作废。开关语义按树归属归并：user 开关管两棵 HOME 树，cwd 开关管
工作区根——不为七类根增设独立开关，配置面保持 0.28 兼容。

## 理由

- **一**：开关语义属 skills 配置面（与 `.agents` 两开关并列），进 dataclass 才能被上游 loader
  解析、类型安全地流经三条 build 路径；自定义通道（B2）会让 0.28 用户 YAML 键失效。
- **二**：0.28 时代上游尚无信任门，「不受限」当年是零成本默认；0.34 下它是显式重做的产品决策——
  桌面端开箱即用优先于项目信任门，产品自有目录（`.aixcoding`）与跨工具共享目录（`.agents`）
  信任分级不同。脚本仍受 approval 审批，信任面增量可控且文档披露。
- **三**：`dataclasses.replace` 保留未指定字段（`tests/conftest.py:447/:474` 实证），裸
  `Path.home()` 天然绕过重定向——0.28 被迫在上游测试 5 个文件散点关开关，且防不住
  `test_adapter.py` 十余处 `skill_names() == [...]` 精确断言（本机 HOME 实存技能 `hanhai-h5`，
  必然污染）。字段入单例后 patch 三处 replace 即全覆盖，并自动覆盖未来上游新增测试。

被否决的备选与死因：

- **A 形态平移（照搬 0.28 补丁）**：40 行业务代码进上游 3 文件，每文件都是 0.35+ 升级冲突点；
  违背 R1 细则二默认形态（函数体归定制包、上游留挂点）。
- **B1-v1（逻辑下沉但保留裸 HOME + 散点测试隔离）**：逻辑收敛达标，但测试隔离散且漏。
- **B2（开关走环境变量）**：上游少动两个文件，但破坏 0.28 用户配置兼容。
- **C（完全不动上游）**：`_collect_skill_paths` 为模块私有、`create_skills_provider` 内部直调，
  只能 monkeypatch；R1 明文「显式小 diff 优于静默 patch」，不可行。
- **一处挂点（逻辑上可省 7 行）**：会把 aixcoding cwd 提到 `.agents` user 之前，"项目
  aixcoding 技能 vs 用户 `.agents` 技能"同名冲突胜负翻转（先到先得已实证：
  `loader.py:501-503`），可观测行为差异，不做。

## 后果

- **信任面**：工作区 `.aixcoding/skills` 的 SKILL.md 指令无信任门直接进上下文（脚本仍受
  approval）。后来者若只看上游设置项会疑惑「为何 Load project skills 管不住它」——本文与
  `docs/*/guides/extensions/skills.md` 的明示段落是解释入口。
- **配置契约**：两开关一经发布即对外承诺；删除或改默认值=破坏 0.28 迁移用户配置，
  变更须重新过 ADR。
- **测试义务**：`aixcoding/tests` 须有「cwd 目录在 `project_skills_enabled=False` 下仍加载」的
  行为锚定（防决策被无意反转）；实施后须在本机（HOME 实存技能）跑上游
  `test_adapter.py` + `test_agent_parity.py` 验证隔离机制生效（污染回归）。
- **文档义务**：`docs/*/guides/extensions/skills.md` 明写目录清单与「不受 Load project skills
  管控」；`docs/*/reference/agent-profile.md` 列两开关；hooks 信任模型两文档补披露。
- **回滚**：用户级＝两开关置 false；代码级＝单 commit revert（挂点、platform 字段、定制包
  互不纠缠，无数据迁移）。
