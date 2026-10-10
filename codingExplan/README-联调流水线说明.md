# Agent Studio 桌面端联调流水线使用说明

> 配套脚本：`D:\project\iCode\util\build-linux-arm64-dev.yml`
> 来源：官方 `.github/workflows/build-linux-arm64.yml` 的联调改造版。
> 唯一实质差异：iCode 二进制不再从 `openJiuwen-ai/iCode` 的 Releases 下载，改为从你自己的 CD（`ypzyfl/iCode`）的 **Artifacts** 下载，其余打包步骤与官方脚本逐字一致。

---

## 1. 安装（只需一次，二选一）

### 方式一：本地 git 推送

```bash
cd <你的 agent_studio_new 仓库>
cp /d/project/iCode/util/build-linux-arm64-dev.yml .github/workflows/
git add .github/workflows/build-linux-arm64-dev.yml
git commit -m "ci: add desktop dev pipeline driven by iCode CD artifacts"
git push   # 必须推到仓库默认分支，否则 Actions 页面看不到触发入口
```

### 方式二：网页端 Actions 直接新建（不用本地 git）

1. 打开仓库 → **Actions** 标签页 → 左侧 **New workflow** → 选 **set up a workflow yourself**
2. 编辑器里清空默认模板，把 `D:\project\iCode\util\build-linux-arm64-dev.yml` 的全部内容粘贴进去
3. 确认文件名为 `build-linux-arm64-dev.yml`（即路径 `.github/workflows/build-linux-arm64-dev.yml`）
4. 点 **Start commit** → **Commit new file**，提交分支选仓库**默认分支**
5. 回到 Actions → 左侧出现 **Build Linux arm64 (dev)** → Run workflow

> 注意：网页端点 Commit 时文件同样会提交进仓库（GitHub 要求 workflow 必须存在于仓库中才能运行），只是省了本地 git 操作。之后改脚本可直接在网页上点文件旁的铅笔图标编辑，同样会生成提交；注意网页版和本地 `D:\project\iCode\util` 的母本保持一致，避免两边越改越乱。

两种方式的前提：仓库 Secrets 里的 `GH_TOKEN` 需要对 `ypzyfl/iCode` 有 **Actions: Read** 权限（fine-grained PAT 单独勾选该仓库并授权 Actions 只读）。

## 2. 日常触发

Actions → **Build Linux arm64 (dev)** → Run workflow，或命令行：

```bash
gh workflow run build-linux-arm64-dev.yml -R nangualin/agent_studio_new
```

所有输入框都有默认值，**直接点 Run 就会自动取 iCode 最近一次成功 CD 的 linux-aarch64 包**。CD 出了新包，重跑一次即得新版本，不需要改任何脚本。

## 3. 取包的三种方式（重点）

| 方式 | 需要填的输入 | 适用场景 |
|---|---|---|
| A. 全自动 | 全部留默认 | 日常联调，永远要最新的包 |
| **B. 固定取某一次的包** | `icode_run_id` + `icode_artifact_id` | 复现问题、回归验证、锁版本 |
| C. 固定包 + 哈希校验 | 方式 B 再加 `icode_sha256` | 对包的正确性有硬性要求时 |

### 方式 B：如何取固定的包

你 CD 产物页面的 URL 长这样：

```
https://github.com/ypzyfl/iCode/actions/runs/37897444772/artifacts/11601741662
                                          └─────── run_id ──────┘└──── artifact_id ────┘
```

把两个数字原样填进触发表单：

- `icode_run_id` = `37897444772`
- `icode_artifact_id` = `11601741662`

`artifact_id` 是最高优先级：填了它就只下载这一个包，平台过滤、名字匹配全部跳过——**点名要什么就是什么**。

命令行等价写法：

```bash
gh workflow run build-linux-arm64-dev.yml \
  -f icode_run_id=37897444772 \
  -f icode_artifact_id=11601741662
```

### 写死进脚本（改 yml 的方式）

不想每次触发都填表的话，可以把固定值写进脚本：打开 `build-linux-arm64-dev.yml`，搜索注释 **【固定取包】**，修改两处 `default:`：

- 第 **47** 行 `default: ''` → `default: '37897444772'`（run_id，URL 中 `runs/` 后面的数字）
- 第 **54** 行 `default: ''` → `default: '11601741662'`（artifact_id，URL 中 `artifacts/` 后面的数字）

两处都改，改完 commit + push 到仓库默认分支，之后每次触发都默认取这个包。注意：行号会随文件改动顺移，以 yml 内 `# ← 固定取包改这里` 标记为准；改回 `default: ''` 即恢复自动取最新包。

### 方式 C：再加一道哈希锁

先在本地算出包的 sha256（对下载到的 zip 内的原始文件算，不是对 zip 本身）：

```bash
unzip icode-linux-aarch64-v0.29.0-dev-c584354-offline.zip -d tmp
sha256sum tmp/icode
```

把哈希填进 `icode_sha256`，脚本校验不一致会直接失败。

## 4. 全平台包会不会取错平台？——机制说明

**问题确实存在**：一次 CD 出全平台包时，同一个 run 里会有多个 artifact（linux-x64 / linux-aarch64 / windows / darwin 各一个），"随便挑一个"就可能挑错。脚本对此的处理：

1. **自动挑选时强制按平台过滤**。`icode_platform` 输入（默认 `linux-aarch64`）必须是 artifact 名字的子串，自动模式只在名字含平台词的 artifact 里选，再优先取含 `offline` 的。
2. **平台词拼错/命名规则变了 → 直接报错**，并列出该 run 里所有 artifact 名字供你选，绝不静默拿错平台的包。
3. **两道事后自检**：
   - 日志里 `Downloading artifact '<名字>'` 一行，一眼可见实际选中的包；
   - 打包前会执行 `chrys --version` 冒烟测试——arm64 runner 上跑了 x64 的二进制会立刻报 "cannot execute binary file" 失败，错误包进不了成品。

**注意两点**：

- 你的 CD 命名用的是 `linux-aarch64`（不是 `linux-arm64`），`icode_platform` 必须填 artifact 名里真实出现的子串。
- 如果填了 `icode_artifact_id` 或精确的 `icode_artifact_name`，平台过滤不生效（也不需要）——那是你显式指定的，选错平台是输入错误，冒烟测试会兜底。

## 5. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| Actions 页面找不到 "Build Linux arm64 (dev)" | workflow 文件没推到仓库**默认分支** |
| 下载步骤 403 / 404 | `GH_TOKEN` 对 `ypzyfl/iCode` 缺 Actions: Read 权限 |
| 报 "No artifact matching platform token ..." | `icode_platform` 填的子串在任何 artifact 名里都不存在，按日志列出的名字修正 |
| 报 "cannot execute binary file" | 取到了别的平台的包（通常是你手填 id/名字填错），重新确认 URL 里的两个数字 |
| 找不到某次的包了 | Artifact 默认保留 **90 天**后自动清理，过期需重新跑 CD |

## 6. 什么时候才需要改脚本本身

只有两种情况：

1. CD 产物**形态**变化：比如以后改成上传 tar.gz（脚本已兼容，无需改）、或二进制改名（改第 4 步的 `$stage/icode` 判断）。
2. 要换默认值（CD 仓库、平台词等）：改 inputs 里的 `default:`。

改完 commit + push 到默认分支即可，与安装步骤相同。
