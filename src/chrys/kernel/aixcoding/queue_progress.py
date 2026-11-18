# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Status copy for a gateway queue position, shared by every frontend.

Customization-facing prose stays a plain Chinese constant rather than an i18n
catalog entry (ADR-0010). The TUI and the CLI render it; the ACP path forwards
only the raw position, so a client draws its own text. It depends on nothing,
so it sits in the kernel tier (ADR-0011). Punctuation is deliberately not
full-width: this file is outside the registered RUF001 exemption paths, and a
new lint exemption costs more than a middle dot.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md``.
"""

from __future__ import annotations


def queue_note(position: int) -> str:
    """The status text for *position* requests ahead; ``0`` means this request is next.

    Kept short on purpose: the TUI renders it on one line beside the waiting
    dot, and the CLI writes it as a single appended line.
    """
    if position < 0:
        return ""
    if position == 0:
        return "正在获取模型资源"
    if position <= 3:
        return f"排队中 · 前方 {position} 个请求"
    return f"排队中 · 前方 {position} 个请求 · 可稍后重试"
