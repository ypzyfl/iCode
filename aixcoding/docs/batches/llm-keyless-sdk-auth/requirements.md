# 需求：无凭证 OpenAI 客户端可正常发请求（llm-keyless-sdk-auth）

## 背景与问题

目录下发的模型 profile 不携带 `api_key`（目录不是凭证通道，设计如此），用户环境也可能没有 `OPENAI_API_KEY`。此场景下 `clients.py` 以空 key provider 构造 OpenAI SDK client——构造能通过，但**发请求时**被 SDK 的 `_validate_headers` 拒绝：

```
TypeError: Could not resolve authentication method. Expected either api_key
or admin_api_key to be set. Or for one of the `Authorization` or
`authorization` headers to be explicitly omitted
```

本地 mock 联调（无凭证的 127.0.0.1 端点）因此完全不可用，必须手工 `export OPENAI_API_KEY=dummy` 才能绕过。

## 目标与非目标

- 目标：空 key 构造的 client 发出的请求**不再被 SDK 本地拒绝**，wire 上不带 `Authorization` 头（无凭证是构造时的既定语义，不是错误）。
- 非目标：**不做**登录 token 兼任 `Authorization: Bearer`（另一方案，已留档 `/tmp` 补丁与本文档备选表，需求出现时另行立项）；不改有 key client 的任何校验行为；不改 mock 与网关。

## 用户场景

本地联调：mock（`aixcoding/mock/model_catalog/`）+ 无任何 key 配置的客户端 → 发消息 → 请求到达 mock（无 Authorization 头），而不是本地抛 TypeError。

## 验收标准

- [ ] 无 profile key、无 env key 时，`_build_openai_sdk_client` 构造的 client 能完成一次 chat 请求（不抛 TypeError）
- [ ] 该请求 wire 上没有 `Authorization` 头
- [ ] 有 key 的 client 行为不变（stock 校验仍在）
- [ ] 上游测试全绿（`tests/service/llm/` 2098 条基线不回归）

## 开放问题

- 上游 SDK 升级若改动 `_validate_headers` / `_merge_mappings` 语义，本覆写需重审（见 design"对上游隐式行为的假设"）——归属：责任人。
