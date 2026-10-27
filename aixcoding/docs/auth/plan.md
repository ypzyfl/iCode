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
- [x] 缩小重构（2026-10-27，负责人确认在 PR #60 内执行）：token 解析归位 auth 包
      `login_token_header_value()`（__all__ 27 项）；clients.py 对 base **diff 归零**退出 R2；
      wire_client 直接 import auth 包（依赖显性化）；上游 2 文件 38 行 → **1 文件 +16/−1**；
      评审两轮收敛（增量评审 3 findings 全修 + 复审无 finding，见 self-review）；全量验证绿；
      1c06bdd 双门禁已全绿（基线确认）
- [ ] 责任人重签 design（R2 表重写）→ 请示 commit+push → CI 绿后合并 PR #60
- [ ] CI 双门禁绿后用户合并 PR #60

## 挂起与备忘

- **【高优先·已知边界】token 无条件注入任意 provider/base_url（peer review C0，2026-10-27
  负责人拍板登记）**：`stamp()` 对有登录态的请求一律注入 `token` 头，无端点判定——用户配置
  非内网网关时 token 随请求外发。0.28 现网同形态（忠实迁入）；立即修复需向 `RequestHeaders`
  传入端点信息=扩大上游侵入，与 R1 细则冲突；需产品语义决策（白名单口径）。**归属：catalog
  批次处理**（模型配置语义所在，端点判定届时自然引入）。
- 【性能观察】每请求同步读盘+OS 解密（peer review C2/C3）：design 成本论证只覆盖 Windows
  DPAPI，**未覆盖 macOS 每请求 spawn `security` 子进程（2s timeout 最坏值）**——"不实施
  TTL/mtime 缓存"的决策前提需补 macOS 实测数据；单例无锁与构造失败重试（0.28 既有）同挂
  此议题，实测成瓶颈再做缓存（保持"登出下一请求生效"语义）。
- 【可选增强】腐蚀 ciphertext 触发 clear() 无日志（C6；clear-on-corruption 本身是 0.28
  有意设计）、stamp() import 失败分支日志（首轮 F-5 已拍板不加）——排查便利性增强，随需再做。
- 【理论边界】纯上游 wheel（不含 aixcoding）上 import 失败不缓存（C9，非现实发行形态）；
  测试裸调 `get_login_session()` 触真实 config dir（PR#60 评审 P2-1，只读不写，2047 passed
  实证无碍）；上游测试触发 auth 构造（P2-5，同实证）。
- 【工具改进项】gen_customizations 匹配粒度：marker module=特性名只匹配特性包登记行，
  上游接线点登记行的 marker 归属与语义字段（如 wire_client 行风险"中"被 auth 包行"低"
  覆盖）失真（PR#60 评审 P2-3）——与"check_docs.py 节标题形态校验"同批做工具小改进。
- `chrys_test.py` 零命中 `aixcoding`：Smart Test 对 `aixcoding/tests/auth` 不可见，
  本地验证以 design"本地验证命令组合"三条为准；
- ty 三平台为 auth 包首次进射程（0.28 从未被 ty 检查），爆错属预期，修复不扩权；
- launcher 配方块打印的 env 名已随 mock 更名联动自动更新（`mock/__main__.py:163`）。
