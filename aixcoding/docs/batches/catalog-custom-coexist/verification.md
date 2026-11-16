# 验证记录：后端同步模型与自定义模型共存

> 活文档：每次验证追加一节，不删旧记录；不签认。

## 起草前只读核查（未实施，2026-11-16）

以下事实在起草 design 前实读源码确认，供后续实施对照：

- **删除根源**：`apply_catalog()` 在 `catalog.py:783-787` 按 `final_names` 删除
  目录里所有不在后端列表的 `*.yaml` / `*.yml`，无来源区分。
- **state 写出**：`write_catalog_state()`（:276-286）在两阶段发布最后一步写
  `.catalog-state.json`，含 `version` / `source` / `profile_ids` /
  `default_profile_id`；`profile_ids` 只来自 `catalog.profile_ids()`（后端项）。
- **指纹语义**：`_coerce_version()` docstring（:334-336）明写「指纹是记录，
  不是跳过机制」；hash 只含 `catalog.items`。同步每次全量重写，无 skip 分支。
- **loader 容忍未知键**：`_parse_profile()`（`loader.py:245-267`）用
  `data.get(...)` 逐字段构造 `ModelProfile`；`read_profile_mapping()` 只要求
  顶层是 mapping，不校验键白名单 → 模型 YAML 加 `synced_from_server` 不需改上游。
- **内存快照**：`_publish()`（:1069）`registry.install_snapshot(catalog.items)`
  只装后端项；`install_snapshot()`（:143-146）是纯内存替换、锁内零磁盘 IO。
- **写盘挂点**：`_write_profile()`（:765-782）用 `dump_yaml(_result_to_dict(profile))`
  落盘，是注入标记字段的唯一点；`os.replace` 保留 `api_key` 的 600 权限。
- **TUI 提示挂点（已裁决不做）**：`_refresh_model_ui(_result)`
  （`app.py:1557-1560`）虽已接收 `CatalogSyncResult` 但未使用；Textual
  `notify()` 是实例方法、`active_app` 是主线程 ContextVar、EventBus 无全局
  单例，业务层无法直接发 toast。责任人裁决先不改源码：告警仅进 detail 日志，
  **零上游改动**，R2 清单空、无 R3 marker。
- **本机 state 实例**：`~/.chrys/models/.catalog-state.json` 实际存在，
  `profile_ids: ["openai-gpt-4o-mini"]`，`source: remote`；同目录
  `openai-gpt-4o-mini.yaml` 含上一批映射的 `max_output_tokens: 16000` /
  `verify_ssl: false` / `vision: true`，证明前批改动已在本机生效。

## 签认前状态申报（如实）

`check_docs.py --closure` 预期因本批 `design.md` / `self-review.md` 状态为
「草案」而报 `draft decision/review document is forbidden by closure`。
这是完整管线的正常中间态，**不是缺陷**，不得由 AI 代填签认绕过。
默认模式 `check_docs.py` 应通过。责任人签认两处后 closure 转绿。

实施与门禁证据在签认后按 R7 追加。

## 2026-11-16 实施与门禁全集（design.md 签认后）

前置：`design.md` 由责任人本人签认（施利利 / 已确认 / 2026-11-16）后按
DEVELOPMENT.md §4.1 实施；签认头部复核未变，正文未改，不触发重签。

### 实施范围

`git diff --stat`（tracked）：2 files changed, 206 insertions(+), 11 deletions(-)，
另批次文档六件套（untracked）。**零上游文件**（R2/R3 实测确认）。

| 文件 | 改动 |
|---|---|
| `src/chrys/service/aixcoding/models/catalog.py` | `_SYNCED_FROM_SERVER_KEY` 常量；`_write_profile` 注入标记；`_is_server_synced` / `_server_owned_names` / `_load_custom_profiles` 三个只读 helper；`CatalogSyncResult` 加 `preserved_profiles` / `overwritten_custom_ids`；`apply_catalog` 写盘前分类、只删带标记旧文件、成功日志报保留数、覆盖告警；`_publish` 快照 = 后端项 + 保留自定义项 |
| `aixcoding/tests/catalog/test_catalog_sync.py` | 新增 9 个用例函数（收集 12 例：8 个单用例 + 非真值标记 ×4 参数化）——标记写入/loader 忽略、删除与保留、非真值、冲突覆盖+告警、F2 stem 判据（显式 id≠stem 两种失真）、state 仍只含后端、指纹不受自定义影响、F3 快照零磁盘 IO、快照含自定义；既有删除失败用例的 stale 文件补标记以维持原语义（F4：原「9 用例」措辞已按最终态更正） |

既有语义保持：两阶段发布顺序、state 写入内容与 `profile_ids` 口径、指纹
`_coerce_version`（只 hash 后端项）、TUI 只读门禁、请求/响应 detail 日志——
均未改。

### 测试

```
uv run pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py  → 78 passed
    （基线 66 + 本批 12 收集：9 函数，其中非真值 ×4；F2/F3 增量补入后由 76 → 78）
uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
    → 821 passed, 47 skipped in 27.48s
uv run python scripts/chrys_test.py --smart --paths <本批 2 个改动文件>
    → Summary: PASSED (exit 0)
      tests         13812 passed, 17 skipped (exit 0)
      architecture  323 passed (exit 0)
```

- `pytest` 全定制套件 47 skipped 为既有 skip（含 2 个 import 失效的 consumer
  契约测试），本批零触碰。
- Smart Test 是本地定向优化，不等于 CI 全套通过。

### 静态检查与治理门禁

```
uv run ruff check <2 个改动 py>          → All checks passed!
uv run ruff format --check <2 个改动 py> → 2 files already formatted（首次 format 修正后）
uv run ty check --error-on-warning --python-platform linux|darwin|win32 src/chrys
    → 三平台均 All checks passed!
uv run python aixcoding/tools/check_docs.py           → OK（27 ADR / 46 design / 45 self-review）
uv run python aixcoding/tools/check_docs.py --closure  → FAILED with 1 error(s)
    （仅 self-review.md 草案，待双 AI 自审 + 责任人签认）
uv run python aixcoding/tools/gen_customizations.py --strict
    → OK — 116 rows / 161 markers / 0 warning
uv run python aixcoding/tools/check_r2_diff.py --base HEAD
    → changed=8 upstream_changed=0 approved_pool=104 → OK
uv run python aixcoding/tools/check_r3_markers.py --base HEAD
    → upstream_changed=0 marker_checked=0 exempt=3 → OK
read_lints（2 个改动 py）                             → 0 diagnostics
```

- `--closure` 唯一错误：`aixcoding/docs/batches/catalog-custom-coexist/self-review.md: draft ...
  forbidden by closure`；属合并前正常中间态，不得由 AI 代填签认。
- `upstream_changed=0` 印证标记逻辑全在定制包 `src/chrys/service/aixcoding/`
  内，R2 清单空、无 R3 marker、零新增 R13 豁免、零第三方依赖。

### 与 design 假设的偏差（如实记录）

- design「升级一次性告警」场景按实现落地：旧版无标记 YAML 首同步按自定义
  处理；若 id 与后端相同则覆盖 + detail 告警。已由冲突用例覆盖。
- 非真值标记（false/字符串/数字/null）一律按自定义保留，未误删——参数化
  用例钉死；design 的保守口径成立。
- 冲突覆盖告警在**全部写盘与 state 成功后**发出（失败路径不发），符合
  design「完成后告警」。

### 未执行项（如实）

- 双 AI 自审、责任人签认 `self-review.md`、按授权提交 / 建 PR 均未进行。
- 未做端到端人工验证（本机启 mock + TUI 放自定义模型观察保留/覆盖），
  本批以契约测试 + 内存快照用例覆盖闭环。

## 2026-11-16 双 AI 自审与 findings 收敛（增量复审）

评审 AI：GLM-5.3-Flash（责任人指定的独立第二 AI，与开发 AI
CodeBuddy / Tencent Hunyuan Hy 不同源）。评审结论 **0 blocker /
3 suggestion（F1 流程、F2 边界、F3 覆盖缺口）/ 3 nit（F4–F6）**。
责任人逐条拍板「按评审建议打包」：F1 留知情确认意见、F2 改代码、F3 补用例、
F4 同步文档、F5 不修（formatter 口径）、F6 不修留档。

### 增量改动

| finding | 处置 | 落地 |
|---|---|---|
| F1（流程，自审签认顺序） | 留档 + 责任人确认意见 | `self-review.md` 头部已由责任人 2026-11-16 签认；正文补写评审结论节，确认意见栏由责任人本人填写（AI 不代填），注明签认先于评审结论、已知情 |
| F2（边界，显式 id≠stem） | **修（改代码）** | `_load_custom_profiles` 改返回 `(stem, profile)`；`apply_catalog` 的冲突/保留判定改用**文件名 stem**（磁盘身份才是 `os.replace` 的覆盖对象）；新增 `test_conflict_and_preservation_use_filename_not_explicit_id` 钉死评审列举的两种失真（stem 撞而 id 不撞 → 报覆盖；id 撞而 stem 不撞 → 保留并进快照） |
| F3（覆盖缺口，快照零 IO） | 修（补用例） | 新增 `test_install_snapshot_stays_in_memory`：`Path.write_text` / `os.replace` 写陷阱，断言 `install_snapshot` 不触盘、纯内存替换；对应 design 假设表现已闭合 |
| F4（nit，用例计数/名称漂移） | 修（文档） | 本文件实施表与 `test-plan.md` 覆盖矩阵按实施后实际用例名更正：9 函数/12 收集（非真值 ×4）；删除与保留合并为一例、三处改名、失败语义复用既有 fault-injection 用例 |
| F5（nit，except 括号） | **不修** | 加括号后 `ruff format --check` 判需回退：项目 `requires-python>=3.14`、ruff target py314 formatter 偏好 PEP 758 无括号形式；已复核合规，保留既有风格更安全 |
| F6（nit，每文件双读） | 不修，留档 | 目录规模小、`_is_server_synced` 与 `_load_custom_profiles` 各读一次全文的开销可忽略；不引入缓存以免带来失效一致性风险 |

### 增量复审命令与结果

```
uv run pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py aixcoding/tests/mock/test_model_catalog_server.py
    → 103 passed, 2 skipped in 13.94s
      （catalog 78 passed = 基线 66 + 本批 12 收集；mock 25 passed；2 skip 为既有失效 import）
uv run ruff check <2 个改动 py>       → All checks passed!
uv run ruff format --check <2 个改动 py> → 2 files already formatted
uv run python aixcoding/tools/check_docs.py           → OK
uv run python aixcoding/tools/check_docs.py --closure → OK（exit 0）
uv run python aixcoding/tools/check_r2_diff.py --base HEAD → upstream_changed=0
uv run python aixcoding/tools/check_r3_markers.py --base HEAD → upstream_changed=0 marker_checked=0
```

- 增量只改 `catalog.py`（F2 判据 + F5 复核后保留）与测试文件（F2/F3 新用例），
  未触及 state 内容、指纹口径、两阶段发布顺序。
- F2 用例致死行：删 `apply_catalog` 里 `stem in server_ids` 判定 → 两种失真
  场景至少一例变红；F3 用例致死行：在 `install_snapshot` 内加任一磁盘写 →
  写陷阱断言变红。均非 vacuous。
- 全量 Smart Test 基线（上节 13812 passed + architecture 323 passed）未被本轮
  增量推翻——增量只改冲突判据与测试、未新增依赖或上游接触。
- 本机 `config_new.json` 曾被手工改为 `mini2` 导致 mock 2 failed，已由责任人
  还原，本轮复跑恢复全绿；该调试残留未纳入本批。
