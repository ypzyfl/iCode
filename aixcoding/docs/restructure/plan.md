# 目录重组执行计划（restructure plan）——迁入考古参考

> **定位更新（2026-10-25）**：新分支 `main_aixcoding_cli`（上游 0.31.0 干净基线）已拉出，旧定制功能未带入——本文从"旧分支原地重组执行清单"转为**阶段三"旧功能迁入"的考古参考**（总路线见 `../ROADMAP.md`）。由此：
> - §1/§2 钉死的行号与文件位置基于旧分支 0.28.0 基线，**已随上游 0.28→0.31 漂移失效**：迁入定位一律以 `AIxCoding` 标记注释在旧分支考古、在新基线重新比对，不得照抄行号；
> - "原地迁移"语义变为"跨分支迁入"：各项"现状"指旧分支 `main_aixcoding_cli_0.28.0_final` 的落点；U1–U5 需按新分支现状逐条重核（如 U1 的 `packages` 在新分支已是 `["src/chrys"]`，或无需还原动作）；
> - §3 执行顺序、§4 验收清单仍有效，作为阶段三操作骨架；前置依赖为先完成 ROADMAP §2 阶段二（五项内容清单）。
> 目标：按 `DIRECTORY.md` 的蓝图重建定制专区。决策依据：`../standards/adr/`（0001–0005；0006 起与目录重组无关）。执行中若发现映射有误，先修本文再动代码。
> 方向确认（2026-10-23）：负责人知情确认 ADR-0002 方向反转（根 `aixcoding/` 退出 wheel、产品代码迁 `src/chrys/aixcoding/`、`packages` 还原 `["src/chrys"]`、含 P4/P5 上游 import 改动在内的 R2 报批范围）。2026-10-25 起按新分支重建路线执行（见 `../ROADMAP.md`）。
> 状态标记：`[ ]` 待办 / `[x]` 完成 / `[~]` 部分完成 / `[-]` 取消（注明原因）。

## 0. 前置事实（执行时核对）

- [x] git 核对上游基线的 `testpaths` 原值（2026-10-25 已核对：新分支与上游 `pyproject.toml` **全文零差异**——`version` 同为上游原值 `0.31.0`、fork 从未改动（首次比对时上游本地副本停在 0.30.1 故 diff 显示 version 一行，副本更新后复核为零差异）；`testpaths = ["tests"]` 一致——U1 之 `testpaths` 还原无动作）。
- [x] git 核对上游基线的 `[tool.hatch.build.targets.wheel]`（同次核对：上游本就有该段且同为 `packages = ["src/chrys"]`，`force-include` / `artifacts` 均系上游自带、非 fork 侧增量——U1 之 `packages` 还原无动作；U1 整体在新分支为无操作，阶段三启动时改记 `[-]` 即可）。
- [ ] **首批工具建设立项**（四个脚本，排入 §3 第 8 步显式里程碑，先于任何新功能开发）：① 定制清单生成脚本（扫描 `AIxCoding` 标记生成 `CUSTOMIZATIONS.md`，规范 §5/§8 依赖，当前不存在——验收第 8 项以其存在为前提）；② R2 diff 比对脚本（PR 改动的上游文件集 vs design.md 批准清单，ADR-0007）；③ R3 标记注释校验脚本（上游 diff 必须带 `AIxCoding` 注释，ADR-0007）；④ import 边界校验脚本（`aixcoding/` 禁 import `tests.support` 等 §9 边界）。防"文档先行、工具永远在后"：规范承诺的自动校验在脚本落地前处于人肉降级态，属临时状态。

> 注：前两项核对仅决定**还原参数**（还原成什么值/删段还是改值），不改变 ADR-0002/0003 的决策结论（单落点、mock_server 自建可删——后者经负责人确认）；若核对发现上游 wheel 配置存在其他 fork 侧增量（如 force-include 系我们添加），U1 审批范围相应更新后再执行。

## 1. 迁移映射（现状 → 目标）

### 1.1 产品代码 → `src/chrys/aixcoding/`

| # | 现状 | 目标 | 备注 |
|---|---|---|---|
| P1 | `src/chrys/aixcoding/`（telemetry + 根模块） | 原地不动 | 已是目标形态 |
| P2 | `aixcoding/auth/`（9 py） | `src/chrys/aixcoding/auth/` | import 改名 `aixcoding.auth` → `chrys.aixcoding.auth`：包内互引（`__init__/session/storage/client/environments` 等 8 文件）+ 下述全部消费方 |
| P3 | `aixcoding/tui/`（含 `login.tcss`） | `src/chrys/aixcoding/tui/` | 同上；`tui/login.py:34` 的 `aixcoding.auth` import 一并改 |
| P4 | **上游 src 树消费方**（2026-10-22 逐文件复核钉死，R2 范围）：`service/profiles/models/catalog.py`×2（459/488 运行时 import）+ **docstring 路径文字×3（76/82/84，R3/R8 口径同步）**、`service/llm/clients.py:148`、`app/tui/screens/main/screen.py`×5（145/991/2246/2253/2272）、`app/tui/screens/main/login_indicator.py`×2（14/15）、`app/tui/app.py`×2（153/1032；1050 行已是 `chrys.aixcoding.*` 目标形态无需动） | 原地改 import（+注释同步） | 均为既有定制点（带 `AIxCoding` 注释），跟随更新。~~commands.py~~ 复核剔除：该文件仅含文案字符串，无 Python import。**执行前仍重跑 `grep -rn "aixcoding\." src/ tests/` 终验防漂移** |
| P5 | **上游 tests 树消费方**：`tests/service/profiles/models/test_catalog_sync.py`（168-169）、`tests/app/tui/screens/main/test_login_indicator.py`（9-12） | 原地改 import 或随 U4 处理 | 与 U4 合并审批（同属上游 tests 树内的定制依赖） |
| P6 | **定制内部互引**：`src/chrys/aixcoding/telemetry/subscriber.py:189`、`src/chrys/aixcoding/context.py:125`（均 lazy import `aixcoding.auth`） | 原地改 import | 随 P2 一起改 |

### 1.2 测试 → `aixcoding/tests/`

| # | 现状 | 目标 | 备注 |
|---|---|---|---|
| T1 | `aixcoding/tests/`（6 测试 + conftest） | 原地保留 | conftest 增强：`sys.path` 注入仓库根（替代 telemetry-mock 目录注入）；更新 telemetry-mock 导入为 `aixcoding.mock.telemetry` 包路径 |
| T2 | `tests/app/aixcoding/`（11 文件） | `aixcoding/tests/`（按特性归组：`auth/`、`tui/` 等） | **上游 tests/ 树内删除，R2 报批**；`test_login_dialog.py` 的 `from tests.support.waiting import wait_until` 复制等价实现进本地 conftest/helper；其 conftest（TUI 主题变量 fixture）合并进 `aixcoding/tests/` |

### 1.3 mock → `aixcoding/mock/`

| # | 现状 | 目标 | 备注 |
|---|---|---|---|
| M1 | `mock_server/aixcoding_auth/` | `aixcoding/mock/auth/` | 无就地测试（测试在 T2） |
| M2 | `mock_server/aixcoding_update/` | `aixcoding/mock/update/` | `test_server.py` → `aixcoding/tests/mock/` |
| M3 | `mock_server/chrys_model_catalog/` | `aixcoding/mock/model_catalog/` | `conftest.py`（direct_route）+ `test_server.py` → `aixcoding/tests/mock/` |
| M4 | `aixcoding/telemetry-mock/` | `aixcoding/mock/telemetry/` | 补 `__init__.py` 与 `main()` CLI（双入口约定）；模块改包内相对导入 |
| M5 | `mock_server/`（整目录） | 删除 | **R2 报批**（含 `testpaths` 还原，见 U1） |
| M6 | `mock_server/README.md` 的规范内容 | `aixcoding/mock/README.md` | 注册表 + 新增 mock 步骤平移，路径/命名按新约定改写 |

### 1.4 根 `aixcoding/` 清理

| # | 现状 | 目标 | 备注 |
|---|---|---|---|
| R1 | `aixcoding/doc/`（**8 份历史文档，非空**：TUI登录改造方案、TUI登录执行计划、桌面端集成登录方案、桌面端集成登录开发计划、启动与登录人工验证指南、LLM模型对接获取说明、aixcoding_cli 发布 Releases 操作指南、项目索引） | 迁 `docs/` 按主题归位：登录系列 → `docs/<login-feature>/`（历史归档）；发布操作指南 → `docs/`（运维文档，`cd.yml` 配套）；LLM 对接说明、项目索引 → 按内容并档或随功能目录 | **有价值历史文档，禁止删除**；执行时责任人逐份定去向 |
| R2' | `aixcoding/__init__.py` | 保留，docstring 更新 | 语义改为开发资产命名空间锚点（不再进 wheel），见 DIRECTORY.md §4/§8 |

## 2. 上游文件改动清单（R2 报批，逐项列改动内容）

| # | 文件 | 改动 | 状态 |
|---|---|---|---|
| U1 | `pyproject.toml` | `packages` 还原 `["src/chrys"]`（删除 `"aixcoding"`）；`testpaths` 还原上游原值（删 `"mock_server"`）；per-file-ignores：`"aixcoding/tui/*"` → `"src/chrys/aixcoding/tui/*"`；`"mock_server/**/test_*.py"` → `"aixcoding/tests/**"` | 已核对（2026-10-25，见 §0）：新分支与上游零差异，还原部分无操作；per-file-ignores 改动在新分支不存在，转为阶段三迁入 tui/tests 时的**新增** R2 报批项 |
| U2 | `tests/architecture/test_layering.py` | DAG 细化：`chrys.aixcoding` 默认 tier 1，`chrys.aixcoding.tui` 单列 tier 4 侧；新增"DAG 豁免 ↔ 定制清单登记"一致性断言 | 待批 |
| U3 | `.github/workflows/aixcoding-tests.yml` | 新建（上游目录内新增文件，ADR-0004）：ruff check/format `aixcoding/` + `pytest aixcoding/tests`，触发对齐 ci.yml，初始单 Linux | 待批 |
| U4 | `tests/app/aixcoding/` 删除（11 文件）+ 上游 tests 树内定制依赖文件更新（P5 两文件） | 见 T2/P5 | 待批（T2/P5/U4 合并审批） |
| U5 | `mock_server/` 删除 | 见 M5 | 待批（可与 M5 合并审批） |

消费方接线点（P4）为既有定制点的更新，不新增审批范围。

## 3. 执行顺序（依赖关系）

1. **文档先行**（本文档组落地 = 本计划外的部分已完成）。
2. `aixcoding/mock/` 建立 + M1–M4 迁移 + T1 conftest 增强 → 验证：`pytest aixcoding/tests` 绿（telemetry 部分先行可跑）。
3. T2 迁移（R2 获批后）→ 验证：全部定制测试绿。
4. P2/P3 产品代码迁移 + P4 接线点更新 → 验证：ty 通过（预留修复窗口：auth/tui 首次进 ty 射程）、定制测试绿、Smart Test 传 `--paths`。
5. U1/U2（R2 获批后）→ 验证：`pytest tests/architecture` 绿（新 DAG 规则）、`uv build` 产物正确。
6. U3 新 workflow → 验证：CI 全绿。
7. M5/R1 收尾删除 → 全量验收（§4）。
8. **首批工具建设**（§0 立项四脚本：清单生成 / R2 比对 / R3 校验 / import 边界）→ 验收：脚本挂入 `aixcoding-tests.yml`（或本地强制自检步骤）并跑绿；在此之前不启动新功能开发——规范承诺的自动化校验不得长期处于人肉降级态。

## 4. 验收清单（全部通过 = 重组完成）

- [ ] **wheel 内容断言**：解包 wheel——`chrys/aixcoding/auth`、`chrys/aixcoding/tui` 在包内；根 `aixcoding` 资产（docs/tests/mock）不在包内。
- [ ] 定制测试全绿：`uv run --extra all pytest aixcoding/tests -m "not integration and not gc_calibration"`（含 mock 契约测试）。
- [ ] 上游架构测试绿：`uv run pytest tests/architecture`（含 layering 新规则与豁免一致性断言）。
- [ ] ty 三平台通过（auth/tui 新进射程的修复完成）。
- [ ] i18n `check` 绿且无 diff（无新增 `msg()`，ADR-0005 预期）。
- [ ] ruff check/format 通过（含 `aixcoding/` 新路径与修订后的 per-file-ignores）。
- [ ] 离线打包冒烟：`dist` 产物 `--version` 正常、登录对话框可打开并完成 mock 登录流程。
- [ ] `CUSTOMIZATIONS.md` 定制清单刷新（脚本扫描 + 本次 U1–U5 登记核对）。
- [ ] 本文 `plan.md` 状态全部勾选后，在文末记一行完成日期并归档（保留作历史）。

## 5. 挂起与备忘

- ty 修复窗口：auth/tui 从未被 ty 检查，迁入后爆错属预期，修复不扩权（不顺手重构）。
- CI 平台矩阵：初始单 Linux；tui（Textual）与 auth（OS 级加密后端）的平台敏感性由首轮 CI 结果决定是否扩。
- `aixcoding/tests/` 不加 `__init__.py`（pytest 无包收集模式）；`aixcoding/mock/` 全链路带 `__init__.py`（包导入）——见 DIRECTORY.md §4。
