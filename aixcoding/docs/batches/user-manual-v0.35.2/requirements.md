# 需求：0.35.2 手册内容同步（user-manual-v0.35.2）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
> 来源：官方 openJiuwen-ai/iCode v0.35.2 发布（2026-11-10 05:02 UTC），手册按"每次升级固定步骤"同步（承接 user-manual 批次 plan.md「手册对齐流程」）。
> 修订记录：2026-11-11（一）初稿；2026-11-11（二）**评审 F1 扩围补录**——独立评审（Claude Code / GLM-5.3-flash）指出工作区 en 侧 22 个整文件 + 本批次文件内混入的追平 hunk 未被批次文档承载（user-manual 批次 en 对齐的未提交延续 + ACP 清扫），经责任人拍板按"扩围"处置：六件套如实改写并扩围，全部改动随本批次提交（处置记录见 plan.md「责任人裁决记录」）。本批次为**事后补录**（改动已实施，六件套按实际终态回写，见 plan.md 状态节）。

## 背景与问题

官方 v0.35.2 发布，其手册改动（`git diff v0.35.2 -- docs/zh-Hans docs/en`，对照工作树 0.35.1 镜像）为
**4 个文件、约 12 行**，zh/en 各一份：

1. sessions：会话搜索增强（跨页搜索 + 分页显示 + 提示词匹配项斜体排序等）；
2. shortcuts：未填参数整体导航/删除/撤销 + Vim 模式行为；
3. skills：Skill 资源发现从"根层+直接子目录"加深到"根层及下两级子目录"；
4. getting-started：粘贴长文本阈值（6 行/+5 行）、标签只读预览与 Ctrl+O 全文编辑、单行/多行引用统一为引用块。

桌面侧上一轮基线（`20261109\0.35版本`）与定稿（`20261109\0.35更新后`）齐备，需按三方合并
把官方 0.35.2 改动落进定制手册（`aixcoding/manual/` zh+en），并重出桌面三件套（MD/PDF/wheel）。

## 目标与非目标

- 目标：
  - 生成 0.35.2 官方汇编 MD（ours，本批次起作为下一轮三方合并基线）；
  - 官方 6 处改动（zh+en 各 6 处，含 getting-started 3 段）落进 `aixcoding/manual/`，套定稿口径
    （iCode→AIxCoding-CLI、Skill 目录→技能目录）；
  - 版本行与构建信息章版本占位统一 0.35.2（zh+en）；
  - **en 侧追平收尾（评审 F1 扩围）**：user-manual 批次遗留的 en 侧未提交追平改动（22 个
    整文件——models 整章重写对齐 zh"切换模型"、getting-started 删 uv 安装章、icode-acp
    增补、`icode serve`→`aixcoding-cli serve`、`icode-ocean.yaml`→`aixcoding-cli-ocean.yaml`、
    ACP 表述清扫等——及本批次 en 5 文件内混入的追平 hunk、zh getting-started 的
    ICODE_CHANNEL→AIXCODING_CHANNEL 1 处）如实纳入本批次登记与提交；该批改动是
    en 侧审计绿的前提（audit_manual 覆盖 zh+en 双语）；
  - 桌面定稿 MD/PDF（含 50 条书签）与定制版 wheel 重出并同步；
  - 全部门禁绿（六项审计、check_links、check_docs、gen_customizations --strict、契约测试、捆绑哈希）。
- 非目标：
  - **代码升级**——0.35.2 的程序改动（MCP 超时校验、流式优化等）走 UPGRADE-RUNBOOK 另批处理；
    文档版本口径先行（构建信息章示例版本号按 SKILL 惯例随手册版本写 0.35.2）；
  - `docs/`（上游镜像）**不做任何定制改写**——内容只允许为纯官方原文。镜像追平节奏由责任人
    2026-11-11 裁决修订：手册批次同步应用官方 docs diff（原"仅随代码升级批次更新"口径作废，
    见 design「docs/ 镜像追平」节与 R2 表）；
  - en 结构重排（标题编号等展示层差异维持 user-manual 批次既定口径）；
  - 手册翻译再创作——仅机械同步官方改动。

## 用户场景

1. 内网客户 F8 手册：看到 0.35.2 的 4 处行为描述（会话跨页搜索、快捷指令参数编辑、Skill
   两级子目录发现、图片/引用/粘贴标签新交互）。
2. 开发机 F8（CHRYS_DOCS_ROOT → `aixcoding/manual/`）：改 MD 即见，与安装版同源。
3. 下一轮手册版本（0.36）：以本批次产出的 `0.35.2版本\AIxCoding-CLI用户手册.md`（官方汇编）
   为基线做三方合并——基线/定稿/官方三方齐备。

## 验收标准

- [x] 0.35.2 官方汇编 MD 生成（与 0.35 基线 diff 恰好 8+/8-：封面 2 行 + 官方 6 处，其余逐字节一致），
      落位 `Desktop\用户手册\20261111\0.35.2版本\`；
- [x] manual 同步：zh+en 共 10 文件 14 处替换（6 处官方改动 ×2 语言 + build-info 版本占位 ×2），
      每处 count==1 断言，套定稿口径（zh getting-started 另含 ICODE_CHANNEL→AIXCODING_CHANNEL
      第 4 处，见 verification 补正后清单）；
- [x] docs/ 镜像追平：官方 0.35.2 手册改动（8 文件 12 行，纯官方原文）应用至仓库 `docs/`，
      `git diff v0.35.2 -- docs/zh-Hans docs/en docs/index.yaml` 归零（责任人 2026-11-11 裁决）；
- [x] en 侧追平收尾（评审 F1 扩围）：22 个 en 整文件追平改动 + 本批次 en 5 文件内混入的
      追平 hunk 全部登记在册（清单见 verification「en 侧追平清单」节），随本批次一起提交；
      `git status` manual 树 = zh 5 + en 27，全部有批次文档承载；
- [x] 手册自检：品牌/禁用词 0（iCode/icode/ACP/OpenTelemetry/otel./Chat 选项）、结构 0、
      内锚 237 引用 0 失效、第三方外链 0（check_links PASS）；
- [x] 六项审计全绿且**基准自动切换**到 0.35.2 定稿（逐章比对 = F8 manual 与桌面定稿一致铁律）；
- [x] PDF：137 页、书签 50 条自校验通过（7 部/32 章/11 节）、首页 32 目录链接保留、
      AIXCODING_CHANNEL 1 / ICODE_CHANNEL 0；
- [x] wheel 重建 + 重装测试环境（`C:\work\icode-wheel-test\.venv`），捆绑 64=64 MD5 全一致，
      0.35.2 新内容抽查命中（三处关键词）；
- [x] 手册契约测试全绿（foundation + invoker + workflows + providers 的 test_documentation，26 passed）；
- [x] 桌面交付：`20261111\0.35.2更新后\`（MD+PDF）、`20261111\0.35.2版本\`（官方汇编）、
      桌面 wheel 覆盖同步。

**验收结论：通过**（待责任人确认，逐条证据见 verification.md）。

## 开放问题

- （无）——流程性异议（如构建信息章示例版本号是否随手册版本预写 0.35.2）见 plan.md「挂起与备忘」。
