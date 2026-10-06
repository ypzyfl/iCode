# AIxCoding 对 iCode 源代码的改动台账

本文件是 AIxCoding fork 对 iCode 上游源代码全部改动的**唯一登记处**。规则见 `AGENTS.md`「AIxCoding fork-local changes」小节；登记格式与团队先例（aixcoding-continue 的 `core/aixcoding/` owner 命名空间实践）同源。

## 规则摘要

1. **新建文件一律放 `src/chrys/aixcoding/`**（按需建子包，如 `telemetry/`、`auth/`）——上游永远不会建这个名字的包，fork 与上游 merge 时整目录零冲突；
2. **对上游既有文件的每一处改动在此登记**，编号 `M-xxx`（递增不复用）：记录改动点（文件:行）、服务的功能、为什么必须改上游代码、跨仓引用写纯文字（如 `agent_studio_new docs/adr/0041`），不写相对链接；
3. **改动处源代码带标记注释** `# [AIxCoding M-xxx] <必改理由>`，与台账编号互链；
4. **对账用 grep 不用记忆**：`grep -rn "\[AIxCoding\]" src/` 的结果必须与本台账"上游文件改动"逐一对应——"改了没登记"与"登记了已删"都是缺陷；上游同步或发行裁切前必须先对账。

## 台账

### 上游文件改动（逐条登记）

### M-001 统一 Hook 通路 install 接线

- **位置**：`src/chrys/orchestration/session_hooks.py`（`SessionHookFactory.__call__` 内，`config_dir` 取得后、`load_hooks_dir` 之前）
- **服务功能**：AIxCoding 会话采集（统一 Hook 方案，agent_studio_new `docs/adr/0041` 与《Chrys-会话采集统一Hook方案》rev.4d）——TUI 与桌面 ACP 两场景经同一引擎 hook 机制触发 collector 上报。
- **必改理由**：install 需要挂接在"每次 session start"时机才能满足条目自愈（用户篡改后下一会话恢复）与"写入条目本 session 立即生效"（首会话冷启动无空窗）；而 TUI/ACP/headless 三种 surface 唯一共同的该时机汇聚点就是 `SessionHookFactory.__call__`。纯外部调用（打包脚本/桌面端/手动）无法覆盖全部 surface，且会把安装责任拉回桌面端（违背方案的 U1/U2）。引擎核心机制（hooks/outbox/finalizer/detach）零改动，只加一处调用。
- **关联**：agent_studio_new `docs/adr/0041`；实现全部位于 `src/chrys/aixcoding/telemetry/install.py`（fork-local）
- **日期 / 状态**：2026-10-06 / 已实现（随 M2-C）

### M-002 layering 守卫与 Source map 注册 `chrys.aixcoding` 顶层包

- **位置**：`tests/architecture/test_layering.py`（`TIER_ORDER` 增加 `AIXCODING: 2`）+ `AGENTS.md` Source map 小节（新增 aixcoding 行）
- **服务功能**：同 M-001——`chrys.aixcoding` 命名空间需要作为合法顶层模块参与 layering DAG。
- **必改理由**：`test_layering.py` 拒绝未注册 `TIER_ORDER` 的顶层包（L214-215 未注册即违规）；fork-local 命名空间是本仓改动纪律（AGENTS.md「AIxCoding fork-local changes」）的载体，必须注册而非把代码塞进上游功能位置。tier 定为 service 级（2）：aixcoding 只 import foundation + service，不触碰 orchestration/app。
- **关联**：同 M-001；CI shard 无需改动（core shard 按根目录 `tests` 收集，`tests/aixcoding/` 自动覆盖）
- **日期 / 状态**：2026-10-06 / 已实现（随 M2-C）

### M-003 tests 顶层布局允许 `tests/aixcoding` fork-local 测试树

- **位置**：`tests/architecture/test_test_layout.py`（`_TARGET_TOP_LEVEL` 增加 `"aixcoding"`）
- **服务功能**：同 M-001——AIxCoding 采集（Python collector 移植，M2-A'）的全部测试位于 `tests/aixcoding/`。
- **必改理由**：`test_test_directories_use_allowed_top_level_layout` 拒绝白名单外的 tests 顶层目录；fork-local 测试树与 `src/chrys/aixcoding` 命名空间一一对应（同 M-002 的注册逻辑），上游永远不会创建 `tests/aixcoding`，合并冲突面为零；塞进上游功能目录（service/foundation 等）反而污染上游域。
- **关联**：agent_studio_new `docs/adr/0041` rev.5（collector Python 化）；实现位于 `src/chrys/aixcoding/telemetry/collector/`（fork-local）
- **日期 / 状态**：2026-10-06 / 已实现（随 M2-A'）

### M-004 detached hook worker 在 Windows 上优先使用 GUI 子系统解释器（pythonw）

- **位置**：`src/chrys/service/hooks/runner.py`（新增模块级 `_detached_worker_executable()`，`spawn_detached` 内 `worker_cmd` 的解释器改为该函数返回值）
- **服务功能**：AIxCoding 会话采集（统一 Hook 通路）——after_turn/session_end hook 每次触发都会经 detach worker spawn collector；同时惠及未来任何 detached hook 用户。
- **必改理由**：Windows 11 默认终端为 Windows Terminal 时，"无控制台父进程 spawn 控制台程序"必然创建控制台且 WT 无视 `STARTUPINFO(SW_HIDE)`，每次 hook 触发闪一个可见窗口（TUI 手工联调实测，含窗口枚举探针实证）；且 venv `python.exe` launcher 会在第二跳重建控制台，`DETACHED_PROCESS` 语义在 launcher 链上失效。唯一稳定解是 GUI 子系统 `pythonw.exe`（两层跳均不建控制台、stdio 走句柄继承不受影响），而 worker 解释器的选择只能在 runner.py 内完成。`pythonw.exe` 不存在时（如 PyApp 冻结别名）回退 `sys.executable`，行为与改动前一致。
- **关联**：agent_studio_new `docs/adr/0041`；配套 fork-local 改动：`src/chrys/aixcoding/telemetry/install.py` 的 `_collector_executable()`（collector argv 同款 pythonw 优先）与 `collector/analysis/git_context.py`（git 子进程 `DETACHED_PROCESS`）；上游测试断言同步于 `tests/service/hooks/test_runner.py`
- **日期 / 状态**：2026-10-06 / 已实现（随 M2-A 出口验收的闪窗修复）

### M-005 断言"空 hooks 契约"的上游引擎测试声明式禁用采集安装

- **位置**：`tests/orchestration/engine/conftest.py`（新增非 autouse fixture `_no_aixcoding_telemetry_install`）+ `tests/orchestration/engine/build/test_lifecycle_hooks.py`（2 个测试签名接入）+ `tests/orchestration/engine/test_shutdown_close.py`（1 个测试签名接入）
- **服务功能**：同 M-001——M-001 的 install 在每次 session start 都会向隔离 config_dir 注入两条 `aixcoding-collector-*` 条目，破坏这 3 个上游测试"无 hooks 配置⇒无 manager/无运行时目录/仅用户条目"的前提。
- **必改理由**：这些测试验证的是引擎自身 hook 机制在空配置下的行为，与 AIxCoding 采集无关；monkeypatch `install.ensure_telemetry_hooks` 为 no-op 是唯一不引入产品开关（P1：采集不可关闭）的隔离方式。install 自身行为由 `tests/aixcoding/telemetry/test_install.py`（含 SessionHookFactory 接线测试）覆盖，不受本 fixture 影响。
- **关联**：agent_studio_new `docs/adr/0041`；发现的契机是 M-004 改动 `runner.py` 使 Smart Test 选择范围扩大到 orchestration/engine 测试（此前从未选中，故 M2-C 落地时未暴露）
- **日期 / 状态**：2026-10-06 / 已实现

### M-006 Windows 构建脚本两处行尾/引号缺陷修复（PyApp patch 4 与 prune 段）

- **位置**：`scripts/build.ps1`（patch 4 段：源文件读取与三个 `$Old*` here-string 匹配前统一 LF 行尾）+ `scripts/build_offline_dist.ps1`（prune 段 `$KeepRg` 的 python -c 载荷 `""` 改 `''`）
- **服务功能**：AIxCoding 会话采集的发行链路——PyApp patch 4（runtime 别名，`chrys-runtime.exe`/`chrys-runtimew.exe`）是采集 hook argv 依赖 `pythonw.exe` 在发行物存在的机制载体（M-004 闪窗修复的发行物侧前提）；prune 段决定发行物体积。
- **必改理由**：① patch 4 是唯一用多行 here-string + 字面 `String.Replace` 的 patch：`autocrlf=true` checkout 下本脚本为 CRLF、PyApp 源码 tar 解包为 LF，字面匹配**静默失败**（其他 patch 用正则或 `r?`n 兼容行尾，唯独 patch 4 无兼容）——2026-10-06 M2-A 出口验收重建发行物时实测失败；② prune 段 `print(names[0] if names else "")` 的 `""` 被 PowerShell 原生命令参数引用折叠为单个 `"`，Python 收到 SyntaxError，`$KeepRg` 恒为空 → 多平台 ripgrep 从不裁剪（非致命但每次构建报错且发行物虚胖）。
- **关联**：agent_studio_new `docs/adr/0041`；发现的契机是 M2-A 出口验收的 PyApp 真机验证（首次在 Windows PowerShell 5.1 + autocrlf 工作区重建发行物）
- **日期 / 状态**：2026-10-06 / 已实现

### 预留条目

（无——后续改动按下方模板新增）

<!-- 登记模板：
### M-xxx <一句话标题>

- **位置**：`src/chrys/<路径>:行区间`
- **服务功能**：<哪个 AIxCoding 能力依赖此改动>
- **必改理由**：<为什么无法在 chrys/aixcoding/ 命名空间内实现、必须改上游代码>
- **关联**：<跨仓引用，纯文字>；实现落于 `src/chrys/aixcoding/<子包>`
- **日期 / 状态**：<YYYY-MM-DD / 进行中|已合入>
-->

### fork-local 新增（命名空间即记录，仅列目录级概览）

- `src/chrys/aixcoding/telemetry/install.py` — install 四合一（归属/auth 刷新 + collector 模块可导入 fail-closed + hooks.yaml 幂等对齐）；唯一公共入口 `ensure_telemetry_hooks()`；hook argv 为 `[_collector_executable(), "-s", "-m", "chrys.aixcoding.telemetry.collector", "run", ...]`（Windows 下 `_collector_executable()` 优先 GUI 子系统 `pythonw.exe`，见 M-004 闪窗修复）。
- `src/chrys/aixcoding/telemetry/collector/` — Python collector（rev.5：模块随 wheel 分发，无 vendor/manifest——rev.3 时代的 vendor 机制已随 M2-A' 删除）；analysis/ 子包（14 文件）+ report/ 子包（file/http sink）+ run 编排 + `__main__` 入口。
- `tests/aixcoding/telemetry/test_install.py` — install 单测 + SessionHookFactory 接线测试 + loader 兼容性 pin。
- `tests/aixcoding/telemetry/collector/` — collector 全量测试（170 项：cli/locator/reader/ledger/lock/attribution/analysis 全模块/report/run 端到端）。
