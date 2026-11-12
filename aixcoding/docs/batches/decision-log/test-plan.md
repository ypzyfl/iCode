# 测试计划：轻量决策记录（MADR——决策记录双档制）

> 活文档：随时更新、不签认。

纯文档批次（零代码、零上游文件、零 marker）——无新增测试代码，验证 = 工具门禁 + 结构一致性人工核对。

## 覆盖矩阵

| # | 验收点（requirements） | 验证方式 | 类型 |
|---|---|---|---|
| 1 | madr/ 目录 + README 就位 | README 含档位规则/命名模板/字段语义；目录内无走完整管线决策的条目（首条真实条目留给首个真实场景） | 人工核对 |
| 2 | ADR-decision-log--dual-tier-decision-records 就位 | 文件名/H1 匹配 `SEMANTIC_FILE_RE`（slug 全英文）、`check_docs.py` 无 identity 错误、机制细则含"与标准 MADR 差异"对照 | 工具 + 人工 |
| 3 | DEVELOPMENT.md 三处（R8 落点 / §6 两句 / 平铺枚举） | 全文检索 "madr" 命中三处、语义正确 | 人工核对 |
| 4 | PEER-REVIEW-HOWTO §二 第 5 项 | 模板含 madr/ 条目核对项（档位恰当 + 详证支撑，一条） | 人工核对 |
| 5 | DIRECTORY.md §2 判定树 + §1 总蓝图 | 判定树新增"是轻量决策记录？"行、总蓝图 docs/ 行含 madr/ | 人工核对 |
| 6 | SELF-REVIEW-HOWTO R8 摘要 | §二 R8 行为场景分流口径（与 DEVELOPMENT R8 落点句一致） | 人工核对 |
| 7 | README 结构图 + 速查表 | 结构一图 docs/ 行含 madr/、速查表含 MADR 检索行 | 人工核对 |
| 8 | 负担红线 | 核对无新增停等点/签认文档/CI 门禁/工具校验（联动清单仅文档修改） | 人工核对 |
| 9 | 工具门禁 | `uv run python aixcoding/tools/check_docs.py`（含 `--closure`）+ `uv run python aixcoding/tools/gen_customizations.py --strict` 双绿 | 工具 |
| 10 | UPGRADE-RUNBOOK 审计接入（机制 5 触发点） | §1 升级前清单含 madr/ 审计步骤及呈报要求 | 人工核对 |
| 11 | peer review madr 核对强度（机制 2 落点） | PEER-REVIEW §三 含人侧必做动作 ④（新增或修改条目均触发，append-only 守护）；微改动说明与 FAQ Q4 同步；**DEVELOPMENT §6 豁免段"peer review 仅做…"句含 madr diff 时 ④ 必做指向**（复审 B3 残留检查点） | 人工核对 |

## 异常与降级

无（纯文档批次；check_docs --closure 若报新批次缺件属实施中间态，实施完成后必须双绿）。
