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
