# 测试方案：定制点登记机制改造（customization-registry）

> 活文档：随时更新、不签认；质量由双 AI 自审（SELF-REVIEW-HOWTO）与错误注入测试保障。

## 测试范围与策略

工具行为变更 + 8 design 登记表重写 + 产物退役 + 规范联动，测试 = **工具单元/注入测试 +
防漂移回归 + 门禁集成 + 人工核对**四层。上游代码零改动，上游测试套只作回归确认。

## 锚匹配算法（design m1 承诺在此钉死）

- **锚语义**：marker 注释正文（去 `# ` 注释前缀后的 marker 全文）的**逐字符前缀**，
  无通配、不折叠内部空白；
- **归一化**：仅对锚与 marker 文本各自 `strip()` 首尾空白；**大小写敏感**；
- **匹配**：`marker_text.startswith(anchor)`；
- **歧义判定（error）**：同文件内一个锚前缀命中的 marker 数 > 该登记行预期计数
  （锚不够长，提示加长）。锚前缀重叠本身不是 error——由同文件**最长锚优先**消解
  （长锚行先吸收其 marker，如 tui 的 C008 长锚先于孪生组短锚）；仅当重叠导致某行
  命中数 ≠ 预期计数时升 error；
- **计数校验（error）**：同 (落点, 锚) 组实际命中数 ≠ 预期计数——
  实际 > 预期报「多出 marker（未登记或锚过短）」，实际 < 预期报「marker 丢失或计数错」；
- **未匹配 marker（error）**：文件内存在不属于任何登记组的 marker（文件无登记行，
  或所有锚均不命中）。

## 覆盖矩阵（错误注入清单 = 验收门槛）

| 场景 | 测试入口 | 断言 |
|---|---|---|
| 未登记 marker | file_tree 造 marker 无登记行 | exit 1，error 含「no registration」 |
| 孤儿登记（宽） | 登记行无 marker，check 默认 | exit 0，warning 进输出 |
| 孤儿登记（strict） | 同上 + `--strict` | exit 1 |
| 未签认 design | 登记表在「草案」design | 不参与匹配；孤儿化或在 notes 说明，不授权 |
| id 重复 / 格式错 | 两表同 id / `X01` | exit 1 |
| id 高水位 | 退役记录含 C030，新行 C030 重复 | exit 1（唯一性含退役号） |
| 锚歧义 | 锚过短命中 2 marker | exit 1，提示加长锚 |
| 孪生计数不符 | 预期 4 实造 3 | exit 1，报丢失方向；造 5 报多出方向 |
| 表头损坏 / 文件不可读 | 登记表节名自创后缀 / chmod 不可读 | fail-closed：exit 非 0 或该 design 计入 error/notes，绝不静默跳过 |
| check 零写入 | 运行前后仓树 hash/mtimes | 无任何文件写入（含 CUSTOMIZATIONS.md 不重建） |
| CLI 退出码 | 各失败/成功路径 | 0 ok / 1 error / 2 env |
| 豁免双消费一致 | `_common.py` 豁免清单 | check_r3_markers 与 report 读同一常量；豁免项改动两处同步 |
| 防漂移回归 A | 两点场景删 1 marker | 其余点 id 不变（report 断言） |
| 防漂移回归 B | 插入字典序更前的文件带新 marker | 存量点 id 不变 |
| report 视图 | 完整 demo 树 | 25 登记行覆盖 29 点、孪生组、豁免表、警告区渲染正确 |
| 考古模式 | `--repo` 外部树 | 行为与现行一致（回归） |

## 集成与门禁验证

| 项 | 命令 | 门槛 |
|---|---|---|
| 现行 29 点对账 | `uv run python aixcoding/tools/gen_customizations.py --strict` | 全绿、孤儿登记清零（stamp() 行核销验证） |
| R3 豁免源切换 | 改豁免清单内文件（.mo 类比）后 `check_r3_markers.py --base` | 不误报；豁免集来自 `_common.py` |
| 定制四门 | `pytest aixcoding/tests -n0 -q -m "not integration and not gc_calibration"` / `check_docs` / `check_import_boundaries` / `check --strict` | 全绿 |
| 上游回归 | `scripts/chrys_test.py --smart --paths`（本批触改文件） | PASSED |
| ruff/format | `uv run ruff check aixcoding/tools aixcoding/tests` 等 | 全过 |
| CI workflow | `aixcoding-tests.yml` 步骤替换后本地等效命令预跑 | 步骤命令逐条本地跑过（auth-logging 批次教训） |

## 实施期人工核对（流程性）

1. **8 表逐字定稿清单**（design m4 实施约束）：呈报责任人核对（含 tier-migration 勘误
   并入后 auth 行 anchor 定稿文本、孪生组行、removal_condition 逐组取值）→ 确认后落盘；
2. **report 全景输出**：29 点人工核对一遍（id/落点/孪生组/removal_condition）；
3. 引用面核查清单逐项打钩（含 `upstream-merge-v0.32.2/design.md` 的 stale 编号修正）。

## 异常与降级路径

- 匹配断裂（现行 29 点迁移后 check 红）→ 按报错逐点修登记行，属预期调试而非方案缺陷；
- `check_r3_markers.py` 切换豁免源后行为异常 → 回退该单文件改动单独排查（豁免语义未变，
  仅换读取来源）；
- 升级批次的 marker 措辞/路径漂移触发登记跟改 → design 既定路径（跟改+R10 重签，id 不丢）。
