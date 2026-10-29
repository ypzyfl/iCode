# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding customizations hosted by the app tier (ADR-0011 placement).

Modules here depend on ``chrys.app.tui`` infrastructure (BaseDialog, command
registry, header widgets), so the app tier is the lowest tier that can host
them; see aixcoding/docs/standards/adr/0011 for the placement rule.
"""
