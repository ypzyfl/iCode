# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding customization at the service tier.

Service-layer features whose dependencies pin them above the kernel tier
(``chrys.kernel.aixcoding``) but which touch no upstream file beyond their
registered wiring points.  Current occupants: the shared
:mod:`chrys.service.aixcoding.config` snapshot, the server-owned model catalog
at :mod:`chrys.service.aixcoding.models.catalog` (see
``aixcoding/docs/batches/catalog-sync/design.md``), and
:mod:`chrys.service.aixcoding.skill_paths` (desktop-shared local skill roots;
see ``aixcoding/docs/batches/skills-aixcoding-dirs/design.md``).
"""
