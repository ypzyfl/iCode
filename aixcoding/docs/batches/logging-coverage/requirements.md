# 需求：定制功能日志覆盖补全（logging-coverage）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

2026-11-19 日志覆盖调查（主干 `main_aixcoding_cli` @ 098b66f1，证据为主码实查）确认：auth 与 model catalog 双通道日志完备（批次① logging-routing-fixes 后实态），但**定制功能模块中存在五处日志缺口**——要么完全无日志、要么埋点游离于 `aixcoding` 日志树之外（挂 `getLogger(__name__)` 即 `chrys.*` 名，不进 `aixcoding.log` / `aixcoding.detail.log` 定制卷）。依据 DEVELOPMENT.md §9 分层口径（主通道=用户功能事件、detail=技术事件）与 ADR-0017 双卷机制，缺口清单（行号为 2026-11-19 基线）：

- **① auto-update**：`app/aixcoding/update/{flow,runner}.py`、`service/aixcoding/update/{client,state}.py` 四文件全部 `getLogger(__name__)`——不在 `aixcoding` 树。其中 `runner.py:150`「could not start the update wrapper」WARNING 是用户功能事件（用户已点"立即更新"却无任何反应），现状英文、仅进上游 `debug.log`；用户确认更新/跳过版本的决策动作完全无留痕。
- **② skills 目录定制**：`service/aixcoding/skill_paths.py` 零日志（成功加载了哪些根目录无 trace）；上游 `skills/adapter.py:296,305` 两处吞错 debug 挂上游 logger——目录不可用时用户技能静默消失，无任何卷可查。
- **③ guard install**：`kernel/aixcoding/guard/guard_install.py`（24.3KB）零日志零 print——安装降级事件（hooks.yaml 解析失败→**备份并重置用户配置**、pack 拷贝失败、幂等重装）全程无痕；仅 `orchestration/startup.py:233` 上游兜底英文 WARNING（覆盖 import 失败场景，保留不动）。
- **④ model catalog 自定义模型**：model-config-restore 批次（d07c5d43）恢复自建模型可编辑后，两个**用户可感知事件**仅进 detail 卷——`catalog.py:1023` 自定义模型被后端同 id 覆盖、`catalog.py:986` 旧版无标记目录被清空重建（用户文件被删除）。
- **⑤ 早期通道**：`service/aixcoding/config/loader.py` 的 `_warn` helper 共 **9 处调用点**（`:51` platform config_dir 不可用、`:65/:69` invalid environment、`:97/:104/:108` invalid model_catalog section/base_url/auto_sync、`:116/:120` invalid update section/base_url、`:136` cannot parse 配置文件——评审核实，初稿仅计 3 处系搜索 pattern 漏检），均为"用户可操作的配置错误"且仅 stderr print；`app/aixcoding/startup/__init__.py:32` startup task 失败仅 stderr——均不落任何卷，重启即丢证据。

责任人裁决（2026-11-19，含同日两轮 AI 评审后改判）：立项补全，逐模块通道划分如下（guard 护栏自身状态不进主通道——护栏对用户不可见原则，例外为"备份重置用户配置"一条改判升主通道；catalog 仅"自定义模型被覆盖/删除"两处进主通道；update 检查失败维持主通道——产品定位区别于 catalog；skills 全 detail-only）。

## 目标与非目标

- 目标（六模块，全部改动落在定制文件，R2 上游改动清单为空表）：
  - **auto-update 迁树**：四文件 logger 改挂 `aixcoding.update` / `aixcoding.detail.update`；wrapper 启动失败→主通道 ERROR 双写；用户确认更新/跳过版本→主通道 INFO；**更新检查失败→主通道 WARNING**（2026-11-19 责任人裁决维持主通道：update 是用户想要的功能，失败时用户希望知道并可报工单——与 catalog 强制同步的 detail-only 定位不同；打点在 client.py 失败分支，"无更新"的 204/304 不打；无频控——评审实证检查失败后 flow 退出、进程内至多一次）+ detail；manifest 成功路径细节、state 读写、argv/pid、流程内部异常→仅 detail；
  - **skills（方案 B，零上游改动，2026-11-19 裁决全 detail-only）**：打点落 `skill_paths.py` 函数内部（`adapter.py` 的 except 保持原样）；目录不可用/函数级异常→仅 detail（含栈），任何记录不进主通道；`_team_skill_dirs` 区分 `FileNotFoundError`（常态，静默）与其余 OSError（detail）；成功加载根目录清单→仅 detail；
  - **guard（护栏自身 detail-only；备份重置单点例外）**：`guard_install.py` 补打点——安装/更新/幂等重装、资源缺失、文件写入/备份路径/pack 清单仅 detail（护栏自身状态对用户不可见）；**例外（2026-11-19 责任人改判）**：`_replace_unparsable` 备份并重置用户手写 hooks 配置→主通道 WARNING 双写（用户资产被改变，与 catalog 覆盖/清空同类）；
  - **catalog 两处升主通道**：`:1023` 覆盖警告、`:986` 清空重建警告升主通道 WARNING + detail 同文案双写；其余既有 detail 打点维持 detail-only（含 `:997` 发布失败——已核实其 raise 为内部控制流信号，调用方按"已在抛出点打点"口径静默降级，现状合规不动；`:1013` 应用成功维持 detail；catalog 同步失败不升主通道系产品定位：强制同步、模型列表仍可用、用户不应感知同步存在）；
  - **config/loader 双通道**：`_warn` 内部改造统一覆盖全部 9 处调用点（stderr 保留——时序早于日志就绪；+ 主通道 WARNING + detail 同文案双写；logging 未就绪时 Python lastResort 自然落 stderr，无副作用）；
  - **startup task 失败双通道**：同上，stderr 保留 + 主通道 WARNING 双打。
- 非目标：
  - 不动 `propagate` / `panel` 机制与 `[logging]` 配置语义（批次②，未立项）；不做日志合并工具（批次③）；不触碰 ADR-0017 六不变量；
  - 不改任何上游文件：TUI `models/screen.py` 保存/删除动作不加日志留痕（toast 即时反馈已够，责任人裁决）；ACP `session_manager.py` 拒绝留痕（可选项，不做）；skills 不改 `adapter.py`（选方案 B）；`orchestration/startup.py` 兜底 WARNING 保留原样；
  - guard 护栏自身状态（安装/更新/幂等/缺失）不进主通道/面板（用户不可见原则；例外仅"备份重置用户配置"一条，2026-11-19 改判）；
  - 不为 `sdk_openai.py` keyless、`command_migration.py`、TUI 徽标/indicator 等补日志（性质为纯函数或已由 auth session 层覆盖）。

## 用户场景

1. **自建模型被覆盖**：用户自建模型 id 与服务端下发目录同 id，同步后用户配置被后端版本替换——主卷出现中文 WARNING「以下自定义模型与后端模型 id 相同，已被后端版本覆盖：…」，用户可改自己的模型 id 避免冲突；旧版无标记目录被清空重建同理；
2. **更新点了没反应**：用户在确认对话框点"立即更新"，wrapper 启动失败——主卷出现 ERROR（中文），用户知道本次未更新、程序未退出；更新检查失败（网络/服务异常）主卷出现 WARNING，用户可报工单；确认更新/跳过版本的决策在主卷留痕；
3. **用户手写 hooks 配置被护栏重置**：hooks.yaml 无法解析时护栏备份并以模板重置——主卷出现 WARNING（含备份路径指引），用户可从 `.pre-guard` 备份找回手写配置；
4. **开发排障自包含**：guard 安装降级（含 hooks.yaml 备份重置路径）、skills 目录加载失败原因、update manifest 请求细节——`aixcoding.detail.log` 单卷可查，无需翻上游 `debug.log`。

## 验收标准

- [ ] auto-update 四文件不再出现 `getLogger(__name__)` 定制埋点；`aixcoding.update` / `aixcoding.detail.update` 域 logger 生效（测试断言目标卷收到记录）；
- [ ] wrapper 启动失败：主通道 ERROR（中文）+ detail 双写；确认更新/跳过版本：主通道 INFO；检查失败：主通道 WARNING（client.py 失败分支落点，204/304"无更新"不打；无频控）；
- [ ] skills：`skill_paths.py` 异常路径 detail 记录（含栈）+ re-raise；成功路径 detail 含目录清单；`FileNotFoundError` 静默；主通道/面板零 skills 记录（测试断言）；`adapter.py` 零改动（R2 空表核对）；
- [ ] guard：`guard_install.py` 关键路径（安装、失败、幂等）均有 detail 记录且主通道零记录；例外：`_replace_unparsable` 备份重置→主通道 WARNING + detail 双写（测试断言）；
- [ ] catalog：`:1023` 与 `:986` 两处主通道 WARNING + detail 同文案双写；其余 catalog 记录维持 detail-only（既有断言不回退）；
- [ ] config/loader 九处（`_warn` 全部调用点）与 startup task 失败：stderr 输出保留 + 主通道 WARNING 双打；
- [ ] 主通道新增文案 PII 哨兵：不含 ehr、完整 URL、异常栈（detail 卷独占）；
- [ ] R2 上游改动清单为空表：`git diff` 对照上游文件零改动；
- [ ] `uv run python aixcoding/tools/verify.py --smart --paths <全部改动文件>` 通过；`uv run pytest aixcoding/tests -n0` 全绿；`uv run pytest tests/architecture -n0` 全绿；
- [ ] `uv run python aixcoding/tools/gen_customizations.py`（含 `--strict`）0 error / 0 warning。

## 开放问题

- auto-update / skills / catalog / **config（loader 九处中文文案）** 新增主通道文案的具体措辞（design 给草案，签认时可改）；
- catalog 两处 WARNING 的频控必要性（覆盖类事件每次同步至多一条，初步判断无需频控，design 定案）；
- 域命名确认：`aixcoding.update` / `aixcoding.skills` / `aixcoding.detail.guard` / `aixcoding.config`（design 定案，沿用 `logging_support.get_logger()` 工厂）；
- ADR 判定：本批沿用 ADR-0017 + §9 口径 + 批次①先例，预计不触发新 ADR；"guard 对用户不可见"原则是否落 madr 轻量决策记录，design 阶段判定。
