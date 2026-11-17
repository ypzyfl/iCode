# 测试方案：后端同步模型与自定义模型共存

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

- 层级：契约测试为主（同步链路真实读写 `tmp_path` 目录），落点
  `aixcoding/tests/catalog/test_catalog_sync.py`（既有文件追加）。
- 锚点行为锚定：`install_snapshot` 的字典后者胜出语义走**真实
  `_publish`** 断言（禁 mock 锚点本身）；`load_profile_from_yaml` /
  `read_profile_mapping` 直调真函数。
- 故障注入沿用本文件既有 fault-injection 模式（monkeypatch 抛 `OSError`）。
- mock 契约测试（`aixcoding/tests/catalog/` 既有套件）保持全绿，覆盖
  auto-sync 门禁与只读门禁不回归。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（test_catalog_sync.py::用例） | 类型 |
|---|---|---|
| 写盘 YAML 含标记；loader 不感知 | `test_synced_profile_yaml_carries_marker_and_loader_ignores_it` | 契约 |
| 只删有标记且不在后端列表；无标记保留 | `test_apply_catalog_deletes_only_synced_and_preserves_custom` | 契约 |
| 非 `true` 标记一律按自定义 | `test_non_true_marker_is_treated_as_custom`（参数化） | 契约 |
| 畸形 YAML 不中断同步 | `test_malformed_yaml_does_not_abort_sync` | 契约 |
| ID 冲突后端覆盖 + detail 告警 | `test_conflict_backend_overwrites_and_logs` | 契约 |
| 冲突/保留按完整文件名而非显式 id | `test_conflict_and_preservation_use_filename_not_explicit_id`（两形态参数化） | 契约 |
| state 内容不变、不作来源判定 | `test_state_profile_ids_stay_backend_only` | 契约 |
| 指纹只含后端项 | `test_fingerprint_ignores_custom_profiles` | 契约 |
| 快照零磁盘 IO | `test_install_snapshot_stays_in_memory`（写陷阱） | 行为锚定 |
| 内存快照保留项按 server_ids 过滤 | `test_snapshot_id_collision_keeps_backend_item_in_memory`（真实 `_publish`） | 行为锚定 |
| 快照含保留的自定义项 | `test_snapshot_includes_preserved_custom_profiles` | 行为锚定 |
| 全无标记目录一次性清空 + 计数 | `test_upgrade_clears_unmarked_directory_once`（精确子串断言） | 契约 |
| 空目录不触发清空 | `test_empty_directory_is_not_treated_as_upgrade` | 契约 |
| 全畸形目录不触发清空 | `test_all_malformed_directory_is_not_cleared` | 契约 |
| 发布失败时旧文件原样保留 | `test_upgrade_publish_failure_preserves_old_files`（fault-injection） | 契约 |

## 异常与降级路径

- 探针 `None`（`except Exception` 兜底）→ 保留 + 不触发清空：
  上表 `test_malformed_yaml_does_not_abort_sync` / `test_all_malformed_directory_is_not_cleared`。
- 非 vacuous 证明（关键 guard「改坏哪行会红」）：
  - 删 `_publish` 的 `server_ids` 过滤 → `test_snapshot_id_collision_keeps_backend_item_in_memory` 红。
  - 把探针 `except Exception` 收窄回窄 `except` → `test_malformed_yaml_does_not_abort_sync` 红。
  - 把升级清空移回 staging 前 → `test_upgrade_publish_failure_preserves_old_files` 红。
  - 删 `marker_probe_failed` guard → `test_all_malformed_directory_is_not_cleared` 红。
- 失败语义由既有 fault-injection 用例承担（stage-one write / mkdir / replace /
  state write / stale delete），不重复建设。

## 手工验证步骤（若需）

- 端到端以契约测试覆盖（mock server 目录 + 真实读写）；无独立手工步骤。
  本地遗留坏文件 `~/.chrys/models/openai-gpt-4o-mini2.yaml` 可作观察样本：
  修复后按自定义保留、不再中断同步（不删除用户数据，未经责任人授权）。
