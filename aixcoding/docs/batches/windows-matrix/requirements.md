# 需求：定制测试 Windows 矩阵（windows-matrix）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
> 修订记录：2026-11-01 立项起草（预案 v3 自 temp/2026-11-01-custom-test-strategy/10 号迁入
> 工程，按仓库规范走完整管线）；同日外部 AI 评审处置（F-01/F-02/F-03 均按处置意见采纳，
> 明细见 design.md 末节）——skip 基线口径明确、验收标准第 2/4/5 条细化。

## 背景与问题

定制质量门 `.github/workflows/aixcoding-tests.yml` 仅 `ubuntu-latest` 单平台，产生已核实的
平台空洞：

- `aixcoding/tests/auth/test_auth_crypto.py` 的 `TestWindowsDPAPI`（2 用例）与
  `test_real_windows_probe_returns_dpapi` 均
  `skipif(sys.platform != "win32")`——含真实 DPAPI round-trip 与 label 校验，
  **在 Linux CI 上永久 skip，从未在 CI 执行**（2026-11-01 本机前置验证三用例逐项 passed，
  但 CI 无守卫）；
- macOS `MacOSSecurity` 仅 monkeypatch `subprocess.run` 验证 CLI 参数（非真实 Keychain），
  平台无关、两 OS 均可跑；
- 后果：Windows 凭据后端损坏时，PR 的两个 CI 门（定制门 + 上游桥接门）可同时通过。

ADR-0004 预留路径："初始单 Linux 平台（定制测试大多平台无关），平台敏感测试验证后再扩
矩阵"——本批即该条款的兑现。

## 目标与非目标

- 目标：
  - `aixcoding-tests.yml` 由单 `gate` job 重构为三层结构（与上游桥接门
    `aixcoding-upstream-ci.yml` 的 filter/ci/gate 模式同构）：
    - `test`：`ubuntu-latest` + `windows-latest` 矩阵，只跑定制测试套件（pytest 命令与
      现门逐字相同）；
    - `govern`：单 Linux，跑全部治理步骤（ruff×2、check_docs、check_import_boundaries、
      gen_customizations --strict、R2/R3）；
    - `gate`：保名 `AIxCoding quality gate`（required check 落点不变），
      `needs: [test, govern]` + `if: always()`，两者都 success 才通过（fail-closed）；
  - Windows shard 实际执行 DPAPI 三真实用例（逐项 passed，非 collected/skipped）；
  - Windows 步骤适配对齐上游 `ci.yml` `test_windows` 既有做法（TEMP/TMP 重定向 D: 盘、
    `.venv` actions/cache）；`py39` install 与 `fetch_rg` 经复核不需要（定制测试零引用）；
  - skip 基线清单落 verification：平台互斥项（Linux 侧 DPAPI 三项）与平台无关项
    （catalog consumer 两项 auto-skip）分列——**首 PR 一次性人工验收口径 + R13 流程
    纪律**（新增 skip 未经批准不得出现），不做常驻 skip 审计机检（评审 F-01③：为
    29 文件小套件引入 JUnit 比对机制属负收益）。
- 非目标：
  - 不加 macOS 矩阵（无已写好的真实 Keychain 测试，仅 CLI 参数 mock，加矩阵只多验平台
    无关路径，收益成本比低——预案 v2 改写理由）；
  - 不改任何测试内容、不新增测试（只改执行平台与 job 组织）；
  - 不动 `aixcoding-upstream-ci.yml` 与上游 `ci.yml`；
  - 不做组合测试（P1-4 批次）；
  - 不加 doc-only 跳过逻辑（定制门全套 <1 分钟，无成本痛点；上游桥接门已有该机制）。

## 用户场景

1. **Windows 凭据后端变更**：改 `src/chrys/*/aixcoding/auth/**`（DPAPI 路径）后开 PR——
   Windows shard 实际执行真实 round-trip，凭据路径损坏即红，平台空洞关闭；
2. **平台无关回归**：定制产品代码/测试改动——双 OS 矩阵并行执行同一套件，任一平台失败
   gate 红（与上游门"验收口径统一"互补）。

## 验收标准

- [ ] workflow 三层结构落盘：`test`（matrix `ubuntu-latest`/`windows-latest`，
      `fail-fast: false`）、`govern`（单 Linux，治理全步骤，`fetch-depth: 0`）、`gate`
      （`needs: [test, govern]`，`if: always()`，双 success fail-closed 判定，name 保持
      `AIxCoding quality gate`）；
- [ ] `test` job 的 pytest 命令与现门逐字相同：
      `uv run pytest aixcoding/tests -m "not integration and not gc_calibration"`（两 OS
      同构，便于对照）；另经 step env `PYTEST_ADDOPTS: "-rA"` 注入 short summary（命令
      文本不变；评审 F-01：使成功/skip 用例逐名可证）；
- [ ] Windows 步骤适配对齐上游：TEMP/TMP 重定向（checkout 前）、`.venv`
      `actions/cache`（pin v6.1.0，key 与上游 `venv-${{ runner.os }}-...` 同构共享）；
      不含 py39 install / fetch_rg / prewarm（design 论证）；
- [ ] 首 PR CI 实证（以 `-rA` short summary 的完整 nodeid 逐名为证）：Windows shard
      DPAPI 三用例 **PASSED**；Linux shard DPAPI 三项 **SKIPPED**（平台互斥，预期）；
- [ ] skip 基线清单逐项一致（首 PR verification 记录，一次性人工验收）：Linux=DPAPI 3
      SKIPPED；两平台=catalog consumer 2 SKIPPED；两平台 collected/passed/skipped 总数
      记录在案；无未批准的新增 skip（R13 口径）；
- [ ] gate check run 名与分支保护 required check `AIxCoding quality gate` 匹配（首 PR
      网页核验，责任人配合；保名设计下理论零改）；
- [ ] 上游零文件改动（R2 清单空——`aixcoding-tests.yml` 为 fork 专属文件）；
- [ ] 文档联动：DIRECTORY.md §7（单 Linux 表述与 workflow 步骤链更新）、ADR-0004 修订
      注记（预留条款兑现）。

## 开放问题

- Q3-a（design 决策点，预案留立项定）：ruff 归 `govern` 层（推荐）还是留 Linux `test`
  一份；
- Q3-b（design 决策点）：gate fail-closed 判定实现（推荐 env + `test "$X" = "success"`
  双断言，对齐 upstream gate 先例）；
- required checks 核验（责任人网页操作项，非本批代码交付物）：gate 名不变则 ruleset
  理论零改，仍需首 PR 实证（temp 材料 40 号指引）。
