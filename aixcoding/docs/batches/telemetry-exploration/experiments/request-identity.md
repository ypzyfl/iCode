# 实验：Request Identity

> 状态：E1、M0/M1-I 和 N7 方向实验已完成；当前暂定 A-final 主键并采用方案 A 外部 UUID。原记录↔独立报告的实际存储 join、后台原子幂等和完整 M1-T 留实施/联调；E3 仅在回退 exchange 时恢复。未完成的实验不预先声明通过，当前总览见 `../research/review-handoff.md`。

## 实验目的

验证最终成功响应的 `request_attempt_id`（A-final）在普通/流式、SDK retry、外层 retry、redirect 和 Responses retrieve 中与 assistant message、实际请求 header 及服务器成功记录保持一致；内部继续保留 exchange 用于关联和开发期回退。缺 A-final 时跳过并记录原因，不用 exchange 混填。

## 已完成：静态与历史调查

- 只读核查当前实现和上游测试语义，证据见 `../research/request-identity.md`。
- 只读 Git 历史定位引入提交，实际命令与结果见 `../verification.md`。
- 这些证据证明当前代码设计和测试意图，不替代本基线运行验证。

## 已完成 E1：上游 request tracking 定向测试

- 对象：`tests/service/llm/test_request_tracking.py`。
- 判别点：三协议 header/body、非流式/流式、SDK retry、redirect、连接失败、message 只保留最后 attempt。
- 结果：2026-11-14 实际执行，收集 10 项，`10 passed in 23.60s`，退出 0；完整命令见 `../verification.md`。
- 边界：这是上游定向测试通过，不是完整套件或定制 telemetry 功能验证。

## E2：A-final 客户端/服务器闭环样本（身份子集已完成，存储闭环待 M1-T）

> 2026-11-17 更新：M0/M1-I 已完成真实 A1→工具→A2、两工具、失败不借旧 A、SDK retry、Responses retrieve、并发 scope 和 redirect 锚点。以下最初样本清单保留为完整验收范围；未覆盖的原记录/独立报告实际保存与 join 不再写成“整个身份实验未开始”。

- 样本：至少包含普通/流式成功、SDK retry、Chrys wire retry、redirect、Responses continuation（非流式/流式），以及前次成功后本次失败、200 后流失败和 pending 后失败。
- 采集：trajectory 的 exchange operation ID、request attempt IDs、最终 assistant message metadata、实际请求 header 和服务器成功记录。
- 判别点：SDK retry 不增加 exchange、成功取最后 A；wire retry 新建 E/A；redirect 使用最终 hop A；Responses 每次 poll 新建 E/A，最终 M 属于最后 poll；同一成功 M 的原成功记录和独立报告使用同一 UUID(M 的 A-final)；工具和 ai-code 仅在实际由该 M 产生时共享该键，不能跨 A1/A2 或历史工具混填。
- 缺失处理：失败/pending/部分流不上报；缺 A-final 时跳过并记录原因，不借历史 A、不用 exchange 或新 UUID4 混填。
- 可逆性：同一 fixture 保留 E/A 双键 golden，内部工具/代码归属不随外部主键切换改变。

## E3：middleware body 前上下文（仅开发期回退 exchange 时恢复）

- 范围：Chat Completions、Responses、Anthropic，主调用和 side call。
- 落位：`aixcoding/tests/telemetry/test_request_identity.py`；仅新增定制测试，不修改上游源码或上游测试。
- 方法：回退分支经 design 签认后，使用最小定制测试 middleware，只读取并断言 ExchangeTrace；wire body 用现有 scripted transport/mock 验证。
- 判别点：`call_next()` 前可读取 operation ID，此时无法取得未来 attempt ID；body 注入的值与 trajectory exchange 归一化后相同。
- 当前 A-final 路线不执行该实验，也不采用无 Trace 时另造 UUID4 的兜底。

## E4：外部表示口径（2026-11-16 已暂定）

> 历史记录：以下生成点 UUID 化和全链同文本是当时的评估方向，已由 2026-11-17 的方案 A 取代；现行口径见本节末尾“方案 A 解决记录”。

- 当前暂定 A-final 为主 requestId；客户端上报什么，服务器就记录什么。
- 外部尽量使用 UUID，除非代价明显高于收益；优先评估 attempt 生成点单点 UUID 化，确保 header、session、报告和服务器全链同文本。
- 若单点 UUID 化代价明显高，则全链保留 32hex，不在独立报告等单一表面转换。
- 后台没有同一逻辑调用的多 HTTP 记录细节，不再确认“同一 requestId 多 HTTP 行”假设。

## 未证明事项

- E1 及 E2 的客户端身份子集已通过；E2 的实际服务器保存/独立报告 join 和完整异常矩阵尚未执行，E3 当前不执行。
- 尚未验证所有 side call、无 trajectory cycle、Responses continuation 和并发 sub-agent 的组合场景。
- A-final 仅为主 requestId 暂定方向；上述样本用于开发期排除严重问题，发现阻塞即暂停并回评 exchange，不承担上线后历史迁移。

## E5：N7 响应时 live-history 与 UUID 兼容实验（2026-11-17）

**实验落位**：新增 `aixcoding/tests/telemetry/test_acp_response_identity.py`，与既有 `test_tool_identity_persistence.py` 同属本批次定制实验/测试目录。后者 docstring 和本文档均已明确其探索实验属性，原本就在正确目录，无需移动或改名。

**选择器实验**：只在测试文件内实现方向性 `_select_response_attempt`，直接复用生产 `Message`、`TurnRecord`、`turn_slices`、history marker 和 `with_chrys_metadata`，不新增产品 helper。覆盖：同一 history 两 logical turn、同 turn 多主模型响应、最后响应缺 A 不借早值、status marker 排除、injected retry 新响应覆盖、opener 缺失 fail closed、live 选择不创建 session 文件、定制 envelope 与 chrys sibling 共存。

首轮收集 7 项，`4 passed / 3 failed`：失败来自实验自身把 tool result 错建成 user turn、使用不存在的 `HistoryMarkerKind.INJECTED`、误猜 `with_chrys_metadata` 签名；按真实 tool 角色、`INJECTED_KEY` 和 `(meta, chrys)` API 修正后 `7 passed in 0.45s`。随后整个定制目录 ruff 通过，`9 passed in 4.42s`（新 7 + 既有工具身份 2）。

**UUID 探针**：直接调用生产 `is_valid_id("request_attempt_id", value)`，canonical UUID4 输出 `canonical_valid=False`，旧 32hex 输出 `legacy_32hex_valid=True`。`request_attempt_id` 未注册特殊分类，默认走 32hex analytics；writer 会将 malformed ID 转为 `ENCODE_FAILURE` gap，reader 也拒绝 malformed ID。相关 `test_ids.py`、`test_request_tracking.py`、`test_turn_trace.py` 共 `96 passed in 3.04s`，锚定当前行为。

**新增问题与最小修正方向**：不能只改 `request_tracking.py` 生成器。保持暂行 UUID 方向还需在 `foundation/trajectory/ids.py` 为 `request_attempt_id` 增加窄范围专用校验，读取侧兼容旧 32hex和新 canonical UUID，新生成只发 UUID4；不得放宽全局 analytics 正则。按“执行中有问题再分析讨论”的约定，本问题在此呈报，未直接修改产品代码。

**方案 A 解决记录（2026-11-17）**：上述生成器+trajectory 校验问题经讨论后，责任人确认后台可按方案 A 配合，原“生成点 UUID+ids.py 双格式校验”不再实施。内部 raw 32hex 保持不动；后台原模型成功记录做 raw→canonical UUID，客户端独立 LLM/tool-detail/ai-code/ACP 在定制出站边界用同一规则转换。UUID 相关上游改动降为 0，N7 仍只需 ACP server 输出接缝。双方 golden、外部记录 join 和桌面 schema 验证见 BR-5。

**未证明**：实验选择器不是实际 ACP server 接线；真实 prompt_lock、并发 session、save=False 的端到端响应、真实压缩、长 history 性能、最终桌面 Zod 闭环仍未验证。E2 的实际服务器保存/关联闭环也未因客户端身份子集和本方向实验完成而完成。
