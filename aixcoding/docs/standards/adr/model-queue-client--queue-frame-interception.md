# ADR-model-queue-client--queue-frame-interception：排队帧拦截与队列拒绝转译

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-<batch-slug>--<decision-slug> 取代）——括号内即后继 ID（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-18
- 确认意见：尽量不改上游，若必须要改，要少而集中的改（可选；审阅中形成的判断、附加条件或保留）

> 本文为决策时点快照；现行规则以 `DEVELOPMENT.md` R1/R2/R9 为准。

## 背景

内网 LLM 网关新增「按模型全局并发上限 + FIFO 排队」，通过 SSE 具名事件 `queue_status` / `queue_rejected` 与 HTTP 429/408/409 表达排队状态。iCode 侧两条硬冲突（本机实测 `openai==2.54.0`）：

- SDK 把未知具名事件按普通 `data:` 解析成 chunk，`choices=None`，触发上游 `raise_invalid_stream_event` → 整个流式请求失败。
- `queue_rejected` 抛裸 `openai.APIError`，被 `RETRYABLE_TYPE_NAMES` 判为 transient → `QUEUE_TIMEOUT` 自动重排队 10~18 次。

客户端没有扩展点：SDK 不暴露 `event:` 名、无 provider 插件注册、chunk 迭代器在上游就地构造。

## 决策

1. **帧拦截在 chunk 层**：在 `chat_completions/client.py` 的 `chunks` 迭代处插一层包装（逻辑外置 `src/chrys/service/aixcoding/llm_queue/`），丢弃 `queue_status` 帧；判据为 `choices is None` 且 `model_extra` 同时含 `position` / `queueSize`（均为 `int`）。
2. **队列拒绝在定制包内转译为 `ProviderResponseError(retryable=False)`**：`exc.code` 为 `QUEUE_TIMEOUT` / `QUEUE_CANCELLED` 时转译，`from exc` 保留根因；`QUEUE_FULL` 不转译，原样上抛维持现状可重试。
3. **分类层不改**：依赖 `classify.classify_error` 既有的 `explicit_retryable` 短路（`classify.py:174` 先于 `_legacy.is_transient` 的 `:188`），不触碰 `foundation/errors/_legacy.py`。
4. **丢帧时续活 stall 看门狗**：调用 `report_wire_progress()`，把网关 20s 位置心跳复用为 idle 续活信号。
5. **落 `service/aixcoding/` 而非 `kernel/aixcoding/`**：包依赖 `chrys.kernel.report_wire_progress`，而 kernel↔kernel 必须相对导入（`test_layering.py:534`）、父级相对被 TID252 禁止，故能容纳其依赖的最低档是 service。
6. **不接 cancel 接口、不改 429 阶梯**：客户端中断即断连、断连即出队；现有 3/7/15… 阶梯比网关文档建议更保守。
7. **排队进度 UI 拆第二批**：本决策先保证正确性，UI 复用同一模块的状态记录。

## 理由

- 否决「底层接管 SSE 分帧读 `event:`」：需替换上游 SDK 流解析路径，与 `_read_after_ending`、`ReplayByteStream` 强耦合；实测 data 字段（`position`/`queueSize`、`code`）完整保留。
- 否决「该模型改非流式」：零上游改动但丢失流式，TUI 长时间空白、TTFT 消失。
- 否决「monkeypatch SDK」：R1「最小 ≠ 最隐」。
- 否决「改 `_legacy.is_transient` 按 `body['code']` 终态化」（首稿方案 E）：其立论「包装层无法遏制重试」经复核**不成立**——`explicit_retryable` 短路在 `is_transient` 之前生效；E 能工作但多改一个全局热路径文件，且判据须额外防 `body` 为 `str`/`None`，无净收益。
- 否决「靠注入回调使定制包落 kernel 档」：R1 硬约束「直接依赖优于间接」，且上游漏传即静默失去心跳续活。
- 不接 cancel：网关文档 FAQ Q3 明确断连即出队，iCode 中断语义已是关流，再接 cancel 是重复机制。

## 后果

- 升级义务：SDK 未知具名事件处理、`APIError.body/code` 形态、`classify` 的 `explicit_retryable` 短路顺序、stall 看门狗的 progress 机制，四处变化时须复核定制登记 `model-queue-client:queue-frame-guard` 并跑定制测试。
- 判据契约：`queue_status` 的 data 形状与 `error.code` 取值成为客户端与网关的隐式契约；失效时表现为 fail-loud（invalid response），不静默丢数据。
- 长排队安全边界：排队时长只受 `maxWaitTime` 约束，不再受 `http_read_timeout`（stall 超时）约束；前提是网关心跳间隔小于该超时。
- 第二批 UI 只能消费 `llm_queue` 模块暴露的状态，不得再在上游新增挂点。
