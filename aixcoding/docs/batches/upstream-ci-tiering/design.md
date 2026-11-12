# 设计：PR 门禁按需触发分层（零上游改动跳过 Upstream CI）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：无特别意见

## 方案概述

将 PR 门禁重构为三层：**L0 基础合规层**（`govern`，恒跑，现状不动）、**L1 定制功能层**
（`test`/`guard`，恒跑；`govern` 扩展静态检查补位）、**L2 上游回归层**（桥接
`aixcoding-upstream-ci.yml`，由“是否触及上游影响面”按需触发），并配 nightly + 手动全量兜底：

```
PR to main_aixcoding_cli
        │
        ├─ AIxCoding Tests（恒跑）
        │    govern: ruff/format/docs/registry/R2R3 ＋【补位】定制产品 ruff/format/ty/compileall
        │    test（双 OS）/ guard（三 OS，不动）
        │    gate「AIxCoding quality gate」恒跑聚合
        │
        └─ AIxCoding Upstream CI
             filter: git diff --no-renames → ci_impact.py 分类 → upstream_touched
             ci: touched=true 才 workflow_call 上游 ci.yml 全套（约 20 job / 11 min）
             gate「AIxCoding upstream gate」恒跑：touched=false 直绿，否则须 ci=success

nightly（schedule，每日）/ workflow_dispatch：filter 直接 touched=true，全量主干合并树
```

**纯定制 PR 效果**：L2 整体跳过（gate 直绿，required check 语义不变），门禁等待约 12 min →
约 3–4 min；上游回归由 nightly 兜底（最迟约 24h 内再次执行全量验证）。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| A. 影响分类器 + L1 补位 + nightly/dispatch（本方案） | 判定即“影响上游功能”；静态门不失守；自动兜底有界 | 引入分类器维护义务；纯定制 PR 的上游回归从 PR 阻断降级为 nightly 发现 | 零上游接触（仅定制资产） | 选定（两轮外部评审 + 责任人 D1–D5） |
| B. workflow 级 paths-ignore | 配置最简 | required check 整体 skip，PR 永久卡 Expected（2026-10-28 评审已拦截） | 零 | 否决（既有先例） |
| C. fork 一份 ci.yml 做 shard 级按需 | 可细分 lint/shard | 双份维护必漂移（upstream-ci design 已否决）；workflow_call 只能整体调用 | 复制上游全套 workflow | 否决 |
| D. 仅镜像 is_custom() 做跳过（初稿） | 改动最小 | 所有权≠影响面：定制产品静态门连带走失、manual/README.pypi.md 构建角色被忽略 | 零 | 否决（外部评审阻塞项，已核实） |
| E. merge 后每次 push 全量兜底 | 主干有记录 | 大多数 PR 最终合并，抵消 runner 节省；不能阻止问题合并 | 零 | 否决（nightly+dispatch 替代） |

## 关键决策

### 决策 1：影响分类器 `needs_upstream_ci()`（独立语义，单实现）

新增 stdlib 分类器 `aixcoding/tools/ci_impact.py`：输入为 diff 文件清单文本，输出
`touched=true/false`；复用 `_common.py` 底层路径常量，但**终判语义独立**于 `is_custom()`。
规则按优先级（首条命中即定）：

| 优先级 | 类别 | 路径集 | 判定 |
|---|---|---|---|
| 1 | FORCE | `README.pypi.md`（wheel 元数据，D1=b1）；`.github/workflows/aixcoding-upstream-ci.yml`（桥接自身必须真实全量验证）；`aixcoding/tools/ci_impact.py` 与 `aixcoding/tools/_common.py`（判定器及其数据源，防“新判定器判自己无需验证”） | touched=true |
| 2 | DOC | `^docs/`（受信任文档区，现口径延续：实测 66 md + `index.yaml` 文档索引数据，无脚本/构建文件）；其余任意 `*.md` | 跳过候选 |
| 3 | CUSTOM | `^aixcoding/`（含 manual，D2=b2）；`^src/chrys/[^/]+/aixcoding/`；`.github/workflows/aixcoding-tests.yml`（精确登记，不收宽 `aixcoding-*.yml`） | 跳过候选 |
| 4 | 默认 | 其他一切（`src/chrys/` 其余、`tests/`、`scripts/`、`locales/`、`pyproject.toml`、`uv.lock`、`.python-version`、`hatch_build.py`、其他 workflow、未知新路径） | touched=true |

空清单 → 非零退出（fail-closed）；分类器自身异常 → 非零退出，filter 失败，gate 不得直绿。

**单实现保障（对评审“双轨”建议的改进）**：filter job 先 `command -v python3` 探测；不可用则
用仓库既有 pin 的 `actions/setup-python`（零新依赖，增约 10s）。**不设 shell 镜像轨道**——
双实现漂移风险（评审已举出 `aixcoding-*.yml` 漂移实例）从源头消除，一致性门禁亦随之不需要。
实施首步实测 `ubuntu-slim` 的 python3 并在 verification 留痕。

> 修订记录（2026-11-12 远程首跑实证，run #125）：`ubuntu-slim` 系统 python3 = 3.12 < 3.14
> （`_common.py` 含 PEP 758 语法），探测由存在性细化为“存在且 ≥3.14”版本门限；当前 runner
> 恒走 setup-python 兜底（约 +10s）。根因与修复详见 verification.md 对应节。

### 决策 2：filter 与 gate 的 fail-closed 强化

- diff 命令加 `--no-renames`：上游文件 rename 进定制目录时源路径删除参与判定，杜绝折叠误判。
- 分类器退出码经显式分支传递（0=touched=false 且仅当 stdout 明确输出、约定码=touched=true、
  其他=filter 失败），不复用 `if grep` 的退出码 1/2 混同陷阱（评审指出的现状 fail-open
  缺陷随 filter 重写一并消除）。
- gate 状态机：PR 下仅 `(touched=true ∧ ci=success)` 或 `(touched=false ∧ ci=skipped)` 合法；
  filter 失败/输出缺失/ci cancelled 均 fail。非 PR 事件恒走 touched=true 分支。

### 决策 3：L1 静态质量门补位（`aixcoding-tests.yml` 的 govern）

现状 `src/chrys/*/aixcoding/` 的 ruff/format/ty/compileall 全由上游套件承担（DIRECTORY §7），
L2 跳过后必须补位，否则纯定制产品 PR 失去全部静态检查：

| 检查 | 补位形态 | 说明 |
|---|---|---|
| ruff check / format --check | govern 增加定制产品路径（shell 收集存在的 `src/chrys/*/aixcoding/` 目录后传入） | 与上游 lint 同命令同配置（pyproject 单源）；成本秒级 |
| ty check --error-on-warning | 同上路径集，govern 单 Linux runner 上显式 `--python-platform` 三平台各跑一次（linux / darwin / win32） | 上游 AGENTS.md 惯例即“--python-platform linux 并重复 darwin/win32”；定制层**强平台敏感**（auth/crypto.py、auth/storage.py、guard 等含 DPAPI/win32/sys.platform 分支，windows-matrix 批次专为 DPAPI 真实用例扩双 OS 矩阵），单 Linux 默认平台会静默丢失 win32 类型视角（评审 F1 修正：推翻初稿“平台相关性弱”取舍）；三平台成本秒级 |
| compileall -q | 同上路径集，govern | 上游其首要目的为性能预热；补位仅承担语法门禁，秒级 |
| build / wheel | **不补位** | 由 FORCE（README.pypi.md）+ nightly 覆盖；manual 按 D2 由 nightly 覆盖 |

### 决策 4：兜底触发与可见性

- `on.schedule`：cron `0 18 * * *`（UTC，北京 02:00，每日）；`on.workflow_dispatch`：手动全量。
  仓库默认分支已 API 核实为 `main_aixcoding_cli` → schedule/dispatch 均合法可用，
  `github.sha` 即主干最新，ci.yml 的 `build_ref || github.sha` 语义天然正确，无需特殊 checkout。
- 非 PR 事件 filter 直接 touched=true，不读 `pull_request.base.sha`。
- concurrency group 沿用 `aixcoding-upstream-ci-${{ github.ref }}`：schedule 落主干 ref，与 PR
  的 merge ref 不互相取消。
- **可见性**：GitHub 失败通知（仓库订阅默认通道）+ 观察责任写入新 ADR（责任人合并前/每日查看
  nightly 结果）。自动开 Issue 等增强机制本批不做（留档可选增强）。

### 决策 5：manual 与 docs 区口径（D2 与评审细节 3 的落点）

- `aixcoding/manual/` 属 CUSTOM 跳过——**现状 doc-only 白名单已含 manual**（2026-11-11 扩围，
  评审 F3 补记），本批为延续跳过语义并补 nightly 兜底，非新增跳过；同步修订 user-manual 批次
  verification 的“等桥接自然覆盖”遗留口径为“等 nightly 兜底”，首次 nightly 实际覆盖后回填
  验证结果（验收标准已含）；修订时注明“原承诺经 upstream-ci-tiering 批次修订”，保持活文档
  决策链可读（评审 F7）。
- `docs/` 整目录维持受信任文档区现口径（含 index.yaml，oracle=跳过），本 design 显式留痕；
  测试矩阵收录 index.yaml 与假想非文档案例（若未来 docs/ 出现脚本/构建文件，须回炉修订本口径
  ——写入新 ADR 的维护义务）。

## 对上游隐式行为的假设

1. `ci.yml` 的 workflow_call 检出 `inputs.build_ref || github.sha` → bridge 不传 build_ref 时，
   PR 事件为合并 ref、schedule/dispatch 为主干最新，均为预期验证对象。假设失效表现：nightly 测错
   树 → verification 以 CI 日志的 checkout commit 核对。
2. required check 匹配 job 级 check run 名（`AIxCoding upstream gate`/`AIxCoding quality gate`）
   → 两个 gate 恒跑保名，任何跳过路径都产生 check run。假设失效表现：纯定制 PR 卡 Expected →
   端到端验收拦截。
3. GitHub schedule/workflow_dispatch 要求 workflow 在默认分支 → 已核实默认分支为
   `main_aixcoding_cli`；若未来默认分支变更，nightly/dispatch 静默失效 → 写入 ADR 维护义务。
4. 上游 ci.yml 的 lint/ty/compileall 命令与 pyproject ruff 配置 → L1 补位复用同一 pyproject
   单源，不复制配置；上游若改 lint 范围口径，定制补位不自动跟随（本批只覆盖定制路径，上游路径
   仍由上游套件负责）。

## 定制点登记预告

不适用：零上游接触（改动全部为定制资产，无 marker 注释新增/改动；`gen_customizations.py
--strict` 在实施与提交前照常跑零 error/warning 验证）。

## 改动文件清单（全部定制资产，零上游文件）

| 文件 | 改什么 | 预估行数 |
|---|---|---|
| `.github/workflows/aixcoding-upstream-ci.yml` | 触发扩展（schedule/dispatch）+ filter 重写（python 分类器、--no-renames、事件分支）+ gate 状态机 | ±60 |
| `.github/workflows/aixcoding-tests.yml` | govern 静态补位（ruff/format/ty/compileall 定制产品路径） | +30 |
| `aixcoding/tools/ci_impact.py` | 新增 stdlib 分类器（复用 _common 常量） | 约 90（新增） |
| `aixcoding/tests/` 下新增分类器测试 | 决策 1 规则全案例矩阵 + fail-closed 案例（目录对齐现有惯例） | 约 150（新增） |
| `aixcoding/docs/standards/adr/upstream-ci-tiering--pr-gate-tiering.md` | 新 ADR（语义 ID，ADR-0024 决策 5 命名规范）：分层模型、FORCE/CUSTOM 维护义务、nightly 观察责任；显式修订 ADR-0004 与 DIRECTORY §7 原覆盖关系 | 约 80（新增） |
| `aixcoding/docs/standards/DIRECTORY.md` | §7 门禁表改写为分层口径；§1 workflow 行补 schedule/dispatch 说明 | 约 10 |
| `aixcoding/docs/standards/adr/0004-定制质量门用独立workflow.md` | 追加注记（append-only，2026-11-01 平台矩阵演进注记先例，评审 F6）：产品定制代码静态门归属改由本批分层模型承载，指向新 ADR | 约 8 |
| `aixcoding/docs/batches/upstream-ci/design.md`、`verification.md` | 交叉引用本批与 ADR-upstream-ci-tiering--pr-gate-tiering（doc-only 判定被本批取代的修订节） | 约 15 |
| `aixcoding/docs/batches/ci-gate/design.md` | 交叉引用（govern 静态补位归属说明） | 约 5 |
| `aixcoding/docs/batches/user-manual/verification.md` | “等桥接自然覆盖”→“等 nightly 兜底”口径修订，注明“原承诺经 upstream-ci-tiering 批次修订”（评审 F7） | 约 5 |

R1/R2 自查：零上游文件改动，无 R2 报批项；两个 workflow 均在 CUSTOM_EXACT_PATHS 登记内，
新增代码全部落 `aixcoding/` 开发资产区；无新增第三方依赖（R11 不适用）。

## 风险与最坏情况

- **分类器漏判**：定制层破坏上游套件，发现延迟至 nightly（执行上界约 24h，发现依赖观察责任）。
  缓解：FORCE 清单 + 默认全量 + 测试矩阵；回滚=filter 改回恒 touched=true（单行级改动）或
  git revert 本批。
- **nightly 失败无人看**：等同无兜底。缓解：ADR 明载观察责任；本批验收含可见性机制实测。
- **门禁语义漂移**：gate 名不变、恒跑不变，分支保护零改动；本批 PR 自身触及桥接 workflow →
  FORCE 命中，恰好以真实全量验证“强制全量清单”生效。

## 验收时点说明（评审 F4）

本批实施 PR 自身触及桥接 workflow → FORCE 命中 → touched=true 全量，**恰好无法自证
touched=false 真实链路**（filter 判定 → ci skip → gate 直绿 → required check 通过可合并）。
该链路的端到端验证安排在**本批合并后**：开一个仅含 doc + 定制文件混合改动的临时验证 PR，
观察三件套后关闭（不触发上游矩阵，恰为被测行为本身）；若届时有真实纯定制批次 PR（如手册
跟进批次）可替代临时 PR。本批 verification 先记录 CI 日志级证据（filter 输出、job 条件、
gate 状态机、nightly/dispatch 触发），跳过链路的真实 PR 证据按上述时点补录。详细矩阵与步骤
在 test-plan.md。

## ADR 判定

需要新 ADR（**ADR-upstream-ci-tiering--pr-gate-tiering：PR 门禁按需触发分层**，按 ADR-0024
决策 5 的批次命名空间语义 ID 规范，不再分配数字编号）：本批永久改变“哪些 PR 可不经上游全量回归合并”
的门禁政策、定制产品代码的质量门归属、合并后风险发现机制，并给后续所有批次新增路径分类维护
义务——超出批次执行层选型，且显式修订 ADR-0004 与 DIRECTORY §7 的既有覆盖关系。
