# 任务清单：0.35.2 手册内容同步（user-manual-v0.35.2）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**已完成（事后补录，2026-11-11）**：实施与验证当日完成，六件套按实际终态回写。
design.md 待责任人签认（签认字段 AI 不代填）。当前分支：`fork/user-manual`（长期分支，
承接 user-manual 批次裁决）。双 AI 评审：**已收敛（2 轮）**——第 1 轮
（Claude Code / GLM-5.3-flash）1 blocker + 1 suggestion + 3 nit，F1 按责任人拍板"扩围"
处置；第 2 轮复审增量通过、无 blocker，N1-N4 已修复，结论已回填 self-review.md。
待责任人签认 design.md + self-review.md，提交通知后按显式路径提交。

## 待办

- [x] 上一版本检查：三方文本定位（基线 `20261109\0.35版本` ✓ / theirs `20261109\0.35更新后` ✓ / ours 待生成）
- [x] 官方 0.35.2 获取：release 资产无手册 md → `git fetch` 上游 tag v0.35.2，
      `git diff v0.35.2 -- docs` 判定官方改动范围（4 文件 12 行；release notes 三重证据定方向）
- [x] 生成 0.35.2 官方汇编（章级点替换，4 章）→ `Desktop\20261111\0.35.2版本\`
- [x] 三方合并定稿（6 处段落替换套口径 + 版本行 + 占位）→ `Desktop\20261111\0.35.2更新后\`
- [x] 手册自检（品牌 0 / 结构 0 / 内锚 237 失效 0 / PASS）
- [x] PDF 重出 + `add_bookmarks.py` 书签 50 条自校验 + pypdf 抽验（注解/CHANNEL/新内容命中）
- [x] manual 同步：zh+en 10 文件 14 处（`.tmp_sync_manual.py`，每处 count==1）
- [x] docs/ 镜像追平（责任人 2026-11-11 裁决，R2 表登记）：官方 8 文件 12 行应用至 docs/，
      `git diff v0.35.2 -- docs` 归零；SKILL §八.8 长期口径改写（manual 批次同步应用官方 docs diff）
- [x] 六项审计（基准自动切换到 0.35.2 定稿）全绿 + check_links 全量 PASS + check_docs OK
      + gen_customizations --strict OK
- [x] 手册契约测试 26 passed（foundation/invoker/workflows/providers）
- [x] wheel 重建 + 重装测试 venv + 捆绑 64=64 MD5 + 0.35.2 新内容抽查
- [x] 桌面交付：md/PDF/官方汇编/桌面 wheel 同步
- [x] 六件套 + INDEX 登记（本文档体系）
- [x] 双 AI 评审第一轮（Claude Code / GLM-5.3-flash；1 blocker + 1 suggestion + 3 nit）
- [x] **F1 扩围处置（评审后）**：六件套如实登记 en 追平 22 整文件 + 混入 hunk + zh CHANNEL
      处（requirements/design/plan/verification 补录；F2 清单补正，F3/F4 修正，F5 登记不修）
- [ ] 复审增量（同一评审 AI 只审补录增量）→ self-review.md 回填
- [ ] design.md / self-review.md 责任人签认
- [ ] 提交/推送：待责任人逐条授权（git 写操作逐条授权铁律）；提交限显式路径，
      `aixcoding-launch.py` 等根目录杂物显式排除

## 责任人裁决记录（2026-11-11）

| # | 事项 | 裁决 | 落地 |
|---|---|---|---|
| 1 | docs/ 镜像追平 | **手册批次同步应用官方 docs diff**（纯官方原文、不加标记），取代"仅随代码升级批次更新"口径 | docs 8 文件已应用，`git diff v0.35.2 -- docs` 归零；SKILL §八.8 已改写 |
| 2 | 评审 F1（en 追平未登记，blocker） | **扩围**：六件套如实重写、全部改动随本批次提交（否决拆批与"按现状提交+补录"） | 本文档体系已补录（见待办第 F1 项） |
| 3 | 评审 F3（icode-run.md 链接文件名）/ F5（aixcoding-launch.py 根目录未跟踪） | **登记不修** | F3 见 self-review 未修项；F5 提交时显式排除 |

## 挂起与备忘

- **版本口径双轨**：文档 0.35.2（版本行/占位/构建信息章示例）先行，代码仍 0.35.1
  （`--version` 与构建信息实际查询显示 0.35.1 是准确事实）——代码升级走 UPGRADE-RUNBOOK
  另批；构建信息章示例按 SKILL 惯例随手册版本预写，代码升 0.35.2 后口径自然对齐。
- **docs 镜像口径变更（2026-11-11 责任人裁决）**：手册批次同步应用官方 docs diff（纯官方
  原文、不加定制标记），取代原"docs 仅随代码升级批次更新"口径；SKILL §八.8 已改写，并新增
  §十 评审后处置规则（评审问题沉淀 + 评审后 PDF/MD 同步）。
  由此 docs 提交与代码版本可能短暂脱钩（如本轮 docs=0.35.2 / 代码=0.35.1），升级 merge 时
  同改同值自动收敛。
- **user-manual 批次 N3（双轨同源对账）的落实方式**：本批次桌面定稿由桌面 0.35 定稿直接
  合并生成，未从 manual 树重出——以六项审计"逐章比对"覆盖等价性（audit 基准=桌面定稿，
  manual 全绿即逐章一致）；N3 原始设想（manual 树重出桌面版做字符级对账）剩余价值为
  拼接规则层面的全等验证，保留登记、下轮视流程变化再评估。
- **architecture 全量测试 11 failed**：与本批次无关——`test_chrys_test_summary` 等 2 处
  实证为中文 Windows（GBK 代码页）子进程输出混入非 UTF-8 字节导致 `UnicodeDecodeError`
  （`PYTHONUTF8=1` 实测无效，文本出自系统层，疑与 SAC 拦截警告相关）；architecture 套件
  按 AGENTS.md 属 Linux CI only，本机全量跑系首次暴露，不属本批次回归。手册契约测试
  26 passed 全绿。
- **临时脚本**：`.tmp_*.py`（替换/校验脚本）与 `docs` 临时 diff 文件用毕已清理；
  `markdown` 依赖已卸载。
