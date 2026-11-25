# 模型并发排队 · 测试用例文档

> 适用：AIxCoding / iCode 内网版本（`feat/model-concurrency-queue` 分支）
> 读者：测试、内网联调
> 日期：2026-11-20
> 配套文档：`requirements.md`、`development.md`、`intranet-verification.md`

---

## 1. 前置条件

| 项 | 要求 |
|---|---|
| 网关 | 测试环境已部署 `model-concurrency-queue`，`POST /api/v3/chat/completions/cancel` 可用 |
| 测试模型 | 专用 `modelKey`，可由网关同事调整 `max_concurrency` / `max_queue_size` / `max_wait_time` |
| 客户端 | 内网包包含本分支（`aixcoding-cli --version` + 请求头带 `Chrys-Request-Attempt-Id` 指纹） |
| 登录/凭据 | TUI `/login` 或桌面端完成登录；确认模型 profile 可用 |
| profile | `base_url` 能拼出 `/api/v3/chat/completions`；`http_read_timeout` > 20s |
| 日志 | 知道 detail 日志路径（见 `intranet-verification.md`） |
| 安全 | 仅测试环境/测试模型；不要记录 `token`；不要在生成环境把线上模型并发调到 1 |

---

## 2. 用例总览

| 编号 | 级别 | 形态 | 场景 |
|---|---|---|---|
| TC-01 | P0 | CLI/TUI | 并发未满直通，无排队提示 |
| TC-02 | P0 | CLI | 排队文案、同 position 去重 |
| TC-03 | P0 | CLI | 名次前移、position 0、放行出字 |
| TC-04 | P0 | TUI | 等待行文案、名次更新、首字消失、新一轮清空 |
| TC-05 | P0 | ACP | `chrys/queue_status` 载荷、去重、`released` |
| TC-06 | P1 | CLI | 长排队心跳不触发 StreamStall |
| TC-07 | P0 | CLI/TUI | `QUEUE_TIMEOUT` 不自动重试 |
| TC-08 | P1 | CLI | `QUEUE_FULL` 退避重试 |
| TC-09 | P0 | TUI | 排队中 Interrupt → cancel 204 |
| TC-10 | P0 | ACP | 排队中 `session/cancel` → cancel 204 |
| TC-11 | P1 | TUI/ACP | 已放行后中断 → 不发 cancel |
| TC-12 | P1 | TUI | 从未排队中断 → 不发 cancel |
| TC-13 | P1 | 接口/单元 | cancel 404/409/5xx/超时的处理 |
| TC-14 | P1 | CLI | 非 QUEUE 错误分类不变 |
| TC-15 | P1 | CLI | 非流式不受影响 |
| TC-16 | P2 | CLI | 定制模块回退 |
| TC-17 | P0 | 日志 | 关键链路日志完整性 |
| TC-18 | P2 | 子代理 | 子代理/workflow 排队不显示 UI（边界） |
| TC-19 | P0 | 抓包/网关日志 | `Chrys-Request-Attempt-Id` 请求头存在且每次尝试不同 |
| TC-20 | P0 | 接口 | cancel URL 推导正确 |

---

## 3. 用例明细

### TC-01 直通回归（P0）

- **前置**：测试模型无占位请求（并发未满）。
- **步骤**：`aixcoding-cli run "你好" -a Code -m <测试模型> -C <目录>`。
- **预期**：
  - 无「当前模型请求量大…」/「已排到队首，当前为队列第一位」行；
  - 正常输出回答；
  - detail 日志无「网关排队」。
- **证据**：CLI stderr、detail 日志。

### TC-02 CLI 排队文案与去重（P0）

- **前置**：网关 `max_concurrency=1`。
- **步骤**：
  1. 窗口 A 发一条长输出请求占住唯一槽位；
  2. 窗口 B 2 秒内再发一条。
- **预期**：
  - B 出现一行 `当前模型请求量大，请求排队约 1 人`；
  - 网关心跳重复同一 position，B **不重复输出**；
  - A 结束后 B 出现 `已排到队首，当前为队列第一位` 并开始出字。
- **证据**：B 的 stderr；detail 日志中 `网关排队心跳` 多条但 CLI 只一行。

### TC-03 名次前移与放行（P0）

- **前置**：`max_concurrency=1`，开三个窗口 A/B/C 依次发。
- **预期**：
  - C 先显示「约 2 人」，A 结束后变「约 1 人」，再变「已排到队首，当前为队列第一位」；
  - 名次只减不增；
  - 放行后提示消失，正常出字；
  - detail 日志有 `网关已放行排队请求` 与 `网关排队等待 N.N 秒后放行`。
- **证据**：三窗口 stderr + detail 日志。

### TC-04 TUI 等待行（P0）

- **前置**：先 CLI 占位；再进 TUI：`aixcoding-cli -m <测试模型>`。
- **步骤**：TUI 中发一句话。
- **预期**：
  - 转写区等待行出现文案；名次变化更新；
  - 首个回答字到达时文案立即消失；
  - 下一轮开始时不残留上一轮文案。
- **证据**：TUI 截图 + `%APPDATA%\chrys\logs\debug.log`（或 `~/.chrys/logs/debug.log`）。

### TC-05 ACP 通知（P0）

- **前置**：ACP 客户端/桌面端连接真实网关；先占位。
- **预期**：
  - 收到 `queue_status`（线上名 `_queue_status`）：排队帧 `{sessionId, requestId, status:"排队中", position, queueSize}`（`requestId` 为 32 位小写 hex，等于该次请求的 `Chrys-Request-Attempt-Id` 请求头值）；
  - 同 (requestId, position) 不重发；重试产生新 `requestId`，同名次也重发；
  - 放行帧 `{sessionId, requestId, status:"放行"}`；
  - 超时拒绝帧（v1.6）`{sessionId, requestId, status:"拒绝", reason:"QUEUE_TIMEOUT", message?, traceId?}`，一次、不去重；
  - 未排队时只会有 `position:0` 排队帧与放行帧（若网关推了 0）。
- **证据**：ACP 客户端日志/驱动脚本输出。

### TC-06 长排队心跳（P1）

- **前置**：测试 profile 临时把 `http_read_timeout` 调到 25s；网关心跳约 20s；占位 60s。
- **预期**：
  - B 排队 60s 不断流、不触发 StreamStall、不重排；
  - detail 日志持续出现 `网关排队心跳`；
  - 反证：把 `http_read_timeout` 调到 15s，B 应在心跳间隙触发 StreamStall（证明续活生效）。
- **注意**：这是客户端 profile 调整，不是网关配置。

### TC-07 `QUEUE_TIMEOUT` 不重试（P0）

- **前置**：测试模型 `max_wait_time=15s`；占位 60s。
- **预期**：
  - 约 15s 后请求结束；
  - 显示网关 message（如「排队等待超时」）；
  - **没有** `↻ Retrying in …` 横幅；
  - detail 日志：`网关拒绝排队请求：code=QUEUE_TIMEOUT retryable=False` + `响应解析`。
- **证据**：CLI stderr + detail 日志。

### TC-08 `QUEUE_FULL` 退避重试（P1）

- **前置**：测试模型 `max_concurrency=1`、`max_queue_size=1`；三窗口并发。
- **预期**：
  - 第三个请求收到 `QUEUE_FULL`；
  - 出现退避重试横幅（既有 transient 阶梯）；
  - detail 日志：`网关队列已满（QUEUE_FULL）…`。
- **注意**：重试会再次排队；只在测试模型做。

### TC-09 TUI 排队中 Interrupt → cancel（P0）

- **前置**：`max_concurrency=1`；先占位；TUI 发请求并确认出现排队文案。
- **步骤**：立即点 Interrupt（或 Esc）。
- **预期**：
  - TUI 立即按「已中断」收尾，不等放行；
  - 网关日志出现 cancel，且 `request_id` 与主请求一致；
  - detail 日志：`正在离开网关队列：POST …`、`发送取消排队请求：POST …`、`取消排队响应：status=204`。
- **反例**：等首字出来后再 Interrupt → 网关日志无 cancel。

### TC-10 ACP 排队中取消（P0）

- **前置**：ACP 客户端排队中。
- **步骤**：发 `session/cancel`。
- **预期**：
  - `stop reason: cancelled`；
  - 网关日志 cancel `204`，主请求 `request_id` 一致；
  - detail 日志同上。
- **说明**：验证取消链路优先用 TUI/ACP；CLI Ctrl+C 有已知时序限制。

### TC-11 已放行后中断不发 cancel（P1）

- **步骤**：排队 → 首字出现 → Interrupt。
- **预期**：网关无 cancel；detail 日志只有 `网关已放行排队请求`，没有 `正在离开网关队列`。
- **窄窗口**：放行后、首字前中断可能发一次 cancel 并收到 `409`，属契约内正常结果，不算失败。

### TC-12 从未排队中断不发 cancel（P1）

- **步骤**：网关空闲，直接发请求并立即中断。
- **预期**：无 cancel；detail 日志无 `正在离开网关队列`。

### TC-13 cancel 404/409/5xx/超时（P1）

- **方式**：接口/单元测试（`aixcoding/tests/llm/test_model_queue_cancel.py`）或 mock 网关。
- **预期**：
  - `404` / `409`：静默通过（detail INFO，不改变中断结果）；
  - `500`：detail WARNING；
  - 连接失败/超时（2s）：detail WARNING，不阻塞中断；
  - 重复取消：返回 404，按 no-op。

### TC-14 非 QUEUE 错误分类不变（P1）

- **方式**：单元测试。
- **输入**：`UPSTREAM_TIMEOUT`、普通 429、连接错误。
- **预期**：`is_retryable` 与改造前一致；detail 无排队相关误报。

### TC-15 非流式不受影响（P1）

- **步骤**：发 `stream=false` 请求。
- **预期**：
  - 请求体无 `request_id`，请求头带 32 位 `Chrys-Request-Attempt-Id`；
  - 不建 tracker、不发 cancel；
  - 网关 429/408/409 按原有错误处理。

### TC-16 定制回退（P2）

- **方式**：模拟定制模块导入失败（单元测试）或使用不含定制的旧包。
- **预期**：
  - 流式照常；
  - 出现 WARNING：`aixcoding llm-queue 定制不可用: 网关排队帧将导致流失败`；
  - 无 cancel、无排队提示；请求头仍带 `Chrys-Request-Attempt-Id`（上游发送）。

### TC-17 日志完整性（P0）

- **步骤**：完成一次「排队 → 放行」和一次「排队 → 取消」。
- **预期 detail 日志能回答**：
  1. 收到什么排队帧（`网关排队帧（解析后）`，含 `model_extra`）；
  2. 解析成什么（`position/queueSize`、`request_id`）；
  3. 放行耗时（`网关排队等待 N.N 秒后放行`）；
  4. 取消发到哪、参数是什么（`发送取消排队请求：POST … body=… token=已携带`）；
  5. 网关返回什么（`取消排队响应：status=… body=…`）。
- **失败取证件**：附上 detail 日志片段 + 网关日志（`request_id` 对齐）。

### TC-18 子代理/workflow 排队不显示 UI（P2，边界）

- **步骤**：让子代理/workflow 节点走同一测试模型并排队。
- **预期**：
  - 主界面**不显示**排队提示（设计边界）；
  - detail 日志仍有 `网关排队`/`取消排队` 记录；
  - 不作为缺陷上报。

### TC-19 `Chrys-Request-Attempt-Id` 指纹（P0）

- **步骤**：连续发两条流式请求；抓包或看网关日志。
- **预期**：
  - 每个 HTTP 尝试的请求头都有 32 位小写 hex `Chrys-Request-Attempt-Id`，请求体无 `request_id`；
  - 两次请求不同；SDK 重试/重定向各产生新值；
  - 非流式同样带该头（客户端不武装取消）；
  - 网关日志能按该头（带头调用方）或请求体 `request_id`（无头的 curl 演练）定位队列元素。

### TC-20 cancel URL 推导（P0）

- **步骤**：查看真实 profile 的 `base_url`，手算 + curl 验证：

```text
http://host/aicoding/api/v3  → http://host/aicoding/api/v3/chat/completions/cancel
http://host/aicoding/api/v1  → 同上
http://host/aicoding         → 同上
```

- **预期**：
  - curl 一个不存在的 `request_id` → `404`（不是 405/HTML 404）；
  - `401/403` 说明 `token` 头/凭据不对；
  - 连接失败说明代理/地址不对。
- **证据**：curl `-i` 输出 + detail 日志中的 endpoint。

---

## 4. 通过标准

- P0 用例全部通过；
- P1 用例通过或有明确、可接受的已知限制记录；
- 每次失败附带：场景、时间、客户端 detail 日志片段、网关日志 `request_id` 对齐、截图/终端输出；
- 不把「子代理/workflow 不显示提示」「非流式不接排队」「CLI Ctrl+C 可能漏 cancel」当缺陷。
