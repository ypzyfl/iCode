# 验证记录：catalog-field-mapping

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-11-14 起草前只读核查（未实施）

命令：

```
git diff --name-status 2ec0829e..HEAD | grep -E "schema.py|catalog.py|config_new.json|options.py|loader.py|serializer.py|server.py"
grep -n "def translate_models_payload\|item: dict\|CONTINUE_PROVIDER\|def parse_catalog" src/chrys/service/aixcoding/models/catalog.py
grep -rn "max_output_tokens\|verify_ssl\|profile.vision" src/chrys/service/llm src/chrys/service/profiles/models/options.py
```

结果：从 `2ec0829e` 到当前 HEAD `46c02674` 的 19 个提交中，
字段相关源码文件**零改动**；`translate_models_payload()` 在 `:405`、
写死式 `item` 在 `:425-443`、`parse_catalog()` 在 `:450`；目标三字段
在 `ModelProfile` 中已存在且在运行时有消费者（结论已写入 design）。
此节仅记录只读事实，**不是实施验证**。

## 2026-11-14 六件套草案门禁（签认前）

命令：

```
uv run python aixcoding/tools/check_docs.py
uv run python aixcoding/tools/check_docs.py --closure
uv run python aixcoding/tools/gen_customizations.py --strict
uv run python aixcoding/tools/check_r2_diff.py --base HEAD
uv run python aixcoding/tools/check_r3_markers.py --base HEAD
git status --short
```

结果：见下方「签认前状态申报」；草案期实跑输出见下一节，完整交付态
门禁证据在责任人签认、按 DEVELOPMENT.md §4.1 动代码后另行追加。

**签认前状态申报（如实）**：`check_docs.py --closure` 预期因本批
`design.md` / `self-review.md` 状态为「草案」而报
`draft decision/review document is forbidden by closure`。
这是完整管线的正常中间态，**不是缺陷**，且不得通过 AI 代填签认绕过。
责任人完成两处签认、并补齐本批六件后应转为全绿。

## 2026-11-14 草案期门禁实跑结果（六件套齐备后、签认前）

命令与退出码（仓库根执行，均为只读校验）：

```
uv run python aixcoding/tools/check_docs.py                    → exit 0
uv run python aixcoding/tools/check_docs.py --closure          → exit 1（预期失败）
uv run python aixcoding/tools/gen_customizations.py --strict    → exit 0
uv run python aixcoding/tools/check_r2_diff.py --base HEAD      → exit 0
uv run python aixcoding/tools/check_r3_markers.py --base HEAD   → exit 0
git status --short
```

输出摘要：

- `check_docs: OK`（27 ADR / 46 design / **45 self-review**，含本批新建的
  `self-review.md`）——六件套齐备、签认栏字段格式合法。
- `check_docs --closure: FAILED with 2 error(s)`，**且仅有这两条**：
  - `aixcoding/docs/batches/catalog-field-mapping/design.md: draft decision/review document is forbidden by closure`
  - `aixcoding/docs/batches/catalog-field-mapping/self-review.md: draft decision/review document is forbidden by closure`

  无缺件报错、无 plan 完成记录报错、无 ADR 引用错误，即失败**纯粹由两处
  「草案」状态造成**，与上一节申报一致。
- `gen_customizations: check OK — 116 rows / 161 markers / 0 warning`。
- `check_r2_diff: changed=8 upstream_changed=0 approved_pool=104 → OK`；
  `check_r3_markers: upstream_changed=0 marker_checked=0 exempt=3 → OK`。
  R2 输出中 13 条「同上 / 文件」类 warn 属其他批次既有遗留，非本批引入。
- `git status --short`：仅 `?? aixcoding/docs/batches/catalog-field-mapping/`
  与 `catalog-sync/` 下此前生成的两份文档；**产品代码、mock 数据、
  测试文件均零改动**。

此节只证明草案文档结构合规与零上游 diff，**不构成实施验证**；
代码路径、契约测试与门禁全集证据待 `design.md` 签认并实施后补记。

## 2026-11-14 实施与门禁全集（design.md 签认后）

前置：`design.md` 由责任人本人签认（施利利 / 已确认 / 2026-11-14）后按
DEVELOPMENT.md §4.1 开始实施；**未修改 `design.md` 正文**，故不触发重签。

### 实施范围

`git diff --stat`（tracked）：5 files changed, 181 insertions(+), 15 deletions(-)。

| 文件 | 改动 |
|---|---|
| `src/chrys/service/aixcoding/models/catalog.py` | 新增 `_CATALOG_NESTED_FIELDS` 映射表 + 循环应用（+18 行），`translate_models_payload()` 既有键与 `parse_catalog()` 未动 |
| `aixcoding/mock/model_catalog/config_new.json` | 补 `completionOptions` / `capabilities` / `requestOptions` 三组嵌套块，`provider`、`aa` 原样保留 |
| `aixcoding/tests/catalog/test_catalog_sync.py` | 新增 4 个用例（含 1 个 4 参数化）：三字段映射与干扰项、非 dict 嵌套块、缺子键、落盘 + `load_profile_from_yaml()` 读回 |
| `aixcoding/tests/mock/test_model_catalog_server.py` | `test_serves_builtin_sample` 补三组嵌套块断言 |
| `aixcoding/mock/model_catalog/README.md` | 补字段映射表与冻结响应体示例；修正客户端路径与失效的文档引用、契约测试文件名 |

另有 `aixcoding/docs/batches/catalog-field-mapping/` 六件套（untracked）。

### 测试

```
uv run pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py aixcoding/tests/mock/test_model_catalog_server.py
    → 90 passed, 2 skipped in 13.95s
uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
    → 810 passed, 47 skipped in 28.64s
uv run python scripts/chrys_test.py --smart --paths <本批 11 个改动文件>
    → Summary: PASSED (exit 0)
      tests         13812 passed, 17 skipped (exit 0)
      architecture  323 passed (exit 0)
```

- 定向用例的 2 个 skip 是 `test_model_catalog_server.py` 里两个 import 已迁走的
  上游模块的 consumer 契约测试（既有 skip，本批未改其断言、未加 R13 豁免），
  与 plan 挂起备忘一致。
- Smart Test 报告 `found 11 changed path(s)`，选择 480 targets / 478 files /
  14152 collected 中的非集成候选；`Summary: PASSED (exit 0)`。
  **Smart Test 是本地定向优化，不等于全套 CI 通过**。

### 静态检查与治理门禁

```
uv run ruff check <3 个改动 py 文件>                       → All checks passed!
uv run ruff format --check <3 个改动 py 文件>               → 3 files already formatted
uv run python -m json.tool aixcoding/mock/model_catalog/config_new.json  → exit 0
uv run ty check --error-on-warning --python-platform linux|darwin|win32 src/chrys
    → 三平台均 All checks passed!
uv run python aixcoding/tools/check_docs.py                → check_docs: OK (27 ADR / 46 design / 45 self-review)
uv run python aixcoding/tools/check_docs.py --closure       → FAILED with 1 error(s)
uv run python aixcoding/tools/gen_customizations.py --strict → OK — 116 rows / 161 markers / 0 warning
uv run python aixcoding/tools/check_r2_diff.py --base HEAD   → changed=13 upstream_changed=0 approved_pool=104 → OK
uv run python aixcoding/tools/check_r3_markers.py --base HEAD → upstream_changed=0 marker_checked=0 exempt=3 → OK
read_lints（3 个改动 py 文件）                              → 0 diagnostics
```

- `--closure` 唯一错误：
  `aixcoding/docs/batches/catalog-field-mapping/self-review.md: draft decision/review document is forbidden by closure`。
  `design.md` 签认后草案错误由 2 条降为 1 条；**剩余这条须在双 AI 自审完成、
  责任人本人签认 `self-review.md` 后清零**，不得由 AI 代填签认。
- R2 输出仍带其他批次 `design.md` 的既有「同上 / 文件」类 warn（非本批引入）；
  `upstream_changed=0` 印证 `src/chrys/*/aixcoding/` 属定制包、不在 R2 范围，
  零上游接触、零新增 R13 豁免、无 R3 marker。

### 与已签认 design 假设的偏差（如实记录，待评审确认）

implementation 期间核查发现：`parse_catalog()` 实际只校验
`id` / `name` / `model_id` / `provider` / `api_style`，**不校验**新映射的
`max_output_tokens` / `vision` / `verify_ssl` 的类型；`ModelProfile` 是普通
dataclass，无 `__post_init__`。因此 design「风险与最坏情况」首段所述
「类型检查把整项判为无效、同步失败并保留上一版目录」对这些字段不成立：
非法类型会原样写入 `item` 并落盘，由 `loader.py` 的 `_coerce_int` /
`_coerce_bool` 兜底（design「对上游隐式行为的假设」表已按此口径登记）。
本批按已签 design 的口径「原样写入、不新增第二层校验」实施，**未改代码行为、
未改 design 正文**；该描述偏差列为双 AI 自审的待确认项，若需补校验须另案
并重新签认。

### 未执行项（如实）

- `requirements.md` 用户场景 1/2 的端到端人工验证（启动 LOCAL mock → TUI 模型
  界面 → 真实 Chat Completions 请求）**未做**；本批按 `test-plan.md` 范围以
  契约测试 + `profile_to_dict` 落盘 + `load_profile_from_yaml()` 读回覆盖，
  请求链消费者未在本批改动、未做请求参数日志。
- 双 AI 自审、责任人签认 `self-review.md`、按授权提交 / 建 PR 均未进行。

## 2026-11-16 双 AI 自审与 findings 收敛（增量复审）

评审 AI：GLM-5.3-Flash / CodeBuddy（独立第二 AI；评审报告标识
`CodeBuddy / GLM` 同模型族）。评审结论 **0 blocker / 3 suggestion / 2 nit**，
责任人逐条拍板「按评审建议打包」：F1 修、F2 修（注记）、F3 保留、F4 不修留档、
F5 修（引用写全）；开发 AI 标识拍板 `CodeBuddy / Tencent Hunyuan Hy`。

### 增量改动

| finding | 处置 | 落地 |
|---|---|---|
| F1（suggestion） | 修 | `test_catalog_sync.py` 新增 `test_null_nested_value_falls_back_to_default_after_yaml_roundtrip`：钉死 `{"verifySsl": null}` → `item["verify_ssl"] is None` → `parse_catalog` 不校验 → 落盘 → `load_profile_from_yaml` 经 `coerce_bool(None, default=True)` 回 `True` 的全链路 |
| F2（suggestion，文档） | 修（原位注记） | `design.md`「风险与最坏情况」首段后加 7 行偏差注记，标注「属注记而非方案变更，不触发重签」；**签认头部未动**，复核 `责任人：施利利 / 状态：已确认 / 日期：2026-11-14` |
| F3（suggestion） | 不修，保留 | mock README 两处路径纠错（客户端路径、契约测试文件名）经评审核实为失效引用，责任人拍板保留 |
| F4（nit） | 不修，留档 | 非 dict 块静默 `continue` 已在设计 / README / 测试三处留档，符合「不新增第二层校验」口径 |
| F5（nit） | 修 | `plan.md:8`、`verification.md:35/80`、`self-review.md:20` 的 `§4.1` 全部写全为 `DEVELOPMENT.md §4.1` |

### 增量复审命令与结果

```
uv run pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py aixcoding/tests/mock/test_model_catalog_server.py
    → 91 passed, 2 skipped in 13.72s   （F1 前基线 90 passed → +1）
uv run ruff check aixcoding/tests/catalog/test_catalog_sync.py                → All checks passed!
uv run ruff format --check aixcoding/tests/catalog/test_catalog_sync.py        → 1 file already formatted
uv run python aixcoding/tools/check_docs.py                                   → OK
uv run python aixcoding/tools/check_docs.py --closure                          → FAILED with 1 error(s)
    （仅 self-review.md 草案，待责任人本人签认）
uv run python aixcoding/tools/gen_customizations.py --strict                   → OK — 116 rows / 161 markers / 0 warning
uv run python aixcoding/tools/check_r2_diff.py --base HEAD                     → upstream_changed=0
uv run python aixcoding/tools/check_r3_markers.py --base HEAD                  → upstream_changed=0 marker_checked=0
```

- 增量仅触及 1 个测试文件（+27 行）与 4 个批次文档；**产品代码未再改动**，
  全量 Smart Test 结论沿用上节（本次增量只加测试与文档，定向复跑已覆盖新断言）。
- `coerce_bool` 实证位置：`src/chrys/service/profiles/coercion.py:10`（评审报告记为
  `coercion.py:10`），`None` 保 default 见第 17–18 行。
- F1 断言的致死行：删 `catalog.py` 的 `item[target] = nested[source]` 或将
  `coerce_bool` 的 `None` 分支改为返回 `False` 都会令该用例变红；非 vacuous。

## 2026-11-16 责任人签认后 closure 终态

责任人本人编辑 `self-review.md` 头部：`责任人：施利利 / 状态：已确认 /
确认日期：2026-11-16`（AI 全程未代填）。复核命令与结果：

```
uv run python aixcoding/tools/check_docs.py --closure   → check_docs: OK（exit 0）
uv run python aixcoding/tools/check_docs.py              → check_docs: OK（exit 0）
uv run python aixcoding/tools/gen_customizations.py --strict
    → OK — 116 rows / 161 markers / 0 warning
git status --short → 5 个 tracked 改动 + ?? catalog-field-mapping/
```

`check_docs` 与 `--closure` 均扫描 27 ADR / 46 design / 45 self-review；
closure 草案错误从签认前的 1 条清零。全部治理门禁收敛，文档侧无可再处置项；
git 提交 / 建 PR 留待责任人逐条授权，按 ADR-0012 执行。
