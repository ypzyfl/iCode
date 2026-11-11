# 测试方案：TUI 欢迎字符画品牌化（logo-branding）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。
> 依据：本目录 requirements.md 验收标准 5 条、design.md（已签认 2026-11-10）R2 清单、
> 「字稿定稿」两份字稿与定制点登记预告（C145/C146 新增、C062 退役、C064 内容维护+扩两条）。

## 测试范围与策略

纯字面量替换批次，无新增业务逻辑与新增落点目录；测试分三层，静态契约不得替代行为验证：

1. **行为锚定（上游测试内，C064 孪生组）**：`tests/app/cli/test_serve.py` 既有
   `test_textual_serve_banner_is_aixcoding_branded` 跟改（ASCII 行断言 → 稿二对应行），
   并新增两条——真调上游符号、不 mock 被锚定符号本身（DEVELOPMENT.md §5）。新增两条带
   `# AIxCoding branding: banner GBK assertions` marker，独立登记 C151-C152（C064 为历史
   单 id、区间不可扩，不并入其孪生组）：
   - `test_textual_serve_banner_gbk_stdout_does_not_crash`：子进程
     `sys.stdout.reconfigure(encoding='gbk')`（语义等价 `PYTHONIOENCODING=gbk`，不依赖平台
     环境变量）下经 Rich `Console().print` 直出 `_icode_serve_logo()` 完整 banner，断言
     exit 0（复现路径 = serve `on_startup` 的 console.print 直出；`▀` 在 GBK 编码写入时
     必抛 `UnicodeEncodeError`，与终端/管道无关）。
   - `test_icode_serve_logo_avoids_upper_half_block`：静态断言 `_icode_serve_logo()` 输出
     不含 `▀`（U+2580），且块字符仅 `{▄,█}`——回归哨兵，未来换稿引入 `▀` 即红面。
   定制层同步跟改：`aixcoding/tests/branding/test_branding_runtime.py` 的 C062 锚定用例
   更名为 `test_c146_serve_banner_gbk_safe_block_aixcoding`，断言换为稿二行 + 无 `▀`。
2. **上游既有测试零跟改原样通过**（证明"零改动/自适应"承诺，不是跟改后通过）：
   `tests/app/tui/behaviors/test_startup_shell.py`（TUI_LOGO 断言全动态自适应，含 20 宽
   裁剪）、`tests/app/tui/screens/main/test_workflow_welcome.py`（`[:6]`/`[:8]`/90 宽
   compact 全原样）、`tests/app/tui/widgets/test_welcome_update_notice.py`、
   `tests/app/tui/widgets/test_loading_widgets.py`。
   另 `test_serve.py` 内 4 处硬编码旧 TUI_LOGO 片段断言（spacing / 登录页 / 两处
   clipboard）经 Smart Test 实证红面，改动态引用 `TUI_LOGO.splitlines()` 行片段
   （R2 已补记，与 `test_startup_shell` 同模式）；并按 F4 责任人裁决各加
   `# AIxCoding branding: logo assertions track TUI_LOGO` marker，登记 C147-C150
   （孪生组计数 4，`--strict` 对账）。
3. **静态契约与门禁**：`uv run python aixcoding/tools/gen_customizations.py --strict`
   0 error / 0 warning（C145/C146 登记、C062 退役对账）；`check_docs.py` OK；ruff /
   ruff format --check（全目录口径，含 md 内嵌代码块）；Smart Test 见手工节。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型（单元/契约/端到端/行为锚定） |
|---|---|---|
| 1. TUI_LOGO 为 AIxCoding 块字符字形；CHAT/WORKFLOW 与上游逐字一致；五个消费点实跑核对 | 字稿逐字比对（实施 diff = design「字稿定稿」稿一，CHAT/WORKFLOW 不出现在 diff 中）；`test_startup_shell.py`（启动壳行为锚定）+ `test_workflow_welcome.py`（Chat/Workflow 空态）；serve splash/登录页与五个消费点实跑见手工节 1-2 | 行为锚定 + 手工 |
| 2. 与既有上游测试断言兼容；test_workflow_welcome 零跟改；其余跟改走 R2 | 上述四个测试文件原样跑通（零跟改项以 `git diff` 无这些文件为证）；跟改仅 `test_serve.py` 一处（R2 表内） | 单元（既有套件） |
| 3. serve banner `{▄,█}`：CP936 不抛异常（新增）、无 `▀`（新增）、实跑截图 | `test_serve.py::test_textual_serve_banner_gbk_stdout_does_not_crash`（新增）；`test_serve.py::test_icode_serve_logo_avoids_upper_half_block`（新增）；截图见手工节 2 | 行为锚定 + 手工 |
| 4. marker 注释 + `gen_customizations.py --strict` 0/0 | `logo.py` 模块 marker×1（C145）、`serve.py` marker 文本更新（C062→C146）；`--strict` 实跑对账 | 契约 |
| 5. Smart Test 通过；serve 消费点冒烟一次 | `uv run python scripts/chrys_test.py --smart --paths src/chrys/app/tui/util/logo.py src/chrys/app/cli/serve.py tests/app/cli/test_serve.py`；serve 冒烟见手工节 2 | 端到端 + 手工 |

## 异常与降级路径

- **GBK/CP936 编码 stdout**：banner 完整输出不抛异常（核心新增测试；serve 启动崩死为本批
  修订 C062 的实证根因，防回归优先级最高）。CP936 仅 `▀` 不可编码，`▄`/`█` 安全（实测
  在案，见 design 宽度预算节）。
- **换稿回归**：未来任何字稿变更引入 `▀` → 无 `▀` 静态断言红面；textual-serve 渲染路径
  变化（bump 重审，上游注释要求）→ GBK 子进程测试红面。
- **窄终端**：20 宽裁剪语义由 `test_startup_shell` 既有参数化覆盖；新稿 51 列 ≤ 90 宽可用
  宽，居中不溢出；Chat/Workflow 零改动，无新增窄终端风险面。
- **浏览器 HTML**：两处 `html.escape(TUI_LOGO)` 注入 UTF-8 页面，块字符 HTML 安全（上游
  现状已实证）；serve 冒烟核对 splash 与登录页。
- **回滚**：纯字面量替换，revert 即完整回滚；C062 若走回退路径（保留 ASCII），两条新增
  GBK/无 `▀` 测试仍保留（对 ASCII 同样成立），防回归不断档。

## 手工验证步骤（若需）

1. **TUI 实跑**（独立可见 cmd 窗口，大写盘符）：
   `Start-Process cmd -ArgumentList '/k','set "AIXCODING_AUTH_ENVIRONMENT=local" && uv run aixcoding-cli' -WorkingDirectory 'D:\Tech\Github\huawei\iCode\fork\iCode-fork_2'`
   （mock 若未启动，登录态不影响启动壳与空态核对）。
   预期：启动加载壳显示 AIxCoding 块字符字形（51 列 × 7 行），无 iCode 残留；Chat 空态
   保持上游 Chat 原样；切 Workflow 空态——宽窗（≥140）显示完整 Workflow 字形、90 宽触发
   compact 文本 "Workflow"。逐点截图。
2. **serve 冒烟**：`uv run aixcoding-cli serve`（独立 cmd 窗口）——终端 banner 为稿二
   `{▄,█}` 字形（51 列 × 6 行 + 版本行）；再 `set "PYTHONIOENCODING=gbk"` 重启一次，
   预期启动不崩、banner 完整。浏览器打开 splash 核对新 TUI_LOGO；带 auth 参数启动核对
   登录页同字形。截图。
3. **门禁**：`gen_customizations.py --strict` 0/0；`check_docs.py` OK；ruff / ruff
   format --check 全目录口径通过。

以上结果记入 verification.md。
