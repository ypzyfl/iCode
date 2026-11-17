# 验证记录：后端同步模型与自定义模型共存

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

（实现完成后逐次追加验证记录。）

## 2026-11-17 实现后全量验证（Smart Test + 定制套件 + 门禁）

命令：

```
uv run python aixcoding/tools/verify.py --smart --paths src/chrys/service/aixcoding/models/catalog.py aixcoding/tests/catalog/test_catalog_sync.py
```

结果：`Summary: PASSED (exit 0)`——上游 Smart Test **13812 passed / 17 skipped**
（18:50），architecture **323 passed**（02:49），定制套件 **829 passed / 47 skipped**
（19:24，与 design 预期计数一致：catalog 84 + mock 25 等全量定制测试）。

命令：

```
uv run ruff check src/ tests/ scripts/... hatch_build.py scripts/i18n_mo.py
uv run ruff format --check src/ tests/ scripts/... hatch_build.py scripts/i18n_mo.py
uv run python aixcoding/tools/gen_customizations.py --strict
uv run ty check --error-on-warning --python-platform {linux,darwin,win32} src/chrys
```

结果：ruff check `All checks passed!`；format `2757 files already formatted`；
`gen_customizations: check OK — 116 registration row(s) / 161 marker(s) across
19 design(s), 7 retired id(s), 0 warning(s)`（零登记增量，符合 design「不适用」
判定）；ty 三平台 `All checks passed!`。

命令：

```
uv run python aixcoding/tools/check_docs.py --closure
```

结果：**1 error——预期失败**：`self-review.md: draft decision/review document is
forbidden by closure`。self-review 尚处草案（双 AI 评审未启动、责任人未签认），
按流程顺序该门禁在评审轮完成并签认后转绿；非本批实现缺陷。

> 勘误（同日）：评审轮启动后该输出已过时——现行报错为
> `self-review.md: status 已确认 but 责任人 is empty`（评审 AI 追加记录时
> 状态先行置位、责任人栏待本人补填，见评审 blocker B4）。

## 2026-11-17 评审修复轮验证（B1/B2/B3 修复 + S2/S5 处置）

命令：

```
uv run pytest aixcoding/tests/catalog -m "not integration and not gc_calibration" -q
uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
uv run ruff check src/chrys/service/aixcoding/models/catalog.py aixcoding/tests/catalog/test_catalog_sync.py
uv run ruff format --check src/chrys/service/aixcoding/models/catalog.py aixcoding/tests/catalog/test_catalog_sync.py
uv run ty check --error-on-warning --python-platform linux src/chrys
```

结果：catalog 套件 **113 passed**（含新增
`test_foreign_encoded_file_stays_decidable_and_clear_proceeds`（B1，GBK 编码
文件可判定、升级清空收敛）与 `test_same_stem_yml_is_a_distinct_file_the_sync_
never_touches`（B2））；全量定制套件 **831 passed / 47 skipped**（+2）；ruff
双检全绿；ty 全绿。

修复内容对照：

- **B1**：探针改 `decode_bytes(read_bytes(), errors="strict")` 与 loader 同路径；
  探针失败记 detail 日志；升级清空被否决时记原因日志。
  `test_all_malformed_directory_is_not_cleared` 增补否决日志断言（非 vacuous）。
- **B2**：覆盖/保留判定从 stem 改为**完整文件名**（覆盖对象 = `<id>.yaml`）；
  同 stem `.yml` 归保留，内存可见性由 `_publish` 显式 id 过滤兜底。
- **B3**：模块 docstring 与 `apply_catalog` docstring 对齐标记共存语义（R8）。
- **S2**：`test_fingerprint_ignores_custom_profiles` 改为重算期望摘要的
  非 vacuous 断言（实现扩大 hash 输入域即红）。
- **S5**：requirements 场景 1 措辞对齐「可见、可选中（TUI 恒只读）」。
- **S1（留档）/ S3（不修留档）/ S4（申报）**：见 design 风险节对应条目。
- **B4**：self-review.md 头部责任人/确认日期待责任人本人补填（AI 不代填）；
  design.md 因 B1/B2 语义修正须责任人重新签认。

## 2026-11-17 三平台文件操作审计与 S6 修复验证

命令：

```
uv run pytest aixcoding/tests/catalog -m "not integration and not gc_calibration" -q
uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
uv run ruff check / ruff format --check（两文件）
uv run ty check --error-on-warning --python-platform {linux,darwin,win32} src/chrys
```

结果：catalog **114 passed**；全量定制 **832 passed / 47 skipped**（+1）；ruff
双检全绿；ty 三平台全绿。

审计结论：所有 `write_text/read_text` 显式 utf-8、`decode_bytes` 纯 Python 探测、
`os.replace` 同卷原子（POSIX rename / Windows MoveFileEx）、tmp 后缀不匹配任何
glob、OSError 失败通道覆盖 Windows 文件锁——三平台均无 locale/平台依赖。

**S6（Windows 大小写边缘，已修）**：`pathlib.glob` 在 Windows 大小写不敏感，
用户 `A.YAML`（无标记）会被判「保留」而 `os.replace("a.yaml")` 实际覆盖之——
一轮内存/磁盘分歧。修复：覆盖/保留判定与陈旧删除的比较经 `os.path.normcase`
（POSIX 恒等、Windows 小写化），口径随平台对齐真实覆盖对象。测试
`test_extension_case_matches_the_platforms_replace_semantics` 按「glob 敏感性 ×
文件系统敏感性」分支断言统一不变量（内存恒与磁盘一致）；实测发现 macOS 默认
APFS 为大小写不敏感 FS（glob 敏感 + FS 不敏感 → 文件不进扫描、被静默覆盖、
内存一致，与基线不可见行为同款，接受），已写入 design S6 注记。

## 2026-11-17 第 2 轮评审修复验证（B5 + r1/r2/r4，r3 留档）

命令：

```
uv run pytest aixcoding/tests/catalog -m "not integration and not gc_calibration" -q
uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q
uv run ruff check / ruff format --check（两文件）
uv run ty check --error-on-warning --python-platform win32 src/chrys
uv run python aixcoding/tools/check_docs.py --closure
```

结果：catalog **115 passed**；全量定制 **833 passed / 47 skipped**（+1）；ruff
双检全绿；ty win32 全绿；`check_docs --closure` **OK**（B4 闭环后持续绿）。

修复内容对照：

- **B5（复审新 blocker）**：升级清空循环的文件名比较补 `os.path.normcase`
  ——S6 只迁了判定与陈旧删除两处，漏了第三处删除点。Windows 上 `A.YAML` 已被
  `os.replace` 覆盖成后端版本，原名比较会漏配并 unlink 刚发布的后端 profile
  （日志还记「已清空 1 个」）。新增
  `test_upgrade_clear_skips_case_variant_of_sync_target`：Windows 分支断言
  A.YAML 存活且带标记（还原 normcase 即红，非 vacuous）；POSIX 分支按文件系统
  大小写行为断言。
- **r1**：模块 docstring 开头改为「coexisting with user-written profiles，以
  标记区分归属、文件内不合并两源」，消除与共存正文的矛盾。
- **r2**：design「待后续健康同步收敛」限定为「文件恢复可判读后的下一轮收敛；
  永久畸形文件持续否决、不自愈——R6 保守 guard 的既定代价」。
- **r4**：否决日志条件简化为 `profile_files and not server_owned and
  marker_probe_failed`（去掉互相蕴含的 `not upgrade_clear`）。
- **r3（不修留档）**：同一坏文件每轮两条 `exc_info` 与 S3 同源，已并入 design
  风险节 S3 条目。

## 2026-11-17 交付评审（peer review）finding 处置

评审人 ypzyfl（2026-11-17，覆盖本 PR 两提交 `18ac293f` + `97ba4bf1`，评审 AI
CodeBuddy/GLM-5.3 独立于开发/自审 AI）：五项独立检查全过（R2/R11 零上游、
closure 对账、幻觉 API 逐一实证、缺陷模式扫描、madr/ 不适用）；作者 self-review
逐条 confirm；Windows 实机抽查 catalog 115 passed、mock 87 passed/2 skipped、
`--strict` 116/161/0、`--closure` OK——与本文件记载一致。**结论：Approve**，
3 findings 均不阻塞，处置如下：

- **finding-1（design 措辞，合并前修）**：「清空本身失败……收敛自愈」不成立
  （清空循环中途失败后后端文件已带标记，`server_owned` 非空 → 清空不再触发，
  残留无标记旧文件被判自定义永久保留、不自愈）。已改为「永久保留、不自愈」
  并注明触发路径与既定代价；`catalog.py:977` 失败日志经裁决**留档限定口径**
  （对 staging/replace/state 失败准确），不改代码。
- **finding-2（留档）**：后端 id 仅大小写不同的 normcase 键碰撞（Windows 写
  同一文件）——后端病态数据、退化温和，design 风险节留档不修。
- **finding-3（nit，顺手修）**：test-plan 覆盖矩阵「按文件名 stem」对齐为
  「按完整文件名」。

命令：

```
uv run python aixcoding/tools/check_docs.py --closure
```

结果：**OK**（27 ADR / 47 design / 46 self-review）。




