# 测试方案：本地诊断包（aixcoding diagnostics）

> 活文档：随时更新、不签认；其质量由双 AI 自审与行为锚定测试保障。

## 测试范围与策略

落 `aixcoding/tests/diagnostics/`，全部自设 fixture（tmp_path 隔离 HOME/config_dir），不依赖上游 `tests/support`。关键 anchor（`_TuiLogHandler` / `install_log_handler` / `MODULE_ORDER` / `chrys.app.cli.app:main`）按 §5 行为锚定：真实 import 上游符号断言其行为，禁 mock 锚点本身。

| 层 | 测试文件 | 策略 |
|---|---|---|
| config | test_config.py | TOML 解析各键/缺省/非法值 fail-safe |
| logging | test_logging_support.py | logger 工厂命名/落盘文件产生/rotation/propagate 开关/与 root handler 共存 |
| 面板 anchor | test_panel_anchor.py | 真实读上游 `MODULE_ORDER` 断言含 `"aixcoding"` 且 F6 白名单派生跟随（行为锚定） |
| crash | test_crash.py | sys.excepthook/threading.excepthook 捕获写文件、faulthandler 启用、atexit 兜底 |
| snapshot | test_snapshot.py | 快照字段存在性 + 脱敏断言（不含 env 全量、不含 token 类键） |
| launcher | test_launcher.py | monkeypatch 上游入口，断言钩子安装顺序与调用；`python -m` 冒烟（子进程） |

## 覆盖矩阵

| 验收标准 | 测试入口 | 类型 |
|---|---|---|
| 落盘恒开 + 轮转 | test_logging_support.py::test_file_always_on / test_rotation | 单元 |
| TOML 解析 + fail-safe | test_config.py::test_defaults / test_invalid_toml_falls_back | 单元 |
| propagate→F6 冒泡 + 降级 | test_logging_support.py::test_propagate_bubbles / test_panel_anchor.py | 单元+行为锚定 |
| 崩溃现场写入 | test_crash.py::test_excepthook_writes / test_thread_crash / test_faulthandler_enabled | 单元 |
| 快照脱敏 | test_snapshot.py::test_fields_present / test_no_secrets | 单元 |
| launcher 钩子顺序 | test_launcher.py::test_hooks_then_main | 单元+冒烟 |
| MODULE_ORDER 一行 | test_panel_anchor.py（锚定测试随 R3 标记一并落地） | 行为锚定 |

## 异常与降级路径

- `aixcoding.toml` 缺失/语法错误 → 内置默认（level=INFO、panel=false），不抛错（fail-safe 验证）；
- 日志目录不可写 → stderr 一行提示后跳过 FileHandler（降级可查，§9），不影响主流程；
- `_TuiLogHandler` 假设失效（上游重构）→ 面板无内容但无错误（纯落盘降级）；锚定测试转红提示跟进；
- crash 钩子自身异常 → 静默不连锁崩溃（诊断设施不得成为故障源），测试注入二次异常验证。

## 手工验证步骤（若需）

- TUI 实测 F6 aixcoding tab 显示（面板场景，自动化受限）；命令与预期记 verification.md。
