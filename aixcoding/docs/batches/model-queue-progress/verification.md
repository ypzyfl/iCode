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
2. `builder.py` 对 `create_client` 的传参曾改为"仅当回调非空"以绕开签名固定的测试替身；该写法触发三平台 `ty` 的 `invalid-argument-type`（字典展开推断不出参数名），**已回退为无条件传参**，改由替身 `Builds.create_client` 接受参数。
3. 共享测试替身 `tests/app/tui/screens/test_prompt_shortcut_send.py::Builds.create_client` 追加 `on_queue_status: Any = None`（+1 行，被 ACP/TUI 多层测试复用）——R2 追加项，已入库 design R2 表。
4. 文案初版使用全角逗号触发 RUF001，改写为中点分隔（避免新增 R13 lint 豁免）。

## 2026-11-18 实现评审修复与全量补跑

独立实现评审（子代理）发现 2 个 blocker 与若干建议，处置后补跑。

**blocker 1 — 同轮内文案不释放**：guard 此前只上报位置帧，放行后无信号，`WaitingRow` 在本轮后续每次等待都会带"排队中"。修复：`queue_frames.py` 在首个数据块时上报 `RELEASED_POSITION = -1`（仅当此前吸收过排队帧），三个前端各自消费。

**blocker 2 — ACP 去重跨会话串号**：`_last_queue_position` 原为单值且无轮次重置。修复：改为 `dict[session_id, position]`，放行时删条目，`ext_notification` 成功后才记录。

其余处置：`query_one(WaitingRow)` → `_waiting_row()` 遍历查询（chrome 重建窗口不再抛 `NoMatches`）；CLI 新增 `TurnStarted` 清零；TUI 放行路径补 `_predates_active_run`；`queue_progress.py` docstring 修正（ACP 只透传位置）。

命令：

```
uv run pytest aixcoding/tests/llm -n0 -q
```

结果：`19 passed`（新增放行上报、无排队不上报放行、CLI 放行重置三条）。

命令：

```
uv run pytest tests/app/tui/screens tests/app/tui/widgets/chat -q -n4
```

结果：`4194 passed, 55 skipped`。

命令：

```
uv run pytest tests/app/acp tests/app/cli -q -n4
```

结果：`1302 passed, 44 skipped`。

命令：

```
uv run pytest tests/app/cli tests/orchestration/engine -q -n4
```

结果：`2020 passed, 55 skipped`。

命令：

```
uv run pytest tests/app/tui -q -n4
```

结果：`13358 passed, 2 failed, 85 skipped`。2 条失败均为 `tests/app/tui/widgets/test_file_scanner.py` 的 `..._real_nul_file` 用例：本机 Windows 无法创建名为 `nul` 的设备名文件（`OSError Errno 123`），单独复跑 0.58s 稳定复现，且该文件与其被测模块 `src/chrys/app/tui/widgets/` 本轮零改动 → 环境限制，非本批次引入。

命令：

```
uv run ty check --error-on-warning --python-platform {win32,darwin,linux} src/chrys
```

结果：三平台均 `All checks passed!`。

命令：

```
uv run python -m tests.support.trajectory_wait_inventory
uv run python aixcoding/tools/gen_customizations.py
```

结果：wait 清单 5 条 reopened（含 `_on_queue_status` 与 `guard_queue_frames:2` 两个新 await，规则 `unresolved`）已刷新；对账 `check OK`。

**仍未完成**：

- `uv run python scripts/chrys_test.py --smart --paths ...`（完整 Smart Test；已用更宽的目录集替代：tui / cli / engine / acp / service.llm / session_host / architecture 守卫）
- 真实网关端到端联调（TUI 文案、CLI 去重行、ACP `chrys/queue_status` 的实际显示）

## 2026-11-19 展示 queueSize

需求侧关闭开放问题：`queueSize` 从"待联调确认"改为必须展示。

改动：`queue_note(position, queue_size=0)` 追加「共 M 个」（`queue_size <= 0` 时省略）；TUI 链路 `ports` / `main_screen_presenter` / `view_adapter` / `event_handlers` 与 CLI `TurnProgress` 透传 `event.queue_size`；ACP payload 原本已带 `queueSize`，未改。

最长文案：「排队中 · 前方 9 个请求 · 共 12 个 · 可稍后重试」（约 26 字），80 列终端可容纳。

命令：

```
uv run pytest aixcoding/tests/llm -n0 -q
```

结果：`20 passed`（新增 `test_queue_note_reports_the_queue_size`）。

命令：

```
uv run ruff check <改动文件>
uv run ty check --error-on-warning --python-platform {win32,darwin,linux} src/chrys
uv run pytest tests/app/cli tests/app/acp -q -n4
uv run python aixcoding/tools/gen_customizations.py
uv run python aixcoding/tools/check_docs.py
```

结果：ruff `All checks passed!`；三平台 ty 均通过；`1302 passed, 44 skipped`；对账 `check OK — 133 row(s) / 196 marker(s)`；`check_docs: OK`。

**本轮未跑**：`tests/app/tui` 全量（新签名只是给已有方法加默认参数，向后兼容；上一轮该套件 `4194 passed`）。

## 2026-11-19 文案调整：改为「当前模型请求量大…」

- 变更：`queue_note` 排队文案由「排队中 · 前方 N 个请求 · 共 M 个」改为
  「当前模型请求量大，请求排队约 N 人，请稍候或切换至其他模型」；`position 0` 仍为「正在获取模型资源」。
  `queueSize` 不再进文案（事件载荷与 ACP `queueSize` 字段不变），**推翻同日「展示 queueSize」的决定**，requirements 已同步。
- 全角逗号触发 `RUF001`，采用行级 `# noqa: RUF001`（owner 指定文案，理由写在该行注释与文件 docstring）。
- 测试：`test_queue_note_branches` 改为断言「约 N 人」与操作建议；`test_queue_note_does_not_show_the_queue_size`
  断言总数不再渲染（`queue_note(2, 5) == queue_note(2)`）。

实跑（mock scripted 网关，真实 CLI）：

```text
uv run aixcoding-cli run "你好" -a Code -m QueueMock -C <mock 目录>
• Code Agent ready · QueueMock · session …
• 当前模型请求量大，请求排队约 3 人，请稍候或切换至其他模型
• 当前模型请求量大，请求排队约 2 人，请稍候或切换至其他模型
• 当前模型请求量大，请求排队约 1 人，请稍候或切换至其他模型
• 正在获取模型资源
✓ Done · 6.1s · 0 tool calls
```

门禁：`aixcoding/tests/llm` 49 passed、`ruff check` / `format` 通过、`ty`（win32）通过、`check_docs --closure` OK。
**局限**：TUI 未截图（文案与 CLI 同源 `queue_note`，只用同一套单元断言；WaitingRow 单行渲染不因文案变化改高度）。
