# 验证记录：tui 迁入实施

## 门禁结果（2026-10-28，feat/tui_login @ 工作区）

| 门禁 | 结果 | 备注 |
|---|---|---|
| aixcoding/tests/tui | **25 passed** | 对话框 3 + wiring 7 + indicator 9 + 徽标 2 + 命令 4 |
| 上游 i18n 断言 | **4 passed** | `/man` 索引期望 +2 行后绿（必然红→修复实证） |
| 上游建议系统回归 | **全绿** | tui_helpers 等 3 构造点修补后 91 连带用例恢复 |
| tests/app/tui 全树 + workflows env | **9926 passed** | 唯 3 失败 = gc_freeze_calibration（在案满载 flaky） |
| Smart Test 全量（pyproject 触发） | **32357 passed** | 1 failed = gc_freeze_calibration（单独复跑 PASSED，见下） |
| Smart Test 定向复跑 | **PASSED (exit 0)** | 含 gc_freeze_calibration 文件，证明为满载偶发 |
| architecture（-n0） | **1237 passed** | test_layering 零豁免（ADR-0011 收益持续） |
| ruff check（src + aixcoding） | **All checks passed** | 含上游 5 接线文件 |
| ruff format | **11 files formatted-clean** | aixcoding 包 + tui 测试 |
| ty check（win32, --error-on-warning） | **All checks passed** | 四轮修复后（self-review 第 4 条） |
| i18n check | **OK** | pot +25 / po msgstr=fallback ×4 / mo 重编 / oracle 2405 |
| check_r2_diff --base main_aixcoding_cli | **16 文件全 approved** | 零 unauthorized（表 7-12 拆行后） |
| gen_customizations | **26 定制点写入**（R3 粒度澄清后 marker 29→20 相邻合并 + 主干 6；初版曾为 28/35 系瘦身前口径） | 唯一 warning 为 auth 既有在案项 |
| check_docs | **OK** | 11 ADR + 14 design + 10 self-review |

## 关键实测证据

1. **ADR-0011 零豁免**：`chrys.app.aixcoding.tui` 落位后 architecture 1237 全绿，无任何
   DAG 登记或豁免边（对照：ADR-0002 旧口径需 +4 行登记 + 3 条豁免起步）。
2. **假设九"必然红"闭环**：`/man` 索引断言实施首跑实红（外部评审 F2 预判实证），期望
   +2 行后绿；但射程被低估（91 构造点连带），见表 13-16。
3. **i18n 三方一致**：extract 4 key 入 pot（`#. English: 中文` 怪条目实测无害，check 过）；
   po msgstr=fallback 复制使 oracle"有可见翻译"集合断言满足；size 2401→2405。
4. **D2 口径行为验证**：`/language en` 下命令描述渲染 fallback 中文（`/man` en 视图索引
   实测显示"用 AIxCoding 账号登录"）——借壳形态的实际效果与纯常量一致（design D2 论断
   实证）。
5. **改进一价值实证**：`git diff main_aixcoding_cli -- src/chrys/app/tui/app.py` 零改动；
   silent check 挂点断言（wiring 2 用例）锚定 MainScreen on_mount/on_unmount。

## 环境备注

- 本地配方（CodeBuddy）：`set PYTHONPATH=`（脱离 genie shim）+ `PYTHONUTF8=1` +
  大写盘符 `D:\` + `UV_PYTHON=3.14.3`。
- `@CI_LINUX_ONLY` 语义（复审 H1 订正）：`skipif(bool(CI) and not linux)`——**本地（任意平台）从不 skip**，仅 CI 的非 Linux 分片 skip；本地实测即有效验证。
