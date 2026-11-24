# 批次1 verification：telemetry-after-turn-slice

> 记录规则（沿用探索批次惯例）：每轮实际执行的命令与输出摘要按时间顺序追加，历史记录不删改；门禁结果以实际执行为准。

## 2026-11-20 开工前提达成与 V1–V3 判别实验

### 前提达成

- requirements 确认（2026-11-20）；mock design 单端口修订 + DIRECTORY 调整签认（统一端口 15678；产品端配置三项改默认+一项新增随本批 R2；含三轮 review 修复：三项改默认精确表述、本机/默认动态区边界标注、DIRECTORY 过渡状态）；design.md 签认（责任人周彬，2026-11-20，"无特别意见"——即 R2 批准 §2 七文件 + D1 §5 清单）。
- CI 前提：两 workflow PR 触发已含长期根分支（长期分支 commit `a9e79024`）。

### V1–V3 判别实验（design §4；新增 `aixcoding/tests/telemetry/test_precondition_probe.py`，真实 engine 落盘文件验证）

命令：

```cmd
cd /d D:\Tech\Github\huawei\iCode\fork\iCode-fork && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run ruff check aixcoding/tests/telemetry/test_precondition_probe.py && uv run pytest aixcoding/tests/telemetry/test_precondition_probe.py -n0 -q
```

结果：**5 passed**（V1×2、V2×2、V3×1）；全目录 `35 passed`；ruff check/format 通过。

| 实验 | 结论 |
|---|---|
| V1-a 两轮追加读取 | expected-turn 读取仅返回目标轮 A/E/工具事实；later-turn 记录显式入 skipped 清单——F1"记录级一致、追加读取正确"成立 |
| V1-b 破坏性改写（rollback） | 实证语义：UserRollback=**同 session 内 transcript 重写**（旧消息移除、turn 计数重置），events.jsonl append-only 残留旧 tool 事件；turn 编号撞车不可作过滤键，防串接必须按 **exchange 归属**过滤（tool 事件 parent ∈ expected turn attempts）——成立，且为产品 reader 硬设计输入 |
| V2 通知契约 | 同 pass 重复合并、新 pass 不吞、late duplicate 不重排、逻辑轮级视图（1001 预留）；probe 初版漏 session 维度被会话隔离测试当场抓出——三元组键 `(session_id, logical_turn_id, pass_id)` 不可简化 |
| V3 当前轮压缩（Phase 4） | 真实触发（小窗口+大 usage；LAST_WORDS 侧调用经脚本 wire 以合规 note 走通）；**transcript 层允许不完整**（当前轮 assistant 内容被折叠，session-only 恢复不足——F3 发现）；**A-final 从 trajectory 可恢复**（最后成功 exchange 的 request_attempt_id == 最后主请求 attempt header）；折叠/旧轮工具事件按归属过滤不重报 |

### 对实施的影响（产品 reader/dispatcher 设计输入）

1. reader 过滤键必须用 exchange/操作 ID 归属，禁用 turn 编号（V1-b 实证撞车）；
2. Phase 4 后 session-only 不足，reader 的 A-final 恢复必须含 trajectory exchange facts 通路（V3）；
3. dispatcher 合并键三元组含 session 维度（V2 实证必要）；
4. V3 的 wire LAST_WORDS 路由（格式契约 "## Task/## Progress/## Next" + ≥300 实质字符）可复用于切片测试。

按 requirements §5.5：V1/V2 通过（实现继续前提达成）；V3 结论=reader 压缩处理集须含 trajectory 补全（完整矩阵留批次3）。下一步为 design §8 第 2 步（上游 R2-1~4 + 定制 notice/dispatcher/owner）。

本轮未修改任何上游/产品代码（实验文件为 aixcoding/tests/ 新增）；未执行 Git 写操作（工作分支待 PR 提交）。

## 2026-11-21 design §8 第 2 步：上游 R2-1~4 + 定制 notice/dispatcher/owner

按已签认 design（R2 批准）实施四文件上游接缝与定制包：

- **R2-1** `turn_state.py`：`RunTurnIdentity` frozen dataclass + `TurnRuntimeState.current_run_identity` 字段 + `reset_after_session_shutdown` 清理（marker ×2）；
- **R2-2** `runner.py`：`pre_run()` 清旧快照 + `_record_trajectory_turn_started()` 在 ID 确定后、recorder await 前一次性写入（marker ×2，运行时 import RunTurnIdentity）；
- **R2-3** `finalizer.py`：`_save_and_drain_hooks()` 增加 `interrupted` 形参（调用点传入）；save/checkpoint 后、外部 hooks 前构造 `TurnTelemetryNotice` 并 lazy dispatch；status 保持 failed 优先 interrupted（`interrupted` 形参与 `status` 字段已于 F1 二次裁决回退/移除，见下文"F1 二次裁决"与"提交前复查"节——补审 nit 2026-11-23 补注）；
- **R2-4** `session_lifecycle.py`：`_teardown()`（usage settle 后）与 `_delete_session_reporting()`（trajectory close/detach 前）接入有界 flush（5s）+ 幂等 close；
- **定制包** `src/chrys/service/aixcoding/telemetry/`（notice.py：不可变通知 + dispatch 入口；owner.py：进程级 owner——per-session queue/worker、三元组合并、有界 flush、幂等 close、删除后重建；tier 落位按 D1 从 design §3.1 暂定收敛为 service 层单包，orchestration 层免建）；
- **登记表**：design.md「定制点登记预告」4 行（语义 id `telemetry-after-turn-slice:*`，marker 计 7）。

**首轮上游回归发现并修复**：lazy import 未隔离——上游测试进程无 `aixcoding` 包路径，`identity is not None` 分支的 `ModuleNotFoundError` 逃逸致 27 个上游 engine 测试失败；修复为三处接缝的 import+调用整体 try 隔离（"telemetry 永不改变 turn 结果"总原则覆盖 import 失败场景）。

验证（全部实际执行）：

```cmd
uv run pytest aixcoding/tests/telemetry -n0 -q                    → 41 passed（新增 owner/notice 单测 6 项）
uv run pytest tests/orchestration/engine -n4 -q                   → 1401 passed, 13 skipped（修复后零失败）
uv run python aixcoding/tools/gen_customizations.py --strict      → OK（110 rows / 161 markers / 21 designs / 0 warnings）
uv run python aixcoding/tools/check_docs.py                       → OK（27 ADR / 50 design / 48 self-review）
uv run ruff format --check（4 上游文件 + 定制包 + 批次文档）        → already formatted
git diff --check                                                   → 无输出
```

下一步：design §8 第 3 步（mock 1A 单端口组合改造 + 既有契约测试回归）。

## 2026-11-21 design §8 第 3 步：mock 1A 单端口组合

- **新增 `aixcoding/mock/combined.py`**（组合层）：`CombinedMockServer` 继承 `CatalogMockServer`（获得 Windows SO_EXCLUSIVEADDRUSE bind 防护与 catalog state 属性）+ auth/update state；`build_single_port_handler` 推广 catalog 内嵌 auth 的组合先例——update 拥有 `/api/v2/**` 路由，其余归 catalog(±auth) handler；`start_combined(port=0)` 支持 OS 随机端口（测试）。
- **重写 `__main__.py` 为单端口 launcher**：默认组合 =model_catalog(含 auth)+update 共 :15678；`--port`（默认 15678，fail-fast 保留）；`--list` 列子服务/端口/路由（实测 smoke 通过）；`--only` 子集语义（auth 独立形态保留、与 model_catalog 互斥沿用）；旧多端口组合退役。
- **各子包独立 factory/CLI 未动**（DIRECTORY §6 承诺：底层测试与调试形态保留）。
- **契约测试重写 `test_mock_launcher.py`**：新增"同端口三路由应答"组合 round-trip（auth `/device/verify` + catalog 门控 401 + update `/api/v2/releases/check` 400 均为活信号，port=0）；独立 auth round-trip 保留；选择解析四项断言更新。
- **README 注册表更新**：单端口决策注记 + 端口表（组合 15678/独立默认原值）+ launcher 用法 + 逃生门 + 新增 mock 步骤引用（`_REGISTRY`/combined）。

验证（全部实际执行）：

```cmd
uv run pytest aixcoding/tests/mock -n0 -q                              → 87 passed, 2 skipped
uv run pytest aixcoding/tests/mock aixcoding/tests/telemetry -n0 -q    → 128 passed, 2 skipped
uv run python -m aixcoding.mock --list                                 → 单端口表单输出正常
uv run ruff format --check aixcoding/mock/ aixcoding/tests/mock/       → 21 files
uv run python aixcoding/tools/check_docs.py                            → OK
uv run python aixcoding/tools/gen_customizations.py --strict           → OK（110/161/0 warning）
git diff --check                                                       → 无输出
```

本轮改动全部位于 `aixcoding/`（mock 为开发资产，无上游/产品代码；免 marker）。下一步：design §8 第 4 步（reader/analyzer/过滤/reporter×3/client + mock 1B telemetry 存储 + 契约测试）。

## 2026-11-21 design §8 第 4 步（前半）：mock 1B telemetry 存储

- **新增 `aixcoding/mock/telemetry/`**（server.py）：三 save 端点（llm-report 单键 / tool-detail `(requestId,funcId)` / ai-code `(requestId,reportId)`）+ `_test/join` 关联查询 + 严格 allowlist（未知字段/缺字段/非 32hex 一律 400，`providerCallId` 等被拒字段天然挡在门外）；幂等语义=同键同内容重放 200 不新增、同键不同内容 409；ID 全程原值 32hex。独立 factory（port=0）保留。
- **catalog chat 捕获钩子**：`_serve_llm_chat` 末尾经 `server.telemetry_capture` 属性回调记录每请求自身 `Chrys-Request-Attempt-Id`（BR-1：不做成功判定、不聚合）；独立 catalog factory 无回调零影响。
- **组合层挂载**：`combined.py` 三路分发（update `/api/v2/` → telemetry `/csas/telemetry/` → catalog 其余）+ `with_telemetry` 参数（默认 True）+ 钩子注入；launcher `_REGISTRY/_COMBO_MEMBERS` 注册 telemetry（默认组合三成员）。
- **文档同步**：README telemetry 行（已迁入+路由前缀+独立端口）；DIRECTORY §6 过渡注记更新为"单端口已落地"。

契约测试（新增 `test_telemetry_server.py` 7 项 + launcher 断言更新）：save 三态（重放 200/键冲突 409/非法 400 含未知字段拒绝）、组合键幂等（同 requestId 不同 funcId 不冲突）、join 聚合四类、组合层端到端（chat 带 attempt header → join 的 modelRecord.requestId=原值 + llmReport 闭环）、无 telemetry 组合 404。首轮 4 失败修复：2 处为 telemetry 注册后的旧断言（默认组合/unknown 名），2 处为测试构造错误（每次随机 sessionId 导致"重放"payload 实为不同内容——409 恰证明冲突检测正确，改为同对象重放）。

验证（全部实际执行）：

```cmd
uv run pytest aixcoding/tests/mock -n0 -q                        → 94 passed, 2 skipped
uv run ruff check aixcoding/mock/ aixcoding/tests/mock/           → All checks passed
uv run ruff format --check aixcoding/mock/ aixcoding/tests/mock/  → 24 files formatted
```

剩余（第 4 步后半）：产品侧管线——reader（V1-V3 结论产品化）/analyzer/DTO/模型来源过滤/三类 reporter/client + owner worker 接线 + 管线测试。

## 2026-11-21 design §8 第 4 步（后半）：产品侧管线端到端

定制包新增六模块（`src/chrys/service/aixcoding/telemetry/`）：

- **dto.py**：三类 DTO 构造（字段集与 mock 1B allowlist 逐一对齐；无三时间字段/providerCallId/普通独立 turn 的 parentSpanId）；
- **reader.py**：expected-turn 读取——复用 `analytics/turn_trace.py` 只读投影（探索 N4 背书）取 logical turn→pass→model calls（成功 call 的**末位 attempt=A-final**，M1 证据）；tools 按 events 的 pass 归属（`event.turn_id==pass_id`，V2：前序 pass 不重报）；`model_profile_id` 从 exchange started facts 提取（过滤键=profile 文件名，非 model id——调试实证纠正）；V1-b 的 exchange 归属防串接内建于按 pass/attempt 的提取本身；
- **filtering.py**：catalog `synced_from_server` 探针（`.yaml` 优先；无文件=不可判定=整批跳过，fail-closed）；
- **client.py**：stdlib urllib 直连（空 ProxyHandler），`AIXCODING_TELEMETRY_BASE_URL` 覆盖（默认 mock :15678）；
- **analyzer.py**：facts+session 文件→三组 DTO（fail-closed：缺函数名/无 ledger→跳过+清单；落盘 function_call 为**扁平结构** `name` 直键——实证纠正，非线上嵌套形态）；ai-code 读 `state.chrys_mutations`（blocks 为内容引用形态，逐字段细化留批次3 前复核）；
- **reporter.py**：LLM→tool→ai-code 顺序投递，单条失败不中断（服务端幂等重放容错）；
- **owner.py 接线**：`_process_notice` 从占位换真实管线（`asyncio.to_thread`，文件读+网络不占事件循环）。

端到端测试（`test_pipeline_delivery.py` 2 项）：真实 engine 一轮（A1 工具→A2 文本）→ 真实 finalizer 通知 → 管线 → 单端口 mock，join 断言：A1/A2 两份 llmReport（requestId=attempt 原值、spanId=logical turn）、toolDetails（funcId=T ∈ events 工具 op、funcName=lookup）、aiCodes 空（lookup 无 mutation=降级不虚构）；反向分支：profile 无 marker → 整批跳过（join 空）。调试三轮实证修正：①过滤键 model id→profile id；②analyzer 直读顶层 messages→state.messages（envelope 结构）；③function.name→扁平 name 键。

验证（全部实际执行）：

```cmd
uv run pytest aixcoding/tests/telemetry -n0 -q    → 43 passed（含端到端 2 项）
uv run pytest aixcoding/tests/mock -n0 -q         → 94 passed, 2 skipped
uv run pytest tests/orchestration/engine -n4 -q   → 1401 passed, 13 skipped（owner 接线后零回归）
uv run ruff format --check aixcoding/ src/chrys/… → 534 files
uv run python aixcoding/tools/gen_customizations.py --strict → OK（110/161/0 warning）
uv run python aixcoding/tools/check_docs.py       → OK
git diff --check                                   → 无输出
```

design §8 第 4 步完成。下一步：第 5 步（产品端配置 R2-5~7 统一 15678 + 全 mock 真流量端到端切片）。

## 2026-11-23 design §8 第 5 步：产品端配置统一 + 全 mock 真流量切片

- **R2-5** `environments.py`：LOCAL 两 origin → `localhost:15678`（docstring 端口表同步为单端口组合）；
- **R2-6** `update/client.py`：`_TIER_BASES["local"]` → `127.0.0.1:15678`（注释同步，dev/prod 不动）；
- **R2-7** `models/catalog.py`：`_CATALOG_BASES["local"]` → `127.0.0.1:15678`。
- **实施核正（登记机制）**：三文件均位于 `src/chrys/{tier}/aixcoding/` 定制层（ADR-0011）=custom 侧，**改动经 R2 批准生效但免 marker、不入登记表**（gen_customizations 只对 upstream 侧对账；首轮误登记 3 行产生 orphan 错误已修正，design 登记表后加注）。
- **真流量切片测试**（`test_real_traffic_join_closes_through_mock`）：engine 模型流量真实打到组合 mock 的 `/v1/chat/completions`（profile base_url 指向 mock，无脚本 wire）→ 捕获钩子记录每请求 attempt → join 视图中 **modelRecord.requestId == llmReport.requestId == events A-final（同一原值）**——BR-1"独立报告 join 声明成功"的完整闭环实证。
- **回归**：首轮 4 失败为测试断言旧端口（auth environments ×3、update tier base ×1——均为本批有意变更），更新断言后全绿。

验证（全部实际执行）：

```cmd
uv run pytest aixcoding/tests -n4 -q                  → 886 passed, 56 skipped
uv run pytest tests/orchestration/engine -n4 -q       → 1401 passed, 13 skipped
uv run pytest tests/kernel -n4 -q                     → 1675 passed
uv run pytest tests/service/profiles -n4 -q           → 560 passed, 3 skipped
uv run python aixcoding/tools/gen_customizations.py --strict → OK（110/161/0 warning）
uv run ruff format --check（改动文件）                → already formatted
git diff --check                                      → 无输出
```

design §8 第 5 步完成。下一步：第 6 步（边界矩阵：无 hooks/save=False/trajectory disabled/A1≠A2/flush → test-plan 全量 → self-review 签认 → PR 回长期分支双 CI）。

## 2026-11-23 design §8 第 6 步：边界矩阵与六件套收口

边界矩阵（`test_pipeline_delivery.py` 边界节，3 项）：

- **无 hooks**：harness 本就无 hook_manager——断言显式化：无 hooks 时管线照常送达 + 工具轮 A1≠A2；
- **save=False**：真实语义核正——抑制的官方机制是 `SessionWriter.save_current_session` 返回 False（非 store 层 patch）；saved=False 经通知局部传递 → dispatch 跳过 → join 零记录（不读旧文件冒充）；
- **无 state_store（NO_SESSION_DIR 形态）**：真实语义核正——session_dir **回退全局目录（非 None）**，skip 由 saved=False 兜底保证；断言 owner 无 worker 入队、join 空、全局目录零 telemetry 残留。

六件套补全：test-plan.md（七层测试矩阵+留批次2/3 项声明）、self-review.md（签认头部+交付摘要+边界如实声明+评审记录——待责任人裁定评审轮次与签认）。

验证（实际执行）：telemetry **47 passed**（边界 3 项含）、mock **94 passed, 2 skipped**；check_docs OK（49 self-review，六件套计入）；ruff format 6 files；diff --check 干净。批次1 全部六步实施完成，停等：① 双 AI 评审轮次裁定；② self-review 签认；③ Git 授权（add→commit→push→PR 回 `feat/telemetry-exploration`，双 CI 首验）。

## 2026-11-23 独立评审轮与 findings 处置

独立评审 AI 轮（另一 AI，模型标识未提供，报告由责任人转交；SELF-REVIEW-HOWTO §二三阶段模板）：**无 blocker**；方向/四项关键决策/实现保真（A-final、V1-b 双层防串接、BR-1 语义、import 反向验证）均获认可；流程合规五项全过。Findings 处置：

- **F1（suggestion，待裁决）**：`TurnTelemetryNotice.status` 本批零消费（llm-report 只报成功 A-final，eventSubType 恒 success）。已按"预留批次2"处置：notice.py 加注释标注预留语义与移除条件；**责任人可改判"本批体现"**（例如 failed turn 记 detail 日志），改判即改。
- **F2（nit，已修）**：turn_state/runner 4 处 marker 注释的归属路径统一为实际落位 `service/aixcoding/telemetry`（锚前缀不变，对账不受影响——实测 gen_customizations OK）。
- **F3（nit，已修）**：owner docstring 从"step-2 占位"更新为"管线已接线"现状。
- **F4（nit，已修）**：`_pending` 键生命周期注释（=session 生命周期，无高水位 by design）+ reporter 类型标注补全。

门禁复核：ruff check/format 通过；gen_customizations --strict OK（110/161/0 warning）；check_docs OK；`pytest aixcoding/tests/telemetry aixcoding/tests/mock` **141 passed, 2 skipped**；diff --check 干净。评审记录已落盘 self-review.md（双 AI 评审轮次齐备，具备签认条件）。

**F1 裁决（责任人，2026-11-23）：A——`notice.status` 预留批次2**（1001/turn 级记录载体；notice.py 预留注释即最终语义，本批零行为变更；批次2 design 复核消费形态）。至此四条 findings 全部关闭，批次1 唯一剩余动作=责任人签认 self-review.md → Git 授权序列。

**F1 二次裁决（责任人，2026-11-23）：改判——`notice.status` 整体移除、记录在案**（0.28.0 基线无 turn 终态上报、需批次2 新建 1001 接口；新版本数据上报不需要）。处置：`finalizer.py` 回退 `interrupted` 参数与 `status` 字段、`notice.py` 删 `status` 字段并注释留档、`test_owner_notice.py`/`test_telemetry_fault_tolerance.py` 去掉 `status="ok"`。详见 self-review.md 评审记录。

## 2026-11-23 内网前置·第一档自方脆弱性测试（责任人裁决：第一档做；二/三档不做——内网无代理/纯 HTTP/超时不验证，环境事实已录 test-plan §4）

- **mock 故障旋钮**：`MockTelemetryFault`（ok/slow/error/rate_limit/flaky 五模式）+ `_test/fault` 控制端点（allowlist 校验 mode）；flaky 按幂等键计首 N 次失败——精确复现"后端瞬时故障后恢复"形态；`save_attempts` 计数供测试断言重试次数。
- **client 单次退避重试**（裁决①加）：`post_save` 对**临时性失败**（传输错误 status=0/超时/5xx/429）退避 0.5s 后重试一次；**4xx（含 409）不重试**（幂等使重试安全、同字节重发无法改变确定性否决——注释已内建）。
- **测试 7 项**（`test_telemetry_fault_tolerance.py`，真实 product client × mock 故障）：flaky 503 被单次重试穿越（attempts==2、join 落库）；恒 500 上浮且恰一次重试（==2）；429 走重试路径；409 不重试（==1）；中文路径/超大 blocks 往返一致；fault 控制端点非法 mode 400；owner 3 session×5 pass 并发（FIFO/排空/无串扰）。

验证：`pytest aixcoding/tests/mock aixcoding/tests/telemetry` **148 passed, 2 skipped**；上游 engine **1401 passed** 零回归；gen_customizations --strict OK；check_docs OK；format 34 files；diff --check 干净。

内网联调风险残留（如实）：后端路径/校验/认证差异（第三档，等确认单回复后贴真）；mock 通过≠后端通过的边界不变。批次1 交付面更新完毕，仍停等：责任人签认 self-review.md → Git 授权序列。

## 2026-11-23 提交前复查（self-review 签认后、Git 序列前）

复查发现并修复一处架构守卫缺口（评审验证范围未覆盖）：`tests/architecture/test_trajectory_wait_inventory.py::test_wait_manifest_matches_source` 失败——`session_lifecycle` 插入 telemetry flush 与新增 `telemetry/owner.py` 引入新 await 节点，`trajectory_wait_manifest.json` 未同步。

**修复**：`uv run python -m tests.support.trajectory_wait_inventory` 刷新（2915 waits，29 节点重开）后，`_teardown` 因插入 flush 导致 ordinal 漂移、17 个已审查节点被重置为 unresolved——逐一恢复原分类（side-question-background×2 / execution-state-notification×1 / session-transition-work×14），新 flush 调用点按先例（`fire_session_end_hooks` 调用点）归 session-transition-work；`owner.py` 4 节点与 `_delete_session_reporting` 新增 flush 保持 unresolved（先例：方法内部 await 默认 unresolved）。

**最终验证**：Smart Test `--paths` 四上游文件+manifest：**tests 16427 passed + architecture 644 passed，exit 0**；`test_trajectory_wait_inventory.py` 单独 57 passed；telemetry 测试 61 passed；ruff check --no-fix / format --check 全过；gen_customizations --strict OK（110 rows/161 markers/0 warning）。

**签认后改动补审（责任人裁决 2026-11-23：选项 B）**：上述架构修复与 F1 二次裁决的 status 回退均发生在独立评审轮与 self-review 签认之后，最终提交形态未经评审 AI 复核——补一轮轻量独立 AI 复审（范围：status 回退 diff + manifest 恢复；提示词由开发 AI 出具、责任人转交），收敛后进入 Git 授权序列。

**补审轮结论（独立评审 AI，2026-11-23）**：**无 blocker，可进入提交流程**。检查点 A-F 全过——A 回退完整性（`TurnTelemetryNotice` 构造点仅 3 处均无 status；`finalizer.py` diff 仅含 notice 块，签名/调用点无 `interrupted`；dto/analyzer 的 `code_status` 系 ai-code 既有字段非残留）；B 注释准确性（三要素+再引入条件齐备）；C 文档一致性；D 回退副作用（`failed`→`fire_after_turn` 正常、上游 `interrupted` 局部变量及既有用途零改动）；E manifest 分类恢复正确（`_teardown` 18 节点：side-question-background×2 + execution-state-notification×1 + session-transition-work×15 含新 flush；已审查节点 expression/primitive/wrapper_target 无改动）；F 归类先例合理（新 flush 与同方法 `settle`/`fire_session_end_hooks` 调用点一致；方法内部 await 默认 unresolved）。Findings 1 条 nit（R2-3 历史记录缺二次裁决交叉标注）**已补注处置**（见上文 R2-3 行）。评审方声明：与开发 AI 不同源、可能共盲、终裁在责任人；验证数字未重跑，基于 diff 与源码/文档静态核对。

## 2026-11-24 PR #144 CI 修复与门禁口径对齐

PR #144（base `feat/telemetry-exploration`）连续三轮暴露出本地复查口径与 CI 不一致。前两轮的 run 因后续推送被标记 cancelled，下表失败点取自责任人转贴的当轮日志。

| 轮次（head） | 失败点 | 根因 | 修复提交 |
|---|---|---|---|
| Run #183 / #266（`847e69a2`） | 定制侧 ty（linux × `$CUSTOM_SRC`） | `reader.py` 把 `TrajectoryEvent.operation_id`（`str \| None`）直接当 `str` 用作 dict key 与 `ToolFact.tool_op_id` | `e2bfc91a`：两处循环取局部变量收窄 |
| Run #184 / #267（`e2bfc91a`） | `check_r2_diff` 报 4 个上游文件未授权 | design.md R2 表标题非标准名（`## 2. 上游 R2 接缝…`）、路径缺 `src/chrys/` 前缀，门禁解析器未识别 | `6f773c84`：标题改 `## 上游改动清单（R2）`、R2-1~7 路径补前缀 |
| Run #185 / #268（`6f773c84`） | 上游 CI 三个 core 分片的 ty 步骤（测试步骤均通过；AIxCoding Tests 已绿） | `SessionResources.session_id` 类型为 `str \| None`（删除当前会话后引擎 detached 时为 None——此前写作「首次落盘前」，有误，见下文「测试覆盖」），`finalizer.py` / `session_lifecycle.py` 三处直接传给要求 `str` 的定制 API | 本次：调用点加 None 守卫（见下） |

**本次修复（责任人 2026-11-24 确认动上游文件）**：

- `finalizer.py` `_save_and_drain_hooks()`：取局部 `session_id`，条件改为 `identity is not None and session_id is not None`，注释同步为「Missing snapshot or session id ⇒ skip」。相对 PR base +24 行（R2-3 区间 18–30）。
- `session_lifecycle.py` `_teardown()`：`try` 内取局部 `session_id`，`if session_id is not None` 包住 owner 获取与 flush/close（owner 获取移入守卫系采纳独立复审建议，见下）。相对 PR base +26 行；design.md R2-4 量级区间 12–24 → 12–26（责任人裁决），签认头部未动。
- `trajectory_wait_manifest.json`：`SessionLifecycle._teardown` 第 11 个 await 表达式同步为新写法——同一等待、同一位置的等价改写（属性访问改为同值局部变量），沿用 `session-transition-work`。
- 语义：`session_id` 为 None 即引擎已 detached（当前会话被删除；此前写作「会话尚未落盘」，有误，见下文「测试覆盖」）。该会话的 worker 已在删除流程中 flush 并 close，teardown 跳过不会遗留孤儿 worker。

**本地门禁口径订正**（读自 `.github/workflows/{ci,aixcoding-tests,aixcoding-upstream-ci}.yml`）：上游 ty 为 `ty check --error-on-warning src/chrys`（三个 core 分片各自平台），本地以显式 `--python-platform linux/darwin/win32` 等价复现；定制侧 ty 的 `$CUSTOM_SRC`（`src/chrys/*/aixcoding`）为其子集；R2/R3 的 `--base` 为 `git merge-base origin/main_iCode HEAD`（本批 `2fd777f6`），不是 PR base；`check_docs.py` 须带 `--closure`。

**本次验证**（全部按上述口径，工作区即待提交内容）：

| 项 | 结果 |
|---|---|
| ruff check --no-fix / format --check（两 workflow 路径并集） | All checks passed / 3244 files already formatted |
| ty 全量 `src/chrys` × linux / darwin / win32 | 三平台 All checks passed |
| compileall -q src | 通过 |
| check_docs --closure | OK（27 ADR / 50 design / 49 self-review） |
| check_import_boundaries | OK（1260 files） |
| gen_customizations --strict | OK（110 rows / 161 markers / 24 retired / 0 warning） |
| check_r2_diff --base 2fd777f6 | OK（upstream_changed=84 全部落入审批池） |
| check_r3_markers --base 2fd777f6 | OK（upstream_changed=84 / marker_checked=81 / exempt=3） |
| pytest aixcoding/tests（-m "not integration and not gc_calibration"） | 896 passed, 56 skipped |
| pytest tests/architecture -n 0 | 1247 passed, 3 skipped |
| Smart Test（--paths finalizer.py / session_lifecycle.py / design.md）产品测试选集 | 16312 passed, 139 skipped |

**本地未覆盖（如实）**：上游 CI 的全量测试分片（约 3.9 万用例分 12 shard）本地仅以 Smart Test 选集替代；Guard hooks、Install wheel 等 job 本次改动未触及、未重跑。产品测试选集在 manifest 表达式同步**之前**执行，之后只重跑了 architecture 全套（manifest 为测试数据，不被产品代码读取）。

**教训**：此前本地复查未按 workflow 实际命令执行——首轮未跑 ty 与 R2/R3 等治理门禁；修 ty 时只跑 linux 平台且范围限于 `telemetry/` 子目录，漏掉目录外的调用方；R2 的 base 误用 PR base；check_docs 漏 `--closure`。另曾误判「未新增 await 则 manifest 不受影响」——已登记 await 的表达式文本变更同样需要同步。还曾仅凭搜索 `flush_session` / `close_session` 的文本出现位置就断言 teardown 的 telemetry 分支没有测试经由 engine 覆盖，未读 `_run_turn`，经实读更正（见下文「测试覆盖」）。此后本地复查以 workflow 实际命令为准。

**独立复审（2026-11-24，独立评审 AI DeepSeek-V4-Pro，责任人转交、标识经其确认）**：对象为上述 ty 修复。结论 Good、无阻塞项；1 条可选建议（`session_lifecycle.py` 把 `get_telemetry_owner()` 移入 `session_id is not None` 守卫内，避免无 id 时无谓初始化惰性单例）已采纳——行数不变，manifest 表达式不变。

**design.md §2 两小表合并（责任人裁决 2026-11-24）**：R2 表标题改标准名（`6f773c84`）后，门禁解析器把原 2.2 小节第二张表的表头行误当作数据行，报 `R2 row names '文件' which is not a file in the repo — ignored`（无害、不阻塞，当轮漏报）。处置：原 2.1（R2-1~4）与原 2.2（R2-5~7）合并为 `## 上游改动清单（R2）` 下的一张表，R2-5~7 量级列记「—」（原设计未单列），文内 3 处小节引用同步，签认头部未动。

**复验（采纳建议与表合并之后，口径同上）**：ruff check / format 通过；ty 全量 `src/chrys` 三平台通过；compileall 通过；check_docs --closure、check_import_boundaries、gen_customizations --strict、check_r3_markers OK；check_r2_diff OK，且本批 design.md 的警告已消失（剩余 13 条均属历史批次）；pytest aixcoding/tests 896 passed, 56 skipped；直接引用 `_teardown` / `SessionLifecycle` 的两个上游测试文件 29 passed；pytest tests/architecture 1247 passed, 3 skipped。Smart Test 产品测试选集未重跑（责任人裁决不需要）：其后仅有的代码改动是把一行无 await 的单例获取移入守卫。

**测试覆盖（更正与补测）**：本节此前写「`_teardown` 的 telemetry 分支没有测试经由 engine 覆盖」，该断言有误——`test_pipeline_delivery.py` 的 `_run_turn` 在返回前调用 `engine.shutdown()`，6 个管线与边界测试实际都执行过 `_teardown` 的非 None 路径，只是没有断言其效果；当时仅凭搜索 `flush_session` / `close_session` 的文本出现位置就下了结论。真实缺口是：None 跳过路径没有任何测试执行，非 None 路径被执行但无断言。按责任人裁决在本 PR 补 `aixcoding/tests/telemetry/test_engine_teardown.py`（harness 镜像 `test_pipeline_delivery.py`，经真实 engine 入口）：

- `test_shutdown_flushes_then_closes_the_session_worker`：跑一轮后 `engine.shutdown()`，断言 teardown 先 flush 后 close（顺序与 session id 由包装 owner 方法的 spy 记录）、worker 被移除、该轮报告到达 mock。
- `test_shutdown_after_deleting_the_current_session_skips_telemetry`：跑一轮后经 `SessionDelete` 删除当前会话——`_delete_session_reporting` 先 flush+close 该会话 worker，再 `detach_for_delete()` 使 `session_id` 为 None——随后 `engine.shutdown()`，断言没有新增任何 owner 调用。此条同时覆盖了 R2-4 的删除流程一处。

**反证**（两次，第二次在最终版测试上）：临时去掉 `_teardown` 的 None 守卫后第二条失败（shutdown 多出 `('flush', None)`），恢复后通过；第一条不受守卫影响。实测另得两条事实：其一，`engine.start()` 即分配 `session_id`（`ActiveSession.begin()`），「启动后不发消息就关闭」不是 None 路径，None 路径的真实场景是删除当前会话之后的 shutdown；其二，`EventBus` 的订阅回调必须是 async（`bus.py` 直接 `await handler(event)`），同步回调会执行但留一条 handler failed 日志——新测试已用 async 回调。现有 harness 的 `bus.subscribe(Error, errors.append)` 是同步回调，按同一实现推断只在真的出现 Error 事件时会多一条这样的日志、不影响收集，属既有写法，本次未改。

**test-plan 同步**：test-plan.md 追加 §6 登记上述两条；其 §2 原已写明端到端测试的 `engine.shutdown()` 均经过 `_teardown` 集成路径，与上述更正一致。

**补测后复验**（代码与测试定稿后、本段写入前，口径同上）：ruff check / format 通过（3245 files）；ty 全量 `src/chrys` 三平台通过；compileall 通过；check_docs --closure OK（27 / 50 / 49）；check_import_boundaries OK（1261 files）；gen_customizations --strict OK（110 / 161 / 24 / 0）；check_r2_diff OK（changed=702，upstream_changed=84，本批无警告）；check_r3_markers OK（84 / 81 / 3）；pytest aixcoding/tests **898 passed, 56 skipped**（含新增 2 条）；直接引用 `_teardown` / `SessionLifecycle` 的两个上游测试文件 29 passed；pytest tests/architecture 1247 passed, 3 skipped。两个上游文件相对 PR base 仍为 +24 / +26。
