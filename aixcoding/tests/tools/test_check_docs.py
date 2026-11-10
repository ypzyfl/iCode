# (tests — asserts are pytest idiom, Chinese prose is the data)
from __future__ import annotations

from pathlib import Path

from aixcoding.tools import check_docs as cd

SIGNED = "- 责任人：t\n- 状态：已确认\n- 确认日期：2026-11-10\n"
DRAFT = "- 责任人：t\n- 状态：草案\n- 确认日期：\n"


def batch_files(name: str = "demo", *, design_status: str = SIGNED) -> dict[str, str]:
    root = f"aixcoding/docs/batches/{name}"
    return {
        f"{root}/requirements.md": "# 需求\n\n正文\n",
        f"{root}/design.md": f"# 设计\n\n{design_status}\n## 方案\n\n正文\n",
        f"{root}/test-plan.md": "# 测试方案\n\n正文\n",
        f"{root}/plan.md": "# 任务清单\n\n正文\n",
        f"{root}/verification.md": "# 验证记录\n\n正文\n",
        f"{root}/self-review.md": f"# 自评审\n\n{SIGNED}\n## 结论\n\n正文\n",
    }


def make_docs(file_tree, extra: dict[str, str] | None = None, *, with_batch: bool = True) -> Path:
    files = {"aixcoding/docs/standards/closure-exemptions.toml": "[exemptions]\n"}
    if with_batch:
        files.update(batch_files())
    files.update(extra or {})
    repo = file_tree(files)
    return repo / "aixcoding" / "docs"


def adr_text(adr_id: str, *, status: str = SIGNED) -> str:
    return f"# {adr_id}：标题\n\n{status}\n## 决策\n\n正文\n"


def test_default_allows_draft_but_closure_rejects(file_tree):
    docs = make_docs(file_tree, with_batch=False)
    files = batch_files(design_status=DRAFT)
    repo = docs.parents[1]
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    assert cd.run_check(docs) == 0
    assert cd.run_check(docs, closure=True) == 1


def test_closure_requires_each_batch_file(file_tree):
    for missing in cd.REQUIRED_BATCH_FILES:
        files = batch_files()
        del files[f"aixcoding/docs/batches/demo/{missing}"]
        docs = make_docs(file_tree, files, with_batch=False)
        (docs / "batches/demo" / missing).unlink(missing_ok=True)
        assert cd.run_check(docs, closure=True) == 1, missing


def test_semantic_adr_filename_validation(file_tree):
    files = batch_files("alpha-beta")
    files["aixcoding/docs/standards/adr/alpha-beta--decision.md"] = adr_text("ADR-alpha-beta--decision")
    docs = make_docs(file_tree, files, with_batch=False)
    assert cd.run_check(docs) == 0
    path = docs / "standards/adr/alpha-beta--decision.md"
    path.write_text(adr_text("ADR-alpha-beta--other"), encoding="utf-8")
    assert cd.run_check(docs) == 1


def test_semantic_adr_batch_must_exist(file_tree):
    docs = make_docs(
        file_tree,
        {"aixcoding/docs/standards/adr/missing-batch--decision.md": adr_text("ADR-missing-batch--decision")},
    )
    assert cd.run_check(docs) == 1


def test_numeric_and_semantic_successors_remain_compatible(file_tree):
    files = batch_files("alpha-beta")
    files.update(
        {
            "aixcoding/docs/standards/adr/0001-old.md": adr_text(
                "ADR-0001", status="- 责任人：t\n- 状态：被取代（被 ADR-0002 取代）\n- 确认日期：\n"
            ),
            "aixcoding/docs/standards/adr/0002-next.md": adr_text(
                "ADR-0002", status="- 责任人：t\n- 状态：被取代（被 ADR-alpha-beta--decision 取代）\n- 确认日期：\n"
            ),
            "aixcoding/docs/standards/adr/alpha-beta--decision.md": adr_text("ADR-alpha-beta--decision"),
        }
    )
    docs = make_docs(file_tree, files, with_batch=False)
    assert cd.run_check(docs, closure=True) == 0


def test_adr_global_pool_and_location_validation(file_tree):
    docs = make_docs(
        file_tree,
        {"aixcoding/docs/batches/demo/adr/0001-old.md": adr_text("ADR-0001")},
    )
    assert cd.run_check(docs) == 1


def test_duplicate_adr_id_errors(file_tree):
    docs = make_docs(
        file_tree,
        {
            "aixcoding/docs/standards/adr/0001-a.md": adr_text("ADR-0001"),
            "aixcoding/docs/standards/adr/0001-b.md": adr_text("ADR-0001"),
        },
    )
    assert cd.run_check(docs) == 1


def test_adr_successor_error_injection(file_tree):
    docs = make_docs(
        file_tree,
        {
            "aixcoding/docs/standards/adr/0001-old.md": adr_text(
                "ADR-0001", status="- 责任人：t\n- 状态：被取代（被 ADR-9999 取代）\n- 确认日期：\n"
            )
        },
    )
    assert cd.run_check(docs) == 1


def test_adr_reference_must_exist_and_be_signed(file_tree):
    files = {"aixcoding/docs/standards/adr/0001-old.md": adr_text("ADR-0001", status=DRAFT)}
    design = "aixcoding/docs/batches/demo/design.md"
    base = batch_files()
    base[design] = base[design].replace("正文", "引用 ADR-0001")
    files.update(base)
    docs = make_docs(file_tree, files, with_batch=False)
    assert cd.run_check(docs) == 0
    assert cd.run_check(docs, closure=True) == 1
    (docs / "standards/adr/0001-old.md").write_text(adr_text("ADR-0001"), encoding="utf-8")
    assert cd.run_check(docs, closure=True) == 0
    (docs / "batches/demo/design.md").write_text(
        (docs / "batches/demo/design.md").read_text(encoding="utf-8").replace("ADR-0001", "ADR-demo--missing"),
        encoding="utf-8",
    )
    assert cd.run_check(docs, closure=True) == 1


def test_plan_completion_requires_minimal_files(file_tree):
    files = batch_files()
    files["aixcoding/docs/batches/demo/plan.md"] = (
        "# 任务\n\n| 任务 | 状态 |\n|---|---|\n| 验证：self-review/verification | 完成（已留痕） |\n"
    )
    docs = make_docs(file_tree, files, with_batch=False)
    assert cd.run_check(docs, closure=True) == 0
    verification = docs / "batches/demo/verification.md"
    verification.write_text("# 仅标题\n", encoding="utf-8")
    assert cd.run_check(docs, closure=True) == 1
    verification.write_text("# 验证\n\n正文\n", encoding="utf-8")
    (docs / "batches/demo/self-review.md").write_text("# 自评审\n\n正文\n", encoding="utf-8")
    assert cd.run_check(docs, closure=True) == 1


def test_plan_negative_and_unrelated_text_do_not_complete(tmp_path):
    batch = tmp_path / "demo"
    batch.mkdir()
    negatives = ["未完成", "完成前补做", "完成度 100%"]
    for status in negatives:
        (batch / "plan.md").write_text(
            f"# 任务\n\n| 任务 | 状态 |\n|---|---|\n| self-review/verification | {status} |\n",
            encoding="utf-8",
        )
        assert cd._check_plan_completion(batch, set()) == []
    (batch / "plan.md").write_text(
        "# 任务\n\n| 任务 | 状态 |\n|---|---|\n| verification-report/self-review-helper | 完成 |\n",
        encoding="utf-8",
    )
    assert cd._check_plan_completion(batch, set()) == []


def test_plan_free_prose_and_fences_do_not_complete(tmp_path):
    batch = tmp_path / "demo"
    batch.mkdir()
    (batch / "plan.md").write_text(
        "# 任务\n\nself-review/verification 完成\n\n```text\n| 任务 | 状态 |\n|---|---|\n| self-review | 完成 |\n```\n",
        encoding="utf-8",
    )
    assert cd._check_plan_completion(batch, set()) == []


def test_exemption_exact_match_and_stale_rejection(file_tree):
    files = batch_files()
    del files["aixcoding/docs/batches/demo/plan.md"]
    files["aixcoding/docs/standards/closure-exemptions.toml"] = '[exemptions]\ndemo = ["plan.md"]\n'
    docs = make_docs(file_tree, files, with_batch=False)
    assert cd.run_check(docs, closure=True) == 0
    (docs / "batches/demo/plan.md").write_text("# 任务\n\n正文\n", encoding="utf-8")
    assert cd.run_check(docs, closure=True) == 1
    (docs / "standards/closure-exemptions.toml").write_text("[exemptions]\n", encoding="utf-8")
    assert cd.run_check(docs, closure=True) == 0


def test_unknown_batch_exemption_is_stale(file_tree):
    docs = make_docs(
        file_tree,
        {"aixcoding/docs/standards/closure-exemptions.toml": '[exemptions]\nmissing = ["plan.md"]\n'},
    )
    assert cd.run_check(docs, closure=True) == 1


def test_dotted_batch_name_uses_exact_quoted_toml_key(file_tree):
    files = batch_files("upstream-merge-v0.32.2")
    del files["aixcoding/docs/batches/upstream-merge-v0.32.2/plan.md"]
    files["aixcoding/docs/standards/closure-exemptions.toml"] = '[exemptions]\n"upstream-merge-v0.32.2" = ["plan.md"]\n'
    docs = make_docs(file_tree, files, with_batch=False)
    assert cd.run_check(docs, closure=True) == 0


def test_new_partial_micro_directory_fails_but_no_directory_is_out_of_scope(file_tree):
    docs = make_docs(file_tree, {"aixcoding/docs/micro/note.md": "# 微改动\n\n正文\n"})
    assert cd.run_check(docs, closure=True) == 0
    files = {
        "aixcoding/docs/batches/partial/plan.md": "# 任务\n\n正文\n",
        "aixcoding/docs/batches/partial/verification.md": "# 验证\n\n正文\n",
        "aixcoding/docs/batches/partial/self-review.md": f"# 自评审\n\n{SIGNED}\n",
    }
    for rel, text in files.items():
        path = docs.parents[1] / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    assert cd.run_check(docs, closure=True) == 1
