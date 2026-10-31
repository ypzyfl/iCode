# 设计：追上游 v0.32.2（upstream-merge-v0.32.2）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：无特别意见

## 方案概述

按 `standards/UPGRADE-RUNBOOK.md` 将 `main_aixcoding_cli` 从上游 0.31.0 升至 **v0.32.2**（c54b60cf）。

```
origin/main_iCode（镜像，918cb599，纯上游）
        │  ← 本次只取其中的 v0.32.2 tag（c54b60cf，!98）
        ▼
特性分支 chore/merge_upstream_v0.32.2（自 main_aixcoding_cli @6e057986 拉出）
        │  git merge v0.32.2 → 解冲突 → 三层核对 → 全量验证
        ▼
PR → main_aixcoding_cli（双 CI 绿后责任人合并）
```

与 runbook §0 标准动作的说明：本次目标是 **release tag v0.32.2**（责任人 2026-10-31
裁决），镜像头领先的 23 个未发版提交（`v0.32.2..918cb599`）留待下次升级。runbook §1 第 1 步允许
"release tag / main 头 commit"两种目标，无流程违反。

### 干跑实测（merge-tree，2026-10-31，未动工作区）

349 个变更文件中冲突仅 **2 处**，均在 i18n 域（ADR-0010 管辖）：

| 冲突文件 | 形态 | 解法 |
|---|---|---|
| `tests/foundation/i18n/test_catalog_oracle.py:26`（C028 在册） | 同一计数行：定制 2335→2405（+4 借壳 key），上游 2335→2499 | 合后重算：2499+4=**2503**（以 merge 后 pot 实测为准，借壳 key 若有丢失则按实际数并回查原因），保留 `# AIxCoding tui:` marker |
| `src/chrys/foundation/i18n/_catalogs/zh-Hans/LC_MESSAGES/chrys.mo` | 二进制编译产物（豁免表在册） | 不手工解，`i18n.py compile` 重新生成 |

其余 347 文件 auto-merge 成功（含 pyproject.toml、AGENTS.md、locales po/pot、TUI screens）。
runbook §2 预警的 C001（AGENTS.md）/ C002（logs/screen.py）高发区本次均 auto-merge 通过——
**auto-merge ≠ 语义正确**，结构层核对（下文）不可省略。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| A. merge v0.32.2 tag（本设计） | 稳定 release；干跑实测冲突仅 2 处 i18n 文件 | 镜像头 23 提交未跟进（留下次） | 最小（实测） | **选定**（责任人裁决） |
| B. merge origin/main_iCode 头（918cb599） | 一次到位、与镜像完全同步 | 含 23 个未发版提交，改动面与风险更大、非稳定版 | 更大（349 文件之上再叠加） | 否决 |
| C. rebase 93 个定制提交到 v0.32.2 | 历史线性 | 改写已发布历史 + 需 force push（纪律禁止） | — | 否决 |
| D. 重建法（0.28→0.31 旧路线） | 无冲突 | 冲突面实测极小，完全不需要；且丢 PR 历史可追溯性 | — | 否决 |

## 上游改动清单（R2；升级批次特例）

**本批次我方对上游文件的新增改动预计为零**：

- merge 引入的上游自身变化不算"我们的改动"——runbook §4 条款：R2/R3 以**新 merge-base** 起算，
  diff 区间从新分叉点（v0.32.2）重新起算，只反映定制侧；
- 冲突解决 = 在册定制点 C028 的数值适配（2405→2503）+ marker 保留，无新定制点；
- `pyproject.toml` version 行：随 merge 自动 0.31.0→0.32.2（上游自身变更）——**本次保留上游三段，
  不启用四段**（责任人 2026-10-31 终裁）；四段启用与日构建递增机制连同 update_check 三段假设的
  行为分析，已登记独立待办 `temp/aixcoding-todos/2026-10-31-four-segment-version.md`；
- 若 merge 后适配过程中发现**需要**新的上游文件改动：停下，按 R2 增补报批后再动（铁律）。

## 对上游隐式行为的假设

| 假设 | 我方依赖方式 | 失效表现与对策 |
|---|---|---|
| 4 个借壳 key（C028）在 0.32.2 的 pot 抽取中仍全部生成 | oracle 计数 = 上游 2499 + 4 = 2503 | oracle 测试红 → 重走 i18n 管线（extract→update→compile）后复测；仍缺则查上游 msg 定义处变更 |
| 上游 0.32.2 未重构 tui 基建符号（`BaseDialog`/`DialogButtonRow`/`localized_binding`/`SlashCommandDef`/`AppHeader`/`MainScreen.on_mount` 等，C002/C005–C020 anchor） | 定制 tui 挂点编译期依赖 | ty check / 定制测试红 → 按 runbook §3 逐 anchor 核对后跟随适配（触及上游文件则回 R2 报批） |
| `chrys.kernel/__init__` 包级导出（`get_login_session` 等，C021/C022 anchor）签名未变 | auth 接线 lazy import | 定制 auth 测试红 → 同上 |
| 上游 ci.yml job 集未变（实测 v0.31.0..v0.32.2 仅 ±2 行） | aixcoding-upstream-ci.yml workflow_call 复用 | 上游 CI 桥接红 → 核对该 4 行 diff 并跟改桥接文件（属 fork 自有文件，非 R2） |
| 上游 `.python-version`/依赖锁定与本地 Python 3.14.8 兼容 | 本地验证环境 | uv sync 失败 → 按团队环境记录对齐解释器后重试 |

## 定制点登记预告

**无新增定制点**（本批次目标是既有 C001–C029 在新基线上存活，不产生新的 marker/上游接线）。

## 既有定制点存活核对矩阵（runbook §3 结构层展开）

| 核对组 | 定制点 | 核对内容 |
|---|---|---|
| 文档入口 | C001 | AGENTS.md AIxCoding 段 marker 行文本不变、段完整 |
| 日志面板 | C002/C007 | `logs/screen.py` MODULE_ORDER 行含 `"aixcoding"` 项 |
| 启动接线 | C004 | `app.py` `main()` 起始 startup 接线行在 |
| TUI 挂点 | C005–C020, C023–C026, C029 | badge/dialog/commands/screen/app_header 各 marker 行在；anchor 符号存在且签名未变 |
| LLM 认证 | C021/C022 | `wire_client.py` token 头注入两行在 |
| i18n | C027/C028 + 豁免表 4 项 | oracle ids / 计数 2503 / pot/po/mo 重生成后 marker 与条目齐全 |
| 机检兜底 | — | `pytest aixcoding/tests/diagnostics/test_panel_anchor.py -n0 -q` 绿 |

## 升级决策交付物（runbook §5，2026-10-31 责任人指示）

以下清单随升级产出，**最终决策全部交责任人裁决**，记录于本目录 `verification.md` 与 PR 描述：

1. **冲突点全清单 + 逐点处理意见**（含 auto-merge 通过但语义核对有疑义的点）——
   已预判 2 处（oracle 计数 2503 / mo 重编），merge 后按实际补全；
2. **定制化改变清单**：需新增 / 建议删除（淘汰候选，附对比分析）/ 需适配的既有定制点；
3. **淘汰检查逐点结论**：即使上游 0.32.2 出现名似功能（如账号/登录类 UI），一律先出
   上游实现 vs 我方定制需求的对比分析，待裁决——**不自行删除任何定制**。

## 风险与最坏情况

- **最大风险：auto-merge 语义静默错**（如 MODULE_ORDER 合并丢项、接线行被上游重构吞并）——
  对策 = 上文核对矩阵逐项 + 行为锚定测试 + 全量测试（上游 + 定制四门）三层兜底。
- i18n 计数偏差：借壳 key 丢失 → oracle 红，重走 i18n 管线；仍红则升级暂停呈报。
- 回滚：merge 在特性分支上进行，任何时候可丢弃分支从 `main_aixcoding_cli` 重来；
  PR 合并后发现问题的回滚 = revert 该 merge PR（merge commit 单点可逆）。

## ADR 判定

按 §6 checklist 逐项：① 被认真考虑但否决的备选——B/C/D 均为 runbook/纪律既定路径的常规排除，
非本批次新决策；② 撤销代价高——否（revert merge 单点可逆）；③ 约束未来工作模式——否；
④ 依赖上游非公开接口——无新增（anchor 均已在册）。**结论：不出 ADR。**

（"目标取 release tag 还是镜像头"是 runbook §1.1 已枚举的操作参数选择，由责任人逐次裁决即可，
不构成需留档的架构决策；本节连同上方备选对比表即留痕。）
