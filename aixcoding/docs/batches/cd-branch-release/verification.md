# 验证：0.35.2 分支手动预发布

- Python 实际为 3.14.8，项目 pin 为 3.14.10。项目工具使用 `uv run --offline --no-sync --no-python-downloads`。
- 读取实际 CD YAML，运行其中的分支解析和制品收集 Bash。九组触发条件符合预期。核对 CI、wheel、二进制引用及标签目标，共用固定 SHA。用测试 wheel 和两种二进制生成 `v0.35.2-cli.42-1`、zip、tar.gz 及校验文件，`sha256sum -c` 通过。正式标签的既有条件、PyPI 和安装脚本 job 保留。
- `pytest -n0 -q tests/architecture/test_workflow_action_pins.py tests/architecture/test_python_pin.py` 退出 0，30 项通过。
- GitHub 首次手动运行仍待核对，未触发远端构建或发布。

## 通用版本分支补充验证

- 使用同一 uv 参数读取实际 YAML 并运行分支解析 Bash，15 组通过。正向包括 0.35.2、0.36.0 和带 `_final` 的 1.2.3。负向覆盖错误分支名、仓库、引用类型、ref 和多行输入。关闭开关的普通构建和正式标签均保留原 ref。与 `9b6c22ae` 对照，除解析 job 外其余 job 完全一致。
- 工作流 action 与解释器 pin 门禁 30 项通过，`check_docs.py --closure` 和 `git diff --check` 通过。仍未触发真实 Actions。
