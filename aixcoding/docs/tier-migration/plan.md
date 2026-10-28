# 任务清单：ADR-0011 存量定制包按 tier 回迁 kernel 档

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

双 AI 评审收敛（2026-10-28：1 轮评审 + 增量复审通过 + S1/S2 尾项修复，blocker 清零），
待责任人签认 self-review.md → commit 请示 → PR。

## 待办

- [x] 责任人签认 design.md（R2 批准）
- [x] ① git mv 两包 → `src/chrys/kernel/aixcoding/{auth,diagnostics}/`；新建
      `kernel/aixcoding/__init__.py`；删旧 `src/chrys/aixcoding/__init__.py`
- [x] ② 包内互引绝对→相对（import 语句）+ docstring/`:mod:` 写新绝对前缀
- [x] ③ 包外前缀替换：上游 3 文件（wire_client / test_layering / screen，见 design R2 表）+
      定制测试 14 文件
- [x] ④ 工具分类器 4 py 5 处改通配 + devtools/design.md:28 + 工具测试夹具 4 文件
- [x] ⑤ 活文档联动：AGENTS.md:8、diagnostics/requirements.md:16；CUSTOMIZATIONS.md 重新生成
- [x] ⑥ 四项验证（architecture 1237 绿 / aixcoding tests 263 绿 / ty 三平台 / wheel 16 条目）
      + 全库旧前缀 grep 清零核对（详见 verification.md）
- [ ] ⑥′ 实施中发现的新联动落档：trajectory_wait_manifest.json 刷新（+33 行，已做）；
      登记表格式修正（tier-migration design bullet→表格）与 4 文档重签（见挂起）
- [ ] ⑦ self-review.md 双 AI 评审 + PR（交付报告按 §7 固定格式）

## 评审轮次记录

- **第 1 轮（2026-10-28）**：评审 AI = Deepseek-V4-Pro（CodeBuddy 环境）。F1 blocker
  （manifest 未列 R2 表）→ 已修复：R2 表补录 +2 行（manifest +33；`src/chrys/aixcoding/__init__.py`
  删除 −8 为实跑 check_r2_diff 发现的评审外补充——分类器通配化后旧路径 diff 形态按上游）；
  F3 suggestion（第 7 条措辞）→ 已修：补澄清句区分"叙述快照"vs"登记表活数据"；F4 nit
  （联动清单回写）→ 已修：第 8 条；F5 nit（细则二豁免明确化）→ 已修。R3 门禁连带三处：
  AGENTS.md:8 行内标记（standards 归属）、wire_client 标记行前缀形态、
  `gen_customizations.py` 新增 `MARKER_EXEMPTIONS` 常量并渲染豁免表（清单重生成 7 条目）。
  复验：check_r2_diff OK（approved_pool=8）、check_r3_markers OK（exempt=1）、
  受影响测试 60 passed、check_docs OK。**F2（重签真实性）待责任人向评审方确认一句**。
  待复审增量。
- **复审（2026-10-28）**：通过——F1-F5 全部处置到位、无新 blocker；2 个非 blocker 尾项
  S1（wire_client 标记行残留 "The"）/S2（AGENTS.md 标记拆断 "is governed"）按评审建议
  修复，复验门禁全绿（R2 OK / R3 OK / gen 7 条目 / tools 53 passed）。评审收敛。
- **peer review 第 2 轮（2026-10-28，PR #64 head `27118f4`；评审 AI = CodeBuddy
  GLM-5.3-FlashX，同工具同模型族不满足双 AI 口径、如实记录，评审档在 `.codebuddy/pr/`
  工作区不入库）**：4 候选处置——C1（kernel 门面导入闭包，唯一行为级）：开发 AI 独立复跑
  实验证实（`chrys.kernel.agent` 连带加载、206ms/354 模块），**接受 + 入档**（无技术
  绕过路径），design 假设 3 勘误 + 基线重审类推勘误 + 登记口径修正（tier-migration 与
  auth 两 design）+ 风险节补时序窗口；C2（R2 行数口径）：R2 表 wire_client 2→+4/−3、
  净效果句 7→8 行勘误；C3（263 复现性）：verification 补环境差异注记（peer review 机
  端口用例失败 base 同败=存量）；C4（R2 双口径）：裁决确认"落位即 custom"为 ADR-0011
  既定语义，design R2 节补注记。ADR-0011 快照不动（档位判据不受影响，导入副作用属未预见
  代价维度，与"语义张力"条同类）。CI 修复：Step7 ruff format（`_common.py` 单行化，
  commit `27118f4`）。

## 挂起与备忘

- **待责任人重签 4 个已签认文档**（正文在签认后有过联动修订，R10 触发重签）：
  ① `tier-migration/design.md`（登记预告 bullet→表格 + adr/0011 入白名单）；
  ② `diagnostics/design.md`（登记表 5 行落点新路径——语义字段单源必须活，否则生成器
  ERROR"标记无登记行"）；③ `auth/design.md`（登记表落点行同因跟改）；
  ④ `devtools/design.md`（分类器定义 :28 与标记示例 :30，ADR-0011"分类器随实现走"口径）。
- 实施事故 2 起已修复并记录于 verification.md（脚本包名索引 bug；测试文件误相对化）。
- 工作区 `aixcoding/docs/tui/design.md`（untracked）属 tui 批次，不入本 PR——提交时按文件
  明确 add，禁 `git add -A`；
- R8 留档项见 design.md 联动清单第 7 条，不在本批次改；
- 验证环境注意（历史经验）：本地全量测试需 `set PYTHONPATH=`（脱离 genie shim）、
  `set PYTHONUTF8=1`、大写盘符 `D:\` 启动。
- `wire_client.py` 编辑带 LF/CRLF 混入 warning（git autocrlf 归一化，无实质影响）。
