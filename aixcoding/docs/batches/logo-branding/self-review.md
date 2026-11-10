# 自评审记录：TUI 欢迎字符画品牌化（logo-branding）

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-10
- 确认意见：无特别意见
- 开发 AI：Kimi-K3.1-Pro / CodeBuddy
- 评审 AI：GLM-5.3 / CodeBuddy（独立第二评审 2026-11-10）

## 范围与规则核对

- **R1/R2**：上游触点恰为签认 R2 表三文件——`logo.py`（仅 `TUI_LOGO` 字面量 + 模块
  marker×1，`CHAT_LOGO`/`WORKFLOW_LOGO` 未出现在 diff）、`serve.py`（函数体/docstring/
  marker）、`tests/app/cli/test_serve.py`（C064 跟改 + 两条新增 + 4 处动态引用跟改）。
  定制目录维护：`test_branding_runtime.py` 用例更名 C146（非上游触点，已在 design 注明）。
- **marker 规范**：新增/更新注释均为单行英文 `AIxCoding` 开头无方括号格式；
  `gen_customizations.py --strict` 0/0 实证。
- **R10**：签认后正文修订（登记锚定稿、C062 迁移、4 处跟改补记）均以"待重签"注记
  留痕，头部未代填；branding-and-command 同模式（environment-config 先例）。
- **R11/ADR**：零新增依赖、零环境变量、零新 tier；不触发新 ADR（design §ADR 判定维持）。
- **目标契合**：无超范围改动——未动 serve HTML 注入逻辑/样式类名、函数名、f-string
  结构与版本行；`CHAT_LOGO`/`WORKFLOW_LOGO` 逐字未动。

## 实施期发现与处置（全部闭环）

1. **C062 退役首版写法被 strict 拦 6 error**：登记锚含"（实施定稿）"占位后缀被当 anchor
   前缀、C062 与 branding-and-command 现役行撞号。按 tombstone 先例修正：锚去后缀、
   原批次现役行删除 + 指向注记、C064 removal 改随 C146；strict 复跑 0/0。
2. **design 遗漏定制层锚定用例**：`test_branding_runtime.py` 的
   `test_c062_serve_banner_is_ascii_aixcoding` 断言 ASCII 旧稿——实施前自查发现，
   更名 `test_c146_serve_banner_gbk_safe_block_aixcoding` 并更新断言（design/test-plan
   补记）。教训：品牌批次的影响面扫描须含 `aixcoding/tests/` 定制套件，不止上游 tests/。
3. **4 处硬编码旧 TUI_LOGO 片段红面**（Smart Test 首跑实证，design 假设 1 预留）：
   spacing/登录页/两处 clipboard 断言改动态引用 `TUI_LOGO.splitlines()` 行片段
   （与 `test_startup_shell` 同模式），消除下次换稿再红；R2 已补记。**裁决已闭合
   （2026-11-10）**：维持动态引用，并按 F4 裁决加 marker 登记 C147-C150（见下评审结论节）。
4. **新增测试两处小修**：子进程 `from rich.console import Console` 导入路径笔误、
   `subprocess.run` 显式 `check=False`（PLW1510）。
5. **新增 GBK/无 `▀` 测试 marker 漏加**（责任人复核发现）：两条新增测试起初无 marker，
   strict 仍绿——工具只对账"有 marker 必登记"，发现不了"应加未加"。先补 C064 同锚
   （计数 1→3）被 strict 拦：C064 为历史单 id、C065-C078 已占用，区间不可扩；改独立锚
   `# AIxCoding branding: banner GBK assertions` 登记 C151-C152（计数 2），C064 计数不变。
   配套 `import TUI_LOGO` 行不加 marker（**责任人 2026-11-10 确认**）：登记锚为消费点
   断言（C147-C150），import 非独立定制锚点，孤儿 import 由 ruff F401 兜底（仓库无
   import 级 marker 先例）。

## 验证结论

Smart Test PASSED（12151 + architecture 506）、strict 0/0、check_docs OK、ruff/format
全目录绿；GBK serve 8321 实跑启动不崩。手工截图核对与 R10 重签见 verification.md
「遗留与后续」。

## 2026-11-10 外部评审结论（GLM-5.3 / CodeBuddy）：处置后通过

- 轮次：1 轮（评审 → 修复/反证 → 复跑门禁）。评审基线 `main_aixcoding_cli` @ `b8b02456`
  工作区未提交变更；逐项检查（R2/R1/R11/幻觉 API/吞错/vacuous test/对账/复跑）全过，
  含 CHAT_LOGO/WORKFLOW_LOGO 与上游 clone AST 逐字一致、字稿与 design 逐字符一致、
  GBK 测试注入 `▀` 反证 returncode=1 等脚本实证。
- blocker 处置：
  - F1（本文件缺标准头部，`check_docs.py` 2 error）→ 已按 §三 模板补头部，复跑
    `check_docs.py` OK（32 self-review）；verification.md 该行同步更正。
  - F2（banner 首行疑与稿二不符）→ **反证不成立，代码零改动**：Rich 剥 markup 保留标签
    后空格，实测输出首行 repr = `' ▄██▄  ▄██▄        ▄███▄'`，与 design 稿二首行逐字
    一致（1 前导空格），无错位。
- nit 处置：
  - F3（test-plan GBK 机制描述）→ 已改 `sys.stdout.reconfigure(encoding='gbk')` 表述。
  - F4（4 处动态引用无 marker）→ **按责任人裁决修复（2026-11-10）**：我方改动行须可
    追踪（防追上游漏判），4 处断言各加 `# AIxCoding branding: logo assertions track
    TUI_LOGO` 并登记 C147-C150（孪生组计数 4）；dynamic 引用本身维持不变。
  - F5（GBK 测试管道 stdout 未覆盖 legacy_windows_render 分支）→ **不修（责任人
    2026-11-10 拍板）**：编码层底座已锚定（`▀` 注入反证 returncode=1，评审实测），
    足以承载 `▀` 禁用约束。

## 遗留

- 视觉验证闭环：AI 截图 + 文本断言自核六项全 PASS，责任人 2026-11-10 实跑终验通过
  （含 compact 文案随 locale 本地化附注，见 verification）；两份 design 重签、PR 提交
  ——待责任人。
- `test_startup_shell` 等四个上游 TUI 测试文件零跟改由 Smart Test 原样通过佐证，
  `git diff` 中无这些文件（提交前 diff 复查项）。
- marker 完备性治理（评审模板检查项、design R2 列可执行化、可选 `gen_customizations`
  diff 感知扫描）已按责任人指示登记 `ROADMAP.md` §4 F 类独立候选事项（2026-11-10），
  不随本批实施；本批仅留存教训记录（第 5 条）。
