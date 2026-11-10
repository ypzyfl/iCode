# 测试计划：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

> 活文档（R10，不签认）；实施中随验证结果更新。方案见同目录 `design.md`（v2.1，已签认），
> 决策见 `adr/0001-aixcoding-skill-dirs-trust-and-contract.md`。

## 测试策略

分四层，全部经 `aixcoding/tools/verify.py` 统一入口或显式 pytest 调用：

1. **定制单元测试**（新增，`aixcoding/tests/skills/test_aixcoding_skill_paths.py`；按 aixcoding/tests 主题目录惯例，无 `service/` 层级）：
   目录枚举、开关、次序、去重的全部领域行为，monkeypatch
   `chrys.service.aixcoding.skill_paths.user_aixcoding_dir` 隔离 HOME。
2. **机制回归测试**（新增，同文件）：`platform.aixcoding_dir` 重定向跟随、`replace` 保留字段
   行为的锚定（防 conftest patch 行丢失后无人察觉）。
3. **上游污染回归**（存量测试，本机实况 HOME 有 `~/.aixcoding/skills/hanhai-h5`）：
   实施后必跑，证明机制性隔离生效。
4. **冒烟**（真实进程）：技能目录出现在运行目录中、同名冲突 aixcoding 胜出。

## 覆盖矩阵（验收标准 → 用例）

| 验收标准（design） | 用例 | 层 | 形态 |
|---|---|---|---|
| 1. `~/.aixcoding` 全树默认扫描（v3） | `test_user_aixcoding_skills_loaded_by_default`（skills 根）+ `test_market_skills_root_loaded` + `test_intellij_mirror_tree_loaded`（镜像三根含 team 成员断言） | 1 | 成员断言 |
| 1a. 开关关则全树不扫 | `test_user_aixcoding_trees_skipped_when_toggle_off`（树内任一根均不出现） | 1 | 成员断言 |
| 1b. team 子目录枚举（v3） | `test_team_skill_dirs_enumerated`（两个 team 各自成根、排序）、`test_team_scan_skips_hidden_and_symlink_entries`、`test_team_container_missing_yields_no_roots` | 1 | 成员/排序断言 |
| 2. cwd 目录默认扫描且绑 runtime.cwd | `test_cwd_aixcoding_skills_loaded_with_runtime` | 1 | 成员断言 |
| 2a. **不受 `project_skills_enabled` 约束**（ADR 锚定） | `test_cwd_aixcoding_skills_load_despite_project_gate_off` | 1 | 成员断言 |
| 2b. 开关关 / 无 runtime 则不扫 | `test_cwd_aixcoding_skills_skipped_when_toggle_off` / `test_cwd_aixcoding_skills_skipped_without_runtime` | 1 | 成员断言 |
| 3. 次序对齐桌面端（v3）：chrys → aix cwd → aix 树 → agents user → agents cwd（D3） | `test_scan_order_matches_desktop`（路径索引次序断言；冲突胜负由先到先得机制保证，`loader.py:501` 实证） | 1 | 索引次序断言 |
| 4. YAML 两开关解析（默认 True） | `test_parse_skills_defaults_true` / `test_parse_skills_explicit_false` | 1 | `_parse_skills` 直调 |
| 5. 三条 build 路径一致 | 上游既有 agent_parity 机制共用 `_collect_skill_paths`，不新增重复测试；挂点单点即天然一致 | — | 结构性保证 |
| 6. 上游测试不受 HOME 污染 | `test_platform_redirect_covers_aixcoding_dir`（机制回归：字段跟随 pin、replace 保留未指定字段）+ 污染回归命令 | 2/3 | 精确断言全绿 |
| 7. CLI 独立会话识别桌面端技能（v3，验收 7） | 冒烟：桌面端任一根（本机 `hanhai-h5`）出现在 `_collect_skill_paths` 结果（冒烟已验证路径级） | 4 | 冒烟 |
| 挂点降级 | `test_hook_swallows_missing_customization`（monkeypatch import 失败 → 不抛、返回基础路径） | 1 | 异常路径 |
| 去重规范 | `test_paths_resolved_and_deduped`（profile path 与 aix cwd 根重叠时单条） | 1 | count 断言 |

## 异常与降级路径

| 场景 | 预期 | 用例/验证 |
|---|---|---|
| 定制包缺失/损坏（挂点 ImportError/AttributeError） | 吞错 + debug 日志，核心技能功能不受损 | 层 1 异常路径用例；冒烟时临时改名包目录验证（手动） |
| HOME 无 `~/.aixcoding` | 目录不报错、路径仍进列表（与上游 missing-root 行为一致） | 层 1 |
| cwd 目录不存在 | 同上 | 层 1 |
| conftest patch 行被上游变更吞掉 | 污染回归命令变红（本机） | 层 3 |
| TUI 面板保存（构造 `SC(...)` 不带新字段） | 开关回默认 True（0.28 已知行为，备案不改） | 人工核对一次，记 verification |

## 验证命令（实施阶段逐条执行并留档 verification.md）

```bash
# 定制套件
uv run pytest aixcoding/tests/skills -n0
# 污染回归（本机 HOME 实存 hanhai-h5，CI 无法复现）
uv run pytest tests/service/skills/test_adapter.py tests/orchestration/workflows/test_agent_parity.py -n0
# 统一入口（--paths = 本批全部改动文件，含删除/新增）
uv run python aixcoding/tools/verify.py --smart --paths <改动文件...>
# 门禁
uv run ruff check <改动文件...> && uv run ruff format --check <改动文件...>
uv run ty check --error-on-warning --python-platform win32 src/chrys   # 另 darwin/linux
uv run python aixcoding/tools/gen_customizations.py --strict
# 冒烟（真实 HOME/工作区）
uv run aixcoding-cli run "列出当前可用技能" -a Code
```

## 不测什么（边界）

- 不重复上游 `_collect_skill_paths` 既有 `.agents`/chrys 行为测试（属上游测试职责，未改动）；
- 不测桌面端真实共享（无桌面端环境；契约 = 字面 HOME 目录路径，由路径形态断言覆盖）；
- 不测 TUI 面板（面板未改，新开关不渲染）。
