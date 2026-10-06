# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""AIxCoding session telemetry collector (one-shot CLI, fork-local).

Python port of the agent_studio_new TS collector ( behavioural baseline,
``eb1ce5f0``): locate the session file, read the revision, analyse, report,
advance the idempotency ledger. Spawned per hook firing as a short-lived
subprocess via ``python -m chrys.aixcoding.telemetry.collector``; see
agent_studio_new ``docs/adr/0041-chrys-session-collection.md`` (rev.5).
"""
