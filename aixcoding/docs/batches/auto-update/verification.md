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
