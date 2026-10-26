# 任务清单：auth 迁入

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。

## 状态

双 AI 自审收敛（1 轮：评审无 blocker + 修复 4 项 + 复审过），self-review.md 待责任人签字，
随后提交审批。

## 待办

- [x] design 签认（2026-10-26；四轮外部评审闭环）
- [x] 探针式接线 + `check_r2_diff` 验证集合收敛（途中发现并修正 R2 节标题格式失配：
      自创后缀 → 标准形态 `（R2）`，语义零变化，待重签认）
- [x] auth 9 文件迁入 `src/chrys/aixcoding/auth/`（import/docstring/示例统一改
      `chrys.aixcoding.auth`，Sphinx 交叉引用含 `~`/`:mod:` 两形态，grep 终验残留 0）
- [x] env 更名（`environments.py` 常量×2 + docstring 4 处含 :24-25 语义反转改写；
      `delegation.py` 常量×3 + docstring 2 处；兼容通道 `AIXCODING_USER_EHR`/`OPENAI_API_KEY` 未动）
- [x] `environments.py:11` mock 路径引用同步（`mock_server/aixcoding_auth` → `aixcoding/mock/auth`）
- [x] types/errors 补 Design 指引行（对齐 diagnostics 形态）
- [x] 7 测试迁入 `aixcoding/tests/auth/`（import 18 处 + env 字面量 6 处 + mock import 3 处；
      文件头 noqa S101/S106/S107 按 mock 批次先例）
- [x] mock 集成断言适配 PR #56 fixture（`ehr 8769092→1234567`、`name 大熊猫→测试员`、
      `token_type AICoding→aixcoding-cli`，共 8 处 mock 往返断言；测试自构数据不动）
- [x] mock 联动更名（`aixcoding/mock/` 代码+README 全量；`docs/mock/design.md` 5 处机械联动
      + 文末变更记录，:121/:130/:151-152 历史记录不回改）
- [x] 阶段验证：`pytest aixcoding/tests/auth` 93 passed；ruff check/format 绿；
      `check_import_boundaries` OK；`check_docs` OK；全仓 `CHRYS_AUTH_` 残留 7 文件全部
      符合"不回改"定性（DIRECTORY.md:134 为规则描述自身）
- [x] **R10 重新签认**（R2 节标题格式修正属正文改动）→ 解锁上游完整实现
  （2026-10-26 负责人确认"延续原签认效力，继续"，已记录于 verification.md）
- [x] `clients.py` 完整 `_login_token()`（探针态空函数 → 0.28 原文平移，docstring 的
      `catalog._catalog_token` 悬空引用改自含表述）+ `_build_default_headers` docstring 尾部两句
- [x] `wire_client.py` `RequestHeaders.stamp()` 完整注入（try 包 import + 语义注释块 +
      早退条件扩展 + `headers["token"]` 赋值）
- [x] 新增 `test_llm_token_wiring.py`（7 例：通道 1 stamp 直驱 + 通道 2 真实 openai SDK +
      MockTransport wire 级；全部跑绿）
- [x] 全量门禁：定制侧 263 passed 2 skipped；`tests/service/llm` 2047 passed；Smart Test
      16740 passed（1 满载 flaky 单跑绿）；ty 三平台 exit 0（14 行级 ignore 覆盖 16 错 +
      2 真类型修复）；ruff/format 绿；四工具全 OK；marker module `login→auth` 修正 + 登记节
      标题第二处全等匹配坑修正；CUSTOMIZATIONS.md 刷新（7 定制点）
- [x] 双 AI 评审第一轮（Deepseek-V4-Pro）：无 blocker；修复 F-2（design R2 表 marker 措辞
      同步 auth）+ F-3（verification ty 计数更正 14 行/16 错）+ F-4（conftest autouse 钳制
      delegation 检测，隔离进程 env 兼容通道）+ F-1 定性补句（test-plan 通道 2=外部依赖行为
      探针）；不修 F-1 代码/F-5（stamp import 失败分支静默——注释已声明降级语义，上游改名
      场景由 tests/service/llm 2047 例 + CI 兜底暴露）
- [x] verification.md 记录全部验证证据
- [x] 双 AI 自审（SELF-REVIEW-HOWTO 五步走完：Deepseek-V4-Pro 评审无 blocker → 修复
      F-2/F-3/F-4+F-1 补句 → 复审增量"过，无 finding"→ self-review.md 生成待签）
- [x] 请示 commit/push + PR（b0375df 已 push，PR #60 已建；Upstream CI windows ty 失败
      根因修复见 verification 2026-10-27 节——crypto.py 3 处平台相关 ignore 改 getattr
      动态获取，三平台零 warning；修复 commit 待授权）
- [ ] CI 双门禁绿后用户合并 PR #60

## 挂起与备忘

- 上游两文件完整实现被 R10 重签阻塞（探针改动已在原签认范围：marker + 空函数骨架）；
- `chrys_test.py` 零命中 `aixcoding`：Smart Test 对 `aixcoding/tests/auth` 不可见，
  本地验证以 design"本地验证命令组合"三条为准；
- ty 三平台为 auth 包首次进射程（0.28 从未被 ty 检查），爆错属预期，修复不扩权；
- launcher 配方块打印的 env 名已随 mock 更名联动自动更新（`mock/__main__.py:163`）。
