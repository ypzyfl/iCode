# 自评审记录：护栏规则包调优（guard-rule-tuning）

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-26
- 确认意见：（可选）

- 评审 AI：GLM-5.3（account:bigmodel-individual-coding-plan/GLM-5.3），ZCode CLI 独立评审 agent（隔离上下文）
- 开发 AI：GLM-5.3（account:bigmodel-individual-coding-plan/GLM-5.3），ZCode CLI 开发会话

> 记录档：签认一次，后续追加评审记录不触发重签。
> **评审独立性如实声明**：本次评审与开发为同一模型、同一工具的不同隔离会话（规范
> SELF-REVIEW-HOWTO Q1 建议不同工具或不同模型）——评审会话不共享开发上下文，全部
> 验证命令由其独立重跑、测试有效性经变异实验独立验证并抓出 blocker F1，事实上发挥了
> 独立评审作用；但与规范的字面建议存在偏差，是否采信由责任人终裁。

## 2026-11-26 评审结论：通过（1 轮：评审 + F1 修复 + 增量复审通过）

- 轮次：1 轮（评审 → F1 修复 → 同一评审 AI 增量复审通过）
- 方案与实现评估（技术评审摘要）：
  - 大方向表态：方向对——诊断「处置模型缺档」与修复形状「三档处置 + 黑名单 + 重开」
    一一对应；ask 档消费引擎既有能力、上游零改动，是把「保护归零」修回「分档保护」
    的最小冲突面路径。
  - 关键决策逐条意见：①删 7 条规则——同意，工具层 T-SHELL-03-2..5 对注入仍兜底，
    但 T-SHELL-04+T-PY-02 同删留下 `exec(marshal.loads(...))` 无覆盖角（见未修项）；
    ②confirm→ask——同意，fail-closed 三路兜底（declined/timed_out/unavailable→blocked）
    经引擎代码逐行核验成立，B16 headless 端到端实测补齐；③网络白名单→黑名单——同意，
    威胁模型重定义（拦攻击目标而非一切内网）由 ADR 承载且责任人签认；④出厂重新开启
    ——同意，已部署机器由安装器整条覆盖收敛，`guardctl off` 是唯一现场退出；
    ⑤后缀锚定 `_host_matches`——正确，变异验证证明负例测试钉死锚定。
  - T1-T4 要点：T1 结构与问题匹配、无漏做；T2 值依据全部有出处（黑名单两条业务给定、
    ask_message 用例给定、阈值沿用旧值）；T3 实现深读未发现逻辑错误，测试更新为「如实
    锁定新行为」（两个被点名测试经变异验证为行为锚定，非 vacuous）；T4 性能可忽略、
    演进脆弱点（引擎 ask 契约）已入 design 假设 1。
  - 临时项与例外：无临时方案；hooks.yaml 旧「temporary shutdown」注释整段清除，
    新注释如实描述分档与拉回语义。
- blocker 处置：
  - F1（四处文档承诺「拒绝后提示『操作不合规…』」，实际为引擎组合拒绝文案）→
    **已修复**：rule-pack README / MANUAL_TESTS / 本批 requirements 三处改为实际文案
    （含 B16 实测输出）；修复经验证：评审 AI 增量复审逐字对照 `_ask_refusal`、
    `handle_decision`、`reject_tool_call` 判定**通过**；OPERATIONS 6.2 不改的判断经复核成立
    （其示例命中 block 档 IN-01，文案承诺真实）。
- 未修项（责任人已拍板不修，2026-11-26）：
  - F3（design/ADR 称 ask 为「公开契约」，authoring spec 实未枚举——实为引擎行为，
    上游测试钉住）| 不修理由：责任人勾选处置时未选该文档包；design 假设 1 的失效表现
    覆盖已足以指导升级核对。
  - F4（坏 CIDR 黑名单条目静默丢弃，全引擎唯一无日志的配置降级路径）| 不修理由：同上
    拍板；行为符合 D7「忽略不误拦」承诺。
  - F5（裸 `*`/`?` 通配分支无测试）| 不修理由：同上拍板；出厂配置未使用该形态。
  - F6（OPERATIONS 旧「拦教务系统」行未更新 + requirements 验收复选框未勾）| 不修理由：
    同上拍板。
  - F7（T-MCP-04 引 confirm 检测器但自身 block 的组合语义未入文档）| 不修理由：同上拍板。
  - 增量复审排版 nit（README 185/195 未加「block 命中时」限定词）| 不修理由：同节 15 行内
    已有显式区分，完整阅读不产生错误结论；字符级句尾句号已顺手补（属 F1 准确性范围）。
  - marshal/exec 残留备案（`python -c "exec(marshal.loads(...))"` 无规则覆盖）| 未拍板，
    随 F3 文档包同处置；ADR 仍为草案，责任人可在签认前决定是否补记。
- 待责任人裁决项（评审期提出、截至本文落笔未闭环，签认前请一并拍板）：
  - ~~F2（回环+危险端口直接拦截不弹框——包内隐含行为，无规格拍板）~~ → **已裁决
    （2026-11-26，责任人经改动包 (4) 与《测试用例(4)》拍板）＝回环完全豁免**（含危险端口，
    豁免范围扩展到 `localhost` / `*.localhost`）；ADR 决策 3 与理由节已按裁决改写（非 R2
    内容变更，不触发重签，git 留痕）。
  - F8（未跟踪目录 `aixcoding/docs/pr/` 两份无关文档归属）：提交按显式路径 stage，
    不会带上；归属请责任人确认。

## 2026-11-26 第 2 轮评审（F2 适配改动包 (4) 增量复审）：通过

- 范围：仅增量——`_guard_core.py`（`_is_loopback_target`＋`_detect_url` 顺序）、自检 +1→107、
  部署验证 +N12/N13→69、README/MANUAL_TESTS/OPERATIONS 的 F2 文档增量＋F1 修复重放、
  `rules.json` 保留仓库修正版、批次文档 F2 口径同步。
- 复审结论：**通过**。四项核验成立——a) 新顺序正确（大小写/尾点/IPv6/伪 TLD/黑名单优先级
  边界实测通过；`localhost` 加入 `blocked_hosts` 仍放行系「豁免优先」的裁决直接推论，非 bug，
  `*.localhost` 需病态 DNS 才指向非回环，静态名字黑名单固有限制）；b) F1 重放与 F2 增量
  零冲突（三方 diff 确认仓库 vs 包 (4) 唯一差异＝F1 重放段）；c) rules.json 取舍正确
  （包 (4) 版会回退首轮两处 note 修正）；d) 新测试双变异验证有效（MUT-A 锚定 IP 分支、
  MUT-B 锚定名字分支，四输入分别钉死）。
- 本轮 blocker 处置：无 blocker。
- 本轮 finding 处置：
  - F2-R1（T-NET-01 note「危险端口…始终生效」与 F2 裁决矛盾，`guardctl show` 可见）
    → **已修**：一行改为「对非回环目标始终生效（回环完全豁免，含 localhost / *.localhost）」；
    修复后自检重跑 `Ran 107 tests / OK (skipped=1)`，本机安装副本 `guardctl show T-NET-01`
    核验为新文案；design note 修正段同步。
  - F2-R2（README/OPERATIONS 未明说「回环目标优先于黑名单，无法用黑名单拦截」）
    → 未修：评审自评「可并入未修项」；现留痕由本记录与 ADR 理由节承载，支持工单口径
    需要时再补一句。
  - F2-R3（MANUAL_TESTS 计数 106→111 与可见 +2 行增量不复算）→ 未修：为改动包作者侧
    文档口径，建议向包作者确认计数来源；不影响自动化验证（自检 107 与部署验证 69 为
    实际执行口径）。
- 验证声明：自检/部署验证由评审 AI 独立重跑一致（107 / 69 0 失败）；ty/ruff 全量
  采信开发侧三平台声明（本轮增量经评审逐行审读）。

## 2026-11-27 第 3 轮：PR #155 评审（责任人转发评审人意见 8 条）处置——全部实质项已修

> 记录档追加（签认一次，追加不重签）。评审条目甄别口径＝责任人指示：纯规则/流程类条目无视，
> 实质缺陷修复。8 条中 7 条实质项＋1 条（suggestion-5）计次修正为实质、§7 结构部分属
> 仓库规则但随 PR 描述重写一并满足。

| # | 评审条目 | 处置 |
|---|---|---|
| 候选 blocker-1 | 「block 优先于 ask」合成决策无测试（变异 `if blocking and not asking:` 后 107/69 全绿，混合输入如 `sudo echo \`whoami\`` 从 block 变 ask） | **修**：`verify_guard_deployed.py` +P13（提示词层：IN-01 block＋IN-05 confirm → block）、+S29（工具层：T-SHELL-01 confirm＋T-SHELL-03-2 block → block），69→71 条，构造上钉死优先级 |
| 候选 blocker-2 | 坏 CIDR 黑名单条目静默失效（无日志，削弱保护不可追溯） | **修**（首轮 F4 由责任人经本评审改判为修）：`_networks` 对被丢弃条目 `_log` 一行 stderr（保持 D7「忽略不误拦」承诺，不采 GuardError 抛错方案——单条手误会 fail-closed 全拦，与 D7 冲突） |
| suggestion-3 | 「另 12 条原 confirm 规则显式钉为 block」未在 design/ADR 补记 | **修**：design 方案概述＋变更清单 rules.json 行；ADR 决策 2（列明 12 条 ID） |
| suggestion-4 | 重新开启的两项代价（launcher 失败即全拦、冷启动约 0.29 s/次）未记 | **修**：design 风险节＋ADR 理由节，含接受结论（评审实测数值，注明来源） |
| suggestion-5 | PR 描述补 §7 结构；「67→69」应为「64→69」 | **修**（计数：AST 核实 main 基线 64 条确认）；PR 描述按 §7 五段重写、计数 64→71，待责任人授权后更新 PR body |
| suggestion-6 | 回环优先于黑名单的两处断言是平凡的（黑名单未含回环条目） | **修**：自检 `test_tnet01_blocked_hosts_is_the_switch` 黑名单加入 `localhost`/`127.0.0.1`、`test_in06_blocked_networks_is_the_switch` 加入 `127.0.0.0/8` 后再断言放行（非平凡豁免） |
| nit-7 | SWITCHES §5.3 ip_cidr 行仍写需要 dictionary 参数 | **修**：改为「读 settings.network.blocked_networks，回环豁免；无词典参数」 |
| nit-8 | design 判定④/ADR 的 ask 载体应指向 docs/en/reference/hooks.md（authoring.md 未枚举） | **修**：design 假设 1＋判定④、ADR 决策 2 均指向该文件 |

修复后验证（2026-11-27）：自检 `Ran 107 tests / OK (skipped=1)`；pytest `27 passed, 1 skipped`；
临时目录部署验证 `共 71 条，失败 0 条：[]`；ruff＋format（guard 路径）通过；ty win32/linux/darwin
三平台通过；Smart Test PASSED（tests 1684＋architecture 323）。改动仍全部在定制目录，上游接触面 0。
