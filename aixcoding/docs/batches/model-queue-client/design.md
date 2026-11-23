# 设计：客户端对接模型并发排队（model-queue-client）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-19
- 确认意见：尽量不改上游，若必须要改，要少而集中的改（可选；审阅中形成的判断、附加条件或保留）

## 方案概述

一处上游接线 + 一个 service 档定制包，业务逻辑全部外置：

```
上游 chat_completions/client.py::updates()              定制包 service/aixcoding/llm_queue/
  chunks = aiter(sdk_stream)                             guard_queue_frames(chunks)
    │                                                     ├─ queue_status 帧
    └─ # AIxCoding llm-queue（lazy import + 全吞错）        │   （choices is None 且 model_extra
         chunks = guard_queue_frames(chunks)              │    含 position/queueSize 两个 int）
                                                          │   → report_wire_progress()
                                                          │   → 丢弃，不产出 update
                                                          ├─ openai.APIError 且 code ∈
                                                          │   {QUEUE_TIMEOUT, QUEUE_CANCELLED}
                                                          │   → raise ProviderResponseError(
                                                          │        retryable=False) from exc
                                                          └─ 其他帧 / 其他异常 → 原样放行
```

重试语义由 `classify.classify_error` 的既有短路决定，**不需要改分类层**：

```
ProviderResponseError(retryable=False)
  └─ provider_signal → explicit_retryable=False     (provider.py:399-406)
       └─ classify.py:174 短路 → transient=False
QUEUE_FULL 不转译 → 裸 openai.APIError
  └─ signal 无 explicit_retryable/verdict → classify.py:188 → _legacy.is_transient → True（现状可重试）
```

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| A. 服务端对该模型不启用排队（`maxConcurrency=0`） | 客户端零改动 | 放弃排队能力本身 | 0 | ✗ 非目标 |
| B. 该模型改非流式（`profile.stream: false` + 调大 `http_read_timeout`） | 零上游改动；非流式 429/408/409 语义天然符合 | 丢失流式：TUI 长时间空白、TTFT 消失、stall 看门狗失去意义 | 0 | ✗ 体验不可接受（技术反对） |
| C. 在 `ReplayByteStream` 处接管 SSE 分帧，读取 `event:` 名 | 语义最精确 | 需替换上游 SDK 流解析路径，与 `_read_after_ending` 等结构强耦合 | 1×大×高 | ✗ 过度设计（data 字段已足以识别） |
| D. monkeypatch `AsyncOpenAI` 的 stream 属性 | 零上游文件 diff | 隐式、依赖 SDK 私有构造；R1「最小 ≠ 最隐」明确反对 | 0（隐式耦合高） | ✗ |
| E. 帧过滤 + 改 `_legacy.is_transient` 按 `body['code']` 终态化 | 分类层兜底，不依赖包装层存活 | 改 2 个上游文件；`is_transient` 是所有错误分类的热路径，判据还须防 `body` 为 `str`/`None`；实测其效果被 E' 完全覆盖 | 2×11×中 | ✗ 接触面更大（详见下方否决说明） |
| **E'. 帧过滤 + 在定制包内把队列拒绝转译为 `ProviderResponseError(retryable=False)`** | 上游只 1 文件；判定收敛在定制包；`QUEUE_FULL` 天然维持现状 | 依赖 `classify` 的 `explicit_retryable` 短路机制 | 1×6×低 | ✓ 采纳 |

**为何否决 E**：曾认为「包装层无法遏制重试」，该论断**不成立**——`classify.py:174-175` 在 `_legacy.is_transient`（:188）之前短路，`ProviderResponseError.retryable` 经 `provider.py:399-406` 进入 `explicit_retryable`，`chrys.foundation.errors.is_retryable`（`errors/__init__.py:24`）就是 classify 版本，wire 层 `attempts.py:20` 走的正是它。E 能工作，但多改一个热路径文件、多一条取值安全约束，无额外收益。

**为何不是 `kernel/aixcoding/`（R9 最低档）**：定制包依赖 `chrys.kernel.report_wire_progress`，而 `test_layering.py:534` 要求 kernel↔kernel 必须相对导入；`pyproject.toml:216` 启用 `TID`（TID252 默认禁父级相对），使 `kernel/aixcoding/*` 无法引用父级 `chrys.kernel`（`DIRECTORY.md:71` 已记录该“二者皆死路”）。唯一能落 kernel 的办法是把 `report_wire_progress` 作为回调由上游注入，但 R1 硬约束「直接依赖优于间接」，且上游漏传即静默退化为无心跳续活（P2 缺陷复现）。故“能容纳其全部依赖的最低档”在此为 service 档。

R1 自查（必答）：
- 业务逻辑是否已全部外置？是。帧识别、错误转译、progress 续活、判据常量都在 `src/chrys/service/aixcoding/llm_queue/`；上游只剩一次函数调用。
- 接线点是否已最小化？是，一处。分类判定不需要上游挂点，转译异常经现有 `except ProviderResponseError: raise`（`client.py:264`）原样直达分类层。
- 能否完全不改上游？不能。SDK 不暴露 `event:` 名、无 provider 插件注册、chunk 迭代器在上游就地构造（实测确认）。

## 上游改动清单（R2）

| 文件 | 改什么 | 实际行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/service/llm/chat_completions/client.py` | `updates()` 内把 `chunks` 换成 `guard_queue_frames(chunks)`：函数内 lazy import 定制包，任何异常回退原迭代器（全吞错）；v1.2 在 `_complete` 增加非流式 attach | +19/−0 | `# AIxCoding llm-queue: guard gateway queue frames`、`# AIxCoding llm-queue: a blocking completion carries a request_id too` |
| `tests/orchestration/engine/test_settings_reload.py` | v1.2 重载等价比较前移除并校验两个不同的合法 `request_id`，其余请求体仍全字段相等 | +5/−1 | `# AIxCoding llm-queue: reload equivalence excludes the per-request correlation id` |
| `tests/architecture/trajectory_wait_manifest.json` | 生成产物：新增 1 条 wait 节点 `chrys.service.aixcoding.llm_queue.queue_frames:guard_queue_frames:1`（`await anext(iterator)`，规则 `unresolved`），刷新命令 `uv run python -m tests.support.trajectory_wait_inventory` | +5 | 无（`MARKER_EXEMPTIONS` 生成产物，见 `aixcoding/tools/_common.py`） |

R2 报批说明：
- 相比首稿已撤销 `foundation/errors/_legacy.py` 的 +5 行（改由 E' 转译覆盖）。
- `client.py` 首稿预估 +6/−1 与实际 +10/−0 的差异：实施后自审补齐了 1 行 `logger.warning` 换行与 1 行注释，且未删任何原行（首稿把 `chunks = aiter(...)` 误算成被替换行）。行数以本表为准。
- wait 清单是上游测试守卫（`tests/architecture/test_trajectory_wait_inventory.py`）的生成产物，本批新增定制模块引入首个定制 wait 节点，必须随本批刷新；该文件属 `MARKER_EXEMPTIONS`，无 marker。

## 对上游隐式行为的假设

1. 假设：`openai==2.54.0` 的 `Stream` 把未知具名事件按普通 `data:` 解析，不丢弃、不改抛错 → 依赖方式：在 chunk 层过滤即可，不必读 `event:` → 失效表现：SDK 改为忽略未知事件则过滤空转（无害）；改为抛错则本改动失效，测试锚定。
2. 假设：`queue_status` 的 data 恒为 `{"position": int, "queueSize": int}`，该帧无 `id`/`choices`/`usage` → 依赖方式：以 `choices is None` + `model_extra` 同时含两个 int 字段作判据 → 失效表现：服务端加字段或改名 → 帧不被识别，回退为 invalid response（**fail-loud**，不静默丢数据）。
3. 假设：`queue_rejected` 在 SDK 层是裸 `openai.APIError`，`body` 为解包后的 `{code,message,traceId}`，`exc.code` 由其派生 → 依赖方式：从 `exc.code` 取码 → 失效表现：SDK 改为 `APIStatusError` 或形态变化 → 转译不命中，退回可重试（最多重排队 10 次，非静默），测试锚定。
4. 假设：`classify_error` 对 `ProviderResponseError` 走 `explicit_retryable` 短路，且该判断先于 `_legacy.is_transient`（`classify.py:174` 先于 `:188`）；`chrys.foundation.errors.is_retryable` 是 classify 版本（`errors/__init__.py:24`），生产 wire 层经它判定（`attempts.py:20`）→ 依赖方式：转译 `ProviderResponseError(retryable=False)` 即可终态化 → 失效表现：上游调整短路顺序或改由 `_legacy.is_transient` 先行 → 定制测试红，需同步改分类层。
5. **假设（评审补入，否则长排队场景仍雪崩）**：stall 看门狗按 idle 计 time，唯一续活信号是 `report_wire_progress()`（`kernel/loop.py:800-831`），`stall_timeout_seconds = http_read_timeout`（默认 300s，`schema.py:47`）→ 依赖方式：guard 丢弃 `queue_status` 帧时同时调用 `report_wire_progress()`，把网关 20s 位置心跳复用为 stall 续活 → 失效表现：若上游改为按 update 数计时或不复制 context 到 task（`start_with_wire_progress` 现为复制行为），排队 ≥ 超时即 `StreamStall` → 断连出队、重连重排（网关 FAQ Q3）。**测试边界**：定制测试只锚定"丢帧时调用了 `report_wire_progress`"（单元 + 拓扑），"chunk 拉取确实运行在 watchdog 的 progress scope 内"属上游 `_watchdog_await` 行为，定制测试不覆盖；该假设失效只能靠上游自身测试或线上现象发现。

## 定制点登记预告

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| model-queue-client:queue-frame-guard | src/chrys/service/llm/chat_completions/client.py | AIxCoding llm-queue: guard gateway queue frames | 1 | `AsyncOpenAI.chat.completions` chunk 迭代（`StreamState.updates_for` 校验前） | 低（10 行接线，异常全吞错，删除即回滚） | 〔上游等价〕SDK 原生忽略未知具名事件且网关改以 HTTP 状态码表达排队拒绝，或网关不再对客户端下发 `queue_status` |
| model-queue-client:queue-cancel | src/chrys/service/llm/chat_completions/client.py | AIxCoding llm-queue: cancel queued request on abort | 3 | `_open_stream`（tracker 构造 / `on_status` 包装 / `finally` 取消） | 中（放行空窗误判只多一次 `409` 旁路请求，契约内） | 〔上游等价〕上游提供 wire 层请求生命周期钩子（abort/close 回调） |
| model-queue-client:queue-request-id | src/chrys/service/llm/chat_completions/client.py | AIxCoding llm-queue: a blocking completion carries a request_id too | 1 | `_complete`（非流式请求发送前 attach） | 低（仅附加网关契约字段并记录日志，异常维持原有降级） | 〔上游等价〕上游提供所有协议统一的请求 ID 注入钩子 |
| model-queue-client:queue-request-id-reload-test | tests/orchestration/engine/test_settings_reload.py | AIxCoding llm-queue: reload equivalence excludes the per-request correlation id | 1 | `test_manual_reload_next_provider_request`（比较前移除并校验 id） | 低（仅测试归一化，仍逐字段比较其余请求体） | 〔上游等价〕上游原生生成请求 ID 并同步调整该测试 |

## 风险与最坏情况

- 判据过宽：把其他 `choices=None` 的合法帧当排队帧丢弃 → 静默丢 usage。缓解：判据要求 `model_extra` 同时含 `position`、`queueSize` 且均为 `int`，并断言无 `id`/`usage`；测试覆盖"`choices=None` 但无排队字段"仍报 invalid response。
- progress 续活失效：见假设 5。定制测试锚定"丢帧 → 上报 progress"的调用点；scope 传播本身在上游，不在本批测试射程内（test-plan 已标注该局限）。
- 转译不命中：`body`/`code` 形态变化 → 退回重排队（可用性尚存，负载放大）。
- `QUEUE_CANCELLED` 在 v1.0 阶段不可达（不接 cancel 接口）；v1.1 起由本端 cancel 触发，但用户已主动中断、多半收不到该帧，转译保留作防御。
- 回滚：删除接线并移除定制包，行为完全回到当前状态（无数据格式、无持久化、无对外契约变化）。

## ADR 判定

- ① 有被认真考虑但否决的备选（A/B/C/D/E）：**是**
- ② 撤销代价高：否（删除 10 行与 1 条 wait 清单行即回滚）
- ③ 约束未来工作模式：否（第二批 UI 另行设计作用域，本批不留进程级状态）
- ④ 依赖上游非公开接口或行为（SDK 对未知事件的处理、`classify` 的 `explicit_retryable` 短路、stall 看门狗的 progress 机制）：**是**

→ 出 ADR：`standards/adr/model-queue-client--queue-frame-interception.md`。

---

## 变更单 v1.1（2026-11-19，责任人裁决）：排队中主动取消

> 契约来源：`ModelQueueFrontend.md` §2（`request_id`/`requestId` 为请求体可选字段）、§3.6（cancel 接口与状态码）、
> `LlmRequestFlow.md` §5（`LlmProxyController.cancelQueue` → `concurrencyRegistry.cancel`）。
> 原 v1.0 非目标"不对接 cancel"的依据是"客户端中断即断连、断连即出队"；责任人澄清该语义为
> **断连后客户端主动补发取消通知（仅排队中）**，故该非目标撤销，本变更纳入同批次闭环。

### 方案概述

仍是一处上游接线 + 定制包承载，v1.0 的帧过滤不动：

```text
client.py::_open_stream                                service/aixcoding/llm_queue/queue_cancel.py
  request = self._build_request(...)                   QueueRequestTracker(request, model, base_url, api_key)
  tracker = track_queue_request(request, ...)            ├─ request_id = uuid4().hex → request["extra_body"]
    │  （+1 行接线；失败返回 None，回退 v1.0）            │   （profile 已带 request_id 时复用）
    ▼                                                    ├─ wrap(on_status)：position == -1 → 已放行，
  chunks = guard_queue_frames(                           │                   否则 → 仍在排队
      chunks, on_status=tracker.wrap(observer...))       └─ cancel_if_still_queued()
  finally:                                                   仅当"排队中"才 POST cancel（2s 超时，全吞错）
      await tracker.cancel_if_still_queued()
```

"是否仍在排队"的判据（复用 v1.0 已有语义，不新增协议理解）：

- `queue_status` 的 `position >= 0` 帧 ⇒ 排队中；
- `RELEASED_POSITION == -1` 是 guard 在**首个数据帧到达时**合成的放行信号（`queue_frames.py:61-62,123-126`）⇒ 已放行；
- 从未收到任何 `queue_status` ⇒ 未排队（直通），两种情形都不发 cancel。

### cancel 请求构造

```
POST {base_url 去尾斜杠、再去尾 /v1}/api/v3/chat/completions/cancel
Content-Type: application/json
token: <profile api_key>

{"model": "<client.model>", "request_id": "<本次 wire 请求 id>"}
```

- `model` 取 `self.model`（profile `model_id`，即网关 `modelKey`）。
- `base_url` 取 `str(self.sdk_client.base_url)`：mock 为 `http://127.0.0.1:8642/v1` → `http://127.0.0.1:8642/api/v3/chat/completions/cancel`；
  内网若为 `http://<host>/aicoding/v1` → `http://<host>/aicoding/api/v3/chat/completions/cancel`（与 §2.1 一致）。
- 独立 `httpx.AsyncClient`，`timeout=2s`，不复用 SDK 私有 `_client`；代理仍按环境变量（`trust_env` 默认开启，
  内网由 `NO_PROXY` 保证）。
- 结果处理：`204` 成功；`404 REQUEST_NOT_FOUND`、`409 REQUEST_ALREADY_RUNNING` 静默（契约内的正常结果）；
  其余状态/异常 `logger.debug/warning`，绝不上抛。

### 为什么挂 `_open_stream` 的 `finally`

四条中断路径（TUI `UserInterrupt`、ACP `session/cancel`、CLI Ctrl+C、stall/异常）最终都会让 `updates()`
生成器关闭并执行 `finally`（`client.py:295-300` 现有 `sdk_stream.close()` 已证明该路径可靠）。
挂在 client 层比在 `kernel.abort()` / `engine.coordinator` 处挂更少接触面，且 `sdk_client.base_url`/`api_key`/`model`
就在手边（`builder.py:485-493` 的注入点拿不到这三者）。

已知窗口：**放行到首个 token 的空窗期**（`ModelQueueFrontend.md` §3.4），客户端仍认定为"排队中"，
会多发一次 cancel → 服务端返回 `409` 被忽略。这是客户端可观测性的上限，代价为一次无副作用的旁路请求。

### 上游改动清单（R2，相对 v1.0 的增量）

| 文件 | 改什么 | 实际行数（+增/−删） | 标记注释位置 |
|---|---|---|---|
| `src/chrys/service/llm/chat_completions/client.py` | `_open_stream`：构造 tracker（13 行，含 lazy import）、`on_status` 交给 tracker 包装（+5/−4）、`finally` 用嵌套 `try/finally` 保证 `cancel_on_close` 在流关闭抛错/被取消时仍执行（+10/−9）；2026-11-20 C2 把 guard/tracker 改为同一次导入（+1 净行） | **+29/−9**（净 +20；相对 base 总计 +38/−5） | `# AIxCoding llm-queue: cancel queued request on abort` |
| `tests/architecture/trajectory_wait_manifest.json` | 生成产物：刷新后重新打开 10 条 wait（4 条新增在 `queue_cancel`、`updates` 的 5 条因函数 wait 数变化重排 + 新增第 6 条），全部保持默认 `unresolved` | +14/−1 | 无（`MARKER_EXEMPTIONS`） |

新增文件（非 R2）：`src/chrys/service/aixcoding/llm_queue/queue_cancel.py`、
`aixcoding/tests/llm/test_model_queue_cancel.py`、`llm_queue/__init__.py` 导出（+13/−1，含 `RELEASED_POSITION`）。

R2 报批说明：
- 首稿预估 +11，实际 **+28/−9**：tracker 构造块按仓库格式展开为 13 行（首稿低估了 lazy import 与多行参数），
  `on_status` 包装是"替换原 4 行调用"（+5/−4），`finally` 因评审要求"流关闭抛错/被取消时仍必须发 cancel"
  改为嵌套 `try/finally`（+10/−9），净增从 +17 变 +19。
- wait 清单首稿估 +5，实际 +14/−1：`_open_stream.updates` 的 wait 序号整体后移（新增第 6 条），
  加上 `queue_cancel` 内 4 条；均为 `unresolved`，无人工规则需要重新套用。
- **2026-11-20 评审 C2 修复**：`guard_queue_frames` 与 `track_queue_request` 改为同一次 lazy import；
  导入失败时不构造 tracker、不注入 `request_id`，消除「已带 id 但 guard 不可用、永不取消」的中间态。
  client.py 相对 base 实测 +38/−5；v1.1 增量由 +28/−9 变为 +29/−9（净 +20）。
  本条属正文 R2 变更，按 R10 需责任人重签头部（AI 未改）。
- 本变更使 R2 清单与定制点登记表发生变化，按 R10 需责任人把本文件头部状态退回「草案」后重签；
  AI 不改头部，实现前必须完成重签。

### 对外部行为的假设

1. 假设：OpenAI SDK 会把 `extra_body` 里的自定义键原样并入请求 JSON，且 `request_id` 不落入
   `PROTECTED_EXTRA_BODY_CHAT_OPTION_KEYS`（`profiles/models/options.py:72-104` 只管 profile 侧受管键）→
   失效表现：字段未发出 → 服务端随机生成 id → cancel 必然 `404`，日志可见，功能降级为"取消无效"而非崩溃。
2. 假设：网关按 `modelKey` + `request_id` 定位排队元素（`LlmRequestFlow.md:62,194`）→ 失效表现：cancel 恒 `404`。
3. 假设：`base_url` 形态为 `<gateway>/v1` 或 `<gateway>`（OpenAI 兼容前缀）→ 失效表现：cancel URL 404/连接失败，
   只记日志；**这是本变更最大的外部依赖**，需在联调时用真实 profile 核对一次。
4. 假设：`sdk_client.api_key` 即 `token` 头的合法值（契约 §2 第 38 行允许 `token` 头或 Bearer）→ 失效表现：`403`/`401`，
   仅影响 cancel。
5. 假设：`RELEASED_POSITION == -1` 是客户端可得的唯一放行信号（网关放行后不再推 `queue_status`）→
   失效表现：放行后仍判定"排队中"，多发一次 cancel → `409`，无害。
6. 假设：`finally` 在任务取消（`CancelledError`）时仍执行 → 失效表现：中断不发 cancel，行为回到 v1.0（不是回归）。
   CLI Ctrl+C 走 `asyncio.run` 取消，若取消发生在 loop 关闭前，cancel 任务可能来不及跑完（2s 超时上限），属已知限制。
7. **使用约束（2026-11-20 评审 C3）**：profile 显式配置 `request_id` 时复用该值（单飞行测试依赖）→
   同一 profile 的并发请求共享一个 id，网关的 position 心跳与 cancel 归属会交叉 →
   缓解：detail 日志提示复用；该字段仅用于单飞行测试，不作为并发特性。

### 定制点登记（增量）

登记行 `model-queue-client:queue-cancel`（预期计数 3）已并入上方 `## 定制点登记预告` 主表，与本批
`queue-frame-guard` 同行维护；`gen_customizations.py --strict` 以该表为准。

### 风险与最坏情况

- **URL 推导不成立**（假设 3）：cancel 全部落空，队列残留回到 v1.0 现状；日志可观测，不引入新故障。
- **误发 cancel**：放行空窗期多发一次 → `409`，服务端明确"已放行"，无副作用。
- **重复取消**：契约幂等（重复取消返 `404`），重试重发产生新 id，旧 id 在 abort 时被 cancel。
- **取消阻塞中断**：`2s` 超时上限 + 全吞错；若 `finally` 处于取消态，则跳过 await（不拖慢用户操作）。
- **代理/证书差异**：独立 `httpx.AsyncClient` 不复用 SDK 连接池；代理按环境变量（`trust_env` 默认开启），内网 `NO_PROXY` 已由环境保证。
- **profile 固定 `request_id` 的并发共享**（2026-11-20 评审 C3）：同一 profile 的多个并发请求会复用同一个 id，
  cancel 与 position 心跳的归属可能交叉；仅在单飞行测试场景使用，detail 日志会提示复用。
- 回滚：删除 `queue_cancel.py`、`client.py` 的 11 行接线与登记行，恢复 v1.0（无 `request_id`、无 cancel）。

### ADR 判定（增量）

- 风险点与 v1.0 同源：仍依赖上游非公开行为（SDK `extra_body` 合并、`finally` 在取消时执行）；不新增 ADR，
  在既有 `model-queue-client--queue-frame-interception` 的决策范围内。

---

## 变更单 v1.2（2026-11-23，责任人裁决）：所有 Chat Completions 请求携带 request_id

责任人在对话中选择方案 A，并要求流式/非流式都必须携带 `request_id`，主日志与落盘明细日志均有记录：

- 流式沿用 `track_queue_request`；生成/复用 id 与 cancel endpoint 推导解耦，推导失败时仍保留 id，仅不武装 tracker。
- 非流式 `_complete` 在 SDK 调用前执行同一 `attach_queue_request_id`，不接 tracker（非流式无排队帧）。
- 新生成与复用 profile id 均写模块主日志和 `aixcoding.detail.llm_queue` 明细文件通道（INFO）。
- 不扩展 anthropic/openai_responses：网关对接契约仅提供 Chat Completions 端点。
- wire 回归测试同时断言流式/非流式实际 JSON 顶层 `request_id`、profile 复用与双日志通道。

### 上游改动清单（R2，相对 v1.1 的增量）

| 文件 | 改什么 | 实际行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/service/llm/chat_completions/client.py` | `_complete` 发送前 lazy import 并 attach；失败仅记日志，维持原有降级行为 | +9/−0 | `# AIxCoding llm-queue: a blocking completion carries a request_id too` |
| `tests/orchestration/engine/test_settings_reload.py` | 重载等价比较前移除并校验两个不同的合法 `request_id`，其余请求体仍全字段相等 | +5/−1 | `# AIxCoding llm-queue: reload equivalence excludes the per-request correlation id` |

非上游改动：`queue_cancel.py` 拆分公开 attach、调整 tracker 推导顺序并双写 INFO 日志；`llm_queue/__init__.py` 导出；
新增 `aixcoding/tests/llm/test_llm_queue_request_id.py`，并同步 `aixcoding/tests/llm/test_model_queue_cancel.py` 两处旧行为断言。
登记行 `model-queue-client:queue-request-id`、`model-queue-client:queue-request-id-reload-test` 已并入主表。
本正文增量按 R10 仍需责任人本人重签头部，AI 未代填。
