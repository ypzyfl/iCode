# 计划：auth 测试隔离 + mock 动态端口（auth-isolation-mock-ports）

> 活文档。**微改动豁免批次**（DEVELOPMENT.md §6 三条件核对：零上游文件 ✓ / 不触发 ADR ✓ /
> 定制目录内约 50 行 ✓；2026-11-01 责任人裁决：豁免 + 合并一个批次）。
> 来源：定制测试策略复审 R-03（裁决选 A：窄 auth 防呆前置）/ R-04（裁决选动态空闲端口方案）；
> 讨论材料 `fork 仓外 temp/2026-11-01-custom-test-strategy/`（00 号 §六/§七、30 号预案）。
> 两件事同源：消除 P0（local-verify）无条件双跑对既有副作用的频率放大。

## 任务

| # | 任务 | 状态 |
|---|---|---|
| 1 | auth 隔离：`aixcoding/tests/auth/conftest.py` 新增窄域 autouse（默认 `LoginSession()` 构造钉 `tmp_path` + `MemoryBackend`；豁免 marker `real_platform_backend` 本地注册，沿用 `allow_delegation_detect` 先例模式）+ `test_auth_session.py` 防退化锚点测试 | 完成 |
| 2 | launcher 动态端口：`aixcoding/mock/__main__.py` 三个 `_start_*` 参数化（默认端口不变，CLI 联调路径与 fail-fast 语义零变化——server 工厂原生支持 `port=0`，docstring 自注 "used by tests"）；`test_mock_launcher.py` round-trip 改 `port=0` + 从 origin 解析实际端口 | 完成 |
| 3 | 验证：ruff + 全量定制套件（本机 7778 被占场景下 `test_mock_launcher` 转绿为 R-04 验收点） | 完成（见 verification.md） |

## 明确不做（R8 留痕）

- 不改三个 server 工厂实现（`port=0` 支持已存在）；
- 不给 `test_auth_crypto.py` 的真实平台后端测试加豁免 marker（它们直接构造平台 backend，
  不经过被 patch 的 `_default_backend` 默认路径，零交集）；
- macOS 产品侧探测项清理（`get_backend()` 写 Keychain 无删除）是产品代码改动（R2 报批项），
  独立待办另行裁决，不入本批。
