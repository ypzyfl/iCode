# 测试计划：客户端对接模型并发排队（model-queue-client）

> 活文档（AI 维护，不签认）。实现前起草，实现中按需增补。

## 测试策略

- 定制测试落 `aixcoding/tests/llm/`，独立收集（`aixcoding/tests` 不在上游默认收集范围）。
- 帧过滤与续活：用本地假 SSE 服务（stdlib `http.server` + 线程，可按帧间 sleep）驱动真实 `ChatCompletionsClient`，不 mock SDK 解析层——mock 会掩盖 SDK 语义变化，而本定制的风险主要在 SDK 语义上。
- 重试判定：一律走**生产入口** `chrys.foundation.errors.is_retryable`（classify 版，`attempts.py:20` 同源），不走 `_legacy.is_retryable`，否则将来被 verdict / FINAL-veto 分支短路时测试不会红。
- 转译路径用真实 `openai.APIError` 构造（`message` 位置参数 + `body` 关键字，`code` 由 body 派生），保证与 SDK 实抛形态一致；不手写仿造异常类。
- 回归护栏：非排队异常必须保持原分类，防止判据过宽。

## 覆盖矩阵

| 验收标准 | 测试用例 | 层次 |
|---|---|---|
| 含 `queue_status` 的流不失败 | 假 SSE：`queue_status` → 正常 chunk → `[DONE]`；断言收到完整回复且无异常 | 端到端（真 SDK + 假服务） |
| `queue_status` 不产出 update | 同上，断言 update 只含正文，usage 正常上报 | 端到端 |
| 判据不过宽 | `choices=None` 且无 `position/queueSize` 的帧 → 仍抛 `ChatClientInvalidResponseException` | 端到端 |
| `QUEUE_TIMEOUT` 非重试 | guard 转译后 `is_retryable(translated) is False`；同时断言根因 `APIError` 在 `__cause__` 上 | 单元 |
| `QUEUE_CANCELLED` 非重试 | 同上 `QUEUE_CANCELLED` | 单元 |
| `QUEUE_FULL` 仍可重试 | 原样上抛裸 `APIError` → `is_retryable(...) is True` | 单元 |
| 心跳续活 stall 看门狗 | 在 `wire_progress_scope` 内消费两帧 `queue_status`，断言上报 2 次 | 单元（调用点锚定）；**局限**：scope 传播由上游 `_watchdog_await` 保证，定制测试不覆盖"生产 watchdog 确实包裹 chunk 拉取" |
| 非 QUEUE 错误不变 | `UPSTREAM_TIMEOUT` code、`APIStatusError(429)`、连接错误各自保持原判定；其中裸 `APIError(code='UPSTREAM_TIMEOUT')` 另跑**经 guard 包装迭代器**的变体，断言原样上抛且分类不变（触达 guard 的 except 放行分支） | 单元 + guard 层 |
| 定制缺失回退 | monkeypatch 定制 import 抛出 → 流式照旧；**必须断言内层异常是 `ChatClientInvalidResponseException`**（回退走了原 invalid-event 路径），而不是只断言 `ChatClientException`——否则删掉 try/except 也绿（自审 F2 破坏实验已证） | 单元 |

## 异常与降级路径

- 定制包导入失败：上游 try/except 全吞错，回退原迭代器；日志 debug 级，不打断请求。
- `queue_status` 形状漂移：不识别 → 走原 `raise_invalid_stream_event`（fail-loud），用例锚定该退化行为。
- 转译不命中（`body`/`code` 形态变化）：退回可重试，用例锚定"裸 APIError 仍可重试"，避免静默变成不可用。
- `exc.code` 取值安全：定制包内对 code 做 `str` 类型判定，`body` 为 `str`/`None`/嵌套 dict 时不崩且不改判（负例覆盖）。

## 上游接触面回归

- 队列事件不得影响 `_read_after_ending` 的 usage 收集：用例中 `[DONE]` 前带 usage chunk，断言 usage 正常上报。
- 帧过滤与转译两条判定链回归：`is_retryable` 对普通 429 / 500 / 连接错误的结果与改造前一致（用同一批输入对比 `_legacy.is_transient` 结论）。
