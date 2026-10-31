# 测试方案：ADR-0011 存量定制包按 tier 回迁 kernel 档

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

无新增测试义务（§5：本批次无新增定制模块，纯位置移动，两包既有 14 测试文件全量回归即是
行为锚定）。守卫由既有测试承担：

- `tests/architecture`（test_layering）：守卫新落位分层合法性（kernel 档相对导入纪律、
  豁免边 Path、TIER_ORDER 键删除后无违规）；
- `aixcoding/tests`：auth 9 + diagnostics 5 前缀替换后全量回归；`test_panel_anchor.py`
  （diagnostics 第 6 个文件）零改动——锚定上游 logger 名 `"aixcoding"`，与 import 路径
  解耦（design.md 联动清单第 1 条负向约束），logger 名不随回迁改；
- `aixcoding/tests/tools`：工具自检 4 文件夹具更新，守卫分类器通配改动（本批次唯一
  "改测试"部分：夹具路径 + 补 tier 形态判定用例）。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| architecture 绿（分层判定/豁免 Path） | tests/architecture/test_layering.py 全量 | 行为锚定 |
| aixcoding tests 绿（14 文件回归） | aixcoding/tests/auth/* + diagnostics/* | 单元/契约回归 |
| 工具分类器通配正确 | aixcoding/tests/tools/ 4 文件（夹具更新+新用例） | 单元 |
| ty check 绿（kernel 档新路径） | `uv run ty check src/chrys` | 静态 |
| wheel 含 chrys.kernel.aixcoding | wheel 冒烟（uv build + unzip -l / import 探测） | 打包验证 |
| 全库无旧前缀残留 | `git grep "chrys\.aixcoding"` 清零核对（R8 留档项除外） | 人工核对 |

## 异常与降级路径

不适用（无行为变化批次）。降级行为（wire_client lazy import 全吞错）由
`test_llm_token_wiring.py` 既有用例回归覆盖。

## 手工验证步骤（若需）

四项验证命令与全库 grep 清零核对，结果记入 verification.md。
