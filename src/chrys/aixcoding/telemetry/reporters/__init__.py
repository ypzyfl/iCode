# ruff: noqa: RUF001, RUF002
"""csas 报文组装层：reporter 只给业务字段，公共字段在此统一补齐。

对齐 aixcoding ``buildToolDetailSaveItem`` 的收口语义（方案 §4.2）：
sessionId 之外的身份/环境字段（userId、git 五件套、channel 三元组、
pluginVersion、projectName）由本层自动附加，端点 reporter 不重复组装。
"""

from __future__ import annotations

import ntpath
import posixpath
from pathlib import Path
from typing import Any

BOUNDED_MEMORY_LIMIT = 1024
"""有界记忆表容量：长驻进程防泄漏（取消等无终态的残留也会被淘汰）。"""


def remember_bounded(mapping: dict, key: str, value: Any, *, limit: int = BOUNDED_MEMORY_LIMIT) -> None:
    """写入并维持容量上限（超限丢最旧，按插入序）。"""
    mapping[key] = value
    while len(mapping) > limit:
        mapping.pop(next(iter(mapping)))


def relative_file_name(raw: str, workspace_cwd: str | None = None) -> str:
    """文件路径的报文口径（tool-detail ``fileName`` 与 ai-code ``filepath`` 共用）：

    会话工作区（``workspace_cwd``）内的文件取**相对路径**（含文件名，POSIX 分隔符）；
    工作区外的文件取**绝对路径**（含文件名）。``workspace_cwd`` 缺失时**不做
    相对化**——进程 cwd 是 iCode 启动目录而非真实工程根
    （2026-10-09 真链路踩坑：projectName/git/fileName 全指向 iCode 仓库），
    宁可不下结论也不误判。路径分隔符统一为 ``/``。
    """
    normalized_raw = raw.replace("\\", "/")
    if not workspace_cwd:
        return normalized_raw
    try:
        windows_path = bool(ntpath.splitdrive(raw)[0] or ntpath.splitdrive(workspace_cwd)[0])
        path_module = ntpath if windows_path else posixpath
        base = path_module.abspath(workspace_cwd.replace("\\", "/"))
        path = path_module.normpath(normalized_raw)
        absolute = path_module.isabs(path)
        if not absolute:
            path = path_module.normpath(path_module.join(base, path))
        try:
            relative = path_module.relpath(path, base)
            if relative != ".." and not relative.startswith(".." + path_module.sep):
                return relative.replace("\\", "/")
        except ValueError:
            pass  # Different Windows drives cannot be made relative.
        if not windows_path and absolute:
            # A workspace can itself be a symlink; compare physical paths only
            # after the lexical path has failed the workspace containment test.
            physical_base = Path(base).resolve()
            physical_path = Path(path).resolve()
            if physical_path.is_relative_to(physical_base):
                return physical_path.relative_to(physical_base).as_posix()
        return path.replace("\\", "/")
    except OSError, ValueError:
        return normalized_raw


def common_fields(workspace_cwd: str | None = None, *, tool_detail: bool = False) -> dict[str, Any]:
    """csas 报文公共字段（channel/git/plugin/project/userId）。

    ``workspace_cwd``：会话工作区（事件携带，``SessionEnvironment.cwd`` 同源）——
    projectName / git 五件套的取值基；缺省回退进程 cwd（2026-10-09 修正，
    对齐 aixcoding workspace 语义）。
    """
    from chrys.aixcoding.context import CHANNEL_CLI, current_channel, current_user_id, plugin_version

    version = plugin_version()
    fields: dict[str, Any] = {"pluginVersion": version}
    user_id = current_user_id()
    if user_id:
        fields["userId"] = user_id

    channel = current_channel()
    fields["channelType"] = channel.channel_type
    icode_tui = tool_detail and channel.channel_type == CHANNEL_CLI and channel.channel_name == "icode-tui"
    fields["channelName"] = "icode" if icode_tui else channel.channel_name
    channel_version = version if icode_tui else channel.channel_version
    if channel_version:
        fields["channelVersion"] = channel_version

    cwd = Path(workspace_cwd) if workspace_cwd else Path.cwd()
    fields["projectName"] = cwd.name or str(cwd)

    from chrys.aixcoding.git_info import collect_git_info

    git = collect_git_info(cwd)
    if git is not None:
        fields.update(
            {
                key: value
                for key, value in (
                    ("gitRemote", git.git_remote),
                    ("gitBranch", git.git_branch),
                    ("gitRevision", git.git_revision),
                    ("gitOwner", git.git_owner),
                    ("gitRepo", git.git_repo),
                )
                if value
            }
        )
    return fields
