# 验证：auth 测试隔离 + mock 动态端口（auth-isolation-mock-ports）

> 追加不删旧。环境：Windows 本机（7778 被 ArmouryCrate 占用的原始红环境），
> 配方 = 大写盘符进仓库 + `PYTHONPATH=`（清空）+ `PYTHONUTF8=1`。日期：2026-11-01。

## V1（批次完成验证）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run ruff check aixcoding/` | All checks passed |
| 2 | `uv run ruff format --check aixcoding/` | 183 files already formatted |
| 3 | `uv run pytest aixcoding/tests/mock/test_mock_launcher.py aixcoding/tests/auth -q -m "not integration and not gc_calibration"` | **119 passed in 6.31s** |
| 4 | `uv run pytest aixcoding/tests -q -m "not integration and not gc_calibration"` | **324 passed, 2 skipped in 11.09s** |

验收点核销：

- **R-04（动态端口）**：V1#3/#4 在 7778 被占用的原红环境下 `test_mock_launcher` 全绿——
  `port=0` 起停 round-trip 不再依赖固定开发端口；CLI 路径默认端口与 fail-fast 语义零变化
  （`_SERVICES` 表与 `main()` 未动）；
- **R-03（auth 隔离）**：新增窄域 autouse（`_isolated_default_construction`）+ 防退化锚点
  （`test_default_construction_is_isolated_by_conftest`，断言默认构造走 `MemoryBackend`）
  后 auth 全目录绿——两个默认构造测试（singleton / delegation 环境检测）意图不变、
  自动受保护；真实平台后端测试（直接构造 backend 类）零交集不受影响；
- 2 个 skip 为 catalog consumer 未迁移的已知 auto-skip（consumer 迁移批次落地自动 unskip，
  与 R-05 基线清单口径一致）；
- 附带证据：全量定制套件本机 11.09s——P0 "无条件双跑多花 <1 分钟" 的代价论证再次实证。

## V2（第三轮复审 S-01/S-04 收尾修复，2026-11-01）

外部 AI 第三轮复审独立复跑与 V1 一致（324 passed / 2 skipped / 11.79s），提出 S-01~S-04
收尾 findings，处置：

| Finding | 处置 | 复验 |
|---|---|---|
| S-01（major）launcher 测试硬编码三 starter → 未来新服务（telemetry）不自动纳入 round-trip | 恢复遍历 `launcher._SERVICES.values()`，starter 调 `starter(port=0)`——注册表语义回归 + 零固定端口依赖并存 | 下行 V2#2 |
| S-04（minor）防退化锚点只断言 backend，docstring 却声称 config-dir 同锁 | 锚点补 `auth_session.default_config_dir() == tmp_path` 断言（pytest 同测试内 fixture 实例共享，断言的正是 autouse patch 的目标） | 下行 V2#2 |
| S-02（minor）loopback 请求捕获能力不足 | 修订 temp 20 号材料：组合测试批次 test-plan 硬性要求（进程内结构化请求快照、原始 token 不入持久日志、会话同一性断言） | 文档 |
| S-03（minor）文档状态滞后 | requirements 开放问题 7778 项标已核销、plan 前置依赖标完成、overview 复审状态更新 | 文档 |

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run ruff check aixcoding/` | All checks passed |
| 2 | `uv run pytest aixcoding/tests/mock/test_mock_launcher.py aixcoding/tests/auth -q -m "not integration and not gc_calibration"` | **119 passed in 4.80s** |
| 3 | `uv run pytest aixcoding/tests -q -m "not integration and not gc_calibration"` | **324 passed, 2 skipped in 10.63s** |

## V3（第四轮评审 T-01 类型声明修复，2026-11-01）

评审发现 `_Services` 零参类型声明与测试 `starter(port=0)` 不符（ty `unknown-argument`，
pytest 不覆盖类型面）。修复：`Callable[[], ...]]` → `Callable[..., ...]]` + 双调用形态
注释；同批补 `INDEX.md` 登记义务（本批 + local-verify 各一行，DEVELOPMENT.md §6）。

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run ty check aixcoding/tests/mock/test_mock_launcher.py aixcoding/mock/__main__.py` | `unknown-argument` 消除（仅剩 1 个存量动态属性诊断 `__main__.py:67 server.mock_config`，为 mock 批次既有模式，非本批引入；ty 门规范口径不查 aixcoding/，DIRECTORY.md §7） |
| 2 | `uv run ruff check aixcoding/` | All checks passed |
| 3 | `uv run pytest aixcoding/tests/mock/test_mock_launcher.py aixcoding/tests/auth -q -m "not integration and not gc_calibration"` | **119 passed in 5.45s** |
| 4 | `uv run pytest aixcoding/tests -q -m "not integration and not gc_calibration"`（T-01 后全量终态确认，责任人质询后补跑；类型注解零运行时语义，结果与 V2 一致） | **324 passed, 2 skipped in 10.88s** |
| 5 | 责任人指出模块 docstring 未反映端口参数化形态（`:9-12` 仍只写 7777/7778）：docstring 补一句双形态说明（CLI 默认固定端口契约 / starter 带 `port` 参数、测试用 `port=0`）；复验 `ruff check` + `ruff format --check`（单文件）+ launcher 测试 | **6 passed in 2.44s** |
