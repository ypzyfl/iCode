# 设计：后端同步模型与自定义模型共存

<!--
签认规则（R10 · 决策档）：责任人本人编辑本头部（状态→已确认、填责任人与日期，
确认意见可选），AI 不得代填。签认后修改正文需重新签认（R2 类正文修正除外，
须在正文原位加注记并标注不触发重签）。
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-17
- 确认意见：2026-11-17 评审修正（B1 探针解码与日志、B2 完整文件名判定、S6/B5 normcase 三处口径、r2 收敛表述限定）后重签；交付评审 finding-1/2 处置后再次确认

## 方案概述

标记只存在于模型 YAML 顶层，只在同步逻辑读写；loader 用它自己的
`read_profile_mapping()` 逐字段构造 `ModelProfile`，未知键被忽略，因此
**不需要改 schema / loader，零上游改动**。本设计为分支重落地后的单轮方案：
所有机制一次到位，不含增量修订历史。

```
apply_catalog(catalog):
  ├─ 阶段一（只读扫描）：逐个读 *.yaml / *.yml 的标记探针（三态）
  │    ├─ True   → 后端管理（本次可删候选）
  │    ├─ False  → 自定义（保留）
  │    └─ None   → 畸形/不可读（保留；探针失败计数 +1）
  ├─ 升级清空判定：目录有配置文件 且 无一 True 且 探针失败计数 = 0
  │    → upgrade_clear = True（待清集合 = 全部无标记文件；本轮内存快照不含它们）
  ├─ 冲突/保留判定（以文件名 stem 为准）：stem ∈ 后端 id 集 → overwritten；
  │    否则 → preserved（读回 ModelProfile，供内存快照）
  ├─ 阶段二（发布）：staging <id>.yaml.tmp → os.replace → 删除「有标记且
  │    文件名不在 final_names」→ write_catalog_state()（内容不变）
  ├─ 升级清空（仅发布全部成功后）：删待清集合中文件名不在 final_names 的项，
  │    detail 记精确计数
  └─ 收尾：detail 记保留计数；有覆盖时 detail 记被覆盖 id（仅日志）
```

内存发布（poll 线程 `_publish`）：

```
server_ids = {profile.id for profile in catalog.items}
kept = tuple(p for p in result.preserved_profiles if p.id not in server_ids)
registry.install_snapshot((*catalog.items, *kept))
```

### 标记契约（冻结）

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
- 序列化：写盘路径（`_write_profile`）在 dump 前注入该键；
  `profile_to_dict()` 与 `ModelProfile` 不感知，落盘后 loader 忽略该键。
- 读取：`_probe_server_marker()` 用 `read_profile_mapping()`（公开函数，不改
  上游）读 YAML，取 `data.get("synced_from_server") is True`。

### 探针三态（防系统级解析失败误删整目录）

`_probe_server_marker(path) -> bool | None`：`True/False` 为确定判定，
`None` 为读取或解析失败（`yaml.ScannerError/ParserError/ConstructorError`
不是 `ValueError`，编解码与 IO 失败同理——**必须 `except Exception` 兜底**，
单个坏文件不得中断整轮同步）。读取走 loader 同款 `decode_bytes`（编码探测、
strict）——utf-8 单一解码会把外语编码文件错标为「不可判定」，永久否决升级
清空且无日志（评审 B1）。探针失败记 detail 日志；清空被探针否决时另记一行
原因日志，杜绝静默跳过。`_server_owned_names()` 返回
`(带标记文件名集合, 探针失败计数>0)`；升级清空判据同时要求两者。
边界：单文件读取/解析失败一律归 `None`（含文件在扫描后、读取前消失的
race）；扫描阶段自身失败（如 glob 迭代抛 `OSError`）不做探针级兜底，作为
裸异常逃出 `apply_catalog`，由调用方 `_sync_once` / `sync_catalog_blocking`
的 `except Exception` 兜底——本轮终止、目录不动、下次重试（既有口径）。

### 冲突与保留判定（以完整文件名为准；评审 B2 修正）

`_load_custom_profiles()` 返回 `(文件名, profile)` 对。覆盖/保留判定一律用
**完整文件名**：同步只写 `<id>.yaml`，`os.replace` 的覆盖对象是同名 `.yaml`
文件——同 stem 的 `.yml` 是另一个文件，同步永不触碰，按保留处理。显式 id
不参与磁盘判定（历史评审 F2 的「按覆盖对象判定」原则不变，B2 把口径从 stem
收窄到完整文件名）；显式 id 撞后端 id 的保留文件在内存层面由 `_publish` 的
`server_ids` 过滤兜底（后端胜出）。大小写口径（评审 S6）：判定与陈旧删除的
比较经 `os.path.normcase`（判定、陈旧删除与升级清空循环三处，评审 B5 补齐
第三处），对齐各平台 `os.replace` 的真实覆盖对象——Windows
的文件系统与 `pathlib.glob` 均大小写不敏感，`A.YAML` 与同步写的 `a.yaml` 是
同一文件、判覆盖；POSIX 系 glob 大小写敏感、`A.YAML` 不进扫描（文件不进内存
快照，内存恒与磁盘一致）。后者的两个子形态均接受：大小写不敏感文件系统
（macOS 默认 APFS）上文件被静默覆盖且无告警、POSIX 大小写敏感文件系统上原样
存活——与基线「glob 不匹配即不可见」行为同款，无内存/磁盘分歧。自定义文件
加载失败（畸形 YAML）按
「保留原文件、不进内存快照」降级，不中断同步。

### 内存快照的两层保证

1. `install_snapshot` 语义不变：锁内纯内存替换、零磁盘 IO（测试用写陷阱钉死）。
2. 传入内容 = 后端项 + 磁盘保留的自定义项，且保留项先按 `server_ids` 过滤——
   `install_snapshot` 内部按 `{profile.id: profile}` 字典构造（后者胜出），
   stem 不撞但显式 id 撞后端 id 的保留文件若不过滤，会在内存里覆盖后端项，
   与「ID 冲突后端覆盖」裁决相反（历史评审 R1）。

### 首次升级清空（触发条件与失败语义）

- **触发条件**：扫描到至少一个 `*.yaml` / `*.yml`，且没有任何一个标记为
  `True`，且所有探针可判定（无 `None`）。空目录不触发（无文件可清空）。
  任一探针 `None` 即否决清空——系统级解析失败会让所有探针返回 `None`，
  此时按「全无标记」清空将误删无法判读的目录；保守保留文件、照常写后端模型，
  文件恢复可判读（被修复或删除）后的下一轮同步即收敛。注意（评审 r2 限定）：
  永久畸形的文件不会自愈，否决会持续——这是 R6 保守 guard 的既定代价，换的是
  「判读不了就不破坏」。
- **清空时机与范围**：`staging → os.replace → 陈旧删除 → write_catalog_state`
  **全部成功后**才删待清集合中文件名不在 `final_names` 的项（同名文件已被
  `os.replace` 覆盖成后端版本，不删）。前置任一步 `OSError` 时旧文件原样保留、
  state 未重写、tmp 被清理，走既有失败分支——与两阶段「失败不碰旧数据」承诺
  一致；下次同步目录仍全无标记，重新触发清空并收敛。清空本身失败走同一失败
  分支：state 已写、后端文件已带标记落盘；残留的无标记旧文件在下一轮被判
  「自定义」**永久保留、不自愈**（交付评审 finding-1 纠正：`server_owned`
  非空使升级清空不再触发——与 r2 同款滞留、不同触发路径；触发罕见、
  无数据丢失，幽灵模型为既定代价）。
- **明确接受的风险**：纯用户目录（从未同步成功、用户自写模型）同样「全无
  标记」，会被一并清空且不可恢复。责任人已裁决接受该风险，换取实现简单、
  零 state 依赖；清空 detail 日志记一行精确计数，便于事后追溯。

## 关键机制与不变量

1. **两阶段发布保持**：先写 tmp → `os.replace` → 删除旧文件 → 写 state，
   任一步失败保留上一版目录。本批只改「删除哪些」「写入带标记」「升级清空」，
   不改顺序。
2. **来源判定不依赖 state**：`read_catalog_state()` 仍被调用（previous_ids 等
   既有语义），但「是否可删 / 是否旧配置」只看 YAML 标记。
   `.catalog-state.json` 的写入内容一行不改。
3. **指纹不变**：`_coerce_version()` 只 hash `catalog.items`（后端项），
   自定义项不进 catalog，hash 口径自然不变。
4. **只读门禁不变**：`is_catalog_managed()` 与 TUI 恒只读逻辑不动。
5. **健壮性口径统一**：标记探针与自定义加载均 `except Exception` 兜底，
   与既有 `_load_custom_profiles` 的容错口径一致；畸形文件按自定义保留、
   记 detail 日志。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| ① YAML 标记 + 同步时比较（本方案） | 零上游改动；判据直观；不依赖 state | 首次升级「全无标记」清空目录，纯用户目录会被误删（责任人接受） | catalog.py 1 文件 × ~150 行 × 同步模块内部 | **选用** |
| ② 给 `ModelProfile` 加布尔字段 | 类型安全、全链路可见 | 改 `schema.py`/`loader.py` 两个上游文件；字段会进 `profile_to_dict` / TUI 编辑面；R2 负担重 | 4+ 文件 × 跨模块 | 否决：需求只要同步时区分，字段不该渗透到 profile 模型 |
| ③ 靠 `.catalog-state.json` 的 `profile_ids` 比较 | 零新增字段 | 与「不依赖 state」裁决冲突；state 是后端全量快照，用户自定义一旦进入就无法区分来源 | catalog.py 1 文件 × ~40 行 | 否决：明确违反需求非目标 |

R1 自查：业务逻辑全部落在定制目录内（`src/chrys/service/aixcoding/models/catalog.py`
本身即定制代码），零上游文件接触，接线点为零；升级冲突面 = 同步模块内部。

## 对上游隐式行为的假设

1. **loader 忽略未知顶层键**：`load_profile_from_yaml` / `read_profile_mapping`
   逐字段构造 `ModelProfile`，未知键不报错、不进 dataclass。
   → 假设失效表现：带标记的 YAML 解析报错，同步全红；契约测试
   `test_synced_profile_yaml_carries_marker_and_loader_ignores_it` 钉死。
2. **`install_snapshot` 按 id 字典构造、后者胜出**：传入项顺序决定同 id 谁胜。
   → 假设失效表现：保留项覆盖后端项或反之；契约测试
   `test_snapshot_id_collision_keeps_backend_item_in_memory` 走真实 `_publish`
   钉死（不 mock 锚点）。
3. **`read_profile_mapping` / `load_profile_from_yaml` 是上游公开函数**且签名
   稳定（file_scan / loader 模块）。→ 失效表现：import 失败即测试红（直接依赖，
   显性可见）。
4. **`os.replace` 同卷原子**：两阶段发布的既有承诺，本批不变。

## 定制点登记预告

不适用：全部改动落在定制目录内（`src/chrys/service/aixcoding/models/catalog.py`
为定制代码；测试与文档在根 `aixcoding/`），零上游接触，无 marker 需登记，
`gen_customizations --strict` 应为零登记增量。

## 风险与最坏情况

- **误删风险（已接受）**：纯用户目录全无标记 → 升级清空删除且不可恢复。
  缓解：探针失败否决清空；清空日志记精确计数；风险由责任人裁决接受并留档。
- **决策错了会怎样**：标记语义误判（如后端某天写 `synced_from_server: "yes"`）
  → 文件被判自定义保留，后端残留——表现为多余模型，不丢数据，下次对齐。
- **回滚**：revert 本批提交即可。带标记文件在旧代码下多一个未知键，loader
  忽略之，目录语义退回「整表替换」，无迁移负担（标记缺失即安全默认）。
- **标记写入侧不封闭（已知限制，评审 S1，留档不修）**：任何绕过同步写盘路径的
  profile 重写（如 ACP `write_model_profile`，无 catalog 门禁）会丢标记，该文件
  降级为自定义；若全部文件被外部重写，「已管理目录」也会落入升级清空范围。
  修复须动上游 serializer/ACP 门禁，违反本批零上游约束。表现是幽灵模型与
  一次性重建，无数据丢失，重载自愈。
- **基线修复申报（R5，评审 S4）**：`apply_catalog` 收尾日志的占位符与参数错位
  （`%d` 收到 str）是基线既有缺陷，本批顺手修正并在此申报；仅日志正确性，
  无语义变化。
- **扫描开销与重复日志（评审 S3/r3，不修留档）**：每轮每文件读 2–3 次、三处
  扫描有时间窗；同一坏文件每轮打两条 `exc_info` 堆栈（探针失败 + 加载失败）。
  目录规模小、开销可忽略，引入缓存反增失效一致性风险（沿用旧轮 F6 先例）。
- **后端 id 仅大小写不同（交付评审 finding-2，留档不修）**：两个后端 id 仅
  大小写不同时，`final_names` 的 normcase 键碰撞（后者胜出），Windows 上实际
  写同一文件。属后端病态数据，退化温和（一个胜出、无数据破坏）。
- **发布失败日志的适用范围（交付评审 finding-1 附带，留档）**：`apply_catalog`
  失败分支日志「旧模型列表仍可使用，下次同步将重试」对 staging/replace/state
  失败准确；对「清空本身失败」不准确（残留按自定义保留、清空不重试，见升级
  清空节）。保留原文不改，以本条限定口径。

## ADR 判定

1. 有被认真考虑但否决的备选方案？——有（方案②③），但属**模块内实现选择**
   （反面清单）：单一定制模块内的来源判定机制，决策理由完整留档于上方备选表。
2. 撤销代价高？——否。标记键缺失即安全默认（无标记 = 自定义 = 保留），回滚
   无数据迁移；不改变目录格式契约的对外承诺（loader 一直忽略未知键）。
3. 约束未来工作模式，后来者会问「为什么这么做」？——否。机制自包含于同步
   模块，docstring 与本文已承载解释。
4. 依赖上游非公开接口或行为？——否。`read_profile_mapping` /
   `load_profile_from_yaml` / `install_snapshot` 均为上游公开面，且假设已在
   「对上游隐式行为的假设」节钉死。

四问均不触发（①命中反面清单），**不出 ADR**。
