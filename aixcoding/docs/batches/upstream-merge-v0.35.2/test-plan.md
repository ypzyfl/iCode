# 测试方案：追上游 v0.35.2（upstream-merge-v0.35.2）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

升级批次不新增功能代码，测试 = **三层回归 + 流程产物验证**（design「升级决策交付物」与
runbook §3/§4）。手册内容对账**不在范围**（2026-11-11 责任人裁决：`aixcoding/manual/`
完整定制、独立批次跟进）；本批仅机检手册捆绑机制键未漂移。

1. **结构层（机检）**：`gen_customizations.py --strict`（预期 109 行 / 150 marker / 7 退役，
   0 error / 0 warning）+ `aixcoding/tests` 全套（含 `diagnostics/test_panel_anchor.py`
   行为锚定）；
2. **语义层（全量）**：`aixcoding/tools/verify.py --full`（fork-full：定制套件 + 委托上游
   全量；CodeBuddy 配方 = 清 `PYTHONPATH`、`PYTHONUTF8=1`、大写盘符）+ ruff/format
   全目录 + ty 三平台 + i18n 管线。定制套件 merge 后首次按继承 addopts 的
   `-n 8 --dist=worksteal` 实跑（`verify.py` 与 CI 同口径）；出现偶发失败先用
   `-n0` 求稳变体对照归因，不直接判定制交互回归；
3. **冲突适配验证**：`test_program_status_lifecycle.py` 唯一冲突解复核——`_ERROR`
   品牌常量、marker 计数 3、新增上游测试经共享常量获得 AIxCoding 期望；整文件通查
   无遗漏 `iCode` 断言（C144 教训）；
4. **固定关注文件**：`test_manual_reload.py` / `test_prompt_shortcut_send.py` 的 skip
   marker 与 reason 前缀逐点核对；排障单文件单跑（合跑跨文件状态污染为上游固有）；
5. **流程产物**：升级决策清单（冲突点+处理意见、定制化改变清单、淘汰检查逐组结论）
   经责任人裁决留痕 verification.md；手册跟进作为独立事项移交记录。**序列约束**：
   verification.md + self-review.md 落盘、六件套齐备后复跑 `check_docs --closure` 绿，
   再开 PR（批次进行中 closure 红为预期态）。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口 | 类型 |
|---|---|---|
| strict 0 error/0 warning，109/150/7 不变 | `uv run python aixcoding/tools/gen_customizations.py --strict` | 工具/结构 |
| runbook §4 矩阵全绿 | `uv run python aixcoding/tools/verify.py --full` + 定制四门 + R2/R3（base `2fd777f`）+ ruff/format + ty 三平台 | 全量回归 |
| worksteal 调度首跑 | merge 后按继承 addopts（`-n 8 --dist=worksteal`）实跑定制套件；失败时 `-n0` 串行对照并记录归因 | 调度回归 |
| runbook §6 收尾快照 / 重评 | `gen_customizations --report` 时点快照附 verification.md；按来源 design 逐组重评 anchor/risk（预期本区间无变化） | 流程检查 |
| 行为锚定测试绿 | `uv run pytest aixcoding/tests/diagnostics/test_panel_anchor.py -n0 -q` | 行为锚定 |
| i18n 管线全通 / 4 借壳 key 存活 | extract → update → compile → check + oracle 测试；pot/po hash 幂等 | 工具/语义 |
| C079–C081 冲突解 | `pytest tests/app/tui/terminal/test_program_status_lifecycle.py` + `git grep -n "iCode"` 整文件通查 + marker 计数核对 | 语义核对 |
| C013–C017 / C036 / C037 登录与 catalog 接线 | marker 逐行核对 + auth/catalog/tui 定制测试（升级前 629/51/0 同口径） | 语义核对 |
| 固定关注文件 skip marker | `test_manual_reload.py` / `test_prompt_shortcut_send.py` 单文件实跑 + marker/reason 核对 | 语义核对 |
| 手册解耦留痕 + 捆绑机制键一致 | design/verification 移交记录；`documentation.py` / `check_wheel.py` / force-include 三方键核对（区间零改动复核） | 流程/契约 |
| UPGRADE-RUNBOOK 基线更新 | `git diff` 头部两行（版本→0.35.2、日期） | 人工检查 |
| TUI 冒烟 | headless `aixcoding-cli --version` = 0.35.2；启动 / F6 aixcoding tab / 登录徽标与命令 / F4 禁用 | 手工端到端 |
| PR 双 CI 绿 | aixcoding-tests.yml + 上游 ci.yml 桥接（PR checks） | CI 门禁 |
| 升级决策清单裁决留痕 | verification.md 裁决记录节（追加不删旧） | 流程检查 |

## 异常与降级路径

- **冲突解后仍有品牌断言红** → 整文件通查 `iCode` 字面量（同函数多断言漏改先例 C144），
  确认属我方品牌适配缺口后按 R2 增补报批（C158 起），禁止顺手改；
- **auto-merge 语义静默错**（登录 / F4 / live label 被编辑器重构影响）→ marker 定位 +
  对应定制测试 + `test_panel_anchor.py`；需触上游文件则停下 R2 报批；
- **pytest 调度口径变化**（addopts `--dist=worksteal` / 默认排除 gc_calibration）→
  命令行 `-m not integration and not gc_calibration` 覆盖 marker 选择，但 `-n 8
  --dist=worksteal` 仍生效；定制套件先按该调度实跑，偶发失败用 `-n0` 求稳变体对照，
  按「调度差异 / 定制交互 / 真实回归」三分归因，不改上游配置；
- **上游测试环境性失败** → 与升级前 629/51/0 基线及历史在案噪音（WinError 448、
  test_install_scripts 满载 flaky、gc_calibration 偶发）对照归因；OS 级证据留
  verification，实跑验证归 PR 双 CI；
- **R2/R3 unexpected upstream file** → 以新 merge-base `2fd777f` 复跑确认；仍在则逐文件
  对名 approved pool，未获批即停下呈报；
- **手册内容差异**（四篇指南语义变化）→ 本批次不修，verification 记移交；若捆绑机制
  测试红则仅按 C154–C157 契约修键值并重报 R2。

## 手工验证步骤（结果记入 verification.md）

1. `uv run aixcoding-cli --version` → `aixcoding-cli 0.35.2`（headless 冒烟）；
2. `uv run aixcoding-cli` 启动正常，无崩溃告警；
3. F6 → 日志面板出现 aixcoding tab；
4. 顶栏徽标显示登录态；`/login` `/logout` 可发现（`/man` 索引含二者）；
5. F4 模型管理入口保持禁用（catalog 定制预期，非回归）；
6. 新特性抽查：会话浏览器搜索提示为"搜索全部会话…"（上游 0.35.2 行为），
   佐证 merge 语义生效。
