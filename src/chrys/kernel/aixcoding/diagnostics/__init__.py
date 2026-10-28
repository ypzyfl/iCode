"""Local diagnostics package: custom log sink, crash capture, env snapshot.

See aixcoding/docs/diagnostics/design.md (signed off 2026-10-25). Import
``logging_support`` for the always-on file sink; use
``python -m chrys.kernel.aixcoding.diagnostics.launcher`` for crash/snapshot hooks.
"""
