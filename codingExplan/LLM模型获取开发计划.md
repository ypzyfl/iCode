# LLM 模型获取开发计划（模型选择与传递）

> 关联：[桌面端代码探查.md](桌面端代码探查.md)（**全部证据与文件行号在本文档**，桌面端行为以它为准）、[LLM模型对接获取说明.md](LLM模型对接获取说明.md)（token/用户 ID 的下游对接速查）、[桌面端集成登录开发计划.md](桌面端集成登录开发计划.md)（token 侧里程碑）。
> 更新日期：2026-10-09。状态标记：✅ 已完成 / ⬜ 未开始 / 🔬 离线模拟已验证（[verify_desktop_model_chain.py](verify_desktop_model_chain.py)，真机联调仍需复核）。

---

## 0. 结论（先读这里）

**iCode 侧不需要为"桌面端选 ICode 引擎后的模型处理"做任何开发。** 模型与 Token 的传递机制不同——Token 是"一个 env 变量"（`OPENAI_API_KEY`），模型是**三条通道的组合**——但三条通道在 iCode 侧的接收端**全部是既有能力**，无需新增代码：

| 通道 | 内容 | iCode 接收点（现状） |
|---|---|---|
| ① 文件 | 模型列表物化为 profile YAML，落 `<config_dir>/models/*.yaml` | `service/profiles/models/registry.py` 目录扫描（既有机制） |
| ② 协议 | 每会话 `session/set_model {sessionId, modelId: 裸 profile id}` | `app/acp/server.py::set_session_model` → `session_manager.py::set_model_profile`（已实现，按会话切换） |
| ③ env | `CHRYS_MODEL_PROFILE` = 启动默认 profile（能力协商用，非用户选择）；`OPENAI_API_KEY` = 模型凭据（= token 通道） | `foundation/config/runtime_pointer.py`（既有）、`service/llm/clients.py:190` `api_key or env` 回退（既有） |

余下工作只有 **V1 联调走查**（§5，iCode 侧已可用 [verify_desktop_model_chain.py](verify_desktop_model_chain.py) 离线预验）和**未排期增强**（§6）。

> **2026-10-09 验证结论**：四个接收点的代码现状核对无误（§3 表格行号全部命中）；离线端到端模拟 13 项必需检查全过（initialize 识别、能力协商、set_model、env token、base_url 路由、会话中切模型、失败即中止语义）；S1 接收点测试切片 364 passed。iCode 侧**零代码改动**。两个新发现见 §5（refreshModels 语义修正）和 §7（modelKey printable-ASCII 约束）。
>
> **2026-10-09 二进制产物验证**（针对"桌面端集成本次不改代码是否成立"）：`uv build` 构建本分支 wheel（含 `chrys` + `aixcoding` + docs + 双入口点，`pyproject.toml [tool.hatch.build.targets.wheel] packages = ["src/chrys", "aixcoding"]`）；全新 venv 仅装 wheel 基础依赖（等价 PyApp 首跑安装，无 extras），对安装出的 `chrys.exe` 跑同一套验证 **13/13 全 PASS**（`uv run python codingExplan/verify_desktop_model_chain.py --exe <chrys.exe>`）；再从该 venv 删除 `aixcoding` 包复跑仍 13/13——**ACP 模式完全不依赖 `aixcoding` 包**，模型+token 链路与登录增量解耦。用户 ID 结论见 §5 末尾"用户 ID（`AIXCODING_USER_EHR`）现状"。

## 1. 问题背景

桌面端（agent_studio_new）支持选 iCode 引擎对话。需要回答：桌面端选完模型后模型是怎么到 iCode 的——iCode 要不要像接 Token 那样额外接收，还是要做更多？两个场景：

1. **S1 独立 TUI**：用户自己 `uv run icode`，模型怎么来；
2. **S2 桌面端集成**：用户在桌面端选 iCode 引擎 + 选模型对话。

## 2. S1 独立 TUI 的模型获取（现状，✅ 既有能力）

- **模型从哪来**：内置 profile + 用户自建 `~/.chrys/models/*.yaml`（Windows `%APPDATA%\chrys\models\`）。`icode models` 命令列出；TUI `/model` 屏选择。
- **凭据**：写在 profile 的 `api_key` 里，**或**留空走 env 回退（`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`…，`clients.py:190`）。
- **选择持久化**：活动指针存用户 settings 的 `model.profile.active`（env 形态 `CHRYS_MODEL_PROFILE`）；下一个进程启动沿用（`env_bridge.py`）。
- **与登录无关**：登录改造只影响 token 获取（`aixcoding/auth`），模型配置路径一字未动。S1 用户想用企业模型就自己写 profile（把 `aixcoding.auth.get_login_session().stored_token` 填进 `api_key`，或导出成 env——见 [LLM模型对接获取说明.md](LLM模型对接获取说明.md)）。

## 3. S2 桌面端选 ICode 引擎（现状，✅ 双端均已实现）

完整链路（证据见[桌面端代码探查.md](桌面端代码探查.md)）：

1. 桌面端登录后从业务后端 `POST /csas/web/model/myModelList` 拉模型列表（**不问 iCode**）；
2. 主进程 `prepareChrysModelProfiles` 把每个模型写成 profile YAML 到账号私有 `chrys-home/<chrys|.chrys>/models/`（`api_key` 留空，provider 映射 AIxCoding→openai，base_url 来自 app-config）——**先写文件，后拉进程**，无竞态；
3. 拉起 `chrys.exe acp --agent aixcoding-<hash> --approval manual`，env 带 `OPENAI_API_KEY`（token）、`HOME`/`APPDATA`（让 iCode 发现上面的 profile 目录）、`CHRYS_MODEL_PROFILE`（vision 能力 profile，仅作启动默认）；
4. `session/new` 成功后立即 `session/set_model` 下发用户选中的裸 profile id；iCode 按会话切换引擎模型；查不到 id 报错、桌面端随即中止会话创建；
5. 会话中切模型：同一 `session/set_model` 方法。

iCode 侧四个接收点核对（全部既有）：

| 桌面端动作 | iCode 现状 | 核对结果 |
|---|---|---|
| profile YAML 落盘 | `registry.py:19-22` 扫 `config_dir/models`；字段与 `schema.py::ModelProfile` 一一对应，JSON 写法可被 YAML loader 解析 | ✅ |
| `session/set_model` 裸 id | `session_manager.py:1047` 按 id 精确查、`Model profile not found` 报错、`SetModelProfile` 按会话切换不写全局 | ✅（报错语义正好满足桌面端"失败即中止"） |
| `api_key: ''` | `clients.py:190` `api_key or os.environ["OPENAI_API_KEY"]` | ✅ 与 token 同通道 |
| `CHRYS_MODEL_PROFILE` | `runtime_pointer.py:38-42` → `Settings.model_profile`，每会话 set_model 覆盖 | ✅ |

### 3.1 iCode 侧的存储图谱（模型 / token / 用户 ID 各存哪，2026-10-09 核查）

桌面集成态下 iCode 是被桌面端拉起的 ACP 子进程，`HOME`/`APPDATA` 指向账号私有 `chrys-home`——**iCode 看到的"整个世界"就是这个目录**。三样东西的存储位置：

| 东西 | 存储 | 谁写的 | 持久性 |
|---|---|---|---|
| **模型 profile 定义** | `<chrys-home>/<chrys\|.chrys>/models/<profileId>.yaml`（JSON-as-YAML，`api_key` 空） | **桌面端**（`prepareChrysModelProfiles`，先写文件后拉进程）；iCode 只读不写（`registry.py` 进程内扫一次盘） | 落盘，随账号目录存活；runtime 重建时桌面端重写 |
| **每会话选中的模型** | 内存：会话自己的 `LoadedSettings` SESSION 层 overlay（`controls.py:276 _pin_session_model_profile` 同时 pin `model_profile` + `model_profile_override`）。**不写 settings.yaml、不写 .env、不动全局指针** | iCode（`session/set_model` 触发） | 进程内存；跨进程靠下一条 |
| **会话模型元数据** | `session.json` meta 的 `model_profile_id`（保存时 `builder.py:524` 随 manifest 写入，`store.py:762`）；恢复会话时 `session_lifecycle.py:1030 _reapply_saved_model_profile` 重新应用为 SESSION 层选择（顺带 eager 写一次**子进程自己的** `CHRYS_MODEL_PROFILE` 指针，origin=SESSION，不落盘） | iCode | 落盘（chrys-home 的 sessions 目录），会话 reload 双保险——桌面端即使不重发 set_model 也能恢复模型 |
| **token** | **不落盘**。子进程 env（spawn 时注入的 `OPENAI_API_KEY`），`clients.py:190` 构建请求时读取 | 桌面端（spawn env） | 进程生命周期；ACP 模式无任何持久化路径（委托登录的 RAM-only 设计 + ACP 路径根本不 import `aixcoding`） |
| **用户 ID（ehr）** | 同 token：env（`AIXCODING_USER_EHR`）进程内存，ACP 模式当前无消费方、不落盘 | 桌面端（部分凭据路径才投递，见 §6 探查文档） | 进程生命周期 |
| 会话/轨迹等运行数据 | chrys-home 下的 sessions 目录（config_dir 派生） | iCode | 账号私有目录内，与真实 `~/.chrys` 天然隔离 |

一句话：**模型"存文件 + 存会话内存 pin + 存会话元数据"三层；token 和用户 ID 只在进程 env 里，iCode 一行都不写盘。**

### 3.2 对话发起后 iCode 怎么用桌面选的模型；与本地 TUI 有无冲突

**每次 LLM 调用的解析链**（`resolver.py::resolve_selection_for_agent`，优先级从高到低）：

1. `settings.model_profile_override`——即 `session/set_model` 钉下的**会话 pin**（主 agent 恒生效）→ **命中这里**；
2. agent 档案的 `model.profile_id` 绑定——桌面端 `aixcoding-<hash>` 档案**没有** `model:` 段，跳过；
3. 父继承（子 agent 用）；
4. `model.profile.active` 活动指针（= `CHRYS_MODEL_PROFILE` 能力 profile，只在没有任何 pin 时兜底）。

选中 profile 后凭据组装：`api_key` 为空 → `clients.py:190` 读 `OPENAI_API_KEY` env → wire 上 `Authorization: Bearer <token>`；`base_url`/`model_id`/`stream` 全部来自该 profile（离线模拟已在 wire 上逐项证实，见 §5）。

**与本地 TUI（S1）的模型会不会冲突——不会，四层隔离：**

| 隔离层 | 机制 |
|---|---|
| 配置目录 | 桌面子进程的 `HOME`/`APPDATA` → 账号私有 `chrys-home`；本地 TUI 用真实 `~/.chrys` / `%APPDATA%\chrys`。models 目录、settings.yaml、agent 档案、sessions 两套互不可见 |
| 进程 + env 快照 | 两个独立进程。子进程 env 在 spawn 时定格；本地 TUI 之后改自己 settings.yaml 的 `model.profile.active` 不会被子进程看到（它也不读那个文件——读的是 chrys-home 的） |
| 会话 pin 不写全局 | `set_model` 只改**本会话**的 `LoadedSettings` overlay（SESSION 层），不写 settings.yaml、不写 .env、不动全局指针（`session_manager.py:1047` docstring 明示）；同一子进程里多个 ACP 会话各持各的 pin，互不覆盖。恢复会话的指针 eager 写也只写**子进程自己的** `os.environ`，影响面是该子进程内无 pin 的兜底解析 |
| 反向无污染 | 子进程一切写入（sessions、恢复指针、桌面端发起的 agent 档案 CRUD）都落在 chrys-home 内，永不触碰真实配置目录 → 本地 TUI 的模型选择不受桌面端任何影响 |

唯一理论上的"共享"是同一台机器的两个目录树，但路径不同、由桌面端强制（账号私有目录校验，拒绝符号链接）。

## 4. iCode 必须保持的契约（改动下列任一项前先查本表）

1. **`initialize` 的 `agentInfo.name === 'iCode'`**——桌面端识别 iCode 的唯一开关。
2. **`session/set_model` 是标准 ACP 方法**，收**裸 profile id**（桌面端会剥掉 `provider/` 前缀）；profile 不存在**必须报错**（桌面端依赖失败信号中止会话创建）。
3. **`<config_dir>/models/*.yaml` 目录发现机制**与 `ModelProfile` 字段名不变（桌面端按 schema 写文件）。
4. **profile `api_key` 为空 → provider env 回退**（`clients.py`）——这是模型凭据与 token 复用同一 env 的前提。
5. **`CHRYS_MODEL_PROFILE` 语义 = 进程启动默认 profile 指针**；不得升级成"每会话选中模型"的通道（那是 `session/set_model` 的职责）。
6. **AIxCoding 模型 = provider `openai` + `api_style: chat_completions` + 自定义 `base_url`**——iCode 必须持续支持 openai 兼容端点。
7. **`promptCapabilities.image` 在 `initialize` 时冻结**——桌面端因此要求启动 profile（`CHRYS_MODEL_PROFILE`）vision 可用；若 iCode 将来把能力协商改成按会话，需同步桌面端。

## 5. V1 联调走查清单

> **离线预验**：`uv run python codingExplan/verify_desktop_model_chain.py`（仓库根目录运行）。它在本机完整模拟桌面端行为——chrys-home 隔离目录 + `prepareChrysModelProfiles` 同构 JSON-as-YAML profile（含安全/哈希两种 profileId）+ `aixcoding-<hash>` agent 档案 + 真实 `chrys acp --agent … --approval manual` 子进程 + `OPENAI_API_KEY` env + `CHRYS_MODEL_PROFILE` + 本地 loopback OpenAI 后端（SSE 流式）——并逐项断言下表标记 🔬 的行为。2026-10-09 运行结果：**13 项必需检查全部 PASS**。
> 标记：🔬 = 离线模拟已验证（真机联调复核即可）；⬜ = 只能真机联调。

**S2 模型主链路**
- [x] 🔬 ACP `initialize` 返回 `agentInfo.name === 'iCode'`（桌面端识别开关，契约 §4.1）；
- [x] 🔬 新会话发消息模型正常回复：`session/new` → `session/set_model`（裸 id）→ `session/prompt`，loopback 后端收到 `Authorization: Bearer <token>`（`OPENAI_API_KEY` env 回退）、`model` = 选中的 modelKey、路径命中 profile `base_url`、`stream: true`；回复文本经 `agent_message_chunk` 通知回到客户端。真机部分（真实登录 token、真实业务 base_url）联调复核；
- [x] 🔬 `CHRYS_MODEL_PROFILE` 语义正确：set_model 之前的首问路由到能力（vision）profile，`promptCapabilities.image === true`（契约 §4.5/§4.7）；
- [x] 🔬 子进程侧 `<chrys-home>/<配置目录>/models/` profile YAML 可被 registry 加载（安全 modelKey 原样 id、不安全 modelKey `aixcoding-<sha256-24>` id 两种形态都命中 `set_model_profile`）；真机抽查实际落盘文件与后端列表一一对应即可；
- [x] 🔬 `session/set_model` 未知 id **必须报错** `Model profile not found: <id>`（桌面端依赖该失败信号中止会话创建，契约 §4.2）；
- [x] 🔬 会话中切换模型 → 引擎按会话 rebuild、新 modelKey 上线；
- [x] 账号模型列表刷新（`refreshModels`）后新模型可用 —— **预期修正（2026-10-09）**：桌面端 `prepareChrysModelProfiles` 每账号 runtime 只物化一次（runtime-composition.ts 注释明示），`refreshModels` 只更新 pi 的 models.json 与内存目录、**不重写 chrys profile 文件也不重建 runtime**；iCode 侧 registry 每进程只扫一次盘（`load_registries` 懒加载一次），离线模拟证实启动后新写入的 profile `set_model` 返回 `Model profile not found`。两端行为自洽：**新模型要等账号 runtime 重建（切账号/重启）后才对 iCode 生效**，联调按此验收，不要按"刷新即可用"验收；
- [ ] 🔬（部分）传图给 vision 会话不被拒：启动 profile 的 vision 能力协商已验证（`promptCapabilities.image === true`）；真实图片经 ACP ImageContentBlock → openai `image_url` 的编码仍需真机联调。

**S1 不受干扰（独立 TUI 回归）**
- [x] 接收点测试切片全绿（2026-10-09，未改任何 `src/chrys` 代码）：`tests/service/profiles/models/` 全套 + `tests/service/llm/test_clients_factory.py` + `tests/app/acp/test_session_manager_{mutations,profiles}.py` + `tests/app/cli/test_acp.py` + `tests/foundation/config/test_runtime_pointer.py` 共 **364 passed, 2 skipped**，另 `tests/app/acp/test_stdio.py` 1 passed——`/model`、`icode models`、profile 加载路径与改造前一致；
- [ ] 真实 `~/.chrys`（`%APPDATA%\chrys`）不受桌面端 chrys-home 隔离目录影响：模拟中子进程全程只写 chrys-home 沙箱（HOME/APPDATA overlay），真机联调时抽查一次真实配置目录即可。

**边缘**
- [x] 🔬 单 profile 目录可建会话（后端不可达时桌面端 fallback 单模型目录的场景，iCode 侧要求只是"profile 存在"）：模拟即单目录 3 profile；桌面端 fallback 逻辑本身联调确认；
- [x] 🔬 新发现（转 §7 风险）：**modelKey 含非 ASCII 字符时 iCode 在引擎 build 时拒绝**（`Model ID contains unsupported character … only printable ASCII is supported`），`set_model` 报错、会话保持原模型。桌面端哈希的是 profile *id*，`model_id` 落的是原始 key——**后端 `myModelList` 的 modelKey 必须 printable ASCII**，否则该模型在 iCode 引擎上不可用。

**二进制产物（桌面端集成形态）**
- [x] 🔬 wheel 打包完整性：`uv build` 产物含 `chrys` + `aixcoding`（14 文件，含 `auth/delegation.py`）+ docs force-include + 入口点 `chrys`/`icode → chrys.app.cli.app:main`；
- [x] 🔬 安装产物行为等价：全新 venv 只装 wheel 基础依赖（PyApp 首跑等同形态，无 extras），对 `chrys.exe` 跑 `verify_desktop_model_chain.py --exe` **13/13 PASS**；
- [x] 🔬 ACP 与登录增量解耦：同一 venv 删除 `aixcoding` 包后复跑仍 13/13——ACP 对话链路零依赖登录模块（打包即使缺 `aixcoding` 也不影响桌面端对话，只影响 TUI `/login`）；
- [ ] 真实 PyApp exe（`scripts/build.ps1`，PyApp 0.29.0 + wheel）由发布流水线产出后用 `--exe` 复跑一次即可收口（本机无 Rust 工具链未现编；PyApp = 装 wheel + 跑入口点，launcher 只做 env/stdio 直通，差异面极小）。**注意桌面端注入的 `resources/icode/chrys.exe` 必须由本分支构建**（登录增量在 TUI 侧；纯模型/token 链路是长期既有能力，旧二进制也兼容）。

**用户 ID（`AIXCODING_USER_EHR`）现状（2026-10-09 核查结论）**
- **iCode 侧**：ACP 模式**当前没有任何消费方**——`aixcoding` 只被 TUI 三个文件导入（`app/tui/app.py`、`screens/main/screen.py`、`commands.py` 的 `/login`/`/logout`），ACP server 路径不导入。变量传进来是被忽略的，**不会破坏任何功能**；桌面端对话流程也不需要它。
- **兼容通道已备**：`aixcoding.auth.get_login_session()` 的 compat 通道（`OPENAI_API_KEY` + `AIXCODING_USER_EHR` → `DelegatedCredential`）在 wheel 安装产物上实测可用（`stored_user_id` 返回 ehr、`stored_token` 返回 token）——未来任何 ACP 侧消费方（如遥测上报）直接调这个 API 即可，无需再写接收代码。
- **桌面侧注意**：`AIXCODING_USER_EHR` 是随 `trustedPiDefaults.environment` → `connection.value.environment` 进入 iCode 子进程的，但桌面 `DesktopAgentConnectionService` 的 **protected-store 凭据路径会丢掉 defaults 环境**（该分支 env 从零构建，只放 provider 凭据变量）——真要消费用户 ID 时桌面侧需先修这条路径（详见[桌面端代码探查.md](桌面端代码探查.md) §6）。

## 6. 未排期增强（明确不在本次范围）

- **S1 复用业务后端模型列表**：独立 TUI 里直接拉 `myModelList` 并物化 profile（登录后 token 可用）。若立项：在 `aixcoding/` 内加 model catalog 客户端 + 物化逻辑（复用 `environments.py` 地址解析），`src/chrys` 仍只做接线；需走方案评审。**当前桌面端方案不要求此项。**
- **`session/set_config_option` 支持**：桌面端对 pi 引擎会先试该方法；iCode 引擎分支明确跳过它，无需实现。

## 7. 风险与注意

| 项 | 说明 |
|---|---|
| **modelKey 字符集**（2026-10-09 新增） | 后端 `myModelList` 的 modelKey 必须 **printable ASCII**：iCode 在引擎 build 时校验 model id 的 HTTP-wire 安全性，非 ASCII 直接拒（`set_model` 报错、会话保留原模型）。桌面端 `chrysModelProfileId` 哈希只保护文件名/profile id，`model_id` 仍是原始 key。若后端可能下发非 ASCII key，需桌面侧对 `model_id` 做净化（如同样落哈希 id） |
| **模型目录的生效时机** | chrys profile 每账号 runtime 物化一次、iCode registry 每进程扫盘一次：`refreshModels` 的新模型要等 runtime 重建才对 iCode 生效（见 §5 修正项），验收与用户预期按此对齐 |
| **用户 ID 桌面侧投递不全** | `AIXCODING_USER_EHR` 随连接 defaults env 进 iCode 子进程，但 protected-store 凭据路径会丢弃 defaults env（见 §5 用户 ID 现状）；iCode ACP 当前无消费方，不构成故障，消费前需桌面侧补投递 |
| 桌面端行号漂移 | 本计划引用的桌面端行号是 2026-10-09 快照，以[桌面端代码探查.md](桌面端代码探查.md)的符号名为准 |
| profile id 哈希形态 | modelKey 不安全时变成 `aixcoding-<sha256-24>`，桌面端两侧同函数生成；iCode 只做精确 id 匹配，无需关心形态 |
| 文件写法 | 桌面端用 `JSON.stringify` 写 `.yaml`（JSON ⊂ YAML，可解析）；iCode 自己写 profile 时仍是 YAML，互不影响 |
| 凭据生命周期 | 子进程 env 不热更新、无 token 刷新——iCode 委托登录设计（RAM-only、拒绝即回落）已覆盖，无需模型侧处理 |
