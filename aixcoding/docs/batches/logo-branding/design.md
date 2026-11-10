# 设计：TUI 欢迎字符画品牌化（logo-branding）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-10
- 确认意见：无特别意见

## 方案概述

`logo.py` 三幅字画中仅 `TUI_LOGO` 含 iCode 品牌词，整幅替换为 "AIxCoding" 块字符字形
（`{▀▄█}`，上游同族）；`CHAT_LOGO`（Chat/iChat 合体首字母）与 `WORKFLOW_LOGO`（整幅即
"Workflow"，2026-11-10 字形复核确认）均不含 iCode 品牌词，保持上游原样零改动。serve 终端
banner（`_icode_serve_logo`，C062 纯 ASCII）同批改为 `{▄,█}` 受限子集——实测 `▀` 在 GBK
编码 stdout 下经 Rich `console.print` 直接 `UnicodeEncodeError` 崩溃（serve `on_startup`
崩死），`▄`/`█` CP936 可编码、Rich 实测安全通过。品牌字稿不追求逐字相同，而是同一品牌在
输出介质约束下的同族适配。

```
logo.py（上游触点①：TUI_LOGO 常量字面量 + 模块 marker）
 └─ TUI_LOGO ────► TUI 启动加载壳（app.py compose，断言自适应）
                   ＋ serve 浏览器 splash 注入（serve.py，UTF-8 HTML）
                   ＋ serve auth 登录页（serve.py，UTF-8 HTML）
（CHAT_LOGO / WORKFLOW_LOGO：零改动——2026-11-10 责任人裁决 + 字形复核；
 二者消费点与 [:6]/[:8]/90 宽 compact 断言全部原样通过）
serve.py（上游触点②：_icode_serve_logo 函数体 + docstring + marker，{▄,█} 子集）
 └─ banner ──────► textual-serve console.print 直出（GBK 编码 stdout 实测门禁）
```

## 裁决记录（2026-11-10，全部闭合）

1. **管线**：完整管线（微改动豁免三条件①触及上游文件不满足，已呈报裁决）。
2. **字形形态 = 块字符**：两轮外部评审与实测复核——CP936 仅 `▀` U+2580 不可编码
   （`▄` U+2584→A8 7B、`█` U+2588→A8 80 可编码）；上游三幅现状已用同组字符服务全部
   消费点（Textual 渲染/浏览器 HTML，不经 GBK console.print），字样替换不新增风险。
   C062 的 ASCII 先例属"新 banner 设计"场景，与本批"既有块字符字样替换"场景不同，
   仅作参考不构成约束。
3. **TUI_LOGO**："iCode" → "AIxCoding"（块字符主字形，字稿见「字稿定稿」）。
4. **CHAT_LOGO 保持原样不动**：整幅读作 "Chat"（首字母为 i/C 合体字形，亦可读作
   "iChat"），两种读法均不含 iCode 品牌词；`[:6]` 断言与消费点零跟改。
5. **WORKFLOW_LOGO 保持上游原样不动**（2026-11-10 字形复核修订）：整幅即 "Workflow"，
   不含 iCode 品牌词。原裁决"去 iCode、保留 Workflow"所依据的 "iCode Workflow" 解读
   系误判，逐行切割稿（原附图 B）作废；`[:8]` 断言、90 宽 compact 分支断言与消费点
   零跟改。
6. **serve banner = `{▄,█}` 受限子集并入本批**：同族视觉；**禁止 `▀`**（GBK 崩溃实证）。
   此为 C062 "pure ASCII, safe on GBK consoles" 已签认决策的修订：防崩溃语义保持
   （编码层安全），字形族从 ASCII 切到块字符子集；C062 的 removal_condition（随 C050
   品牌政策变更时逐点裁决）正构成本批裁决时机。
7. **字稿定稿方式**：原拟委托外部多模态 AI 加工；实际执行为 AI 按上游风格组件起草、
   责任人逐轮考察定稿（2026-11-10，`A` 脚 `▀`→`▄`→`█` 两轮修订），两份字稿已回填
   「字稿定稿」节，随本 design 签认。

## 消费点可用宽度预算（实测，2026-11-10）

> 方法：临时探针测试（parametrize 90/100/140 终端宽，`run_test` 直读
> `WelcomeWidget.size.width`；字形宽度 `rich.cells.cell_len`；CP936 编码能力
> `str.encode('cp936')`；Rich 崩溃行为 `PYTHONIOENCODING=gbk` 下实跑）。探针跑完已删
> 除，工作区无残留。

| 消费点 | 介质 | 90 宽可用宽 | 现字形宽 | 结论 |
|---|---|---|---|---|
| 启动壳 | 终端（Center 居中） | 90 | TUI_LOGO 现 29 → 新稿 51 | 断言动态自适应（20 宽参数覆盖裁剪语义）；✓ |
| Chat 空态（无 compact 回退） | 终端 | 45 | CHAT_LOGO 25（**不动**） | 零改动、断言原样；✓ |
| Workflow 空态（compact 回退） | 终端 | 46 | WORKFLOW_LOGO 56（**不动**） | >46 保持触发 compact，90 分支断言零跟改；✓ |
| serve splash / 登录页 | 浏览器（UTF-8 HTML） | — | 29 → 新稿 51 | 无宽度断言；✓ |
| serve 终端 banner | console.print 直出 | — | 现 52（ASCII）→ 新稿 51 | `{▄,█}` 门禁 + GBK 实跑测试；见验收 |

CP936 / Rich 实测：`▀` U+2580 → `UnicodeEncodeError`（Rich `legacy_windows_render` 路径
traceback 在案，裸 `print` 同崩）；`▄` U+2584 → A8 7B、`█` U+2588 → A8 80，Rich 实跑安全
输出；`▀` GB18030 可编码（81 37 99 32）但 CP936 控制台程序无此能力。"安全"限定为**编码层
安全**：`▄█` 不因 CP936 崩溃；字形外观仍取决于终端字体与渲染器，不承诺所有终端完美无缝。

## 字稿定稿（2026-11-10：AI 起草 + 责任人逐轮考察定稿）

> 定稿方式以裁决记录 7 为准（原拟外部多模态 AI 加工，实际未启用）。两稿同源（同一套
> 字母组件表），由临时拼装脚本生成并自验硬约束（脚本用后删除）；实跑截图列入实施验收。

### 稿一：TUI_LOGO = "AIxCoding"（块字符主字形，定稿）

- **字符集**：`{▀, ▄, █}`（块字符，上游同族；空格分隔）。
- **字稿**（51 列 × 7 行）：

  ```text
   ▄██▄  ▀██▀        ▄███▀
  ██  ██  ██        ██▀             █▄
  ██  ██  ██        ██              ██ ▄
  ██████  ██  ▀█▄█▀ ██     ▄███▄ ▄████ ██ ████▄ ▄███▄
  ██  ██  ██   ▄█▄  ██▄    ██ ██ ██ ██ ██ ██ ██ ██ ██
  ██  ██ ▄██▄ ▄█▀█▄  ▀███▄ ▀███▀ ▀███▀ ██ ██ ██ ▀████
                                                 ▀██▀
  ```

- **设计要点**：大写 `A`/`I`/`C` 全高衬线（`A` 满格直腿收底、`I` 顶 `▀██▀` 底 `▄██▄`
  衬线）；小写用上游圆弧组件（`▄███▄` 顶、`██ ██` 身、`▀███▀` 底；`n` 借上游 `h` 的
  `████▄` 拱）；`d` ascender 高两格、`i` 点高一格、`g` descender 下伸一行（上游"上细节
  下主体"层次）。
- **硬约束与自验**：无行数硬约束（`test_startup_shell` 断言全动态自适应，20 宽裁剪语义
  已覆盖）；宽度建议 ≤52 ✓（逐行 `cell_len` 实测 `[24, 36, 38, 51, 51, 51, 51]`）；
  字符集 `{▀,▄,█,空格}` ✓；每文本行一整行 ✓。
- **待实施验证**：实跑启动壳截图人工核对。

### 稿二：serve banner = `{▄,█}` 受限子集（定稿）

- **字符集**：**仅 `▄` 与 `█`，禁止 `▀`**（GBK 编码 stdout 下 Rich 崩溃实证；两条新增
  测试锚定）。零 `▀` 已脚本自验 ✓。
- **字稿**（51 列 × 6 行；`v{__version__}` 版本行照现状接第 5 行尾 `▄████` 之后）：

  ```text
   ▄██▄  ▄██▄        ▄███▄
  ██  ██  ██        ██              █▄ ▄
  ██████  ██  █▄ ▄█ ██     ▄███▄ ▄████ ██ ████▄ ▄███▄
  ██  ██  ██   ▄█▄  ██▄    ██ ██ ██ ██ ██ ██ ██ ██ ██
  ██  ██ ▄██▄ █▄ ▄█  ▄███▄ ▄███▄ ▄███▄ ██ ██ ██ ▄████
                                                 ▄██▄
  ```

- **与稿一关系**：同字母结构、密度减半适配——大写 5 行（稿一 6 行）、`I` 顶 `▄██▄`
  （上下对称）、`C`/`o` 底弧 `▄███▄`、`x` 沙漏形 `█▄ ▄█ / ▄█▄ / █▄ ▄█`；`A` 直腿、
  `d`/`i`/`g` 层次保留。差异全部由 `▀` 禁用驱动，非为差异而差异。
- **保留**：现有 f-string 结构、`[bold magenta]` 样式与 `v{__version__}` 版本行；函数名
  `_icode_serve_logo` 不变。
- **docstring**："pure ASCII, safe on GBK consoles" → "GBK-safe block subset: no U+2580,
  which CP936 cannot encode"（实施定稿）。
- **待实施验证**：`PYTHONIOENCODING=gbk` 下输出完整 banner 不抛异常（新增测试，进 CI）；
  banner 无 `▀`（新增静态断言）；实跑截图人工核对。

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/tui/util/logo.py` | 仅 `TUI_LOGO` 替换为稿一（6 行 → 7 行）；`CHAT_LOGO`/`WORKFLOW_LOGO` 零改动 | +~8 / -~6 | 模块 docstring 下方 marker×1（覆盖 TUI_LOGO） |
| `src/chrys/app/cli/serve.py` | `_icode_serve_logo()` 函数体 ASCII → 稿二（5 行 → 6 行）；docstring 更新 | +~7 / -~6 | 现有 marker 文本更新（原 C062 锚含 "ASCII" 不再成立） |
| `tests/app/cli/test_serve.py` | banner 断言跟改（C064 处，锚不变内容维护）；新增 GBK 编码 stdout 输出不抛异常、banner 无 `▀` 两条测试（独立锚登记 C151-C152 孪生组）；另 4 处硬编码旧 TUI_LOGO 片段断言（`test_inject_browser_serve_branding_logo_preserves_logo_spacing`、`test_auth_required_protects_tui_and_websocket_until_login`、两处 `*_injects_browser_clipboard_support`）改为动态引用 `TUI_LOGO.splitlines()` 行片段——假设 1 预留红面实证，与 `test_startup_shell` 动态引用先例同模式，消除下次换稿再红 | ~+26 / -~6 | 既有 marker 处（C064）＋4 处动态引用断言各加 marker×1（C147-C150 孪生组计数 4，2026-11-10 F4 责任人裁决：我方改动行须可追踪）＋GBK/无 `▀` 两用例各加 marker×1（C151-C152 孪生组计数 2） |

定制层测试跟改（非上游触点，不入 R2 表）：`aixcoding/tests/branding/test_branding_runtime.py`
的 `test_c062_serve_banner_is_ascii_aixcoding` 更名为
`test_c146_serve_banner_gbk_safe_block_aixcoding`，断言换为稿二行 + 无 `▀`（C062→C146
语义继承）。

R1 自查（必答）：业务逻辑全部外置？——无业务逻辑，仅字面量与既有断言维护；接线点最小
化？——零新增接线点：三个 TUI 消费点与两处 serve HTML 注入均经既有常量引用，消费点代码
零改动，`logo.py` 单文件即令五个消费点生效。

## 对上游隐式行为的假设

| # | 上游行为 | 我方依赖方式 | 失效表现/检测 |
|---|---|---|---|
| 1 | `test_startup_shell.py` 全部断言动态引用 `TUI_LOGO` 常量（行数、宽度、居中、20 宽裁剪语义） | 稿一替换后断言自适应，零跟改 | 未发现的硬编码字样断言会红面——实证：`test_serve.py` 4 处硬编码旧片段红面（Smart Test 2026-11-10），已改动态引用（R2） |
| 2 | `test_workflow_welcome.py` 的 `[:8]` 断言对应 `WORKFLOW_LOGO` 8 非空行 | `WORKFLOW_LOGO` 零改动，断言原样通过 | 无失效面 |
| 3 | 同测试 `[:6]` 断言与 `CHAT_LOGO` 相关 | `CHAT_LOGO` 零改动，断言原样通过 | 无失效面 |
| 4 | 同测试 90 宽分支 `workflow_rows[0] == "Workflow"` 依赖 `WORKFLOW_LOGO` 最宽行 > 46（现 56） | 零改动，compact 触发保持、断言原样通过 | 无失效面 |
| 5 | serve 两处 `html.escape(TUI_LOGO)` 注入 UTF-8 HTML | 块字符 HTML 安全（上游现状已实证） | 注入本身无失效面；其测试的硬编码片段红面见假设 1（已跟改）；serve 冒烟核对 |
| 6 | `WelcomeWidget` 的 `cell_len` 居中与 `_visible_logo` compact 切换 | 块字符 `cell_len` = 精确单宽（与上游一致） | 无失效面；现有测试覆盖 |
| 7 | textual-serve banner 经 `self.console.print` 直出（`serve.py:834`，依赖其 internals，上游注释要求 bump 时重审） | 稿二 `{▄,█}` 保证 CP936 编码层不崩（实测）；新增两条测试充当回归哨兵 | 换稿引入 `▀` 或 textual-serve 渲染路径变化 → 新增测试红面 |

## 定制点登记预告

> id 自 C145 起（现高水位 C144）。C062 因 marker 锚文本含 "ASCII" 不再成立而**退役**
> （removal 记录见下），从 branding-and-command 现役登记移入本批退役记录；原 design 保留
> 指向说明并由责任人按 R10 一并重签（本 design 同：2026-11-10 实施修订——登记锚定稿、
> C062 迁移、定制测试跟改补充、C147-C150 登记（F4 裁决）——待重签）。后继点 C146 登记。C064 锚
> 不变、断言内容维护；两条新增 GBK/无 `▀` 测试独立登记 C151-C152（原拟并入 C064 孪生组，
> 因 C064 为历史单 id、C065-C078 已占用致区间不可扩，改独立锚；计数以 `--strict` 对账为准）。
> 实施后实跑对账。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C145 | src/chrys/app/tui/util/logo.py | AIxCoding branding: TUI welcome wordmark | 1 | `TUI_LOGO` 常量 | 低 | 〔品牌政策〕随 C050：品牌字形再次变更时逐点裁决 |
| C146 | src/chrys/app/cli/serve.py | AIxCoding branding: GBK-safe serve banner | 1 | `_icode_serve_logo` 输出 | 低 | 〔品牌政策〕随 C145 |
| C147-C150 | tests/app/cli/test_serve.py | AIxCoding branding: logo assertions track TUI_LOGO | 4 | 4 处 splash/登录页/clipboard/spacing 断言动态引用（F4 评审后责任人裁决登记：我方改动行须可追踪，防追上游漏判） | 低 | 〔品牌政策〕随 C145 |
| C151-C152 | tests/app/cli/test_serve.py | AIxCoding branding: banner GBK assertions | 2 | GBK 编码 stdout 不崩 + 无 `▀` 静态断言两用例（原拟并入 C064，因 C064 为历史单 id 且 C065-C078 已占用、区间不可扩，改独立登记） | 低 | 〔品牌政策〕随 C146 |

### 退役记录

| id | 原落点 | 退役日期 | 依据 |
|---|---|---|---|
| C062 | src/chrys/app/cli/serve.py | 2026-11-10（随本批实施） | marker 锚 "ASCII serve banner" 随 `{▄,█}` 子集字形变更不再成立；防崩溃语义由 C146 继承（`▀` 禁用 + GBK 测试）。C4 "不改为 block 字形"决策经实测证据修订（见裁决记录 6） |

## 风险与最坏情况

- **字稿实跑观感不达**：字稿已定稿（脚本自验硬约束通过），但终端字体/渲染器下的外观不
  承诺完美；实跑截图若明显不达，修订字稿并重新签认 design。
- **banner `{▄,█}` 视觉效果差**：子集表达力受限（无上半块，顶部细节用 `▄` 表达）；实施
  出图后若明显差于 `#` 形，回退路径 = 保留 ASCII（C062 不退役、C146 撤销，design 重签）；
  两条 GBK/无 `▀` 测试在任何路径下保留（防回归）。
- **上游升级**：`logo.py`/`serve.py` 低概率冲突；`gen_customizations --strict` 对账 +
  UPGRADE-RUNBOOK 既有流程覆盖；textual-serve banner internals 依赖由上游注释标注、
  新增测试充当回归哨兵。
- **回滚**：纯字面量替换，revert 即完整回滚，无持久状态、无公开契约变化。

## ADR 判定（DEVELOPMENT.md §6）

1. 有被认真考虑但否决的备选？——有：纯 ASCII 形态、三幅全换（CHAT_LOGO 已撤回）、
   WORKFLOW_LOGO 切割去 "iCode"（字形复核确认原图即 "Workflow"，无需任何改动，方案撤销）、
   banner 全块字符（`▀` 崩溃实证否决）、banner 保持 ASCII（字形族分裂否决）。
2. 撤销代价高？——**否**：字面量替换 revert 即回滚，无持久状态与公开契约变化。
3. 约束未来工作？——**轻**：字形维护归 C050 族品牌政策；banner `{▄,█}` 约束由测试锚定。
4. 依赖上游非公开行为？——**否**：仅消费公开常量与既有渲染路径；banner 对 textual-serve
   internals 的既有依赖（上游注释明示）随两条新测试获得回归哨兵。

结论：不触发新 ADR（与 C4 品牌字面量定制先例同类；C062 修订属 removal_condition 预设的
品牌政策变更路径，非架构决策）；无新增第三方依赖（R11 无涉）、无新增环境变量
（DIRECTORY.md §9 无涉）、无新增 tier 落位（R9 无涉）。
