# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""提示词层拦截 Hook（``user_prompt_submit``）。

对应《拦截规则一览表》：反编译工具、攻击工具、路径穿越、内网资产、
合规类（强制留痕）与失败兜底。

命中后通过 ``$CHRYS_HOOK_RESULT`` 写 ``{"action": "block", "reason": ...}``
或 ``{"action": "ask", "reason": ...}``：block 以 ``hook_blocked`` 错误打断
本轮；ask 由引擎弹确认框，确认后发送，拒绝 / 无法询问时按 block 兜底。

用法见同目录 ``README.md``；规则与词典在 ``rules.json``。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _guard_core as guard  # ty: ignore[unresolved-import]  # copied beside this script at install time


def main() -> int:
    """评估用户提示词；返回进程退出码。"""
    return guard.run_hook("prompt")


if __name__ == "__main__":
    raise SystemExit(main())
