# 自评审记录：auth 测试隔离 + mock 动态端口（auth-isolation-mock-ports）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-01
- 确认意见：无特别意见
- 开发 AI：CodeBuddy（BM:GLM-5.3）
- 评审 AI：Kimi-K3.1-Pro（用户中转，四轮评审——方案 F 系列 → 复审 R 系列 → 代码 S 系列 →
  批次 T 系列，与主力开发 AI 不同源）

> 评审形态如实声明：本批代码的评审是"local-verify 方案三轮评审链的第三轮"——评审 AI 在
> 第三轮将实际代码改动（工作区 diff）纳入复审并独立复跑（324 passed / 2 skipped /
> 11.79s，与 verification.md V1 一致），并非按 SELF-REVIEW-HOWTO checklist 独立起跑的
> 专项评审。是否需要补一轮完整 checklist 评审，由责任人在签认时裁决。

## 2026-11-01 评审结论：通过（S-01/S-04 已修复复验，无未修项）

- 轮次：方案与代码合计三轮（每轮 = 评审 + 修复 + 复审）；本批代码对应第三轮（S 系列）
  及其修复复验，前两轮（F/R 系列）评的是方案与预案材料（留痕：temp/2026-11-01-custom-
  test-strategy/ 讨论集 + local-verify/design.md 末节处置记录）

- blocker/major 处置：
  - S-01（major，代码）：launcher round-trip 测试硬编码三 starter，`_SERVICES` 新增服务
    （telemetry 预告）不自动纳入 → 已修复：恢复遍历 `launcher._SERVICES.values()` +
    `starter(port=0)`，注册表语义与零固定端口依赖并存；复验 119 passed / 全量 324 passed
    （verification.md V2#2/#3）
  - S-04（minor→已修，代码）：防退化锚点只断言 backend，docstring 声称 config-dir 同锁 →
    已修复：补 `auth_session.default_config_dir() == tmp_path` 断言（fixture 实例共享）；
    复验同上
  - 代码质量面复审确认项（评审 AI 列"已检查无新增问题"）：autouse patch 落点正确
    （`default_config_dir`/`_default_backend` 均为 `LoginSession` 默认构造的模块级查找名）；
    真实平台 backend 测试零交集不受影响；三 starter 默认端口不变、CLI fail-fast 语义未改；
    释放探测用实际 bind 端口；零上游文件、范围符合批准

- 未修项（次要问题，责任人拍板不修）：无——S-02/S-03 为文档项且已处置：
  - S-02：loopback 请求捕获能力不足 → 修订 temp 20 号材料（组合测试批次 test-plan 硬性
    要求），非本批范围
  - S-03：文档状态滞后 → requirements/plan/overview 三处已同步更新

## 2026-11-01 第四轮评审（self-review 落盘后的完整批次评审）：处理后通过

评审 AI 对三份材料（plan/verification/self-review）与实际实现做只读评审并独立复跑
（119 passed / 324 passed 2 skipped，与记录一致），发现 1 应修 + 2 收尾项：

- T-01（应修，代码）：`_Services` 类型别名仍声明零参 starter（`Callable[[], ...]`），
  测试 `starter(port=0)` 过不了类型检查（`unknown-argument`，pytest 不覆盖类型面），且
  会误导 telemetry starter 实现成零参 → **已修复**：改 `Callable[..., ...]` 并加注释
  说明双调用形态（CLI 无参 / 测试 port=0）；复验：`ty check` 目标文件 unknown-argument
  消除（仅剩 1 个存量动态属性诊断，非本批引入；ty 门规范口径不查 aixcoding/），
  ruff 通过，119 passed（verification.md V3）
- T-02（收尾）：批次目录未登记 `INDEX.md`（DEVELOPMENT.md §6 登记义务，local-verify
  同漏）→ **已补**：两个批次目录各一行
- T-03（收尾，流程）：①评审 AI 标识不具体 → 头部改为"待责任人补记"；②S-01/S-04 修复
  增量的复审未落盘 → **补记**：本轮（第四轮）即同一评审 AI 对第三轮修复增量的复审
  （独立复跑 + 代码审查 + 发现 T-01），连同本节落盘闭环

评审 AI 另确认（"已核实通过"节）：autouse patch 落点正确、三 starter 返回实际绑定端口、
CLI 默认端口与 fail-fast 路径未变、四个代码文件 ruff/format 通过。
