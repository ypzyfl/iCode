# 批次1 test-plan：telemetry-after-turn-slice

> 状态：随实现同步成文（2026-11-23）；矩阵行均为已实际执行的测试（结果见 verification.md 对应节）。

## 1. 测试矩阵

| 层 | 文件 | 覆盖点 | 结果 |
|---|---|---|---|
| 判别实验（前置） | `tests/telemetry/test_precondition_probe.py` | V1-a 两轮追加读取；V1-b 破坏性改写（transcript 重写+events 残留、exchange 归属防串接）；V2 通知合并（同 pass/新 pass/三元组键/会话隔离）；V3 Phase 4 真实压缩（transcript 允许不完整、A-final 从 trajectory 可恢复、折叠轮不重报） | 5 passed |
| owner/notice 单元 | `tests/telemetry/test_owner_notice.py` | 入队+flush 排空；同 pass 合并/新 pass 不吞；saved=False 跳过；会话隔离+close 幂等；删除后重建 worker；dispatch 异常隔离 | 6 passed |
| mock 1B 契约 | `tests/mock/test_telemetry_server.py` | 三 save 幂等三态（重放 200/键冲突 409/非法 400）；组合键（同 requestId 异 funcId 不冲突）；allowlist 严格（未知字段/缺字段/坏 hex）；join 聚合；组合层捕获（chat 带 attempt → modelRecord 原值）；无 telemetry 组合 404 | 7 passed |
| mock 1A 契约 | `tests/mock/test_mock_launcher.py` | 默认组合（含 telemetry）；--only 子集/互斥/unknown；同端口三路由应答 round-trip；独立 auth round-trip | 6 passed |
| 管线端到端 | `tests/telemetry/test_pipeline_delivery.py` | 脚本 wire 全链（llm×2/tool funcId=T/ai-code 降级）；过滤跳过分支；**真流量闭环**（modelRecord=llmReport=A-final 同原值） | 3 passed |
| 边界矩阵 | `tests/telemetry/test_pipeline_delivery.py`（边界节） | 无 hooks 不妨碍（+A1≠A2 显式）；save=False（saved 局部传递→dispatch 跳过→不读旧文件）；无 state_store（NO_SESSION_DIR 形态：session_dir 全局回退、saved=False 兜底跳过、全局目录零 telemetry 残留） | 3 passed |
| 上游回归 | `tests/orchestration/engine`（+kernel/profiles） | R2 四文件+配置三文件零回归 | 1401/1675/560 passed |

## 2. flush 与生命周期

- flush 排空/幂等/重建：owner 单测（6 项内）+ V2 probe；
- 真实 teardown flush：所有端到端测试的 `engine.shutdown()` 均经过 `_teardown` 集成路径（R2-4）。

## 3. 本批明确不覆盖（留批次2/3）

- ACP/1001/桌面输入捕获（批次2）；M1-T 全字段 parity、compaction 完整矩阵、slash/local child/hosted 保留场景、BR-9/10 矩阵、长会话/背压（批次3）；
- ai-code blocks 内容形态（本批为内容引用 `{kind: content-ref, sha256}`——逐字段细化在批次3 parity 前复核 B8 契约后定）；
- 真实后台联调（独立内网门禁，mock 通过不宣称现网通过）；
- trajectory disabled 的 `LEASE_HELD` 途径（本批采用 `NO_SESSION_DIR` 形态覆盖；LEASE_HELD 需双开进程，收益与成本留 test-plan 复审）。

## 4. 内网环境事实（责任人 2026-11-23 提供，联调前置规划依据）

- **无代理**：内网到后端**直连可达**——client 的强制直连（空 ProxyHandler）即最终策略，无需代理支持；
- **纯 HTTP**：无 HTTPS/TLS/自签证书——无需证书信任链预案；
- **超时**：内网不做专门超时验证——现有 5s 客户端超时仅作兜底，非联调验证项。

依据以上事实，"环境预演"档（代理穿透/HTTPS/超时注入）整体不做；"契约贴真"档（后台确认单回复后的差异化 mock、认证预埋）暂缓。当前推进项=第一档自方脆弱性测试（故障注入/容错/重试评估/unicode/并发，见 verification 后续记录）。

## 5. 第一档自方脆弱性测试（2026-11-23 已实施）

| 覆盖点 | 文件 | 结果 |
|---|---|---|
| mock 故障旋钮（ok/slow/error/rate_limit/flaky + `_test/fault` 控制） | `mock/telemetry/server.py` | 契约内 |
| client 单次退避重试（临时性失败 0.5s 重试一次；4xx/409 不重试） | `service/aixcoding/telemetry/client.py` | 契约内 |
| flaky 503 重试穿越 / 恒 500 恰一次重试 / 429 重试路径 / 409 不重试（attempts 计数断言） | `tests/mock/test_telemetry_fault_tolerance.py` | 4 passed |
| 中文路径/超大 blocks 往返 | 同上 | 1 passed |
| fault 控制端点校验 | 同上 | 1 passed |
| owner 3 session×5 pass 并发（FIFO/排空/无串扰） | 同上 | 1 passed |
