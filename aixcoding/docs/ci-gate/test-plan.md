# 测试方案：定制 CI 质量门（ci-gate / aixcoding-tests.yml）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与本地等效验证保障。

## 测试范围与策略

无产品代码，无单测义务（§5 测试义务针对定制模块）。验证分两层：

1. **本地等效命令**：CI 步骤逐条在本地跑通（Windows + uv 环境配方），R2/R3 base 用本地 merge-base——结果记 verification.md；
2. **远程首跑**：push 后 GitHub Actions 实际执行——本批未验证事项，观察后补录。

无 mock 依赖；无上游 anchor。

## 覆盖矩阵

| 验收标准（requirements.md） | 验证方式 | 类型 |
|---|---|---|
| workflow 文件落地（触发/单 job/pin 对齐） | YAML 结构人工审 + design R2 表对照 | 人工审 |
| 步骤覆盖 ADR-0004 四步 + 四工具五步 | 本地等效命令逐条（verification #表） | 等效执行 |
| 本地等效命令跑通 | verification.md 命令+输出 | 等效执行 |
| YAML 合法 | 本地解析（若环境有 yaml 模块）或 Actions 首跑 | 机检/远程 |

## 异常与降级路径

- merge-base 计算失败（main_iCode 缺失/历史不足）：CI 步骤显式报错 exit 非 0（fail-fast，不静默跳过门禁）；
- gen 幂等失败输出 diff 摘要：责任人本地重跑 `gen_customizations.py` 提交清单；
- R2/R3 失败输出违规清单：处置路径见各工具 docstring（补 design 签认或回退改动）；
- **R2 违规会掩盖 R3 违规**（workflow `bash -e` 下 R2 失败即中断，R3 不执行）：接受此取舍——先修 R2 再看 R3，本地两条命令可分开跑；改为收集两门结果统一退出会增加复杂度，不值。

## 未验证事项

- **GitHub Actions 远程首跑**：本地不可复现（步骤/语法/runner 环境）；
- **CI `-n 8` 并行 vs 本地 `-n0` 串行**：`aixcoding/tests` 全部用 `tmp_path` 隔离、无共享态，理论并行安全，但首跑前未在并行模式下实际执行过（pyproject `addopts` 默认 `-n 8`，CI 的 pytest 步骤未显式传 `-n`）；
- `uv sync` 在干净 runner 的时长。
