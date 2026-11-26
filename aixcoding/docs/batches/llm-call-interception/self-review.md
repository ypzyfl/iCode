# 自评审记录：进程内大模型 HTTP 调用拦截（llm-call-interception）

<!--
签认规则（R10 · 记录档）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认一次后，后续追加评审记录不触发重签。
双 AI 规则：评审 AI 必须与主力开发 AI 不同（不同工具或不同模型），如实记录标识。
完整操作见 SELF-REVIEW-HOWTO.md。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-11-25
- 确认意见：无特别意见
- 开发 AI：CodeBuddy / Kimi-K3.1-Pro
- 评审 AI：CodeBuddy / GLM-5.4（外部独立第二 AI）；另经内部 `code-explorer` 子代理两轮只读审查

## 2026-11-25 外部独立评审与修复闭环

- 原结论：不通过，B1 启动安装跨测试污染、B2 Content-Type 分派静默失效；开发 AI 独立复现 B1 为 48 passed、2 failed。
- B1 修复：空策略不附 hooks，非空策略先注册后建 Client。真实 startup 50 项组合恢复 **50 passed**；上游 core shard
  **24146 passed、652 skipped**。
- B2 修复：实际内容 512 字节 sniff、同 iterator 回放、普通/SSE 自适应分派、缓冲 SSE 和回调不匹配 detail。双向误标、
  三真实 SDK、门闩增量、512/513 边界、BOM、超大 chunk 和关闭语义均通过；本批及 startup 共 **125 passed**。
- Client 安装失败按裁决改为主通道+detail、不写 stderr，并分别断言两个 logger。动态 setattr 已就地留痕，
  签名漂移由 `follow_wrapped=False` 契约测试承担，不宣称该写法提供静态签名守卫。
- 修复后 Smart Test：tests **11040 passed、349 skipped**，architecture **600 passed、2 skipped**；完整定制套件
  **1002 passed、56 skipped**。修复后只读复核未发现新的运行时 blocker/high。

### S1-S9 逐项处置

| 项 | 处置 | 结果 |
|---|---|---|
| S1 签名断言恒真 | `follow_wrapped=False` + `inspect.unwrap` + 参数/kind 精确签名 | 已关闭 |
| S2 R13 外 ty 豁免 | 精确参数注解、`update_wrapper`；动态 setattr 就地说明，签名漂移由测试守卫 | 已关闭 |
| S3 私有 ByteStream | 改公开 `httpx.ByteStream` | 已关闭 |
| S4 缓存键无依据 | provider 归一为 OpenAI/Anthropic 两族后 `maxsize=2` | 已关闭 |
| S5 Client 安装通道/设计缺行 | 主通道+detail、不写 stderr；design 增加独立降级行 | 已关闭 |
| S6 压缩响应 | 保持原样直通+detail；design 明确框架不隐式改 Accept-Encoding，策略可自行协商 | 裁决不修，列入未修项 |
| S7 test-plan 名称 | 覆盖矩阵对齐真实用例，新增 B1/B2/边界/core shard 证据入口 | 已关闭 |
| S8 本批 R2 清单 | design 新增“上游改动清单（R2）”，独立登记 wait manifest | 已关闭 |
| S9 双 AI 标识 | 记录外部评审 CodeBuddy / GLM-5.4，与开发模型不同 | 已关闭 |

### Nit 逐项处置

- trajectory context key 复用上游 `_CONTEXT_EXTENSION`；Chrys cycle 断言排除全 `None`；取消测试断言首事件已处理。
- `Block.reason` 256 字符上限及禁止放入凭证/正文已写入 design/ADR。
- 默认无 hooks 后，缺阶段回调不再产生每请求上下文固定开销；已启用策略的上下文构造属于必要能力，不另做优化。
- SSE 尾部不完整事件只直通一次，已有测试；启动开销外部实测约 +12.9ms / 16 模块，作为参考记录。
- plan/verification 状态已更新；最新 Smart Test 与 self-review 签认状态以各文件最新记录为准。

## 2026-11-25 外部增量复审结论与处置

- 外部 GLM-5.4 增量复审**通过**：B1/B2 均确认修复，新代码路径未发现行为缺陷；其独立复核为真实 startup 50 passed、
  无策略 `tests/service/llm` 2099 passed、完整定制 1002 passed / 56 skipped。
- **方案与实现评估**：条件挂载保持默认上游行为；实际内容 sniff、同 iterator 回放和 fail-open/containment 符合重签
  design/ADR。N1 extension 导入已前移到安装期，N2 已补 sniff 未判定期间取消/异常/提前关闭三用例；N3 已补动态
  setattr 理由和测试守卫说明；N4 已登记 manifest 28 节点/+64 行并澄清完整 chunk；N5 已补注册时序 docstring；
  N6 已将 headers 快照前移；N7 已补齐本记录模板与当前 HTTP ADR 状态澄清。
- **最终复验**：本批/startup **129 passed**，完整定制 **1006 passed / 56 skipped**，上游 core shard
  **37256 passed / 699 skipped**，Smart Test **11040 passed / 349 skipped**、architecture **600 passed / 2 skipped**。
  三平台 ty、ruff/format、导入边界、定制清单、compileall、R2/R3 均通过；wait 生成器为 2937 waits / 0 reopened。
- **未修项（次要问题，责任人拍板不修）**：

| 位置 | 说明 | 不修理由 |
|---|---|---|
| `hooks.py` 非 identity Content-Encoding | 压缩普通/SSE body 不做内容处理，原样直通并记录 detail | 责任人采纳 S6 裁决：框架不隐式修改 Accept-Encoding；需要时由策略在请求阶段自行协商 identity |

- 签认事实：design/ADR 在 B1/B2 修订后已由周彬于 2026-11-25 重签。manifest 当前为 28 节点/+64 行，待责任人在
  本记录签认时一并确认知悉。

## 2026-11-25 PR #153 独立评审结论与处置

- PR #153 独立评审**通过（Approve），无阻塞项**：评审对象 head `1bb01be3`（单提交，base `baddb7f5`）；Block 不被
  SDK/Chrys 重试、httpx 0.28.1 流语义、hook 顺序与 raw log、空策略零开销、R2/R11/分层、containment 边界与降级日志
  核对均通过。评审方标识以 PR #153 评审记录为准。
- CI 交叉核对（开发 AI 经 GitHub API 复核 head `1bb01be3`）：check-runs 28 项 = **27 success + 1 skipped**
  （`Guard hooks`，未触及 guard 路径的设计内跳过）；`AIxCoding Tests`、`AIxCoding Upstream CI` 均 success。评审所述
  “28/28 全绿”按此校正。
- **方案与实现评估**：实现与已签认 design/ADR 一致，B1/B2 修复彻底；7 条建议均为非阻塞，事实前提经开发 AI 逐条
  只读核实属实。评审措辞有三处与实测不符，已校正：CI 数字；冒号启发式不要求空行分隔，前 512 字节内不以
  `{`/`[`/`<` 打头且含 `:` 即判 SSE；SSE 终结符为 `\n\n` 或 `\r\n\r\n` 两种，design 仅隐含提及，“替换体须自带
  终结符”此前只由测试断言体现。

### 建议逐项处置（责任人裁决采纳方案 B）

| # | 评审级别 | 位置 | 处置 | 结果 |
|---|---|---|---|---|
| 1 | 建议关注 | `hooks.py` 压缩响应整体直通 | 维持 S6 裁决不修；核实中实证默认 `Accept-Encoding: gzip, deflate`，且协商 identity 须在 `httpx.Headers` 副本上赋值（`dict` 加驼峰键会发重复头并静默失败），均写入 `HttpPolicy` docstring；补 2 个用例锚定两种写法 | 已登记，docstring 与测试已补 |
| 2 | Low | `hooks.py` `_classify_prefix` | 不修：合法 SSE 字段行与注释行均含 `:`，现规则只误判不漏判，收紧须另行设计 | 不修 |
| 3 | Low | `hooks.py` `_NormalBodyStream` | 不修：整体替换语义的固有代价，design 已声明 | 不修 |
| 4 | Nit | `interceptor.py` `_sdk_block_type` | 不修：当前仅 `anthropic` 一个 provider id 属 anthropic 族，两套口径等价，分叉时两族 Block 仍均非重试 | 不修 |
| 5 | Nit | wait manifest 28 节点 | 补逐节点复核留痕（根 `AGENTS.md` 要求逐个复核），结论均保持 `unresolved` | 已补，见 verification.md |
| 6 | Nit | `HttpPolicy` docstring | 补 SSE 事件终结符契约：事件自带空行终结符，替换体必须保留 | 已修 |
| 7 | Nit | `hooks.py` `getattr(policy, ...)` | 不修：policy 实例属外边界，评审自评可接受 | 不修 |

- 核实证据：探针输出见 verification.md “HttpPolicy docstring 补充与 Accept-Encoding 协商探针”一节。
- 新发现跟进（核实 #1 时发现）：(a) 协商 identity 的两种写法补专门用例——责任人裁决**补测试**（2026-11-26），
  `test_request.py` 新增 2 例；(b) `HttpChange.headers` 出现同名多值时是否在框架层检测并告警——责任人裁决**本 PR
  不做，登记为后续候选**（2026-11-26），见下表。
- manifest 28 节点/+64 行已随本记录签认（2026-11-25）知悉。
- 本节为签认后追加的评审记录，按头部规则不触发重签。

### 未修项（次要问题，责任人拍板不修）

| 位置 | 说明 | 不修理由 |
|---|---|---|
| `hooks.py` 非 identity Content-Encoding | 压缩普通/SSE body 不做内容处理，原样直通并记录 detail | 责任人维持 S6 裁决：框架不隐式修改 Accept-Encoding；后续业务批次接入文档须置顶此条 |
| `hooks.py` `_classify_prefix` 冒号启发式 | 非 `{`/`[`/`<` 打头且含 `:` 的纯文本会被判为 SSE，`before_sse_event` 可能收到非 SSE 字节 | 低影响、只误判不漏判；收紧须另行设计 |
| `interceptor.py` `_sdk_block_type` | provider 判族与 `clients.py` 的 `PROVIDERS[...].sdk` 为两套口径 | 当前等价，无功能危害 |
| `HttpChange.headers` 同名多值 | 策略用 `dict` 加不同大小写的键替换已有头时会发送重复头；框架原样转发，不合并、不告警 | 责任人裁决本 PR 不做，登记为后续候选（2026-11-26）：默认空策略不触发；正确写法已写入 docstring 并有 2 例测试锚定；框架层检测属行为变更，待首个业务策略接入时评估 |

## 2026-11-26 对原有流程的影响与性能评估（责任人要求）

- **评估范围**：本方案对上游流程的全部改动点、默认（空策略）与启用策略两条路径的功能与性能影响、必要性。实测为本机
  开发环境、隔离进程、`MockTransport`，一次性内联探针未入库，方法与输出见 verification.md “对原有流程的性能影响实测”。
- **对上游流程的改动点**（上游手写文件 0 改动）：
  1. 启动：`aixcoding_startup()` 的 `_TASKS` 增加一个任务，在 `chrys.app.cli.app:main()` 首行执行，因此每次
     `aixcoding-cli` 调用（含 `--version`、`--help` 与所有子命令）都会运行；
  2. 启动：进程内把上游模块属性 `chrys.service.llm.clients._build_profile_http_client` 替换为包装函数（上游唯一调用点
     在 `create_client`；`update_wrapper` 保留 `__wrapped__`，兼容上游 `inspect.unwrap` 与各 `monkeypatch.setattr`
     patch 点）；无卸载路径；
  3. 创建 Client：经包装层；策略非空时向共享 `httpx.AsyncClient` 追加 request/response hook；
  4. 每请求：仅在 hook 已附加时执行读、改、拦与 SSE 逐事件处理；
  5. 生成物 `tests/architecture/trajectory_wait_manifest.json` +64 行，无运行时影响。
- **功能影响**：默认空策略下第 3、4 项不执行，hook 清单与上游一致（有精确清单测试与上游 core shard 37256 passed
  为证），模型请求/响应路径不被触碰，原有流程不受破坏。设计已声明的边界不变：不经该工厂的模型路径不被拦截；
  fail-open 意味着不是安全硬阻断。
- **性能影响（实测）**：

| 路径 | 默认空策略 | 启用空操作策略 |
|---|---|---|
| 启动，每次 CLI 调用 | **+200–215 ms、+383 模块**（`--version` 脚本总耗时约 48 → 250–270 ms） | 同左 |
| 创建 Client | +0.49 µs | +0.49 µs |
| 每请求，非流式 2 KB / 512 KB | 不执行 | +15 µs / +37 µs |
| SSE 每事件 | 不执行 | 约 1.4–1.7 µs（5000 事件合计约 +7 ms） |

- **方案与实现评估**：
  1. **启动期无条件安装是默认路径上的纯成本，建议去除。** `install_http_interception()` 不判断策略是否为空，启动即
     导入 httpx、上游 `clients` 及其依赖树并替换工厂；空策略下该包装只做透传，没有功能收益，却让每次
     `aixcoding-cli` 调用多约 200 ms。此前记录的“+12.9 ms / 16 模块”是 pytest 热进程数字，低估 15 倍以上，按本节
     实测更正。建议把安装点从启动期改为策略注册时（`set_http_policy` 触发安装）并移除启动任务。仅“空策略时跳过
     安装”不够：包的 `__init__` 会连带导入上下文与 trajectory 子系统，实测仍需 85–95 ms / 196 模块，启动路径必须
     完全不导入本包。该改法变更已签认 ADR 的核心决策，需修订 design/ADR 并重签。
  2. **运行期热路径开销很小，建议保留，不另做优化。** 按事件数逐级翻倍实测，单 chunk 多事件时每事件耗时稳定，
     未观察到 SSE 缓冲前移的平方级增长。
  3. **必要性：当前没有业务策略使用本框架。** 默认状态收益为零；惰性化后默认路径成本趋近于零，剩余代价是源码与
     测试的长期维护（上游 httpx/SDK 升级时需跟随验证）。是否现在合入取决于业务策略需求是否明确。
- **惰性化（安装点由启动期改为策略注册时）的代价与风险**：
  - 代价——文档：ADR 决策 1（启动期安装）、6（启动安装失败语义）、8（真实 startup 回归）及理由、四场景矩阵需修订，
    文件名含 `http-startup-runtime-wrapping`，原地修订还是新建 ADR 待责任人定；design 约 12 处、requirements 2 条
    验收标准、test-plan 3 行同步；design/ADR 重签。代码：startup 两文件移除任务，`set_http_policy` 增加安装触发与
    失败处理；`hooks.py`、`context.py` 不动。测试：startup 清单与安装失败用例回退或改写，安装器用例按注册时序改写，
    估计涉及 10–15 例。流程：全量回归、外部增量评审、CI 一轮。
  - 风险——功能风险低：hook 核心逻辑与时序语义（先注册后建 Client、不追溯既有 Client）不变，默认路径由“透传包装”
    变为“不接触”，暴露面缩小。新增三个设计点需定：安装触发 API 的形态；注册期安装失败是抛出还是降级；注册策略的
    单元测试不应触发安装或改动全局工厂（当前约 9 个测试文件直接调用 `set_http_policy`）。
  - 不做的后果：每次 `aixcoding-cli` 调用约 +200 ms 随 PR 合入主干。
  - 开发 AI 意见：需要做。
- **裁决跟进**：(2) 已完成的评审处置改动先作为独立提交推送——责任人采纳（2026-11-26）；(1) PR #153 的处理方式——
  责任人方向上认同在本 PR 内完成惰性化后再合并，是否实施待上述评估后裁决（2026-11-26）。
- 本节为签认后追加的评审记录，按头部规则不触发重签。

## 2026-11-26 启动成本测量更正与惰性化重新评估

- **更正**：上节“性能影响”表中的“启动 +200–215 ms、+383 模块”，以及“此前记录低估 15 倍以上”“不做的后果约
  +200 ms”等论断不成立。该探针未执行前两个启动任务，第三任务于是独自承担了本应由它们分摊的公共依赖导入。真实启动
  路径复测（全部启动任务真实执行、配置目录隔离）中，原安装任务的净增量约为 **18–20 ms、18 个模块**；`main()` 约
  370–480 ms 的主体是既有的前两个任务。外部评审最初记录的“+12.9 ms / 16 模块”与此吻合，其结论基本正确。数据与方法见
  verification.md “启动成本测量更正”。
- **连带更正**：以“仅导入即需 85–95 ms / 196 模块”否决“启动期判空”的理由不成立，真实路径上该方案只多 3 个模块；
  不采用它的正当理由是启动期策略必为空、该任务恒为空转。上述错误数字已写入 design 方案概述与备选对比、ADR 理由与
  修订记录，需按本节更正并由责任人重签。
- **对决策的影响**：责任人是在“每次启动 +200 ms”的前提下裁决做惰性化并重签 design/ADR 的。更正后，惰性化的默认
  启动收益约为 18–20 ms；其余收益不变：默认路径完全不触碰上游工厂，PR 对 `src/chrys/app/` 净零改动，定制测试以
  fixture 恢复工厂、隔离更干净。代价已付（文档修订、重签、实施、测试），剩余为上游 core shard、Smart Test 与增量评审。
- **开发 AI 意见**：保留惰性化仍然合理，它在默认路径上优于启动期安装，功能与时序语义无变化；但收益量级比此前呈报的
  小一个数量级，是否保留应由责任人在正确事实下重新裁决。回退到启动期安装的代价是再次修订并重签
  design/ADR/requirements、丢弃已通过测试的实施。
- **现状**：惰性化实施已在工作区完成，未提交。惰性化代码上通过本批 133、完整定制 1010/56、真实 startup 组合 50、
  上游 core shard 37256/699（与惰性化前一致）、Smart Test 11040/349 + architecture 600/2、三平台 ty、wait 生成器
  2937 waits / 0 reopened、R2/R3 与文档闭环。PR 相对主干变更 26 文件（原 29），`src/chrys/app/` 与
  `diagnostics/test_entry_wiring.py` 净零改动。design/ADR 的数字更正已由责任人确认（2026-11-26），惰性化增量评审
  已通过（见下节）；待办：两组改动的提交与 CI 复验。
- **实施中的适配**：`test_block.py::test_final_block_classification_and_exception_hygiene` 原在替换工厂之后才注册
  策略，注册触发的安装把测试替身又包了一层，导致 `transport` 参数重复；已把注册挪到替换工厂之前。全部 12 处替换
  工厂的测试中仅此一处顺序相反。
- **责任人裁决（2026-11-26）**：在更正后的事实下保留惰性化；design/ADR 中的错误数字据此更正，并经责任人确认。
- **责任说明**：测量失误在开发 AI——未核实“前两个启动任务是否已预导入相关依赖”，即把探针差值当作真实净增量呈报，
  并据此推动方案变更。
- 本节为签认后追加的评审记录，按头部规则不触发重签。

## 2026-11-26 惰性化增量评审结论与处置

- 增量评审**通过（无 blocker，3 条非阻塞建议）**：评审对象为惰性化实施（安装时机由启动期改为注册非空策略时），核心
  代码、测试迁移与文档一致性逐项核对通过。评审以静态审查为主，未独立运行测试，测试数字以 verification 与 CI 为凭，
  建议合并前由 CI 复验一轮。评审方标识以 PR #153 评审记录为准。
- **方案与实现评估**：懒安装的“先安装后保存策略”顺序与 ADR 一致，安装路径不读策略；注册期安装失败 fail-open 符合
  requirements 11；conftest 恢复未包装工厂解决了注册触发安装带来的测试污染；`test_entry_wiring.py` 删除的启动安装
  失败用例已由 `test_installer.py` 的注册期失败用例替代，startup 通用失败 containment 仍有既有用例覆盖。
- **建议逐项处置**：

| # | 级别 | 位置 | 处置 |
|---|---|---|---|
| 1 | nit | `interceptor.py` 两个安装失败报告函数的 WARNING 文案重复 | 责任人裁决不修（2026-11-26）：重复仅一行消息文本，提取后代码量不减，且会把注册期与 Client 期两条日志路径耦合在一起 |
| 2 | nit（文档） | 本记录“现状”段仍列“待重签” | 已更正（见上方现状段） |
| 3 | nit | `test_startup_never_references_http_interception` 的 `glob("*.py")` 非递归 | 责任人裁决采纳（2026-11-26）：改为 `rglob("*.py")`，守卫对子目录同样有效 |

- 本节为签认后追加的评审记录，按头部规则不触发重签。

## 2026-11-25 内部评审结论：代码审查与交付验证通过，已被后续外部评审推翻

- 轮次：2 轮（首轮评审 + 修复 + 独立复审）。
- 方案与实现评估：实现与已签认 HTTP 启动期运行时包装、默认空策略、真实可空调用归属和异常 containment 一致；未实现逻辑调用层或具体业务策略。wait manifest 是唯一经重新签认的上游生成物例外。
- blocker 处置：无 blocker。
- high 处置：标准 `exc_info` 会输出原异常消息；修复中又发现 traceback 源码行可含秘密字面量，最终改为只输出文件名、行号、函数名和固定 redacted 结尾。四阶段合成 token、prompt、工具参数、响应正文均验证不出现在最终格式化日志中；见 verification.md 的 111 项回归。
- medium 处置：客户端创建期安装失败补 stderr、主通道 WARNING、脱敏 detail 和宿主继续测试；三协议普通响应修改补缓冲/真实流到 SDK `raw.parse()` 的证据，普通流 Block 与三 provider 流式 Block 补 SDK/Chrys 无重试、无重放证据。
- low 处置：响应头故障注入改为真正进入 headers 应用；SSE body 修改时删除陈旧 `Content-Length`，并验证 raw log 仍保留网络原始响应。
- 复审结果：独立复审确认原 6 项 finding 全部 closed，未发现新增 blocker/high/medium/low。
- 未修项（次要问题，责任人拍板不修）：无。
- 交付证据：Smart Test 普通套件 11040 passed / 349 skipped、architecture 600 passed / 2 skipped；完整定制套件 988 passed / 56 skipped；三平台 ty、ruff/format、导入边界、定制清单、编译和 R2/R3 均通过，详见 verification.md。
- 交付限制：仅余 design 的 ID 来源澄清重签、本记录签认及 `check_docs --closure`；不涉及未修复代码问题。

## 2026-11-26 PR #153 二次评审结论与处置

- 评审结论：**Request changes（暂不 Approve）**。评审对象 head `089f52cc`，base 快照 `baddb7f5`，主干 `b2385928`。
  阻塞项 B1（与主干冲突不可合并）、B2（PR 描述仍是惰性化之前的版本）；主要发现 F1–F6。评审方标识以 PR #153
  评审记录为准。开发 AI 逐项只读复核（`git merge-tree`、GitHub API、源码与文档行号），全部属实。
- 轮次：1 轮（二次评审 → 处置；复审由评审人按 PR 流程进行）。
- 责任人裁决（2026-11-26）：F1 取扩展方案、F4 确认为 §6 批准例外并留痕、F5 仅澄清 docstring，其余按呈报处置；
  合并主干采用 merge（仓库惯例，保留评审引用的提交号）。
- 方案与实现评估（技术评审摘要）：
  - 大方向表态：同意评审结论——代码主体无阻塞性缺陷，缺口在合并态、交付报告与三处守卫/文档一致性，处置均为
    小改动。
  - 关键决策逐条意见：
    - F1 扩展支持 CR | 同意：两个 pinned SDK 的解码器都接受 `\r\r`，不支持等于对这类流静默失效且 `Block` 拦不住。
    - F4 确认为批准例外 | 有保留并留痕：与 §6 字面有张力，依据是该 ADR 修订时未合入主干且决策主体未变。
    - F5 仅澄清 docstring | 同意：当前无生产调用方，no-op 基类是未被要求的功能。
  - T1-T4 要点：F1 的边界定义已写入 design「SSE 事件」与「隐式行为假设」第 6 条；F2 的守卫写入「新增定制
    测试」；F5 的类型契约写入「HTTP 策略契约」；R2 行随 F1 更新为 30 节点 / +68 行。
  - 临时项与例外：F4 为流程例外，留痕于 ADR 修订记录；是否为 §6 补通用条款另立规范议题，不在本批决定。
- blocker 处置：
  - B1 → 已处置：merge `origin/main_aixcoding_cli`，唯一冲突文件 `tests/architecture/trajectory_wait_manifest.json`
    先落为主干版本再用官方生成器重写（2950 waits / 28 reopened，相对主干 +64 行）；合并后回归见 verification.md。
  - B2 → 处置安排：全部处置定稿后把 PR 描述重写到最终态，由责任人在 GitHub 更新；PR 描述为 §7 交付报告，
    以最终提交为准。
  - F1 → 已处置：`hooks.py` 事件边界改为两个行结束符（LF/CRLF/CR），单个 CRLF 不拆；流式路径在边界落在缓冲
    末尾且以 CR 结尾时推迟到下一 chunk，流结束后定案。新增 19 个用例实例，变异验证见 verification.md。
  - F2 → 已处置：`test_installer.py` 新增子进程用例，隔离 HOME/APPDATA 并经真实 `main()` 执行全部启动任务，
    断言 startup 已执行、本模块未导入、上游工厂无 `__wrapped__` 与 marker。
  - F3 → 已处置：plan、research、test-plan 同步，design 补「定制点登记预告（不适用）」，本记录与 verification
    追加处置记录。
  - F4 → 已处置：ADR 修订记录追加责任人确认，slug 注明为历史名。
  - F5 → 已处置：`HttpPolicy` docstring 澄清协议声明与运行期可省略阶段的关系。
- 顺带发现：
  - `verification.md` 的“上游 core shard”口径 | 此前把 CI core shard（24146 / 652）与 `tests` 全量含 TUI
    （37256 / 699）都称作 core shard | 已在 verification.md 处置记录中更正，旧记录保留。
  - `plan.md` 签认日期 | design/ADR 的签认日期停留在 2026-11-25，未随 2026-11-26 重签更新 | 已随 F3 更正。
- 未修项（次要问题，责任人拍板不修）：无新增；评审 F6 的观察与既有未修项表一致，维持不修。
- 本节为签认后追加的评审记录，按头部规则不触发重签。
