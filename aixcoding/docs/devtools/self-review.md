# 自评审记录：规范落地四工具（devtools，含 agents-md-note 补登记）

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-25
- 确认意见：无特别意见
- 评审 AI：CodeBuddy · Deepseek-V4-Pro（独立会话，与开发 AI 不同源）
- 开发 AI：CodeBuddy · GLM-5.3

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-10-25 评审结论：通过（待复审增量）

- 轮次：1 轮（评审 + 修复，共 10 findings：0 blocker / 5 suggestion / 4 nit / 1 说明项）
- blocker 处置：无 blocker。
- 已修 findings（责任人 2026-10-25 拍板"按建议修"，7 项）：
  - F-1 untracked 读失败 fail-open → 改 fail-closed 记 violation（check_r3_markers.py）；锁定测试 `test_untracked_read_failure_fails_closed`（monkeypatch read_text 抛 OSError）
  - F-2 `scan_text_file` 读失败静默返空 → stderr 打点名提示（§9 降级可查）
  - F-3 `MarkerHit.column` 零消费 → 删除字段
  - F-4 缺结尾词边界 → `MARKER_PREFIX_RE = AIxCoding\b`（对齐 design.md 声明）；锁定测试 `test_keyword_suffix_rejected_by_word_boundary`
  - F-7 requirements.md 验收命令 `--extra all`（旧分支口径误植）→ 改 `uv run pytest aixcoding/tests/tools -n0`
  - F-8 R2 表/登记表列名漂移静默跳过 → 表头列全缺时 note 点名文档（兑现 design/test-plan 承诺）；锁定测试 `test_r2_header_drift_is_loud`
  - F-9 HTML 注释标记残留 `-->` → `_comment_body` 截尾；锁定测试 `test_html_comment_body_drops_closer`；C001 标记列已重生成确认干净
  - 修复验证：`uv run pytest aixcoding/tests/tools -n0 -q` → **52 passed**；ruff check/format 干净；gen_customizations 重跑 OK；check_docs OK
- 未修项（责任人拍板不修，3 项）：
  - F-5 `git()` 无 timeout | 本地工具，git 挂起场景罕见，按"不修功能会错吗"口径不修 | 留档
  - F-6 `test_no_third_party.py` 与被测同思路 | 评审自评"可保留"，作为验收标准的机检落点有价值 | 保留
  - F-10 PEP 758 无括号 except | 非缺陷：requires-python>=3.14 保证 + 仓内 ruff format 强制输出（既有口径） | 留档
- 复审：见下方第 2 轮记录。

## 2026-10-25 复审（第 2 轮）：通过

- 评审 AI 核对第 1 轮 7 项修复逐条到位、锁定测试真实有效、记录与代码一致、无新引入 bug。
- 复审新 finding **F-11**（suggestion）：F-4 词边界修复不彻底——`added_line_has_marker`（R3 门禁路径）仍用 `startswith`，与 `_hit`（扫描/生成路径）的 `AIxCoding\b` 口径分歧。
- 处置（已修）：`added_line_has_marker` 改用 `MARKER_PREFIX_RE.match` 与 `_hit` 共用同一正则（门禁与清单生成口径统一）；补断言 `not added_line_has_marker("X = 2  # AIxCodingSuffix: x")`；修复后 52 passed、ruff/format 干净。
- 收敛判定：blocker 始终为 0；全部 suggestion 级 findings（F-1/F-2/F-4/F-7/F-8/F-11）已修；nit 留档 3 项。**主要问题清零，评审收敛。**

## 评审红线检验摘录（评审 AI 提供）

- `test_signed_design_approves_only_listed_files`：改坏 `_common.py` R2 表"文件"列读取 → 立即红（真实行为测试）
- `test_marker_missing_fails`：改坏 `added_line_has_marker` 判定 → 立即红（真实行为测试）
