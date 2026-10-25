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
- 升级 = merge `origin/main_iCode` into `main_aixcoding_cli`（分支已发布，不 rebase）；
- 当前基线记录于 `aixcoding/docs/CUSTOMIZATIONS.md` 人工区（"当前所基于的上游版本"）。

## 1. 升级前（准备）

1. 记录目标版本：上游 release tag / main 头 commit；
2. 同步镜像：上游 → 本地 `main_iCode`（fast-forward）→ push `origin/main_iCode`；
3. 确认工作树干净、定制全绿：
   ```bash
   uv run pytest aixcoding/tests -n0 -q
   uv run python aixcoding/tools/check_docs.py
   ```
4. 读取定制清单 `aixcoding/docs/CUSTOMIZATIONS.md`——升级期间它是地图。

## 2. 文本层（merge 与冲突）

```bash
git merge origin/main_iCode
```

- 冲突点**逐个对照清单 C 编号**（paths 列指向标记位置），不允许"整体接受一方"式解决；
- 已知冲突高发区（均为清单在册定制点）：
  | 定制点 | 文件 | 冲突形态 |
  |---|---|---|
  | C001 | `AGENTS.md` | 上游重写 AGENTS.md 时入口段冲突——保留我们的段，合入上游正文 |
  | C002 | `src/chrys/app/tui/screens/logs/screen.py` | MODULE_ORDER 行——保留 `"aixcoding"` 项，合入上游新增模块项 |
  | C003–C005 | `tests/architecture/test_layering.py` | 上游重构架构测试时登记区冲突——保留 tier 注册与 `_DAG_EDGE_ALLOWLIST`，合入上游规则变化 |
- 坑：git 冲突输出对中文文件名默认八进制转义，人工核对用 `git -c core.quotepath=off ...`；
- 坑：`except A, B:`（PEP 758，py3.14）是本仓 ruff format 强制输出，**不要**被编辑器/linter"修复"。

## 3. 结构层（anchor 核对）

清单 `anchor` 列逐项核对上游是否仍存在、签名/语义是否变化：

- 当前锚点速查：`MODULE_ORDER`/`MODULE_WHITELIST`/`_TuiLogHandler`（C002）、`TIER_ORDER` 注册制与 DAG 采集器（C003–C005）、`chrys.app.cli.app:main` 入口签名（launcher，登记预告在 diagnostics design）、`get_platform().config_dir`；
- **行为锚定测试是机检手段**：`uv run pytest aixcoding/tests/diagnostics/test_panel_anchor.py -n0 -q` 红 = 上游行为变化，定制需跟随；
- DAG 白名单制：上游新增/重命名**自己的**子包不影响定制；上游若重构 `test_layering.py` 本体，登记区人工合并后 stale 检测会自动核对豁免边仍有真实 import。

## 4. 语义层（全量验证）

```bash
# 上游侧全量（Smart Test 按 AGENTS.md；--full 完整套件）
uv run python scripts/chrys_test.py --full
# 定制侧四门 + 测试
uv run pytest aixcoding/tests -n0 -q
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

对照清单 `removal_condition`（当前多为"待补"——**首次升级时应回填**该列）：上游已提供等价能力的定制就地删除，不保留死补丁；删除后重跑 gen，清单自动收敛。

## 6. 收尾

1. 重生成并提交 `CUSTOMIZATIONS.md`（生成区）；
2. 人工区更新：`当前所基于的上游版本` → 新版本；`最近一次升级完成日期`；
3. 各定制点 `upstream_base`/`risk` 重评（§8 第 6 步）；
4. 版本号按 `aixcoding/docs/versioning.md`：上游三段 + fork 第四段，**基线升级重置第四位**（如 0.31.0.x → 0.32.0.1）；改 `pyproject.toml` version 属 R2 项，随升级 PR 一并报批；
5. 升级报告 = PR 描述（§7 交付报告格式）：diff 区间、冲突处置逐点、anchor 核对结论、验证输出；
6. push 后两套 CI（上游 ci.yml + aixcoding-tests.yml）全绿方可合并。

## 7. 已知坑速查（实战沉淀）

| 坑 | 现象 | 处置 |
|---|---|---|
| `core.quotepath` | git 输出中文路径八进制转义+引号 | 工具已内置 `-c core.quotepath=off`；人工操作显式加同参 |
| 依赖漂移 | openai/mcp 等版本漂移致批量契约失败 | `uv sync --frozen`；禁 --extra all（新分支无此 extra） |
| CodeBuddy 全量测试 | shim 干扰/NUL 文件/GBK 解码 | 清 `PYTHONPATH`、`PYTHONUTF8=1`、大写盘符、`UV_PYTHON=3.14.3`（详见团队环境记录） |
| vendored ripgrep | fetch_rg 版本随上游升级 | `./scripts/fetch_rg.sh` 重取（Windows 用 .ps1） |
| PEP 758 | `except A, B:` 被误判语法错误 | py3.14+ 合法且 ruff format 强制输出，勿修 |
| CI 缓存 | 首跑慢 | setup-uv 缓存按 uv.lock 共享，后续秒级 |

## 8. 双轨期注意

本 runbook 只管新分支 `main_aixcoding_cli`。旧分支 `main_aixcoding_cli_0.28.0_final` 按冻结条款服役（阶段二 DoD 满足日起只修阻塞级 bug），**不随本 runbook 升级**；其功能按 ROADMAP 阶段三逐特性迁入新分支。
