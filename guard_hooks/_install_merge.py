# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""把规则包的两个 hook **合并**进钩子配置文件。

不能直接覆盖 ``hooks.yaml``：多数机器上那里已经有别的 hook（遥测、审计等），
覆盖会把它们全部弄丢。做法是：

1. 把 4 个脚本/词典文件复制到 ``<config_dir>/hooks/guard/``（子目录，避免和
   已有脚本混在一起）；
2. 若配置里还没有 ``security-prompt-guard``，就把两个 blocking hook 追加到
   ``hooks`` 列表末尾，脚本路径指向 ``guard/``；
3. 写回前自动备份为 ``hooks.yaml.pre-guard``，并保留原文件的换行风格与 BOM。

配置文件不存在时新建一个最小骨架；``hooks: []`` 这种流式写法会先归一成块序列，
否则追加的条目会变成非法 YAML。

幂等：已存在 ``security-prompt-guard`` 时直接退出，可重复执行。

用法::

    uv run python guard_hooks/_install_merge.py            # 合并安装
    uv run python guard_hooks/_install_merge.py --check    # 只报告，不改文件

回退：把 ``<config_dir>/hooks/hooks.yaml.pre-guard`` 拷回 ``hooks.yaml``。
"""

from __future__ import annotations

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


def config_dir() -> Path:
    """返回全局配置目录，与主程序 ``foundation/platform`` 的推断保持一致。

    Windows 用 ``%APPDATA%\\chrys``（缺环境变量时退 ``~/AppData/Roaming/chrys``）；
    macOS / Linux 用 ``~/.chrys``。
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(appdata) / "chrys"
    return Path.home() / ".chrys"


def hooks_dir() -> Path:
    """返回全局钩子配置目录（``<config_dir>/hooks``）。"""
    return config_dir() / "hooks"


def project_hooks_dir(workspace: Path) -> Path:
    """返回项目级钩子配置目录（``<workspace>/.chrys/hooks``）。"""
    return workspace / ".chrys" / "hooks"


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


def merge(target: Path, body: str) -> bool:
    """把 hook 条目追加进配置文件；返回是否发生了写入。"""
    raw = target.read_bytes()
    has_bom = raw.startswith(BOM)
    text = raw.decode("utf-8-sig")
    if GUARD_HOOK_ID in text:
        return False

    backup = target.with_name(target.name + ".pre-guard")
    shutil.copyfile(target, backup)

    crlf = "\r\n" in text
    text = _EMPTY_HOOKS_KEY.sub(r"\g<indent>hooks:", text.replace("\r\n", "\n"))
    head = text.rstrip("\n")
    # 没有 hooks: 键时先补一个，否则追加的块序列会落在顶层变成非法 YAML。
    if not _HOOKS_KEY.search(head):
        head += "\n\nhooks:"
    merged = head + "\n" + body + "\n"
    if crlf:
        merged = merged.replace("\n", "\r\n")
    payload = merged.encode("utf-8")
    target.write_bytes(BOM + payload if has_bom else payload)
    print(f"已合并到 {target}")
    print(f"  备份：{backup}")
    return True


def install_to(target_dir: Path, here: Path) -> int:
    """把规则包安装进 ``target_dir``（全局或项目级均可），返回退出码。"""
    target = target_dir / "hooks.yaml"

    if "--check" in sys.argv[1:]:
        installed = target.exists() and GUARD_HOOK_ID in target.read_bytes().decode("utf-8", "replace")
        guard_dir = target_dir / GUARD_SUBDIR
        files = [name for name in PAYLOAD_FILES if (guard_dir / name).exists()]
        missing = [name for name in PAYLOAD_FILES if name not in files]
        print(f"配置目录：{target_dir}")
        print(f"  hooks 已安装：{installed}")
        print(f"  规则包文件：{len(files)}/{len(PAYLOAD_FILES)} {files}")
        if missing:
            print(f"  缺失：{missing}")
        return 0 if installed and not missing else 1

    if not target.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(SEED.encode("utf-8"))
        print(f"未找到钩子配置文件，已新建最小骨架：{target}")

    written = copy_payload(here, target_dir)
    print(f"已复制 {len(written)} 个文件到 {target_dir / GUARD_SUBDIR}/")
    if not merge(target, hook_entries(here / "hooks.yaml")):
        print("配置里已存在规则包的 hook，未改动 hooks.yaml（幂等）")
    print("下一步：uv run icode hook validate && uv run icode hook list")
    return 0


def main() -> int:
    """执行安装或检查；返回进程退出码。

    支持三种模式::

        python _install_merge.py                 # 全局（<config_dir>/hooks/）
        python _install_merge.py --check         # 全局只检查
        python _install_merge.py --project [DIR] # 项目级（<DIR>/.chrys/hooks/，默认当前目录）
    """
    here = Path(__file__).resolve().parent
    argv = sys.argv[1:]
    if "--project" in argv:
        idx = argv.index("--project")
        rest = argv[idx + 1 :]
        workspace = Path(rest[0]).resolve() if rest and not rest[0].startswith("--") else Path.cwd().resolve()
        print(f"项目级安装目标：{workspace}")
        print("提醒：项目级 hooks 需要在设置里打开 project.hooks_enabled 才会加载。")
        return install_to(project_hooks_dir(workspace), here)

    return install_to(hooks_dir(), here)


if __name__ == "__main__":
    raise SystemExit(main())
