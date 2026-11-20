# 测试计划：外置 OTel 业务埋点

## 基线隔离与证据要求

首轮模拟环境固定官方 0.36.0 `78802f87d07f053fe560d680e4696c2bf322e2c2`，独立回归环境固定官方 0.35.2 `2fd777f626649d53d7ccd701e26a1a7ada569ce8`；每个环境独立锁定其官方Python/SDK/OTel组合，不借用fork依赖证明新版本运行通过。业务对照进程固定已交付fork提交。禁止在带旧来源字段的fork上证明零补丁；不mock掉正在验证的官方符号；报文存在不等于宿主等价。

## 决定性门禁

| ID | 对应需求 | 场景 | 必须断言 |
|---|---|---|---|
| G1 | RQ1/2/10 | 原版同进程 wheel 启动＋instrument/uninstrument | 官方源文件/入口/依赖哈希不变，原函数调用一次，禁用不残留 |
| G2 | RQ3/4 | A1→write→A2，再连续 edit 同文件 | LLM/tool/ai-code 精确条数、同次官方快照、逐次 diff、A1/A2分工；轨迹开/关均判别；真实 finalize 命中所登记调用绑定，卸载后路径恢复 |
| G3 | RQ4/5 | 并发子调用、同 provider ID、retry、流 close/cancel | invocation/pass/occurrence 不串，前序关联保留、重放不新增执行，原流协议不变 |
| G4 | RQ3/5/8 | 真实官方 ACP prompt/retry 双 session | 输入作用域、1001、最终身份、原 meta 合并，stdout 只有协议 |

G1–G4 必需能力失败时停止扩大实现；不能把失败转成未批准 skip。通过之前不承诺完整零源码业务替代。

执行顺序：先0.36.0跑G1–G4，再对0.35.2跑相同fixtures，分别记录结果。两版共用facts/correlation/编码器，若能力差异只修改adapter，不能为让矩阵通过而分叉企业业务。未来每个版本重复这一资格验证，不以“同属0.x”自动通过。

## 全量兼容与异常矩阵

| ID | 需求 | 场景 | 预期 |
|---|---|---|---|
| T1 | RQ3/4 | 三模型协议、stream/non-stream、SDK/wire retry、Responses retrieve | 业务 ID 粒度对拍，usage不重复，失败/辅助语义明确 |
| T2 | RQ3/5 | 审批修改参数、拒绝、tool_error、异常、取消 | 状态由结构事实判定，业务采集异常不替换宿主结果 |
| T3 | RQ3/4 | 连续/并发 write/edit、同 T 多 mutation、空 blocks | 使用官方执行快照，不读当前文件冒充；支持或明确差异 |
| T4 | RQ3 | 引用技能但不加载、实际 load_skill 多次 | 引用不计加载，各实际执行单独计数 |
| T5 | RQ3/8 | workspace/模型/凭据切换，自定义/catalog 模型 | 不跨 session，不取安装目录，过滤依据和时点固定 |
| T6 | RQ4/5 | hosted 正常/中断、local child、Workflow 重试 | 不复制执行，不把 hosted 当本地工具；来源缺口单列 |
| T7 | RQ6 | 慢网/断网/响应丢失/429/409、队列满 | 主流程不被网络阻塞，重试仅按真实幂等，丢弃可查 |
| T8 | RQ2/6 | 正常退出、取消、active delete、异常关闭 | 有界 drain，owned client正确 loop关闭，其他 provider不关闭 |
| T9 | RQ2/7 | 重复 instrument、未知版本、其他 wrapper、OTel关闭 | 全组预检、冲突退出、不覆盖他人 wrapper，无双 provider |
| T10 | RQ1/10 | TUI/CLI/ACP/serve 子进程与各 OS | 所有实际业务进程明确装配；无法装配形态不能标通过 |
| T11 | RQ8 | 内容关闭、敏感/超长参数、凭据轮换 | token不外泄，代码正文不进metrics，裁剪不静默伪完整 |
| T12 | RQ9 | 单写切换、回退、隔离双链路 | 生产始终一个企业 sender；不同 ID 不能假定后台自动去重 |
| T13 | RQ3/8 | 官方原版＋企业上下文 provider，缺失/映射更新/账户切换 | server-owned 至少一条真实业务记录，custom/unknown 可解释；归属按调用时快照，旧主体不由新账户 token 发送；缺 provider 明确 unavailable |
| T14 | RQ11/12 | 0.36.0/0.35.2与未知版本、相同签名不同语义、模块路径变化 | 只在adapter/注册表变化，核心不分叉；未知版本不获生产资格，不猜未知字段 |
| T15 | RQ11/12 | 0.36.0 result override/extra context、discovery关闭hooks | 原始执行状态与hook后模型可见结果区分；失败不因文字替换算成功；连接探测不算Agent调用；0.35.2同业务口径分别验 |
| T16 | RQ12/13 | 制品摘要不符、依赖组合变化、注册表降级/回退 | 不从source-reviewed跳到qualified；不同内容的同版本不默许；宿主继续，业务明确unavailable；离线加载已审注册表 |

## 报文比较与完整率

使用同一组录制模型响应、工具执行和审批输入重放，比较接口、字段存在性/类型、事件顺序、状态、数量及身份关系。随机值按对应 occurrence 建双射，不按 provider ID 全局去重，不比较两次自由模型生成的代码文本。

每个样本必须有精确预期记录数、必需字段、允许缺失项和原因；零错关联与完整性分别验收。批准降级/不支持列表单列且由人确认，不用任意覆盖率百分比或自生成测试数量代替业务验收。

## 性能与升级

对每个被测官方版本比较 disabled/enabled：首token、流pull、工具主路径、快照复制、CPU/内存、积压和关闭耗时。预算由实测及责任人底线确定。以0.36.0为首轮，0.35.2为回归；未来release先以固定制品、能力与语义门禁获得资格，官方main固定SHA只作演进预警。分别报告源码零diff、适配变更和业务等价，不把静态文件相同当运行通过。

## 本轮运行状态

以上为测试设计，尚未执行 G/T 实验。本轮只有官方源码读取和文档校验，见 verification.md；没有借用已交付 fork 的测试结果作为新方案通过证据。
