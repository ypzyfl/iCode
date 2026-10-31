# 测试方案：auth 登录状态埋点（aixcoding.auth logging）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

- 层级：**单元测试**（行为断言，`caplog` 捕获 `aixcoding.auth` 子树记录）；零上游接触故无上游行为锚定项；唯一契约锚定 = logger 命名空间（断言 `record.name == "aixcoding.auth"`，落盘与 F6 冒泡均依赖此名字，属基建既有测试已覆盖链路的入口约定）。
- 落点：新增 `aixcoding/tests/auth/test_session_logging.py`；设施复用 `from test_auth_session import MockServer, make_session`（同目录 pytest 导入，零改动既有文件）+ 既有 conftest（delegation 钳制）。
- mock：`aixcoding/mock/auth`（loopback MockServer：`mode="auto"` 正常流 / 未知 token 业务拒绝 / `deny_next=True` → `DevicePollDenied`）；网络故障用死地址 `http://127.0.0.1:1/api/v1`（既有先例）；delegation 用 `LoginSession(delegated=DelegatedCredential(...))` 显式注入（不受 conftest 钳制影响）。
- **logger 隔离 fixture（评审 F5，本文件 autouse）**：仿 `tests/diagnostics/conftest.py` 的 `aix_logger_state`——保存/恢复顶层 `aixcoding` logger 的 handlers/propagate/level，测试内显式 `propagate=True`，防 diagnostics 测试 `setup_logging(panel=False)` 的跨测试顺序污染（caplog 挂 root，record 需经 propagate 冒泡才被捕获）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| 12 条记录全落 `aixcoding.auth`，分级 ERROR×5 / INFO×7 | test_session_logging.py 12 个分支用例（每个用例断言 `record.name`、消息全文、levelname） | 单元 |
| 脱敏红线（token/refresh/device_code/异常 str 绝不入日志） | 全用例公共反断言 helper：构造含可识别秘密串的 token（如 `secret-token-x`），断言其不出现在任何 `record.getMessage()`；另断言全部 `record.exc_info is None`（无调用栈红线） | 单元 |
| `exc=`/`cause=` 原因格式 | #2/#6 断言 `exc=AuthServerError`；#3/#7 断言 `exc=AuthNetworkError cause=ConnectError`（死地址的 `__cause__` 即 httpx.ConnectError）；#11 断言 `exc=DevicePollDenied` | 单元 |
| F6 面板启动即见记录 | 手工验证（见下）；面板冒泡链路属 diagnostics 基建既有测试（`test_logging_support.py::test_propagate_follows_panel_switch` 等）已覆盖 | 手工 + 既有 |
| `aixcoding.log` 落盘 | 手工验证（见下）；落盘链路属既有测试（`test_setup_creates_sink_and_records`）已覆盖 | 手工 + 既有 |
| `pytest aixcoding/tests` 全绿 | 全目录回归命令 | 回归 |
| 零上游文件改动 | `git diff --stat` 仅 `session.py` + `aixcoding/tests/auth/test_session_logging.py` + 文档；`gen_customizations.py` 产物 diff 为空 | 检查 |

## 用例清单（12 分支 × 断言三件套：消息全文 / levelname / 反断言）

| # | 用例 | 构造 | 期待 |
|---|---|---|---|
| 1 | silent ok (delegated) | `delegated=DelegatedCredential(token=…, ehr=…)` + auto server | INFO `已登录（桌面端登录）；ehr=… env=local` |
| 2 | delegated rejected | `delegated` + 服务器拒绝的 token（未知 token 业务拒绝） | ERROR `桌面端传入的登录已失效，改用本机登录；… exc=AuthServerError`；且 store 接管（`_delegated_rejected` 生效） |
| 3 | delegated network fail | `delegated` + 死地址 | ERROR `登录检查未完成（网络不通），登录状态保留；… exc=AuthNetworkError cause=ConnectError` |
| 4 | no credential | 空 store + auto server | INFO `未登录（首次使用或登录已过期）；env=local` |
| 5 | silent ok (stored) | 登录 round-trip 后再 check_silent | INFO `已登录（本机保存的登录）；ehr=…` |
| 6 | stored rejected | store 预置 bogus token（既有先例） | ERROR `本机保存的登录已失效，已自动清除，请重新登录；… exc=AuthServerError`；且 `store.load(...) is None` |
| 7 | stored network fail | store 有效 token + 死地址（既有先例） | ERROR `登录检查未完成（网络不通），登录信息保留；… exc=AuthNetworkError cause=ConnectError`；且 `stored_token` 保留 |
| 8 | login success | auto server `complete_login` | INFO `登录成功；ehr=… env=local` |
| 11 | login failed | `deny_next=True` server（若 deny_next 需 confirm 触发，则改用 `http=httpx.MockTransport` 伪造 `error=access_denied` 信封——实施时定） | ERROR `登录失败；… exc=DevicePollDenied`；`pytest.raises` 断言异常照抛（re-raise 语义） |
| 12 | login cancelled | `cancel_event` 预先 set | INFO `取消登录；env=local`；`pytest.raises(DevicePollCancelled)` |
| 9 | logout skipped | `delegated` active 下 `logout()` | INFO `跳过登出（当前使用桌面端登录，由桌面端管理）；env=local`；store 未动 |
| 10 | logged out | 登录后 `logout()` | INFO `已登出；env=local` |

## 异常与降级路径

- 网络失败 ≠ 登出（#3/#7）：断言 credential 保留（`stored_token` 不变）——"离线不是登出"行为锚定；
- 拒绝自清（#6）：断言死凭证被清除（下次登录从干净态开始）；
- delegation 拒绝回退（#2）：断言 `_delegated_rejected` 后 `stored_token` 走 store；
- re-raise 语义（#11/#12）：`pytest.raises` 断言异常类型原样上抛——埋点不吞异常；
- logging handler 故障不扰主流程：标准库契约（design §风险四道防线已论证），不为标准库行为写注入测试——理由：测标准库≠测我方代码。

## 接线测试（全模式落盘，2026-10-29 责任人裁决追加）

新增 `aixcoding/tests/diagnostics/test_entry_wiring.py`：

| 用例 | 构造 | 期待 |
|---|---|---|
| ensure_file_sink 幂等 | 隔离 fixture 下两次调用 | 同一 sink 路径（`_Marker` 复用） |
| ensure_file_sink fail-safe | monkeypatch `load_config` 抛异常 | 不抛出、返回 None、stderr 有 note（§9 降级可查） |
| main() 接线锚定 | monkeypatch `ensure_file_sink` + `sys.argv=["icode","--version"]` 跑 `app.main()` | 被调用（上游重构删接线即红——架构级回归锚） |
| DAG 合法性 | 既有 `test_layering` 全量跑 | app→kernel 标准边，无新豁免需求 |

手工（TUI 直跑，不经 launcher）：`uv run icode` → F6 aixcoding tab 有记录 **且** `%APPDATA%/chrys/aixcoding-logs/aixcoding.log` 同步落盘——全模式落盘的最终验收。

## 手工验证步骤（结果记入 verification.md）

1. `set PYTHONPATH=& set UV_PYTHON=3.14.3&& uv run pytest aixcoding/tests -n0` → 全绿（含既有 9 个 auth 测试文件回归）；
2. `uv run python aixcoding/tools/gen_customizations.py` 后 `git diff aixcoding/docs/CUSTOMIZATIONS.md` → 空；
3. launcher 启动 TUI：`~/.chrys/aixcoding.toml` 置 `[logging] panel = true`，`uv run python -m chrys.kernel.aixcoding.diagnostics.launcher` → F6 → "aixcoding" tab 启动即见 `未登录（首次使用或登录已过期）` 或 `已登录（本机保存的登录）`；
4. 查 `~/.chrys/aixcoding-logs/aixcoding.log` 含同样记录（UTF-8 中文正常）；
5. （可选，走一遍登录/登出）：mock server 起服务跑登录流，确认 `登录成功`/`已登出` 记录与 F6 呈现。
