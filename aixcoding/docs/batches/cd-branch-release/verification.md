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

## Windows ARM64 依赖缓存

- 本地解析工作流 YAML，核对 ARM64 离线 job 在 setup-uv 前解析缓存路径，安装依赖与恢复缓存共用短路径；vcpkg 使用独立文件缓存。缓存 key 覆盖 vcpkg 提交及 runner 镜像，uv 另对 Python pin、依赖锁和构建约束分隔。实际构建、离线启动测试和发布 job 与 `a2220943` 一致。
- 现有 Python 3.14.8，以 `uv run --offline --no-sync --no-python-downloads` 执行 `pytest -n0 -q tests/architecture/test_workflow_action_pins.py tests/architecture/test_python_pin.py tests/app/cli/test_app.py::test_releases_upload_the_checked_wheel_to_pypi_without_a_stored_secret`，退出 0，31 项通过。R2、R3、文档闭环和差异检查退出 0。项目 pin 为 3.14.10。
- 尚未在 Windows ARM64 runner 验证。首次成功构建会填充缓存，两次相同配置的运行对照 setup-uv 恢复日志、vcpkg 命中、源码准备和离线构建耗时。

## 2026-11-17 测试打包与正式发布

依据已签认的 design-refresh-release-assets.md，手动入口改为 test（默认）、update-release、create-release。版本分支解析为触发 SHA，正式模式要求全平台并核对 wheel 版本。更新保留已有 Release 元信息与 Tag；六平台安装包、wheel、BUILD_INFO.md 和校验和齐备后先备份现有附件，再覆盖同名附件，SHA256SUMS.txt 最后上传。创建模式先原子创建固定 SHA 的 Tag，再使用 --verify-tag 创建 Release；失败后残留 Tag/草稿须人工核验恢复。

本次使用现有 Python 3.14.8。全部 uv 命令加 --offline --no-sync --no-python-downloads，并设置 UV_CACHE_DIR=/tmp/icode-cd-uv-cache。工具如实警告项目请求 3.14.10。未安装解释器或依赖。

- `uv run --offline --no-sync --no-python-downloads python /tmp/icode-cd-release-smoke.py`，退出 0。8 个 dispatch、10 个目标 Release/Tag（含草稿、不可变、权限错误）、3 个 wheel/Tag 版本用例通过。另通过六平台名称、sha256sum -c、缺包、备份先于覆盖、checksum 最后上传、上传失败中断及创建 Tag 失败后禁止发布的模拟。脚本位于 /tmp，未作为持久化回归测试提交。
- 提取实际 YAML 内 Bash 执行 bash -n，18 个块通过，退出 0。
- `uv run --offline --no-sync --no-python-downloads pytest -n0 tests/architecture/test_workflow_action_pins.py tests/architecture/test_python_pin.py`，退出 0，30 passed。
- `uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_docs.py --closure`，退出 0，check_docs: OK。
- `uv run --offline --no-sync --no-python-downloads python aixcoding/tools/check_r2_diff.py --base HEAD` 和 `python aixcoding/tools/check_r3_markers.py --base HEAD`（后者同样经 uv），均退出 0。diff 中唯一上游文件为 cd.yml。原签认头部保持。
- `uv run --offline --no-sync --no-python-downloads python aixcoding/tools/gen_customizations.py --strict`，退出 1，28 个错误均来自已有 .codebuddy/worktrees/bg-01a1c9d3 的扫描假阳性，0 warning。未修改该目录或检查器，未将此项记为通过。
- `git diff --check`，退出 0。

远端只读查询为 main_aixcoding_cli_0.35.2 @ 182d5b88730048c7dc1a5b7dcf151ab391f6b961，较本地 e0316c1c 多 5 个提交。对象已存在，本地核对该区间未修改 cd.yml。合并与推送须按 git 逐条授权执行。

真实 GitHub 的备份下载、附件替换、新建 Tag、Release 发布以及桌面端下载仍待联调。本地模拟不证明远端凭据权限。首次操作须从含新工作流的分支打开 Run workflow。GitHub 附件替换为逐文件操作，中断时从本次运行的 previous-release 附件归档恢复整套文件；新建失败保留 Tag 与运行证据，人工核验后补发 Release。

### 2026-11-18 Smart Test 与静态检查

下列命令沿用前述 UV_CACHE_DIR 和 uv 参数，实际 Python 3.14.8。

- `uv run --offline --no-sync --no-python-downloads python scripts/chrys_test.py --smart --paths .github/workflows/cd.yml aixcoding/docs/batches/cd-branch-release/design.md aixcoding/docs/batches/cd-branch-release/design-refresh-release-assets.md aixcoding/docs/batches/cd-branch-release/plan.md aixcoding/docs/batches/cd-branch-release/test-plan.md aixcoding/docs/batches/cd-branch-release/verification.md aixcoding/docs/batches/cd-branch-release/self-review.md`，退出 1。Summary 为 tests 38 passed（退出 0），architecture 198 passed、2 failed（退出 1）。两处失败都在 test_lowered_priority_reaches_the_processes_tests_start，沙箱拒绝 os.setpriority，导致 PermissionError 及优先级解析失败。未放宽沙箱、未修改测试。
- `uv run --offline --no-sync --no-python-downloads ruff check --no-fix src/ tests/ scripts/chrys_test.py scripts/check_wheel.py scripts/calibrate_gc_freeze.py scripts/gc_freeze_calibration_math.py scripts/chat_panel_workloads.py hatch_build.py scripts/i18n_mo.py`，退出 0，All checks passed。
- 同一文件集运行 `uv run --offline --no-sync --no-python-downloads ruff format --check ...`，退出 0，2774 files already formatted。
