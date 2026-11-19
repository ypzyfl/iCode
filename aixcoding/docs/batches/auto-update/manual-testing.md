# 自动更新：手动测试与排障手册

> 2026-11-19 整理自实际联调记录。设计文档见同目录 `design.md`；本文面向**动手测试**，
> 覆盖触发方法、接口清单、状态文件、手动复现命令与已知问题。

## 1. 版本号的两个来源（先分清，测降版本才不会困惑）

| 来源 | 用途 | 位置 |
|---|---|---|
| `PYAPP_PROJECT_VERSION`（编译期常量） | `chrys --version` / `aixcoding-cli --version` 的显示 | 打包时写入 PyApp 二进制（`scripts/build.sh:152`），运行时不可变 |
| `importlib.metadata.version("iCode-TUI")` | **升级检查的 `currentVersion`** | 安装目录内 dist-info 的 `METADATA` `Version:` 行 |

真实安装布局（PyApp，`PYAPP_PROJECT_NAME=chrys`）：

| 平台 | 项目目录 | dist-info 位置（offline/pip flavor，FULL_ISOLATION） |
|---|---|---|
| Linux | `~/.local/share/chrys` | `<distribution_id>/<version>/python/lib/python3.14/site-packages/icode_tui-<ver>.dist-info/METADATA` |
| macOS | `~/Library/Application Support/chrys` | 同上 |
| Windows | `%LOCALAPPDATA%\chrys` | 同上 |

- 安装目录里**没有 `.venv`**；只有 uv flavor 会建虚拟环境，名字是 `venv`（不带点）。
- 非 offline flavor（pip/uv）项目目录名是 `icode-tui`（按 wheel 元数据归一化，
  `src/chrys/app/installer.py:169-172`）。
- `~/.local/bin/aixcoding-cli` 是 `chrys` 二进制的别名（installer.py:36-37）。
- **降版本测更新**：只改 `METADATA` 的 `Version:` 行，不要动版本目录名（目录名参与
  `chrys install` 的旧版本清理排序）。

## 2. 触发链路与四道门

流程接线：主屏 push 后启动（`app/tui/app.py:1094`）→ `app/aixcoding/update/flow.py::_flow`。

门（`flow.py:101-117`），命中任意一条即静默跳过，**不发请求**：

1. pytest（`PYTEST_CURRENT_TEST`）
2. `CI` 环境变量非空且不是 `0/false/no`
3. textual web driver
4. **SOURCE flavor**（仓库 checkout，editable 安装）—— `AIXCODING_UPDATE_FORCE=1` 只豁免这一条
5. 设置 `update_check` 关闭

通过门之后还有状态门（`~/.chrys/` 下）：

- `aixcoding-update.json` 的 `checked_at` 在 24h 内 → 不检查也不弹窗（`CHECK_INTERVAL_SECONDS`）
- `update-skip-today`（mtime 为今天）→ 当天整个流程关闭，只提示
- `update-failures` 行数 ≥ 3 且是今天的 → 转 skip-today 并清空计数

环境与地址（`service/aixcoding/update/client.py:74-78`）：

| environment | 检查 base | mirror root（检查地址的 origin，去掉 `/csas`） |
|---|---|---|
| prod（默认） | `http://82.187.34.98/csas` | `http://82.187.34.98/aixcoding/file/aixcoding` |
| dev | `http://81.89.182.150/csas` | ⚠ 当前实际为 **prod 的 mirror**（见下） |
| local | `http://127.0.0.1:7778` | ⚠ 当前实际为 **prod 的 mirror**（见下） |

**⚠ pin 注记（2026-11-19，design 修订二十）**：mirror root 当前**临时写死为生产
origin**（`commands.py::_PINNED_MIRROR_ORIGIN`），不分环境——上表 dev/local 行的
mirror 地址是 D4 派生的**预期值**，仅在 dev 镜像发布、恢复推导后才生效。在此之前：

- dev/local 客户端的**检查**走各自环境的网关，**安装一律下载生产镜像**（跨环境
  混装，责任人已确认可接受）；
- `[update].base_url` 覆盖只迁移检查端点，**不迁移 mirror**；
- 已知症状：dev/local 下点"立即更新"实际 curl 的是 `82.187.34.98` 的 install.sh。

恢复 D4 推导后本表自然恢复正确。

## 3. 接口清单（全部 GET，无鉴权头）

### 3.1 版本检查（弹窗来源）

```
GET {base}/api/v2/releases/check?clientType=cli&platform=<win32|darwin|linux>&architecture=<x64|arm64>&currentVersion=<SemVer>
```

- 200：manifest（`version` / `artifact.url` / `forceUpgrade`）→ 弹窗
- 204：已是最新 / 平台无包 / 灰度未命中 → 静默
- 400：参数缺失或非法（严格模式）
- 版本比较**完全在服务端**；客户端 `_should_ask` 只做 `latest != __version__` 字符串判断

**注意：manifest 的 `artifact.url` 在 CLI 链路里是死字段**——wrapper 不下载它，
实际下载走安装脚本 + channel 文件（见 3.2/3.3）。

### 3.2 安装脚本（点“立即更新”后 wrapper 下载）

```
GET {mirror_root}/install.sh        # POSIX（runner.py:79，curl -fsSL 下载到临时文件再 bash）
GET {mirror_root}/install.ps1       # Windows（Invoke-RestMethod | Invoke-Expression）
```

失败 → 计一行 `date +%s` 到 `~/.chrys/update-failures`，不重启；成功 → 安装 + `exec` 重启（带会话）。

### 3.3 安装脚本内部再取的镜像文件

```
GET {mirror_root}/channels/cli/{prod|test}.txt                              # 渠道版本指针
GET {mirror_root}/releases/cli/<版本>/aixcoding-cli-<平台>-v<版本>-offline.tar.gz   # 先试 .tar.gz 再试 .zip
```

注意：脚本渠道是 `prod|test` 二选一（`AIXCODING_CHANNEL`），与客户端 environment 是**两套概念**。

### 3.4 mock 调试接口（仅测试）

```
POST /debug/config   # mode/version/force_update/force_upgrade/slow_ms/raw_body/drop_fields
GET  /debug/requests # 逐条请求日志（参数、时间、返回码）
POST /debug/reset
```

## 4. 测试方法

### 4.1 开发 checkout 里演练（Mac）

```bash
uv run python aixcoding/mock/update/server.py        # :7778，默认 update 模式，候选 999.0.0
export AIXCODING_ENVIRONMENT=local
export AIXCODING_UPDATE_FORCE=1                      # 只豁免 SOURCE 门
unset CI
rm -f ~/.chrys/aixcoding-update.json ~/.chrys/update-failures ~/.chrys/update-skip-today
uv run aixcoding-cli
```

场景热切换（不用重启 mock）：

```bash
curl -X POST http://127.0.0.1:7778/debug/config -d '{"mode":"no_update"}'      # 204
curl -X POST http://127.0.0.1:7778/debug/config -d '{"mode":"error"}'          # 500 静默
curl -X POST http://127.0.0.1:7778/debug/config -d '{"mode":"garbage"}'        # 解析失败静默
curl -X POST http://127.0.0.1:7778/debug/config -d '{"force_upgrade":true}'    # 强更弹窗（仅一个按钮）
curl -X POST http://127.0.0.1:7778/debug/config -d '{"slow_ms":20000}'         # 客户端 15s 超时
curl -X POST http://127.0.0.1:7778/debug/config -d '{"force_update":true,"version":"0.0.1"}'  # 脏数据
```

弹窗要重新触发就删 `~/.chrys/aixcoding-update.json`。只验 client 层可跳过 TUI：

```bash
uv run python -c "import asyncio; from chrys.service.aixcoding.update.client import check_for_update; print(asyncio.run(check_for_update()))"
```

### 4.2 真实安装的客户端在线上测（Linux 测试机）

**10 秒自证请求发没发**：

```bash
cat ~/.chrys/aixcoding-update.json
# checked_at 为今天 → 已发过；latest 有值 → 服务端回过 200；两者皆无 → 被门挡了或还没到点
```

**抓包看真实请求**（明文 HTTP，最直观）：

```bash
sudo tcpdump -i any -nn -A -s0 'tcp port 80 and (host 81.89.182.150 or host 82.187.34.98)'
rm -f ~/.chrys/aixcoding-update.json && aixcoding-cli
# 期待: GET /csas/api/v2/releases/check?clientType=cli&platform=linux&architecture=x64&currentVersion=<版本>
```

**mock 当外挂请求日志服务器**（server.py 纯标准库单文件，拷到测试机即可）：

```bash
python3 server.py &
mkdir -p ~/.chrys && printf '[update]\nbase_url = "http://127.0.0.1:7778"\n' >> ~/.chrys/aixcoding.toml
rm -f ~/.chrys/aixcoding-update.json && aixcoding-cli
curl http://127.0.0.1:7778/debug/requests | python3 -m json.tool
```

### 4.3 dev 环境手动复现整条链路

**pin 提醒（design 修订二十）**：当前 mirror 写死生产 origin——第 1 步检查请求
发往 dev 网关，但第 2 步的 `install.sh` 实际取自 `82.187.34.98`；若 dev 镜像
路径未发布而生产镜像正常，整条链路仍可走通（装的是生产制品）。下文 dev 镜像
URL 仅供恢复 D4 推导后对照。

```bash
# 0. 确认指向 dev（默认 prod，必须先设）
export AIXCODING_ENVIRONMENT=dev

# 1. 版本检查
curl -sS -w "\nHTTP %{http_code}\n" \
  "http://81.89.182.150/csas/api/v2/releases/check?clientType=cli&platform=linux&architecture=x64&currentVersion=0.28.0"

# 2. wrapper 下载安装脚本
curl -sS -w "\nHTTP %{http_code}\n" \
  "http://81.89.182.150/aixcoding/file/aixcoding/install.sh" -o /tmp/install.sh

# 3. 执行安装（仅第 2 步 200 时）
bash /tmp/install.sh

# 4. wrapper 的重启动作
exec aixcoding-cli

# 一次性完整复现（等价于点“立即更新”，不含等待进程退出）
curl -fsSL "http://81.89.182.150/aixcoding/file/aixcoding/install.sh" -o /tmp/install.sh \
  && bash /tmp/install.sh && exec aixcoding-cli \
  || { date +%s >> ~/.chrys/update-failures; echo "Update failed - see the output above."; }
```

### 4.4 状态文件参考

| 文件 | 内容/规则 |
|---|---|
| `aixcoding-update.json` | `checked_at` / `latest` / `force_upgrade` / `skipped_version`；原子写；损坏降级为默认 |
| `update-failures` | wrapper 失败逐行追加 `date +%s`；mtime 非今天整体作废 |
| `update-skip-today` | 计数达 3 生成；mtime 为今天则全程关闭；**手删即“立即重试”逃生口** |

`latest=""`（只能来自手改状态文件）：合法但不哑火弹窗；`checked_at` 仍在则当天静默，次日检查自愈。

## 5. 已知问题（2026-11-19 审查结论）

1. **纯 HTTP + 脚本直接执行**（高）：检查与镜像都是明文 HTTP，wrapper `curl|bash` 无摘要校验，供应链风险。
2. **Windows wrapper 路径未转义**（高）：`runner.py:105` 单引号内插 `failures` 路径，用户名带 `'` 时整个 `-Command` 失效；POSIX 侧用了 `shlex.quote`，不对称。
3. **skip-today 连强更一起压掉**（中）：`forceUpgrade` 也被 D2 门挡一天。
4. **代理策略不一致**（中）：检查侧 `trust_env=False` 直连，wrapper 的 curl/IRM 却尊重环境代理，corp proxy 下“查得到、装不上”。
5. **失败与成功同罚**（低）：`checked_at` 先盖章后检查，一次失败 24h 内不再试。
6. 其余：wrapper 等 PID 的复用竞态、`read_state` 的 bool 穿透、`_should_ask` 不比较 semver（信任服务端）、`artifact.url` 死字段。

## 6. 排障速查

| 症状 | 排查 |
|---|---|
| 看不到 `releases/check` 请求 | 四道门逐个查（`AIXCODING_UPDATE_FORCE` / `$CI` / 设置 / flavor）；再查 `checked_at`；确认 environment 指向对了服务器 |
| 弹窗出现但更新失败，curl 400 | mirror 路径（裸 origin，无 `/csas`）未在网关发布——服务端部署问题，非客户端 bug；`curl -sS <mirror>/install.sh | head -5` 看响应体 |
| 客户端 F6 Log Viewer 看不到更新日志 | 更新诊断日志为 DEBUG 级；`chrys` logger 可能被 OTel setup 钉在 INFO（setup.py:476-478），白名单降级逻辑跳过已钉级别的 logger |
| 想立即重试 | 删 `~/.chrys/update-skip-today`（及 `aixcoding-update.json`、`update-failures`） |
