# 验证记录：排队进度提示（model-queue-progress）

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**。

## 2026-11-18 实施验证（部分，按责任人要求先提交）

命令：

```
uv run ruff check <16 个改动文件>
```

结果：`All checks passed!`

命令：

```
uv run ty check --error-on-warning --python-platform win32 src/chrys
```

结果：`All checks passed!`（仅 win32；darwin / linux 未跑）

命令：

```
uv run pytest aixcoding/tests/llm/test_model_queue_progress.py aixcoding/tests/llm/test_model_queue_frames.py -n0 -q
```

结果：`15 passed in 3.54s`（新批次 7 条 + 上一批次 8 条）。

命令：

```
uv run pytest tests/service/llm tests/app/acp tests/orchestration/test_session_host.py -q -n4 -m "not integration and not gc_calibration"
```

结果：`2817 passed, 2 skipped`。首轮曾 `74 failed`，根因两处并已修复：`_assemble_stack` 新参数缺默认值、共享测试替身 `Builds.create_client` 签名固定（见下）。

命令：

```
uv run python aixcoding/tools/gen_customizations.py
```

结果：`check OK — 132 registration row(s) / 193 marker(s) across 21 design(s), 7 retired id(s), 0 warning(s)`。首轮报 8 条 twin-group count mismatch（同文件多处同文本 marker 的预期计数），已按实际计数更新登记表。

命令：

```
uv run python -m tests.support.trajectory_wait_inventory
uv run pytest tests/architecture/test_trajectory_wait_inventory.py::test_wait_manifest_matches_source -n0 -q
```

结果：`2912 waits, 5 reopened`（2 条为新 await：`build_agent._on_queue_status`、`guard_queue_frames:2`；3 条为表达式漂移），刷新后守卫 `1 passed`。所有新节点保持默认规则 `unresolved`（fail-closed）。

命令：

```
uv run python aixcoding/tools/check_docs.py
```

结果：`check_docs: OK`。

**缺陷修复记录（实施中）**：

1. `_assemble_stack(on_queue_status=...)` 首版为无默认值的 keyword-only 参数，上游 74 个直接调用它的测试全部 `TypeError` → 补 `= None`。
2. `builder.py` 对 `create_client` 的传参改为"仅当回调非空"（测试替身签名固定，避免无谓参数）。
3. 共享测试替身 `tests/app/tui/screens/test_prompt_shortcut_send.py::Builds.create_client` 追加 `on_queue_status: Any = None`（+1 行，被 ACP/TUI 多层测试复用）——R2 追加项，已入库 design R2 表。
4. 文案初版使用全角逗号触发 RUF001，改写为中点分隔（避免新增 R13 lint 豁免）。

**本轮未跑（责任人要求先提交，后续继续）**：

- `tests/app/tui`、`tests/app/cli`、`tests/orchestration/engine`（用户取消执行）
- `uv run python scripts/chrys_test.py --smart --paths ...`（完整 Smart Test）
- `ty` 的 darwin / linux 平台
- 真实网关端到端联调（`chrys/queue_status` 在插件端的实际显示）
- `self-review.md`（双 AI 评审，PR 前义务）
