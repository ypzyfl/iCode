# 测试方案：catalog-auto-sync

> 活文档：随时更新、不签认；其质量由双 AI 自审与行为锚定测试本身保障。

## 测试范围与策略

- **单元**：config 解析追加于 `aixcoding/tests/config/test_config.py`；catalog 守卫与归属语义新建
  `aixcoding/tests/catalog/test_auto_sync_gate.py`（复用该目录 conftest 的单例复位与登录桩）。
- **tier 隔离方式**：`monkeypatch` 桩 `catalog_module.load_config` 返回构造快照
  （`environment` + `model_catalog.auto_sync`）——避免读真实 `~/.chrys/aixcoding.toml`，
  同时覆盖 `catalog_tier()` 与 `auto_sync_enabled()` 两个读取点。
- **回归**：`aixcoding/tests/catalog/` 与 `aixcoding/tests/config/` 全目录——既有用例默认
  environment=prod（conftest 清环境变量、无 TOML 文件），auto_sync 开，行为不变。
- 零上游接触，无新增行为锚定测试（ADR-0015 射程外）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口 | 类型 |
|---|---|---|
| 1. 未设置时 local 不同步 | `test_auto_sync_gate.py::test_local_default_disables_blocking_sync`（fetch 不被调）+ `::test_local_default_disables_poll_start` + `::test_resume_after_login_is_blocked` | 单元 |
| 1. 未设置时 dev/prod 照旧 | `::test_dev_prod_defaults_unchanged`（参数化 dev/prod，轮询可启动、blocking 走原路径） | 单元 |
| 2. auto_sync=false 任意 tier 三触发点不执行 | `::test_explicit_false_blocks_any_tier`（参数化 local/dev/prod） | 单元 |
| 2. 无 state 时目录归用户 / 有 state sticky | `::test_catalog_managed_semantics`（矩阵：state 有无 × 开关） | 单元 |
| 3. auto_sync=true local 恢复现状 | `::test_explicit_true_enables_local`（blocking 实际完成一次同步到隔离目录） | 单元 |
| 4. 非法值 warn + 未设置 | `test_config.py::test_auto_sync_invalid_warns_and_falls_back` | 单元 |
| 5. local 未设置且已有 yaml 保留 | 覆盖于 `test_local_default_disables_blocking_sync`（隔离目录预置 yaml，断言原样） | 单元 |
| 6. README 操作说明 | 人工核对两份 README 四块内容（verification 记录） | 人工 |

## 异常与降级路径

- `auto_sync` 非 bool（TOML 字符串/整数）→ warn + None（按未设置）。
- **base_url 非法 + auto_sync 显式 true 组合**（P3）：`test_config.py::test_bad_base_url_does_not_discard_auto_sync`
  ——逐字段降级，auto_sync 不被连坐。
- state 文件损坏 → `read_catalog_state()` 返回 None（现状），按无 state 处理。
- auto_sync 关时 `start_sync_runtime` 仍记录 `_last_wiring`（resume 语义不变，重试仍被同一守卫挡）。

## 手工验证步骤（若需）

1. LOCAL 默认：`AIXCODING_ENVIRONMENT=local` 启动 TUI（不起 mock），预置的
   `~/.chrys/models/*.yaml` 原样保留，模型可加载。
2. LOCAL 恢复同步：TOML 设 `auto_sync = true`，起 mock 并登录，catalog 同步发生（现状路径）。
结果记入 verification.md。
