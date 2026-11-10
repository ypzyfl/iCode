# 验证记录：无凭证 OpenAI 客户端跳过 Authorization 头校验（llm-keyless-sdk-auth）

## 2026-11-10 实施与回归（方案 D 终态）

命令与输出摘要（R7）：

```
$ uv run ruff check src/chrys/service/llm/sdk_openai.py aixcoding/tests/llm/
All checks passed!

$ uv run ruff format --check src/chrys/service/llm/sdk_openai.py aixcoding/tests/llm/
2 files already formatted

$ uv run pytest aixcoding/tests/llm/ -n0 -q -m "not integration and not gc_calibration"
2 passed in 1.91s
  - test_keyless_client_sends_unauthenticated_request_on_purpose（wire 级：无 key 请求成功且无 Authorization 头）
  - test_keyed_client_keeps_the_stock_validation（分支级：有 key 校验仍在 / 无 key 跳过）

$ uv run pytest tests/service/llm/ -n0 -q
2098 passed, 1 skipped in 41.16s   ← 基线不回归（方案 C 期间曾 20 failed，已消除）
```

## 2026-11-10 方案 A 证伪记录

构造期 `default_headers={"Authorization": Omit()}`：wire 级测试红，仍抛
`TypeError: Could not resolve authentication method`。根因：SDK `_merge_mappings`
（`openai/_base_client.py:2275`）在校验前删除值为 `Omit` 的键，声明到不了
`_validate_headers`；而校验认的 `_has_omitted_header(custom_headers, ...)` 只查
per-request 层。留证：`git log` 无（当场撤改），测试输出当时贴于会话。

## 2026-11-10 方案 C 证伪记录

定制子类 + `clients.py` 换 import 后 `tests/service/llm/` 20 failed——上游 factory
测试 `monkeypatch.setattr("chrys.service.llm.sdk_openai.RetryGuardedAsyncOpenAI", _Spy)`
断言构造参数，换 import 后 patch 点失效（含 keyless 场景测试
`test_openai_async_client_passes_empty_key_when_profile_and_env_missing`）。
结论：挂点必须在上游类本体。已还原并切换方案 D。
