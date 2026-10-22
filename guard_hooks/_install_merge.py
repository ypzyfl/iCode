# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""把规则包的两个 hook **合并**进钩子配置文件。

不能直接覆盖 ``hooks.yaml``：多数机器上那里已经有别的 hook（遥测、审计等），
覆盖会把它们全部弄丢。做法是：

1. 把 4 个脚本/词典文件复制到 ``<config_dir>/hooks/guard/``（子目录，避免和
   已有脚本混在一起）；
2. 探测一个**真实**的 Python 解释器，把两个 hook 的 ``run`` 从 ``type: script``
   改写成钉死解释器绝对路径的 ``type: command``：iCode 选解释器时会选中 Windows
   应用商店的 0 字节转发存根，选中就起不来，配上 ``on_error: block`` 等于把所有
   请求都拦下（见 ``OPERATIONS.md`` 5.3）；
3. 若配置里还没有 ``security-prompt-guard``，就把两个 blocking hook 追加到
   ``hooks`` 列表末尾，脚本路径指向 ``guard/``；
4. 写回前自动备份为 ``hooks.yaml.pre-guard``，并保留原文件的换行风格与 BOM。
   只改写解释器的那次升级另存 ``hooks.yaml.pre-pin``，不覆盖原始回退点。

配置文件不存在时新建一个最小骨架；``hooks: []`` 这种流式写法会先归一成块序列，
否则追加的条目会变成非法 YAML。

幂等：已存在 ``security-prompt-guard`` 时不重复追加，只在解释器还没钉死时补一次
改写，可重复执行。

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
PAYLOAD_FILES = ("_prompt_guard.py", "_tool_guard.py", "_guard_core.py", "rules.json")

SEED = "version: 1\n\nhooks:\n"
"""配置不存在时写入的最小骨架。``hooks:`` 留空（null）而不是 ``[]``：追加的条目是块序列。"""

_HOOKS_KEY = re.compile(r"^[ \t]*hooks[ \t]*:", re.MULTILINE)
_EMPTY_HOOKS_KEY = re.compile(r"^(?P<indent>[ \t]*)hooks[ \t]*:[ \t]*\[[ \t]*\][ \t]*$", re.MULTILINE)


def hooks_dir() -> Path:
    """返回全局钩子配置目录（Windows 用 ``%APPDATA%\\chrys\\hooks``）。"""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "chrys" / "hooks"
    return Path.home() / ".chrys" / "hooks"


def hook_entries(snippet: Path) -> str:
    """从规则包的 ``hooks.yaml`` 里取出 hooks 列表（不含 settings）。"""
    block = snippet.read_text(encoding="utf-8")
    marker = "\nhooks:\n"
    if marker not in block:
        raise SystemExit(f"规则包配置里没有 hooks 段落：{snippet}")
    body = block[block.index(marker) + len(marker) :].rstrip("\n")
    for name in PAYLOAD_FILES[:2]:
        body = body.replace(f"path: {name}", f"path: {GUARD_SUBDIR}/{name}")
    return body


def copy_payload(here: Path, target: Path) -> list[str]:
    """复制脚本与词典到 ``guard/`` 子目录，返回复制成功的文件名。"""
    dest = target / GUARD_SUBDIR
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name in PAYLOAD_FILES:
        src = here / name
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


_GUARD_SCRIPT_RUN = re.compile(
    r"(?P<indent>[ \t]*)run:[ \t]*\n"
    r"[ \t]*type:[ \t]*script[ \t]*\n"
    r"[ \t]*path:[ \t]*(?P<rel>(?:[^\s#]+[/\\\\])?_(?:prompt|tool)_guard\.py)[ \t]*\n"
)
"""规则包两个 hook 的未钉死写法；只认这两个脚本名，不碰配置里别人的 hook。"""

_GUARD_COMMAND_RUN = re.compile(
    r"(?P<indent>[ \t]*)run:[ \t]*\n"
    r"[ \t]*type:[ \t]*command[ \t]*\n"
    r"[ \t]*argv:[ \t]*\n"
    r"[ \t]*-[ \t]*(?P<q>['\"])(?P<prog>[^'\"\n]+)(?P=q)[ \t]*\n"
    r"[ \t]*-[ \t]*(?P=q)(?P<script>[^'\"\n]*_(?:prompt|tool)_guard\.py)(?P=q)[ \t]*\n"
)
"""已钉死的写法；靠脚本名认领，别的 hook 即使也是 ``type: command`` 也不碰。"""


def _pinned_run(indent: str, interpreter: str, script: Path) -> str:
    """生成一个 ``type: command`` 的 ``run`` 块（YAML 单引号，路径里的反斜杠不会被当转义）。"""
    inner = indent + "  "
    item = inner + "  "
    return f"{indent}run:\n{inner}type: command\n{inner}argv:\n{item}- '{interpreter}'\n{item}- '{script}'\n"


def pin_interpreter(text: str, interpreter: str, hooks_dir_path: Path) -> tuple[str, int]:
    """把两个 hook 的解释器钉成绝对路径，返回 ``(新文本, 改写条数)``。

    两种情况会被改写：``type: script``（靠 iCode 现选，可能选中商店存根）；以及已经
    钉死但那个解释器已经没了（卸载 / 搬家）——死掉的钉子不换，hook 依旧起不来。
    还活着的手改 ``argv`` 一律不动，所以可以重复执行。

    ``argv`` 不做模板展开（``${...}`` 只在 ``run.cwd`` / ``run.env`` 里生效），所以
    解释器与脚本路径都得写成绝对路径。*hooks_dir_path* 是 ``run.path`` 相对路径的基准
    目录，即含有 ``hooks.yaml`` 的那个目录（不是 ``guard/``）。
    """
    if not interpreter:
        return text, 0

    def pin_script(match: re.Match[str]) -> str:
        script = hooks_dir_path / match.group("rel").replace("\\", "/")
        return _pinned_run(match.group("indent"), interpreter, script)

    def repin_command(match: re.Match[str]) -> str:
        nonlocal refreshed
        if not is_store_stub(match.group("prog")):
            return match.group(0)
        refreshed += 1
        return _pinned_run(match.group("indent"), interpreter, Path(match.group("script")))

    text, from_script = _GUARD_SCRIPT_RUN.subn(pin_script, text)
    # 第二趟里“还活着的钉子”也会被 ``sub`` 计一次替换，所以自己数。
    refreshed = 0
    text = _GUARD_COMMAND_RUN.sub(repin_command, text)
    return text, from_script + refreshed


def pinned_interpreters(text: str) -> list[str]:
    """配置里已经钉死的解释器（去重、保持出现顺序），供 ``--check`` 报告真实状态。"""
    seen: list[str] = []
    for match in _GUARD_COMMAND_RUN.finditer(text):
        if match.group("prog") not in seen:
            seen.append(match.group("prog"))
    return seen


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
    """写入 hook 条目：首次追加，或把已有条目升级成钉死解释器的形式。

    返回 ``merged`` / ``pinned`` / ``unchanged``。两种写入都会先备份，追加备份成
    ``hooks.yaml.pre-guard``，只改解释器备份成 ``hooks.yaml.pre-pin``——后者不覆盖
    原始回退点。
    """
    raw = target.read_bytes()
    has_bom = raw.startswith(BOM)
    text = raw.decode("utf-8-sig")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")

    if GUARD_HOOK_ID in text:
        text, pinned = pin_interpreter(text, interpreter, target.parent)
        if not pinned:
            return "unchanged"
        backup = target.with_name(target.name + ".pre-pin")
        action = "pinned"
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
    else:
        print(f"已把 {pinned} 个 hook 的解释器钉死为 {interpreter}")
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
        unpinned = len(_GUARD_SCRIPT_RUN.findall(raw))
        programs = pinned_interpreters(raw)
        dead = [prog for prog in programs if is_store_stub(prog)]
        print(f"配置目录：{target.parent}")
        print(f"  hooks 已安装：{GUARD_HOOK_ID in raw}")
        print(f"  规则包文件：{len(files)}/{len(PAYLOAD_FILES)} {files}")
        if missing:
            print(f"  缺失：{missing}")
        if unpinned:
            print(f"  配置里的解释器：{unpinned} 个 hook 仍是 type: script，由 iCode 从 PATH 现选")
        if programs:
            print(f"  配置里的解释器：已钉死 {'、'.join(programs)}")
        if dead:
            print(f"  ⚠️ 钉死的解释器已不可用（不存在或为空文件）：{'、'.join(dead)}")
        print(f"  {interpreter_report()}")
        if unpinned or dead:
            print("  修复：重跑本脚本（不带 --check）即可自动钉死 / 重新钉死")
        healthy = GUARD_HOOK_ID in raw and not missing and not unpinned and bool(programs) and not dead
        return 0 if healthy else 1

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(SEED.encode("utf-8"))
        print(f"未找到钩子配置文件，已新建最小骨架：{target}")

    interpreter = resolve_python(override)
    written = copy_payload(here, target.parent)
    print(f"已复制 {len(written)} 个文件到 {target.parent / GUARD_SUBDIR}/")
    action = merge(target, hook_entries(here / "hooks.yaml"), interpreter=interpreter)
    if action == "unchanged":
        print("配置里已存在规则包的 hook，未改动 hooks.yaml（幂等）")
    if interpreter:
        print(f"解释器：{interpreter}")
    else:
        print("⚠️ 本机没有可用的 Python 解释器，hook 仍是 type: script。")
        print("   iCode 会自己从 PATH 选，选中 Microsoft Store 存根就会「什么都干不了」。")
        print("   装一个真解释器（或 uv）后重跑本脚本，或用 --python <路径> 指定。")
    print("下一步：uv run icode hook validate && uv run icode hook list")
    return 0 if interpreter else 1


if __name__ == "__main__":
    _relax_console_encoding()
    raise SystemExit(main())
