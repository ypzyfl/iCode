# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Gateway model-queue support for the Chat Completions wire client.

Wired from ``chrys.service.llm.chat_completions.client`` (the single upstream
contact point, registered as ``model-queue-client:queue-frame-guard`` and
``model-queue-client:queue-cancel``).
Design: ``aixcoding/docs/batches/model-queue-client/design.md``.
"""

from chrys.service.aixcoding.llm_queue.queue_cancel import (
    QueueRequestTracker,
    cancel_endpoint,
    close_stream_and_cancel,
    track_queue_request,
    wire_queue_callback,
)
from chrys.service.aixcoding.llm_queue.queue_frames import (
    RELEASED_POSITION,
    TERMINAL_QUEUE_CODES,
    QueueStatus,
    guard_queue_frames,
    queue_position,
    terminal_queue_rejection,
)

__all__ = [
    "RELEASED_POSITION",
    "TERMINAL_QUEUE_CODES",
    "QueueRequestTracker",
    "QueueStatus",
    "cancel_endpoint",
    "close_stream_and_cancel",
    "guard_queue_frames",
    "queue_position",
    "terminal_queue_rejection",
    "track_queue_request",
    "wire_queue_callback",
]
