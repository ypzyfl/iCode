# 长会话扫描成本、去重状态与队列生命周期

> 2026-11-17。范围：30 轮真实 engine 文件基准和 test-local per-session queue 原型；不是生产 reporter，不设任意毫秒验收阈值，不证明真实 TUI/ACP/后台端到端性能。结论：后台队列路线可行，但 expected-turn 过滤本身不降成本，逐轮全目录重建存在明确的线性单轮/累计二次增长；正常设计应只处理显式当前轮，不扫描启动前历史。

## 1. 真实文件基准

同一会话执行 30 轮，其中 14 轮含工具、6 轮创建独立 write_file；每轮 finalizer 后分别运行全历史 reader 和 expected-turn reader。每个采样点取 3 次中位数，单位为本机 Windows 临时目录实验的毫秒：

| turn | session KiB | trajectory KiB | 全量中位 ms | expected-turn 中位 ms | 全量记录 |
|---:|---:|---:|---:|---:|---|
| 5 | 25.8 | 119.1 | 7.307 | 7.329 | 7 LLM / 2 tool / 1 ai-code |
| 15 | 75.7 | 370.0 | 20.942 | 18.921 | 22 / 7 / 3 |
| 30 | 149.1 | 742.0 | 38.409 | 38.439 | 44 / 14 / 6 |

30 轮累计测量：全量 638.960 ms，expected-turn 711.301 ms；后者更高是运行噪声，不能解释为过滤增加固定成本。两者都每轮完整加载 session/transcript/trajectory 和 mutation ledger，故主要成本没有本质差异。

逐轮结果等价断言同时通过：expected-turn 的 LLM/tool/ai-code 与全量结果中该 span 的子集完全一致。它证明**报文裁剪正确，但不是 I/O 优化**。

样本初稿重复 write 同一路径，真实工具以 `file_exists` 失败；改为每轮独立文件后通过。该失败不是 trajectory 落盘慢，也没有被隐藏或重写成成功。

## 2. 性能方向判断

当前数据足以确认增长形状，不足以规定“多少毫秒不可接受”：单轮成本随文件总量近似线性增长，若每轮都重读全部历史，累计工作量为二次增长。30 轮绝对耗时不大，不代表长会话、大 blob 或慢盘没有积压风险。

实施默认应调整优先级：

1. after_turn 只处理通知指定的 expected 当前轮，不在每轮上报所有找到的历史，也不在进程启动时回放旧会话；
2. 生产 reader 至少避免当前方向实验的重复 session 加载，先做一次加载/复用投影，再谈复杂缓存；
3. trajectory 可用已校验字节 offset/文件 signature 做性能增量，但 offset 失效、torn tail、gap 或 compaction 时必须安全重读；
4. session.json 是全量重写格式，持久化 cursor 不会自动消除其解析成本；需要实测后再决定是否增加当前轮物化快照，不能先发明复杂存储；
5. 大 blob 只在当前 turn 的 ai-code 需要时读取，不能为全历史重复读取。

## 3. 最小去重状态

本任务明确 best-effort、允许孤儿且不做崩溃补报，因此正常正确性不要求持久化全局高水位：

- 通知层：普通分析通知按 `(sessionId, logicalTurnId, passId)` 合并同 pass 重复；不同 pass 在首任务 pending/running/completed 时均不得静默丢弃。selected Agent 1001 仍按 `(sessionId,logicalTurnId)` 保持一条，不随普通通知改为每 pass 一条；
- reader：区分当前 pass 新执行、为关联所需的前序来源和 retry 纯重放/继承内容，不得每 pass 重报整个 logical turn；
- 记录层：使用已经确定的 requestId/funcId/reportId 幂等键作为第二道防线，重试和跨进程语义重放由后台去重；
- fork：只处理本 fork 显式执行的本地 turn，不主动扫描继承历史；
- save=False：通知层直接跳过，reader 再做 expected-turn/pass 防御；
- 重启：不补扫旧历史，所以无需为“崩溃后恢复所有未报记录”设计 cursor。

异步 worker 读取不受 FIFO 对 engine 写入的保护。2026-11-19 F1 裁决以记录级事实一致和关联正确为目标，不预设全局原子快照：正常追加后旧 pass 仍应精确重建；回滚/压缩后不得拼接不兼容、归属不同或证据不足的事实；不可恢复时显式记录并由责任人裁决该降级是否可接受。保存版本校验、受保护读取和当前轮不可变快照仅为候选机制，新增 I/O、锁等待和 R2 成本必须计入路线比较。

文件 offset/检查点仅是性能缓存，可以丢失并安全重建，不能冒充可靠上报 ACK 或崩溃恢复机制。无界 queue 也不是免费的：生产 design 仍需通知合并、queue depth/丢弃日志和有界关闭策略，避免慢后台造成内存积压。

## 4. 当前 after_turn 接缝的真实缺口

当前 `run/turn_hooks.py` 的 payload 只有 session_id、profile、cwd、数值 turn、status/failed；**没有稳定 turnId，也没有 saved**。无 HookManager 或无 after_turn hooks 时直接返回。`saved` 仅是 finalizer 局部变量，虽然 save/checkpoint 先于通知，但不会传给消费者。

因此生产候选应在 finalizer 的 save/checkpoint 后、外部 hooks 前设置定制 dispatcher，显式传 saved 和稳定 expected turn 身份；await 部分只构造不可变通知并 `put_nowait`。后续源码复核确认：runner 在 trajectory 激活前已经生成 logical/pass 身份，最小可靠方案需经 run-owned 快照把它们交给 finalizer，不能宣称只改 finalizer，也不能取 latest `TurnRecord`。这涉及上游接缝，必须另走实施 design/R2，不能用 test monkeypatch 冒充已具备；详见 `nodes/after-turn-lifecycle.md` 第14节。

## 5. 队列原型与正常退出边界

新增 test-local owner：每 session 一个 FIFO queue/worker，不同 session 独立；notify 同步 put_nowait；flush 有超时；close 幂等、必要时 cancel+gather。3 项实验通过：

- 同 session 第一个 reporter 阻塞时第二个不开始，释放后严格 FIFO；
- 两 session 可同时进入 reporter，最大活跃数为 2；
- 永久阻塞 reporter 的 flush 在 20ms 预算返回 False，close 可取消 worker，重复 close 安全。

初版 close 在 timeout=0 时创建未等待的 Queue.join 协程，产生 3 条 ResourceWarning；改为仅在 timeout>0 时创建 join 后，`3 passed in 0.06s` 且无警告。

这只证明原型调度语义。当前 engine hook inflight 不追踪自定义 reporter worker，TUI shutdown、ACP close/delete/EOF 是否调用 owner.flush/close 仍需生产接线和各自入口测试。active delete 应在目录删除前有界 flush，超时仍允许删除；目录已不存在时 reporter 必须 skip/deferred，不重建目录、不无限重试。强杀和崩溃不在保证范围。

## 6. 最终回归与下一步

定制实验、request tracking、compaction 和 fork 锚点共 `52 passed in 10.14s`，ruff 通过。本阶段关闭了“全量扫描无成本”和“expected-turn 过滤等同增量”的疑问，也暴露了真实通知契约缺口。

责任人随后要求继续严格按方向性优先级调查。after_turn稳定身份/saved/owner接缝现已完成只读复核：推荐run-owned身份快照+direct finalizer dispatcher+集中per-session lifecycle drain，最小候选为`turn_state.py`、`runner.py`、`finalizer.py`、`session_lifecycle.py`四个上游文件；trajectory disabled无需再接受身份缺失，也禁止latest回退。详见`nodes/after-turn-lifecycle.md`第14节。R2批准后才做真实after_turn→reader→reporter→mock垂直切片及真实ACP桌面闭环，M1-T的200/409、并发唯一和孤儿矩阵随后验证。
