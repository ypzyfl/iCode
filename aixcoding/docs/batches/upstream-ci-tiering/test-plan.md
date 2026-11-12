# 测试方案：PR 门禁按需触发分层

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

三层验证：

1. **单元**：分类器 `aixcoding/tools/ci_impact.py` 为纯函数（路径清单文本 → touched 判定），
   测试落点 `aixcoding/tests/tools/test_ci_impact.py`，直接覆盖同一实现（单实现，无镜像轨道）。
   零上游 anchor 涉及（本批零上游接触），无需行为锚定测试。
2. **CI 日志级**：本批实施 PR 自身 FORCE 命中（触及桥接 workflow）→ 真实全量路径自证；
   `govern` 日志核对 L1 静态补位实际执行（ruff/format/ty 三平台/compileall）。
3. **真实 PR 端到端**：touched=false 链路在本批合并后以临时验证 PR 执行（design 验收时点
   说明，F4）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口 | 类型 |
|---|---|---|
| 纯定制 PR 跳过 + gate 直绿 | 合并后临时验证 PR（doc+定制混合，观察 filter 输出/ci skipped/gate 直绿后关闭） | 端到端（合并后时点） |
| 上游文件触及全量（src 其余/tests/scripts/环境文件/其他 workflow/README.pypi.md） | `test_ci_impact.py` 逐类案例；本批 PR 自身 FORCE 全量自证 | 单元 + 端到端（本批 PR） |
| rename 上游→定制目录不误判 | 单元：清单含上游源路径删除 + 定制目标新增；workflow 层 `--no-renames` 由本地 git 模拟 diff 复核输出形态 | 单元 + 手工 |
| fail-closed（空 diff/分类器异常/输出缺失/gate 状态机） | 单元：空清单、异常输入；gate 状态机由 CI 日志与本批 PR 观察 | 单元 + CI 日志 |
| L1 静态补位实际执行 | 本批 PR 的 govern 日志（ruff/format 定制路径、ty 三平台、compileall） | CI 日志 |
| nightly 计划执行 + dispatch 手动 + 失败可见性 | 合并后 dispatch 立即手动触发一次全量；schedule 首个到点观察；失败通知通道实测（design 决策 4） | 手工（合并后时点） |
| 分类器测试矩阵全绿 | `uv run pytest aixcoding/tests/tools/test_ci_impact.py` | 单元 |
| manual-only 跳过后首次 nightly 覆盖回填 user-manual | 首个 nightly 的 build/wheel 日志 → user-manual verification 回填 | 手工（挂账） |
| 文档联动（ADR/DIRECTORY/三批次） | `check_docs.py --closure` + `gen_customizations.py --strict` | 门禁 |
| 真实纯定制 PR 端到端（复刻 PR #114 形态） | 同第 1 行临时验证 PR | 端到端（合并后时点） |

### 分类器单元测试矩阵（决策 1 规则全覆盖）

| 案例 | 输入清单特征 | 预期 |
|---|---|---|
| 纯定制根目录 | `aixcoding/tests/catalog/test_x.py` | false |
| 定制产品代码 | `src/chrys/service/aixcoding/config/loader.py` | false |
| 定制产品代码（各 tier） | kernel/service/orchestration/app 各一例 | false |
| 手册（D2） | `aixcoding/manual/zh-Hans/x.md`、`aixcoding/manual/index.yaml` | false |
| 纯文档 | `README.md`、`docs/en/start/what-is-icode.md`、`aixcoding/docs/batches/x/design.md` | false |
| docs 区索引数据（受信任文档区口径） | `docs/index.yaml` | false |
| 定制 workflow 精确登记 | `.github/workflows/aixcoding-tests.yml` | false |
| FORCE：README.pypi.md | 单独 / 与定制文件混合 | true |
| FORCE：桥接自身 | `.github/workflows/aixcoding-upstream-ci.yml` | true |
| FORCE：分类器与数据源 | `aixcoding/tools/ci_impact.py`、`aixcoding/tools/_common.py`（单独/混合） | true |
| 新增未登记 aixcoding workflow | `.github/workflows/aixcoding-new.yml` | true（不收宽） |
| 上游 workflow | `.github/workflows/ci.yml`、`cd.yml` 等 | true |
| 上游代码/测试/脚本 | `src/chrys/app/app.py`、`tests/app/test_app.py`、`scripts/chrys_test.py` | true |
| 环境/构建文件 | `pyproject.toml`、`uv.lock`、`.python-version`、`hatch_build.py` | true |
| 其他上游目录 | `locales/chrys.pot` | true |
| docs 区假想非文档（有意口径，见 oracle 注） | `docs/build.py` | false（受信任文档区整目录豁免的有意后果，非疏漏） |
| rename 形态 | 上游源路径 `src/chrys/x/old.py`（删除）+ 定制目标 `src/chrys/x/aixcoding/old.py` | true（源路径参与） |
| 混合 PR（PR #114 形态复刻） | 定制代码 + 定制测试 + 批次文档 | false |
| 空清单 | 空 | 非零退出（fail-closed） |
| 非法/空白行 | 空行、空白、反斜杠路径 | 归一化或报错，不得静默放行 |

> oracle 注（决策 5）：`^docs/` 整目录为受信任文档区，故 `docs/build.py` 假想例按现口径
> 预期 false 并在测试中显式标注该取舍；若未来 docs/ 真实出现脚本/构建文件，须回炉修订口径
> （新 ADR 维护义务）。此行为在测试中以注释显式标记为“有意口径”，非疏漏。

## 异常与降级路径

- 分类器自身异常/输入文件不可读 → 非零退出，filter 失败，gate 不得直绿。
- 分类器退出码约定：0=touched=false（stdout 须精确输出 `upstream_touched=false`）；
  约定码 10=touched=true（stdout 精确输出 `upstream_touched=true`）；其余=错误。
  shell 显式捕获并逐分支校验 stdout 字样，任何不匹配即 fail（决策 2）。
- runner python3 缺失或版本 <3.14 → setup-python 兜底分支（决策 1；2026-11-12 远程首跑实证
  当前 ubuntu-slim 系统 python3=3.12，恒走兜底，详见 verification.md）。
- 非 PR 事件（schedule/dispatch）→ 不执行 diff，直接 touched=true。

## 手工验证步骤

1. 本地模拟：`git -c core.quotePath=off diff --name-only --no-renames <base> HEAD` 输出喂分类器
   CLI，逐类路径复核判定（含一次真实 rename 场景的 diff 输出形态核对）。
2. 本批 PR：观察 filter 日志（FORCE 命中、python3 探测结果）、ci 全量、gate 成功；govern
   日志核对 L1 补位四检查。
3. 合并后：dispatch 手动全量一次；临时验证 PR 观察 touched=false 三件套；首个 nightly 到点
   观察并回填 user-manual。结果记入 verification.md。
