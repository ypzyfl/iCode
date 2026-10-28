# 自评审记录：tui 迁入实施

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-28
- 确认意见：无特别意见

## 实施概览

分支 `feat/tui_login`（基线 `main_aixcoding_cli` @ fdea034）：新增
`src/chrys/app/aixcoding/tui/` 5 文件 + `aixcoding/tests/tui/` 6 文件；上游接线 16 文件
（R2 表全表 approved）；i18n 三点登记落地。

## 关键自评点（含试错留档）

1. **容器方案 → sibling 方案的实测回退**（最重要教训）：实施先按 design 表 3 号的 0.28
   容器先例（`#header-badges` Horizontal 包三徽标）落地，Smart Test 全量跑出
   `test_app_restyle_budget` 红——`#approval-reviewing` 的 visibility/动态 margin 机制
   依赖 overlay dock 布局，移入容器即失效（诊断实录：容器内 badge region 溢出屏）。
   两轮修复尝试（cluster region 锚定 / badge region 反推）均败于布局时序，最终**回退为
   三 overlay sibling + 动态 margin**（`_place_login_badge`，与 0.31 reviewing 机制完全
   同构，`_refresh_review_count` 恢复上游原文零改动）。**教训：考古先例必须对照目标版本
   的同类机制现状——0.31 已把"多徽标错开"演进为动态 margin 模式，同构跟随优于形态平移。**
2. **假设九射程低估**：design 评审（外部 AI + peer review 两轮）只识别出 i18n 断言组
   必然红；全量实跑暴露测试基建的三个 `SlashCommandActions` 构造点硬依赖字段集（91 用例
   连带 TypeError）。结论：**字段集变更的连带面=构造点全集，评审期应 grep 构造点**——已
   作为 13-15 号补入 R2 表。
3. **包 `__init__` lazy 化**：eager `from .login import LoginDialog` 使 silent check
   启动路径连带加载对话框——改 PEP 562 `__getattr__`（实施发现，plan T1 留档）。
4. **ty 四轮修复**：`_before_dismiss` 参数 LSP（0.28 遗留）、dismiss 回调逆变
   （isinstance narrow）、Protocol `push_screen` 返回型/`notify` Literal 签名对齐——
   0.28 代码未过 0.31 的 ty 门槛，平移时须逐一对齐。
5. **mock fixture 用户名漂移**：0.28"大熊猫"→ PR #56 mock"测试员"（期望值对齐事实）。

## 与 design 的偏差清单（全部已回写 design 变更记录九/十/十一）

| 偏差 | 处置 |
|---|---|
| 容器方案失败 → sibling 改案 | design 表 3/4 号重写（十一） |
| R2 表 7-9 拆行 + mo 漏列 | 表 7-12（十） |
| 测试基建 4 文件新增改动 | 表 13-16（十一） |
| 登记节 bullet → 表格 / marker 格式修正 3 处 | 十（机器字段单源适配） |

## 遗留事项

- catalog 联动占位注释（D3）随 catalog 批次实调。
- auth/design.md wire_client 登记行 warning（既有，非本批）。
