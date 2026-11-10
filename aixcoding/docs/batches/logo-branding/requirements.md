# 需求：TUI 欢迎字符画品牌化（logo-branding）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

上游 `src/chrys/app/tui/util/logo.py` 的三幅终端字符画为上游原版字样（已与上游 clone 逐字
核对一致，无任何批次触碰）：`TUI_LOGO` 拼出 "iCode"、`CHAT_LOGO` 拼出 "Chat"（首字母为
i/C 合体字形，亦可读作 "iChat"）、`WORKFLOW_LOGO` 拼出 "Workflow"。其中仅 `TUI_LOGO`
含 "iCode" 品牌词，与已定稿的 AIxCoding 品牌不一致；另两幅不含 iCode 品牌词（责任人裁决
均保持原样）。消费点：

- TUI 启动加载壳（`app/tui/app.py` `compose()`，等待主屏导入的约 1-2 秒）；
- Chat 欢迎空态（`app/tui/widgets/chat/chrome.py`）；
- Workflow 面板空态（`app/tui/widgets/workflow/panel.py`，compact 文本回退）；
- serve 浏览器 splash 注入（`app/cli/serve.py` `_inject_browser_serve_branding_logo`）；
- serve auth 登录页（`app/cli/serve.py` `_render_auth_login_page`）；
- serve 终端 banner（`app/cli/serve.py` `_icode_serve_logo`，C062 已为纯 ASCII `#` 形
  AIxCoding 字形，docstring 注明 "pure ASCII, safe on GBK consoles"）。

历史先例：branding-and-command（C4）当时明确决策"serve banner 不改为 block 字形"且不动
`logo.py`。本批按实测证据修订该决策（见 design 裁决记录）。

## 责任人裁决（2026-11-10，两轮 + 字形复核）

1. 走完整管线。
2. 字形形态 = **块字符**（两轮外部评审与 CP936/Rich 实测复核后定）。
3. `TUI_LOGO`："iCode" → "AIxCoding"。
4. `CHAT_LOGO`：**保持上游原样不动**（Chat/iChat 两种读法均不涉及 iCode 品牌）。
5. `WORKFLOW_LOGO`：**保持上游原样不动**（2026-11-10 字形复核修订：整幅即 "Workflow"，
   不含 iCode 品牌词；此前"去 iCode、保留 Workflow"裁决所依据的 "iCode Workflow" 解读
   系误判，切割方案撤销）。
6. serve 终端 banner：同批改为 `{▄,█}` 受限子集块字符（与 TUI 同族；**禁止 `▀`**——实测
   GBK 编码 stdout 下 Rich `console.print` 遇 `▀` 直接 `UnicodeEncodeError` 崩溃，serve
   启动崩死）。
7. 字稿由 AI 按上游风格组件起草、责任人逐轮考察定稿（原拟委托外部多模态 AI 加工，实际
   未启用）；定稿已回填 design「字稿定稿」节。

## 目标与非目标

- 目标：
  1. `logo.py` 唯一含品牌词的字画 `TUI_LOGO` 整幅替换为 "AIxCoding" 块字符字形；
     `WORKFLOW_LOGO`、`CHAT_LOGO` 零改动。五个 `logo.py` 消费点经既有常量引用自动生效，
     消费点代码零改动。
  2. serve 终端 banner 改 `{▄,█}` 子集：与 TUI 块字符视觉同族；编码层安全保持（`▄` A8 7B /
     `█` A8 80 CP936 可编码，实测 Rich 安全输出），并以两条针对性测试锚定。
  3. 字形形态不引入超出上游现状的兼容风险：上游现状已使用块字符服务全部消费点；TUI 消费
     点走 Textual 渲染/浏览器 HTML，不经 GBK console.print（CP936 实测仅 `▀` U+2580 不可
     编码）。
  4. 上游测试影响面最小：新字形与既有断言兼容（`test_workflow_welcome` 零跟改）；跟改全部
     走 R2 表呈批签认，禁止静默 deselect。
- 非目标：
  1. 不改 `CHAT_LOGO` 与 `WORKFLOW_LOGO`（含其消费点与 `[:6]`/`[:8]`/90 宽 compact 断言）。
  2. banner 只改函数体字形、docstring 与 marker（C062 修订为 `{▄,█}` 子集）；不改函数名
     `_icode_serve_logo`、f-string 结构与 `v{__version__}` 版本行（C4 design 既定）。
  3. 不改 serve HTML 注入逻辑与样式类名（`chrys-serve-logo` 不动）。
  4. 不做 logo 主题化、配置化、动画或 i18n 化。
  5. 不改品牌名与命令名（C4 已定稿）。

## 用户场景

1. `aixcoding-cli` 启动：加载壳显示 AIxCoding 块字符字形，无 "iCode" 字样残留。
2. Workflow 空态与 Chat 空态均保持上游原样（Workflow / Chat 字样，本无 iCode 残留）。
3. serve：终端 banner 为 `{▄,█}` 块字符子集（GBK 编码 stdout 下启动不崩）；浏览器 splash
   与 auth 登录页显示新 TUI_LOGO。
4. 窄终端下字形无换行错乱；GBK 编码 stdout 场景 serve 启动不因 banner 崩溃。

## 验收标准

- [ ] `TUI_LOGO` 为 "AIxCoding" 块字符字形；`CHAT_LOGO`、`WORKFLOW_LOGO` 与上游逐字一致；
  五个 `logo.py` 消费点实跑核对。
- [ ] 新字形与既有上游测试断言兼容（`tests/app/tui/behaviors/test_startup_shell.py`、
  `tests/app/tui/screens/main/test_workflow_welcome.py`、
  `tests/app/tui/widgets/test_welcome_update_notice.py`、
  `tests/app/tui/widgets/test_loading_widgets.py`）；其中 `test_workflow_welcome` 零跟改
  （`[:6]`/`[:8]`/90 宽 compact 断言原样通过）；其余跟改项以 R2 表呈批签认。
- [ ] serve banner 为 `{▄,█}` 子集字形：CP936 编码 stdout 下输出完整 banner 不抛异常
  （新增测试）；banner 不含 `▀`（新增静态断言）；实跑截图人工核对。
- [ ] `logo.py`/`serve.py` 改动带 `AIxCoding` marker 注释；`uv run python
  aixcoding/tools/gen_customizations.py --strict` 0 error / 0 warning。
- [ ] Smart Test（--paths 含 `logo.py`、`serve.py` 与全部跟改测试）通过；serve 消费点
  冒烟一次。

## 开放问题

- （无开放项：裁决全部闭合、两份字稿已定稿并回填 design「字稿定稿」节（2026-11-10），
  随 design 签认。）
