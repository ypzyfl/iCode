"""AIxCoding customization layer (product code).

Everything here ships in the wheel via ``packages = ["src/chrys"]``. Dev-only
assets live in the repo-root ``aixcoding/`` directory instead. Layering rules
(DEVELOPMENT.md R9): depend on ``chrys.foundation`` / ``chrys.kernel`` only,
except for explicitly registered entry-point adapters (see
``aixcoding/docs/diagnostics/design.md``).
"""
