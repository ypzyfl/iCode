# 自评审记录：企业埋点迁移

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：兰荣达
- 状态：已确认
- 确认日期： 2026-11-12
- 确认意见：无
- 开发 AI：Codex（本地线程 `01a18a75-8a1f-78f3-a412-e584a35c3b86`）
- 评审 AI：CodeBuddy `kimi-k3.1-pro`（原 session `01a1cd80-abc2-7513-8cd4-b0fdcc46e722`；整批审阅 2026-11-12 16:25:47–16:39:36 上海时间，HOWTO §二补审 17:10:54–17:22:45）

## 2026-11-12 评审结论：代码审阅无 blocker，规范清单补审已归档；验证与验收仍未通过

头部四字段由责任人本人填写：17:14 写入责任人「兰荣达」、状态「已确定」、确认日期「2026-11-12」、确认意见「无」；17:16 将状态更正为规范值「已确认」。本文件于 17:08 创建时状态为「草案」、签认栏留空，该历史已被责任人更新，不再作为当前时态。头部签认不等于统一验证、T08、生产对账或验收通过，也不代替 HOWTO 要求的责任人对其后新 finding 的逐条拍板。

- 轮次：1 轮独立整批审阅（16:25:47–16:39:36）+ 1 轮 HOWTO §二准确范围补审（17:10:54–17:22:45，同一 CodeBuddy session）。整批审阅未发现 blocking 代码缺陷，故无「修复 → 同一评审 AI 增量复审」循环。
- 说明：父 bot / 收尾 bot 对审阅摘要与门禁输出的核对，不是正式第二审，不能冒充 HOWTO 规定的独立评审。t125 / t129 代签只覆盖当时新增 R2 / 登记范围，不适用于本文件签认。
- 当前基线：分支 `main_aixcoding_cli_0.35.2`，HEAD `d651fc42`（文档，2 个活文档），其父 `890e2ec7`（实现 / 测试 / design / ADR，51 个文件）。未跟踪的 `.codebuddy/` 不在本批范围内，也不为过门禁而改删。

### 已完成的独立审阅（16:25–16:39）

CodeBuddy 在可访问本仓库文件的环境下做了整批静态审阅（仓库 Read / Grep / Glob；当时只读 git 在非交互模式被拒，清单后由收尾 bot 用已授权机器工具核对，与审阅所列 53 文件一致）。要点：

- 无 blocking 代码缺陷。去重、无来源字段、回滚保存锁与取消等有路径行号引用，见当时 `/tmp/cb-icode-batch-review.out`。
- 审阅时指出点级严格对账证据未覆盖最终登记（静态估计 155 / 196）。之后主工作区按 `git ls-files --cached --others --exclude-standard` 排除 `.codebuddy/`，调用同一工具 `run_check(strict=True)`，退出 0：**155 条登记、196 个 marker、0 warning**（18 个 design，7 个 retired）。官方原生 `gen_customizations.py --strict` 退出 1，28 条 ERROR 全部位于 `.codebuddy/worktrees/bg-01a1c9d3/`，属已知假阳性，主工作区 0 条；未改工具、未删该目录。
- `rollback.py` / `session_lifecycle.py` 的 14:47 授权范围当时未进入 design R2「文件」列。已把同一已授权路径同步进该列（相对 `a752020b` 为 +14/−9 与 +32/−7），不扩大范围，未改头部本人签认字段。补表后官方 `check_r2_diff.py --base a752020b` 中这两路径为 approved (changed)，批准池 112→114；原生退出码仍为 1，唯一 ERROR 仍是上述 worktree 假阳性。`check_r3_markers.py` 同样：排除该假阳性后本批无违规。

### HOWTO §二补审（17:10:54–17:22:45）

由 CodeBuddy `kimi-k3.1-pro` 在原 session `01a1cd80-abc2-7513-8cd4-b0fdcc46e722` 执行准确范围补审，未整批重审。完整原文见 `/tmp/cb-icode-howto-s2-review.out`（session 事件跨度至 17:22:45）。该回合：只读 Git 与 `check_docs.py --closure` 的 Bash 调用被非交互权限拒绝，**CodeBuddy 未跑出退出码**；Edit 被拒绝，**CodeBuddy 未修改任何文件**。下列逐项结论来自其最终回复。closure 的当前机器结果以协调者事后实跑为准，不照抄补审结束时仍引用的过时「草案 + closure 退出 1」。

| 检查项 | 结论 | 路径：行号证据 / 未执行原因 |
|---|---|---|
| R2：原 17 个接线路径 | 过 | `design.md:243-247` 逐项批准：`engine.py`；`kernel/middleware.py`、`build/builder.py`、`invoker/kernel.py`、`sub_agents/tools.py`、`workflows/agent_node_build.py`、`service/llm/clients.py`；`foundation/events/types.py`、`kernel/loop.py`、`events/tool_events.py`、`events/sub_agent_events.py`；`run/bindings.py`、`events/hosted_tools.py`、`response_validation.py`；`app/acp/server.py`、`run/active_injection.py`、`run/runner.py`。 |
| R2：回滚两路径 | 过 | `design.md:251-252` 已把 `rollback.py`、`session_lifecycle.py` 同步进「文件」列，与补充签认 `design.md:373-383` 一致。 |
| R2：回归与生成清单 | 过 | `design.md:248-250` 对名 `trajectory_wait_manifest.json`、`test_settings_reload.py`、`test_web_search_budget.py`。 |
| R2：`test_layering.py` | finding（nonblocking） | 该文件有实现差异（`890e2ec7` 中 +8/−0），并由同 design 补充签认（15:07 / t129，`design.md:393`）明确批准，但补审当时未进入本批 R2「文件」列。不是未授权改动。处置见下节，不把它写成责任人已拍板「不修」。 |
| R1 逐行归属 | 过 | 原 17 个接线见 `r2-review.md:28-72`、`:74-112`；回滚职责见 `design.md:251-252`、`:323-327`。每组均有归属回答。 |
| R11 第三方依赖 | 过 | 基线文件集没有 `pyproject.toml` / `uv.lock` 改动；`design.md:239` 明确不申请第三方依赖。新增外部 import 仅使用既有依赖：`pyyaml`（`pyproject.toml:31`）、`agent-client-protocol`（`:44`）、`httpx`（`:47`）、`pytest`（`:115`）。无清单外引入。 |
| 幻觉 API | 过 | 补审逐项核到定义与签名，包括 `ChatContext` / `ChatMiddleware` / `ChatMiddlewareLayer`（`kernel/middleware.py:184`、`:246`、`:494`）、`finish_close`（`foundation/util/once_close.py:16-27`，与 `session_lifecycle.py:45`、`:910` 一致）及事件、Workflow、ACP、配置等符号。详见 `/tmp/cb-icode-howto-s2-review.out`。 |
| vacuous test：编辑报文 | 过 | `test_tool_reports.py:174-221` 使用真实引擎、SDK、文件写入和 HTTP 捕获。若把 `events.py:114` 改为强制无来源，`:210` 的 requestId 相等断言会失败；若破坏 `reporters.py:339` 的编辑定位或 `:349` 的 >64 回退，`:221` 及 `test_code_reports.py:43-47` 会失败。 |
| vacuous test：非零回滚 | 过 | `test_entrypoints.py:100-328` 使用真实 TUI、持久化和恢复。若把 `session_lifecycle.py:902` 的 `not self._attribution_saves_paused` 改为真，旧历史会在替换后写回，`:283-285` 会失败；若删除 `:859` 的锁，`in-flight-save` 会在 `:273-277` 观察到未排空写入。 |
| 静默吞错 | 过 | 降级均有注释、日志或计数：`clients.py:639-646`、`events.py:118-119`、`model.py:60-61`、`delivery.py:56-59`、`:91-98`、`:109-113`、`lifecycle.py:51-56`、`acp.py:46-51`。未发现新增无痕迹吞错。 |
| 过度工程 | 过 | `_engine` / `_responses` 被多个测试复用。`pause_mutation_attribution_saves` 虽只有 `rollback.py:343` 一个调用方，但处理已实际复现的保存竞态，并有明确锁语义和门禁登记。 |
| 数据边界 | 过 | 外发仍受 `design.md:199-224` 冻结表约束；路径相对化见 `reporters.py:218-246`；token 仅作发送 header（`delivery.py:105-108`），不进入 payload 或日志。 |
| 边界条件 | 过 | `test_code_reports.py:16-90`、`test_delivery.py:127-162`、`:165-224`。 |
| 异常与资源 | 过 | `lifecycle.py:59-69`、`delivery.py:119-135`、`model.py:62-66`、`acp.py:46-51`、`rollback.py:356-357`。既有去重和无来源结论仍成立，见 `events.py:160-194`。 |
| 并发异步与取消 | 过 | 既有回滚锁/取消结论仍成立：`session_lifecycle.py:855-863`、`:898-910`，`rollback.py:341-357`，`test_entrypoints.py:89-98`。 |
| closure 对账 | 协调者实跑，非 CB 执行 | CodeBuddy 因非交互 Bash 拒绝**未执行、无退出码**。其回复引用的是协调者在草案、签认留空时的结果（当时 `--closure` 退出 1，ERROR 为草案 forbidden）。责任人于 17:16 将状态改为「已确认」后，协调者于 17:17 重跑：普通 `check_docs.py` 退出 0，`--closure` 退出 0。不得把过时的 closure 退出 1 或「最终签认仍开放」写成当前状态。 |

CodeBuddy 声明：本评审为独立第二 AI 评审，与开发 AI 不同源；仍可能共盲，终裁在责任人。

### 补审 finding 处置（N1，nonblocking）

`tests/architecture/test_layering.py` 已由 2026-11-12 15:07（上海时间，UTC+8）t129 授权，并落盘于 `design.md`「2026-11-12 新增 R2 范围补充签认（回滚修复的任务所有权与等待清单登记）」，范围与已提交差异一致（所有权键 `("session_lifecycle", "SessionLifecycle", "refresh_mutation_attribution")`，计数 1，相对 `a752020b` 为 +8/−0）。这不是未授权改动，也不需要新的签认或扩大授权。已于本次归档把**同一已批准路径**同步进本批 R2「文件」列，供本批读表自包含；不追加其他文件，不修改 design 头部本人签认字段，也不把该 finding 记为责任人已拍板「不修」。

### 未修项与验收缺口（均不得记为通过）

- 统一验证：`verify.py --smart --paths` 退出 1。定制套件 612 passed、47 skipped、71 failed、17 errors；88 项失败/错误已独立核读，堆栈终点均为首次 `socket.bind()` 的 `PermissionError: [Errno 1] Operation not permitted`。不能绕沙箱或关闭验证来改写结论。
- 上游 Smart Test 选中 0 项；其退出 0 不表示上游测试通过。
- 实际运行 Python 3.14.8，项目要求 3.14.10；未为此安装依赖或改锁。
- T08 后续版本升级演练未实施。
- 生产入库、缺省关联字段的后端处理及服务端去重未对账。
- 责任人已本人签认本文件头部；该签认不关闭上述验收缺口。

### 收尾验证补记

评审归档已在 `9dd573eb` 本地提交。随后由本线程 Codex 运行上游定向 Smart Test，常规 37 项通过，架构 504 项通过、2 项因当前进程优先级权限失败。上一轮「上游选中 0 项」是当时的范围记录。未改产品代码，未产生新的独立评审结论。统一验证、目标 Python 3.14.10、T08 与生产对账仍开放。命令、结果和后续条件见 [本地收尾与验收前置](verification.md#本地收尾与验收前置)。
