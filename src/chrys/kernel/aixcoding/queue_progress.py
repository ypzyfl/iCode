# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Status copy for a gateway queue position, shared by every frontend.

Customization-facing prose stays a plain Chinese constant rather than an i18n
catalog entry (ADR-0010). The TUI and the CLI render it; the ACP path forwards
only the raw position, so a client draws its own text. It depends on nothing,
so it sits in the kernel tier (ADR-0011). Punctuation stays half-width except
the queued copy's commas, which are the wording the owner asked for and carry
a line-level ``noqa: RUF001``.

Design: ``aixcoding/docs/batches/model-queue-progress/design.md``.
"""

from __future__ import annotations


def queue_note(position: int, queue_size: int = 0) -> str:
    """The status text for *position* requests ahead among *queue_size* waiting.

    ``position == 0`` means this request is next; a negative position means the
    queue released it (no note at all). ``queue_size`` is still accepted so the
    frontends keep one call shape, but the copy speaks about the position only:
    the total queue length is not shown.

    Kept on one line on purpose: the TUI renders it beside the waiting dot, and
    the CLI writes it as a single appended line.
    """
    if position < 0:
        return ""
    if position == 0:
        return "正在获取模型资源"
    # The full-width comma is the wording the owner asked for; the exemption stays line-level.
    return f"当前模型请求量大，请求排队约 {position} 人"  # noqa: RUF001
