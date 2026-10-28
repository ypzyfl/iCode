# 验证记录：ADR-0011 存量定制包按 tier 回迁 kernel 档

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；真实性由双 AI 自审与评审抽查保障。

## 2026-10-27 四项验证全绿 + 生成产物刷新

环境：`set PYTHONPATH=`（脱离 shim）、`set PYTHONUTF8=1`、大写盘符 `D:\`、`set UV_PYTHON=3.14.3`。

1. **上游架构测试**：

   ```
   uv run pytest tests/architecture -q -m "not integration and not gc_calibration"
   ```

   结果：**1237 passed, 3 skipped**（首轮 1236 passed + 1 failed——`test_trajectory_wait_inventory`
   报 13 个 `chrys.kernel.aixcoding.auth.*` wait 节点未分类；按提示执行
   `uv run python -m tests.support.trajectory_wait_inventory` 刷新 manifest（+33 行，纯新增
   kernel 条目、无旧条目残留）后全绿。**此为 ADR-0011 联动清单未预见、由测试暴露的第 6 处
   真实联动：trajectory wait manifest 是按模块路径登记的生成产物**）。

2. **定制测试全量**：

   ```
   uv run pytest aixcoding/tests -q
   ```

   结果：**263 passed, 2 skipped**（含 tools 夹具 4 文件更新后自检、diagnostics
   panel_anchor 锚定测试零改动通过）。过程事故（如实记录）：首轮脚本对测试文件误用
   "包内相对化"规则（测试目录不属于产品包，10 个文件 `from .x import` 崩）；处置 =
   `git checkout` 恢复后改用纯前缀替换规则重跑，复测全绿。**教训：测试文件与产品包的
   import 改写规则不同（绝对 vs 相对），机械替换脚本须按目录区分**。

3. **ty 静态检查三平台**：

   ```
   uv run ty check --error-on-warning --python-platform linux src/chrys   # darwin / win32 同
   ```

   结果：三平台均 **All checks passed!**。

4. **wheel 冒烟**：

   ```
   uv build --wheel   →   dist/icode_tui-0.31.0-py3-none-any.whl
   python -c "...zipfile 检查..."
   ```

   结果：wheel 内 **16 个 `chrys/kernel/aixcoding` 条目**（`__init__` + auth 9 + diagnostics 6），
   `src/chrys/aixcoding/` 旧路径零存在（断言通过）。

5. **附加核对**：
   - `gen_customizations.py` 重新生成成功（5 定制点、1 个既有 warning——auth design 的
     wire_client token 注入登记行无匹配标记，回迁前已存在，非本批次引入）；
   - 全库旧前缀 grep 清零：代码类文件（py/yml/toml/cfg/sh）`chrys.aixcoding` 与
     `src/chrys/aixcoding` 双形式零命中；md 残留全部在 R8 白名单内（auth/*、diagnostics/*、
     mock/design.md、adr/0002/0005/0011、restructure/plan.md P4-P6、ROADMAP:106-107、
     archaeology-report）+ 3 处有意保留（gen_customizations 考古兼容 bases、
     test__common 旧路径负例 fixture、mock/update docstring）；
   - `check_docs.py` OK（实施中 design 正文有过联动修订，见 plan 挂起事项）。

## 2026-10-28 双 AI 评审处置后的门禁复验

1. R2 门禁：

   ```
   uv run python aixcoding/tools/check_r2_diff.py --base main_aixcoding_cli
   ```

   结果：**OK**（changed=56，upstream_changed=6，approved_pool=8——R2 表补录 manifest 与
   `src/chrys/aixcoding/__init__.py` 删除后由 6 → 8）。

2. R3 门禁：

   ```
   uv run python aixcoding/tools/check_r3_markers.py --base main_aixcoding_cli
   ```

   结果：**OK**（marker_checked=5，exempt=1——manifest 走豁免表；`AGENTS.md:8` 句末标记、
   `wire_client.py` 注释块末独立标记行均为前缀形态）。

3. 清单与工具自检：

   ```
   uv run python aixcoding/tools/gen_customizations.py        # 7 custom point(s)
   uv run pytest aixcoding/tests/tools -q                     # 53 passed
   ```

   过程记录（如实）：R3 首跑 3 violation（AGENTS.md 新增行无标记、wire_client 新增行无标记、
   manifest 豁免格式未登记）→ 三处处置（行内/独立标记 + `MARKER_EXEMPTIONS` 常量渲染豁免表）
   → 复跑 OK；标记迭代 2 次（括号内形态不满足"注释体前缀"规则、S1 残留 "The"）→ 终态前缀
   形态独立行。
