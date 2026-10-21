# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""把规则包的两个 hook **合并**进钩子配置文件。

不能直接覆盖 ``hooks.yaml``：多数机器上那里已经有别的 hook（遥测、审计等），
覆盖会把它们全部弄丢。做法是：

1. 把 4 个脚本/词典文件复制到 ``<config_dir>/hooks/guard/``（子目录，避免和
   已有脚本混在一起）；
2. 若配置里还没有 ``security-prompt-guard``，就把两个 blocking hook 追加到
   ``hooks`` 列表末尾，脚本路径指向 ``guard/``；
3. 写回前自动备份为 ``hooks.yaml.pre-guard``，并保留原文件的换行风格与 BOM。

幂等：已存在 ``security-prompt-guard`` 时直接退出，可重复执行。

用法::

    uv run python guard_hooks/_install_merge.py            # 合并安装
    uv run python guard_hooks/_install_merge.py --check    # 只报告，不改文件

回退：把 ``<config_dir>/hooks/hooks.yaml.pre-guard`` 拷回 ``hooks.yaml``。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"
GUARD_SUBDIR = "guard"
GUARD_HOOK_ID = "security-prompt-guard"
PAYLOAD_FILES = ("_prompt_guard.py", "_tool_guard.py", "_guard_core.py", "rules.json")


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
    merged = text.replace("\r\n", "\n").rstrip("\n") + "\n" + body + "\n"
    if crlf:
        merged = merged.replace("\n", "\r\n")
    payload = merged.encode("utf-8")
    target.write_bytes(BOM + payload if has_bom else payload)
    print(f"已合并到 {target}")
    print(f"  备份：{backup}")
    return True


def main() -> int:
    """执行安装或检查；返回进程退出码。"""
    here = Path(__file__).resolve().parent
    target = hooks_dir() / "hooks.yaml"

    if "--check" in sys.argv[1:]:
        installed = target.exists() and GUARD_HOOK_ID in target.read_bytes().decode("utf-8", "replace")
        guard_dir = target.parent / GUARD_SUBDIR
        files = [name for name in PAYLOAD_FILES if (guard_dir / name).exists()]
        missing = [name for name in PAYLOAD_FILES if name not in files]
        print(f"配置目录：{target.parent}")
        print(f"  hooks 已安装：{installed}")
        print(f"  规则包文件：{len(files)}/{len(PAYLOAD_FILES)} {files}")
        if missing:
            print(f"  缺失：{missing}")
        return 0 if installed and not missing else 1

    if not target.exists():
        raise SystemExit(f"没有找到钩子配置文件：{target}")

    written = copy_payload(here, target.parent)
    print(f"已复制 {len(written)} 个文件到 {target.parent / GUARD_SUBDIR}/")
    if not merge(target, hook_entries(here / "hooks.yaml")):
        print("配置里已存在规则包的 hook，未改动 hooks.yaml（幂等）")
    print("下一步：uv run icode hook validate && uv run icode hook list")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
