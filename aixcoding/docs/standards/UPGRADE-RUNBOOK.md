# 上游升级 Runbook（UPGRADE-RUNBOOK）

> 活文档：操作手册（DEVELOPMENT.md §8 六步的展开），随时按实战修订、不签认。
> 适用：fork 分支 `main_aixcoding_cli` 跟随上游（iCode/chrys）新版本。
> 升级节奏与债务控制条款见 DEVELOPMENT.md §8 正文。

## 0. 分支拓扑与铁律

```
上游仓库 ──同步──▶ origin/main_iCode（fork 内的纯上游镜像分支）
                        │
                        └──merge──▶ main_aixcoding_cli（定制分支，团队开发主线）
```

- **main_iCode 纯镜像纪律**：只允许 fast-forward 上游内容，**禁止任何定制提交**——
  R2/R3 门禁的 base 取 `git merge-base origin/main_iCode HEAD`，镜像一旦被污染即静默漏报累积上游改动；
- 升级 = merge 上游内容 into `main_aixcoding_cli`（目标取 **release tag 或镜像头** `origin/main_iCode`，
  由批次 design 记录裁决；分支已发布，不 rebase）；
- **git 写操作逐条授权**：建分支/merge/commit/push 等每条单独请示、执行后停等汇报（ADR-0012 与团队 git 纪律）；
- 当前基线记录于 `aixcoding/docs/CUSTOMIZATIONS.md` 人工区（"当前所基于的上游版本"）。

## 1. 升级前（准备）

1. 记录目标版本：上游 release tag / main 头 commit；
2. 同步镜像：上游 → 本地 `main_iCode`（fast-forward）→ push `origin/main_iCode`；
3. 确认工作树干净、定制全绿：
   ```bash
   uv run pytest aixcoding/tests -n0 -q -m "not integration and not gc_calibration"
   uv run python aixcoding/tools/check_docs.py
   ```
4. 读取定制清单 `aixcoding/docs/CUSTOMIZATIONS.md`——升级期间它是地图。

## 2. 文本层（merge 与冲突）

```bash
git merge <目标ref>   # release tag（如 v0.32.2）或镜像头 origin/main_iCode，以批次 design 记录为准
```

- 冲突点**逐个对照清单**定位定制点——以**文件路径 + 符号**为主键；`C` 编号是生成序号
  （`gen_customizations.py` 按 `(file, line)` 排序后 `enumerate`），随定制点增删/文件排序**整体漂移**，
  只作参考、**以当前 `CUSTOMIZATIONS.md` 为准**；不允许"整体接受一方"式解决；
- 已知冲突高发区（文件 + 符号主键）：
  | 定制点（文件 + 符号） | 冲突形态 |
  |---|---|
  | `AGENTS.md` 的 AIxCoding 入口段 | 上游重写 AGENTS.md 时入口段冲突——保留我们的段，合入上游正文 |
  | `src/chrys/app/tui/screens/logs/screen.py` 的 `MODULE_ORDER` 行 | 保留 `"aixcoding"` 项，合入上游新增模块项 |
- （历史注记：`tests/architecture/test_layering.py` 曾是高发区，其定制登记已随 ADR-0013 移除、
  现无定制登记残留，上游重构该文件时直接以上游为准。）
- 坑：git 冲突输出对中文文件名默认八进制转义，人工核对用 `git -c core.quotepath=off ...`；
- 坑：`except A, B:`（PEP 758，py3.14）是本仓 ruff format 强制输出，**不要**被编辑器/linter"修复"。

## 3. 结构层（anchor 核对）

清单 `anchor` 列逐项核对上游是否仍存在、签名/语义是否变化：

- 当前锚点速查（文件 + 符号主键，`C` 编号以当前清单为准）：`logs/screen.py` 的 `MODULE_ORDER`
  （日志面板 tab，diagnostics 批次）、`get_platform().config_dir`（`~/.chrys` 目录约定）、
  tui 基建符号（`BaseDialog`/`localized_binding`/`AppHeader`/`MainScreen.on_mount` 等，tui 批次登记）、
  `chrys.kernel/__init__` 包级导出（auth 批次）——完整清单以 `CUSTOMIZATIONS.md` anchor 列为准；
- **行为锚定测试是机检手段**：`uv run pytest aixcoding/tests/diagnostics/test_panel_anchor.py -n0 -q` 红 = 上游行为变化，定制需跟随；
- DAG 白名单制：上游新增/重命名**自己的**子包不影响定制；`test_layering.py` 的定制豁免登记已随
  ADR-0013 移除，上游重构其本体时直接以上游为准（现存 kernel-private allowlist 为上游自有机制）。

## 4. 语义层（全量验证）

```bash
# 以下为 bash（Git Bash）语法；Windows cmd 需改写变量赋值（如 set "BASE=..."）
# 上游侧全量：升级验证一律 --full（完整套件）；Smart Test（--smart）仅日常小改动使用，勿混
uv run python scripts/chrys_test.py --full
# 定制侧四门 + 测试
uv run pytest aixcoding/tests -n0 -q -m "not integration and not gc_calibration"
uv run python aixcoding/tools/check_docs.py
uv run python aixcoding/tools/check_import_boundaries.py
uv run python aixcoding/tools/gen_customizations.py && git diff --exit-code aixcoding/docs/CUSTOMIZATIONS.md
BASE=$(git merge-base origin/main_iCode HEAD)
uv run python aixcoding/tools/check_r2_diff.py --base "$BASE"
uv run python aixcoding/tools/check_r3_markers.py --base "$BASE"
# 类型（上游 gate 覆盖 src/chrys，含定制包）
uv run ty check --error-on-warning --python-platform linux src/chrys   # darwin/win32 同理
```

- `gen_customizations` 幂等失败是**期望信号**：清单需重生成并随升级 PR 提交；
- R2/R3 以**新 merge-base** 跑：升级 PR 中上游文件改动必须 ⊆ 已签认 R2 表并集（merge 引入的上游自身变化不算"我们的改动"——merge 后 diff 区间重新从新分叉点起算）；
- 关键链路人工验证（TUI 冒烟：`uv run icode`，F6 查看 aixcoding tab）。

## 5. 淘汰检查

对照清单 `removal_condition`（当前多为"待补"——**回填属独立事项**，2026-10-31 责任人裁决与升级批次
解耦、勿在升级中顺手回填；升级期间按本节"升级决策交付物"以人工对比分析执行）：命中条件的定制列为
**淘汰候选**，**禁止自行就地删除**——上游实现按上游一般需求做的，与我方按内部需求定制的实现
很可能不完全一样（功能名相似 ≠ 等价），必须逐点产出对比分析与处理意见、交责任人裁决，
获批后方可删除；删除后重跑 gen，清单自动收敛。

**升级决策交付物（每次升级必备，最终决策全部交责任人，留痕于批次目录 verification.md 与 PR 描述）**：

1. 冲突点全清单 + 逐点处理意见（含 auto-merge 通过但语义核对有疑义的点）；
2. 定制化改变清单：需新增 / 建议删除（淘汰候选，附上游实现 vs 我方定制需求的对比分析）/
   需适配的既有定制点；
3. 裁决记录（verification.md 追加，不删旧）。

（2026-10-31 责任人指示确立：淘汰与新增的最终决策必须交由人判断，不得 AI 自行处置。）

## 6. 收尾

1. 重生成并提交 `CUSTOMIZATIONS.md`（生成区）；
2. 人工区更新：`当前所基于的上游版本` → 新版本；`最近一次升级完成日期`；
3. 各定制点 `upstream_base`/`risk` 重评（§8 第 6 步）；
4. 版本号按 `aixcoding/docs/versioning.md`：上游三段 + fork 第四段，**基线升级重置第四位**——
   四段机制**启用前**（versioning.md 实施后置；2026-10-31 裁决与日构建递增机制一并独立设计），
   基线升级**只随上游同步三段**（version 行变化为上游自身变更，不算我方改动）；
   启用后改 `pyproject.toml` version 属 R2 项，随升级 PR 一并报批；
5. 升级报告 = PR 描述（§7 交付报告格式）：diff 区间、冲突处置逐点、anchor 核对结论、验证输出；
6. push 后两套 CI（上游 ci.yml + aixcoding-tests.yml）全绿方可合并。

## 7. 已知坑速查（实战沉淀）

| 坑 | 现象 | 处置 |
|---|---|---|
| `core.quotepath` | git 输出中文路径八进制转义+引号 | 工具已内置 `-c core.quotepath=off`；人工操作显式加同参 |
| 依赖漂移 | openai/mcp 等版本漂移致批量契约失败 | `uv sync --frozen`；禁 --extra all（新分支无此 extra） |
| CodeBuddy 全量测试 | shim 干扰/NUL 文件/GBK 解码 | 清 `PYTHONPATH`、`PYTHONUTF8=1`、大写盘符；本地 Python 已 3.14.8 对齐 `.python-version`，**勿设 `UV_PYTHON`**（强设会退回旧版，详见团队环境记录） |
| vendored ripgrep | fetch_rg 版本随上游升级 | `./scripts/fetch_rg.sh` 重取（Windows 用 .ps1） |
| PEP 758 | `except A, B:` 被误判语法错误 | py3.14+ 合法且 ruff format 强制输出，勿修 |
| CI 缓存 | 首跑慢 | setup-uv 缓存按 uv.lock 共享，后续秒级 |

## 8. 双轨期注意

本 runbook 只管新分支 `main_aixcoding_cli`。旧分支 `main_aixcoding_cli_0.28.0_final` 按冻结条款服役（阶段二 DoD 满足日起只修阻塞级 bug），**不随本 runbook 升级**；其功能按 ROADMAP 阶段三逐特性迁入新分支。
