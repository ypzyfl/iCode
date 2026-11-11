# 验证记录：追上游 v0.35.2（upstream-merge-v0.35.2）

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，不删旧记录。

## 一、验证矩阵结果总表（2026-11-11）

| 验证项 | 结果 | 证据 / 说明 |
|---|---|---|
| 升级前基线：定制套件 | **629 passed / 51 skipped / 0 failed**（117.83s，`-n0`） | 基线 HEAD `d52626f1`；guard symlink 环境性失败本次未复现 |
| 升级前基线：文档与登记 | `check_docs --closure` OK（24 ADR / 38 design / 37 self-review）；`gen_customizations --strict` OK（**109 行 / 150 marker / 7 退役 / 0 warning**） | 批次目录创建前时点；六件套齐备前 closure 红为预期 |
| merge | `git merge 2fd777f…` 停在 **1 处冲突**，与干跑预判逐字一致 | 仅 `tests/app/tui/terminal/test_program_status_lifecycle.py` |
| 冲突解 | `_ERROR = _seq("state=error:app=AIxCoding")` + marker 迁移；后两处 marker 原样；整文件无 `iCode` 残留、无冲突标记 | `git diff --check` OK；marker 3 处（65/150/231） |
| 冲突解目标测试 | **8 passed**（31.16s，`-n0`） | `pytest tests/app/tui/terminal/test_program_status_lifecycle.py` |
| 依赖对齐 | `uv sync --frozen` OK；包版本 **0.35.2** | `.python-version` 仍 3.14.10；`uv.lock` 仅版本行变化 |
| i18n 管线 | extract → update → compile → check **三轮全过**；pot/po hash 第二、三轮逐位一致：pot `cd915d7431a29cfbe687657d629a0dd87f88fc55` / po `67ff465d58802d5da781ba9806d45f51a41fb1ee` | 4 个借壳 key 全在 id 集合（commands description ×2 + man body ×2） |
| worksteal 首跑 | 定制套件继承 `-n 8 --dist=worksteal`：**629 passed / 51 skipped**（29.35s） | 无需 `-n0` 对照；verify.py 与 CI 同口径 |
| 定制门禁 | `check_docs.py`（不带 `--closure`）OK；`check_import_boundaries.py` OK（1222 files）；`gen_customizations --strict` OK（**109 / 150 / 7 / 0**） | merge 后复跑；closure 口径见表末 |
| R2 | `check_r2_diff.py --base 2fd777f…` **OK**：add 后终态 changed=561 / upstream_changed=85 / approved_pool=93（558 为六件套落盘前工作树时点，+3 全为本批次 custom 文档） | 85 个上游变更全落审批池；历史“文件/同上”表头 warn 在案（非本批新增） |
| R3 | `check_r3_markers.py --base 2fd777f…` **OK**：add 后终态 upstream_changed=85 / marker_checked=82 / exempt=3 | index 已收敛，无 UU/RM/MM 残留 |
| ruff / format | `ruff check --no-fix … aixcoding/` OK；`ruff format --check … aixcoding/` **3099 files already formatted** | 全目录口径（含 aixcoding） |
| ty 三平台 | linux / darwin / win32 均 **All checks passed!** | `--error-on-warning` |
| fork-full | `uv run python aixcoding/tools/verify.py --full` **全过** | 后台执行由责任人确认 console 全过；无机器留存计数（见第六节裁决记录）。进程正常结束，result 临时文件由 `chrys_test.py` 自清理。脚本源码核实 `--full` = regular worksteal + architecture 串行 |
| 打包 | `uv build` 成功（sdist + wheel）；`scripts/check_wheel.py dist/icode_tui-0.35.2-py3-none-any.whl` **通过** | wheel 含 67 个用户手册文件与 zh-Hans catalog；安装探测 `aixcoding-cli` = 0.35.2，13 个 help screen 渲染，rg 随包 |
| headless 冒烟 | `uv run aixcoding-cli --version` → **0.35.2** | — |
| TUI 手工冒烟 | **五项通过**：启动无崩溃；F6 有 aixcoding tab；登录徽标与 `/login` `/logout` 可用；F4 保持禁用；`/sessions` 搜索占位显示“搜索全部会话…（匹配 ID、标题、目录和你的提示词）” | mock 复用既有 `python -m aixcoding.mock`（7777/7778 连通，来自 `iCode-fork_2` 工作树，未杀旧实例）；TUI 独立可见窗口启动于本仓 |
| UPGRADE-RUNBOOK 基线 | 头部更新为 0.35.2 / 2026-11-11 | git diff 人工核对 |
| `check_docs --closure` | **OK（24 ADR / 39 design / 38 self-review）** | self-review 签认后实测；收尾独立评审同口径复测绿 |

## 二、冲突点全清单 + 逐点处理意见（runbook §5 交付物 1）

### merge 文本冲突（1 处，与干跑预判一致）

| # | 文件 | 处置 | 验证 |
|---|---|---|---|
| 1 | `tests/app/tui/terminal/test_program_status_lifecycle.py`（C079–C081） | 接受上游模块级 `_ERROR` 常量形态并品牌适配为 `app=AIxCoding`；原 inline marker 迁移到常量定义，后两处 marker 保留（计数 3 不变）。上游新增测试与原测试共享常量，自动获得品牌期望 | 单文件 8 passed；整文件 `iCode`/冲突标记通查零残留；strict 150 marker 对账 |

### auto-merge 通过但语义核对（design 预判点全部覆盖）

- `AGENTS.md`：C001/C130/C131 三段 marker 存活；
- `pyproject.toml`：7 个 marker 存活；`-m` 选择被命令行覆盖，worksteal 调度按新 addopts 首跑全绿；
- `model_indicator.py`（C041）/ `main/screen.py`（C013–C017/C036/C037）：marker 存活，编辑器重构区与定制接线零交叠，定制套件绿；
- `test_hooks_panel_flow.py`（C083–C085）、`test_progressive.py`（C091–C093）：品牌 marker 存活，全套通过；
- `test_manual_reload.py`（C136/C137）、`test_prompt_shortcut_send.py`（C135）：skip marker 与 reason 前缀在，固定关注文件由 fork-full 覆盖；
- `tui_helpers.py`（C029）：login stub marker 存活；
- pot/po：上游仅版本头与 2 个 sessions 搜索条目，4 借壳 key 不受影响，三轮管线幂等；
- `trajectory_wait_manifest.json`：上游自身刷新，fork-full / architecture 覆盖；
- `fetch_rg.ps1/.sh`：仅重试策略变化，`RG_VERSION/RgVersion` 零变化。

## 三、定制化改变清单（runbook §5 交付物 2）

- **需新增**：无（R2 预跑 85 个上游变更全落既有审批池，无 C158+ 增补）；
- **需适配**：仅 C079–C081 冲突解（marker 迁移到 `_ERROR` 常量，计数 3 不变）；
- **建议删除**：无淘汰候选执行——C004/C140 相关扩展机制文件本区间零改动，v0.35.1“保留”裁决无新触发；
- **手册内容 knowingly 不适配**：上游 4 篇指南语义变化（会话全局搜索 / 粘贴标签 / skills 两层 / shortcuts），`aixcoding/manual/` 保持 0.35.1，独立手册批次跟进（2026-11-11 责任人裁决）；
- **手册捆绑机制**：`BUNDLED_DOCS_PATH` / `BUNDLED_DOCS_PREFIX` / force-include 三方区间零改动，wheel 探测 67 个手册文件通过。

## 四、登记矩阵逐组存活核对结论（runbook §3 结构层）

输入 = merge 后 `gen_customizations --report` 时点快照（109 行 / 150 marker / 7 退役 / 孤儿 0）。

| 来源 design（登记行数） | 结论 |
|---|---|
| agents-md-note（1） | 存活：C001/C130/C131 三段 marker 在 |
| tui（18） | 存活：C013–C017/C029 等 marker 在；`main/screen.py` 编辑器重构零交叠 |
| auth（2）+ auth-logging（1） | 存活：相关上游文件区间零改动 |
| diagnostics（1） | 存活：`logs/screen.py` 零改动 |
| catalog-sync（15） | 存活：C036/C037/C041 marker 在；catalog 定制测试绿 |
| catalog-auth-gating（1） | 存活：落点零改动 |
| branding-and-command（48） | 存活：C079–C081 冲突解完成；C083–C085/C091–C093 marker 在；`-G iCode` 无其他新增断言 |
| logo-branding（4） | 存活：落点零改动 |
| guard-hooks（2）+ guard-switches（1） | 存活：落点零实质改动 |
| llm-keyless-sdk-auth（1） | 存活：`sdk_openai.py` 零改动 |
| ruff-test-exemptions（1） | 存活：per-file-ignores 行在 |
| user-manual（4） | 存活：C154–C157 捆绑契约零改动；manual 内容滞后属裁决范围 |
| upstream-merge-v0.33.0（3） | 存活：C135 skip marker 在 |
| upstream-merge-v0.34.0（4） | 存活：C136/C137 skip marker 在 |
| upstream-merge-v0.35.1（2） | 存活：C143/C144 落点零改动 |
| 机检兜底 | strict 109/150/7 = 0/0；行为锚定含于定制套件 629/51/0 |

## 五、淘汰检查逐组结论（runbook §5 交付物 3）

以 merge 后 report 全景为输入，按来源 design 分组：

| 来源 design | hit / not-hit 与依据 |
|---|---|
| agents-md-note / ruff-test-exemptions | **not-hit**：〔常驻〕/政策未变 |
| tui / branding / logo | **not-hit**：品牌与登录政策未变；上游会话/编辑器变化未提供等价登录或品牌机制 |
| auth + auth-logging | **not-hit**：`wire_client.py`、`app/cli/app.py`、kernel 导出零改动；无官方启动期登录机制 |
| diagnostics | **not-hit**：`logs/screen.py` 零改动，无第三方模块分层原生机制 |
| catalog-sync / catalog-auth-gating | **not-hit**：F4 禁用与只读政策未变；上游模型配置变化未触及 registry/config_actions |
| guard-hooks / guard-switches | **not-hit**：扩展 hook / 规则包分发机制相关文件零改动，v0.35.1 C004/C140 保留裁决继续有效 |
| llm-keyless-sdk-auth | **not-hit**：`sdk_openai.py` 零改动 |
| user-manual | **not-hit**：上游未提供手册数据源配置化或交付文档治理通道；内容滞后为独立批次而非退役条件 |
| 三个历史 upstream-merge 批次 | **not-hit**：测试支撑 skip/断言定制 removal_condition 未触发 |

**结论：本批次无淘汰候选、无登记行删除、无退役记录新增。**

## 六、裁决记录（追加不删旧）

- **2026-11-11 开工裁决**：完整升级管线；merge 目标 = release tag v0.35.2（commit `2fd777f626649d53d7ccd701e26a1a7ada569ce8`）；镜像已由责任人手动同步至 `3ea2ca2a`（目标是其祖先）。
- **2026-11-11 手册解耦裁决**：`aixcoding/manual/` 为完整定制手册，升级批次不做内容对账；手册跟进上游由独立批次处理。UPGRADE-RUNBOOK §2 与 user-manual/plan 已同步修订。
- **2026-11-11 外部文档评审处置**：B1 SHA 订正；B2 选择“统一修订后重签”；B3(a) C079–C081 anchor 描述漂移留痕、不改 `branding-and-command/design.md`；建议 7 项全部纳入。
- **2026-11-11 design 重签**：责任人周彬确认（正文修订后按 R10 重签）。
- **2026-11-11 git 写操作逐条授权**：建分支 `chore/merge_upstream_v0.35.2`；merge `2fd777f…`。冲突解为工作区编辑，未 add/commit。
- **2026-11-11 fork-full 结果归属**：后台 console 由责任人确认“全过”；进程正常结束；临时 result 文件被脚本清理，具体 passed 计数未留存。
- **2026-11-11 收尾独立评审（CodeBuddy / Deepseek-V4-Pro）**：blocker 0；strict /
  closure / R2 / R3 / R11 / 冲突解 / 配套文档实测通过。nit ×3 处置——R2 changed
  558→561 时点漂移已注明（+3 全为本批次 custom 文档）；plan 两项滞后勾选已同步；
  pot/po 的 MM 为 Windows autocrlf 状态噪音（`git diff --numstat` 为空），add 后确认
  无纯行尾内容 diff。报告留 self-review.md 第六节。

## 七、定制点时点快照（gen_customizations，2026-11-11 merge 后）

- 完整逐行 report 已存档：`customizations-snapshot-2026-11-11.md`
  （SHA-256 `76F204424FCEF22978A4186CF0F7AB4FABBECB0CC3294AA9F50DB8B552C6D845`）；
- 摘要：定制点 **109 行** / 孤儿 **0** / 退役 **7**；
- `--strict` 实测：`109 registration row(s) / 150 marker(s) across 17 design(s), 7 retired id(s), 0 warning(s)`；
- 升级前同为 109/150/7：本批次零新增、零退役、零 marker 计数变化。

## 八、anchor / risk 重评（runbook §6 第 3 步，按来源 design 分组）

结论：**17 组 anchor 与 risk 全部维持原登记，无需重签任何源 design**。依据 =
marker/anchor 全景对账 0 error 0 warning + 上游区间与定制落点交集逐文件核对（第四节）。

| 来源 design | anchor / risk 重评 |
|---|---|
| agents-md-note | anchor（AGENTS 三段）不变，risk 低；上游正文 5 行改动未触碰 marker |
| tui | `BaseDialog`/`MainScreen` 等anchor 存活，`main/screen.py` 编辑器重构与登录接线零交叠；risk 维持原判 |
| auth + auth-logging | `wire_client.py` / `app/cli/app.py` / kernel 导出零改动；risk 不变 |
| diagnostics | `logs/screen.py` 的 `MODULE_ORDER` 零改动；risk 不变 |
| catalog-sync | C036/C037/C041 anchor 行在，registry/config_actions 等落点零改动；risk 不变 |
| catalog-auth-gating | process_settings 等落点零改动；risk 不变 |
| branding-and-command | C079–C081 marker 锚与计数不变（实现形态迁移已按 B3(a) 留痕），其余品牌 anchor 存活；risk 低不变 |
| logo-branding | serve/TUI logo 落点零改动；risk 不变 |
| guard-hooks + guard-switches | startup / pack / lint profile 落点零实质改动；risk 不变 |
| llm-keyless-sdk-auth | `sdk_openai.py` 零改动；risk 不变 |
| ruff-test-exemptions | per-file-ignores anchor 行在；risk 不变 |
| user-manual | 捆绑三方键零改动；manual 内容滞后属独立批次，不改变 anchor/risk |
| upstream-merge-v0.33.0 | C135 skip anchor 在；risk 不变 |
| upstream-merge-v0.34.0 | C136/C137 skip anchor 在；risk 不变 |
| upstream-merge-v0.35.1 | C143/C144 断言 anchor 在；risk 不变 |
| 机检结论 | `--strict` 0/0 + 定制套件 629/51/0 支撑上述“无需重评变更”结论 |

## 九、遗留项与收尾跟踪

- merge commit / push：`git add -A` 已逐条授权完成（index 无 UU/RM/MM 残留，locales 无未暂存内容漂移，staged whitespace OK）；commit 与 push 继续逐条申请；
- PR 双 CI：push 后由责任人在 GitHub 网页建 PR，双 CI 绿后合并；
- **手册跟进**：4 篇上游指南语义变化移交独立手册批次（含 manual 同步、去链/措辞重放、wheel/PDF 重出评估）；
- **`rg-cache-warmer.yml` 首次运行观察**：workflow 随 merge 入库；`schedule` 为每周一 06:23 UTC，push/PR 仅限 `main` 路径。fork 默认分支合并后观察首次定时运行并在此追加记录；
- ~~R2/R3 终态复跑~~ 已完成：R2 561/85/93 OK、R3 85/82/3 OK（add 后）；
- ~~`check_docs --closure` 终态复跑~~ 已完成：OK（24 ADR / 39 design / 38 self-review）。
