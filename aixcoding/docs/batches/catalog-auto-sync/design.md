# 设计：模型目录 auto_sync 开关（LOCAL 默认不自动同步）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-11
- 确认意见：无特别意见

## 方案概述

新增 fork 私有配置键 `[model_catalog] auto_sync`（`~/.chrys/aixcoding.toml`），三态语义：
未设置时按 tier 默认（local 关、dev/prod 开），显式 `true`/`false` 全 tier 覆盖。
开关判定与全部守卫落在 fork 定制层，上游接线零改动：

```
aixcoding.toml [model_catalog] auto_sync   （三态：None / True / False）
        │  loader.py 解析（非法值 warn + None）
        ▼
catalog.py auto_sync_enabled()  =  显式值 ?? (catalog_tier() != "local")
        │
        ├─ sync_catalog_blocking() 入口：关 → return None   ← app.py:1510 接线不动
        ├─ start_sync_runtime()  入口：关 → return False    ← app.py:1564 接线不动；
        │    登录 resume_sync_runtime() 内部走本函数，连带被挡（login_actions.py 不动）
        └─ is_catalog_managed()：state 存在 → True（sticky 不变）；
             否则 auto_sync 关 → False（目录归用户）；开 → 维持原语义
```

底层 `sync_catalog` / `fetch_catalog` / `apply_catalog` 不动：现有测试直接调用照常工作，
手动同步能力（测试恢复 = TOML 显式 `auto_sync = true`）由底层原样保留。

**`is_catalog_managed()` 改写的关键背景**：现状为 `bool(catalog_url()) or state 存在`
（`catalog.py:279`），而 `catalog_url()` 在 LOCAL **恒非空**（`_CATALOG_BASES` 每 tier 均有 base）
——LOCAL 下该函数恒 True，state 检查实为死分支，目录从首次启动即只读。因此新语义必须在
auto_sync 关时**显式忽略 catalog_url 分支、只看 state**，而非"无 state 时本来就该 False"。
连带：`catalog.py` 模块头 docstring（16-19 行"read-only from the first start"段）与新语义
矛盾，实施时同步更新。

**loader 解析规则：逐字段独立降级**。`base_url` / `auto_sync` 各自非法时 warn 并仅丢弃该字段，
不连坐整节。现状 `base_url` 为唯一键，"丢整节"与"丢该字段"等效；引入第二键后若沿用整节丢弃，
"base_url 非法 + auto_sync 显式 true" 组合会把 auto_sync 静默回退 tier 默认（local→关），
与"显式值全 tier 覆盖默认"的语义承诺冲突——逐字段降级消除该边角（对 base_url 既有行为零影响：
非法时仍丢该字段、仍为空）。auto_sync 非 bool → warn + None（按未设置处理）。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| A. 三态 TOML 键 + tier 默认分叉（本方案） | LOCAL 开箱即不覆盖；显式配置可恢复 PROD 行为；配置可见可文档化 | 多一个配置键与三态语义 | 零上游接触（守卫在定制包函数入口） | 选定 |
| B. 硬编码 LOCAL 分支 + 环境变量恢复 | 改动最小 | tier 分叉埋代码；LOCAL 复现 PROD 行为须设 env；配置不可见于 TOML | 零上游接触 | 否决：同族实现形态，可发现性差 |
| C. 二态键默认 true（未设置=全 tier 自动同步） | 语义最简、零默认漂移 | LOCAL 痛点仍在：每个外网开发人员须手动加配置才不被覆盖 | 零上游接触 | 否决：未解决主场景开箱体验（讨论中提出后被 tier 默认分叉取代） |
| D. mock LLM 透传真实端点（`--llm-upstream`） | LOCAL 下模型可真实推理 | 不解决"假模型覆盖真配置"；引入凭证管理与流式转发复杂度 | mock 专区改动 | 否决为本批次路径：议题独立，留作后续候选 |

## 对上游隐式行为的假设

1. **`load_config()` 进程级 `@cache`**（`config/loader.py:106`）→ tier 与 auto_sync 在进程启动时
   定死，运行中改 TOML 不生效。我方依赖方式：守卫在入口读取缓存值即可，无需动态监听。
   假设失效（缓存被移除/改动态）时表现：行为仍正确，仅多了运行中切换的可能，无破坏。
2. **TUI 启动接线对 `sync_catalog_blocking()` 返回 None 统一降级**（`app.py:1510`，现状
   "无来源/失败保留旧列表"路径）→ 守卫复用该通道，启动继续、目录不动。假设失效（上游把
   None 改为致命）时表现：LOCAL 启动报错——属 C034 登记锚的既有风险，非本批次新增。
3. **模型管理 UI 只读为硬编码**（`config_actions.py:286` `read_only=True`；F4 禁用
   C036/C038）→ 不消费 `is_catalog_managed()`，本批次归属联动不会意外解禁 UI。
   假设失效（上游改为动态只读）时表现：LOCAL 无 state 时 UI 可能解禁，需届时另行裁决。

## 定制点登记预告

不适用：**零上游接触**。本批次全部改动落 fork 定制层（`src/chrys/service/aixcoding/`），
复用 C034（`app.py` 启动/轮询接线）等既有登记点且不改其 marker 文本；定制包内部改动
不入登记表（ADR-0015 射程为上游文件定制点，同 catalog-sync 批次 design 末注）。

## 风险与最坏情况

- **LOCAL 已同步过的用户（有 state）**：升级后轮询默认停止，目录停留于上次 mock catalog；
  sticky 语义保留旧列表不丢模型。恢复手段 = 显式 `auto_sync = true`；回用户自管 =
  手工删除 `.catalog-state.json` 与 mock 模型 yaml（文档说明）。
- **DEV/PROD 用户误设 `auto_sync = false`**：不再接收服务端模型更新（自伤式配置）。
  缓解：守卫拒绝时 detail 日志留痕；配置说明落点两份——子包 `mock/model_catalog/README.md`
  写完整操作说明（含"仅 LOCAL 自管场景使用"提示），总 `mock/README.md` 注册表/合用端口说明
  补 LOCAL 默认不同步一句并指向子包。
- **回滚**：revert 本批次提交即回现状；无数据格式变更（state 文件结构不动），无迁移负担。

## ADR 判定

按 §6 四问过一遍：

1. 被认真考虑但否决的备选：B/C/D 均为同族实现形态或独立议题，属"模块内实现选择"
   （反面清单），无跨功能约束 → 不触发。
2. 撤销代价：低——纯配置键 + 函数守卫，无依赖方向/目录落点/数据格式/对外契约变更 → 不触发。
3. 约束未来工作模式：否，普通功能配置键 → 不触发。
4. 依赖上游非公开接口或行为：仅复用 C034 既有接线（已登记 anchor），无新增 → 不触发。

结论：不出 ADR。若责任人审阅认为"tier 默认分叉"属需独立追溯的决策，可签认时要求补出。
