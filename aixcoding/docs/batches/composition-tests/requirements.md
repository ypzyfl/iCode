# 需求：服务组合测试（composition-tests）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
> 修订记录：2026-11-01 立项起草（预案 v3 自 temp/2026-11-01-custom-test-strategy/20 号迁入
> 工程，按仓库规范走完整管线；预案经 2026-11-01 三轮评审收敛——F-05 + R-01/R-02 + S-02
> 处置意见已并入本批各文档）；同日首轮工程内 design 评审（外部 AI，无 blocker，5 major +
> 3 minor）全部采纳处置（明细见 design.md 末节）——形态 A 补第七约束（登录态建立禁令）、
> 快照日志承诺缩窄。

## 背景与问题

现有定制测试（28 文件）以局部契约与接线点测试为主，**缺少跨模块生产组装的链路验证**：

- token 注入是单元级（`aixcoding/tests/auth/test_llm_token_wiring.py`：channel 1 直接驱动
  `RequestHeaders.stamp()`；channel 2 虽经真实 openai SDK client + MockTransport，但 SDK client
  由测试自建，未经生产工厂）；
- 登录会话是模块级（`test_auth_session.py`：MockServer 驱动 `LoginSession` 状态机，不触达
  LLM 请求侧）；
- TUI 侧是组件级（对话框/徽标/指示器纯函数或裸 App）。

局部契约全绿不代表真实组合时序正确——**组合根（composition root）恰是最容易在升级中
断裂的位置**（`create_client` / `LoginSession` / wire 装配任一环节上游重构，单元测试都可能
保持绿色而组合行为已坏）。

命名口径：本批产物是"**服务组合测试**"（会话与 LLM 请求的生产组装链路），不得宣称为完整
用户业务链路或 UI E2E 覆盖。

## 目标与非目标

- 目标：
  - 一条主链路的组合测试：**登录 → 会话建立 → LLM 请求携带正确凭据 → 登出 → 下一请求
    不再携带旧登录凭据**（凭据生命周期闭环；登出后仍携带是安全级缺陷）；
  - 测试形态为**进程内真实组件组装**（形态 A），验收条件六条（LLM client 经真实生产工厂
    `create_client(ModelProfile(...))` 创建、HTTP 出口经 loopback 端点拦截、同一 client 实例
    贯穿三次请求、逐次捕获最终 header 快照、登录侧真实 `LoginSession` + `CredentialStore`、
    mock 后端用 `aixcoding/mock` auth 契约），防止退化为"现有单元测试串联"；
  - 配套测试设施：loopback LLM 端点的**结构化请求快照**（逐次捕获最终凭据相关 header，
    原始 token 不落任何持久日志，内存快照随测试结束丢弃）；
  - **同一性断言**：登录所用会话实例与请求盖章读取的会话（`get_login_session()` 单例）
    是同一实例——防"登录了一个 session，wire 却读取另一个默认 session"的假绿。
- 非目标：
  - 不覆盖模型目录缓存、diagnostics 面板、TUI 全屏交互（防范围蔓延，待主链路落地后按需
    评估）；
  - 不做最小 Textual pilot（UI 生命周期真实挂载）——现有源码字符串接线检查不能替代真实
    UI 生命周期验证，此缺口显式登记为已知边界，是否追加为**后续独立决策**；
  - 不宣称覆盖真实 OS 凭据后端（`MemoryBackend` 只替代平台持久化层，真实 DPAPI/Keychain
    由 `test_auth_crypto.py` 平台矩阵用例承载）；
  - 不访问真实模型服务，不给 `create_client` 新增 transport 参数（上游源码改动路径，预案
    已否决为默认）。

## 用户场景

1. **升级回归检测**：上游重构 `create_client` 装配链 / `stamp()` 注入时点 / SDK header 合并
   语义后开 PR——组合测试红 = 组合语义冲突信号，跟随上游调整（这正是其价值）；
2. **凭据生命周期安全回归**：改 `src/chrys/*/aixcoding/auth/**` 或 wire 注入逻辑后开 PR——
   "登出后下一请求仍携带旧登录凭据"的安全级缺陷在 PR 阶段即红。

## 验收标准

- [ ] 主链路组合测试落盘 `aixcoding/tests/auth/`（受益既有 conftest 窄域防呆），形态 A
      六条件 + 第七约束（登录态只能由真实 `complete_login()` 建立，禁止手工注入凭据
      header / 直写 CredentialStore）逐条满足并在测试内可核对；
- [ ] 三次请求逐次断言：登录前请求无登录 token header；登录后请求 `token` = 登录会话
      签发的凭据；登出后请求不再携带**旧登录凭据**（断言区分"登录凭据"与"静态/委托凭据"，
      不无条件断言"完全无 token"）；
- [ ] 同一性断言：`get_login_session()` 返回实例与登录所用实例 `is` 同一；
- [ ] 环境前置：构造会话前清理全部三个委托通道变量（`AIXCODING_AUTH_DELEGATED_TOKEN`、
      `OPENAI_API_KEY` + `AIXCODING_USER_EHR` compat 对），显式断言 `detect_delegation() is
      None`；显式固定 auth 环境、endpoint URL、profile 的 API key / base URL；
- [ ] loopback LLM 端点结构化快照设施就位：每次请求至少含请求序号 + 最终凭据相关
      header（含 `token` 与 SDK 静态 `Authorization`），不依赖现有请求计数或脱敏日志文本；
      stub 不主动写任何持久日志（快照仅保存 mock 凭据，断言避免无必要打印完整快照）；
- [ ] 上游零文件改动（R2 清单空）；
- [ ] 新增测试随定制套件全绿（本地 `uv run python aixcoding/tools/verify.py --smart` 与
      定制门 CI 双通道）；
- [ ] 文档联动：mock README（若 auth mock 侧有改动）与本批 verification 落盘证据。

## 开放问题

- 无方案级开放问题（预案 Q4 经三轮评审已处置：transport 默认走 loopback 端点；其余立项
  细化项——LLM stub 落点、auth mock 是否补捕获、`ModelProfile` 固定方式——见 design.md
  备选对比与决策）。
