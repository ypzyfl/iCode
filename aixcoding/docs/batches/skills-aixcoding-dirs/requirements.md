# 需求：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

> 活文档（R10，不签认）；需求事实以本文为准，方案与决策见同目录 `design.md`（v5，已确认 2026-11-23）。
> 2026-11-11 按 PR #107 合规处置终态回写。

## 背景

0.28 分支（`origin/main_aixcoding_cli_0.28.0_final`）的 SKILL 定制——自动加载
`~/.aixcoding/skills/` 与 `<cwd>/.aixcoding/skills/`（与 AIxCoding 桌面客户端共享的技能
目录）——未随 `chore/merge_upstream_v0.34.0` 迁入当前基线。同时桌面端早已扩展为七类
本地技能根，CLI 独立会话漏识别 5 类（`market-skills`、`team-skills/<team>`、
`.aixcoding_intellij` 镜像树）。

**2026-11-18 需求变更**：桌面端「已安装技能」存储
（`<appData>/AIxCoding/<环境>/users/<用户>/private/skills/system/`）同样纳入共享范围，
口径与插件端 `aixcoding-continue@75407294`（插件/CLI/桌面端三端个人 skill 互通）一致。
原「不扫描该存储、只走桌面端 profile 注入」的结论仅对桌面端拉起的会话成立，
CLI 独立会话（用户直接运行 `aixcoding-cli`）看不到这些技能——本次补齐该缺口。

## 需求目标

1. 恢复并升级 aixcoding 技能目录自动加载：识别桌面端全部 **7 类本地根**，扫描次序与桌面端
   `runtime-composition.ts` 实测一致（工作区根优先于用户级根）。
2. 与 0.28 用户的 profile YAML 零迁移成本：开关进 `SkillsConfig`
   （`auto_load_aixcoding_user_skills` / `auto_load_aixcoding_cwd_skills`，默认 True）。
3. 上游测试机制性隔离：目录根挂 `PlatformInfo.aixcoding_dir`（v4 增 `app_data_dir`），随既有
   config-dir 重定向机制一并 patch，HOME 与应用数据目录的实存技能都不污染上游测试。
4. 上游接触面最小化：逻辑下沉定制包 `chrys.service.aixcoding.skill_paths`，上游仅 2 处
   挂点 + 2 个 platform 字段（v4 后）+ 2 个 schema 字段 + 2 行解析 + 2 行 conftest patch。
5. （2026-11-18 增）桌面端已安装技能存储
   `<appData>/AIxCoding/<环境>/users/<用户>/private/skills/system/` 纳入自动加载，
   与插件端 `75407294` 同构：全部环境 × 全部账号、只认 `SKILL.md` 所在目录、只读。

## 范围

- **改**：`src/chrys/service/skills/adapter.py`（挂点×2）、
  `src/chrys/foundation/platform/__init__.py`（`aixcoding_dir` + 2026-11-18 增
  `app_data_dir` 字段）、`src/chrys/service/profiles/agents/{schema,loader}.py`（开关契约）、
  `tests/conftest.py`（重定向 patch×2 处，2026-11-18 起各多覆盖 `app_data_dir`）。
- **增**：`src/chrys/service/aixcoding/skill_paths.py`（定制包；2026-11-18 起扩
  `desktop_installed_skill_paths`）、`aixcoding/tests/skills/test_aixcoding_skill_paths.py`
  （行为锚）。
- **不改**（2026-11-11 裁决，原清单 6-9 与 11 项撤销；#10 已于 2026-11-10 自然取消）：
  `docs/en`、`docs/zh-Hans` 用户手册与
  hooks 文档——与 `fork/user-manual` 批次并行改写冲突，手册缺口由该批次补齐。
  2026-11-18 变更不扩大该清单：桌面端安装存储的说明只进本批次内部文档
  （`skill-directories.md`），不改上游 `docs/`。

## 验收条件

> 编号以 `design.md` 为准（design 另有「三条 build 路径一致」与「CLI 独立会话识别」两条）；
> 本文第 7–9 项对应 design 验收条件 8–9。

1. 七类根按桌面端次序进入技能发现列表；team 子目录逐个枚举，跳过隐藏目录。
2. 两个开关分别关断对应树（user 开关管两棵 HOME 树，cwd 开关管工作区根），关断后
   `.aixcoding` 路径不出现在列表。
3. 工作区根 `.aixcoding/skills` 不受 `project.skills_enabled` 信任门管控（上游测试
   `test_cwd_aixcoding_skills_load_despite_project_gate_off` 行为锚定，防无意反转）。
4. 与 `.agents` 的同名技能冲突胜负由挂点次序决定（aixcoding 先于 agents user 级）。
5. HOME 实存技能（本机 `hanhai-h5`）不污染上游 `test_adapter.py` /
   `test_agent_parity.py`（重定向隔离生效）。
6. 门禁全绿：ruff（check + format）`aixcoding/`、`check_docs.py --closure`、
   `gen_customizations.py --strict`、R2/R3 门禁、`pytest aixcoding/tests`。
7. （2026-11-18 增）桌面端安装存储按「全部环境 × 全部账号」枚举，只认
   `private/skills/system` 下的技能目录；隐藏目录与符号链接跳过、按名排序、
   目录缺失不报错、不阻塞会话。
8. （2026-11-18 增）该根由 `auto_load_aixcoding_user_skills` 统一管控，扫描位置在
   `~/.aixcoding_intellij` 树之后、`~/.agents/skills` 之前；关断开关后整组不出现。
9. （2026-11-18 增）**安装 ≠ 启用**：桌面端禁用（`enabled: false`）的技能在 CLI 独立会话
   中同样可发现（责任人 2026-11-18 裁决）；不解析桌面端 `skill.json` /
   `active-candidates.json` 等内部状态文件。

## 约束

- 配置契约一经发布即对外承诺：删除开关或改默认值须重新过 ADR 判定。
- 脚本执行安全底线不变：技能发现无门 ≠ 执行无审批，统一经 approval。
- 定制点登记 C158-C166 与代码 marker 一一对应，`--strict` 持续把关。
- 桌面端布局（`<appData>/AIxCoding/<环境>/users/<key>/private/skills/system`）是跨端契约，
  由定制测试的行为锚暴露变更；本批次不引入对桌面端内部状态文件的解析依赖。
