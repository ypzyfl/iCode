# 计划：catalog-auto-sync

状态：**已合并**（PR #114，merge commit `d52626f1`，2026-11-11；特性分支 `feat/catalog-auto-sync`）。
Smart Test 按责任人指示暂时跳过（2026-11-11）；该验证面已由后续 upstream-merge-v0.35.2
批次的 fork-full 全量覆盖（时序在本批合并之后），无残留验证债。

## 任务清单

- [x] 方案讨论与形态收敛（三态 `auto_sync` 键 + tier 默认分叉 + 零上游改动；2026-11-11 对话确认）
- [x] design.md 责任人签认（周彬，2026-11-11）
- [x] test-plan.md（覆盖 requirements 验收标准逐条 + 降级路径，含 base_url 非法 + auto_sync=true 组合）
- [x] 实施：
  - [x] `src/chrys/service/aixcoding/config/types.py`：`ModelCatalogConfig.auto_sync: bool | None = None`
  - [x] `src/chrys/service/aixcoding/config/loader.py`：auto_sync 解析（非 bool warn + None）；逐字段独立降级
  - [x] `src/chrys/service/aixcoding/models/catalog.py`：`auto_sync_enabled()` + 两入口守卫 + `is_catalog_managed()` 归属联动 + 模块头 docstring 更新
  - [x] 测试：`test_auto_sync_gate.py` 新建 + `test_config.py` 追加 4 例；conftest 固定 prod 快照隔离真实本机配置（18 失败根因修复，见 verification.md）
  - [x] 文档：`mock/model_catalog/README.md` 自管操作说明四块 + 总 `mock/README.md` 一句与指针
- [x] 验证落盘 verification.md（110 passed；ruff；双规范校验；Smart Test 跳过注明）
- [x] 双 AI 评审（文档轮 P1-P4 + 实施轮 ①-④ + 增量复审）→ self-review.md 已签认 → closure 全绿
- [x] 提交：特性分支 + PR（逐步授权）→ 已推送、建 PR #114 并合并（merge commit `d52626f1`，2026-11-11）

## 续接入口

先读本目录 requirements.md / design.md；上游接线现状见 catalog-sync 批次 design（C034 等登记点）。
