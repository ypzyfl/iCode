# 测试方案：docs 目录分层组织（docs-reorg）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

本批次零产品运行时行为变更、零上游文件接触，测试重心两层：

1. **单元层**（`aixcoding/tests/tools/`）：治理工具在新布局下的扫描行为——既有夹具
   （`test_gen_customizations.py` 31 处 demo、`test_check_r2_diff.py:38,46`、
   `test__common.py`）路径同步 `batches/` 布局；**新增布局用例**锁
   `find_design_docs` 的"仅扫 `batches/*/design.md`"契约；
2. **手工验证层**（本节 H1–H6，结果记入 verification.md）：四工具全量、R2 审批池
   前后等价、全仓复扫零命中、测试套件、INDEX 完整性——verification 的主体证据。

无上游 anchor、无 mock 需求。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| 1. 顶层仅 `standards/`+`batches/`，18 目录平铺 | 手工 H1（结构断言） | 手工 |
| 2. 四工具本地全绿 | 手工 H2 | 手工 |
| 3. R2 审批池等价（前后集合逐字一致） | 手工 H3（迁移前快照 → 迁移后 diff 为空） | 手工 |
| 4. aixcoding 测试套件全绿（夹具同步） | `aixcoding/tests/tools/`（改造夹具全量）+ 手工 H6 | 单元+手工 |
| 5. 复扫旧路径零命中（两种斜杠形式 + 仓外） | 手工 H4 | 手工 |
| 6. INDEX.md 落地（18 条目 + 链接有效） | 手工 H5 | 手工 |
| 7. CI 全绿 | PR 触发 `aixcoding-tests.yml` + 上游桥接（端到端，合并前证据） | 端到端 |
| （design §4.2）`find_design_docs` 仅扫 batches 一层 | `test__common.py::test_find_design_docs_batches_layout`（**新增**） | 单元 |

新增布局用例设计：tmp 仓库夹具同时建 `aixcoding/docs/batches/demo/design.md`（有效）与
`aixcoding/docs/topdemo/design.md`（顶层假目录），断言 `find_design_docs` 仅返回前者——
锁"精确单层、不递归"契约，防止未来误改回递归或顶层扫描。

## 异常与降级路径

- **中间态红提交**：由 §4.2 原子性纪律保障（单提交），不做测试自动化；本地验证固定
  在 mv/工具/引用三者齐变后一次运行；
- **工具漏扫**：布局用例锁行为 + `gen_customizations.py --strict` 对账兜底（漏扫即
  孤儿 marker → 红，C001 场景实证）；
- **复扫白名单外命中**：一律视为断链，逐处清零后复跑 H4 至零命中。

## 手工验证步骤（若需）

结果（命令 + 输出摘要）记入 verification.md：

- **H1 结构**：`ls aixcoding/docs`（预期仅 `standards`、`batches`、`INDEX.md`、
  `ROADMAP.md`、`versioning.md` + 本批次随迁）+ `ls aixcoding/docs/batches`
  （预期 18 目录平铺、无中间层）；
- **H2 四工具**：`uv run python aixcoding/tools/check_docs.py`、
  `uv run python aixcoding/tools/gen_customizations.py --strict`、
  `uv run python aixcoding/tools/check_r2_diff.py`、
  `uv run python aixcoding/tools/check_r3_markers.py`（各自 OK / 29 点对账）；
- **H3 R2 池等价**：**迁移前**先以与 `check_r2_diff.py:52` 相同调用方式
  （`_common.r2_approved_upstream_files(Path("aixcoding/docs"))`）输出 approved 集合
  保存临时文件；**迁移后**同命令重跑并 diff——必须为空（含 `AGENTS.md`）；
- **H4 复扫**：对 18 个目录名 × 两种形式
  （`aixcoding/docs/<name>/`、`aixcoding/docs/<name>`）全仓 rg（含 `.github`、
  `src`、`aixcoding`、`AGENTS.md`），豁免仅 `batches/devtools/archaeology-report-0.28.0.md`
  （其内容为上游文档引用文本）；另对 `temp/aixcoding-todos/` 整目录复扫——预期均零命中；
- **H5 INDEX**：条目计数 = 18，目录列链接逐条抽查可达；
- **H6 测试套件**：`uv run pytest aixcoding/tests`（本地配方：清 PYTHONPATH、
  PYTHONUTF8=1、大写盘符）全绿。
