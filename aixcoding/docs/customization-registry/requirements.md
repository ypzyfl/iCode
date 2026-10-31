# 需求：定制点登记机制改造（customization-registry）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

定制点登记/清单机制（design.md「定制点登记预告」表 → `aixcoding/tools/gen_customizations.py`
扫描合并 → `CUSTOMIZATIONS.md`）存在三个同根问题 + 一项待办耦合：

1. **登记源多源混淆**（ROADMAP 补做义务①，launcher 批次登记）：语义字段（anchor/risk）从
   **所有**已签认 design 的登记表聚合，历史快照与现行登记无区分——实证：C021/C022 被
   `aixcoding/docs/auth/design.md` 与 `aixcoding/docs/tier-migration/design.md` 双源拼接，
   勘误追加不替换，产物中留 `~~删除线~~` 残留（launcher 批次治标：
   tier-migration/design.md:92 事实同步改写）。
2. **C 编号零持久化**（upstream-merge-v0.32.2 runbook 外部评审 B1 路线二）：`C{idx}` 为扫描
   序号（`gen_customizations.py` 按 `(file, line)` 排序后 enumerate），任何定制点增删/文件
   排序变化使后续编号整体漂移——实证：runbook 曾引 C002=`logs/screen.py`，tui 批次在
   `pyproject.toml` 登记 marker 后 C002 漂移为 `pyproject.toml:206`，引用静默失效
   （已兜底：runbook 改「文件路径+符号」主键引用；本批次让编号本身稳定）。
3. **清单结构性膨胀**（责任人 2026-10-31 裁决并入）：登记落点为批次/目录级（tui 批次仅
   1 行落点=`src/chrys/app/aixcoding/tui/` 整目录），marker 为行级（22 处），gen 将登记行
   anchor/risk 全文复制到每个 marker 行（≈15KB 重复）；`reason`/`tests`/
   `removal_condition` 三列「待补」回填后体积将进一步增大。
4. **removal_condition 回填耦合**（独立待办
   `fork 仓外 temp/aixcoding-todos/2026-10-31-removal-condition-backfill.md`）：29 点 /
   6 源 design 登记表回填 + 各 R10 重签，与①②③动同一批文件；待办明确「先 ID 后回填
   （或合并）→ 登记表一次改到位」。责任人 2026-10-31 裁决：**并入本批次**（四合一统筹）。

三个问题的共同根因：**登记粒度（批次/落点级）与定制点粒度（marker 行级）错配**，
`module_matches` 前缀包含匹配把一个登记行的语义摊到该落点下全部 marker。

## 目标与非目标

- 目标：
  - **登记单一现行源**：每个定制点的语义字段有唯一权威登记源，历史批次 design 不再
    重复供源（ROADMAP 补做义务①闭环）；
  - **id 稳定（降级定位）**：id 为登记行沟通标识（非匹配主键，主键=落点+marker 锚），
    分配含退役号高水位（tombstone），增删/排序变化不漂移（责任人 2026-10-31 终裁：留+降级）；
  - **产物退役**：`CUSTOMIZATIONS.md` 衍生文件删除，freshness 铁律退役（责任人 2026-10-31
    依三轮 AI 评审裁决 C+ 方向）；全景视图改 report 命令按需输出；
  - **removal_condition 回填到位**：判据语义进 UPGRADE-RUNBOOK §5 附录 + 逐组取值落
    登记表（双轨），29 点无「待补」残留；
  - **防漂移机检**：回归测试证明删一个 marker 后其余点 id 不变。
- 非目标：
  - 不改 R3 marker 格式规范（`AIxCoding` 无括号口径）与存量 29 处 marker 注释文本
    （「marker 内写 id」列为未来演进候选，本轮不做）；
  - 不动上游源码（预计零上游文件改动，R2 面为零）；
  - 不改 marker 扫描/分类逻辑（`_common.py` R3 识别与豁免后缀机制维持）；
  - 不引入集中台账（E 方向，评审否决——与 R10 design 签认体系冲突）。

## 用户场景

1. **升级现场**（UPGRADE-RUNBOOK 消费者）：按稳定 ID 或「文件+符号」定位定制点，编号
   不因历史批次增删而失效；
2. **批次开发者**（design 作者）：登记表一次登记即含 anchor/risk/removal_condition
   全语义，无需跨 design 处理勘误叠加；
3. **淘汰裁决**（责任人）：升级时按 removal_condition 触发条件逐点做「上游实现 vs 我方
   定制需求」对比分析（DEVELOPMENT.md §8 第 5 步）。

## 验收标准（草案，design 签认后细化）

- [ ] `gen_customizations.py --strict` 对账全绿（29 点存活、孤儿登记清零、豁免清单核对过）；
- [ ] check 零文件写入（测试断言）；错误注入清单全过（未登记/孤儿/未签认/id 重复/
      锚歧义/孪生计数/表头损坏 fail-closed/退出码/豁免双消费一致）；
- [ ] 防漂移回归测试：删除任一 marker，其余点 id 不变；插入新文件改变扫描排序，存量 id 不变；
- [ ] removal_condition 29 点全回填（8 种判据进 runbook §5 附录 + 逐组取值落登记表），无「待补」；
- [ ] 8 个源 design 登记表改造完成，各自 R10 重签；
- [ ] `CUSTOMIZATIONS.md` 删除；人工区信息迁 UPGRADE-RUNBOOK；R3 豁免源迁 `_common.py`
      （`check_r3_markers.py` 切换消费，CI freshness 步骤替换为 strict 对账）；
- [ ] 存量引用面核查：现行文档 `CUSTOMIZATIONS.md` 引用改命令口径，C0xx 引用保持有效，
      历史记录档不改写；
- [ ] 定制四门 + 上游测试套全绿；PR 双 CI 绿。

## 开放问题（均已裁决，2026-10-31）

1. 技术路线 → **C+ 终局**（三轮 AI 评审收敛 + 责任人终裁）：点级登记 + id 降级保留 +
   产物退役 + check/report 双命令 + CI strict 对账；
2. id 形态 → **留 + 降级定位**（主键=落点+marker 锚，id=沟通标识；tombstone 高水位）；
3. 产物表结构 → **文件退役**（report 按需输出全景；升级时点快照附 verification.md）；
4. 登记源单一化判定 → 点级唯一登记行自然消解（C001→agents-md-note、C021/C022→auth、
   C007→diagnostics，tier-migration/ai-gates 登记表清空指向）；
5. 校验语义 → marker 无登记=error；孤儿登记本地 warning / CI strict=error；
   孪生组按 (落点,锚) + 预期计数校验（不依赖行序契约）。
