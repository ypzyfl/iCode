# 模型并发排队 · 开发文档

> 适用：AIxCoding / iCode 内网版本（`feat/model-concurrency-queue` 分支）
> 读者：开发、测试、内网联调
> 日期：2026-11-20
> 关联批次：`aixcoding/docs/batches/model-queue-client/`、`aixcoding/docs/batches/model-queue-progress/`

---

## 1. 实现范围

| 层 | 内容 |
|---|---|
| 服务端 | 网关按 `modelKey` 的全局并发上限 + FIFO 队列（本仓库不实现） |
| 客户端 wire 层 | 吸收 `queue_status`、续活 stall 看门狗、转译终态拒绝、注入 `request_id`、排队中调用 cancel |
| 客户端进度层 | `GatewayQueueStatus` 事件 → TUI / CLI / ACP |
| 日志层 | 模块 logger（TUI/告警）+ `aixcoding.detail.llm_queue`（文件专用，CLI/TUI/ACP 通用） |

---

## 2. 总体数据流

```text
网关 SSE
  event:queue_status / queue_rejected / data:...
        │
        ▼
OpenAI SDK 解析（openai==2.54.0）
  queue_status  → ChatCompletionChunk(choices=None, model_extra={position,queueSize})
  queue_rejected→ 裸 openai.APIError(body={code,message,traceId})
        │
        ▼
service/aixcoding/llm_queue/queue_frames.py::guard_queue_frames
  ├─ 位置帧：吸收 + report_wire_progress() + on_status(QueueStatus)
  ├─ 放行：首个数据帧时合成 RELEASED_POSITION(-1)
  └─ 拒绝：QUEUE_TIMEOUT/QUEUE_CANCELLED → ProviderResponseError(retryable=False)
           QUEUE_FULL → 原样上抛（走既有重试）
        │
        ▼
service/llm/chat_completions/client.py::_open_stream
  ├─ track_queue_request(request, model, sdk) → tracker（cancel 凭据：请求头 token 优先，回退 api_key）
  ├─ tracker.observing(observer.on_queue_status) 包一层
  └─ finally: tracker.cancel_on_close()  （仅仍在排队时发 cancel）
        │
        ▼
WireCallObserver.on_queue_status
        │
        ▼
orchestration/engine/build/construction.py::_on_queue_status
  bus.publish(GatewayQueueStatus(session_id, position, queue_size))
        │
        ├─ TUI：订阅 → WaitingRow 文案
        ├─ CLI：TurnProgress.handle → stderr 行（同 position 去重）
        └─ ACP：server → chrys/queue_status 扩展通知
```

---

## 3. 代码落点

### 3.1 定制包（无 R2）

| 文件 | 职责 |
|---|---|
| `src/chrys/service/aixcoding/llm_queue/queue_frames.py` | 帧识别、吸收、心跳续活、终态转译、`QUEUE_FULL` 放行、日志 |
| `src/chrys/service/aixcoding/llm_queue/queue_cancel.py` | `request_id` 注入、cancel URL 推导、排队中取消、响应处理、日志 |
| `src/chrys/service/aixcoding/llm_queue/__init__.py` | 公开导出 |
| `src/chrys/kernel/aixcoding/queue_progress.py` | TUI/CLI 共用文案：`queue_note(position, queue_size)` |

### 3.2 上游接线点（已签认 R2）

| 文件 | 接线 |
|---|---|
| `src/chrys/service/llm/chat_completions/client.py` | tracker 构造；guard 包裹 chunk 迭代；`finally` 取消；定制不可用 WARNING |
| `src/chrys/service/llm/observer.py` | `WireCallObserver.on_queue_status` 回调参数 |
| `src/chrys/service/llm/clients.py` | `create_client(... on_queue_status=...)` 透传 |
| `src/chrys/orchestration/engine/build/builder.py` | 构造参数透传 |
| `src/chrys/orchestration/engine/build/construction.py` | `bus.publish(GatewayQueueStatus(...))` |
| `src/chrys/foundation/events/types.py` | `GatewayQueueStatus(Event)` 事件类型 |
| `src/chrys/orchestration/session_host.py` | `_HEADLESS_RUN_EVENT_TYPES` 加入事件类型（否则 CLI/ACP 静默丢弃） |
| `src/chrys/app/tui/screens/main/` | 订阅、handler、WaitingRow 渲染、协议与 presenter |
| `src/chrys/app/cli/progress.py` | `TurnProgress.handle` 新 case + 同 position 去重 + `TurnStarted` 清零 |
| `src/chrys/app/acp/server.py` | `chrys/queue_status` 通知 + 同 position 去重 + `released` |

### 3.3 测试

| 文件 | 覆盖 |
|---|---|
| `aixcoding/tests/llm/test_model_queue_frames.py` | 帧吸收、usage、心跳、终态转译、`QUEUE_FULL`、契约漂移、日志 |
| `aixcoding/tests/llm/test_model_queue_cancel.py` | request_id、cancel 报文、状态码、超时、URL 推导、日志 |
| `aixcoding/tests/llm/test_model_queue_progress.py` | 事件回调/文案/前端消费 |
| `aixcoding/tests/llm/conftest.py` | `detail_records` fixture（捕获文件专用通道） |

运行：

```bash
uv run pytest aixcoding/tests/llm -n0 -q
```

---

## 4. 关键行为

### 4.1 帧判据

```python
choices is None
and "position" in chunk.model_extra and "queueSize" in chunk.model_extra
and type(position) is int and type(queueSize) is int
and chunk.id is None and chunk.usage is None
```

- 不满足判据的 `choices=None` 帧保持原 invalid response 行为（fail-loud）。
- 若帧带 `position`/`queueSize` 但被拒（多了 `id`/`usage`、`choices=[]`、字段类型不对），输出 WARNING/detail，避免只看到最终 invalid response。

### 4.2 心跳与放行

- 每吸收一帧调用 `report_wire_progress()`，重置 stall 看门狗空闲计时。
- 首个数据帧到达且此前吸收过位置帧 → 合成 `RELEASED_POSITION = -1`，通知前端清文案。
- detail 日志记录「排队等待 N.N 秒后放行」，便于内网量化排队时长。

### 4.3 终态与重试

| 网关 code | 客户端处理 |
|---|---|
| `QUEUE_TIMEOUT` / `QUEUE_CANCELLED` | `ProviderResponseError(code, message, retryable=False)`，根因 `APIError` 在 `__cause__` |
| `QUEUE_FULL` | 原样上抛，保持可重试（既有 3/7/15… 退避） |
| 其他 | 原样上抛，分类不变 |

### 4.4 `request_id`

- 位置：`client.py::_open_stream` 构造 tracker 时写入 `request["extra_body"]["request_id"]`。
- 生成：`uuid.uuid4().hex`（32 位）。
- 复制：写入前 `dict(extra)` 拷贝，避免污染调用方 options。
- profile 已带 `request_id` 时复用。
- 非流式 `_send` 不建 tracker、不注入。

### 4.5 取消排队

- 触发：`_open_stream` 的 `finally` → `tracker.cancel_on_close()`。
- 条件：`self._position_seen and not self._released`。
- URL 推导：

```text
base_url 去掉尾部 /api/v3、/api/v2、/api/v1、/v1
  → <root>/api/v3/chat/completions/cancel
```

- 请求：`POST`，body `{"model", "request_id"}`，header `token`，超时 2s。
- 响应：`204` 成功；`404`（未排队/已完结/已取消）与 `409`（已放行）按正常 no-op；其他状态/网络错误只记日志。
- 取消任务用 `_PENDING_CANCELS` 持有强引用，避免取消场景下被回收。
- 当前处于取消态时，`cancel_on_close` 不 `await`，避免拖慢中断。

---

## 5. 日志设计

### 5.1 两个通道

| 通道 | 内容 | 可见形态 |
|---|---|---|
| 模块 logger `chrys.service.aixcoding.llm_queue.*` | 用户可感知事件：首帧、放行、终态拒绝、回调失败、取消发起/结果/跳过 | TUI `debug.log`（INFO+）；CLI/ACP 的 WARNING 走 stderr |
| `aixcoding.detail.llm_queue` | 技术细节：解析后的帧、心跳、排队耗时、cancel 报文/响应 body、tracker 就绪 | **文件专用**，CLI/TUI/ACP 都写 `aixcoding.detail.log` |

> CLI 没有 INFO 文件日志；CLI/ACP 的详细取证必须看 `aixcoding.detail.log`。

### 5.2 路径

| 平台 | 路径 |
|---|---|
| Windows | `%APPDATA%\chrys\aixcoding-logs\aixcoding.detail.log`；TUI 另有 `%APPDATA%\chrys\logs\debug.log` |
| Linux / macOS | `~/.chrys/aixcoding-logs/aixcoding.detail.log`；TUI 另有 `~/.chrys/logs/debug.log` |

### 5.3 关键日志

```text
网关排队：position=2 queueSize=5
网关排队帧（解析后）：{'id': None, 'choices': 'null', 'usage': None,
  'model_extra': {'position': 2, 'queueSize': 5, 'traceId': '...'}}
网关排队心跳：position=1 queueSize=4（第 2 帧），解析后：...
网关已放行排队请求（此前收到 2 个排队帧）
网关排队等待 12.3 秒后放行
排队放行后收到首个数据帧：{'id': 'chatcmpl-...', 'choices': 'list[1]', ...}
网关拒绝排队请求：code=QUEUE_TIMEOUT retryable=False，响应解析：{...}
网关队列已满（QUEUE_FULL），交由 wire 重试通道退避；响应解析：{...}
无法识别的网关排队帧：choices=... id=... usage=... position=... queueSize=... model_extra=...
排队状态回调失败，前端将看不到本次排队更新
网关排队取消已就绪：request_id=... endpoint=... model=... base_url=... token来源=请求头|api_key
正在离开网关队列：POST <url>，model=...，request_id=...
发送取消排队请求：POST <url>，body={'model': '...', 'request_id': '...'}，token=已携带
取消排队响应：status=204，请求已出队（request_id=...，endpoint=...）
取消排队响应：status=404，body='{"error":{"code":"REQUEST_NOT_FOUND",...}}'（...）
网关排队取消跳过：没有可用 token，请求将留在队列中（request_id=...）
网关排队取消无法连接 <url>（request_id=...），请求可能仍在队列中
```

不记录：模型回答正文、`token` 值、完整请求头、原始 SSE 字节。

---

## 6. 配置与部署

### 6.1 模型 profile

| 字段 | 要求 |
|---|---|
| `provider` | `openai`（内部网关统一走 OpenAI 兼容链路） |
| `api_style` | `chat_completions` |
| `base_url` | 必须能拼出文档的 completion 路径，例如 `http://<host>/aicoding/api/v3`（SDK 再拼 `/chat/completions`） |
| `http_read_timeout` | 默认 300s；必须大于网关 `queue_status` 心跳间隔（约 20s） |
| `api_key` | 取消请求 `token` 的**回退**来源；v1.5 起优先用主请求自带的 `token` 头（登录态注入），两源皆空才跳过 cancel |
| `bypass_proxy` / `verify_ssl` | 只影响主请求；取消请求不继承 |

### 6.2 网关侧

- 排队只在模型配置了并发上限时触发：`max_concurrency` / `max_queue_size` / `max_wait_time`。
- 测试时使用**专用测试模型**或测试环境，不要在生成环境随意把线上模型并发调到 1。

### 6.3 回退

- 定制包导入失败：上游流式照旧，WARNING `aixcoding llm-queue 定制不可用: 网关排队帧将导致流失败`。
- 回退时无 `request_id`、无 cancel、无排队提示；此时不应把「没有排队行为」当功能缺陷，先排查安装包/导入。

---

## 7. 已知问题与待办

1. ~~**cancel 鉴权与登录态不同源**~~ **已修复（2026-11-25，design v1.5）**：cancel 凭据改为「原请求 `token` 头优先，回退 profile `api_key`」，与主请求同源——网关用什么凭据入队，就用什么凭据取消。纯登录态不再跳过；仅两源皆空才跳过（WARNING：`网关排队取消跳过：没有可用 token`）。
2. **cancel 不继承代理/TLS 配置**：独立 `httpx.AsyncClient`，内网代理或自签证书需专项验证。
3. **CLI Ctrl+C 可能漏发 cancel**：事件循环关闭时序；以 TUI/ACP 验证为主。
4. **ACP 通知失败可能冒泡**：`ext_notification` 异常未被吞掉，属健壮性问题。
5. **原始 SSE 不可见**：guard 只拿解析后的 chunk；需要原文用 curl 或 raw HTTP capture。
6. **`queueSize` 不展示**：事件/ACP 仍携带，文案只讲 `position`。
