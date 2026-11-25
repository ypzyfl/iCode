# 模型并发排队 · 内网验证步骤与说明（测试人员版）

> 适用：AIxCoding / iCode 内网版本（`feat/model-concurrency-queue` 分支）
> 读者：测试、内网联调、技术支持
> 日期：2026-11-20
> 目标：在内网真实网关上验证「排队能看见、放行能出字、超时不重试、中断能出队」，并能用日志定位失败点

---

## 0. 先看结论：验什么、不验什么

**验**：

1. 网关真实帧是否与客户端契约一致（裸 curl 抓帧）；
2. 客户端是否能吸收排队帧、显示进度、正常放行；
3. `QUEUE_TIMEOUT` / `QUEUE_FULL` 的处理；
4. 排队中中断是否真的调用 cancel 出队；
5. 日志是否足以回答「收到什么、解析成什么、取消发了什么、网关回了什么」。

**不验**（已知边界，不要当缺陷）：

- 子代理 / workflow 节点不显示排队提示；
- 非流式请求不接排队；
- CLI Ctrl+C 在事件循环关闭时可能漏发一次 cancel；
- `queueSize` 不进入 TUI/CLI 文案（事件/ACP 仍带）。

**快速流程（赶时间看这里）**：

1. 按 1.1 设 `AIXCODING_ENVIRONMENT=dev`，确认模型 profile 的 `base_url` 是测试网关；
2. 按 1.2 开 3 个标签页，确认每个窗口环境一致；
3. 按 1.3 单开一个窗口跟 detail 日志；
4. 窗口 A 发长请求占位，窗口 B 2 秒内发第二个请求；
5. 看 B 的排队行、放行、取消；日志取证按第 6 节，异常按第 8 节排查。

---

## 1. 开测前确认（缺一项就会白测）

### 1.1 设定环境：测试环境 / 生产环境

客户端用 `AIXCODING_ENVIRONMENT` 选择部署环境，取值：

| 取值 | 含义 | 用途 |
|---|---|---|
| `local` | 本机 mock | 开发自测，不用于内网联调 |
| `dev` | **测试环境** | 内网联调默认用这个 |
| `prod` | **生产环境** | 只在明确授权时使用 |

> 默认值是 `prod`。**不设置就是生产环境**，测试前必须确认当前值。
> 旧变量 `AIXCODING_AUTH_ENVIRONMENT` 已退役，不再生效，不要使用。

**方式 A：环境变量（当前窗口生效，优先级最高）**

Windows PowerShell：

```powershell
$env:AIXCODING_ENVIRONMENT = "dev"    # 测试环境
# $env:AIXCODING_ENVIRONMENT = "prod" # 生产环境（需授权）
$env:AIXCODING_ENVIRONMENT            # 确认当前值
```

Windows cmd：

```bat
set AIXCODING_ENVIRONMENT=dev
echo %AIXCODING_ENVIRONMENT%
```

Linux / macOS：

```bash
export AIXCODING_ENVIRONMENT=dev
echo "$AIXCODING_ENVIRONMENT"
```

需要对新开的窗口也生效时（PowerShell/cmd 均可）：

```powershell
setx AIXCODING_ENVIRONMENT dev
```

> `setx` 只影响**之后新开**的进程；当前窗口仍要用 `$env:` / `set` 设置。设置后建议重新登录/重启客户端。

**方式 B：共享配置文件（推荐，所有窗口一致）**

文件位置：

| 平台 | 路径 |
|---|---|
| Windows | `%APPDATA%\chrys\aixcoding.toml` |
| Linux / macOS | `~/.chrys/aixcoding.toml` |

内容（顶层一行即可；文件已存在就改这一行，不要重复添加）：

```toml
environment = "dev"
```

确认配置文件里的值：

```powershell
Get-Content "$env:APPDATA\chrys\aixcoding.toml" -Encoding utf8 |
  Select-String "^environment"
```

```bash
grep -E "^environment" ~/.chrys/aixcoding.toml
```

修改后重启客户端生效。优先级：**环境变量 > `aixcoding.toml` > 默认 `prod`**。

**设置后必须确认两件事：**

1. 当前窗口的环境值正确（上面的 `echo` / `$env:` 命令）；
2. **模型 profile 的 `base_url` 指向对应环境的网关**。环境选择主要影响登录与模型目录；LLM 推理地址来自模型 profile（服务端 `apiBase` 或手工配置）：

```powershell
Get-Content "$env:APPDATA\chrys\models\<模型id>.yaml" -Encoding utf8 |
  Select-String "base_url|http_read_timeout"
```

```bash
grep -E "base_url|http_read_timeout" ~/.chrys/models/<模型id>.yaml
```

| 环境 | profile `base_url` 应包含 |
|---|---|
| 测试 `dev` | `81.89.182.150` |
| 生产 `prod` | `82.187.34.98` |

> 不要打印/上传 `api_key`。只看 `base_url` 与 `http_read_timeout`。
> 如果 profile 是手工创建或桌面端注入的，切换环境变量**不会**自动改它的 `base_url`；以 profile 为准。
> 服务端目录同步的 profile 会按新环境重写；手工 profile 不受影响。

**环境地址（测试环境优先）**：

| 场景 | 网关基址 | completion 路径 |
|---|---|---|
| 测试环境 | `http://81.89.182.150/aicoding` | `/api/v3/chat/completions` |
| 生产环境（只在明确授权时） | `http://82.187.34.98/aicoding` | `/api/v3/chat/completions` |
| 直连地址 | `http://<host>:9098` | `/api/v3/chat/completions` |

> 不要把 auth 的 `/csas/api/v1`、user data 的 `/aicoding/api/v1` 当成推理网关地址；推理基址看模型 profile。

### 1.2 打开多窗口（占位 + 排队）

排队的验证核心是「先占住并发槽位，再发第二个请求」。至少需要两个窗口，推荐三个。

**Windows（Windows Terminal 推荐）**

1. 打开 Windows Terminal（或 PowerShell）；
2. 按 `Ctrl+Shift+T` 新开两个标签页（共三个），每个标签页是独立 shell；
3. 三个标签页都进入同一个工作目录：

```powershell
cd D:\project\iCode
```

4. **确认每个标签页的环境一致**（重要）：

```powershell
$env:AIXCODING_ENVIRONMENT
```

如果某个标签页显示为空或 `prod`，而你要测测试环境：
- 最稳妥：把 `environment = "dev"` 写进 `aixcoding.toml`（1.1 方式 B），然后重开标签页；
- 或者在每个标签页都执行 `$env:AIXCODING_ENVIRONMENT = "dev"`；
- 注意：在标签页 A 里设置的 `$env:` **不会**自动传给标签页 B。

5. 三窗口分工：

| 窗口 | 用途 | 命令 |
|---|---|---|
| A | 占住唯一并发槽位 | `aixcoding-cli run "写 2000 字" -a Code -m <测试模型> -C <工作目录>` |
| B | 排队观察 | 2 秒内执行：`aixcoding-cli run "你好" -a Code -m <测试模型> -C <工作目录> 2>&1 \| Tee-Object -FilePath cli-b.log` |
| C | 第三个并发/取消/日志跟踪 | 按用例执行；或 `Get-Content <detail日志> -Wait -Tail 50 -Encoding utf8` |

> 不要用 `&` / `Start-Job` 把 A 丢到后台后关掉窗口；用独立标签页，A 的请求要一直占着槽位，直到 B 看到排队。
> 如果 A 结束太快（短回答），B 还没来得及排队就放行了；把 A 的提示词改成长输出（如「写 2000 字」）。

**Windows（不用 Windows Terminal）**

直接开多个 PowerShell 窗口（开始菜单 → PowerShell，重复三次）。每个新窗口会继承用户/系统环境变量，但**不会**继承你在上一个窗口里临时设置的 `$env:`；所以要么用 `aixcoding.toml`，要么在每个窗口都设置一次。

**Linux / macOS**

开三个终端标签页，或使用 tmux：

```bash
tmux new -s queue
# Ctrl+b c 新建窗口，Ctrl+b n 切换；每个窗口单独 export 或统一用 aixcoding.toml
export AIXCODING_ENVIRONMENT=dev
```

**CLI 输出提示**

- 排队进度行在 **stderr**；`2>&1 | Tee-Object`（PowerShell）或 `2>&1 | tee`（bash）才能同时看到并落盘。
- 只重定向 stdout 会看不到排队行。
- 三个窗口建议都用同一个 `-m <测试模型>`，否则排的是不同模型的队列。

### 1.3 先确认日志能看（测试中要实时跟）

**detail 日志（CLI/TUI/ACP 都有）**：

| 平台 | 路径 |
|---|---|
| Windows | `%APPDATA%\chrys\aixcoding-logs\aixcoding.detail.log` |
| Linux / macOS | `~/.chrys/aixcoding-logs/aixcoding.detail.log` |

开测前执行一次命令（如 `aixcoding-cli run "你好" ...`），然后确认文件存在且在增长：

```powershell
$detail = "$env:APPDATA\chrys\aixcoding-logs\aixcoding.detail.log"
Test-Path $detail
Get-Item $detail | Select-Object FullName, Length, LastWriteTime
```

```bash
ls -l ~/.chrys/aixcoding-logs/aixcoding.detail.log
```

实时跟踪（测试时建议单独开一个窗口；新窗口里要重新定义 `$detail`）：

```powershell
$detail = "$env:APPDATA\chrys\aixcoding-logs\aixcoding.detail.log"
Get-Content $detail -Wait -Tail 50 -Encoding utf8
```

```bash
tail -f ~/.chrys/aixcoding-logs/aixcoding.detail.log
```

只看排队/取消相关行：

```powershell
Get-Content $detail -Wait -Tail 200 -Encoding utf8 |
  Select-String "网关排队|网关拒绝|取消排队|api_key"
```

```bash
tail -f ~/.chrys/aixcoding-logs/aixcoding.detail.log |
  grep -E "网关排队|网关拒绝|取消排队|api_key"
```

**TUI 内查看**：

- 按 **F6** 打开日志面板；排队模块的模块级日志在 **`chrys`** 标签页（不是 `aixcoding`）。
- 按 **Space** 切换级别过滤（DEBUG/INFO/WARNING/ERROR）。
- `aixcoding.detail.llm_queue` 是**文件专用**通道（`propagate=False`），**不会**出现在 F6；完整排队帧/取消报文必须看上面的 detail 文件。

**日志没出现时**：

1. 确认路径与平台（Windows 是 `%APPDATA%\chrys`，不是 `~/.chrys`）；
2. 看客户端 stderr 是否有 `aixcoding.logging: file sink unavailable ...`（有就是文件 sink 失败/权限问题）；
3. 日志按 1MB×4 轮转，长测试可能已切到 `aixcoding.detail.log.1`，检查同目录；
4. `aixcoding.toml` 的 `[logging] level` **不控制** queue 日志，不要靠改它来“打开”日志。

### 1.4 开测前确认表

| # | 确认项 | 怎么确认 | 负责人 |
|---|---|---|---|
| 1 | 网关已部署排队能力 | 网关同事确认测试环境版本包含 `model-concurrency-queue`；`POST /api/v3/chat/completions/cancel` 路由存在 | 网关 |
| 2 | 有可调的测试模型 | 专用 `modelKey`，可调 `max_concurrency` / `max_queue_size` / `max_wait_time`；**不要用生产模型** | 网关 |
| 3 | 客户端包包含本分支 | `aixcoding-cli --version`；发一条流式请求，网关入口能看到请求头 `Chrys-Request-Attempt-Id`（32 位 hex）；日志出现 `aixcoding llm-queue 定制不可用` 说明是回退包 | 测试 |
| 3b | **网关已支持请求头** | 网关同事确认版本会读 `Chrys-Request-Attempt-Id`（**请求头优先**，请求体 `request_id` 兜底）；**网关必须先上线**，否则新客户端 cancel 恒 404 | 网关 |
| 4 | 登录与模型可用 | TUI `/login` 或桌面端登录；`-m <模型>` 能正常问答 | 测试 |
| 5 | 环境与 profile | 每个窗口的 `AIXCODING_ENVIRONMENT` 一致（测试=`dev`）；profile `base_url` 指向测试网关、`http_read_timeout` > 20s | 测试 |
| 6 | 网络 | 能直连网关；若配了 `HTTP(S)_PROXY`，确认 `NO_PROXY` 包含网关；自签证书需确认 | 测试/运维 |
| 7 | 日志可看 | 1.3 的 detail 文件存在且在增长；知道实时跟踪命令 | 测试 |

---

## 2. 第一步：裸 curl 抓真实帧（不依赖客户端，最重要）

准备一个有效 `token`（找网关同事要测试 token，或在测试账号登录后抓取；**不要把 token 贴到工单**）。

### 2.1 占住唯一并发槽位

Windows PowerShell：

```powershell
$BASE = "http://81.89.182.150/aicoding"
$TOKEN = "<测试 token>"

curl.exe -N -sS --max-time 120 -H "token: $TOKEN" -H "Content-Type: application/json" `
  --data-raw '{"model":"<测试模型>","stream":true,"request_id":"drill-occupy-1","messages":[{"role":"user","content":"写 2000 字"}]}' `
  "$BASE/api/v3/chat/completions"
```

Linux/macOS：

```bash
BASE=http://81.89.182.150/aicoding
TOKEN=<测试 token>

curl -N -sS --max-time 120 -H "token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"model":"<测试模型>","stream":true,"request_id":"drill-occupy-1","messages":[{"role":"user","content":"写 2000 字"}]}' \
  "$BASE/api/v3/chat/completions"
```

### 2.2 第二个请求排队并留存原始帧

```powershell
curl.exe -N -sS --max-time 120 -H "token: $TOKEN" -H "Content-Type: application/json" `
  --data-raw '{"model":"<测试模型>","stream":true,"request_id":"drill-queued-1","messages":[{"role":"user","content":"你好"}]}' `
  "$BASE/api/v3/chat/completions" | Tee-Object -FilePath raw-queued.txt
```

```bash
curl -N -sS --max-time 120 -H "token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"model":"<测试模型>","stream":true,"request_id":"drill-queued-1","messages":[{"role":"user","content":"你好"}]}' \
  "$BASE/api/v3/chat/completions" | tee raw-queued.txt
```

### 2.3 逐项核对原始帧

| 检查 | 期望 | 不符时 |
|---|---|---|
| 事件名 | `event:queue_status` / `event:queue_rejected` | 记录原文，网关契约不一致 |
| `queue_status` data | `{"position":int,"queueSize":int}`；`choices` 为 `null`；帧内无 `id`/`usage` | 客户端可能判 invalid response；把原文交给开发 |
| 心跳间隔 | 约 20s | 影响 `http_read_timeout` 配置 |
| `queue_rejected` body | `{"error":{"code","message","traceId"}}` | 客户端转译可能不命中 |
| 放行 | 不再推 `queue_status`，开始 `data:` 帧 | — |

### 2.4 验证 cancel 路由（排队中执行）

再开一个窗口，在第二个请求仍排队时：

```powershell
curl.exe -i -X POST -H "token: $TOKEN" -H "Content-Type: application/json" `
  --data-raw '{"model":"<测试模型>","request_id":"drill-queued-1"}' `
  "$BASE/api/v3/chat/completions/cancel"
```

```bash
curl -i -X POST -H "token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"model":"<测试模型>","request_id":"drill-queued-1"}' \
  "$BASE/api/v3/chat/completions/cancel"
```

| 结果 | 含义 | 处置 |
|---|---|---|
| `204` | 取消成功；原流应收到 `queue_rejected(QUEUE_CANCELLED)` + `[DONE]` | 通过 |
| `409 REQUEST_ALREADY_RUNNING` | 已放行，无法取消 | 契约正常；重排队再试 |
| `404 REQUEST_NOT_FOUND` | 未排队/已完结/已取消 | 检查 `request_id` 与 model |
| `401/403` | token 不对/头不对 | 换测试 token；检查代理是否改写头 |
| `405` / HTML 404 | 路径或代理不对 | 核对 `base_url` 前缀与网关路由 |

---

## 3. 第二步：客户端展示（CLI / TUI / ACP）

> 客户端请求与 curl 共用同一个测试模型；先占位，才能看到排队。

### 3.1 CLI

窗口 A（占位）：

```powershell
aixcoding-cli run "写 2000 字" -a Code -m <测试模型> -C <工作目录>
```

窗口 B（2 秒内）：

```powershell
aixcoding-cli run "你好" -a Code -m <测试模型> -C <工作目录> 2>&1 | Tee-Object -FilePath cli-b.log
```

预期（B 的 stderr）：

```text
• 当前模型请求量大，请求排队约 1 人
（A 结束后）
• 已排到队首，当前为队列第一位
```

- 同一 position 只出现一次（心跳去重）；
- 名次前进时出现新行；
- A 结束后 B 开始出字。

### 3.2 TUI

先 CLI 占位，再：

```powershell
aixcoding-cli -m <测试模型>
```

在 TUI 发一句话，观察等待行：

1. 出现「当前模型请求量大，请求排队约 N 人」；
2. 名次前进时更新；
3. `position=0` 变「已排到队首，当前为队列第一位」（仍可能随后排队超时，属网关语义）；
4. 首个回答字到达，文案消失；
5. 下一轮开始不残留。

### 3.3 ACP / 桌面端

用桌面端或 ACP 客户端连接 `aixcoding-cli acp`，排队时观察扩展通知：

```json
{"sessionId":"...","requestId":"<32位hex>","position":1,"queueSize":2}
{"sessionId":"...","requestId":"<32位hex>","position":0,"queueSize":1}
{"sessionId":"...","requestId":"<32位hex>","released":true}
```

- 同一 `(requestId, position)` 只发一次；重试产生新 `requestId`，同名次也重发；
- `requestId` 等于该次请求的 `Chrys-Request-Attempt-Id` 请求头值（网关日志可对齐），可能缺席（tracker 未武装）；
- 放行后有 `released: true`；
- 若桌面端不显示，先确认客户端是否消费 `_chrys/queue_status`（线上名带 `_` 前缀；这是桌面端/插件侧责任）。

---

## 4. 第三步：异常分支

### 4.1 长排队心跳（P1）

- 测试 profile 临时把 `http_read_timeout` 调到 25s；
- 占位 60s，让 B 排队 60s+；
- 预期：B 不断流、不重排，detail 日志持续有 `网关排队心跳`；
- 反证：调到 15s，B 应在心跳间隙断流（证明心跳续活生效）。

### 4.2 排队超时 `QUEUE_TIMEOUT`（P0）

- 网关把测试模型 `max_wait_time` 调到 15s；占位 60s；
- 预期：B 约 15s 后结束，显示网关 message（如「排队等待超时」），**没有** `↻ Retrying` 横幅；
- detail 日志：`网关拒绝排队请求：code=QUEUE_TIMEOUT retryable=False` + `响应解析`。

### 4.3 队列满 `QUEUE_FULL`（P1）

- `max_concurrency=1`、`max_queue_size=1`，三窗口并发；
- 预期：第三个请求报 `QUEUE_FULL`，出现退避重试横幅；
- detail 日志：`网关队列已满（QUEUE_FULL）…`。

---

## 5. 第四步：取消排队（重点，含鉴权风险）

### 5.1 TUI 排队中 Interrupt

1. 先占位；TUI 发请求，确认出现排队文案；
2. 立即点 **Interrupt**（或 Esc）；
3. 预期：TUI 立即按「已中断」收尾，不等放行；
4. 网关日志出现 cancel，`request_id` 与主请求一致；
5. detail 日志：

```text
正在离开网关队列：POST http://.../api/v3/chat/completions/cancel，model=...，request_id=...
发送取消排队请求：POST http://.../api/v3/chat/completions/cancel，
  body={'model': '...', 'request_id': '...'}，token=已携带
取消排队响应：status=204，请求已出队（request_id=...，endpoint=...）
```

### 5.2 ACP `session/cancel`

排队中发 `session/cancel`：

- `stop reason: cancelled`；
- 网关 cancel `204`；
- detail 日志同上。

### 5.3 反例

- 等首字出现后再中断 → 网关日志**无** cancel（已放行）；
- 网关空闲时直接中断 → **无** cancel（从未排队）；
- 放行后、首字前的窄窗口中断 → 可能发一次 cancel 并收 `409`，属契约正常。

### 5.4 取消没发出？按日志定位

| detail 日志 | 含义 | 处置 |
|---|---|---|
| `网关排队取消跳过：没有 api_key，请求将留在队列中` | profile 没有 `api_key`（纯登录态），cancel 被跳过 | **已知风险**，记录为待修；见 5.5 |
| `取消排队响应：status=401/403` | token 不对/头被代理改写 | 换 token/查代理 |
| `网关排队取消无法连接 …` | URL 推导错 / 代理 / TLS | 核对 endpoint、NO_PROXY、证书 |
| 完全没有 `正在离开网关队列` | 已放行、从未排队，或 CLI Ctrl+C 时序 | 用 TUI/ACP 复测；看是否有 `网关排队取消已就绪`（detail DEBUG） |
| `aixcoding llm-queue 定制不可用` | 安装包不含定制/导入失败 | 换包，不是功能缺陷 |

### 5.5 已知风险：cancel 的 token 与登录态不同源

- 当前 cancel 请求的 `token` 取 profile `api_key`；主请求的 `token` 来自登录会话。
- 如果内网 profile **没有 api_key**（纯登录态），取消会被静默跳过（现在会打 WARNING）。
- 验收时把这一项单独记录：**「排队中取消」是否真正发出 cancel**，不要只看 UI 是否收尾。
- 如果是这个原因，取消功能不能算通过；需要后续最小修复（`登录 token or api_key`）。

---

## 6. 第五步：日志取证

### 6.1 路径

| 平台 | detail 日志（CLI/TUI/ACP 都有） | TUI debug 日志 |
|---|---|---|
| Windows | `%APPDATA%\chrys\aixcoding-logs\aixcoding.detail.log` | `%APPDATA%\chrys\logs\debug.log` |
| Linux / macOS | `~/.chrys/aixcoding-logs/aixcoding.detail.log` | `~/.chrys/logs/debug.log` |

> CLI 没有 INFO 文件日志；**CLI/ACP 的详细取证只能看 detail 日志**。
> `aixcoding.toml` 的 `[logging] level` 不控制这些 queue 日志，别用它当开关。

### 6.2 测试中实时查看

开测前先按 1.3 确认文件存在。测试过程中单开一个窗口跟日志：

```powershell
$detail = "$env:APPDATA\chrys\aixcoding-logs\aixcoding.detail.log"
Get-Content $detail -Wait -Tail 50 -Encoding utf8
```

> 新开的窗口不会继承上一个窗口的 `$detail`，先执行第一行。

```bash
tail -f ~/.chrys/aixcoding-logs/aixcoding.detail.log
```

只看排队/取消：

```powershell
Get-Content $detail -Wait -Tail 200 -Encoding utf8 |
  Select-String "网关排队|网关拒绝|取消排队|api_key"
```

```bash
tail -f ~/.chrys/aixcoding-logs/aixcoding.detail.log |
  grep -E "网关排队|网关拒绝|取消排队|api_key"
```

TUI 内按 **F6** 看模块级日志：排队模块的 INFO/WARNING 在 **`chrys`** 标签页；detail 通道是文件专用，不在 F6。

### 6.3 测试后抓取与按 `request_id` 追踪

Windows PowerShell：

```powershell
$detail = "$env:APPDATA\chrys\aixcoding-logs\aixcoding.detail.log"
Get-Content $detail -Encoding utf8 |
  Select-String -Pattern "网关排队|网关拒绝|取消排队|api_key|契约" |
  Select-Object -Last 200
```

Linux/macOS：

```bash
grep -E "网关排队|网关拒绝|取消排队|api_key" \
  ~/.chrys/aixcoding-logs/aixcoding.detail.log | tail -200
```

拿到本次请求的 `request_id` 后（详情里的 `正在离开网关队列` 或 `网关排队取消已就绪`），把整条链路的日志一次捞出：

```powershell
$rid = "<request_id>"
Get-Content $detail -Encoding utf8 | Select-String $rid
```

```bash
grep "<request_id>" ~/.chrys/aixcoding-logs/aixcoding.detail.log
```

日志按 1MB×4 轮转；如果当前文件里没有，检查同目录的 `aixcoding.detail.log.1` 等备份。

### 6.4 一次完整排队应看到的日志

```text
网关排队：position=2 queueSize=5
网关排队帧（解析后）：{... 'model_extra': {'position': 2, 'queueSize': 5, ...}}
网关排队心跳：position=1 queueSize=4（第 2 帧），解析后：...
网关已放行排队请求（此前收到 2 个排队帧）
网关排队等待 12.3 秒后放行
排队放行后收到首个数据帧：{...}
```

一次取消应看到：

```text
网关排队取消已就绪：request_id=... endpoint=... model=... base_url=...
正在离开网关队列：POST <url>，model=...，request_id=...
发送取消排队请求：POST <url>，body={'model': '...', 'request_id': '...'}，token=已携带
取消排队响应：status=204，请求已出队（request_id=...，endpoint=...）
```

### 6.5 提交问题时的最小附件

1. 场景与时间（含时区）；
2. 客户端 detail 日志片段（不要贴 token）；
3. 网关侧同一 `request_id` 的日志（排队/放行/ cancel）；
4. 若是帧契约问题，附 `raw-queued.txt` 原始 SSE 片段；
5. 客户端版本 `aixcoding-cli --version` 与模型 profile 的 `base_url`（不贴 api_key）。

---

## 7. 判定表

| 用例 | 通过标准 |
|---|---|
| TC-01 直通 | 无排队行，正常回答 |
| TC-02 CLI 排队 | 文案出现一次、名次更新、放行转「已排到队首，当前为队列第一位」 |
| TC-04 TUI | 等待行文案出现/更新/消失/不残留 |
| TC-05 ACP | 通知按 position 去重，有 `released:true` |
| TC-06 心跳 | 排队 60s 不断流；反证配置能断 |
| TC-07 超时 | 透出 message，无 `↻ Retrying` |
| TC-08 满队 | 出现退避重试 |
| TC-09/10 取消 | 网关收到同一 `request_id` 的 cancel，204 |
| TC-11/12 反例 | 已放行/未排队不发 cancel |
| TC-17 日志 | 能回答收到什么、解析成什么、取消发了什么、网关回了什么 |
| TC-19 请求头 | `Chrys-Request-Attempt-Id` 32 位 hex、每次 HTTP 尝试不同；请求体无 `request_id`；非流式也带该头 |
| TC-20 URL | curl cancel 返回 404/409/401 而非 405/HTML |

---

## 8. 常见问题排查

| 现象 | 可能原因 | 处置 |
|---|---|---|
| 完全没有排队行 | 网关空闲 / 模型未配并发上限 / 包是旧的 / `-m` 没选对 | 先占位；核对模型与包；看 detail 有无「网关排队」 |
| 排队时 invalid response | 真实帧形状不符合判据（多了 `id`/`usage`、`choices:[]`、字段类型不对） | 看 WARNING「无法识别的网关排队帧」；附原始 SSE 给开发 |
| 排队超时后自动重试 | 包是旧的（转译未生效） | 核对版本；detail 应有 `retryable=False` |
| 排队中中断但网关无 cancel | `api_key` 为空 / 已放行 / CLI Ctrl+C 时序 / URL/代理 | 看 detail 的取消日志按 5.4 定位 |
| CLI 看不到详细日志 | CLI 无 INFO 文件日志 | 看 `aixcoding.detail.log` |
| detail 日志不存在 | 启动时文件 sink 失败 / 路径不对 | 看 stderr 是否有 `aixcoding.logging: file sink unavailable` |
| 中文乱码 | 终端/编辑器编码 | 用 UTF-8 打开；PowerShell `Get-Content -Encoding utf8` |
| ACP 没有排队通知 | 桌面端未消费 `chrys/queue_status` | 先确认客户端侧；服务端不代替渲染 |
| 子代理/workflow 没提示 | 设计边界 | 不是缺陷；detail 日志应有记录 |

---

## 9. 安全与纪律

- 只在**测试环境/专用测试模型**上调并发参数；不要在生产模型上调 `max_concurrency=1`。
- 不要在工单、截图、聊天中贴 `token`、`api_key`、完整请求头。
- 原始 SSE / 日志可能包含用户提示词；按内部数据规范传递。
- 触发 cancel 失败时不要反复重试线上请求；记录日志后联系开发。
