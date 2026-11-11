# (tests — asserts are pytest idiom, Chinese prose is the data)
from __future__ import annotations

import subprocess
from pathlib import Path

from aixcoding.tools import check_docs as cd
from aixcoding.tools import check_id_only as cio
from aixcoding.tools import gen_customizations as gc

SIGNED = "- 责任人：t\n- 状态：已确认\n- 确认日期：2026-11-10\n"


def design(rows: str) -> str:
    return (
        "# 设计\n\n"
        f"{SIGNED}\n"
        "## 定制点登记预告\n\n"
        "| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |\n"
        "|---|---|---|---|---|---|---|\n"
        f"{rows}\n"
        "## 文件与改动清单\n\n无\n"
    )


def row(cid: str, file: str, anchor: str, count: int | None = None, risk: str = "低") -> str:
    count_cell = str(count) if count is not None else ""
    return f"| {cid} | src/chrys/app/{file} | {anchor} | {count_cell} | — | {risk} | — |\n"


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], check=False, capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr}"
    return proc.stdout


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-q", "-m", message)


def collision_repo(git_repo, beta_id: str = "C145"):
    files = {
        "src/chrys/app/a.py": "A = 1  # AIxCoding alpha: shared\n",
        "src/chrys/app/b.py": "B = 1  # AIxCoding beta: shared\n",
        "aixcoding/docs/batches/alpha/design.md": design(row("C145", "a.py", "AIxCoding alpha: shared")),
        "aixcoding/docs/batches/beta/design.md": design(row(beta_id, "b.py", "AIxCoding beta: shared")),
        "aixcoding/docs/other.md": "# 其他\n\n正文\n",
    }
    return git_repo(files)


def test_id_only_legacy_collision_passes_without_writes(git_repo):
    repo = collision_repo(git_repo)
    path = repo / "aixcoding/docs/batches/beta/design.md"
    path.write_text(path.read_text(encoding="utf-8").replace("C145", "beta:legacy-c145"), encoding="utf-8")
    before = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert cio.run_check(repo, "HEAD", "beta") == 0
    after = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert after == before
    assert gc.run_check(repo, strict=True) == 0


def test_same_batch_duplicate_slug_uses_source_order(git_repo):
    files = {
        "src/chrys/app/b1.py": "B1 = 1  # AIxCoding beta: one\n",
        "src/chrys/app/b2.py": "B2 = 1  # AIxCoding beta: two\n",
        "aixcoding/docs/batches/beta/design.md": design(
            row("beta:foo", "b1.py", "AIxCoding beta: one") + row("beta:foo", "b2.py", "AIxCoding beta: two")
        ),
    }
    repo = git_repo(files)
    path = repo / "aixcoding/docs/batches/beta/design.md"
    text = path.read_text(encoding="utf-8")
    first = text.index("beta:foo")
    second = text.index("beta:foo", first + 1)
    text = text[:second] + "beta:foo-m1-2" + text[second + len("beta:foo") :]
    path.write_text(text, encoding="utf-8")
    assert cio.run_check(repo, "HEAD", "beta") == 0
    assert gc.run_check(repo, strict=True) == 0


def test_occupied_preferred_slug_gets_deterministic_suffix(git_repo):
    repo = collision_repo(git_repo)
    extra = row("beta:legacy-c145", "c.py", "AIxCoding beta: occupied")
    write(repo, "src/chrys/app/c.py", "C = 1  # AIxCoding beta: occupied\n")
    path = repo / "aixcoding/docs/batches/beta/design.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("\n## 文件与改动清单", f"{extra}\n## 文件与改动清单"),
        encoding="utf-8",
    )
    commit(repo, "occupy preferred")
    path.write_text(path.read_text(encoding="utf-8").replace("C145", "beta:legacy-c145-m1-1"), encoding="utf-8")
    assert cio.run_check(repo, "HEAD", "beta") == 0


def test_mapping_is_repeatable(git_repo, capsys):
    repo = collision_repo(git_repo)
    path = repo / "aixcoding/docs/batches/beta/design.md"
    path.write_text(path.read_text(encoding="utf-8").replace("C145", "beta:legacy-c145"), encoding="utf-8")
    assert cio.run_check(repo, "HEAD", "beta") == 0
    first = capsys.readouterr().out
    assert cio.run_check(repo, "HEAD", "beta") == 0
    assert capsys.readouterr().out == first


def test_legacy_range_is_not_mechanically_converted(git_repo):
    files = {
        "src/chrys/app/a.py": "A = 1  # AIxCoding twin: shared\nA2 = 1  # AIxCoding twin: shared\n",
        "src/chrys/app/b.py": "B = 1  # AIxCoding twin: shared\nB2 = 1  # AIxCoding twin: shared\n",
        "aixcoding/docs/batches/alpha/design.md": design(row("C001-C002", "a.py", "AIxCoding twin: shared", 2)),
        "aixcoding/docs/batches/beta/design.md": design(row("C001-C002", "b.py", "AIxCoding twin: shared", 2)),
    }
    repo = git_repo(files)
    path = repo / "aixcoding/docs/batches/beta/design.md"
    path.write_text(path.read_text(encoding="utf-8").replace("C001-C002", "beta:twins"), encoding="utf-8")
    assert cio.run_check(repo, "HEAD", "beta") == 1


def test_semantic_diff_is_fail_closed(git_repo):
    repo = collision_repo(git_repo)
    path = repo / "aixcoding/docs/batches/beta/design.md"
    original = path.read_text(encoding="utf-8")
    mutations = [
        original.replace("b.py", "other.py").replace("C145", "beta:legacy-c145"),
        original.replace("AIxCoding beta: shared", "AIxCoding beta: changed").replace("C145", "beta:legacy-c145"),
        original.replace("| 低 |", "| 高 |").replace("C145", "beta:legacy-c145"),
        original.replace("无\n", "额外正文\n").replace("C145", "beta:legacy-c145"),
    ]
    for text in mutations:
        path.write_text(text, encoding="utf-8")
        assert cio.run_check(repo, "HEAD", "beta") == 1


def test_out_of_scope_and_ambiguous_changes_fail(git_repo):
    repo = collision_repo(git_repo)
    path = repo / "aixcoding/docs/batches/beta/design.md"
    path.write_text(path.read_text(encoding="utf-8").replace("C145", "beta:legacy-c145"), encoding="utf-8")
    write(repo, "aixcoding/docs/other.md", "# 其他\n\n额外修改\n")
    assert cio.run_check(repo, "HEAD", "beta") == 1


def test_multi_mapped_reference_outside_registration_is_ambiguous(git_repo):
    repo = git_repo(
        {
            "src/chrys/app/b1.py": "B1 = 1  # AIxCoding beta: one\n",
            "src/chrys/app/b2.py": "B2 = 1  # AIxCoding beta: two\n",
            "aixcoding/docs/batches/beta/design.md": design(
                row("beta:foo", "b1.py", "AIxCoding beta: one") + row("beta:foo", "b2.py", "AIxCoding beta: two")
            ),
            "aixcoding/docs/batches/beta/notes.md": "引用 beta:foo\n",
        }
    )
    path = repo / "aixcoding/docs/batches/beta/design.md"
    text = path.read_text(encoding="utf-8")
    second = text.index("beta:foo", text.index("beta:foo") + 1)
    path.write_text(text[:second] + "beta:foo-m1-2" + text[second + len("beta:foo") :], encoding="utf-8")
    write(repo, "aixcoding/docs/batches/beta/notes.md", "引用 beta:foo-m1-2\n")
    assert cio.run_check(repo, "HEAD", "beta") == 1


def test_duplicate_landing_anchor_is_m2(git_repo):
    repo = git_repo(
        {
            "src/chrys/app/b.py": "B = 1  # AIxCoding beta: same\nB2 = 1  # AIxCoding beta: same\n",
            "aixcoding/docs/batches/beta/design.md": design(
                row("beta:foo", "b.py", "AIxCoding beta: same") + row("beta:foo-m1-2", "b.py", "AIxCoding beta: same")
            ),
        }
    )
    assert cio.run_check(repo, "HEAD", "beta") == 1


def test_adr_numeric_collision_migration_and_decision_diff(git_repo):
    old = "aixcoding/docs/batches/beta/adr/0001-guard.md"
    new = "aixcoding/docs/standards/adr/beta--legacy-adr-0001.md"
    files = {
        "aixcoding/docs/batches/beta/design.md": design(""),
        "aixcoding/docs/standards/adr/0001-other.md": "# ADR-0001：其他\n\n- 责任人：t\n- 状态：已确认\n- 确认日期：2026-11-10\n\n## 决策\n\n正文\n",
        old: "# ADR-0001：护栏\n\n- 责任人：t\n- 状态：已确认\n- 确认日期：2026-11-10\n\n## 决策\n\n正文\n",
    }
    repo = git_repo(files)
    text = (repo / old).read_text(encoding="utf-8").replace("ADR-0001", "ADR-beta--legacy-adr-0001")
    write(repo, new, text)
    (repo / old).unlink()
    assert cio.run_check(repo, "HEAD", "beta") == 0
    assert cd.run_check(repo / "aixcoding/docs") == 0
    write(repo, new, text.replace("正文", "改动决策"))
    assert cio.run_check(repo, "HEAD", "beta") == 1


def test_parallel_branches_merge_without_coordination(git_repo):
    repo = git_repo({"README.md": "base\n"})
    main = git(repo, "branch", "--show-current").strip()
    git(repo, "checkout", "-q", "-b", "alpha")
    write(repo, "src/chrys/app/a.py", "A = 1  # AIxCoding alpha: shared\n")
    write(
        repo, "aixcoding/docs/batches/alpha/design.md", design(row("alpha:shared", "a.py", "AIxCoding alpha: shared"))
    )
    commit(repo, "alpha")
    git(repo, "checkout", "-q", main)
    git(repo, "checkout", "-q", "-b", "beta")
    write(repo, "src/chrys/app/b.py", "B = 1  # AIxCoding beta: shared\n")
    write(repo, "aixcoding/docs/batches/beta/design.md", design(row("beta:shared", "b.py", "AIxCoding beta: shared")))
    commit(repo, "beta")
    git(repo, "-c", "user.email=t@example.com", "-c", "user.name=t", "merge", "-q", "--no-ff", "alpha", "-m", "merge")
    assert gc.run_check(repo, strict=True) == 0
    assert cd.run_check(repo / "aixcoding/docs") == 0
    assert not (repo / "aixcoding/docs/INDEX.md").exists()
    assert not (repo / "aixcoding/docs/ROADMAP.md").exists()
