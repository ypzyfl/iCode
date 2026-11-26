# ADR-llm-call-interception--http-startup-runtime-wrapping：默认降级的 HTTP 模型拦截采用策略注册时运行时包装

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-<batch-slug>--<decision-slug> 取代）——括号内即后继 ID（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py

命名与编号：文件统一放 standards/adr/<batch-slug>--<decision-slug>.md，H1 加 ADR- 前缀；
batch-slug 必须对应既有批次目录，决策 slug 在本批次内稳定且唯一。新 ADR 不取全局数字编号。
自包含快照原则：决策节写定不改；重大规则变更出新 ADR，本文标“被取代”。规范引用仅作导航。
决策更新处理：实质变更新建 ADR；原地修改仅限非决策性修正。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-26
- 确认意见：无特别意见

> 本文为决策时点快照；现行规则以 `DEVELOPMENT.md R1/R9、§5/§9` 与 `DIRECTORY.md §3` 为准。

## 背景

AIxCoding 需要在进程内读取、修改和阻断实际模型 HTTP 请求及响应，覆盖 OpenAI、OpenAI-compatible、
Anthropic 的普通与流式调用，并获得真实 session、turn、逻辑调用和实际发送标识。现有配置、
ChatMiddleware、Extension、YAML Hooks、OTel 与 EventBus 均不提供完整原始 HTTP 能力。

当前真实模型 HTTP 调用共享 `clients._build_profile_http_client()` 创建的 HTTPX Client；上游 request
tracking 已将 `TrajectoryContext` 写入 request extensions。现阶段不需要逻辑调用级 pre/post 或上游组装
后的完整语义响应，因此仅实施 HTTP 层，不修改 `kernel/loop.py`。

责任人裁决本层默认开启、允许失效降级，失效必须留下日志；原始“尽量少改、最好不改”是偏好，本层可实现
零上游文件改动。

## 决策

1. **接入方式**：`set_http_policy()` 注册非空策略时幂等包装
   `chrys.service.llm.clients._build_profile_http_client`，先安装后保存策略，两者之间不让出事件循环；不接入
   `aixcoding_startup()`。未注册策略的默认启动路径不导入本模块、不改动任何上游模块属性。“默认开启”指无需用户
   配置开关、注册即生效；出厂策略为空，故出厂状态不安装。包装器调用原工厂后调整共享 AsyncClient 的
   event hooks；不修改上游文件，不包装 `create_client()`，不替换 Transport。
2. **代码归属**：HTTP 策略注册、上下文、hooks、SSE 转换和安装器位于
   `src/chrys/service/aixcoding/llm_call_interception/`。首版持有一个组合 HTTP 策略，不建立外部插件发现。
   通用读写改拦能力在定制代码内实现，但默认策略为空；空策略不附加定制 hooks，保持上游原始 event hooks，
   不产生固定 hook 调用、body 读取、headers 复制、JSON/SSE 解析或响应流替换开销。非空策略须在目标 Client
   创建前注册，未附 hooks 的既有 Client 不做追溯安装。
3. **调用归属**：AIxCoding hooks 排在 tracking 后，从 request/response.request extensions 读取真实
   `session_id`、可空 `turn_id`、`cycle_operation_id`、`exchange_operation_id`、
   `request_attempt_id`、actor 和 provider/model。缺失字段保持缺失，不伪造，不使用派生路由 header 冒充
   真实 session id，不把 trajectory ID 未经验证等同于外部 OTel span ID。
4. **技术层**：普通 body 完整转换；流式 body 按完整 SSE 事件转换，网络 chunk 不视为完整响应。普通/SSE
   分派依据实际 identity body 的前 512 字节分类窗口，不信任可能双向误标的 Content-Type；跨界网络 chunk
   必须完整保留回放，SSE 判定后保持增量处理。本批不提供完整语义 `ChatResponse`、全流聚合修改、本地合成响应、已输出内容撤回或
   外部 ACP 覆盖。
5. **hook 顺序**：请求为 route → tracking → AIxCoding → raw HTTP log；响应为 route → tracking →
   raw HTTP log → AIxCoding。日志记录实际发送的修改后请求和网络原始响应。
6. **失效语义**：注册期安装失败不抛出，写主通道 WARNING + 脱敏 detail，不直写 stderr，注册调用方与宿主继续；
   单个 Client 运行期安装失败写主通道 WARNING + 脱敏 detail，不直写 stderr。策略内部异常回退当前原始请求、
   响应或 SSE 事件，实际响应类型与唯一内容回调不匹配时原样直通，均写
   `aixcoding.detail.llm_call_interception`。日志不含认证信息或报文正文。本机制不承诺安全硬阻断。
7. **主动阻断**：与内部异常分离；SDK 请求循环内按 provider 抛可透传且不被 Chrys 判为重试的 SDK 异常，
   SSE 阶段使用非重试异常。最终异常控制 cause/context/args，对外固定文本，reason 仅以最多 256 字符进入
   detail，并经 `classify_error()` 验证 `retryable=False`、`transient=False`。首版不修改公共分类器。
8. **升级守卫**：私有工厂、tracking 扩展字段、HTTPX hook 时序、缓冲响应、实际内容 sniff/回放、SSE
   chunk 边界、SDK 异常和 Chrys 重试分类均为行为锚点；必须有真实 `create_client()` 契约测试，禁止 mock
   被验证的工厂。注册触发安装与注册期安装失败降级同为锚点。真实 `main()` 执行 startup 后上游工厂未被包装
   及上游 core shard 是强制回归，Smart Test 不能替代。
9. **重审条件**：若未来需要逻辑调用级 pre/post、完整语义响应、本地合成响应、全流聚合修改、外部 ACP
   覆盖或失效不可放行，应重新立项评估。
10. **未来逻辑层独立性**：当前仅固定 HTTP 类型、注册和生命周期。未来逻辑层可在 kernel 档独立设计，
    两层只通过现有调用 IDs 关联，不要求复用 HTTP 上下文、流对象或可变状态，也不提前创建 kernel 公共包。

## 理由

- HTTPX 是统一覆盖所有真实 provider、最终 headers/body、普通与流式路径的进程内原始报文层。
- 上游已有调用归属，无需自建逻辑调用 ID 或修改核心循环。
- 策略注册时包装同样满足默认开启和 HTTP 零上游文件改动，避免修改发送、接收及精确 hook 清单测试；未注册策略时
  默认启动路径不触碰上游工厂，也不付出安装成本。启动期无条件安装在默认策略为空时仍替换上游工厂，真实启动路径
  实测每次 CLI 调用多约 18–20 ms 与 18 个模块，没有功能收益，故不采用。
- 普通响应可直接完整处理；流式按 SSE 事件处理满足当前需求，无需为完整语义响应引入逻辑层。
- 允许降级时，私有工厂失效的最坏结果是 HTTP 拦截未生效而模型功能继续，与责任人裁决一致；主通道告警、
  detail 日志和真实契约测试使其可查。
- Transport、ChatMiddleware、Anthropic middleware 和进程外方案均存在已记录的粒度或维护面问题。

## 四场景选型矩阵

| 场景 | 推荐接入方式 | 必须接受的条件 |
|---|---|---|
| 默认关闭、配置启用 | 显式修改 `clients.py`，默认不挂 hooks | 上游源码只有一个接入点，默认 hook 清单测试可保持不变 |
| 默认开启、允许失效降级 | AIxCoding 策略注册时运行时包装 | ADR、真实 `create_client()` 契约测试、安装失败显式告警 |
| 失效不可放行 | 优先显式默认挂载 | 接受一个上游源文件及相关上游测试调整；hook 构建或加载失败必须使请求失败 |
| 失效不可放行且零上游文件是硬约束 | 只能运行时包装 | 注册期安装失败须显式告警并由业务侧处理；以契约测试发现上游绕路 |

本 ADR 固定第二行，其余三行保留为重审依据。

## 后果

- 后续 HTTP 策略不得各自再次 patch SDK、HTTPX 或模型协议路径。
- 每次追上游必须复核私有工厂及 design 行为假设；真实契约测试不可 mock 锚点。
- HTTP hooks 按实际 attempt 执行，策略须幂等或显式处理重试/重定向。
- 同一逻辑调用下的多个 attempts 通过 cycle ID 归并，不承诺逻辑级恰好一次 hook。
- 流式 chunk 不是完整响应；策略按完整 SSE 事件处理，已转发事件不可撤回。
- 允许降级意味着策略可能未生效，不得描述为“必定拦截”。
- 业务组合必须在任何 `create_client()` 之前完成策略注册；注册前已创建的 Client 不被拦截。
- 定制测试注册策略会触发进程级安装，须由 fixture 在每个测试前后恢复未包装的工厂。
- HTTP 零上游 marker，点级登记不适用；私有 anchor 由 ADR、design 假设和契约测试承载。若需要新增上游
  marker，即超出本决策，须重新审批。
- 逻辑层显式接线 ADR 草案已撤回；未来出现完整语义响应或逻辑级 hook 需求时另立设计与 ADR。
- 范围澄清（2026-11-25，非决策性）：本 ADR 所称“零上游文件改动”指不修改上游手写运行时代码、手写测试、
  构建或打包文件。`tests/architecture/trajectory_wait_manifest.json` 是 service 档新增异步节点时由上游架构门禁
  强制刷新的生成物；本批只允许用上游官方生成器登记本模块 wait 节点。这不改变运行时接入决策，也不豁免其他
  上游文件审批。

## 修订记录

- 2026-11-26：决策 1 的接入方式由“`aixcoding_startup()` 启动期安装”修订为“`set_http_policy()` 注册非空策略时
  安装”，同步修订失效语义（决策 6）、升级守卫（决策 8）、理由与四场景矩阵。原因：默认策略为空时，启动期安装
  仍替换上游工厂，每次 `aixcoding-cli` 调用都执行而没有功能收益；改为注册时安装后，默认启动路径不触碰上游工厂，
  该成本（真实启动路径实测约 18–20 ms、18 个模块）只在首次注册策略时支付。当时记录的 +12.9 ms / 16 模块与复测
  结果基本一致。修订过程中开发 AI 曾以未执行前两个启动任务的探针得出“净增 200 ms”的错误结论并据此呈报，经
  真实启动路径复测更正；责任人知情后裁决保留策略注册时安装。
- 本次按责任人裁决原地修订，未新建取代 ADR：决策主体（HTTP 层运行时包装工厂、零上游文件改动、默认空策略、
  失效降级）未变，仅安装触发时机调整，且本 ADR 尚未合入主干。ADR ID 与文件名沿用。
