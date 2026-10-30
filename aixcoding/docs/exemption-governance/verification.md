# 验证记录：豁免治理（R13——豁免须理由与批准）

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-10-30 实施完成验证（8 项：7 处联动 + ADR-0014 新建）

命令（签认校验 + 改动清单）：

```
cd /d D:\Tech\Github\huawei\iCode\fork\iCode-fork && set "PYTHONUTF8=1" && uv run python aixcoding/tools/check_docs.py && git status --short
```

结果：`check_docs: scanned 14 ADR(s), 14 design(s), 11 self-review(s) under aixcoding/docs` → **check_docs: OK**；git status 改动清单与 design 联动表逐项吻合、无越权文件：

```
 M aixcoding/README.md
 M aixcoding/docs/standards/DEVELOPMENT.md
 M aixcoding/docs/standards/DIRECTORY.md
 M aixcoding/docs/standards/PEER-REVIEW-HOWTO.md
 M aixcoding/docs/standards/SELF-REVIEW-HOWTO.md
?? aixcoding/docs/exemption-governance/
?? aixcoding/docs/standards/adr/0014-豁免须理由与批准.md
```

注：首次运行因 cmd `set PYTHONUTF8=1 && ...` 尾随空格污染变量值报 `preconfig_init_utf8_mode: invalid PYTHONUTF8 environment variable value`，改 `set "PYTHONUTF8=1"` 后通过——环境问题非产物问题，如实留痕。

命令（活指引残留检索）：

```
search_content pattern="走 `_DAG_EDGE_ALLOWLIST`|DAG_EDGE_ALLOWLIST` 豁免 \+" path=aixcoding/
```

结果：唯一命中 `exemption-governance/design.md` 联动表 #2 的"现文"引文（变更说明，非活指引）；DEVELOPMENT.md / DIRECTORY.md / 两个 HOWTO / README 均无活指引残留。历史快照引用（UPGRADE-RUNBOOK 的"已移除"注记、ADR-0011/0013 快照正文）属合法保留。

命令（签认状态确认）：

```
read_file aixcoding/docs/exemption-governance/design.md（头部）
```

结果：责任人周彬，状态已确认，确认日期 2026-10-30，确认意见"无特别意见"——R10 签认在案，实施有据。

## 2026-10-30 评审处置后修正（A/B 两处；文字级修正，R2 清单零变更——按 R10 分档不触发 design 重签）

背景：外部评审 AI 复核评审提示词时顺带抓出两处（nit/suggestion 级），处置见 design.md"实施期修正记录"节。

- A（确定遗漏）：`DEVELOPMENT.md` §3 标题"硬规则（R1–R12，违反即返工）"→"R1–R13"（R 系列同步义务漏项，design 联动清单补 #8 回写）；全库排查 `R1–R1[12]` 仅 3 处命中——§3 标题（已修）、design 联动 #7 引文（合法变更描述）、`ROADMAP.md:28` 阶段一历史产出记录（合法保留）；
- B（design 内部不一致残留）：联动表 #5/#6 摘要行"约束例外"（五类版遗留）→"等"，与实施落 HOWTO 的四类条文逐字对齐；
- 复跑 `uv run python aixcoding/tools/check_docs.py`：`scanned 14 ADR(s), 14 design(s), 12 self-review(s)` → **check_docs: OK**（self-review +1 为本批次新增件入册）；
- 注：第一节"7 处联动"为当时快照（旧记录不改），A/B 修正后联动表实为 8 处（#8 为评审补项）。

## 2026-10-30 实施 diff 复审后修正（F1–F7，复审 AI：CodeBuddy Deepseek-V4-Pro，通过/零 blocker）

F7 处置——残留检索方法修正（窄 pattern"唯一命中"式结论改为宽 pattern 全量检索+逐处分类）：

```
search_content pattern="_DAG_EDGE_ALLOWLIST" path=aixcoding/（outputMode=count）
```

结果：13 文件 17 处，逐处分类——本批次自身引文 4 处（exemption-governance 的 design×2 / test-plan×1 / verification×1）；历史批次快照 6 处（diagnostics design+verification、launcher-retirement design×2+verification+requirements）；ADR 快照 4 处（0011×2、0013×2）；规范活文件否定注记 3 处（DEVELOPMENT.md R9"已随 ADR-0013 整体移除"、DIRECTORY.md §3"已移除"、UPGRADE-RUNBOOK"已移除，无定制登记残留"）。**结论：无"走该通道豁免"类可执行活指引**（与复审 AI 独立检索结论一致）。

其余处置：F1/F2/F4（design 方案概述与验证方式、test-plan 计数 7→8）、F3（requirements 验收标准"五类"→"四类+兜底句"）、F6（本文件第二节标题签认口径修正——A/B 文字级、R2 清单零变更，按 R10 分档不触发 design 重签）；F5 并入上节末注。处置明细见 self-review.md 追加记录。
