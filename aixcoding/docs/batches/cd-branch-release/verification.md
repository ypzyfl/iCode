# 验证：0.35.2 分支手动预发布

- Python 实际为 3.14.8，项目 pin 为 3.14.10。项目工具使用 `uv run --offline --no-sync --no-python-downloads`。
- 读取实际 CD YAML，运行其中的分支解析和制品收集 Bash。九组触发条件符合预期。核对 CI、wheel、二进制引用及标签目标，共用固定 SHA。用测试 wheel 和两种二进制生成 `v0.35.2-cli.42-1`、zip、tar.gz 及校验文件，`sha256sum -c` 通过。正式标签的既有条件、PyPI 和安装脚本 job 保留。
- `pytest -n0 -q tests/architecture/test_workflow_action_pins.py tests/architecture/test_python_pin.py` 退出 0，30 项通过。
- GitHub 首次手动运行仍待核对，未触发远端构建或发布。
