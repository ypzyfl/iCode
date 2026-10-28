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

结论：桥接批次目标达成；本节（远程首跑）相关未验证事项全部闭环。后续批次新增的未验证事项见下方各节，均未闭环。

## 2026-10-26 required check 修正（peer review 后续发现）

**问题**：ruleset 手输 workflow 名 `AIxCoding Upstream CI` 设为必过 → 永久 "Expected — Waiting for status to be reported"。根因：GitHub 分支保护的 required check 匹配 **job 级 check run 名**（实测对照：job 名 `AIxCoding quality gate` 正常匹配），而桥接的 job 全部是被调 ci.yml 的上游 job 名，fork 无自有名字的 check run。

**修正**：桥接新增汇总 gate job `AIxCoding upstream gate`（`needs: ci`；reusable job 的 result 聚合被调 workflow 全部 job）作为稳定必过 check 落点。上游 job 增删改名 → `workflow_call` 自动跑新矩阵、gate 自动聚合，ruleset 零同步。

**取舍记录**：替选方案"把 17 个上游 job 名逐个设为必过"被否决——上游任一 job 改名即致旧条目永久 Expected（门禁自杀），维护成本高。

## 2026-10-26 gate job 首跑验证（PR #58，commit fb5a61e，run 40285498100）

**18 job 全部 success**（17 上游矩阵 + 1 gate）。gate 验证要点：

- **独立 check run 报告且为绿**：job `AIxCoding upstream gate`（id 121452145813）3 步全 success，耗时 4 秒（07:35:59→07:36:03）——秒级是设计预期：gate 是聚合判定官非测试执行者，唯一实质步骤 `Verify the upstream suite` 执行 `test "$CI_RESULT" = "success"`；测试本体在矩阵 job 跑（同 run 实测：`Unix shard (macos/core)` Run tests 约 11 分钟、`Windows shard (windows/core)` 约 8 分钟、`Architecture` 约 4 分 20 秒）；
- **`needs: ci` 聚合语义正确**：时序证明 gate 等完了全矩阵——最慢 job `macos/core` 07:35:46 结束 → 上游 `Test (macos)` gate 07:35:56 → 本 gate 07:35:59 才启动；
- **同构对照**：同 run 内上游 ci.yml 自带的三个 gate（`Test (linux)`/`Test (windows)`/`Test (macos)`）同样各 4-5 秒，模式逐字一致；
- **fail-closed 语义**：矩阵任一 job 失败 → `needs.ci.result=failure` → gate 断言失败 → 必过 check 拦截合并。

**ruleset 配置生效**：required check `AIxCoding upstream gate`（手输 job 名添加）由 "Expected — Waiting" 转绿，匹配成功；旧 workflow 名条目已清除，PR checks 全部通过、`mergeable_state: clean`。

结论：本节两条未验证事项全部闭环；桥接批次含 gate 修正完整验证完毕。

## 2026-10-28 doc-only 跳过的 required check 语义（外部 AI 评审拦截）

**同源坑复盘**：本文件上一节已确立"required check 匹配 **job 级** check run 名"——但 CI 收窄初版（workflow 级 `paths-ignore`）恰恰漏了这条联动：`paths-ignore` 命中时**整个 workflow 不触发**，`AIxCoding upstream gate` 不产生 check run → required check 变 skipped → 纯文档 PR 永久卡 "Expected"、`mergeable_state` 非 clean、**无法合并**（GitHub 官方 troubleshooting 的 "Handling skipped but required checks" 章节即此故障态；社区先例 *"Docs PRs stopped burning runner time. Then they stopped merging."*）。

**修正（已入 design 备选表）**：跳过判断下放 job 级——`filter` job（秒级 git diff 判 `doc_only`）→ `ci` 条件跳过 → `gate` 保持 `if: always()` 且 doc-only 直通 exit 0。**gate 永远产生 check run**，门禁语义不变（doc-only 直绿 / 混合 PR 仍需全套矩阵绿）。

**待实测验证**（该 PR 自身改 workflow，会照跑全套）：首个纯文档 PR 上观察 gate 报告 "doc-only PR: upstream matrix skipped by design" 且 check 转绿、PR 可合并。

## 未验证事项

- （本批次全部闭环；后续新增未验证事项在此登记）
