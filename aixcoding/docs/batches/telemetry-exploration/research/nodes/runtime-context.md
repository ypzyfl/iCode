# N9：运行时上下文与公共字段

> 技术判断：**大方向条件可行，不推翻 session 目录 + 进程内 after_turn。**但这不是全量文件恢复：当前运行时/finalizer、ACP 输入和必要的事件时快照各自承担不同字段。
>
> 决策状态：采用“固定运行时 + 当前轮 live session + ACP 按 session/turn 捕获 + 无依据省略”。Git 轮末快照与事件时精度的选择属于字段语义/实施，不影响 telemetry 主路线能否工作。

## 1. 旧字段并非所有报文完全统一

| 字段 | LLM body | tool-detail/save | ai-code/save | selected Agent 记录 |
|---|---|---|---|---|
| pluginVersion | 必有，产品包版本 | 同左 | 同左 | 同左 |
| channelType | cli/desktop | 同左 | 同左 | 同左 |
| channelName | 永远 `icode` | CLI 为 icode；desktop 为 ideName | 同 tool-detail | 同 tool-detail |
| channelVersion | 可选，desktop ideVersion | 可选；CLI/TUI 有 pluginVersion 特判 | 可选，通常 desktop ideVersion | 同 tool-detail |
| userId | **没有** | 可选，登录优先/旧配置兜底 | 同左 | 同左 |
| projectName | 有 workspace 才带 | 必组包；无 workspace 错回退进程 cwd | 同左 | ACP session.cwd，亦有 cwd 回退 |
| Git 五件套 | 有 workspace 时可选 | 可选 | 可选 | 可选 |
| remoteUrl/branch/gitUserName/gitUserEmail | 无 | 无 | 可选；remoteUrl/branch 与 Git 五件套同源 | 无 |
| agentName | 非 desktop 的实际 agent；desktop 省略 | desktop 为 functionName runner，其他为实际 agent | 同左 | runner，不是选中的 Agent |
| 选中的 Agent | 无独立 selectedAgent 字段 | 无 | 无 | 写入 funcName，funcType=1001 |

旧最终 selected-agent envelope 的准入字段为 `agentMarketSkillId`，上报名称为 `agentName`；`agentMarketSkillId` 本身不上报。此前简写为 agent/version/toolsetId 的描述以最终 `acp_meta.py:61-75` 为准。

旧 tool-detail update 不重新携带公共字段；关联依赖 funcId。mock 最低校验不代表上述实际组包行为。

## 2. 当前字段分类

| 字段组 | 固定/当前运行时 | session/trajectory | 必要补采或降级 |
|---|---|---|---|
| appVersion | `chrys.__version__` | meta 是最近保存版本；runtime.started 有运行时版本 | 当前轮直接用运行时；不用升级后的版本覆盖历史 |
| pluginVersion | 无独立插件模型 | 无 | 可按旧“产品版本”语义显式映射 appVersion；不能不说明就当成另一个插件版本 |
| CLI/ACP surface、品牌 | 启动方式、branding、当前 surface | `last_surface` 只是最后使用面 | 可辅助 channel；不能自动等同完整 channel 三元组 |
| channelType/Name/Version | 无现成统一模型 | 无 | CLI 可在定制层识别；desktop 必须 ACP 输入，缺失时 unknown/省略 |
| userId | 当前 auth `stored_user_id`（EHR） | 不进 session | 当前轮可读；未登录/委派无 EHR/历史用户均省略，不解 token 猜 |
| cwd/working dirs | live workspace、after_turn hook 输入 cwd | meta 保存最近原始路径；turn 只有 workspace 指纹 | 当前轮可得；历史原始 cwd 不用 session-latest 填充 |
| projectName | 可按当前 primary cwd basename 约定派生 | 无独立字段 | 当前轮可派生；多 root/子目录/历史项目身份不能猜 |
| 主 Agent profile | live session 完整 profile | meta、switch history；每轮指纹/exchange profile ID | 当前轮/最近保存可恢复；不能把指纹反解成任意历史 display name |
| desktop envelope、selected Agent | 只存在于 ACP 输入 | 当前不保存 | **只能 ACP 入口按 session/turn 捕获；已丢弃的历史只能省略** |
| Git remote/branch/revision/owner/repo/user | 可读取当前文件系统 | 无事件时记录 | finalizer 只能提供轮末快照；要求事件时精度则更早捕获，否则省略 |

部署环境 `local/dev/prod` 和安装器 channel `prod/test` 不是 telemetry channel 的可靠运行时事实，不能混用。

## 3. 版本、channel 和 userId

### 版本

当前产品版本可由 `__version__` 获得，session meta 和 runtime events 也有 appVersion。旧 pluginVersion 表示产品包版本，因此可在定制契约中显式映射；这不等于当前存在独立插件系统。

### channel

旧版采用 argv 识别 + ACP desktop meta 覆盖。当前没有等价统一模型，但 CLI 启动形态和 surface 可作为定制层输入；desktop 的 ideName/ideVersion 仍需 ACP。

标准 ACP initialize 的 `client_info` 和自定义 `_meta`/kwargs 当前都会被丢弃。N7 需通过真实桌面样本确认所需值究竟位于标准 client_info 还是自定义 envelope；N9 只确定“入口不捕获就无法补回”。

### userId

当前 auth 运行时提供本机登录 EHR；桌面委派只有 token、无 EHR hint 时，`stored_user_id` 可能为空。current config 没有旧版 userId YAML 回退。

因此当前轮可读取 auth，未登录、委派缺 EHR、凭证异常或历史用户无法确认时省略。不得从 token 解码或拿当前登录用户覆盖历史轮次。

## 4. workspace、projectName 与主 Agent

当前轮 after_turn 可直接取得 live workspace、profile 和 cwd；现有 after_turn hook 输入也含 profile/cwd/turn/status。正常路径不需要从旧文件猜当前轮。

session meta 保存原始 primary_cwd/working_dirs、主 Agent profile 和 surface，但它们是**最近一次保存快照**。trajectory 每轮只保存 workspace/profile 指纹，不可逆出原始路径或任意历史 display name。

所以：

- 当前轮：live runtime/finalizer 可提供 workspace 和主 Agent；
- 已保存当前轮：meta 可辅助；
- 历史轮：没有精确值时省略；
- 无 workspace：不得回退进程 cwd 生成 projectName/Git，这是旧 L-D03 缺陷，不复制。

projectName 只是 cwd basename 约定，不是独立项目 ID；多 root、仓库子目录、worktree/submodule 需要按实际业务语义处理。

## 5. Git 的真实边界

Git remote/branch/revision/owner/repo、remoteUrl、gitUserName/gitUserEmail 均没有事件时持久化。当前 TUI Git reader 只提供当前分支显示，不是历史数据源。

after_turn 采集只能表示**轮末当前状态**：

- 工具可能已 commit/checkout/switch；
- remote 或 git config 可能轮中改变；
- 多 root、shell workdir、submodule/worktree 可能不属于 primary cwd 仓库；
- Git user 是当前配置，不等于历史 commit author。

旧版本身也是各报文组装时读取 Git，并有 cwd 级 300 秒缓存，不是严格事件时真值。因此新版不需要虚构“旧版始终精确”。应按业务语义选择：

1. 接受轮末快照：finalizer 采集并明确其含义；
2. 要求 turn 开始事实：在 turn admission/started 前后捕获；
3. 要求每次工具所属仓库：需在工具执行时按实际目标捕获；
4. 未捕获的历史或无法确定：省略，不读当前 `.git` 冒充。

这影响 Git 字段精度，不影响 LLM/工具/ai-code 的主关联和上报能力。

## 6. ACP 是不可替代的输入接缝

当前 0.35.2：

- initialize 丢弃 client_info/kwargs；
- session/new、session/load、session/prompt 丢弃自定义 kwargs；
- ManagedSession 只保存 cwd 和解析后的 profile_name，不保存 desktop envelope/selected Agent。

因此 desktop channel、functionName runner、selected Agent 如果属于必需数据，必须在 ACP 入口按 session/turn 捕获。进入 finalizer 后信息已经不存在，文件分析和上游 Git/workspace 都无法补救。

这是一处已知且可定位的 fork 接缝，不是路线不可行。具体捕获字段和真实桌面样本归 N7。

### 6.1 ACP 也是已确认的输出接缝

**责任人决定（2026-11-17）**：必须保持 0.28.0 的形态，在最终 `PromptResponse._meta` 中主动携带当前 turn 的 requestId；让客户端另行调用 `session/turns` 查询不满足要求。

源码与 Git 历史已核实：

- 0.28.0 在模型响应完成后登记 requestId，并在最终 `PromptResponse` 合并 `agent-studio.dev/telemetry`；可选 `final-model-identity` 还携带桌面归因 span。旧 telemetry envelope 没有 sessionId，不能继续按旧文档误写。
- 上游 b4f354d（v0.30.1）已经提供 `chrys/turn_started`、每个流式 update 的 turnId/turnNumber、最终响应 turn 身份，以及 `session/turns` 中的 requestAttemptId；9cd8031d（v0.31.0）已经提供标准 ACP 流式文本和推理 chunk。当前 0.35.2 已包含两者。
- 上游没有把 requestAttemptId 直接放入最终 PromptResponse，因此仍需要一个定制输出合并点；不需要重新生成 session/turn/request ID，也不需要新增逐模型调用流式通知。
- 当前 `session/prompt` 的 `_TurnExecution` 已直接提供 sessionId/turnId；最终响应已有 `_meta.chrys.turnId`。缺的是当前 turn 的最终成功主模型 A-final 到目标 envelope 的组合。
- after_turn 在正常路径早于 PromptResponse，但其现有 hook 输入没有 turnId；ambient trajectory ID 是 pass ID，retry 时与 ACP logical turnId 不同，不能直接作为 registry key。
- telemetry 的 turn span 与 final-model-identity 的桌面归因 span 是不同语义，不能混填；任何失败/取消路径不得回退前一轮 requestId。

### 6.2 身份准备路线比较与暂行执行方案（2026-11-17）

| 路线 | 数据与时点 | 改动/成本 | 当前评价 |
|---|---|---|---|
| **A. 响应时 live-history 选择** | `_run_turn()` 完成后、释放 prompt_lock 前，直接读 live 主 history 和 TurnRecord，按精确 logical turnId 选择 A-final | **1 个上游文件 `app/acp/server.py` + 1 个定制 helper**；O(全 history 消息数) 元数据扫描，无磁盘 I/O、无需正文序列化；无 registry 生命周期 | **暂行采用**：责任人暂按 AI 建议执行，遇问题再讨论 |
| B. after_turn registry | finalizer 从当前 run 消息切片选择，ACP 按 key 取 | 至少 finalizer+server+helper；为 retry/trajectory disabled 显式传 logical turnId 可能还需 runner/turn_state；有清理/消费状态 | O(当前 pass) 更省扫描，但接缝和状态更多 |
| C. 模型完成时 live registry | kernel `_response_ready` 在 continuation terminal、validation 通过后登记 | kernel/loop+trajectory+server+helper；需 actor/root-main、pass→logical 和 registry 生命周期 | 真正的模型完成时捕获，但最终响应前没有消费者，当前非必要 |
| D. after_turn 调 session/turns | 扫描 trajectory/events.jsonl 后投影全 session turns | 每轮 O(全日志)，长会话累计近平方；另需 root-main、partial 和 A-final selector | 不作为轻量路线 |

A 的暂行选择规则：用上游 `turn_slices` 和 TurnRecord.opening_item_id 精确对齐，不按 session 末尾猜测；在匹配 logical turnId 的消息范围内找最后一个非 marker 的主 assistant 响应，只读取它自己的 `_chrys_request_attempt_id`。最后响应缺 A 时跳过，不能回退同 turn 更早 A；同 logical turn 的 retry pass 没有新成功响应时，可保留该 turn 既有最后成功响应，但绝不跨 logical turn。主 history 天然排除 side/sub-agent。

A 必须在 per-session `prompt_lock` 仍持有时完成，结果作为局部值交给 `_TurnExecution`；锁外读 live history 会与下一 prompt 竞争。save=False 仍读内存，不读旧磁盘；连续/并发 session 不共享可变 registry。若 opener 因历史压缩或旧数据无法精确对齐，按缺失跳过并记录原因。O(全 history) 是暂行方案的简单性/性能权衡；实际执行发现性能或归属问题即带回分析讨论，不擅自升级为 B 或加缓存。

**ID 原值裁决（2026-11-18）**：所有 ID 保持原值 32hex、不转 UUID。内部 header/session/trajectory/message 和 live-history selector 与全部出站（独立 LLM/tool-detail/ai-code/ACP）使用同一原值，客户端无转换层；后台原模型记录直接原值保存，其他入口原值保存。`request_tracking.py` 和 `foundation/trajectory/ids.py` 均不需要修改，N7 的上游接缝仍只有 `app/acp/server.py`。同一成功 M 的相关外部记录同文本，缺失/非法 raw 不另造 ID；tool/ai-code 关联 A1，ACP 通常关联 A2。配套：Agent Studio `ModelRequestIdSchema`（原 `z.string().uuid()`）放宽接受 32hex，纳入验收；后台 32hex 格式接受与新旧混存见 BR-5。

方向实验 `aixcoding/tests/telemetry/test_acp_response_identity.py` 已覆盖精确 turn、多响应、缺 A、marker、injected retry、opener 缺失、无文件和 metadata sibling，最终 7 passed；定制 telemetry 目录合计 9 passed。A 的真实 ACP server 接线、锁内并发、save=False 端到端、真实压缩、性能和桌面 Zod 闭环仍未实现/验证；暂行方案不替代具体实施 design/R2。

## 7. 大方向结论与实施项

继续当前路线，字段来源分为：

```text
固定运行时：版本、启动形态、当前 auth
当前轮 live/finalizer：workspace、主 Agent、轮末 project/Git
ACP 入口：desktop channel、functionName、selected Agent
文件：当前保存身份、历史关联及可恢复事实
无依据：unknown/省略
```

不需要恢复旧进程级“最后写入者赢”的 channel/functionName，也不需要恢复 cwd 回退或 session-latest。Q2 已确认保持桌面 0.28 能力，因此 ACP 输入捕获、selected Agent 1001 和 desktop 上下文属于实施范围，不再暂缓；最小 DTO 也不能替代 0.28 全字段 parity。1001 的输入须形成不可变 turn 上下文供 after_turn 消费：save-only、无 T，按 `(sessionId,logicalTurnId)` 去重一条，关联当前 turn 首个成功主模型 A-final，无成功或缺输入时跳过。

以下留 N7 或实施，不阻塞当前探索：

- 真实桌面 initialize/new/load/prompt 原始样本；
- ACP metadata 的 per-session/per-turn 输入隔离和真实桌面 envelope 样本；最终输出契约已确认，不再列为未知项；
- Git 轮末 vs turn/tool 事件时语义选择及必要样本；
- 多 root、委派无 EHR、历史轮次等字段降级矩阵。

## 8. 证据与行为锚定

旧最终源码：

- `aixcoding/context.py`：channel、functionName、userId、pluginVersion；
- `telemetry/reporters/__init__.py:65-108`：公共字段和 cwd 回退；
- `telemetry/llm_telemetry.py:240-284`：LLM 实际字段；
- `telemetry/acp_meta.py:47-75`：desktop/selected Agent envelope；
- `aixcoding/git_info.py`：当前采集与 300 秒缓存。

当前源码：

- `service/state/store.py`、`service/trajectory/session.py`：appVersion/runtime；
- `service/session/persistence.py`、`orchestration/engine/state/session_writer.py`：workspace/profile 快照；
- `orchestration/engine/run/turn_hooks.py:75-99`：当前 after_turn 输入；
- `kernel/aixcoding/auth/session.py`：当前用户；
- `app/acp/server.py`、`session_manager.py`：ACP 输入丢弃边界。

2026-11-14 实际执行：

```cmd
cd /d "D:\Tech\Github\huawei\iCode\fork\iCode-fork" && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run pytest tests/service/session/test_persistence.py tests/orchestration/engine/state/test_session_writer.py tests/orchestration/engine/test_trajectory_recorder.py tests/app/acp/test_server_capabilities.py tests/app/acp/test_session_manager.py aixcoding/tests/auth/test_auth_session.py aixcoding/tests/auth/test_auth_delegation.py -n0
```

结果：收集 205 项，`205 passed in 14.24s`，退出 0。锚定 workspace/profile 持久化、trajectory 指纹、ACP 当前行为和 auth 用户语义；不证明 desktop envelope 捕获或事件时 Git 已实现。
