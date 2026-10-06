# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Analysis core (Python port of the TS ``analysis/`` behavioural baseline).

Turn slicing, incremental computation and event projection over the engine's
session.json — defensive parsing per the Session guide §1.3 (missing/null/
0/empty stay distinct); never modifies input objects.
"""
