# ruff: noqa: RUF002, RUF003
"""TUI 版本更新检测：启动后台单发 GET，全吞错、不阻塞主流程。

检测端点 ``GET {base_url}/api/v2/releases/check``：四个必填查询参数（严格模式，
未知参数 400）。客户端只做两件事——映射参数、解析 200 响应中的 ``version`` 与
``artifact.url``；版本比较完全在服务端闭环
（200=有适用新版本 / 204=无 / 304=ETag 兜底 / 其他=检测失败）。manifest v2
新增字段（``releaseNotes`` / ``forceUpgrade`` 等）一律不消费。

命名说明：本模块与类型统一采用 update（检测更新）语义，不复用服务端
``/releases`` 契约命名（``AppReleaseManifestV2`` 等），避免"发布版本"误读；
服务端字段名仅在引用契约原文时出现。

检测为一次性单发（无重试、不持久化 etag、无冷却），任何失败静默返回
``None``——调用方（TUI ``on_mount`` 后台任务）不打扰会话启动。
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from chrys import __version__
from chrys.aixcoding.config import load_settings
from chrys.foundation.platform import get_platform

logger = logging.getLogger(__name__)

RELEASE_CHECK_URL_PATH = "api/v2/releases/check"
_TIMEOUT_SECONDS = 15.0

# clientType：TUI 属 CLI 形态，固定上送 cli（桌面端另有 desktop）。
_CLIENT_TYPE = "cli"

# platform 域：sys.platform 原值即合法（定稿契约 win64 已并入 win32，位数由
# architecture 区分），域外（如 freebsd）跳过检测。
_PLATFORMS = ("win32", "darwin", "linux")

# 架构映射：PlatformInfo.arch 内部命名是 ``amd64``（不是 x64）；
# x86 作为 32 位兜底映射为 x64（服务端按不匹配回 204）；域外跳过检测。
_ARCH_MAP = {"arm64": "arm64", "amd64": "x64", "x86": "x64"}

# currentVersion 严格校验：1–64 字符、MAJOR.MINOR.PATCH[-PRERELEASE]。
# 正式版与 dev 构建（-dev-{sha}）均合法、正常上送，无特判；校验失败一律静默跳过。
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")
_VERSION_MIN_LENGTH, _VERSION_MAX_LENGTH = 1, 64

# debug 日志中响应体的截断长度：失败诊断够用（含代理错误页），又不至于刷屏。
_BODY_LOG_LIMIT = 2000


@dataclass(frozen=True)
class AppUpdate:
    """一次成功的检测结果：候选版本号与下载页地址（均来自服务端下发）。"""

    version: str  # 服务端下发的候选版本号，如 "0.29.0"
    download_url: str  # 服务端下发的下载页地址（点击徽章跳转用）


def _is_strict_semver(version: str) -> bool:
    return _VERSION_MIN_LENGTH <= len(version) <= _VERSION_MAX_LENGTH and _SEMVER_RE.fullmatch(version) is not None


def build_query_params() -> dict[str, str] | None:
    """构造四个必填查询参数；版本号或架构不可用（无法映射）时返回 None（跳过检测）。"""
    if sys.platform not in _PLATFORMS:
        return None
    arch = _ARCH_MAP.get(get_platform().arch)
    if arch is None:
        return None
    if not _is_strict_semver(__version__):
        return None
    return {
        "clientType": _CLIENT_TYPE,
        "platform": sys.platform,
        "architecture": arch,
        "currentVersion": __version__,
    }


def _request_headers() -> dict[str, str]:
    """请求头挂点：契约未要求鉴权；服务端如加 token 头，只改这里。"""
    return {}


def _body_preview(response: httpx.Response) -> str:
    """响应体文本预览（失败诊断用），超长截断，避免大 body 刷屏。"""
    text = response.text if response.content else ""
    if len(text) > _BODY_LOG_LIMIT:
        text = f"{text[:_BODY_LOG_LIMIT]}...(truncated, total {len(text)} chars)"
    return text


def _parse_response(response: httpx.Response) -> AppUpdate | None:
    """响应处理：200 取 version + artifact.url；204/304 无更新；其余静默失败。"""
    if response.status_code == 200:
        try:
            payload = response.json()
            version = payload["version"]
            download_url = payload["artifact"]["url"]
        except Exception as exc:
            logger.debug(
                "update check: unparseable manifest body: %s: %s (body=%s)",
                type(exc).__name__,
                exc,
                _body_preview(response),
            )
            return None
        if isinstance(version, str) and version and isinstance(download_url, str) and download_url:
            return AppUpdate(version=version, download_url=download_url)
        logger.debug("update check: manifest missing version/artifact.url (body=%s)", _body_preview(response))
        return None
    if response.status_code in (204, 304):
        return None  # 已最新 / 平台不匹配 / 灰度未命中 / ETag 兜底
    logger.debug("update check: unexpected status %s (body=%s)", response.status_code, _body_preview(response))
    return None


async def check_for_update() -> AppUpdate | None:
    """单次 GET 检测。任何失败（网络/状态码/解析）返回 None，绝不抛出。

    - URL 复用 ``load_settings().base_url``（含 ``/csas`` 前缀，环境变量可整体覆盖）；
    - ``trust_env=False`` 对齐 ``aixcoding/http.py``：内网端点直连，不受本机代理
      环境变量干扰；
    - 不发送 ``If-None-Match``：每次启动均为新进程，不持久化 etag。
    """
    params = build_query_params()
    if params is None:
        logger.debug("update check skipped: unbuildable query params")
        return None
    url = f"{load_settings().base_url.rstrip('/')}/{RELEASE_CHECK_URL_PATH}"
    try:
        # asyncio.timeout 兜住 httpx 分阶段超时（connect/read/write/pool 各 15s）
        # 的总耗时上界，保证"超时≤15s"不变量；超时被下面的 except 吞掉并记
        # debug 日志，语义不变。
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, trust_env=False) as client:
                request = client.build_request("GET", url, params=params, headers=_request_headers())
                # 完整请求观测：方法 + 含查询串的最终 wire URL + 实际上线请求头
                # （含 httpx 注入的默认头），逐字段多行展示，可对账。
                logger.debug(
                    "update check: sending request\n  method: %s\n  url: %s\n  headers: %s\n  timeout: %gs",
                    request.method,
                    request.url,
                    dict(request.headers),
                    _TIMEOUT_SECONDS,
                )
                response = await client.send(request)
    except httpx.TimeoutException, TimeoutError:
        # httpx 分阶段超时与 asyncio 总上界触发，对客户端是同一件事：超时。
        logger.debug("update check: timed out after %gs (GET %s?%s)", _TIMEOUT_SECONDS, url, urlencode(params))
        return None
    except Exception as exc:
        # 连接拒绝 / DNS 失败等网络错误：给一行异常摘要即可定位，不甩 traceback。
        # 此分支可能来自 build_request 本身（如 base_url 非法），request 未必绑定，
        # 故用 url+urlencode 重建完整地址。
        logger.debug(
            "update check: request failed: %s: %s (GET %s?%s)",
            type(exc).__name__,
            exc,
            url,
            urlencode(params),
        )
        return None
    logger.debug(
        "update check: got response\n  status: %s\n  elapsed: %gs\n  body: %s",
        response.status_code,
        response.elapsed.total_seconds(),
        _body_preview(response),
    )
    return _parse_response(response)
