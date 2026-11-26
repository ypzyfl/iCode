# 设计：默认降级的进程内大模型 HTTP 调用拦截（llm-call-interception）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-26
- 确认意见：无特别意见

## 方案概述

HTTP 拦截器在**首次注册非空策略时**安装：`set_http_policy()` 幂等包装
`chrys.service.llm.clients._build_profile_http_client`；包装器先调用原工厂，仅当进程内已注册非空策略时，才向共享
`httpx.AsyncClient` 注入 AIxCoding request/response hooks。不接入 `aixcoding_startup()`：默认（未注册策略）启动路径
不导入本模块、不改动任何上游模块属性。启动期无条件安装在默认策略为空时仍会替换上游工厂，每次 `aixcoding-cli`
调用多约 18–20 ms 与 18 个模块（真实启动路径实测，见 verification.md “启动成本测量更正”），没有功能收益，故不采用。
全部策略调度、报文处理、
异常控制和资源管理位于 `src/chrys/service/aixcoding/llm_call_interception/`，上游手写行为文件零改动。唯一例外是
架构门禁强制生成的 `tests/architecture/trajectory_wait_manifest.json`：仅用上游生成器登记本模块异步 wait 节点，
不改变上游运行时行为。

```text
SDK 构造最终请求
  → route / tracking hooks（写入真实 TrajectoryContext 和 attempt id）
  → AIxCoding request hook（读取/修改/阻断）
  → raw_http_log（记录实际发送报文）
  → 网络

网络响应
  → route / tracking hooks
  → raw_http_log stream wrapper（记录网络原始响应）
  → AIxCoding response hook / stream wrapper（读取/修改/阻断）
  → SDK 解析
```

本批只实现 HTTP 层，交付通用读取、修改和阻断能力，但**默认定制策略为空，不实现任何业务处理逻辑**。
默认空策略下既不安装工厂包装，也不附加定制 hooks，因此没有启动期模块导入，也没有固定 hook 调用、body 读取、
headers 复制、JSON/SSE 解析或响应流替换开销。
业务策略必须在目标 Client 创建前注册：注册时安装工厂包装，之后创建 Client 时才获得定制 hooks。对注册前已经
创建且未附 hooks 的 Client 不提供追溯安装或弱引用注册表。已附 hooks 的 Client 在策略原子替换后继续由新策略
驱动。

本批不修改 `kernel/loop.py`，不增加逻辑调用级 pre/post，也不处理上游已组装的完整语义 `ChatResponse`。
普通响应 body 可完整处理；流式响应按完整 SSE 事件处理，网络 chunk 不视为完整响应。

## 定制模块与改动清单

### 新增产品模块

```text
src/chrys/service/aixcoding/llm_call_interception/
├── __init__.py       # HTTP 策略注册入口与公共类型重导出
├── context.py        # HttpCallContext、修改结果、Block 与上下文提取
├── interceptor.py    # 单组合 HTTP 策略、进程内持有、注册触发安装、非重试异常与降级
├── installer.py      # HTTP 工厂包装、幂等标记、hook 顺序安装
└── hooks.py          # 请求/响应调度、body 替换、普通流与 SSE 事件流包装
```

- 首版只持有一个组合 HTTP 策略；多个业务规则由该对象内部组合，不做外部插件发现和优先级框架。
- `_policy is None` 时安装器保持原 Client hooks；非空策略只影响其后创建的 Client，调用方负责在创建前注册。
- `set_http_policy()` 注册非空策略时幂等安装：先安装后保存策略，两者之间不让出事件循环；`set_http_policy(None)`
  只清空策略，不卸载已安装的包装。安装只加载必要模块并替换模块属性；SDK 异常类型和具体报文处理延迟到实际调用。
- 工厂包装使用 `functools.update_wrapper` 的真实契约是与上游 `inspect.unwrap` 惯例兼容，而不是仅靠 `inspect.signature`
  跟随 `__wrapped__` 证明参数正确；参数名、kind 和全部 kwargs 转发必须独立断言。
- 产品代码落 service 档：实际依赖为 `chrys.service.llm.clients`、request extensions 中的 trajectory
  类型、HTTPX/SDK 类型。注册入口与安装都在本模块内完成，不依赖 app 档启动组合。

### 启动组合零改动

- 不修改 `src/chrys/app/aixcoding/startup/`：`aixcoding_startup()` 的任务清单保持主干原状，安装由
  `set_http_policy()` 触发。
- 不修改 `aixcoding/tests/diagnostics/test_entry_wiring.py`：该文件相对主干净零改动。
- 不采用“启动期先判空、非空才安装”：启动期业务代码尚未运行，策略必为空，该任务恒为空转、没有功能作用；策略
  生效仍须由注册触发安装。其成本本身可忽略（真实启动路径上多 3 个模块）。

### 新增定制测试

- `aixcoding/tests/llm_call_interception/`：覆盖注册触发安装与安装幂等、注册期安装失败降级、真实工厂契约、
  调用归属、请求/响应读写改拦、普通与 SSE、缓冲响应、重试分类、降级日志、并发隔离和资源关闭。
- 不修改上游手写测试，不 import 上游 `tests/support/`。

**R1/R2 自查**：全部业务逻辑均在定制模块；运行时只包装一个统一 HTTP 工厂，上游手写源码、测试、构建和打包
文件均不修改，因此没有上游 marker。私有工厂及行为锚点由 ADR、假设和真实契约测试承载。

### 上游改动清单（R2）

| 文件 | 改动 | 审批依据 |
|---|---|---|
| `tests/architecture/trajectory_wait_manifest.json` | 官方生成器新增本模块 **28 个 wait 节点（+64 行）**；不改手写测试和运行时行为 | 2026-11-25 生成物范围专项裁决及 design/ADR 重签；增量复审呈报行数 |

除上述生成物外，本批不得修改其他上游文件；不得依赖其他批次的 R2 存量登记替代本行。

## 与未来逻辑层的边界

- 当前公共类型明确命名为 `HttpCallContext`、HTTP 策略和 HTTP 注册入口，不把 HTTP 原始报文上下文抽象成
  未来逻辑层也必须复用的通用调用上下文。
- 未来逻辑层可在 kernel 档建立独立模块、独立策略注册和独立生命周期，处理 messages、语义 updates 或完整
  `ChatResponse`；是否需要修改 `kernel/loop.py` 由届时需求重新评估，本批不作预先承诺。
- 两层未来只通过现有 session/turn/cycle/exchange/attempt IDs 关联，不共享可变报文状态或流对象；需要共享
  `Block` 等基础类型时再按依赖方向确定落点，本批不提前创建 kernel 公共包。
- 当前 HTTP 实现不替未来逻辑层决定同步/异步 pre、options 写能力或完整语义响应缓冲方式，避免 HTTP 方案
  成为未来独立逻辑设计的约束。

## 调用归属上下文

### 来源

上游 `build_request_tracking_hooks()` 在每次实际请求前写入：

- `request.extensions["chrys_request_attempt_id"]`；
- `request.extensions["chrys_request_trajectory_context"]`。

AIxCoding request hook 排在 tracking 之后；response hook 通过 `response.request.extensions` 读取同一
上下文。自定义 HttpCallContext 只保存必要字段，不新建或篡改上游 ID。

### 字段语义

| 字段 | 来源与用途 |
|---|---|
| `session_id` | 直接读取 `TrajectoryContext.session_id`；有有效上下文时为真实会话 ID，无上下文时为 `None`，不从请求头推导 |
| `turn_id` | 直接读取 `TrajectoryContext.turn_id`；无当前用户轮次或无上下文时为 `None`，不从 session 或请求头推导 |
| `cycle_operation_id` | 直接读取 `TrajectoryContext.cycle_operation_id`；标识一次逻辑模型调用并关联其全部发送，无上下文或未设置时为 `None` |
| `exchange_operation_id` | 直接读取 `TrajectoryContext.exchange_operation_id`；标识一次 Chrys wire acquisition，重试可产生新值，无上下文或未设置时为 `None` |
| `request_attempt_id` | 读取 `request.extensions["chrys_request_attempt_id"]`，仅接受字符串；标识一次实际 HTTP 往返，SDK 重试和重定向可产生新值，缺失或类型不符时为 `None` |
| `actor.kind` / `actor.role` | 直接读取 `TrajectoryContext.actor` 的只读字段，区分主 Agent、内置 sub-agent、workflow、审批 judge、标题、compaction 等；无上下文时 `actor=None` |
| provider / model | 安装 HTTP Client hooks 时分别读取并闭包保存 `ModelProfile.provider`、`ModelProfile.model_id`，不解析请求 body 或请求头 |

- 请求头中的 session 路由 ID 可能是派生值，不作为真实 session id 来源。
- `session_id` / `turn_id` 为 `None` 是合法输入，不触发框架异常；业务策略必须显式判空，策略误用空值产生的异常按
  containment 规则隔离并回退原始报文。
- `cycle_operation_id` 只用于归并和关联，不在本批实现逻辑调用级恰好一次 hook。
- 不宣称任何 trajectory ID 天然等于外部 OTel span ID；如未来需要映射，由消费方明确指定字段。

## HTTP 策略契约

策略接收 HttpCallContext 与当前阶段的 headers/body 视图，返回：

- `None`：不修改；
- 修改结果：替换 headers 和/或 body；
- `Block(reason)`：主动终止。

hook 在策略成功返回后才一次性应用修改；策略内部异常不应用部分结果，回退当前原始请求、响应或 SSE
事件并记录 detail。`Block` 走独立控制路径，不得被 fail-open 吞掉。

### 定制异常隔离边界

- 策略调用、结果归一化、headers/body 修改应用和自定义 SSE 调度均置于 AIxCoding containment 内；任何
  定制业务异常都不得逃逸到 SDK、Chrys、TUI/CLI 主流程。
- 捕获范围为业务 `Exception`；`asyncio.CancelledError`、进程退出和键盘中断等宿主控制信号不得被误吞。
  上游网络、SDK 或宿主自身异常不属于定制异常，保持宿主原语义。
- 策略异常、结果类型错误和修改应用失败均回退当前原始报文并记录 detail；日志失败不得再次外溢。
- `Block` 在 containment 外转换为受控的非重试模型调用错误，仅终止当前调用，由上层正常呈现；不得导致
  进程退出或整个应用崩溃。
- SSE 若无法继续安全识别事件边界，停止自定义处理并将剩余原始字节直通；已转发内容不回滚，不能因定制
  解析失败破坏主流程。

## 请求处理

- 通过 `await request.aread()` 获取最终序列化 body；
- 可读取和替换最终 headers/body；
- body 替换后更新 `Content-Length`；
- 主动 Block 时网络层不得收到当前请求；
- 报文接口为原始字节，策略可使用标准库解析 JSON，框架不自动做 JSON 字段合并；
- 非 identity `Content-Encoding` 由策略自行保持编码一致；无法安全处理时记录 detail 并原样放行。

## 普通与流式响应处理

response hook 先处理 status/headers，再按**实际 body 内容**选择普通 body 或 SSE 事件回调；Content-Type 仅作
元数据，不作为分派依据。上游已证明兼容网关会把合法 SSE 标为 `application/json`，也会把 JSON 错误信封标为
`text/event-stream`，仅信 Content-Type 会造成静默失效或把增量流全缓冲。

### 有限前缀分类与回放

1. 非 identity `Content-Encoding` 不做内容分类，记录 detail 并原样直通；策略可在 request 阶段自行协商
   `Accept-Encoding: identity`，框架不隐式改写请求。
2. 对 identity 内容只考察前 **512 字节**分类窗口，与上游 stream sniff 窗口一致；跳过前导 UTF-8 BOM 和空白，
   以 `{`、`[`、`<` 开头判为普通文档，以字段冒号判为 SSE，EOF 或窗口内无法形成 SSE 则判为普通内容。
   若网络 chunk 跨越窗口边界，必须保留并回放完整 chunk，因此单次实际读取和回放可超过 512 字节。
3. 已读前缀必须原样回放，且只在判定前等待必要字节；一旦判为 SSE 即转入增量事件处理，不等待完整流。
4. 分类、回放和后续处理失败按 containment 回退可保证的原始字节；底层网络异常、取消和关闭保持宿主语义。

### 普通 body

实际内容为普通文档且存在 `before_response_body` 时，在 SDK 解析前完整读取 body：`None` 原样重放，修改结果
替换 body，`Block` 终止，策略异常重放原始 body。真实网络响应通过 stream wrapper，预置 `_content` 的缓冲响应
走独立分支；HTTPX 当前无公开 content setter，作为行为锚点由 MockTransport 覆盖。

### SSE 事件

实际内容为 SSE 且存在 `before_sse_event` 时，累积至完整 CRLF/LF 事件边界后逐事件处理：`None` 原样转发，
修改结果替换当前事件，`Block` 终止剩余流；策略异常只回退当前事件，已转发事件不撤回。网络 chunk 可能拆分或
合并事件，不得视为完整响应。缓冲 SSE 也按相同事件契约处理，不得因存在 `_content` 而跳过。结束、提前关闭、
取消和底层异常均关闭原始流，不重复提交缓冲事件；尾部不完整事件原始字节仅直通一次。

### 回调不匹配与范围

实际 SSE 只有普通 body 回调、或实际普通内容只有 SSE 回调时，不调用错误回调、不全缓冲 SSE，记录一次
`response_handler_mismatch` detail 后按原始字节直通。`HttpPolicy` docstring 必须明确普通内容走
`before_response_body`、SSE 走 `before_sse_event`。若未来要求完整原始流或完整语义响应后再修改/阻断，须另立
全流缓冲或逻辑层设计，本批不承诺。

## 主动阻断与异常分类

request、response-header 和普通 body 阶段位于 SDK 请求循环内，按 provider 使用可透传且不被 Chrys
重试的异常：

- OpenAI：不带 `status_code`、不继承 `APIError`/`APIConnectionError`/超时类型的 `OpenAIError` 子类；
- Anthropic：不继承 `APIConnectionError`、超时或其他可重试类型的 `AnthropicError` 子类。

SSE 转换器已离开 SDK 请求重试循环，可使用 AIxCoding 自有非重试异常。Responses 等 wire 层可能重包装，
上层识别沿异常链。

所有主动阻断：

- 不直接抛普通 `Exception`；
- 使用 `raise ... from None`，控制 `__cause__`、未抑制 `__context__` 和 `args`；
- 对外使用固定文本，策略 reason 仅进 detail；
- 最终异常经公开 `classify_error()` 验证 `retryable=False`、`transient=False`；
- 契约测试对实际抛出并捕获的异常断言，不修改公共错误分类器。

## 失效降级与日志

| 失效点 | 宿主行为 | 日志 |
|---|---|---|
| 注册期安装失败 | 不安装，注册调用方与宿主继续；其后创建的 Client 无定制 hooks | 主通道 WARNING + 脱敏 detail；**不直写 stderr**，不抛出 |
| 单个 Client 运行期安装失败 | 原 Client 继续，无定制 hooks | 主通道 WARNING + 脱敏 detail；**不直写 stderr**，避免干扰 TUI |
| 请求策略异常 | 原请求继续 | `aixcoding.detail.llm_call_interception` WARNING + 脱敏栈 |
| 响应头/普通 body 策略异常 | 原响应继续 | 同上 |
| SSE 当前事件策略异常 | 当前原始事件继续，后续仍处理 | 同上 |
| 实际响应类型与已注册回调不匹配 | 原始字节直通，不调用错误回调 | 每响应一次 `response_handler_mismatch` detail |
| 不支持的压缩报文 | 原始字节继续 | detail WARNING，不含正文 |
| 主动 Block | 终止，不属于失效 | detail 记录阶段、provider、调用 IDs 与最多 256 字符的原因摘要 |

- 运行期策略技术事件只写 detail；注册期安装失败与单个 Client 安装失败例外地写主通道 WARNING + detail，但不写
  stderr。
- 日志可含 provider、model id、阶段、调用归属和异常类型；不得记录 Authorization/token、cookies、
  prompt、工具参数、headers 全量或响应正文。`Block.reason` 仅记录前 256 字符以防单条日志失控，策略不得把
  凭证或正文放入 reason。
- 首版按失败事件记录，不预先新增频控抽象；日志洪峰另行评估。
- 允许降级意味着本机制不是安全硬阻断。
- 策略在事件循环上执行，不得包含阻塞调用。

## HTTP 层最终选型矩阵（四场景）

| 场景 | 推荐接入方式 | 必须接受的条件 |
|---|---|---|
| 默认关闭、配置启用 | 方案二：显式修改 `clients.py`，默认不挂 hooks | 上游源码只有一个接入点，默认 hook 清单测试可保持不变 |
| 默认开启、允许失效降级 | 方案一：AIxCoding 策略注册时运行时包装 | ADR、真实 `create_client()` 契约测试、安装失败显式告警 |
| 失效不可放行 | 优先方案二，默认挂载 | 接受一个上游源文件及相关上游测试调整；hook 构建或加载失败必须使请求失败 |
| 失效不可放行且零上游文件是硬约束 | 只能采用方案一 | 注册期安装失败须显式告警并由业务侧处理；另以契约测试发现上游绕路 |

本批选择第二行。其他三行保留为未来重审依据，不视为当前需求。

## 备选方案对比

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| HTTPX hooks + TrajectoryContext | 原始报文全覆盖；现有调用归属；零上游 | 流式需处理 SSE 边界 | **采纳** |
| 启动期无条件安装（原方案） | 业务代码无需关心安装时机 | 默认策略为空时仍替换上游工厂，每次调用多约 18–20 ms 与 18 个模块，零功能收益 | 否决，改为策略注册时安装 |
| 启动期判空、非空才安装 | 保留启动期安装的形式 | 启动期策略必为空，该任务恒为空转；策略生效仍须由注册触发安装 | 否决 |
| HTTPX + ChatMiddleware | 同时获得语义 messages/updates/最终响应 | 中间件非全路径、无原始 headers；本批不需要 | 后续按需叠加 |
| HTTPX Transport | 可本地合成响应 | 代理、TLS、连接池和关闭语义扩大 | 本批否决 |
| 协议请求构建函数包装 | 可直接处理 provider JSON | 响应和轮询覆盖不全 | 否决主干 |
| Anthropic SDK middleware | 官方扩展 | 仅 Anthropic，非统一 | 否决 |
| 逻辑层显式接线 | 每逻辑调用一次，可取组装后语义响应 | 一个上游核心文件；不提供原始 HTTP；本批不需要 | 撤回，不实施 |

## 对上游隐式行为的假设

1. **统一工厂覆盖**：真实模型 SDK Client 均经 `create_client()` 和 `_build_profile_http_client()`；新增
   绕路时该路径不受拦截，真实工厂契约测试只锚定当前路径。
2. **tracking 顺序与扩展字段**：tracking 在每次 attempt 写入 trajectory context 和 attempt id，redirect
   会替换旧 scope；AIxCoding 排在其后可获得真实归属。
3. **上下文可空性**：`turn_id` 等字段可空，标题等辅助调用可能无 turn；实现不得伪造。
4. **HTTPX hook 时序**：request 在 auth 后、redirect 循环内，response 在普通 body 预读前；变化可能使
   普通 body 修改失效，需行为测试。
5. **Client hooks 可调整**：`AsyncClient.event_hooks` 当前可读、可整体赋值；变化时安装失败并告警降级。
6. **流式 chunk 边界**：HTTPX 不保证 chunk 等于 SSE 事件，SDK 另行做 SSE 解码；本批自行缓冲事件边界。
7. **缓冲响应**：MockTransport 等可预置 `_content`，真实网络通常走 stream；两种形态分别适配。
8. **SDK 异常透传**：基础 SDK 错误可透传，普通异常可能重试并包装；每 provider 的调用次数断言锚定。
9. **Chrys 分类器**：读取完整异常链、内置类型、状态码和短语；最终 Block 分类自检和契约测试锚定。
10. **已输出不重放**：Chrys 在答案文本已交付后禁止流式重放；若改变，需重新验证阻断语义。
11. **raw log 包装**：现有 logger 可替换 response.stream；组合测试锚定请求修改后记录、响应原始记录。
12. **Content-Type 不可信**：上游 Chat Completions 明确按 decoded leading bytes 而非 Content-Type 判定 SSE；定制
    必须对 identity 内容做等价的有限前缀分类，不得退回 Content-Type 分派。
13. **测试进程的工厂状态**：注册非空策略的定制测试会在进程内包装上游工厂，定制测试 conftest 在每个测试前后
    恢复未包装的工厂并清空策略。上游 CLI 测试真实执行 `aixcoding_startup()` 后工厂保持原状；上游 core shard
    仍为强制回归。
14. **unwrap 惯例**：上游 scripted wire 会 `inspect.unwrap` 工厂；`functools.update_wrapper` 用于保持该行为，签名参数和
    kwargs 转发另做非 vacuous 断言。
15. **扩展字段漂移**：trajectory context extension key 应复用上游定义，使重命名成为显式导入失败或契约失败，
    不得静默退化为全 `None`。

## 风险与回滚

- **静默绕路**：上游新增不经统一工厂的模型路径时仍放行；本机制不能用于安全硬阻断。
- **降级导致策略未生效**：责任人已接受，注册期和运行期日志为可观测底线。
- **重试放大**：异常类型、context 或短语设计错误会把一次阻断放大为多轮请求；必须断言调用次数。
- **流式部分修改**：当前事件之前的内容已交付，无法整体回滚。
- **报文损坏**：策略返回非法 JSON/SSE 属于策略输出责任；框架只保证策略异常时回退原始报文。
- **并发与串扰**：进程内单组合策略需测试隔离；生产替换应原子生效，不在 hooks 内持锁等待策略。
- **晚注册边界**：工厂在首次注册非空策略时才被包装；未附 hooks 的既有 Client 不会被晚注册策略追溯覆盖。
  业务组合必须保证先注册、后建 Client，最好在任何 `create_client()` 之前完成注册。
- **测试进程污染**：注册非空策略会包装全局工厂；定制测试用 autouse fixture 在每个测试前后恢复未包装的工厂，
  并跑上游 core shard，不能只依赖 Smart Test 的选择结果。
- **回滚**：业务代码停止注册策略即不安装；删除定制包即完全回滚，无配置、数据格式、启动组合或上游代码迁移。

## ADR

本批接入决策由以下 ADR 承载（文件名沿用创建时的 ID；内容已于 2026-11-26 按责任人裁决原地修订为策略注册时
安装，修订缘由见该 ADR 的“修订记录”）：

- `aixcoding/docs/standards/adr/llm-call-interception--http-startup-runtime-wrapping.md`

已撤回的“草案”仅指逻辑层显式接线 ADR；当前 HTTP ADR 已确认。未来重新出现完整语义响应或逻辑级 hook
需求时再立项。
