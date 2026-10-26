# 验证证据：上游 CI 桥接（upstream-ci / aixcoding-upstream-ci.yml）

> 活文档：命令 + 输出摘要（R7 落盘形态，追加不删旧）。

## 2026-10-26 实施完成（本地等效验证）

环境：Windows，`PYTHONPATH=`、`PYTHONUTF8=1`、`UV_PYTHON=3.14.3`；R2/R3 base 与 CI 同语义（`git merge-base origin/main_iCode HEAD` = 3104004）。

| # | CI 步骤（本地等效命令） | 结果摘要 |
|---|---|---|
| 1 | `uv run python aixcoding/tools/gen_customizations.py` + `git diff --stat CUSTOMIZATIONS.md` | 5 custom point(s), 0 warning(s) / **GEN-IDEMPOTENT-OK**（新文件经 `CUSTOM_EXACT_PATHS` 豁免，清单无漂移） |
| 2 | `uv run python aixcoding/tools/check_docs.py` | 9 ADR + 6 design + 4 self-review / OK（含本批 design.md 草案头部） |
| 3 | `uv run python aixcoding/tools/check_import_boundaries.py` | scanned 1082 / OK |
| 4 | `uv run ruff check aixcoding/` + `ruff format --check aixcoding/` | All checks passed / 96 files already formatted |
| 5 | `check_r2_diff --base 3104004` | changed=109 / **upstream_changed=3**（AGENTS.md、logs/screen.py、test_layering.py——均为历史批次已批准项，本批零新增）/ OK；草案 R2 表被忽略为预期警告（签认后生效，双轨设计） |
| 6 | `check_r3_markers --base 3104004` | upstream_changed=3 / marker_checked=3 / exempt=0 / OK |
| 7 | `uv run pytest aixcoding/tests tests/architecture/test_workflow_action_pins.py -m "not integration and not gc_calibration" -q` | **190 passed, 2 skipped** in 11.28s（含 action pins / permissions 守卫对新 workflow 的扫描：本地 `uses: ./.github/workflows/ci.yml` 豁免 pin、`permissions: contents: read` 显式声明合规） |

本批属性：零修改/删除上游既有文件；唯一上游目录内变更为新增 workflow（GitHub 硬约束），`CUSTOM_EXACT_PATHS` 登记 + design.md R2 表双轨（同 ci-gate 先例）。

## 2026-10-26 耗时基线（GitHub API 实测，供 PR 等待时间预期）

| Workflow | 数据来源 | 实测 |
|---|---|---|
| `AIxCoding Tests` | 本仓库近期 run（uv 缓存热） | **38-49 秒** |
| `AIxCoding Upstream CI`（workflow_call 复用 ci.yml 全套 17 job） | 上游 openJiuwen-ai/iCode 同款 ci.yml 近期 PR run | 成功 **11 分 02 秒 / 11 分 35 秒**；失败 16 分 28 秒 |

- PR 总等待 ≈ 上游矩阵关键路径 11-12 分钟（两 workflow 并行，瓶颈为多 OS 分片 + `build → wheel_install` 依赖链）。
- fork 仓库历史 200 个 run 中无任何 `CI` 记录——确认上游 CI 从未在本 fork 触发过（PR 目标分支均为 main_aixcoding_cli 系，ci.yml 仅绑定 PR 至 main；tag-release 的发布链路亦从未在此 fork 走过）。
- 首跑契机：pull_request 事件的 workflow 定义取自 PR merge ref，提交桥接文件的 PR 自身即触发新 workflow，无需单独验证轮次。

## 2026-10-26 远程首跑（PR #58，commit 86b8ca3）

**AIxCoding Upstream CI #1：completed / success**，run 40279169732，**10 分 47 秒**——首跑三合一验证一次通过：

- 桥接机制：workflow_call 正常拉起上游 ci.yml 全套（run 内引用 ref `refs/pull/58/merge`）；
- checkout ref 语义：PR merge ref，与设计一致（不传 build_ref，`inputs.build_ref || github.sha` 取调用方 commit）；
- 上游全量测试在本 fork 历史上**首次运行且全绿**——现有 3 处已批准上游改动（AGENTS.md、logs/screen.py、test_layering.py）无任何远端消费者破坏；耗时与上游基线（11-12 分钟）吻合。

**AIxCoding Tests #14：completed / success**，run 40279169833，38 秒（uv 缓存热）。

两 run 由同一提交 pull_request 同时触发，PR 总等待 10 分 47 秒。

结论：桥接批次目标达成；下方未验证事项全部闭环。

## 未验证事项

- （首跑后清空；后续新增未验证事项在此登记）
