# 测试方案：护栏规则包调优（guard-rule-tuning）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

规则包为标准库零耦合引擎（子进程协议 `CHRYS_HOOK_PAYLOAD_FILE` / `CHRYS_HOOK_RESULT`），
无需 mock——三层验证全部跑**真实 hook 子进程**：

1. **自检**（`aixcoding/tests/guard/guard_pack_selftest.py`，unittest 经 `-m` 直跑）：
   107 条——每条存留规则一个正例、被删 7 条的「保持删除」回归、confirm→ask 映射与文案、
   网络黑名单组（后缀锚定 / 通配 / 网段开关 / 回环豁免 / 回环+危险端口放行（F2 裁决）/ 未列入放行）、Hook 写 `ask` 的
   两个入口子进程用例、开关层与安装器组。
2. **pytest 收集层**（`aixcoding/tests/guard/`）：安装器（出厂 enabled + 手改拉回）、
   hooks.yaml 模板锚、打包（wheel 单副本）、核心回归。
3. **部署验证**（`aixcoding/tests/guard/verify_guard_deployed.py`，`AIXCODING_GUARD_HOOKS_DIR`
   指向临时目录，不触碰本机真实配置）：71 条三态期望（block / ask / allow），含混合命中
   用例（P13/S29：confirm 与 block 同现时合成决策必须 block）。

上游 anchor（引擎 ask 兜底语义，design 假设 1）为上游公开契约：其单元行为由上游测试集
（`tests/service/hooks`）覆盖；本批次以部署验证＋手工 B16 锚定可观察结果，**不 mock 引擎**。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| 自检 107 条全过 | `guard_pack_selftest.py`（`-m` 直跑） | 端到端（真实子进程） |
| pytest 层全绿 | `test_guard_install.py::test_managed_entries_ship_enabled_and_pull_back_a_manual_disable` 等 | 契约 |
| 部署验证 71 条 0 失败 | `verify_guard_deployed.py`（临时目录安装） | 端到端 |
| 出厂 enabled: true / 33 条 · 开 32 · 关 1 | `test_anchors.py`（模板锚）＋ `guard_pack_selftest.py` 安装器组 ＋ 手工 `guardctl status` | 契约＋手工 |
| IN-05 confirm / T-NET-01 block | `guard_pack_selftest.py::test_confirm_maps_to_ask_by_default`、`NetworkGuardTests` ＋ 手工 `guardctl show` | 单元＋手工 |
| 已删 7 条保持删除 | `guard_pack_selftest.py::test_removed_high_false_positive_prompt_rules_stay_removed`、`::test_removed_high_false_positive_shell_rules_stay_removed`；verify P03/P04/P09、S11/S16/S27 | 回归 |
| headless 无法询问按 block 兜底 | 引擎事实（manager.py `_confirm`，上游测试集覆盖）＋ 手工 B16：`aixcoding-cli run "看看 ../../../../etc/passwd" -a Code` | 行为锚定＋手工 |
| 本机护栏开启 | 实装后 `guardctl.cmd status`（`%APPDATA%\chrys\hooks\guard\`） | 手工 |
| ruff / format / ty（三平台） | 命令见 requirements 验收标准 | 门禁 |

## 异常与降级路径

fail-closed 三路（每路有代码＋用例）：①决策文件写不出 → 非零退出 → `on_error: block`；
②子进程崩溃 / 超时 → `hooks.yaml` `on_error: block`；③规则非法 → `GuardError` →
`_fail_closed()`（IN-09，自检覆盖）。网络层降级：非法 CIDR 黑名单条目忽略不误拦（D7）；
状态文件损坏按出厂默认。confirm 无法询问 → 引擎 `unavailable` → block（design 假设 1）。

## 手工验证步骤（若需）

按《iCode 安全护栏测试用例》§1/§3 抽测，结果记 verification.md：

1. `guardctl.cmd status` → `规则：33 条 · 开 32 · 关 1`；`show IN-05` → confirm；
   `show T-NET-01` → block 且无词典参数。
2. B16 headless 兜底：`aixcoding-cli run "看看 ../../../../etc/passwd" -a Code` →
   无交互、请求被拦截（`ask` 为原因或 block 文案）。
3. E 组开关轮换抽测：`disable T-SHELL-01` → `rm -rf /tmp/testdir` 放行；`enable` 恢复确认框；
   测完 `guardctl reset` 回出厂。
