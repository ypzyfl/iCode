# 验证：0.35.2 分支手动预发布

- Python 实际为 3.14.8，项目 pin 为 3.14.10。项目工具使用 `uv run --offline --no-sync --no-python-downloads`。
- 读取实际 CD YAML，运行其中的分支解析和制品收集 Bash。九组触发条件符合预期。核对 CI、wheel、二进制引用及标签目标，共用固定 SHA。用测试 wheel 和两种二进制生成 `v0.35.2-cli.42-1`、zip、tar.gz 及校验文件，`sha256sum -c` 通过。正式标签的既有条件、PyPI 和安装脚本 job 保留。
- `pytest -n0 -q tests/architecture/test_workflow_action_pins.py tests/architecture/test_python_pin.py` 退出 0，30 项通过。
- GitHub 首次手动运行仍待核对，未触发远端构建或发布。

## 通用版本分支补充验证

- 使用同一 uv 参数读取实际 YAML 并运行分支解析 Bash，15 组通过。正向包括 0.35.2、0.36.0 和带 `_final` 的 1.2.3。负向覆盖错误分支名、仓库、引用类型、ref 和多行输入。关闭开关的普通构建和正式标签均保留原 ref。与 `9b6c22ae` 对照，除解析 job 外其余 job 完全一致。
- 工作流 action 与解释器 pin 门禁 30 项通过，`check_docs.py --closure` 和 `git diff --check` 通过。仍未触发真实 Actions。

## 首次 CD 运行的回归修复

[运行 44032393467](https://github.com/ypzyfl/iCode/actions/runs/44032393467) 的版本分支解析成功，三平台各出现同样的发布契约与 TUI 弹窗断言失败，后续打包与发布被跳过。本地定向复现两项失败。

- 两种发布共用 wheel 版本检查的触发条件。正式标签保留与 wheel 版本及触发标签的匹配检查。分支版本标签由检查步骤从已构建的 wheel 派生，发布任务使用该输出。PyPI、构建来源及安装脚本 job 保持原样。
- 在测试 wheel 上运行实际 Bash，6 组覆盖预发布标签、正式标签匹配与不匹配、触发标签与 ref 不一致。均符合预期。
- Python 3.14.8 下，使用 `uv run --offline --no-sync --no-python-downloads pytest -n0 -q --tb=short tests/app/cli/test_app.py tests/app/tui/screens/test_modal_insert_clipboard.py aixcoding/tests/telemetry/test_report_logging.py tests/architecture/test_workflow_action_pins.py tests/architecture/test_python_pin.py`，76 项通过。Ruff、格式检查、文档闭环和差异检查通过。项目 pin 为 3.14.10。修复版 GitHub 发布待启动。
