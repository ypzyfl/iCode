from __future__ import annotations

from pathlib import Path

from aixcoding.tools import docs_report as dr


def make_docs(file_tree, files: dict[str, str]) -> Path:
    repo = file_tree(files)
    return repo / "aixcoding" / "docs"


def test_discovers_every_batch_directory_in_sorted_order(file_tree, capsys):
    docs = make_docs(
        file_tree,
        {
            "aixcoding/docs/batches/zeta/plan.md": "# Zeta 计划\n",
            "aixcoding/docs/batches/alpha/design.md": "# Alpha 设计\n",
            "aixcoding/docs/batches/beta/requirements.md": "# Beta 需求\n",
        },
    )
    assert dr.run_report(docs) == 0
    captured = capsys.readouterr()
    assert "批次目录全景" in captured.out
    assert captured.out.index("[alpha]") < captured.out.index("[beta]") < captured.out.index("[zeta]")
    assert "3 batch directories" in captured.out
    assert captured.err == ""


def test_title_fallback_and_plan_only_legacy_directory(file_tree, capsys):
    docs = make_docs(
        file_tree,
        {
            "aixcoding/docs/batches/plan-only/plan.md": "# 仅有计划\n",
            "aixcoding/docs/batches/design-first/design.md": "# 设计优先\n",
            "aixcoding/docs/batches/design-first/plan.md": "# 不应采用\n",
            "aixcoding/docs/batches/requirements-first/requirements.md": "# 需求优先\n",
            "aixcoding/docs/batches/requirements-first/design.md": "# 不应采用\n",
        },
    )
    assert dr.run_report(docs) == 0
    out = capsys.readouterr().out
    assert "仅有计划" in out
    assert "设计优先" in out
    assert "需求优先" in out
    assert "不应采用" not in out


def test_non_batch_micro_records_are_out_of_scope(file_tree, capsys):
    docs = make_docs(
        file_tree,
        {
            "aixcoding/docs/batches/demo/plan.md": "# 批次\n",
            "aixcoding/docs/micro/tiny/plan.md": "# 无目录微改动\n",
            "aixcoding/docs/other/plan.md": "# 其他记录\n",
        },
    )
    assert dr.run_report(docs) == 0
    captured = capsys.readouterr()
    assert "demo" in captured.out
    assert "无目录微改动" not in captured.out
    assert "其他记录" not in captured.out
    assert "微改动" not in captured.out


def test_output_is_deterministic_and_writes_nothing(file_tree, capsys):
    docs = make_docs(file_tree, {"aixcoding/docs/batches/demo/plan.md": "# 批次\n\n正文\n"})
    repo = docs.parents[1]

    def snapshot() -> dict[str, bytes]:
        return {
            path.relative_to(repo).as_posix(): path.read_bytes() for path in sorted(repo.rglob("*")) if path.is_file()
        }

    before = snapshot()
    assert dr.run_report(docs) == 0
    first = capsys.readouterr()
    assert dr.run_report(docs) == 0
    second = capsys.readouterr()
    assert first.out == second.out
    assert first.err == second.err == ""
    assert snapshot() == before


def test_missing_sources_h1_and_non_utf8_fail_loudly(file_tree, capsys):
    docs = make_docs(
        file_tree,
        {
            "aixcoding/docs/batches/no-sources/verification.md": "# 验证\n",
            "aixcoding/docs/batches/no-h1/requirements.md": "正文，没有标题\n",
            "aixcoding/docs/batches/no-h1/design.md": "# 可回退标题\n",
            "aixcoding/docs/batches/bad-utf8/plan.md": "# 先占位\n",
        },
    )
    (docs / "batches/bad-utf8/plan.md").write_bytes(b"\xff\xfe")
    assert dr.run_report(docs) == 1
    captured = capsys.readouterr()
    assert "no usable title" in captured.err
    assert "no non-empty H1" in captured.err
    assert "unreadable" in captured.err
    assert "可回退标题" in captured.out


def test_missing_batches_root_and_cli_exit_code(file_tree, capsys, monkeypatch):
    docs = make_docs(file_tree, {"aixcoding/docs/other/plan.md": "# 其他\n"})
    monkeypatch.setattr(dr, "DOCS_ROOT", docs)
    assert dr.main() == 1
    assert "batches directory is missing" in capsys.readouterr().err
