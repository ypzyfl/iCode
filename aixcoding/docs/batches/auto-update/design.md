# 设计：TUI 自动更新流程（auto-update）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期、确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：

> 修订记录：2026-11-11 初版（requirements 五问已全裁决；R12 索引＝0.28
> `src/chrys/aixcoding/update_detection.py` 考古 + ADR-0022 配置契约）。
> 2026-11-11（二）design 级裁决落稿：D1 并存保留、D2 失败计数临时文件机制
> （责任人方案，取代初版"不缓解"回退）、D3 按建议；D4 待域名确认。
> 2026-11-11（三）D2 修订（责任人）：改双临时文件——计数文件仅追加（wrapper 零
> 删除操作），≥3 次时由 flow 创建"今日跳过"标记并清计数；标记存在则全天不做
> 更新检查。
> 2026-11-11（四）D4 定案（责任人）：更新指令域名 `aicoding.s.bocsys.cn`（http，
> 路径＝镜像目录布局考古值）；检测地址不域名化——参考项目既有配置（catalog
> 同构：共享 environment tier 表 + 基础地址拼路径）。
> 2026-11-11（五）D4 修订（责任人）：**弃域名**——镜像根同样从项目基地址派生
> （检测 base 的 origin + 镜像路径），更新指令与检测地址完全同源。
> 2026-11-11（六）实施期 R2 清单缩减（R10：R2 变更须重签）：对话框文案改
> `login.py` 同构的纯字符串常量（aixcoding TUI 既有风格），不走 msg()/i18n
> 流水线——原 R2 2/3 号（locales pot/po）**取消**，R2 收敛为仅 1 号（app.py
> 接线 C172）。
> 2026-11-11（七）本地冒烟逃生门：`AIXCODING_UPDATE_FORCE=1` 仅越过 SOURCE
> 形态 gate（其余豁免不变），供责任人从仓库 checkout 手工驱动弹框链路
> （§3.5）。
> 2026-11-11（八）首次人工冒烟发现包装器缺陷（责任人 2026-11-11 复测"立即
> 更新"）：`curl | bash` 管道退出码取 bash 的——下载失败（404）时空输入
> bash 仍退出 0，wrapper 误判成功并重启 TUI；Windows 同病（`-ErrorAction
> Stop` 原挂在尾部 `Invoke-Expression`，404 为非终止错误穿透）。**弃管道，
> 改"先下载到临时文件、再执行、检查退出码"**（两平台同修，§3.4）；临时
> 文件两分支各自清理，D2 语义不变（wrapper 对 flow 状态文件零删除）。
> 2026-11-11（九）责任人变更弹框语义：③"稍后提醒"改**"下次提醒"**——不再
> 持久化 `asked_at`、不做当日去重，**除"跳过此版本"外每次启动都弹**（强更
> 行为不变）；state 文件 `asked_at` 字段退役（旧文件读取时忽略）。随冒烟
> 反馈加固对话框键盘链路：`on_mount` 显式聚焦"立即更新"（save.py/
> vision_unsupported.py 先例）+ 方向键切换（`ConfirmDialog` 同款
> `switch_focus`，修订九时误以为 Tab 不可靠，修订十二查明真相后两者皆可）。
> 2026-11-11（十）失败输出追加**条件式提示行**（责任人选方案 B）：wrapper
> 与 shell 提示符的先后是竞态（TUI 退出后提示符即回，wrapper 后台输出
> 落在其后且 shell 不重绘；有时 wrapper 先结束则正常）——失败分支在错误
> 信息后追加"如未出现命令提示符，请按回车返回命令行。"（中英文各一行，
> 两平台同构；方案 A 的 exec 改造被否）。runner.py 随之新增文件级
> `# ruff: noqa: RUF001`（中文常量，与 dialog.py/flow.py 同族，R13 待批）。
> 2026-11-11（十一）弹框改等"屏幕栈干净"再弹（`_wait_for_startup_modals`）
> ——**当日即被证伪**：`AgentLoadDialog` 在更新弹框**之后**才压栈，flow
> 启动瞬间栈即"干净"，随后仍被盖住。由修订十三取代。
> 2026-11-11（十二）弹框键盘问题终审（责任人持续报"Tab 不能切换"，埋点
> 定位）：①启动竞态（修订十一之弊）——临时改弹框延迟 30 秒
> （`DIALOG_DELAY_SECONDS`，修订十三去除）；②焦点不可见——实测验证：
> 本 App 的 flat 按钮焦点标记仅为 `text-opacity: 70%` 文字变暗（无反显
> 无背景变化），且**widget 级 DEFAULT_CSS 在本 App 中无论 specificity
> 均输给 chrys.tcss 的 `Button.-style-flat` 规则**——焦点高亮改为
> `DescendantFocus/Blur` 事件驱动的**内联样式**，失焦清内联回落 CSS。
> 高亮外观终审（责任人反馈"选中状态叠加"）：**三按钮静止统一暗色，聚焦
> 按钮独占主变体实心填充**（`tui-button-primary-background/border/
> foreground`，theme.py 已算好）——高亮即"立即更新"的默认观感，随焦点
> 移动。Tab 本身经埋点确认在稳定态一直可循环（责任人 debug 日志实测
> 焦点依次 update-now→later→skip 回绕）。
> 2026-11-11（十三）去除 30s 硬延迟（责任人）：改**两阶段等待**——
> phase 1 等 `AgentLoadDialog` 出现（grace 5s），phase 2 等屏幕栈无
> 任何模态（上界 10min）；弹框在引擎构建完成后立即出现。
> 2026-11-12（十四）R13 集中化（责任人裁决方案①，批准 R2 新增
> `pyproject.toml` 一行）：删 3 个文件级 `# ruff: noqa: RUF001` 与 2 个
> 行内 `# noqa: S603`，改 `[tool.ruff.lint.per-file-ignores]` 单条目录级
> `"src/chrys/app/aixcoding/update/*" = ["RUF001", "S603"]`——与
> catalog-auth-gating 已签先例同构（不新增文件级 noqa、就地注释含理由与
> 批准指向），豁免条目 5→1。§4 R2 表新增第 5 行、§7 登记 C173、
> `--strict` 预期改 111/152/0。**R2 清单变更须责任人本人重签头部签认
> 字段**（AI 不得代填），本条由 AI 追加、git 留痕。
> 2026-11-12（十六）跨批次登记号撞号裁决（责任人原文：「本批后移」）：
> 并行批次 `skills-aixcoding-dirs` 与本批均自 C158 起编号，`--strict`
> 报 2 个 duplicate id。按裁决本批后移——实测当前活跃登记最大 C166、
> C167-C171 已备案撤销且不复用，故两个登记点由 C158/C159 后移为
> **C172/C173**；§4 R2 表、§7 登记表、§12 回滚条目与头部修订（六）/（十四）
> 的引用同步，`runner.py` 注释与四件文档同步。R2 清单（3 个上游文件
> 及各自行数）**未变**，按 DEVELOPMENT §4.1 判定不触发重签，头部签认
> 字段保持责任人 2026-11-12 本人落盘值；责任人 2026-11-12 明确裁决
> **不重签**。本条由 AI 追加、git 留痕。证据见 verification.md
> 「责任人裁决：本批后移」。
> 2026-11-12（十七）弹框退出通道统一（责任人裁决「按 B 执行」）：
> 责任人明确**不推翻 ADR-0005/0010、不支持英文**，文案维持 `login.py`
> 同构的纯中文常量，i18n 例外程序不启动；§3.3:244 的「msg() 借壳
> en fallback + zh-Hans po」属过时快照，仍列 PR 评审期待复核措辞。
> 退出通道改为**两种弹框统一严格模态**：`dismiss_on_backdrop=False`
> 覆盖普通版本（强更版本原已如此）；`action_answer_escape()` 对两种
> 版本均为 noop，保留 `priority=True` binding 吞掉 Esc 防冒泡；按钮
> 成为唯一退出路径。普通版本「下次提醒 / 跳过此版本」仍是显式取消
> 路径，「未保存工作保护」由文案与按钮承载，而非 Esc/背景点击。
> 本条取代 §3.3「Esc/点击外部＝下次提醒」、§9 假设表首行的失效后果、
> §13 验收第 5 条的原口径；原行按 R10 不改写，现行状态以本条与
> verification.md「弹框严格模态（修订十七）」为准。requirements 需求
> 4 / Q5、test-plan 覆盖矩阵、self-review、plan、verification 同步补记。
> 零上游文件、R2 清单（3 个上游文件及行数）未变、零 locales/pot/po、
> 零登记号、零新增豁免；按 DEVELOPMENT §4.1 不触发重签，头部签认
> 字段保持责任人 2026-11-12 本人落盘值。本条由 AI 追加、git 留痕。

## 0. 前置事实

1. **上游检查与本批并存**：上游 `app/update_check.py`（每日一次查 PyPI→GitHub，欢迎页
   静态提示条）内网不可达、静默失败——本批在其旁新增内网检测流，**不改上游检查
   逻辑**（D1 裁决项）。
2. **wire 契约已冻结**（`aixcoding/mock/update/`）：`GET {base}/api/v2/releases/check`
   四参数；200 manifest（`version`/`artifact.url`/`forceUpgrade`）/ 204 / 304 / 400；
   **版本比较在服务端闭环**，客户端不比较。
3. **ADR-0022 第 7 条预留**：`aixcoding.toml` `[update].base_url`，复用顶层
   `environment`；"服务路径由各自客户端持有"＝tier 地址表归 update 客户端自带；
   "字段只有在对应消费批次才实现"＝本批即消费批次。
4. **配置共享读取器已就位**：`service/aixcoding/config/`（`load_config()` 进程内缓存，
   环境变量 > TOML > tier 默认；`[model_catalog]` 节为同构先例）。
5. **TUI 启动挂接缝**：上游 `app/tui/app.py` push 主屏后 `create_task(_run_update_check)`
   （:1089-1090）为本批接线点；catalog 批次 C034（`main()` 内 lazy import）为同文件
   先例。
6. **对话框基建**：`app/tui/screens/dialogs/base.py::BaseDialog`（点击外部关闭可配、
   防重复 dismiss）；`ask_user.py` 有 escape-noop（不可取消）先例。
7. **installer 运行中阻断**：`installer.py:482` 拒绝 Chrys 运行中安装——更新必须发生在
   TUI 退出之后（wrapper 编排的根据）。
8. **0.28 资产**（R12 内容索引，分支 `main_aixcoding_cli_0.28.0_final`）：
   `update_detection.py`（178 行完整客户端，15s 总超时、`trust_env=False`、全吞错）、
   `config.py`（tier 表：PROD `82.187.34.98/csas` / DEV `81.89.182.150/csas`）、
   `tests/app/aixcoding/test_update_detection.py`（12.9 KB）。
   0.28 的 `AIXCODING_EXTENSION_*` + `aixcoding.yaml` 配置路径已被 ADR-0022 否决。
9. **登记高水位**：C157（2026-11-11 `--report` 实测）；strict 基线 109 行/150 marker/
   0 warning。
   > 2026-11-12 补记（记录档追加，不改写已签认原行）：上条 C157 为
   > 11-11 时刻的历史快照；本批按责任人「本批后移」裁决改用 C172/C173
   > （依据＝当前活跃登记最大 C166、C167-C171 已备案撤销且不复用）。§7
   > 的 111/152/0 是「相对本批基线 109/150 各 +2」的**内部对账口径**；
   > 他人批次落盘后全库实跑为 116 行 / 161 marker / 19 design /
   > 7 retired id / 0 warning，差值 5 行 / 9 marker 全来自并行批次，
   > 本批自身仍为 +2/+2。证据见 verification.md「责任人裁决：本批后移」。
10. **pytest 抑制先例**：C140 wiring 以 `PYTEST_CURRENT_TEST` 抑制进程内自动安装
    （`tests/guard/test_anchors.py:54-59`）——本批检测流同构采用，防上游 TUI 测试
    触发真实网络请求。

## 1. 裁决项

### 1.1 已随 requirements 定案（2026-11-11）

| # | 裁决 | 定案 |
|---|---|---|
| R-需求① | 执行深度 | c：确认后退出 TUI → 执行镜像安装脚本 → 成功后自动重启（恢复当前会话） |
| R-需求② | 弹框选项 | 立即更新 / 下次提醒（修订九：不持久化，下次启动再弹，原"当日不再弹"取消）/ 跳过此版本（持久化） |
| R-需求③ | 更新指令 | 镜像安装脚本（修订八：执行形态改"先下载到临时文件再执行"，弃管道，见 §3.4）：POSIX `curl -fsSL <镜像>/install.sh -o "$tmp" && bash "$tmp"`；Windows `Invoke-RestMethod -Uri <镜像>/install.ps1 -ErrorAction Stop \| Invoke-Expression` |
| R-需求④ | 失败处置 | 失败后停止：wrapper 打印错误、不重启，用户手动处置 |
| R-需求⑤ | 强更 | `forceUpgrade=true` → 仅"立即更新"、不可取消（启动时检查、无未保存工作） |
| R-需求⑥ | 检测源 | 并入内部化（方案 A）：冻结契约 + ADR-0022 配置 + mock 驱动开发验收 |

### 1.2 design 级裁决项

| # | 议题 | 裁决（2026-11-11，责任人） |
|---|---|---|
| D1 | 上游 PyPI/GitHub 检查的存废 | **并存保留**（零上游行为变化，内网静默失败无害，改动面最小） |
| D2 | 更新失败反复弹框/强更锁死的缓解 | **双临时文件**：①失败计数 `update-failures`——wrapper **仅在失败时追加一行，零删除操作**；②当日跳过标记 `update-skip-today`——flow 在计数 ≥3 时创建并**同时删除①**；标记存在且为今日 → **全天不做更新检查**，仅通知（"今日跳过、明日再试"）；用户删除②并重启 ＝ 立即重试。细则见 §3.2/§3.4/§3.5 |
| D3 | 重启命令解析 | 退出前 `shutil.which("aixcoding-cli")` 绝对路径（避免依赖 wrapper 环境 PATH），回退 `sys.argv[0]` resolve |
| D4 | 更新指令地址 | **从项目基地址派生**（2026-11-11 二轮修订，弃域名）：镜像根 ＝ 检测 base（`[update].base_url` > tier 默认，§2）的 origin（scheme+host）+ `/aixcoding/file/aixcoding`——与检测地址**同源同 tier**，一处配置同时移动两端；prod 实效 `http://82.187.34.98/aixcoding/file/aixcoding` |

## 2. 总体方案

```
src/chrys/service/aixcoding/
├── update/                          # 检测客户端（service 档：httpx/config/platform 全在射程内）
│   ├── __init__.py
│   ├── client.py                    # 0.28 update_detection.py 同构迁移 + forceUpgrade 消费
│   └── state.py                     # <config_dir>/aixcoding-update.json：checked_at/latest/
│                                    #   force_upgrade/skipped_version（修订九：asked_at 退役）
│                                    #   + 双临时文件读取：update-failures（计数，唯一写方＝
│                                    #     wrapper）/ update-skip-today（当日跳过标记，写方＝flow）
└── config/
    ├── types.py                     # +UpdateConfig(base_url)（aixcoding 树内，非 R2）
    └── loader.py                    # +[update] 节解析（逐字段降级，对齐 model_catalog 先例）
src/chrys/app/aixcoding/
└── update/                          # 流程编排（app 档：TUI 对话框 + 进程编排）
    ├── __init__.py
    ├── flow.py                      # 启动编排：gate → 状态读取 →（到期则）检测 → 弹框 → 处置
    ├── dialog.py (+ .tcss)          # UpdateConfirmDialog（BaseDialog 派生）
    ├── runner.py                    # 退出-更新-重启 wrapper（detached 子进程，per-OS）
    └── commands.py                  # 更新指令 per-OS 默认 + tier 检测地址表
aixcoding/tests/auto_update/
├── test_client.py                   # 契约测试（mock update server 测试桩真起）
├── test_state.py                    # 节流/跳过/失败计数持久化
├── test_dialog.py                   # 选项可用性、强更不可取消（选项级逻辑 + Textual pilot）
├── test_runner.py                   # wrapper 命令 per-OS 构造断言 + file:// 假安装脚本端到端冒烟（成功/脚本失败/下载失败）
└── test_flow.py                     # gate 矩阵（CI/serve/pytest/SOURCE/开关）+ 状态联动
上游接线（R2，见 §4）：app/tui/app.py 一处 marker 行（C172）+
pyproject.toml 一条目录级 lint 豁免（C173，修订十四）
```

检测地址（责任人 2026-11-11 裁决：**参考项目既有配置，基础地址 + 路径拼接**——
完全对齐模型目录 `catalog.py` 的既有形态）：tier 表归 `commands.py`，键＝共享
environment（`load_config().environment`），dev/prod 与 auth/catalog **同主机**
（一次部署一对 tier，对齐 `catalog.py::_CATALOG_BASES` 及其 drift test 先例），
local 指向 update mock：

| environment | 检测 base | 说明 |
|---|---|---|
| prod | `http://82.187.34.98/csas` | 与 auth（`environments.py:42`）/ catalog（`catalog.py:122`）同主机 |
| dev | `http://81.89.182.150/csas` | 同上（`environments.py:41` / `catalog.py:121`） |
| local | `http://127.0.0.1:7778/csas` | `aixcoding/mock/update/` 默认端口（非 auth 的 7777、非 0.28 telemetry-mock 的 4321） |

完整检测 URL ＝ base + `api/v2/releases/check`（`catalog_url()` 同构拼接）。
优先级：`[update].base_url`（TOML）> tier 默认（`catalog_base_url()` 同构；不设
update 专用环境变量——ADR-0022 未预留）。配套 **drift test** 钉死 dev/prod 与
auth 主机一致（`test_catalog_sync.py` drift 先例）。**更新指令的镜像根同源派生自
同一 base**（origin + `/aixcoding/file/aixcoding`，§3.6）——本表既是检测地址表，
也是镜像根的源；`[update].base_url` 覆盖时检测与更新指令整体移动。

## 3. 模块设计

### 3.1 client.py（检测客户端，R12 同构迁移 + 增强）

0.28 逻辑平移：四参数构造（clientType=cli / platform=sys.platform / arch 映射
amd64→x64、x86→x64 / currentVersion 严格 SemVer）、`asyncio.timeout(15)` 总上界、
`trust_env=False`、单发无重试、全吞错返 None、debug 级日志（含 wire URL 与 body 截断）。

本批增强：`AppUpdate` 增加 `force_upgrade: bool`（manifest `forceUpgrade` 消费——
0.28 明确不消费，本批按 R-需求⑤消费）；`artifact.url` 继续解析但不用于执行
（更新指令按 R-需求③走镜像脚本，`artifact.url` 留作后续批次可能的直装通道，不删解析）。

base 解析（`catalog.py::catalog_base_url()/catalog_url()` 同构）：
`load_config().update.base_url or _TIER_BASES[load_config().environment]`，
URL ＝ base + `RELEASE_CHECK_URL_PATH`（`api/v2/releases/check`）。

### 3.2 state.py（状态文件）

`<config_dir>/aixcoding-update.json`（原子写，复用 `foundation/platform/files.atomic_write_text`）：

```json
{"checked_at": 0.0, "latest": "", "force_upgrade": false,
 "skipped_version": ""}
```

- **checked_at**：24h 节流（时钟回拨视为已过一天，对齐上游 `update_check.py:222` 语义）；
- ~~asked_at~~（修订九退役）：原"稍后提醒当日去重"——语义改为"下次提醒"后无
  可记之物；旧状态文件中的该字段读取时忽略；
- **skipped_version**：跳过版本；新版本（`latest` 变化）自动恢复提示；
- **双临时文件**（D2，独立于上述 json；落 config_dir 而非系统临时目录——后者可能
  被重启清理，且用户需能按提示手工删除）：
  - `update-failures`（失败计数）：**唯一写方＝wrapper，仅在失败时追加一行、零删除
    操作**（§3.4）；flow 启动时消费——mtime 非今日 → 整体删除（"明日再试"＝计数
    不跨日）；行数 ≥3 → 创建 skip-today 标记并删除本文件；
  - `update-skip-today`（当日跳过标记）：flow 创建；存在且 mtime 为今日 →
    **全天不做更新检查**（含网络检测与弹框），仅发一次通知；mtime 非今日 →
    flow 删除后正常流程。用户手工删除本文件并重启 ＝ 立即重试。

缓存重显判定（无网络时的弹框依据，修订九）：`latest` 非空、`latest != __version__`、
`latest != skipped_version` → **每次启动都弹**（"下次提醒"不再做当日抑制）。
不做本地版本大小比较（契约：比较在服务端；字符串不等即"该缓存仍适用"，
服务端降级推送等脏数据场景由 204/新缓存自然收敛）。

### 3.3 dialog.py（确认框）

`UpdateConfirmDialog(BaseDialog)`，构造参数 `(update: AppUpdate, on_confirm: Callable[[], None])`：

- 文案（msg() 借壳 key，en fallback + zh-Hans po，对齐 tui 批次 i18n 先例）：
  标题"发现新版本 {version}"；正文"更新将关闭当前窗口。请确认当前工作是否已保存，
  如未保存请先保存后再更新。"；
- **普通版本**：三按钮（立即更新 / 下次提醒（修订九） / 跳过此版本）；Esc/点击外部＝
  下次提醒（`BaseDialog` 默认语义）；按钮键盘切换：Tab 与**左右方向键**均可
  （`ConfirmDialog` 同款 `switch_focus` 为方向键路径），`on_mount` 显式聚焦
  "立即更新"（save.py/vision_unsupported.py 先例）；焦点高亮为
  `DescendantFocus/Blur` 驱动的**内联样式**（修订十二：DEFAULT_CSS 在
  本 App 输给 chrys.tcss，App 自带焦点标记仅 70% 透明度变暗不可见）；
- **强更**（`force_upgrade=True` 且 `force_failures < 3`）：仅"立即更新"；
  `dismiss_on_backdrop=False` + escape noop binding（ask_user.py:47-50 先例手法）；
- 按钮动作经 `on_confirm` 回调交 flow 处置（对话框不持有 runner 依赖，便于测试）。

### 3.4 runner.py（退出-更新-重启编排）

确认"立即更新"后：

1. **退出前解析**（TUI 进程内）：relaunch 命令（D3：`shutil.which("aixcoding-cli")`
   → 回退 `Path(sys.argv[0]).resolve()`）+ 会话参数（当前会话 id，`-s <id>`；获取
   通道实施时核对公共访问器，不可得则降级为不带 `-s`）+ 当前 PID；
2. **spawn detached wrapper**（stdout 继承当前终端——TUI 退出后输出可见；失败
   输出末尾追加条件式提示行，见修订十）：
   - POSIX：`sh -c 'while kill -0 <pid> 2>/dev/null; do sleep 0.2; done; tmp=$(mktemp) || exit 1; if curl -fsSL <install_url> -o "$tmp" && bash "$tmp"; then rm -f "$tmp"; exec <relaunch>; else rm -f "$tmp"; date +%s >> <failures>; echo <错误提示> >&2; exit 1; fi'`，
     `Popen(..., start_new_session=True)`；
   - Windows：`powershell -NoProfile -Command 'while (Get-Process -Id <pid> ...) { sleep }; try { Invoke-RestMethod -Uri <install_url> -ErrorAction Stop | Invoke-Expression; <relaunch> } catch { Add-Content <failures> <时间戳>; Write-Error <错误提示>; exit 1 }'`，
     `CREATE_NEW_PROCESS_GROUP`；精确语法实施期 Windows 实机冒烟定稿；
   - **先下载再执行（修订八）**：绝不使用 `curl | bash` / `irm | iex` 管道——
     管道退出码取执行端，下载失败（404）时空输入仍退出 0，wrapper 会误判成功
     并重启（首次人工冒烟实发）。`-ErrorAction Stop` 必须挂在下载命令本体
     （`Invoke-RestMethod`）而非尾部执行命令；临时文件在成功/失败两分支各自
     清理，不属于 D2 约束的 flow 状态文件；
3. `app.exit()`（上游 API，无需上游改动）。

等待父进程退出是硬前提（前置事实 7：installer 阻断运行中实例）。其他终端里的
Chrys 实例由安装脚本自身的进程检查处理（在终端中可见阻塞提示，用户可处置）。

**失败计数（D2）**：`<failures>` ＝ `<config_dir>/update-failures`。wrapper **唯一的
文件操作＝失败时追加一行**——安装前/成功后均不删除（计数消费与重置全部由 flow 在
下次启动时完成，§3.5），失败同时打印错误摘要并 `exit 1`（不重启，R-需求④）。
wrapper 是外部 shell 进程，追加一行是其原生能力。

### 3.5 flow.py（启动编排）

接线行调用 `start_internal_update_flow(app, screen)`（内部 `create_task`，返回 task
供测试断言）。流程：

1. **gate**（全豁免，静默返回）：上游设置 `app.update_check` 关（读取通道实施时核对，
   优先 ChrysApp settings 句柄公共访问器）；`running_under_textual_web_driver()`（serve）；
   `CI` 环境变量（对齐上游 `_running_in_ci`）；`PYTEST_CURRENT_TEST`（前置事实 10
   先例）；`detect_install_flavor() is SOURCE`——**可被 `AIXCODING_UPDATE_FORCE=1`
   单独越过**（修订七：本地冒烟逃生门，仅此一项，其余豁免照常生效）；
2. **失败计数闸**（D2，双临时文件，按序判定）：
   - `update-skip-today` 存在且 mtime 为今日 → **全天不做更新检查**，发一条 TUI
     通知（"更新已连续失败 3 次，今日跳过、明日自动重试；如需立即重试，删除
     <标记文件路径> 后重启软件"）后返回；mtime 非今日 → 删除标记，继续；
   - `update-failures`：mtime 非今日 → 整体删除（计数不跨日），继续；行数 ≥3 →
     创建 skip-today 标记 + 删除本文件 + 发上述通知后返回；行数 <3 → 正常流程；
2.5. **弹框等待启动窗口结束**（修订十三，取代修订十二的 30s 硬延迟）：
   两阶段——phase 1 等 `AgentLoadDialog` 出现（grace 5s，快速构建可能
   不出现），phase 2 等屏幕栈无任何模态（上界 10min）——弹框在引擎
   构建完成后立即出现，而非固定等待；
3. 读 state：缓存重显判定（§3.2）成立 → 弹框；
4. `checked_at` 超 24h → `client.check_for_update()`（后台 daemon 线程承载网络，对齐
   上游 `_fetch_in_background` 的"DNS 挂起不拖退出"手法）→ 写 state → 重显判定 → 弹框；
5. 弹框回调处置：立即更新 → runner（§3.4）；下次提醒 → 无需记录（修订九）；跳过 → 写
   `skipped_version`。

### 3.6 commands.py

- 镜像根**从项目基地址派生**（D4 二轮修订）：`mirror_root = origin(base) +
  "/aixcoding/file/aixcoding"`——`base` 即 §3.1 的检测 base（`[update].base_url` >
  tier 默认），`origin()` 取其 scheme+host（`urlsplit`，auth `_replace_origin`
  同构手法）；路径 `/aixcoding/file/aixcoding` ＝ 文件镜像目录布局
  （internal-installer 考古值，与 install 脚本内部默认同源）——prod 实效
  `http://82.187.34.98/aixcoding/file/aixcoding`，`[update].base_url` 覆盖时
  检测与镜像根随之整体移动；
- `install_script_url() -> str`：`{mirror_root}/install.sh`（POSIX）或
  `{mirror_root}/install.ps1`（Windows）——wrapper 先下载到临时文件再执行
  （修订八：原 `update_command()` 管道形态已删，见 §3.4）；
- tier 检测地址表（§2）。

## 4. 上游改动清单（R2）

| # | 文件 | 改动 | 行数 | marker |
|---|---|---|---|---|
| 1 | `src/chrys/app/tui/app.py` | push 主屏后、上游 `_update_check_task` 旁新增接线行：`start_internal_update_flow(self, screen)`（lazy import 对齐 C034 手法） | +4（含 marker 注释与 import） | C172 |
| 2 | `tests/architecture/trajectory_wait_manifest.json` | 生成产物刷新（守卫命令 `uv run python -m tests.support.trajectory_wait_inventory`）：`check_for_update` 的 3 个网络等待以默认 fail-closed `unresolved` 规则入册（15s 总上界、无控制流交接语义，与 catalog 网络等待同类） | +7 | 免 marker（JSON 无法携带注释，守卫强制同批刷新） |
| ~~3~~ | ~~`locales/chrys.pot`~~ | **取消**（修订六：文案改 `login.py` 同构纯字符串常量，不走 i18n 流水线） | — | — |
| ~~4~~ | ~~`locales/zh-Hans/LC_MESSAGES/chrys.po`~~ | **取消**（同上） | — | — |
| 5 | `pyproject.toml` | `[tool.ruff.lint.per-file-ignores]` 新增单条目录级豁免 + 就地 R3 marker 注释（修订十四，R13 集中化） | +3 | C173 |

**零改动**：上游 `update_check.py` / `screen.py` / `chrome.py` / `installer.py` /
`settings.py`（开关复用既有 `app.update_check` 键，不改声明）。

上游测试连带预估：接线行位于 TUI mount 路径，上游 TUI 测试（CI 内跑，`CI` 变量在）
被 gate 豁免；本地无 `CI` 时被 `PYTEST_CURRENT_TEST` 豁免——预期零红面。若实施期
出现红面，按三分类口径甄别后随发现随登记（catalog-sync 先例）。

## 5. 备选方案对比

**对比一：检测流挂点**

| 方案 | 否决理由 |
|---|---|
| A（采纳）app.py mount 路径接线一行 | 最小刀口；catalog C034 同文件先例 |
| B 改上游 `for_this_copy` 返回值注入 | 改上游检查语义（D1 并存决策下不需要），R2 扩大 |
| C `app/aixcoding/startup/_TASKS` 追加 | startup 任务是同步 fail-safe CLI 级（headless/ACP 也跑），弹框需要 TUI 上下文与 asyncio task——语义错位 |

**对比二：更新执行位置**

| 方案 | 否决理由 |
|---|---|
| A（采纳）退出后 detached wrapper 执行 | installer 阻断运行中实例（前置事实 7）；Windows 替换运行中二进制失败 |
| B TUI 内直接执行更新指令 | 同上，且网络下载时长占住退出流程 |
| C 不执行、仅展示命令 | 不满足 R-需求①执行深度 c |

**对比三：状态承载**

| 方案 | 否决理由 |
|---|---|
| A（采纳）独立 `aixcoding-update.json` | 与上游 `update-check.json`（PyPI 检查）语义分离，互不污染；原子写基建现成 |
| B 复用上游 `update-check.json` | 上游缓存含 source 语义（pypi/github），混写引入跨形态误判（上游 :215 的教训） |
| C 无状态（每次启动都查都弹） | 修订九后该项顾虑消失（"下次提醒"即每次启动再弹）；跳过版本仍需持久化，state 文件保留 |

## 6. R12 迁移重审（0.28 → 0.35.1 基线）

| 0.28 形态 | 新基线同类机制 | 判定 |
|---|---|---|
| `src/chrys/aixcoding/update_detection.py` 平铺 | `service/aixcoding/{config,models}` 子包化 + ADR-0011 tier 落位 | **迁 `service/aixcoding/update/`**（tier=service：httpx/config/platform 依赖齐备；消费方在 app） |
| `AIXCODING_EXTENSION_*` + `aixcoding.yaml` 共享配置 | `aixcoding.toml` + `AIXCODING_ENVIRONMENT`（ADR-0022） | **换血**：`[update].base_url` + 共享 `load_config()`；旧路径零兼容（ADR-0022 第 6 条先例） |
| tier 表共享（telemetry/update 同 base） | 各客户端自持 tier 表 | **跟随**：update 自持（LOCAL 指向 7778 mock，非 0.28 的 4321） |
| header 徽章交互 | 上游欢迎页 notice（chrome.py） | **替换为本批确认框**（需求原意）；徽章与 notice 均不保留在内部流（上游 notice 随上游检查并存，见 D1） |
| 不消费 `forceUpgrade` | — | **增强消费**（R-需求⑤） |
| 测试 `tests/app/aixcoding/` | `aixcoding/tests/`（ADR-0001） | **迁 `aixcoding/tests/auto_update/`** |

## 定制点登记预告

（即 §7）

上游接触为单文件单 marker（TUI mount 路径接线行），按下表点级登记。
实施后跑 `--strict` 对账。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C172 | src/chrys/app/tui/app.py | AIxCoding update: internal release check + confirm dialog | 1 | 主屏 push 后接线 `start_internal_update_flow(self, screen)`——内网发布检测（冻结契约）+ 确认弹框 + 退出-更新-重启编排 | 低（新增 4 行接线，删除即完全回滚到上游检查行为） | 〔目录退役〕内网 update 服务与镜像安装器退役，或该流程被产品级方案取代 |
| C173 | pyproject.toml | AIxCoding update: Chinese full-width punctuation and locally-built wrapper argv | 1 | `src/chrys/app/aixcoding/update/*` 的 RUF001/S603 目录级豁免及批准注释（R13 集中化，修订十四） | 低（单条 lint 配置） | 〔目录退役〕该 app 定制目录退役，或中文文案回到上游 i18n 体系且该目录不再有固定 argv 的 subprocess 调用 |

`--strict` 预期：111 行 / 152 marker / 0 warning（相对基线 109/150 各 +2：C172 与 C173）。

> 2026-11-12 补记（记录档追加，不改写已签认原行）：登记号已按责任人
> 「本批后移」裁决由 C158/C159 改为 C172/C173（原号与并行批次
> `skills-aixcoding-dirs` 撞号），依据见 §0 补记。本行 111/152/0
> 保留为「相对本批基线」的内部对账预期；全库实跑为 `check OK —
> 116 registration row(s) / 161 marker(s) across 19 design(s),
> 7 retired id(s), 0 warning(s)`，差值来自他人批次落盘，本批自身
> 仍为 +2/+2。命令与完整输出见 verification.md「责任人裁决：本批后移」。

## 8. ADR 判定

**不触发**。checklist：①有被否决备选（§5 三组）但均为模块内实现选择，不约束未来
工作模式；②无新顶层目录/新机制/规范变更（配置契约 ADR-0022 已覆盖且本批即其预留
消费批次）；③"退出-更新-重启"编排是本需求独有流程，无跨批次复用承诺。ADR-0022
第 7 条"不得视为功能实施授权"＝本 design 承担实施授权（签认后生效）。

## 9. 对上游隐式行为的假设

| 假设 | 依据 | 失效后果 |
|---|---|---|
| `BaseDialog` 可被子类化且 escape/背景关闭可关 | `dialogs/base.py:39`（`dismiss_on_backdrop` 参数）+ ask_user escape-noop 先例 | 强更框可被 Esc 逃逸——测试锚定（§10） |
| ChrysApp 存在当前会话 id 的可访问通道 | `app.py` `startup_session_id` / session 持久化体系 | 重启降级为不带 `-s`（新会话），功能不阻断 |
| `shutil.which("aixcoding-cli")` 在离线安装形态可解析 | internal-installer：alias 落 PATH（`~/.local/bin` 等） | 回退 `sys.argv[0]` resolve；仍失败则 wrapper 报错（Q4 停止语义） |
| detached 子进程继承 stdout 且在父进程退出后继续输出 | POSIX `start_new_session=True` 保留 fd；Windows 同 console 进程组 | 更新输出不可见——冒烟验收项（§13） |
| 上游 TUI 测试不因接线行红面 | gate 三重豁免（CI/PYTEST/开关） | 实施期红面按三分类甄别、随发现随登记（§4） |
| mock update server 可作测试桩起在随机端口 | `aixcoding/mock/update/server.py::create_server`（README 用法） | 契约测试改 httpx MockTransport 手写响应（降级，覆盖不减） |

## 10. 测试策略（细则见 test-plan.md）

- **test_client.py**：mock server 测试桩真起（`create_server`，port=0）：四参数正确性、
  200/204/304/400、`forceUpgrade` 解析、garbage/缺字段静默、tier 与 `[update].base_url`
  优先级（含 dev/prod 与 auth 主机一致的 drift 断言）、15s 总超时（slow 模式缩短
  断言）；
- **test_state.py**：24h 节流（时钟注入）、同日去重、跳过持久化与新版本恢复、原子写、
  双临时文件读取（计数行数/mtime 日期/标记存在性）；
- **test_dialog.py**：普通三选项、强更单选项 + Esc/backdrop 不关（Textual pilot）；
- **test_runner.py**：per-OS wrapper 命令串断言（含 PID 等待前缀、失败追加序、
  **零删除操作**、镜像根随 base 派生）、假命令端到端（fake 脚本写标记文件，
  验证等待-执行-重启序）；
- **test_flow.py**：gate 矩阵（开关/CI/serve/pytest/SOURCE）、失败计数闸（计数 ≥3 →
  建标记+删计数+通知+跳过；标记今日 → 全天不检查；计数/标记非今日 → 重置后正常弹）、
  缓存重显、三选项状态迁移；
- 平台豁免：Windows 专属命令构造断言在非 Windows skip（R13 形态＝skipif，理由＝
  被测路径依赖 Windows 真实 console 行为；批准指向＝本 design 签认；与
  internal-installer POSIX skip 同构）。

## 11. 风险与对策

| # | 风险 | 对策 |
|---|---|---|
| 1 | 更新指令持续失败 → 反复弹框/强更锁死 | D2 双临时文件：当日失败 ≥3 次 → skip-today 标记全天不做检查（明日自动重试；计数不跨日），删除标记＝立即重试（§3.2/§3.4/§3.5） |
| 2 | Windows wrapper 行为（console 输出/进程等待/`start` 语义） | 实施期 Windows 实机冒烟定稿；test_runner 假命令覆盖命令构造层 |
| 3 | 更新后旧二进制路径失效 | D3：退出前解析 PATH 绝对路径；回退 argv[0] |
| 4 | 镜像/检测地址迁移（服务器变更） | 两者同源于 tier 表（与 auth/catalog 同主机）——迁移由 tier 表与 drift test 联动暴露；`[update].base_url` 可整体覆盖逃生 |
| 5 | 服务端脏数据（`force_update` 推旧版本） | 客户端零本地比较（契约）；字符串不等重显的边界在 §3.2 注记 |
| 6 | 弹框打扰 | 24h 检查 + 同日去重 + 跳过版本三层收敛 |
| 7 | `--strict` 基线漂移 | 实跑前后对照（预期 +2/+2，§7） |

## 12. 回滚方案

revert 批次 PR 即净：上游 1 处接线行（C172）+ locales 生成条目随 i18n 流水线刷新；
其余全部为 aixcoding 树内新增。用户侧状态文件 `aixcoding-update.json` 残留无害
（无消费方后即死数据，可手工删除）。

## 13. 验收（对齐 requirements 验收口径）

1. mock server 驱动：有更新弹框（版本号 + 保存提醒文案）、三选项行为逐项正确；
2. "立即更新"端到端（假命令替身）：TUI 退出 → wrapper 等待-执行-重启序成立，
   relaunch 携带 `-s <当前会话>`；
3. 更新指令失败：wrapper 输出错误且不重启（Q4）；
4. "跳过此版本"跨启动持久，新版本恢复提示；
5. `forceUpgrade=true`：单选项且 Esc/backdrop 不可关；
6. 检测失败/无更新/开关关闭/CI/serve/pytest 全静默（gate 矩阵测试 + 冒烟）；
7. 检测请求符合冻结契约（test_client 对 mock server 断言）；
8. 上游测试不回归；`--strict` 111/152/0（§7 预期）；
9. Windows 实机冒烟：wrapper console 输出可见、等待-更新-重启链路（实施期执行，
   证据入 verification.md）。
