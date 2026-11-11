# 设计：追上游 v0.35.2（upstream-merge-v0.35.2）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-11
- 确认意见：无特别意见

## 方案概述

按 `standards/UPGRADE-RUNBOOK.md` 将 `main_aixcoding_cli` 从上游 0.35.1 升至 **v0.35.2**
（`2fd777f626649d53d7ccd701e26a1a7ada569ce8`；merge 目标 ref = release tag，责任人
2026-11-11 裁决）。

```
上游 v0.35.2 = 2fd777f（父 78acc3b9 + 40e01edd；commit 对象已从本地上游原仓取回）
        │
        ├─ 镜像：责任人已手动同步，main_iCode = origin/main_iCode = 3ea2ca2a
        │  （2fd777f 是其祖先；领先 31 提交 / 25 非合并，不影响 merge 目标）
        ▼
特性分支 chore/merge_upstream_v0.35.2（自 main_aixcoding_cli @d52626f1 拉出）
        │  git merge 2fd777f → 解冲突（干跑预判 1 处）→ 三层核对 → 全量验证
        ▼
PR → main_aixcoding_cli（双 CI 绿后责任人合并）
```

与 runbook §0/§1 标准动作的差异与说明：

- 镜像无需再动：本地/远端 `main_iCode` 均已在 `3ea2ca2a`，`2fd777f` 是其祖先；
  镜像头领先 release 属既定允许状态（v0.35.1 批次先例），merge 目标与 R2/R3 base
  仍取 `2fd777f`；
- GitHub 直连 fetch tag 曾 443 超时，目标 commit 对象已从本地上游原仓
  （`D:\Tech\Github\huawei\iCode\iCode`）按 SHA 取回并核验元数据；merge 使用完整 SHA；
- 升级前基线全绿（2026-11-11）：定制 629 passed / 51 skipped / 0 failed，
  `check_docs --closure` OK，strict 109 行 / 150 marker / 7 退役 / 0 warning；
- **手册解耦（责任人 2026-11-11 裁决）**：`aixcoding/manual/` 是完整定制手册，本批次
  **不做** `docs/` → manual 内容对账、不重放去链/措辞定制、不因手册内容重出 wheel/PDF；
  上游 `docs/` 变更随 merge 带入，手册跟进上游另立手册批次。升级侧仅核对捆绑机制键
  （`BUNDLED_DOCS_PATH` / `BUNDLED_DOCS_PREFIX` / force-include 目标）未漂移；
- 本批次无新增登记表 / 退役表：`gen_customizations --strict` 无草案窗口期信号，
  预期 109 / 150 / 7 终态不变。

### 干跑实测（merge-tree --write-tree，2026-11-11，未动工作区）

区间 149 文件、+8650/−1381 中冲突 **1 处**（v0.35.1 批次为 4 处）：

| # | 冲突文件 | 形态（两侧改动） | 解法 |
|---|---|---|---|
| 1 | `tests/app/tui/terminal/test_program_status_lifecycle.py`（C079–C081 在册） | 上游新增 `_ERROR = _seq("state=error:app=iCode")` 常量 + 新测试 `test_acknowledging_the_context_clears_a_done_or_an_error_result_alike`，原 inline error 期望改用常量；我方同点 inline 改为 `app=AIxCoding` 且带 marker | 接受上游常量形态并品牌适配：`_ERROR = _seq("state=error:app=AIxCoding")`；原 inline marker 迁移到常量定义（覆盖新增测试与原测试），后两处 marker 原样保留——C079–C081 孪生组 **marker 计数 3 不变**，无新增登记 |

其余 148 文件 auto-merge 成功。上游区间 `-G iCode` 全量筛查：含 `iCode` 字面量变更的
测试**仅上述冲突文件**，无其他新增品牌断言预判（fork-full 实证若有遗漏，按 R2 增补报批，
编号自 C158 起）。

### 已预见的语义适配点（auto-merge 通过但需核对）

| 文件 / 产物 | 在册定制 | 上游区间变化 | 核对口径 |
|---|---|---|---|
| `AGENTS.md` | C001 / C130 / C131 | 5 行（pytest 收集口径等正文） | 三段 marker 干跑树全存活；逐段人工比对（auto-merge 过 ≠ 语义对） |
| `pyproject.toml` | C002 / C003 / C103 / C132 / C141 / C154 / C157 | version、pytest addopts（`--dist=worksteal` + 默认 `-m 'not gc_calibration'`）、新 marker `real_css_parse` | 全部 marker 干跑树存活；命令行 `-m` 覆盖默认 marker 选择，但**调度仍继承 `-n 8 --dist=worksteal`**（`verify.py` 与 aixcoding-tests.yml 均不带 `-n0`）——merge 后定制套件先按该调度实跑，偶发失败用 `-n0` 求稳变体对照归因，不改上游配置 |
| `src/chrys/app/tui/screens/main/model_indicator.py` | C041 | `fmt_context_size` 改为调用 `util.formatting.format_compact_count`（2+/7−） | marker 行在、catalog 定制测试绿 |
| `src/chrys/app/tui/screens/main/screen.py` | C013–C017 / C036 / C037 | 89+/27−，集中在 `_on_editor_requested` / `_on_editor_result` / paste editor / editor mode 记忆链路 | C036（F4 禁用）、C013–C017（登录静默校验与 `/login` `/logout` 接线）、C037（live label）与上述编辑器重构区零交叠；auth + catalog + tui 定制测试机检 |
| `tests/app/tui/screens/main/test_hooks_panel_flow.py` | C083–C085 | 测试稳定性重构（68+/9−） | 3 处品牌 marker 干跑树存活；整文件实跑 |
| `tests/app/tui/screens/test_manual_reload.py` | C136–C137 | 测试时序 / helper 变化 | 2 个 skip marker 与 reason 前缀在；**固定关注文件，排障单文件单跑口径** |
| `tests/app/tui/screens/test_prompt_shortcut_send.py` | C135 | `running_session(load_holds=True)` 等测试改造 | skip marker 与 reason 前缀在；固定关注文件 |
| `tests/service/mcp/test_progressive.py` | C091–C093 | 新增重连用例（38+/0−） | 3 处 reserved tool 品牌 marker 在；MCP 测试实跑 |
| `tests/support/tui_helpers.py` | C029 | 点击 helper 增加 Button `-active` 判定 | login stub marker 在；TUI 定制测试绿 |
| `locales/chrys.pot` / `chrys.po`（豁免产物） | R2 表生成/登记产物 | Project-Version 与 2 个 sessions 搜索文案条目 | 与 4 个借壳 key（login/logout）零交叠；merge 后重走 i18n 管线验证 hash 幂等 |
| `tests/architecture/trajectory_wait_manifest.json`（豁免产物） | tier-migration 登记 | 上游自身刷新 | 随 fork-full / architecture 套件验证；不手工编辑 |
| `scripts/fetch_rg.ps1` / `.sh` | 无 marker | 仅重试策略增强 | `RG_VERSION/RgVersion` 零变化，无需重取 vendored rg |
| 上游 `docs/` 8 个文件 | 无定制（手册在 `aixcoding/manual/`） | 会话搜索 / 粘贴标签 / skills 层级 / shortcuts 说明更新 | merge 直接接受上游；**manual 内容不同步**（独立手册批次），仅核对捆绑机制键 |

环境与机制核查：

- `.python-version` 零变化（3.14.10），`uv.lock` 仅 `icode-tui` 版本行 0.35.1→0.35.2，
  merge 后 `uv sync --frozen` 对齐即可；
- `BUNDLED_DOCS_PATH`（`foundation/documentation.py`）、`BUNDLED_DOCS_PREFIX`
  （`scripts/check_wheel.py`）与 force-include 目标在区间零改动，C154–C157 捆绑契约无暴露；
- 上游 CI 变化（TUI 套件拆分、ripgrep 缓存、新增 cache-warmer workflow）为上游自身变更；
  fork 侧 `aixcoding-upstream-ci.yml` 经 `workflow_call` 复用上游 `ci.yml`，无需改动。
  `rg-cache-warmer.yml` 的 `schedule` 触发器在 fork 默认分支会按 cron 真正运行（无害），
  verification.md 记录首次运行观察（责任人 2026-11-11 裁决纳入）。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（R1） | 结论 |
|---|---|---|---|---|
| A. merge v0.35.2 release commit（本设计） | 稳定 release；干跑冲突仅 1 处且解法明确；无环境版本变更 | — | 小（实测） | **选定**（责任人已裁决目标 ref） |
| B. 等待后续版本再升级 | 可能少一次升级成本 | 违反 §8 节奏条款（需显式决策）；债务累积 | — | 否决 |
| C. merge 镜像头 `origin/main_iCode`（3ea2ca2a） | 一步带到上游 main 最新 | 引入未发布提交（领先 31 提交），违背本次 release 目标裁决 | 更大 | 否决 |
| D. rebase 定制提交到 v0.35.2 | 历史线性 | 改写已发布历史 + force push，纪律禁止 | — | 否决 |

## 上游改动清单（R2）

**本批次我方对上游文件的新增改动 = merge 冲突解 1 处**，落在既有在册定制点，无新增登记：

| 文件 | 改什么 | 标记注释位置 |
|---|---|---|
| `tests/app/tui/terminal/test_program_status_lifecycle.py` | 接受上游 `_ERROR` 常量形态并品牌适配为 `state=error:app=AIxCoding`；原 inline marker 迁移到常量定义，后两处 marker 保留（C079–C081 计数 3 不变；上游新增测试经共享常量自动获得品牌期望） | 既有 `AIxCoding branding: OSC app name assertions` |

merge 带入的上游自身变更（版本行、pytest addopts、CI、docs、src/tests 等）不属我方改动；
R2/R3 以新 merge-base（预期 `2fd777f`）跑，fork 相对 base 的上游文件 diff 应全部落在既有
approved pool（109 登记行口径）。

配套适配（非上游文件，不占 R2；前两项已随本草案落地，2026-11-11）：

- `aixcoding/docs/standards/UPGRADE-RUNBOOK.md`：手册对账条款改为解耦口径；收尾更新头部基线；
- `aixcoding/docs/batches/user-manual/plan.md`：手册跟进口径同步改为独立批次；
- 本批次目录文档与 verification 留痕。

若 merge 后验证暴露新的上游测试品牌断言冲突：停下按 R2 增补报批后再动
（新 marker 编号自 **C158** 起，随 design 重签生效）。

## 对上游隐式行为的假设

| 假设 | 我方依赖方式 | 失效表现与对策 |
|---|---|---|
| `main/screen.py` 编辑器重构不改变登录接线 / F4 禁用 / live model label 的调用时机 | C013–C017 / C036 / C037 marker 与 anchor | auth / catalog / tui 定制测试红 → 按 marker 定位后跟随适配（触上游文件则回 R2 报批） |
| `format_compact_count` 抽取仅移动数字格式化，不改变 model indicator 的 live registry 语义 | C041 label 计算 | catalog 定制测试红 → 核对 `compute_model_indicator_state` 签名与 registry 参数 |
| pytest addopts 的 `-m` 选择被我方命令行覆盖，`-n 8 --dist=worksteal` 调度则继续生效 | `verify.py` 定制命令与 aixcoding-tests.yml 均不带 `-n0`，merge 后首次在 worksteal 下跑定制套件 | 偶发失败 → 先用 `-n0` 求稳变体对照归因（调度差异 / 定制交互 / 真实回归三分），勿直接改上游配置 |
| sessions 全局搜索 / MCP 重连 / kernel 序列化变化不与在册定制点交叠 | 这些文件无定制 marker | 上游测试红 → 先归因纯上游 vs fork 交互；上游自身缺陷记录呈报，不擅自修上游 |
| 2 个 sessions 搜索文案变更不触碰 4 个借壳 key | C027 id 集合 | oracle / i18n check 红 → 重走管线后复测，仍缺则查 msg 定义处 |
| 手册捆绑机制键三方一致 | C154–C157 捆绑契约 | `test_documentation.py` / `check_wheel.py` 红 → 键值跟随并重报 R2 |
| 镜像头领先 release 不影响 merge 结果 | merge 目标为 `2fd777f`，R2/R3 base = 新 merge-base | diff 区间异常 → 核对 merge-base 是否恰为 `2fd777f` |

## 定制点登记预告

不适用：本批次零新增定制点、零退役。唯一冲突解落在既有 C079–C081 孪生组，
marker 计数保持 3；预期 strict 终态仍为 109 登记行 / 150 marker / 7 退役。

C079–C081 anchor 描述漂移已知（源 design 写「3 个测试函数」；冲突解后形态 =
1 个模块级 `_ERROR` 常量被 2 个测试函数共用 + 2 个函数内断言）。责任人 2026-11-11
裁决 B3(a)：**不修改** `branding-and-command/design.md` 登记行，本节与 verification.md
留痕即可——marker 锚与计数不变，`--strict` 机检不受影响。

## 既有定制点存活核对矩阵（runbook §3 结构层展开）

输入 = 升级前 `gen_customizations --report` 时点快照（109 行 / 150 marker / 7 退役）。
上游区间与 marker 文件交集共 10 文件 + 3 豁免产物（见语义适配点表）；按来源 design 逐组结论：

| 来源 design（登记行数） | 暴露与结论 |
|---|---|
| agents-md-note（1） | AGENTS.md 5 行上游改动；C001/C130/C131 干跑树存活，逐段人工比对 |
| tui（18） | `main/screen.py`（编辑器重构，marker 零交叠）、`tui_helpers.py`（C029）存活；C013–C017/C036/C037 由定制测试机检 |
| auth（2）+ auth-logging（1） | `wire_client.py` / `app/cli/app.py` / `chrys.kernel` 包级导出区间零改动，无暴露 |
| diagnostics（1） | `logs/screen.py` 区间零改动，无暴露 |
| catalog-sync（15） | `main/screen.py` C036/C037、`model_indicator.py` C041 交叠但 marker 存活；registry/config_actions 等其余落点零改动 |
| catalog-auth-gating（1） | process_settings 等落点区间零改动 |
| branding-and-command（48） | 4 个测试文件交叠（C079–C085 / C091–C093），marker 干跑树存活；唯一冲突即 C079–C081；`-G iCode` 确认无其他新增品牌断言 |
| logo-branding（4） | serve/TUI logo 落点区间零改动 |
| guard-hooks（2）+ guard-switches（1） | startup / pack / lint profile 落点区间零实质改动（pyproject 仅 addopts/marker/version），marker 存活 |
| llm-keyless-sdk-auth（1） | `sdk_openai.py` 区间零改动 |
| ruff-test-exemptions（1） | pyproject per-file-ignores 行存活 |
| user-manual（4） | C154/C155/C156/C157 捆绑机制键区间零改动；**manual 内容 knowingly 保持 0.35.1，待独立手册批次**（责任人 2026-11-11 裁决） |
| upstream-merge-v0.33.0（3） | C135 落点 `test_prompt_shortcut_send.py` 交叠，skip marker 存活 |
| upstream-merge-v0.34.0（4） | C136/C137 落点 `test_manual_reload.py` 交叠，skip marker 存活 |
| upstream-merge-v0.35.1（2） | C143/C144 落点（extension tool hooks / startup 断言）区间零改动 |
| 机检兜底 | strict 109/150/7 + `test_panel_anchor.py` + 定制全套（升级前 629/51/0） |

## 升级决策交付物（runbook §5）

1. **冲突点全清单 + 逐点处理意见**：干跑 1 处（上表），merge 后按实际补全；
   auto-merge 语义核对点见"语义适配点"表；
2. **定制化改变清单**：
   - 需新增：预判无（fork-full 实证如有品牌断言遗漏，R2 增补报批）；
   - 建议删除：预判无淘汰候选——C004/C140 相关扩展机制文件本区间零改动，
     v0.35.1"保留"裁决无新触发；其余 removal_condition 逐组未命中（最终结论以
     merge 后 report 全景复核为准）；
   - 需适配：C079–C081 冲突解（marker 迁移到 `_ERROR` 常量，计数不变）；
   - 手册内容** knowingly 不适配**：独立手册批次跟进（本批次留移交记录）；
   - **淘汰检查逐组结论载体（固定口径）**：merge 后以 `gen_customizations --report`
     全景为输入，**按 17 个来源 design 分组**出表落入 verification.md（与「既有定制点
     存活核对矩阵」同构），逐组记录 hit/not-hit 与依据，最终决策交责任人；
3. **裁决记录**：verification.md 追加不删旧（开工 / 目标 ref / 手册解耦 / B3(a) /
   任何增补处置）；
4. **runbook §6 收尾交付**：`gen_customizations --report` 时点快照附 verification.md；
   各定制点 anchor/risk 按来源 design 分组重评（预期本区间无变化，结论落 verification）。

## 风险与最坏情况

- **最大风险：`main/screen.py` 编辑器重构与测试基建改造的语义静默错**——对策 =
  marker 逐行核对 + auth/catalog/tui 定制测试 + fork-full + TUI 冒烟；
- **worksteal 首跑调度差异**：定制套件历史上常以 `-n0` / 既有调度跑，merge 后首次
  继承 `-n 8 --dist=worksteal`（verify.py 与 CI 同口径）——偶发失败先 `-n0` 对照
  三分归因（调度差异 / 定制交互 / 真实回归），不据此放宽 CI 门禁；
- **同函数多断言漏改**（v0.35.1 C144 教训）：冲突文件已按 `-G iCode` 全区间筛查，
  解冲突后整文件再通查一遍；
- **本机环境性噪音**：历史在案 WinError 448 junction 族、test_install_scripts 满载 flaky、
  gc_calibration 偶发——升级前基线本轮 0 failed；merge 后同口径复跑归因，不据此放宽门禁；
- **手册内容滞后**：0.35.2 行为与 0.35.1 手册存在四篇语义差（会话搜索/粘贴标签/
  skills 层级/shortcuts），本批次接受该窗口期，移交独立手册批次；捆绑机制键仍机检；
- **回滚**：merge 在特性分支进行，可随时丢弃分支从 `main_aixcoding_cli` 重来；
  PR 合并后回滚 = revert 该 merge PR（单点可逆）。

## ADR 判定

按 §6 checklist 逐项：①否决的备选（B/C/D）为 runbook/纪律既定路径常规排除，非新决策；
②撤销代价低（revert merge 单点可逆）；③不约束未来工作模式（手册解耦为既有 user-manual
批次方向的执行口径澄清，已落活文档）；④无新增上游非公开接口依赖。**结论：不出 ADR。**
