# 验证记录：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

> 活文档。全部命令于 2026-11-09 在开发机（Windows，Python 3.14.8，本机 HOME 实存
> `~/.aixcoding/skills/hanhai-h5`）实际执行；输出摘要如实摘录。

## 代码实施后的验证矩阵

| # | 验证项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 冒烟：默认配置根列表 | `uv run python -c "..._collect_skill_paths(SkillsConfig())..."`（重定向读回） | 6 根齐：`%APPDATA%\chrys\skills`、`.aixcoding\skills`、`.aixcoding\market-skills`、`.aixcoding_intellij\{skills,market-skills}`、`.agents\skills`；次序符合 v3（team 根本机容器不存在故为空，cwd 根需 runtime 正常缺省） |
| 2 | 定制套件 | `uv run pytest aixcoding/tests/skills -n0 -q -p no:cacheprovider` | **17 passed**（含机制回归 `test_platform_redirect_covers_aixcoding_dir`） |
| 3 | 污染回归（本机 HOME 实存技能） | `uv run pytest tests/service/skills/test_adapter.py tests/orchestration/workflows/test_agent_parity.py -n0 -q` | **64 passed, 1 skipped**（既有平台跳过）——机制性隔离生效 |
| 4 | 直接相关上游面 | `uv run pytest tests/service/profiles/agents tests/foundation/platform tests/service/skills -n0 -q` | **776 passed, 84 skipped** |
| 5 | 架构套件 | `uv run pytest tests/architecture -n0 -q -p no:cacheprovider` | 全绿（exit 1 为本机临时目录 safe-delete 批量确认副作用，非测试失败；两次复跑输出均无 F/FAILED） |
| 6 | ruff check | `uv run ruff check <9 个代码文件>` | 0 error（初检 SIM105 已按建议改 `contextlib.suppress`） |
| 7 | ruff format | `uv run ruff format --check <代码文件 + 5 个 md>` | 全绿（测试文件初检 6 处签名折行已 format） |
| 8 | ty 三平台 | `uv run ty check --error-on-warning --python-platform {win32,linux,darwin} src/chrys` | 三平台全绿（junction 修复后复跑 win32 仍绿） |
| 9 | 登记对账 | `uv run python aixcoding/tools/gen_customizations.py --strict` | OK — 110 行登记 / **151 marker** 全对账（C143-C151 本批 9 marker；初检 26 错全部为登记表格式，已修） |
| 10 | R2 审批对账 | `uv run python aixcoding/tools/check_r2_diff.py --base HEAD` | 本批全部上游改动文件 **approved**（4 docs + platform/conftest/adapter/schema/loader）；ERROR 项全部为**批次前遗留的工作区 untracked 杂物**（`.codebuddy/pr64_*`、`pr87_*` 评审探针、`.workbuddy/`、`.zcodeignore`、`review_scope_pr69.txt`、`util/build-linux-arm64-dev.yml`、`制品/*` 离线包），非本批引入，按 R6 未动，待责任人裁决清理 |
| 11 | 文档校验 | `uv run python aixcoding/tools/check_docs.py` | OK（23 ADR / 32 design） |

## 上游 Smart Test 全量说明（环境限制，如实记录）

`scripts/chrys_test.py --smart --paths <13 文件>`：**34797 passed, 62 failed, 743 skipped**。
62 个失败经取证为**本机环境性既有失败**，与本批无关：

- 实证：`test_windows_long_search_roots_*` 失败栈为 `WinError 206 文件名或扩展名太长`——
  测试刻意构造超长目录树，而本机 pytest 临时根 `...\Temp\pytest-of-李海潮\...` 含中文用户名，
  路径预算被占用必然触顶；同类失败覆盖 NUL 文件 walk、安装脚本路径、长 activation id——
  全部位于本批未触达的模块（tools/search、app/install、workflows 存储等）。
- 本批直接触达面的对应上游套件（矩阵 #3、#4、#5）独立全绿。
- CI PR gates（英文环境 + 长路径启用）为该 62 项的权威判定环境。

## AI 评审轮次

| 轮次 | 评审方 | 结论 | 处置 |
|---|---|---|---|
| 第一轮 | 独立评审 AI（CodeBuddy 子代理，只读，very thorough） | 1 blocker + 6 minor + 14 项核对通过 | 全部处置（见 self-review.md） |
| 第二轮 | 独立复审 AI（同上，增量复审） | 修复项通过；新发现 3 小项（断言方向反、design 验证命令旧路径、行号漂移）+ configuration.md 备案判断成立 | 全部修复；复跑全绿 |
