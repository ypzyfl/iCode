# 设计：auth 迁入（src/chrys/aixcoding/auth + LLM token 接线）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：确认变更方案——对上游源代码改动更小

## 方案概述

阶段三第 2 项（顺序 mock ✅ → **auth** → tui → 其余 → telemetry 殿后，ROADMAP §2）：将旧分支
`main_aixcoding_cli_0.28.0_final` 的设备码登录内核（`aixcoding/auth/` 9 文件，~1350 行）迁入
新基线 `src/chrys/aixcoding/auth/`，并接上**最薄的第一个产品消费方**——LLM 请求 send-time
`token` 头注入（范围 B，负责人 2026-10-26 拍板）。auth 是首个触碰上游源码文件的迁入批次。

```
本期 IN                                                        本期 OUT（后续批次）
─────────────────────────────────────────────                  ─────────────────────────
src/chrys/aixcoding/auth/          9 文件迁移                   tui 全家（login dialog /
aixcoding/tests/auth/              7 测试迁移 + 1 新增             indicator / commands / screen）
env 更名 AIXCODING_AUTH_*×5        含 DELEGATED_* 三件            catalog 模型目录同步（整套重建）
LLM token 接线                     wire_client.py（唯一上游挂点）  context / telemetry（殿后）
mock 更名联动                      aixcoding/mock/ 内 6+ 文件      update_detection
```

范围 B 拍板记录（2026-10-26 负责人，二选一）：A 纯内核（auth 悬空、仅 mock 端到端可验收）/
**B 内核+LLM 接线（推荐，auth 有真实消费方，登录后 LLM 请求自动带 token）** → 取 B；
DELEGATED_* 三件是否同步更名 → **同步更名**（见"环境变量更名方案"）。

外部 AI 评审（2026-10-26，签认前轮）：无 blocker；P1 联动面遗漏两处（`mock/README.md:17`、
`model_catalog/README.md:19,26`）已补，全仓重扫另收敛 `docs/batches/mock/design.md` 配方串与排除项
（见"更名联动面"）；建议 1（测试③双通道覆盖语义）、建议 2（charset gate 边界记录，假设 7）
均已采纳。

外部 AI 复审（2026-10-26，第二轮）：无 blocker；P1 **更名联动面漏迁入源自身**（此前 grep 只扫
新基线仓，auth 包与测试尚在旧分支不在范围内）——`environments.py` docstring 4 处（含 :24-25
语义反转改写）、`delegation.py` docstring 2 处、`test_auth_environments.py` 6 处硬编码字面量
（key 失配静默 fall back PROD）已全部补入迁入映射；P2 测试 18 处 import 统一改写规则已列明；
建议 3（测试③通道 2 锚定手段移交 test-plan 钉死、不得 mock SDK 合并行为）已采纳。

外部 AI 三轮评审（2026-10-26）：无 blocker；P1 **batches/mock/design.md 联动面误纳 4 处历史/决策记录**
（:121 议题由来、:130 考古事实表、:151-152 决策状态——机械替换致史实失真/同义反复，与"不回改"
原则自相矛盾）已移入不回改名单，机械联动收窄为 5 处（:99,106,108,114,115）；P2 三条均已采纳：
①逐文件表补 `environments.py:34`、`storage.py:34-40` 包内 import 及 storage "路径不变"仅指
lazy platform 一处的澄清；②总则点明覆盖 docstring Sphinx 交叉引用与示例 import、逐文件 grep
终验；③`_login_token()` docstring 的 `catalog._catalog_token` 悬空引用（catalog 本批 OUT）改
为自含表述。

外部 peer review 第四轮（2026-10-26，代码级核验 + 治理工具规则）：无 blocker；P1-1 **R2 gate
机器语义硬约束**（批准池=已确认 design 的 R2 表并集、草案授权为零、untracked 也比对）→ 新增
"实施流程约束"节（先签认后动工 + 探针式接线第一步 + 集合外溢出协议）；P1-2 **测试脱离根
conftest 三护栏**（config-dir 重定向/CHRYS_* env 清理/socket 守卫）→ 测试节写死隔离自带声明、
loopback-only 网络边界、本地验证命令组合（Smart Test 对 `aixcoding/tests` 不可见的补偿）；
P2 四条均采纳：import+调用同进 try（wire_client 注入形态稳健性增强）、httpx event hook 备选
登记对比二含切换触发条件、三条行为边界入假设 8-10、每请求读盘成本记录不实施。正面核验 13 项
（三 codec send/stream 均进 stamp、PEP 758 上游现行在用等）全部通过。

## 备选方案对比

**对比一：本期范围**（负责人 2026-10-26 拍板，记录在案）：

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| A 纯内核 | 零上游改动，无需 R2 | auth 悬空至 catalog/tui 批次，无产品消费方 | 零 | 否 |
| **B 内核 + LLM token 接线** | 最薄真实消费（2 上游文件 ~35 行）；登录态直接服务 LLM 网关鉴权 | 触发本仓首个源码级 R2 | clients.py ×1 函数、wire_client.py ×1 方法，锚点稳定 | **是** |
| B+ catalog 重建 | 消费方更完整 | catalog 在 0.31 整套缺位（settings 声明+周期同步+registry 联动+9KB 测试），范围膨胀 | 大 | 否 |

**对比二：token 头注入位置（0.31 结构下）**：

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| **`RequestHeaders.stamp()` 内注入**（0.28 instrumented `_set_chrys_request_headers` 的 0.31 等价落点） | 与 0.28 语义同构：send-time 逐请求解析、登录/登出下一请求生效；复用既有 managed 过滤+charset 门 | — | **是** |
| `create_client` 构造期快照 | 一次解析 | 0.28 已论证否决：engine/clients 构造先于登录完成，快照会固化空 token（0.28 instrumented.py:210-216 教训） | 否 |
| **httpx request event hook**（`_build_profile_http_client` 的 `event_hooks` 组合点，clients.py:257-285 已组合 route/tracking hooks）——**记录在案的回头班车，本期不采用** | R2 文件 2→1；直接改最终 `request.headers["token"]`，**不依赖 SDK 的 extra/default headers 合并语义**（测试③通道 2 的锚定难点根源；`anthropic_messages/client.py:189-193` 注释已暴露 case-sensitive merge 双头坑）；顺带消除假设 2 的裸 codec 边界 | 未经 0.28 验证的新形态；hook 内抛异常直接砸掉请求，需 hook 内部全吞 | 否（本期），**触发条件**：通道 2 在任一 SDK 上实测发现 per-request 不覆盖 default_headers 或大小写致重复头 → 切换本方案 |

## 上游改动清单（R2）

> 节标题须保持机器可解析的标准形态（`check_r2_diff.py` 全等匹配本节标题）；本表即本批次全部上游改动与 R2 报批清单。

| # | 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|---|
| 1 | `src/chrys/service/llm/wire_client.py` | `RequestHeaders.stamp()` 内注入：**import 与调用同进一个 try**（`try: from chrys.aixcoding.auth import login_token_header_value; login_token = login_token_header_value() / except Exception: login_token = ""`——0.28 语义，解析函数本体位于 auth 包公共 API）→ send-time 语义注释块（0.28:210-216 精神平移）→ 早退条件追加 `and not login_token` → 头赋值区尾部 `if login_token: headers["token"] = login_token` | +16 / −1 | 注释块首行 `# AIxCoding auth: ...`（0.28 instrumented 两处标记的合并平移；module 词 `login`→`auth` 系实施期修正，对齐 module=特性名先例与登记落点匹配，见 verification"定制清单刷新"节） |

> **缩小重构记录（2026-10-27，负责人确认在 PR #60 内执行）**：初版 R2 表曾含
> `clients.py` 两处（`_login_token()` 函数 + `_build_default_headers` docstring，+23 行）。
> 依"减少一处上游改动也值得认真对待"原则收敛：token 解析逻辑归位 auth 包
> （`chrys.aixcoding.auth.login_token_header_value()` 公共函数，自定义路径），`clients.py`
> **完全退出 R2**（对 base diff 归零），wire_client 对定制层由"经 clients 私有函数的间接
> 依赖"改为"直接 import auth 包"（分层合规：service(2)→aixcoding(1) 合法向下，
> test_layering 零豁免、check_import_boundaries 零违规；依赖显性化利于升级冲突可见）。
> 附带收益：catalog 批次的 `_catalog_token` 可直接复用该公共函数，消除 0.28 的双份实现。

R1 自查：业务逻辑（会话/存储/加密/轮询/token 解析）全部外置 `src/chrys/aixcoding/auth/`；
上游仅剩**一个**最小接线锚点（send-time 注入点），构造期快照方案已被 0.28 否决、hook/patch
路线经评估劣于显式挂点（见对比二与四轮评审）——单文件挂点为 chrys 侧 send-time 语义的最小承载。

**不改动**的上游相邻项：`clients.py` **整文件**（缩小重构后恢复上游原样）、`wire_client.py`
的 `WireClient._stamp_request_headers`（None 跳过路径保留原样）、
`tests/architecture/test_layering.py`（auth 落 `src/chrys/aixcoding/` 自动 tier 1，无需新
DAG 豁免——service(2) → aixcoding(1) 属合法向下依赖）、`pyproject.toml`（httpx 已声明，
per-file-ignores 无需新增）。

## 迁入映射与改写点

### 1. 产品代码（9 文件，旧 `aixcoding/auth/` → 新 `src/chrys/aixcoding/auth/`）

| 文件（行数） | 改写点 |
|---|---|
| `types.py`（177） | 零依赖叶子，原样；docstring 补 `Design: aixcoding/docs/batches/auth/design.md` 指引行（对齐 diagnostics 形态） |
| `errors.py`（52） | 原样（同上补指引行） |
| `environments.py`（87） | `ENVIRONMENT_VARIABLE`/`SERVER_URL_VARIABLE`（:42-43）值改 `AIXCODING_AUTH_ENVIRONMENT`/`AIXCODING_AUTH_SERVER_URL`；docstring 4 处引用同步（:18,21,71 直改；**:24-25** "deliberately mirror the ``CHRYS_*`` convention of the host app" 更名后语义反转，**改写**为 AIXCODING_ 前缀的归属说明，不得原样平移）；包内 import `from aixcoding.auth.types import Environment`（:34）同总则改写 |
| `delegation.py`（87） | `DELEGATED_TOKEN/EHR/NAME_VARIABLE`（:40-42）值改 `AIXCODING_AUTH_DELEGATED_TOKEN/_EHR/_NAME`；docstring 2 处引用同步（:23,25）；兼容通道 `AIXCODING_USER_EHR`/`OPENAI_API_KEY`（:46-47）**不动** |
| `crypto.py`（266） | 原样（DPAPI/Keychain/明文降级，零第三方） |
| `storage.py`（200） | 顶部包内 import `from aixcoding.auth.crypto/types import ...`（:34-40）同总则改写；docstring `:class:`~aixcoding.auth.crypto.MemoryBackend`` 交叉引用（:18）同总则改写；lazy `chrys.foundation.platform` import 路径不变（0.31 platform 已模块化成包，`get_platform().config_dir` 存活已核）——**"路径不变"仅指这一处 lazy import，勿误读为 storage.py 的 import 全不动**；**PEP 758 无括号 `except A, B:`（:119,139）保留，勿"修复"** |
| `client.py`（166） | 包内互引 import 改 `chrys.aixcoding.auth.*` 绝对导入 |
| `session.py`（245） | 同上 |
| `__init__.py`（70） | 同上；`__all__` 26 项不变 |

包内 import 改写规则（统一）：0.28 的 `aixcoding.auth[.X]` 全部改 `chrys.aixcoding.auth[.X]`
（绝对导入，对齐 mock 迁入 ADR-0001 以来的口径）——**覆盖代码 import、docstring Sphinx 交叉
引用（`:class:`~aixcoding.auth.X``、`:mod:`aixcoding.auth`` 等）与 docstring/注释中的示例
import，逐文件 grep 终验**；旧文件首行 Huawei copyright + "AIxCoding
device-code login" docstring 保留，R3 标记按现行规范形态（`AIxCoding` 关键词、无方括号）核一遍。

### 2. 测试（旧 `tests/app/aixcoding/` → 新 `aixcoding/tests/auth/`）

| 旧文件（行数） | 处理 |
|---|---|
| test_auth_client/crypto/delegation/environments/session/storage/types（7 个，共 ~1113） | 迁入；**import 统一改写**（18 处 `from aixcoding.auth[.X] import ...` / `import aixcoding.auth.session` → `chrys.aixcoding.auth[.X]`，同产品代码规则）；**env 字面量同步**：`test_auth_environments.py` 6 处硬编码（:20,25,47,53,59,65）——测试传 `{"CHRYS_AUTH_ENVIRONMENT": ...}` 而代码改读新名后 key 失配，会静默 fall back PROD 破坏断言语义，必须随更名逐处改；mock import `mock_server.aixcoding_auth.server` → `aixcoding.mock.auth.server`（test_auth_session:11、test_auth_delegation:27、test_auth_client:233 类内 lazy 三处）；含 `TestLoopbackMockIntegration`（mock 端到端，PR #56 mock/auth `__init__.py:27-30` 预告的"端到端行为测试随 auth 迁入到达"）。注：`test_auth_delegation.py` 经 `DELEGATED_*_VARIABLE` 常量构造 env，改常量值自动跟随，无字面量 |
| **新增** `test_llm_token_wiring.py`（~130） | 0.28 LLM 接线无测试覆盖，本期补强：① 有登录态 → `RequestHeaders.stamp()` 注入 `token` 头；② 无登录态/异常 → 不含头、请求照发；③ **覆盖语义双通道**：登录 token 覆盖 caller 经 `extra_headers` 传入的静态 `token`，**且**构造静态 `token` 在 `profile.http_headers`（→ `default_headers` 构造期层）的场景——0.28 语义是 SDK 的 default_headers 与 per-request extra_headers 合并后登录 token 胜出（credential authoritative），两通道都要锚定。通道 2 的锚定手段（真实 SDK client + mock transport 观察最终 wire 头，还是分层断言 `stamp()` 进 extra_headers + `_build_default_headers()` 进 default_headers 后依赖 SDK 已知合并语义）**在 test-plan 阶段钉死**；无论哪种，不得把 SDK 合并行为 mock 掉（DEVELOPMENT.md §5 行为锚定原则）；④ `_login_token()` 全吞错。落在 `aixcoding/tests/auth/`（import `chrys.service.llm.wire_client`，B1/B3 边界内合法） |
| 旧 `conftest.py`（33） | **不迁**：唯一 fixture `provide_tui_variable_defaults` 是 TUI 域专用（随 tui 批次再建） |
| test_login_dialog / test_login_command_wiring / test_update_detection | **不属本期**（tui / update 批次），留旧分支原位 |

**测试隔离与网络边界声明**（迁入 `aixcoding/tests/auth/` 脱离根 `tests/conftest.py` 三护栏
——config-dir 重定向 / `CHRYS_*` env 清理 / socket 网络守卫——后必须写死的两件事）：

1. **隔离自带**：7 个迁移测试全部自带隔离（`tmp_path` / `config_dir=` 注入 / backend 注入 /
   environ dict 传参，外部评审抽验 `test_auth_storage.py:17-19`、`test_auth_session.py:31-37`），
   不依赖根 conftest；实施终验若发现任一用例依赖环境（写真实 `~/.chrys`、读 `os.environ`），
   按 ADR-0001 在 `aixcoding/tests/auth/conftest.py` **自建**等价 fixture（禁 import `tests.*`）。
2. **网络策略**：`aixcoding/tests` 无网络守卫（根 conftest 的 guard 对 loopback 本就放行，迁入后
   连放行语义也消失）——本批测试仅连 loopback（127.0.0.1:7777 mock，`TestLoopbackMockIntegration`
   同旧位形态）；**约束：`aixcoding/tests` 禁止引入非 loopback 网络目标**，guard fixture 是否
   统一自建留后续测试基建议题（mock 契约测试已同状态跑绿先例）。

**本地验证命令组合**（`pyproject.toml` `testpaths=["tests"]` 且 `scripts/chrys_test.py` 零命中
`aixcoding` → Smart Test `--paths` 选不到本批测试，AGENTS.md 默认流程对本批**不适用**，以下组合
为准——Smart Test 仍跑上游侧 `tests/service/llm`）：

```bash
uv run pytest aixcoding/tests -m "not integration and not gc_calibration"   # 定制侧全量
uv run pytest tests/service/llm                                            # 上游被改两文件的相邻测试
uv run python scripts/chrys_test.py --smart --paths src/chrys/service/llm/clients.py src/chrys/service/llm/wire_client.py   # 上游侧 Smart Test
```

### 3. 环境变量更名方案（一次性，无兼容期）

| 旧名 | 新名 | 依据 |
|---|---|---|
| `CHRYS_AUTH_ENVIRONMENT` | `AIXCODING_AUTH_ENVIRONMENT` | ADR-0009 字面 |
| `CHRYS_AUTH_SERVER_URL` | `AIXCODING_AUTH_SERVER_URL` | ADR-0009 字面 |
| `CHRYS_AUTH_DELEGATED_TOKEN` | `AIXCODING_AUTH_DELEGATED_TOKEN` | ADR-0009 总则（fork 新增变量统一 AIXCODING_ 前缀）；ADR 字面仅列举前两件，本 design 依据总则扩展，负责人 2026-10-26 拍板同步更名 |
| `CHRYS_AUTH_DELEGATED_EHR` | `AIXCODING_AUTH_DELEGATED_EHR` | 同上 |
| `CHRYS_AUTH_DELEGATED_NAME` | `AIXCODING_AUTH_DELEGATED_NAME` | 同上 |

不动：兼容通道 `AIXCODING_USER_EHR` / `OPENAI_API_KEY`（desktop ≤fix-1008 契约）；
新基线 `tests/foundation/util/test_env_templates.py` 的 `CHRYS_AUTH_TYPE`/`CHRYS_AUTH_TOKEN`
（env 模板解析的无关样例变量，**勿误改**）。

**跨仓联动查证**（2026-10-26）：desktop 仓 `aixcoding-continue` 全仓 grep
`CHRYS_AUTH_DELEGATED` 零命中——主通道注入未实装，更名无断链风险；未来实装按新名。
desktop 若走兼容通道（`AIXCODING_USER_EHR`+`OPENAI_API_KEY`）完全不受影响。

**更名联动面**（2026-10-26 全仓 grep `CHRYS_AUTH_` 后逐项核定，外部 AI 评审补漏 + 全仓重扫收敛）：

- 代码（`aixcoding/mock/` 内，非上游）：`mock/auth/__init__.py:17`、`mock/auth/server.py:43`、
  `mock/auth/README.md:24`、`mock/__main__.py:11,163`、`mock/README.md:11,17,48`、
  `mock/model_catalog/server.py:17,26,95`、`mock/model_catalog/README.md:19,26`；
- 文档配方串：`docs/batches/mock/design.md` **5 处机械联动**（:99,106,108,114,115——配方说明与端口表，
  设计语义零变化）——文末变更记录注明"2026-10-26 auth 更名联动（见 batches/auth/design.md）"即视为
  授权处理，不重走 R10 全量重签；ADR-0009:74-75 已预告该同步（"文档配方 + mock README"）；
- **不回改**：`docs/batches/mock/verification.md` 历史验证记录（活文档"不删旧记录"，记录的是当时
  真实执行的命令；更名后新验证轮次自然追加新记录衔接）、`docs/batches/devtools/archaeology-report-0.28.0.md`
  （考古报告钉死 0.28 历史原貌，改即失真）、`docs/standards/adr/0009` 正文（决策记录含
  旧→新映射本身）、**`docs/batches/mock/design.md` 的 4 处历史/决策记录**（:121 议题由来——负责人质询
  旧名前缀归属的史实；:130 考古事实表——记录 0.28 当时变量名与 "deliberately mirror CHRYS_*"
  动机；:151-152 决策状态——CHRYS_→AIXCODING_ 更名动作本身，机械替换将致同义反复/史实失真）；
- **勿误伤**：同行出现的 `CHRYS_MODEL_CATALOG_BASE_URL`（mock/README.md:48、batches/mock/design.md:115）
  属挂上游 settings 体系的例外，**不改**（ADR-0009 口径）。

## 对上游隐式行为的假设

1. **wire-client 重构等价性**：0.31 `RequestHeaders.stamp()`（每个请求构建的最后一步，
   `WireClient` docstring: "Every protocol builds its request through one method that ends
   with `_stamp_request_headers`"）= 0.28 instrumented `_set_chrys_request_headers` 的
   send-time 边界。失效表现：token 头未随请求发送 → 内网网关 401。
2. **裸 codec 跳过路径**：无 `RequestHeaders` 的 wire client（codec 测试用裸客户端）不注入
   token——产品路径全部携带 RequestHeaders，与 0.28 语义等价；记录为已知边界非缺陷。
3. **`token` 头不属 chrys managed names**（已核 0.31 `chrys_headers.py` 无 token 项）：caller
   静态 `token` 保留至登录 token 覆盖；失效表现：覆盖优先级行为变化。
4. **`get_platform().config_dir` 存活**（已核 0.31 `foundation/platform/__init__.py:46`）：
   失效时 storage 自身吞错回落 `~/.chrys`（storage.py:45-56 既有语义），非阻塞。
5. **httpx==0.28.1 已声明**（pyproject:48，auth 唯一第三方依赖零新增）。
6. **mock 契约端点对齐**（PR #56 已核）`/api/v1/auth/device/{code,token}` + `/api/v1/user/info`
   与 `AuthClient` 请求路径一致；失效表现：TestLoopbackMockIntegration 红。
7. **token 值不经 charset gate**：`headers["token"] = login_token` 赋值在
   `_reject_wire_unsafe_request_values` 之后（0.28 同行为）——token 来源是本地加密存储的
   受控值而非手编辑配置，上游升级若调整 gate 位置，此处对照 0.28 行为保持不动。
8. **token 过期 = 网关 401，无"请重新登录"提示**：`stored_token` 在 credential 过期时返回
   None（发送侧表现与未登录一致），`StoredCredential.refresh_token` 字段存在但从不使用——
   tui 批次前无重登入口，属已知边界非 bug（避免后续误报）。
9. **早退分支语义微变**：加 `and not login_token` 后，"有 token 但 model/session 全空"的
   请求 caller `extra_headers` 首次经 managed-name 过滤重建（原早退分支直接透传）——产品路径
   model 恒非空（三 codec 均传 `model`），仅裸 codec/测试路径可见。
10. **openai_responses continuation 轮询不经 stamp**：`_poll`/`token is not None` 分支绕过
    `_build_request`，轮询请求不带 token 头——0.28 同类既有边界，随该 codec 上游演进观察。

## 定制点登记预告

> 节标题须保持标准形态（`gen_customizations.py` 全等匹配）。点级登记（customization-registry 批次起）：匹配键＝(落点, marker 锚)，id 为沟通标识。
>
> **批次锚注**（anchor/risk 列「（批次锚注）」指此段）：anchor＝`chrys.foundation.platform`（storage lazy import）+ httpx + kernel 门面导入链（`chrys.kernel/__init__` 包级导入，冷导入 206ms/354 模块一次性，主程序运行时零增量；门面导入期异常时崩溃钩子未装的窄窗口——tier-migration 勘误 C1 语义并入）。risk＝低（tier 1 自治包 + 上述窄耦合边；`RequestHeaders.stamp()` 方法若上游再重构 header stamping 需重接线，对照 0.28→0.31 instrumented→wire_client 迁移史）。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C021 | src/chrys/service/llm/wire_client.py | AIxCoding auth: send-time | | （批次锚注） | （批次锚注） | 〔上游等价〕上游 wire_client 原生支持从登录会话/凭据存储注入请求头，且满足内部凭据管理需求（对比确认后提请裁决） |
| C022 | src/chrys/service/llm/wire_client.py | AIxCoding auth: helper path | | （批次锚注） | （批次锚注） | 〔上游等价〕随 C021 一并裁决（ADR-0011 路径注释行随实现迁移） |

## 实施流程约束（R2 gate 机器语义，2026-10-26 四轮评审补写）

1. **先签认后动工，顺序硬约束**：`check_r2_diff.py` 的批准池 = 全部**已确认** design 的
   "上游改动清单"表所列文件名并集——**草案状态的本文档授权为零**。实现 PR 的 CI R2 gate
   按 `git diff --name-only <base>` + untracked 比对，出现本文 R2 表之外的上游文件即 exit 1。
2. **实施第一步 = 探针式接线**：两文件各加最小改动（`clients.py` 空 `_login_token` + marker、
   `wire_client.py` 一行 marker 注释）后立即跑
   `uv run python aixcoding/tools/check_r2_diff.py --base "$(git merge-base origin/main_iCode HEAD)"`
   确认上游改动集合收敛为 R2 表的 2 个文件，再写完整实现与测试——把"发现第三文件"的返工
   风险消灭在写实现之前。
3. **集合外溢出协议**：实施中确需第三个上游文件（如 codec、`chrys_headers.py`）→ 停手 →
   改本文 R2 表 → R10 重新签认 → 再继续；不得先改代码后补表。
4. 自定义路径（根 `aixcoding/`、`src/chrys/aixcoding/`、aixcoding CI workflow）在 R2 范围外，
   auth 9 文件与测试免 R2（工具规则 `is_upstream` 已核）。

## 风险与最坏情况

- **本期无产品内登录入口**（TUI 批次前）：登录只能经 mock 流程（测试）或手动脚本触发——
  范围 B 的固有边界，验收以 mock 端到端 + LLM token 注入测试为准，可接受。
- **上游再重构 send-time 边界**：wire_client 是 0.31 新结构（`84a8b97` one-package-per-wire
  重构的产物），若追版本时 stamp 再变，按本 design "对比二" 的语义不变量（send-time 逐请求
  解析 + 全吞错 + token 头名）重新找落点即可，auth 本体不受影响。
- **每请求读盘成本（记录不实施）**：`_login_token()` → `store.load()` = 每次 LLM 请求一次磁盘
  读 + OS 解密（Windows DPAPI）+ JSON 解析，且在 async 路径同步阻塞；一个 turn 可有数十次 wire
  call，相对 LLM RTT 可忽略。若实测成瓶颈，加 ~1s TTL / mtime 缓存（保持"登出下一请求生效"
  语义）——优化留待实测数据支撑，本期不做。
- **回滚**：整个批次一个 PR；回滚 = revert PR。auth 包为新增目录零残留；两个上游接线点
  删除即恢复纯上游形态；env 更名回滚需同步回 mock 联动面（同一 PR 内，原子）。

## ADR 判定（DEVELOPMENT.md §6）

- 新建 ADR：**不需要**——env 更名是 ADR-0009 总则的执行（DELEGATED_* 三件按总则扩展并在本
  design 记录拍板，属执行澄清非决策推翻）；上游改动走本 design 的 R2 报批；无新依赖（R11）；
  不推翻任何既有 ADR；不新增目录约定（`src/chrys/aixcoding/auth/` 符合 ADR-0002 既有蓝图）。
