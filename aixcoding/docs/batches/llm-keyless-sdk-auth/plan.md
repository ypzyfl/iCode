# 任务清单：无凭证 OpenAI 客户端跳过 Authorization 头校验（llm-keyless-sdk-auth）

## 状态

实施完成，待责任人签认 design 与 self-review 后提 PR。

## 待办

- [x] 方案 A（构造期 `default_headers` 放 `Omit`）实施与证伪（`_merge_mappings` 删除 Omit 值）
- [x] 方案 C（定制子类 + `clients.py` 接线）实施与证伪（上游 20 条 factory 测试 patch 点失效）
- [x] 方案 D 实施：`sdk_openai.py` 追加 `_validate_headers` 覆写 + R3 标记
- [x] 定制测试落位 `aixcoding/tests/llm/test_sdk_auth.py`（R4）
- [x] 验证：定制测试 2 条 + 上游 LLM 层 2098 条 + ruff + import 边界
- [x] 批次文档六件套
- [ ] 责任人签认 design.md（R10，本人编辑，AI 不得代填）
- [ ] 责任人签认 self-review.md
- [ ] PR + peer review（评审模板精简版：缺陷模式抽查 + 验证输出必看）

## 挂起与备忘

- 方案 B（wire 层登录 token 兼任 `Authorization: Bearer` + per-request `Omit`）完整实现曾落地并全测通过（2239 条），按"最小改动"决策移除；补丁留档 `/tmp/auth_changes_full_backup.patch`（274 行），需求出现时另行立项。归属：责任人。
- 方案 C 的定制子类代码已删除（`src/chrys/service/aixcoding/llm/` 移除），其决策过程记录于 design 备选表。
