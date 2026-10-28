# 设计：规范落地四工具（devtools）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-28
- 确认意见：无特别意见

## 方案概述

纯开发资产（根 `aixcoding/tools/`），四入口脚本 + 共享库，stdlib-only。无上游改动、无新依赖。

```
aixcoding/tools/
  _common.py                  共享基建：标记正则 / 文件分类器 / git diff 封装
  gen_customizations.py   ①   扫描标记 → CUSTOMIZATIONS.md（或 --repo 考古报告）
  check_r2_diff.py        ②   git diff 上游文件集 ⊆ 已签认 design.md R2 表并集
  check_r3_markers.py     ③   被改上游文件新增行须含 AIxCoding 标记（豁免表放行）
  check_import_boundaries.py ④ AST 静态扫描四条边界规则

aixcoding/tests/tools/        配套测试（临时 git repo / 临时文件树 fixture，可复现）
```

**文件分类器（①②③④共用）**：定制 = 根 `aixcoding/` + `src/chrys/*/aixcoding/`（ADR-0011 tier 落位，档位段通配）+ `.github/workflows/aixcoding-tests.yml`；其余全部视为上游（含 `tests/`、`pyproject.toml`、`src/chrys/` 上游部分——R2 定义"对上游代码的任何改动（含 tests/、构建与打包配置）"）。

**标记正则（①③共用）**：行注释中 `\bAIxCoding\b` 且非方括号形态、大小写敏感；命中行同时捕获注释全文与归属模块（标记后括号内路径，如 `(src/chrys/kernel/aixcoding/tool_events)`）。字符串常量中的 `AIxCoding`（品牌名）非注释形态——按语法甄别（Python: AST/tokenize 注释 token；文本格式: 行首 `#` 后接标记）。

**标记来源**：R3 口径——存量 19 处 + 新增均为 `# AIxCoding <模块>: <说明>` 单行英文注释；tcss/toml 等文本格式用 `#` 同规则。

## 备选方案对比

| 决策点 | 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| ①语义字段来源 | design.md"定制点登记预告"表合并 | 单一事实源；强制"先 design 后代码"闭环（无登记→生成报错） | design.md 未填登记表时清单缺行（以报错暴露，属期望行为） | **采用** |
| | 独立登记文件 | 解耦 | 多一处台账，必然漂移（§5 禁手工维护代码事实的初衷） | 否 |
| ②③比对基准 | 显式 `--base <ref>` | 本地/CI/runbook 三语境统一；无隐性猜测 | 用户须知道 base 是什么（提示语兜底） | **采用** |
| | 内置 merge-base 猜测 | 零参数 | fork 多 remote 场景猜错=门禁失效 | 否 |
| ③校验粒度 | 文件级（每被改上游文件≥1 处标记） | 抗格式化噪音；实现简单 | 同文件多处改动只验存在性，密度靠 peer review | **采用** |
| | hunk 级 | 精确 | diff 噪音（reformat/移动）误报率高 | 否 |
| ④实现方式 | AST 静态扫描（`import ast`） | 精确（含 `from x import y`、相对 import 解析）；零执行风险 | 只覆盖 .py（合理：边界规则约束的就是 .py） | **采用** |
| | 正则匹配 import 行 | 简单 | 多行 import/别名/动态 import 误判 | 否 |
| 汇总形态 | 四入口脚本 + `_common.py` | 单一职责、可独立调用、CI 按需组合 | 共享库需维护 | **采用** |
| | 单一大脚本子命令 | 一次安装 | 职责混杂，与 check_docs.py 单文件风格不一 | 否 |

ADR 判定：均为"模块内实现选择 + 照规范（§5/§9/ADR-0007）执行"，机制级决策（门禁三件套、清单脚本生成）已由规范与 plan.md §0 承载，此处无新机制决策——不出 ADR。理由链：§5 已定"脚本扫描自动生成与校验"；ADR-0007 已列 R2/R3/import 三门禁为机器门禁扩容项；登记预告表是 design.md 模板既有节（diagnostics/design.md 已在用），非新增义务。

## 对上游隐式行为的假设

| 假设 | 依赖方式 | 失效表现 |
|---|---|---|
| 仓库为 git 仓库、`--base` ref 可解析 | ②③ 调 `git diff`（子进程） | 退出非零并提示 ref 无效（fail-fast） |
| 布局约定 `src/chrys/` + 根 `tests/`（AGENTS.md 路径约定） | ①④ 扫描范围按此定位 | 上游重构布局时扫描遗漏——分类器集中一处，改一行适配 |
| design.md R2 表/登记预告表格式为 Markdown 表格 | ②① 解析表头列名定位 | 格式漂移→解析失败报错（显式提示哪份文档），不静默跳过 |

无上游文件改动，无 anchor。

## 定制点登记预告

不适用：纯开发资产（根 `aixcoding/tools/`），无上游接触面，不入 CUSTOMIZATIONS.md（清单只登记上游定制点）。

## 风险与最坏情况

- 误报（门禁误拦）：极端情况可 `--waive` 显式传豁免并留痕于输出，不设静默跳过；豁免滥用由 peer review 把关；
- 漏报（标记正则未覆盖新注释风格）：文件级粒度 + peer review 双保险；正则集中在 `_common.py` 一处，发现即修；
- 回滚：纯新增文件，删除即回滚，无任何上游影响。

## ADR 判定

四问（§6 checklist）：①否决备选——均为模块内实现选择，无机制级否决备选；②撤销代价——纯开发资产可即删，低；③约束未来工作模式——机制已由规范承载，无新约束；④依赖上游非公开接口——无（仅 git 与文件布局公开约定）。反面清单命中"照规范执行 + 模块内实现选择"。结论：不出 ADR。
