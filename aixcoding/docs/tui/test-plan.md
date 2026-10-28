# 测试计划：tui 迁入

## 测试矩阵

| 验证面 | 载体 | 类型 |
|---|---|---|
| 对话框全流程（mock 授权成功/取消不落盘/不可达报错） | `aixcoding/tests/tui/test_login_dialog.py`（3 用例，mock server 端到端） | 集成（loopback mock） |
| `/login` `/logout` 动作与 toast（未登录警告/登出/成功 toast/delegated 拦截 ×2） | `test_login_command_wiring.py`（7 用例，SimpleNamespace host） | 单元 |
| silent check 挂点（on_mount 启动 + on_unmount 取消，源码锚定） | `test_login_command_wiring.py`（2 用例，inspect.getsource） | 结构断言 |
| 徽标三态计算（未登录/已登录+ehr 回退/delegated ×3/拒绝回退） | `test_login_indicator.py`（9 用例，中文常量期望） | 单元 |
| 徽标 widget（显示/隐藏/`-logged-out` 类/tooltip/可关） | `test_app_header_login_badge.py`（2 用例，Pilot） | 组件 |
| 命令注册（存在性/allow_while_running/action 转发/man 收录） | `test_slash_login_commands.py`（4 用例，registry 构造） | 单元 |
| 上游建议系统回归（91 用例连带面） | `tests/app/tui/screens/test_suggestions.py` 等（现有套件，helper 修补后全绿） | 回归 |
| i18n 三方一致（pot/po/oracle/索引期望） | `i18n.py check` + `test_catalog_oracle.py`（CI_LINUX_ONLY）+ `test_command_suggestions_i18n.py` | 门禁 |
| 分层（ADR-0011 零豁免） | `tests/architecture`（1237 用例） | 架构 |

## 异常与降级路径

- 对话框测试 timeout 10s 已留裕量（0.28 沉淀的 wait_until 模式平移，本地 conftest 实现
  不共享上游失败域）。
- `test_catalog_oracle.py` 带 `@CI_LINUX_ONLY`：本地 Windows skip，oracle 集合断言以 CI
  为准（design 假设 8 环境注记）。
- mock 端口冲突：`create_server(port=0)` 临时端口（PR #56 形态）。
- gc_freeze_calibration 满载偶发 flaky 在案：与本批次无关，单跑即绿。
