# Session 文件重建与降级实验

> 2026-11-17。测试代码仅在 `aixcoding/tests/telemetry/test_tool_identity_persistence.py`；没有生产 analyzer、私人会话输入或上游修改。

## 1. 方法与判别标准

新增异步 `_reconstruct_from_files(session_dir, session_id, expected_turn_id=None)`。它重新实例化文件 store，只从 session/transcript/trajectory/mutation/blob 生成测试态 LLM/tool/ai-code，不接收 live message、A、T 或目标 call。重复 T、缺成功终态、多 mutation、参数不一致和 blob 不可用均 skip。补充复核后增加 `store.session_dir(session_id)==session_dir` 一致性断言，并用 `verify_accounted_prefix` 将未解释 sequence hole 标为 `trajectory-untrusted`；缺文件标为 `trajectory-absent`。store 构造有 mkdir/tombstone sweep 副作用，仅用于 tmp_path 副本。

正常样本为两轮三模型响应：文本 turn→write A1→最终 A2。期望 3 LLM/1 tool/1 ai-code，requestId 顺序等于实际三个 HTTP A，tool/ai-code 只取第二轮 A1/T，重复 reader 结果完全一致。

## 2. 失败修正留痕

- 初次 reader 使用 `message.content`，真实 API 为 `message.contents`，首轮 1 failed；修正后正常两轮 `1 passed in 2.14s`。
- 首轮五项降级结果 `1 failed, 4 passed, 12 deselected`：缺 blob 时 `read_blob()` 返回 None，实验误调 `.decode()`。按真实 API 显式把 None 转为降级信号后，`5 passed, 12 deselected in 2.80s`。
- 这些失败均为实验接口假设修正，没有放宽记录数量、身份或 skip 断言。

## 3. 降级结果

### Blob 缺失

真实 write 后删除 mutations 下唯一 blob，保留工作区 `degraded.py`。重建仍为 2 LLM/1 tool，ai-code 为空并记录 `ai-code-blob-or-arguments`；没有回读当前工作区补历史。

### 工具终态 gap

从真实 trajectory 删除 `tool.operation.finished`，其余 session/function_result/blob 不变。重建保留 2 LLM，tool/ai-code 均为空并记录 `tool-outcome-unknown`；补充复核后同时断言未解释 sequence hole 被标记为 `trajectory-untrusted`，该日志不再提供工具终态证据。没有从结果正文或后续文本猜成功。

### Fork

对父 session 调用真实 `fork_session()`。父目录仍为 2 LLM/1 tool/1 ai-code；fork 因继承 turn 的 origin 被排除，结果为零 LLM/tool/ai-code，不以新 sessionId 重报父历史。补充守卫后实测该直接 store fork 副本尚无 events 文件，故同时记录 `trajectory-absent`；不能假设父 trajectory 已复制或本地 opening 已生成。

### Save suppressed

第一轮正常保存，第二轮和 shutdown 均处于 `saves_suppressed()`。从 trajectory 取得当前 expected turn 后，guard reader 返回空集合和 `expected-turn-not-saved`。不带 guard 的 reader 只返回第一轮旧 A，证明它不能用于冒充当前轮；第二轮实际 A 不在 session 重建结果中。

## 4. Compaction 证据边界

真实 reader 尚未跑在 engine 自动 compaction 后的组合样本上。补充源码复核修正了初稿：Phase 3 fold 会把 fold range deep-copy 到 `compressed_msgs[*].messages`，原始消息及稳定 A/T/item/operation 元数据可在归档中保留；active `state["messages"]` 则被替换为 fold 前消息、SUMMARY 和 fold 后消息。transcript 不展开 archive，因此 transcript-only 确定会漏 folded 历史，但 archive 可作为有限 fallback，且必须按稳定 ID 去重，不能无差别并集 active+archive+trajectory。

Phase 1/2/4 仍可能以 tool summary/LAST_WORDS 替代内容，不保证所有 compaction 形态都有完整原始归档。正常 after_turn 在 save/checkpoint 后执行，saved=True 读到的是本 run compaction 后的文件；当前轮 A-final 可按 opener/nonmarker fail closed，但当前轮全部 A1/T 仍需 trajectory+mutation，尤其 Phase 4。复跑上游 `test_multi_turn_progressive_compaction`、`test_full_tool_phase_cascade` 和完整 `test_fork_session.py`，12 项通过；真实组合、archive 去重计数和 Phase 4 当前轮工具缺失仍未执行。

所以当前支持逐轮 after_turn，不支持承诺“压缩后完整补回全部历史 DTO”。本任务不做崩溃补报，该边界不推翻主路线；完整历史导出若成为需求必须重评。

## 5. 最终组合验证

```cmd
cd /d D:\Tech\Github\huawei\iCode\fork\iCode-fork && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run ruff check aixcoding/tests/telemetry && uv run ruff format --check aixcoding/tests/telemetry && uv run pytest aixcoding/tests/telemetry tests/service/llm/test_request_tracking.py tests/service/context/compaction/test_compaction.py::test_multi_turn_progressive_compaction tests/service/context/compaction/test_compaction.py::test_full_tool_phase_cascade tests/service/state/test_fork_session.py -n0
```

结果：ruff 通过，3 files already formatted；初次组合收集 48 项，`48 passed in 5.50s`。补充目录一致性、sequence hole/absent 守卫和 archive 表述修正后复跑，仍为 `48 passed in 6.44s`，退出 0。其中定制 26（含本轮文件重建 5）、request tracking 10、compaction 2、fork 10。

## 6. 未证明事项

没有真实用户脱敏样本，没有生产 cursor/reporter，没有完整 edit diff，没有真实 engine compaction×reader，没有全 trajectory 文件丢失组合，没有长会话性能或 flush 数据。下一阶段进入 P0-3 性能与正常退出，而不是把这些测试态结果写成生产已完成。
