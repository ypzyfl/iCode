# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""iCode 安全拦截引擎 —— 提示词层与工具调用前两个 Hook 的唯一公共依赖。

设计约束（决定了这里的写法）：

* Hook 以子进程方式运行，标准输入是 ``DEVNULL``，因此**无法**在 Hook 内做
  交互式确认。所有"处置"只能表达成 ``action: block`` + ``reason``，由 iCode
  把 ``reason`` 推给用户（提示词层走 ``Error(code="hook_blocked")``，工具层
  走被拒绝的工具调用）。这也是 ``settings.confirm_disposition`` 默认取
  ``block`` 的原因：表里的 ``confirm`` 一律先按"打断 + 提示"落地。
* Hook 只看得到**入参**，看不到工具返回值，所以输出侧的扫描不在本层。
* 与主程序零耦合：本模块只用标准库，不 import 任何 ``chrys`` 包；规则与词典
  全部外置在 ``rules.json``，改词典不需要改代码。

对外接口只有四个：:func:`load_config`、:func:`evaluate_prompt`、
:func:`evaluate_tool_call`、:func:`run_hook`。
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sys
import tempfile
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

RULES_FILE_NAME = "rules.json"
"""与本脚本同目录的默认规则文件。"""

RULES_PATH_ENV = "ICODE_GUARD_RULES"
"""可用该环境变量指向另一份 ``rules.json``（测试或多套策略切换用）。"""

AUDIT_PATH_ENV = "ICODE_GUARD_AUDIT"
"""可用该环境变量覆盖留痕文件路径。"""

MAX_SNIPPET_CHARS = 80
"""命中片段在用户提示里最多展示的字符数。"""

MAX_RULE_REFS_DEPTH = 4
"""``rule_refs`` 递归上限，防止规则互相引用形成环。"""

_ASCII_TOKEN = re.compile(r"[A-Za-z0-9 ._+:/\\@-]+")
"""纯 ASCII 的词典条目按词边界匹配，避免 ``IDA`` 命中 ``validation``。"""

_IPV4_IN_TEXT = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_URL_IN_TEXT = re.compile(r"\b(?:https?|ftp)://[^\s\"'`<>|&]+", re.IGNORECASE)
"""从自由文本（如 shell 命令）里提取 URL；trailing 标点在调用处裁掉。"""

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_PATH_ARG_HINTS = ("path", "file", "dir", "target")
_URL_ARG_HINTS = ("url", "uri", "endpoint", "host", "address", "link")


class GuardError(RuntimeError):
    """引擎自身无法继续（配置损坏、正则非法等）时抛出。"""


class DeadlineExceeded(RuntimeError):
    """单次评估超过 ``settings.self_timeout_seconds`` 时抛出。"""


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


class GuardConfig:
    """``rules.json`` 的内存视图。"""

    __slots__ = ("dictionaries", "path", "prompt_rules", "settings", "source", "tool_rules")

    def __init__(self, data: dict[str, Any], *, path: Path) -> None:
        self.source = data
        self.path = path
        self.settings = data.get("settings") or {}
        self.dictionaries = data.get("dictionaries") or {}
        self.prompt_rules = [r for r in (data.get("prompt_rules") or []) if isinstance(r, dict)]
        self.tool_rules = [r for r in (data.get("tool_rules") or []) if isinstance(r, dict)]

    # -- 设置读取 ---------------------------------------------------------

    def setting(self, name: str, default: Any = None) -> Any:
        value = self.settings.get(name)
        return default if value is None else value

    def sub_setting(self, name: str, default: Any = None) -> dict[str, Any]:
        value = self.settings.get(name)
        return dict(value) if isinstance(value, dict) else dict(default or {})

    # -- 词典读取 ---------------------------------------------------------

    def dictionary(self, name: str) -> list[Any]:
        entries = self.dictionaries.get(name)
        return list(entries) if isinstance(entries, list) else []

    def rule(self, rule_id: str) -> dict[str, Any] | None:
        for candidate in (*self.tool_rules, *self.prompt_rules):
            if candidate.get("id") == rule_id:
                return candidate
        return None

    @property
    def max_scan_chars(self) -> int:
        try:
            return max(1024, int(self.setting("max_scan_chars", 262144)))
        except (TypeError, ValueError):
            return 262144

    @property
    def self_timeout_seconds(self) -> float:
        try:
            return max(0.2, float(self.setting("self_timeout_seconds", 4.0)))
        except (TypeError, ValueError):
            return 4.0

    @property
    def fail_closed(self) -> bool:
        return bool(self.setting("fail_closed", True))


def config_home() -> Path:
    """推断 ``<config_dir>``（通常是 ``~/.chrys``）。

    运行期环境变量里没有现成的值，但 payload 文件一定落在
    ``<config_dir>/hooks/tmp/`` 下，据此回溯三层即可；推断失败时退回
    ``~/.chrys``。
    """
    payload = os.environ.get("CHRYS_HOOK_PAYLOAD_FILE")
    if payload:
        try:
            resolved = Path(payload).resolve()
            if resolved.parent.name == "tmp":
                return resolved.parent.parent.parent
        except OSError:
            pass
    return Path.home() / ".chrys"


def expand(value: str) -> str:
    """展开 ``${chrys_home}``（iCode 在 ``run.env`` 里支持的同名模板）。"""
    return value.replace("${chrys_home}", str(config_home()))


def rules_file() -> Path:
    """返回本次要加载的 ``rules.json`` 路径。"""
    override = os.environ.get(RULES_PATH_ENV)
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / RULES_FILE_NAME


def load_config() -> GuardConfig:
    """读取并解析规则文件；任何异常都冒泡给调用方走失败兜底。"""
    path = rules_file()
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise GuardError(f"规则文件顶层必须是对象：{path}")
    return GuardConfig(data, path=path)


# ---------------------------------------------------------------------------
# 条目 / 模式
# ---------------------------------------------------------------------------


def _entry_parts(entry: Any) -> tuple[str, str, bool]:
    """把词典条目拆成 ``(正则/字面量, 展示名, 是否为正则)``。"""
    if isinstance(entry, str):
        return entry, entry, False
    if isinstance(entry, dict):
        value = entry.get("value")
        text = value if isinstance(value, str) else ""
        name = entry.get("name")
        label = name if isinstance(name, str) and name else text
        return text, label, bool(entry.get("regex"))
    return "", "", False


def _select_entries(entries: list[Any], names: Any) -> list[Any]:
    """按 ``names`` 过滤词典条目；``names`` 缺省或含 ``"*"`` 时不过滤。"""
    if not isinstance(names, list) or not names or "*" in names:
        return entries
    wanted = {str(n) for n in names}
    selected = [e for e in entries if isinstance(e, dict) and str(e.get("name")) in wanted]
    if selected:
        return selected
    # 条目没有名字（纯字符串词典）时退回全量，避免配置写错导致规则静默失效。
    return [e for e in entries if not isinstance(e, dict)] or entries


class Pattern:
    """一条编译好的词典条目。"""

    __slots__ = ("label", "regex", "source")

    def __init__(self, source: str, label: str, regex: re.Pattern[str]) -> None:
        self.source = source
        self.label = label
        self.regex = regex


def compile_literal(text: str, *, label: str) -> Pattern:
    """把字面量编成带词边界的正则（纯 ASCII 时），否则编成普通子串。"""
    if _ASCII_TOKEN.fullmatch(text):
        source = r"(?<![A-Za-z0-9_])" + re.escape(text) + r"(?![A-Za-z0-9_])"
    else:
        source = re.escape(text)
    return Pattern(source, label, re.compile(source, re.IGNORECASE))


def compile_patterns(config: GuardConfig, detector: dict[str, Any], *, mode: str) -> list[Pattern]:
    """把一个词典型检测器展开成编译好的模式列表。

    ``mode``：``literal`` 按词边界匹配字面量（用于工具名关键词），``plain``
    按普通子串匹配字面量（用于路径片段、扩展名等不应受词边界影响的场景），
    ``regex`` 直接把条目当正则。条目显式标了 ``"regex": true`` 时一律按正则。
    """
    name = str(detector.get("dictionary") or "")
    if not name:
        raise GuardError(f"检测器缺少 dictionary：{detector!r}")
    entries = _select_entries(config.dictionary(name), detector.get("names"))
    if not entries:
        raise GuardError(f"词典为空或 names 未命中：{name}")
    patterns: list[Pattern] = []
    for entry in entries:
        value, label, is_regex = _entry_parts(entry)
        if not value:
            continue
        try:
            if mode == "regex" or is_regex:
                patterns.append(Pattern(value, label, re.compile(value, re.IGNORECASE)))
            elif mode == "plain":
                patterns.append(Pattern(re.escape(value), label, re.compile(re.escape(value), re.IGNORECASE)))
            else:
                patterns.append(compile_literal(value, label=label))
        except re.error as exc:
            raise GuardError(f"词典 {name} 中的正则非法：{value!r}（{exc}）") from exc
    return patterns


# ---------------------------------------------------------------------------
# 扫描上下文与命中
# ---------------------------------------------------------------------------


class ScanContext:
    """一次 Hook 评估的输入切片。"""

    __slots__ = ("args", "config", "cwd", "kind", "payload", "profile", "texts", "tool_name")

    def __init__(
        self,
        *,
        config: GuardConfig,
        texts: list[tuple[str, str]],
        args: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        tool = payload.get("tool")
        if not isinstance(tool, dict):
            tool = {}
        self.config = config
        self.texts = texts
        self.args = args
        self.payload = payload
        self.kind = str(tool.get("kind") or "")
        self.tool_name = str(tool.get("name") or "")
        self.cwd = str(payload.get("cwd") or "")
        self.profile = str(payload.get("profile") or "")


class Evidence:
    """一条命中证据，用于用户提示与留痕。"""

    __slots__ = ("label", "snippet", "source")

    def __init__(self, label: str, snippet: str, source: str) -> None:
        self.label = label
        self.snippet = snippet
        self.source = source

    def describe(self) -> str:
        where = f"，来源 {self.source}" if self.source else ""
        return f"命中「{self.label}」{where}：{self.snippet}"

    def to_json(self) -> dict[str, str]:
        return {"label": self.label, "snippet": self.snippet, "source": self.source}


class Hit:
    """一条规则命中。"""

    __slots__ = ("disposition", "evidence", "rule_id", "rule_name")

    def __init__(self, rule: dict[str, Any], disposition: str, evidence: list[Evidence]) -> None:
        self.rule_id = str(rule.get("id") or "?")
        self.rule_name = str(rule.get("name") or self.rule_id)
        self.disposition = disposition
        self.evidence = evidence

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.rule_id,
            "name": self.rule_name,
            "disposition": self.disposition,
            "evidence": [e.to_json() for e in self.evidence],
        }


def snippet_of(text: str, start: int, end: int) -> str:
    """截取命中位置前后的短片段。"""
    left = max(0, start - 20)
    right = min(len(text), end + 20)
    piece = text[left:right].replace("\n", " ").replace("\r", " ").strip()
    if left > 0:
        piece = "…" + piece
    if right < len(text):
        piece = piece + "…"
    return piece[:MAX_SNIPPET_CHARS]


# ---------------------------------------------------------------------------
# 取值
# ---------------------------------------------------------------------------


def _stringify(value: Any, budget: int) -> str:
    if isinstance(value, str):
        return value[:budget]
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:budget]
    except (TypeError, ValueError):
        return str(value)[:budget]


def collect_texts(args: dict[str, Any], arg_keys: Any, budget: int) -> list[tuple[str, str]]:
    """按 ``arg_keys`` 收集待扫描文本；未指定时扫描全部参数。"""
    keys = (
        [str(key) for key in arg_keys if key in args] if isinstance(arg_keys, list) and arg_keys else list(args.keys())
    )
    texts: list[tuple[str, str]] = []
    remaining = budget
    for key in keys:
        if remaining <= 0:
            break
        text = _stringify(args.get(key), remaining)
        if not text:
            continue
        remaining -= len(text)
        texts.append((str(key), text))
    return texts


def path_values(args: dict[str, Any]) -> list[str]:
    """取出所有看起来像文件路径的参数值。"""
    found: list[str] = []
    for key, value in args.items():
        lowered = str(key).lower()
        if not any(hint in lowered for hint in _PATH_ARG_HINTS):
            continue
        if isinstance(value, str) and value:
            found.append(value)
        elif isinstance(value, list):
            found.extend(str(v) for v in value if isinstance(v, str) and v)
    return found


def url_values(args: dict[str, Any]) -> list[str]:
    """取出所有看起来像 URL / 主机名的参数值。"""
    found: list[str] = []
    for key, value in args.items():
        lowered = str(key).lower()
        if not any(hint in lowered for hint in _URL_ARG_HINTS):
            continue
        if isinstance(value, str) and value:
            found.append(value)
        elif isinstance(value, list):
            found.extend(str(v) for v in value if isinstance(v, str) and v)
    return found


def split_host_port(raw: str) -> tuple[str, int | None]:
    """把 ``url`` / ``host:port`` / 裸 IP 统一解析成 ``(host, port)``。"""
    text = raw.strip()
    if not text:
        return "", None
    if "://" in text:
        parts = urlsplit(text)
        host = parts.hostname or ""
        try:
            port = parts.port
        except ValueError:
            port = None
        if port is None and parts.scheme == "https":
            port = 443
        elif port is None and parts.scheme == "http":
            port = 80
        return host.lower(), port
    if text.startswith("//"):
        return split_host_port("http:" + text)
    candidate = text.split("/", 1)[0]
    if candidate.startswith("["):
        host, _, rest = candidate[1:].partition("]")
        port_text = rest[1:] if rest.startswith(":") else ""
        return host.lower(), int(port_text) if port_text.isdigit() else None
    host, _, port_text = candidate.partition(":")
    if port_text.isdigit():
        return host.lower(), int(port_text)
    return candidate.lower(), None


def _as_ip(host: str) -> Any:
    """把主机名解析成 IP 对象；不是 IP 字面量时返回 ``None``。"""
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _network_or_none(entry: Any) -> Any:
    try:
        return ipaddress.ip_network(str(entry), strict=False)
    except ValueError:
        return None


def _networks(entries: list[Any]) -> list[Any]:
    nets = [_network_or_none(entry) for entry in entries]
    return [net for net in nets if net is not None]


# ---------------------------------------------------------------------------
# 检测器
# ---------------------------------------------------------------------------


def _match_patterns(patterns: list[Pattern], texts: list[tuple[str, str]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for label, text in texts:
        for pattern in patterns:
            found = pattern.regex.search(text)
            if found is None:
                continue
            evidence.append(Evidence(pattern.label, snippet_of(text, found.start(), found.end()), label))
            if len(evidence) >= 4:
                return evidence
    return evidence


def _detect_patterns(config: GuardConfig, detector: dict[str, Any], ctx: ScanContext, *, mode: str) -> list[Evidence]:
    return _match_patterns(compile_patterns(config, detector, mode=mode), ctx.texts)


def _detect_ip_cidr(config: GuardConfig, detector: dict[str, Any], ctx: ScanContext) -> list[Evidence]:
    networks = _networks(config.dictionary(str(detector.get("dictionary") or "")))
    if not networks:
        return []
    evidence: list[Evidence] = []
    for label, text in ctx.texts:
        for raw in _IPV4_IN_TEXT.findall(text):
            address = _as_ip(raw)
            if address is None:
                continue
            for network in networks:
                if address.version == network.version and address in network:
                    evidence.append(Evidence(str(network), raw, label))
                    break
    return evidence


def _detect_path(config: GuardConfig, detector: dict[str, Any], ctx: ScanContext) -> list[Evidence]:
    patterns = compile_patterns(config, detector, mode="plain")
    evidence: list[Evidence] = []
    for raw in path_values(ctx.args):
        normalized = raw.replace("/", "\\")
        for pattern in patterns:
            found = pattern.regex.search(normalized) or pattern.regex.search(raw)
            if found is None:
                continue
            evidence.append(Evidence(pattern.label, raw, "path"))
            break
    return evidence


def _detect_extension(config: GuardConfig, detector: dict[str, Any], ctx: ScanContext) -> list[Evidence]:
    patterns = compile_patterns(config, detector, mode="plain")
    evidence: list[Evidence] = []
    for raw in path_values(ctx.args):
        lowered = raw.lower()
        for pattern in patterns:
            if pattern.regex.search(lowered):
                evidence.append(Evidence(pattern.label, raw, "path"))
                break
    return evidence


def _detect_write_scope(ctx: ScanContext) -> list[Evidence]:
    """T-FS-01：只允许写工作区与 ``$TEMP/icode-session-**``，帮助文档只读。"""
    scope = ctx.config.sub_setting("write_scope", {})
    if scope.get("allow_outside_workspace", False):
        return []
    workspace = _resolve_workspace(ctx.cwd)
    temp_root = Path(tempfile.gettempdir()).resolve()
    temp_prefixes = [str(p) for p in scope.get("temp_prefixes") or ["icode-session-"]]
    readonly_globs = [str(g) for g in scope.get("readonly_globs") or []]

    evidence: list[Evidence] = []
    for raw in path_values(ctx.args):
        target = _resolve_workspace(ctx.cwd, raw)
        if target is None:
            # 解析失败的路径按违规处理（fail-closed）。
            evidence.append(Evidence("工作区外写入", raw, "path"))
            continue
        posix = target.as_posix()
        for glob in readonly_globs:
            if fnmatch(posix, glob):
                evidence.append(Evidence("只读帮助文档", raw, "path"))
                break
        if workspace is not None and _is_within(target, workspace):
            continue
        if _is_session_temp(target, temp_root, temp_prefixes):
            continue
        evidence.append(Evidence("工作区外写入", raw, "path"))
    return evidence


def _resolve_workspace(cwd: str, raw: str | None = None) -> Path | None:
    if raw is None:
        base = Path(cwd) if cwd else Path.cwd()
    else:
        base = Path(raw).expanduser()
        if not base.is_absolute():
            base = Path(cwd or Path.cwd()) / base
    try:
        return base.resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def _is_within(target: Path, root: Path) -> bool:
    try:
        target.relative_to(root)
    except ValueError:
        return False
    return True


def _is_session_temp(target: Path, temp_root: Path, prefixes: list[str]) -> bool:
    if not _is_within(target, temp_root):
        return False
    parts = target.parts
    return any(part.startswith(prefix) for prefix in prefixes for part in parts[-4:] if len(part) > len(prefix))


def _detect_url(ctx: ScanContext, mode: str) -> list[Evidence]:
    """网络分类：``blocked`` 命中黑名单/危险端口，``default`` 命中非白名单地址。

    除了 URL 形态的参数值，还扫描待检文本（shell 命令的 ``command`` 等）里
    出现的 ``http(s)://`` 地址，堵住"用 curl 绕过网络规则"的盲区。
    """
    values = url_values(ctx.args)
    for _label, text in ctx.texts:
        values.extend(match.group(0).rstrip(".,;:)]}") for match in _URL_IN_TEXT.finditer(text))
        # 裸 IP（ping/traceroute 等不带 scheme）同样按候选地址评估；
        # 白名单网段（127/10/172.16/192.168）在 default 模式天然放行。
        values.extend(match.group(0) for match in _IPV4_IN_TEXT.finditer(text))
    blocked_hosts = compile_patterns(ctx.config, {"dictionary": "blocked_hosts", "names": None}, mode="plain")
    dangerous_ports = {int(p) for p in ctx.config.dictionary("dangerous_ports") if isinstance(p, (int, float))}
    allowed = _networks(ctx.config.dictionary("internal_networks"))
    allowed.extend(_networks([str(n) for n in ctx.config.sub_setting("network", {}).get("allowed_networks") or []]))

    evidence: list[Evidence] = []
    if mode == "blocked":
        # 黑名单主机即使不带 scheme（curl elearning/x、ping 22.122.49.168）也要拦，
        # 所以先对原始文本直接做黑名单匹配，再走逐个候选地址的精确分类。
        for pattern in blocked_hosts:
            for _label, text in ctx.texts:
                found = pattern.regex.search(text)
                if found is not None:
                    evidence.append(Evidence(pattern.label, snippet_of(text, found.start(), found.end()), "text"))
                    break
            if evidence:
                break
    for raw in values:
        host, port = split_host_port(raw)
        if not host:
            continue
        if mode == "blocked":
            if port is not None and port in dangerous_ports:
                evidence.append(Evidence(f"危险端口 {port}", raw, "url"))
                continue
            for pattern in blocked_hosts:
                if pattern.regex.search(host):
                    evidence.append(Evidence(pattern.label, raw, "url"))
                    break
        elif mode == "default":
            address = _as_ip(host)
            in_network = address is not None and any(address.version == n.version and address in n for n in allowed)
            if not in_network:
                evidence.append(Evidence("非白名单地址", raw, "url"))
    return evidence


def _detect_mcp_server(ctx: ScanContext) -> list[Evidence]:
    allowed = [str(s) for s in ctx.config.sub_setting("mcp", {}).get("allowed_servers") or []]
    if not allowed:
        return []
    candidates = {
        str(ctx.args.get("server") or ""),
        str(ctx.args.get("server_name") or ""),
        ctx.tool_name.split("_", 1)[0] if ctx.tool_name else "",
        ctx.tool_name,
    }
    candidates.discard("")
    for name in candidates:
        for entry in allowed:
            if name == entry or name.startswith(entry + "_") or name.endswith("_" + entry):
                return []
    return [Evidence("MCP Server 不在白名单", ctx.tool_name or "<unknown>", "tool.name")]


def _detect_mcp_args_schema(ctx: ScanContext) -> list[Evidence]:
    """MCP 入参的基本结构校验（完整 JSON Schema 校验需要 MCP 服务端配合）。"""
    if not isinstance(ctx.args, dict):
        return [Evidence("入参不是对象", type(ctx.args).__name__, "args")]
    evidence: list[Evidence] = []
    limit = 100000
    for key, value in ctx.args.items():
        text = _stringify(value, 200000)
        if not isinstance(key, str) or not key:
            evidence.append(Evidence("参数名非法", repr(key), "args"))
            continue
        if len(text) > limit:
            evidence.append(Evidence("参数过长", f"{key}（{len(text)} 字符）", "args"))
        elif _CONTROL_CHARS.search(text):
            evidence.append(Evidence("参数含控制字符", key, "args"))
    return evidence


def _detect_caller_context(ctx: ScanContext) -> list[Evidence]:
    mcp = ctx.config.sub_setting("mcp", {})
    allowed_profiles = [str(p) for p in mcp.get("allowed_profiles") or []]
    if allowed_profiles and ctx.profile not in allowed_profiles:
        return [Evidence("调用方 Profile 不在白名单", ctx.profile or "<empty>", "profile")]
    allowed_workspaces = [str(w) for w in mcp.get("allowed_workspaces") or []]
    if allowed_workspaces:
        workspace = _resolve_workspace(ctx.cwd)
        roots = [_resolve_workspace("", w) for w in allowed_workspaces]
        if workspace is None or not any(r is not None and _is_within(workspace, r) for r in roots):
            return [Evidence("调用方工作目录不在白名单", ctx.cwd or "<empty>", "cwd")]
    return []


def _detect_rule_refs(detector: dict[str, Any], ctx: ScanContext, depth: int) -> list[Evidence]:
    evidence: list[Evidence] = []
    for rule_id in detector.get("rules") or []:
        rule = ctx.config.rule(str(rule_id))
        if rule is None:
            raise GuardError(f"rule_refs 引用了不存在的规则：{rule_id}")
        for item in _run_detectors(rule.get("detect") or [], ctx, depth + 1):
            evidence.append(Evidence(f"{rule_id} {item.label}", item.snippet, item.source))
            if len(evidence) >= 6:
                return evidence
    return evidence


def _run_detectors(detectors: list[Any], ctx: ScanContext, depth: int = 0) -> list[Evidence]:
    evidence: list[Evidence] = []
    if depth > MAX_RULE_REFS_DEPTH:
        raise GuardError("rule_refs 递归过深")
    for detector in detectors:
        if not isinstance(detector, dict):
            continue
        kind = str(detector.get("type") or "")
        if kind == "keyword":
            found = _detect_patterns(ctx.config, detector, ctx, mode="literal")
        elif kind == "path":
            found = _detect_patterns(ctx.config, detector, ctx, mode="plain")
        elif kind in ("regex", "secret"):
            found = _detect_patterns(ctx.config, detector, ctx, mode="regex")
        elif kind == "ip_cidr":
            found = _detect_ip_cidr(ctx.config, detector, ctx)
        elif kind == "extension":
            found = _detect_extension(ctx.config, detector, ctx)
        elif kind == "write_scope":
            found = _detect_write_scope(ctx)
        elif kind == "url":
            found = _detect_url(ctx, str(detector.get("mode") or "blocked"))
        elif kind == "mcp_server":
            found = _detect_mcp_server(ctx)
        elif kind == "mcp_args_schema":
            found = _detect_mcp_args_schema(ctx)
        elif kind == "caller_context":
            found = _detect_caller_context(ctx)
        elif kind == "rule_refs":
            found = _detect_rule_refs(detector, ctx, depth)
        else:
            raise GuardError(f"未知检测器类型：{kind!r}")
        evidence.extend(found)
        if evidence:
            return evidence
    return evidence


# ---------------------------------------------------------------------------
# 规则求值
# ---------------------------------------------------------------------------


def _rule_enabled(rule: dict[str, Any]) -> bool:
    return bool(rule.get("enabled", True))


def _applies_to(rule: dict[str, Any], ctx: ScanContext) -> bool:
    applies = rule.get("applies_to")
    if not isinstance(applies, dict):
        return True
    kinds = applies.get("kinds")
    if isinstance(kinds, list) and kinds and ctx.kind not in {str(k) for k in kinds}:
        return False
    names = applies.get("tool_names")
    return not (isinstance(names, list) and names and ctx.tool_name not in {str(n) for n in names})


def effective_disposition(rule: dict[str, Any], config: GuardConfig) -> str:
    """把规则里的 ``block`` / ``confirm`` 映射成实际处置。

    ``settings.confirm_disposition`` 是全局开关：默认 ``block``，表里的
    ``confirm`` 一律打断并提示；改成 ``notify`` 则 confirm 类规则只留痕、
    提示词层额外给模型一条 ``system_reminder``。
    """
    disposition = str(rule.get("disposition") or "confirm").lower()
    if disposition != "confirm":
        return disposition
    return "block" if str(config.setting("confirm_disposition", "block")) == "block" else "notify"


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() > deadline:
        raise DeadlineExceeded("超过 settings.self_timeout_seconds")


def evaluate_rules(
    rules: list[dict[str, Any]],
    ctx: ScanContext,
    *,
    deadline: float | None,
) -> list[Hit]:
    """顺序跑规则，返回全部命中（按规则表顺序）。"""
    hits: list[Hit] = []
    for rule in rules:
        _check_deadline(deadline)
        if not _rule_enabled(rule) or not _applies_to(rule, ctx):
            continue
        evidence = _run_detectors(rule.get("detect") or [], ctx)
        if evidence:
            hits.append(Hit(rule, effective_disposition(rule, ctx.config), evidence))
    return hits


def evaluate_prompt(config: GuardConfig, text: str, *, deadline: float | None = None) -> list[Hit]:
    """提示词层：拿用户输入跑 ``prompt_rules``。"""
    ctx = ScanContext(config=config, texts=[("text", text[: config.max_scan_chars])], args={}, payload={})
    return evaluate_rules(config.prompt_rules, ctx, deadline=deadline)


def evaluate_tool_call(config: GuardConfig, payload: dict[str, Any], *, deadline: float | None = None) -> list[Hit]:
    """工具调用层：拿工具入参跑 ``tool_rules``。"""
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        tool = {}
    raw_args = tool.get("args")
    if not isinstance(raw_args, dict):
        raw_args = {}
    ctx = ScanContext(config=config, texts=[], args=dict(raw_args), payload=payload)
    hits: list[Hit] = []
    for rule in config.tool_rules:
        _check_deadline(deadline)
        if not _rule_enabled(rule) or not _applies_to(rule, ctx):
            continue
        applies = rule.get("applies_to")
        arg_keys = applies.get("arg_keys") if isinstance(applies, dict) else None
        ctx.texts = collect_texts(dict(raw_args), arg_keys, config.max_scan_chars)
        evidence = _run_detectors(rule.get("detect") or [], ctx)
        if evidence:
            hits.append(Hit(rule, effective_disposition(rule, ctx.config), evidence))
    return hits


# ---------------------------------------------------------------------------
# 用户提示与留痕
# ---------------------------------------------------------------------------

DEFAULT_BLOCK_MESSAGE = "操作不合规，请修改后重试。"


def format_message(config: GuardConfig) -> str:
    """生成给用户看的拦截提示。

    刻意只有一句：用户界面不需要知道命中了哪几条规则、证据是什么——那些明细
    完整写在留痕文件里，需要排查时看那里。文案可用 ``settings.block_message``
    改，不必动代码。
    """
    return str(config.setting("block_message") or DEFAULT_BLOCK_MESSAGE)


def audit_path(config: GuardConfig) -> Path:
    """留痕文件路径。"""
    override = os.environ.get(AUDIT_PATH_ENV)
    if override:
        return Path(override)
    return Path(expand(str(config.setting("audit_log", "${chrys_home}/hooks/guard_audit.jsonl"))))


def audit_records(layer: str, hits: list[Hit], payload: dict[str, Any], *, action: str) -> list[dict[str, Any]]:
    """构造留痕记录。"""
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        tool = {}
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return [
        {
            "ts": stamp,
            "layer": layer,
            "hook_id": os.environ.get("CHRYS_HOOK_ID", ""),
            "session_id": payload.get("session_id", ""),
            "profile": payload.get("profile", ""),
            "cwd": payload.get("cwd", ""),
            "tool": {"name": tool.get("name", ""), "kind": tool.get("kind", "")},
            "action": action,
            "rules": [hit.to_json() for hit in hits],
        }
    ]


def write_audit(records: list[dict[str, Any]], config: GuardConfig) -> None:
    """追加留痕；写不进去也不能影响拦截本身。"""
    path = audit_path(config)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError as exc:
        _log(f"留痕写入失败（{path}）：{exc}")


# ---------------------------------------------------------------------------
# 子进程协议
# ---------------------------------------------------------------------------


def read_payload() -> dict[str, Any]:
    """读取 ``$CHRYS_HOOK_PAYLOAD_FILE``。"""
    path = os.environ.get("CHRYS_HOOK_PAYLOAD_FILE")
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def write_decision(decision: dict[str, Any]) -> bool:
    """写入 ``$CHRYS_HOOK_RESULT``；返回是否成功。"""
    path = os.environ.get("CHRYS_HOOK_RESULT")
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(decision, handle, ensure_ascii=False)
    except OSError as exc:
        _log(f"决策写入失败（{path}）：{exc}")
        return False
    return True


def _log(message: str) -> None:
    sys.stderr.write(f"[guard] {message}\n")


def _fail_closed(config: GuardConfig | None, layer: str, detail: str) -> int:
    """IN-09 失败兜底：引擎自身异常时按 fail_closed 决定打断还是放行。"""
    fail_closed = True if config is None else config.fail_closed
    _log(f"{layer} 引擎异常：{detail}")
    if fail_closed:
        message = f"{DEFAULT_BLOCK_MESSAGE}\n（原因：策略引擎异常，{detail[:150]}）"
        if write_decision({"action": "block", "reason": message}):
            return 0
        # 连决策文件都写不进去时用非零退出码，让 on_error: block 兜住。
        return 1
    return 0


def run_hook(layer: str) -> int:
    """两个入口脚本共用的主流程。

    返回进程退出码：正常路径恒为 ``0``（放行或写好决策）；只有在决策都写不
    出来时才返回非零，交给 ``hooks.yaml`` 的 ``on_error: block`` 兜底。
    """
    started = time.monotonic()
    config: GuardConfig | None = None
    payload: dict[str, Any] = {}
    try:
        payload = read_payload()
        config = load_config()
        if not config.setting("enabled", True):
            return 0
        deadline = started + config.self_timeout_seconds
        if layer == "prompt":
            hits = evaluate_prompt(config, str(payload.get("text") or ""), deadline=deadline)
        else:
            hits = evaluate_tool_call(config, payload, deadline=deadline)

        if not hits:
            if config.setting("audit_on_allow", False):
                write_audit(audit_records(layer, [], payload, action="allow"), config)
            return 0

        blocking = [h for h in hits if h.disposition == "block"]
        write_audit(audit_records(layer, hits, payload, action="block" if blocking else "notify"), config)
        if not blocking:
            # confirm_disposition=notify：提示词层把命中规则告诉模型让它自己调整，
            # 工具层只留痕。system_reminder 不直接展示给用户，所以带上规则 ID。
            if layer == "prompt":
                ids = ", ".join(hit.rule_id for hit in hits)
                write_decision({"system_reminder": f"[安全策略] {DEFAULT_BLOCK_MESSAGE}命中规则：{ids}"})
            return 0
        write_decision({"action": "block", "reason": format_message(config)})
        return 0
    except (DeadlineExceeded, GuardError) as exc:
        return _fail_closed(config, _layer_title(layer), str(exc))
    except Exception as exc:
        return _fail_closed(config, _layer_title(layer), f"{type(exc).__name__}: {exc}")


def _layer_title(layer: str) -> str:
    return "提示词层" if layer == "prompt" else "工具调用前"


if __name__ == "__main__":  # pragma: no cover - 手工冒烟入口
    raise SystemExit(run_hook(sys.argv[1] if len(sys.argv) > 1 else "tool"))
