# 需求：进程内大模型 HTTP 调用拦截（llm-call-interception）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

AIxCoding 需要在进程内对每个实际模型 HTTP 请求和响应进行读取、修改和阻断，并让策略知道该流量属于
哪个会话、用户轮次、逻辑模型调用和实际发送。这里的 head/body 指实际 HTTP headers 和序列化 body，
不是仅指解码后的 messages 或 `ChatResponse`。

现阶段不需要在逻辑模型调用边界增加 pre/post，也不需要上游已组装的完整语义响应。HTTPX 已能统一覆盖
真实 provider 流量，上游 request tracking 也已把 `TrajectoryContext` 放入 request extensions，因此本批
收敛为仅实现 HTTP 层，不修改 `kernel/loop.py`。

## 目标与非目标

- 目标：
  1. 实现通用 HTTP 读取、修改和阻断能力，但**默认定制策略为空，不写任何业务处理逻辑**；注册非空策略时幂等
     安装工厂包装，未注册策略的默认启动路径不导入本模块、不改动上游模块属性。`_policy is None` 时不向 Client
     附加定制 hooks，保留上游原始 hooks 和零报文处理开销；非空策略必须在目标 Client 创建前注册，既有未附
     hooks 的 Client 不做追溯安装。
  2. 请求发送前可读取最终请求 headers 和序列化 body，可替换 headers/body，也可阻断且网络层收不到
     当前请求。
  3. 响应进入 SDK 解析前可读取、修改 status 对应的 headers；普通响应 body 可完整读取、替换或阻断。
     普通/SSE 分派必须依据实际 identity body 的有限前缀与回放，不信任可能双向误标的 Content-Type。
  4. 流式响应可读取、修改响应 headers，并按完整 SSE 事件读取、替换或阻断 body；正确处理一个事件
     跨多个网络 chunk、一个 chunk 包含多个事件及流提前结束。
  5. 每个实际 HTTP attempt 都可处理，包括 SDK 重试和 HTTP 重定向；同一逻辑调用下的多个 attempts
     通过既有 ID 关联，不额外承诺逻辑调用级恰好一次 hook。
  6. 请求和响应两侧均可从 `request.extensions` 获取调用归属：
     `session_id`、可空的 `turn_id`、`cycle_operation_id`、`exchange_operation_id`、
     `request_attempt_id`、`actor.kind`、`actor.role`、provider/model。
  7. `cycle_operation_id` 用于关联一次逻辑模型调用内的全部发送，`exchange_operation_id` 用于区分
     Chrys 发送，`request_attempt_id` 用于区分实际 HTTP 往返；不把派生路由 session header 当作真实
     session id。
  8. `turn_id` 等上游字段缺失时保持缺失，不伪造；策略可用 actor role 区分主 Agent、内置 sub-agent、
     workflow、审批 judge、标题生成和 compaction 等调用。
  9. 主动拦截不得被 SDK 或 Chrys 当作临时网络故障重试；流式已输出后的阻断只终止后续流，不重放请求、
     不撤回已输出内容。
  10. **默认开启、允许失效降级，定制异常绝不外溢**：安装失败、策略不可用或任意策略业务异常均不得
      影响宿主正常工作流或导致进程出错；原始请求/响应继续。主动 `Block` 是受控的单次模型调用终止结果，
      由上层正常呈现，不得导致 TUI/CLI 崩溃，不属于意外异常。
  11. 失效必须留日志：注册期安装失败与运行期单个 Client 安装失败均写主通道 WARNING 与 detail、不写 stderr、
      不抛出；运行期策略异常及实际响应类型/回调不匹配写 `aixcoding.detail.llm_call_interception`，不记录认证头、
      prompt、工具参数或响应正文。
  12. 零上游手写行为文件改动；产品逻辑位于 `src/chrys/service/aixcoding/llm_call_interception/`，不修改启动组合
      `src/chrys/app/aixcoding/startup/`。唯一例外是用上游生成器刷新架构门禁要求的
      `tests/architecture/trajectory_wait_manifest.json`。不新增第三方依赖。
  13. hook 在事件循环上执行，策略不得包含阻塞调用；阻塞工作不得卡住 TUI 或其他模型流量。
- 非目标：
  - 进程外代理、外部 hook 进程或 sidecar；
  - 本地合成成功响应；本批拦截仅指终止并报告明确错误；
  - 修改 `kernel/loop.py`，增加逻辑调用级 pre/post，或自建逻辑调用 ID；
  - 读取、修改上游已组装的完整语义 `ChatResponse`，或免除语义内容拼装；
  - 在整个 SSE 流结束后才提供全流聚合修改；本批处理普通完整 body 或流式完整事件；
  - 撤回已经交付给用户的流式内容；
  - 外部 ACP sub-agent 进程中的模型调用及 `mock` provider；
  - 具体业务脱敏/过滤规则、动态外部 Python 插件或新增用户配置开关。

## 用户场景

1. **请求策略**：策略读取最终 headers/body 和真实调用归属，按 session、turn、actor role 或 provider
   修改请求，或阻断当前实际 HTTP 请求。
2. **普通响应策略**：策略在 SDK 解析前读取完整响应 headers/body，替换内容或阻断，不需要自行拼装。
3. **流式响应策略**：策略处理完整 SSE 事件；框架负责跨 chunk 边界，策略不把网络 chunk 误当成完整响应。
4. **逻辑调用归并**：策略通过 `cycle_operation_id` 关联同一次逻辑调用下的多个 HTTP attempts，通过
   `exchange_operation_id` 和 `request_attempt_id` 进一步区分发送和 HTTP 往返。
5. **失效降级**：安装或策略内部失败时原始报文继续，日志记录失败阶段、异常类型和可得的调用归属；
   主动 Block 不被 fail-open 吞掉。

## 验收标准

### 安装、上下文与覆盖

- [ ] 注册非空策略时完成安装，重复注册或重复安装不重复包装，`set_http_policy(None)` 不安装。空策略不附加
      定制 hooks，不调用 `request.aread()`、不复制 headers、不解析 JSON/SSE、不替换 `response.stream`，请求
      和响应内容与原行为一致且无固定 hook 开销。
- [ ] 真实 `cli_app.main()` 执行 startup 后，上游工厂未被包装、本模块未被导入，同进程 route/default hook
      精确清单保持上游原值；注册策略后创建的 Client 才带定制 hooks。真实 startup 串行组合和上游 core shard
      均通过，不能只以 Smart Test 选择结果作为证据。
- [ ] 注册策略的定制测试在每个测试前后清空策略并把上游工厂恢复为未包装状态，依赖“工厂未包装”的用例不受
      执行顺序影响。
- [ ] 策略在 Client 创建前注册时，OpenAI Chat Completions、OpenAI Responses（含 retrieve/poll）和
      Anthropic Messages 的普通及流式调用均经过拦截器；外部 ACP 进程和 `mock` provider 按非目标排除。
- [ ] 请求和响应两侧均可读取真实 `session_id`、可空 `turn_id`、cycle/exchange/attempt IDs 和 actor
      信息；子代理、标题、审批等派生路由 header 不被当作真实 session id。
- [ ] 标题生成等缺少 turn 的调用保持 `turn_id=None`，不生成替代 ID；actor role 可用于策略过滤。
- [ ] 同一逻辑调用的多个 attempts 共享预期 cycle 标识，Chrys 重试和 HTTP 重定向分别产生对应新 ID。

### 请求与普通响应

- [ ] 请求 headers/body 修改在实际 wire 请求上可见；阻断时网络层无当前请求，且 SDK/Chrys 不发生
      主动拦截导致的重试。
- [ ] 普通响应 headers/body 修改在 SDK 解析结果上可见；响应阻断不进入正常解析，且不发生主动拦截
      导致的重试。
- [ ] 真实网络响应和带 `_content` 的缓冲响应均有覆盖；策略异常时重放原始 body。缓冲 SSE 同样逐事件处理，
      不得因 `_content` 存在而跳过。

### 流式响应

- [ ] 测试证明网络 chunk 不等于完整响应：跨 chunk SSE 事件可完整读取、修改或阻断，一个 chunk 中的
      多个事件不会混淆。
- [ ] 策略内部异常只回退当前原始事件；已转发事件不撤回，后续事件仍按契约处理。
- [ ] 流结束、异常、取消和提前关闭均正确关闭原始流，不重复提交缓冲事件。
- [ ] 已输出内容后的阻断不重放请求，不重复输出已交付文本。
- [ ] `application/json` 误标的实际 SSE 仍按事件增量处理；`text/event-stream` 误标的普通 JSON 按普通 body
      处理。分类只考察前 512 字节，跨界网络 chunk 完整保留回放，不得等待完整 SSE 流后才交付首个事件。
- [ ] 实际响应类型与唯一已注册内容回调不匹配时，不调用错误回调、不全缓冲 SSE，并记录每响应一次
      `response_handler_mismatch` detail。

### 阻断、降级与回归

- [ ] 各阶段分别注入 `ValueError`、`RuntimeError`、自定义业务异常、非法返回类型和修改应用失败时，异常
      均不逃逸到 SDK/Chrys/TUI，原始工作流和进程继续，原始报文保持一致且有 detail 日志。
- [ ] 最终阻断异常经公开 `classify_error()` 验证 `retryable=False`、`transient=False`，并控制
      `__cause__`、未抑制 `__context__` 和 `args`；Block 对外使用固定文本，reason 仅进 detail。
- [ ] 注册期安装失败不抛出，不影响注册调用方与宿主，写主通道 WARNING 与脱敏 detail、不写 stderr；单个
      Client 运行期安装失败同通道。运行期策略异常和回调不匹配有 detail，正文和认证信息不落日志。
- [ ] 真实 `create_client()` 契约测试不 mock `_build_profile_http_client`。
- [ ] raw HTTP 日志与拦截器组合启用时，请求日志记录实际发送的修改后请求，响应日志记录网络原始响应。
- [ ] 本批 diff 不含上游手写行为文件；唯一上游生成物变更是官方刷新的 wait manifest。不新增第三方依赖，
      全部定制测试及规定质量门通过。

## 后续扩展边界

若未来需要逻辑调用级恰好一次 pre/post、完整语义 `ChatResponse`、本地合成响应、全流聚合修改、外部 ACP
覆盖或失效不可放行，须重新评估并另立设计，不在本批隐含扩展。
