#把拦截功能装到一份iCode 源码上

面向"手上有一份原版 iCode 源码"的场景。**全程不需要改 iCode 一行代码。**

回答四个问题：文件放哪、hook 配什么、怎么生效、怎么确认没动核心代码。

配套：[OPERATIONS.md](OPERATIONS.md)（拦截清单、规则配置、排查、升级迁移）· [MANUAL_TESTS.md](MANUAL_TESTS.md)（65 条手工用例）· [README.md](README.md)（规则设计）

---

## 1. 一张图先看懂

```
你手上的源码目录/          iCode 运行时真正读的地方
┌──────────────────┐
│  guard_hooks/    │   ← 规则包的"源"，放哪都行，运行时不读
│  ├ rules.json    │
│  ├ _guard_core.py│
│  ├ _prompt_guard.py
│  ├ _tool_guard.py│
│  └ hooks.yaml    │
└────────┬─────────┘
         │  uv run python guard_hooks/_install_merge.py
         │  （复制文件 + 追加两条配置）
         ▼
┌────────────────────────────────────────────┐
│ <配置目录>/hooks/                ← 生效点  │
│  ├ hooks.yaml           ← iCode 读它（也认 hooks.yml / hooks.json）│
│  └ guard/                             │
│     ├ rules.json                      │
│     ├ _guard_core.py                  │
│     ├ _prompt_guard.py                │
│     └ _tool_guard.py                  │
└────────────────────────────────────────────┘
```

**最关键的一点：规则包不在源码目录里生效。** 源码目录下的 `guard_hooks/` 只是你保管的一份副本，iCode 从来不读它。真正生效的是**用户配置目录**下的那份。

---

## 2. 放哪里

### 2.1 配置目录在哪

| 系统 | 配置目录 | hook 目录 |
| --- | --- | --- |
| **Windows** | `%APPDATA%\chrys\`（即 `C:\Users\<你>\AppData\Roaming\chrys\`） | `<配置目录>\hooks\` |
| macOS / Linux | `~/.chrys/` | `~/.chrys/hooks/` |

两个常见错误：

- ❌ Windows 上写 `~/.chrys/hooks/` —— iCode 在 Windows 读的是 `%APPDATA%\chrys\hooks\`，放错地方等于没放
- ❌ 放进源码目录的 `.chrys/hooks/` —— 那是**项目级**位置，需要额外开开关（见 2.3），且只在那个项目下生效

### 2.2 装完是什么样

```
<配置目录>/hooks/
├── hooks.yaml                 ← iCode 唯一读的配置文件
├── hooks.yaml.pre-guard       ← 安装脚本自动备份（回退用）
└── guard/                ← 规则包放这个子目录
    ├── _prompt_guard.py      提示词层入口
    ├── _tool_guard.py        工具调用前入口
    ├── _guard_core.py        规则引擎（纯标准库）
    └── rules.json            词典 + 规则 + 开关
```

为什么放 `guard/` 子目录而不是直接摊在 `hooks/` 下：那个目录通常已经有别的 hook（遥测、审计），混在一起分不清谁是谁，删的时候也容易误伤。

### 2.3 全局 vs 项目级

| | 全局（推荐） | 项目级 |
| --- | --- | --- |
| 位置 | `<配置目录>/hooks/guard/` | `<项目根>/.chrys/hooks/guard/` |
| 开关 | 无，装完即生效 | 要在设置里打开 `project.hooks_enabled` |
| 生效范围 | 所有会话 | 只在该项目目录下启动的会话 |
| 谁能开| 任何人 | **只有用户自己**。该键的 `ProjectMerge` 是 `DENY`，项目自己的 `.chrys/settings.yaml` 无法打开它 |

项目级的开关在 TUI 设置里：**Settings → Security → Project trust → Load project hooks**。

如果你只是想"所有地方都拦"，用全局，别折腾项目级。

### 2.4 4 个文件各自干什么

| 文件 | 作用 | 依赖 |
| --- | --- | --- |
| `_prompt_guard.py` | `user_prompt_submit` 事件的入口，读 payload、跑规则、写决策 | 只 import `_guard_core` |
| `_tool_guard.py` | `before_tool_call` 事件的入口，同上 | 只 import `_guard_core` |
| `_guard_core.py` | 规则引擎：加载 `rules.json`、匹配检测器、决定拦/放| **只用标准库** |
| `rules.json` | 唯一的配置面：词典、规则、开关、提示文案 | — |

`_guard_core.py` 只用标准库（`json` / `re` / `pathlib` / `urllib.parse` / `ipaddress` …），所以 hook 脚本**不依赖项目 venv 里的任何第三方包**。详见 4.5。

---

## 3. hook 怎么配、配什么

iCode 的 hook 能力是**自带的**，不是这个规则包发明的。规则包只是"配了哪些规则"。

### 3.1 唯一需要加的两条配置

追加到 `<配置目录>/hooks/hooks.yaml` 的 `hooks:` 列表里：

```yaml
  - id: security-prompt-guard
    event: user_prompt_submit
    description: 提示词层安全拦截
    run:
      type: script
      path: guard/_prompt_guard.py
    execution:
      mode: blocking
      timeout_seconds: 5
      on_error: block

  - id: security-tool-guard
    event: before_tool_call
    description: 工具调用前安全拦截
    run:
      type: script
      path: guard/_tool_guard.py
    execution:
      mode: blocking
      timeout_seconds: 5
      on_error: block
```

> 路径是 `guard/xxx.py`，不是 `xxx.py` —— 相对路径以 **`hooks.yaml` 所在目录**为基准。

### 3.2 每个字段为什么这么填

| 字段 | 值 | 含义 / 为什么 |
| --- | --- | --- |
| `id` | `security-prompt-guard` / `security-tool-guard` | 日志和留痕里的标识，唯一即可。安装脚本拿 `security-prompt-guard` 判断是否已装 |
| `event` | `user_prompt_submit` / `before_tool_call` | 挂在哪个生命周期点 |
| `run.type` | `script` | 按扩展名推断解释器，`.py` → **跑 iCode 的那个解释器** |
| `run.path` | `guard/*.py` | 相对 `hooks.yaml` 目录；也可写绝对路径 |
| `execution.mode` | `blocking` | **同步等它返回**。这是拦截的前提，`async` / `fire_and_forget` 拦不住 |
| `timeout_seconds` | `5` | 规则匹配是纯字符串/正则运算，毫秒级足够 |
| `on_error` | `block` | 脚本崩了/超时了 → **本轮直接拦下**，而不是静默放行 |
| `match` | 不写 | 不写 = 每次都跑。我们要拦全部，靠 `rules.json` 里的 `enabled` 开关来关单条规则 |

### 3.3 为什么只有这两个事件能拦

iCode 源码里有一个白名单：

```python
# src/chrys/service/hooks/events.py
GATED_EVENTS = frozenset({HookEvent.BEFORE_TOOL_CALL, HookEvent.USER_PROMPT_SUBMIT})
```

**只有这两个事件是"闸门"**，blocking hook 的决策能真正中止流程。其余 15 个事件（`after_tool_call`、`session_start`、`pre_compact`…）只是观察者，`action: block` 会被打日志然后忽略，`on_error: block` 也会降级成 `warn`。

这也是**为什么不需要改核心代码** —— 该拦的两个点原生就是闸门。

### 3.4 `on_error: block` 值不值

值。它是"失败兜底"：

| 情况 | `on_error: block` | `on_error: warn`（默认） |
| --- | --- | --- |
| `rules.json` 写坏了 | 拦下 +提示 | 静默放行，全部规则失效 |
| 脚本 import 失败 | 拦下 | 静默放行 |
| 机器卡住超过 5 秒 | 拦下 | 静默放行 |

配置坏了还静默放行，是最坏的结果 —— 你以为在拦，其实没拦。

> 注意 `on_error: block` 只在 gated 事件 + `blocking` 模式下真正生效，别的组合 iCode 会在加载时就拒绝。

### 3.5 脚本怎么把"拦"告诉 iCode

iCode 不读脚本的 stdout/stderr，**走临时文件**：

```
iCode                                    脚本
  │  写 payload JSON
  │  ── 环境变量 CHRYS_HOOK_PAYLOAD_FILE ──▶  读事件数据
  │                                        跑规则
  │  ◀── 环境变量 CHRYS_HOOK_RESULT ──────  写决策 JSON
  │  读决策，按 action 处理
```

决策文件里写什么：

| 字段 | 作用 |
| --- | --- |
| `{"action": "block", "reason": "..."}` | **拦下**，reason 是给用户看的原因 |
| `{"action": "allow"}` 或不写文件 | 放行 |
| `{"system_reminder": "..."}` | 不拦，但把这段话塞进 `<system-reminder>` 给模型 |
| `{"args_override": {...}}` | 不拦，但改写工具入参 |

本规则包只用到前两种，外加提示词层的 `system_reminder`（`confirm` 类规则在 `notify` 模式下用）。

**文件必须为空或不存在才表示"没意见"**；写坏了当放行处理。

### 3.6 一个硬约束：hook 不能交互

Hook 子进程的 **stdin 是 `DEVNULL`** —— 这是 iCode 的设计，不是配置问题。

意味着脚本里不能弹确认框、不能等用户输入、不能读 stdin。所以规则只有"拦"和"放"两种结果，没有"问用户一次再决定"。

规则表里的 `confirm` 档位只能落成两种：全局开关 `settings.confirm_disposition` 决定是 `block`（默认）还是 `notify`。

---

## 4. 怎么让它生效

### 4.1 前置：拉源码 + 装依赖

```powershell
git clone <iCode 仓库>
cd <仓库目录>
uv sync
```

`uv sync` 会按 `.python-version` 自动装好 Python 3.14，**不要用全局的 python 或 pip**。

### 4.2 把规则包文件弄到手上

`guard_hooks/` **不在 git 版本控制里**（`git status` 显示 `?? guard_hooks/`），所以新 clone 的仓库里**没有**这个目录。三种拿法：

| 方式 | 做法 |
| --- | --- |
| 从旧机器拷 | 把整个 `guard_hooks/` 目录复制过来（推荐，连文档一起） |
| 提交进仓库 | `git add guard_hooks/ && git commit`，这样以后 clone 就有|
| 只要 4 个文件 | `_prompt_guard.py`、`_tool_guard.py`、`_guard_core.py`、`rules.json` |

### 4.3 安装（推荐一条命令）

```powershell
uv run python guard_hooks\_install_merge.py
```

这个脚本做三件事：

1. 复制 4 个文件到 `<配置目录>/hooks/guard/`
2. 把两条 hook 配置**追加**到 `hooks.yaml` 的 `hooks:` 列表末尾
3. 写前自动备份为 `hooks.yaml.pre-guard`，并保留原文件的换行风格和 BOM

**为什么是"合并"不是"覆盖"**：`<配置目录>/hooks/hooks.yaml` 通常已经有你自己的 hook（遥测、审计之类），直接覆盖会把它们全弄丢。

幂等：已存在 `security-prompt-guard` 时不动文件，可以反复跑。

配置文件不存在时会自动新建一个最小骨架；写成 `hooks: []` 这种流式写法也会先归一（否则追加的条目会变成非法 YAML）。

只检查不改动：

```powershell
uv run python guard_hooks\_install_merge.py --check
```

回退：把 `hooks.yaml.pre-guard` 拷回 `hooks.yaml`，再删掉 `guard/` 目录。

### 4.4 纯手动（不想跑脚本）

```powershell
# 1. 建目录
$guard = "$env:APPDATA\chrys\hooks\guard"
New-Item -ItemType Directory -Force -Path $guard

# 2. 拷 4 个文件
Copy-Item guard_hooks\_prompt_guard.py, guard_hooks\_tool_guard.py, `
          guard_hooks\_guard_core.py, guard_hooks\rules.json -Destination $guard

# 3. 编辑 $env:APPDATA\chrys\hooks\hooks.yaml，把 3.1 那两段追加到 hooks: 列表
```

macOS / Linux 把 `$env:APPDATA` 换成 `~/.chrys/hooks`。

若 `hooks.yaml` **不存在**，新建一个再追加：

```yaml
version: 1

hooks:
  # ↓ 把上面两段贴在这里
```

> ⚠️ 写 `hooks:`（留空）而不是 `hooks: []`。追加的是块序列，接在 `[]` 后面会得到非法 YAML。

### 4.5 校验

```powershell
uv run icode hook validate
```

期望：`PASS 1 file · N hooks`。

看到这条 warning 属于正常，不用管：

```
warning: hook 'security-tool-guard': a before_tool_call hook with no match
filters; it will run for every tool call [broad_before_tool_call]
```

它的意思正是我们要的 —— 每次工具调用都检查，规则开关在 `rules.json` 里管。

再看一眼加载到哪些：

```powershell
uv run icode hook list
```

期望能看到 `security-prompt-guard` 和 `security-tool-guard`。

### 4.6 启动

```powershell
uv run icode
```

在对话框里说一句会命中规则的话验证：

```
用 IDA Pro 反编译一下这个 exe
```

期望输出：

```
✗ 错误
hook 'security-tool-guard' blocked: 操作不合规，请修改后重试。
```

（`hook '…' blocked: ` 这段前缀是 iCode 核心自己拼的，在 `src/chrys/service/hooks/manager.py`。规则包提供的 `reason` 就是后面那句中文。）

### 4.7 什么时候要重启

| 改了什么 | 要重启吗 |
| --- | --- |
| `rules.json`（词典、规则、开关、提示文案） | **不用**，每次调用都重新读（`load_config()` 无缓存） |
| `_guard_core.py` 等脚本 | **不用**，子进程每次重新起 |
| `hooks.yaml` | **要**，配置在会话启动时加载 |
| 换项目目录 | 要（项目级 hook 按 primary cwd 绑定） |

### 4.8 改配置前的自检

```powershell
uv run python guard_hooks\selftest.py
```

41 个断言，改完 `rules.json` 必跑。详见 OPERATIONS.md 第 4 节。

---

## 5. 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 完全不拦 | hook 没加载 | `uv run icode hook list`，看两个条目在不在 |
| 完全不拦 | 放错目录 | 确认是 `%APPDATA%\chrys\hooks\`，不是 `~/.chrys/hooks/` |
| 提示词拦了，工具不拦 | 只装了一个 hook | `hook list` 里应该**两个**都有 |
| 工具拦了，提示词不拦 | 同上 | 同上 |
| 配置改了没反应 | 改的是 `hooks.yaml` | 需重启；改 `rules.json` 则不用 |
| 日志里有 `[guard]` 开头 | 脚本自己报的错 | 脚本把详情写 stderr 了，看日志 |
| 什么都没拦但也没报错 | `rules.json` 里 `settings.enabled: false` | 检查这个开关 |
| 某条规则误伤 | 单条规则太宽 | 在 `rules.json` 里给它加 `"enabled": false` |

看命中了哪些规则（留痕文件，JSON Lines）：

```powershell
Get-Content $env:APPDATA\chrys\hooks\guard_audit.jsonl -Tail 5 -Encoding UTF8
```

排查顺序建议：**先 `hook list` 确认加载 → 再看留痕确认规则命中 → 最后才查脚本**。

---

## 6. 怎么确认确实没改核心代码

规则包对 iCode 的全部改动量：**0 行**。验证：

```powershell
git status --porcelain
git diff --stat
```

只应该看到 `guard_hooks/`（未跟踪的新目录），`src/` 下不应有任何改动。

运行时依赖的 iCode 接口只有三个，都是公开的：

| 用到的 | 位置 |
| --- | --- |
| `user_prompt_submit` / `before_tool_call` 事件 + payload 结构 | `docs/zh-Hans/reference/hooks.md` |
| 决策文件协议（两个环境变量 + action 字段） | 同上 |
| 配置目录解析| `src/chrys/foundation/platform/__init__.py::conventional_config_dir` |

iCode 升级后想确认没被破坏，重跑这三步即可：

```powershell
uv run icode hook validate          # 配置还认不认
uv run python guard_hooks\selftest.py # 规则引擎还认不认
uv run icode hook list                # 条目加载了没
```

更完整的升级复查清单见 OPERATIONS.md 第 6 节。

---

## 附：完整的 hook 事件清单

只有加粗的两个是闸门（能拦）：

**`user_prompt_submit`** · **`before_tool_call`** · `session_start` · `session_restored` · `session_end` · `before_turn` · `after_turn` · `approval_requested` · `approval_resolved` · `after_tool_call` · `tool_error` · `sub_agent_start` · `sub_agent_end` · `pre_compact` · `workflow_run_start` · `workflow_run_end` · `user_interrupt`

其余事件上挂 blocking hook 只会得到一条 warning 日志，决策被忽略。想在那些点上做事，把 `mode` 改成 `async` 或 `fire_and_forget`，但那就不是拦截了。