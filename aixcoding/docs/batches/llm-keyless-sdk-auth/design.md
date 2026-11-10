# 设计：无凭证 OpenAI 客户端跳过 Authorization 头校验（llm-keyless-sdk-auth）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-10
- 确认意见：（可选；审阅中形成的判断、附加条件或保留）

## 方案概述

在 `RetryGuardedAsyncOpenAI`（项目对 `AsyncOpenAI` 的子类）上覆写 `_validate_headers`：client 无任何静态凭证（`api_key` 与 `admin_api_key` 皆空）时跳过 stock 校验，请求照常发出、wire 上无 `Authorization` 头；有凭证则原样走 `super()`。纯 append 方法，不改既有行。

```
_build_openai_sdk_client(api_key="")
  └─ effective_key = "" or env or _empty_openai_api_key_provider(callable)
       └─ RetryGuardedAsyncOpenAI(**kwargs)          ← 覆写生效点
            └─ 请求时 _validate_headers:
                 api_key 空 → return（跳过校验，无 Authorization 上 wire）
                 api_key 有 → super()（stock 校验不变）
```

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| A. 构造期 `default_headers` 放 `Authorization: Omit()` | 零自定义类 | **实测不可行**：SDK `_merge_mappings` 在校验前删除值为 `Omit` 的键（`_base_client.py:2275`），声明到不了校验点 | — | ✗ 已证伪 |
| B. wire 层 `stamp()` 注入 per-request `Omit()` | 兼容登录 token 兼任 Bearer（本批次非目标） | 改 `wire_client.py`+`clients.py` 两个上游文件 ~50 行；功能超出本需求 | 2×50×高 | ✗ 范围外 |
| C. 定制子类 `src/chrys/service/aixcoding/llm/sdk_auth.py` + `clients.py` 换 import（函数体归位定制包，R1 细则二默认形态） | 归位正确 | **实测不可行**：上游 20 条 factory 测试 patch `sdk_openai.RetryGuardedAsyncOpenAI` 断言构造参数，换 import 后 patch 点失效全红；修测试则扩到 2 个上游文件 | 名义 1×4，实际 2×~60×高 | ✗ 已证伪（patch 点结构约束） |
| D. 覆写方法直接加在 `RetryGuardedAsyncOpenAI`（本方案） | 纯 append、零逻辑耦合、上游测试全绿 | 函数体在上游类内（细则二归属让位于测试兼容，见下） | 1×18×低（append-only） | ✓ 采纳 |

R1 自查（必答）：业务逻辑能否完全外置？——方案 C 已实施后证伪：上游测试的 patch 点（模块属性 `sdk_openai.RetryGuardedAsyncOpenAI`）是**上游结构本身**，"在上游结构允许的前提下"（R1 边界条款）挂点只能在类本体。细则二"行数最小与归属正确冲突时归属优先"在此与"不改上游既有测试"冲突，取后者——改测试文件的冲突面（语义耦合 + 逐版本 rebase）大于 append 一个方法。

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/service/llm/sdk_openai.py` | `RetryGuardedAsyncOpenAI` 追加 `_validate_headers` 覆写（纯新增方法） | +18（含标记与 docstring） | 方法定义前单行 `# AIxCoding auth: tolerate a credential-free client (aixcoding/docs/batches/llm-keyless-sdk-auth)` |

R2 报批说明：本表为实施后补录（用户直接指令"加一个 Omit 最小改动"后实施中发现方案 A 不可行、迭代至方案 D）。责任人签认本 design 即为批准记录落盘。

## 对上游隐式行为的假设

1. 假设：SDK `_merge_mappings`（`_base_client.py:2275`）删除值为 `Omit` 的键 → 依赖方式：因此构造期无法声明省略，必须跳过校验本身 → 失效表现：若上游改为保留 `Omit` 到校验点，本覆写仍正确（只是不再必要）。
2. 假设：`_validate_headers` 是唯一的凭证拒绝点（sync/async 两处覆写同构），`self.api_key` 在 callable provider 刷新后为 `""` → 依赖方式：以 `not self.api_key and not self.admin_api_key` 判定无凭证 → 失效表现：上游若增加新的拒绝路径或改判定字段，无凭证请求可能重新被拒（表现为 TypeError 回归，测试即红）。
3. 假设：`_empty_openai_api_key_provider`（空 key 兜底）语义为"故意无凭证" → 依赖方式：本覆写将其语义补完到请求层 → 失效表现：上游若删除该兜底，空 key 构造直接失败（与本覆写无关的更早错误）。

## 定制点登记预告

不适用点级登记评估：上游接触为单文件 append 方法 + 行内标记，`gen_customizations.py` 扫描口径覆盖（标记注释格式合规）；批次完结时以脚本扫描结果为准。

## ADR 判定

不出 ADR：撤销代价低（删除 18 行即完全回滚），无架构决策、无依赖引入、无豁免（R13 不触发）。
