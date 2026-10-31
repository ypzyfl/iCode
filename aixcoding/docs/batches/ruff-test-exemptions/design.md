# 设计：aixcoding/tests 的 ruff 豁免切换为目录级配置

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：确认实施期修正记录（marker 括号适配，R2 实质零变更）

## 方案概述

`pyproject.toml` `[tool.ruff.lint.per-file-ignores]` 区块（上游 `tests/**` 行近旁）追加 2 行：R3 marker 注释 + 目录级豁免行。随后清理测试文件冗余 noqa 头：28 个整行删除，`tools/test_check_import_boundaries.py` 收窄为 `# ruff: noqa: RUF002`。

```toml
# AIxCoding custom tests: fake creds/asserts, frozen Chinese-message assertions (aixcoding/tests)
"aixcoding/tests/**" = ["S", "PERF401", "RUF001"]
```

规则集核对（现状 29 个带头文件的规则分布 → 目录行覆盖情况）：

| 规则 | 现状文件数 | 目录行覆盖 |
|---|---|---|
| S101 | 29（全部带头文件） | S 组 |
| S106 / S107 | 7 / 1 | S 组 |
| S603 / S607 | 1（`tests/conftest.py`） | S 组 |
| S310 | 2（mock 族） | S 组 |
| RUF001 | 8（tui 3 + auth 1 + tools 4） | 显式 |
| PERF401 | 0（预防性，对齐上游 `tests/**` 口径） | 显式 |
| RUF002 | 1（`tools/test_check_import_boundaries.py`，docstring 全角标点） | **不覆盖**——单文件保留，不进目录行 |

删除安全性论证：ruff 文件级 `# ruff: noqa` 只豁免头中列出的规则码，未列规则一直处于检查中（未报 = 无违规）；因此删头唯一可能暴露的是头中已列规则的违规——S101/S106/S107/S603/S607/S310/RUF001 全部被目录行覆盖，RUF002 已保留，删头后 `ruff check aixcoding/` 必然维持绿（实施期机器验证兜底）。

**组级 vs 规则级的取舍标准**（2026-10-30 评审补充，可审计）：S 用整组——S 组全部是安全审计类规则（assert/凭证/subprocess/eval），测试目录整体豁免是社区与上游 `tests/**` 验证过的口径；RUF 用单规则——RUF 组含 RUF012（可变类属性默认值）等对测试代码同样有效的规则，不能整组放行，故只挑 RUF001。**RUF001 进目录、RUF002 单文件保留的边界标准是频率**：RUF001 是 8 个文件的持续需求（断言冻结中文消息是定制测试常态）、RUF002 是 1 个文件孤例——将来新测试文件 docstring 含全角标点仍会触发 RUF002 报错，属有意为之（"零心智负担"与"豁免面最小"的取舍边界，接受单点保留成本）。

marker 注释单行（与区块内上游注释风格及 tui 批次先例一致）。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| **A. 目录级 per-file-ignores（pyproject +2 行）** | 一劳永逸、集中可审计；新测试文件零心智负担 | R2 报批一次；per-file-ignores 区块追加行 | 1 上游文件 × 2 行（追加行，低耦合） | **采用** |
| B. 维持逐文件 noqa | 零上游足迹 | 靠人记必漏（PR #70 实证）；每新文件/新规则重复劳动 | 0 上游文件 | 否 |
| C. `aixcoding/` 全目录一行 | 配置更少 | `aixcoding/tools/`、`aixcoding/mock/` 非测试文件是 T201 为主的不同规则族（CLI 工具打印是本职），与测试豁免（S/RUF001）混同后豁免面过大 | 同 A | 否（"不扩"决定，R8 留档） |
| D. 行内逐处 noqa | 豁免最精准 | 数百处标注，维护成本最高 | 0 上游文件 | 否 |

R1 自查：无业务逻辑，纯 lint 配置；上游接触面即 per-file-ignores 追加 2 行（与 tui 批次先例 `"src/chrys/app/aixcoding/tui/*"` 同区块同形态），无法更少。

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `pyproject.toml` | `[tool.ruff.lint.per-file-ignores]` 追加 marker 注释 1 行 + `"aixcoding/tests/**" = ["S", "PERF401", "RUF001"]` 1 行 | +2 | 配置行上方单行：`# AIxCoding custom tests: fake creds/asserts, frozen Chinese-message assertions (aixcoding/tests)` |

## 对上游隐式行为的假设

| 行为 | 我方依赖方式 | 假设失效时的表现 |
|---|---|---|
| ruff per-file-ignores 的 glob 相对 pyproject.toml 所在目录（仓库根）解析，`**` 匹配任意层级子目录 | `aixcoding/tests/**` 覆盖 tests 全部子目录（auth/tui/tools/mock/diagnostics 及各级 conftest） | 豁免不生效 → 删头后 `ruff check aixcoding/` 红，实施期机器验证即暴露（与上游 `tests/**` 同构，先例在工作） |
| 上游 CI ruff 门禁（`ruff check src/ tests/ …`）不含 `aixcoding/`，fork 门禁（aixcoding-tests.yml）独立扫 `aixcoding/` | 两套门禁互不干扰；上游 `tests/**` 行不动 | 无失效路径（命令串实态，非隐式行为） |
| S/RUF 组语义随 ruff 升级扩充新规则码 | 组级豁免自动覆盖新规则——正是本批次目的（新规则不再逐文件补头） | 组内新规则被豁免到测试目录——可接受（测试目录 S/RUF 豁免是常态口径，上游 `tests/**` 同款） |

## 定制点登记预告

`pyproject.toml` 已是登记对象（tui 批次 per-file-ignores 行先例在库）；点级登记（customization-registry 批次起）：

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C003 | pyproject.toml | AIxCoding custom tests | | 无上游符号依赖（纯工具配置；marker 落 `pyproject.toml` per-file-ignores 区块 +2 行） | 低（升级合并冲突面＝追加 2 行） | 〔目录退役〕aixcoding/tests 目录退役；或豁免迁 pyproject per-file-ignores 目录级（既有遗留待办，届时触发上游 R2 报批） |

## 风险与最坏情况

- 决策错了会怎样：删 2 行配置 + git 还原测试文件即完全回滚；noqa 头增删是注释级变更，测试行为零影响；
- 最坏情况：目录行意外豁免测试目录内本不该豁免的真问题（如真实凭证硬编码）——缓解：S 组豁免限于测试目录（假凭证是测试常态，上游 `tests/**` 同款口径）；lint 豁免不是审计豁免，真凭证问题由提交评审与 secret 扫描兜底；
- **S 整组的扩展面代价**（2026-10-30 评审补充）：`"S"` 整组意味着 ruff 升级新增的 S3xx/S5xx/S7xx（如 S301 pickle、S324 弱哈希）自动豁免到测试目录——这是"整组"比"精确列出当前 6 个 S 规则码"更宽的代价（与假设表第 3 行同判：可接受；换来的是新规则码零维护，正是本批次目的）；另 RUF001 除全角标点外也检测同形字/零宽字符等混淆字符，测试目录豁免即放弃该检查于测试字符串，同由评审兜底。

## ADR 判定

1. 被认真考虑但否决的备选？——备选（B/C/D）是常规配置形态对比，未达决策粒度。否。
2. 撤销代价高？——2 行配置删除即回滚。否。
3. 约束未来工作模式？——弱：确立"aixcoding/tests 目录级豁免"惯例；性质是减负担（新测试零 noqa 配置），tui 批次同类决策（per-file-ignores 加行）未出 ADR，同构跟随。否。
4. 依赖上游非公开接口或行为？——否（ruff 公开配置语义，glob 行为已钉假设表）。

结论：不出 ADR。

## 验证方式

1. `uv run ruff check aixcoding/` + `uv run ruff format --check aixcoding/`（目录行生效 + 删头无新暴露；对齐 aixcoding-tests.yml 门禁）；
2. `uv run ruff check src/ tests/`（上游豁免格局不受影响）；
3. `uv run pytest aixcoding/tests -m "not integration and not gc_calibration"`（注释级变更，惯例全量兜底）；
4. `uv run python aixcoding/tools/gen_customizations.py --strict` 对账全绿（孤儿登记清零；customization-registry 批次起 freshness 义务已随产物退役）。

## 实施期修正记录

- 2026-10-30：`gen_customizations.py` 首跑拦截 marker 无登记行匹配——`classify_marker_body`（`aixcoding/tools/_common.py`）优先取**括号内含 `aixcoding` 的路径**作 module，无括号时回退冒号前词（原 marker 提取为 `custom`，与登记落点不可匹配）。修正：marker 文本补括号指向 `(aixcoding/tests)`（module = `aixcoding/tests`），登记表落点同步改为 `aixcoding/tests/`（规范路径形态，tui 批次先例同构）。批准实质（`pyproject.toml` +2 行、规则集、位置）零变更，属工具契约的格式适配（同 tui 批次变更记录（十）"marker 格式修正"性质）。
