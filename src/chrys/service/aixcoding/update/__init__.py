# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Release-check client and persisted state for the AIxCoding auto-update flow.

``client`` talks to the frozen ``releases/check`` contract (see
``aixcoding/mock/update/`` for the wire protocol and its fault drills);
``state`` owns the daily check cache and the two failure-bookkeeping files
the detached update wrapper cooperates with.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from chrys.service.aixcoding.update.client import (
    AppUpdate,
    check_for_update,
    check_url,
    resolve_check_base,
)
from chrys.service.aixcoding.update.state import (
    UpdateState,
    create_skip_today,
    drop_failure_tally,
    drop_skip_today,
    read_failure_tally,
    read_state,
    skip_today_active,
    write_state,
)

__all__ = [
    "AppUpdate",
    "UpdateState",
    "check_for_update",
    "check_url",
    "create_skip_today",
    "drop_failure_tally",
    "drop_skip_today",
    "read_failure_tally",
    "read_state",
    "resolve_check_base",
    "skip_today_active",
    "write_state",
]
