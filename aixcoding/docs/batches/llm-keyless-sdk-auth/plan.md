# 任务清单：无凭证 OpenAI 客户端跳过 Authorization 头校验（llm-keyless-sdk-auth）

## 状态

实施与签认完成（2026-11-10）；peer review request changes 已全部处置（见挂起与备忘），待推送 PR。

## 待办

- [x] 方案 A（构造期 `default_headers` 放 `Omit`）实施与证伪（`_merge_mappings` 删除 Omit 值）
- [x] 方案 C（定制子类 + `clients.py` 接线）实施与证伪（上游 20 条 factory 测试 patch 点失效）
- [x] 方案 D 实施：`sdk_openai.py` 追加 `_validate_headers` 覆写 + R3 标记
- [x] 定制测试落位 `aixcoding/tests/llm/test_sdk_auth.py`（R4）
- [x] 验证：定制测试 2 条 + 上游 LLM 层 2098 条 + ruff + import 边界
- [x] 批次文档六件套
- [x] 责任人签认 design.md（R10，2026-11-10）
- [x] 责任人签认 self-review.md（2026-11-10）
- [x] peer review finding-A：登记改号 C145 → C153（并行批次 logo-branding 已占 C145-C152）
- [x] peer review finding-B：提交补规范 body（动机/改动/验证）
- [x] peer review finding-C：本状态节同步
- [x] peer review finding-D：verification.md 补 `--strict` 对账记录
- [ ] PR + peer review 终审（复核 finding 处置）

## 挂起与备忘

- 方案 B（wire 层登录 token 兼任 `Authorization: Bearer` + per-request `Omit`）完整实现曾落地并全测通过（2239 条），按"最小改动"决策移除；补丁留档 `/tmp/auth_changes_full_backup.patch`（274 行），需求出现时另行立项。归属：责任人。
- 方案 C 的定制子类代码已删除（`src/chrys/service/aixcoding/llm/` 移除），其决策过程记录于 design 备选表。
