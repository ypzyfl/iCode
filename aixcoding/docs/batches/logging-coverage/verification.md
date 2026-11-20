# 验证：定制功能日志覆盖补全（logging-coverage）

> 追加不删旧；命令 + 输出摘要（R7）。

## 2026-11-20 实施验证（分支 feat/logging-coverage，基线 098b66f1）

改动清单（git status）：9 个定制源文件 + 4 个既有测试文件修订 + 1 个新测试目录 + 批次文档目录；**R2 空表核实**：`src/chrys/*/aixcoding/` 与 `aixcoding/` 之外零改动（上游文件 git diff 为空）。

### 机器验证（配方：`set "PYTHONPATH=" && set "PYTHONUTF8=1"`、大写盘符）

| 门禁 | 命令 | 结果 |
|---|---|---|
| 定制全量 | `uv run pytest aixcoding/tests -n0 -q` | **864 passed / 56 skipped**（修订 entry_wiring 断言后复跑 diagnostics+config 33 passed；前次 8 挂均为既有英文断言随中文文案的预期修订，见下"实施注记"） |
| 架构 | `uv run pytest tests/architecture -n0 -q` | **1248 passed / 3 skipped** |
| 默认入口 | `uv run python aixcoding/tools/verify.py --smart --paths <14 文件>` | **Summary: PASSED (exit 0)**：custom 865 passed / 56 skipped；upstream 16621 passed / 162 skipped + architecture 326 passed（Smart Test 自动扩展全量） |
| 静态 | `uv run ruff check` + `ruff format --check`（9 源文件 + 5 测试文件） | 全过（noqa 落位于字符串字面量行） |
| 对账 | `uv run python aixcoding/tools/gen_customizations.py --strict` | **106 行 / 154 marker / 0 warning**（与基线一致：本批零上游 marker 变更） |
| 文档 | `uv run python aixcoding/tools/check_docs.py` | OK（27 ADR / 49 design / 47 self-review） |

### 新增测试（T7）

- `aixcoding/tests/logging_coverage/test_coverage.py`（新建，25 用例）：静态扫描（四文件零 `getLogger(__name__)`）、update 检查失败五分支参数化（主 WARNING 逐字断言兼 PII 嗣兵 + detail 原因）、204/304 静默守卫、unbuildable detail-only、wrapper 失败 ERROR 双写、skills 三用例（成功清单/异常 re-raise/FileNotFoundError 静默）、guard 三用例（安装幂等 detail-only/坏 yaml 重置主 WARNING 含备份路径/资源缺失 detail-only）、config 九场景三通道参数化、startup task 三通道；
- `test_flow.py` +2：CONFIRM/SKIP 主通道 INFO（spy 需 pin logger INFO 级别——root WARNING 门槛会拦 INFO 记录，fixture 内 setLevel+恢复）；
- `test_catalog_sync.py` +3：覆盖/清空主通道 WARNING 逐字断言 + 健康同步零公共记录哨兵。

### 实施注记（对 design 的两处实施级偏离，均语义修正）

1. **update `client.py:180` unbuildable params 落为 detail-only**（design 表格曾列入失败分支）：参数不可构造=本机在契约外"未检查"（freebsd/未知架构/版本畸形），非"检查失败"——升主通道会把"未检查"误报为失败，与 204/304 静默同理。`_detail_log`「更新检查查询参数不可构造…本次不检查」；
2. **成功路径 detail 打点去掉 `response.elapsed` 字段**：MockTransport/未读响应下 `elapsed` 抛 RuntimeError（测试实证）；生产价值低，删除。

### 既有断言修订（design ⑤ "三通道统一中文"预告的落实）

- `aixcoding/tests/config/test_config.py` 6 处英文 stderr 断言 → 中文（invalid environment/base_url/auto_sync/cannot parse）；
- `aixcoding/tests/diagnostics/test_entry_wiring.py:63` "task boom failed" → 「启动任务 boom 失败」。

### 待办

- [x] 手工三抽验（2026-11-20 完成，见下节）；
- [ ] self-review（双 AI 评审）；
- [ ] overview.md:21 过时表述修订（T9，随 PR）。

## 2026-11-20 手工三抽验（T8 手工部分）

方法：`APPDATA` 环境变量重定向至 `%TEMP%\lc-verify\AppData`（**零接触真实 `~/.chrys`**）；mock 组合（`python -m aixcoding.mock`，:7777 catalog+auth auto、:7778 update）可见窗口；TUI 可见窗口；真实登录链路（mock auto 批准，device-code）；隔离 toml `environment="local"` + `[model_catalog] auto_sync=true`（local tier 默认关同步需显式开启）。

**三条主通道 WARNING 全部在 `aixcoding.log` 主卷命中**（GBK 控制台乱码不影响卷文件本身为 UTF-8）：

| # | 场景构造 | 主卷记录（实测） |
|---|---|---|
| 1 | 落盘 `openai-gpt-4o-mini.yaml` 去标记（变自建）+ 辅助标记文件 `zz-server.yaml`（防误判升级清空）+ 同步 | `WARNING aixcoding.catalog: 以下自定义模型与后端模型 id 相同，已被后端版本覆盖：openai-gpt-4o-mini。` |
| 2 | `hooks/hooks.yaml` 写入非法 YAML → TUI 重启 | `WARNING aixcoding.guard: 检测到无法解析的 hooks 配置，已备份至 …\hooks.yaml.pre-guard 并以安全护栏模板重置；原配置可从该备份恢复。` + `.pre-guard` 备份文件实证存在 |
| 3 | 全目录无标记 + 有文件 → 同步 | `WARNING aixcoding.catalog: 检测到旧版无标记模型目录；已清空 0 个配置文件，本次按后端目录重建。`（0 个：同名文件经 os.replace 重写不计清空，触发与文案正确） |
| 4 | 坏 toml（非法语法）+ **sink 就绪后** `load_config`（独立冒烟：`setup_logging` → `cache_clear` → `load_config`） | 主卷 `WARNING aixcoding.config: 配置文件无法解析（…），已回退全部默认。` + detail 卷同文案双写（`aixcoding.detail.config`，时间戳相邻）+ stderr 同文案——**三通道统一中文实证** |

**附带实证**（过程中自然覆盖）：skills 成功清单 detail（工作区+用户根目录清单）；guard 首装 detail 与幂等重装「已就绪」detail；auth PII 双卷（主卷登录成功**无** ehr、detail 含 `ehr=1234567`）；catalog 请求 detail 双版（path 版+userId 全量版）；env 伪 token 被 dispatch 401 拒绝（安全行为正确）。

**抽验中钉死的两个环境事实**（非本批缺陷，留档）：
1. **first-run 边界实证**（design 假设 5 的现实印证）：`_configure_environment` 在 sink 建立前读配置，坏 toml 的 loader 警告仅落 stderr（TUI 窗口）+ lastResort，**主/detail 卷无记录**，且 `@cache` 后同进程不再触发——故 loader 抽验改用"sink 就绪后独立冒烟"取卷内证据（测试用例已覆盖三通道断言）；
2. PS5.1 `Set-Content -Encoding utf8` 写 **BOM** → `tomllib` 解析失败回退全默认（`data={}`）——写隔离 toml 须无 BOM（`[IO.File]::WriteAllText`）。

清理：mock/TUI 窗口进程树终止、隔离目录删除、临时脚本删除；工作区恢复纯批次改动（git status 核对）。

## 2026-11-20 评审 F1 修复回归（DeepSeek-V4-Pro 代码评审 blocker）

修复内容：`loader.py` environment 来源 origin 字面化；`guard_install.py` 主通道 WARNING 改固定相对形（绝对备份路径仅 detail）；新增 `test_main_channel_pii_sentinel` + guard 用例强化（详见 self-review.md 轮④）。

| 门禁 | 结果 |
|---|---|
| `uv run pytest aixcoding/tests -n0 -q` | **866 passed / 56 skipped** 全绿 |
| `uv run ruff check` + `format --check`（三改动文件） | 全过 |

> 注：手工抽验节的 guard 重置实测记录为修复前文案（含绝对路径）——恰为 F1 泄漏的实证；修复后主卷文案为相对形（`hooks/hooks.yaml.pre-guard`），由新增哨兵用例钉死。

## 2026-11-20 增量复审处置（F1 复审通过后）

- 复审结论：F1 三处修复复审通过、blocker 清零、收敛达标（评审原文落 self-review.md ④增量行）；
- S1 已修：`_resolve_environment` 删 dead `source` 形参 + 调用处同步（`uv run pytest aixcoding/tests/config/ aixcoding/tests/logging_coverage/ -n0 -q` → **51 passed**；ruff check/format 过）；
- N1 呈报不修（理由见 self-review.md ④增量行：`~/.chrys` 前缀在 Windows 指向不存在路径）。

## 2026-11-20 PR #141 CI 修复（RUF001 行级 noqa 失效 → 方案 A 文件级头）

- **现象**：CI `ruff check` 报 `guard_install.py:331` 两处 RUF001——F1 修复后 ruff format 按显示宽度（East Asian wide=2）将单行 WARNING 折为三行，行尾 noqa 被留在闭括号行、脱离字符串行诊断（noqa 按行匹配）；本地 format 重排后未重跑该文件 check，漏检。CI "1 fixed" 为 fix=true 自动清理失效 noqa。
- **修复（责任人裁决方案 A）**：两文件改**文件级豁免头**（`guard_install.py` 新增 `# ruff: noqa: RUF001`；`startup/__init__.py` 并入现有 T201 头），删除全部 6 处行级 noqa——noqa 不在打点行，format 任意折行不再影响；零上游（不动 pyproject）。loader.py `noqa: T201` 头同款先例。design R13 节已随改（签认后修订注记）。
- **复验**：`ruff format --check`（两文件）不再重排；`ruff check aixcoding/ src/chrys/`（CI 同口径）All checks passed；`pytest logging_coverage/ guard/ diagnostics::entry_wiring` 61 passed / 1 skipped。

## 2026-11-20 真实环境复验（责任人手动 + AI 构造场景，当前分支工作区代码）

责任人手动验证通过：`/login`（登录成功 INFO/徽标）、启动本身。AI 在真实环境（`C:\Users\Zhoubin\AppData\Roaming\chrys`，先备份 `.rv-backup/` 后构造、终态还原核对）补验四场景，**全部命中**：

| 场景 | 主卷实测（时间戳 2026-11-20） |
|---|---|
| guard 备份重置（坏 hooks.yaml + 重启） | `WARNING aixcoding.guard: 检测到无法解析的 hooks 配置，已备份并重置为安全护栏模板；原配置可从 hooks/hooks.yaml.pre-guard 备份恢复。`（14:30:48）——**F1 修复后新文案首次实机验证，相对形无路径** |
| catalog 清空重建（真实旧版无标记目录形态：两文件全无标记 + 无 catalog-state） | `WARNING aixcoding.catalog: 检测到旧版无标记模型目录；已清空 1 个配置文件，本次按后端目录重建。`（14:30:48）——"1 个"实证 B5 语义（同名文件经 os.replace 重写不计清空） |
| loader 坏 toml（sink 就绪冒烟） | stderr + 主卷 `WARNING aixcoding.config: 配置文件无法解析（…），已回退全部默认。`（14:31:37）+ detail 同文案——三通道统一中文，exc 文本无路径 |
| catalog 覆盖（去标记 + 辅助 marker + 重启） | `WARNING aixcoding.catalog: 以下自定义模型与后端模型 id 相同，已被后端版本覆盖：openai-gpt-4o-mini。`（14:32:58） |

**还原核对**（脚本自动执行）：toml 恢复用户原版（`environment="local"` + `[logging]`，无 model_catalog 段）；models/ 恢复用户原两文件（`deepseek-flash.yaml`、`openai-gpt-4o-mini.yaml`），mock 产物（含 `.catalog-state.json`、`zz-server.yaml`）清除；验证期坏 `.pre-guard` 删除；TUI 恢复运行。备份目录 `.rv-backup/` 暂存仓库根，责任人确认还原无误后删除。真实日志卷新增的验证记录为事实流不清理。


## 2026-11-20 PR #141 peer review 处置（CodeBuddy 同源评审，缺陷模式抽查）

评审结论：R2/R11/幻觉 API 通过；破坏性实验 4/4 ANCHORED；候选七条处置——

- **C1（修）** `{exc}` 可变字段 PII 残留：loader.py OSError 分流无路径文案（「配置文件无法读取，已回退全部默认。」；TOMLDecodeError/UnicodeDecodeError 文本天然无路径保留原文案）；startup `{exc}` 改 `type(exc).__name__` + detail 补 `exc_info=True`（栈仅 detail 卷）；测试补异常注入哨兵（startup 用例改注入带路径 PermissionError、新增 `test_config_oserror_message_carries_no_path`）。
- **C2（修）** 两处测试锚定缺口：新增 `test_skills_team_permission_error_logged_detail`（PermissionError→detail 分支，test-plan 原承诺落地）；`test_flow.py` CONFIRM/SKIP 补 detail 双写断言（`_detail_spy` helper）。
- **C3（修）** check_docs 计数勘误：机器验证表「47 self-review」为首跑时点快照（self-review.md 尚未落盘），self-review 落盘后实测 **48**（PR 树复跑与 --closure 双证）；本节勘误按追加不删旧纪律留存，正文数字不改。
- **C4（修）** test-plan 组织表/用例名回填实际落地形态（集中 `logging_coverage/test_coverage.py` 为主 + flow/catalog/config/entry_wiring 四文件修订），见 test-plan.md 实施回填节。
- **C5（不动作）** RUF001 文件级豁免面扩大：方案 A 既裁决（观察留档）；guard_install 后续批次注意文案静默面。
- **C6（修）** overview.md skills 域措辞消歧（无主通道 logger，仅 detail 子树）。
- **C7（PR 描述勘误，GitHub 侧）** 「6 测试文件」应为 **5**（1 新建 + 4 修订，verification.md:7 自身口径正确）；PR 描述修正由责任人在 GitHub 编辑。

处置后本地复验见下节。

### 处置后复验（2026-11-20）

| 门禁 | 命令 | 结果 |
|---|---|---|
| 定向测试 | `uv run pytest aixcoding/tests/logging_coverage/ aixcoding/tests/auto_update/test_flow.py -n0 -q` | **44 passed**（含 C1/C2 新增用例） |
| 定制全量 | `uv run pytest aixcoding/tests -n0 -q` | **868 passed / 56 skipped**（基线 866 + C1×1 + C2×1 新增用例，全部通过） |
| 静态 | `uv run ruff check --no-fix aixcoding/ src/chrys/` + `ruff format --check`（8 改动文件） | All checks passed（`test_coverage.py` 一处 assert 折行经 `ruff format` 归一后复查通过） |
| 文档 | `uv run python aixcoding/tools/check_docs.py` | OK（27 ADR / 49 design / 48 self-review） |
| 定制清单 | `uv run python aixcoding/tools/gen_customizations.py --strict` | check OK——106 行 / 154 marker / **0 warning** |

环境注记：复验以 `set "PYTHONPATH="`（脱离 safe-delete shim）+ `set "PYTHONUTF8=1"` 运行；safe-delete 对 pytest 临时目录批量清理的拦截（SAFE_DELETE_BULK_CONFIRM_REQUIRED）为环境噪音在案，不影响测试结果本身。
