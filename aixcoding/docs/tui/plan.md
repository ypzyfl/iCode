# 计划：tui 迁入实施

## 步骤（T1-T8，全部完成）

- **T1 产品代码**：`src/chrys/app/aixcoding/tui/` 5 文件（login.py/login.tcss/
  login_indicator.py/login_actions.py/__init__.py）——login.py 0.28 平移 + import 前缀改 +
  Design 指引行；login_indicator.py D2 改写（去 localizer、中文常量、死注释不迁）；
  login_actions.py 新建（Protocol 化 host 协议、LoginDialog 函数内 lazy import、
  catalog 占位注释）；__init__.py PEP 562 `__getattr__` lazy 导出（实施发现：eager import
  使 silent check 启动路径连带加载对话框）。
- **T2 R2 接线**：screen.py（silent check 挂 MainScreen——改进一）+ commands.py 三层 +
  app_header.py（**实施改案：三 overlay sibling + 动态 margin**，容器方案实测失败回退，
  见 self-review）+ chrys.tcss + diff/screen.py + pyproject RUF001。
- **T3 测试迁入**：`aixcoding/tests/tui/` 6 文件（conftest 主题 fixture + wait_until
  本地实现；期望值全部中文化；wiring 含挂点断言 2 用例）。
- **T4 i18n 流水线**：extract（pot +25 行）/ update / po msgstr 手工填 fallback 复制 /
  compile（mo）/ oracle 登记 4 key + size 2405 / `/man` 索引期望 +2 行。
- **T5 上游测试适配**（实施实测新增）：tui_helpers / toast_notifications / buddy_petting
  三处 `SlashCommandActions` 构造 +2 stub 字段；screen_lifecycle 宿主 +1 属性。
- **T6 验证**：分层单套 + ruff + ty（win32）+ i18n check + R2 门禁 + gen_customizations +
  check_docs；Smart Test 全量（--paths 含 pyproject 自动升级）。
- **T7 文档联动**：DIRECTORY.md §8 例外表核销（预登记→已登记）；CUSTOMIZATIONS 再生成；
  design 变更记录（九）（十）（十一）留痕。
- **T8 六文档补齐**（本批）：requirements / plan / test-plan / self-review / verification。

## 风险与应对（实施后复盘）

- **容器方案试错**（已回退）：0.28 容器先例与 0.31 overlay 机制冲突——教训：**考古先例
  必须对照目标版本的同类机制现状**（0.31 已把"多徽标错开"做成 reviewing 动态 margin 模式，
  同构跟随优于形态平移）。已写入 self-review 与 design 表 3 号归属结论。
- **假设九射程低估**（已扩面）：测试基建的构造点硬依赖字段集，不只断言文本——design 已
  补 13-16 号行。
- **gc_freeze_calibration 满载 flaky**：在案已知（单跑绿），与本批次无关。

## 挂起与备忘

- catalog 批次到时替换 `login_actions.py` 两处占位注释为实调（D3）。
- 遗留 warning（既有非本批引入）：auth/design.md wire_client 登记行无 marker
  （tier-migration 批次在案的 designed-not-implemented）。
