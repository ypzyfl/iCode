# 验证记录：内网安装器与发布约定迁移（internal-installer）

> 活文档：追加验证证据，不删除旧记录；命令均在仓库根以大写盘符执行。
> 本记录只覆盖本地自动验证与明确标注的兼容性冒烟，不代表真实制品端到端验收已完成。

## 2026-11-05：实现后本地验证

环境：Windows 11 x64，Python 3.14.8；Windows PowerShell 5.1 与 pwsh 均实际参与 ps1
契约测试。运行前清空 `PYTHONPATH`，设置 `PYTHONUTF8=1`。

### 1. 安装器定向契约测试

命令：

```bat
uv run pytest aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py -n0
```

结果：**44 passed / 46 skipped，exit 0**（90 collected）。其中 42 个 Windows 用例在
pwsh / Windows PowerShell 5.1 上实跑，2 个静态契约用例实跑；46 个 POSIX 用例按
design §10 已批准的 R13 平台豁免在 Windows 跳过。

覆盖：prod/test 与显式版本 URL、base URL/channel 四级优先级、显式 SHA-256、离线包、
旧包拒绝、冲突两分支与外部文件字节不变、幂等、渠道降级、管道 stdin、退出码 126、
Rosetta/glibc/musl、品牌上下文、ps1 包结构/自检/install 故障及地址逃生门。

### 2. 统一验证入口

命令：

```bat
uv run python aixcoding/tools/verify.py --smart --paths <本批全部新增/修改路径>
```

结果：**Fork verify Summary: PASSED (exit 0)**。

- custom：**511 passed / 50 skipped**（561 items）。
- upstream：Smart Test 收集 36420 个非集成候选后，判定本批为非运行时变更，最终
  0 targets / 0 tests；输出 `Smart Test found no applicable pytest tests`。
- 该上游结果仅表示无适用的局部测试，不表述为上游全量测试通过。

### 3. 登记、文档与格式门禁

| 命令 | 结果 |
|---|---|
| `uv run python aixcoding/tools/gen_customizations.py --strict` | OK；98 registration rows / 135 markers / 10 designs；0 retired id / 0 warning；零新增登记、零漂移 |
| `uv run python aixcoding/tools/check_docs.py` | OK；扫描 20 ADR / 28 design / 26 self-review |
| `uv run ruff check --no-fix aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py` | All checks passed |
| `uv run ruff format --check aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py` | 1 file already formatted |
| `git diff --exit-code -- scripts/install.sh scripts/install.ps1 tests/app/test_install_scripts.py` | 零输出、exit 0；上游脚本与测试零改动 |

### 4. POSIX 脚本额外兼容性冒烟

当前机器的 `bash` 默认命令指向无可用发行版的 WSL，不能运行目标 POSIX 测试。另发现
Git Bash 后执行：

```bat
"C:\Program Files\Git\bin\bash.exe" -n aixcoding/release/install-internal-mirror.sh
"C:\Program Files\Git\bin\bash.exe" aixcoding/release/install-internal-mirror.sh --help
```

结果：两命令均 exit 0；帮助输出使用 AIxCoding / `aixcoding-cli`、统一 IP 和
`AIXCODING_*` 推荐变量。**这只是语法与帮助路径兼容性证据，不计作 Linux/macOS 通过。**

实现自查据此将 `${OS,,}` 改为显式平台 `case` 映射，避免依赖 macOS 系统 Bash 3.2
不支持的小写展开；修改后上述两项冒烟与统一验证均已重跑通过。

## 2026-11-06：一般用户 / 技术支持双层手册

- `aixcoding/release/INSTALL.md` 重写为一般用户版，仅保留默认安装、升级、卸载与求助路径。
- 新增 `aixcoding/docs/install-uninstall-support.md`，承接版本、完整下载地址、渠道/变量、
  全安装方式、冲突、PATH/rc、卸载残留和排障细节；已登记 `aixcoding/docs/INDEX.md`。
- requirements、design、test-plan 和静态契约测试同步按双层范围对账：用户版不含
  `--channel`、环境变量、内部 `chrys` 或镜像协议，支持版覆盖完整技术口径。
- 定向静态/品牌测试：**2 passed**；ruff lint/format 通过。
- 统一验证入口：**511 passed / 50 skipped，PASSED**；上游 Smart Test 对非运行时变更无适用
  用例。`check_docs.py` OK；strict 保持 98 登记行 / 135 marker、0 warning。

## 2026-11-06：第 2 轮独立评审复验

GLM-5.3 在完整工作区独立评审中复跑并确认：

- `check_docs.py`：OK（20 ADR / 28 design / 27 self-review）。
- `gen_customizations.py --strict`：98 登记行 / 135 marker / 0 warning，零新增、零漂移。
- `uv run pytest aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py -n0`：
  **44 passed / 46 skipped，exit 0**，与本文件第 1 节记录一致。

该复验是独立评审证据，不新增任何平台实测结论；下列五项缺口保持不变。

## 2026-11-06：PR #97 CI 平台证据（第 3 轮外部评审触发追加）

head `4c85018c` 的 PR CI（GitHub Actions check-runs API 查证，2026-11-06 02:04–02:18
UTC）：23 个 check run 全绿，含 **Custom tests (ubuntu-latest) 与 Custom tests
(windows-latest) 均 success**。

- ubuntu-latest 的 Custom tests 实跑了本批契约测试文件的 POSIX 用例：**缺口 1 的
  Linux 部分由 CI 关闭**（46 个 POSIX 用例在 Linux 实跑通过）。
- macOS 无对应 Custom tests job（aixcoding-tests.yml 未定义），**缺口 1 的 macOS
  部分维持**。
- CI Windows runner 用户名与临时路径为纯 ASCII，未覆盖 C1 的中文 Windows 编码
  场景；该场景证据见下节。

## 2026-11-06：第 3 轮外部评审（peer review）核实与修复

外部评审（head `4c85018c`）提出 C1–C4 四条候选，逐项只读核实后按责任人裁决
（2026-11-06，"按照你的建议处理"）实施：

- **C1（采纳，代码修复）**：契约测试在中文 Windows 默认编码下失败——
  `_PsMachine._run` 的 `subprocess.run(..., text=True)` 未显式指定编码，GBK 默认
  解码 CLIXML stderr 中的非 ASCII 字节抛 `UnicodeDecodeError`，使 `stderr=None`、
  断言处 `TypeError`。本机复现（不设 `PYTHONUTF8=1`，`--basetemp` 指向纯 ASCII
  路径）：修复前 **3 failed / 41 passed / 46 skipped**。修复＝`_run` 显式
  `encoding="utf-8", errors="replace"`。此前本地全绿系 `PYTHONUTF8=1` 掩盖、
  CI 系 ASCII 用户名掩盖；被测 ps1/sh 脚本自身无编码问题。修复后复验结果见下。
- **C2（采纳，本节及上节即处置）**：verification 与 CI 事实不一致——Linux 侧
  契约测试实际已由 PR #97 CI 覆盖，缺口 1 表述按活文档原则以上节追加更新。
- **C3（采纳，文档一行修正）**：`design.md` §6 R12 表"幂等跳过"行未限定平台
  （支持手册 §6.2 与 ps1 实现本就一致限定 POSIX）。修正＝该行补"（仅 POSIX sh；
  ps1 维持重跑即装）"限定，无行为改动。
- **C4（采纳，文档化）**：POSIX 脚本无 root/sudo 检测，root 下 `$HOME` 使安装与
  rc 写入落到 `/root`，对实际用户不可见（ps1 走 `LOCALAPPDATA` 无此问题）。处置＝
  INSTALL.md 与支持手册 §6.4 各加 root/sudo 提示，不加代码检测（按裁决）。

修复后复验（2026-11-06，Windows 11 x64，**不设 `PYTHONUTF8`**，`--basetemp` 指向
纯 ASCII 路径以排除路径编码干扰）：

```bat
uv run pytest aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py -n0
```

结果：**44 passed / 46 skipped，exit 0**（与修复前同条件的 3 failed 对照，C1 关闭）。
治理门禁同步通过：ruff check / format（测试文件）All checks passed；
`check_docs.py` OK（20 ADR / 28 design / 27 self-review）；
`gen_customizations.py --strict` 98 登记行 / 135 marker / 0 warning，零新增登记、
零漂移（C 类登记预期不变，四项处置均不触 marker）。

## 尚未执行的验收与覆盖缺口

1. **Linux/macOS 真实契约测试未运行**：46 个 POSIX 用例的 Windows skip 不是通过证据；
   须在 Linux/macOS CI 或实机重跑同一文件。
2. **0.33.0 真实制品端到端未运行**：内网在线 prod/test、POSIX `--from` 离线、解压直接
   启动、Windows 在线与手工 exe 均未在本轮连接真实镜像执行；design §13.1 保持未完成。
3. **Windows on Arm 未实测**：当前仅验证 x64 Windows 契约与文档中的仿真口径，不能宣称
   Arm 仿真已实机验证。
4. **真实外部命令升级未实测**：自动测试已断言 fake 外部文件字节不变及安装目录内命令
   验证，真实包内 alias 创建/冲突保护仍随真实制品验收确认。
5. **发布与回滚操作未实操**：publishing.md 的上传改名、先制品后指针、IP 迁移与回滚
   步骤本轮只完成文档对账，未变更真实镜像。

后续证据应按 test-plan.md 的真实制品步骤追加到本文件；在上述缺口关闭前，不得将本批
描述为全部验收完成。

## 2026-11-19：0.35.2 ZIP 与双入口安装体验

本轮按用户明确指令“开始修改”实施；未修改历史责任人签认字段，未执行 git 写操作或上传镜像。

### 改动与独立评审

- 内网默认根地址迁至 `http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding`。
- Linux/macOS 四个平台与 Windows x64 仅消费 `aixcoding-cli-<平台>-v<版本>-offline.zip`。
- 同时创建并验证 `aixcoding` / `aixcoding-cli`；相同版本免下载修复入口，支持 `--force` /
  `-Force`，分别提示首次安装、版本更新和重装。外部同名命令保留或在安装前明确拒绝。
- 网络和包内安装输出写入临时日志；显式失败和意外失败均非零并提示日志路径，成功清理日志。
- 独立 reviewer 只读检查后提出 PATH 写入失败缺日志指引，已修复。新增运行时回归进一步发现
  macOS Bash 3.2 对复合命令重定向失败可能返回成功；最小 shell 复现后改成单条 `printf`
  显式检查状态。最终静态复查无新增确定问题。
- POSIX 测试包采用原子 `mv` 替换主体，覆盖升级后旧硬链接入口的修复；另测外部相对软链接
  不能误认作自有安装、版本不一致时拒绝覆盖，以及失败日志保留。

### 实际验证

本机 macOS，系统 Bash 3.2.57。项目固定 Python 3.14.10 在本机不可用，现有 uv 无法解析其
下载，故以下命令均使用现有 `.venv` 的 Python 3.14.8，以 `--no-sync --python 3.14.8`
运行；没有修改项目 Python 固定版本或依赖。

```bash
uv run --no-sync --python 3.14.8 pytest aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py -q
```

结果：**64 passed / 50 skipped，exit 0**。50 个 Windows 用例在 macOS 跳过，不能计为 Windows 通过。

```bash
uv run --no-sync --python 3.14.8 python aixcoding/tools/verify.py --smart --paths aixcoding/release/install-internal-mirror.sh aixcoding/release/install-internal-mirror.ps1 aixcoding/release/INSTALL.md aixcoding/docs/install-uninstall-support.md aixcoding/docs/batches/internal-installer/design.md aixcoding/docs/batches/internal-installer/requirements.md aixcoding/docs/batches/internal-installer/test-plan.md aixcoding/docs/batches/internal-installer/publishing.md aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py
```

最终代码的定制套件：**995 passed / 55 skipped**；上游 Smart Test 对本次非运行时路径无适用
测试（收集 39495 项、执行 0 项）。整体 **Fork verify Summary: PASSED (exit 0)**。
本节仅为运行证据追加，不参与本轮测试代码选择。

其他实际检查：

- `bash -n aixcoding/release/install-internal-mirror.sh`：exit 0；`--help` 正常输出新域名、ZIP、双入口及 `--force`。
- `uv run --no-sync --python 3.14.8 ruff check --no-fix aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py`：All checks passed。
- `uv run --no-sync --python 3.14.8 ruff format --check aixcoding/tests/internal_installer/test_install_internal_mirror_scripts.py`：1 file already formatted。
- `uv run --no-sync --python 3.14.8 python aixcoding/tools/check_docs.py`：OK，扫描 29 ADR / 51 design / 50 self-review。
- `git diff --check`：exit 0。
- `uv run --no-sync --python 3.14.8 python aixcoding/tools/gen_customizations.py --strict`：**exit 1，28 errors**，
  全部路径位于已有的 `.codebuddy/worktrees/bg-01a1c9d3/`，是该嵌套工作树的未登记 marker；
  本轮没有修改该目录或登记审计器，不绕过此失败。完整输出保存在本机 `/tmp/icode-installer-registry.log`。

### 验证边界

- Linux 平台选择是在 macOS 上通过 uname/ldd 替身验证，未验证真实 Linux ZIP 的运行兼容性。
- 无本机 PowerShell / Windows 环境；Windows 只完成脚本静态评审并补充契约测试，须由 Windows CI/实机验证。
- 五平台 0.35.2 真实包、内网镜像下载与服务端上传未执行。
- POSIX 脚本新增的 `aixcoding` 入口在上游卸载后可能保留悬空链接，清理步骤已在支持手册说明；本轮未扩大到上游卸载器。
