# ADR-model-queue-client--gateway-cancel-required：网关排队取消链路永久保留（取代帧拦截决策 6）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-<batch-slug>--<decision-slug> 取代）——括号内即后继 ID（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认（签认时：状态→已确认、填日期；并将 `model-queue-client--queue-frame-interception.md` 状态行改为：被取代（被 ADR-model-queue-client--gateway-cancel-required 取代））
- 确认日期：2026-11-26
- 确认意见：无特殊意见

> 起草说明（2026-11-26，PR #154 独立评审 B2）：决策 6（"不接 cancel 接口……断连即出队"）自
> v1.1 起被实施反转、v1.4 认定根因不成立，但 ADR 未走取代流程。本文按 §6 补流程；所记录的
> 决策本身均为责任人已签变更单（v1.1/v1.4/v1.5/v1.6），无新决策。

## 背景

`ADR-model-queue-client--queue-frame-interception` 决策 6 以网关文档 FAQ Q3 为据裁定"不接
cancel 接口：客户端中断即断连、断连即出队"。2026-11-24 内网联调（design v1.4）实测推翻该前提：
**网关无法感知客户端断连**——流关闭后请求仍留在 FIFO 队列占并发槽位直到 `max_wait_time`
超时。自 v1.1 起（责任人裁决"排队中主动取消"）iCode 已接 `/api/v3/chat/completions/cancel`，
v1.5 修凭据同源、v1.6 修传输同源（verify/代理旁路），取消链路为生产必经路径。

## 决策

1. **取消链路永久保留，撤销决策 6 的"不接 cancel"非目标**：中断（用户 Esc / 取消排队按钮 /
   流异常收尾）一律经 `close_stream_and_cancel` → `QueueRequestTracker.cancel_on_close` 出队；
   上游等价替代（wire 层 abort/close 生命周期钩子）出现前不移除（登记点
   `model-queue-client:queue-cancel` 的 removal_condition 已如实改为无上游等价）。
2. **"断连即出队"不作为任何设计前提**：网关侧无此语义，涉及排队的故障排查（联调手册 §5.5）
   一律先查 cancel 是否真的发出（detail 日志通道 `aixcoding.detail.llm_queue`）。
3. 429 阶梯维持决策 6 原裁定（3/7/15… 比网关建议保守），不受本 ADR 影响。

## 理由

- 根因实证：v1.4 联调记录（design 变更单）+ v1.5 生产事故（纯登录态 cancel 未发出、请求滞留
  队列，2026-11-25 14:53 request_id=f59688fa…）均以"断连不出队"为前提故障。
- 取代而非修订：决策 6 是方向性裁定（不接 vs 接），按 §6 实质变更出新 ADR 回指。

## 后果

- 旧 ADR `model-queue-client--queue-frame-interception` 决策 6 由本文取代；其状态行改为
  "被取代（被 ADR-model-queue-client--gateway-cancel-required 取代）"，其余决策（1–5、7）继续有效。
- 升级义务并入既有清单：cancel 端点契约（`ModelQueueFrontend.md` §3.6：204 成功 / 404 未知 /
  409 已放行）、`Chrys-Request-Attempt-Id` 逐尝试唯一性、凭据与传输同源（v1.5/v1.6）。
