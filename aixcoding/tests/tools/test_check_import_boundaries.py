# ruff: noqa: S101, RUF002
# (tests — asserts are pytest idiom, Chinese prose is the data)
"""Unit tests for aixcoding/tools/check_import_boundaries.py (rules B1–B4)."""

from __future__ import annotations

from pathlib import Path

from aixcoding.tools import check_import_boundaries as cib

RULES = {"B1", "B2", "B3", "B4"}


def check(tmp_path: Path, rel: str, code: str) -> list[cib.Violation]:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, encoding="utf-8")
    return cib.check_file(rel, p)


def test_b1_root_aixcoding_imports_upstream_tests(tmp_path):
    v = check(
        tmp_path,
        "aixcoding/tests/test_x.py",
        "import tests.support.ci\n",
    )
    assert v and v[0].rule == "B1" and v[0].lineno == 1


def test_b1_from_form_also_caught(tmp_path):
    v = check(tmp_path, "aixcoding/mock/util.py", "from tests.support import ci\n")
    assert v and v[0].rule == "B1"


def test_b2_upstream_imports_root_namespace(tmp_path):
    v = check(tmp_path, "src/chrys/app/foo.py", "import aixcoding.mock.catalog\n")
    assert v and v[0].rule == "B2"


def test_b2_not_triggered_inside_chrys_aixcoding(tmp_path):
    v = check(tmp_path, "src/chrys/aixcoding/adapter.py", "import aixcoding.mock.catalog\n")
    assert v and v[0].rule == "B3"  # B3 scope, not B2


def test_b3_custom_product_imports_tests(tmp_path):
    v = check(tmp_path, "src/chrys/aixcoding/telemetry.py", "from tests.support import ci\n")
    assert v and v[0].rule == "B3"


def test_b4_mock_imports_product_package(tmp_path):
    v = check(tmp_path, "aixcoding/mock/catalog/server.py", "import chrys.foundation.http\n")
    assert v and v[0].rule == "B4"


def test_b4_mock_imports_third_party(tmp_path):
    v = check(tmp_path, "aixcoding/mock/auth/server.py", "import flask\n")
    assert v and v[0].rule == "B4"


def test_b4_mock_relative_import_escapes_package(tmp_path):
    # aixcoding/mock/x.py: '..' reaches the aixcoding root package
    v = check(tmp_path, "aixcoding/mock/x.py", "from ..tools import _common\n")
    assert v and v[0].rule == "B4" and "escapes" in v[0].detail


def test_b4_mock_relative_within_package_ok(tmp_path):
    assert check(tmp_path, "aixcoding/mock/x.py", "from . import peer\n") == []


def test_clean_files_pass(tmp_path):
    files = {
        "aixcoding/tests/tools/test_ok.py": (
            "import os\nimport pytest\nfrom aixcoding.tools import _common\nfrom aixcoding.mock import catalog\n"
        ),
        "aixcoding/tools/ok.py": "import ast\nimport subprocess\n",
        "aixcoding/mock/svc.py": "import http.server\nfrom aixcoding.mock import peer\n",
        "src/chrys/app/up.py": "import asyncio\n",
        "src/chrys/aixcoding/mod.py": "from chrys.foundation import branding\n",
    }
    violations = []
    for rel, code in files.items():
        violations.extend(check(tmp_path, rel, code))
    assert violations == []


def test_syntax_error_reported_not_crashed(tmp_path):
    v = check(tmp_path, "aixcoding/broken.py", "def f(:\n")
    assert v and v[0].rule == "parse"


def test_only_rules_b1_to_b4_and_parse(tmp_path):
    v = check(tmp_path, "aixcoding/tests/t.py", "import tests.x\n")
    assert {x.rule for x in v} <= RULES | {"parse"}
