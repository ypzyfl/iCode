# 测试方案：后端同步模型与自定义模型共存

> 活文档：随时更新、不签认。

## 范围与策略

- 单元/契约测试落在 `aixcoding/tests/catalog/test_catalog_sync.py`，复用既有
  `_wire_disk(monkeypatch, tmp_path)` 夹具（:369）隔离 `catalog_directory()` /
  `catalog_state_path()`。
- 冲突告警只验证 detail 日志（责任人裁决不做 TUI 主动提示，零上游）。
- 不依赖真实网络：全部用 payload 字面量 + 本地临时目录。
- 测试语言：pytest，描述性用例名（项目既有风格）。

## 覆盖矩阵

| 验收点 | 用例（实施后实际名） | 类型 |
|---|---|---|
| 后端写入带 `synced_from_server: true`，loader 不感知 | `test_synced_profile_yaml_carries_marker_and_loader_ignores_it` | 契约 |
| 有标记的旧模型被删除 + 无标记自定义保留（同一场景） | `test_apply_catalog_deletes_only_synced_and_preserves_custom` | 契约 |
| 标记非 true（false/'true'/1/null）一律保留 | `test_non_true_marker_is_treated_as_custom`（×4 参数化） | 边界 |
| ID 冲突：后端覆盖 + detail 日志告警 | `test_conflict_backend_overwrites_and_logs` | 契约 |
| 冲突/保留按文件名 stem 判定（显式 id≠stem 两种失真，F2） | `test_conflict_and_preservation_use_filename_not_explicit_id` | 契约 |
| `profile_ids` 仍只含后端 id、state 内容不变 | `test_state_profile_ids_stay_backend_only` | 契约 |
| 指纹只含后端项、不因自定义变化 | `test_fingerprint_ignores_custom_profiles` | 契约 |
| 快照本身零磁盘 IO（F3） | `test_install_snapshot_stays_in_memory` | 回归 |
| 内存快照含自定义项 | `test_snapshot_includes_preserved_custom_profiles` | 契约 |
| 两阶段发布失败语义保留 | 复用既有 `test_publish_fault_injection_stale_delete_fails` 等 fault-injection 用例（stale 文件已补标记） | 回归 |
| 既有目录同步测试不回归 | `pytest aixcoding/tests/catalog/ aixcoding/tests/mock/ -n0 -q` | 回归 |

> 每条验收标准至少一行；空缺即为覆盖缺口，须说明理由。
> F4：草案期用例名与实际实现有漂移（两用例合并、三处改名、失败语义由既有
> fault-injection 用例承担），本表已按实施后的实际用例名更正。

## 异常与降级

- YAML 损坏 / 标记读取失败：按「无标记=自定义」保守保留，不删；不抛异常阻断
  整次同步（否则一次坏文件会让后端模型全部无法更新）。
- 后端写入失败（tmp → replace 阶段）：沿用既有两阶段失败语义，保留上一版目录，
  不写 state，不发告警（告警只在成功后发）。
- 冲突覆盖告警失败（日志/TUI 通道异常）：不得回滚已完成的同步——告警是
  best-effort，目录与内存发布已完成；测试断言告警失败不影响 result 成功态。

## 手工验证（实施后）

1. 在 `~/.chrys/models/` 放一个无标记的 `my-model.yaml` 并启动 TUI → 列表可见。
2. 触发同步（auto_sync 或手动）→ 自定义文件仍在、TUI 仍可见。
3. 令后端移除某模型 → 同步后该 `<id>.yaml` 消失、自定义仍在。
4. 令自定义 id 与后端某模型同 id → 同步后文件内容为后端版本，detail 日志与
   TUI 各出现一次覆盖告警。
5. 检查 `~/.chrys/models/.catalog-state.json` → 内容与本批前一致，
   `profile_ids` 不含自定义 id。

## 门禁命令

```
uv run pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py aixcoding/tests/mock/test_model_catalog_server.py
uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
uv run python scripts/chrys_test.py --smart --paths <本批改动文件>
uv run ruff check <改动 py> && uv run ruff format --check <改动 py>
uv run ty check --error-on-warning --python-platform linux|darwin|win32 src/chrys
uv run python aixcoding/tools/check_docs.py [--closure]
uv run python aixcoding/tools/check_r2_diff.py --base HEAD
uv run python aixcoding/tools/check_r3_markers.py --base HEAD
uv run python aixcoding/tools/gen_customizations.py --strict
```
