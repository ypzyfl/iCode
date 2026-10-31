# 验证记录：追上游 v0.32.2（upstream-merge-v0.32.2）

> 追加不删旧；本地验证证据落盘于此，CI 证据归属 PR checks 本身（§7）。

## 2026-10-31 升级实施（merge b817f004）

### 冲突点全清单与处理（决策交付物 1，已呈责任人裁决认可）

| # | 冲突 | 双方变动 | 处理 | 验证 |
|---|---|---|---|---|
| 1 | `tests/foundation/i18n/test_catalog_oracle.py:26`（C028） | 我方 2335→2405（tui 批次借壳 4 key：`aixcoding.tui.commands.description.login/.logout`、`aixcoding.tui.man.login.body/logout.body`，marker 在行尾）；上游 2335→2499（+94 msg，ids 族重组：新建 `_tool_card_catalog_oracle_ids.py` +171、`_hook_panel_catalog_oracle_ids.py` +32、`_settings_catalog_oracle_ids.py` +4、主文件迁出） | 2499+4=**2503**，marker 保留 | oracle `1 passed`（数量+集合逐项相等+全部条目已翻译三重断言）；pot 实测 2612−108(复数)−1(头部)=2503 吻合 |
| 2 | `chrys.mo`（豁免表在册） | 二进制，两侧各自重编（我方 2405 条版 / 上游 2499 条版） | po（auto-merge 干净）→ `i18n.py compile` 重编 = 2503 条 | `i18n.py check` 过 + oracle 加载断言过 |

### 语义层影响点（auto-merge 通过，12 处 marker 行号漂移，纯移位零语义变化）

C007 `logs/screen.py` 67→72；C009–C012 `main/commands.py` 473→478 / 515→520 / 554→559 / 907→912；
C013–C017 `main/screen.py` 471→477 / 782→798 / 822→838 / 1321→1339 / 1332→1350；
C027 `_catalog_oracle_ids.py` 351→352；C029 `tui_helpers.py` 1172→1220。
（上游插入所致；上游未触碰 marker 行本身。C 编号本轮无漂移——无 marker 增删。）

### 定制化改变清单（决策交付物 2/3，已呈责任人裁决认可）

- 需新增定制点：**无**；
- 建议删除（淘汰候选）：**无**——上游 0.32.2 变更域（hook 确认体系/pillow workflow/dialog 重构/docs 全套/chat_panel_workloads）与定制域（登录/诊断/启动接线/mock/测试豁免）零重叠；
- 需适配：C028 计数（已适配）+ 12 处行号（gen 已自动反映）。

### 验证矩阵（test-plan 全项）

| 项 | 命令 | 结果 |
|---|---|---|
| i18n 四步 | `i18n.py extract → update → compile → check` | 全过；**二次幂等**（第二轮零变化） |
| oracle | `pytest tests/foundation/i18n/test_catalog_oracle.py -n0` | `1 passed` |
| 定制侧全套 | `pytest aixcoding/tests -n0 -q -m "not integration and not gc_calibration"` | **294 passed, 2 skipped**（与升级前基线逐位一致；含 test_panel_anchor 行为锚定） |
| 定制清单 | `gen_customizations.py` 连跑 | **29/29 定制点存活**，幂等；生成区 12 处行号更新 |
| ruff 双门禁 | `ruff check` + `format --check`（全目录，含上游新增 chat_panel_workloads.py） | All checks passed / 2543 files already formatted |
| R2/R3 | `check_r2_diff.py` / `check_r3_markers.py --base c54b60cf`（新 merge-base） | **双双 OK**：upstream_changed=21 全部 ⊆ 25 项已签认池；marker_checked=17 + exempt=4 |
| ty 三平台 | `ty check --error-on-warning --python-platform {linux,darwin,win32} src/chrys` | 三平台 All checks passed |
| 上游全量 | `chrys_test.py --full` | **tests 33222 passed, 613 skipped（8:46）+ architecture 1237 passed（2:12），Summary: PASSED (exit 0)**；较基线 32342 净增 880 上游新测试全过；在案 install_scripts 满载 flaky 未复现 |
| 入口冒烟 | `uv run icode --version` | `0.32.2`（随上游三段，正确） |
| TUI 完整冒烟 | F6 aixcoding tab / 徽标 / `/login` `/logout` | **待责任人手工执行**（交互式；PR 合并前完成即可） |
| PR 双 CI | aixcoding-tests.yml + 上游 ci.yml 桥接 | push 后 PR checks |

### 环境

Windows 11 / CodeBuddy；配方：清 `PYTHONPATH` + `PYTHONUTF8=1` + 大写盘符启动；本地 Python 3.14.8（未设 `UV_PYTHON`）。

## 2026-10-31 TUI 冒烟补验（责任人手工执行，通过）

- 环境：`uv run python -m aixcoding.mock`（组合服务 ：7777 catalog+内嵌 auth / :7778 update，进程 19736）+ 独立窗口 `uv run icode`（`AIXCODING_AUTH_ENVIRONMENT=local` 接 mock 认证）。
- 结果：**8 项全部通过**（责任人 2026-10-31 确认"全部通过"）——启动正常；账号徽标登录态切换（C005/C018–C020）；`/login` 登录对话框与设备码流程（C008–C012）；`/logout` 生效；F6 日志面板 `aixcoding` tab（C007）；`/man` 索引含 `/login` `/logout`（C024）；中文文案（ADR-0010）；上游 0.32.2 新特性正常呈现。
- 验证矩阵至此 **11/12** 完成，余 PR 双 CI（push 后 PR checks）。

