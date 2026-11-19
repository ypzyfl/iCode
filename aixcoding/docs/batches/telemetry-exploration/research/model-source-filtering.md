# 上报过滤：仅上报 catalog 下发模型的调用

> 需求来源：责任人 2026-11-18 提出。背景：659b56ef（catalog-custom-coexist-v2，PR #132，2026-11-17 合并）实现了后端同步模型与用户自定义模型共存；为减小服务器端压力，端侧需判断当前使用的模型是否为 catalog 下发模型——**下发模型（通过模型配置接口获得的配置）上报 telemetry，自定义模型不上报**。
>
> 状态：需求已登记；过滤钩子随批次1各 reporter 实施落地（见 `../plan.md` 待办）。本文为需求、分析与讨论结果记录，不构成实施授权。

## 1. 判断依据：`synced_from_server` 标记（已存在，零新增上游）

- 服务器 catalog 同步写的 `~/.chrys/models/<id>.yaml` 顶层必带 `synced_from_server: true`；用户自建文件无该 key（loader/`ModelProfile` 不感知标记，仅 `service/aixcoding/models/catalog.py` 读写——catalog-custom-coexist 批次落地）。
- 判断原语现成（`catalog.py`）：
  - `_probe_server_marker(path)` 三态探针：`True`=下发 / `False`=用户自建 / `None`=不可判定（编码检测与 loader 同源，异常兜底留 detail 日志）；
  - `_is_server_synced()`：已定义"不可判定 → 非下发"的 fail-closed 语义；
  - sync 后内存快照持有 server-owned id 集合（`_publish` 按 server_ids 过滤），可免读盘查询。

## 2. 模型信息获取（三层来源）

### 2.1 主源：trajectory exchange facts（调用时刻快照）

after_turn 联读 `model.exchange.started/finished` 事件 payload（上游 `service/analytics/turn_trace.py:506-511,559-563` 投影直接消费，M0/M1-I 实验已实证真实 engine 管线可得）：

| 事件 | 字段 |
|---|---|
| `model.exchange.started` | `model_profile_id`（UUID hex，=磁盘文件名 stem）、`agent_profile_id`、`provider`、`api_style`、`request_model`（配置的模型标识）、`stream`、配置指纹×2 |
| `model.exchange.finished` | `response_model`（服务端实际返回模型名，映射/别名场景与 request_model 可能不同）、`response_id`、`usage`、`retryable` |

会话中途换模型后，历史调用仍按当时 profile 记录（优于查"当前 active"）。

### 2.2 辅源：live 期 `ModelProfile` 对象（engine 内存）

`service/profiles/models/schema.py:27-62` 全量配置（id/name/provider/api_style/model_id/base_url/api_key/HTTP 调优/vision/stream 等）。**过滤逻辑不需要此层**；`api_key` 等敏感字段不得上报；trajectory facts 为有意精选子集，不含 base_url/api_key。

### 2.3 归属判断：标记探针 / 内存集合

```text
exchange facts 的 model_profile_id
  → ~/.chrys/models/<id>.yaml
  → synced_from_server 探针（或 live 期 server-owned id 集合）
  → True=下发；False/None/文件缺失=按自定义处理
```

## 3. 过滤设计要点（随批次1 reporter design 裁决采纳）

| 要点 | 结论/建议 |
|---|---|
| 过滤位置 | 各 reporter **出站边界**统一前置判断（独立 LLM/tool-detail/ai-code/ACP envelope/1001 共用同一定制 helper） |
| 粒度 | **per 关联模型调用**：独立 LLM 按该调用自身；tool/ai-code 按关联 A1；ACP 最终响应按 A2；1001 按首个成功主模型；同 session 中途换模型天然支持 |
| fail-closed | 探针 `False`/`None`、文件缺失、profile 无文件 → 一律按自定义跳过 + detail 日志（与 `_is_server_synced` 语义一致） |
| 时点语义 | 判断的是**判断时刻**（轮末/分析时）的归属，非调用时刻；profile id 稳定，标记仅在 catalog 同步覆盖同名 id 时变化（极罕见），按统计用途接受并留档 |
| 对已签认方案 | 纯增量上报前置条件，不影响身份/join/幂等/BR 契约结论；mock 可顺带覆盖过滤分支测试 |

## 4. 待批次1 design 裁决的实现细节

1. 同名 stem 的 `.yml`/`.yaml` 共存时（catalog 批次 B2 场景）探针路径的选择，及 registry 加载优先级核实；
2. 无对应文件的 profile（如内置默认 profile）按不可判定跳过的语义确认；
3. 探针结果按 profile id 缓存（避免逐条读盘）与缓存失效时机（catalog 同步后）。

## 5. 证据

- 标记/探针/分类实现：`src/chrys/service/aixcoding/models/catalog.py`（`_SYNCED_FROM_SERVER_KEY`、`_probe_server_marker`、`_is_server_synced`、`_server_owned_names`、`_load_custom_profiles`）；
- 共存批次：commit 18ac293f / merge 659b56ef（PR #132，2026-11-17），批次文档 `aixcoding/docs/batches/catalog-custom-coexist/`；
- exchange facts：`src/chrys/orchestration/engine/trajectory.py` `exchange_facts()` + `service/analytics/turn_trace.py` 投影字段；
- facts 可得性实验：`../experiments/m0-record-contract.md`、`../experiments/m1-identity-contract.md`（真实 engine A1→write_file→A2 管线）。
