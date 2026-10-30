# 验证记录：auth 登录状态埋点（aixcoding.auth logging）

> 追加不删旧（R7：验证即证据——命令 + 输出摘要）。本地验证落盘于此；CI 证据归属 PR checks 本身（§7）。

## 2026-10-29 实施验证（Windows 11，本地）

环境口径（DEVELOPMENT.md 本地配方）：`PYTHONPATH=` 清空、`UV_PYTHON=3.14.3`、`PYTHONUTF8=1`、大写盘符。

### 1. 单测：12 分支全绿

```
uv run pytest aixcoding/tests/auth/test_session_logging.py -n0 -q
12 passed in 16.72s
```

auth 目录回归（含既有 9 文件 + 新文件）：

```
uv run pytest aixcoding/tests/auth -n0 -q
112 passed in 36.46s
```

全量定制测试（实施后绝对导入改写复跑）：

```
uv run pytest aixcoding/tests -n0 -q
301 passed, 2 skipped in 68.38s
```

（2 skipped 为既有环境相关跳过，非本批次引入。）

### 2. 门禁：ruff / ty / 定制清单

```
uv run ruff check src/chrys/kernel/aixcoding/auth/session.py     → All checks passed
uv run ruff format --check src/chrys/kernel/aixcoding/auth/session.py → 1 file already formatted
uv run ty check --error-on-warning --python-platform win32 src/chrys → All checks passed
uv run python aixcoding/tools/gen_customizations.py 后 git diff aixcoding/docs/CUSTOMIZATIONS.md → 零 diff（幂等）
```

实施波折记录：①ruff 首跑 TID252×1（父模块相对导入被禁）——`..diagnostics` 改绝对导入 `from chrys.kernel.aixcoding.diagnostics.logging_support import get_logger`（ruff --fix 自动归位排序）；②RUF001×29（中文全角标点判 ambiguous）——`session.py` 文件头 `# ruff: noqa: RUF001`（先例：pyproject:207 为 tui 目录 per-file-ignores 豁免、但那是上游文件，为守"零上游改动"口径用定制文件级 noqa，同款先例 `logging_support.py:1`）。③test_09 首版断言用错对象（MemoryBackend 的 RAM 态在 CredentialStore 实例非 backend 实例，两个 session 不共享），改用 seed session 的 store 断言"delegation logout 不销毁已存凭证"。

### 3. 落盘闭环（launcher 启动 TUI，验收标准 4）

`%APPDATA%\chrys` 为本机 config_dir（`get_platform().config_dir` 实测输出）。launcher 短暂启动 15 秒后终止：

```
uv run python -m chrys.kernel.aixcoding.diagnostics.launcher   （TUI 正常启动，stdout 渲染帧正常）
```

`%APPDATA%\chrys\aixcoding-logs\aixcoding.log` 落盘内容（启动即有 silent check 记录）：

```
2026-10-29 17:37:56,813 INFO aixcoding.auth: 未登录（首次使用或登录已过期）；env=prod
```

直走链路探针（launcher 同款 setup_logging + 真实 check_silent）复现：

```
config: DiagnosticsConfig(logging=LoggingConfig(level=20, panel=True), source=...\chrys\aixcoding.toml)
sink: C:\Users\Zhoubin\AppData\Roaming\chrys\aixcoding-logs\aixcoding.log
--- log file ---
... 17:37:56 INFO aixcoding.auth: 未登录（首次使用或登录已过期）；env=prod
... 17:39:28 INFO aixcoding.auth: 未登录（首次使用或登录已过期）；env=prod   ← 探针自身写入
```

日志文件中另观测到 17:33/17:36 两对 `env=local; ehr=1234567` 的「已登出/登录成功」记录——**非测试泄漏**（见下条），为本机手动 mock 登录活动（真实用户路径闭环的旁证：mock server 登录流程的 #8/#10 记录如约落盘）。

### 4. 测试无泄漏（评审 F5 隔离 fixture 有效性实证）

```
基线 7 行 → uv run pytest aixcoding/tests/auth aixcoding/tests/diagnostics aixcoding/tests/mock -n0 -q
222 passed, 2 skipped → 日志仍 7 行 → NO LEAK
```

### 5. 待人工项：F6 面板呈现（验收标准 3）

本机 `aixcoding.toml` 已是 `panel=true`。面板冒泡链路（propagate → root `_TuiLogHandler` → MODULE_ORDER 白名单 "aixcoding" tab）由 diagnostics 既有测试覆盖（`test_propagate_follows_panel_switch` 等）；TUI 交互式目验（F6 打开见中文记录）留责任人下次启动时顺带确认——launcher 落盘已实证记录产生，面板仅差目视一环。

### 6. 工作区改动面（零上游）

```
git status --short
 M src/chrys/kernel/aixcoding/auth/session.py        （唯一源码改动，+26 行左右埋点）
?? aixcoding/docs/auth-logging/                       （六文档管线产物）
?? aixcoding/tests/auth/test_session_logging.py       （12 用例 + 隔离 fixture）
```

## 2026-10-29 双 AI 自审（实施态）修复复跑

评审 AI：Deepseek-V4-Pro（独立会话）；6 findings（A-F）+ 1 覆盖缺口 nit，无 blocker；责任人裁决全处置。

**勘误**：上节波折③"改用 seed session 的 store 断言"为**错误修复方向**——两个独立 `CredentialStore` 各持 `_ram`（`storage.py:65/83`），`seed.store.load` 恒非 None，断言 vacuous（评审 Finding B 指出）。已改为向 session 自身 store 预存 credential、断言 delegation logout 后仍在。

修复清单（责任人 2026-10-29 裁决）：

- A：`session.py` #9 消息改回 design 冻结口径 `跳过登出（当前使用桌面端登录，由桌面端管理）`（实现曾误用机制词"父进程"，偏离签认口径）；
- B：test_09 重写（预存断言，消除 vacuous）；
- C：test_02 补 `delegated_credential is None`（拒绝停止 shadow）、test_03 补 `delegated_credential is not None`（网络失败保留 delegation）；
- D：删 `plain_session`（复用 `make_session`）；
- E：保留 `cause=ConnectError` 精确断言 + 平台假设注释（loopback 死端口立即拒绝；责任人裁决保留精确）；
- F：`DIRECTORY.md` §3 相对导入语义澄清（同包子模块 `.` 相对；跨子包 `..` 父级相对被 ruff TID252 禁止、用包内绝对导入——责任人裁决选 A）；
- 覆盖缺口（#11 仅测 `DevicePollDenied`）：不补——`exc=类名` 机制对异常子类自动工作，其余失败类型走同一代码路径。

复跑：

```
uv run pytest aixcoding/tests/auth -n0 -q     → 112 passed in 36.03s
uv run ruff check src/chrys/kernel/aixcoding/auth/session.py      → All checks passed
uv run ruff format --check src/chrys/kernel/aixcoding/auth/session.py → already formatted
```

## 2026-10-30 恢复补验（launcher-retirement 合并后、聚合入口实施前）

背景：批次改动备份暂存后恢复（HANDOFF：`fork/temp/auth-logging_backup/`，前置 PR #69 已合并 `1784707`）；`session.py` 已是解耦版（直写 `logging.getLogger("aixcoding.auth")`，不 import diagnostics）。本节补上原实施期验证缺口——当时只过 ruff/ty 未跑 tests/architecture，若绝对导入旧形态仍在会被 `test_layering` 的 kernel↔kernel 必须相对规则（`_is_violation`）拦截。

### 1. 恢复操作

- 备份 3 项复制回工作区（`session.py` 解耦版 / 六文档 / `test_session_logging.py`）；
- `DIRECTORY.md` §3 相对导入括号注重应用后**修正**为死锁结论（`..` 相对被 TID252 禁、绝对导入被 test_layering 禁，kernel 跨子包须解耦——外部评审 M1，责任人 2026-10-30 认可）；
- `test-plan.md` #9 期望消息同步冻结口径（外部评审 M3①，责任人认可）。

### 2. 单测 + 架构全量

```
uv run pytest aixcoding/tests/auth -n0 -q      → 112 passed in 40.35s
uv run pytest tests/architecture -n0 -q        → 1238 passed, 3 skipped in 142.27s
uv run python aixcoding/tools/check_docs.py    → OK (13 ADR / 12 design / 10 self-review)
```

解耦版 `session.py` 在 kernel↔kernel 架构规则下全绿——design §依赖方向自查的机器实证（app→app 接线边属待实施项，实施后按 design §验证方式五条复跑）。

## 2026-10-30 实施验证（聚合入口接线，design 重签后）

环境口径同上。design 重签（2026-10-30，R2 批准）后实施待实施项①-④：`app/aixcoding/startup.py` 聚合入口、`logging_support.py::ensure_file_sink()`、`app.py main()` 接线（+3 行，唯一上游行）、`test_entry_wiring.py`（6 用例）。

### 1. 单测 + 架构

```
uv run pytest aixcoding/tests/diagnostics/test_entry_wiring.py -n0 -q → 6 passed in 4.37s
uv run pytest aixcoding/tests/diagnostics -n0 -q                  → 22 passed（ruff fix 后复跑）
uv run pytest aixcoding/tests -n0 -q                               → 294 passed, 2 skipped
uv run pytest tests/architecture -n0 -q                            → 1238 passed, 3 skipped
```

（294 与 10-29 记录的 301 差 = launcher 退役批次 PR #69 删测试，非本批次引入；本批次 +6。）

### 2. 闭环：直跑 icode 落盘（验收标准 4）

直跑 `uv run icode`（TUI 正常启动，渲染帧正常），12 秒后终止进程树。`%APPDATA%\chrys\aixcoding-logs\aixcoding.log` 新增（launcher 退役后首条，新链路 `main() → aixcoding_startup() → ensure_file_sink` 端到端实证）：

```
2026-10-30 12:14:58,166 INFO aixcoding.auth: 未登录（首次使用或登录已过期）；env=prod
```

F6 面板目验（验收标准 3）留责任人下次启动顺带确认（本机 `aixcoding.toml` panel=true）。

### 2b. 责任人实测目验（2026-10-30 13:50，F6 + 落盘双通道通过）

责任人亲自运行：mock auth（`python -m aixcoding.mock --only auth`，:7777）+ iCode TUI（`AIXCODING_AUTH_ENVIRONMENT=local`）。**F6 "aixcoding" tab 目验通过**（silent check / 登录 / 登出记录面板可见）；落盘文件同步核对（消息全文与 design 冻结口径逐字一致，env=local，ehr 仅成功路径）：

```
2026-10-30 13:50:21,412 INFO aixcoding.auth: 未登录（首次使用或登录已过期）；env=local
2026-10-30 13:50:32,570 INFO aixcoding.auth: 登录成功；ehr=1234567 env=local
2026-10-30 13:51:18,805 INFO aixcoding.auth: 已登出；env=local
```

### 3. 定制清单（freshness 义务）

```
uv run python aixcoding/tools/gen_customizations.py ×2 → wrote (28 custom points)，连跑两次幂等
```

新 C003 行（`app.py:177` marker，来源 auth-logging design）入产物。首跑曾拦下 marker↔登记行格式不匹配（error：模块词 `customizations` 匹配不上落点 `src/chrys/app/cli/app.py`）——按 C005（diagnostics）同构模式修复：marker 补括号归属 `(src/chrys/app/aixcoding/startup.py)`、登记行落点列改纯路径，design R2 表文案同步。剩余唯一 warning 为 auth 批次遗留预告（wire_client token 注入未实施），与本批次无关。

### 4. 门禁

```
uv run ruff check <四改动文件>            → 1 auto-fixed, 0 remaining
uv run ruff format --check <四改动文件>   → 4 files already formatted
uv run ty check --error-on-warning --python-platform win32 src/chrys → All checks passed
```

### 5. 工作区改动面

```
 M src/chrys/app/cli/app.py                                 （+3 行，R2 唯一上游行）
 M src/chrys/kernel/aixcoding/diagnostics/logging_support.py（+18 行 ensure_file_sink）
?? src/chrys/app/aixcoding/startup.py                       （聚合入口，tui 同族）
?? aixcoding/tests/diagnostics/test_entry_wiring.py         （6 用例）
 M aixcoding/docs/CUSTOMIZATIONS.md                         （C003 纳入产物，随提交）
```
```
