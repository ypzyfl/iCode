# 自评审记录：后端同步模型与自定义模型共存

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：施利利
- 状态：已确认
- 确认日期：2026-11-17 
- 确认意见：已确认
- 开发 AI：CodeBuddy / GLM-5.3-Flash
- 评审 AI：Deepseek-V4.1-Flash

（实现完成后按 SELF-REVIEW-HOWTO 执行双 AI 评审，追加评审记录。）

## 2026-11-17 第 1 轮评审：不通过（3 blocker / 5 次要）

- 评审范围：`git diff`（`src/chrys/service/aixcoding/models/catalog.py`、
  `aixcoding/tests/catalog/test_catalog_sync.py`）+ 本批六件套。
- 评审 AI 标识：Deepseek-V4.1-Flash（独立第二 AI，与开发 AI GLM-5.3-Flash 不同源；
  仍可能共盲，终裁在责任人）。
- 实测复核（非引用 verification.md）：
  - `uv run pytest aixcoding/tests/catalog/test_catalog_sync.py -n0 -q` → **84 passed**（1.97s）
  - `uv run ruff check …catalog.py …test_catalog_sync.py` → All checks passed；
    `ruff format --check` → 2 files already formatted
  - `uv run ty check --error-on-warning --python-platform darwin src/chrys` → All checks passed
  - `gen_customizations --strict` → 116 row / 161 marker / 0 warning（零增量，与 design 一致）
  - `check_docs --closure` → **1 error**（见 B4，非"draft forbidden"）
  - Smart Test 全量未重跑（见"未重跑项"）

### 过项（附证据）

| 检查项 | 结论 | 证据 |
|---|---|---|
| R2 上游文件 | 过：零接触 | diff 仅 2 文件；产品代码落在 `src/chrys/service/aixcoding/models/catalog.py`（定制目录），无上游文件、无 marker 需求 |
| R11 依赖 | 过：零变化 | `pyproject.toml` / `uv.lock` 未动；新增 import 为仓内既有模块 |
| 幻觉 API | 过 | `read_profile_mapping(text: str)`（`service/profiles/file_scan.py:33`）、`load_profile_from_yaml(path: Path)`（`service/profiles/models/loader.py:183`）签名与调用一致 |
| 两阶段顺序 | 过 | 升级清空在 staging→`os.replace`→陈旧删除→`write_catalog_state` 之后（catalog.py:890-923）；`test_upgrade_publish_failure_preserves_old_files` 非 vacuous（把清空移到 staging 前即红） |
| 内存快照过滤 | 过 | `server_ids` 过滤后传入（catalog.py:1213-1215），与 `install_snapshot` 字典后者胜出语义一致；`test_snapshot_id_collision_keeps_backend_item_in_memory` 走真实 `_publish` |
| 数据外发 | 过 | 新增字段仅落本地 detail 日志与 YAML 标记，无外发、无路径泄漏 |

### blocker

1. **探针失败被静默吞掉，且永久否决升级清空**（`catalog.py:757-771`、`:779-790`、`:859`、`:874`）
   `except Exception: return None` 之后，`marker_probe_failed` 只参与 `upgrade_clear` 计算，
   **从不进任何日志**（§9 降级必须可查）。且探针用 `read_text(encoding="utf-8")`，而 loader 用
   `decode_bytes()`（编码探测），两者判定不一致：GBK/BOM 文件 loader 能读、探针读不了。
   实测（一次性脚本，`/tmp` 下执行）：目录内放 `old-server.yaml`（无标记旧残留）+ GBK 编码
   `cn.yaml` → 探针返回 `None` → `old-server.yaml` **未被清空**、`preserved_profiles=['cn','old-server']`，
   日志只写"保留 2 个自定义模型"。该状态**每轮重复且永不自愈**（无任何代码会删除/修复不可读文件），
   与 design「待后续健康同步收敛」的表述不符。
   处置建议：① 探针改用 `decode_bytes(path.read_bytes(), errors="strict")` 与 loader 同源；
   ② `probe_failed` 落一条 detail 日志（"N 个文件无法判读；本轮跳过升级清空"）；
   ③ 修正 design §首次升级清空的"后续健康同步收敛"表述（仅对暂时性失败成立）。

2. **`.yml` 同名误判：日志撒谎 + 内存消失**（`catalog.py:879-880`）
   `overwritten` 与 `preserved_profiles` 都按 **stem** 判，但 `os.replace` 的覆盖目标只有
   `{id}.yaml`。实测：`a.yml`（YAML 显式 id 为 `mine-alias`）在同 stem 后端项 `a` 同步后
   **文件原样存在、内容未改**，却得到 `overwritten_custom_ids=('a',)`，日志输出
   "已被后端版本覆盖：a"（事实错误），且该文件不进 `preserved_profiles` → TUI 列表里消失，
   重启后 `registry.load_all()` 又会出现（前后不一致）。
   处置建议：判定用完整文件名（`path.name == f"{id}.yaml"`）而非 stem；补一条 `.yml` 形态用例。

3. **R8 文档/代码契约不符：模块与函数 docstring 仍是旧语义**（`catalog.py:5-13`、`:27-33`、`:825-845`）
   模块头仍写"目录只有一个主人、两个来源之间无合并"、"每次同步 wholesale 替换 — 目录不再包含的文件被删除"；
   `apply_catalog` docstring 未提标记、保留项、升级清空。与实现直接矛盾，后续读者/agent 会按旧契约推理。
   处置建议：同一文件内更新模块头 + `apply_catalog` docstring（非上游文件，无 R2 负担）。

4. **签认头部不成立：状态"已确认"但责任人为空 → closure 红**（`self-review.md:10-12`）
   `check_docs --closure` 现在的错误是 `status 已确认 but 责任人 is empty`，而非 verification.md
   记录的 `draft decision/review document is forbidden by closure`——**验证记录已与现实不符**，
   需按现状追加一节。同时本文件在双 AI 评审尚未完成、责任人未签字时即为"已确认"，违反 R10
   （签认须责任人本人，AI 不得代填）。
   处置建议：责任人本人填 `责任人`（或评审完成前改回`草案`）；verification.md 追加当前 closure 实况。

> blocker 4 由评审发现于"自我签认"环节，与实现代码无关；实现侧 blocker 为 1–3。

### 次要问题

- **S1 标记写入侧不封闭**（`serializer.py:51-63`、`app/acp/session_manager.py:469-500`）：`synced_from_server`
  只在 `_write_profile` 注入，任何经 `save_profile`（`profile_to_dict`）重写同名文件的路径都会丢标记，
  ACP `write_model_profile` 且无 catalog 门禁。后果：该文件变"自定义"→ 后端下架后成永久幽灵模型；
  若客户端把全部同步文件重写一遍，目录成"全无标记"，下次同步可能触发升级清空删掉用户真自定义模型
  （把"从未同步的纯用户目录"风险扩到"已管理的正常目录"）。处置：design「对上游隐式行为的假设」补一条 +
  ACP 写路径加门禁（新范围，需责任人裁决）；不改上游 `serializer.py`。
- **S2 vacuous test**（`test_catalog_sync.py:1596-1606`）：`test_fingerprint_ignores_custom_profiles`
  不可能红——`_coerce_version(catalog)` 只吃 catalog，任何保留/标记逻辑改坏都不影响它。处置：删掉或改造。
- **S3 三次扫描**：每个 YAML 每轮被读 2–3 次（`:863-865`），且三处扫描间存在时间窗（扫描后新增/消失的文件分类不一致）。nit，可一次遍历产出。
- **S4 未申报的顺手修复**（`catalog.py:946-953`）：基线日志参数错位（`%d` 收到 `source`，logging 静默吞成 "--- Logging error ---"），本批顺手改正但 design/plan/verification 均未记（R5 只改必需内容）。处置：补一句记录，避免复审误判为未申报变更。
- **S5 需求措辞**（`requirements.md:45-46` vs `app/tui/screens/main/config_actions.py:286`、`registry.py:157`）：
  TUI `ModelConfigScreen(read_only=True)` 恒真、`install_snapshot` 清空 `registry.sources`，
  自定义模型"可见、可用"= 可选中，不可编辑/新建。design 已声明只读门禁不变，需求场景措辞宜对齐。

### 未重跑项（如实记录）

- Smart Test 全量（verification.md 记 13812 passed）与定制套件全量（829 passed）未重跑：
  本次只重跑了 catalog 套件（84 passed，与记录一致）与 ruff/format/ty/gen_customizations/closure。
- 未在 Windows 上验证；未做端到端手工验证（test-plan 声明无独立手工步骤）。

## 2026-11-17 第 2 轮（增量复审）：B1/B2/B3/S2/S5/S6 → 1 个新 blocker（B5）+ 3 处残留

- 复审范围：**仅本轮修复增量**（未重跑全量）。`catalog.py` 的模块/`apply_catalog`
  docstring、`_probe_server_marker`、`_load_custom_profiles` 返回口径、`apply_catalog`
  判定段与清空循环、`_publish`；测试新增 5 例；design / requirements / verification 对应段落。
- 实测（本次亲自执行）：`uv run pytest aixcoding/tests/catalog -m "not integration and
  not gc_calibration" -q` → **114 passed**（与 verification 记载一致）；
  `ruff check` / `ruff format --check`（两文件）→ 全过；
  `ty check --error-on-warning --python-platform darwin src/chrys` → 全过；
  `check_docs.py --closure` → **OK**（B4 已由责任人补填 责任人，关闭）；
  `gen_customizations --strict` → 116 row / 161 marker / 零增量。Smart Test 与全量定制套件未重跑。

### 逐条结论

| finding | 结论 | 证据 |
|---|---|---|
| B1 探针静默 + 编码分歧 | **过** | 探针改 `decode_bytes(path.read_bytes(), errors="strict")`（:774）与 loader 同源；失败与否决各有 detail 日志（:782、:898-902）；`test_foreign_encoded_file_stays_decidable_and_clear_proceeds`（GBK 文件 → 清空收敛）与 `test_all_malformed_directory_is_not_cleared` 的否决日志断言均非 vacuous（回退到 `read_text(utf-8)` 或删掉否决日志即红） |
| B2 同 stem `.yml` 误判 | **过** | `_load_custom_profiles` 返回完整 `path.name`（:822），`final_names` 以文件名键入（:910），`overwritten`/`preserved` 均按文件名（:916-919）；`test_same_stem_yml_is_a_distinct_file_the_sync_never_touches` 回退到 stem 判定即红 |
| B3 docstring 契约 | **过（残留 1 处自相矛盾）** | 模块头与 `apply_catalog` 已对齐标记/保留/升级清空；但 :5-6 仍留"has exactly one owner at a time, and there is no merge between two sources"，与紧随其后的共存段落冲突（见残留 r1） |
| S2 vacuous test | **过** | `test_fingerprint_ignores_custom_profiles` 现重算期望摘要，扩大 hash 输入域即红，已非 vacuous |
| S5 需求措辞 | **过** | requirements 场景 1 改为"可见、可选中发起会话（不含编辑/新建）" |
| S6 大小写口径 | **不通过 → B5** | 判定段对齐了 normcase，但**升级清空循环未对齐**（:955），见下 |

### blocker

**B5 升级清空循环仍用原始文件名与 normcased 键比较，Windows 上会删掉本次刚写入的后端文件**（`catalog.py:910` vs `:955`）

- 现状：`final_names = {os.path.normcase(f"{id}.yaml"): id}`（:910，键已 normcase 小写化），
  但清空循环用 `if path.name in final_names: continue`（:955，`path.name` 为磁盘原始大小写）。
  S6 已把"判定"与"陈旧删除"（:935）迁到 normcase，唯独第三处删除点漏改，口径自相矛盾。
- 触发三条件（缺一不触发）：Windows（glob 大小写不敏感，`.YAML` 会进扫描）+ 目录**全部无标记**
  （否则 `upgrade_clear` 为 False）+ 存在大小写变体文件名（如 `A.YAML`，后端 id `a`）。
- 后果链：`os.replace` 已把 `A.YAML` 覆盖成后端版本 → 清空循环因 `'A.YAML' ∉ {'a.yaml'}`
  而 `unlink()` → 大小写不敏感文件系统上解析到同一文件，**删掉刚发布的后端 profile**；
  `apply_catalog` 仍返回成功、日志还记"已清空 1 个配置文件"，模型缺席直到下轮同步。
- 现有测试不覆盖：`test_extension_case_matches_the_platforms_replace_semantics` 带
  `_add_marker_anchor` → `upgrade_clear=False`，清空循环不进入（本条为代码阅读 + 平台语义推演，
  未在 Windows 实机执行）。
- 处置：`if os.path.normcase(path.name) in final_names: continue`（一行）；建议在 S6 用例
  再加一个"全无标记目录 + 大小写变体名"分支（Windows 分支断言后端文件仍在）。

### 残留（次要，责任人可拍板不修）

- **r1（B3 残留）**：模块 docstring :5-6「``~/.chrys/models/`` has exactly one owner at a time,
  and there is no merge between two sources」与本批正文（共存）自相矛盾，一句话删掉即可。
- **r2（B1 残留）**：design:105-111 仍写"保守保留文件…**待后续健康同步收敛**"——改用
  `decode_bytes` 后**编码**不再导致 `None`，但**永久畸形**文件探针恒为 `None`，清空被永久否决、
  不会自愈（本批无任何代码清理不可读文件）。建议把该句限定为"仅暂时性读取失败可自愈；
  永久畸形文件使升级清空长期失效（按保守保留处理，日志留痕）"。
- **r3（nit）**：`_probe_server_marker` 的失败日志（:782）经 `_server_owned_names` 与
  `_load_custom_profiles`→`_is_server_synced` 各打一次，同一坏文件每轮两条 `exc_info` 堆栈；
  与已登记的 S3（三次扫描）同源，可一次遍历取值。
- **r4（nit）**：`:898` 的 `not upgrade_clear and profile_files and not server_owned and marker_probe_failed`
  前四条件互相蕴含，可简化为 `profile_files and not server_owned and marker_probe_failed`。

### 收敛判断

B1 / B2 / B3 / S2 / S5 已收敛；S6 自身引入 B5（一行修复 + 一条用例）。**B5 修完并复审该行后，
本批 blocker 清零**，可进入签认与提交。

