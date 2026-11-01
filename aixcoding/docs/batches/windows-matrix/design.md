# 设计：定制测试 Windows 矩阵（windows-matrix）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-01
- 确认意见：无特别意见

## 方案概述

将 `.github/workflows/aixcoding-tests.yml` 从单 `gate` job（全步骤 + Linux）重构为与上游
桥接门（`aixcoding-upstream-ci.yml` 的 filter/ci/gate）同构的三层结构；治理步骤与测试
步骤分离，测试扩 Windows 矩阵，required check 落点（job 名 `AIxCoding quality gate`）
保持不变：

```
jobs:
  test:    # matrix [ubuntu-latest, windows-latest]，fail-fast: false，timeout-minutes: 15
           #   只跑: uv run pytest aixcoding/tests -m "not integration and not gc_calibration"
           #   （与现门逐字相同；另经 step env PYTEST_ADDOPTS="-rA" 注入 short summary，
           #    命令文本不变——评审 F-01；Windows 侧加 TEMP/TMP 重定向 + .venv 缓存）
  govern:  # 单 ubuntu-latest，timeout-minutes: 15，跑全部治理步骤:
           #   ruff check/format aixcoding/、check_docs.py、check_import_boundaries.py、
           #   gen_customizations.py --strict、R2/R3（checkout fetch-depth: 0）
  gate:    # name: "AIxCoding quality gate"（required check 名不变）
           #   needs: [test, govern]，if: always()，
           #   env 双断言 test "$TEST_RESULT" = "success" / test "$GOVERN_RESULT" = "success"
           #   runs-on: ubuntu-slim（仅 shell 判定，秒级，不设 timeout——对齐 upstream gate）
```

变更范围：`aixcoding-tests.yml` 单文件重构（fork 专属文件）+ 批次文档 + 文档联动
（DIRECTORY.md §7、ADR-0004 修订注记）。上游 `ci.yml` 与 `aixcoding-upstream-ci.yml`
不动。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| A 单 job matrix + `if:` 条件步骤 | 改动最小 | required check 名随 matrix 展开成 job 实名（分支保护匹配 job 级 check run 名——upstream-ci verification 2026-10-26 实证），稳定性不可证伪；治理步骤随 OS 重复或全加 `if` | 低 | 否（预案评审 F-03） |
| B 拆两并列 job（linux/windows） | 直观 | 无稳定汇总 gate，required check 须钉两个实名，OS 增删即改 ruleset；治理重复 | 低 | 否 |
| C 三层 test/govern/gate | required check 保名稳定（gate 唯一落点）；治理单次不随 OS 重复；双 OS 并行；与上游桥接门/上游 ci.yml 平台 gate 双先例同构 | job 数 +2；workflow 首次重构需首 PR 实证 check 名 | 低（fork 专属文件，上游升级零接触） | **采用**（预案 v3 已裁决） |

**决策点 Q3-a（ruff 归层）**：

| 选项 | 理由 | 结论 |
|---|---|---|
| ruff 归 `govern` 层 | ruff 语义上是治理不是测试；`test` 两 OS 保持逐字相同命令（对照清晰，避免"Linux 多跑 ruff、Windows 只跑 pytest"的不对称）；ruff 平台无关单次足够；`govern` 反正为 R2/R3 单独存在，挂入零额外成本 | **推荐** |
| ruff 留 Linux `test` 份 | 步骤留在原 job 内 | 否（不对称 + 语义错位） |

**决策点 Q3-b（gate fail-closed 实现）**：`needs: [test, govern]` + `if: always()` +
step env 注入 `TEST_RESULT: ${{ needs.test.result }}` / `GOVERN_RESULT:
${{ needs.govern.result }}`，shell 双断言两个值均 `= "success"`——对齐
`aixcoding-upstream-ci.yml` gate（doc-only 分支同构判定）与上游 `ci.yml`
`test_windows_gate`（matrix 聚合判定）双在产先例。matrix 聚合语义：`needs.test.result`
在任一分片失败时为 `failure`；`skipped`/`cancelled` 均不等于 `success` → fail-closed。
gate 自身无 `needs` 缺失路径（两上游 job 均无 `if` 条件跳过，必产生 result）。

## 上游改动清单（R2）

无上游改动：`aixcoding-tests.yml` 为 fork 专属新增文件（ci-gate 批次产物，ADR-0004），
非上游 `ci.yml`；本批不触 `src/chrys/**`、上游 `.github/**`、`pyproject.toml`、
`uv.lock`。

R1 自查：不适用（零上游文件）。

## 对上游隐式行为的假设

1. `actions/cache`（pin `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` v6.1.0）在
   `windows-latest` 可用——上游 `ci.yml` `test_windows` 同 pin 同 OS 在产；
2. `.venv` 缓存 key 与上游同构（`venv-${{ runner.os }}-${{ hashFiles('.python-version',
   'uv.lock', 'pyproject.toml') }}`）**有意共享**：两边 `uv sync` 命令与 lockfile 一致，
   同 key 共享一份缓存最省配额；`uv sync` 为精确化操作，缓存内容即使不匹配也会被矫正
   （只影响速度不影响正确性）；
3. `needs.<job>.result` 对 matrix job 聚合（任一分片失败 → `failure`）——GitHub Actions
   语义，上游 `test_windows_gate` 同用法在产；
4. 定制测试不依赖 ripgrep——已复核 `aixcoding/tests/**` 零 `ripgrep|fetch_rg` 引用
   （2026-11-01），无需 `fetch_rg.ps1` 步骤；
5. 定制测试不 spawn py39 workflow worker——已复核零 `CHRYS_PY39|PY39` 引用，无需
   `uv python install 3.9` 步骤；
6. matrix 全部子 job skipped 时 `needs.test.result` 的聚合值——官方文档未明确（评审
   标注需查证：最小 workflow 实验可验）；当前 `test` 无 job 级条件跳过、无触发路径，
   方案不依赖该边界；未来若引入条件跳过，先实验验证再依赖。

## 定制点登记预告

不适用：纯开发资产（fork 专属 CI workflow 文件重构），零上游接触。

## 风险与最坏情况

- **Windows runner 环境差异**（端口/路径/时序）：定制测试端口已动态化
  （auth-isolation-mock-ports 批，`port=0`）；若首跑暴露存量 flaky，按 R13 豁免流程逐条
  裁决（须理由+批准），**不得以 deselect/skip 方式把 DPAPI 或其他失败一并放行**；
- **required check 失配**：保名设计（gate job 名不变）+ upstream-ci required check 语义
  实证（job 级 check run 名匹配）双保险；首 PR 网页核验（验收标准）；若失配，
  ruleset 改名一处即修，workflow 不回滚；
- **runner 时长/成本**（评审 F-03 修正口径）：净增 = ① Windows test runner（定制套件
  <1 分钟，环境准备占大头，预估 3-5 分钟）+ ② 第二份 Linux 环境准备（govern 的
  checkout/setup-uv/setup-python/uv sync）+ ③ 轻量 ubuntu-slim gate；`.venv` 缓存与上游
  共享 key 抑制 Windows 侧；首 PR verification 记录各 job 实测时长（Windows 冷/热缓存）
  及是否超上游 ≈11 分钟瓶颈；`test`/`govern` 各保留 job 级 `timeout-minutes: 15`（沿用
  现值，不调大），gate 秒级 shell 判定不设；
- **govern 步骤迁移引入回归**：所有步骤命令逐字平移（不改参数），仅从单 job 拆出；
  本地治理四工具预跑配方在案（local-verify V2 终验步骤 4）；**有意接受的语义变化**
  （评审 F-02）：仓库 `tool.ruff.fix = true`（pyproject.toml:149），旧单 job 中 pytest
  运行于 ruff auto-fix 后的工作区，拆分后 `test` 在原始 checkout 上运行——CI 测试实际
  提交的树更合理，不为恢复旧行为串行化 job 或传递工作区 artifact；
- **回滚**：revert workflow 单提交即回到单 job 结构，分支保护零改（check 名全程未变）。

## ADR 判定

四问：①否决备选——上表已记（A/B/C + Q3 两决策点，预案 v2/v3 两轮评审收敛）；②撤销
代价——单 workflow 文件重构，revert 即回，低；③约束未来工作模式——"定制门平台矩阵 =
test/govern/gate 三层"为 CI 组织形态演进，由 DIRECTORY.md §7 承载；ADR-0004 预留条款
（"平台敏感测试验证后再扩矩阵"）兑现而非推翻，加修订注记即可；④依赖上游非公开接口——
无（标准 GitHub Actions 语义 + 上游 workflow 的公开做法参照）。结论：**不出 ADR**
（ADR-0004 修订注记 + DIRECTORY.md §7 更新承载；若责任人认为 job 结构三层化属 ADR 级，
可在签认意见中要求补出，实施前裁决）。

## 文档联动（本批交付物清单）

- DIRECTORY.md §7：单 Linux 表述更新（"初始单 Linux 平台…再扩矩阵"→ 已扩 Windows 三层
  结构实态）、workflow 步骤链描述同步（§7 表格 aixcoding-tests.yml 行）；
- ADR-0004：修订注记（预留平台条款兑现；job 组织三层化说明；"现行规则以 DIRECTORY.md
  §7 为准"既有口径不变）；
- 批次文档全套（requirements/design/test-plan/verification/self-review，本目录）。

## 草案评审处置记录（2026-11-01）

评审 AI：外部（责任人指定）；结论：三层结构成立，**无 blocker**，1 major + 2 minor；
责任人裁决"三条均按处置意见"全采纳。评审的两个关键事实断言已本地复核成立
（`pyproject.toml:123` addopts 无逐名输出、`:149` `tool.ruff.fix = true`）。

| Finding | 级别 | 处置 | 落点 |
|---|---|---|---|
| F-01 验收证据链缺口：pytest 配置（`-n 8 --strict-markers`）不逐名输出成功用例，"DPAPI 三用例逐项 passed"按现配置不可证；skip 基线是人工快照非机检 | major | `test` 两 OS 以 step env `PYTEST_ADDOPTS="-rA"` 注入 short summary（命令文本不变）；验收标准细化 nodeid 逐名为证（Windows 3 PASSED / Linux 3 SKIPPED / 两平台 catalog 2 SKIPPED + 总数）；skip 基线明确为**首 PR 一次性人工验收 + R13 纪律**，不做常驻 skip 审计（JUnit 比对机制负收益，不引入） | 方案概述 test 注释；requirements 目标节 skip 口径、验收标准第 2/4/5 条 |
| F-02 拆分后 pytest 不再运行于 ruff auto-fix 后的树（`fix=true`），"逐字平移行为不变"表述不完整 | minor | 风险节补"有意接受的语义变化"注记（CI 测实际提交的树更合理）；不串行化、不传 artifact | 风险节"govern 步骤迁移"条目 |
| F-03 成本口径漏项（还有第二份 Linux 环境准备 + gate runner）；timeout 迁移未明确 | minor | 成本改"净增三项"口径；首 PR verification 记各 job 实测时长；`test`/`govern` 各 15 分钟、gate 不设 | 风险节成本条目；方案概述注释 |

留档不阻塞：matrix 全 skipped 聚合值（假设 6，未来条件跳过引入时实验验证）。评审
"已检查无问题项"清单 17 项在案（三层结构取舍、替代形态排除、checkout SHA 一致性、
fail-closed 边界、`always()` 选择、共享缓存 key、py39/fetch_rg/prewarm 排除论证、
ADR 判定等全部背书现方案）；Q1–Q7 逐问作答原文由责任人留存（评审提示词见
temp/windows-matrix-review-prompt.md）。
