# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""把规则包的两个 hook **合并**进钩子配置文件。

不能直接覆盖 ``hooks.yaml``：多数机器上那里已经有别的 hook（遥测、审计等），
覆盖会把它们全部弄丢。做法是：

1. 把 5 个脚本/词典/启动器文件复制到 ``<config_dir>/hooks/guard/``（子目录，
   避免和已有脚本混在一起）；
2. 把配置里所有 ``type: script`` 的 hook（规则包的，也包括遥测等别人家的）
   升级成不依赖本机 Python 的形态：Windows 上是 PowerShell 启动器
   （``guard/_launcher.ps1``，经 ``-File`` 调用），hook 每次执行时现找一个真实
   的 python——先 PATH（跳过 Microsoft 应用商店的 0 字节/转发点存根），再打包
   版 iCode 首次运行解压在 ``%LOCALAPPDATA%\\pyapp\\data\\chrys`` 的内嵌解释器。
   不升级的坏处：iCode 自己选解释器的顺序是 ``uv → python3 → python`` 且不
   过滤存根，``python --version`` 正常也没用——只要 ``python3`` 命中 WindowsApps
   的占位程序，hook 就以 exit 9009 起不来，配上 ``on_error: block`` 等于把
   所有请求都拦下（见 ``OPERATIONS.md`` 5.3）；POSIX 上保持 ``type: script``。
   ``--python`` 指定解释器时则钉死成绝对路径；
3. 若配置里还没有 ``security-prompt-guard``，就把两个 blocking hook 连同模板里的
   ``enabled: false`` 一起追加到 ``hooks`` 列表末尾；
4. 已有受管条目时，除了升级 ``run``，还把条目的 ``enabled`` 同步成模板值——现场
   手改过的开关会被模板口径覆盖，本版本即“不拦截”；
5. 写回前自动备份为 ``hooks.yaml.pre-guard``，并保留原文件的换行风格与 BOM。
   改写已有条目的那次升级另存 ``hooks.yaml.pre-pin``，不覆盖原始回退点。

配置文件不存在时新建一个最小骨架；``hooks: []`` 这种流式写法会先归一成块序列，
否则追加的条目会变成非法 YAML。

幂等：已存在 ``security-prompt-guard`` 时不重复追加，只在 ``run`` 或 ``enabled``
与模板不一致时改一次，可重复执行。

用法::

    uv run python guard_hooks/_install_merge.py            # 合并安装
    uv run python guard_hooks/_install_merge.py --check    # 只报告，不改文件
    uv run python guard_hooks/_install_merge.py --python D:\\py\\python.exe

回退：把 ``<config_dir>/hooks/hooks.yaml.pre-guard`` 拷回 ``hooks.yaml``。
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"
GUARD_SUBDIR = "guard"
GUARD_HOOK_ID = "security-prompt-guard"
PAYLOAD_FILES = ("_prompt_guard.py", "_tool_guard.py", "_guard_core.py", "rules.json", "_launcher.ps1")

SEED = "version: 1\n\nhooks:\n"
"""配置不存在时写入的最小骨架。``hooks:`` 留空（null）而不是 ``[]``：追加的条目是块序列。"""

_HOOKS_KEY = re.compile(r"^[ \t]*hooks[ \t]*:", re.MULTILINE)
_EMPTY_HOOKS_KEY = re.compile(r"^(?P<indent>[ \t]*)hooks[ \t]*:[ \t]*\[[ \t]*\][ \t]*$", re.MULTILINE)

_HOOK_ITEM_ID = re.compile(r"^(?P<indent>[ \t]*)-[ \t]+id[ \t]*:[ \t]*(?P<id>[^\s#]+)", re.MULTILINE)
"""一个 hook 列表项的起始行；块从这一行到下一个同级条目或顶层键为止。"""

_ENABLED_LINE = re.compile(r"^(?P<indent>[ \t]*)enabled[ \t]*:[ \t]*(?P<value>[^\s#]+)(?P<rest>[^\n]*)$", re.MULTILINE)
"""条目自己的开关行；``rest`` 留着行尾注释，改写时原样带回去。"""

_HOOK_EVENT_LINE = re.compile(r"^(?P<indent>[ \t]*)event[ \t]*:", re.MULTILINE)

_TOP_LEVEL_KEY = re.compile(r"^[A-Za-z_][\w-]*[ \t]*:", re.MULTILINE)
"""顶格键（``settings:`` / ``hooks:``）；块扫描遇到它即截止，不越出列表项。"""


def hooks_dir() -> Path:
    """返回全局钩子配置目录（Windows 用 ``%APPDATA%\\chrys\\hooks``）。"""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "chrys" / "hooks"
    return Path.home() / ".chrys" / "hooks"


def hook_entries(snippet: Path) -> str:
    """从规则包的 ``hooks.yaml`` 里取出 hooks 列表（不含 settings）。

    模板本身就是启动器形态（``GUARD_SCRIPT`` 已带 ``guard\\`` 前缀），不需要
    再改写路径。"""
    block = snippet.read_text(encoding="utf-8")
    marker = "\nhooks:\n"
    if marker not in block:
        raise SystemExit(f"规则包配置里没有 hooks 段落：{snippet}")
    return block[block.index(marker) + len(marker) :].rstrip("\n")


def copy_payload(here: Path, target: Path) -> list[str]:
    """复制脚本与词典到 ``guard/`` 子目录，返回复制成功的文件名。"""
    dest = target / GUARD_SUBDIR
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name in PAYLOAD_FILES:
        src = here / name
        if not src.exists():
            # 启动器在规则包的 guard/ 子目录里，其余文件在根目录。
            src = here / GUARD_SUBDIR / name
        if not src.exists():
            raise SystemExit(f"规则包文件缺失：{src}")
        shutil.copyfile(src, dest / name)
        written.append(name)
    return written


_WINDOWS_STUB_DIR = "Microsoft\\WindowsApps"
"""Windows 的 App Execution Alias 目录：``python.exe`` / ``python3.exe`` 是转发存根。"""


def is_store_stub(candidate: str) -> bool:
    """*candidate* 是不是「跑起来只会弹应用商店」的转发存根（或者压根不存在）。"""
    if not candidate:
        return True
    if _WINDOWS_STUB_DIR.casefold() in os.path.normcase(candidate):
        return True
    try:
        return os.path.getsize(candidate) == 0
    except OSError:
        return True


def resolve_python(override: str = "") -> str:
    """挑一个真解释器的绝对路径；挑不到返回空串。

    顺序 ``python3`` → ``python`` → ``sys.executable``，与 iCode 自己的解析顺序
    一致，唯一区别是过滤掉商店存根。``shutil.which`` 会把 0 字节的转发器当成
    合法结果，所以 ``icode hook validate`` 看不出任何异常——它和 iCode 一样被骗。
    """
    if override:
        path = os.path.abspath(override)
        if is_store_stub(path):
            raise SystemExit(f"指定的解释器不可用（不存在或为空文件）：{override}")
        return path
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and not is_store_stub(found):
            return os.path.abspath(found)
    return "" if is_store_stub(sys.executable) else os.path.abspath(sys.executable)


def interpreter_report() -> str:
    """复刻 iCode 的选择顺序（不过滤存根），把差异摆出来给人看。"""
    parts: list[str] = []
    uv = shutil.which("uv")
    if uv:
        parts.append(f"uv（{uv}）")
    for name in ("python3", "python"):
        found = shutil.which(name)
        if not found:
            continue
        kind = "⚠️ Microsoft Store 存根" if is_store_stub(found) else "真实解释器"
        parts.append(f"{name} → {found}（{kind}）")
    if not parts:
        return "iCode 的选择顺序：PATH 上既没有 uv 也没有 python（回退 sys.executable）"
    return "iCode 的选择顺序（不过滤存根）：" + " → ".join(parts)


_ANY_SCRIPT_RUN = re.compile(
    r"(?P<indent>[ \t]*)run:[ \t]*\n"
    r"[ \t]*type:[ \t]*script[ \t]*\n"
    r"[ \t]*path:[ \t]*(?P<q>['\"]?)(?P<rel>[^'\"\s#]+)(?P=q)[ \t]*\n"
)
"""任意 ``type: script`` 的 ``run`` 块（规则包的两个 guard，也包括遥测等其他 hook）。

只认 ``run:/type: script/path:`` 三连，不会碰列表里别的字段；替换时只吃掉这三行，
``run.args`` 等后续字段留在原位（command 形态下 iCode 会把它拼在 ``argv`` 后面，
启动器再原样转发给脚本）。"""

_GUARD_COMMAND_RUN = re.compile(
    r"(?P<indent>[ \t]*)run:[ \t]*\n"
    r"[ \t]*type:[ \t]*command[ \t]*\n"
    r"[ \t]*argv:[ \t]*\n"
    r"[ \t]*-[ \t]*(?P<q>['\"])(?P<prog>[^'\"\n]+)(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)(?P<script>[^'\"\n]*_(?:prompt|tool)_guard\.py)(?P=q)[ \t]*\n"
)
"""已钉死的写法；靠脚本名认领，别的 hook 即使也是 ``type: command`` 也不碰。"""


_POWERSHELL_EXE = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
"""Windows 自带 PowerShell 的固定路径（所有 Windows 机器一致）。启动器靠它绕开
``type: script`` 的解释器选择（``uv → python3 → python``，可能命中商店存根），
在每次 hook 执行时现找一个真实的 python。"""

_LAUNCHER_PS1 = r"guard\_launcher.ps1"
"""启动器脚本在 argv 里的写法（相对 ``cwd: ${chrys_home}/hooks``）。"""

_GUARD_LAUNCHER_RUN = re.compile(
    r"(?P<indent>[ \t]*)run:[ \t]*\n"
    r"[ \t]*type:[ \t]*command[ \t]*\n"
    r"[ \t]*cwd:[ \t]*[^\n]*\n"
    r"[ \t]*argv:[ \t]*\n"
    r"[ \t]*-[ \t]*(?P<q>['\"])[^'\"]*powershell\.exe(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-NoProfile(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-NonInteractive(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-ExecutionPolicy(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)Bypass(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-File(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)[^'\"]*_launcher\.ps1(?P=q)[ \t]*\n"
    r"[ \t]*env:[ \t]*\n"
    r"[ \t]*GUARD_SCRIPT:[ \t]*(?P<script>[^\s#]+)[ \t]*\n"
)
"""``-File`` 启动器形态的 ``run`` 块（含 ``cwd`` 与 ``env``）；脚本名不限规则包，
因为安装脚本会把配置里所有 script 形态都转成这个形态。"""

_OLD_ENCODED_RUN = re.compile(
    r"(?P<indent>[ \t]*)run:[ \t]*\n"
    r"[ \t]*type:[ \t]*command[ \t]*\n"
    r"[ \t]*argv:[ \t]*\n"
    r"[ \t]*-[ \t]*(?P<q>['\"])[^'\"]*powershell\.exe(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-NoProfile(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-NonInteractive(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)-EncodedCommand(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)[A-Za-z0-9+/=]{64,}(?P=q)[ \t]*\n"
    r"[ \t]*env:[ \t]*\n"
    r"[ \t]*GUARD_SCRIPT:[ \t]*(?P<script>_[a-z]+_guard\.py)[ \t]*\n"
)
"""上一版 ``-EncodedCommand`` 启动器形态；升级为 ``-File`` 形态（启动器逻辑放进
``guard/_launcher.ps1`` 文件，改逻辑不用再重生成 base64）。"""


def _pinned_run(indent: str, interpreter: str, script: Path) -> str:
    """生成一个 ``type: command`` 的 ``run`` 块（YAML 单引号，路径里的反斜杠不会被当转义）。"""
    inner = indent + "  "
    item = inner + "  "
    return f"{indent}run:\n{inner}type: command\n{inner}argv:\n{item}- '{interpreter}'\n{item}- '{script}'\n"


def _launcher_run(indent: str, rel_script: str) -> str:
    """生成 ``-File`` 启动器形态的 ``run`` 块。

    脚本名由 ``run.env.GUARD_SCRIPT`` 带进去（相对 hooks 根目录，如
    ``guard\\_prompt_guard.py``），启动器按自身位置（``$PSScriptRoot`` 的上一级）
    拼出完整路径，``cwd: ${chrys_home}/hooks`` 只用来定位 argv 里的启动器相对路径
    ——所以这份配置不依赖本机路径，换电脑原样可用。"""
    inner = indent + "  "
    item = inner + "  "
    return (
        f"{indent}run:\n"
        f"{inner}type: command\n"
        f"{inner}cwd: ${{chrys_home}}/hooks\n"
        f"{inner}argv:\n"
        f"{item}- '{_POWERSHELL_EXE}'\n"
        f"{item}- '-NoProfile'\n"
        f"{item}- '-NonInteractive'\n"
        f"{item}- '-ExecutionPolicy'\n"
        f"{item}- 'Bypass'\n"
        f"{item}- '-File'\n"
        f"{item}- '{_LAUNCHER_PS1}'\n"
        f"{inner}env:\n"
        f"{item}GUARD_SCRIPT: {rel_script}\n"
    )


def _posix_run(match: re.Match[str]) -> str:
    """启动器形态改回 ``type: script``（POSIX 上 iCode 现选解释器是安全的）。"""
    indent = match.group("indent")
    script = match.group("script").replace("\\", "/")
    if "/" not in script:
        # 旧 -EncodedCommand 形态的 GUARD_SCRIPT 只有文件名，不带 guard/ 前缀。
        script = f"{GUARD_SUBDIR}/{script}"
    return f"{indent}run:\n{indent}  type: script\n{indent}  path: {script}\n"


def pin_interpreter(text: str, interpreter: str, hooks_dir_path: Path) -> tuple[str, int]:
    """把配置里的 ``run`` 升级成不依赖本机 Python 的形态，返回 ``(新文本, 改写条数)``。

    默认（*interpreter* 为空）：Windows 上把**所有** ``type: script`` 的 hook（规则包
    的，也包括遥测等其他 hook）统一改成 ``-File`` 启动器形态——hook 每次执行时现找
    python（PATH 真解释器 → 打包版内嵌运行时），配置因此可跨机器携带；POSIX 上把
    启动器形态改回 ``type: script``（iCode 现选解释器在那里是安全的）。``--python``
    指定解释器时则钉死成 ``type: command`` + 绝对路径。

    四种写法会被改写：``type: script``（iCode 按 ``uv → python3 → python`` 现选，
    只要 python3 命中商店存根 hook 就起不来）；上一版的 ``-EncodedCommand`` 启动器
    形态（升级为 ``-File`` 形态）；``-File`` 启动器形态（只在 ``--python`` 时改写成
    钉死形态）；已经钉死但那个解释器没了（卸载 / 搬家）或只是旧钉死形态——死掉的
    钉子不换，hook 依旧起不来，而且钉死的路径换电脑就失效。已是目标形态的配置
    四个正则都不改写它，所以可以重复执行。

    ``argv`` 不做模板展开（``${...}`` 只在 ``run.cwd`` / ``run.env`` 里生效），所以
    钉死形态的解释器与脚本路径都得写成绝对路径。*hooks_dir_path* 是 ``run.path``
    相对路径的基准目录，即含有 ``hooks.yaml`` 的那个目录（不是 ``guard/``）。
    """

    def script_run(indent: str, rel: str) -> str:
        return f"{indent}run:\n{indent}  type: script\n{indent}  path: {rel}\n"

    def launch_run(indent: str, rel_script: str) -> str:
        if interpreter:
            return _pinned_run(indent, interpreter, hooks_dir_path / rel_script.replace("\\", "/"))
        if sys.platform == "win32":
            return _launcher_run(indent, rel_script)
        return script_run(indent, rel_script.replace("\\", "/"))

    from_script = 0
    from_encoded = 0
    from_launcher = 0
    refreshed = 0

    def convert_script(match: re.Match[str]) -> str:
        nonlocal from_script
        from_script += 1
        return launch_run(match.group("indent"), match.group("rel").replace("/", "\\"))

    def convert_encoded(match: re.Match[str]) -> str:
        nonlocal from_encoded
        from_encoded += 1
        return launch_run(match.group("indent"), f"{GUARD_SUBDIR}\\{match.group('script')}")

    def convert_launcher(match: re.Match[str]) -> str:
        nonlocal from_launcher
        from_launcher += 1
        return launch_run(match.group("indent"), match.group("script"))

    def repin_command(match: re.Match[str]) -> str:
        nonlocal refreshed
        prog = match.group("prog")
        if interpreter:
            if not is_store_stub(prog):
                return match.group(0)  # 还活着的钉子，不动。
            refreshed += 1
            return _pinned_run(match.group("indent"), interpreter, Path(match.group("script")))
        refreshed += 1
        return launch_run(match.group("indent"), f"{GUARD_SUBDIR}\\{Path(match.group('script')).name}")

    if interpreter:
        # --python：三种“现选解释器”的形态全部钉死成绝对路径。
        text = _ANY_SCRIPT_RUN.sub(convert_script, text)
        text = _OLD_ENCODED_RUN.sub(convert_encoded, text)
        text = _GUARD_LAUNCHER_RUN.sub(convert_launcher, text)
    elif sys.platform == "win32":
        text = _ANY_SCRIPT_RUN.sub(convert_script, text)
        text = _OLD_ENCODED_RUN.sub(convert_encoded, text)
    else:
        # POSIX 没有商店存根的问题；启动器形态在那里跑不起来，改回 script。
        text, from_launcher = _GUARD_LAUNCHER_RUN.subn(_posix_run, text)
        text, from_encoded = _OLD_ENCODED_RUN.subn(_posix_run, text)
    # 死钉子是最后一趟：前几趟刚生成的形态不会被它匹配（``sub`` 会把“原样
    # 返回”也算一次替换），所以改写数在回调里自己数。
    text = _GUARD_COMMAND_RUN.sub(repin_command, text)
    return text, from_launcher + from_encoded + from_script + refreshed


def pinned_interpreters(text: str) -> list[str]:
    """配置里已经钉死的解释器（去重、保持出现顺序），供 ``--check`` 报告真实状态。"""
    seen: list[str] = []
    for match in _GUARD_COMMAND_RUN.finditer(text):
        if match.group("prog") not in seen:
            seen.append(match.group("prog"))
    return seen


def _hook_block_spans(text: str) -> list[tuple[str, int, int, str]]:
    """返回每个 hook 条目的 ``(id, 起始偏移, 结束偏移, 缩进)``。

    结束位置是下一个条目的起始行、或列表后的第一个顶层键、或文本末尾。注释与
    空行留在所属块内，所以按块改写不会把别人的内容卷进来。
    """
    items = list(_HOOK_ITEM_ID.finditer(text))
    spans: list[tuple[str, int, int, str]] = []
    for index, item in enumerate(items):
        end = items[index + 1].start() if index + 1 < len(items) else len(text)
        top_level = _TOP_LEVEL_KEY.search(text, item.end())
        if top_level is not None and top_level.start() < end:
            end = top_level.start()
        spans.append((item.group("id"), item.start(), end, item.group("indent")))
    return spans


def _as_bool(raw: str) -> bool:
    """把 YAML 布尔字面量读成 bool（只有 ``true`` 算开，其余按关处理）。"""
    return raw.strip().lower() == "true"


def _template_switches(template_body: str) -> dict[str, bool]:
    """模板里每个 hook 条目的 ``enabled`` 值（没写该行按 ``true`` 记）。"""
    switches: dict[str, bool] = {}
    for hook_id, start, end, _indent in _hook_block_spans(template_body):
        match = _ENABLED_LINE.search(template_body, start, end)
        switches[hook_id] = _as_bool(match.group("value")) if match is not None else True
    return switches


def managed_enabled_states(text: str, template_body: str) -> dict[str, bool]:
    """配置里模板受管条目的 ``enabled`` 现状；缺失的行按 ``true`` 记。"""
    managed = _template_switches(template_body)
    states: dict[str, bool] = {}
    for hook_id, start, end, _indent in _hook_block_spans(text):
        if hook_id not in managed:
            continue
        match = _ENABLED_LINE.search(text, start, end)
        states[hook_id] = _as_bool(match.group("value")) if match is not None else True
    return states


def _line_end(text: str, offset: int) -> tuple[int, str]:
    """返回 ``offset`` 所在行之后的位置与该行的换行符；末行无换行时返回文本末尾。"""
    newline_index = text.find("\n", offset)
    if newline_index == -1:
        return len(text), "\n"
    newline = "\r\n" if newline_index > 0 and text[newline_index - 1] == "\r" else "\n"
    return newline_index + 1, newline


def sync_managed_enabled(text: str, template_body: str) -> str:
    """把已装配置里受管 hook 的 ``enabled`` 同步成模板值。

    模板是开关的唯一来源：现场手改过 ``enabled``，重跑安装也会回到模板口径
    （本版本模板为 ``false``，即不拦截）。只动模板里有的 id，其他 hook、缩进
    与行尾注释一律保留；已有行就地改值，没有就补在 ``event:`` 之后。
    """
    switches = _template_switches(template_body)
    for hook_id, start, end, indent in reversed(_hook_block_spans(text)):
        if hook_id not in switches:
            continue
        wanted = "true" if switches[hook_id] else "false"
        match = _ENABLED_LINE.search(text, start, end)
        if match is not None:
            if match.group("value") == wanted:
                continue
            line = f"{match.group('indent')}enabled: {wanted}{match.group('rest')}"
            text = text[: match.start()] + line + text[match.end() :]
            continue
        anchor = _HOOK_EVENT_LINE.search(text, start, end)
        insert_at, newline = _line_end(text, anchor.end() if anchor is not None else start)
        line_indent = anchor.group("indent") if anchor is not None else indent + "  "
        # 末行没有换行时先补一个，否则新行会粘在原行末尾。
        prefix = newline if insert_at == len(text) and not text.endswith("\n") else ""
        text = text[:insert_at] + f"{prefix}{line_indent}enabled: {wanted}{newline}" + text[insert_at:]
    return text


def _relax_console_encoding() -> None:
    """控制台编码容错：Windows 中文控制台是 GBK，输出 ``⚠️`` 会抛 UnicodeEncodeError。

    不改编码，只把无法编码的字符替换掉——这个脚本的输出是给人看的诊断信息，
    报错字符总比报错本身有用。（iCode 跑 hook 时会设 ``PYTHONUTF8=1``，不受影响。）
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(OSError, ValueError):
                reconfigure(errors="replace")


def merge(target: Path, body: str, *, interpreter: str = "") -> str:
    """写入 hook 条目：首次追加，或把已有条目升级成可移植的启动器形态。

    返回 ``merged`` / ``pinned`` / ``synced`` / ``unchanged``。首次追加按模板整段
    写入（含 ``enabled``）；已有条目除了升级 ``run``，还会把 ``enabled`` 同步成
    模板值——否则现场手改过的开关会让“出厂停用”失效。两种写入都会先备份：追加
    备份成 ``hooks.yaml.pre-guard``，改写已有条目备份成 ``hooks.yaml.pre-pin``
    ——后者不覆盖原始回退点。
    """
    raw = target.read_bytes()
    has_bom = raw.startswith(BOM)
    text = raw.decode("utf-8-sig")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")

    if GUARD_HOOK_ID in text:
        text, pinned = pin_interpreter(text, interpreter, target.parent)
        synced_text = sync_managed_enabled(text, body)
        synced = synced_text != text
        text = synced_text
        if not pinned and not synced:
            return "unchanged"
        backup = target.with_name(target.name + ".pre-pin")
        action = "pinned" if pinned else "synced"
    else:
        body, _ = pin_interpreter(body, interpreter, target.parent)
        backup = target.with_name(target.name + ".pre-guard")
        # 没有 hooks: 键时先补一个，否则追加的块序列会落在顶层变成非法 YAML。
        text = _EMPTY_HOOKS_KEY.sub(r"\g<indent>hooks:", text)
        head = text.rstrip("\n")
        if not _HOOKS_KEY.search(head):
            head += "\n\nhooks:"
        text = head + "\n" + body.rstrip("\n") + "\n"
        action = "merged"

    shutil.copyfile(target, backup)
    payload = text.encode("utf-8")
    if crlf:
        payload = payload.replace(b"\n", b"\r\n")
    target.write_bytes(BOM + payload if has_bom else payload)
    if action == "merged":
        print(f"已合并到 {target}")
    elif interpreter:
        print(f"已把 {pinned} 个 hook 的解释器钉死为 {interpreter}")
    else:
        print(f"已把 {pinned} 个 hook 的 run 升级成启动器形态（执行时现找 python）")
    print(f"  备份：{backup}")
    return action


def main() -> int:
    """执行安装或检查；返回进程退出码。"""
    here = Path(__file__).resolve().parent
    target = hooks_dir() / "hooks.yaml"
    args = sys.argv[1:]
    override = ""
    if "--python" in args:
        index = args.index("--python")
        if index + 1 >= len(args):
            raise SystemExit("--python 需要一个路径参数")
        override = args[index + 1]

    if "--check" in args:
        raw = target.read_bytes().decode("utf-8-sig", "replace") if target.exists() else ""
        guard_dir = target.parent / GUARD_SUBDIR
        files = [name for name in PAYLOAD_FILES if (guard_dir / name).exists()]
        missing = [name for name in PAYLOAD_FILES if name not in files]
        script_runs = len(_ANY_SCRIPT_RUN.findall(raw))
        encoded_runs = len(_OLD_ENCODED_RUN.findall(raw))
        programs = pinned_interpreters(raw)
        launchers = len(_GUARD_LAUNCHER_RUN.findall(raw))
        dead = [prog for prog in programs if is_store_stub(prog)]
        print(f"配置目录：{target.parent}")
        print(f"  hooks 已安装：{GUARD_HOOK_ID in raw}")
        template_body = hook_entries(here / "hooks.yaml")
        expected_switches = _template_switches(template_body)
        states = managed_enabled_states(raw, template_body)
        stopped = [hook_id for hook_id in expected_switches if not states.get(hook_id, True)]
        switches_match = all(states.get(hook_id, True) == value for hook_id, value in expected_switches.items())
        print(f"  护栏开关：{len(stopped)}/{len(expected_switches)} 个受管 hook 停用")
        if not switches_match:
            print("  修复：重跑本脚本（不带 --check）即可把护栏开关同步成模板值")
        print(f"  规则包文件：{len(files)}/{len(PAYLOAD_FILES)} {files}")
        if missing:
            print(f"  缺失：{missing}")
        if script_runs:
            print(f"  配置里的 run：{script_runs} 个 hook 仍是 type: script，由 iCode 从 PATH 现选")
        if encoded_runs:
            print(f"  配置里的 run：{encoded_runs} 个 hook 是旧 -EncodedCommand 形态，需升级")
        if launchers:
            print(f"  配置里的 run：{launchers} 个 hook 用 -File 启动器形态（执行时现找 python）")
        if programs:
            print(f"  配置里的 run：已钉死 {'、'.join(programs)}")
        if dead:
            print(f"  ⚠️ 钉死的解释器已不可用（不存在或为空文件）：{'、'.join(dead)}")
        if programs and not launchers and sys.platform == "win32":
            print("  提示：钉死形态绑定本机路径，换电脑会失效；重跑本脚本可升级成可移植的启动器形态")
        print(f"  {interpreter_report()}")
        if sys.platform == "win32":
            if script_runs or encoded_runs or dead:
                print("  修复：重跑本脚本（不带 --check）即可自动升级成启动器形态")
            healthy = (
                GUARD_HOOK_ID in raw
                and not missing
                and not dead
                and launchers >= 2
                and not script_runs
                and not encoded_runs
                and switches_match
            )
        else:
            # POSIX 上没有商店存根；script 是健康形态，启动器/旧 encoded 是残留。
            if launchers or encoded_runs or dead:
                print("  修复：重跑本脚本（不带 --check）即可自动改回 type: script")
            healthy = (
                GUARD_HOOK_ID in raw
                and not missing
                and not dead
                and not launchers
                and not encoded_runs
                and switches_match
            )
        return 0 if healthy else 1

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(SEED.encode("utf-8"))
        print(f"未找到钩子配置文件，已新建最小骨架：{target}")

    interpreter = ""
    if override:
        interpreter = resolve_python(override)
    written = copy_payload(here, target.parent)
    print(f"已复制 {len(written)} 个文件到 {target.parent / GUARD_SUBDIR}/")
    action = merge(target, hook_entries(here / "hooks.yaml"), interpreter=interpreter)
    if action == "unchanged":
        print("配置里已存在规则包的 hook，未改动 hooks.yaml（幂等）")
    if action == "synced":
        print("已把护栏开关同步成模板值（本版本模板为 enabled: false，即不拦截）")
    if interpreter:
        print(f"解释器（--python 指定，已钉死）：{interpreter}")
    elif sys.platform == "win32":
        print("解释器策略：启动器形态——hook 执行时现找 python（PATH 真解释器 →")
        print("  打包版内嵌运行时 %LOCALAPPDATA%\\pyapp\\data\\chrys\\...\\python.exe）")
    else:
        print("解释器策略：type: script，由 iCode 从 PATH 现选")
    print("下一步：uv run icode hook validate && uv run icode hook list")
    return 0


if __name__ == "__main__":
    _relax_console_encoding()
    raise SystemExit(main())
