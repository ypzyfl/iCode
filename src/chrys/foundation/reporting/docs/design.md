# Chrys 会话数据上报（TUI）——设计方案与实施计划

> 状态：第一阶段已落地（契约 schema、mock server、collector 骨架与测试）。
> 契约源头：AIxCoding 桌面端 `packages/contracts/src/chrys-telemetry-report.ts` 及
> 《Chrys-会话数据上报接口契约与MockServer方案》§2/§4。本仓库侧的单一事实源是
> `chrys.foundation.reporting.schemas`，两侧修改必须同步。

## 1. 背景与目标

iCode（Chrys）需要把会话中的工具调用与代码生成活动上报到 Chrys 会话数据后端
（`/csas/telemetry/api/v1/...`，共 4+1 个端点），与 AIxCoding 桌面端共用同一后端与
同一契约。本地开发与回归需要一个可控的接收端：完整落库原文、暴露校验失败第一现场、
可注入故障以验证发送端的失败与重试链路。

**目标**

- TUI（以及后续 headless/ACP，三端共享同一组装层）能以同一 collector 上报会话数据。
- 契约校验在发送端与本地接收端之间**单一事实源**，不允许两侧漂移。
- 上报永远不阻塞、不破坏用户可见路径（与 trajectory 记录同一铁律）。
- 本地 mock server 覆盖：原文落库、debug 查询/导出/清空、故障注入（6 种模式）。

**非目标（本阶段）**

- 不模拟真实后端的逐字段长度约束之外的语义（如业务去重、限流）。
- 不上报 OTel 遥测（那是 `foundation/observability/` 的 OTLP 链路，与本方案互不相干）。
- 不在本阶段接入引擎装配与设置面板（见 §6 阶段计划）。

## 2. 模块落位与分层

| 模块 | 角色 |
|---|---|
| `src/chrys/foundation/reporting/schemas.py` | 契约单一事实源：端点常量、请求体校验、响应包络判定、幂等头解析。纯 stdlib。 |
| `src/chrys/foundation/reporting/collector.py` | 发送端：订阅 Invocation 工具事件 → 投影为上报报文 → 后台异步发送。 |
| `scripts/telemetry_mock.py` | 本地接收端 mock（调试工具，不随产品分发）：stdlib `http.server` + `sqlite3`，导入 schemas 做同一份校验。 |
| `tests/foundation/reporting/` | 三层测试：schema 单测、mock 集成、collector 端到端（真 EventBus → 真 mock）。 |

分层约束：`reporting` 位于 foundation（tier 0），只依赖 stdlib、httpx（核心依赖）与
foundation 内部模块（`events`、`util.httpx_helpers`），满足 `foundation → {}` 的
DAG 边界。未来引擎装配（orchestration）引用它属于合法的 `orchestration → foundation`。

## 3. 契约（schemas.py）

校验策略按**接收端语义**（与 zod 原版一致）：

- 必填集最小化：只拒绝对定位/统计核心的破坏（如 `tool-detail/save` 的
  `productName/funcType/funcName`、`update` 的 `funcId/codeStatus`、`ai-code/save`
  的 `reportId/sourceType`）。
- 类型错误一律非法（`bool` 不被接受为整数——Python 特有的坑）。
- 未知字段不拒绝（`.passthrough()` 语义）。
- 校验返回首个问题的 `"{code} at {field}: {message}"` 描述，便于 mock 直接回 400 与
  观察。

**双响应包络**（`report_is_accepted`）：

- `ai-code/save`：`{"code": 200, "message", "data"}`；
- 其余接口：`{"success": true, "code": 200, "timestamp", "result", "e"}`。
- HTTP 200 但业务失败（`success=false` / `code!=200`）是**确定答复**：collector 不重试。

**幂等语义**（契约 §4.3，mock 端已实现，collector 端待接入）：

| 端点 | 幂等键 | 重复到达行为 |
|---|---|---|
| `tool-detail/save` | `sessionId + funcId + X-Turn-Content-Hash + X-Analysis-Version` | 折叠（无版本头不折叠） |
| `tool-detail/batch-save` | `sessionId + spanId` | 覆盖（upsert） |
| `ai-code/save` | `reportId`（主键） | 折叠 |
| `tool-detail/update` | —（回写该 funcId 最新 save 行） | last-write-wins |

## 4. Mock server（scripts/telemetry_mock.py）

- 仅允许 loopback 绑定（127.0.0.1/::1，启动即拒绝其它地址）；默认端口 4321，
  `--port 0` 由内核分配（测试约定）。
- 请求体上限 8MB（413）；可选 `--require-token` 校验 `token` 头（401）。
- 落库：每接口一张表 + `rejected_reports`；`body_json` 保留完整原文（调试核心价值：
  核对"实际收到了什么"）。文件库通过 `ALTER TABLE` 幂等补列兼容演进。
- Debug 面：`GET /health`、`GET /`（零依赖自包含观察页：分表列表、关键列、展开原文、
  sessionId 过滤、2s 自动刷新、被拒报文红色标注）、`GET /debug/reports`、
  `GET /debug/dump`、`POST /debug/clear`、`POST /debug/faults`。
- 故障注入：`none/http500/http503/slow/envelope_reject/drop_body` × `rate`(0-1) ×
  `slowMs` × `interfaces` 过滤；`drop_body` 直接断连；伪随机以毫秒为种子（同毫秒同
  判定，便于测试断言）。与被移植实现一致：先落库、后返回故障响应。
- 可作为模块导入：`start_telemetry_mock(port=0, quiet=True) -> RunningTelemetryMock`
  （daemon 线程 + 幂等 `close()`），测试直接复用。

用法：

```bash
uv run python scripts/telemetry_mock.py --port 4321 --db /tmp/chrys-telemetry.db
```

## 5. Collector（foundation/reporting/collector.py）

**事件源**：EventBus 订阅 `InvocationToolCallStart` / `InvocationToolCallResult`
（精确类型匹配；`session_id` 与 `origin` 直接可用），按 `call_id` 配对
start→result。`origin.root.invocation_id` 作为 `requestId`（即用户可见的请求单位）。

**投影规则（当前覆盖 2/5 端点）**

| 事件 | 端点 | 关键映射 |
|---|---|---|
| `InvocationToolCallStart` | `tool-detail/save` | `funcName=tool_name`、`funcId=uuid4().hex`（按 call_id 记忆供 update 配对，上限 4096 后整体清空）、`value/fileName=代表性入参`（path/command/query 优先）、`codeStatus=0` |
| `InvocationToolCallResult` | `tool-detail/update` | `codeStatus=1/2`（成功/失败；失败以结果文本 `Error: ` 前缀判定——`tool_error` 契约，UI 与持久化同读）、`funcErrorMessage=结果文本截断 4096` |

**发送自检**：投影出的报文入队前先过 `validate_report_body`（单一事实源的另一半），
非法投影就地丢弃并留 warning——映射 bug 在第一现场被发现，而不是发给后端吃 400。

**失败语义**

- handler 只做同步 `put_nowait`（publish 内联 await handler，绝不等待网络）。
- 发送在专属后台 task；传输错误/非 200 按 `retry_delays_seconds`（默认 0.5s/2s）重试，
  耗尽丢弃；业务拒绝（200+success=false）不重试直接丢弃。
- 队列有界（默认 1000），溢出丢弃并计数——遥测的价值永远抵不过拖垮会话。
- `sent_count`/`dropped_count` 暴露给测试与诊断。

**HTTP 客户端**：惰性构造 `httpx.AsyncClient`（核心依赖，零新增包），`stop()` 时
aclose；可选 `bypass_proxy`（复用 `BYPASS_PROXY_MOUNTS`，对齐 MCP transport 约定）。

## 6. 阶段计划

**第一阶段（本次已交付）**

1. 契约 schema 模块（单一事实源）+ 单测。
2. mock server + 集成测试（含 token、幂等折叠/覆盖/回写、6 种故障、观察页）。
3. collector：事件订阅、save/update 投影、后台队列与发送、有限重试 + 端到端测试
   （真 EventBus → 真 mock，覆盖成功/错误结果/业务拒绝/重试后恢复/幂等启停）。

**第二阶段（待办，按序）**

1. **设置项与装配**：`foundation/config/settings.py` 新增
   `telemetry.report_enabled` / `telemetry.report_endpoint` / `telemetry.report_token`
   （group `telemetry`，`Apply.RESTART`，`ProjectMerge.DENY`——telemetry 不可被项目层
   设置；token 标 `Risk.DANGEROUS`）。注意：设置项需要 `msg()` 标签，必须走完整 i18n
   流水线（extract → update → 翻译 zh-Hans → compile → check），并同步
   `tests/foundation/i18n/_catalog_oracle_ids.py` 与计数断言。
2. **引擎装配**：在 `orchestration/engine` 的会话绑定处（参照 TrajectoryRecorder 的
   bind_session/close 位置）按设置构造 collector 并 `start(bus)`，shutdown 时
   `stop()`；TUI/headless/ACP 三端因此一次覆盖。新增 async wait 需运行
   `uv run python -m tests.support.trajectory_wait_inventory`。
3. **batch-save 投影**：用户输入触发（turn 开始，`opens_turn`），幂等键
   `sessionId + spanId`。
4. **ai-code/save 投影**：需要 `service/mutations` 的文件快照（added/deleted 行数用
   `difflib.SequenceMatcher` 手算，参照 `app/tui/widgets/chat/renderers/file_edit.py`
   的现成范式）；注意分层——mutations 在 service 层，投影逻辑需要以回调/参数注入的
   方式从 orchestration 装配层喂给 foundation 的 collector，不能反向 import。
5. **幂等头接入**：`X-Turn-Content-Hash` 需要 turn 内容指纹（复用 trajectory 的
   `fingerprint` 域思路），`X-Analysis-Version` 递增策略需与后端定稿。
6. **funcType/codeStatus 枚举对齐**：当前 `func_type=0` 占位、codeStatus 0/1/2 为
   保守约定，需与 Chrys 后端枚举表对齐后改为按 `tool_kind` 映射。

## 7. 测试与验证

```bash
# mock server 手工联调
uv run python scripts/telemetry_mock.py            # 终端摘要
open http://127.0.0.1:4321/                        # 观察页

# 指向 mock（第二阶段设置项落地后）
CHRYS_TELEMETRY_REPORT_ENDPOINT=http://127.0.0.1:4321 uv run icode

# 回归
uv run pytest tests/foundation/reporting/ -n 0
uv run python scripts/chrys_test.py --smart --paths \
  src/chrys/foundation/reporting scripts/telemetry_mock.py tests/foundation/reporting
```

测试约定遵守：mock 绑定端口 0；loopback 出网不触发 integration mark；HTTP 测试带
`direct_route`（绕过环境/系统代理）；等待一律 `wait_for`（同步谓词），无固定 sleep。

## 8. 安全与隐私

- mock 仅 loopback；不落任何凭证；`--db` 指定的落库文件只含上报原文。
- collector 的 endpoint/token 只来自设置层（settings/env），永不来自会话内容；
  项目层 `.chrys/settings.yaml` 默认 DENY，防止仓库内配置静默上报。
- `ai-code/save` 上报代码内容——第二阶段落地前必须复核是否需要额外的开关
  （类比 `otel_sensitive_data` 的 `Risk.DANGEROUS` 门控），默认关闭上报。
- 上报失败只降级（丢弃+计数+日志），永不影响 turn 执行。

## 9. 开放问题

1. `funcType` 枚举表：后端侧数值语义（桌面端样例中 3=read_file、0=java_code_review）
   需要一份权威对照，当前以配置占位。
2. `codeStatus` 枚举（0/1/2 之外是否有中断/超时等状态）。
3. `X-Turn-Content-Hash` 的哈希输入范围（整 turn 内容 or 工具调用序列）需与后端确认。
4. 与 AIxCoding 仓库的契约同步机制：两侧 schema 应保持逐字段一致，建议任一侧修改
   契约时在两侧仓库同步提交并互相引用。
5. sub-agent / workflow_node 的调用是否上报（当前 collector 不过滤 `origin.kind`，
   全量上报；若后端只要主 turn 需在投影层加过滤）。
