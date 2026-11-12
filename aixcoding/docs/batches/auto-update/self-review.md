# Self-Review：TUI 自动更新流程（auto-update）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期），AI 不得代填。
AI 的自查结论不是签认；签认前 block 条目必须全数闭环。
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：
- 评审 AI：Deepseek-V4-Pro（独立第二 AI，与开发 AI 不同源）
- 开发 AI：CodeBuddy / GLM5.3

> 双 AI 自审（SELF-REVIEW-HOWTO §三）：开发 AI＝CodeBuddy / GLM5.3，
> 评审 AI＝Deepseek-V4-Pro；2026-11-12 完成 1 轮独立评审，findings 与
> 处置见下「评审结论」。初版误记为「实施 AI 自查」，已按责任人提供的
> 标识更正（记录档追加，不触发重签）。终裁在责任人。
> 自查范围：本批次全部代码与文档。
> 修订记录：2026-11-11 初版（实施完成后）。
> 2026-11-11（二）首次人工冒烟后更新：修订八～十三（wrapper 弃管道、下次
> 提醒语义、失败提示行、启动窗口两阶段等待、焦点内联高亮）已并入自查。
> 2026-11-12（三）责任人裁决 R13 方案①（design 修订十四）：R2 清单新增
> `pyproject.toml`，5 处散落豁免集中为 1 条目录级条目，R13 block 清零；
> design 头部签认字段待责任人本人重签。
> 2026-11-12（四）独立评审（Deepseek-V4-Pro）findings 处置：责任人拍板
> 方案 3（最小处置）——补双 AI 身份与评审结论节，次要项以追加补记
> 清理，nit 项留理由不修；零上游改动、零重签、零提交。
> 2026-11-12（五）责任人裁决跨批次登记号撞号「本批后移」：C158/C159
> → **C172/C173**，design 事实源、四件文档与 `runner.py` 注释同步；
> `design.md` 的 R2 清单（3 个上游文件及行数）未变，按 §4.1 判定不
> 触发重签，头部签认字段保持本人落盘值。下方已签认正文及各历史节
> 中的 C158/C159 均为当时快照，按 R10 不改写；现状以本节、评审结论
> 节补记与 verification.md 为准。

## 2026-11-12 评审结论：通过

本节为独立第二 AI 评审后**追加**，不改变下方已签认正文；标识由责任人
2026-11-12 提供。

- 轮次：1 轮（Deepseek-V4-Pro 独立评审 → 责任人逐条拍板 → AI 修复）。
  如实申报：修复增量**未再调用评审 AI 复审**，以机器门禁复跑与责任人
  抽查为准（命令与结果见 verification.md「独立评审处置」）。
- blocker 处置（1 项）：`self-review.md` 头部缺「评审 AI / 开发 AI」、
  无「评审结论」节、初版「自查主体＝实施 AI」读起来像实现者自查，
  不满足 DEVELOPMENT §4.2 第 5 步与 R10 的评审 AI 记录要求 → **已修复**：
  补齐两个字段、更正主体表述、按 §三 模板新增本节（轮次 / blocker /
  未修项）。验证：`uv run python aixcoding/tools/check_docs.py --closure`
  （签认校验 OK）＋本节与 §三 模板逐项对照。
- 已修次要项（追加补记，不改写已签认原行）：
  - 第 2 项：R1/R2 摘要漏 `trajectory_wait_manifest.json` → 补记于 R1/R2 条目。
  - 第 3 项：「请求」节与头部「已确认」状态矛盾 → 补记于「请求」节。
  - 第 4 项：R13 漏第③类测试豁免（skipif）→ 补记于 R13 条目；PR 变更
    导览「新增豁免清单」在 plan.md 改列 2 条。
  - 附带：头部修订记录（三）「design 头部待重签」、R1/R2「须重签，见下」、
    R7「待 Smart Test 定稿」、R10「修订六后须重签」均为早期状态快照；
    现状＝design 与 self-review 头部均「已确认 / 2026-11-12」、
    `check_docs --closure` OK、最终态 Smart Test 已跑完（verification.md）。
    按 R10「记录档签一次、追加不重签」在此统一留痕，不改写原行。
- 未修项（次要问题，责任人 2026-11-12 拍板不修）：
  - `pyproject.toml:249-250` | R3/R13 批准注释拆两行、`R13 exemption
    ledger` 非规范清单名 | nit 级，`check_r3_markers` 已过、本批评审
    处置前 `--strict` 111/152/0 全绿；压成单行会连带 C173 登记锚、
    design §4 行数与 `--strict` 复跑，代价高于收益，且本轮定位为
    零上游改动（注：复跑时 `--strict` 出现 2 个跨批次撞号 error，
    与本项无关，见下）。
  - `design.md` §3.3 / §2、§3.6 / §12 / §3.4 | 已签认正文四处与实施态
    不符的措辞 | 属措辞层，不改变 R2 审批对象与已签决策；按 R10 决策档
    仅 R2 清单变更须重签，留 PR 评审期处理（plan.md 已列可后置项）。
  - Windows 实机冒烟、真实内网联调、成功 relaunch 真实镜像路径 |
    未验证事项 | 可后置，已在「未验证事项」如实申报。

> 2026-11-12 追加补记（责任人裁决撞号「本批后移」）：本批登记号现为
> **C172 / C173**（原 C158/C159，与并行批次 `skills-aixcoding-dirs`
> 撞号）。上列「未修项」属本轮新增的评审结论节，其登记锚引用已同步为
> 现行值；下方「Block 判定条目」「已核实的正确性要点」「请求」等
> **已签认正文**及各历史快照中的 C158/C159 一律保留原样，按 R10 不
> 改写。`--strict` 由 FAILED（2 个 duplicate id）恢复为
> `check OK — 116 / 161 / 19 design(s) / 7 retired / 0 warning`，
> 证据见 verification.md「责任人裁决：本批后移」。`design.md` 的 R2
> 清单未变，本次不重签；责任人 2026-11-12 明确裁决**不重签**。

## Block 判定条目（有任何一条为 block 即不得请求签认）

- **R1/R2**：上游改动＝design §4 清单（修订六后仅 app.py 一处 +4 行 C158；
  修订十四新增 pyproject.toml 一行 +3 行 C159，经责任人 2026-11-12 裁决批准）
  ＋ config 两文件为 aixcoding 树内（非上游）。**无清单外上游文件**；
  `check_r2_diff.py --base HEAD` 与 `check_r3_markers.py --base HEAD` 实跑 OK。
  R2 缩减（修订六）与扩充（修订十四）均已落修订记录——**须重签，见下**。
  → 无 block，附待办。
  > 2026-11-12 独立评审补记（记录档追加，不触发重签）：本行摘要漏列
  > design §4 第 2 行的 `tests/architecture/trajectory_wait_manifest.json`
  > （生成产物刷新 +7 行，JSON 无法携带注释故免 marker）。R2 清单实为
  > **3 个上游文件**：app.py（+4，C158）、trajectory_wait_manifest.json
  > （+7）、pyproject.toml（+3，C159）；实测 `git diff --stat` 为
  > `3 files changed, 14 insertions(+)`，与 `check_r2_diff` /
  > `check_r3_markers` 结论一致，无合规缺口，仅本行措辞不全。
  > 另：本行「须重签」为 11-11 快照，design 与 self-review 头部均已
  > 「已确认 / 2026-11-12」，`check_docs --closure` OK，已闭环。
- **R3**：marker 单行英文、指向批次文档（`aixcoding/docs/batches/auto-update`）。→ 无 block。
- **R4**：新文件全部落 aixcoding 目录（`src/chrys/service/aixcoding/update/`、
  `src/chrys/app/aixcoding/update/`、`aixcoding/tests/auto_update/`）。→ 无 block。
- **R5**：无清单外顺手改动；git status 干净面＝design 预告面。→ 无 block。
- **R6**：全部新代码带 docstring（模块级含设计引用；关键函数含行为契约）。→ 无 block。
- **R7**：上游测试零红面（Smart Test 结果见 verification.md 补录；gate 三重豁免
  设计保证 TUI 测试不触发真实请求）。→ 待 Smart Test 定稿（非 block 预期）。
- **R8**：verification.md 逐条附命令与结果。→ 无 block。
- **R9**：tier 落位＝service（client：httpx/config/platform）与 app（flow/dialog/
  runner/commands：TUI 与进程编排），依赖方向全部下行或同层。→ 无 block。
- **R10**：本文件由 AI 起草、责任人签认；design 已由责任人签认（2026-11-11），
  修订六后**须重签**。→ 无 block，附待办。
- **R11**：零新依赖（httpx/pytest 既有；shlex/subprocess 标准库）。→ 无 block。
- **R12**：0.28 资产迁移重审完成（design §6 六行对照表）；配置换血至 ADR-0022；
  测试迁 `aixcoding/tests/`。→ 无 block。
- **R13**：责任人 2026-11-12 裁决方案①——原 5 处散落豁免
  （RUF001 文件级 ×3 + S603 行内 ×2）**全数删除**，改 `pyproject.toml`
  单条 `"src/chrys/app/aixcoding/update/*" = ["RUF001", "S603"]`，就地 R3
  marker 注释含理由与批准指向（catalog-auth-gating 已签先例同构）。豁免
  条目 5→1；C159 已登记，`--strict` 111/152/0 对账通过。批准落盘＝
  本文件修订三 + design 修订十四 + `check_r2_diff` OK。→ **block 解除**。
  > 2026-11-12 独立评审补记（记录档追加，不触发重签）：本批 R13 豁免
  > 实为 **2 类**，本行只汇总了 lint 一类：① ②类 ruff 豁免——上文
  > `pyproject.toml` 单条目录级条目（C159）；② ③类测试豁免——
  > `aixcoding/tests/auto_update/test_runner.py` 的平台 skipif
  > （非 Windows 跳过 Windows 命令构造断言、POSIX 侧同构反向 skipif），
  > 理由＝被测 `cmd /c` / `sh` 序列依赖真实平台 console 语义，批准
  > 指向＝design.md 签认（design §10、test-plan「平台豁免」）。
  > PR 变更导览「新增豁免清单」须列 **2 条**而非 1 条（plan.md 已同步）。

## 已核实的正确性要点（抽查描述）

- D2 双临时文件语义与责任人三轮裁决一致：wrapper 唯一文件操作＝失败追加一行
  （test_runner 命令串断言"零删除"）；flow 按"标记今日 → 全天不检查 / 计数不跨日 /
  ≥3 建标记删计数"次序判定（test_flow 三闸各自独立用例）。
- 强更框仅"立即更新"且 Esc/backdrop 不可关（test_dialog 实测 press escape 后
  answers 为空、screen 未变）。
- 检测地址与镜像根同源（test_client/test_runner：`[update].base_url` 覆盖时
  两端整体移动；auth 主机 drift 钉死）。
- 会话恢复：`_start_update` 经 `screen.chat_session_id` 取当前会话传 `-s`
  （test_confirm 断言 sess-1）。
- 退出-更新-重启次序：e2e 用例以短命子进程模拟 TUI，断言 wrapper 在父进程
  存活期零动作、终止后执行、成功重启、失败计数且不重启。
- 首次人工冒烟新增核实（2026-11-11，design 修订八～十三）：
  - wrapper 弃 `curl | bash` 管道，改"先下载到临时文件再执行"——curl 404
    不再伪装成功重启，两平台同修（test_runner 含下载失败回归用例）；
  - "立即更新"在真实 ChrysApp 上 0.3s 内自动退出、wrapper 失败分支追加
    计数且不重启（debug.log 与责任人终端实测）；
  - 跳过通知指向 `update-skip-today`（原误指已消费的 `update-failures`，
    测试断言点名标记文件）；
  - 弹框键盘：埋点证明 Tab 焦点循环正常，根因是启动加载框压栈 + App
    flat 按钮焦点标记不可见 + DEFAULT_CSS 输给 chrys.tcss——最终以两阶段
    等待 + `DescendantFocus/Blur` 内联主变体实心高亮闭环，责任人确认样式
    与时机（修订十三）均正常；
  - "下次提醒"语义：不写 `asked_at`、每次启动再弹（test_should_ask_rules
    与手工复测一致）。
- R13 集中化（修订十四，2026-11-12）：`ruff check --no-fix` /
  `format --check` 全绿；`ruff check --select RUF001,S603 --ignore-noqa`
  复核 **0 处**（改动前同命令 9 处：7 RUF001 + 2 S603），证明豁免来自
  配置级 `per-file-ignores` 而非散落 noqa；`--strict` 111/152/0、
  R2/R3 两门 OK。改动仅 lint 配置与注释，无行为变更。

## 未验证事项（如实申报）

- Windows wrapper 为静态构造（PowerShell 序列），未在 Windows 实机跑过
  （test-plan 冒烟 8 待做，Windows CI 会跑命令串断言）。
- 真实内网环境全链路（后端未就绪，责任人称环境属预期）。
- 成功 relaunch（安装脚本真成功后的会话恢复）只在 file:// e2e 与命令串
  断言层覆盖；真实镜像成功路径未实测（mock 恒 404）。
- 最终态 Smart Test（全量门禁）未跑完：实施期首轮 23234 passed / 2 个
  `tzset` 环境性 error（与本批无关），冒烟修订后（含修订十四）仅跑
  auto_update 套件与独立门禁；定稿前需按最终 paths 复跑一次。
  > 2026-11-12 补记（记录档追加，不触发重签）：已按最终 paths 跑完，
  > 因 `pyproject.toml` 升级为全量 `--full`——定制 697 passed 47 skipped、
  > 上游 38096 passed 143 skipped + 同样 2 个 `tzset` 环境性 error、
  > architecture 补跑 1251 passed 1 deselected。三分类判定不变（上游
  > `test_usage_report.py` 的 `time.tzset()` 在 darwin 无该 API，本批零
  > 触碰）。证据见 verification.md「最终态 Smart Test」，**本项闭环**。
- `test_state.py::test_is_today_uses_the_local_calendar_day` 在
  `00:00–01:00`（本地 CST）会因"一小时前仍同一天"的断言失败：
  `2026-11-12 00:11 CST` 实跑 1 failed / 63 passed，`TZ=UTC` 复跑同一
  套件 64 passed。`state.py` 与该测试文件本轮零改动，判定为**既有跨午夜
  时钟边界缺陷**，与 R13 集中化无关；是否单开微改动修该断言待责任人裁定
  （本轮按 R5 未扩大改动范围）。
  > 2026-11-12 补记（记录档追加，不触发重签）：责任人核实该用例系本批次
  > 新增后裁定修复，修订十五已固定当天中午；本地 `00:26 CST` 与 UTC /
  > 纽约 / Kiritimati 三个时区均 64 passed，本项**闭环**。证据见
  > verification.md「修订十五机器验证」。

## 未验证 / 待裁决事项（评审处置复跑时新增，如实申报）

> 本节为 2026-11-12 评审处置复跑时的**历史快照**，下方原文按 R10
> 不改写；撞号事项已由责任人裁决并闭环，见本节末尾补记。

- **跨批次登记号撞号（本轮复跑新发现，非本批引入）**：并行批次
  `skills-aixcoding-dirs`（已 tracked，他人工作树）`design.md:243-244`
  占了 C158 / C159-C160；本批 `design.md:102` 以 C157 为高水位同样从
  C158 起编，故 `gen_customizations.py --strict` 报 2 个 duplicate id。
  本批评审处置前 `--strict` 111/152/0 全绿；本轮对 `design.md` /
  `pyproject.toml` / 他人文件均零改动。按 R6 与 ADR-0012，编号后移属
  免判定清单外动作（改动已签认 design 正文、需重签、影响全批引用），
  **已停下未擅自处置**，待责任人裁决哪一批后移。证据与命令输出见
  verification.md「独立第二 AI 评审处置」。

> 2026-11-12 补记（责任人裁决「本批后移」＋授权，记录档追加，不触发
> 重签）：上条「待裁决」**已闭环**。责任人明确由本批后移编号；实测
> 当前活跃登记最大 C166、C167-C171 已备案撤销且不复用，故取
> **C172 / C173**（原 C158/C159）。改动落点：`design.md`（§4 R2 表、
> §7 登记表、§12 回滚、§0 前置事实 9 补记、头部修订（十六））、
> `plan.md`、`self-review.md`、`verification.md`、`test-plan.md`
> 与 `src/chrys/app/aixcoding/update/runner.py:123` 注释；
> **未触碰他人批次任何文件**，R2 上游 3 个文件及其行数零改动。
> `--strict` 恢复 `check OK — 116 / 161 / 19 design(s) / 7 retired /
> 0 warning`。R2 清单未变，按 DEVELOPMENT §4.1 判定不触发重签；
> 责任人 2026-11-12 明确裁决**不重签**。证据与最终门禁复跑见
> verification.md「责任人裁决：本批后移」。

## 请求

请责任人：① R13 已裁定并落地（2026-11-12），本人重签 design.md 头部签认
字段（R2 清单变更＝修订六缩减 + 修订十四新增 pyproject.toml；头部字段 AI
不得代填）；② 复核 design 正文与实施态的几处表述差（§3.3 i18n 文案、
§2/§3.6 tier 表落点、§12 locales 回滚、§3.4 Windows 管道措辞）；
③ 签认本文件（状态 草案 → 已确认，本人编辑）；④ 确认 Windows 实机冒烟
与真实内网联调的排期（可后置）；⑤ 批准后执行最终态 Smart Test 与 PR。

> 2026-11-12 独立评审补记（记录档追加，不触发重签；原文保留为历史快照）：
> ① design 头部已由责任人重签落盘「已确认 / 2026-11-12」；③ 本文件
> 头部已「已确认 / 2026-11-12」（且本节之上的评审结论节已补齐双 AI
> 标识）；⑤ 最终态 Smart Test 已跑完，见 verification.md「最终态 Smart
> Test」与「独立评审处置」。② design 正文四处措辞差、④ Windows 实机与
> 真实内网联调仍为可后置项（见 plan.md 待办），⑤ 的 PR 尚未提交。
