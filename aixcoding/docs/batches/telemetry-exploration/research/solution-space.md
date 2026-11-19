# Telemetry 决策空间图

> 状态：主要方向性节点已收敛，当前有效结论及评审入口见 `review-handoff.md`。本图仍不是线性实施计划或授权；节点可以分裂、合并、重开，分支间存在依赖时按图处理，不强行保持为树。

## 1. 目的与使用方式

本图记录已知方向、确定可行/不可行的技术边界、责任人已确认决策、当前倾向、待调查问题和必须实施后才能验证的事项。任何节点未被标记为“已确认”，都不得因写在文档中而被当作实施决定。

详细节点放在 `nodes/`；总图只保存节点状态、分支摘要和依赖，避免复制大段证据。

### 技术判断

- **已证可行**：有充分源码/测试或运行证据支持。
- **条件可行**：依赖服务器、上游 API、数据前提或消费方改造。
- **待调查**：现有证据不足以判断。
- **待实验**：有候选假设，需样本或实际实现验证。
- **当前不可行**：在现有机制和约束下不能实现；上游新增能力后可重开。

### 决策状态

- **已确认**：责任人已明确选择，可在实施中作为当前基线；发现新问题仍可重开。
- **当前倾向**：讨论中的优先方向，未确认。
- **备选**：保留的可行路线。
- **暂缓**：暂不投入，等待前提。
- **未选**：各分支尚未裁决。
- **排除**：当前需求下不采用，并记录理由。

### 节点记录模板

```text
节点 ID / 问题 / 依赖
分支：技术判断 / 决策状态
已核实证据
未知、风险和反例
下一判别动作及成功标准
对其他节点的影响
```

## 2. 当前高层图

```text
N0 需求约束
  │
  ├─ N2 成功模型调用 requestId 选哪一种？
  │    ├─ N2-B-final 最终成功 attempt ID【暂定采用】
  │    └─ N2-A 最终成功 exchange ID【开发期回退备选】
  │
  ├─ N1 LLM telemetry 通过什么通道上报？
  │    ├─ N1-A 模型 body middleware【备选】
  │    ├─ N1-B exchange header【回退备选/上游候选】
  │    └─ N1-C 原调用接口 + after_turn 独立 telemetry endpoint【当前倾向】
  │         ├─ 现有 attempt header + 报告/工具/ai-code 使用 A-final【当前路线】
  │         ├─ C1 新增 exchange header 直接关联【开发期回退备选】
  │         ├─ C2 attempt 映射到 exchange【开发期回退备选】
  │         ├─ 依赖 N3 进程内分析触发
  │         └─ 依赖 N8 有序 best-effort【已确认】
  │
  ├─ N3 何时、在哪里分析？
  │    ├─ 进程内 after_turn【大方向已证可行】
  │    ├─ run-owned快照 + N3-A finalizer【AI当前推荐】/ N3-B EventBus【多消费者再评】
  │    ├─ 外部 after_turn hook【不满足进程内要求】
  │    └─ SessionSaved/success callback/stream【不能单独替代】
  │
  ├─ N4 分析哪些数据？
  │    ├─ 仅 session.json【不足以覆盖完整需求】
  │    └─ 整个 session 目录【大方向条件可行，实施细节暂缓】
  │
  ├─ N5 工具与技能如何投影？
  ├─ N6 ai-code 如何重建？
  ├─ N7 ACP 如何获得 ID 和桌面上下文？
  ├─ N8 投递顺序、ACK、幂等和失败策略
  ├─ N9 文件缺失的运行时上下文如何补采或降级？
  ├─ N10 mock 与实验如何验证所选组合？
  └─ N11 fork 先行、上游先行还是并行？
```

## 3. 节点总表

| 节点 | 已知分支与当前状态 | 已确定边界 | 下一判别动作 |
|---|---|---|---|
| **N0 需求约束** | 旧版提需不猜测、零上游优先/必要改动少而集中、逐方案先查大阻塞、非实时、只记录成功模型调用、无崩溃补报、不补桌面端上报【已确认】 | 缺陷修复与差异由人确认；不可行即停；上游建议/自行定制/无法做到分类 | 新约束出现时重开 |
| **N1 LLM 上报通道** | 原调用接口+独立 telemetry 当前倾向；最小关联 envelope、save endpoint、requestId 单键幂等【B7 暂行采用 AI 方案】；C1/C2 仅作回退 | 责任人暂无法技术决断并委托 AI；旧搭车无 model/usage/timing；后台现网未确认，首版不强制业务扩展字段 | 按暂行契约设计 mock 关联闭环；正式后台返回或实施问题再集中回评，不各出口打补丁 |
| **N2 requestId** | 最终成功 raw attempt【暂定采用】；内外均原值 32hex 不转 UUID【2026-11-18 原值裁决】；exchange【开发期回退备选】 | 内部 header/session/trajectory/message 与全部出站同文本原值，客户端无转换层；同一成功 M 的外部记录同文本，A1/A2 不混用 | 32hex 格式接受/新旧混存、三协议/retry/流式/Responses、原记录/报告 join 和桌面 schema（放宽）验收 |
| **N3 分析触发** | 进程内 after_turn【大方向已证可行】；run-owned身份快照+N3-A direct finalizer【AI 当前推荐】；N3-B EventBus【公共多消费者时再评】 | runner在trajectory激活前已确定logical/pass；最小候选为turn_state/runner/finalizer/session_lifecycle四文件；禁止latest TurnRecord；普通异常隔离、取消不吞 | 先由另一 AI 评审；收敛后呈报实施design/R2裁决，新增组合行为留实施验证 |
| **N4 数据源** | 整个 session 目录【大方向条件可行】；仅 session.json【不足】 | 默认装配；exchange/attempt 需 trajectory，ai-code 需 mutation/blob；缺失可检测并降级 | 不阻塞；逐字段 parity、故障组合和增量分析留 N5/N6/实施 |
| **N5 工具与技能** | 本地普通工具/load_skill/shell/MCP 与 local child【大方向条件可行】；普通工具最小 final DTO【B8 暂行采用 AI 方案】 | 七项必填、终态1/2/4、无 PENDING/update、无三时间字段、成功不报完整正文；BR-8 providerCallId 已撤销（2026-11-19），对账端侧完成；严格 mock 校验与 `(requestId,funcId)` 幂等 | 按暂行契约设计 mock；slash/cancelled 继续单列，不扩展 hosted/外部 ACP 内部 |
| **N6 ai-code** | outcome 闸门 + 最终参数 + mutation/blob【大方向条件可行】；reportId=T 原值、`(requestId,reportId)` 幂等【B8 暂行采用 AI 方案】 | 当前 write/edit 单 T 单 mutation；同 T 多 mutation 跳过；不新增上游 mutationId；同路径多次写不合并 | 按暂行 golden 设计 mock；组合样本、同键冲突、截断参数和 golden parity 留实施 |
| **N7 ACP** | 最终 PromptResponse 主动携带 requestId【已确认】；响应时 live-history【暂行采用】；requestId 原值 32hex【2026-11-18 原值裁决】；桌面 0.28 输入捕获【Q2 已确认纳入】 | 输入按 session/turn 捕获 selected Agent/desktop 上下文；输出 prompt_lock 内选 raw A-final 直接作为 requestId（无转换）；仅 server+定制 helper，无需 registry；request_tracking/ids 不改 | 实施设计/R2 按 N7 批次进行；恢复 1001/desktop 字段，验证输入并发/缺失、后台格式接受和桌面 schema（放宽接受 32hex）；workflow 明确退出 |
| **N8 投递与失败** | 有序 best-effort、允许孤儿【已确认】；进程级owner按session隔离，集中lifecycle有界flush+session close【AI 当前推荐】 | flush只排空已生成报文，不做trailing-save最终补扫；active delete失败可重建worker；TUI/ACP/delete/EOF无需逐入口接线 | 随N3呈报实施design/R2；后续故障注入、无hooks、删除失败和正常退出验证 |
| **N9 运行时上下文** | 固定运行时 + 当前轮 live/finalizer + ACP 捕获【大方向条件可行】 | desktop envelope 只能 ACP 补；Git 轮末快照不等于事件时事实；无依据省略 | 不阻塞主路线；N7 真实 ACP 样本、Git 语义和降级矩阵留后续 |
| **N10 mock/实验** | 当前 auth+catalog:7777、update:7778【已核实】；单端口唯一组合模式【责任人已选评估目标】；telemetry 与骨架按 1A/1B 分步【AI 建议，讨论中】 | 外网开发不能以前后端直连为前置；mock 只证明目标契约；独立工厂仅测试/调试，不形成多端口组合；旧 mock design 与 DIRECTORY §6 只有实际实施前才修订 | 在本探索批次内讨论总体路线和最小闭环；是否另建实施批次/ADR 另行呈报裁决 |
| **N11 实施路线** | fork 最小接缝 / 上游先行 / 并行【未选】 | 上游建议必须通用，探索 design 不授权 R2 | 主要节点已收敛；另一 AI 评审后由责任人按依赖和上游反馈裁决 |

## 4. 当前路径与未决组合

当前推荐路径仍须独立评审和实施 design/R2，不是最终授权：

```text
N2-B-final 最终成功 attempt ID【暂定采用】
  + N1-C 原调用接口 + 独立 telemetry endpoint【当前倾向/B7暂行】
  + 现有 raw attempt header，报告/工具/ai-code 出站使用同一原值 A-final【2026-11-18 原值裁决：不转 UUID】
  + run-owned 快照 + N3-A direct finalizer + 集中 lifecycle drain【AI当前推荐】
  + N4 整个 session 目录【大方向条件可行】
  + N8 有序 best-effort、允许孤儿【已确认】
```

该组合可消除 LLM body、ChatMiddleware 注入和新增 exchange header。内部仍保留 E/A-final 双 ID 以完成工具/mutation 关联和开发期回退；外部 requestId 由 raw A-final 单点确定性转换，缺失时跳过并记录原因，不用 exchange 混填。若开发期发现严重问题，再回评 C1 exchange header 或 C2 attempt 映射。

## 5. 分支相关的 fork 与上游建议

| 建议/改动 | 适用分支 | 不适用时可否取消 |
|---|---|---|
| ChatMiddleware 注册/统一组栈 | N1-A，或需要请求前运行时信息时 | N1-C 下本 telemetry 不需要 |
| `Chrys-Exchange-Id` | N1-B、开发期回退 N1-C1 或通用网关追踪 | 当前 N1-C A-final 路线复用现有 attempt header，可取消新增 |
| exchange body 前 helper | N1-A/N1-B | N1-C 从事后 trajectory 获取，不需要 |
| EventBus AfterTurn/SessionEnded | N3，适用于 N1-A/N1-B/N1-C 的进程内事后分析 | 长期通用能力；fork 可用直接 finalizer 回调过渡，也可直接采用通用事件 |
| tool invocation audit | N5/N9 高保真分支 | 接受降级时可取消 |
| ACP model-call notification | N7 流式消费分支 | 最终响应或 session/turns 足够时取消 |

## 6. 已知“确定不能这样做”的边界

- 事后分析 session 不能修改已经发出的模型 HTTP body。
- `request_attempt_id` 不能被当作“整个 exchange 不变”的 ID，除非改变上游语义；本需求不改变它。
- 仅用 `session.json` 不能保证恢复全部 exchange、attempt、mutation/blob 细节。
- 文件缺失时不能用 session-latest、当前 cwd、当前 Git HEAD 或当前磁盘文件冒充历史事实。
- 独立 CSAS mock 收不到发给模型网关的 body/header。
- 有序发送不等于服务器已成功建立父记录；严格依赖需要业务 ACK。
- 外部 after_turn hook 不满足“分析在 aixcoding-cli 进程内”的约束。

当前剩余开放项主要是 A-final 开发期闭环与原值口径联调验收（32hex 格式接受/混存/桌面 schema 放宽）、slash/cancelled 协议，以及 N7 暂行方案的实施验证，见 [开放风险与协议疑问](open-risks.md)；N7 最终 PromptResponse 主动携带 requestId 已确认，响应时 live-history 暂行采用；2026-11-18 原值裁决——所有 ID 保持 32hex 原值、无转换层，遇到问题回评。三个执行时间字段已全部去掉，hosted 时间保真和补采不再是开放项。外部 ACP 内部工具明细退出当前重点，N6 和 N9 不再列为方向风险。

## 7. 探索推进规则

1. 每次讨论先定位节点；新分支加入总图，再记录证据，不直接覆盖旧分支。
2. 责任人确认只改变对应节点的“决策状态”；技术证据变化可重开已确认节点，但必须留痕。
3. 某分支被排除时保留理由和重开条件，防止后续重复讨论。
4. 实验先写判别标准，失败结果同样记录；不能用单一样本证明整个分支。
5. fork/上游建议按适用分支记录，不能从某条路径的需要推导为全局必需。
6. 当前路径变化时同步 `new-version-solution-map.md` 和 `plan.md`，实施批次只引用已确认节点及其实际依赖。
7. 详细证据优先放专题/节点文档，总图保持可扫读，不复制完整报文和源码。
8. 方案按“不改上游 → 必要改动少且集中 → 需要上游/外部协作”的顺序逐个探索；确认不可行即停止该分支，保留证据和重开条件，不继续投入非阻塞细节。
9. 旧版缺陷修复和与旧版不一致的变通只是建议，责任人逐项确认后才改变实施基线；技术分类或源码证据不等于需求裁决。
10. 近期实验只回答当前方案的方向性阻塞；逐字段 parity、完整异常矩阵和报文实现细节留到实际实施，除非它们本身足以推翻方案。

## 8. 已展开节点

- [N1：LLM telemetry 上报通道](nodes/llm-report-transport.md)
- [N2：逻辑 requestId 选择](nodes/request-id.md)
- [N3：进程内 after_turn 公共生命周期](nodes/after-turn-lifecycle.md)
- [N4：整个 session 目录的数据覆盖](nodes/session-data.md)
- [N5：工具与技能的 exchange/attempt 关联及协议覆盖](nodes/tools-and-skills.md)
- [N5 扩展：广义工具、技能、命令与智能体调用覆盖](nodes/broad-tool-coverage.md)
- [N6：ai-code 报文与代码块重建](nodes/ai-code.md)
- [N9：运行时上下文与公共字段](nodes/runtime-context.md)
- [D1：旧版缺陷、协议限制与新版重建边界](defect-register.md)

其余节点先在总表保留分支和状态；进入集中讨论或出现分支争议时再展开独立文档。
