# 设计：护栏规则包调优——confirm 分档、网络黑名单与重新开启（guard-rule-tuning）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-26
- 确认意见：（可选；审阅中形成的判断、附加条件或保留）

## 方案概述

判定＝**改动包整包合入（17 文件）＋ rules.json 两处过期 note 修正**。R1＝零上游接触：
改动全部落在既有定制目录（`guard/pack/`、`aixcoding/tests/guard/`、批次 rule-pack 文档），
不改上游文件、不加接线点、无新增文件——无可外置逻辑，无 R2 项，无新依赖（R11 无涉）。

来源与审计：桌面 `iCode-guard-hooks-changes.zip`（《iCode 安全护栏测试用例》第 6 节所指
改动包，展开于 `D:\Ai\iCode-guard-hooks-changes(2)`；**F2 裁决后适配最新版
`iCode-guard-hooks-changes(4)` 与配套测试用例(4)**）。外来包按不可信数据逐文件 diff
过目：包内代码、规则、107 条自检、69 项部署验证与五份文档口径自洽；`fnmatch` 导入已在；
包外 `test_guard_core.py` / `test_packaging.py` / `guard_install.py` 无被删规则或旧配置键
残留引用；CI guard job（`aixcoding-tests.yml`）无硬编码规则计数。

一次误报治理，三件事联动：

```
误报来源                     处置                                        规则
──────────────────────────────────────────────────────────────────────────────────
几乎必中日常开发（7 条）     删除；自检「保持删除」回归用例钉住           IN-03/04/07、T-SHELL-03-1/04、
                                                                          T-PY-02、T-NET-02
中高风险（7 条）             confirm + confirm_disposition: ask           IN-05/06/08、T-SHELL-01、
                               Hook 写 action: ask → 引擎弹确认卡        T-FS-02/03、T-OUT-01
                               ├ TUI / 声明能力的 ACP：用户裁决
                               └ headless / 拒绝 / 超时：block 兜底（fail-closed）
真危险（其余 25 条）         block 原样
网络                         白名单（回环外全拦）→ 黑名单               出厂 *.bocsys.cn +
                               回环最先完全豁免（含 localhost）；          22.122.49.168/32
                               危险端口对非回环恒拦；后缀锚定防误伤
出厂开关                     enabled: false（PR #129 临时停用）→ true
```

规则规模 40 → 33（开 32 · 关 1，`T-OUT-02` 高熵长串出厂仍关）。其中 **12 条原 confirm
规则显式钉为 block**（`IN-01`/`IN-02`、`T-SHELL-02-1/-4/-5/-6`、`T-SHELL-03-2`~`-5`、
`T-PS-03`、`T-OUT-02`），不再随 `confirm_disposition` 变化（PR 评审补记）。现场效应：已部署机器
下次启动即收敛到新包（安装器整条覆盖受管条目与规则文件）——从「护栏停用」变为
「分档护栏开启」。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| A 现场逐条 `guardctl disable` 误报规则，不改包 | 零发版 | 治标：每台机器手工、口径漂移；`disable` 表达不了「确认」这一档；PR #129 全停正是因为这些规则人人必中 | 0（但保护仍归零） | 否 |
| **B 整包合入＋note 修正（选定）** | 误报根治＋保护恢复＋风险分档一次到位；ask 用引擎既有能力，零上游改动 | 安全语义翻转需责任人裁决（本 design＋ADR）；17 文件数百行 diff | 全在定制目录，上游 0 | **是** |
| C 只删 7 条规则，confirm 仍按 block 落地 | 改动更小 | 中高风险仍打断（`rm -rf /tmp/xx` 清理、读 `.ssh` 排查部署），误报减半不除根；改动包已完成的 ask 实现与测试白费 | 约减 1/3 | 否 |
| D 保持出厂停用，仅合入规则修正 | 风险最低 | 护栏名存实亡——「有规则包不生效」正是 PR #129 要解决的问题，保护归零是临时态 | 0（但目标落空） | 否 |

## 定制目录变更清单（17 文件，全部为既有文件修改，无新增文件）

**规则包 `src/chrys/kernel/aixcoding/guard/pack/`（8）**

| 文件 | 改什么 |
|---|---|
| `rules.json` | 40→33 条（删 7）；7 条 confirm＋12 条原 confirm 显式钉为 block；`confirm_disposition` block→ask；新增 `ask_message`；network 键白名单→黑名单（出厂 `*.bocsys.cn`、`22.122.49.168/32`，删 `allowed_networks`/`allowed_hosts`/`default_disposition`）；`T-OUT-02` 出厂仍关；**两处 note 修正**（见下） |
| `_guard_core.py` | confirm 三态映射（ask）；`DEFAULT_ASK_MESSAGE`/`format_ask_message`；ask 决策写出（写不出→非零退出走 `on_error: block`）；网络黑名单引擎（`_host_matches` 后缀锚定/通配/子串、`_blocked_hosts`/`_blocked_networks`、`_is_loopback_target` 回环最先完全豁免——127/8、`::1`、`localhost`、`*.localhost`，危险端口也不例外（**F2 责任人裁决**，适配包 (4)）、危险端口对非回环恒拦）；`_detect_ip_cidr` 改读黑名单；settings 校验随键名更新 |
| `_prompt_guard.py` / `_tool_guard.py` | 模块 docstring 随规则集与 ask 语义更新（行为无变化） |
| `hooks.yaml` | 两个受管条目 `enabled: false`→`true`；注释与 description 随新口径 |
| `guardctl.py` / `guardctl.cmd` / `guardctl.sh` | 用法示例 `IN-07`→`IN-05`（IN-07 已删），行为无变化 |

**测试 `aixcoding/tests/guard/`（4）**

| 文件 | 改什么 |
|---|---|
| `guard_pack_selftest.py` | 100→107 条：被删 7 条的正例改「保持删除」回归；confirm→ask 映射与文案用例；网络黑名单组（后缀锚定、通配、网段开关、回环豁免、**回环+危险端口放行（F2）**、未列入放行）；Hook 写 `ask` 的两个入口子进程用例 |
| `test_anchors.py` | 出厂锚 `enabled` 断言 false→true |
| `test_guard_install.py` | 安装后出厂 `enabled: true`＋手改关被模板拉回（方向翻转）；状态示例 `IN-07`→`IN-05` |
| `verify_guard_deployed.py` | 期望从 bool 改三态（block/ask/allow）；71 条口径（含 N12/N13 回环+危险端口放行、P13/S29 混合命中合成 block——PR 评审补强，钉死「block 优先于 ask」）；S04/S09 显式写回出厂写范围，避免 confirm 被 `T-SHELL-05` 的 block 盖住 |

**文档 `aixcoding/docs/batches/guard-hooks/rule-pack/`（5）**：`README.md`、`OPERATIONS.md`、
`PORTING.md`、`SWITCHES.md`、`MANUAL_TESTS.md` 随新口径（分档表、黑名单与回环完全豁免
说明、107 条自检 / 111 条手工用例）。

**note 修正（包内过期文案，合入时一并修正）**：`rules.json` 中 `IN-06` 与 `T-NET-01`
的 note 写「出厂为空（预留）」，与同文件出厂值（含 bocsys 条目）、`_guard_core.py` docstring、
部署验证 N09/N10（期望 block）、README 的口径矛盾——改为与出厂值一致；F2 裁决后
`T-NET-01` note 的「危险端口…始终生效」同批修正为「对非回环目标始终生效（回环完全豁免）」
（第 2 轮复审 F2-R1）。

## 对上游隐式行为的假设（以下游行为均为已核验事实，非猜测）

1. **引擎 `action: ask` 语义**（本批次 confirm 档的依赖核心）→
   `service/hooks/events.py:161` `GATED_EVENTS = {BEFORE_TOOL_CALL, USER_PROMPT_SUBMIT}`——
   恰为护栏两个事件；`service/hooks/manager.py:495-526` `_confirm()`：approved→放行，
   declined / timed_out / unavailable（含 headless `cannot_ask`、`frontend_unavailable`）→
   `decision.blocked = True`（**fail-closed 兜底成立**）→ 失效表现：上游若移除 ask 支持或
   改兜底语义，confirm 规则在引擎侧被忽略（`ignoring ask` warning）或行为漂移——
   升级时按 UPGRADE-RUNBOOK 核对 hooks 规范（`docs/en/reference/hooks.md`，含确认框
   语义；`service/hooks/docs/authoring.md` 未枚举 ask）与 `_confirm`。
2. **安装器整条覆盖收敛** → `guard_install.py` 按同 id 整条替换受管条目与规则文件
   → 已部署机器首次启动后从「停用＋40 条白名单」收敛到「开启＋33 条黑名单」→
   失效表现：老机器在下次启动前维持旧态；`test_guard_install.py` 已锚定拉回行为。
3. **`guard_state.json` 不含 network 键**（仅 `enabled`/`rules{}`/`write_scope`）→
   network 键名替换无状态迁移问题，旧键随规则文件覆盖消失 → 失效表现：无（已核实
   状态文件 schema 与 `guardctl` 读写面）。
4. **fail-closed 既有假设沿用**（`batches/guard-hooks` 假设不变）：hook 崩溃/超时 →
   `on_error: block`；决策文件写不出 → 非零退出；规则非法 → `GuardError` → `_fail_closed()`。

## 定制点登记预告

不适用——零上游接触、无 marker 改动、无新增文件；既有登记点（`bootstrap_runtime()`
接线、C141 lint 配置、C142 行尾声明）本批次不触碰。

## 风险与最坏情况

- **安全语义翻转（有意裁决，ADR 承载）**：网络从「白名单外即拦」到「黑名单外放行」——
  未列入黑名单的内网地址（RFC1918 等）不再有任何提示。收严路径：改 pack 的
  `rules.json` 加黑名单条目并发版（现场改已安装副本会被下次启动覆盖）。
- **现场效应**：已部署机器升级重启后护栏从「全停」变为「分档开启」，中高风险操作开始
  弹确认框——是本批次目标，但属可见变化，PR 描述需显著标注。
- **confirm 打断流**：`rm -rf /tmp/testdir` 这类清理也要确认一次；拒绝/无人确认＝拦
  （fail-closed），不会静默放行。
- **重新开启的运行代价（已接受，PR 评审补记）**：① launcher 现找解释器失败 → fail-closed
  全拦（可观测、可恢复，`hook list` 可查）；② 每次调用冷启动 hook 子进程，评审本机实测
  约 0.29 s/次——对比 PR #129 全停（保护归零换零延迟），接受该开销。
- **已删规则被静默加回**：自检「保持删除」回归用例＋verify 用例双锚。
- **回滚**：单 commit revert 即回到「出厂停用＋40 条＋白名单」；现场应急关闭用
  `guardctl off`，无需回滚代码。
- **最坏情况**：合入引入 hook 崩溃 → `on_error: block` → 每句被拦（fail-closed 方向，
  不静默放行），`aixcoding-cli hook list` 与自检可观测、可恢复。

## ADR 判定

- ① 有被认真考虑但否决的备选方案 → **是**（上表 A / C / D）。
- ② 撤销代价高 → 否——全部在定制包内；`rules.json` 为随包数据（每次启动覆盖安装），
  不构成对外契约；旧键消失由覆盖安装收敛，无状态迁移。
- ③ 约束未来工作模式，后来者会问「为什么」 → **是**——出厂重新开启＋网络改黑名单＋
  删除 7 条规则，后来者必然问「为什么默认放行内网」「为什么这 7 条没了」。
- ④ 依赖上游非公开接口或行为 → 否——ask 为上游公开契约（`docs/en/reference/hooks.md`），
  且已核验。

结论：①③ 成立 → 决策记录为
`standards/adr/guard-rule-tuning--tiering-and-network-blacklist.md`（草案随本 design 一并呈报）。
