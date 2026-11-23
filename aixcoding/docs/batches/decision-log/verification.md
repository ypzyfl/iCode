# 验证：轻量决策记录（MADR——决策记录双档制）

> R7 落盘形态：命令 + 输出摘要，追加不删旧。

## 2026-11-12 实施后首轮验证（Windows 11，D:\Tech\Github\huawei\iCode\fork\iCode-fork）

**命令 1**：`uv run python aixcoding/tools/check_docs.py`

```
check_docs: scanned 25 ADR(s), 42 design(s), 40 self-review(s) under aixcoding/docs
check_docs: OK
```

签认与 ADR identity 校验通过：25 ADR（含新建 `decision-log--dual-tier-decision-records.md`，文件名/H1 匹配语义 ID 正则、批次目录存在）；design 42（含本批已签认）。

**命令 2**：`uv run python aixcoding/tools/gen_customizations.py --strict`

```
gen_customizations: check OK — 114 registration row(s) / 159 marker(s) across 18 design(s), 7 retired id(s), 0 warning(s)
```

纯文档批次零 marker 触碰，freshness 无义务，strict 通过。

**命令 3**：`uv run python aixcoding/tools/check_docs.py --closure` —— FAILED with 27 error(s)，逐类核验均为**管线中间态**（非缺陷）：

| 类别 | 数量 | 消解条件 |
|---|---|---|
| ADR 草态 forbidden | 1 | 责任人签认 ADR-decision-log--dual-tier-decision-records（本人编辑头部） |
| ADR 引用 targets a draft（连锁） | 24 | 同上——签认后同时清零 |
| 批次缺件 verification.md | 1 | 本文件落盘后清零 |
| 批次缺件 self-review.md | 1 | 双 AI 评审完成后落盘清零 |

**结构一致性人工核对**（test-plan 覆盖矩阵 #1–#8 逐项）：

| 联动 | 核对结果 |
|---|---|
| madr/ 首条条目 | ✅ 模板五字段齐全（决定人=周彬/背景/决定/否决项/详证指向本批 design.md，PR 号后补口径已注） |
| ADR 正文 | ✅ 机制 1–10 + 与标准 MADR 差异对照齐备，快照注记指向 DEVELOPMENT/DIRECTORY |
| DEVELOPMENT.md ×3 | ✅ R8 落点句、§6 豁免段两句（可选落 madr + rule of three）、§6 平铺句例外枚举补 madr/ |
| PEER-REVIEW-HOWTO | ✅ §二 模板第 5 项（madr/ 条目核对：档位恰当 + 详证支撑，一条） |
| SELF-REVIEW-HOWTO | ✅ R8 摘要行补"决定不做落 madr/"半句 |
| DIRECTORY.md ×2 | ✅ §2 判定树新增"是轻量决策记录？"行（置于"是文档？"前）、§1 总蓝图 docs/ 行补 madr/ |
| README ×2 | ✅ 结构一图 docs/ 行补 madr/、速查表"查为什么这样定"行补 madr/ 检索入口 |
| 负担红线 | ✅ 联动均为文档修改，无新增停等点/签认文档/CI 门禁/工具校验 |

**实施中修正 1 处**：closure 首跑报 design.md 引用编号 0025 无全局池目标（`ADR reference ... has no global-pool target`）——评审记录 B1 处置段的历史字样被 ADR 引用校验误命中，改为不带前缀的"原案编号 0025"描述后清零（非决策性修正）。

## 待办（阻塞 PR）

1. ADR 签认（责任人本人）→ 消解 25 错；
2. 双 AI 自审（换评审 AI）→ self-review.md 落盘签认 → 消解 1 错 → closure 全绿。

## 2026-11-12 自查轮（ADR 签认后，双 AI 评审前）

**ADR 签认确认**：`decision-log--dual-tier-decision-records.md` 头部已由责任人编辑（已确认 / 2026-11-12）——closure 由 27 错降至 2 错（draft 禁令与 24 处 targets-a-draft 连锁全部清零）。

**修正 1 处**：verification 首轮记录中引用历史报错原文含编号 0025 前缀字样，被 ADR 引用校验误命中（与 design 评审记录同款问题），改写为不带前缀描述后清零。同款问题两处均已消——教训：记录"报错原文"时引用类 token 会被校验扫描，应转述而非照抄。

**diff 逐文件核对**（`git status --short` + `git --no-pager diff`）：工作区 = 5 修改（README / DEVELOPMENT / DIRECTORY / PEER-REVIEW-HOWTO / SELF-REVIEW-HOWTO）+ 3 新增（batches/decision-log/、madr/、ADR）——与 design 联动清单逐项对应，**无越权文件、无意外产物、无 marker 触碰**（纯文档批次）。

**DEVELOPMENT.md 三处直接读取复核**（62 R8 落点句 / 160 平铺句例外枚举 / 175 §6 豁免段两句）：全部就位。备注：search_content 对该文件返回 0 命中为**工具假阴性**（文件大、修改实际存在，read_file 复核为准）——后续评审请勿单凭搜索工具下"未修改"结论。

**旧口径/旧名残留检查**（全库 `merge 即裁决|decisions/`）：仅 design.md 评审记录 2 处命中，均为修正过程的历史留痕（评审记录须保留当时表述），非残留缺陷。

**closure 终态**：`FAILED with 1 error(s)`——仅剩 `required batch file missing: self-review.md`，为双 AI 评审后的预期落盘项。

## 2026-11-12 修正轮（责任人指出示例条目档位矛盾）

首轮核对表中"madr/ 首条条目 ✅"一项**作废**：责任人指出"首条条目 = 本决策自身"违反本批机制 3——本决策命中 ADR 判定①③、走完整管线、已由 ADR 承载，按档位规则不该落 madr/（双档重复记录 + 错误示范）。处置：删除 `madr/2026-11-12-决策记录双档制.md`，改为 `madr/README.md`（目录说明：档位规则/命名模板/字段语义，非条目）；design 联动 #5、验证方式节、requirements 验收标准、test-plan 矩阵 #1、plan 任务 5 同步改写；S3（详证时序）随之失效。教训（design 六次修正）：方案评审未用自己定义的档位规则检验自己的示例。

## 2026-11-12 修正轮 2（责任人指出详证强约束时序不可落地）

**问题**：原详证口径"指向 PR/commit/仓库文档"在豁免区起草时刻全部不可用——PR 未创建、commit 未发生（条目自身在 commit 内，指向即自指）、豁免区无文档。**修正**：默认且合法详证载体 = **本 PR**（拍板现场 = 本 PR 的 commit 授权前呈报；决策要点写入本 PR 描述即外化完成）；决策现场在更早处才指向外部。改写：`madr/README.md` 详证行与字段语义、design 机制 2（时序与默认口径）。防滥登效力不变；ADR 正文无需变更（"PR 描述"枚举本已涵盖本 PR）。

## 2026-11-12 修正轮 3（责任人指出"号合并后补"不落地）

七次修正中"合并后补注 PR 号"不落地：PR 建立后回改文件为冗余编号多一次修改动作；"本 PR"即自足（条目与 PR 同体，`git log --follow`/blame 可查归属）。修正：详证"本 PR"即终态、**无回补动作**（README 详证行与字段语义、design 机制 2 同步）。

追加（同轮）：design 载体形态节模板行与 ADR 决策节模板行同步补"本 PR"（此前修正轮 2/3 只改了机制 2 与 README，模板代码块滞后）——ADR 模板行修改经责任人裁定按"非决策性一致性修正"原地改（决策结论不变：机制 2 载体枚举本已涵盖"本 PR"）。

## 2026-11-12 修正轮 4（双 AI 自审：CodeBuddy / Kimi-K3.1-Pro，4B+2S+2N 全采纳）

- **B1**：DEVELOPMENT R8 落点句绝对化与 §6"可选"/机制 3"管线内不涉足"三方冲突 → 改场景分流（管线 design 承载/豁免区可选/纯讨论 madr 或 ADR）；SELF-REVIEW 摘要、design 机制 7、联动 #2、ADR 机制 7 同步。
- **B2**：机制 5 审计无操作入口触发 → UPGRADE-RUNBOOK §1 新增第 5 步 madr/ 审计（呈报一行：滞留升格/堆积/可疑档位/频率；处置留档升级批次文档）；联动补 #10；requirements/test-plan 补项。
- **B3**：peer review 核对可被跳过 + 不守护 append-only → PEER-REVIEW §三 新增核心动作 ④（100% 过目，**新增或修改**均触发；修改查非决策性修正）；头部微改动说明、FAQ Q1/Q4、§二 第 5 项触发条件同步。
- **B4**：madr/README 违反本批判定树（非 `YYYY-MM-DD-主题.md` 形态）→ DIRECTORY 判定行明示"或目录级 `README.md` 使用说明"；ADR 载体形态同步声明。
- **S5**：madr/README 补③边界正反例（尾部 N 行 vs mock stdlib-only）。**S6**："编号档"措辞改"正式 ADR 档（语义 ID）"（design 方案概述/载体形态、ADR 决策节）。
- **Nit1**：plan 任务 9 删条目表态残留。**Nit2**：PEER-REVIEW"三项检查/交叉"对齐五项。

## 2026-11-12 修正轮 5（责任人指出决定人字段填写来源未定义）

补两级来源 + 锁定：①对话明确拍板；②AI 建议经呈报获认可；**未表态的纯 AI 选择不得填"决定人=责任人"**（先呈报转化）；commit 授权前呈报表态为最终锁定。落点：madr/README 决定人字段语义（design 评审记录十次修正留痕）。

追加（同轮）：**身份解析**（名字从哪来）三级——①任务文档头部"责任人"字段（git 可查最可靠，R10 唯一责任人制）；②纯讨论取对话拍板者表明身份；③不确定禁止猜测、呈报时询问（design 评审记录十一次修正留痕）。

## 2026-11-12 修正轮 6（增量复审处置：B3 残留 + B5 证据落盘 + 1S2N；评审 AI 同轮独立复跑确认）

**修改清单**：DEVELOPMENT §6 豁免段"仅做"句补 madr diff 时 ④ 必做指向（B3 残留）；README 填写来源②精确化（对该决策内容的明确认可，普通 git 写授权不构成认可）；design 联动 #8 与 test-plan #6 同步分流口径、test-plan #11 补总纲检查点；PEER-REVIEW 13/69 行"三个核心动作/三动作"对齐四项。

**修复后真实验证**（B5：R7 证据落盘，2026-11-12 执行）：

```
$ uv run python aixcoding/tools/check_docs.py
check_docs: scanned 25 ADR(s), 42 design(s), 41 self-review(s) under aixcoding/docs
check_docs: OK

$ uv run python aixcoding/tools/gen_customizations.py --strict
gen_customizations: check OK — 114 registration row(s) / 159 marker(s) across 18 design(s), 7 retired id(s), 0 warning(s)

$ uv run python aixcoding/tools/check_docs.py --closure
ERROR aixcoding/docs/batches/decision-log/self-review.md: draft decision/review document is forbidden by closure
check_docs: FAILED with 1 error(s)
```

closure 现状如实记录：**仅剩 self-review.md 草案态一项**（本文件体系内的最后签认件）；责任人签认 self-review 后须**再跑一次 closure 并把最终输出追加到本节**，不以预写"全绿"替代（评审 B5 要求）。

## 2026-11-12 最终轮（第 3 轮复审通过 + self-review 签认后门禁全绿）

第 3 轮复审（评审 AI：CodeBuddy / Kimi-K3.1-Pro，只审上轮增量）：**通过**——B3/B5 闭环确认、次要问题（旧口径/计数残留/Suggestion/身份解析一致性）全部确认修复，无新 blocker。收尾 nit 采纳：PEER-REVIEW §一③ "两个 100%"→"各项 100% 硬标准"（100% 项现为三个：上游逐行、blocker 裁决、madr 核对）。

self-review 签认后三重门禁**全绿**（真实输出）：

```
$ uv run python aixcoding/tools/check_docs.py
check_docs: scanned 25 ADR(s), 42 design(s), 41 self-review(s) under aixcoding/docs
check_docs: OK

$ uv run python aixcoding/tools/gen_customizations.py --strict
gen_customizations: check OK — 114 registration row(s) / 159 marker(s) across 18 design(s), 7 retired id(s), 0 warning(s)

$ uv run python aixcoding/tools/check_docs.py --closure
check_docs: scanned 25 ADR(s), 42 design(s), 41 self-review(s) under aixcoding/docs
check_docs: OK
```
