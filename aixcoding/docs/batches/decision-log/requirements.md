# 需求：轻量决策记录（MADR——决策记录双档制）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

治理现状三层（ADR / 六文档管线 / 微改动豁免）存在**决策落点断层**，三个具体缺口：

1. **中间地带沉没**：够不上 ADR checklist 但有决策含量的小决策，只存在于 PR 描述（GitHub 资产，不进 git 仓库）或人脑中；
2. **R8 有义务无载体**："决定不做的事同样必须记录"是既有规范义务，但无统一落点，散落或丢失；
3. **ADR ③ 无泄压阀**：checklist ③（后来者会问为什么）门槛宽——严格执行则 ADR 泛滥，软性收窄则 ③ 形同虚设；灰色地带没有合法留痕出口，压力以"选择性忽略规则"的形式泄漏。

方案经三轮外部 AI 评审 + 责任人三条要求（负担红线 / 界限机制 / AI 建议人裁决）收敛，讨论全程留于 2026-11-12 会话，关键裁决以本 design 签认为准。

## 目标与非目标

- 目标：
  - 引入轻量决策记录载体 `aixcoding/docs/madr/`（日期命名、4–5 行模板、append-only），与 ADR 构成双档制；
  - 双档界限三层机制：事前 AI 档位建议 + 人裁决 / 写时哨兵 / 事后低频审计，防双向漂移（ADR 弱化与 ADR 泛化）；
  - 档位裁定流程（分场景二元，AI 建议人裁决）：豁免区微改动决策——落条目/不落（豁免资格已含未命中 ADR 判定，三条件②）；纯讨论/否决决策（R8，无改动载体）——出 ADR/落条目（对照 checklist）；
  - 补齐 R8 落点；
  - 并入 C 方案：同类微改动演进脉络按 rule of three 固化进既有文档。
- 非目标：不建共享索引（ADR-0024 方向）；不进 `check_docs.py` 闭环、不新增任何工具门禁；不修改 ADR 判定 checklist 本身；不溯及存量（既有 PR/文档不回填）；不重复管辖已由完整管线覆盖的决策（design.md / ADR 内的决策不落 madr/）。

## 用户场景

1. **微改动豁免路径出现小决策**（如工具实现方式取舍）→ AI 起草条目随 PR 提交（PR 描述附一行落/不落建议）→ **commit 授权前呈报附条目全文请人表态，无表态追问、不得默认**——零新增停等点（表态与 git 写授权同回合）；
2. **讨论/评审中否决某方案（R8）** → 档位二选一：命中 checklist 出 ADR / 否则落"决定不做"条目，详证指向 PR 描述等 git 可查对象；
3. **AI 接任务判断决策含量** → 按场景走二元轴（豁免区=落/不落；纯讨论=ADR/条目），判定单/PR 描述附建议 + 对照 checklist 一句理由，人裁决；
4. **半年后有人问"当初为什么 X"** → madr/ 按文件名（日期+主题）检索，或已被升格为正式 ADR。

## 验收标准

- [ ] `aixcoding/docs/madr/` 就位，含 README（目录说明：档位规则/模板/字段语义；首条真实条目留给首个真实场景——本批决策自身走完整管线由 ADR 承载，不落 madr/）；
- [ ] ADR-decision-log--dual-tier-decision-records 留决策档（`standards/adr/decision-log--dual-tier-decision-records.md`，语义 ID 体系；双档制、命名裁决、模板、详证强约束、三层界限、审计、升格与修正口径）；
- [ ] `DIRECTORY.md` 修订：§2 落点判定树新增 madr/ 行、§1 总蓝图补 madr/（madr/ 为 docs/ 下第三一级目录，须先修判定树）；`aixcoding/README.md` 结构一图与速查表同步（docs/ 子目录注释补 madr/ + MADR 检索入口行）；
- [ ] `SELF-REVIEW-HOWTO.md` / `PEER-REVIEW-HOWTO.md` R8 摘要同步（R 系列变更同步义务）；
- [ ] `DEVELOPMENT.md`：R8 落点句按场景分流（管线内 design 承载 / 豁免区可选落 madr / 纯讨论落 madr 或 ADR）；§6 微改动豁免段补"决策要点可选落 madr/"与 rule of three 两句；§6 平铺句"除 `standards/` 与根文件外"例外枚举补 `madr/`；
- [ ] `UPGRADE-RUNBOOK.md` §1 升级前清单补 madr/ 低频审计步骤（机制 5 审计的触发接入）；
- [ ] `PEER-REVIEW-HOWTO.md` §二 评审 AI 模板新增 madr/ 条目核对项；
- [ ] 负担红线成立（人工核对）：无新增独立停等点、无新增签认文档、无新增 CI 门禁；
- [ ] `uv run python aixcoding/tools/check_docs.py`（含 `--closure`）通过——madr/ 不在闭环范围；
- [ ] `uv run python aixcoding/tools/gen_customizations.py --strict` 通过（纯文档零上游，无 freshness 义务）。

## 开放问题

- 三个 design 阶段待定点（审计节律挂点、纯对话决策外化载体、条目非决策性修正口径）由 design 给出建议方案，随签认一并裁定。
