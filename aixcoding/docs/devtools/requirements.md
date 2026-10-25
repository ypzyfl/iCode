# 需求：规范落地四工具（devtools）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

规范（DEVELOPMENT.md）承诺了四项自动校验：定制清单生成（§5）、R2 diff 比对、R3 标记校验（R2/R3 + ADR-0007 机器门禁）、import 边界校验（§9 / DIRECTORY.md §4–6）。生成脚本未建，全部处于人肉降级态——plan.md §0 已立项为首批工具建设，防"文档先行、工具永远在后"。当前分支为上游 0.31.0 干净基线，阶段三迁入前落地门禁成本最低。

## 目标与非目标

- 目标：
  - 四个可独立运行的脚本：`gen_customizations.py` / `check_r2_diff.py` / `check_r3_markers.py` / `check_import_boundaries.py` + 共享库 `_common.py`，全部落 `aixcoding/tools/`；
  - 建立 `aixcoding/docs/CUSTOMIZATIONS.md` 生成机制（代码事实扫描派生 + design.md 登记预告表合并语义字段）；
  - 工具①支持 `--repo` 指向旧分支副本产出考古扫描报告（ROADMAP §4 盘点清单输入）；
  - 四脚本均有配套测试且全绿。
- 非目标：
  - 不建 CI workflow `aixcoding-tests.yml`（U3 另行，工具只保证可被 CI 调用）；
  - 不做 LLM 自动评审（ADR-0007 演进方向，资源未就绪）；
  - 不做 R9 tier/DAG 校验（上游 `tests/architecture/test_layering.py` 已有机制，不重复）；
  - 不扫描/校验 wheel 打包产物（`check_wheel.py` 上游已有）。

## 用户场景

1. **日常开发自检**：改完代码跑四脚本，确认无越权上游改动、标记齐全、import 边界干净；
2. **PR 门禁**（CI 或评审人本地）：`check_r2_diff --base <PR base>` + `check_r3_markers --base <PR base>`，机器判断"上游文件改动是否全部在已签认 design.md 的 R2 表内、是否带标记"；
3. **升级 runbook 执行**（阶段二第 4 项）：拉上游 tag 后 `--base <upstream tag>` 比对，产出需人工处理的冲突清单；
4. **阶段三考古**：`gen_customizations --repo <旧分支副本>` 输出候选定制点报告，填充 ROADMAP §4 盘点表。

## 验收标准

- [ ] `gen_customizations.py` 对当前仓库运行：生成 `aixcoding/docs/CUSTOMIZATIONS.md`（干净基线=空清单体 + 人工维护区保留）；文件已存在时人工维护区内容不丢失；
- [ ] `gen_customizations.py --repo <旧分支副本>`：产出候选报告（含命中文件、行号、标记文本、甄别分类：注释标记 / 疑似品牌字符串命中），不依赖该仓库有 design.md；
- [ ] `check_r2_diff.py`：上游零改动时通过；构造一处未批准上游文件改动 → 退出非零并列出该文件与已批准清单；未签认 design.md 的 R2 表不纳入批准集；
- [ ] `check_r3_markers.py`：上游文件 diff 新增行含 `AIxCoding` 标记时通过；无标记 → 非零退出；JSON/二进制等无法加注释格式按豁免表放行；
- [ ] `check_import_boundaries.py`：对构造的违规样本（根 aixcoding import `tests.*`、上游代码 import 根 `aixcoding.*`、定制产品代码 import `tests.*`、mock 非 stdlib import）逐条报错，报错含文件与 import 语句；对当前仓库运行通过；
- [ ] 四脚本与 `_common.py` 零第三方依赖（stdlib-only，含测试）；
- [ ] `aixcoding/tests/tools/` 配套测试全绿（`uv run pytest aixcoding/tests/tools -n0`）。

## 开放问题

- 无（5 个设计决策点已于 2026-10-25 经负责人确认，见 design.md 备选对比）。
