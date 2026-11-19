# A-final 五类记录最小端到端闭环

> 2026-11-17 只读调查。结论：客户端身份来源与工具/文件变更的数据充分性已有较强证据，但五类外部记录的生产、保存和 join 尚未实现；本轮没有发现新的“已证明不可行”硬阻塞，也没有把 B7/B8 暂行契约当成现网能力。

## 1. 判别目标与正确身份关系

目标不是让五类记录机械地具有同一个 requestId，而是验证每条记录关联**实际产生它的成功模型响应**。正常工具调用后还有最终文本响应，因此一个 turn 至少可能有两个 A-final：

- `A1`：产生 write/edit 工具调用的成功模型响应；
- `A2`：工具执行后产生最终文本的成功模型响应；
- `T`：该工具 dispatch 的 operation ID。

最小且有判别力的关系为：

| 记录 | 期望身份 |
|---|---|
| 原模型成功记录 1 + 独立 LLM 报告 1 | `requestId=A1 原值` |
| tool-detail | `requestId=A1 原值`、`funcId=T 原值` |
| ai-code | `requestId=A1 原值`、`reportId=T 原值` |
| 原模型成功记录 2 + 独立 LLM 报告 2 | `requestId=A2 原值` |
| 最终 ACP PromptResponse | `requestId=A2 原值` |

必须断言 `A1 != A2`。如果只构造“每类一条、所有 requestId 全相同”的样本，会同时掩盖两类常见错误：工具/ai-code 错取 turn 最后一次 A2，以及 ACP 错借产生工具的 A1 或历史 turn。

共同转换 golden 仍使用：

```text
raw A1 = 00112233445566778899aabbccddeeff（requestId 直接使用，无转换）
raw T  = 10000000000000000000000000000002（funcId/reportId 直接使用）
UUID   = 10000000-0000-0000-0000-000000000002
```

实验另取不同的 raw A2，并分别断言内部 header/session/trajectory/message 与外部记录使用同一原值（2026-11-18 原值裁决：外部记录同样为 32hex 原值，无转换；实验当时的 UUID golden 断言为归一化安排时期的历史记录）。

## 2. 现有能力与缺口矩阵

| 环节 | 已有实现和证据 | 最小闭环缺口 | 判定 |
|---|---|---|---|
| 共同身份来源 | `request_tracking.py:37-43,62-83` 每个 prepared attempt 生成 raw A；`observer.py:478-493` 将最终 A 写入 landed response/新 assistant message | 服务器与五类外部记录尚未共同验证 | 来源已证，闭环未证 |
| 原模型成功记录 | 三协议 request tracking 测试覆盖实际 header、response/message、retry、redirect、流式和 ContextVar 并发 | `model_catalog` 不读取 attempt header、不保存成功业务记录；无 Responses/retry/redirect 脚本化服务 | 阻断 |
| 独立 LLM | session/exchange/message 有来源，B7 定义最小 envelope 和 endpoint | 无 analyzer、实际 DTO、reporter、endpoint/mock、持久化及 join | 阻断 |
| tool-detail | 真实 engine/scripted HTTP 实验证明 `T/C/M/A`，且工具关联 A1 而非同 turn 最后 A2；rollback 负例防错连 | 无 after_turn 组包、原值出站、HTTP reporter 和 final-save 存储 | 阻断 |
| ai-code | mutation 有 T、before/after hash/blob，outcome 与审批来源已定位 | 无真实 write/edit 组合分析器、blocks 重建、reportId/DTO、HTTP/mock | 阻断 |
| ACP | PromptResponse 可扩展 `_meta`；测试内 selector 已验证精确 turn、最后主响应和不借旧 A | 真实 server 未接 selector/UUID；桌面 attribution 输入被丢弃；未输出桌面消费的 identity envelope | 阻断 |

这里的“阻断”指当前代码无法直接完成最小端到端实验，不等于路线已证不可行。model/usage/timing/runtime、完整旧字段 parity、广义工具覆盖和 debug 展示不属于最小闭环前置。

## 3. 原模型 mock 的真实边界

`aixcoding/mock/model_catalog/server.py:401-417` 只读取 body 的 model/stream 并返回固定 completion；流式分支 `:436-452` 只发送两个 SSE chunk 和 `[DONE]`。`state.py:24-38` 没有原模型业务记录集合，现有 `test_model_catalog_server.py:300-341` 只验证响应形状。

因此当前 mock 不能证明：

1. 最终成功实际请求的 raw A 被读取并转换为 UUID；
2. 失败 attempt、pending 或部分流不产生成功记录；
3. SDK retry/redirect 只保存最终成功 A；
4. Responses create pending→retrieve 成功时保存最终 retrieve 的 A；
5. 原模型记录能与其他四类记录 join。

这些是身份正确性验证，不是 mock 展示或路由组织细节。

## 4. ACP 真实消费方的新证据

Agent Studio 顶层 PromptResponse Zod 允许扩展 metadata，但手写 `finalModelIdentity()` 只读取 `agent-studio.dev/final-model-identity`：

- `packages/adapters-node/src/agent-host/acp-agent-host.ts:3126-3158` 要求 `schemaVersion=1`、合法 UUID requestId、合法 source，并要求 `spanId` 等于当前 prompt 的桌面 response-attribution span；
- 同文件 `:1382-1407` 发送 attribution、解析最终身份，再按 requestIdentified→complete 顺序推进；
- `packages/contracts/src/ids.ts:25-26` 定义通用 UUID schema，不要求 UUID4 version；
- 当前 fork `src/chrys/app/acp/server.py:281-290` 只返回 turnId/turnNumber/sessionUsage，`:558-566` 未保留 prompt kwargs 中的 attribution；
- 当前方向实验使用的 `agent-studio.dev/telemetry` 只能证明 metadata sibling 共存，不能触发桌面 `prompt.request_identified`。

所以 ACP 最小闭环除了 selector 和 UUID，还必须有两个目标契约要素：捕获/回显桌面 attribution span，以及输出 `final-model-identity`。telemetry turn span 与桌面归因 span 是不同语义，不得混填。真实 server 接线和上游文件修改仍须后续实施 design/R2，本探索不借实验名义直接修改。

## 5. 关键场景证据状态

| 场景 | 已有证据 | 尚未证明 |
|---|---|---|
| 普通成功 | 三协议 header→response/message A；本轮 request tracking 10 passed | 五类记录保存与 join |
| SDK retry × 流式 | 429 A→成功 A，最终 response/message 取成功 A，stream 两态通过 | 原模型只保存成功 A，依赖记录不取失败 A |
| redirect | 每 hop 新 A、并发 scope 不串号 | 最终 hop 与服务器成功记录一致 |
| Responses continuation | 产品 create/retrieve 分支和控制流测试存在 | 现有 continuation 测试使用 AsyncMock，未经过真实 HTTP tracking；最终 retrieve A 的五类闭环未证 |
| 工具后最终回答 | 定制真实 engine 实验证明工具取 A1、不取 A2 | 同一 fixture 的 LLM/tool/ai-code/ACP 联合报文 |
| 失败/pending/部分流 | prepared/连接失败和 wire 清理有底层测试 | 不产生成功报告、不借旧 A、不产生虚假 ai-code |
| 并发/多 turn | ContextVar 与测试内 selector 锚点 | 实际存储、reporter、真实 ACP server 和桌面不串号 |

## 6. 推荐最小判别实验

### M0：五类记录存在性

用 A1 返回一次真实 write_file function_call、工具成功留下一个 mutation、A2 返回最终文本：

1. 原模型 mock 保存 A1/A2 两条成功记录，独立 LLM 也各一条；
2. tool-detail 与 ai-code 都关联 A1 原值，funcId/reportId 都为 T 原值；
3. ai-code blocks 与最终参数、after blob 一致，codeStatus=1；
4. 最终 ACP 身份关联 A2 原值，并回显桌面 attribution span；
5. 任一所需 A/T/blob 缺失时 fail closed，不取 attempts[-1]、session-latest 或新 UUID4。

### M1：一对多与严重错关联拦截

在 M0 后扩展，不阻塞首次存在性验证：

- A1 同时产生两个工具，其中一次 write/edit：两个 funcId 不同、共享 A1，只有成功文件修改生成 ai-code；
- SDK retry、redirect、Responses retrieve：失败/中间 A 不形成成功记录；
- 前轮成功、本轮失败/取消：不借旧 A；
- 两 session 并发：原记录、报告和 ACP 不串号；
- 相同报文重放不新增，同键不同内容 409；这属于遥测传输幂等，不能与模型 SDK retry 的 A-final 选择混为一谈。

## 7. 后续边界

开发期可先在定制目录扩展 mock 和自包含实验，验证目标契约及身份关系；真实 `app/acp/server.py` 接线、response-attribution 捕获和最终桌面联调属于后续实施/R2与内网验收范围。即使 M0 全部通过，也只证明开发期目标闭环，不证明真实后台已经部署或全量 session/性能路线已经验收。

## 8. M0 结果（2026-11-17）

M0 已在 `aixcoding/tests/telemetry/test_tool_identity_persistence.py` 落地：真实 engine 经 scripted `httpx.MockTransport` 发出 A1/A2，真实 write_file 创建 `m0.py`，shutdown 后重读 session、trajectory、mutation 和 after blob，再构造五类测试态目标 DTO。实际 headers 与持久化 message 均为 `[raw A1, raw A2]`；tool/ai-code 使用 A1/T，测试态 ACP final-model-identity 使用 A2 和独立 attribution span，固定 UUID golden 及非法 raw 拒绝均通过。

实验首轮因全局 hook 与无前端审批等待超时，随后明确隔离为空 hooks 配置并使用 bypass 自动审批；另按真实文件修正 arguments 为 JSON 字符串的解析假设。失败过程见 `../experiments/m0-record-contract.md`。最终整个定制 telemetry 目录 `16 passed in 2.34s`，ruff 和 IDE diagnostics 通过。

该结果关闭了“正常工具 turn 的 A1/A2 目标关系是否存在矛盾”的方向疑问，但不冒充生产实现：没有实际 reporter/endpoint/数据库，没有真实 ACP server/桌面事件，没有经过 TCP，也没有覆盖 M1 的 retry/Responses/并发和传输幂等。

## 9. M1-I 结果与 M1-T 边界（2026-11-17）

M1-I 已完成：同一 A1 两工具共享 requestId 但 funcId 不同且只有 write_file 形成 ai-code；前轮成功、本轮 400 失败时当前 turn 无 A 且不借旧值；429→A1→A2 只让成功 attempt 形成记录；Responses create pending→retrieve completed 的 response/message 和测试态成功记录均取 retrieve A；两个并发 Chat scope 的 session/span/request 均不串号。redirect 沿用上游真实 profile HTTP client 锚点共同复跑。最终定制实验与 request tracking `31 passed in 7.30s`，详见 `../experiments/m1-identity-contract.md`。

M1-T 不能由这些测试替代：真实 HTTP reporter/endpoint/数据库尚不存在，语义重放 200、不新增、同键冲突 409、并发原子唯一、孤儿晚到 join 和 read-your-writes 留待 mock/实施验收。按整体风险排序，下一调查转为真实 session 重建正确性，不继续把 mock 存储细节当作最高优先级。真实 ACP server/桌面接线仍未完成。
