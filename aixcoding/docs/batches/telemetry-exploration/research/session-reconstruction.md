# 真实 session 文件重建正确性

> 2026-11-17。范围：临时目录中由真实 engine 生成的生产格式 session，不读取私人 `~/.chrys`；测试态 reader 只接收 `session_dir + session_id` 和可选 expected turn，不使用 live message、已知 A/T 或预期报文倒推。结论：正常未压缩历史可精确重建，降级可以 fail closed；`save=False` 必须有 expected turn 守卫，fork 必须排除继承历史，compaction 后不能承诺完整历史补报。

## 1. 与既有 M0/M1 的区别

M0/M1 已证明单一样本的 A1/A2/T 关系，但报文构造仍知道目标 call 和 turn。本轮新增 `_reconstruct_from_files()` 作为方向性测试 reader：

- 通过新的 `JsonFileStateStore` 重新加载 session/transcript，并断言 `store.session_dir(session_id)==session_dir`；构造器会 mkdir/tombstone sweep，所以只允许对 tmp_path 副本这样做，不能当作任意真实目录上的纯只读操作；
- 从 turn opener/registry 对齐 active messages；
- 从 assistant message 取 A，从 function_call 取 T 和最终参数；
- 从 trajectory 只接受明确 success 的工具终态，并检查 corrupt/torn/unsupported 与 `verify_accounted_prefix`；缺文件记录 `trajectory-absent`，未解释 sequence hole 记录 `trajectory-untrusted`；
- 从 mutation ledger 和 blob 构造简单 write_file ai-code；
- 对缺 A/T、重复 T、缺成功终态、同 T 多 mutation、参数/blob 不一致全部记录 skip；
- 它是定制实验，不是生产 analyzer，不支持完整 edit diff 或全工具矩阵。

## 2. 正常多轮精确性

真实两轮样本：第一轮一条文本 LLM；第二轮 A1 write_file→A2 最终文本。

仅从文件重建得到：

- 三条 LLM，requestId 转回 raw 后与三个实际 HTTP A 完全同序；
- 两个不同 turn span，第二轮 A1/A2 共用同一 span；
- 一个 tool-detail 和一个 ai-code，均取第二轮 A1/T，不取 A2；
- ai-code blocks 为 `first\nsecond\n`，与 after blob 一致；
- 重复运行 reader 的完整结果完全相同，无重复或顺序漂移。

这证明正常未压缩 session 的“文件里有数据”可以转化为确定性的正确组包，不只是静态字段检查。

## 3. `save=False`：最重要的新行为边界

第一轮正常保存，第二轮在 `saves_suppressed()` 中成功执行，shutdown 也保持抑制：

- trajectory 已有第二轮 turn ID；
- session.json 仍只有第一轮；
- 不带 expected turn 的全扫描会返回第一轮旧 LLM，不能说明“第二轮已上报”；
- 传当前 expected turn 时，reader 返回空 LLM/tool/ai-code，并记录 `expected-turn-not-saved`。

因此 `after_turn` 接口不能只通知 session_dir/session_id，必须携带本轮 expected turn ID 和保存结果，或在通知层明确 `saved=False` 直接跳过。**禁止把旧 session 文件当成本轮成功证据。**这也意味着“每轮无差别读取整个目录并上报所有找到的记录”并不安全，必须有 turn/cursor 归属。

## 4. trajectory 终态缺口与 blob 缺失

| 故障 | 实测结果 | 正确降级 |
|---|---|---|
| 删除 write 工具的 `tool.operation.finished` | 两条 LLM 仍在；tool/ai-code 均为空；同时记录 `trajectory-untrusted` 和 outcome unknown | sequence hole 由 `verify_accounted_prefix` 检出，禁用该 trajectory 的终态证据，不从 function_result 猜成功 |
| 删除唯一 after blob，工作区文件仍存在 | 两条 LLM 和一个 tool 保留；ai-code 为空并记录 blob/args 降级 | 不读当前工作区文件冒充历史 after |
| trajectory 文件完全不可用 | events 为空并记录 `trajectory-absent`；工具/ai-code 不形成；LLM 能否归属仍取决于 session turn registry | 本轮在 fork 副本上实测了 absent；独立正常 session 的全 trajectory disabled 组合仍待做 |

实测还核正了两个实验假设：当前 `Message` 字段是 `contents`；`SnapshotStore.read_blob()` 缺 blob 返回 None，而不是抛出 FileNotFoundError。生产 analyzer 必须处理 None。`read_trajectory()` 缺文件会返回空结果而非抛错，不能只遍历 events 就宣称日志健康。

## 5. fork：继承历史不能换 sessionId 重报

真实 `fork_session()` 复制包含两条 LLM、一个工具和一个 mutation 的父 session。原 session 重建结果不变；fork reader 因 turn registry 的 `origin_session_id` 排除继承 turn，返回空 LLM/tool/ai-code，并因该直接 store fork 副本尚无 events 文件而记录 `trajectory-absent`。这修正了“fork 一定已有本地 trajectory”的假设；完整 engine fork opening 组合仍另留验证。

如果只看复制的 messages/mutations，不过滤 origin，就会把父历史以新 sessionId 再报一遍。当前结论适用于“父 turn 已按原 session 上报”的逐轮 telemetry；若未来要求独立完整导出 fork 历史，需要另立去重/归属语义，不能混用。

## 6. compaction：有限归档、去重与完整历史补报的边界

当前源码明确 Phase 3/force fold 会 deep-copy fold range 到 `compressed_msgs[*].messages`，原始消息及其 A/T/item/operation 元数据可在该归档副本中保留；随后 active `state["messages"]` 被替换为 fold 前消息、SUMMARY marker 和 fold 后消息。`load_session_transcript()` 不展开 compressed blocks 并跳过 `_excluded`，所以 transcript 对 folded 历史确定不完整；但“compressed block 一概不含原始 A/T/参数”的旧表述不准确，已修正。

这仍不意味着所有 compaction 历史都可完整恢复：Phase 1/2/4 还可能用 tool summary/LAST_WORDS 替代被丢内容，不保证每种形态都有完整归档。正常重建应以 trajectory 为历史执行权威，session archive 只作有限 fallback；稳定 ID 可用于去重，不能无去重地并集 active+archive+trajectory，否则会把同一执行重复上报。

当前有界结论：

1. 正常 finalizer 在 `save_current_session()` 和 trajectory checkpoint 后才 fire after_turn；saved=True 时读取的是本 run compaction 后的文件，而不是 compaction 前旧快照；
2. 当前轮 A-final 可用 expected opener + nonmarker assistant fail-closed 选择，旧 folded A 不应冒充当前 A；这不等于当前轮全部 A1/T 都能从 session-only 恢复，尤其 Phase 4 仍须 trajectory+mutation；
3. 持久化 cursor/已报记录不应因后续 compaction 而被重新解释；archive fallback 必须按稳定身份去重；
4. 压缩后的 session 仍不能保证补回所有旧轮原始 DTO，缺证据时只能跳过；本任务不做崩溃补报，所以这不是需要发明恢复算法的方向性阻塞，完整历史导出若成为需求则必须重评。

上游 progressive compaction/full cascade 两项行为锚点本轮复跑通过，但尚未生成“真实 engine compaction 后运行本 reader”的组合样本；以上真实组合、archive 去重计数和 Phase 4 当前轮工具缺失不得记成已通过。

## 7. 当前正确性矩阵

| 场景 | 证据等级 | 结果 |
|---|---|---|
| 正常两轮/一轮两次模型 | 真实文件组合实验 | 3 LLM/1 tool/1 ai-code 精确且确定性通过 |
| 同一 A1 两工具 | M1 真实文件实验 | 两个 funcId、唯一 write ai-code，通过 |
| blob 缺失 | 真实文件组合实验 | 仅 ai-code 跳过，通过 |
| 工具终态 gap | 真实文件删除终态事件 | LLM 保留，tool/ai-code fail closed |
| save=False | 真实 suppressed save 组合实验 | expected turn 守卫通过；无守卫会返回旧轮 |
| fork | 真实 fork 文件 + reader | 继承历史零重报 |
| compaction | 源码 + 上游两项锚点 | folded 历史不可保证完整补报；真实组合样本待做 |
| 私人/现网真实 session | 未读取 | 不宣称覆盖率；后续只能使用明确授权的脱敏样本 |

## 8. 下一步

2026-11-19 F1–F3 裁决后，批次1先完成延迟读取/新 pass/当前轮真实压缩的最小判别，再扩大 reporter/ACP 开发。生产实现必须固定 expected logical turn+pass、saved、fork-origin、记录级一致性和防重语义；V3 须在同 turn 早期模型调用与工具修改后触发实际压缩，再仅凭保存数据核对恢复数量、关联和必需字段，并列出全部恢复/跳过记录。不能恢复且责任人不接受降级时停止扩张，裁决补采或快照并重估成本。完整压缩矩阵和完整 edit 重建仍可留批次3。
