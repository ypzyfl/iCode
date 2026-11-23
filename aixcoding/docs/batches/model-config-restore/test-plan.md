# 测试计划：模型配置恢复官方可编辑

> 结构：定制套件（重写/新增）+ 上游恢复面 + 真机手工面三层。

## 1. 定制套件（aixcoding/tests/catalog/test_read_only_gate.py，重写 9 用例）

| # | 用例 | 断言 |
|---|---|---|
| T1 | idle 打开可写 | `_read_only is False`（`_config_read_only()` 门限恢复） |
| T2 | busy 四态参数化只读 | agent_running / execution_busy / submit_active / 全三者 `_read_only is True` |
| T3 | 指示器 configure 入口 | 走真实 open 链，idle 可写 |
| T4 | 官方文案回归 | fallback 含 "Agent is running"、不含 "centrally managed" |
| T5 | F4 绑定存在 | `("f4", "models_config")` ∈ MainScreen.BINDINGS |
| T6 | 列表过滤 | mock `server_owned_profile_ids`，侧栏仅自建 |
| T7 | 删除拒绝 | mock 判定为 True，`_do_delete` 抛 `ConfigError` |
| T8 | 保存拒绝 | 同上，`_save_only` 抛 `ConfigError` |
| T9 | （ACP 两用例见 §2） | — |

## 2. ACP 契约（tests/app/acp/test_session_manager_profiles.py +2）

| # | 用例 | 断言 |
|---|---|---|
| T9 | write 拒绝下发 | mock 判定 True，`AcpSessionError` match "managed by the server catalog" |
| T10 | delete 拒绝下发 | 同上 |

## 3. 上游恢复面（5 文件整文件回 v0.35.2 官方版）

test_model_config / test_model_picker / test_model_indicator_wiring /
test_chrys_footer / test_bindings——官方版断言即本批验收（F4 在、manage 条目
在、快照标签、官方文案），不另写。

## 4. 真机手工面（已执行，用户签认）

F4 打开且列表无下发模型；切换列表含下发模型可选用并发消息连通；自建新建/
编辑/删除；轮次运行中 F4 只读提示；picker"管理模型…"入口可达；ACP 面
（内网联测留待真环境）。

## 5. 门禁

定向子集 + core 范围并行 + ruff 双检 + ty 三平台（全量 src/chrys）+ i18n
三连与 oracle + gen --strict / R2 / R3 / closure。
