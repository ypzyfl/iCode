# 测试计划：aixcoding/tests 的 ruff 豁免切换为目录级配置

> 活文档：随时更新、不签认（git 留痕）。

## 测试策略

零新增测试。本批次改动 = lint 配置 2 行 + 测试文件删注释行，无运行时行为变更，无新逻辑可锚定；验证义务由**既有门禁全量绿**承载（ruff 双命令 + pytest 全量 + gen 幂等）。

豁免生效性本身由删头反向验证：28 个文件删头后若目录行未生效，`ruff check aixcoding/` 立即红（S101 等恢复报错）——删头即内建回归锚。

## 覆盖矩阵

| 验收标准（requirements） | 验证方式 |
|---|---|
| per-file-ignores 含 marker + 目录行 | `ruff check aixcoding/` 绿 + `pyproject.toml` diff 目验 |
| 28 文件删头 / 1 文件收窄 RUF002 | `git diff --stat aixcoding/tests/` 目验 + ruff 绿 |
| ruff check / format aixcoding/ 绿 | CI 同款命令本地预跑 |
| pytest aixcoding/tests 全绿 | CI 同款命令本地预跑 |
| gen 幂等 + 产物随提交 | 连跑两次 `git diff` 为空 |
| 上游 tests/ src/ 格局不变 | `ruff check src/ tests/` 绿 |

## 异常与降级路径

不适用（无运行时路径）。理论异常仅一处：目录行 glob 不生效（假设表第 1 行）→ 表现为删头后 ruff 红，修正 glob 或回退。
