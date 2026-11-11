# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""The AIxCoding auto-update flow: confirm dialog, exit-update-relaunch runner.

``flow`` wires the whole startup path (gate → D2 failure gates → cached
verdict → daily check); ``dialog`` is the confirmation modal; ``runner`` is
the detached exit-update-relaunch wrapper; ``commands`` derives the internal
install command from the release-check base.

Design: aixcoding/docs/batches/auto-update/design.md
"""

from chrys.app.aixcoding.update.flow import start_internal_update_flow

__all__ = ["start_internal_update_flow"]
