# ADR-0003：mock 统一迁入 `aixcoding/mock/` 专区

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-22
- 确认意见：无特别意见

## 背景

自建 mock（模拟内部后端服务的持久契约测试资产，非临时脚手架）曾有四份、两套机制：

- `mock_server/aixcoding_auth/`、`aixcoding_update/`、`chrys_model_catalog/`——包模式，位于上游 `testpaths = ["tests", "mock_server"]` 收集范围内（经 git 与负责人确认：`mock_server/` 整目录为我们自建，非上游原生）；
- `aixcoding/telemetry-mock/`——无 `__init__.py`，靠 conftest 把目录加入 `sys.path` 后以顶层模块名（`server`/`store`/`faults`）导入。

## 决策

*（本文为决策时点快照；现行规则以 DIRECTORY.md §6 为准。）*

1. 四份 mock 统一迁入 `aixcoding/mock/`，按无前缀服务名命名：`auth/`、`update/`、`model_catalog/`、`telemetry/`。
2. 统一**包模式**：全链路带 `__init__.py`，测试以 `from aixcoding.mock.<name> import server` 导入；`aixcoding/tests/conftest.py` 只做一次"仓库根入 `sys.path`"注入。
3. 契约测试迁 `aixcoding/tests/mock/`，mock 子包只留实现 + README。
4. `mock_server/` 整目录删除，`testpaths` 还原上游原值。
5. 结构强约束沿用原 `mock_server/README.md` 已验证规范：每子包 `server.py` 提供 `create_server(...)`（factory，测试进程内驱动）+ `main()`（CLI，独立进程起服务）双入口；loopback-only、stdlib-only、不 import 产品包、wire quirks 逐字节复刻、测试直连避开系统代理。

## 理由

1. **资产归属判据是"谁建谁维护"**：`model_catalog` 模拟的后端主要服务上游的模型目录功能，但它是我们建的测试资产，照样进专区；上游若自建 mock 体系，随升级自然落在上游位置，与我们无关。
2. **顶层模块名注入模式不可扩展**：多 mock 合并后必有多个 `server.py`，`sys.path` 多目录注入按顺序命中——撞名且脆弱。
3. **消除"看似上游目录、实为定制资产"的甄别陷阱**：`mock_server/` 删除后 `pyproject.toml` 的 `testpaths` 还原上游原值，**R2 定制点 -1**。
4. **契约测试随定制测试独立收集**（与 ADR-0001 同构）：不再依赖 `testpaths` 默认收集。

## 否决的备选

- **维持 `mock_server/` 注册表模式**：其 README 与组织规范质量不错（已平移承接为 `aixcoding/mock/README.md` 的规范来源），但目录位置在上游收集射程内，继续维护等于保留一个假上游目录。
- **契约测试留在 mock 子包内（自包含模式）**：被否决——维持"测试唯一落点 = `aixcoding/tests`"的规则纯粹性，人和 AI 不用记"mock 里也藏测试"；`chrys_model_catalog/conftest.py` 的 `direct_route` fixture 随契约测试迁移。

## 后果

- `telemetry-mock` 迁移时需补 `__init__.py` 与 `main()` CLI 入口（对齐双入口约定），conftest 的旧注入逻辑改为包导入；
- ruff per-file-ignores 的 `"mock_server/**/test_*.py"` 条目改为 `"aixcoding/tests/**"`（与上游 `tests/**` 同款 S/PERF401 豁免）。
