# M1：身份矩阵与传输验证边界

> 2026-11-17。M1-I（identity）覆盖一对多、失败 turn、SDK retry、Responses continuation 和并发；M1-T（transport）的 HTTP 200/409 与原子存储仍待真实 reporter/mock，不用测试态字典冒充。结论：未发现推翻 A-final 主路线的身份矛盾，下一阶段应回到整体 P0 的真实 session 重建正确性，而不是继续扩展 mock 细节。

## 1. 一对多：同一 A1 的两个工具

在 `test_tool_identity_persistence.py` 中，A1 同时返回 `lookup` 与真实 `write_file`，A2 返回最终文本。shutdown 后从 session/trajectory/mutation 重读：

- 两个 function_call 属于同一个 assistant message，共享 raw A1；
- 两个 T 不相同，各自有 success finished event；
- 只有 write_file 的 T 留下一个 mutation；
- 两条测试态 tool-detail 共享 UUID(A1)，funcId 分别为 UUID(T_lookup)/UUID(T_write)；
- 唯一 ai-code 使用 UUID(A1)/UUID(T_write)，不为只读 lookup 生成代码变更；
- tool/ai-code 的 requestId 都不等于最终 UUID(A2)。

该样本直接证明“一对多共享 requestId”与“funcId/reportId 必须按 T 区分”可以同时成立。

## 2. 失败 turn：不借上一轮 A

先执行成功文本 turn，再让当前 turn 的模型请求返回不可重试 400：

- 两轮实际 HTTP attempt 不同；
- 旧 turn selector 返回旧 raw A；
- 当前失败 turn selector 返回 None；
- 当前 turn 成功报告集合为空，不复用旧 A。

初稿使用 500 时两次等待 turn 30 秒超时；尝试无用户交互开关不改变结果。为隔离自动 retry/backoff，改用 400 后单项 `1 passed in 1.66s`，并删除无效交互开关。这里验证的是不可重试失败的 fail-closed，不宣称所有 5xx/断网/cancelled 终态已经统一。

## 3. SDK retry：失败 attempt 不形成成功记录

脚本依次为 429、A1 lookup tool_call 成功、A2 最终文本成功，profile 允许一次 SDK retry：

- 实际状态为 `[429, 200, 200]`；
- 三个 raw attempt 全部不同；
- 工具 message 关联第二个 raw A1，不是 429 的第一个值；
- 最终 selector 关联第三个 raw A2；
- 测试态原模型成功记录和独立 LLM 只包含 UUID(A1)/UUID(A2)。

这与上游 `test_request_tracking.py` 的 SDK retry×流式锚点一致。遥测报文重放是另一层语义，见第 6 节。

## 4. Responses continuation：retrieve A 才是成功身份

新增自包含 `test_request_identity.py`，使用当前 0.35.2 的 `ModelProfile`、`_build_profile_http_client`、`ResponsesApiClient`、`ExchangeTrace` 和真实 OpenAI SDK：

1. POST create 返回 `in_progress`，保存 raw A_create；
2. 取得 continuation token；
3. GET retrieve 返回 `completed`，使用不同 raw A_retrieve；
4. 最终 ChatResponse 与 assistant message 均保存 A_retrieve，不是 A_create；
5. 测试态原模型成功记录与独立 LLM 均只使用 UUID(A_retrieve)。

初稿曾参考不适配当前源码的旧导入路径和 ModelProfile 字段，发生收集错误，行为测试未执行；以当前生产接口重写后两项协议实验 `2 passed in 2.15s`。本地最小 sink 是复制上游测试设施语义的定制实验资产，没有 import 上游 tests/support。

## 5. 并发与 redirect

两个 Chat Completions 调用共享真实 client/HTTP transport，使用不同 session、turn、exchange context 并发执行：

- 两个 raw attempt 不同；
- 每个 response/message 只携带本 scope 的 raw A；
- 测试态原模型与独立 LLM 的 requestId 一致；
- 两组 sessionId、spanId、requestId 分别不相等。

该证据覆盖客户端/目标 DTO 层，不覆盖尚未实现的全局 reporter。redirect 使用上游真实 profile HTTP client 的既有锚点：两并发 scope 各经历 307 hop，四个 attempt 全不同；本轮与定制实验共同复跑通过。

## 6. M1-T：200/409 与原子幂等仍待真实存储

当前没有 telemetry HTTP reporter、endpoint 或数据库，因此本轮不声称下列事项已验证：

| 契约 | 真正可接受的验证 |
|---|---|
| 独立 LLM requestId 单键 | 相同规范报文重放返回 200 且不新增；同键不同内容 409 |
| tool-detail `(requestId,funcId)` | 同组合重放不新增；同 requestId 不同 funcId 可共存；同键冲突 409 |
| ai-code `(requestId,reportId)` | 同组合重放不新增；同 requestId 不同 reportId 可共存；同键冲突 409 |
| 并发唯一 | 两个同时首次写入只能产生一个记录，不能依赖“先查后插”非原子序列 |
| 非法输入 | 400，不落半条记录，不触发后续 join |
| 孤儿/乱序 | 可保存、缺父不报错、原记录晚到后可 join |
| ACK 语义 | 200 仅证明该服务已接受/语义重放，不证明全局 join 或内网落库完成 |

简单内存 dict 的单元测试只能检查测试代码本身，不能证明真实存储的原子性或跨进程语义。上述矩阵留待 telemetry mock/reporter 实现阶段；按整体优先级，它不应阻塞下一项真实 session 重建调查。

## 7. 最终行为证据

```cmd
cd /d D:\Tech\Github\huawei\iCode\fork\iCode-fork && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run ruff check aixcoding/tests/telemetry && uv run ruff format --check aixcoding/tests/telemetry && uv run pytest aixcoding/tests/telemetry tests/service/llm/test_request_tracking.py -n0
```

结果：ruff 通过，3 files already formatted；收集 31 项，`31 passed in 7.30s`，退出 0。其中定制 ACP 方向 7、M0/M1 工具与 UUID 12、Responses/并发 2、上游 request tracking 10。

## 8. 下一阶段

按整体风险顺序，下一项是 P0-2 真实 session 重建正确性：正常多轮、一轮多模型/多工具、compaction/fork、save=False、trajectory gap 和 blob 缺失，重点统计记录数量、归属、去重与降级。真实 ACP server/桌面接线和 M1-T 存储契约分别保留，不冒充本轮完成。
