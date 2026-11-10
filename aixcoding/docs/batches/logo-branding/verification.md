# 验证：TUI 欢迎字符画品牌化（logo-branding）

> 依据：本目录 test-plan.md；design.md（2026-11-10 签认，实施修订后待 R10 重签）。
> 环境：Windows 11 / CPython 3.14.10（uv managed）/ 大写盘符 / PYTHONPATH 清空 / PYTHONUTF8=1。

## 自动验证（已跑，全绿）

| 项 | 命令/入口 | 结果 |
|---|---|---|
| banner 行为锚定三用例 | `pytest tests/app/cli/test_serve.py -k "banner or upper_half" -n0` | 3 passed（C064 跟改 + GBK 子进程不崩 + 无 `▀` 静态断言） |
| 定制层 branding 锚定套件 | `pytest aixcoding/tests/branding/test_branding_runtime.py -n0`（与上项合并跑） | 合计 5 passed（含更名后 `test_c146_serve_banner_gbk_safe_block_aixcoding`） |
| 4 处硬编码片段跟改 | `pytest tests/app/cli/test_serve.py -k "preserves_logo_spacing or until_login or clipboard_support" -n0` | 5 passed（动态引用 `TUI_LOGO.splitlines()`） |
| Smart Test | `chrys_test.py --smart --paths src/chrys/app/tui/util/logo.py src/chrys/app/cli/serve.py tests/app/cli/test_serve.py aixcoding/tests/branding/test_branding_runtime.py` | **PASSED exit 0**：tests 12151 passed / 132 skipped；architecture 506 passed（首跑 4 红面→跟改后复跑全绿；含 `test_startup_shell`/`test_workflow_welcome`/`test_welcome_update_notice`/`test_loading_widgets` 零跟改原样通过） |
| 定制点对账 | `gen_customizations.py --strict` | 0 error / 0 warning（104 行 / 145 marker / 15 design / 7 retired；C145/C146/C147-C150/C151-C152 登记、C062 退役 tombstone、branding-and-command 现役行删除对账一致） |
| 文档门禁 | `check_docs.py` | OK（23 ADR / 34 design / 32 self-review；外部评审 F1 头部修复后复跑） |
| lint | `ruff check`（四改动文件）、`ruff format --check`（四文件 + `aixcoding/` 全目录） | All checks passed / 313 files already formatted |

实施期发现与处置（详见 self-review.md）：C062 退役按 tombstone 先例迁移（原批次现役行删除 +
指向注记 + C064 removal 改随 C146）；`test_branding_runtime.py` C062 锚定用例更名 C146；
4 处 HTML 注入测试硬编码旧字形片段改动态引用（F4 裁决加 marker 登记 C147-C150）；
两条新增 GBK/无 `▀` 测试按责任人复核补 marker 独立登记 C151-C152（C064 区间不可扩）；
新增测试的 import/`check=False` lint 修正。

## 手工验证（测试机制截图 + 文本断言自核全过；产物已留档）

2026-11-10 由 AI 启动三个独立可见 cmd 窗口（工作区 `D:\Tech\Github\huawei\iCode\fork\iCode-fork_2`），
并以 Textual `run_test`/`save_screenshot` 与 Rich `export_svg` 探针产出视觉证据（探针用后
删除，工作区无残留），产物位于本目录 `screenshots/`：

| 产物 | 覆盖消费点 | 文本断言自核（`&#160;` 还原后逐片断言） |
|---|---|---|
| `tui-shell.svg` | TUI 启动加载壳（100 宽） | 完整 7 行稿一字形、无旧 iCode 片段；标题 `AIxCoding v0.35.1` |
| `chat-welcome-140.svg` / `chat-welcome-90.svg` | Chat 空态（140/90 宽） | 上游 CHAT_LOGO 原样（`▀██████▀` 在）、新 TUI_LOGO 片段不在 |
| `workflow-welcome-140.svg` | Workflow 空态 140 宽 | 完整上游 Workflow 字形（`▄███▄▀█▄` 在） |
| `workflow-welcome-90.svg` | Workflow 空态 90 宽 compact | 仅 compact 文本 "Workflow"，整幅字形不在 |
| `serve-banner.svg` | serve 终端 banner（Rich record） | 稿二字形在、全图零 `▀` |
| `serve-splash.html` | serve 浏览器 splash（实跑 8321 抓取） | 新 TUI_LOGO 片段在、`chrys-serve-logo` 类名在 |

六项断言全 PASS（临时核对脚本输出在案）。实跑侧：mock 7777/7778 监听正常；**GBK 编码
stdout 下 serve（8321）启动未崩、监听正常**（`PYTHONIOENCODING=gbk` 实跑窗口，banner 经
`on_startup` console.print 直出，若含 `▀` 必崩死）。auth 登录页与 splash 同源（同一
`TUI_LOGO` 常量 + `html.escape` 注入），行为由
`test_auth_required_protects_tui_and_websocket_until_login` 动态断言覆盖；未单独起
auth 实例截图。

**责任人终验（2026-11-10）：通过**——TUI 实跑（启动壳/Chat/Workflow 宽窄两态）、serve
banner、splash 全部确认无问题。附注：Workflow 面板调窄后的 compact 回退文本随会话语言
本地化（en="Workflow"、zh-Hans="工作流"，`panel.py:159` `MODE_WORKFLOW` i18n 渲染 +
`refresh_localization` 动态刷新，上游既有机制、本批零改动；上游测试断言与本批 90 宽 SVG
探针均按 `locale="en"` 环境，责任人中文会话显示"工作流"符合预期）。

## 遗留与后续

- 两份 design 待 R10 重签：本批 design（实施修订：登记锚定稿、C062 迁移、4 处动态引用
  跟改、定制测试跟改）与 branding-and-command design（C062 现役行删除 + 指向注记 +
  C064 removal 改随 C146）。头部"已确认"未动以保登记生效（先例：environment-config /
  catalog-sync 同模式）。
- 外部双 AI 评审（GLM-5.3 / CodeBuddy，2026-11-10）已完成，处置见 self-review.md
  「2026-11-10 外部评审结论」节：F1/F3 已修复并复跑门禁、F2 经反证不成立（代码零改动）、
  F4/F5 留责任人拍板。提交流程（特性分支 + PR）待重签与人工核对闭环后启动；提交前
  复查清单（代码/文档/测试/签认/生成物）逐项核对。
