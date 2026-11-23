# 设计：对齐后端模型目录字段在 iCode 中的使用

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-14
- 确认意见：（可选；审阅中形成的判断、附加条件或保留）

## 方案概述

在 `src/chrys/service/aixcoding/models/catalog.py` 的 `translate_models_payload()`
内新增一张嵌套字段映射表，在既有写死式 `item` 构造完成后，从服务端条目的
`completionOptions` / `capabilities` / `requestOptions` 三个嵌套对象里取出
`maxTokens` / `uploadImage` / `verifySsl`，写入 `item` 的同名 iCode 字段：

```
服务端 models[] 条目
  title / model / apiBase / contextLength  ──► 既有写死式 item（不动）
  completionOptions.maxTokens              ──► max_output_tokens   【新增】
  capabilities.uploadImage                 ──► vision              【新增】
  requestOptions.verifySsl                 ──► verify_ssl           【新增】
  completionOptions.reasoning / provider / aa / apiKey  ──► 丢弃（不动）
        │
        ▼
  {"items": [...], "version": "", "default_profile_id": ...}
        │  parse_catalog()（白名单 = fields(ModelProfile)，不动）
        ▼
  ModelProfile → apply_catalog() 落盘 YAML → loader.py → options.py / clients.py
```

- 嵌套值**原样写入**，由 `parse_catalog()` 统一把关，不新增第二层校验。
- `apiBase` 的 `str(...).strip() or CONTINUE_BASE_URL` 兜底、`_positive_int()`、
  `parse_catalog()` 的 `allowed = _profile_field_names()` 一概不动。
- 按下方冻结契约补齐 `config_new.json` 的三组嵌套块，作为契约夹具。
- **零上游文件接触**：改动只在 `src/chrys/service/aixcoding/`（定制包）与
  `aixcoding/`（自有目录）。R2 清单为空、R3 无 marker、R13 零新增豁免。

### 冻结的后端契约（本批约定，内联于本文档）

下面这段 JSON 是本批**自行约定**的目标响应体形态，内联在此作为唯一事实源：
`aixcoding/mock/model_catalog/config_new.json` 的补齐目标、契约测试的期望值
都以它为准。本批尚未开始实施。

`aixcoding/mock/model_catalog/config_new.json` 目标形态（字段集合与取值，
`provider` 与 `aa` 必须原样保留）：

```json
{
  "models": [
    {
      "title": "GPT-4o mini",
      "provider": "openrouter",
      "model": "openai/gpt-4o-mini",
      "apiBase": "http://127.0.0.1:7777/v1",
      "contextLength": 128000,
      "completionOptions": { "maxTokens": 16000, "reasoning": true },
      "capabilities": { "uploadImage": true },
      "requestOptions": { "verifySsl": false }
    }
  ],
  "aa": { "test": "as" }
}
```

- `verifySsl: false` 是**故意取非默认值**：`verify_ssl` 默认 `true`，
  只有非默认值才能在契约测试与落盘 YAML 里看出映射生效。
- `completionOptions.reasoning` 保留在响应体里（服务端真实下发），
  但**不映射**：iCode 侧无布尔思考开关，也没有消费这个布尔值的字段；
  同名的 `chat_options` 键是 Responses 的对象参数 `{"effort": ...}`，
  同名不同义。按 R8「决定不做」留档于下方备选对比。
- 同步只从 `models` 取值；顶层 `aa` 是验证该约束的干扰项。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| ① 写死式 `item` + 嵌套映射表（最小增量） | 改动 1 个定制文件、约 10 行；与转换层既有形态一致；零上游 | 后端将来新增字段仍需显式补映射 | 1 文件 × ~10 行 × 转换层内部 | **选用**（责任人裁决） |
| ② 改成字段白名单式透传 | 未来后端字段自动可达，随 `ModelProfile` 扩展 | 需引入排除键、补类型/枚举校验（如 `thinking_block_binding` 在 `parse_catalog` 无校验）；转换层语义重构，回归面大 | 1 文件 × ~40 行 × 转换层 + 校验链 | 否决：本批为最小对齐，不重构 |
| ③ ② + mock 参数日志 + 端到端闭环 | 可观测、验证最完整 | 范围扩散到日志与请求链，超出「字段对齐」 | ≥6 文件 × 跨模块 | 否决：日志属独立议题 |
| 新增 `ModelProfile.reasoning` 布尔字段 | 与后端同名，直观 | 跨 7+ 上游文件（`schema.py`/`loader.py`/`options.py`/TUI/本地化）；触发 R2 审批；引入无消费方字段 | 高 | 否决：无消费方，且改上游 |
| `reasoning → chat_options` 布尔直塞 | 只改翻译层 | `{"reasoning": true}` 在 Responses 期望对象、在 Chat Completions/Anthropic 是未知顶层参数，会被 SDK 拒绝；不实现后端语义 | 低但语义错误 | 否决（责任人裁决 A：明确丢弃） |
| 改服务端 `provider` 为 `openai` / 新增 openrouter provider | — | 服务端契约不在本批范围；iCode 已按 `CONTINUE_PROVIDER` 忽略 | — | 否决：保持现状 |

## 对上游隐式行为的假设

| 上游行为 | 我方依赖方式 | 假设失效时的表现 |
|---|---|---|
| `fields(ModelProfile)` 含 `max_output_tokens` / `vision` / `verify_ssl` | `parse_catalog()` 用 `_profile_field_names()` 作白名单 | 字段被判为未知、写 detail 日志后丢弃；契约测试立即红 |
| `serializer.profile_to_dict()` 省略默认值字段 | `apply_catalog()` 落盘 | 若 `verifySsl` 取 `true`（默认），YAML 看不到该键，映射无法观测；故夹具固定 `false` |
| `loader.py` 的 `coerce_bool` / `_positive_int` 兜底 | 落盘后加载 | 非法类型被降级或报错；不新增校验 |
| `options.py::effective_chat_options()` 把 `max_output_tokens` 折成 `max_tokens` | 运行时消费 | 上游改名则请求上限失效，属上游演进，不在本批守卫 |
| `clients.py` 用 `profile.verify_ssl` 作 httpx `verify` | 运行时消费 | 同上 |
| `stream` 默认值当前为 `True` | 落盘不含 `stream` 键时按默认生效 | 若以 `stream: false` 的日志期望值判断会误判；本批不引入请求日志，无验收依赖 |

## 定制点登记预告

**不适用**：本批零上游接触，全部改动落在定制包与自有目录，
无 R3 marker、无点级登记对象；`gen_customizations.py --strict` 无新增登记义务。

## 风险与最坏情况

- **最坏情况**：嵌套块形状与冻结契约不符（例如 `completionOptions` 是数组、
  或 `maxTokens` 是字符串）。此时 `item` 写入原样值，`parse_catalog()` 构造
  `ModelProfile` 后类型检查把整项判为无效，同步失败并保留上一版目录
  （`apply_catalog` 的失败语义）；不会静默写入半份配置。
  > **实施期偏差注记（2026-11-14，责任人拍板 F2）**：上述「类型检查判整项无效」
  > 对三个新映射字段不成立——`parse_catalog()` 只校验
  > `id`/`name`/`model_id`/`provider`/`api_style`，`ModelProfile` 无
  > `__post_init__`；非法类型会原样落盘，由 `loader.py` 的 `_coerce_int` /
  > `_coerce_bool` 兜底（见「对上游隐式行为的假设」表与 `verification.md`
  > 偏差节）。原文保留为签认时的原始判断，实际行为以本注记与验证记录为准；
  > 属注记而非方案变更，不触发重签。
- **映射遗漏**：三个字段之外的后端新字段仍被写死式 `item` 丢弃——这是
  方案 ① 的已知取舍，责任人已裁决接受；后续如需可扩展再另案讨论方案 ②。
- **回滚**：revert 本批 PR 即净——改动全在定制目录，无上游行、
  无登记号、无豁免；已落盘的 `~/.chrys/models/*.yaml` 会在下次同步收敛，
  用户侧残留无害。

## ADR 判定

按 `DEVELOPMENT.md §6` checklist 逐项过：

1. 有被认真考虑但否决的备选方案 → **是（形式）**：方案 ②/③、
   `reasoning` 三条路径均在上表逐条留档。按 R8「决定不做」落 design 备选对比，
   且这些否决均属**模块内实现选择**，命中反面清单，不构成跨批次决策。
2. 撤销代价高（依赖方向/目录落点/数据格式/对外契约） → **否**：
   零上游、1 文件约 10 行，revert 即净。
3. 约束未来工作模式、后来者会问「为什么」 → **否**：消费既有契约，
   不改字段集合与目录落点；「为何不映射 reasoning」已在本文件留档。
4. 依赖上游非公开接口或行为 → **否**：仅依赖 `ModelProfile` 公开 dataclass 字段
   与 `parse_catalog()` 公开行为，无 anchor 登记需求。

**结论：不新增/修订 ADR**。本批属「模块内实现选择 + 照规范执行」，
命中反面清单；被否决方案按 R8 在本文件备选对比承载。
**若责任人认定「字段映射表＝对外契约」或否决方案构成决策级备选，
则须出语义 ADR（`ADR-catalog-field-mapping--<decision-slug>`）并签认**，
此为该判定的最终归属。

## 验收

对齐 `requirements.md` 的 8 条验收标准，逐条映射到 `test-plan.md` 覆盖矩阵；
门禁全集见 `verification.md`。
