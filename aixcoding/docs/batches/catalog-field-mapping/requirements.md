# 需求：对齐后端模型目录字段在 iCode 中的使用

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

后端模型目录接口下发 `models` 数组，每个条目用服务端自有客户端的字段名与嵌套结构。
iCode 侧的 `translate_models_payload()`（`src/chrys/service/aixcoding/models/catalog.py`）
目前用**写死式 `item`** 只构造 7 个键，服务端嵌套对象里有 iCode 消费者的三个字段
被静默丢弃：

| 后端字段 | iCode 字段 | 运行时消费者 |
|---|---|---|
| `completionOptions.maxTokens` | `max_output_tokens` | `options.py:287-292` → 请求 `max_tokens`；`side_question.py:158` |
| `capabilities.uploadImage` | `vision` | TUI `#mc-vision`；`loader.py` |
| `requestOptions.verifySsl` | `verify_ssl` | `llm/clients.py:299` → httpx `verify` |

三个目标字段在 `ModelProfile` 中**已存在**，无需新增字段、无需改上游。
同时本仓库 mock 的 `config_new.json` 只剩 5 个顶层字段，连这三组嵌套块都没有，
导致无法验证映射是否生效，也无法复现真实后端响应形态。

## 目标与非目标

- 目标：
  1. **范围 ①（最小增量）**：只补上述 3 个字段的映射，不动转换层其余结构、
     不改 `parse_catalog()`、不改 `loader.py` / `serializer.py` / `options.py`。
  2. mock 数据按 `design.md` 内联冻结的服务端响应体契约补齐，
     作为契约事实源与验证夹具。
  3. 用契约测试钉死「三个字段落盘 + 干扰项不落盘」，含 `reasoning` 明确丢弃。
- 非目标（防止范围蔓延）：
  - 不改成字段白名单式透传（方案 ②）；不做端到端闭环与请求参数日志（方案 ③）。
  - 不新增 `openrouter` provider，不碰 `VALID_PROVIDERS` 与 LLM 客户端栈。
  - 不改服务端下发的 `provider` 值，客户端继续忽略并落 `CONTINUE_PROVIDER`。
  - 不映射 `completionOptions.reasoning`（责任人裁决 A：明确丢弃、无消费方）。
  - 不新增 `ModelProfile` 字段，不改 `schema.py` 等任何上游文件。
  - 不碰 iCode 侧后端不下发的 13 个本地字段（`http_*`、`chat_options`、
    `stream`、thinking 三件套等），它们继续取本地默认值。
  - 不删顶层 `aa` 干扰项，不下发顶层 `vision`。

## 用户场景

1. LOCAL 环境启动 mock，同步后打开模型配置界面：`max_output_tokens` 显示 16000、
   Vision 勾选、跳过 TLS 勾选，与后端下发一致。
2. 同一 profile 发起 Chat Completions 请求：`max_tokens` 为 16000、
   `verify` 按 `verify_ssl=false` 生效。
3. 后端继续下发 `completionOptions.reasoning` 与顶层 `aa`，同步结果不受影响，
   落盘 YAML 里不出现这些键。

## 验收标准

- [x] `translate_models_payload()` 对含三组嵌套块的 payload 产出
      `max_output_tokens=16000`、`vision=True`、`verify_ssl=False`。
- [x] 经 `parse_catalog()` 得到的 `ModelProfile` 三个字段取值同上；
      既有 4 个顶层映射（`title`/`model`/`apiBase`/`contextLength`）与
      `provider` 忽略行为不变。
- [x] `completionOptions.reasoning`、顶层 `aa`、`apiKey`/`api_key`、
      三个嵌套块整块均不进入 `item`，也不落盘。
- [x] `aixcoding/mock/model_catalog/config_new.json` 与 `design.md` 冻结契约
      字段集合一致（`provider`、`aa` 原样保留；`verifySsl: false` 取非默认值）。
- [x] 落盘 profile 为 `provider=openai`、`max_output_tokens=16000`、
      `vision=True`、`verify_ssl=False`，且无 `reasoning` 键。
- [x] 新增转换契约测试通过；既有目录同步相关测试不回归。
- [x] 零上游文件改动（`check_r2_diff` / `check_r3_markers` 的
      `upstream_changed=0`），零新增 R13 豁免。
- [ ] `check_docs.py --closure`、`gen_customizations.py --strict`、
      ruff check/format、Smart Test 全绿（签认完成后）。
      > 除 `--closure` 外均已实测通过；`--closure` 仍报 1 条
      > `self-review.md` 草案错误，待双 AI 自审 + 责任人签认后清零。
      > 证据见 `verification.md` 实施节。

> 用户场景 1/2 的端到端人工验证未执行，按 `test-plan.md` 范围由契约测试 +
> 落盘 / loader 读回覆盖，如实记于 `verification.md`「未执行项」。

## 开放问题

- **ADR 判定**：按 §6 四问，「决定不做」（方案 ②/③、`reasoning` 丢弃、
  不改 `schema.py`）是否构成「被认真考虑但否决的备选」而需出语义 ADR——
  本批倾向不出（模块内实现选择 + R8 在 design 备选对比留档），
  **最终由责任人裁决**。
- 双 AI 自审的评审 AI 需与开发 AI 不同源，由责任人指定或裁决是否沿用
  HOWTO ② 的建议性口径。
- 批次目录名 `catalog-field-mapping` 为提议值，责任人可改。
