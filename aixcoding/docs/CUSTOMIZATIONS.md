# 定制清单（CUSTOMIZATIONS）

<!-- manual-zone-start（人工维护区，生成脚本不触碰；DEVELOPMENT.md §8） -->
- 当前所基于的上游版本：0.31.0
- 最近一次升级完成日期：（随每次升级完成人工更新）
<!-- manual-zone-end -->

> 生成区由 `aixcoding/tools/gen_customizations.py` 自动生成（DEVELOPMENT.md §5：禁止手工维护
> 代码事实）；语义字段合并自已签认 design.md 的定制点登记预告表；`upstream_base` 取人工区
> 全局值（§8）。标记豁免（无法加注释的格式）在下方豁免表登记。

<!-- generated-zone-start -->
## 定制点

| id | paths | 标记 | 归属模块 | anchor | risk | reason | tests | removal_condition | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C001 | AGENTS.md:5 | AIxCoding entry point to the customization standards (aixcoding/docs/standards) | aixcoding/docs/standards | AGENTS.md 文档结构（正文段落，无符号依赖） | 低 | 待补 | 待补 | 待补 | aixcoding/docs/agents-md-note/design.md |
| C002 | src/chrys/app/tui/screens/logs/screen.py:67 | AIxCoding diagnostics: F6 tab for custom-layer logs (src/chrys/aixcoding/diagnostics) | src/chrys/aixcoding/diagnostics | `~/.chrys/` 目录约定（`get_platform().config_dir` 同源）；`logging` 标准机制 + `MODULE_ORDER`（R2 一行）；`chrys.app.cli.app:main` 入口签名；`faulthandler` / `sys.excepthook` / `threading.excepthook`（标准库）；版本/平台信息来源（`chrys.__init__` 与 platform 模块） | 低；低（面板）/零（落盘）；中（上游入口重构时需跟） | 待补 | 待补 | 待补 | aixcoding/docs/diagnostics/design.md |
| C003 | src/chrys/service/llm/clients.py:105 | AIxCoding auth: token header for the LLM gateway (auth migration design). | auth | `chrys.foundation.platform`（storage lazy import）+ httpx | 低（tier 1 自治包，升级零耦合） | 待补 | 待补 | 待补 | aixcoding/docs/auth/design.md |
| C004 | src/chrys/service/llm/wire_client.py:114 | AIxCoding auth: send-time token header for the LLM gateway | auth | `chrys.foundation.platform`（storage lazy import）+ httpx | 低（tier 1 自治包，升级零耦合） | 待补 | 待补 | 待补 | aixcoding/docs/auth/design.md |
| C005 | tests/architecture/test_layering.py:44 | AIxCoding diagnostics: custom layer registers at kernel tier — may depend only on foundation/kernel (src/chrys/aixcoding/diagnostics) | src/chrys/aixcoding/diagnostics | `~/.chrys/` 目录约定（`get_platform().config_dir` 同源）；`logging` 标准机制 + `MODULE_ORDER`（R2 一行）；`chrys.app.cli.app:main` 入口签名；`faulthandler` / `sys.excepthook` / `threading.excepthook`（标准库）；版本/平台信息来源（`chrys.__init__` 与 platform 模块） | 低；低（面板）/零（落盘）；中（上游入口重构时需跟） | 待补 | 待补 | 待补 | aixcoding/docs/diagnostics/design.md |
| C006 | tests/architecture/test_layering.py:89 | AIxCoding diagnostics: registered DAG edge exemption (src/chrys/aixcoding/diagnostics) | src/chrys/aixcoding/diagnostics | `~/.chrys/` 目录约定（`get_platform().config_dir` 同源）；`logging` 标准机制 + `MODULE_ORDER`（R2 一行）；`chrys.app.cli.app:main` 入口签名；`faulthandler` / `sys.excepthook` / `threading.excepthook`（标准库）；版本/平台信息来源（`chrys.__init__` 与 platform 模块） | 低；低（面板）/零（落盘）；中（上游入口重构时需跟） | 待补 | 待补 | 待补 | aixcoding/docs/diagnostics/design.md |
| C007 | tests/architecture/test_layering.py:245 | AIxCoding diagnostics: registered edge exemption (src/chrys/aixcoding/diagnostics) | src/chrys/aixcoding/diagnostics | `~/.chrys/` 目录约定（`get_platform().config_dir` 同源）；`logging` 标准机制 + `MODULE_ORDER`（R2 一行）；`chrys.app.cli.app:main` 入口签名；`faulthandler` / `sys.excepthook` / `threading.excepthook`（标准库）；版本/平台信息来源（`chrys.__init__` 与 platform 模块） | 低；低（面板）/零（落盘）；中（上游入口重构时需跟） | 待补 | 待补 | 待补 | aixcoding/docs/diagnostics/design.md |

## 标记豁免（无法加注释的格式）

| 文件 | 改动概述 | 依据 |
| --- | --- | --- |

（暂无。）

## 校验备注

- aixcoding/docs/auth/design.md: registration row `clients.py::_login_token()` has no matching marker (designed but not implemented yet, or attribution typo)
- aixcoding/docs/auth/design.md: registration row `wire_client.py::RequestHeaders.stamp()` token 注入` has no matching marker (designed but not implemented yet, or attribution typo)

<!-- generated-zone-end -->
