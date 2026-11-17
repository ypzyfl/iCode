# 测试方案：检查域模型与定制域按需触发

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

三层验证：

1. **单元**：`aixcoding/tests/tools/test_ci_impact.py` 扩展——规则表 R1-R12 全案例矩阵、并集
   语义、`--domains` CLI 输出格式、既有 38 例 upstream 判定零回归；**F6 AST 双形态扫描测试**
   （必须项）：遍历 `aixcoding/tests` 源码 AST，提取 `_read("...")` Call 实参与
   `REPO_ROOT / "a" / "b"` 拼接链字符串常量，重组仓库相对路径，断言每个都被分类器判为
   aixcoding-tests 命中（新增静态契约测试时自动防漏登记）。
2. **CI 日志级**：本批 PR 自身触及 `aixcoding-tests.yml` 与 `ci_impact.py`（R1 FORCE）→
   定制双域全跑自证；filter 日志记录 probe 与事件分支行为。
3. **真实 PR 端到端**：touched=false 链路在本批合并后验证——合并后的纯文档回填 PR（同
   upstream-ci-tiering 的 PR #122 先例），观察 filter 双输出 false → test/guard skipped →
   gate 直绿三件套。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口 | 类型 |
|---|---|---|
| 纯文档 PR 双域跳过 + gate 直绿 + 各域状态输出 | 合并后纯文档回填 PR（真实端到端） | 端到端（合并后时点） |
| 射程矩阵逐格行为 + 多域命中 | `test_ci_impact.py` R1-R12 全案例（每规则正例 + 跨规则并集） | 单元 |
| "文档即验证输入"9 文件触发正确 | 单元精确案例（R7 双域、R11 的 8 文件）+ F6 扫描自动守护 | 单元 |
| FORCE（workflow/分类器/_common）双域全跑 | 单元 R1 案例；本批 PR 自证 | 单元 + 端到端（本批 PR） |
| 未知路径三域全跑（fail-closed） | 单元 R12 案例（新目录/新扩展名/无扩展名） | 单元 |
| push 至主干恒全跑 / nightly·dispatch 覆盖 | 合并后观察 push run 全跑 + 首个 nightly | 手工（合并后） |
| 既有 upstream 判定与 38 例零回归 | 既有测试文件不动全绿 | 单元 |
| gate 状态机（逐域 touched/success/skipped + filter 前置） | CI 日志级（本批 PR + 回填 PR 正反两证） | CI 日志 |
| 新 ADR/DIRECTORY/闭包 | `check_docs.py --closure` + `gen_customizations.py --strict` | 门禁 |

### 分类器单元矩阵（规则表逐条）

| 规则 | 正例路径 | 预期域集合 |
|---|---|---|
| R1 | `ci_impact.py`、`_common.py`、两个 aixcoding workflow | 双域 |
| R2 | `aixcoding/tests/config/test_x.py`；`aixcoding/tests/guard/verify_guard_deployed.py` | {aixcoding-tests}；后者追加 {guard-deploy}（与 R3 累积） |
| R3 | `src/chrys/kernel/aixcoding/guard/guard_install.py` | {guard-deploy, aixcoding-tests}（∪ R4） |
| R4 | `src/chrys/service/aixcoding/config/loader.py`（各 tier） | {aixcoding-tests} |
| R5 | `aixcoding/mock/model_catalog/server.py`、`aixcoding/mock/auth/README.md` | {aixcoding-tests}（README 并集 R11 空集不移除） |
| R6 | `aixcoding/tools/gen_customizations.py`；`aixcoding/tools/guard_install_merge.py` | 前者 {aixcoding-tests}；后者追加 {guard-deploy}；`aixcoding/tools/README.md`（文档后缀）落 R11 空集 |
| R7 | `MANUAL_TESTS.md` | {guard-deploy, aixcoding-tests}（双消费，M1） |
| R8 | `pyproject.toml`、`uv.lock`、`.python-version` | 双域 |
| R9 | `src/chrys/app/app.py` | 双域 |
| R10 | `tests/app/test_app.py`、`docs/en/x.md`、`docs/index.yaml`、`locales/chrys.pot` | 空集（有依据豁免） |
| R11 | 8 个例外文件各一例；`aixcoding/docs/batches/x/design.md`、`README.md`、`aixcoding/manual/zh-Hans/x.md` | 例外 → {aixcoding-tests}；其余空集 |
| R12 | `brand-new-dir/file.txt`、`weird.ext`、`noext` | 双域（fail-closed） |
| 并集语义 | R7×R11（同一 MANUAL_TESTS.md）、R5×R11（mock README） | 空集规则不移除已贡献域 |
| CLI | `--domains` 输出恰好两行 `test_touched=...` / `guard_touched=...`（布尔）；错误 exit 2 | 接口约定 |

## 异常与降级路径

- 空 diff / 分类器异常 / 输出非法 → filter 失败，gate 不放行（同 upstream-ci-tiering 模式）。
- probe python3 版本门限（run #125 教训内置）；非 PR 事件（push/schedule/dispatch）→ 双域恒
  touched=true 不做 diff。
- concurrency 按 `ref + event_name` 分组：push 与 nightly 不互取消。
- gate：`filter.result == success` + 双 touched 精确匹配 + 逐域 `(touched∧success)∨(¬touched∧skipped)`。

## 手工验证步骤

1. 本地模拟：真实 diff 清单喂 `--domains`，逐类路径复核（含 9 例外文件与 mock README 并集）。
2. 本批 PR：R1 FORCE 自证（双域全跑）、filter 日志（probe/事件分支）、gate 输出各域状态。
3. 合并后：纯文档回填 PR 三件套；push run 全跑观察；首个 nightly（UTC 18:00）观察。结果记
   verification.md。
