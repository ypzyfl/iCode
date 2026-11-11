# 验证记录：0.35.2 手册内容同步（user-manual-v0.35.2）

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-11-11 官方改动范围与方向判定

命令：

```
git fetch https://github.com/openJiuwen-ai/iCode.git tag v0.35.2 --no-tags
git diff --stat v0.35.2 -- docs/zh-Hans docs/en docs/index.yaml
```

结果：`8 files changed, 12 insertions(+), 12 deletions(-)`——sessions/shortcuts/skills/
getting-started 的 zh+en 各 4 对文件；`index.yaml` 零变化。方向判定（`-` 侧 = v0.35.2）经
release notes 三重证据交叉确认（跨页搜索 / 两级子目录 / 引用统一块引用）。

## 2026-11-11 官方汇编生成与 diff 断言

命令（章级点替换脚本 `.tmp_build_ours.py`）：

```
python .tmp_build_ours.py   # 4 章替换 + 封面 2 行
git diff --no-index '...\20261109\0.35版本\AIxCoding-CLI用户手册.md' '...\20261111\0.35.2版本\AIxCoding-CLI用户手册.md'
```

结果：`1 file changed, 8 insertions(+), 8 deletions(-)`——封面 2 行 + getting-started 3 段 +
sessions/shortcuts/skills 各 1 行，与官方改动精确吻合；其余逐字节一致。
（首轮曾抓出章体末尾空行缺失——diff 净 -4 行暴露，补空行后重生成通过。）

## 2026-11-11 定稿生成与 diff 核对

命令（`.tmp_build_definitive.py`，每处替换前 count==1 断言）：

```
python .tmp_build_definitive.py
# 输出：6 处官方改动全部替换 ✓；版本行改 v0.35.2 ✓；版本号占位 5 处 → 0.35.2 ✓
```

diff 逐行核对：12+/12- = 版本行 1 + getting-started 3 段 + 构建信息章占位 5 + skills 1 +
shortcuts 1，另有 sessions 搜索行（经直接定位验证在文件中生效）。

## 2026-11-11 手册自检（SKILL §三）

命令：`.tmp_final_check.py` + `check_links.py <定稿md>`

结果：

```
品牌/禁用词命中合计: 0
结构问题: 0
内锚引用: 237 | 失效: 0 | 第三方外链: 0 | 裸 URL: 42
结论: PASS
```

## 2026-11-11 PDF 与书签

命令：`md2html.py` → Edge 无头打印 → `add_bookmarks.py`（内置自校验）→ pypdf 抽验

结果：书签写入 **50 条（7 部 / 32 章 / 11 节）**，自校验全绿；页数 137；首页链接注解 32；
`AIXCODING_CHANNEL: 1 | ICODE_CHANNEL: 0`；新内容抽验命中（"6 行及以上"、"下两级子目录"、
"每个未填的参数是一个整体"、"单击图片或引用标签可打开只读预览"、"搜索范围是复选框所选的全部会话"）。

## 2026-11-11 manual 同步

命令：`.tmp_sync_manual.py`（zh+en 10 文件 14 处，逐处 count==1）

结果：

```
✓ zh-Hans/start/getting-started.md ×3（官方 3 段）+ 1 处 ICODE_CHANNEL→AIXCODING_CHANNEL（评审 F2 补正）
✓ zh-Hans/guides/daily-use/sessions.md
✓ zh-Hans/guides/extensions/shortcuts.md
✓ zh-Hans/guides/extensions/skills.md
✓ en/start/getting-started.md ×3
✓ en/guides/daily-use/sessions.md
✓ en/guides/extensions/shortcuts.md
✓ en/guides/extensions/skills.md
✓ zh-Hans/guides/daily-use/build-info.md: 5 处 0.35.1 → 0.35.2
✓ en/guides/daily-use/build-info.md: 5 处 0.35.1 → 0.35.2
```

## 2026-11-11 门禁总检

命令：`audit_manual.py` / `check_links.py @全部md` / `check_docs.py` / `gen_customizations.py --strict`

结果：

```
基准: ...\20261111\0.35.2更新后\AIxCoding-CLI用户手册.md   ← 基准自动切换到本批次定稿
=== 审计通过：内容与基准逐章一致，锚点/外链/品牌/目录全绿 ===
结论: PASS   （check_links 全量）
check_docs: OK
gen_customizations: check OK — 109 registration row(s) / 150 marker(s) across 17 design(s), 7 retired id(s), 0 warning(s)
```

## 2026-11-11 手册契约测试

命令：`pytest tests\foundation\test_documentation.py tests\orchestration\invoker\test_documentation.py tests\orchestration\workflows\test_documentation.py tests\service\context\providers\test_documentation.py -q --basetemp=<TEMP>`

结果：`26 passed in 58.51s`（basetemp 置于 TEMP，仓库树无残留——承接 uv build 符号链接教训）。

注：同日曾跑 `tests/architecture` 全量得 11 failed / 1252 passed——与本批次无关（实证：
`test_chrys_test_summary` 2 例为中文 Windows GBK 代码页子进程输出解码失败，`PYTHONUTF8=1`
实测无效；architecture 属 Linux CI only，本机首次全量跑暴露既有环境性问题），详见 plan.md
「挂起与备忘」。

## 2026-11-11 wheel 重建与捆绑校验

命令：`uv build` → `uv pip install --force-reinstall dist\icode_tui-0.35.1-py3-none-any.whl
-p C:\work\icode-wheel-test\.venv\Scripts\python.exe` → `.tmp_bundle_check.py`

结果：`Successfully built dist\icode_tui-0.35.1-py3-none-any.whl`；捆绑校验：

```
bundle md: 64 | manual md: 64
MD5 不一致: 0 []
✓ 下两级子目录 → zh-Hans\guides\extensions\skills.md
✓ 每个未填的参数是一个整体 → zh-Hans\guides\extensions\shortcuts.md
✓ 搜索范围是复选框所选的全部会话 → zh-Hans\guides\daily-use\sessions.md
```

## 2026-11-11 docs/ 镜像追平（责任人裁决后的补充执行）

命令：

```
git checkout v0.35.2 -- docs/zh-Hans/start/getting-started.md docs/zh-Hans/guides/daily-use/sessions.md docs/zh-Hans/guides/extensions/shortcuts.md docs/zh-Hans/guides/extensions/skills.md docs/en/start/getting-started.md docs/en/guides/daily-use/sessions.md docs/en/guides/extensions/shortcuts.md docs/en/guides/extensions/skills.md
git diff --stat v0.35.2 -- docs/zh-Hans docs/en docs/index.yaml
git status --short -- docs/
```

结果：`git diff v0.35.2 -- docs` **输出为空（完全追平）**；`git status` 显示 docs/{zh-Hans,en}/
8 文件 M（内容 = 纯官方 0.35.2 原文，净 12+/12-）。批准：责任人 2026-11-11 聊天裁决
（方案 B），随本批次一起提交，R2 落盘于 design.md 签认。

## 2026-11-11 en 侧追平清单（评审 F1 扩围登记）

命令：

```
git status --short -- aixcoding/manual/en
```

结果：en M 27 = 本批次 5（build-info/sessions/shortcuts/skills/getting-started）+ **追平类 22 整文件**：

```
en/guides/configuration/agents.md、approval.md、compaction.md、models.md、settings.md、
tools.md、web-tools.md
en/guides/daily-use/workspaces.md
en/guides/extensions/hooks.md、mcp.md、python-extensions.md
en/guides/running/icode-acp.md、icode-run.md、terminal-status.md、workflows.md
en/reference/agent-profile.md、hooks.md、settings.md、themes.md、tool-kinds-and-names.md、workflows.md
en/start/what-is-icode.md
```

改动性质（= user-manual 批次 en 对齐的未提交延续 + ACP 表述清扫，方向与本批次验收门
"禁用词 0（含 ACP）"一致，内容由 audit_manual zh+en 双语章级比对背书）：

- en/guides/configuration/models.md：整章重写（Configure models → Switch models，对齐 zh 侧
  "切换模型"口径）；
- en/start/getting-started.md：删 uv 安装章节（110 → 74 行）；
- en/guides/running/icode-acp.md：ACP 说明增补（+254 行）；
- 全树：`icode serve`→`aixcoding-cli serve`、`icode-ocean.yaml`→`aixcoding-cli-ocean.yaml`、
  ACP 表述清扫、模型配置措辞统一；
- 本批次 en 5 文件内另混入追平 hunk（如 en sessions.md 删 ACP 复选框句、models 链接改写）；
- zh 侧同批 1 处：zh-Hans/start/getting-started.md 的 ICODE_CHANNEL→AIXCODING_CHANNEL。

## 2026-11-11 桌面交付

- `Desktop\用户手册\20261111\0.35.2更新后\`：MD（版本行如实抄录：`版本 v0.35.2 ｜ 本手册撰写于2026年11月11日`，评审 F4 修正）+ PDF（书签版）
- `Desktop\用户手册\20261111\0.35.2版本\`：官方汇编（下轮基线）
- `Desktop\用户手册\20261110\icode_tui-0.35.1-定制手册版-py3-none-any.whl`：覆盖同步
- 清理：临时脚本/diff/TEMP 产物删除，`markdown` 依赖卸载（`uv pip uninstall`）
