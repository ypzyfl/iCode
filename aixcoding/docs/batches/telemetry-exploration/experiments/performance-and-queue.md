# 性能与 after_turn 队列实验

> 2026-11-17。测试代码仅在定制 `aixcoding/tests/telemetry/`，不设生产性能阈值。

## 1. 基准方法

`test_session_scan_benchmark_full_vs_expected_turn` 创建 30 轮真实 session：14 个工具轮、6 个独立 write_file。每轮 finalizer 后分别测全历史和 expected-turn reader，断言当前轮 LLM/tool/ai-code 与全量结果的 span 子集一致；5/15/30 轮各取 3 次中位数，并记录 session/trajectory/mutation 大小。

初稿反复写 `benchmark.py`，真实 write_file 以 `file_exists` 失败；改为 `benchmark-{turn}.py` 后通过。诊断曾怀疑工具终态异步落盘，但完整 payload 证明是真实失败，未按错误假设修改 telemetry。

## 2. 测量结果

| turn | session KiB | trajectory KiB | full median ms | expected median ms |
|---:|---:|---:|---:|---:|
| 5 | 25.8 | 119.1 | 7.307 | 7.329 |
| 15 | 75.7 | 370.0 | 20.942 | 18.921 |
| 30 | 149.1 | 742.0 | 38.409 | 38.439 |

最终 44 LLM/14 tool/6 ai-code。30 轮主测量累计 full=638.960ms、expected=711.301ms；两者都完整读文件，expected 只裁报文，不是增量 I/O。单次基准 `1 passed in 7.02s`。

## 3. 队列原型

`test_after_turn_queue.py` 实现 test-local per-session FIFO worker：

- 同 session 阻塞时严格串行，释放后按 turn-1/turn-2 完成；
- 不同 session 可同时进入 reporter；
- 永久阻塞时 flush(timeout=0.02) 返回 False 且总等待小于 0.2s；close cancel+gather，重复 close 安全；
- 初版 timeout=0 创建未等待 join 协程，出现 3 条 ResourceWarning；修复后 `3 passed in 0.06s`，无警告。

该原型未接真实 finalizer/engine，不证明生产 after_turn 已非阻塞或 TUI/ACP 已 flush。静态复核确认当前 after_turn 无稳定 turnId/saved，无 hooks 时 early return，engine 也不自动追踪自定义 worker；这些均留实施 design/R2。

## 4. 最终组合命令

```cmd
cd /d D:\Tech\Github\huawei\iCode\fork\iCode-fork && set "PYTHONPATH=" && set "PYTHONUTF8=1" && uv run ruff check aixcoding/tests/telemetry && uv run ruff format --check aixcoding/tests/telemetry && uv run pytest aixcoding/tests/telemetry tests/service/llm/test_request_tracking.py tests/service/context/compaction/test_compaction.py::test_multi_turn_progressive_compaction tests/service/context/compaction/test_compaction.py::test_full_tool_phase_cascade tests/service/state/test_fork_session.py -n0
```

结果：ruff 通过，4 files already formatted；收集 52 项，`52 passed in 10.14s`，退出 0。其中定制 30、request tracking 10、compaction 2、fork 10。

## 5. 未证明事项

没有生产 reader 的单次 session 加载优化、增量 offset、真实长会话大 blob、queue depth 背压、真实 finalizer/engine flush、TUI unmount、ACP EOF/delete 或内网后台验收。下一步 M1-T mock/reporter 契约可独立调查；真实上游接线不得借本实验提前实施。
