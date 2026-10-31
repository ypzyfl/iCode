# 验证记录：docs 目录分层组织（docs-reorg）

> **副作用披露（design §4.3-G② 披露义务）**：本批次对既有文档（含 verification/变更记录
> 等历史叙述）中的路径做了**纯前缀机械替换**（`aixcoding/docs/<name>` →
> `aixcoding/docs/batches/<name>`，脚本执行 + git diff 逐处仅前缀变化核验）——历史文档
> 中呈现的新路径**不代表当时在新路径执行/验证**，迁移前原貌以 git tag `docs-pre-reorg`
> 为锚点溯源（`git show docs-pre-reorg:<path>` / `git diff docs-pre-reorg..HEAD -- aixcoding/docs`）。

## 实施摘要（2026-10-31，分支 feat/docs-reorg，基线 f9850c87）

- 目录迁移：`git mv` ×17（已跟踪）+ move ×1（本批次草案目录未跟踪）→ `aixcoding/docs/batches/`；
- 工具改造：`_common.py` glob 前缀平移（`batches/*/design.md`）+ MARKER_EXEMPTIONS 依据 ×4 + 帮助文本 ×5 文件；
- 引用替换：脚本纯前缀替换 **45 处/35 文件**（仓内 18 名单模式）+ 短形式 `docs/<name>/` ×18 + 裸名 `<name>/<doc>.md` **×85/35 文件**（评审 F5 处置扩展：裸名形态全量补扫）+ ROADMAP 裸名 ×9 + CI 注释 ×3 + 夹具 ×33（字符串型）+ 链式路径构造 ×3 + 相对链接加深 ×5（batches/restructure/plan.md 4+1）+ 仓外待办 ×9；
- 新增：`INDEX.md`（18 条目纯静态导航）、`standards/adr/0016`（草案）；
- 规范修订：`DEVELOPMENT.md` §6（落点/ADR 分池/INDEX 登记钩子）、`DIRECTORY.md`（:7 链接/目录树/判定树/:117/:139/命名表）；
- 评审处置（三轮）：① Kimi-K3.1-Pro 全量评审（2026-10-31）：F2 README 两处语义修订经责任人追认纳入；F3 布局用例增强（嵌套诱饵反递归 + 空集/缺目录断言，+2 用例）；F4 INDEX auth 路径改 kernel 档；F5 规范两处 + 裸名形态全量 85 处 + 复扫 pattern 纳入裸名形态；F6 "关键验证复现命令"节补齐；F7 requirements 删虚构维度半句；F1 ADR-0016 签认待责任人；② Kimi-K3.1-Pro 增量复审（2026-11-01）：一轮修复全过，F8 裸名通配 ×4、F9 H4 口径当日修复（责任人裁决免第三轮机器复审）；③ Deepseek-V4-Pro 全量评审（2026-11-01）：无 blocker，F1'/F2' 相对链接深度 ×2 修复（勘误见下），F3' self-review 签认提 PR 前完成；
- 勘误记录（三轮 F1'/F2'，R7 留档）：`batches/restructure/plan.md:10` 的 standards 相对链接应为 `../../standards/adr/`——实施脚本"加深一层"时误写 `../../../`（三层，design §4.3-G④ 预扫记录同源笔误，design 已签认正文不改、以本勘误为准）；`standards/DIRECTORY.md:7` 原文 `../../restructure/plan.md` 系**存量断链**（standards/ 一层即达 docs/），本批次机械沿用未察觉，随批修正为 `../batches/restructure/plan.md`（失效链接原地修正范畴）。

## 门禁结果

| 验证项（test-plan H1–H6 + ruff） | 结果 | 摘要 |
|---|---|---|
| H1 顶层结构 | ✅ | `aixcoding/docs/` 顶层 = `batches/`、`standards/`、`INDEX.md`、`ROADMAP.md`、`versioning.md`；`batches/` 下 18 目录平铺 |
| H2 `check_docs.py` | ✅ | 16 ADR / 17 design / 14 self-review，OK（ADR-0016 草案被接受） |
| H2 `gen_customizations.py --strict` | ✅ | **25 登记行 / 29 marker / 6 design，0 warning**（登记对账：C001–C029 全覆盖） |
| H2 `check_r2_diff.py --base c54b60cf` | ✅ | changed=221 / upstream_changed=21 / **approved_pool=25**，OK（AGENTS.md changed & approved——C001 生效） |
| H2 `check_r3_markers.py --base c54b60cf` | ✅ | marker_checked=17 / exempt=4，OK（豁免依据路径已更新生效） |
| H3 R2 审批池等价 | ✅ | 迁移前后 `r2_approved_upstream_files()` 输出快照 `fc` 对比：**no differences**（25 文件逐字一致，含 AGENTS.md） |
| H4 全仓复扫 | ✅ | 四形态（全前缀/短形式/裸名/通配）× 18 名单 × 词边界，仓内 + 仓外 `temp/aixcoding-todos/` **零命中**；白名单：archaeology-report（上游引用文本快照）+ tier-migration/test-plan:23 测试目录通配语境 + 本文件 :28/:42 pattern 文档化行自引用 |
| H5 INDEX.md | ✅ | 18 条目（目录/类型/一句话简介），目录列相对链接目标均存在 |
| H6 `pytest aixcoding/tests` | ✅ | **320 passed / 2 skipped**（`-n 8`）；1 失败 = `test_update_server.py::test_post_reset...` WinError 10053（本机软件中止 loopback 连接，环境性），**单独复跑 `-n0` PASSED（0.17s）在案** |
| ruff check aixcoding/ | ✅ | All checks passed |
| ruff format --check aixcoding/ | ✅ | 177 files formatted-clean（夹具链式路径加长 2 行定向 format 后复验） |
| 新增布局用例 | ✅ | `test__common.py::TestFindDesignDocs::test_batches_layout_only`（batches 内被扫/顶层不被扫），随套件绿 |
| CI（PR 双门禁） | 待 PR | aixcoding-tests.yml + 上游桥接，push 后以 Actions 结果为准 |

## 关键验证复现命令（R7；本地配方 `set PYTHONPATH=` + `set PYTHONUTF8=1` + 大写盘符）

- **H1 结构**：`dir /b aixcoding\docs` → `batches`、`INDEX.md`、`ROADMAP.md`、`standards`、`versioning.md`；`dir /b aixcoding\docs\batches` → 18 个目录名、无中间层。
- **H3 R2 池快照**（迁移前后各执行一次，输出存 `temp/docs-reorg-r2-pool-{before,after}.txt`）：
  `uv run python -c "import sys; sys.path.insert(0, 'aixcoding/tools'); from pathlib import Path; import _common; a, n = _common.r2_approved_upstream_files(Path('aixcoding/docs')); print('APPROVED (%d):' % len(a)); print('\n'.join(sorted(a))); print('NOTES (%d):' % len(n)); print('\n'.join(n))"`
  对比：`fc temp\docs-reorg-r2-pool-before.txt temp\docs-reorg-r2-pool-after.txt` → `FC: no differences encountered.`
- **H4 复扫**（四形态逐行扫描 `aixcoding/`、`src/`、`.github/`、`tests/`、`scripts/`、`AGENTS.md` + 仓外 `temp/aixcoding-todos/`；白名单豁免 `batches/devtools/archaeology-report-0.28.0.md` 与 `batches/tier-migration/test-plan.md:23`（`aixcoding/tests/auth/* + diagnostics/*` 系测试目录通配语境）；18 目录名清单见 design §4.1）：
  正则四 pattern——全前缀 `aixcoding/docs/(名)(?![\w-])`、短形式 `(?<![\w/.-])docs/(名)(?![\w-])`、裸名 `(?<![/\w-])(名)/(design|requirements|test-plan|plan|verification|self-review|archaeology-report)`、通配 `(?<![/\w-])(名)/\*`；执行方式 python 脚本逐行 match（rg 无 PCRE2 lookahead 时用 python `-c`），输出 `RESCAN: 0 hit(s)`。
- **H5 INDEX**：`findstr /c:"| [batches/" aixcoding\docs\INDEX.md` → 18 行；链接列 `batches/<name>/` 目标存在性由 H1 的目录清单一一对照。

## 环境性失败记录

- `aixcoding/tests/mock/test_update_server.py::test_post_reset_restores_defaults_and_empties_log`：
  并行满载（`-n 8`）下 `ConnectionAbortedError [WinError 10053]`（主机软件中止 loopback HTTP），
  单独复跑 PASSED——与本批次改动面（docs 目录/工具 glob/文档引用）无交集，环境偶发在案
  （同族先例：mock 7777/7778 端口环境项）。
