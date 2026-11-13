# 验证记录：企业埋点上报日志

## 2026-11-13 方案核对

- 现有独立上报的三个端点均经过 `TelemetryDelivery._send`，具备统一采集落点。
- `LogViewerScreen` 普通日志显示行上限 2048 字符，缓冲单行上限 16 KiB；现有普通日志管道无法满足完整查看和复制。
- 已从安装的 httpcore 源码核对 HTTP/1.1 响应含 `network_stream`，AnyIO 后端的 `server_addr` 来自连接的远端地址。
- `UV_CACHE_DIR=/tmp/icode-telemetry-logging-uv uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_docs.py` 退出 0，`check_docs: OK`。默认 uv 缓存目录不可写，使用临时缓存目录后完成检查。使用现有 `.venv`，uv 提示与项目要求 Python 3.14.10 不符。
- 本阶段仅核对源码并准备签认材料，实施验证待签认后运行。

## 2026-11-13 实施验证

实际运行环境为现有 `.venv` 的 Python 3.14.8。项目要求 3.14.10，以下 uv 命令均提示版本不符并继续使用现有环境。

```sh
export UV_CACHE_DIR=/tmp/icode-telemetry-logging-uv
AIXCODING_EXTENSION_BASE_URL=https://telemetry.invalid uv run --offline --no-sync --no-python-downloads pytest -n0 --tb=short aixcoding/tests/telemetry aixcoding/tests/diagnostics tests/app/tui/screens/test_log_viewer.py tests/architecture/test_layering.py tests/architecture/test_trajectory_wait_inventory.py
uv run --offline --no-sync --no-python-downloads ty check --error-on-warning --python-platform darwin src/chrys
uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_r2_diff.py --base HEAD
uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_r3_markers.py --base HEAD
uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_docs.py
uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_docs.py --closure
uv run --offline --no-sync --no-python-downloads python aixcoding/tools/gen_customizations.py --strict
git diff --check
```

- 最终定向回归退出 0，417 项通过。新增 5 项覆盖三个接口的实际发出请求与文件逐字段对拍、HTTP 503/连接失败、默认关闭、F6 长报文查看和复制、连接关闭前采集对端地址，以及诊断异常不影响发送统计。测试使用合成报文和传输替身。
- Ruff check、Ruff format --check（本批五个 Python 文件）、macOS ty、R2、R3、普通文档检查及空白检查均退出 0。R2 识别到唯一上游变更为 `logs/screen.py`，+5/−0。等待清单 57 项通过，无清单差异。
- 原生定制点严格检查退出 1，报告历史 `.codebuddy/worktrees/bg-01a1c9d3/` 的 28 条既有扫描干扰。使用同一匹配器单独对账主工作区，159 登记 / 200 marker，退出 0。未修改工具或旧工作树。
- 回环 HTTP 探针在绑定 `127.0.0.1:0` 时收到沙箱 `PermissionError`，退出 1，真实套接字地址未在当前环境验收。保留 HTTPX 响应钩子与短连接时序回归。
- 独立评审发现诊断异常缺少降级记录，修复并经增量复审关闭。详见 self-review.md。未访问生产。
- 评审记录归档后，普通文档检查退出 0，`--closure` 退出 1，唯一问题为 `self-review.md` 尚待责任人签认。

## 2026-11-13 CodeBuddy 代码审阅

- 审阅范围：分支 `feat/aixcoding-telemetry-logging` 上「首批埋点日志」未提交改动。会话 `01a1d2ad`，模型 Kimi-K3.1-Pro，时间 10:12:53–10:22:38（上海时间）。
- 结论：未发现阻断缺陷。本轮未改文件、未提交、未连生产端点。
- 相关遥测、F6 和架构回归 388 项通过。Ruff check、Ruff format check、ty 通过。`git diff --check HEAD` 通过。
- 本机回环实测通过：记下了 `127.0.0.1` 和动态端口，载荷完整，认证 token 未进入日志。此前实施验证中沙箱绑定 `127.0.0.1:0` 失败的记录仍保留在上一节，未改写。
- 实际运行环境仍为现有 `.venv` 的 Python 3.14.8，项目要求 3.14.10，uv 提示版本不符。
- `self-review.md` 状态为「已确认」但责任人为空，本轮未改签认字段。文档闭环仍须待责任人签认。
