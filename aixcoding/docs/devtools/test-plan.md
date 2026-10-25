# 测试方案：规范落地四工具（devtools）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与测试本身保障。

## 测试范围与策略

单元测试为主，落 `aixcoding/tests/tools/`。fixture 全部临时构造（`tmp_path` 下建文件树 / `git init` 微型仓库），不依赖本仓库当前状态——保证可复现、不随定制演进漂移。无上游 anchor，无行为锚定测试义务。

`conftest.py` 复用 `aixcoding/tests/` 的 sys.path 注入机制（本批随首个测试目录一并建立）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| ①当前仓库生成空体清单+人工维护区保留 | test_gen_customizations.py::test_clean_baseline_empty / test_manual_zone_preserved | 单元 |
| ①考古模式（--repo 无 design.md 依赖） | test_gen_customizations.py::test_archaeology_mode | 单元 |
| ①甄别品牌字符串 vs 注释标记 | test_gen_customizations.py::test_marker_vs_brand_string | 单元 |
| ②零上游改动通过 | test_check_r2_diff.py::test_no_upstream_change_passes | 单元 |
| ②未批准上游改动报错+清单展示 | test_check_r2_diff.py::test_unapproved_upstream_change_fails | 单元 |
| ②未签认 design.md 的 R2 表不纳入 | test_check_r2_diff.py::test_unsigned_design_ignored | 单元 |
| ③有标记通过 / 无标记报错 | test_check_r3_markers.py::test_marker_present / test_marker_missing | 单元 |
| ③豁免表（JSON/二进制）放行 | test_check_r3_markers.py::test_exempt_formats | 单元 |
| ④四条规则逐条：违规报错+定位信息 | test_check_import_boundaries.py::test_rule_<rule>_violated / test_clean_repo_passes | 单元 |
| stdlib-only | test_no_third_party.py::test_tools_import_stdlib_only（AST 扫描 tools 与 tests 入口模块） | 单元 |

## 异常与降级路径

- `--base` ref 不存在 / 非 git 仓库：非零退出 + 明确提示（不栈崩溃）；
- design.md R2 表列名漂移：解析失败报错点名文档路径（不静默跳过=门禁失效防护）；
- 扫描目标含二进制/不可解码文件：跳过并在报告计数（考古模式不因个别文件中断）；
- `--repo` 目标无 `aixcoding/` 结构（非本 fork 仓库）：报错提示（考古模式仍要求基本布局，完全无布局无意义）；
- 空仓库/首次运行（CUSTOMIZATIONS.md 不存在）：正常生成初始文件。

## 手工验证步骤（若需）

- 对当前真实仓库跑四脚本（基线应全绿）：记入 verification.md；
- 对旧分支副本 `d:\Coding\aixcoding\aixcoding-cli\aixcoding-cli__0.28.0_final` 跑考古扫描（ROADMAP §4 交付物，属实施步骤而非测试）。
