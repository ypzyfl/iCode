# 任务清单：Telemetry 方案探索（telemetry-exploration）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 当前环节与下一步（新对话先看本节）

### 当前所在环节：批次1 已实施并合回长期根分支；0.37.0 升级影响评估已落盘

截至 2026-11-24，探索批次与批次1 均已落地：

1. 探索六件套、research、experiments 与四个测试态实验（2026-11-19，探索 commit `7f3fe332`）；
2. 长期分支 CI 触发调整（commit `a9e79024`）；
3. 批次1 `telemetry-after-turn-slice` 已实施并经 **PR #144 合回长期根分支**（origin `136b692b`）：after_turn→reader→analyzer→reporter→单端口 mock 垂直切片、V1–V3、四文件上游接缝（turn_state/runner/finalizer/session_lifecycle）与 local 端口统一均完成，细节见 `telemetry-after-turn-slice/plan.md` 与 `verification.md`；
4. 上游 v0.37.0（`08175eaa`）working-directory 支持影响评估已落盘（`research/upstream-v0.37.0-impact.md`）：结论为不构成方向性变化，跟进项为升级后复验。

新对话必须以实际 `git status`、签认头部与文末实施策略为准。

### 唯一下一步：0.37.0 升级复验，随后批次2 开工

> 批次1 已验收并合回（PR #144）。当前不推进批次2 的开发；先按 `research/upstream-v0.37.0-impact.md` §5 完成 0.37.0 升级后的复验，再确认批次2 在 0.37.0 基线上开工的接缝。

新对话按以下顺序推进：

1. 完成 0.37.0 升级（走 UPGRADE-RUNBOOK 与独立升级批次），随后复跑批次1 全部 telemetry 测试与 V1–V3 判别结论；
2. 批次2 `telemetry-acp-desktop` 在 0.37.0 基线上编写 requirements/design/R2（上游已改 `app/acp/server.py`、`session_manager.py`、`history.py`，接缝行号需重定位）；
3. 批次3 `telemetry-parity-hardening`：M1-T、全字段 parity、保留/删除/差异清单。

当前裁决只处置探索结论与升级影响评估，不授权修改产品代码、执行 Git 写操作。

### 探索交付后的实施顺序

| 顺序 | 下一环节 | 开始前提 |
|---|---|---|
| 1 | （已完成）调整两个 workflow 把 `feat/telemetry-exploration` 加入 PR 触发（改动本身可直推长期分支），实证工作块 PR 双 CI | 长期分支已建立（已完成）；责任人逐条授权 Git/文件改动 |
| 2 | （已完成，PR #144）批次1 `telemetry-after-turn-slice`：基于长期分支建工作块分支，编写 requirements/design/R2，同时修订 mock design/DIRECTORY 并呈报本批 D1；签认后开发 after_turn→reader→reporter→单端口 mock 垂直切片，做好后 PR 合回长期分支 | CI 触发可用；批次1及 mock design/R2 已签认，本批 D1 已裁决 |
| 3 | 批次2 `telemetry-acp-desktop`：ACP 输入、1001/desktop、最终响应与真实桌面闭环 | 批次1已验收并回合长期分支；批次2 design/R2 已签认 |
| 4 | 批次3 `telemetry-parity-hardening`：M1-T、全字段 parity、保留场景和长会话/异常治理 | 批次2已验收；批次3 design/R2 已签认 |
| 5 | 长期分支整体回归、文档签认、真实后台/数据治理内网门禁，最终整体 PR 并入主干；若 session 分析路线最终不可行则整体废弃、不并入 | 三个批次全部完成，无未处置重大问题；若主干直接发布，真实后台冒烟必须通过 |

### 新对话读取顺序

1. 本文件的“当前环节与下一步”及“实施批次与分支策略”；
2. `research/review-handoff.md` 了解当前有效技术结论；
3. `verification.md` 和 `self-review.md` 了解实际验证、评审和签认缺口；
4. 用只读 `git status`/分支信息核实真实工作区，不仅凭历史文字推断。

## 待办

- [x] 责任人裁决采用完整探索管线（2026-11-14）
- [x] 完成 request-identity 首轮源码、上游测试和 Git 历史只读调查
- [x] 建立六件文档、能力矩阵、request-identity 研究及实验记录
- [x] request-identity E1：`test_request_tracking.py` 定向测试 10 passed（2026-11-14）
- [x] 责任人审阅并签认探索 design（2026-11-14）
- [x] 责任人明确七条探索约束：旧版提需不猜测、零上游优先/必要改动少而集中、逐方案先查大阻塞、不可行即停、缺陷修复与差异由人确认、上游工作分类（2026-11-16）
- [x] 整理 `research/legacy-0.28-telemetry.md`，固化旧版实现、ID、报文、ACP、mock 和缺陷基线
- [x] 整理 `research/new-version-solution-map.md`，分类新版方向、fork 接缝、上游建议和降级边界
- [x] 建立 `research/solution-space.md` 决策空间图，展开 N1 LLM 上报通道和 N2 requestId 节点
- [x] 责任人确认 N2-A：服务器主 requestId 使用 exchange operation ID（2026-11-14）
- [x] 责任人确认 N8：按 0.28.0 类似方式有序 best-effort 上报，允许孤儿数据，不以 LLM ACK 为依赖门槛（2026-11-14）
- [x] N1-C 前提澄清：独立报告不能替代原调用接口记录，两者必须组合（2026-11-14）
- [x] 责任人确定优先 N1-C1 exchange header 直接关联，C2 attempt 映射保留备选（2026-11-14）
- [x] 当前 A-final 路线不再依赖新增 `Chrys-Exchange-Id` 或 C2 映射；仅当开发期回退 exchange 时才重评 C1/C2 及相应上游/fork 接缝（2026-11-16）
- [x] request-identity 的 A-final 客户端身份矩阵已覆盖普通/流式成功、SDK retry、redirect 锚点和 Responses retrieve；原记录↔独立报告的实际存储关联留 M1-T/后台联调，不再把完整服务器闭环写成尚未开始的身份调查。E3 middleware 仅在回退 exchange 时恢复
- [x] 整体风险优先级重排：A-final 五类记录闭环→真实 session 重建→长会话性能/flush→桌面 ACP；真实后台与数据治理列为上线门禁但不阻塞外网开发，mock 路由/DTO 增强后置（2026-11-17）
- [x] A-final 五类记录只读调查：确认当前只有客户端身份来源和局部关联证据，五类外部生产/保存/join 均未实现；明确 A1 产生工具、A2 最终回答，tool/ai-code 应取 A1而 ACP 通常取 A2；桌面只消费 final-model-identity 且需回显 attribution span（2026-11-17）
- [x] M0 五类记录目标契约实验：真实 A1→write_file→A2、session/trajectory/mutation/blob 重读和五类测试态 DTO 关系通过；共同 golden/非法 raw 与既有实验合计 16 passed，未实现生产 reporter/存储或真实 ACP server（2026-11-17）
- [x] M1-I 身份矩阵：同一 A1 两工具/唯一 write ai-code、失败 turn 不借旧 A、SDK retry 只取成功 A、Responses retrieve A、并发 scope 与 redirect 锚点通过；定制+上游 request tracking 合计 31 passed（2026-11-17）
- [x] P0-2 session 文件重建：仅凭目录/ID 的正常两轮精确重建、blob/工具终态降级、fork 继承零重报和 save=False expected-turn 守卫通过；compaction 明确不支持完整历史补报，定制+上游组合 48 passed（2026-11-17）
- [x] P0-3 性能/生命周期：30轮基准显示全量与expected-turn均约7→38ms线性增长、累计约0.64–0.71秒，过滤不等于增量；队列FIFO/跨session并发/有界flush原型通过，组合52 passed。正常只处理显式当前轮、进程内合并+后端幂等，不为崩溃补报引入持久化高水位（2026-11-17）
- [x] after_turn最高优先级接缝调查完成：runner在trajectory激活前已生成并注册logical/pass身份；推荐run-owned快照+direct finalizer dispatcher+集中per-session lifecycle drain，最小R2候选为`turn_state.py`、`runner.py`、`finalizer.py`、`session_lifecycle.py`四文件；禁止latest TurnRecord回退，主路线无需推翻（2026-11-17，详见N3节点第14节）
- [x] 另一 AI 已完成一轮独立评审：认可 N1-C/N3/N4/N7 主路线和最小接缝，无方向性反例；新增 R1 后台依赖、R2 公共字段、R3 ACP 输入及 funcId 对账等重点（2026-11-17）
- [x] 责任人裁决评审范围问题：Q2 保持桌面 0.28 能力并纳入 ACP 输入捕获/1001；Q4 workflow 退出 telemetry；Q5 后台前提失败时重评 N1-A 完整成本；三个工具时间字段删除再次确认关闭（2026-11-17）
- [x] 评审反馈与复审收敛：另一 AI 接受五项限定并核实文档落地；补记 N1-A middleware 时序/registry 成本、0.28 全字段 parity 的 M1-T/联调关闭门禁、1001 输入→after_turn→首个成功 A-final 的去重链（2026-11-17）
- [x] 责任人确认实施组织：探索批次独立；生产实现采用 `feat/telemetry-session-analysis` 集成分支，三个开发批次分别 PR 回集成，全面验证后再合并主干；mock 归属批次1（2026-11-17，详见文末策略）
- [x] 责任人确认 `aixcoding/tests/telemetry/` 四个测试态实验文件随探索批次保留和提交，作为可复现证据；不进 wheel、不移入上游 tests，正式实现有等价覆盖后再逐项裁决退役（2026-11-17）
- [x] 完成探索最终 self-review/签认（2026-11-17 周彬签认；2026-11-19 裁决不建探索独立 PR，commit `7f3fe332` 落长期根分支 `feat/telemetry-exploration`）；随后批次1先落实施 design/R2 与长期分支 CI 触发，再开发真实垂直切片。M1-T 必须关闭全字段 parity 和 BR-9/BR-10
- [x] 展开 N3 公共 after_turn 生命周期：核清正常 ACP 时序、save=False/强制取消边界、EventBus 复用和同步/后台分层；现有 EventBus+finalizer 定向测试 23 passed（2026-11-14）
- [x] N3 大方向可行性已核清；N3-A/N3-B、同步策略、失败与 flush 细节不影响能否工作，留到实施或 N7 消费契约阶段（2026-11-14）
- [x] N3/N8 接缝与 flush 专项：AI 推荐 direct finalizer + 进程级 reporter 按 session 隔离；flush 只排空已生成报文，不做 trailing-save 最终补扫。EventBus 需额外订阅 owner，active delete 失败需可续用；九组现有测试 241 passed。该项早期“trajectory disabled 身份降级”口径已由第32项 run-owned 四文件完整身份方案取代（2026-11-17）
- [x] 独立 LLM 契约调查：旧搭车无 model/usage/timing/error，旧 mock 无独立 LLM endpoint；AI 提出最小关联 envelope、save 路径和 requestId 单键幂等/409；真实 exchange/usage/attempt 测试 45 passed（2026-11-17）
- [x] B7 暂行采用 AI 方案：责任人表示知识不足、暂时无法决断，委托按 AI 判断制定并记录；开发期采用最小关联 envelope/golden，业务扩展字段不列为必需，后台现网未确认、实施遇问题再集中回评（2026-11-17）
- [ ] B7 后续仅在实际后台契约返回或 mock/客户端实施发现问题时重开；不得把暂行方案写成现网已支持或正式 R2 批准
- [x] final DTO/ai-code 幂等调查：首版建议 reportId=UUID(T)、`(requestId,reportId)` 幂等，同 T 多 mutation 跳过且不新增上游 mutationId；普通工具最小 final DTO/严格 mock 校验已形成，相关测试 55 passed、18 skipped（2026-11-17）
- [x] B8 暂行采用 AI 方案：责任人表示与 B7 一样暂时没有能力评审，明确委托 AI；开发期采用受限 reportId=UUID(T)、两类最小 final DTO、严格 mock 和 ai-code golden，后台现网未确认，cancelled/interrupted 继续单列（2026-11-17）
- [ ] B8 仅在正式后台契约返回或实施发现身份粒度/字段兼容性问题时重开；不得把暂行方案写成现网支持或正式 R2 批准
- [x] N4 大方向条件可行：session/trajectory/mutation 默认装配且互补，exchange→tool→mutation 关联链与 write/edit 输入齐全；相关现有测试 179 passed（2026-11-14）
- [x] N5 大方向条件可行：普通工具/load_skill 可关联 exchange 及生产响应 attempt，slash 仅关联 pass；现有 request/trajectory 测试 43 passed、2 skipped（2026-11-14）
- [x] 工具身份复核：provider call_id、tool operation、call item 和 UI call ID 角色已分清；以 call_item_id→C/M→A-final 为主链，重复 call_id 可共享 T，funcId 外部契约待确认；补充现有行为测试 6 passed（2026-11-16）
- [x] 按旧最终源码纠正 tool-detail 基线：无 reportId/eventTime/funcResponse，funcType=技能0/MCP1/内置3（2026-11-14）
- [x] 责任人确认模型请求 body/header 均可由服务器持久化，关闭 exchange header 无法落库疑虑（2026-11-14）
- [x] 责任人明确 requestId 不强制 UUID 但优先保持 UUID 文本；内部 exchange 可无损格式化，所有外部上报面一致，格式化留实施（2026-11-14）
- [x] funcId 本地契约复核：旧 CLI 为 provider/event ID 二选一并复用，update 不带 requestId；桌面侧也以自身 toolCallId 更新，AI 推荐每次执行使用新稳定 funcId，避免依赖服务器消歧（2026-11-16）
- [x] B1 已确认：新版原调用接口可从 body telemetry 改为当前 attempt header，服务器不另造 ID；retry/redirect/Responses 无需后台识别或聚合，最终成功记录保存 A-final，UUID 优先客户端单点化（2026-11-16）
- [x] B2 已确认：save 插入新记录，PENDING/final 仅按 func_id 更新，无 funcId=provider call_id 的其他消费；UUID(T) 语义路线成立，funcId 需全局唯一，save 不可依赖查重（2026-11-16）
- [x] B3 已确认：后台接受 36 字符 UUID，无唯一索引，依赖客户端全局唯一；重复 save 插入重复行，update 全部重复行。UUID(T) 契约成立，但客户端必须同一 T 至多 save 一次（2026-11-16）
- [x] B6 当前行为已确认：final-only 失败、重复 final 改字段、PENDING 可回退终态；AI 推荐单工具单次 final snapshot save，后台建议组合 requestId+funcId 防重（2026-11-16）
- [x] 后台目标态可协调：单次 final snapshot save、`(requestId,funcId)` 原子幂等和重复终态语义均可修改支持；明确需求与验收见 `research/backend-change-requests.md`（2026-11-16）
- [x] 相同组合不同内容已裁决：明确冲突（例如 409）、不隐式覆盖并记录原因，BR-4 已落盘（2026-11-16）
- [x] B4 概念语义已确认：turn 是一轮对话，spanId 为当前 turn ID且本轮模型/工具共用；parentSpanId 仅指真实直接父 turn，普通独立 turn 不传，不从时间上一轮或 E/A/T 派生（2026-11-16）
- [x] B5/P2 已关闭：责任人明确 `executionStartedAt`、`executionFinishedAt`、`executionDurationMs` 全部去掉，适用于新版所有工具记录；不发送 null/0，不补采本地或 provider 时间（2026-11-17）
- [ ] parentSpanId 语义差异已登记（父 turn 语义 vs 0.28 父模型调用 llmSpanId，记入 parity 差异项）；当前对话模型为平面 turn、无真实嵌套 turn 场景，父 turn ID 持久化仅在将来出现该场景时再验证（2026-11-19 责任人澄清，两版 turn 结构无差异）
- [ ] 批次1用真实 A1→write_file→A2 的垂直切片和最小 mock 闭环验证目标契约实际存取，不先扩大异常矩阵；真实后台留后续内网验收，不作为外网开发前置
- [x] N10 mock 现状与单端口调查：当前 auth+catalog 共享 7777、update 使用 7778；现有契约测试 87 passed、2 skipped；旧 telemetry 的 SQLite/debug/故障骨架可迁移，身份 join、独立 LLM、final 幂等/冲突、UUID golden 和时间字段缺席需新增或改造（2026-11-17）
- [x] 单端口目标：责任人明确不维护单/多端口两套组合模式；1A 单端口骨架、1B telemetry 是 AI 提出的分步建议。责任人已确认 mock 随批次1垂直切片实施，不在探索批次提前建设，也不另设大型前置 mock 批次（2026-11-17）
- [x] 总体实施路线已回到 `telemetry-exploration` 收敛：direct finalizer/EventBus 取舍、四文件 R2 接缝、独立 LLM 最小契约和阶段验收均已汇总到评审交接；是否新建实施批次或 ADR 仍必须在另一 AI 评审后由责任人裁决，越权草案已按责任人确认删除
- [x] N6 大方向条件可行：成功 write/edit 可重建旧 blocks/requestId/span/1/5，outcome 闸门和参数/blob 降级明确；当前相关测试 113 passed，旧 ai-code 22 passed、1 skipped（2026-11-14）
- [x] N9 大方向条件可行：固定运行时/live session/ACP 分工明确，desktop envelope 必须入口捕获，Git 轮末与事件时语义分开；相关测试 205 passed（2026-11-14）
- [x] 广义调用对照：本地 tool/shell/MCP/load_skill 与 local child 主链可行，provider-hosted 字段级可行，外部 ACP 内部只能投影降级或补采；当前 216 passed、8 skipped + 99 passed，旧 tool-detail 37 passed、1 个路径断言失败（2026-11-14）
- [x] 特殊调用逐字段调查：外部 ACP 旧版也是本地投影，hosted 业务字段可由文件恢复；B5/P2 已确认三个执行时间字段全部去掉且不补采，外部 ACP 内部明细已退出当前关注范围（2026-11-17）
- [x] P1 已改判并确认：必须保持 0.28.0 形态，在最终 `PromptResponse._meta` 主动携带 requestId；客户端另查 `session/turns` 不满足要求（2026-11-17）
- [x] 上游 ACP 历史已查证：b4f354d 在 v0.30.1 提供稳定 session/turn 身份和 request-attempt 查询，9cd8031d 在 v0.31.0 提供真实流式文本/推理；当前 0.35.2 定向测试 29 passed（2026-11-17）
- [x] N7 身份准备路线已比较：新增响应时 live-history 选择为当前 AI 推荐，仅 `app/acp/server.py` + 定制 helper；after_turn/live registry 和全量 turn trace 均非最小路线，现有锚点新增 57 passed（2026-11-17）
- [x] N7 路线暂行决策：责任人表示“人暂时没有能力判断，先按照AI建议的方案执行，实际执行过程中如果有问题，再分析讨论”（2026-11-17）。响应时 live-history 精确选择继续有效；中间的 UUID 化暂行安排均已由 2026-11-18 ID 原值裁决取代。
- [x] N7 方向实验落盘：新增 `aixcoding/tests/telemetry/test_acp_response_identity.py`，首轮 3 个实验假设错误修正后 7 passed，定制目录合计 9 passed；UUID 影响面现有回归 96 passed，实测发现 trajectory 默认校验拒绝 canonical UUID（2026-11-17）
- [x] UUID 表示问题已重议定案（2026-11-18 ID 原值裁决）：所有 ID 保持原值 32hex、不转换，`request_tracking.py` 与 `ids.py` 均不改；此前 2026-11-17 的 UUID 归一化安排已被取代，演进过程见 verification。
- [ ] 按原值口径（2026-11-18 裁决）编写实施 design/R2：N7 仅 `app/acp/server.py` 上游接缝+定制输入上下文/selector（requestId 直接用 raw 原值，无 UUID helper）；after_turn 各定制 reporter 出站即为原值，内部 join 同文本。后台 BR-5 32hex 格式接受/新旧混存、原记录/报告 join、BR-9/BR-10、公共字段 parity、非法 ID、1001 和桌面 schema（放宽接受 32hex）验收必须纳入
- [ ] 完成真实 ACP server 接线后验证输入捕获/1001、prompt_lock、并发 session、save=False、真实压缩、长 history 和桌面 Zod；现有 7 项仅为输出选择器实验。Q2 已确认输入捕获纳入，不再暂缓
- [x] capability-matrix 已按专题同步 A-final/独立 LLM、tool-detail、技能、ai-code、ACP、公共字段及当前证据边界；不再保留初始静态评估口径（2026-11-17）
- [x] 建立并复核旧版 defect-register：L-D01–L-D11 分类，新增外部 ACP interrupted 误报成功；区分客户端缺陷、协议限制、设计取舍和新版边界（2026-11-16）
- [ ] D1 按实施范围分批签认：批次1 design 签认时呈报该批涉及的 L-D01–L-D11 项，其余随对应批次；只阻塞涉及该项的批次，不要求全部 D1 在批次1前一次性关闭
- [x] 责任人暂定 N2：以最终成功 attempt 作为主 requestId；客户端上报什么服务器记录什么，外部尽量 UUID；缺 A-final 跳过并记录原因，不用 exchange 混填（2026-11-16）
- [ ] 实施 design 保持身份可逆：内部同时保留 E/A-final、内部 join 不绑死外部键、requestId 选择单点化、golden fixture 双键验证；开发期发现严重问题即停并回评 exchange，不承担上线后历史迁移场景
- [x] N2 最小身份样本已由 M0/M1-I 完成：普通成功、两工具、失败不借旧 A、SDK retry、Responses retrieve、并发和 redirect 锚点已排除主要身份/协议方向阻塞；实际后台存储 join 留 M1-T，不再重复开展一轮相同最小调查
- [x] 工具方向最小样本：普通工具 T→C→M→A-final 主链和真实 rollback 孤儿事件拒绝均通过；新增定制自包含实验 `aixcoding/tests/telemetry/test_tool_identity_persistence.py`，最终 2 passed，完整矩阵与报文 parity 留实施（2026-11-16）
- [ ] 逐项评审 upstream-proposals 的通用性，形成可与 iCode 团队沟通的版本；该工作走独立时间线，不阻塞三个 telemetry 实施批次
- [x] 主要开放问题已经独立评审/复审收敛；责任人已确认三批次、mock 归属、独立集成分支和 CI 前置条件，详见文末实施策略（2026-11-17）
- [x] 探索交付前完成双 AI 自审、verification 证据闭环和 self-review 签认（2026-11-17：选项 A 裁定+周彬签认；closure 门禁通过，见 verification.md 末节）
- [ ] 批次1各 reporter 出站边界实现模型来源过滤：仅上报 catalog 下发模型（`synced_from_server` 探针）的调用，自定义/不可判定 fail-closed 跳过并留 detail 日志；同名 stem、无文件 profile、探针缓存三个实现细节随批次1 design 裁决（2026-11-18 需求登记，分析见 research/model-source-filtering.md）
- [x] 批次1 `telemetry-after-turn-slice` 实施完成并经 PR #144 合回长期根分支（2026-11-24 核实 origin `136b692b`；细节见 `telemetry-after-turn-slice/` 目录）
- [ ] 0.37.0 升级影响评估已落盘（`research/upstream-v0.37.0-impact.md`，2026-11-24）；跟进：升级后复跑批次1 V1–V3 与 telemetry 测试、批次2 在 0.37.0 基线上开工、批次3 公共字段取 live workspace 不取进程 cwd

## 实施批次与分支策略（2026-11-17 确认，2026-11-19 责任人裁决修订为长期根分支模式）

### 长期根分支（取代原"探索批次独立 PR 交付"）

- `feat/telemetry-exploration` 为**长期根分支**：探索 commit（`7f3fe332`，六件套+research+experiments+四个测试态实验）已落在其上；**不创建探索独立 PR、方案未确定前不合并 `main_aixcoding_cli`**。
- 交付物（文档、研究、实验记录与 `aixcoding/tests/telemetry/`）随分支存续，作为后续实施的证据基线；不含生产 telemetry 行为。
- 后续每块工作基于长期分支再建分支（如 `feat/telemetry-session-analysis`），**确定做好后 PR 合回长期分支**；全部工作确定完成后**再整体 PR 并入 `main_aixcoding_cli`**。
- **失败出口**：若最终结论是"通过分析 session 文件实现 telemetry 不可行"，长期分支整体废弃、不并入主干。

### 三个开发批次

| 顺序 | 批次 | 核心范围 | 上游 R2 候选 | 主要退出条件 |
|---|---|---|---|---|
| 1 | `telemetry-after-turn-slice` | run-owned 身份、direct dispatcher、per-session owner/flush、expected logical turn+pass reader、独立 LLM/tool/ai-code reporter；V1 延迟读取、V2 两 pass、V3 当前轮真实压缩及 F5 支持/降级矩阵；mock 包含 1A 单端口骨架和 1B 本切片所需保存/join/幂等/冲突 | `run/turn_state.py`、`run/runner.py`、`run/finalizer.py`、`engine/session_lifecycle.py`；若判别需要快照/锁或新增接缝，重新呈报 R2；workflow/mock design 影响按实际文件登记 | 真实 A1→write_file→A2 到单端口 mock 的闭环；无 hooks、save=False、trajectory disabled、A1≠A2、正常 flush 通过；V1–V3 判别完成且恢复/跳过清单经责任人裁决后才扩大 reporter/ACP 开发 |
| 2 | `telemetry-acp-desktop` | ACP 输入捕获、selected Agent 1001、desktop 上下文、锁内 live-history 输出选择、final-model-identity/attribution、真实桌面 schema | `app/acp/server.py` | 输入/输出与桌面消费闭环；1001 每 logical turn 一条且关联首个成功 A，最终响应通常关联 A2；并发、save=False、取消不串值 |
| 3 | `telemetry-parity-hardening` | M1-T、0.28 全字段 parity、slash/local child/hosted 保留场景、BR-9/BR-10、compaction/edit/脱敏、长会话/背压/全局资源关闭 | 由本批次 design 另行裁决 | 字段和异常矩阵关闭，所有保留/删除/差异有依据；offset 缓存是否实施由实测决定 |

mock **放在批次1**，不放探索批次，也不另建大型前置 mock 批次。批次1同时包含 1A 单端口骨架与 1B 本切片 telemetry；开始前必须按流程修订既有 mock design 的多端口决定和 DIRECTORY 约束并签认，未签认不得实施 1A/1B。批次1只实现垂直切片所需能力；完整故障注入和其他扩展矩阵归批次3。BR-1/5/6 在批次1期间并行向后台正式确认；关键前提失败时停止扩张并重评 N1-A 完整成本。

真实后台与数据治理是独立内网验收门禁，不混入外网开发批次；BR-1~BR-7/BR-9/BR-10（BR-8 已撤销）实际部署、真实存储 join、桌面生产组合和代码/路径/参数治理按上线验收执行。

### 长期根分支与工作块分支

```text
main_aixcoding_cli
  └─ feat/telemetry-exploration              # 长期根分支（探索 commit 已在其上）
      ├─ feat/telemetry-session-analysis     # 工作块分支（示例名，按批次/工作块命名）
      ├─ ……（批次1/2/3 等各工作块分支，做好后 PR 合回长期根分支）
```

- 各工作块分支从长期根分支切出，PR 回合到长期根分支；每块仍独立 requirements/design/R2/verification，不把长期分支变成不可审的巨型提交。
- 当前 `aixcoding-tests.yml` 和 `aixcoding-upstream-ci.yml` 仅对目标为 `main_aixcoding_cli` 的 PR 自动触发。**首个工作块 PR 前，必须在实施 design 中登记并修改这两个 workflow 的 `pull_request.branches`，加入 `feat/telemetry-exploration`，并实证工作块 PR 双 CI 运行**；该 workflow 改动本身可直推长期根分支（一次性、低风险，人工核验）。不能只本地跑测试代替。
- 长期根分支定期同步 `main_aixcoding_cli` 以限制漂移。最终 `feat/telemetry-exploration → main_aixcoding_cli` 整体合并前完成全部批次验收、整体回归、文档签认和最终 PR 双 CI；F4 同时要求以已交付 0.35.2 为基线完成保留/复用/替换/删除清单、唯一生产发送权、后台/桌面切换与回退验证，不默认要求历史数据迁移或提前选定开关机制；若主干会直接用于发布，真实后台内网冒烟也必须在合并前通过。
- 本策略只是已确认的组织方案，不是修改 workflow 或执行 Git 写操作的授权；实际命令仍逐条授权。

### `aixcoding/tests/telemetry/` 处置

**明确结论：四个文件已随长期根分支首个 commit `7f3fe332` 提交并推送（2026-11-19），不创建探索独立 PR，也不等待任何实施批次。**四个文件为 `test_tool_identity_persistence.py`、`test_request_identity.py`、`test_after_turn_queue.py`、`test_acp_response_identity.py`。

后续不再重复探索提交或 PR 步骤；工作块 PR 只携带该工作块实际变更。正式实现有等价或更强覆盖前，四个实验文件继续保留。

它们用于复现 M0/M1、session 重建、队列和 N7 方向证据，位于根定制开发资产目录，不进 wheel，不影响生产运行，也不移入上游 `tests/`。

这些文件含 test-local helper/harness，不能冒充生产实现。实施批次可复用其样本和断言，并新增正式生产测试；只有正式实现及等价/更强覆盖已合并、文档证据链接已调整后，才逐项呈报是否精简或退役，不在探索交付前删除、合并或搬移。

## 挂起与备忘

- F1 裁决（责任人，2026-11-14）：首轮静态研究和 E1 依据 DEVELOPMENT.md §4.2 免判定清单②的只读操作/运行测试，合规且无需追认；路径 1 裁决范围是建立探索文档。未签认 design 的实验描述不是 E1 的授权依据；E3 等新增实验代码必须待探索 design 签认后实施。
- 此前“request_attempt_id 不能作为 requestId”的表述已纠正：它能唯一标识实际 HTTP attempt，只是不能在保持旧逻辑调用语义时原位替换。详见 `research/request-identity.md`。
- 2026-11-14 的 N2-A exchange 主键和 C1 优先是历史决策；2026-11-16 已暂定改为最终成功 attempt 主键，C1/C2 仅作开发期严重问题后的回退备选。缺 A-final 跳过并记录原因，不混填；N1-C 独立 LLM endpoint 仍是当前倾向而非实施授权，详见 `research/solution-space.md`。
- 此前四实施批次预案已由 2026-11-17 责任人确认的“三个开发批次+独立内网验收门禁”取代，具体见上文实施策略。
- 不做崩溃/强杀补报；不补桌面端原本自行上报的内容。
- ACP 流式模型调用通知暂无已确认消费方需求，不提前实施。
- 不恢复共享 INDEX/ROADMAP；全库批次全景使用 `docs_report.py`，后续实施状态归各自 plan。
- BR-1 语义修订（2026-11-18 责任人裁决）：服务器不做"实际成功请求"判定（200+业务错误、流中断、Responses pending 在服务器侧不可靠判定），每条请求记录保存自身 attempt header；成功语义由独立 LLM 报告 join 命中声明，BR-6 升格为成功语义唯一声明源、与 BR-1/BR-5 绑定 P0。后台义务减轻。已同步 backend-change-requests/backend-confirmation-checklist/review-handoff/request-identity/request-id/open-risks/requirements/test-plan/backend-contract-questions（B1 历史答案加注记）。
- ID 原值裁决（2026-11-18 责任人）：`Chrys-Request-Attempt-Id` 及其他全部 ID（requestId/funcId/reportId/spanId/parentSpanId）**保持原值 32hex、不转 UUID**，取代此前短暂的 UUID 归一化安排（演进全记录见 verification）；前提为全局唯一性（均为 128-bit 随机 ID，工程满足）。配套：后台需接受 32hex 格式并与 0.28 UUID 文本历史数据混存（BR-5 确认点）；Agent Studio `ModelRequestIdSchema` 放宽接受 32hex（桌面侧配套，N7/批次2 落实）。核心契约文档（checklist/change-requests/handoff/requirements/open-risks）已按新口径改写；request-identity 及相关节点（request-id/llm-report-transport/ai-code/tools-and-skills）中的 UUID 转换与 golden 表述以本条为准，批次1 design 时统一重写。
- BR-8 撤销（2026-11-19 责任人裁决）：不新增可选 providerCallId 字段——后台上报协议面向多个 AI 工具，其他工具没有该字段，不为 iCode 特有对账需求增加协议项；模型侧对账在端侧完成（funcId=T 可在客户端 session/trajectory 反查 provider toolUseId 与工具调用信息）。tool-detail 报文不含 providerCallId；确认单已删该项。
