# 设计：客户端对接模型并发排队（model-queue-client）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：草案
- 确认日期：
- 确认意见：尽量不改上游，若必须要改，要少而集中的改（可选；审阅中形成的判断、附加条件或保留）
- 待重签说明（2026-11-18 自审后）：R2 清单新增 `tests/architecture/trajectory_wait_manifest.json`（+5），`client.py` 行数按实际改为 +10/−0；正文同步补假设 5 的测试边界与登记 risk 行数。

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
| `src/chrys/service/llm/chat_completions/client.py` | `updates()` 内把 `chunks` 换成 `guard_queue_frames(chunks)`：函数内 lazy import 定制包，任何异常回退原迭代器（全吞错） | +10/−0 | `# AIxCoding llm-queue: guard gateway queue frames (src/chrys/service/aixcoding/llm_queue)` |
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

## 风险与最坏情况

- 判据过宽：把其他 `choices=None` 的合法帧当排队帧丢弃 → 静默丢 usage。缓解：判据要求 `model_extra` 同时含 `position`、`queueSize` 且均为 `int`，并断言无 `id`/`usage`；测试覆盖"`choices=None` 但无排队字段"仍报 invalid response。
- progress 续活失效：见假设 5。定制测试锚定"丢帧 → 上报 progress"的调用点；scope 传播本身在上游，不在本批测试射程内（test-plan 已标注该局限）。
- 转译不命中：`body`/`code` 形态变化 → 退回重排队（可用性尚存，负载放大）。
- `QUEUE_CANCELLED` 在 iCode 场景可达性低（不接 cancel 接口、断连即出队）→ 属**防御性覆盖**，保留以免服务端策略变化时误重试。
- 回滚：删除接线并移除定制包，行为完全回到当前状态（无数据格式、无持久化、无对外契约变化）。

## ADR 判定

- ① 有被认真考虑但否决的备选（A/B/C/D/E）：**是**
- ② 撤销代价高：否（删除 10 行与 1 条 wait 清单行即回滚）
- ③ 约束未来工作模式：否（第二批 UI 另行设计作用域，本批不留进程级状态）
- ④ 依赖上游非公开接口或行为（SDK 对未知事件的处理、`classify` 的 `explicit_retryable` 短路、stall 看门狗的 progress 机制）：**是**

→ 出 ADR：`standards/adr/model-queue-client--queue-frame-interception.md`。
