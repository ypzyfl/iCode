# 开始使用 AIxCoding-CLI

本教程介绍如何安装 AIxCoding-CLI，并在项目中使用智能体完成一次开发任务。

## 1. 安装 AIxCoding-CLI

AIxCoding-CLI 为 macOS、Linux 和 Windows 提供预构建的离线安装包。安装包已包含 Python 和运行依赖，无需另行安装 Python。

以下命令中的 `<version>` 和 `<architecture>` 是占位符，请替换为下载文件名中的实际值。

### macOS

根据处理器选择 `aixcoding-cli-macos-aarch64-v<version>-offline.tar.gz`（Apple 芯片）或 `aixcoding-cli-macos-x86_64-v<version>-offline.tar.gz`（Intel），然后在下载目录运行：

```bash
tar xzf aixcoding-cli-macos-<architecture>-v<version>-offline.tar.gz
chmod +x ./aixcoding-cli
./aixcoding-cli install
```

### Linux

根据处理器选择 `aixcoding-cli-linux-x86_64-v<version>-offline.tar.gz` 或 `aixcoding-cli-linux-aarch64-v<version>-offline.tar.gz`，然后在下载目录运行：

```bash
tar xzf aixcoding-cli-linux-<architecture>-v<version>-offline.tar.gz
chmod +x ./aixcoding-cli
./aixcoding-cli install
```

Linux x86-64 安装包要求 glibc 2.17 或更高版本，ARM64 安装包要求 glibc 2.18 或更高版本。Alpine Linux 等只提供 musl 的发行版不在预构建包的支持范围内。

HTTP 下载根地址为 `http://22.189.54.139/aixcoding/file/aixcoding`，对应服务器目录 `/homepage/aixcoding/`。根目录放 `install.sh` 和 `install.ps1`；`channels/cli/prod.txt`、`channels/cli/test.txt` 各存一行完整版本号，安装包放在 `releases/cli/<完整版本号>/`。无需 FTP 凭据。Linux 与 macOS 用户可执行同一条命令；脚本会自动识别平台，并创建 `aixcoding` 启动命令：

```bash
curl -fsSL -o install.sh 'http://22.189.54.139/aixcoding/file/aixcoding/install.sh' && bash install.sh
```

默认安装生产包；安装测试包时运行 `bash install.sh --channel test`。CD 流水线分别上传各平台二进制 Artifact，不打包安装脚本。手动把两个安装脚本放在 HTTP 根目录、对应平台的 Artifact ZIP 放在 `releases/cli/<完整版本号>/`，再将完整版本号写入对应频道文件；构建用 wheel 无需上传到 HTTP 镜像。只构建 Linux 时产物中只有 Linux 二进制包。五种平台包名见 README 安装表。

### Windows

在 PowerShell 中执行以下命令，安装生产频道当前版本的 Windows x86-64 包：

```powershell
irm 'http://22.189.54.139/aixcoding/file/aixcoding/install.ps1' | iex
```

安装测试包时，先执行 `$env:ICODE_CHANNEL='test'`（该环境变量沿用历史名），再运行上述命令。安装器会尝试将 AIxCoding-CLI 加入当前用户的 `PATH`。安装完成后，请打开一个新终端。

### 验证安装

```shell
aixcoding-cli --version
```

命令应输出 AIxCoding-CLI 的版本号。在 macOS 或 Linux 上，如果系统找不到 `aixcoding-cli`，请按安装器的提示将 `~/.local/bin` 加入 `PATH`；如果安装器提示 `~/.local/bin/aixcoding-cli` 已存在，该命令会启动其他程序，请改用 `chrys` 命令。在 Windows 上请打开新的终端；如果安装器提示更新用户 PATH 失败，请手动将 `%LOCALAPPDATA%\chrys\bin` 加入用户 `PATH`。

> **启动命令说明**：`aixcoding-cli` 是本工具的标准启动命令；`aixcoding`（由安装脚本自动创建）和 `chrys`（历史命令名）与它完全等价，输入任意一个都会启动同一程序。本手册统一使用 `aixcoding-cli`。

### 卸载 AIxCoding-CLI

运行：

```shell
aixcoding-cli uninstall
```

如果安装的是离线安装包，该命令会列出要删除的内容：`aixcoding-cli` 和 `chrys` 命令，以及安装包解压出的文件。确认后即删除。在 Windows 上，它还会把 AIxCoding-CLI 从用户 `PATH` 中移除，最后一部分文件会在命令退出后稍等片刻删除。下载的安装包本身仍保留在原处。

AIxCoding-CLI 的数据保存在 `~/.chrys`（Windows 上是 `%APPDATA%\chrys`），包括设置、API 密钥、模型配置、智能体、技能和会话等。卸载时会保留这个文件夹。如需连同其中的全部内容一并删除，请运行 `aixcoding-cli uninstall --purge`；如果把会话保存在了其他文件夹，那里的 `sessions` 文件夹也会删除。加上 `--yes` 可跳过确认。

## 2. 在项目中启动 AIxCoding-CLI

建议在使用 Git 管理或能够安全恢复的项目中开始本教程。在让智能体修改文件前，请先保存尚未写入磁盘的内容，并使用 Git commit 记录已有变更，以便区分智能体所做的修改，并在需要时恢复到修改前的状态。

在终端中进入要处理的项目目录并启动 AIxCoding-CLI：

```shell
cd <project-directory>
aixcoding-cli
```

将 `<project-directory>` 替换为项目目录的实际路径。启动后如需切换目录，请参阅[工作目录](../guides/daily-use/workspaces.md#工作目录)。

AIxCoding-CLI 会先显示 `Starting AIxCoding-CLI...`，并在准备期间显示加载界面。进入主界面后，主界面会继续显示加载状态，直到智能体准备就绪。

运行期间，输入栏上方的状态栏会显示已运行时长、工具调用次数，以及文字到达时的速度。长时间运行会显示小时和天，例如英文界面的 `1d 4h 20m 50s`，中文界面的 `1天 4小时 20分 50秒`。工具卡片、后台任务、CLI 进度和 F12 耗时面板也支持显示天数；紧凑显示区域只保留较大的时间单位。

智能体答复后，答复标题会显示这一轮的总耗时，例如 `Code Agent - 2:04 AM (6m 5s)`：从你发送消息，或点击 **继续** 或 **重试** 起，到答复完成为止，智能体等待你审批或回答的时间也计算在内。智能体工作期间你发送的消息不会让计时重新开始。重新打开会话时显示的耗时与此相同。

## 3. 使用智能体

### 选择智能体

AIxCoding-CLI 默认提供两个主智能体：Q&A Agent（问答智能体）和 Code Agent（代码智能体）。两者都可以阅读项目、分析代码和讨论方案，但定位和可用工具不同：Q&A Agent 主要提供只读能力，适合了解项目、解释代码和分析问题；Code Agent 则可以修改文件、运行命令，适合编写、审查、重构、调试和验证代码。

当前没有正在运行的智能体任务时，可以切换智能体。在输入栏中输入 `#`，输入栏上方会显示智能体列表，可以通过鼠标点击，或使用上下方向键并按回车进行选择。也可以点击输入栏上方状态栏中的智能体名称，在智能体选择窗口中进行切换。

### 使用 Q&A Agent

Q&A Agent 适合在**不修改项目的情况下**了解项目、分析代码、追踪实现和讨论方案。它会基于项目内容给出回答，并尽量提供可追溯的依据。

切换到 **Q&A Agent** 后，在输入栏中输入 `/new` 并回车，开始新会话。

以下示例假设当前项目是一个待办事项应用，仅用于展示使用方式。实际使用时，请根据实际项目调整问题和任务。

```text
请分析任务列表的实现，并为增加“清除已完成任务”功能提出方案。说明需要修改哪些文件以及实现步骤。
```

Q&A Agent 可能会搜索文件、读取文件内容或运行只读命令。工具调用会以卡片形式显示，连续的调用归在同一个标题下。调用进行中，标题显示智能体正在做什么；全部完成后，标题按类别说明调用做了什么，例如 `▸ 读取 3 个文件 · 搜索 2 个模式 · 运行 1 条命令`，如有失败或中断的调用，末尾会标出次数；窗口放不下整行时，先截掉前面的类别，这部分保留。如果只调用了一次且成功，标题改为说明这次调用具体做了什么，例如 `▸ 读取 src/app.py` 或 `▸ 运行 zsh 命令：运行测试`；当前工作文件夹内的路径显示为相对路径。智能体用 `sleep` 等待时，标题显示等待原因和剩余时间的倒计时，例如 `休眠中：等待 CI · 还剩 29 秒`；如不想再等，展开卡片点击**跳过**。完成后标题会说明休眠了多久及原因，例如 `▸ 休眠了 23 秒：等待 CI`。点击标题可显示或隐藏卡片。完成分析后会给出实现方案。

### 使用 Code Agent

Code Agent 适用于需要**修改文件、运行命令和验证结果**的任务。它会先阅读相关代码，再按任务要求实现、调试或重构代码。

Q&A Agent 给出实现方案后，可以在同一会话中切换到 **Code Agent**。切换智能体不会清除当前会话的上下文，Code Agent 可以基于已有方案继续完成开发任务：

```text
请根据刚才讨论的方案实现“清除已完成任务”功能。修改代码并运行必要的测试。
```

如果出现审批对话框，请检查即将执行的工具调用，尤其是命令内容、目标文件和影响范围，确认符合预期后再批准。有关不同审批模式的行为，请参阅[配置审批模式](../guides/configuration/approval.md#配置审批模式)。

任务完成后，检查智能体的最终回复，并通过 `/diff` 浏览当前会话记录的文件修改。随后使用 Git 等版本控制工具检查工作目录的完整变更，并确认功能正确、必要的测试已经通过且不包含无关改动。确认无误后，可以提交这些变更。

### 询问 AIxCoding-CLI 本身的用法

可以直接在输入栏向智能体询问 AIxCoding-CLI 的问题，例如：

- “AIxCoding-CLI 有哪些功能？”
- “如何在 AIxCoding-CLI 中配置 MCP 服务器？”
- “AIxCoding-CLI 的上下文压缩是如何工作的？”

智能体会查阅当前安装版本附带的用户指南，并告诉你参考了哪些页面。如果指南里介绍的功能在当前智能体中没有开启，回答会说明。如果智能体不能读取文件，它会告诉你没有查到指南。

也可以输入 `/help` 或按 **F8** 自己查看用户指南。

### 输入多行消息

按 **Enter** 发送消息，按 **Shift+Enter**、**Ctrl+Enter** 或 **Ctrl+J** 换行。按 **Ctrl+O** 可在更大的编辑器中输入。

有些终端（包括 macOS 自带的“终端”和部分 tmux 配置）无法区分 Shift+Enter 或 Ctrl+Enter 与 Enter，这时按相应的组合键会直接发送消息，请改用 Ctrl+J。

在其他多行输入框中，按 **Enter** 或 **Shift+Enter** 换行。在 Ctrl+O 编辑器中，按 **Ctrl+O** 或 **Ctrl+Enter** 提交。

### 附带图片、引用对话和粘贴长文本

在消息框里粘贴截图或图片，或拖入图片文件，会显示为 **[图片 #1]**。要引用对话中的一段内容，用鼠标选中它，再点击出现的 **引用** 按钮，光标处会加入 **[引用 #1]**。粘贴的长文本（超过 800 个字符，或 4 行及以上）会显示为 **[粘贴文本 #1 +3 行]**。标签的文字跟随界面语言。你可以在它们前后照常输入；每条消息里每种标签都从 1 开始编号。

点击标签可以查看它代表的内容：图片显示文件路径和图片本身，引用和粘贴的文本显示完整文字。标签作为一个整体编辑：光标会跳过它，按 Backspace 或 Delete 会把它整个删掉。全屏提示词编辑器（Ctrl+O）里也是一样，标签照常可用。

发送时，每个标签都换成它代表的内容：图片随消息一起发给模型，粘贴的文本放回标签所在的位置，单行的引用加上引号放在标签的位置；多行的引用单独成段，作为引用块发出，其中的标题、列表或代码都留在引用块里。引用是别人说过的话，其中的 `@文件` 或 `` !`命令` `` 不会生效：发送时会在前面加上反斜杠，作为普通文字发出。粘贴的文本算作你自己的话，和手打的文字一样生效。你发出的消息，以及用上箭头或从提示词历史取回的内容，显示的都是这段完整的文字，不再显示标签。发出消息后，在空的消息框里按 **Ctrl+Z**，可以把整条消息连同标签一起找回来。

### 阅读和复制回复

所有智能体的回复都支持 Markdown、数学公式和 Mermaid 图表。你自己发送的消息中的公式不作数学渲染。

列表和引用可以包含标题、表格、代码和公式。

回复中，`$...$` 或 `\(...\)` 包围的公式以单行显示；`math` 代码块、`$$...$$` 或 `\[...\]` 中的块公式可显示分式、矩阵和对齐公式。普通文字、价格和 shell 变量保留原有 Markdown 格式。不支持或过宽的公式会完整显示为可换行的源码。

例如，`$x^{n+1}$` 显示为 xⁿ⁺¹，`$90^\circ$` 显示为 90°。

Mermaid 代码块会显示为图表，点击**打开完整图表**可查看、滚动完整内容。部分图表会简化显示并提示，不支持的图表保留源码。

模型服务返回可读的思考文本时，回复上方的折叠行先显示 **思考中**。随着文本到达，这一行会显示这段思考的估算 token 数，再加上近期速度，例如 `思考中（3.2k token · 70 tok/s）`。括号及其中的数字以淡色显示，每秒更新一次。思考完成后，折叠行显示 **思考：** 和原文的开头。随时点击这一行都可展开查看完整思考或再次折叠，模型仍在写时也可以（`/fold` 可一次折叠或展开全部已完成的思考、工具组和工具调用之间的文字）。模型转入工具调用或回复后，思考会像工具组一样自动折叠；模型在工具调用前写的文字也会折叠为一行，显示其开头。思考没有**复制**按钮，复制回复时也不包含思考。如需在模型写出思考时完整展开，请在设置对话框中开启**默认展开思考**（**通用** → **显示偏好**）。

鼠标选择复制显示结果，不会因屏幕折行额外插入换行。消息标题旁的**复制**保留原始 Markdown 和 LaTeX。重新打开旧会话时，也会使用当前的渲染效果。

## 4. 结束本次使用

若要结束本次使用，输入 `/exit` 或按 `Ctrl+Q` 退出 AIxCoding-CLI。

## 5. 下一步

至此，已经完成 AIxCoding-CLI 的安装，并了解了 Q&A Agent 和 Code Agent 的基本使用方式，以及如何在同一会话中配合完成开发任务。

接下来，可以继续探索：

- [配置智能体](../guides/configuration/agents.md#配置智能体)，创建或修改智能体，并设置其指令、模型、工具和子智能体
- [工作目录](../guides/daily-use/workspaces.md#工作目录)
- [配置审批模式](../guides/configuration/approval.md#配置审批模式)
- 通过技能和 MCP 扩展 AIxCoding-CLI

---
