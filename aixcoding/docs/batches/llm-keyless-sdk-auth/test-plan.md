# 测试方案：无凭证 OpenAI 客户端跳过 Authorization 头校验（llm-keyless-sdk-auth）

## 测试范围与策略

两级锚定，全部落在定制测试区 `aixcoding/tests/llm/test_sdk_auth.py`（R4）：

1. **wire 级**：走生产构造路径（`_build_openai_sdk_client` 无 profile key、无 env key）+ `httpx.MockTransport`，SDK 的头合并与校验真实运行，不 mock SDK 内部（DEVELOPMENT.md §5）。
2. **分支级**：直驱 `_validate_headers`，锚定"豁免只作用于无凭证 client"的边界。

上游回归：`tests/service/llm/` 全量（含 20 条 patch `RetryGuardedAsyncOpenAI` 的 factory 测试——它们同时是方案 C 的证伪证据与方案 D 的兼容性守卫）。

## 覆盖矩阵

| 用例 | 层级 | 断言 |
|---|---|---|
| `test_keyless_client_sends_unauthenticated_request_on_purpose` | wire | 请求成功（不抛 TypeError）；wire 上无 `Authorization` 头 |
| `test_keyed_client_keeps_the_stock_validation` | 分支 | 有 key：`_validate_headers({}, {})` 仍抛 TypeError（stock 校验未丢失）；无 key：同样输入不抛 |
| 上游 `tests/service/llm/` 2098 条 | 回归 | 基线不回归（尤其是 factory 的 `_Spy` patch 测试） |

## 异常与降级路径

- 上游 SDK 升级改变 `_validate_headers` 语义 → 分支级测试红，暴露漂移。
- 定制包/标记被升级冲掉 → wire 级测试红（TypeError 回归），指向恢复。

## 手工验证步骤

```bash
uv run python aixcoding/mock/model_catalog/server.py --port 0 --no-auth   # 本地无凭证端点
# 客户端不设任何 key，发送一条消息 → 请求到达 mock（日志显示 no credential header），不抛本地错误
```
