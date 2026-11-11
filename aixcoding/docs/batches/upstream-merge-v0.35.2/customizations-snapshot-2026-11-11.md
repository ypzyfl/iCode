# 定制点登记全景（report，实时对账视图）

> 事实源 = 代码 marker + 已签认 design.md 登记表；本视图为衍生输出（`gen_customizations.py --report`），
> 勿编辑、不落盘。升级批次可将本输出附入 verification.md 作时点快照。

## 定制点（109 行）

| id | 落点 | marker 行 | marker | 归属模块 | removal_condition | 来源 |
| --- | --- | --- | --- | --- | --- | --- |
| C001 | AGENTS.md | 6 | AIxCoding entry point to the customization standards (aixco… | aixcoding/docs/standards | 〔常驻〕随 fork 定制体系存续，仅改址/退役时提请裁决 | aixcoding/docs/batches/agents-md-note/design.md |
| C002 | pyproject.toml | 245 | AIxCoding tui: user-visible text is Chinese-only constants … | tui | 〔政策变更〕ADR-0010 政策变更（定制文案回归上游 i18n 体系） | aixcoding/docs/batches/tui/design.md |
| C003 | pyproject.toml | 249 | AIxCoding custom tests: fake creds/asserts, frozen Chinese-… | aixcoding/tests | 〔目录退役〕aixcoding/tests 目录退役；或豁免迁 pyproject per-file-ignores 目录级（既有遗留待办，届时触发上游 R2 报批） | aixcoding/docs/batches/ruff-test-exemptions/design.md |
| C004 | src/chrys/app/cli/app.py | 177 | AIxCoding customizations: startup hooks on every icode invo… | src/chrys/app/aixcoding/startup/__init__.py | 〔消费者退役〕接线消费者全部退役，或上游提供官方插件/hook 机制可承载 | aixcoding/docs/batches/auth-logging/design.md |
| C005 | src/chrys/app/tui/chrys.tcss | 191 | AIxCoding tui: account login badge (signed-in / logged-out … | tui | 〔上游等价〕上游原生提供账号登录态徽标 UI，且经对比分析确认可对接内部认证体系与交互/文案需求（名似≠等价，逐点对比后提请裁决） | aixcoding/docs/batches/tui/design.md |
| C006 | src/chrys/app/tui/screens/diff/screen.py | 1330 | AIxCoding tui: no account badge on the diff screen | tui | 〔上游等价〕随 C005 主徽标一并裁决（diff 屏无徽标特例） | aixcoding/docs/batches/tui/design.md |
| C007 | src/chrys/app/tui/screens/logs/screen.py | 72 | AIxCoding diagnostics: F6 tab for custom-layer logs (src/ch… | src/chrys/kernel/aixcoding/diagnostics | 〔上游等价〕上游日志面板原生支持第三方模块分层展示（MODULE_ORDER 类机制）且可承载定制层日志 | aixcoding/docs/batches/diagnostics/design.md |
| C008 | src/chrys/app/tui/screens/main/commands.py | 14 | AIxCoding tui: /login /logout texts | tui | 〔上游等价〕上游原生提供登录/登出命令（含 man 索引文案）且可对接内部认证 | aixcoding/docs/batches/tui/design.md |
| C009–C012 | src/chrys/app/tui/screens/main/commands.py | 531, 576, 615, 979 | AIxCoding tui: /login /logout ×4 | tui | 〔上游等价〕同 C008（注册表孪生组，随命令定制整体裁决） | aixcoding/docs/batches/tui/design.md |
| C013 | src/chrys/app/tui/screens/main/screen.py | 563 | AIxCoding tui: silent login check | tui | 〔上游等价〕上游原生提供启动期静默登录校验机制且可对接 | aixcoding/docs/batches/tui/design.md |
| C014–C015 | src/chrys/app/tui/screens/main/screen.py | 922, 965 | AIxCoding tui: /login /logout ×2 | tui | 〔上游等价〕同 C008 | aixcoding/docs/batches/tui/design.md |
| C016 | src/chrys/app/tui/screens/main/screen.py | 1645 | AIxCoding tui: validate any stored login credential silentl… | tui | 〔上游等价〕随 C013 一并裁决（凭据校验入口） | aixcoding/docs/batches/tui/design.md |
| C017 | src/chrys/app/tui/screens/main/screen.py | 1658 | AIxCoding tui: cancel the startup silent login check (app t… | tui | 〔上游等价〕随 C013 一并裁决（teardown 取消登记） | aixcoding/docs/batches/tui/design.md |
| C018 | src/chrys/app/tui/widgets/chrome/app_header.py | 98 | AIxCoding tui: account badge toggle | tui | 〔上游等价〕随 C005 一并裁决 | aixcoding/docs/batches/tui/design.md |
| C019 | src/chrys/app/tui/widgets/chrome/app_header.py | 121 | AIxCoding tui: account badge -- an overlay-docked sibling d… | tui | 〔上游等价〕随 C005 一并裁决（overlay sibling 结构） | aixcoding/docs/batches/tui/design.md |
| C020 | src/chrys/app/tui/widgets/chrome/app_header.py | 133 | AIxCoding tui: initial badge paint | tui | 〔上游等价〕随 C005 一并裁决（初始绘制） | aixcoding/docs/batches/tui/design.md |
| C021 | src/chrys/service/llm/wire_client.py | 114 | AIxCoding auth: send-time login ``token`` header for the LLM | auth | 〔上游等价〕上游 wire_client 原生支持从登录会话/凭据存储注入请求头，且满足内部凭据管理需求（对比确认后提请裁决） | aixcoding/docs/batches/auth/design.md |
| C022 | src/chrys/service/llm/wire_client.py | 121 | AIxCoding auth: helper path updated by ADR-0011 tier migrat… | auth | 〔上游等价〕随 C021 一并裁决（ADR-0011 路径注释行随实现迁移） | aixcoding/docs/batches/auth/design.md |
| C023 | tests/app/tui/behaviors/test_buddy_petting.py | 139 | AIxCoding tui: /login /logout stubs | tui | 〔随组〕登录 UI 定制整体淘汰获裁时一并移除（测试支撑） | aixcoding/docs/batches/tui/design.md |
| C024 | tests/app/tui/i18n/test_command_suggestions_i18n.py | 172 | AIxCoding tui: /man index expectation includes /login /logo… | tui | 〔随组〕同 C023（/man 索引期望） | aixcoding/docs/batches/tui/design.md |
| C025 | tests/app/tui/i18n/test_toast_notifications.py | 129 | AIxCoding tui: /login /logout stubs | tui | 〔随组〕同 C023 | aixcoding/docs/batches/tui/design.md |
| C026 | tests/app/tui/screens/main/test_screen_lifecycle.py | 54 | AIxCoding tui: startup check handle | tui | 〔随组〕同 C023（生命周期句柄） | aixcoding/docs/batches/tui/design.md |
| C027 | tests/foundation/i18n/_catalog_oracle_ids.py | 426 | AIxCoding tui: /login /logout keys | tui | 〔机制退役〕借壳 key 机制退役（登录文案改上游 msg() 体系承载，或登录功能下线） | aixcoding/docs/batches/tui/design.md |
| C029 | tests/support/tui_helpers.py | 1255 | AIxCoding tui: /login /logout stubs for the screen double | tui | 〔随组〕同 C023（screen double 桩） | aixcoding/docs/batches/tui/design.md |
| C030 | src/chrys/service/profiles/models/registry.py | 39 | AIxCoding catalog: background sync thread replaces the whol… | catalog | 〔上游等价〕上游自带跨线程安全且整替语义有官方通道，经对比分析确认可迁移（提请裁决） | aixcoding/docs/batches/catalog-sync/design.md |
| C031 | src/chrys/service/profiles/models/registry.py | 153 | AIxCoding catalog: install a same-version snapshot (short c… | catalog | 〔随组〕随 C030 一并裁决 | aixcoding/docs/batches/catalog-sync/design.md |
| C034 | src/chrys/app/tui/app.py | 1499 | AIxCoding catalog: startup sync + poll wiring — one blockin… | catalog | 〔上游等价〕上游提供启动期目录同步挂点，或部署形态取消本地目录同步 | aixcoding/docs/batches/catalog-sync/design.md |
| C035 | src/chrys/app/tui/screens/main/config_actions.py | 283 | AIxCoding catalog: centrally managed, always read-only — | catalog | 〔政策变更〕档案集中管理政策取消 | aixcoding/docs/batches/catalog-sync/design.md |
| C036 | src/chrys/app/tui/screens/main/screen.py | 299 | AIxCoding catalog: F4 model-management entry disabled — the… | catalog | 〔政策变更〕随 C035 一并裁决 | aixcoding/docs/batches/catalog-sync/design.md |
| C037 | src/chrys/app/tui/screens/main/screen.py | 874 | AIxCoding catalog: live label via registry — a catalog sync… | catalog | 〔随组〕随同步特性整体裁决 | aixcoding/docs/batches/catalog-sync/design.md |
| C038 | src/chrys/app/tui/screens/models/picker.py | 97 | AIxCoding catalog: "Manage models…" entry disabled — the pi… | catalog | 〔政策变更〕随 C035 一并裁决 | aixcoding/docs/batches/catalog-sync/design.md |
| C040 | src/chrys/app/tui/screens/models/screen.py | 75 | AIxCoding catalog: read-only notice wording — read-only is … | catalog | 〔政策变更〕随 C035 一并裁决 | aixcoding/docs/batches/catalog-sync/design.md |
| C041 | src/chrys/app/tui/screens/main/model_indicator.py | 117 | AIxCoding catalog: label tracks the live registry — a catal… | catalog | 〔随组〕随同步特性整体裁决 | aixcoding/docs/batches/catalog-sync/design.md |
| C044 | tests/app/tui/screens/test_model_picker.py | 79 | AIxCoding catalog: manage entry disabled — profiles only. | catalog | 〔政策变更〕随 C038（manage 入口恢复时反断言随之撤除） | aixcoding/docs/batches/catalog-sync/design.md |
| C045 | tests/app/tui/screens/test_model_picker.py | 141 | AIxCoding catalog: manage routing via synthesized event — t… | catalog | 〔随组〕随 C038/C044；manage 入口恢复时还原为真实选项驱动，协议分支整体删除的清理批次再退役 | aixcoding/docs/batches/catalog-sync/design.md |
| C046 | tests/app/tui/screens/test_model_indicator_wiring.py | 366 | AIxCoding catalog: registry is the live name source — a cat… | catalog | 〔随组〕随 C037/C041；live label 语义恢复快照时回改 | aixcoding/docs/batches/catalog-sync/design.md |
| C047 | tests/app/tui/screens/test_model_config.py | 736 | AIxCoding catalog: centrally managed notice assertion — rea… | catalog | 〔随组〕随 C040；notice 文案恢复时回改 | aixcoding/docs/batches/catalog-sync/design.md |
| C048 | tests/app/tui/behaviors/test_chrys_footer.py | 52 | AIxCoding catalog: F4 footer key removed — assertions no lo… | catalog | 〔随组〕随 C036；F4 入口恢复时期望随之回补 | aixcoding/docs/batches/catalog-sync/design.md |
| C049 | tests/app/tui/i18n/test_bindings.py | 420 | AIxCoding catalog: f4 binding retired — the provenance set … | catalog | 〔随组〕随 C036/C048；F4 声明恢复时条目回补 | aixcoding/docs/batches/catalog-sync/design.md |
| C050 | src/chrys/foundation/branding.py | 7 | AIxCoding branding: display name and user command | branding | 品牌政策变更时逐点裁决 | aixcoding/docs/batches/branding-and-command/design.md |
| C051 | src/chrys/service/context/providers/documentation.py | 21 | AIxCoding branding: LLM prompt self-reference | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C052 | src/chrys/service/context/providers/documentation.py | 59 | AIxCoding branding: prompt tail self-reference | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C053 | src/chrys/service/context/providers/context_management.py | 61 | AIxCoding branding: reminder instructions self-reference | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C054 | src/chrys/service/tools/builtins/web/hosted.py | 21 | AIxCoding branding: hosted-tools notice placeholder | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C055 | src/chrys/service/tools/builtins/web/hosted.py | 61 | AIxCoding branding: bind app for hosted-tools notice | branding | 随 C054 | aixcoding/docs/batches/branding-and-command/design.md |
| C056 | src/chrys/service/tools/builtins/filesystem.py | 61 | AIxCoding branding: read tool description | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C057 | src/chrys/service/skills/adapter.py | 49 | AIxCoding branding: skill trust notice placeholder | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C058 | src/chrys/service/skills/provider.py | 141 | AIxCoding branding: bind app for skill prompt | branding | 随 C057 | aixcoding/docs/batches/branding-and-command/design.md |
| C059 | src/chrys/foundation/observability/setup.py | 180 | AIxCoding branding: OTLP error message | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C060 | src/chrys/service/profiles/agents/builtins/Code.yaml | 6 | AIxCoding branding: built-in agent self-reference | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C061 | src/chrys/service/profiles/agents/builtins/QA.yaml | 6 | AIxCoding branding: built-in agent self-reference | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C063 | tests/app/cli/test_app.py | 443 | AIxCoding branding: sole command follows APP_COMMAND | branding | 随 C050/C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C064 | tests/app/cli/test_serve.py | 1851 | AIxCoding branding: banner assertion | branding | 随 C146 | aixcoding/docs/batches/branding-and-command/design.md |
| C065-C078 | tests/app/tui/terminal/test_program_status.py | 107, 154, 240, 271, 310, 385, 634, 649, 666, 709, 792, 807, 866, 890 | AIxCoding branding: OSC app name assertions ×14 | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C079-C081 | tests/app/tui/terminal/test_program_status_lifecycle.py | 65, 150, 231 | AIxCoding branding: OSC app name assertions ×3 | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C082 | tests/app/tui/widgets/test_hook_run_list.py | 431 | AIxCoding branding: hooks empty-state text | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C083-C085 | tests/app/tui/screens/main/test_hooks_panel_flow.py | 217, 356, 754 | AIxCoding branding: hooks panel states ×3 | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C086 | tests/app/tui/i18n/test_command_suggestions_i18n.py | 153 | AIxCoding branding: man page branding | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C087 | tests/app/tui/i18n/test_modal_screens.py | 236 | AIxCoding branding: exit man page | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C088 | tests/app/cli/test_tui_startup.py | 40 | AIxCoding branding: startup message | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C089 | tests/app/cli/test_run.py | 1701 | AIxCoding branding: offline error text | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C090 | tests/orchestration/engine/build/test_lifecycle_hooks.py | 849 | AIxCoding branding: soft-restart warning | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C091-C093 | tests/service/mcp/test_progressive.py | 295, 350, 428 | AIxCoding branding: reserved tool conflict text ×3 | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C094 | tests/orchestration/invoker/test_runtime_recipes.py | 210 | AIxCoding branding: prompt documentation title | branding | 随 C051/C052 | aixcoding/docs/batches/branding-and-command/design.md |
| C095 | tests/orchestration/workflows/test_documentation.py | 51 | AIxCoding branding: prompt documentation title absent | branding | 随 C051/C052 | aixcoding/docs/batches/branding-and-command/design.md |
| C096 | tests/orchestration/invoker/test_documentation.py | 87 | AIxCoding branding: prompt documentation title absent | branding | 随 C051/C052 | aixcoding/docs/batches/branding-and-command/design.md |
| C097 | tests/app/cli/test_approvals.py | 73 | AIxCoding branding: approval usage line | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C098 | tests/app/cli/test_workflow.py | 123 | AIxCoding branding: workflow usage line | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C099 | tests/app/cli/test_profiles.py | 221 | AIxCoding branding: profiles usage line | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C100-C101 | tests/app/cli/test_hooks.py | 220, 239 | AIxCoding branding: hook validate hint text ×2 | branding | 随 C050 | aixcoding/docs/batches/branding-and-command/design.md |
| C102 | tests/orchestration/engine/build/test_agent_builder_rollback.py | 317 | AIxCoding branding: hosted warning bound args | branding | 随 C054/C055 | aixcoding/docs/batches/branding-and-command/design.md |
| C103 | pyproject.toml | 80 | AIxCoding branding: wheel command entry | branding | 命令品牌政策变更时裁决 | aixcoding/docs/batches/branding-and-command/design.md |
| C104 | scripts/check_wheel.py | 42 | AIxCoding branding: wheel command probe | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C105 | scripts/build.sh | 303 | AIxCoding branding: PyApp output name | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C106 | scripts/build.ps1 | 452 | AIxCoding branding: PyApp output name | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C107-C110 | .github/workflows/cd.yml | 108, 349, 466, 516 | AIxCoding branding: release command artifacts ×4 | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C111-C112 | scripts/install.sh | 143, 237 | AIxCoding branding: POSIX install command contract ×2 | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C113-C114 | scripts/install.ps1 | 104, 203 | AIxCoding branding: Windows install command contract ×2 | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C115 | src/chrys/app/installer.py | 39 | AIxCoding branding: legacy command process recognition | branding | 旧版迁移支持退役时裁决 | aixcoding/docs/batches/branding-and-command/design.md |
| C116 | src/chrys/app/installer.py | 549 | AIxCoding branding: legacy alias migration hook | branding | 旧版迁移支持退役时裁决 | aixcoding/docs/batches/branding-and-command/design.md |
| C117 | src/chrys/app/uninstaller.py | 142 | AIxCoding branding: legacy alias uninstall hook | branding | 旧版迁移支持退役时裁决 | aixcoding/docs/batches/branding-and-command/design.md |
| C118 | src/chrys/service/agent_middleware/control/approval.py | 66 | AIxCoding branding: approval command text | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C119-C124 | tests/app/test_install_scripts.py | 182, 252, 318, 587, 655, 775 | AIxCoding branding: install script contract tests ×6 | branding | 随 C111-C114 | aixcoding/docs/batches/branding-and-command/design.md |
| C125-C127 | tests/app/test_installer.py | 615, 631, 692 | AIxCoding branding: legacy alias migration tests ×3 | branding | 随 C115-C116 | aixcoding/docs/batches/branding-and-command/design.md |
| C128-C129 | tests/app/test_uninstaller.py | 166, 177 | AIxCoding branding: legacy alias uninstall tests ×2 | branding | 随 C117 | aixcoding/docs/batches/branding-and-command/design.md |
| C130 | AGENTS.md | 3 | AIxCoding branding: development entry facts | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C131 | AGENTS.md | 32 | AIxCoding branding: development command examples | branding | 随 C103 | aixcoding/docs/batches/branding-and-command/design.md |
| C132 | pyproject.toml | 247 | AIxCoding catalog: full-width Chinese punctuation (approved… | catalog | 〔目录退役〕该 service 定制目录退役，或中文文案回到上游 i18n 体系且豁免不再必要 | aixcoding/docs/batches/catalog-auth-gating/design.md |
| C133 | tests/service/tools/web/test_tools.py | 221 | AIxCoding branding: keenable title assertion | branding | 随 C050（品牌政策变更时逐点裁决） | aixcoding/docs/batches/upstream-merge-v0.33.0/design.md |
| C134 | tests/app/tui/screens/test_models_dialog_deletion.py | 130 | AIxCoding catalog: upstream deletes profiles in the local d… | catalog | 〔随组〕catalog 只读管控语义整体淘汰获裁时恢复上游测试（测试支撑） | aixcoding/docs/batches/upstream-merge-v0.33.0/design.md |
| C135 | tests/app/tui/screens/test_prompt_shortcut_send.py | 1216 | AIxCoding catalog: local model dialog send-in-flight case d… | catalog | 〔随组〕catalog 只读管控语义整体淘汰获裁时恢复上游 models 参数（测试支撑） | aixcoding/docs/batches/upstream-merge-v0.33.0/design.md |
| C136 | tests/app/tui/screens/test_manual_reload.py | 189 | AIxCoding catalog: upstream opens the local model dialog vi… | catalog | 〔随组〕catalog 只读管控语义整体淘汰获裁时恢复上游测试（测试支撑） | aixcoding/docs/batches/upstream-merge-v0.34.0/design.md |
| C137 | tests/app/tui/screens/test_manual_reload.py | 229 | AIxCoding catalog: upstream deletes the default profile in … | catalog | 〔随组〕同 C136 | aixcoding/docs/batches/upstream-merge-v0.34.0/design.md |
| C138 | tests/app/tui/screens/test_reload_profiles.py | 117 | AIxCoding catalog: upstream edits models in the local edito… | catalog | 〔随组〕同 C136 | aixcoding/docs/batches/upstream-merge-v0.34.0/design.md |
| C139 | tests/service/extensions/test_discovery.py | 74 | AIxCoding branding: extension skip message assertion | branding | 随 C050（品牌政策变更时逐点裁决） | aixcoding/docs/batches/upstream-merge-v0.34.0/design.md |
| C140 | src/chrys/orchestration/startup.py | 220 | AIxCoding guard: install bundled security guard hooks (src/… | src/chrys/kernel/aixcoding/guard | 〔上游机制替代〕上游自带 hook 规则包分发/安装机制，或安全护栏特性整体退役（届时按 UPGRADE-RUNBOOK §5 淘汰检查呈报裁决） | aixcoding/docs/batches/guard-hooks/design.md |
| C141 | pyproject.toml | 190 | AIxCoding guard: bundled rule pack lint profile (src/chrys/… | src/chrys/kernel/aixcoding/guard/pack | 〔上游机制替代〕payload 最低解释器提升到 3.14 且文案改为 ASCII 后摘除；或护栏整体退役时摘除 | aixcoding/docs/batches/guard-hooks/design.md |
| C142 | .gitattributes | 23 | AIxCoding guard: guardctl.cmd is invoked by cmd.exe; keep C… | guard | 〔上游重排〕`.gitattributes` 不再需要单独行尾声明（如上游统一声明 `*.cmd`） | aixcoding/docs/batches/guard-switches/design.md |
| C143 | tests/service/agent_middleware/test_extension_tool_hooks.py | 224 | AIxCoding branding: extension after_tool failure note asser… | branding | 随 C050（品牌政策变更时逐点裁决） | aixcoding/docs/batches/upstream-merge-v0.35.1/design.md |
| C144 | tests/orchestration/test_startup.py | 122 | AIxCoding branding: invalid proxy warning assertion | branding | 随 C050（品牌政策变更时逐点裁决） | aixcoding/docs/batches/upstream-merge-v0.35.1/design.md |
| C145 | src/chrys/app/tui/util/logo.py | 5 | AIxCoding branding: TUI welcome wordmark | branding | 〔品牌政策〕随 C050：品牌字形再次变更时逐点裁决 | aixcoding/docs/batches/logo-branding/design.md |
| C146 | src/chrys/app/cli/serve.py | 1134 | AIxCoding branding: GBK-safe serve banner | branding | 〔品牌政策〕随 C145 | aixcoding/docs/batches/logo-branding/design.md |
| C147-C150 | tests/app/cli/test_serve.py | 315, 1147, 1217, 1257 | AIxCoding branding: logo assertions track TUI_LOGO ×4 | branding | 〔品牌政策〕随 C145 | aixcoding/docs/batches/logo-branding/design.md |
| C151-C152 | tests/app/cli/test_serve.py | 1873, 1885 | AIxCoding branding: banner GBK assertions ×2 | branding | 〔品牌政策〕随 C146 | aixcoding/docs/batches/logo-branding/design.md |
| C153 | src/chrys/service/llm/sdk_openai.py | 22 | AIxCoding auth: tolerate a credential-free client (aixcodin… | aixcoding/docs/batches/llm-keyless-sdk-auth | 〔目录退役〕上游 SDK 移除/改写 `_validate_headers` 校验点使覆写失效，或网关与目录下发保证 profile 恒有凭证使无凭证场景不复存在 | aixcoding/docs/batches/llm-keyless-sdk-auth/design.md |
| C154 | pyproject.toml | 134 | AIxCoding manual bundle: wheel docs source key (user-manual… | manual | 〔机制替代〕上游提供手册数据源配置化能力，或手册定制淘汰回归纯上游版本 | aixcoding/docs/batches/user-manual/design.md |
| C155 | scripts/check_wheel.py | 146 | AIxCoding manual bundle: compare against the fork-owned man… | manual | 〔机制替代〕同 C154（两点同生共死） | aixcoding/docs/batches/user-manual/design.md |
| C156 | tests/foundation/test_documentation.py | 79 | AIxCoding manual bundle: source key follows the fork-owned … | manual | 〔机制替代〕同 C154（契约随捆绑源同生共死） | aixcoding/docs/batches/user-manual/design.md |
| C157 | pyproject.toml | 182 | AIxCoding manual bundle: the manual is delivered user-facin… | manual | 〔机制替代〕上游把交付文档纳入格式化治理并提供正式排除通道，或手册定制淘汰 | aixcoding/docs/batches/user-manual/design.md |

## 孤儿登记（0）

- （无。）

## 退役记录（7，id 永不复用）

- C028（tests/foundation/i18n/test_catalog_oracle.py）— aixcoding/docs/batches/upstream-merge-v0.35.1/design.md
- C032（src/chrys/foundation/config/settings.py）— aixcoding/docs/batches/environment-config/design.md
- C033（src/chrys/foundation/config/process_settings.py）— aixcoding/docs/batches/environment-config/design.md
- C039（src/chrys/app/tui/screens/settings/layout.py）— aixcoding/docs/batches/environment-config/design.md
- C042（tests/foundation/i18n/_catalog_oracle_ids.py）— aixcoding/docs/batches/environment-config/design.md
- C043（tests/foundation/i18n/test_catalog_oracle.py）— aixcoding/docs/batches/environment-config/design.md
- C062（src/chrys/app/cli/serve.py）— aixcoding/docs/batches/logo-branding/design.md

## 标记豁免（无法加注释的格式；源：`aixcoding/tools/_common.py::MARKER_EXEMPTIONS`）

| 文件 | 改动概述 | 依据 |
| --- | --- | --- |
| `tests/architecture/trajectory_wait_manifest.json` | 生成产物：wait 节点清单随模块路径刷新（`uv run python -m tests.support.trajectory_wait_inventory`） | aixcoding/docs/batches/tier-migration/design.md |
| `locales/chrys.pot` | 生成产物：i18n extract 条目（借壳 key 随 msg 定义处生成，R2 表 7 号） | aixcoding/docs/batches/tui/design.md |
| `locales/zh-Hans/LC_MESSAGES/chrys.po` | 登记产物：po 中文条目（msgstr=fallback 复制，ADR-0010 细则 2，R2 表 8 号） | aixcoding/docs/batches/tui/design.md |
