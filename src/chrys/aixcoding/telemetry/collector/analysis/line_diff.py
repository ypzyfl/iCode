# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Line-level diff (Myers O(ND); TS ``line-diff.ts``; M5 plan §6.1 line
counting and §6.3 blocks).

Ops are per-line over before/after ('-' deletes a before line, '+'
inserts an after line, '=' is shared), in merged order from both
sequence starts to the ends. Counts (added/deleted) are derived by the
caller. Past the safety caps (total lines / edit distance) returns None —
callers degrade by omitting, never blocking events.

Ported from the TS Myers implementation instead of ``difflib``:
``difflib`` is heuristic (not a minimal edit script), so its op sequence
and added/deleted counts can diverge from the TS golden reference and
break equivalence verification.
"""

from __future__ import annotations

MAX_TOTAL_LINES = 20_000
MAX_EDIT_DISTANCE = 2_000

LineDiffOp = str  # "+" | "-" | "="


def compute_line_diff(before: list[str], after: list[str]) -> list[LineDiffOp] | None:
    n = len(before)
    m = len(after)
    if n + m == 0:
        return []
    if n + m > MAX_TOTAL_LINES:
        return None
    size = n + m
    offset = size
    v = [0] * (2 * size + 1)
    trace: list[list[int]] = []
    found_d = -1
    for d in range(size + 1):
        if d > MAX_EDIT_DISTANCE:
            return None
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v[offset + k - 1] < v[offset + k + 1]):
                x = v[offset + k + 1]
            else:
                x = v[offset + k - 1] + 1
            y = x - k
            while x < n and y < m and before[x] == after[y]:
                x += 1
                y += 1
            v[offset + k] = x
            if x >= n and y >= m:
                trace.append(v[:])
                found_d = d
                break
        if found_d >= 0:
            break
        trace.append(v[:])
    if found_d < 0:
        return None

    # Backtrack: retrace each edit step from (n, m) in reverse, collect
    # reversed, then flip. Reading prevX from trace[d] (not trace[d-1])
    # is safe: step d only updates diagonals of matching parity, so
    # prevK's entry still holds the d-1 value.
    ops: list[LineDiffOp] = []
    x = n
    y = m
    for d in range(len(trace) - 1, 0, -1):
        snapshot = trace[d]
        k = x - y
        prev_k = k + 1 if k == -d or (k != d and snapshot[offset + k - 1] < snapshot[offset + k + 1]) else k - 1
        prev_x = snapshot[offset + prev_k]
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:
            ops.append("=")
            x -= 1
            y -= 1
        if y == prev_y:
            ops.append("-")
            x -= 1
        else:
            ops.append("+")
            y -= 1
    while x > 0 and y > 0:
        ops.append("=")
        x -= 1
        y -= 1
    ops.reverse()
    return ops
