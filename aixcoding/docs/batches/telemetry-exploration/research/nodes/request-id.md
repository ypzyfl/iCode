# N2：成功模型调用 requestId 选择

> 决策状态：**暂定采用“最终成功响应的 request attempt ID”作为服务器主 requestId（责任人，2026-11-16）**。实际实现发现严重问题时暂停并回评 exchange；这里不承担上线后迁移场景。
>
> 内部仍保留 exchange + final attempt 双 ID，内部分析不绑死外部键。缺少最终 attempt 时跳过该条并记录原因，**不允许用 exchange 混填 requestId 兜底**。
>
> **2026-11-18 ID 原值裁决**：所有 ID 保持原值 32hex、不转 UUID（此前归一化安排作废）；本文历史讨论中的 UUID 形态表述按原值理解。权威口径见第 5 节与 `../backend-change-requests.md` BR-5。

## 1. 已确认的需求语义

当前只记录成功大模型调用，不要求维持旧版“一次逻辑调用一个主 ID”的粒度；目标是让该次成功响应产生的工具调用、ai-code 和其他信息关联到同一个成功模型调用记录。

```text
服务器主 requestId = 最终成功 assistant message._chrys_request_attempt_id（A-final）
exchange ID         = 内部关联、retry 边界和开发期回退证据
失败/pending/部分流 = 不上报，不选择失败或中间 attempt 冒充成功
```

“模型成功”指最终模型响应落地，不是任意 HTTP 2xx，也不要求后续工具或整个 turn 全部成功。工具自身 outcome 和 ai-code 成功写入条件独立判断。

## 2. 分支裁决

| 分支 | 技术判断 | 决策状态 | 理由 |
|---|---|---|---|
| **N2-B-final 最终成功 attempt** | 正常成功 message 已持久化 A-final；线上已有 attempt header | **暂定采用** | 直接标识最终成功响应；服务器可记录同一值；无需新增 exchange header 或 E↔A 分组 |
| **N2-A 最终成功 exchange** | 文件可持久化；需 C1/C2 关联原记录 | 开发期回退备选 | 保留内部逻辑调用关联；Responses 每次 poll 也新建 E，回退时使用 E-final |
| **N2-C provider request ID** | 条件可用 | 排除为主 ID | 响应侧返回、可能缺失，不能由客户端统一生成 |
| **N2-D 另造本地 UUID4** | 旧版可用 | 排除为当前 fallback | 会脱离原成功记录；缺 A-final 时按裁决跳过，不另造主键 |
| **N2-E turn/tool operation ID** | 标识其他实体 | 排除为主 ID | 一个 turn 可有多个模型调用；tool operation 属于工具 |

## 3. 已核实的持久化关联

```text
assistant message._chrys_operation_id = 产生消息的 exchange E
assistant message._chrys_request_attempt_id = 最终响应 attempt A-final
model.request.*.operation_id = 所属 E
model.request.*.request_attempt_id = 单次 HTTP A
工具 parent_model_operation_id = 产生工具调用的 E
mutation.tool_operation_id → tool operation → parent E / assistant M
```

正常成功时，`session.json` 同时有 E 和 A-final；全部 attempts 必须联读 trajectory/turn trace。普通工具经 `T/C→M` 取得 E/A-final，ai-code 经 `mutation→T→M` 取得。失败/取消/未 landing 时没有本次最终成功 M，不上报且不借用历史 M。详见 `../request-identity.md` 第 9–14 节。

## 4. retry、redirect、Responses 和流式口径

- SDK 内 HTTP retry：E 不变，A 新建；主 requestId 使用最后成功 A，不使用失败 A。
- redirect：E 不变，每个 hop 新 A；使用最终响应 hop 的 A-final。
- Responses create/retrieve：当前每次 continuation poll 都重新 `begin_exchange()` 并关闭上一 E，因此 E/A 都变化；最终响应属于最后 poll 的 E-final/A-final。
- Chrys 外层 retry：E/A 都新建；使用新逻辑调用最终成功 M 的 A-final。
- 流式：同一 HTTP stream 的 blocks/chunks 共用 E/A；最终 result hook stamp A-final。prepared/200 不等于成功，流失败且无最终 M 时不上报。
- 一个 turn 可有多个成功模型响应；每个工具和 ai-code 关联实际产生它的 M，不统一挂 turn 最后调用。

## 5. ID 表示：内外均为原值 32hex（2026-11-18 责任人裁决）

UUID 表示历经两版暂行（attempt 生成点 UUID 化、raw→canonical UUID 归一化）后，由 2026-11-18 责任人裁决定案：**所有 ID 保持原值 32hex、不转 UUID**（演进全记录见 `../verification.md`）。

- **内外同文本原值**：`Chrys-Request-Attempt-Id`、request extension、response/message metadata、session、trajectory、raw HTTP log、内部 E/A join 与全部上报出口（独立 LLM/tool-detail/ai-code/ACP）均使用同一 raw 32hex。`request_tracking.py`、`foundation/trajectory/ids.py` 和通用 `new_analytics_id()` 均不修改，客户端不引入任何转换 helper。
- **后台职责**：原模型调用记录直接保存该次请求的 raw header 原值，不做成功判定（BR-1）；成功语义由独立 LLM 报告 join 命中声明。缺失/非法 raw 不另造 ID。
- **后台接收入口**：独立 LLM/tool-detail/ai-code 收到 32hex 原值后按不透明字符串原值保存，不再次生成或转换。查询、合并及 `(requestId,funcId)` 幂等统一使用原值文本；后台需接受 32hex 格式并与 0.28 UUID 文本历史数据混存（BR-5 确认点）。
- **桌面配套**：Agent Studio `ModelRequestIdSchema`（原 `z.string().uuid()`）放宽接受 32hex，纳入端到端验收。
- **缺失处理**：缺 A-final、raw 非 32hex、metadata 损坏或无法确认最终响应时跳过并记录原因，不用 exchange、本地 UUID4或历史 attempt 混填。

该口径不需要 UUID 相关上游源码改动；N7 仍只需 `app/acp/server.py` 的最终 ACP 输出接缝和定制 helper。

## 6. 对 N1 上报通道的作用

当前路线可直接复用现有 `Chrys-Request-Attempt-Id`：原成功请求与 after_turn 内部关联使用同一 raw A-final；后台原成功记录和客户端独立报告、工具、ai-code 的外部记录统一使用 A-final 原值（32hex），无需 C1 exchange header 或 C2 E↔A 映射。

N1-A body middleware、N1-B exchange header 不再承担当前主键上传；C1/C2 仅作为开发期 attempt 方案出现严重问题后的 exchange 回退通道。after_turn + 全 session 联读 + N8 有序 best-effort 的关系不变。

## 7. 开发期下一判别动作

- 最小样本验证普通/流式、SDK retry、redirect、外层 retry、Responses continuation 中最终 M 与实际成功请求为同一 raw A-final，服务器记录为 A-final 原值。
- 验证前次成功后本次失败、200 后流失败、pending 后失败不上报且不借旧 A；并发不串号。
- 验证模型成功后工具失败仍关联 A-final；ai-code 按实际成功写入条件处理。
- 以同 fixture 保留 A/E 双键 golden，确保开发期回退只改变外部键，不改变工具/代码归属。
- 在实施 design 中落实原值直用（无转换层）；验证原记录/独立报告/工具/ai-code/ACP 全链同文本原值，不修改生成点或 trajectory 校验。

详细历史证据见 `../request-identity.md`，实验记录见 `../../experiments/request-identity.md`。
