# 设计：后端同步模型与自定义模型共存

<!--
签认规则（R10 · 决策档）：责任人本人编辑本头部（状态→已确认、填责任人与日期，
确认意见可选），AI 不得代填。签认后修改正文需重新签认（R2 类正文修正除外，
须在正文原位加注记并标注不触发重签）。
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-16
- 确认意见：（可选）
- 开发 AI：CodeBuddy / Tencent Hunyuan Hy
- 评审 AI：（待责任人指定，须与主力开发 AI 不同源）

## 方案概述

标记只存在于模型 YAML 顶层，只在同步逻辑读写；loader 用它自己的
`read_profile_mapping()` 逐字段构造 `ModelProfile`（`loader.py:245-267`），
未知键被忽略，因此**不需要改 schema / loader**。

```
apply_catalog(catalog):
  ├─ 阶段一：读 previous（只读 .catalog-state.json，不用于来源判定）
  ├─ 扫描目录 *.yaml / *.yml → 逐文件读标记 synced_from_server
  │    ├─ true  → 后端管理（本次可删候选）
  │    └─ 无/假 → 自定义（保留；若 id 与后端冲突 → 记入 conflicts）
  ├─ 计算 final_names = 本次后端 id 对应的文件名
  ├─ 删除：对每个候选，仅当「有标记 且 文件名不在 final_names」→ unlink
  ├─ 写入：本次后端模型 → <id>.yaml.tmp → os.replace（每个带标记字段）
  ├─ 发布：install_snapshot(后端项 + 保留的自定义项)   ← 一次原子内存替换
  ├─ 写 state：write_catalog_state()（profile_ids 仍只含后端 id，语义不变）
  └─ 冲突告警：detail 日志记录被覆盖 id 与原因（仅日志，不做 TUI 提示）
```

## 冻结的标记契约

后端同步写入的每个模型 YAML 顶层多一个键：

```yaml
id: openai-gpt-4o-mini
name: GPT-4o mini
...
synced_from_server: true
```

- 键名固定 `synced_from_server`，值固定布尔 `true`（同步写入侧恒真）。
- 判定语义：只有 `is True` 才视为「后端写入、可删除」；缺失、false、非布尔
  一律视为自定义（保守：宁可保留，不误删）。
- 序列化：由写盘路径（`_write_profile` 或其调用点）在 dump 前注入该键；
  `profile_to_dict()` 与 `ModelProfile` 不感知，落盘后 loader 忽略该键。
- 读取：用 `read_profile_mapping()`（`chrys.service.profiles.file_scan`，只读
  公开函数，不改上游）读匹配到的 YAML，取 `data.get("synced_from_server") is True`。

## 关键机制与不变量

1. **两阶段发布保持**：先写 tmp → `os.replace` → 删除旧文件 → 写 state，
   任一步失败保留上一版目录。本批只改「删除哪些」和「写入带标记」，不改顺序。
2. **来源判定不依赖 state**：`read_catalog_state()` 仍被调用（用于 previous_ids
   等既有语义），但「是否可删」只看 YAML 里的标记，不看 `profile_ids`。
   `.catalog-state.json` 的写入内容一行不改。
3. **指纹不变**：`_coerce_version()` 只 hash `catalog.items`（后端项），本批
   不把自定义项塞进 catalog，hash 口径自然不变。
4. **内存快照**：`install_snapshot()` 的纯内存语义不变；调用点改为传入
   `后端项 + 保留的自定义项`。自定义项由扫描阶段读目录得到（用
   `load_profile_from_yaml` 公开函数，不改上游），只在同步成功路径发生。
5. **只读门禁不变**：`is_catalog_managed()` 与 TUI 恒只读逻辑不动。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| ① YAML 标记 + 同步时比较（本方案） | 零上游改动；判据直观；不依赖 state | 旧版无标记 YAML 首同步有一次迁移告警 | catalog.py 1 文件 × ~60 行 × 同步模块内部 | **选用** |
| ② 给 `ModelProfile` 加布尔字段 | 类型安全、全链路可见 | 改 `schema.py`/`loader.py` 两个上游文件；字段会进 `profile_to_dict` / TUI 编辑面；R2 负担重 | 4+ 文件 × 跨模块 | 否决：需求只要同步时区分，字段不该渗透到 profile 模型 |
| ③ 靠 `.catalog-state.json` 的 `profile_ids` 比较 | 零新增字段 | 与责任人「不依赖 state」裁决冲突；state 是后端全量快照，用户自定义一旦进入就无法区分来源 | catalog.py 1 文件 × ~40 行 | 否决：明确违反需求非目标 |

## 对上游隐式行为的假设

| 假设 | 来源 | 不成立时的后果 | 本批防线 |
|---|---|---|---|
| `read_profile_mapping()` 对未知顶层键不报错、不污染返回值 | `file_scan.py` 只读解析 | 带标记的 YAML 加载失败 | 契约测试：写带标记 YAML → `load_profile_from_yaml` 成功且 `ModelProfile` 无该属性 |
| `install_snapshot()` 只做内存替换、不做磁盘 IO | `catalog.py:143-146` | 快照扩展引入锁内 IO 或死锁 | 复审 `install_snapshot` 实现，测试断言调用前后目录无写操作 |
| `os.replace` 同名覆盖不丢权限位（600 for api_key） | `catalog.py:776-782` | 覆盖后 key 文件权限变松 | 复用同一 `_write_profile`，不另写落盘路径 |
| TUI 回调 `_refresh_model_ui(_result)` 在 UI 线程 | `app.py:1557-1560` | 提示触发线程错误 | 走既有 `call_from_thread` / 通知通道，不改线程模型 |

## 风险与最坏情况

- **误删风险**：标记读取失败（YAML 损坏）时按「无标记=自定义」保守保留，不会误删；
  代价是后端模型可能残留一个坏 YAML，下次同步同名覆盖会修复。
- **一次性迁移告警**：旧版写入的无标记 YAML 首同步按自定义处理；若 id 与后端
  相同 → 覆盖 + 告警。已记入 requirements 场景 4，责任人接受。
- **冲突覆盖的不可逆性**：后端覆盖同 id 自定义文件是责任人裁决；告警在覆盖
  **完成后**发出，用户无法阻止本次覆盖。备选「冲突则保留自定义并跳过该 id」
  被否决（违反裁决 1）。
- **零上游**：责任人裁决不做 TUI 主动提示，告警仅进 detail 日志；
  `schema.py` / `loader.py` / `app.py` 均不改，R2 清单空、无 R3 marker。

## 定制点登记预告（ADR-0015）

- 本批**无**新工具、无新 ACP 方法、无新 MCP 工具、无新 Skill——不涉及
  `gen_customizations.py` 登记。
- **零上游改动**：不改 `app.py`，R2 清单为空，不新增 R2/R3 登记。

## ADR 判定

- **不出新 ADR**：本批是对已签 catalog-sync 方案的行为修正（删除范围 + 标记
  契约），无新对外协议、无新配置面、无跨包新概念；记录留在 design 与 R2 表。
- 若责任人裁决把 `synced_from_server` 上升为跨项目契约，需另出语义 ADR
  并签认——当前无此意图。

## 验收

见 `requirements.md` 验收标准与 `test-plan.md` 覆盖矩阵；实测证据写入
`verification.md`。签认后按 DEVELOPMENT.md §4.1 方可动代码。
