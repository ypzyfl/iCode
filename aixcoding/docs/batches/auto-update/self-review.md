# Self-Review：TUI 自动更新流程（auto-update）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期），AI 不得代填。
AI 的自查结论不是签认；签认前 block 条目必须全数闭环。
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：

> 自查主体：实施 AI（CodeBuddy / GLM）。自查范围：本批次全部代码与文档。
> 修订记录：2026-11-11 初版（实施完成后）。
> 2026-11-11（二）首次人工冒烟后更新：修订八～十三（wrapper 弃管道、下次
> 提醒语义、失败提示行、启动窗口两阶段等待、焦点内联高亮）已并入自查。
> 2026-11-12（三）责任人裁决 R13 方案①（design 修订十四）：R2 清单新增
> `pyproject.toml`，5 处散落豁免集中为 1 条目录级条目，R13 block 清零；
> design 头部签认字段待责任人本人重签。

## Block 判定条目（有任何一条为 block 即不得请求签认）

- **R1/R2**：上游改动＝design §4 清单（修订六后仅 app.py 一处 +4 行 C158；
  修订十四新增 pyproject.toml 一行 +3 行 C159，经责任人 2026-11-12 裁决批准）
  ＋ config 两文件为 aixcoding 树内（非上游）。**无清单外上游文件**；
  `check_r2_diff.py --base HEAD` 与 `check_r3_markers.py --base HEAD` 实跑 OK。
  R2 缩减（修订六）与扩充（修订十四）均已落修订记录——**须重签，见下**。
  → 无 block，附待办。
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

## 请求

请责任人：① R13 已裁定并落地（2026-11-12），本人重签 design.md 头部签认
字段（R2 清单变更＝修订六缩减 + 修订十四新增 pyproject.toml；头部字段 AI
不得代填）；② 复核 design 正文与实施态的几处表述差（§3.3 i18n 文案、
§2/§3.6 tier 表落点、§12 locales 回滚、§3.4 Windows 管道措辞）；
③ 签认本文件（状态 草案 → 已确认，本人编辑）；④ 确认 Windows 实机冒烟
与真实内网联调的排期（可后置）；⑤ 批准后执行最终态 Smart Test 与 PR。
