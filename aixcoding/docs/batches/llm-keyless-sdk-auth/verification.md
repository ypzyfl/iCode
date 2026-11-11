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

## 2026-11-10 peer review 处置与 `--strict` 对账补录（finding-A/C/D）

- finding-D：design 承诺"实施后跑 `--strict` 对账"，记录补录——
  ```
  $ uv run python aixcoding/tools/gen_customizations.py --strict
  gen_customizations: check OK — 102 registration row(s) / 139 marker(s)
  across 15 design(s), 6 retired id(s), 0 warning(s)
  ```
- finding-A：登记改号 C145 → C153（peer review 证实并行批次 logo-branding
  `origin/feat/logo-branding` 已登记 C145-C152；评审建议的 C151 亦在其
  C151-C152 孪生组区间内，故取 C153）。改号后复跑：
  ```
  $ uv run python aixcoding/tools/gen_customizations.py --strict
  （见下方当日复跑输出，exit 0）
  ```
- peer review 证据抽查（评审 AI 复跑，与本文档既有记录一致）：
  `test_sdk_auth.py 2 passed` / `tests/service/llm 2098 passed, 1 skipped`。

## 2026-11-10 第二轮 peer review（approve）与合并主干后复检

- 第二轮 peer review（评审 AI 于 HEAD `5369c285` 执行）：**建议 approve**。
  上游接触面 18 行 100% 过目（四问全过）、三项交叉检查（R2/R11 比对、
  幻觉 API 验证——openai 2.54.0 实测符号全真、缺陷模式扫描含 MRO 无冲突）、
  两 blocker 与第一轮 findings A-D 复核均 confirm、证据抽查复跑通过
  （`test_sdk_auth.py 2 passed`；`--strict` check OK 102/139/0，与本文档补录一致）。
  唯一候选 finding（轻微）：commit body 未含"评审处置"要素——经规范核对，
  DEVELOPMENT.md 无提交 body 五要素要求（三要素已齐），评审结论的规范落点为
  PR 描述（§7 交付报告第 4 项）与本目录活文档；裁决待责任人。
  另注（评审查证）：SDK `_provider_runtime` 豁免路径与 `api_key`/`base_url`
  互斥，本项目必传 base_url，结构性不适用，不构成更优方案。
- 合并 `main_aixcoding_cli`（merge commit `a35e57e3`，带入 logo-branding PR #109）
  后复检：
  ```
  $ git diff main_aixcoding_cli...HEAD --stat
  8 files changed, 335 insertions(+)   ← 与合并前一致，无多余改动混入
  $ uv run python aixcoding/tools/gen_customizations.py --strict
  gen_customizations: check OK — 105 registration row(s) / 146 marker(s)
  across 16 design(s), 7 retired id(s), 0 warning(s)
  （增量 3 行/7 marker 来自 logo-branding C145-C152；C153 不撞号）
  $ uv run pytest aixcoding/tests/llm/ -n0 -q
  2 passed in 2.31s
  $ uv run pytest tests/service/llm/ -n0 -q
  2098 passed, 1 skipped in 38.89s
  ```
