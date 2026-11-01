# 测试方案：服务组合测试（composition-tests）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。
> design 已签认（2026-11-01，含首轮评审 8 findings 处置）；本文钉死 design 留给本步的
> 调用形态与验收细节。

## 测试范围与策略

- **层级**：组合级（composition root——真实生产工厂 + 真实登录会话 + 进程内 loopback 拦截）。
  一个测试文件贯穿凭据生命周期主链路；**主用例单用例贯穿三阶段**（同一 client 实例跨
  登录/登出是本批语义核心，拆分即失去组合意义）。
- **落点**：`aixcoding/tests/auth/test_composition_lifecycle.py`（受益 `tests/auth/conftest.py`
  窄域防呆：委托钳制 + 默认构造隔离）。
- **mock 边界**：`aixcoding/mock/auth`（真实登录服务 wire 复刻，零改动）+ 测试文件内
  `_LoopbackLLM`（进程内 LLM stub，本批新增）；`MemoryBackend` 替代平台持久化层。以上均为
  协作对象。**行为锚定（§5，禁 mock 锚点本身）**：

| anchor（依赖的上游符号） | 锚定方式（真实调用） | 主用例体现 |
|---|---|---|
| `create_client(ModelProfile)` 生产工厂 | 真实调用构造 stack，禁止自建 SDK client | client 创建步骤 |
| `RequestHeaders.stamp()` / `login_token_header_value()` / `get_login_session()` | 生产链路内真实走到（`get_response` → wire 层 → stamp），不 patch 这三个符号 | 快照[1] 的 `token` 出现即其行为证明 |
| openai SDK 装配 + `default_headers`×`extra_headers` 合并 | 真实 SDK client + 真实 httpx 栈经 loopback | 快照逐次 header 值 |
| `LoginSession` 登录状态机 | 真实 `request_device_code()` + `complete_login()` 驱动 | 登录步骤（第七约束：唯一登录态来源） |

## 调用形态（design 决策三留待本文钉死）

- **profile 构造**（上游先例 `tests/service/llm/test_network_faults_real_sdk.py::_profile`
  同款 + F-01/F-04 处置）：

  ```python
  ModelProfile(
      id="composition-test",
      name="composition-test",
      provider="openai",
      model_id="test-model",  # 非空必填（F-04 条 1）
      base_url=llm_stub.base_url,  # stub 的 loopback URL（SDK 自动拼 /chat/completions）
      api_key="k-test",  # 静态凭据（Authorization 断言对象）
      bypass_proxy=True,  # F-01：公开字段隔离代理，不依赖 NO_PROXY 环境
  )
  ```

- **三次请求驱动**（上游先例 `test_openai_chat_completion.py:1050` 的 Message 构造 +
  `loop.py:2266` 签名）：

  ```python
  from chrys.kernel import Message

  # 每次请求（惰性 Awaitable，必须真实 await——F-04 条 2/3）：
  response = await client.get_response(
      [Message("user", ["hi"])],
      stream=False,
      options={},
  )
  ```

  调用形态硬约束五条（design 决策三）逐条对应：非空 `model_id` ✓（profile）、显式
  `stream=False` ✓、真实 `await` ✓、stub 响应恒为合法无 tool call 无 continuation 的普通
  JSON completion ✓（不传 SSE）、不传 retry/compaction 等额外参数 ✓（仅 `options={}`）。

- **stub 响应体**：标准 OpenAI chat completion JSON（`id`/`object`/`created`/`model`/
  `choices[{index, message:{role, content}, finish_reason:"stop"}]`/`usage`——参照
  `test_llm_token_wiring.py` channel 2 handler 响应体形态）；恒 HTTP 200（不触发 SDK 重试）。
- **快照结构**：`list[dict]`，每项 `{seq: int, token: str | None, authorization: str | None}`
  （凭据相关两 header 的逐次最终值；串行请求下 handler 在响应前写入、await 返回后读取，
  无需锁——design 时序基线）。**计数基线 = 3**（每阶段恰一次；偏离即红，按 design 假设 5
  处置口径调整前先查明原因）。
- **登录时序基线（F-07）**：`mode="auto", interval=0` 下首次 token poll 返回 pending，
  客户端固定等待约 1 秒后二次 poll authorized——测试预算按 ≥1 秒计，不写紧超时。

## 覆盖矩阵

| 验收标准（requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| AC1 形态 A 六条件 + 第七约束 | `test_composition_lifecycle.py::test_credential_lifecycle_through_production_stack`（六条件映射：真实工厂=client 创建；loopback=stub/base_url；同实例三次=三段请求；逐次快照=断言依据；真实 LoginSession+CredentialStore=登录步骤；mock auth 契约=auto 模式真实轮询。第七约束=登录仅经 `complete_login()`，代码中无任何手工注入/直写 store） | 组合 |
| AC2 三次请求逐次断言 | 同主用例三段：快照[0] 无 `token` + `Authorization=="Bearer k-test"`；快照[1] `token==登录签发值` + Authorization 不变；快照[2] 无 `token` 键 + Authorization 不变 | 组合（断言精确表见 design"三次请求断言"） |
| AC3 同一性断言 | 主用例前置步骤：patch `auth_session._default_session = session` 后，经包级 `chrys.kernel.aixcoding.auth.get_login_session()` 断言 `is session`（真实单例函数路径） | 组合 |
| AC4 环境前置 | 主用例 fixture：清三委托通道变量 → 从包级/`.delegation` 调**真实** `detect_delegation()` 断言 `is None`（时点在 session 构造前）→ 显式固定 auth 环境/endpoint/profile | 组合 |
| AC5 快照设施 | `_LoopbackLLM` 实现（序号 + `token` + `Authorization`；内存态；stub 无持久日志写入；断言不打印完整快照） | 组合（设施被主用例消费） |
| AC6 上游零文件改动 | 非测试用例：PR diff + R2 门（`check_r2_diff.py`）核验 | 人工/CI |
| AC7 双通道绿 | verification.md：`verify.py --smart`（本地）+ 定制门 CI（PR） | 验证步骤 |
| AC8 文档联动 | verification/self-review 落盘（实施与交付阶段） | 流程 |

## 异常与降级路径

- 本批是**检测器**（组合语义冲突时红是价值而非缺陷）——不设计"容忍失败"的降级路径；
  断言失败即失败，失败输出避免打印完整快照（F-08：凭据为 mock 值，不引入脱敏设施）；
- **资源清理的异常路径（F-05）**：client 创建后立即 `try/finally: await client.aclose()`；
  两个 server 以 context manager 进入/退出（`shutdown()` + `server_close()`）——用例内任一
  步骤抛异常，stack 与 server 均被释放，不向同进程后续测试泄漏连接池/线程；
- **快照计数偏离**（假设 5 失效场景）：断言 `len(快照)==3` 先于逐次断言——多发/少发请求
  时给出计数事实再红，便于定位（上游装配链变化 vs stub 响应不合法）。

## 手工验证步骤

```bash
# 1. 单文件调试（-n0 关并行，观察时序）
uv run pytest aixcoding/tests/auth/test_composition_lifecycle.py -v -n0

# 2. 定制套件整域 + 上游委托（本地统一入口，P0 批次）
uv run python aixcoding/tools/verify.py --smart --paths aixcoding/tests/auth/test_composition_lifecycle.py

# 3. lint（目录级豁免已就位）
uv run ruff check aixcoding/ && uv run ruff format --check aixcoding/
```

结果（含用时，对照时序基线与预算监控口径）记入 verification.md；PR 阶段以定制门 +
上游门双 CI 为准。
