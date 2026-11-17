# 自评审记录：PR 门禁按需触发分层

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-12
- 确认意见：（可选）
- 开发 AI：CodeBuddy（Kimi-K3.1-Pro）
- 评审 AI：CodeBuddy（BM:GLM-5.3）——独立第二 AI，与开发 AI 不同源

## 2026-11-12 方案与文档评审：收敛（三轮，design 签认前）

- 轮次：三轮（方案评审 → 裁决建议反馈 → requirements/design 文档评审）。
- 第一轮（方案）：有条件通过——①定制产品静态门随 L2 跳过失守（阻塞级，核实 DIRECTORY §7 属实）；
  ②所有权分类≠影响分类；③nightly+dispatch 必做兜底；④`--no-renames`、grep 退出码 fail-open、
  gate 状态机等 fail-closed 强化。**全部采纳**并展开为批次蓝图（D1–D5 经责任人确认）。
- 第二轮（裁决建议）：README.pypi.md（b1）与 manual（b2）拆开裁决、独立批次完整管线 + 新 ADR、
  七项全量 nightly 不推迟、compileall 单独评估、nightly“≤24h”表述精确化 + 失败可见性、
  docs/ oracle 定案。**全部采纳**（docs/ 实测 66 md + index.yaml 支撑受信任文档区口径）。
- 第三轮（文档评审，F1–F7，无 blocker）：
  - F1 ty 平台取舍与定制层平台敏感性事实不符 → **已修**：单 runner 显式三平台各跑一次；
  - F2 注入点计数过时 → **已修**：31 上游文件 / 52 处（2026-11-12 实测口径）；
  - F3 现状正则漏 manual 分支 → **已修**（11-11 扩围补记，D2 改为延续语义）；
  - F4 touched=false 验收时点 → **已修**：design 新增验收时点说明（合并后临时验证 PR）；
  - F5 清单路径口径 → **已修**（统一完整路径）；F6 ADR-0004 修订形态 → append-only 注记；
  - F7 user-manual“不再回填”承诺张力 → 修订注明原承诺经本批修订。
  - 复核：`check_docs.py` OK；关键事实经评审独立核实与本地复核双确认。
- 未修项：无。

## 2026-11-12 实施评审：通过（blocker 清零）

- 评审 AI：CodeBuddy（BM:GLM-5.3）。评审方法为独立复现（非转述）：38 单元测试、684 定制套件、
  strict、pins、closure（9 errors=草案挂账预期）均独立复跑一致；checkout/setup-python 两个
  pin 经 GitHub API 核实签名匹配（顺带核销 upstream-ci 在案未验证事项，已回填）。
- 逐项检查 14 项全过：R2 比对（12 处改动全在 design 清单内、零上游文件）、R11（无新依赖，
  setup-python 与上游既有 pin 逐字符一致）、幻觉 API、静默吞错、vacuous test 抽 2（删 FORCE
  条目/删空清单 raise 均致测试红）、gate 状态机四象限穷举、ci.yml build_ref 假设、文档联动
  交叉一致、YAML 语法、测试落位惯例等。
- findings（均非阻断）：
  - F1 filter 的 `fetch-depth: 0` 对非 PR 事件浪费全历史 clone | **不修**（责任人拍板
    2026-11-12：每晚数十秒，结构简单优先）
  - F2 DIRECTORY §7“约 20 job”与历史 17 job 数字漂移 | **不修**（责任人拍板 2026-11-12，
    nightly 首跑后统一口径）
  - F3 upstream-ci 在案 pin 未核事项 | **已回填**（本次评审 API 核实，含 setup-python）
- 本地验证证据：见 verification.md 2026-11-12 节。
