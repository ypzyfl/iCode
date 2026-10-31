# 设计：定制 CI 质量门（ci-gate / aixcoding-tests.yml）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-25
- 确认意见：无特别意见

## 方案概述

单 job、单 Linux、12 步流水：环境三步（checkout 全历史 + setup-uv + setup-python + uv sync）→ ADR-0004 四步（ruff check / ruff format --check / check_docs / pytest）→ 四工具五步（import 边界 / 清单生成幂等 / R2 比对 / R3 标记）。R2/R3 的 base 统一取 `git merge-base origin/main_iCode HEAD`——fork 分叉点即上游基线锚点（`main` 已重命名 `main_iCode`，2026-10-25 负责人确认；当前分叉点 3104004，上游镜像已推进至 !84 不影响语义：门禁比对的是"本分支累积上游改动 ⊆ 批准池"）。

## 备选方案对比

| 决策点 | 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| base 锚点 | merge-base origin/main_iCode HEAD | 分叉点语义精确=上游基线；随上游镜像推进自动移动；无需维护 tag | 依赖 main_iCode 保持纯上游镜像（团队纪律，升级 runbook 固化） | **采用** |
| | fork 侧打 base tag（如 aixcoding/upstream-base） | 显式可控 | 升级时需人工移 tag，忘移=门禁失效；多一个维护物 | 否 |
| | PR 事件 base ref | 零计算 | 语义错误：PR base 是 fork 分支非上游；嵌套 PR 漏检累积改动 | 否 |
| 清单校验方式 | gen 后 `git diff --exit-code`（幂等） | 机检"清单与代码一致"，手改生成区/加标记不重生成即红 | 清单警告文本变化（如签认状态流转）也触发——属期望行为 | **采用** |
| | 只跑不校验 | 无误报 | 幂等漂移无人发现，§5"禁止手工维护"无牙齿 | 否 |
| 触发范围 | PR + push 至 main_aixcoding_cli，无路径过滤 | 任何上游文件改动（R2/R3 射程）都触发门禁 | 无关改动也全跑（门轻：分钟级，可接受） | **采用** |
| | 路径过滤 aixcoding/** | 省 runner | 上游文件改动不触发=R2/R3 门禁失效，违背本门存在意义 | 否 |

ADR 判定：机制级决策已由 ADR-0004（独立 workflow/四步框架/单 Linux/不加 ty/mock 不单独门禁）承载，本批为执行 + 四工具挂入的运行细节（base 锚点、幂等校验均为操作层选型，上表记录理由）——不出新 ADR。

## 上游改动清单（R2；无上游改动则删除本节）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `.github/workflows/aixcoding-tests.yml` | 新建定制质量门 workflow（GitHub 硬约束：workflow 必须位于上游目录 `.github/workflows/`）：触发 PR+push 至 main_aixcoding_cli、单 job ubuntu-latest、环境三步 + ADR-0004 四步 + 四工具五步 | 约 75 | 不加（ADR-0004 后果节明确定位为"上游目录内定制文件"；工具分类器 `CUSTOM_EXACT_PATHS` 已收录为定制资产，非上游文件改动处） |

R1 自查：GitHub 平台硬约束下无其他落点（否决过的改 ci.yml 属更高冲突面）；文件为纯新增，上游零感知。

补记（2026-10-25 评审后）：①**R2 表登记 ≠ 门禁检查对象**——本 workflow 真正的豁免来自工具分类器 `CUSTOM_EXACT_PATHS`（`aixcoding/tools/_common.py`），R2 表登记是流程层批准留痕，两者双轨自洽（少登记会触发拦截，多登记仅使 approved_pool 含不生效条目，fail-safe）；②本批无新增第三方依赖——3 个 GitHub Actions 复用上游 `ci.yml` 同 SHA，属上游已有依赖。

## 对上游隐式行为的假设

| 假设 | 依赖方式 | 失效表现 |
|---|---|---|
| `origin/main_iCode` 持续作为纯上游镜像分支存在 | merge-base 计算门禁 base | 镜像含定制提交 → 门禁漏报累积改动（升级 runbook 固化镜像纪律；失效可由 gen 幂等步的部分场景交叉暴露） |
| `actions/checkout@v7.0.1`（SHA pin 同上游 ci.yml）fetch-depth:0 提供 origin/main_iCode 引用 | merge-base 计算与 R2/R3 `git diff` | 步骤显式失败（merge-base 报错 → 工具 exit 2） |
| `.python-version` / `uv.lock` / `pyproject.toml` 可安装定制测试环境（pytest 由 dev group 提供） | `uv sync` | sync 步骤失败，门禁 fail-fast |

无产品代码 anchor。

## 定制点登记预告

不适用：纯开发资产（CI workflow），无上游接触面、无运行时行为，不入 CUSTOMIZATIONS.md（同 devtools 口径）。

## 风险与最坏情况

- **GitHub Actions 远程环境本批不可本地复现**：本地跑等效命令 + YAML 人工审，首跑验证后置（push 后观察，失败即修，最坏删除 workflow 文件回滚——门禁消失不损害仓库功能）；
- runner 时长：uv sync 全量 dev 依赖 ~分钟级；后续可按需加缓存微调（对齐上游已有 setup-uv enable-cache）；
- 回滚：删除 `.github/workflows/aixcoding-tests.yml` 即完全回滚。

## ADR 判定

四问：①否决备选——操作层选型已记上表，机制级无新否决（ADR-0004 在案）；②撤销代价——单文件可即删，低；③约束未来工作模式——base 锚点纪律（main_iCode 纯镜像）将固化进升级 runbook，属流程文档非 ADR 级；④依赖上游非公开接口——无（公开 Actions/分支约定）。结论：不出 ADR。
