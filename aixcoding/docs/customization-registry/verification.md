# 验证记录：定制点登记机制改造（customization-registry）

> 追加不删旧；本地验证证据落盘于此，CI 证据归属 PR checks 本身（§7）。

## 2026-10-31 实施（C+ 终局形态：点级登记 + id 降级保留 + 产物退役 + 对账命令化）

### 实施清单

| 域 | 改动 |
|---|---|
| `aixcoding/tools/gen_customizations.py` | 全面改造：check（默认，零写入）/ `--strict`（孤儿升级 error）/ `--report`（stdout 全景）；点级匹配（落点+marker 锚前缀、同文件最长锚优先、孪生组预期计数、区间 id 展开与计数一致性、tombstone 高水位唯一性）；考古模式不动；落盘渲染全删 |
| `aixcoding/tools/_common.py` | `MARKER_EXEMPTIONS` 迁入（R3 与 report 共用单一来源）；`parse_table_section` 加代码围栏感知（**实施期实战修复**：design 契约示例（```markdown 围栏内）曾整表混入对账——12 个 error 实证，围栏内节/表不再解析，fail-closed） |
| `aixcoding/tools/check_r3_markers.py` | 豁免源切换 `_common.MARKER_EXEMPTIONS`（原从 `CUSTOMIZATIONS.md` 读回的间接环消除） |
| 8 个 design 登记表 | 点级化重写（19+2+1+1+1+1=25 行覆盖 29 点；孪生组区间行 C009–C012×4 / C014–C015×2）；tier-migration/ai-gates 登记表清空为迁移声明（双源消解）；auth stamp() 孤儿行删除（**auth-stamp 待办核销**）；removal_condition 29 点全回填（8 类判据） |
| `CUSTOMIZATIONS.md` | **删除**（产物退役）；人工区基线信息迁 `UPGRADE-RUNBOOK.md` 头部「当前基线」节 |
| 规范联动 | DEVELOPMENT.md §5 重写（登记机制）/§8 基线信息指向；UPGRADE-RUNBOOK §0/§1/§2/§3/§4/§5/§6 新口径 + §5 附录（8 类淘汰判据）；`templates/design.md` 登记节新格式（含退役记录）；`AGENTS.md` AIxCoding 段补 report/strict 命令入口（C001 段内，marker 行未动）；ROADMAP 义务①销项 + 部分 DoD 对账口径 |
| `.github/workflows/aixcoding-tests.yml` | freshness 步骤（gen + git diff）替换为 `gen_customizations.py --strict` 单步 |
| `aixcoding/tests/tools/` | test_gen_customizations 重写（25 用例：错误注入矩阵/防漂移回归 A、B/围栏 fail-closed/零写入/区间组）；test_check_r3_markers 豁免源适配 |

### 验证矩阵

| 项 | 命令 | 结果 |
|---|---|---|
| strict 对账（真仓库） | `gen_customizations.py --strict` | **check OK — 25 行 / 29 marker / 6 design / 0 retired / 0 warning**（迁移一次通过；孤儿清零） |
| 工具测试 | `pytest aixcoding/tests/tools -n0 -q` | **72 passed**（含注入矩阵 + 防漂移 + 围栏 + 零写入 + 区间） |
| 定制全套 | `pytest aixcoding/tests -n0 -q -m "not integration and not gc_calibration"` | **313 passed, 2 skipped** |
| check_docs | 含新 ADR-0015（草案） | 15 ADR / 16 design / 13 self-review，OK |
| check_import_boundaries | — | OK（1127 files） |
| ruff 双门禁 | `ruff check` + `format --check`（aixcoding/tools + aixcoding/tests 全目录） | All checks passed / 40 files already formatted |
| Smart Test | `chrys_test.py --smart --paths`（本批 8 个触改文件，含删除的 CUSTOMIZATIONS.md） | **198 passed, 2 skipped — Summary: PASSED (exit 0)**（architecture 域 watch 命中 workflow 改动） |
| report 全景 | `--report` | 25 行/29 点全渲染、孪生区间行、孤儿 0、豁免表来自 _common——首次时点快照附本文件末尾 |

### 待责任人动作

1. **R10 重签 8 个 design**（登记表改动，可一次审阅批量签）：tui / auth / diagnostics / auth-logging / agents-md-note / ruff-test-exemptions / tier-migration / ai-gates；
2. **ADR-0015 签认**（草案）；
3. PR 流程（push 特性分支 → 网页建 PR → 双 CI）。

> 2026-10-31 状态更新：①②已完成（8 design、ADR-0015、self-review.md 均当日签认，
> design 另因一轮评审 F1 修正 R2 节口径重签一次）；③进行中——评审链闭环后本地
> add/commit 完成（a0bfac89），push 待授权。

### 连带核销确认

- auth-stamp-registration-cleanup（temp 待办）：孤儿登记清零，核销；
- stable-customization-id（temp 待办）：本批次实现（id 降级保留 + tombstone 高水位），核销；
- removal-condition-backfill（temp 待办）：29 点全回填 + 8 类判据进 runbook §5 附录，核销；
- ROADMAP 补做义务①：销项标记已落。

### 环境

Windows 11 / CodeBuddy；配方：清 `PYTHONPATH` + `PYTHONUTF8=1` + 大写盘符。

## 2026-10-31 二轮评审（Kimi-K3.1-Pro）处置与复验

- 二轮独立评审发现 **1 blocker + 3 suggestion + 1 nit**，责任人拍板全修：
  - F1（blocker，退役表被活动登记解析吸收、strict 必红）→ 已修：gen 侧新增
    `_registration_section`（节文本截取，围栏感知）+ `_active_part`（活动表止于首个
    `### ` 子节），退役解析限定节内；开发 AI 已先行独立复现（strict exit=1 两条伪
    '预期计数' error）确认评审属实；补 `test_retired_strict_coexists`（合法退役 strict==0）；
  - F2（畸形退役 id 静默丢弃/退役解析越节）→ 已修：非空不可解析退役 id 记 note、
    空 id 行记 note（fail-closed 可查）；越界随节限定修复；补反向区间/节外诱饵小节两用例；
  - F3（DEVELOPMENT 残留旧字段表 reason/tests/upstream_base/paths；runbook 逐点
    upstream_base 义务）→ 已修：§5 字段表替换为新契约七字段 + 基线全局承载注记；
    runbook §6 第 3 条改 anchor/risk 重评口径；
  - F4（test-plan 承诺未落实：design 不可读/CLI 退出码/孪生多出方向）→ 已修：
    `load_registrations` 包 OSError→note + `test_design_unreadable_fails_closed`；
    `test_main_exit_codes`（0/2 + strict 1 经 REPO_ROOT monkeypatch）；`test_twin_count_overflow_direction_errors`；
  - F5（验证口径漂移）→ 本节即追加记录（旧 72 passed 为修复 F2 前数字，现 79）；
    test-plan 改"25 登记行覆盖 29 点"；下方快照节措辞改"摘要"。
- 修复后复验（2026-10-31）：工具测试 **79 passed**（+6 评审回归用例）；strict 对账 OK
  （25 行/29 marker/0 警告）；ruff 双检全过；check_docs OK。
- 一轮评审（Deepseek-V4-Pro）小结：无 blocker、2 suggestion + 3 nit 全修、增量复审收敛
  （明细见 self-review.md）。
- 一轮评审（Deepseek-V4-Pro）后的 5 项修复与本轮 5 项修复的增量复审记录见 self-review.md。
- 三轮微调（Kimi 增量复审 findings F2-T/F4-T/F5-D）：诱饵测试补 `0 retired id(s)` 断言、
  main 层补 exit 1 失败夹具（均为既有用例内断言增强，用例数不变）、verification 数字/
  重复标题订正；复验 79 passed + strict OK。

## 附：首次 report 时点快照（2026-10-31，迁移落盘当日；**摘要**——全表逐行以当日 report 实时输出与 PR diff 为准）

> 生成命令 `uv run python aixcoding/tools/gen_customizations.py --report`；此后以实时输出为准。

- 25 行 / 29 定制点（C001–C029 全量，id 冻结取现值）；孪生组 2 组：`main/commands.py` `AIxCoding tui: /login /logout` ×4（行 478/520/559/912）、`main/screen.py` 同锚 ×2（行 798/838）；
- 孤儿登记 0；豁免 4 项（trajectory manifest / pot / po / mo，源 `_common.MARKER_EXEMPTIONS`）；
- removal_condition 8 类判据分布：上游等价 15、随组 5、机制退役 2、政策变更 1、消费者退役 1、目录退役 1、常驻 1、随点迁移语义并入各引用行 3（C006/C016/C017/C019/C020/C022 随主点）；
- 全表逐行文本见当日 report 输出（正文表格从略，git 留痕于本批次 PR）。
