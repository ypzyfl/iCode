# 测试方案：并行批次编号与文档热点治理（parallel-batch-governance）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

本批零上游源码、零产品运行时改动，不设上游行为锚定测试，不启动 mock server。采用四层验证：

1. **临时文档树单测**：以 `tmp_path` 构造 design、ADR、plan、marker 和豁免清单，注入格式错误、缺件、草案和引用断裂；不修改真实仓库文档。
2. **临时 Git 仓库演练**：验证 M0 合并、M1 确定性改号/差异证明和 M2 停等。Git 提交使用命令级 `-c user.name/-c user.email`，不改全局配置。
3. **真实仓库只读门禁**：运行 strict、check/docs 导航、ruff/format、静态引用与 Git 历史检查；所有只读工具验证前后工作树文件不变。
4. **PR 双 CI 与人工签认**：fork `aixcoding-tests.yml` 在 pull_request 执行 closure，上游 CI 保持不触碰；guard ADR/self-review 和本批 self-review 由责任人本人签认。

测试入口：

- 既有 `aixcoding/tests/tools/test_gen_customizations.py` 增补语义 ID、兼容和考古输出用例；
- 新增 `aixcoding/tests/tools/test_check_docs.py` 覆盖 ADR 双格式、closure、plan 和豁免清单；
- 新增 `aixcoding/tests/tools/test_parallel_batch_conflicts.py` 覆盖 M0/M1/M2 与 `check_id_only.py`；
- 新增 `aixcoding/tests/tools/test_docs_report.py` 覆盖批次目录导航边界；
- 根文档、规范、workflow 和 guard 最终形态用只读命令及 CI 核验，结果记入 verification.md。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口（文件::用例/命令） | 类型 |
|---|---|---|
| 新定制点/ADR 语义 ID 与文件名 | `test_gen_customizations.py::test_semantic_id_format_validation`；`test_check_docs.py::test_semantic_adr_filename_validation` | 单元 |
| 批次归属、全局唯一、旧 ID/区间/取代链兼容 | `test_gen_customizations.py::test_semantic_id_uniqueness_and_legacy_compatibility`；`test_check_docs.py::test_numeric_and_semantic_successors_remain_compatible` | 单元/契约 |
| 不同批次同局部 slug、M0 无共享冲突 | `test_parallel_batch_conflicts.py::test_parallel_branches_merge_without_coordination` | 临时 Git 端到端 |
| 语义孪生组计数及既有对账语义不回归 | `test_gen_customizations.py::test_semantic_twin_group_count` 及既有最长锚/孤儿/未签认/零写入用例 | 单元回归 |
| ADR 单池、guard 迁移、0023/0024 预留与引用更新 | `test_check_docs.py::test_adr_global_pool_and_location_validation`；guard 静态核验 | 单元/静态 |
| 数字/语义 ADR 双格式后继及错误注入 | `test_check_docs.py::test_adr_successor_error_injection` | 单元 |
| M1 确定性、占用集合、后缀分配、ID-only 证明与停等 | `test_parallel_batch_conflicts.py` 的 deterministic/allocation/diff/M2 用例组 | 单元/临时 Git 端到端 |
| docs_report 全目录、存量微改动、H1、确定性与零写入 | `test_docs_report.py` 全组 | 单元/契约 |
| INDEX 删除、README 双入口与无目录微改动边界 | `test_docs_report.py::test_non_batch_micro_records_are_out_of_scope`；README/文件存在性静态核验 | 单元/静态 |
| ROADMAP 物理删除且历史可从 Git 获取 | 文件存在性检查 + `git show <删除前revision>:aixcoding/docs/ROADMAP.md` | 静态/历史契约 |
| 现行引用清理、考古输出标签和批次授权资产不变 | `test_gen_customizations.py::test_archaeology_output_has_no_roadmap_dependency`；引用扫描 + strict | 单元/静态回归 |
| ADR-0015/0016 修订范围不扩散 | ADR/规范静态核验；既有 strict 与 check_docs 回归 | 静态/契约 |
| closure 草案、六件、ADR 引用、plan 最小形态与 PR 触发 | `test_check_docs.py` 全组；workflow 静态核验 + pull_request CI | 单元/端到端 |
| 豁免清单、微改动增量分流、R13/评审模板 | `test_check_docs.py` 的 exemption/micro 用例；规范静态核验 | 单元/静态 |
| guard 修复、真实补签与历史事实更正 | guard 文件/引用/签认字段静态核验 + 最终 closure | 静态/人工签认/闭环 |
| 新测试使用行为名，不批量改旧测试 | 本批测试文件名/用例名评审；`git diff --stat` 检查无批量重命名 | 静态 |
| 全部质量门与 PR 双 CI | 本文“执行顺序与验证命令” | 综合 |

## 关键用例设计

### 1. 定制点 ID 与既有对账

在 `test_gen_customizations.py` 增加：

- 合法：`batch-a:foo`、`batch-b:foo` 可同时存在；批次前缀必须等于 design 所在目录；report 紧凑展示完整 ID。
- 非法：大写、下划线、冒号缺失/多个冒号、空 slug、错误批次前缀均报错；`legacy-` 前缀仅接受 M1 保留字 `legacy-c###`（可带 `-m1-N`），其他人工新登记形态报错。
- 唯一性：active/active、active/retired 的完整 ID 重复均报错；旧 `C###`、旧区间和 tombstone 原样通过。
- 孪生组：一个语义组 ID + 计数 2 接受两个 marker；计数 1/3 报错；旧区间仍按区间成员数校验。
- 回归：既有最长锚优先、无登记 marker、孤儿登记、未签认 design、零写入用例全部保留并通过。
- 考古输出：docstring 与报告标题不再含“ROADMAP §4 输入”，report/check 行为及退出码不变。

### 2. ADR 双格式与引用闭环

在 `test_check_docs.py` 使用可注入的临时 docs root 覆盖：

- 新语义 ADR 文件名/H1/批次前缀正确时通过；文件名与 H1 不符、批次目录不存在、完整 ID 重复、`batches/*/adr/` 位置错误均失败。
- 旧数字后继继续解析到四位数字文件；新语义后继解析到完整语义文件名；缺失后继报错。
- 精确 `ADR-NNNN` 与 `ADR-<batch>--<decision>` 引用：已确认/被取代目标通过，缺失或草案目标失败；templates 与占位文本不误报。
- 默认模式仍允许草案；closure 对 ADR、design、self-review 草案分别报错。

### 3. M0/M1/M2 与 check_id_only

在 `test_parallel_batch_conflicts.py` 覆盖：

- **M0**：共同基线拉出两个分支，各自新增独立批次目录、相同局部 point/decision-slug 和独立 marker；合并没有 INDEX/ROADMAP/编号冲突，strict 与 ADR 校验通过。
- **旧单 ID**：`C145` 映射为 `<batch>:legacy-c145`；`0001-*.md` 映射为 `<batch>--legacy-adr-0001.md` 和对应完整 ADR ID。
- **同批重复**：两条不同落点/锚的 `foo` 按 design 物理位置依次得到 `foo`、`foo-m1-2`；ADR 按旧 POSIX 路径排序。
- **占用集合**：已合并侧同值 ID 不随待修复条目被剔除；首选及 `-m1-<n>` 被占用时，从 occurrence index 起取首个空闲后缀。
- **确定性**：改变 fixture 创建顺序并重复运行两次，映射及规范化输出逐字节相同。
- **合法 ID-only**：只改声明的 ID/路径和唯一归属引用时通过；工具不创建、删除或改写工作树文件（不含 `.git` 内部状态）。
- **语义差异注入**：分别改变落点、锚、计数、anchor、risk、removal_condition、R2、ADR 决策节、范围外文件和无关正文，均非零退出。
- **停等**：旧区间/孪生组、歧义引用、清单外引用、完整 `(落点, 锚)` 重复、R2 或 ADR 决策分歧均 fail-closed，不得靠改 ID 通过。

### 4. docs_report 导航

在 `test_docs_report.py` 覆盖：

- 自动发现全部一级目录并按目录名排序；新增目录无需登记即出现。
- requirements → design → plan 的 H1 回退顺序正确；封闭清单形态的存量目录只有 plan 时可导航。
- 非 batches 的 micro 记录不进入输出；输出明确“批次目录全景”，不包含无目录微改动数量或分类。
- 两次运行输出一致，运行前后文件树快照一致，不生成 INDEX 或其他文件。
- 目录无 requirements/design/plan、H1 缺失、文件不可读/非 UTF-8 时警告明确且退出非零。

### 5. closure、plan 与豁免清单

在 `test_check_docs.py` 参数化覆盖：

- 六个必备文件分别缺失均报错；新增缺件微改动目录报错；无目录微改动 fixture 不触发六件门禁。
- plan 仅在“任务/状态”表且状态为 `完成`、`完成（...）`、`完成(...)` 时解析；token 可位于任务或状态单元格。
- 对应文件缺失、空文件、仅 H1、非 UTF-8 均失败；self-review 草案失败，verification 不新增签认义务。
- `未完成`、`完成前`、`完成度`、自由 prose、跨行、`verification-report`、`self-review-helper` 不按完成状态误报；合法完成状态与最小文件通过。
- 当前 TOML 精确覆盖的存量缺失可豁免；清单外缺失、stale 豁免及未经批准的新增/扩大注入失败；补齐文件并删除豁免后通过。
- 最终 fixture 中 guard-switches 不命中任何豁免；微改动无目录/有目录六件两条路径分别通过，新增缺件目录失败。

## 异常与降级路径

- 所有解析工具对非法 ID、错误批次、缺失/不可读文件和歧义映射均 fail-closed，不静默跳过。
- docs_report 的“无目录微改动排除”是已接受边界，不作为错误；有目录但无可用导航源才报警。
- check_id_only 无法证明语义不变时只读停等，不自动修复、不写文件、不扩大授权。
- guard 修复前运行真实 closure 只允许用于诊断，预期至少命中 guard 未签/缺件及本批尚未完成的 verification/self-review；不得记录为最终验证通过。
- 无网络、GitHub API 或 PR 描述解析依赖；GitHub merged PR 视图仅作为人工查询入口。

## 执行顺序与验证命令

1. 先运行四个工具测试入口，再运行静态检查；随后实施并完成 guard 修复及责任人签认。
2. 补齐本批 verification/self-review 并完成签认后，才执行最终 closure 和综合质量门。
3. 结果逐条记入 verification.md，注明套件、数量、退出码和任何环境性限制。

```text
uv run pytest aixcoding/tests/tools/test_gen_customizations.py -n 0
uv run pytest aixcoding/tests/tools/test_check_docs.py -n 0
uv run pytest aixcoding/tests/tools/test_parallel_batch_conflicts.py -n 0
uv run pytest aixcoding/tests/tools/test_docs_report.py -n 0

uv run python aixcoding/tools/gen_customizations.py --strict
uv run python aixcoding/tools/docs_report.py
uv run python aixcoding/tools/check_docs.py
uv run python aixcoding/tools/check_docs.py --closure

uv run ruff format --check aixcoding/
uv run ruff check --no-fix aixcoding/
uv run python scripts/chrys_test.py --smart --paths <本批全部变更文件，含删除路径>
git diff --check
```

最终静态核验：

- `aixcoding/docs/INDEX.md`、`aixcoding/docs/ROADMAP.md` 均不存在，无重定向/占位/生成式替代文件。
- README 两个全景命令相邻，含 GitHub merged PR 边界说明；现行规范和 UPGRADE-RUNBOOK 不再依赖 INDEX/ROADMAP。
- `git show <删除前revision>:aixcoding/docs/INDEX.md` 与对应 ROADMAP 路径可读。
- guard 新 ADR-0023 已确认且日期为实际补签日；3 个文件旧引用和 ADR 自身 H1 全部更新，self-review/verification 如实记录补做历史。
- `.github/workflows/aixcoding-tests.yml` 的 pull_request 与主干 push 均执行 closure；上游 `ci.yml`、`src/chrys/`、上游 `tests/`、`AGENTS.md` 零改动。
- PR 的 AIxCoding Tests 与 Upstream CI 双绿。

## 覆盖边界

不测试无目录微改动总数、PR 描述自然语言分类或 plan 自由文本真实性——均为 design 明确排除的范围。除此之外，requirements.md 第 50–66 行验收标准均有上表对应入口，无已接受的覆盖缺口。