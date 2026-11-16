# 测试方案：对齐后端模型目录字段在 iCode 中的使用

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

- **契约测试（主）**：`aixcoding/tests/catalog/test_catalog_sync.py` 追加用例，
  直接调 `translate_models_payload()` 与 `parse_catalog()`，断言三字段映射、
  干扰项不落盘、既有映射不变。
- **夹具**：`aixcoding/mock/model_catalog/config_new.json` 按 `design.md`
  内联冻结的响应体契约补齐；
  mock server 原样返回文件内容（`source.py`），不 import 产品代码（黑盒）。
- **回归**：`aixcoding/tests/catalog/`、`aixcoding/tests/mock/` 全量；
  `pytest aixcoding/tests -m "not integration and not gc_calibration"`。
- 零上游改动 → 无 R3 marker、无行为锚定测试义务（无上游 anchor 被改动）。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| 三字段映射产出 `16000/True/False` | `aixcoding/tests/catalog/test_catalog_sync.py::test_translation_maps_nested_catalog_fields_and_ignores_decoys` | 契约 |
| `parse_catalog()` 后 `ModelProfile` 取值同上、4 个顶层映射与 provider 不变 | 同上用例后半段 | 契约 |
| `reasoning` / `aa` / `apiKey` / 三个嵌套块整块不进 `item` | 同上用例的 `not in item` 断言 | 契约 |
| `config_new.json` 字段集合与 `design.md` 冻结契约一致、`verifySsl: false` | `aixcoding/tests/mock/test_model_catalog_server.py`（既有 payload 契约用例）+ `python -m json.tool` | 契约 / 数据 |
| 落盘 YAML 为 `provider=openai` / `16000` / `True` / `False` 且无 `reasoning` | `aixcoding/tests/catalog/test_catalog_sync.py::test_translated_profile_is_published_and_reloaded_with_the_three_fields` | 契约 |
| 新增契约测试通过、既有目录同步测试不回归 | `pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py aixcoding/tests/mock/test_model_catalog_server.py` + `pytest aixcoding/tests -m ... -q` + Smart Test（实测见 `verification.md`） | 回归 |
| 零上游、零新增 R13 豁免 | `check_r2_diff.py --base HEAD`、`check_r3_markers.py --base HEAD`、`gen_customizations.py --strict` | 门禁 |
| `check_docs --closure`、ruff、Smart Test 全绿 | `verification.md` 门禁全集（`--closure` 尚余 self-review 草案 1 条） | 门禁 |
| 嵌套块非 dict / 缺子键的降级 | `::test_nested_catalog_blocks_that_are_not_objects_are_skipped`（4 参数）、`::test_nested_catalog_blocks_with_missing_keys_keep_profile_defaults` | 契约 |

> 每条验收标准至少一行；空缺即为覆盖缺口，须说明理由。
> 落盘一项已新建 `apply_catalog` + `load_profile_from_yaml()` 用例，
> 未复用既有夹具；实测结果见 `verification.md` 实施节。

## 异常与降级路径

- 嵌套块不是 dict（数组/字符串/null）→ 跳过该块，三个字段取默认值，
  不抛异常、不写半份 `item`。
- 嵌套块缺子键 → 只写出现的键，其余取 `ModelProfile` 默认值。
- `maxTokens` 为非法类型 → 按已签 design 口径原样写入 `item`，**不在转换层
  新增第二层校验**；`parse_catalog()` 实际不校验该字段类型（只校验
  id/name/model_id/provider/api_style），值会落盘，由 `loader.py` 的
  `_coerce_int` / `_coerce_bool` 兜底。此与 design「风险与最坏情况」首段的
  偏差已如实记入 `verification.md`，列为双 AI 自审待确认项。
- 顶层 `aa` 干扰项存在 → 只从 `models` 取值，`aa` 不进入任何 `item`。
- `provider: "openrouter"` 继续被忽略，落 `CONTINUE_PROVIDER="openai"`；
  不触发 `parse_catalog()` 的 provider 校验失败。

## 手工验证步骤（若需）

```bash
uv run python -m json.tool aixcoding/mock/model_catalog/config_new.json > /dev/null
uv run pytest -n0 -q aixcoding/tests/catalog/test_catalog_sync.py -k nested
uv run pytest aixcoding/tests/mock/ -n0 -q
```

结果记入 `verification.md`。
