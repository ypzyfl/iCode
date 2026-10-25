# 任务清单：规范落地四工具（devtools）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

双 AI 评审**收敛**：2 轮——第 1 轮 10 findings（修 7 留 3），复审确认修复到位并发现 F-11（词边界两路径口径分歧，已修统一）；52 测试全绿；`self-review.md` 两轮结论已落盘（草案）。待责任人签认 self-review.md → 组装 PR。

## 待办

- [x] design.md 签认（责任人 2026-10-25）
- [x] `aixcoding/tests/` 测试基建首建（conftest：sys.path 注入 + file_tree/git_repo fixture，对齐 DIRECTORY.md §5）
- [x] 工具④ `check_import_boundaries.py`（B1–B4 规则 + mock 相对 import 出包解析）
- [x] 工具① `gen_customizations.py`（含 `_common.py` 标记正则/分类器；生成模式 + `--repo` 考古模式）
- [x] 工具② `check_r2_diff.py`（untracked 拦截 + 未签认 design 不授权）
- [x] 工具③ `check_r3_markers.py`（untracked 全文检查 + 豁免表）
- [x] 配套测试（aixcoding/tests/tools/ 6 文件 48 用例）全绿
- [x] 对旧分支副本跑考古扫描 → `archaeology-report-0.28.0.md`（932 命中：24 注释标记 / 908 品牌串；57 定制资产文件）
- [x] verification.md 记录真实仓库四脚本运行证据
- [x] 挂起项①处置：方案 A 落地——`agents-md-note/design.md` 签认，CUSTOMIZATIONS.md 生成（C001 + diagnostics 草案警告）
- [x] 双 AI 自审第 1 轮：评审 AI = CodeBuddy·Deepseek-V4-Pro；10 findings（0 blocker）；责任人拍板修 7 留 3；52 passed
- [x] 复审（第 2 轮）：7 项修复核对通过；新 finding F-11（`added_line_has_marker` 词边界未同步）已修并统一口径 → **评审收敛**
- [ ] self-review.md 签认（责任人）→ 组装 PR（§7 交付报告）
- [ ] 挂起项②待确认：diagnostics/design.md 签认回退是否有意（不阻塞本批）

## 挂起与备忘

- **①（阻塞工具①对真实仓库的清单生成）AGENTS.md:5-12 的 `<!-- AIxCoding ... -->` 入口段是未登记的既有上游定制点**。待负责人裁决：A 补极薄 design（`agents-md-note`：R2 表一行+登记预告一行）签认后合法收录（推荐）；B 改工具口径排除根级 md（不推荐，漏报）。工具当前正确地报 error 拒绝生成——这是门禁的预期行为。
- **② diagnostics/design.md 签认状态现为"草案"**（此前一度为"已确认"，后被回退）。若有意（先做四工具、签认推迟到实施前）则现状正确；若无意请重新签认。工具②已按草案正确忽略其 R2 表。
- 实施中修复的两个门禁漏洞（已含测试）：untracked 上游新文件 R2 拦截 / R3 全文检查；md `#` 标题误判注释标记（md 只认 `<!-- -->` 形态）。
- CI 挂接（四工具进 `aixcoding-tests.yml`）属 U3 另行任务，本批只保证脚本可被 CI 调用（退出码即结论）。
- ruff 豁免走文件级 `# ruff: noqa`（check_docs.py 先例），未改上游 `pyproject.toml`（改 per-file-ignores 属 R2 项，将来若嫌文件头噪音可报批一行换集中配置）。
- 5 个设计决策点已确认（2026-10-25）：语义字段来源=design.md 登记预告表；--base 显式传；③文件级粒度；薄文档管线；目录名 devtools。
