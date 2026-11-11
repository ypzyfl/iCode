# 需求：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

> 活文档（R10，不签认）；需求事实以本文为准，方案与决策见同目录 `design.md`（已签认）。
> 2026-11-11 按 PR #107 合规处置终态回写。

## 背景

0.28 分支（`origin/main_aixcoding_cli_0.28.0_final`）的 SKILL 定制——自动加载
`~/.aixcoding/skills/` 与 `<cwd>/.aixcoding/skills/`（与 AIxCoding 桌面客户端共享的技能
目录）——未随 `chore/merge_upstream_v0.34.0` 迁入当前基线。同时桌面端早已扩展为七类
本地技能根，CLI 独立会话漏识别 5 类（`market-skills`、`team-skills/<team>`、
`.aixcoding_intellij` 镜像树）。

## 需求目标

1. 恢复并升级 aixcoding 技能目录自动加载：识别桌面端全部 **7 类根**，扫描次序与桌面端
   `runtime-composition.ts` 实测一致（工作区根优先于用户级根）。
2. 与 0.28 用户的 profile YAML 零迁移成本：开关进 `SkillsConfig`
   （`auto_load_aixcoding_user_skills` / `auto_load_aixcoding_cwd_skills`，默认 True）。
3. 上游测试机制性隔离：目录根挂 `PlatformInfo.aixcoding_dir`，随既有 config-dir 重定向
   机制一并 patch，HOME 实存技能不污染上游测试。
4. 上游接触面最小化：逻辑下沉定制包 `chrys.service.aixcoding.skill_paths`，上游仅 2 处
   挂点 + 1 个 platform 字段 + 2 个 schema 字段 + 2 行解析 + 2 行 conftest patch。

## 范围

- **改**：`src/chrys/service/skills/adapter.py`（挂点×2）、
  `src/chrys/foundation/platform/__init__.py`（字段）、
  `src/chrys/service/profiles/agents/{schema,loader}.py`（开关契约）、
  `tests/conftest.py`（重定向 patch×2）。
- **增**：`src/chrys/service/aixcoding/skill_paths.py`（定制包）、
  `aixcoding/tests/skills/test_aixcoding_skill_paths.py`（行为锚）。
- **不改**（2026-11-11 裁决，原清单 6-10 项撤销）：`docs/en`、`docs/zh-Hans` 用户手册与
  hooks 文档——与 `fork/user-manual` 批次并行改写冲突，手册缺口由该批次补齐。

## 验收条件

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

## 约束

- 配置契约一经发布即对外承诺：删除开关或改默认值须重新过 ADR 判定。
- 脚本执行安全底线不变：技能发现无门 ≠ 执行无审批，统一经 approval。
- 定制点登记 C158-C166 与代码 marker 一一对应，`--strict` 持续把关。
