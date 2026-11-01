# 设计：服务组合测试（composition-tests）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-01
- 确认意见：无特别意见

## 方案概述

新增一个组合测试文件 `aixcoding/tests/auth/test_composition_lifecycle.py`：**进程内**组装
真实生产组件，验证凭据生命周期主链路。零上游改动，全部新增资产落在 `aixcoding/tests/`
（测试 + 进程内 LLM stub）。

```
pytest 进程（aixcoding/tests/auth/，受益 conftest 窄域防呆）
│
│ ① 环境前置：清三个委托通道变量；assert detect_delegation() is None
│
│ ② aixcoding/mock/auth create_server(mode=auto, port=0)   ← 真实登录服务（已有，零改动）
│       LoginSession(environment=LOCAL, endpoints=mock,     ← 真实会话 + CredentialStore
│                   config_dir=tmp_path, backend=MemoryBackend())
│       monkeypatch auth_session._default_session = session ← 保真实单例函数（F-02）
│
│ ③ _LoopbackLLM(port=0)                                    ← 本批新增（测试文件内，进程内）
│       极简 OpenAI chat completions 兼容响应 + 结构化请求快照列表
│       ModelProfile(id=uuid, name=test, provider=openai,   ← 公开字段直接构造
│                    model_id=非空必填, base_url=stub,
│                    api_key=k-test, bypass_proxy=True)     ← 代理隔离（F-01）
│       client = await create_client(profile)               ← 真实生产工厂（禁止自建 SDK client）
│
│ ④ 同一 client 实例贯穿三次请求（stack 公开 get_response 接口，显式 stream=False，
│   真实 await；每次调用=恰好一次 HTTP 请求，约束清单见"实施硬约束"）：
│       请求1（登录前）  → 快照[0]: 无 token header
│       session.request_device_code() + complete_login()    ← 真实 device-code 流程
│       请求2（登录后）  → 快照[1]: token = 登录签发凭据
│       session.logout()
│       请求3（登出后）  → 快照[2]: 不携带旧登录凭据（静态 Authorization 仍在，属合法）
```

三次请求的凭据断言对象是 stub 端**逐次结构化快照**（请求序号 + 最终凭据相关 header），
不依赖现有请求计数或脱敏日志文本；快照仅保存 mock 凭据、随 stub 对象丢弃；stub 不主动写
任何持久日志（pytest 失败时的断言输出不属 stub 承诺范围——断言写法避免无必要打印完整
快照；凭据均为 mock 值，不引入哈希/脱敏设施——F-08 缩窄口径）。

## 备选方案对比

### 决策一：HTTP 出口拦截方式

核实基础：`create_client()`（`src/chrys/service/llm/clients.py:365`）无 transport/http_client
参数；transport seam 在内部 `_build_profile_http_client()`（`clients.py:228`，docstring 自认
是上游 client contract tests 的 seam），`create_client` 调用时不向下转发——"真实
`create_client` + 参数注入 transport"在现接口上不可同时成立。

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| 1. loopback 模型端点：`ModelProfile.base_url` 指向进程内 stub，真实 `create_client` 走完整生产 HTTP 栈（httpx client + route/tracking hooks + SDK 装配 + header 合并） | 零上游依赖、零内部 seam 依赖；生产栈最完整 | stub 需自带快照设施（S-02 已计入工作量） | 零（仅依赖 `base_url` 公开字段） | **采用**（预案钉死默认） |
| 2. monkeypatch `_build_profile_http_client` 注入 `MockTransport` | 无网络栈 | 有意依赖上游内部函数（上游重构该 seam 时测试红 = 语义冲突信号，可接受但要知情登记） | 1×~5×中（内部函数名+签名） | 否决：方案 1 可得时无理由承担内部依赖 |
| 3. 给 `create_client` 新增 transport 参数 | 最干净 | 上游源码改动，须单独 R2 报批 | 1×~3×低 | 否决：不得作为测试批默认路径（预案钉死） |

**代理隔离（F-01 处置，方案 1 的前置确定性条件）**：httpx 默认 `trust_env=True` 且**不会为
loopback 地址天然绕过代理**——`HTTP(S)_PROXY`/`ALL_PROXY` 等环境变量或系统代理存在时，
127.0.0.1 请求可能被代理劫持而到不了 stub（CI runner、开发机、未来执行环境不可控）。最小
修法：profile 显式 `bypass_proxy=True`（公开字段，`clients.py:266-267` 经显式 `None` mounts
覆盖环境派生的 proxy transports，保留其余生产 HTTP 栈行为）——不引入代理清理 fixture，
不依赖 `NO_PROXY` 环境配合。

### 决策二：loopback LLM stub 落点

DIRECTORY.md §6 明文："进程内替身不属本专区：测试专用 fake/stub 归 `aixcoding/tests/`"。

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| 测试文件内定义 `_LoopbackLLM` 类（参照 `test_auth_session.py` 的 `MockServer` 类先例） | 单消费方内聚；快照生命周期与测试一致；不触发 mock 专区契约测试义务（非 `aixcoding/mock/` 资产，其正确性由组合测试断言本身承载）；无 launcher 编排联动 | 将来第二消费方出现时需提取 | **采用**（R5 最小变更；提取义务登记于 plan） |
| 新建 `aixcoding/mock/llm/` 子包 | 可独立联调（CLI 起服务） | 本批无联调需求（纯测试消费）；须配套契约测试 + `__main__.py` launcher 编排评估——为一个测试设施引入整套专区义务，负收益 | 否决：YAGNI |
| 给 `aixcoding/mock/auth` server 增加 chat completions 路由 | 复用既有 server 骨架 | 职责混淆：auth mock 契约是 device-code 登录服务的 wire 复刻，塞 LLM 端点破坏单一职责；预案 Q4 的"auth 侧补捕获"经核实不成立——**组合测试需要捕获的是 LLM 请求的 header，登录侧请求无此断言需求**，auth mock 零改动 | 否决（澄清预案遗留表述） |

### 决策三：三次请求的驱动接口

`create_client` 返回 `ToolLoopLayer` stack（`clients.py:456`）。`loop.py:2223` 明示单次模型
调用可直接用内层 chat layer；完整组合入口是 `get_response`。design 只约束：**经 stack 公开
`get_response`**（不自绕 stack 直拼 SDK 调用），快照计数与请求数一一对应。

**调用形态硬约束（F-04 处置，test-plan 逐条落验收）**——"每次调用恰好一次 HTTP 请求"仅在
以下全部条件下成立，任一偏离都可能引入多发请求或误触发 SSE 路径：

1. profile 显式设置非空 `model_id`（schema 注明使用前必须设置）；
2. 每次调用显式 `stream=False`（`get_response` 默认即非流式；`ModelProfile.stream=True`
   默认值**不会**自动传入 `get_response`——但测试必须显式钉死，防上游改默认值）；
3. 真实 `await` 消费返回（`get_response` 是惰性的，不 await 不发请求）；
4. stub 恒返回合法、无 tool call、无 continuation 的普通 JSON completion（若误走流式，
   需 SSE + `[DONE]`，普通 JSON 不适用）；
5. 不传 wire retry / compaction 等额外策略参数。

## 上游改动清单（R2）

**无上游改动。** 全部新增资产：`aixcoding/tests/auth/test_composition_lifecycle.py` 一个
文件（测试 + 进程内 stub 同文件）。

R1 自查（必答）：本批能否完全不改上游？——**能**。拦截走 `ModelProfile.base_url` 公开
字段 + loopback 端点，登录走既有 `aixcoding/mock/auth`，凭据读取走 `stamp()` 公开行为；
无一处需要上游接线点。

## 对上游隐式行为的假设

1. **`create_client(ModelProfile)` 经 `base_url` 走完整生产 HTTP 栈**（`clients.py:365`、
   `schema.py:28`：`provider`/`base_url`/`api_key` 均为公开字段，`id`/`name` 必填）。假设
   失效（如工厂内部强制改写 base_url）→ 组合测试连接失败即红，属预期检测语义；
2. **`stamp()` 逐请求经 `login_token_header_value()` → `get_login_session()` 解析凭据**
   （`wire_client.py:106-158`、`auth/__init__.py:48-67`：构造时不快照，send-time 解析）。
   失效（上游改为构造时快照）→ 登录后请求 2 拿不到 token 即红——**这正是本批要守护的
   组合语义**（`login_token_header_value` docstring 自述的"login/logout on the next request"）；
3. **per-request `extra_headers` 能到达最终 wire 请求**（组合层锚定；SDK 先在普通 dict 合并
   再构造大小写不敏感的 httpx Headers）。注意（F-06 缩窄）：本批 profile **不含静态
   `token`**，故组合测试**未**在组合层重新锚定"default × extra 同名字段覆盖"语义——该语义
   继续由 `test_llm_token_wiring.py` channel 2（default_headers 含静态 token 的对抗构造）
   单元级承载，本批不为覆盖它而改变三次生命周期断言设计；
4. **`LoginSession.__init__` 在构造时点调用一次委托检测**（事实陈述，时点语义的守护归
   `test_auth_delegation.py` 单元测试，非本批断言对象——F-03 处置：删除原"时点失效时前置
   断言先行红"的错误因果表述，环境前置断言只证明"构造时环境无委托"）；
5. **stack 每次公开对话调用在"调用形态硬约束"（决策三）全部满足时恰好发出一次 HTTP
   请求**——SDK 重试 0 次（`http_max_retries=2` 但 stub 恒 200，无触发条件）；route/tracking
   hooks 不发额外探测请求；无 tool call 响应下 blocking loop 直接返回不进第二轮。失效 →
   快照计数断言红，按实际情况调整计数口径（test-plan 记录基线）。

## 定制点登记预告

不适用：纯开发资产（`aixcoding/tests/` 内新增测试文件），零上游接触、无 marker 可锚——
`gen_customizations.py` 的登记对象是上游文件内的定制点，本批不产生。

## 实施硬约束（预案 v3 R-01 + 评审 F-01~F-08 处置）

### 环境前置

- 构造任何会话之前清理全部三个委托通道变量——`AIXCODING_AUTH_DELEGATED_TOKEN`（primary，
  单独存在即激活委托、`logout()` 变 no-op）、`OPENAI_API_KEY` + `AIXCODING_USER_EHR`
  （compat 对，成对存在激活；`OPENAI_API_KEY` 另有 provider env fallback 身份，清理后
  profile 显式 `api_key` 即唯一来源）。display hints 变量
  （`AIXCODING_AUTH_DELEGATED_EHR`/`_NAME`）单独存在不激活委托，不强制清理；
- **`detect_delegation() is None` 断言的命名空间钉死（F-03）**：conftest 钳制 patch 的是
  `auth_session.detect_delegation`（session 模块命名空间）——测试**不得**从 session 模块
  取该函数（断言会恒 None，证明不了环境清理有效），必须从包级
  `chrys.kernel.aixcoding.auth` 或 `.delegation` 调**真实函数**；断言时点在 session 构造前；
- conftest 窄域防呆（`tests/auth/conftest.py`：委托钳制 + 默认构造隔离）已就位（P1-5
  落地），测试置于 `tests/auth/` 自动受益；测试内显式断言为文档化自证，不依赖 conftest
  存续。

### 登录态建立禁令（形态 A 第七约束，F-04/Q1 处置）

除 profile 的静态 `api_key` 外，测试**不得**手工注入 `token`/`Authorization` header，
**不得**直接写 `CredentialStore`——登录态只能由真实 `request_device_code()` +
`complete_login()` 建立。此禁令防"测试自己塞 token"的假组合退化（六条件未覆盖的薄弱面）。

### 三次请求断言（F-05 精确化）

| 快照 | 断言 |
|---|---|
| [0] 登录前 | 无 `token` 键；`Authorization == "Bearer k-test"`（静态凭据在场） |
| [1] 登录后 | `token == 登录签发值`；`Authorization` 不变 |
| [2] 登出后 | 无 `token` 键（直接断言键不存在，不做"不等于旧值"冗余断言）；`Authorization` 不变 |

断言语义：区分"登录凭据"（`token` header，生命周期随登录会话）与"静态凭据"（SDK 由
profile `api_key` 自动生成的 `Authorization`，登出后合法保留）。本测试 profile 未配置
`http_headers` 静态 `token` 场景，不声称覆盖（同 F-06 缩窄口径）。

### 同一性断言（F-02 改法）

monkeypatch `auth_session._default_session = session`（**保真实 `get_login_session()` 函数**，
`session.py:296-301` 的单例函数体仍被生产链路执行；仓内先例：
`test_login_command_wiring.py` 五处同款、`test_auth_delegation.py:130`）。测试内经包级
`chrys.kernel.aixcoding.auth.get_login_session()` 调用并断言 `is session`——证明的是
"真实单例函数返回测试实例"（wire 链路 `login_token_header_value` → 同一函数），而非
"monkeypatch 生效"。单例机制本身（缓存、惰性构造）由既有
`test_get_login_session_is_a_singleton` 单元测试守护，本批不重复覆盖。禁止 patch 整个
`get_login_session` 函数（评审 F-02：那只能证明 patch 生效，且 from-import 别名可能调错
函数）。

### 资源生命周期（F-05 处置）

- stack：`create_client` docstring 明示调用方拥有并负责关闭——创建后立即建立
  `try/finally: await client.aclose()` 关闭责任（异常路径同样关闭，不留连接池）；
- 两个 loopback server：context manager 形态（`test_auth_session.py` 的 `MockServer`
  `__exit__` 先例：`shutdown()` + `server_close()`；`_LoopbackLLM` 同款），异常路径同样释放。

### auth mock auto 模式时序基线（F-07）

`mode="auto", interval=0` **不是**立即授权：poll 状态机奇数次 pending、偶数次 authorized
（`server.py:276-279`），客户端在两次 poll 间有固定等待（约 1 秒）。测试预算按 ≥1 秒计，
不写紧超时；不试图改生产轮询间隔提速。test-plan 记录该确定性序列作为时长基线。

## 风险与最坏情况

- **组装层 API 漂移**（`create_client`/`LoginSession`/wire 装配上游重构）：组合测试本身就是
  升级时语义冲突的检测器，红了即跟随上游调整——这正是其价值，不是本批缺陷；
- **测试时长**：进程内组装预期秒级（两个 loopback server + 三次本机 HTTP 请求 + auto 模式
  登录的固定 poll 等待约 1 秒，见"时序基线"）；纳入 local-verify 预算监控（Windows 开发机
  中位数 >1min 或 P95 >2min 时评估分区，P0 批次口径）；
- **回滚**：删除单个测试文件即完全回滚，无任何产品代码影响。

## ADR 判定

按 DEVELOPMENT.md §6 checklist：

1. 有被认真考虑但否决的备选方案？——transport 三方案与 stub 落点三方案均有否决项，但属
   **批次内实现选型**，理由已完整留档本 design 备选表（windows-matrix 同例：三层结构
   备选对比未出 ADR）——判定"否"（不构成架构级决策）；
2. 撤销代价高？——否：单测试文件，删除即回滚；
3. 约束未来工作模式？——否：不改变任何规范/目录约定（stub 落 tests/ 是 DIRECTORY.md §6
   既有明文的跟随，非新约定）；
4. 依赖上游非公开接口或行为？——否：方案 1 全部经公开字段与公开行为（假设 1-3 均为公开
   docstring 自述行为）。

结论：**不出 ADR**。

## 草案评审处置记录（2026-11-01，外部 AI 评审：无 blocker，5 major + 3 minor，全部采纳）

评审输入：`temp/composition-tests-review-prompt.md`（自包含九问）；评审对照仓库源码与锁定
版本（openai 2.54.0 / httpx 0.28.1）核验。

| # | 级别 | 要点 | 处置（本 design 落点） |
|---|---|---|---|
| F-01 | major | loopback 未隔离代理：httpx `trust_env` 不为 127.0.0.1 绕过代理，环境/系统代理可劫持请求 | 采纳：profile 显式 `bypass_proxy=True`（公开字段），不引入代理清理 fixture（决策一补段） |
| F-02 | major | patch 整个 `get_login_session` 只证明 patch 生效，不守护真实单例路径；from-import 别名风险 | 采纳：改 patch `auth_session._default_session`，保真实单例函数；先例 `test_login_command_wiring.py`（"同一性断言"节改写） |
| F-03 | major | `detect_delegation` 断言命名空间未钉死（conftest 钳制面下可能恒真）；假设 4 失效预测因果不成立 | 采纳：钉死从包级/`.delegation` 调真实函数；删除假设 4 错误因果表述，时点守护归单元测试 |
| F-04 | major | "恰好一次 HTTP"调用条件未成硬约束；手工注入 token 退化路径未封死 | 采纳：决策三"调用形态硬约束"五条 + "登录态建立禁令"（形态 A 第七约束） |
| F-05 | major | stack 与两 server 异常路径清理缺失，违反 `create_client` 关闭所有权契约 | 采纳：新增"资源生命周期"节（try/finally aclose + context manager） |
| F-06 | minor | 本批 profile 无静态 token，未在组合层重锚定同名字段覆盖语义 | 采纳：假设 3 缩窄为"extra_headers 到达 wire"；同名覆盖归 channel 2，不为覆盖改变断言设计 |
| F-07 | minor | `interval=0` 非立即授权，仍有约 1 秒固定 poll 等待 | 采纳：新增"时序基线"节；测试预算 ≥1s，不改生产轮询间隔 |
| F-08 | minor | "不落任何持久日志"未覆盖 pytest 失败断言输出，表述过强 | 采纳：缩窄为"stub 不主动写持久日志，快照仅保存 mock 凭据"；断言避免无必要打印完整快照，不引入脱敏设施 |

评审"已检查无问题项"（方案主线、transport 路线、stub 落点、auth mock 零改动、环境变量
清单、登出断言方向、假设 1/2/5 主体、零上游/零依赖/单文件回滚/不出 ADR）均维持。
