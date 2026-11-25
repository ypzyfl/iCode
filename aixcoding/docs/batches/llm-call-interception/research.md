# 调研：进程内大模型 HTTP 调用拦截

> 调查日期：2026-11-24；补充调研：2026-11-25。本文记录只读调查、多轮外部 AI 复核及范围重估，
> 不作为实施授权。

## 1. 最终需求归纳

本质需求是一个**进程内、带调用归属信息的模型流量策略层**：能够读取、修改或拒绝实际模型 HTTP
流量，并知道流量属于哪个 session、turn、逻辑模型调用和实际发送。

当前约束：

- 读取、修改和阻断 request/response 的 HTTP headers 与 body；
- 定制代码在 iCode 进程内执行，排除进程外代理和外部 hook；
- 零上游或极少上游改动；
- 默认开启、允许失效降级，但失效必须留日志；
- 当前不需要逻辑调用级恰好一次 pre/post，也不需要上游组装后的完整语义 `ChatResponse`；
- 本步选择“能力就绪、默认空策略”：通用 HTTP 读写改拦能力在 AIxCoding 定制代码中实现，但不写业务规则；
  空策略不附加定制 hooks，不读 body、不复制 headers、不解析 JSON/SSE、不替换流，不产生固定 hook 调用开销。

因此最终选择仅为 HTTP 层。曾讨论的逻辑层显式接线方案作为备选调研保留，不在本期实施；当前 HTTP 结构
需给未来独立逻辑层留下清晰边界，而不是强迫未来复用 HTTP 上下文或流处理。

## 2. 调查方法与版本

调查基于当前工作树静态读码、已安装依赖源码、最小 Python ContextVar 语义实验和只读导入测量：

- `httpx==0.28.1`
- `openai==2.54.0`
- `anthropic==0.125.0`

未修改产品文件，未进行真实外部模型端到端请求。SDK、HTTPX 与 Chrys 的隐式行为必须由后续测试锚定。

## 3. 调用层次与 HTTP 统一覆盖

```text
ToolLoopLayer.get_response()
  └─ 整个模型/工具运行，可能有多次逻辑模型调用
      └─ _WireCaller.blocking_response() / streaming_response()
          │  一次逻辑模型调用，含 retry/poll/fallback
          └─ _WireCaller._call()
              │  一次 Chrys wire acquisition
              └─ ChatMiddlewareLayer
                  └─ WireClient
                      └─ OpenAI / Anthropic SDK
                          └─ 共享 httpx.AsyncClient
                              一次实际 HTTP 往返；含 SDK retry 和 redirect
```

生产 SDK Client 只在 `src/chrys/service/llm/clients.py` 构造。HTTPX 统一覆盖 Chat Completions、
Responses（含 retrieve/poll）、Anthropic Messages，以及主 Agent、内置 sub-agent、workflow、审批 judge、
标题生成和 compaction 等真实 HTTP 调用。外部 ACP sub-agent 是独立进程，`mock` provider 不走 HTTPX。

关键位置：HTTP 工厂 `clients.py:264-324`，总工厂 `404-516`，SDK 共用 Client `525-543`，协议分发
`wire_client.py:208-245`。

## 4. 调用归属：上游已有，不需新建逻辑 ID

### 4.1 TrajectoryContext 已进入 HTTP request extensions

`src/chrys/service/llm/request_tracking.py:65-83` 在每次实际 HTTP 请求前写入：

- `request.extensions["chrys_request_attempt_id"]`；
- `request.extensions["chrys_request_trajectory_context"]`。

response hook 通过 `response.request.extensions` 读取同一上下文（`request_tracking.py:85-106`）。
AIxCoding hooks 排在 tracking 后即可在请求和响应两侧取得调用归属。

`TrajectoryContext` 定义于 `foundation/trajectory/context.py:109-119`，包含：

| 字段 | 含义与策略用途 |
|---|---|
| `session_id` | 真实会话 ID |
| `turn_id` | 当前用户轮次，可空 |
| `cycle_operation_id` | 一次逻辑模型调用，含其全部发送 |
| `exchange_operation_id` | 一次 Chrys wire acquisition，重试可产生新值 |
| `request_attempt_id` | 一次实际 HTTP 往返，SDK 重试和重定向可产生新值 |
| `actor.kind` / `actor.role` | 主 Agent、sub-agent、workflow、审批、标题、compaction 等 |

`SessionTrajectory.context()` 直接构造上下文，不检查落盘状态（`service/trajectory/session.py:312-322`）。

### 4.2 边界

- 请求头中的 session 路由 ID 可能是派生值，不能替代真实 `TrajectoryContext.session_id`。
- 标题生成等调用可能发生在 turn 外，`turn_id=None`；必须保持缺失，不伪造。
- `cycle_operation_id` 可用于归并同一逻辑调用下的 HTTP attempts，但不提供逻辑级恰好一次 hook。
- `exchange_operation_id` 是 trajectory operation ID；不能未经消费方确认就宣称等于外部 OTel span ID。
- actor role 已允许策略过滤辅助调用，无需修改逻辑层增加用途标识。

## 5. 现有扩展机制比较

| 机制 | 能力 | 缺口 | 结论 |
|---|---|---|---|
| 模型配置字段 | 预设部分请求字段 | 无动态响应和通用阻断 | 不满足 |
| `raw_http_log` | 读取最终请求、响应和普通/流式 body | 不修改、不阻断 | 技术参考 |
| ChatMiddleware | 语义 messages/options、解码后响应和 updates | attempt 级、无原始 HTTP、部分旁路不可见 | 后续按需叠加 |
| `ResponseStream` hooks | 语义 update 转换、最终响应处理 | 无原始 headers/body | 当前不需要 |
| Python Extension / YAML Hooks | 工具、上下文、prompt 等事件 | 无完整模型 HTTP 事件；YAML 还涉及外部进程 | 不满足 |
| OTel / EventBus | 语义观测 | 非原始 HTTP 控制层 | 不满足 |
| Anthropic 官方 middleware | SDK 选项层 headers/JSON | 仅 Anthropic，OpenAI 无统一对应物 | 否决统一方案 |
| HTTPX event hooks | 原始请求/响应读写改拦 | 上游未提供 AIxCoding 注册入口 | **主干** |
| HTTPX Transport | 上述能力及本地合成响应 | 影响代理装配，维护面大 | 仅未来合成响应时考虑 |
| 各协议请求构建函数包装 | provider JSON 和 headers | 无响应侧、轮询覆盖不全 | 不作主干 |

结论：没有配置即用的完整机制；HTTPX hooks 加响应流包装是当前最小统一实现。

## 6. HTTPX 行为事实

### 6.1 请求与普通响应

- request hook 在认证注入后、重定向循环内，每个实际 attempt 执行；
- response hook 在普通响应预读前执行，可在 SDK 解析前完整读取、修改或阻断 body；
- 现有参考实现为 `src/chrys/service/llm/raw_http_log.py:67-198`；
- `httpx.MockTransport` 等已缓冲响应可能预置 `_content`，真实网络响应通常走 stream，必须分别处理。

### 6.2 流式响应是不完整的字节块

response hook 初始只有 status、headers 和未消费完的 `response.stream`。后续每次迭代得到网络 chunk：

- 可能只有半个 SSE 事件；
- 可能包含多个事件；
- 可能在 UTF-8 字符或 JSON 字段中间断开。

`raw_http_log.py:143-198` 也只是 `_chunks.extend(chunk)` 后原样转发，最终拼接用于日志。OpenAI SDK
则另外通过 SSEDecoder 处理字节块和事件边界（`openai/_streaming.py:161-163、317-321`）。

因此 HTTP 策略若处理流式 body，必须自行缓冲到完整 SSE 事件。若需要完整原始 body，必须缓存整个流；
本批只按完整 SSE 事件处理，不提供全流聚合修改。

### 6.3 与完整语义响应的区别

上游逻辑流会把语义 updates 通过 `ChatResponse.from_updates()` 组装为最终 `ChatResponse`
（`kernel/_types.py:931-967、2049-2065`）。这能免除 SSE 和语义内容拼装，但：

- 不提供原始 HTTP headers/body；
- updates 仍是增量的；
- 最终响应形成时，之前的 updates 通常已交付；
- 修改 update 不自动同步最终响应，修改最终响应也不会撤回已显示内容。

当前不需要“免拼装、处理完整语义响应”，所以不引入逻辑层。若未来需要，应单独评估逻辑层或
ChatMiddleware，并明确是否需要全流缓冲门控。

## 7. 异常、重试与 Block

### 7.1 SDK 请求循环内

request、response-header 和普通 body 阶段位于 SDK 请求循环内：

- OpenAI 透传 `OpenAIError`；普通异常可能重试并最终包装为 `APIConnectionError`；
- Anthropic 透传 `AnthropicError`；普通异常包装为 `APIConnectionError` 后可能重试；
- Chrys 还会沿异常链分类并进入 wire retry。

主动阻断必须按 provider 使用可透传且 Chrys 不重试的异常，不得直接抛普通异常或复用
`APIConnectionError`。

### 7.2 完整异常图与短语

`iter_full_chain` 会跟随 `__cause__` 和未抑制的 `__context__`；legacy 层还匹配 "connection closed"
等短语。因此：

- 使用 `raise ... from None`；
- 控制 cause、context、args、状态码和类型名；
- 对外固定文本，reason 仅进 detail；
- 最终异常经公开 `classify_error()` 验证 `retryable=False`、`transient=False`；
- 首版不修改公共错误分类器。

### 7.3 流式与失效

SSE 转换器已离开 SDK 请求重试循环，可使用 AIxCoding 非重试异常。Responses 等 wire 层可能重包装，
识别沿异常链。Chrys 在已输出答案文本后不会重放请求。

安装失败或任意策略业务异常均不得外溢到宿主工作流，原始报文继续并记录日志；定制结果归一化、报文应用和
SSE 解析也必须位于同一隔离边界内。`Block` 是受控的单次模型调用终止结果，由上层正常呈现，不能导致应用
崩溃，也不能被 fail-open 吞掉。宿主取消和进程控制信号不属于可吞掉的业务异常。

## 8. 接入方案与最终选择

### 8.1 当前采纳：启动期运行时包装

`aixcoding_startup()` 在 CLI 命令分发前执行。HTTP 安装任务幂等包装
`clients._build_profile_http_client`，调用原工厂后仅在已注册非空策略时注入 hooks。产品代码位于
`src/chrys/service/aixcoding/llm_call_interception/`，上游手写行为文件零改动；架构 wait manifest 是唯一的
强制生成物例外。

外部独立评审实证：运行时包装经真实 CLI startup 进入同进程上游测试后，精确 route/default hook 清单会失败；
因此默认空策略必须保持原始 hooks，不能仅靠 Smart Test。另一实证是上游兼容网关会双向误标 Content-Type，
普通/SSE 分派必须按实际 identity body 的前 512 字节分类窗口判断，并完整回放跨界 chunk，保持 SSE 增量交付。

优点：默认开启工厂包装、空策略零上游行为差异、原始 HTTP 全覆盖。缺点：依赖私有工厂；业务策略须先于目标
Client 创建注册，既有未附 hooks Client 不做追溯覆盖。

### 8.2 HTTP 四场景选型矩阵

| 场景 | 推荐接入方式 | 必须接受的条件 |
|---|---|---|
| 默认关闭、配置启用 | 方案二：显式修改 `clients.py`，默认不挂 hooks | 上游源码只有一个接入点，默认 hook 清单测试可保持不变 |
| 默认开启、允许失效降级 | 方案一：AIxCoding 启动期运行时包装 | ADR、真实 `create_client()` 契约测试、安装失败显式告警 |
| 失效不可放行 | 优先方案二，默认挂载 | 接受一个上游源文件及相关上游测试调整；hook 构建或加载失败必须使请求失败 |
| 失效不可放行且零上游文件是硬约束 | 只能采用方案一 | 修改 AIxCoding 自有 startup 聚合，使安装失败终止启动；另以契约测试发现上游绕路 |

本批选择第二行，其余保留为未来重审依据。默认显式挂载 hooks 会影响
`test_default_http_client_parity.py`、`test_clients_factory.py` 和 `test_route_extension_wire.py`
的精确清单断言。

## 9. 逻辑层方案评估记录（当前不实施）

曾考虑在 `kernel/loop.py` 保留两个公共逻辑调用方法为薄壳、原方法体移为核心实现，并让 stall
fallback 直接调用核心实现，以实现每逻辑调用一次 pre/post。该方案被称为“逻辑层显式接线方案”。

调研结论：

- 它能提供每逻辑调用一次的语义 pre/post，并利用上游组装后的最终 `ChatResponse`；
- 它不提供原始 HTTP headers/body，也不能替代 HTTPX；
- 它需要修改一个上游核心文件，并处理共享 options、fallback 和原流对象身份；
- 早期运行时包装逻辑层的 ContextVar 防重入方案已被否决：跨任务关闭流时 reset 会失败；
- 代理逻辑流也被否决：上游会直接清理和读取原流的 `updates`，代理可能破坏身份一致性；
- 共享 options 含 continuation token 和后续 tool_choice，不能直接改写后整体恢复。

既然当前不需要逻辑级 hook 和完整语义响应，上述成本没有必要承担，相关 ADR 草案已撤回。未来若重新
需要，应基于本记录重新立项，而不是恢复为当前批次的隐含范围。

## 10. 残余风险与验证义务

1. 私有 HTTP 工厂及上游绕路：真实 `create_client()` 契约测试和升级覆盖复核。
2. HTTPX hook 时序、缓冲响应、SDK 异常和 Chrys 分类：行为测试锚定。
3. 普通与流式响应差异：必须显式构造跨 chunk、多事件/chunk、提前关闭和取消测试。
4. 调用归属：主 Agent、辅助调用、派生路由 session、空 turn 和多次 attempts 的 ID 断言。
5. 允许失效降级：启动和运行期日志是底线，不用于安全硬阻断。
6. 已转发事件不可撤回；完整审查后再显示需要未来另行全流缓冲设计。
7. 策略运行在事件循环上，不得阻塞 TUI。
