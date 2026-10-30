# 测试方案：豁免治理（R13——豁免须理由与批准）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

纯文档批次（零代码、零上游文件）：无代码测试义务（§5 不适用），验证层为**文档一致性与签认合规核对**：

1. `check_docs.py` 全量通过（含新建 ADR-0014 草案态合法性）；
2. 8 处联动逐项与 design.md 联动表对照（条文落位、R9/§3 口径、§3 标题、§7 子项、两 HOWTO 摘要、README 速查）；
3. 全库检索确认无 `_DAG_EDGE_ALLOWLIST` 活指引残留（历史快照与"现文"引文除外）。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型（单元/契约/端到端/行为锚定） |
|---|---|---|
| R13 生效（枚举/立场/停等点/留痕/档位/存量） | 文档核对：DEVELOPMENT.md R13 vs design 条文全文 | 人工核对 |
| R9 与 DIRECTORY §3 对齐 ADR-0013 | 文档核对 + 残留检索（无"走 allowlist 豁免"活指引） | 人工核对 |
| HOWTO 摘要与 README 速查同步 | 文档核对（R 系列同步义务，§3 尾注） | 人工核对 |
| ADR-0014 留档并签认 | `check_docs.py`（草案→已确认的状态机校验） | 工具校验 |
| check_docs.py 通过 | `uv run python aixcoding/tools/check_docs.py` | 工具校验 |

## 异常与降级路径

不适用（纯文档批次，无运行时行为）。

## 手工验证步骤（若需）

见 verification.md 2026-10-30 节（check_docs / 残留检索 / git status 改动清单三项）。
