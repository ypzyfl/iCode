# 自评审记录：追上游 v0.35.2（upstream-merge-v0.35.2）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-11
- 确认意见：无特别意见
- 开发 AI：CodeBuddy（BM:GLM-5.3）
- 评审 AI：外部文档评审 AI（责任人提供，2026-11-11，标识未披露；B1/B2/B3 + 建议 7 项）
  + CodeBuddy code-explorer 子代理（实施只读独立复核 + 增量复审）

> 记录档：签认一次，后续追加评审记录不触发重签。评审历程与裁决记录详见 verification.md 第六、九节。

## 一、评审历程

| 轮次 | 发现 | 处置 |
|---|---|---|
| 外部文档评审（责任人提供，2026-11-11） | **blocker 级事实错误 1**：requirements SHA 39 位（B1）；流程状态矛盾（B2）；C079–C081 anchor 描述漂移（B3）；建议 7 项（分支头表述、行数口径、worksteal 影响面、runbook 收尾、closure 序列、淘汰载体、rg-cache 观察） | B1 订正 40 位 SHA；B2 选择统一修订后重签；B3 按责任人裁决 (a) 本批留痕不改源登记行；建议 7 项全部并入四件套；design 重签闭环 |
| 实施只读独立复核（code-explorer 子代理，2026-11-11） | **blocker 0**；suggestion ×2：R2/R3 add 后复跑状态矛盾、anchor/risk 重评未落；nit ×3：plan 勾选滞后、report 快照仅摘要、check_docs/fork-full 证据口径易误读 | 全部处置：plan 拆出 add 后终态复跑待办；verification 新增第八节 17 组 anchor/risk 重评；完整 report 存档 `customizations-snapshot-2026-11-11.md`（SHA-256 76F204…D845）；plan 勾选同步；check_docs 不含 closure 与 fork-full 无机器留存计数均显式披露 |
| 增量复审（同一 code-explorer 子代理，2026-11-11，只审增量） | 3/3 PASS；R2/R3 状态、anchor/risk、快照存档、plan 状态、证据口径全部收敛 | **blocker 清零，可进入责任人签认** |

## 二、实施期自审发现（自身问题清单）

1. **design/plan 状态一度不同步**：design 已签认而 plan 仍写“待签认”（外部评审 B2）——
   根因是责任人签认后未同步活文档；已按“统一修订 → 重签 → plan 同步”闭环，
   并把签认后正文修订必须重签列为停等点。
2. **worksteal 影响面初判过窄**：初稿只注意到命令行 `-m` 覆盖，漏掉 `verify.py` /
   aixcoding-tests.yml 不带 `-n0` 时会继承 `-n 8 --dist=worksteal`——已补 design 假设、
   test-plan 必跑项与 plan 待办，并完成首跑 629/51/0。
3. **fork-full 后台执行无机器留存计数**：工具侧选择后台导致汇总行未进会话记录，
   result 临时文件被脚本自清理——以责任人 console 确认、进程结束、脚本源码核实
   （regular worksteal + architecture 串行）作为联合证据，并在 verification 第六节
   如实披露证据边界，不虚构计数。
4. **报告快照 initially 只存摘要**：独立复核指出 runbook §6.1 要求完整 report——
   已落 `customizations-snapshot-2026-11-11.md` 并记录 SHA-256，verification 改为
   存档引用 + 摘要双口径。

## 三、关键实现复核结论

- 唯一 merge 冲突解与 design 精确一致：`_ERROR = _seq("state=error:app=AIxCoding")`，
  marker 迁移到常量；同锚 marker 3 处（65/150/231），后两处保留；全文无 `iCode`
  断言与冲突标记残留；目标测试 8 passed。
- 无幻觉 API：冲突文件新增/引用符号均在同目录定义；无静默吞错、无 vacuous test、
  无过度工程（独立复核结论）。
- R2：85 个上游变更全落 93 文件审批池；R3：85 / 82 / 3 OK（工作树口径，add 后复跑）。
- 无新增第三方依赖、无新增豁免、无新登记/退役；strict 109/150/7 = 0/0。
- 手册解耦三处（runbook / user-manual plan / verification）口径一致；捆绑机制键
  三方零改动，wheel 67 手册文件探测通过。

## 四、未修项（次要问题，责任人拍板不修）

- R2 输出中 `branding-and-command` / `upstream-merge-v0.35.1` 历史 R2 表头
  “文件 / 同上” warn ×11 | 工具宽容忽略且为存量噪音，本批次未新增 | 不顺手重构历史
  已签文档；终态复跑仍预期同 warn。
- fork-full 无机器留存精确 passed 计数 | 后台执行与临时报告自清理机制所致 | 已如实
  记录证据边界；定制套件独立计数 629/51/0，architecture 归属 fork-full 且责任人
  确认全过。

## 五、结论

外部文档评审 + 实施独立复核 + 增量复审三轮收敛，blocker 0；升级验证矩阵全绿
（merge 冲突解、i18n 三轮幂等、worksteal 首跑、R2/R3 工作树口径、ruff/format/ty、
fork-full、wheel、headless/TUI 冒烟）。可进入责任人 self-review 签认与 git add 授权
流程；R2/R3 add 后终态复跑与 closure 绿为后续既定序列。

## 六、2026-11-11 收尾独立评审（签认后追加，不触发重签）

- **评审 AI**：CodeBuddy（Deepseek-V4-Pro），与开发 AI CodeBuddy（BM:GLM-5.3）
  同工具不同模型，满足第二 AI 要求；评审报告由责任人提供。
- **实测范围**：strict / closure / R2 / R3 / R11 / pyproject / 冲突解逐行 / 配套文档口径。
- **结论**：**blocker 0**；冲突解正确、四门机检全绿、无新增依赖、无越权上游改动。
- **nit ×3 与处置**：
  1. verification R2 `changed=558` 与终态实测 `changed=561` 时点漂移——已注明
     558 = 六件套落盘前工作树时点，561 = 批次文档齐套后终态；upstream_changed=85 不变；
  2. plan 中 self-review 签认与 closure 复跑两项勾选滞后——已按事实勾选；
  3. pot/po 显示 MM 但 `git diff --numstat` 为空（Windows autocrlf 行尾/状态噪音）——
     已留痕，`git add` 后确认无纯行尾内容 diff。

> 本节为签认后追加评审记录；按 R10 记录档规则不触发重签。
