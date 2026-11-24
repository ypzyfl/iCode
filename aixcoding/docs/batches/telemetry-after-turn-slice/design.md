# 批次1 design：telemetry-after-turn-slice（after_turn 垂直切片）

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-20
- 确认意见：无特别意见

> 草稿说明：AI 起草，待责任人审阅 → R2 批准；未批准前不实施任何上游/产品代码改动。签认即代表 R2 授权（含 §2 七文件上游修改与 §5 D1 清单）。
> 输入：本批 `requirements.md`（2026-11-20 确认）；探索批次结论（`telemetry-exploration/research/`，重点 N3 节点 §12–§14、`model-source-filtering.md`、B7/B8 暂行契约）；mock 单端口决策（`mock/design.md` 2026-11-20 修订节，统一端口 15678）。
> 探索实验资产：`aixcoding/tests/telemetry/` 四个测试态实验（身份链/队列/ACP 身份/工具身份）为本批实现的直接前置参考。

## 通俗版说明（第一次读这篇文档，先看这里）

> 本节用大白话解释这份设计方案"整体怎么运转、改哪几个文件、新增哪些代码"，供非技术读者快速建立大图景。精确的改动行数、字段清单、内部编号（R2-1~7、V1-V3、D1、N3、F1/F2、B7/B8 等）仍以下文正式章节为准。

### 一句话概括

这份设计回答一个问题：**一轮对话结束后，怎么把这一轮的数据（用了哪个模型、调了什么工具、AI 写了哪些代码）自动收集、组装、发给后台。** 答案是一条流水线：轮末抓一份身份快照 → 交给分发器入队 → 后台工作线程按顺序读取、组装、过滤、发送。

### 整条流水线怎么转（对应第 1 节）

1. **轮末抓快照**：一轮结束后，收尾模块在保存数据之后、执行外部收尾动作之前，先抓一份"身份快照"（哪次会话、哪一轮、第几个 pass、是不是重试）；
2. **分发器入队**：分发器校验快照，把同一轮重复的通知合并掉（但新的 pass 绝不丢），放进对应会话的队列；
3. **工作线程干活**：每个会话有一个后台工作线程，按顺序做"读 → 组 → 过滤"：
   - 读：把会话文件、轨迹事件、变更账本里的数据拼起来；
   - 组：拼出三种记录（独立 LLM 报告、工具详情、ai-code）；
   - 过滤：判断模型是不是"平台下发的"，不是就整批跳过；
4. **发送**：三种记录按"LLM → 工具 → ai-code"顺序，HTTP 发到本地假服务器（端口 15678）。

### 要改哪几个文件（对应第 2 节，共 7 个）

**第一类：4 个"抓快照 / 发通知 / 收尾"的文件**（只改身份快照和通知触发点，不碰业务逻辑）：
- 一个文件增加"身份快照"的字段定义；
- 一个文件在轮开始时清旧快照、ID 确定后写入新快照；
- 一个文件在轮末保存后、外部收尾前，构造通知并调用分发器；
- 一个文件在会话结束时排空并关闭这个会话的上报。

**第二类：3 个配置文件**——把本地环境默认端口从 7777/7778 统一改成 15678（只动本地默认值，不动正式/测试环境）。

### 新增哪些代码（对应第 3 节，全在 fork 自己的目录，不动上游）

- 通知 + 分发器：把快照包成通知，校验、合并、入队；
- 会话管理：保证"每个会话一个工作线程"，会话结束能排空、关闭；
- 读取器：把散落数据拼成完整事实；
- 组装 + 三种报文 + 过滤 + 发送客户端；
- mock 改造：把原来多端口的假服务器合成一个 15678，并加上"数据存储"逻辑（保存 / 对账 / 去重 / 冲突）。

### 三个实验是干嘛的（对应第 4 节）

写正式代码前先做三个小实验，验证之前定下的假设站不站得住：
- V1：验证"读取"准确、数据被改写后不串线；
- V2：验证"同一轮多个 pass"的通知不丢、不重报；
- V3：验证"当前轮数据被压缩折叠"后还能不能正确读。
任何一个证伪就先停下、回头重估，不硬写。

### 实施顺序（对应第 8 节）

实验 → 上游 4 文件改动 + 通知/分发器/会话管理 → mock 单端口改造 → 读取/组装/过滤/发送 + mock 存储 → 配置端口 + 端到端跑通 → 边界验证 → 测试全绿 → 合回长期分支。

## 1. 总体架构

```text
engine 轮末（finalizer _save_and_drain_hooks）
  │ save/checkpoint 后构造不可变 TurnTelemetryNotice
  │ （session_dir/session_id/logical_turn_id/pass_id/turn_number/is_retry/saved）
  ▼
direct dispatcher（定制，进程级单例，lazy import）
  │ 校验快照 → 按 (session_id, logical_turn_id, pass_id) 合并同 pass 重复 → put_nowait
  ▼
per-session worker（进程级 owner 管理，session 内 FIFO，跨 session 并发）
  │ reader：按 expected logical+pass 联读 session.json / trajectory events / mutation ledger+blob
  │ analyzer：构造三类记录事实（原值 ID：requestId=A、funcId=T、reportId=T、spanId=turn ID）
  │ 过滤：模型来源判断（catalog synced_from_server 探针）→ 非下发模型整批跳过
  ▼
reporter×3（同 session 内 LLM→tool→ai-code 有序）
  ▼ HTTP → 单端口 mock :15678（1A 组合 + 1B telemetry 存储）
```

分层契约（N3 §5）：dispatcher 同步路径只做校验/合并/入队；分析与网络全在 worker；通知只保证已入队。`saved=False` 或快照空 → 记录并跳过。普通异常隔离、`CancelledError` 不吞。

## 上游改动清单（R2）

> 原第 2 节「上游 R2 接缝（7 文件，函数级）」；标题按 R2 门禁（check_r2_diff）标准命名。原 2.1（N3 四文件，依据探索 N3 §14.4 逐项落实，R2-1~4）与原 2.2（产品端 local 默认端口统一 15678，单端口决策连带，责任人 2026-11-20 裁决纳入本批 R2，R2-5~7）两小表于 2026-11-24 合并为一张（责任人裁决）：门禁只解析本节的第一张表，第二张表的表头会被误当作数据行。

| # | 文件 | 改动 | 量级 |
|---|---|---|---:|
| R2-1 | `src/chrys/orchestration/engine/run/turn_state.py` | `TurnRuntimeState` 增加 run-owned 不可变身份快照（`logical_turn_id/pass_id/turn_number/is_retry`）+ `pre_run` 前清空 + `reset_after_session_shutdown()` 同步清理；不含 telemetry 业务字段 | 15–25 行 |
| R2-2 | `src/chrys/orchestration/engine/run/runner.py` | `pre_run()` 开始清旧快照；`_record_trajectory_turn_started()` 在 ID 确定后、`await recorder.turn_started()` 前一次性写入快照 | 10–18 行 |
| R2-3 | `src/chrys/orchestration/engine/run/finalizer.py` | `_save_and_drain_hooks()` 的 save/checkpoint 后、外部 hooks 前：构造 `TurnTelemetryNotice`（含局部 `saved`；turn 终态 `status` 字段已于 2026-11-23 二次裁决移除、留待批次2，见 self-review.md）并 lazy import 调用定制 dispatcher；不改外部 hook 语义 | 18–30 行 |
| R2-4 | `src/chrys/orchestration/engine/session_lifecycle.py` | `_teardown()` 与 `_delete_session_reporting()` 集中调用定制 per-session 有界 flush+close（delete 在 trajectory close/detach/物理删除前；删除失败后 worker 可重建；close 幂等） | 12–26 行 |
| R2-5 | `src/chrys/kernel/aixcoding/auth/environments.py` | `_BASE_PATHS[LOCAL]` 两个 origin `localhost:7777` → `localhost:15678`（docstring 端口表同步） | — |
| R2-6 | `src/chrys/service/aixcoding/update/client.py` | `_TIER_BASES["local"]` `127.0.0.1:7778` → `127.0.0.1:15678`（注释同步；dev/prod 不动） | — |
| R2-7 | `src/chrys/service/aixcoding/models/catalog.py` | `_CATALOG_BASES["local"]` `127.0.0.1:7777` → `127.0.0.1:15678`（dev/prod 不动） | — |

不修改：`turn_hooks.py`、EventBus、ACP `server.py/session_manager.py`、TUI app、headless entry（N3 §14.4 已排除）。`app/acp/server.py` 是批次2（N7）接缝，不入本批。

R2-5~7 均为 local 默认值替换，原设计未单列量级。telemetry 产品端指向为**新增配置**（见 §3.4），不属改默认值。`app/cli/serve.py:41` 的 `_DEFAULT_PORT=7777` 是独立产品 serve 命令端口，与 mock 无关，**不在本批范围**。

## 3. 定制模块设计（新增代码，落位 ADR-0011 产品层）

### 3.1 通知与 dispatcher（`orchestration/aixcoding/telemetry/notice.py` 暂定）

- `TurnTelemetryNotice` 不可变 dataclass（§1 字段清单）；序列化仅内存传递，不持久化。
- `dispatch_telemetry_notice(notice)`：模块级单例入口（finalizer lazy import 的目标）；同步路径=校验→按 `(session_id, logical_turn_id, pass_id)` 合并同 pass 重复（首任务 pending/running/completed 期间同 pass 重复合并；**新 pass 不得被吞**，F2 裁决）→`put_nowait` 到对应 session 队列。普通异常捕获记录（detail 日志），`CancelledError` 传播。

### 3.2 owner 与 per-session worker（`service/aixcoding/telemetry/owner.py` 暂定）

- 进程级 `TelemetryOwner`：`dict[session_id → SessionWorker]`；SessionWorker=queue + 单 worker task，session 内 FIFO 保序（LLM→tool→ai-code 由任务内顺序保证），跨 session 并发。
- `flush_session(session_id, timeout)`：排空既有队列（**不做 trailing-save 补扫**）；超时记录并取消剩余任务；`close_session` 幂等；delete 失败后再入队自动重建 worker（N3 §14.3）。
- 无持久化高水位；文件 offset 仅进程内缓存（可丢失）。

### 3.3 expected-turn reader（`service/aixcoding/telemetry/reader.py` 暂定）

以探索 P0 系列实验的 reader 为蓝本（`tests/telemetry/test_request_identity.py` 等已验证的联读逻辑产品化）：

- 输入：`session_dir/session_id/expected logical_turn_id/pass_id`；输出：本轮三类记录事实集 + 恢复/跳过清单。
- 联读：session.json（function_call/result、`_chrys_operation_id`=T、`_chrys_request_attempt_id`=A、turn registry）、trajectory events（exchange facts、工具 operation 事件、pass 交叉校验）、mutation ledger+blob（ai-code blocks）。
- F1/F2 裁决口径：**区分当前 pass 新执行 / 关联所需前序来源 / retry 纯重放继承**——按原始执行身份上报，前序来源不重报，纯重放不形成新执行记录；不预设全局原子快照，以记录级事实一致与关联正确为目标。
- fail-closed：缺证据（缺 A/T/blob/终态）→ 跳过该记录并列入清单；`saved=False` → 整轮跳过；禁止 session-latest 回退。

### 3.4 analyzer + 三类 reporter + 过滤（`service/aixcoding/telemetry/` 暂定：`analyzer.py`、`reporters/llm.py|tool.py|ai_code.py`、`filtering.py`、`dto.py`、`client.py`）

- **DTO**（B7/B8 已定契约，ID 全部原值 32hex）：独立 LLM 最小 envelope（schemaVersion/sessionId/eventType=llm/eventSubType=success/requestId=A 原值/span 按真实关系）；tool-detail 七项必填（requestId=A1/funcId=T/funcName/funcType/sessionId/spanId/codeStatus）；ai-code 最小字段（reportId=T/requestId=A1/filepath/blocks/sourceType/inputMethod/codeStatus 等）。三时间字段、providerCallId、parentSpanId（普通独立 turn）一律不出现。
- **过滤**（出站统一前置，`model-source-filtering.md` 设计要点）：该批记录关联的 `model_profile_id` → catalog `synced_from_server` 探针（复用 `service/aixcoding/models/catalog.py` 现有原语，或 sync 后 server-owned 内存集合）→ 非下发/不可判定 → **整批跳过**（独立 LLM 按自身调用，tool/ai-code 按关联 A1）+ detail 日志。探针结果按 profile id 进程内缓存，catalog sync 后失效。三个实现细节裁决（design 内定，呈报 R2 时确认）：①同名 stem 探针先 `.yaml` 后 `.yml`；②无对应文件的 profile 按不可判定跳过；③缓存仅进程内。
- **client**：stdlib `urllib`（mock 与未来真实后台同构），顺序 POST；mock 通过≠真实后台通过。telemetry 产品端指向：新增 local tier 配置 `http://127.0.0.1:15678`（配置项命名随 D1 定，默认随 R2-5/6/7 同端口）。

### 3.5 mock 1A：单端口组合（`aixcoding/mock/__main__.py` 改造）

- 目标形态：`python -m aixcoding.mock` 起单 server `:15678`，挂载全部子服务路由：auth（设备码）+ catalog（目录+LLM chat `/v1`）+ update（`/csas/api/v2/...`）+ telemetry（§3.6）。
- 实现方式：推广 model_catalog 已有的"内嵌 auth 路由"先例——各子包 server.py 新增路由表导出（如 `routes() -> list[Route]` 或挂载函数），组合层统一组装单个 `ThreadingHTTPServer`；各子包 `create_server(port)` 独立形态**保留**（契约测试与调试用，auth-isolation-mock-ports 的 `port=0` 用例不变）。
- launcher 参数：`--list`（列子服务与路由前缀）、`--port`（默认 15678，fail-fast 语义不变）；`--only` 语义调整为"单端口下选择挂载哪些子服务路由"（默认全部）。旧多端口组合不再提供（不长期维护两套）。
- 契约测试影响：`tests/mock/` 既有三份契约测试直连各子包独立 factory（不变）；launcher round-trip 测试改单端口断言。

### 3.6 mock 1B：telemetry 存储（`aixcoding/mock/telemetry/` 新子包）

- 端点（与产品端 client 对应，全部挂 :15678）：

| 端点 | 方法 | 语义 |
|---|---|---|
| `/csas/telemetry/api/v1/llm-report/save` | POST | 独立 LLM 报告：requestId 单键原子幂等（内存 dict 锁）；语义重放 200 不新增、同键不同内容 409、缺字段/非法 32hex 400 |
| `/csas/telemetry/api/v1/tool-detail/save` | POST | 单次终态保存：`(requestId,funcId)` 组合幂等，200/409/400 同上 |
| `/csas/telemetry/api/v1/ai-code/save` | POST | `(requestId,reportId)` 组合幂等，同上 |
| `/csas/telemetry/_test/join?requestId=` | GET | 测试专用：按原值 requestId 返回关联记录集（原模型+LLM+tool+ai-code），验证 join 闭环 |

- **原模型记录捕获**：catalog 子包的 LLM chat `/v1` handler 增加旁路记录——每请求读取 `Chrys-Request-Attempt-Id` header 原值 + 请求模型名 + 响应模型名，存入 telemetry 状态（BR-1：每请求各存自身 attempt，不做成功判定）。实现为 telemetry 子包向 catalog server 提供的记录钩子（保持 catalog 子包不 import telemetry——由组合层/工厂参数注入，具体接线随 D1）。
- 内存态 `MockTelemetryState`：records/joins/幂等键，进程生命周期即存储；严格 allowlist（未知字段 400，不静默通过）；不执行模型推理。
- 契约测试 `tests/mock/test_telemetry_server.py`：最小 envelope 落存、重放/冲突/非法三态、组合幂等、join 查询、allowlist 拒绝、原模型捕获（带 attempt header 的 chat 请求 → join 可见）。

## 4. V1–V3 判别实验设计（实现前执行；证伪即停扩张回评）

新增 `aixcoding/tests/telemetry/`（工作块内新实验文件，不动既有四份）：

| 实验 | 步骤 | 通过判据 | 证伪处置 |
|---|---|---|---|
| **V1 读取一致性**（F1） | ①真实/半真实 session 两轮保存后，reader 以 expected 第一轮身份读取；②构造 rollback/覆盖保存（破坏性改写）后同读；③记录恢复/跳过清单 | ①仅返回第一轮事实；②不串接新旧（身份/终态/blob 一致或显式跳过）；③清单完整可审计 | 若串接且无法以记录级一致判定 → 呈报快照/锁方案与成本供责任人裁决（F1 裁决预留） |
| **V2 pass 契约**（F2） | 模拟同 logical turn 两 pass（retry 新 pass）通知序列：pass1 pending→completed、pass2 入队时 pass1 仍在跑等交错 | 同 pass 重复合并；新 pass 不被吞；跨 pass 关联按原始执行身份；pass1 工具不在 pass2 重报；1001 契约位（本批仅断言通知层保持 logical turn 单键） | 通知合并丢 pass → 回评三元组键或去重策略 |
| **V3 当前轮压缩**（F3） | 构造当前轮 compaction 后 reader 读当前轮 | 折叠不影响当前轮事实与身份；被折叠前序仅作来源不重报 | 当前轮不可读 → 呈报显式降级矩阵供裁决 |

V1/V2 通过是生产实现继续的前提（requirements §5.5）；V3 结论决定 reader 压缩处理集（完整矩阵留批次3）。

## 5. D1：本批定制文件清单（R2 呈报，逐项裁决）

**上游修改（R2，7 文件）**：§2 表 R2-1~4（原 2.1，N3 四文件）+ R2-5~7（原 2.2，local 默认端口统一）。
**产品层新增（ADR-0011 落位，`src/chrys/{tier}/aixcoding/telemetry/`）**：notice/dispatcher（orchestration tier）、owner/reader/analyzer/reporters/filtering/dto/client（service tier；最终 tier 划分随 D1 复核 marker 登记）。
**开发资产新增/修改**：`aixcoding/mock/telemetry/`（新子包）、`aixcoding/mock/__main__.py`（单端口改造）+ 各子包路由导出（auth/update/model_catalog server.py 小改）、`aixcoding/tests/mock/test_telemetry_server.py`、`aixcoding/tests/telemetry/` V1–V3 与切片测试、本批六件套文档。
**不含**：批次2 ACP 接缝、批次3 parity、真实后台、上游提案。

## 定制点登记预告

> 点级登记（匹配键＝(落点, marker 锚)；语义 id 形式）。定制新增包 `src/chrys/service/aixcoding/telemetry/` 在定制目录内、免 marker（file classification：custom 侧）。实施后跑 `gen_customizations.py --strict` 对账。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| telemetry-after-turn-slice:turn-identity | src/chrys/orchestration/engine/run/turn_state.py | AIxCoding telemetry: run-owned turn identity snapshot | 2 | `TurnRuntimeState` 字段 + `reset_after_session_shutdown` 清理（孪生） | 低（纯增量字段；上游重构 TurnRuntimeState 时随迁） | 〔telemetry 退役〕批次1-3 全部退役或上游提供官方身份快照 API |
| telemetry-after-turn-slice:identity-stamp | src/chrys/orchestration/engine/run/runner.py | AIxCoding telemetry: run-owned turn identity snapshot | 2 | `pre_run()` 清旧 + `_record_trajectory_turn_started()` recorder await 前写入（孪生） | 低-中（上游重构 pre_run/turn started 时序需跟） | 同上 |
| telemetry-after-turn-slice:after-turn-notice | src/chrys/orchestration/engine/run/finalizer.py | AIxCoding telemetry: after-turn notice | 1 | `_save_and_drain_hooks()` save/checkpoint 后、外部 hooks 前（lazy import，无构造器注入扩散） | 低-中（上游重构保存顺序需跟；异常已隔离） | 同上 |
| telemetry-after-turn-slice:session-flush | src/chrys/orchestration/engine/session_lifecycle.py | AIxCoding telemetry: bounded per-session flush + close | 2 | `_teardown()`（usage settle 后）与 `_delete_session_reporting()`（trajectory close/detach 前）（孪生） | 低（独立于 hooks；flush 有界 5s 不阻塞进程） | 同上 |

> 原 §2.2 三项（R2-5/6/7，现同在 §2 表）实施核正：三文件均位于 `src/chrys/{tier}/aixcoding/` 定制层（ADR-0011），属 custom 侧文件——**改动经 R2 批准生效，但免 marker、不入登记表**（gen_customizations 只对 upstream 侧 marker 对账；首轮误登记为 orphan 已修正）。

## 6. ADR 判定

- 单端口组合：子包结构/命名/契约测试强约束不变，仅编排层挂载方式变化——维持 mock design 2026-11-20 修订节判定，**不升 ADR**（设计决策记录足够）。
- run-owned 快照/通知/owner：N3 §14 已论证为最小集中接缝，不改变上游公共 API 语义——不升 ADR；上游 marker 按定制规范随 R2 登记预告。
- local 端口统一：纯配置默认值变更（dev/prod 不动）——不升 ADR。

## 7. 风险与回滚

| 风险 | 缓解 |
|---|---|
| V1/V2 证伪 | 实验前置（§4），证伪即停，按 F1/F2 裁决预留路径回评 |
| 四文件+三配置 R2 diff 超预期 | R2 呈报附实际 diff；超量级估计 50% 即回呈 D1 重议 |
| 单端口组合对既有契约测试的扰动 | 独立 factory 形态保留，测试直连不变；仅 launcher round-trip 改造 |
| update/auth 联调回归（端口迁移） | 契约测试 + LOCAL 档冒烟（mock 起后 auth/update/catalog 端到端） |
| 回滚 | 上游 7 文件 revert + 删除定制包与 mock telemetry 子包即完整回滚，无数据残留 |

## 8. 实施顺序（R2 批准后）

1. V1–V3 实验（新增实验文件）→ 结论落盘 verification；
2. 上游 R2-1~4（身份快照→通知→flush）+ 定制 notice/dispatcher/owner；最小单测；
3. mock 1A 单端口改造 + 既有契约测试回归；
4. reader/analyzer/过滤/reporter×3/client + mock 1B + 契约测试；
5. 产品端配置 R2-5~7 + 端到端垂直切片（真实 engine A1→write→A2 → mock 闭环）；
6. 边界矩阵（无 hooks/save=False/trajectory disabled/A1≠A2/flush）→ test-plan 全量 → self-review → PR 回长期分支（双 CI）。
