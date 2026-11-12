# 验证记录：TUI 自动更新流程（auto-update）

> 实施完成后填写；每条验证附命令与结果（R8）。活文档，签认前可补。

## 2026-11-11 实施完成首轮机器验证

- 定制测试（本批次五件）：

  ```
  $ uv run pytest aixcoding/tests/auto_update/ -n0 -q
  57 passed in 5.04s
  ```
  （test_client 14：冻结契约全分支 + tier/base_url 优先级 + auth 主机 drift 钉 + 超时上界；
  test_state 10：缓存往返/降级/原子写/当日判定/计数/标记生命周期；
  test_dialog 6：三选项、强更单选项且 Esc/backdrop 不关、重复 dismiss 恰好一答；
  test_runner 9：per-OS 命令串（等待前缀/失败追加/零删除/镜像根派生）+ 假命令
  端到端（等待-执行-重启序、失败计数且不重启）；test_flow 18：gate 矩阵、D2 双闸、
  三选项状态迁移、缓存重显/到期检查。）

- 全量 aixcoding 定制测试（config 扩展连带）：

  ```
  $ uv run pytest aixcoding/tests/ -n0 -q
  690 passed, 47 skipped in 94.58s
  ```

- 登记对账（预期 110/151/0，design §7）：

  ```
  $ uv run python aixcoding/tools/gen_customizations.py --strict
  gen_customizations: check OK — 110 registration row(s) / 151 marker(s)
  across 18 design(s), 7 retired id(s), 0 warning(s)
  ```

- 静态检查：

  ```
  $ uv run ruff check src/ aixcoding/tests/auto_update/     → All checks passed!
  $ uv run ruff format --check（涉及文件）                    → 全部已格式化
  $ uv run ty check --error-on-warning --python-platform {linux,darwin,win32} src/chrys
                                                              → 三平台 All checks passed!
  ```

- Smart Test（--paths=本批次全部变更路径）：

  ```
  $ uv run python scripts/chrys_test.py --smart --paths \
      src/chrys/app/tui/app.py src/chrys/service/aixcoding/config/loader.py \
      src/chrys/service/aixcoding/config/types.py src/chrys/app/aixcoding/update/ \
      src/chrys/service/aixcoding/update/ aixcoding/tests/auto_update/
  tests         23234 passed, 42 skipped, 2 errors (exit 1)
  ```
  2 个 error＝`tests/service/analytics/test_usage_report.py` 两用例 setup 时
  `time.tzset()` AttributeError——**环境性既存失败**（本机 Python 3.14.10 darwin
  构建无 `tzset`，`hasattr` 实测 False；该文件属上游提交 d9201466，本批次零触碰、
  零 import 交集；CI Linux 上该 API 存在）。三分类判定：与本变更无关。

- Architecture 守卫（Smart Test 因上述环境 error 未选跑，本地补跑）：

  ```
  $ uv run pytest tests/architecture -n0 -q -m "not integration and not gc_calibration"
  1249 passed, 1 deselected → 首跑 2 failed（均为本批次合法捕获）：
  ① test_test_hygiene::subprocess-explicit-stdin——spawn_wrapper 两处 Popen 未设
    stdin → 已修（stdin=subprocess.DEVNULL）；
  ② test_trajectory_wait_inventory——check_for_update 3 个等待未分类 → 已按守卫
    命令刷新 manifest（默认 unresolved 规则，逐项复查：15s 总上界网络等待、无
    控制流交接语义，与 catalog 同类同规则）。
  复跑两项守卫 + auto_update 57 用例 + ruff → 全绿。
  ```

## 实施与设计的三处偏差（如实记录，见 self-review.md）

1. **R2 清单缩减**（design 修订六）：对话框文案走 `login.py` 同构的纯字符串常量，
   不经 msg()/i18n 流水线，原 R2 2/3 号（locales pot/po）取消；R2 收敛为仅
   app.py 一处（C158）。**按 R10 须责任人重签 design**。
2. **tier 表落点**：design §2 写"tier 表归 commands.py"，实施中因依赖方向
   （service 档 client 需要它、app 档 commands 只能下行引用）落在
   `service/aixcoding/update/client.py`，`commands.py` 复用其
   `resolve_check_base()` 派生镜像根——单一来源不变，方向更正。
3. **弹框回执通道**：design §3.3 写 `on_confirm` 回调，实施为 `on_result`
   （confirm/later/skip 三态经 `BaseDialog._before_dismiss` 钩子统一投递，
   backdrop/Esc/按钮全部经同一漏斗，恰好一次）。对话框仍不持有 runner 依赖。

## 实施期新增的 lint 事项（R13，待责任人批准）

- `dialog.py`/`flow.py` 文件级 `# ruff: noqa: RUF001`（中文全角标点，对齐
  `app/aixcoding/tui/*` 的 pyproject per-file-ignores 先例——若责任人倾向
  pyproject 条目形态，改法为在 `[tool.ruff.lint.per-file-ignores]` 增加
  `"src/chrys/app/aixcoding/update/*" = ["RUF001"]`，二者取一）。
- `runner.py` 文件级 `# ruff: noqa: RUF001`（修订十新增：失败输出的中文提示
  常量，与上两条同族同处置）。
- `runner.py` 行内 `# noqa: S603` ×2（`spawn_wrapper` 的 Windows/POSIX 两处
  Popen；固定 argv 非 user input，`crypto.py` 同款先例）。
- 测试侧无新增豁免（`aixcoding/tests/**` 既有 `S`/`RUF001` per-file-ignores 覆盖）。
- 合计＝RUF001 文件级 ×3 + S603 行内 ×2，与 self-review.md 的 R13 block 一致。

> 2026-11-12 修订十四结论：本节 5 处散落豁免**已全部删除**，改
> `pyproject.toml` 单条目录级条目（见「修订十四机器验证」）。本节保留为
> 实施期决策留痕，不再是待批事项。

## 首次人工冒烟发现并修复的缺陷（2026-11-11，design 修订八）

责任人本地冒烟（mock server 404 场景）点"立即更新"：TUI 退出后**仍自动重启**，
`update-failures` 未计数——期望失败即停（R-需求④）。根因：POSIX wrapper 用
`curl -fsSL <url> | bash` 管道，退出码取管道末位 bash 的，curl 404 失败后空输入
bash 退出 0，`&&` 误判成功；Windows 同病（`-ErrorAction Stop` 原挂尾部
`Invoke-Expression`，下载 404 为非终止错误穿透）。测试盲区：原 e2e 用
`echo`/`false` 直接当命令，未覆盖"下载失败"路径。

修复（两平台同修）：弃管道，改"mktemp 临时文件 → `curl -o "$tmp"` →
`bash "$tmp"`，检查退出码"；Windows `-ErrorAction Stop` 挂到 `Invoke-RestMethod`
本体。`update_command()` 删除，`commands.py` 只留 `install_script_url()`。
临时文件两分支各自 `rm -f`，D2 语义不变（wrapper 对 flow 状态文件零删除）。

修复后机器验证（2026-11-11）：

```
$ uv run pytest aixcoding/tests/auto_update/ -q    → 59 passed（新增
  test_wrapper_download_failure_tallies_and_stops 下载失败回归；e2e 改用
  file:// 假安装脚本：成功/脚本 exit 1/下载失败三路径）
$ uv run ruff check/format（改动文件）              → 全绿
$ uv run ty check --error-on-warning src/chrys      → darwin 全绿
$ uv run python aixcoding/tools/gen_customizations.py --strict
                                                   → 110/151/0（marker 无增减）
```

责任人复测指引：`rm -f ~/.chrys/aixcoding-update.json` →
`AIXCODING_UPDATE_FORCE=1 AIXCODING_ENVIRONMENT=local … uv run aixcoding-cli` →
点"立即更新" → 预期 TUI 退出、终端可见 `curl: (22) … 404` 与错误提示、**不重启**、
`~/.chrys/update-failures` 增加一行。

## 修订九机器验证（2026-11-11，"下次提醒"语义 + 方向键切换）

```
$ uv run pytest aixcoding/tests/auto_update/ -q    → 61 passed（新增
  test_arrow_keys_switch_button_focus；should-ask/later 测试改写为每次启动
  都弹口径；test_state 增加旧文件 asked_at 忽略用例）
$ uv run ruff check / format（改动文件）            → 全绿
$ uv run ty check --error-on-warning src/chrys      → darwin/linux/win32 全绿
$ uv run python aixcoding/tools/gen_customizations.py --strict
                                                   → 110/151/0（marker 无增减）
```

## 修订十机器验证（2026-11-11，失败输出条件式提示行）

```
$ uv run pytest aixcoding/tests/auto_update/ -q    → 61 passed（形状测试两平台
  均断言提示行存在；e2e 失败路径断言不变）
$ uv run ruff check / format（改动文件）            → 全绿（runner.py 新增
  文件级 RUF001 豁免，R13 待批）
$ uv run ty check --error-on-warning src/chrys      → darwin 全绿
```

## 修订十二机器验证（2026-11-11，弹框键盘问题终审）

根因定位（pty 真实 TUI + 埋点 + SVG 导出 + harness 隔离实验，详见 design
修订十二）：①`AgentLoadDialog` 在更新弹框之后压栈吃键 → 弹框延迟 30s；
②App flat 按钮焦点标记仅 70% 透明度变暗 + DEFAULT_CSS 永远输给
chrys.tcss（实测：同选择器 App 源生效、DEFAULT_CSS 源失效）→ 焦点高亮
改 `DescendantFocus/Blur` 内联样式。责任人 debug 日志实测 Tab 焦点循环
正常（功能从未坏，不可见的是标记）。

```
$ uv run pytest aixcoding/tests/auto_update/ -q    → 65 passed（新增
  test_focused_button_carries_a_visible_inline_highlight、
  test_dialog_delay_is_thirty_seconds、_ask 等待启动模态两个用例）
$ uv run ruff check / format                        → 全绿
$ uv run ty check --error-on-warning src/chrys      → darwin 全绿
  （注：shell 需 VIRTUAL_ENV 正确，否则 ty 误解析到系统 site-packages 报
  chrys.workflows unresolved-import，与本批无关）
```

## 修订十三机器验证（2026-11-11，去除 30s 硬延迟）

两阶段等待（phase 1 grace 5s 等启动模态出现 → phase 2 等栈无模态）。
责任人确认高亮观感终审通过（三按钮静止暗色、聚焦独占主变体实心填充）。
上一节 65 passed 中的 `test_dialog_delay_is_thirty_seconds` 与
`DIALOG_DELAY_SECONDS` monkeypatch 随硬延迟一同删除；`_ask` 等待用例保留
（栈已干净的场景 monkeypatch `STARTUP_MODAL_GRACE_SECONDS = 0.0`）。

```
$ uv run pytest aixcoding/tests/auto_update/ -q    → 64 passed
$ uv run ruff check / format                        → 全绿
$ uv run ty check --error-on-warning src/chrys      → darwin 全绿
```

## 最终态收尾复验（2026-11-11，修订十三后无代码再改）

文档收尾阶段按 R7 复跑一次可复现的独立门禁（未跑全量 Smart Test——那是
责任人批准后的 PR 前动作）：

```
$ uv run pytest aixcoding/tests/auto_update/ -n0 -q
  64 passed in 6.50s
$ uv run ruff check src/chrys/app/aixcoding/update/ \
      src/chrys/service/aixcoding/update/ aixcoding/tests/auto_update/
  All checks passed!
$ uv run ruff format --check（同上三处）
  13 files already formatted
$ uv run ty check --error-on-warning --python-platform darwin src/chrys
  All checks passed!
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 110 registration row(s) / 151 marker(s) across 18 design(s),
             7 retired id(s), 0 warning(s)
$ uv run python aixcoding/tools/check_docs.py
  scanned 24 ADR(s), 40 design(s), 39 self-review(s) → OK
  （默认模式允许本地草案；self-review.md 仍为草案）
$ uv run python aixcoding/tools/check_docs.py --closure
  FAILED with 1 error(s)：
  auto-update/self-review.md: draft decision/review document is forbidden by closure
```

三分类判定：代码与独立门禁全部绿；无新增失败、无新增豁免、无新增上游文件。
`--closure` 的唯一失败＝`self-review.md` 状态仍为草案，属 R10 签认前的**预期**
结果，不是回归——责任人签认后该门即过（design.md 已是「已确认」，六件齐全）。

> 2026-11-12 修订十四注记：本节是修订十三时刻的快照，110/151 已被
> 111/152 取代（C159 登记），"无新增上游文件"亦随之失效——修订十四按
> 责任人批准的 R2 新增了 `pyproject.toml` 一行。现行状态见下节。

## 修订十四机器验证（2026-11-12，R13 集中化）

责任人裁决方案①：批准 R2 新增 `pyproject.toml` 一行。改动＝该文件增单条
`"src/chrys/app/aixcoding/update/*" = ["RUF001", "S603"]`（含 R3 marker
与批准指向），删 `dialog.py` / `flow.py` / `runner.py` 三个文件级
`# ruff: noqa: RUF001` 与 `runner.py` 两处行内 `# noqa: S603`；
`design.md` §4 R2 表新增第 5 行、§7 登记 C159、strict 预期改 111/152/0。
同族先例＝`catalog-auth-gating/design.md:20-25`（不新增文件级 noqa、
就地注释含理由与批准指向）与 `pyproject.toml:237`（installer.py 集中式 S603）。

```
$ uv run ruff check --no-fix src/ tests/ scripts/… aixcoding/tests/auto_update/
  All checks passed!
$ uv run ruff format --check（同范围）
  2761 files already formatted
$ uv run ruff format src/chrys/app/aixcoding/update/runner.py
  1 file reformatted   （删 noqa 后两处 Popen 压成单行，复跑 --check 全绿）
$ uv run ruff check --no-fix --select RUF001,S603 --ignore-noqa \
      --output-format concise src/chrys/app/aixcoding/update/
  All checks passed!   （改动前同命令 9 errors：7 RUF001 + 2 S603）
$ uv run ty check --error-on-warning --python-platform darwin src/chrys
  All checks passed!
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 111 registration row(s) / 152 marker(s) across 18 design(s),
             7 retired id(s), 0 warning(s)   （与 design §7 预期一致）
$ uv run python aixcoding/tools/check_r2_diff.py --base HEAD
  check_r2_diff: OK
$ uv run python aixcoding/tools/check_r3_markers.py --base HEAD
  base=HEAD upstream_changed=3 marker_checked=2 exempt=3 → OK
$ uv run python aixcoding/tools/check_docs.py
  OK   （--closure 仍 1 error：self-review.md 草案，签认前预期）
$ uv run pytest aixcoding/tests/auto_update/ -n0 -q
  1 failed, 63 passed   （00:11 CST，见下）
$ TZ=UTC uv run pytest aixcoding/tests/auto_update/ -n0 -q
  64 passed in 5.86s
$ git diff --check && git diff --stat uv.lock
  OK；uv.lock 未变动
```

三分类判定：`test_state.py::test_is_today_uses_the_local_calendar_day`
在 `2026-11-12 00:11 CST` 失败——断言「一小时前仍是同一天」跨午夜不成立
（`now - 3600` 落到前一日）。`state.py` 与该测试文件本轮**零改动**；
换 `TZ=UTC` 后同一套件 64 passed，判定为**既有跨午夜时钟边界缺陷**，与
R13 集中化无关。是否单开微改动修该断言待责任人裁定，本轮按 R5 未扩大
范围。其余门禁全绿：豁免标记 5→1、登记 110/151 → 111/152、
`--ignore-noqa` 由 9 处归零（配置级豁免生效，非"删 noqa 瞒过"）。

## 修订十五机器验证（2026-11-12，时钟注入）

责任人裁定口径：「本次新加的测试就修，否则不修」。三条证据判定
`test_is_today_uses_the_local_calendar_day` **系本批次新增**：
①`aixcoding/tests/auto_update/test_state.py` 未被 git 跟踪，整个
`auto_update/` 目录为 R4 新增；②该用例名在 git 全史唯一出现于
`0a53ecb4`（2026-11-11「untracked files on main_aixcoding_cli」快照，
19 个新文件 2578 行）；③0.28 final 分支无 `is_today`/state 相关测试，
本节首轮亦记为「test_state 10：…当日判定…」。→ 按条件修。

修复＝把 `now = time.time()` 改为**固定本地当天中午 12:00**
（`datetime.fromtimestamp(time.time(), tz=UTC).astimezone().replace(hour=12, …)`，
与 `state.py` 的 DTZ-clean 写法同构），产品代码零改动、零上游文件；
`import time` 因 `test_skip_today_marker_lifecycle` 仍在用而保留。

```
$ uv run ruff check --no-fix aixcoding/tests/auto_update/test_state.py
  All checks passed!
$ uv run ruff format aixcoding/tests/auto_update/test_state.py
  1 file reformatted   （复跑 check / format --check 均绿）
$ date → 2026-11-12 00:26:37 CST   （仍在原来的失败窗口）
$ uv run pytest aixcoding/tests/auto_update/ -n0 -q
  64 passed in 7.67s
$ TZ=UTC / TZ=America/New_York / TZ=Pacific/Kiritimati（同套件）
  64 passed / 64 passed / 64 passed
$ uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
  697 passed, 47 skipped in 17.77s
$ uv run ruff check --no-fix src/ tests/ aixcoding/tests/ → All checks passed!
$ uv run ruff format --check（同范围）→ 2810 files already formatted
$ uv run ty check --error-on-warning --python-platform darwin src/chrys
  All checks passed!
$ uv run python aixcoding/tools/gen_customizations.py --strict → 111/152/0 OK
$ uv run python aixcoding/tools/check_docs.py --closure → OK
$ check_r2_diff --base HEAD / check_r3_markers --base HEAD → OK
$ git diff --check → OK
```

## 最终态 Smart Test（2026-11-12，定稿前全量门禁）

按 `DEVELOPMENT.md §4.2` 统一入口 `verify.py --smart`，`--paths` 只列
本批次全部变更路径（8 项，含 `pyproject.toml`、上游 3 文件、定制源码
两目录与测试目录）。**注意：因 `pyproject.toml` 属全局测试配置，Smart Test
按既有规则自动升级为 `--full`**，跑的是完整本地非集成 pytest 范围
（不是 Smart 选样子集）；两套均执行、无短路。

```
$ uv run python aixcoding/tools/verify.py --smart --paths \
    pyproject.toml src/chrys/app/tui/app.py \
    src/chrys/service/aixcoding/config/loader.py \
    src/chrys/service/aixcoding/config/types.py \
    tests/architecture/trajectory_wait_manifest.json \
    src/chrys/app/aixcoding/update/ src/chrys/service/aixcoding/update/ \
    aixcoding/tests/auto_update/
  Smart Test found 8 changed path(s): …（8 项逐一列出）
  Smart Test escalated to --full: global test environment or configuration
                                 changed: pyproject.toml
  Running the complete local non-integration pytest scope …

  custom    passed  exit 0; 697 passed, 47 skipped in 30.26s
  tests     38096 passed, 143 skipped, 2 errors (exit 1)
  architecture  not run: the suite above failed
  Summary: FAILED (exit 1)
  Fork verify Summary: FAILED (exit 1)
```

**2 个 error 的三分类判定：环境性既存失败，与本批无关**：
`tests/service/analytics/test_usage_report.py` 两个用例在 setup
`_utc_plus_eight()` 调 `time.tzset()` → `AttributeError: module 'time'
has no attribute 'tzset'`（本机 Python 3.14.10 darwin，`hasattr` 实测
False；CI Linux 有该 API）。该文件属上游提交 `d9201466`，本批次零改动、
零 import 交集；实施期首轮 Smart Test 亦为同样 2 个 error（见上文）。
与本次修订（R13 集中化、时钟注入）无因果关系。

`architecture` 套件因上游套件 exit 1 被短路未跑，本地按同口径补跑：

```
$ uv run pytest tests/architecture -n0 -q \
      -m "not integration and not gc_calibration"
  1251 passed, 1 deselected in 272.26s
```

**结论**：定制套件全绿、上游完整套件 38096 passed 仅 2 个已知环境性
error、architecture 守卫补跑全绿。除该 2 项外本批改动零回归；CI（Linux）
不受 `tzset` 影响。Smart Test 通过不等于全套件通过，此处实跑的是升级后的
完整范围，口径如实申报。

## 待补（后端就绪后 / 责任人排期）

- 真实环境联调：`/csas/api/v2/releases/check` 上线后，将本机指向真实 tier 复测
  检测-弹框-更新-重启全链路（责任人称当前环境非生产，属预期不可达）。
- Windows 实机冒烟（test-plan 冒烟 8）：wrapper console 输出可见性、
  `Get-Process` 等待、`Invoke-RestMethod -ErrorAction Stop | Invoke-Expression`
  执行与重启。修订八形态＝**POSIX 弃管道改临时文件下载**；Windows 保留
  `Invoke-RestMethod | Invoke-Expression`，但把 `-ErrorAction Stop` 挂到下载
  命令本体，使 404 成为终止错误被 catch 计数（design §3.4「绝不使用管道」
  的措辞比实施态更严格，重签时宜按此口径校正）。Windows 语法为静态构造
  （test_runner 命令串断言），实机行为待验。
- ~~最终态 Smart Test（全量门禁）~~：2026-11-12 已按最终 paths 跑完，
  见下节；**闭环**。PR 待责任人批准执行。
- ~~`test_state.py::test_is_today_uses_the_local_calendar_day` 跨午夜断言~~：
  责任人 2026-11-12 裁定「本次新加则修」，已按修订十五固定当天中午并复验
  任意时区 64 passed（见上节），**闭环**。

## 独立第二 AI 评审处置（2026-11-12，方案 3 最小处置）

评审 AI＝**Deepseek-V4-Pro**（独立第二 AI，与开发 AI 不同源）；开发
AI＝**CodeBuddy / GLM5.3**（标识由责任人提供）。评审读取六件文档与
git diff 后给出 5 项 findings，责任人拍板按方案 3 处置：**零上游改动、
零重签、零提交**，仅动活文档与记录档追加。

| finding | 严重度 | 处置 |
|---|---|---|
| 1 双 AI 评审身份未落盘（头部缺两个字段、无「评审结论」节、「自查主体＝实施 AI」像实现者自查） | blocker | `self-review.md` 补 `评审 AI` / `开发 AI` 字段、更正主体表述、按 SELF-REVIEW-HOWTO §三 新增「2026-11-12 评审结论：通过」节（轮次 / blocker 处置 / 未修项） |
| 2 R1/R2 摘要漏 `trajectory_wait_manifest.json`（实测 3 个上游文件 14 insertions） | suggestion | R1/R2 条目后追加补记，补齐第 3 个文件并说明「须重签」已闭环 |
| 3 「请求」节与头部「已确认」状态矛盾 | suggestion | 「请求」节后追加补记逐项标注闭环，原文保留为历史快照 |
| 4 R13 漏第③类测试豁免（`test_runner.py` 平台 skipif） | suggestion | R13 条目后追加补记补上第 2 类豁免；`plan.md` 的 PR「新增豁免清单」由 1 条改列 2 条 |
| 5 R3/R13 批准注释拆两行、`R13 exemption ledger` 非规范清单名 | nit | **不修**，理由落 `self-review.md` 未修项：门禁已过，压成单行会连带 C159 登记锚、design §4 行数与 `--strict` 复跑；且本轮定位零上游改动 |

复核命令与结果（本轮改动纯文档，零代码 / 零上游文件，故不重跑测试套件）：

```
$ uv run python aixcoding/tools/check_docs.py --closure
  OK   （24 ADR / 42 design / 41 self-review，签认零草案）
$ uv run ruff check --no-fix src/ tests/ aixcoding/tests/
  All checks passed!
$ uv run ruff format --check src/ tests/ aixcoding/tests/
  2812 files already formatted
$ git diff --check
  OK
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check FAILED — 2 error(s), 0 warning(s):
  ERROR skills-aixcoding-dirs/design.md: duplicate id `C158`
         (already used by auto-update/design.md)
  ERROR skills-aixcoding-dirs/design.md: duplicate id `C159`
         (already used by auto-update/design.md)
```

**`--strict` 这两项 error 不是本轮改动引入，且不在本批可控范围，如实申报**：
并行批次 `skills-aixcoding-dirs`（已 tracked，属他人工作树）在
`verification.md:23` 记录「第二轮撞号重编…本批 C147-C160 全段撞号——
整体后移为 **C158-C171**（占号快照 = `main_aixcoding_cli@9d824cb5`
最大 C157）」，其 `design.md:243-244` 已占 C158 / C159-C160；而本批
`design.md:102` 的登记高水位同样是 C157（2026-11-11 `--report` 实测），
故两批**同时从 C158 起编号**而撞号。本批评审处置前 `--strict`
111/152/0 全绿，此次复跑是他人批次落盘后的新状态；本轮对本批
`design.md` / `pyproject.toml` / 他人文件均**零改动**，`check_docs`
扫描数由 40 design / 39 self-review 增至 42 / 41 亦印证并行变更。
撞号须由责任人裁决哪一批后移编号，本轮**未擅自改动任何登记号**。

如实申报：① 修复增量**未再调用评审 AI 复审**，以机器门禁复跑与责任人
抽查为准；② 本轮零上游改动、零重签，C158/C159 登记锚保持原样；
③ 特性分支 `feat/aixcoding-auto-update-v2` 上 24 个文件**已被 stage**
（本轮未执行 `git add`，属并行工作树状态；其中 4 份文档为 `AM`——
index 中是评审处置前的版本，本轮改动仅在未暂存工作区）；
**未 commit / 未 push**。若直接提交，需重新 `git add` 那 4 份文档。

## 责任人裁决：本批后移（2026-11-12，登记号撞号闭环）

责任人裁决原文：「撞号怎么裁决：**本批后移**」＋「授权」。据此把本批
两个登记点整体后移，**未触碰他人批次任何文件**，R2 上游 3 个文件及
其行数零改动。本节为现行状态；上文各历史节中的 C158/C159、
「登记锚保持原样」「待裁决」等陈述均为**当时快照**，按 R10 不改写，
与本节不矛盾。

### 后移目标实测依据

`--report` 在撞号状态下输出不完整，故手工扫描全部 design 的 active /
retired 登记与撤销备案：当前活跃登记最大 **C166**；并行批次
`skills-aixcoding-dirs` 的 C167-C171 已备案撤销且按惯例不复用；本批
原 C158/C159 与该批 C158 / C159-C160 冲突。→ 取 **C172 / C173**
（跳过 C167-C171 号段）。

### 改动清单（本批 6 个文件）

| 落点 | 改动 |
|---|---|
| `design.md` | §4 R2 表、§7 登记表、§12 回滚条目、头部修订（六）/（十四）的 C158/C159 → C172/C173；追加修订（十六）、§0 前置事实 9 补记、§7 表格后补记 |
| `plan.md` | 状态节、实施 C / 修订十四待办、PR 豁免清单的登记号同步；撞号待裁决项改为已闭环；追加后移说明 |
| `self-review.md` | 头部修订（五）、评审结论节补记、未修项登记锚同步；「未验证 / 待裁决事项」保留历史原文并追加闭环补记 |
| `verification.md` | 追加本节 |
| `test-plan.md` | 平台豁免节 R13 ②类登记号同步 |
| `src/chrys/app/aixcoding/update/runner.py:123` | 注释 `registered as C159` → `C173`（纯注释，零行为变更） |

`design.md` 的 §0「登记高水位 C157」、§7 与 §13 的 `--strict`
111/152/0 均**保留为已签认原行**：前者是 2026-11-11 的时刻快照，
后者是「相对本批基线 109/150 各 +2/+2」的内部对账口径；两者各以
追加补记说明，不改写（R10）。同理，`self-review.md` 已签认正文与
本文档各历史验证节里的 111/152/0 保留为历史门禁结果。

### `--strict` 恢复

```
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 116 registration row(s) / 161 marker(s) across 19 design(s),
             7 retired id(s), 0 warning(s)
```

全库绝对值由 111/152 变为 116/161，差值 5 行 / 9 marker **全部来自
并行批次 `skills-aixcoding-dirs` 等他人落盘**，本批自身仍为 +2/+2
（C172 / C173 两行两 marker），`0 warning` 不变。

### 最终门禁复跑（本轮改动后，9 项全绿）

```
$ uv run python aixcoding/tools/check_docs.py --closure
  scanned 24 ADR(s), 42 design(s), 41 self-review(s) → OK
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 116 / 161 / 19 design(s) / 7 retired / 0 warning
$ uv run python aixcoding/tools/check_r2_diff.py --base HEAD
  base=HEAD changed=24 upstream_changed=3 approved_pool=104 → OK
  （其它批次 R2 表历史措辞 warn 若干条，与本批无关、非 error）
$ uv run python aixcoding/tools/check_r3_markers.py --base HEAD
  upstream_changed=3 marker_checked=2 exempt=3 → OK
$ uv run ruff check --no-fix src/ tests/ aixcoding/tests/
  All checks passed!
$ uv run ruff format --check src/ tests/ aixcoding/tests/
  2812 files already formatted
$ uv run pytest aixcoding/tests/auto_update/ -n0 -q
  64 passed in 5.99s
$ git diff --check              → OK
$ git diff --cached --check     → OK
  EXIT CODES: 0 0 0 0 0 0 0 0 0
```

`runner.py` 为纯注释改动，按其归属目录复跑 `aixcoding/tests/auto_update/`
64 passed；**未重跑 Smart Test 全量**（本轮零产品代码逻辑变更，定稿全量
证据见上文「最终态 Smart Test」）。如实申报：Smart Test 通过不等于全
套件通过，此处口径为注释级改动 ＋ 九项独立门禁。

### 签认与 git 状态

- 责任人 2026-11-12 明确裁决「**不重签**」：`design.md` 的 R2 清单
  （3 个上游文件及各自行数）**未变**，按 DEVELOPMENT §4.1 判定不触发
  重签；头部「已确认 / 2026-11-12」保持责任人本人落盘值，AI 未代填，
  本轮亦未改动任何签认字段。
- 本轮按授权以显式路径 `git add` 上述改动；**未 commit / 未 push**。
- 特性分支 `feat/aixcoding-auto-update-v2`；旧分支
  `feat/aixcoding-auto-update` 与提交 `5396dfe1` 保留作备份。

## 弹框严格模态（修订十七，2026-11-12）

责任人裁决「按 B 执行」：两种更新弹框统一严格模态，Esc 与点击外部
均不关闭，按钮为唯一退出路径；同时明确**不支持英文**、不推翻
ADR-0005/0010、不启动 i18n 例外程序。上文各历史节中的「Esc/点击外部
＝下次提醒」「强更框 Esc/backdrop 不可关」「backdrop/Esc/按钮全部经
同一漏斗」等陈述均为修订十七前快照，按 R10 不改写，现行状态以
本节与 design 修订（十七）为准。

### 改动清单

| 落点 | 改动 |
|---|---|
| `src/chrys/app/aixcoding/update/dialog.py` | `dismiss_on_backdrop=False`（原 `not force_upgrade`）；`action_answer_escape()` 改为两种变体共用 noop、保留 `priority=True` binding 吞 Esc 防冒泡；模块 docstring、BINDINGS 注释、`_before_dismiss` 注释同步新不变量 |
| `aixcoding/tests/auto_update/test_dialog.py` | 反转 `test_escape_counts_as_later_on_normal_release` → `test_escape_does_not_close_either_variant`（两种变体按 Esc 后 `answers == []` 且 `app.screen is dialog`）；新增 `test_backdrop_click_does_not_close_either_variant`（`_dismiss_on_backdrop is False` + `pilot.click(offset=(0,0))` 后不产生回答）；强更单选项、按钮回答、重复 dismiss 恰好一答等原用例不变 |
| `design.md` | 追加修订（十七），取代 §3.3 / §9 / §13 的原退出口径，原行不改写 |
| `requirements.md`、`test-plan.md`、`self-review.md`、`plan.md`、`verification.md` | 追加补记，声明现行口径与历史快照边界 |

`test_dialog.py` 用例 7→8；backdrop 点击用例有效性由上游
`tests/app/tui/behaviors/test_click_outside_dismiss.py:150-156`
反证（gate 打开时同一 `pilot.click(offset=(0,0))` 会 dismiss）。

### 不变量与边界

- 普通版本「下次提醒 / 跳过此版本」仍是显式取消路径；「未保存工作
  保护」由弹框文案与按钮承载，不再依赖 Esc/背景点击。
- `_before_dismiss` 的 `None → LATER` 兜底保留为防御；Esc/backdrop
  封死后实际不可达，`flow.py::_ask` 的 `answered` future 只由按钮
  `deliver`，不会产生孤儿回答或挂死。
- 零上游文件、R2 清单（3 个上游文件及行数）未变、零 `locales`/
  pot/po/oracle、零 `pyproject.toml`、零登记号、`--strict` 无波动、
  零新增 R13 豁免；按 DEVELOPMENT §4.1 不触发重签，头部签认字段
  保持责任人 2026-11-12 本人落盘值。

### 机器验证（2026-11-12 最终态，9 项全绿）

```
$ uv run python aixcoding/tools/check_docs.py --closure
  scanned 24 ADR(s), 42 design(s), 41 self-review(s) → OK
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 116 registration row(s) / 161 marker(s) across 19 design(s),
             7 retired id(s), 0 warning(s)
$ uv run python aixcoding/tools/check_r2_diff.py --base HEAD
  check_r2_diff: OK
$ uv run python aixcoding/tools/check_r3_markers.py --base HEAD
  base=HEAD upstream_changed=0 marker_checked=0 exempt=3 → OK
$ uv run ruff check --no-fix src/ tests/ aixcoding/tests/
  All checks passed!
$ uv run ruff format --check src/ tests/ aixcoding/tests/
  2812 files already formatted
$ uv run pytest aixcoding/tests/auto_update/ -n0 -q
  65 passed in 6.11s
$ uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
  715 passed, 47 skipped in 17.08s
$ git diff --check                 → OK
  EXIT CODES: 0 0 0 0 0 0 0 0 0
$ uv run ty check --error-on-warning --python-platform {darwin,linux,win32} src/chrys
  All checks passed! ×3（三平台分别实跑，exit 0）
```

`test_dialog.py` 7→8 用例（`auto_update` 64→65 passed），全量定制
714→715 passed；`--strict` 仍 116/161/0（本轮未新增登记点或 marker）。
`check_r3_markers` 的 `upstream_changed=0` 印证本轮零上游文件改动。

如实申报：**未重跑 Smart Test 全量** —— 本轮改动限于
`src/chrys/app/aixcoding/update/dialog.py` 与 `aixcoding/tests/auto_update/`
两个定制路径，按归属目录复跑 auto_update 与 aixcoding 全量；本批定稿
全量证据仍见上文「最终态 Smart Test」。Windows 分支行为（`pilot.click`
backdrop / Esc noop）由 PR #119 的 Windows CI 复跑确认，本地 darwin
只能验证 POSIX 侧；按 DEVELOPMENT §7，CI 结果证据归 PR checks，不回写
仓库文档。

### 签认与 git 状态

- design 用追加修订记录落法（责任人裁决「追加修订记录」），不重签；
  AI 未代填任何签认字段。
- 本轮**未执行 git 写操作**；提交说明另备，未 commit / 未 push。

## local tier 去 /csas（修订十八，2026-11-12）

责任人裁决「确认只改 mock」＋「local 对应的也去掉」。`catalog.py`
的 local base 是 `http://127.0.0.1:7777`（origin 直出、无 `/csas`），
dev/prod 才带部署前缀；本批 local 原先写成
`http://127.0.0.1:7778/csas`，与既有形态不一致。本次两端配对修正。

### 改动清单（6 个代码/mock 文件、12 处）

| 落点 | 改动 |
|---|---|
| `src/chrys/service/aixcoding/update/client.py` | `_TIER_BASES["local"]` → `http://127.0.0.1:7778`；tier 表注释补「local 从 origin 直出、前缀属真实主机而非冻结路径」 |
| `aixcoding/mock/update/server.py` | `API_PREFIX` `/csas/api/v2` → `/api/v2`（`RELEASE_ROUTE` 与 `:579` 日志由常量派生，自动跟随）；模块 docstring 同步 |
| `aixcoding/mock/update/__init__.py`、`README.md`（2 处）、`aixcoding/mock/__main__.py:90` | 端点路径描述四处同步 |
| `aixcoding/tests/auto_update/test_client.py` | 三处 `_point_at` 去掉 `/csas` 后缀；`test_tier_bases` 的 local 期望改 `http://127.0.0.1:7778` |

`aixcoding/tests/mock/test_update_server.py` 的 6 处 URL 全部由
`update_server.RELEASE_ROUTE` 常量构造，**零改动自动跟随**；
`test_client.py:156` 的 `check_url()` 断言由 `expected` 拼接，同样
自动跟随。

### 明确不动的引用

- **冻结路径段** `api/v2/releases/check` 未变；`/csas` 是 dev/prod
  真实部署主机的前缀，不是 wire 契约的一部分（`design.md §0`
  前置事实 2 的 `GET {base}/api/v2/releases/check` 本就正确）。
- `client.py` dev/prod、`test_client.py` dev/prod/unknown 期望与显式
  `base_url` 覆盖（`http://10.0.0.9/csas`）、`test_runner.py` 三处
  prod 形态 base、`catalog.py` / `auth/environments.py` 的 tier 地址
  全部保留。镜像根取 base 的 **origin**，`/csas` 本就不参与，零影响。
- `requirements.md:28` 冻结契约原文与 `:49` 的 PROD/DEV 502 探测
  记录属真实部署与历史快照，按 R10 不改写，另以补记说明分界。
- 按 R6 未触碰他人批次与考古快照：
  `aixcoding/docs/batches/mock/verification.md:40`、
  `batches/mock/design.md:100`、
  `batches/devtools/archaeology-report-0.28.0.md`（4 处）；
  另约 20 处只提端口 `7778` 不带路径的引用不受影响。
- 零上游文件、R2 清单（3 个上游文件及行数）未变、零登记号、
  `--strict` 无波动、零新增 R13 豁免；按 DEVELOPMENT §4.1 不触发
  重签，AI 未代填任何签认字段。

### 机器验证（2026-11-12 最终态，10 项全绿）

```
$ uv run python aixcoding/tools/check_docs.py --closure
  scanned 24 ADR(s), 42 design(s), 41 self-review(s) → OK
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 116 registration row(s) / 161 marker(s) across 19 design(s),
             7 retired id(s), 0 warning(s)
$ uv run python aixcoding/tools/check_r2_diff.py --base HEAD        → OK
$ uv run python aixcoding/tools/check_r3_markers.py --base HEAD
  base=HEAD upstream_changed=0 marker_checked=0 exempt=3 → OK
$ uv run ruff check --no-fix src/ tests/ aixcoding/tests/ aixcoding/mock/
  All checks passed!
$ uv run ruff format --check src/ tests/ aixcoding/tests/ aixcoding/mock/
  2827 files already formatted
$ uv run pytest aixcoding/tests/auto_update/ aixcoding/tests/mock/ -n0 -q
  152 passed, 2 skipped in 21.84s
$ uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
  715 passed, 47 skipped in 20.51s
$ uv run ty check --error-on-warning --python-platform {darwin,linux,win32} src/chrys
  All checks passed! ×3
$ git diff --check                 → OK
  EXIT CODES: 0 0 0 0 0 0 0 0 0 0
```

`check_r3_markers` 的 `upstream_changed=0` 再次印证零上游文件改动。
本地 mock 端点变更由 `aixcoding/tests/mock/` 全套（含 launcher 组合
服务）覆盖，均通过。

如实申报：**未重跑 Smart Test 全量** —— 本轮改动限于定制目录的
local tier 地址与本地 mock 路由，按归属目录复跑 auto_update / mock
两套与 aixcoding 全量；本批定稿全量证据仍见上文「最终态 Smart
Test」。真实 prod/dev 端点未改，无需内网联调复验。

### 签认与 git 状态

- design 用追加修订（十八）落法、不重签（§4.1，R2 清单未变）；
  五件活文档以补记同步，历史快照原行不改写。
- 本轮**未执行 git 写操作**；提交说明另备，未 commit / 未 push。

## Peer Review 推荐方案 A 修复（design 修订十九，2026-11-12）

### 依据与处置

责任人粘贴 Peer Review 裁决报告并授权「按推荐帮我修改吧」。评审基线
`d764f4d5..951f8884`（4 提交、28 文件 +3975/-8）；本机只读复核确认
finding-A/B/C/D 与 design 已签认正文的措辞差均成立。按推荐方案 A：

- **finding-A**（修）：`aixcoding/tests/auto_update/test_runner.py` 三处
  `skipif(WIN32)` 的 reason 原称「Windows twin runs on Windows CI」，实际
  Windows CI 只有 `test_windows_wrapper_shape` 命令串断言、POSIX 三条
  `file://` e2e 并无同构孪生；改为如实口径（真实 console e2e 属冒烟 8）。
- **finding-C**（修）：`src/chrys/app/aixcoding/update/commands.py`
  `mirror_root()` docstring 删去「flow 判定更新命令不可用」的不实说法，
  改述 base 不可解析时得到相对 `/install.sh|/install.ps1`、由 wrapper
  下载失败分支计数并停止兜底。
- **finding-B**（锚定）：`src/chrys/app/aixcoding/update/runner.py`
  `build_windows_wrapper()` docstring 显式写明镜像安装脚本必须 `throw`
  失败——`exit 1` 在 `Invoke-Expression` 内会终止 powershell 进程、绕过
  catch，导致失败计数与停止提示同时丢失。核对
  `aixcoding/release/install-internal-mirror.ps1`：13 处 `throw`、
  零处裸 `exit 1`，现行脚本符合约定。命令串零改动。
- **finding-D**（留记录、驳回修复必要性）：POSIX `tmp=$(mktemp) || exit 1`
  不追加失败计数，按评审建议不改代码；理由写入 design 修订（十九）。
- **design 修订（十九）**：覆盖六处历史快照措辞差（§3.3 文案走 i18n、
  §3.3 `on_confirm` 签名与答案交付、§3.3/§9/§13 Esc 与 backdrop 口径、
  §2/§3.6 tier 表落点、§12 locales 回滚条目、§3.4 两平台「绝不使用
  管道」与 Windows `IRM | IEX` 实际形态），并声明 §12 现行 R2 三文件
  （`app/tui/app.py` +4/C172、`trajectory_wait_manifest.json` 生成产物、
  `pyproject.toml` +3/C173）与 R13 就地注释状态；原行按 R10 不改写。

### 改动清单（8 个文件，本文件在内）

代码/测试 3 个（`test_runner.py` 三处 reason、`commands.py` docstring、
`runner.py` docstring），design 1 个（修订十九），活文档补记 4 个
（`test-plan.md`、`self-review.md`、`plan.md`、本文件）。`check_r2_diff`
运行时本文件尚未补记，故报 `changed=7`。零上游文件、零登记号、
零新增 R13 豁免、零 i18n/pot/po。

### 机器验证（2026-11-12 最终态，12 项全绿）

```
$ uv run python aixcoding/tools/check_docs.py --closure
  scanned 24 ADR(s), 42 design(s), 41 self-review(s) → OK
$ uv run python aixcoding/tools/gen_customizations.py --strict
  check OK — 116 / 161 / 19 design(s) / 7 retired / 0 warning(s)
$ uv run python aixcoding/tools/check_r2_diff.py --base HEAD
  base=HEAD changed=7 upstream_changed=0 approved_pool=104 → OK
$ uv run python aixcoding/tools/check_r3_markers.py --base HEAD
  base=HEAD upstream_changed=0 marker_checked=0 exempt=3 → OK
$ uv run ruff check --no-fix src/ tests/ aixcoding/tests/ aixcoding/mock/
  All checks passed!
$ uv run ruff format --check src/ tests/ aixcoding/tests/ aixcoding/mock/
  2827 files already formatted
$ uv run pytest aixcoding/tests/auto_update/ aixcoding/tests/mock/ -n0 -q
  152 passed, 2 skipped in 27.44s
$ uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
  715 passed, 47 skipped in 21.26s
$ uv run ty check --error-on-warning --python-platform {darwin,linux,win32} src/chrys
  All checks passed! ×3
$ git diff --check                 → OK
  EXIT CODES: 0 ×12
```

`check_r3_markers` 的 `upstream_changed=0` 与 `check_r2_diff` 的
`upstream_changed=0` 再次印证零上游改动；`--strict` 计数与修订十八后
一致，登记号 C172/C173 未动。本文件补记完成后复跑：
`check_docs --closure` OK、`--strict` OK、
`check_r2_diff base=HEAD changed=8 upstream_changed=0` OK、
`check_r3_markers` OK、`git diff --check` OK（12 项门禁结论不变）。

如实申报：**未重跑 Smart Test 全量**——本轮只改 docstring、测试
`skipif` reason 与批次活文档，按归属目录复跑 auto_update / mock 两套与
aixcoding 全量；定稿全量证据仍见上文「最终态 Smart Test」。Windows 实机
冒烟 8、真实内网联调、普通版本 Esc/backdrop 不关的实机复核仍未做；
PR CI 结论以网页 checks 为准。评审 HOWTO ②「换 AI 交叉」为 Q1 建议非
强制，同源 AI 评审独立性弱，是否补异源交叉由责任人裁决，方案 A 不补。

### 签认与 git 状态

- design 以追加修订（十九）落法、不重签（§4.1，R2 清单 3 个上游文件
  及各自行数未变）；四件活文档以补记同步，已签认原行不改写。
- 本轮**未执行 git 写操作**；提交说明另备，未 commit / 未 push。
