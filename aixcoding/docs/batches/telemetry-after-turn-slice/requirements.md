# 批次1 requirements：telemetry-after-turn-slice（after_turn 垂直切片）

> 状态：草稿（AI 起草，待责任人审阅修订后进入 design）。
> 上游：探索批次 `telemetry-exploration`（`feat/telemetry-exploration` 长期根分支，已签认交付）；本批次为其 plan 实施顺序第 2 项，首个实施垂直切片。
> 分支：`feat/telemetry-after-turn-slice`（基于长期根分支切出；完成后 PR 合回长期分支，双 CI 已就绪）。

## 通俗版说明（第一次读这篇文档，先看这里）

> 本节用大白话解释这个批次"要解决什么问题、做什么、不做什么、怎么算完成"，供非技术读者或新加入者快速理解。精确的技术契约和内部编号（F1-F6、B7/B8、V1-V3、R2、D1 等）仍以下文正式章节为准。

### 一句话概括

iCode 要把运行时的数据（谁用了哪个模型、AI 干了什么、调了哪些工具）上报给后台做治理分析。之前的"探索批次"只把规则定好了，还没写代码真正跑起来。这个批次就是写第一段真实能跑的代码，把整条上报链路从头到尾打通一次，证明方案行得通。

### 几个反复出现的词，先翻译一下

| 原文 | 大白话 |
|------|--------|
| telemetry（数据上报） | 把运行数据发给后台 |
| turn（轮） | 一轮对话：用户下指令、AI 完成，算"一轮" |
| after-turn | 一轮结束后那一刻触发的上报 |
| 垂直切片 | 不铺开做全量，只挑一条"从源头到终点"的最小链路先打通 |
| 身份快照 | 在某时刻把"这是谁、哪一轮、第几个 pass"抓一份存下来 |
| reader（读取器） | 把散落在多个文件里的数据读出来、拼到一起 |
| reporter（报文构造器） | 把数据组装成"要发给后台的报文" |
| mock | 本地模拟的假服务器，开发验证用，不连真实后台 |
| 幂等 | 同样的请求重复发，结果不变、不产生重复数据 |
| join（对账） | 后台把不同来源的报告按 ID 关联起来，拼成完整记录 |
| fail-closed | 拿不到证据时"宁可不上报，也不瞎报" |

### 这批要做什么（对应第 2 节）

1. 先做三个小实验（V1-V3），验证之前定的规则站得住；证伪了就停下，不白写代码；
2. 在 4 个既有文件里做最小改动，拿到"身份快照"；
3. 写一个"读取器"，把会话文件、轨迹事件、变更账本里的数据拼到一起；
4. 写三种"报文构造器"：独立 LLM 报告、工具详情、ai-code；
5. 模型来源过滤：只上报平台下发的模型，用户自配的跳过并留日志；
6. 把本地 mock 服务合并成单端口，并实现最小存储逻辑（保存/对账/去重/冲突）；
7. 补全六份批次文档。

### 这批不做什么（对应第 3 节）

桌面端相关、全量字段对齐、连真实后台、回馈上游等，全部留给后续批次（批 2、批 3）。

### 怎么算完成（对应第 6 节）

真实链路在 mock 上闭环、边界情况通过、重复/冲突/非法请求处理正确、模型过滤正确、测试全绿、文档签认闭环。

### 开工前提（对应第 5 节）

需求确认 → mock 方案修订 → design 获批 → 文件清单裁决 → 三个实验结论落盘，全部满足后才写正式代码。

## 1. 背景与目标

探索批次已收敛并签认：A-final 原值主键（所有 ID 保持 32hex 不转 UUID）、服务器不做成功判定（独立 LLM 报告 join 声明）、单次终态保存与组合幂等等契约已定，技术评审 F1-F6 已按责任人裁决落盘。本批次目标是**打通第一个真实垂直切片**：轮末从 run-owned 身份快照触发，经 expected-turn reader 联读 session/trajectory/mutation，由三类 reporter 构造报文，发送到单端口 mock 并验证保存/join/幂等/冲突闭环——用最小实现证明主链可运行，为批次2（ACP 桌面）与批次3（parity 加固）提供契约落地基础。

## 2. 范围（in scope）

1. **V1-V3 判别实验（前置，先于生产实现）**：
   - V1（F1 读取一致性）：证明追加式读取正确、破坏性改写（rollback/compaction）后不串接，并列出恢复/跳过记录清单供责任人裁决降级与快照/锁成本；
   - V2（F2 pass 契约）：覆盖通知与 reader 的 pending/running/completed、新 pass 不被合并丢弃、防重、跨 pass 关联及旧工具不重报；1001 保持每 logical turn 一条（其实现留批次2，本批仅契约约定）；
   - V3（F3 当前轮压缩）：最小真实当前轮压缩实验（前置），完整矩阵留批次3。
2. **run-owned 身份四文件 R2 接缝**：`run/turn_state.py`、`run/runner.py`、`run/finalizer.py`、`engine/session_lifecycle.py`——logical/pass 身份快照、direct finalizer dispatcher、per-session owner/flush（N3 已定方案，具体改动归 design）。
3. **expected-turn reader**：按 expected logical turn 联读 session.json/trajectory events/mutation ledger/blob，复用探索批次 P0 系列结论；缺证据 fail-closed 跳过并记录（不误报）。
4. **三类 reporter（出站边界）**：独立 LLM（B7 最小 envelope）、tool-detail（B8 七项必填 final DTO）、ai-code（B8 最小字段）——报文 ID 全部原值 32hex。
5. **模型来源过滤**：各 reporter 出站统一前置判断（复用 catalog `synced_from_server` 探针），仅上报 catalog 下发模型的调用；自定义/不可判定 fail-closed 跳过 + detail 日志（需求分析见探索批次 `model-source-filtering.md`；同名 stem、无文件 profile、探针缓存三细节随 design 裁决）。
6. **mock 1A 单端口骨架**：修订既有 mock design 的多端口决定与 DIRECTORY 约束（开工前签认），组合为单端口服务。
7. **mock 1B telemetry 存储**：本切片所需的最小保存/join/幂等/冲突语义（严格 allowlist、语义重放 200、同键不同内容 409、非法 400）。
8. 批次文档六件套（requirements/design/test-plan/verification/self-review/plan）按流程逐步完备。

## 3. 非目标（out of scope）

- ACP 输入捕获、selected Agent 1001、desktop 上下文、真实桌面 schema（批次2 `telemetry-acp-desktop`）；
- M1-T 全字段 parity 矩阵、slash/local child/hosted 保留场景、BR-9/BR-10 完整矩阵、长会话/背压/全局资源关闭（批次3 `telemetry-parity-hardening`）；
- 真实后台联调与数据治理（独立内网验收门禁，mock 通过不宣称现网通过）；
- 上游化：本批次全部改动为 fork 定制，不提交上游（上游提案独立时间线）；
- 崩溃/强杀补报、流式模型调用通知（探索批次已明确非目标）。

## 4. 约束与既定契约（引用，不重新裁决）

- **ID 原值**：全部 ID（requestId/funcId/reportId/spanId/parentSpanId）保持 32hex 原值，无转换层；`request_tracking.py`/`ids.py` 不改（2026-11-18 责任人裁决）。
- **BR-1 语义**：服务器（mock 同样实现）每请求存自身 attempt 原值，不做成功判定；成功语义由独立 LLM 报告 join 命中声明。
- **BR-8 已撤销**：tool-detail 报文不含 providerCallId；模型侧对账由客户端按 funcId=T 本地反查。
- **三个执行时间字段**：不采集、不上报（B5/P2 最终关闭）。
- **上游接触面**：仅第 2 节所列四文件接缝（design 呈报具体 diff 后 R2 授权）；hook、全局 registry、ChatMiddleware 注入等已否决路线不复活。
- **长期分支变更规则**（2026-11-20 责任人确认）：实质变更（代码/批次文档/测试）走工作块分支 + PR（双 CI）；基础设施类（workflow 调整、主干同步 merge）可直推，commit message 注明性质与核验方式。
- **CI 前提已就绪**：两 workflow PR 触发已含长期根分支（`a9e79024`）。

## 5. 开工前提（全部满足后方可写生产代码）

1. 本 requirements 经责任人确认；
2. mock design 多端口决定修订 + DIRECTORY 约束调整完成并签认；
3. design.md 完成（含四文件 R2 具体 diff、reader/reporter/过滤/mock 模块划分、V1-V3 实验设计）并经 R2 批准；
4. D1（本批定制文件清单）呈报责任人裁决；
5. V1-V3 判别实验结论落盘（V1/V2 任一证伪即停止扩张回评，V3 按裁决前置）。

## 6. 验收标准（批次退出条件）

- 真实 engine A1→write_file→A2 全链在单端口 mock 闭环：五类记录（本批为原模型+独立 LLM+tool+ai-code 四类；ACP 归批次2）按原值 ID 正确关联，join 查询可用；
- 边界矩阵通过：无 hooks、save=False、trajectory disabled（`NO_SESSION_DIR` 或 `LEASE_HELD` 途径，批次1 test-plan 裁决选用）、A1≠A2、正常 flush；
- 幂等/冲突：语义重放 200 不新增、同键不同内容 409、非法 400；
- 模型来源过滤：下发模型上报、自定义/不可判定跳过且有 detail 日志；
- mock 测试与定制 telemetry 实验全绿；批次双 CI（PR 回长期分支）通过；
- self-review 签认 + verification 证据闭环。

## 7. 开放问题（留 design 裁决）

1. V1 降级链是否实现（缺工具终态时按 function_call A-final 降级上报 vs 保持 fail-closed 跳过——F1 裁决要求列出恢复/跳过记录交责任人决定）；
2. 通知合并键三元组 `(session_id, logical_turn_id, pass_id)` 的最终形态（F2 候选，design 裁决）；
3. 模型来源过滤三细节（同名 stem `.yml`/`.yaml`、无文件 profile、探针缓存策略）；
4. mock 1A 与既有 mock 服务骨架的复用边界（修订 mock design 时一并裁决）；
5. reader 对 compaction 折叠历史的最小处理集（完整矩阵留批次3，本批仅 V3 实验结论所需）。

## 8. 里程碑与风险

- 里程碑：requirements 确认 → mock design 修订签认 → design/R2 → D1 → V1-V3 实验 → 实现 → 边界矩阵 → mock 闭环 → PR 回长期分支。
- 主要风险：V1/V2 判别实验证伪读取/pass 契约假设（触发回评）；四文件 R2 diff 超预期（触发 D1 重议）；后台 BR-1/5/6 书面确认未返回（不阻塞 mock 开发，但影响后续批次范围）。
