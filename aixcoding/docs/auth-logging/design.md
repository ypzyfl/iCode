# 设计：auth 登录状态埋点（aixcoding.auth logging）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：全程参与讨论，所有问题已确认，含 10-30 格式适配与文案勘误。

## 方案概述

源码改动三处：①`src/chrys/kernel/aixcoding/auth/session.py`（定制层）：三个状态转换方法（`check_silent` / `complete_login` / `logout`）插入 12 条 logger 记录，logger 直取 `logging.getLogger("aixcoding.auth")`（**2026-10-30 修订：不再 import `diagnostics.get_logger`**——见下"依赖方向"与"风险"节的架构论证）；②**新增** `src/chrys/app/aixcoding/startup.py`（定制层，宿主挂接包）：聚合入口 `aixcoding_startup()`——启动期定制初始化任务的单点聚合（每个子任务独立幂等 + fail-safe；当前唯一子任务 `ensure_file_sink()`：`load_config` + `setup_logging` 包装，§9 全吞错 + stderr note）；③`src/chrys/app/cli/app.py`（上游，R2 报批一行级接线）：`main()` 起始处调用 `aixcoding_startup()`——**icode 入口的全部运行形态（TUI/headless run/ACP/serve…，2026-10-30 复核勘误：原表述"全 CLI 模式"分类不当——TUI/headless/ACP 是运行形态且全为该入口的分支）均挂 aixcoding 落盘**，推翻"仅 launcher 落盘"的初版边界（2026-10-29 责任人裁决）。聚合入口设计（2026-10-30 责任人定稿）：上游接线点固化——将来新增启动任务（如 model catalog 同步）只改定制层 `startup.py`，上游 `main()` 触碰次数从 N 收敛为 1（R2/marker/登记/freshness 全套成本只付一次）。

```
chrys.app.cli.app:main（全模式分发点，R2 接线 +1 调用）
    │ aixcoding_startup()（幂等、逐任务 fail-safe）
    ▼
app/aixcoding/startup.py（聚合入口，宿主挂接包）
    │ 子任务①：ensure_file_sink() → load_config + setup_logging
    ▼
logger "aixcoding"（顶层）◀── session.py 埋点（logging.getLogger("aixcoding.auth") 直写，零依赖）
    ├─ RotatingFileHandler（落盘恒开）──▶ %APPDATA%/chrys/aixcoding-logs/aixcoding.log（Unix ~/.chrys）
    └─ propagate = tui.panel 开关（diagnostics 批次已建）
        ▼ panel=true 时冒泡
root._TuiLogHandler（MODULE_ORDER 白名单已含 "aixcoding"）──▶ F6 "aixcoding" tab
```

launcher 已于 2026-10-30 退役（ADR-0013，批次 `launcher-retirement/` **先行合并——责任人终裁，空窗期接受**：auth 埋点从未进主干，无用户可见影响）；本批次（接线）尽快跟进合并，合并后全模式落盘就位。

依赖方向自查（R9 / DIRECTORY tier 表，2026-10-30 更新）：`main()`（app 层）→ `app.aixcoding.startup` 为 **app→app 同层**调用；`startup.py` → `kernel.aixcoding.diagnostics` 为 app(4)→kernel(1) 标准向下边（绝对导入，DAG 合法，无需豁免）；**`session.py` 直写 `logging.getLogger` 后与 `diagnostics` 零依赖**——原方案"auth 子包跨子包引用 diagnostics"存在架构死锁（`..` 父级相对被 ruff TID252 禁、kernel↔kernel 绝对导入被 `test_layering:550` 禁——2026-10-30 复盘发现原实施只过了 ruff/ty 未跑 architecture，属验证缺口；解耦后彻底消除该风险，且"import 通道"风险源同步消失）。聚合入口的分层依据：app/aixcoding 是宿主挂接包（tui 同族），启动挂钩属"与宿主的接缝"，且 app 最高层向下聚合无天花板（kernel 层方案则装不下 service/orchestration 层任务）。

## 埋点清单（12 条；消息全文为实施冻结口径）

消息语言**中文**（2026-10-29 责任人裁决：开发人员母语中文，日志应尽量用中文；编码无障碍——file handler `encoding="utf-8"`、F6 RichLog 中文显示无碍；§6"代码与注释跟随上游"不覆盖日志消息）。**保留英文的部分**：异常类名（`exc=`/`cause=` 的值，其他模块提供的技术标识）、字段名（`ehr`/`env`/`exc`/`cause`，短键便于 grep）。`%s` 参数化（延迟求值，便于 caplog 断言）；`[ cause=%s]` 段仅当 `exc.__cause__` 非 None 时附加。

**运行形态对应**（2026-10-29 责任人两次澄清）：定制支持两种形态——桌面端（AIxCoding 以 ACP 方式运行 iCode 子进程）与 CLI 端（用户直接 CLI/TUI 运行）。delegation 专属事件 4 条（#1/#2/#3/#9，其中 #1/#2/#9 消息带"桌面端"字样）仅桌面端子进程会发生（`AIXCODING_AUTH_DELEGATED_*` 环境变量由桌面端父进程注入，CLI 端 `detect_delegation()` 恒为 None）；其余 8 条两端语义相同、共用（桌面端委派被拒回退后同样触发本机登录分支的消息）。

**"桌面端"措辞的时效性边界**（2026-10-29 责任人裁决维持）：当前 delegation 的唯一生产注入方是 AIxCoding 桌面端，故消息直呼"桌面端登录"。已知边界——启动模式与登录来源**正交**：ACP 是通用协议，第三方 ACP 宿主启动 iCode 时不注入 AIxCoding 私有变量 → 走本机登录；登录来源的唯一信号是 delegation 检测本身，而非启动模式。将来其他宿主以 ACP 启动并注入 delegation 变量时，措辞改为机制词（"父进程传入的登录"）或扩展协议携带宿主名（如 `AIXCODING_AUTH_DELEGATED_HOST`），属将来批次。

| # | 方法 | 分支 | 级别 | 消息全文 |
|---|---|---|---|---|
| 1 | check_silent | delegated 校验成功 | INFO | `已登录（桌面端登录）；ehr=%s env=%s` |
| 2 | check_silent | delegated 被服务端拒（AuthServerError） | ERROR | `桌面端传入的登录已失效，改用本机登录；env=%s exc=%s` |
| 3 | check_silent | delegated 非服务端拒绝失败（AuthError 兜底，当前即 AuthNetworkError） | ERROR | `登录检查未完成（网络不通），登录状态保留；env=%s exc=%s[ cause=%s]` |
| 4 | check_silent | 无 live credential（含过期，无 delegation） | INFO | `未登录（首次使用或登录已过期）；env=%s` |
| 5 | check_silent | stored 校验成功 | INFO | `已登录（本机保存的登录）；ehr=%s env=%s` |
| 6 | check_silent | stored 被服务端拒（AuthServerError，已清除） | ERROR | `本机保存的登录已失效，已自动清除，请重新登录；env=%s exc=%s` |
| 7 | check_silent | stored 非服务端拒绝失败（AuthError 兜底，当前即 AuthNetworkError） | ERROR | `登录检查未完成（网络不通），登录信息保留；env=%s exc=%s[ cause=%s]` |
| 8 | complete_login | 成功（store 写入后） | INFO | `登录成功；ehr=%s env=%s` |
| 9 | logout | delegation active（跳过） | INFO | `跳过登出（当前使用桌面端登录，由桌面端管理）；env=%s` |
| 10 | logout | 真登出（credential 已清除） | INFO | `已登出；env=%s` |
| 11 | complete_login | 登录尝试失败（AuthError 家族，Cancelled 除外；记录后 re-raise） | ERROR | `登录失败；env=%s exc=%s[ cause=%s]` |
| 12 | complete_login | 用户取消（DevicePollCancelled；记录后 re-raise） | INFO | `取消登录；env=%s` |

### 分级原则（用户感知定级，2026-10-29 责任人两次裁决）

登录是定制层核心能力的门槛——**用户无法使用 AI 功能即是严重问题**：用户感知不区分根因（token 丢失还是网络不通，"AI 用不了"就是立刻抱怨级的事故），且日志受众是排查者而非终端用户，ERROR 密度不构成用户噪音。定级：

- **ERROR（#2/#3/#6/#7/#11）**：静默校验失败的全部四个分支——服务端拒绝（#2/#6，确定性丧失登录态，#6 伴随 credential 不可逆清除）与网络失败（#3/#7，token 虽保留，用户此刻所见同样是未登录/AI 不可用；离线启动留下的一条 ERROR 正是"用户抱怨当天网络就不通"的排查证据）；以及登录尝试失败（#11，poll 超时/拒绝/`fetch_user_info` 失败——用户感知同样是"登录不上、AI 用不了"，2026-10-29 双 AI 评审 F4 补、责任人裁决选 A）。
- **INFO（其余 7 条）**：成功与常规态转换。#4（无 live credential）维持 INFO（2026-10-29 责任人认可）：新用户首次启动的必经状态（"还没登录"而非"登录坏了"），是引导登录的路标，不是故障。#12（用户取消）非故障，INFO。
- WARNING 空缺：本模块状态语义中不存在"中间态"事件，不硬凑。

（历史：初稿曾按异常类型分 ERROR/WARNING 两档，2026-10-29 责任人裁决推翻——token 保留不能降级用户感知的严重性。）

实现映射：`check_silent` 四个失败分支（两处 `except AuthServerError` / 两处 `except AuthError`）一律 ERROR；`complete_login` 包一层 try/except——先 `except DevicePollCancelled`（INFO）后 `except AuthError`（ERROR），记录后原样 re-raise，控制流与 UI 行为零变更。`except` 分支即级别边界，测试断言规整。

与交接要点"8 处"的偏差说明：交接粗数未单列"无 live credential"态（#4）且 logout 未拆两态；逐分支核对后 10 条；2026-10-29 双 AI 评审（Deepseek-V4-Pro）F4 指出 `complete_login` 失败路径缺口，责任人裁决补 #11/#12，定稿 12 条。

调用频率自查：`check_silent` 仅 TUI 启动一次（`silent_login_check`）+ 手动登录流程，`logout` 仅 `/logout` 命令——无刷屏路径；"无 live credential"（#4）每次未登录启动一条 INFO，可接受。

### 脱敏与内容边界（2026-10-29 责任人确认：脱敏 + 不暴露技术性内容）

- 记录字段白名单：`environment`（env id）、`ehr`（仅成功路径 #1/#5/#8；注：ehr 属 PII，2026-10-29 责任人裁决记录不打码）、credential 来源（delegated/stored，嵌在消息文本）、异常类名（失败路径 `exc=type(exc).__name__`）。
- **失败原因记录格式**（责任人要求"尽量记录清楚原因"）：一律 `exc=类名`（`AuthServerError`=服务端拒绝 / `AuthNetworkError`=网络问题，异常子类扩展自动如实呈现）；网络类附 `cause=type(exc.__cause__).__name__`——底层 httpx 异常类名（如 `ConnectTimeout`/`ConnectError`），取自 `client.py` `raise ... from exc` 的异常链，`__cause__` 为空则省略。
- **两条红线（责任人 2026-10-29 明确）**：
  1. **脱敏**：token、refresh_token、device_code 等凭证值绝不入日志；
  2. **不暴露技术性内容**：不记异常 `str()`/`repr()`（`AuthError` 子类 message 透传服务端响应体，边界不受我方控制）；不记调用栈/traceback（不使用 `exc_info`/`logger.exception`，测试断言 `record.exc_info is None`）；不记 URL 与 HTTP 状态码（本协议 wire contract 不以状态码判错，价值有限且需改 `client.py`，不做）。
- `client.py` 不埋：poll 循环 `DEFAULT_POLL_INTERVAL = 1.0` 秒/次，记录即刷屏（交接已定）。

## 备选方案对比

埋点落点：

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| **埋 session.py（状态转换边界）** | `LoginSession` 即模块契约中的边界对象，三方法覆盖全部状态转换语义；每分支一条，量恰好 | 无 | 0 上游文件；定制层内约 +26 行 | **采用** |
| 埋 client.py（协议边界） | 覆盖 HTTP 层细节 | poll 每秒记录刷屏；协议细节弱状态语义 | 0 上游文件 | 否 |
| 埋 storage.py（持久化边界） | 覆盖读写 | `stored_token` 每次查询都走 `load`（登录徽标刷新即调），刷屏；且与 #1/#5 语义重复 | 0 上游文件 | 否 |

落盘全模式接线路径（2026-10-29 责任人裁决"所有模式下都必须有日志"后新增对比）：

| 方案 | 优点 | 缺点 | 升级冲突面 | 结论 |
|---|---|---|---|---|
| **E. 上游 CLI 入口单点 + 聚合入口（`app.py main()` 调 `aixcoding_startup()`）** | 一处覆盖**全部**模式（`main()` 是唯一分发点）；接线点固化——将来启动任务不触碰上游 | 触上游 1 文件 ×2-3 行（R2 报批，见下节） | 1 上游文件 ×2-3 行（**一次性**） | **采用**（2026-10-30 责任人定稿聚合形态） |
| E-0. 入口直调 `ensure_file_sink()`（初版） | 少一层聚合 | 将来每加启动任务重付一遍 R2/marker/登记/freshness（上游触碰 N 次） | N × 上游触碰 | 否（聚合形态取代） |
| A'. 零上游拼合（login_actions 模块级 + acp/server.py 定制段各加） | TUI 侧零上游 | headless 仍无落盘；接线分散两处、语义牵强 | 0 + 1 上游文件 | 否 |
| B. import 副作用（logging_support import 即 setup） | 零上游全覆盖 | 破坏"get_logger 零副作用"既定原则；配置时机不可控 | 0 上游文件 | 否 |

聚合入口层次（2026-10-30 责任人裁定 app 层）：

| 层次 | 判定 |
|---|---|
| **app/aixcoding/startup.py（采用）** | 最高层向下聚合无天花板（任何层的启动任务可挂）；宿主挂接包语义正解（tui 同族，"挂接归 app"原则第二次应用）；`app→app` 同层 + `app→kernel` 向下，绝对导入零摩擦 |
| kernel/aixcoding/startup.py | 只能聚合 kernel 层任务（将来 service 层任务向上违规需重定位）；kernel 定位是纯机制库，启动编排是接缝非机制 | 

R1 自查：埋点即日志语句，无逻辑外置需求；上游接线点唯一（全模式必经的 `main()`），能一处不两处且只碰一次。

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/cli/app.py` | `main()` 起始处函数内 lazy import + 调用 `aixcoding_startup()`（聚合入口本体是**新增定制文件** `src/chrys/app/aixcoding/startup.py`，不属上游改动；`ensure_file_sink()` 落 `logging_support.py`：`load_config` + `setup_logging` 的幂等 fail-safe 包装）——icode 入口全部运行形态均挂 aixcoding 落盘 | 2-3 | 调用行行尾，`# AIxCoding customizations: startup hooks on every icode invocation (src/chrys/app/aixcoding/startup.py)` |

R1 自查：业务逻辑全部外置定制层（聚合入口与子任务在 app/kernel 定制包）；上游仅剩"入口调一行"，无法更少且只碰一次；接线经 `test_layering` DAG 为 app→app 同层边（`startup.py` 内部 app→kernel 向下），无需豁免。**实施前按 R2 流程向负责人确认本表（批准落盘 = 重签本文档）。**

## 对上游隐式行为的假设

沿用 diagnostics 批次已钉假设，本批次新增依赖各行：

| 行为 | 我方依赖方式 | 假设失效时的表现 |
|---|---|---|
| ~~`setup_logging` 仅 launcher 入口调用~~（2026-10-29 责任人裁决推翻：所有模式必须有日志）→ 本批次 R2 接线后：`app.py main()` 全模式调用 `aixcoding_startup()`（launcher 本体已于 2026-10-30 退役，ADR-0013——落盘唯一来源即本接线） | TUI / headless / ACP / serve 及全部子命令均落盘 | 接线被上游重构移除 → 全模式无落盘，行为可察（文件无新记录），架构测试锚定（`test_entry_wiring` 断言 `main()` 调用 `aixcoding_startup`，上游重构删调用即红） |
| 未经 `setup_logging` 时顶层 `aixcoding` logger 默认 `propagate=True` 且 level=NOTSET；app 启动的 `install_log_handler()`（`screen.py:190-193`）把白名单内 NOTSET logger 降为 DEBUG | 直接 `icode` 启动时 INFO/ERROR 记录得以产生（NOTSET 若不降级将继承 root 的 WARNING，INFO 被过滤）并冒泡 root → `_TuiLogHandler` → F6 可见（panel 开关此路径下不生效，diagnostics 批次已登记的同族边界；评审 F2 补全机制） | 面板无内容则降级为不可见，无错误 |
| `_TuiLogHandler` 挂 root、按 `record.name` 前缀对照 `MODULE_ORDER` 白名单 | 白名单项 `"aixcoding"` 已随 diagnostics 批次入库，本批次零接触 | 同上 |
| delegation 的生产注入方目前唯一 = AIxCoding 桌面端（ACP 启动子进程） | 消息 #1/#2/#9 直呼"桌面端"（当前事实陈述，非协议绑定；正交性与演进路径见埋点清单节） | 其他宿主注入时措辞失准——届时按既定边界改文案为机制词，无功能影响 |
| headless / 测试进程 root 为 NullHandler | 记录无输出 | 无（logging 语义保证，测试经 caplog 自挂） |

## 定制点登记预告

新增一个定制点（R2 接线）；点级登记（customization-registry 批次起）：

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C004 | src/chrys/app/cli/app.py | AIxCoding customizations: startup hooks | | `chrys.app.cli.app:main`（接线行落 `app.py` `main()` 起始 +2-3 行，R2 表；icode 唯一入口的全形态分发点，launcher 退役前曾锚定同一符号） | 低-中（上游入口重构时需跟，架构测试锚定） | 〔消费者退役〕接线消费者全部退役，或上游提供官方插件/hook 机制可承载 |

`session.py` 埋点部分无新增定制点（2026-10-30 修订后更简）：直写 `logging.getLogger("aixcoding.auth")`（标准库，名字约定仅耦合一个字符串），与 `diagnostics` 零依赖，不触发登记。customization-registry 批次起 freshness 义务已随 `CUSTOMIZATIONS.md` 退役（`gen_customizations.py` 改对账命令，CI 门禁为 check --strict）。

## 风险与最坏情况

**埋点不干扰主流程的四道防线**（2026-10-29 责任人质询后钉死）：

1. 参数表达式全部安全：12 条调用的实参只有枚举值、成功路径必有字段、`type(exc).__name__`——参数求值本身不可能抛；
2. logging 模块契约级兜底：handler 的一切故障（磁盘满/权限/轮转失败/格式化错误）走 `Handler.handleError` → stderr，永不向调用方抛异常（标准库设计契约，非代码自觉）；
3. #11/#12 的 except 圈定精确：只捕 `AuthError` 家族（`Cancelled` 先判），bare `raise` 保 traceback；非 AuthError 异常穿透，行为与改造前一致（`store.store()` 失败亦同）；
4. 无环依赖：`diagnostics` 不 import `auth`。

**import 通道（2026-10-30 修订后消灭）**：原方案顶层 `from ..diagnostics.logging_support import get_logger` 存在两个问题——①架构死锁（`..` 父级相对被 ruff TID252 禁、kernel↔kernel 绝对导入被 `test_layering:550` 禁，原实施只过了 ruff/ty 未跑 architecture，属验证缺口，CI 将红）；②理论传染路径（import 失败连累登录功能）。修订为 `session.py` 直写 `logging.getLogger("aixcoding.auth")`（标准库零依赖）后，两个问题同时消灭——这也是 2026-10-29"论证登记不加防护"裁决的最优终结形态。

**既有基建边界（非本批次引入）**：多会话下多个 iCode 子进程并发写同一 `aixcoding.log`，轮转竞态由 `handleError` 兜住（可能丢半行，不崩）；auth 埋点频率极低（启动 1-2 条），不放大此风险。

其余：

- 决策错了会怎样：约 26 行埋点删除即完全回滚，零残留；
- 记录量：正常启动 1 条（#4 或 #5），登录成功 +1（#8）、失败 +1（#11），登出 +1（#10），无循环路径。

## ADR 判定

按 DEVELOPMENT.md §6 checklist 逐项：

1. 被认真考虑但否决的备选？——备选（client.py / storage.py 落点）是常规方案对比，未达决策粒度。**否**。
2. 撤销代价高？——约 26 行日志语句，删除即回滚。**否**。
3. 约束未来工作模式？——弱触发：本批次确立的"边界对象埋点 + 字段白名单 + 异常只记类名"模式将成为 telemetry 等后续消费者的样板；判定为 diagnostics 批次既有原则（策略层独立、机制层复用）的执行细节，不另出 ADR。**责任人已裁决（2026-10-29）：不出 ADR；后续消费者（model catalog / telemetry 等）统一走同一套基建（`get_logger` 接入即得落盘 + F6 面板），埋点模式各自引用本 design 先例**。
4. 依赖上游非公开接口或行为？——R2 接线锚定上游入口 `main()`（公开 entrypoint 符号，launcher 已锚定同符号）；其余零上游接触。**否**。

结论：不出 ADR（第 3 项已裁决，2026-10-29）。

## 验证方式

1. 单测：`uv run pytest aixcoding/tests -n0`——新增 `aixcoding/tests/auth/test_session_logging.py`，复用既有 `MockServer` + `make_session` 模式与 delegation fake 设施，`caplog.at_level(logging.INFO, logger="aixcoding.auth")` 逐分支断言（12 条消息全文 + levelname + `record.exc_info is None` + 脱敏反断言）。**测试隔离 fixture 必备**（评审 F5）：仿 `tests/diagnostics/conftest.py` 的 `aix_logger_state`——保存/恢复顶层 `aixcoding` logger 的 handlers/propagate/level，测试内显式 `propagate=True`，防 diagnostics 测试 `setup_logging(panel=False)` 的跨测试顺序污染（caplog 挂 root，record 依赖 propagate 冒泡才可捕获）；
2. **接线与聚合测试**：新增 `aixcoding/tests/diagnostics/test_entry_wiring.py`——①`ensure_file_sink()` 幂等（两次调用同一 sink 路径）+ fail-safe（config 破坏时不抛、返回 None、stderr note）；②`aixcoding_startup()` 聚合契约：逐任务 fail-safe（子任务抛异常不阻断、不外抛，stderr 留痕 §9）+ 幂等（子任务各自幂等则聚合幂等）；③`app.main()` 调用锚定：monkeypatch `aixcoding_startup` 后以 `--version` argv 跑 `main()`，断言被调（上游重构移除接线即红，架构级回归锚）；④新增 `startup.py` 落位测试（app/aixcoding 层存在性与聚合入口契约）；
3. **架构回归（2026-10-30 补：原验证缺口）**：`uv run pytest tests/architecture -n0` 全绿——覆盖 `main()` 接线边（app→app 同层）、`startup.py` 内部边（app→kernel 向下）、**`session.py` 直写后 kernel 内无跨子包绝对导入**（原 `get_logger` 绝对导入在 `test_layering:550` kernel↔kernel 非相对规则下会红，本项为其回归锚定）；
4. 闭环（人工）：直接 `uv run icode` 启动 TUI → F6 "aixcoding" tab 启动即见 silent check 记录**且 `%APPDATA%/chrys/aixcoding-logs/aixcoding.log` 同步落盘**；步骤与输出摘录落 verification.md；
5. 防御：`uv run python aixcoding/tools/gen_customizations.py`——本批次含 app.py 新 marker，**产物变更须纳入提交**（freshness 义务，连跑两次幂等）。
