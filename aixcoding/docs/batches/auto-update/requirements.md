# 需求：TUI 自动更新流程（auto-update）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
> 来源：责任人需求（2026-11-11，三口径已当面拍板，见"目标"）；系 ROADMAP §4 C 类
> "C1 版本更新检测内部化"及 catalog-sync / internal-installer 两批次非目标中预留的
> 独立 update 批次；配置契约按 ADR-0022 第 7 条预留键名接入。
> 修订记录：2026-11-11 初版（完整 §6 管线，开工判定已于同日裁决）。

## 背景与问题

上游 `app/update_check.py` 的更新检查**每天一次、仅 TUI 启动时**跑，查 PyPI → GitHub，
结果只是欢迎页一条静态提示（`chrome.py` notice，命令可点击复制）；不弹框、不执行更新。

内网现实使这条链路整体失效，且需求要求的"确认后自动更新"完全没有支撑：

1. **检测源不可达**：内网用户无法访问公网（internal-installer requirements 背景已钉死），
   当前检查在内网**静默失败**——弹框永不触发；
2. **无确认交互**：无模态框，无"关闭窗口前请保存工作"的提醒；
3. **无更新执行**：提示的升级命令（`uv tool upgrade` 等）面向公网形态，内网形态应为
   重跑内网镜像安装器（`aixcoding/release/install-internal-mirror.{sh,ps1}`，下载制品后
   `chrys install`）；
4. **更新与运行互斥**：包内 installer 的 `_require_no_running_chrys_instances`
   （`installer.py:482`）拒绝在 Chrys 运行中安装——**更新前必须退出 TUI**，这正是
   需求"告知用户将关闭当前窗口"的技术根源。

已就位的基建（本批次消费，不重建）：

- **wire 契约（冻结）**：`GET /csas/api/v2/releases/check?clientType=cli&platform=&architecture=&currentVersion=`
  ——四参数严格校验（缺/非法 → `400 {"error":"invalid_app_release_query"}`）；有更新 →
  `200` manifest v2（`kind`/`version`/`artifact{url,platform,architecture}`/`forceUpgrade`）
  + `ETag`（`If-None-Match` 命中 → `304`）；无更新 → `204`；**客户端不做本地版本比较**
  （`204`/`200` 之外不判断）。mock：`aixcoding/mock/update/`（含 error/garbage/缺字段/
  强制推送等演练模式）。
- **配置契约（ADR-0022 第 7 条）**：`~/.chrys/aixcoding.toml` 的 `[update].base_url`，
  复用顶层 `environment`（`AIXCODING_ENVIRONMENT`，local/dev/prod，默认 prod）；
  环境变量 > TOML；重启生效。
- **更新指令**：内网镜像安装器（internal-installer 批次已落地），URL 根
  `http://82.187.34.98/aixcoding/file/aixcoding`。

## 0.28 资产考古（2026-11-11，分支 `main_aixcoding_cli_0.28.0_final`）

| 资产 | 0.28 形态 | 新分支处置 |
|---|---|---|
| `src/chrys/aixcoding/update_detection.py`（178 行） | 完整客户端：四参数构造、15s 总超时、`trust_env=False` 内网直连、单发无重试全吞错；200 取 `version`+`artifact.url`，204/304 无更新；**不消费 `forceUpgrade`/`releaseNotes`** | R12 内容索引：逻辑同构迁入（新基线重审），`forceUpgrade` 消费为本批次增强（Q5） |
| `src/chrys/aixcoding/config.py` | 平台连接配置：`AIXCODING_EXTENSION_PROFILE/BASE_URL` + `aixcoding.yaml`，tier 表 LOCAL `127.0.0.1:4321/csas` / DEV `81.89.182.150/csas` / PROD `82.187.34.98/csas` | **路径已被 ADR-0022 否决（备选 3）**：改 `aixcoding.toml` `[update].base_url` + `AIXCODING_ENVIRONMENT`，tier 地址表由 update 客户端自带（对齐 auth/模型目录） |
| TUI 消费（`app.py` 启动任务 + `screen.set_pending_update`） | header 可点击徽章（版本号，跳 `artifact.url` 下载页），无弹框 | 本批次升级为模态确认框（三选项），徽章形态是否保留 design 裁决 |
| `tests/app/aixcoding/test_update_detection.py`（12.9 KB） | 客户端契约测试 | R12 内容索引，随客户端迁移改造 |

**后端就绪状态（2026-11-11）**：本机探测 PROD 与 DEV 的 `/csas/api/v2/releases/check`
均返回 HTTP 502。**责任人澄清：当前环境非实际生产环境，访问不了属正常**——502 不构成
"后端未部署"的证据，就绪状态以真实生产环境为准。本批次按冻结契约实现，开发与验收用
mock 驱动；真实环境的检测随后端就绪自然生效，无需客户端变更。

## 目标（含已拍板口径，责任人 2026-11-11）

1. **检测到新版本 → 模态确认框**：展示新版本号，告知"更新将关闭当前窗口，请确认当前
   工作是否已保存；如未保存，请先保存后再更新"；
2. **弹框三选项**（口径②"加上"）：
   - **立即更新**：退出 TUI → 执行内部更新指令（口径③）→ 更新完成后**自动重启 TUI**
     （口径①"执行深度 c"）；
   - **稍后提醒**：本次不更新，下次每日检查（次日）再问；
   - **跳过此版本**：记录该版本号，不再为其弹框（更新版本再发布时恢复提示）；
3. **更新指令**（口径③）：按操作系统执行对应的内部指令（内网可达、负责软件的下载与
   安装）；具体指令内容与来源见开放问题 Q2；
4. **检测源内部化**（建议项，待 Q1 裁决）：以冻结契约接入内网 update 服务器，配置按
   ADR-0022。

## 非目标

- 不做**后台静默**自动更新（用户确认是前提，需求原意）；
- 不做 uv/pipx/pip 公网形态的自动升级执行（内网场景不适用；公网形态是否保留现有
   欢迎页提示条、还是一并切到新流程——design 裁决）；
- 不改包内 installer 的运行中实例阻断逻辑（`_require_no_running_chrys_instances`
   语义保持——它是"先退出再更新"的保障，不是障碍）；
- telemetry（ADR-0022 同样预留，独立批次，殿后）；
- 不做 `serve`/headless/ACP/CI 场景的弹框（沿用现有检查豁免面，`update_check.py:11`）。

## 用户场景

1. **完整更新**：内网用户启动 TUI → 每日检查查内网 update 服务器 → 有新版本 → 弹出
   确认框（版本号 + 保存提醒）→ 用户确认已保存，点"立即更新" → TUI 退出 → 终端中
   更新指令执行（可见进度/结果）→ 完成后 TUI 自动重启（会话恢复口径见 Q3）；
2. **稍后提醒**：点"稍后提醒" → 弹框关闭，当日不再打扰，次日检查后再弹；
3. **跳过版本**：点"跳过此版本" → 该版本不再弹框；服务器发布更新版本后恢复提示；
4. **未保存工作的保护**：弹框文案明确提示保存；用户取消（Esc/点击外部，沿用
   `BaseDialog` 语义）等同"稍后提醒"；
5. **检测失败/无更新**：零打扰（静默，沿用现有失败语义）；
6. **更新指令失败**：用户得到明确错误提示，处置口径见 Q4；
7. **强更（`forceUpgrade=true`）**：弹框仅"立即更新"一项且不可取消（Esc/点击外部
   不关闭）；检查在启动时、无未保存工作，无延迟理由。

## 验收标准（草案，design 细化）

- [ ] 有新版本时弹框出现，文案含版本号与保存提醒；三选项行为逐项正确；
- [ ] "立即更新"链路端到端走通：TUI 退出 → 更新指令执行 → TUI 自动重启且为新版本；
- [ ] "跳过此版本"持久化（重启后仍生效），且不阻断后续新版本提示；
- [ ] 更新指令失败有用户可见的错误提示，TUI 不会停在"既未更新也未重启"的悬空状态；
- [ ] 检测失败、无更新、`app.update_check=false` 三种情况全程静默（现有开关语义保持）；
- [ ] 检测请求符合冻结契约（四参数、ETag/304 消费、400 容错），用 `aixcoding/mock/update/`
      驱动测试；
- [ ] `forceUpgrade=true` 时弹框仅"立即更新"且不可取消，普通版本三选项照常；
- [ ] 上游测试不回归；`gen_customizations --strict` 零漂移（登记以 design 预告表为准）。

## 开放问题（design 前须裁决）

- **Q1 范围（已裁决 2026-11-11）**：**并入，方案 A**——检测源内部化与本批弹框/执行链
  同批交付。依据：接口确系内网接口（0.28 考古证实），本机不可达属环境限制（非后端
  缺失）；不内部化则内网检测永不触发、需求不可验收。配置按 ADR-0022
  （`[update].base_url` + `AIXCODING_ENVIRONMENT`，tier 地址表由 update 客户端自带，
  对齐 auth/模型目录）；开发与验收用 `aixcoding/mock/update/` 驱动。
- **Q2 更新指令（已裁决 2026-11-11）**：指令内容＝**内网镜像安装脚本**
  （POSIX `curl -fsSL <镜像>/install.sh | bash`；Windows `irm <镜像>/install.ps1 | iex`），
  责任人确认。指令**来源**（内置 per-OS 默认对齐 D5 统一 IP、`aixcoding.toml` 可覆盖、
  还是 manifest 下发）留 design 裁决。
  > 执行形态后续修正（design 修订八，责任人首次人工冒烟实测）：POSIX 的
  > `curl | bash` 管道会让 404 伪装成成功并重启，已改为"先下载到临时文件再
  > 执行"；Windows 保留 `Invoke-RestMethod | Invoke-Expression`，但
  > `-ErrorAction Stop` 挂到下载命令本体使失败终止。此处保留原始裁决口径，
  > 现行形态以 design §3.4 为准。
- **Q3 重启后会话口径（已裁决 2026-11-11）**：**恢复当前会话**（重启时透传原会话，
  打开用户更新前的会话）。
- **Q4 更新失败处置（已裁决 2026-11-11）**：**失败后停止**——不自动重启旧版，停留在
  终端显示错误信息，由用户处置后手动重启。
- **Q5 强更语义（已裁决 2026-11-11）**：`forceUpgrade=true` 时弹框**仅"立即更新"一项，
  不可取消**（Esc/点击外部不关闭）——检查发生在启动时，不存在未保存的工作，无延迟
  理由。普通版本三选项照常（保存提醒文案保留，需求原文）。

> 2026-11-12 责任人补裁（活文档追加，原文保留为历史快照）：
> ① **不支持英文**，维持 ADR-0005/0010 中文单语，本批不启动 i18n
> 例外程序、不引入 `msg()`/pot/po；弹框文案继续走纯中文常量。
> ② **退出通道统一**：两种弹框均为严格模态，Esc 与点击外部都
> 不关闭，只能经按钮退出（design 修订十七）。上文需求 4「用户取消
> （Esc/点击外部，沿用 BaseDialog 语义）等同稍后提醒」的处置口径
> **改为按钮路径**：普通版本仍可用「下次提醒 / 跳过此版本」显式
> 取消，「未保存工作保护」由弹框文案与按钮承载；检查在启动时、
> 不存在未保存的工作这一前提不变。Q5「普通版本三选项照常」不变。
