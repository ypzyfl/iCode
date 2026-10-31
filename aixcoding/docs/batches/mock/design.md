# 设计：mock 基建迁入（aixcoding/mock）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-25
- 确认意见：无特别意见

## 方案概述

阶段三第 1 项：将旧分支 `mock_server/` 三服务（auth / update / model_catalog）复制迁入
`aixcoding/mock/`（M1–M3，纯开发资产、零上游改动），并新增包根组合启动器
`__main__.py` 解决手动 TUI 联调"要记得起多个 mock"的痛点。M4（telemetry-mock）随
telemetry 殿后（ROADMAP §2 阶段三，2026-10-25 顺序调整）。

```
aixcoding/mock/
├── __init__.py            # 命名空间锚点（docstring 重写，分级约定移 README）
├── __main__.py            # 组合启动器：python -m aixcoding.mock（一键起基础组合）
├── README.md              # M6：注册表 + 新增 mock 步骤 + 端口约定 + launcher 用法
├── auth/                  # M1：设备码认证 mock（server.py 547 行 + __init__ + README）
├── update/                # M2：版本更新检测 mock（server.py 558 行 + __init__ + README）
└── model_catalog/         # M3：模型目录 mock（server/modes/source/state + config_new.json
                           #     + __init__ + README；默认同端口内嵌 auth 路由，行为原样保留）
```

测试落点：`aixcoding/tests/mock/`（契约测试三份：`test_auth_server.py`（**新增最小集**，
见"命名与 CLI 形态变化"）、`test_update_server.py`、`test_model_catalog_server.py` +
子目录 `conftest.py` 的 `direct_route` 夹具）。

## 备选方案对比

**对比一：手动联调"起多个 mock"痛点的解法**（2026-10-25 与负责人确认取组合启动器）：

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| 合并单 server 单进程单端口 | 一条命令一个端口 | 需 ADR 推翻 DIRECTORY.md §6；产品端 LOCAL 默认配置必须改（auth :7777 与 update/telemetry base 分属 environments.py / config.py，统一端口牵连 auth 特性）；故障域耦合 | 零（同在 aixcoding/） | 否 |
| **组合启动器（单进程多线程，各 server 独立端口）** | 一条命令；子包独立性/契约测试结构/产品配置零变动；纯 stdlib | 多端口（launcher 打印地址清单） | 零 | **是** |
| 维持现状（多命令） | 零成本 | 痛点不解决 | 零 | 否 |

**对比二：契约测试 HTTP 客户端**（修正此前"统一 urllib"倾向）：

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| 保留 httpx（现状） | 零改写；async 形态对齐产品端 `chrys/aixcoding/http.py` 的 AsyncClient；上游主依赖（pyproject `httpx[socks]==0.28.1`）零新增 | 与 update 测试的 urllib 手法不一致 | **是** |
| 统一 urllib | 手法一致 | 改写 catalog 契约测试的 async 用例；与产品端 async 形态脱节 | 否 |

## 迁入映射与改写点

### 逐文件映射（来源：旧分支 `mock_server/`，行数为实测）

| 旧落点 | 新落点 | 改写点 |
|---|---|---|
| `__init__.py`（44） | `aixcoding/mock/__init__.py` | docstring 重写：命名空间锚点 + 指引 README（分级约定移 README） |
| `aixcoding_auth/{__init__,server}.py`（32+547）+ README（59） | `auth/` | 无跨包 import，原样；README 用法改 `python -m aixcoding.mock.auth.server`；测试桩示例改 `aixcoding.mock.auth.server`；**新增最小契约测试** `aixcoding/tests/mock/test_auth_server.py`（评审 blocker 修正，见下） |
| `aixcoding_update/{__init__,server,test_server}.py`（35+558+418）+ README（99） | `update/`；`test_server.py` → `aixcoding/tests/mock/test_update_server.py` | import 改名；README 同上 |
| `chrys_model_catalog/{__init__,server,modes,source,state}.py`（44+608+76+55+64）+ `config_new.json`（14）+ README（114） | `model_catalog/` | ① `from mock_server.aixcoding_auth.server import …` → `from aixcoding.mock.auth.server import …`（内嵌 auth 路由，行为原样保留，含 `--no-auth`）；② 包内互引 `mock_server.chrys_model_catalog.*` → `aixcoding.mock.model_catalog.*`（**保持绝对导入**——直跑形态无包上下文，相对导入不可用）；③ server.py 的 `sys.path.insert` 直跑 hack **保留并适配**（`parents[2]` → `parents[3]`，注释同步。动机还原：hack 专供"直跑脚本文件"形态——直跑时 `sys.path[0]` 是脚本目录而非仓库根，跨包/包内绝对导入都依赖它；`python -m` 形态下冗余但无害）；④ `source.py` 读 `config_new.json` **零改动**（源码核验 2026-10-25：已是 `Path(__file__).with_name("config_new.json")` 包内定位，随目录迁移自然正确——原"实施时核对"提前关闭） |
| `chrys_model_catalog/{test_server,conftest}.py`（250+63） | `aixcoding/tests/mock/test_model_catalog_server.py` + `conftest.py` | import 改名；`direct_route`/`clear_proxy_env` 保持复制实现（不 import 上游 tests/conftest——上游测试接口无稳定性承诺，ADR-0001 故障域隔离） |
| `README.md`（77） | `aixcoding/mock/README.md` | M6：注册表/新增步骤/命名约定平移改写（去前缀命名、`python -m` 用法、端口表、launcher） |
| `mock_server/`（整目录） | 无动作 | 新分支不存在该目录，M5 无删除动作 |

### 命名与 CLI 形态变化

- 子包去前缀：`aixcoding_auth` → `auth`、`chrys_model_catalog` → `model_catalog`（DIRECTORY.md §9）；
- CLI **双形态均支持**：直跑 `python aixcoding/mock/<name>/server.py`（沿用旧分支 README
  使用惯例，依赖 sys.path hack）与 `python -m aixcoding.mock.<name>.server`（模块运行。
  `-m` 须落到 `server.py`——子包 `__init__.py` 仅 docstring 无入口，`-m` 到包名不起服务，
  2026-10-25 评审勘误；launcher 例外：包根有 `__main__.py`，`python -m aixcoding.mock` 正确）；
  README 以直跑为主示例、`-m` 并列。DIRECTORY.md §6 的 main() 约定不限定调用形态；
- `--port` 参数勘误（2026-10-25 源码核验）：**auth 已有**（`server.py` 经 `args.port`）、
  catalog 已有（`--port 0` 随机）；**仅 update 需补**（其 `__init__.py` 注释明确
  "there are no CLI flags"）——端口被占人工作出时需要；
- auth mock **补最小契约测试**（`test_auth_server.py`：设备码申请 `result` 信封 / 轮询
  pending-authorized 交替与 `access_denied` / `user/info` `data` 信封及未知 token 的
  "HTTP 200 + code:400 无 success 键"怪癖，2–4 个用例）。**评审 blocker 修正
  （2026-10-25）**：原方案"不配测试、靠 auth 特性端到端覆盖"与 DIRECTORY.md §6
  "每个 mock 必须有契约测试，无契约测试的 mock 不得合入"**硬冲突**；且契约测试锚定的
  是 **mock 自身的 wire 复刻**，与"产品端是否测过"是两个层面，不能互相替代；再者
  auth 特性测试迁入前存在无测试窗口期。三选一裁决：①补最小契约测试（**采纳**）；
  ②登记例外（留下窗口期裸奔，且违背规范精神）；③延迟合入（不可行——catalog 内嵌
  auth 路由依赖 `aixcoding.mock.auth.server` 的 `build_handler_class` 等，auth
  server.py 必须随 catalog 同步进入）。旧分支"不配测试"决策的真实语境（避免与
  `tests/app/aixcoding/` 端到端用例重复建设）在迁入期不成立；auth 特性迁入后端到端
  用例回归，契约层与端到端层各司其职。

## 组合启动器设计

`aixcoding/mock/__main__.py`（实现薄，可直接单文件；复杂化再拆 launcher.py）：

- `python -m aixcoding.mock`——默认起**基础组合**：model_catalog（:7777，含内嵌 auth 路由，
  即"登录 + 模型目录"一次就绪）+ update（:7778）；
- `--all`：加全部已迁入 mock（telemetry 迁入后含 :4321）；`--only auth,update` 自选；
  `--list`：列可用 mock、端口、产品端配置项；
- 实现：argparse → 调各子包 `create_server(...)`（固定端口）→ 每 server 一 daemon 线程
  `serve_forever` → 打印服务清单与**产品端联调配方**（`AIXCODING_AUTH_ENVIRONMENT=local`、
  `AIXCODING_EXTENSION_BASE_URL=http://127.0.0.1:7778/csas` 等）→ 等 KeyboardInterrupt →
  全部 shutdown；端口被占时明确报错指出是哪个服务。

### 端口约定（沿用旧分支既有默认，产品端 LOCAL 档已对齐）

合用说明：catalog 默认与 auth 合用 :7777 **并非技术上必须**——auth 有
`AIXCODING_AUTH_SERVER_URL` 覆盖（替换 origin 保留 `/api/v1` 路径）、catalog 有独立 base
配置项，任意端口组合都配得出——而是 LOCAL 档零配置联调的刻意选择：
`AIXCODING_AUTH_ENVIRONMENT=local` 默认指向 :7777，catalog 内嵌 auth 路由后**单 server +
单 env** 即覆盖登录、目录、LLM chat（`apiBase` 指 :7777/v1）。`--no-auth` + 独立
auth mock 的拆用形态原样保留。

| mock | 默认端口 | 产品端指向（默认） | 换端口逃生门（产品端 env） |
|---|---|---|---|
| auth（独立形态） | 7777 | `AIXCODING_AUTH_ENVIRONMENT=local`（零配置） | `AIXCODING_AUTH_SERVER_URL` |
| model_catalog（默认内嵌 auth） | 7777 | 同上（一站式）；目录端点经 `model.catalog.base_url` | `CHRYS_MODEL_CATALOG_BASE_URL`（目录）/ `AIXCODING_AUTH_SERVER_URL`（auth） |
| update | 7778 | `AIXCODING_EXTENSION_BASE_URL=http://127.0.0.1:7778/csas` | 同左（改指新端口） |
| telemetry（殿后，占位） | 4321 | config.py LOCAL 档默认 | 同左 |

### 决策记录：auth 环境变量前缀 CHRYS_ 改为 AIXCODING_（2026-10-25 拍板）

> 议题由来：2026-10-25 本 design 审阅中负责人质询 `CHRYS_AUTH_SERVER_URL` 前缀归属
> （"是否为培养上游代码"）。经查证不成立，但暴露 fork 内两套前缀并存、分界不显著的
> 真问题。完整记录于此，供 auth 特性迁入引用与后续规范参考。

**考古事实**（0.28.0 全景，fork 定制新增的环境变量）：

| 变量 | 所属模块 | 前缀 | 命名动机（代码注释自述） | 硬约束 |
|---|---|---|---|---|
| `AIXCODING_EXTENSION_PROFILE` / `AIXCODING_EXTENSION_BASE_URL` / `AIXCODING_TOKEN` / `AIXCODING_TELEMETRY_DISABLED` | `chrys/aixcoding/config.py` | AIXCODING_ | "对齐 aixcoding 同名环境变量"——桌面端产品线的跨产品契约 | 有（桌面端同名字段语义） |
| `CHRYS_AUTH_ENVIRONMENT` / `CHRYS_AUTH_SERVER_URL` | `aixcoding/auth/environments.py` | CHRYS_ | "deliberately mirror the `CHRYS_*` convention **of the host app**"——运行宿主进程命名空间一致性 | **无**：纯 fork 模块；上游不存在此变量；桌面端零消费（2026-10-25 于 aixcoding-continue 全仓检索证实） |
| `CHRYS_MODEL_CATALOG_BASE_URL` / `CHRYS_MODEL_CATALOG_SYNC_INTERVAL` | `service/profiles/models/catalog.py`（上游文件定制点） | CHRYS_ | 配置声明挂上游 foundation settings 体系（`chrys.foundation.config.settings`） | 有（宿主配置声明机制） |

**判断**：①"为回馈上游而用 CHRYS_"不成立——注释所指是运行宿主（host app）而非上游仓库，
且同仓 telemetry 用 `AIXCODING_` 反证当时无统一前缀策略，各模块各按理由命名；
②三组变量中 `CHRYS_AUTH_*` 的宿主一致性理由最弱（纯 fork 模块、无任何硬约束），且存在
"伪上游变量"认知成本（上游代码/文档查无此变量，审阅者自然产生归属疑问）。

**备选方案**：

| 方案 | 内容 | 成本 | 收益 | 结论 |
|---|---|---|---|---|
| A 保持 `CHRYS_AUTH_*` | 不动 | 零 | 零；认知成本永续，前缀分裂固化 | 否 |
| B 更名 `AIXCODING_AUTH_*` | auth 迁入时一次性切换（模块 + 测试 + 文档联调配方 + mock README 配方同步） | 小：桌面端零消费已查证、消费点限于本仓、内部产品无需兼容期 | fork 定制变量前缀统一，消除伪上游变量误导 | **已决策（采纳，2026-10-25）** |
| C 双前缀兼容期 | 旧名 alias 过渡 | 双倍维护面 | 过度设计（内部产品） | 否 |

`CHRYS_MODEL_CATALOG_*` 无论决策结果均**不改**（挂上游 foundation settings 声明体系，
改名侵入上游配置机制，违反最小改动）。

**决策状态**（负责人 2026-10-25 结构化问答拍板）：

- **改**：auth 环境变量前缀 **CHRYS_ → AIXCODING_**——`CHRYS_AUTH_ENVIRONMENT` /
  `CHRYS_AUTH_SERVER_URL` 于 auth 特性迁入时一次性更名
  `AIXCODING_AUTH_ENVIRONMENT` / `AIXCODING_AUTH_SERVER_URL`，实现 fork 定制变量
  前缀统一、消除伪上游变量误导；
- **不改**：`CHRYS_MODEL_CATALOG_BASE_URL` / `CHRYS_MODEL_CATALOG_SYNC_INTERVAL`——
  挂**上游 foundation settings 声明体系**（`chrys.foundation.config.settings`），
  改名侵入上游配置机制、违反最小改动原则；
- 配套：命名约定已固化于 DIRECTORY.md §9（fork 新增环境变量统一 `AIXCODING_` 前缀，
  挂上游 settings 体系者例外并登记）。

**执行时点**：无论决策结果，**mock 基建行为锚定不改任何 env 名**（端口表与联调配方用
现名）；若决策 B，由 auth 特性迁入 design 引用本节执行切换，并同步更新 mock README 配方。

### 决策记录：mock 实现目录维持 `aixcoding/mock/`（2026-10-25 拍板）

> 议题由来：2026-10-25 本 design 审阅中负责人提议"实现放 `mock_server/`（因为是 mock
> 的 server），将来 iCode/aixcoding 进程内的 mock 再放 `mock/`"。

**分析要点**：

1. 命名与位置已有 ADR-0003 正式决策（`aixcoding/mock/` 专区 + `tests/mock/` 对仗）；
   其"否决的备选"针对根顶层 `mock_server/`（上游 `testpaths` 收集射程内的假上游目录），
   专区内更名虽不落入该射程，仍属规范修订（需增补 ADR + 改 DIRECTORY.md 四处）；
2. "进程内 mock"按 DIRECTORY.md §2 判定树**不归本专区**：测试专用 fake/stub 归
   `aixcoding/tests/`（§5），产品内可注入测试挂钩归 `src/chrys/aixcoding/`，专区被
   挤占的概率低；
3. 目录名与资产形态耦合（`mock_server/`）有演进风险：非 server 形态 mock 资产出现时
   目录名失真或需开平级目录；现行设计以目录名描述职责域、文件名描述形态（`server.py`）；
4. 更名涟漪面：ADR-0003 增补 + DIRECTORY.md §1/§2/§6/§9 + `tests/mock/` 对仗决策 +
   launcher 命令（`python -m aixcoding.mock_server`）。

**决策状态**（负责人 2026-10-25 结构化问答拍板）：维持 `aixcoding/mock/`；以
DIRECTORY.md §6 补"形态语义"说明吸收关切（当前全是 server 形态、进程内替身归属指引、
非 server 形态按 §2 重新论证），零规范扰动。

### 决策记录（三）：CLI 直跑形态保留 + sys.path hack 适配（2026-10-25 确立）

> 议题由来：初版 design 曾提"删除 sys.path hack、CLI 统一 `python -m`"，负责人审阅
> 质询"为什么要删除？请仔细分析原先提供 hack 的原因和动机"。

**动机还原**：hack（`sys.path.insert(0, parents[2])`，注释自述）专供**直跑脚本文件**
形态——`python mock_server/<pkg>/server.py` 时 `sys.path[0]` 是脚本所在目录而非仓库根，
而 catalog server 有跨包绝对导入（内嵌 auth 的 `mock_server.aixcoding_auth.*`）与包内
绝对导入（`modes/source/state`），无仓库根即全部 ImportError；auth mock 自包含故从
不需要；pytest 环境自带仓库根。旧分支三服务 README 的全部用法示例均为直跑形态——
**既定使用惯例**，非 hack 的附带品。

**决策**：保留直跑形态与 hack（迁入后适配 `parents[2]` → `parents[3]`，注释同步）；
CLI 双形态均支持（直跑为主示例，`python -m aixcoding.mock.<name>` 并列）；包内互引
保持**绝对导入**（直跑形态无包上下文，相对导入不可用；`-m` 形态下 hack 冗余但无害）。
删 hack 换来的仅是少 3 行代码，代价是强改调用习惯——不划算。

**已知脆弱点**：hack 索引依赖脚本目录深度（迁移/再挪动时须重核），已由注释锚定意图；
归类模块内实现选择，不升 ADR。

### 端口占用处理（fail-fast，不静默换端口）

固定端口是联调可预期的前提（产品端 LOCAL 档默认对齐）；静默换端口会让产品流量打不到
mock、联调者被半开组合误导。处理分层：

1. **启动明确报错**：launcher 与各 mock CLI 捕获 `OSError`（EADDRINUSE），输出
   "<服务> 需要 127.0.0.1:<端口>，已被占用"+ 查占指引（Windows：
   `netstat -ano | findstr :7777` → PID → `tasklist /fi "PID eq <pid>"`）；launcher
   遇占用**整体退出**，不起半套组合；
2. **逃生门**：人工换端口（mock CLI `--port`）+ 产品端 env 同步覆盖（见上表末列）；
3. **不做**：自动选空闲端口（违背可预期）、自动杀占用进程（越权危险）。

## 对上游隐式行为的假设

1. 契约测试消费者侧验证 import `chrys.service.profiles.models.catalog` 的
   `parse_catalog` / `ModelCatalogError`（0.28.0 符号）→ 假设 0.31.0 中同名符号仍存在且
   语义兼容 → 失效表现：测试期 ImportError/行为差异 → 迁入时以新基线重定位（ROADMAP
   阶段三原则：不得照抄旧行号）；
2. `direct_route`/`clear_proxy_env` 夹具复制自旧分支 `tests/conftest.py` → 假设其语义
   （清代理环境变量）在 0.31.0 不变 → 失效表现：代理干扰直连 → 实施时对照新分支
   `tests/conftest.py` 核对；
3. mock 端点路径与 wire 形态（信封、HTTP 200 语义、故障模式）是**我方对后端的契约复刻**，
   不随上游版本变化——上游消费方（catalog.py / update_detection.py / auth 客户端）迁入时
   若行为漂移，以其特性 design 为准回改测试，mock 侧不动。

## 定制点登记预告

无。本特性全部落 `aixcoding/mock/` 与 `aixcoding/tests/mock/`（纯开发资产、零上游文件
改动），不产生 CUSTOMIZATIONS.md 定制点。

## 风险与最坏情况

- **符号漂移**（假设 1）：0.31.0 `parse_catalog` 位置/签名变化 → 契约测试小改 import；
  最坏情况消费者侧验证暂时降级（保留 mock 行为断言、去掉产品解析器对拍），随 auth 特性
  迁入补齐；
- **launcher 端口冲突**：明确报错定位到服务，不静默换端口（联调要可预期）；
- **回滚**：删除 `aixcoding/mock/` 与 `aixcoding/tests/mock/` 即完整回滚，无任何上游残留。

## ADR 判定

特性级四问：

- 是否新增子包/落点未覆盖于 DIRECTORY.md？——否：`aixcoding/mock/` 是 §6 既有落点；
  launcher（包根 `__main__.py`）已作为编排层登记于 §6（2026-10-25 随形态语义段落字）；
- 是否引入新依赖/新机制？——否：launcher 为 stdlib（argparse + threading + 各子包既有
  `create_server`）；
- 是否推翻既有 ADR/规范？——否（ADR-0003 维持，§6 形态语义段为澄清非推翻）；
- 是否上游改动？——否（R2 无报批项）。

分项结论（评审修正 2026-10-25：正文含多项"认真考虑但否决的备选"，逐项过 ADR
checklist，不再笼统"全否"）：

| 决策项 | 记录位置 | 升 ADR | 依据 |
|---|---|---|---|
| 组合启动器 vs 合并单 server | 备选方案对比 | 否 | 模块内实现选择（反面清单）；合并方案否决根因（须改产品 LOCAL 默认）随方案否决失效 |
| 契约测试保留 httpx | 备选方案对比 | 否 | 模块内实现选择 |
| mock 目录名维持 `aixcoding/mock/` | 决策记录（二）+ §6 形态语义 | 否 | 对 ADR-0003 的重确认与语义澄清，未推翻任何决策 |
| 直跑形态保留 + sys.path hack 适配 | 决策记录（三） | 否 | 模块内实现选择（动机与脆弱性已记录在案） |
| fork 环境变量统一 `AIXCODING_` 前缀 | 决策记录（一）+ DIRECTORY.md §9 | **是 → ADR-0009（已出，待签认）** | 命中 checklist ①（否决备选：保持/兼容期）与 ③（约束未来全部特性的 env 命名） |

---

变更记录：

- 2026-10-26：auth 更名联动——`CHRYS_AUTH_ENVIRONMENT`/`CHRYS_AUTH_SERVER_URL` 配方串与端口表（5 处）同步为新名 `AIXCODING_AUTH_*`（机械联动、设计语义零变化；依据 ADR-0009 与 `aixcoding/docs/batches/auth/design.md` 联动面清单；:121/:130/:151-152 历史与决策记录按约定不回改）。
