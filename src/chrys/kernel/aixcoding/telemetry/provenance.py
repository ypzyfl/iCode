# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Associate response contents and tool operation IDs in process memory."""

from __future__ import annotations

import time
import weakref
from collections import OrderedDict
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_LIMIT = 4096
_TTL = 1800
_content_sources: OrderedDict[int, tuple[weakref.ReferenceType[object], str]] = OrderedDict()
_operation_sources: OrderedDict[str, tuple[str, float]] = OrderedDict()


class ResponseContent(Protocol):
    @property
    def type(self) -> str: ...
    @property
    def informational_only(self) -> bool: ...
    @property
    def provider_hosted(self) -> bool: ...


class ResponseMessage(Protocol):
    @property
    def contents(self) -> Sequence[ResponseContent]: ...


class ModelResponse(Protocol):
    @property
    def messages(self) -> Sequence[ResponseMessage]: ...


def _remember(content: object, source_id: str) -> None:
    key = id(content)
    current = _content_sources.get(key)
    if current is not None and current[0]() is content:
        return

    def remove(ref: weakref.ReferenceType[object]) -> None:
        row = _content_sources.get(key)
        if row is not None and row[0] is ref:
            del _content_sources[key]

    _content_sources[key] = (weakref.ref(content, remove), source_id)
    _content_sources.move_to_end(key)
    if len(_content_sources) > _LIMIT:
        _content_sources.popitem(last=False)


def _lookup(content: object | None) -> str | None:
    if content is None:
        return None
    row = _content_sources.get(id(content))
    return row[1] if row is not None and row[0]() is content else None


def remember_local_source(response: ModelResponse, source_id: str) -> None:
    for message in response.messages:
        for content in message.contents:
            if content.type == "function_call" and not content.informational_only and not content.provider_hosted:
                _remember(content, source_id)


def remember_hosted_source(contents: Iterable[ResponseContent], source_id: str) -> None:
    for content in contents:
        if content.provider_hosted:
            _remember(content, source_id)


def hosted_source(call: object | None, result: object | None) -> str | None:
    return _lookup(result) or _lookup(call)


def bind_tool_operation_source(content: object, operation_id: str) -> None:
    source = _lookup(content)
    if source is None:
        return
    _operation_sources[operation_id] = (source, time.monotonic() + _TTL)
    _operation_sources.move_to_end(operation_id)
    if len(_operation_sources) > _LIMIT:
        _operation_sources.popitem(last=False)


def operation_source(operation_id: str | None) -> str | None:
    if operation_id is None:
        return None
    row = _operation_sources.pop(operation_id, None)
    return row[0] if row is not None and row[1] > time.monotonic() else None
