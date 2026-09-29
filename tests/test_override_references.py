"""`tcw capabilities check` and `tcw taxonomy rm` see the references a local
override sets (spec:
2026-09-26-check-capability-overrides-for-taxonomy-references-in-capabilities-check-and-taxonomy-rm)."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
from test_capabilities_federation import child_of, write_cap

UPSTREAM = {"auth/login": {"id": "cap-aaa111", "Status": "Supported"}}


def node(tmp_path: Path) -> Path:
    """A child node with a local taxonomy that extends a `base` capabilities
    ledger holding `cap-aaa111`."""
    _base, child = child_of(tmp_path, UPSTREAM)
    init(["taxonomy"], child, "child")
    return child


def term(root: Path, slug: str, kind: str = "") -> None:
    d = root / "docs" / "taxonomy" / slug
    d.mkdir(parents=True)
    meta = {"name": slug}
    if kind:
        meta["kind"] = kind
    (d / "meta.yaml").write_text(yaml.safe_dump(meta))
    (d / "description.md").write_text("")
    subprocess.run(["git", "-C", str(root), "add", str(d)], check=True)


def override(root: Path, **fields) -> None:
    write_cap(root, "ov", overrides="cap-aaa111", **fields)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)


def check(root: Path) -> list[str]:
    return FsCapabilitiesStore.open(root).check()


# ── criteria 1–3: check ──────────────────────────────────────────────────────

def test_check_reports_a_dangling_feature_and_subject_in_an_override(tmp_path):
    root = node(tmp_path)
    override(root, Subject=["ghost"], Feature="nope")
    problems = check(root)
    assert "ov: Feature → dangling ref 'nope'" in problems, problems
    assert "ov: Subject → dangling ref 'ghost'" in problems, problems


def test_check_reports_a_dangling_identifier_an_override_sets(tmp_path):
    root = node(tmp_path)
    override(root, **{"Blocked by": "missing-cap"})
    assert "ov: Blocked by → dangling identifier 'missing-cap'" in check(root)


def test_an_override_that_clears_fields_reports_nothing_for_them(tmp_path):
    """`null` clears an inherited field: it names nothing, and read as a value
    it would be the string 'None' — a bogus `Roles` slug."""
    root = node(tmp_path)
    override(root, Subject=None, Roles=None)
    assert not [p for p in check(root) if p.startswith("ov:")], check(root)


def test_an_override_naming_a_real_term_reports_nothing(tmp_path):
    root = node(tmp_path)
    term(root, "zed")
    override(root, Subject=["zed"])
    assert not [p for p in check(root) if p.startswith("ov:")]


# ── criteria 4–5: taxonomy rm ────────────────────────────────────────────────

@pytest.mark.parametrize("field, value, kind", [
    ("Subject", ["zed"], ""), ("Feature", "zed", "Feature")])
def test_rm_refuses_a_term_an_override_names(tmp_path, monkeypatch, capsys,
                                             field, value, kind):
    root = node(tmp_path)
    term(root, "zed", kind)
    override(root, **{field: value})
    with pytest.raises(ValueError, match=rf"capability override ov \({field}\)"):
        FsTaxonomyStore.open(root).remove("zed")
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["taxonomy", "rm", "zed"]) == 1
    assert f"capability override ov ({field})" in capsys.readouterr().err
    assert FsTaxonomyStore.open(root).get("zed") is not None


def test_an_override_naming_another_term_does_not_block(tmp_path):
    root = node(tmp_path)
    term(root, "zed")
    term(root, "other")
    override(root, Subject=["other"])
    FsTaxonomyStore.open(root).remove("zed")
    assert FsTaxonomyStore.open(root).get("zed") is None


def test_a_malformed_override_refuses_the_removal_readably(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    override(root, Subject=["other"])
    (root / "docs" / "capabilities" / "ov" / "meta.yaml").write_text("overrides: [unclosed\n")
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["taxonomy", "rm", "zed"]) == 1
    err = capsys.readouterr().err
    assert "capabilities that might name it cannot be read" in err and "Traceback" not in err, err
    assert FsTaxonomyStore.open(root).get("zed") is not None


# ── review fold-in: check(identifier) on an inherited capability ────────────

def test_checking_an_overridden_capability_by_path_reports_each_problem_once(tmp_path):
    """`set` puts an override at the folder mirroring the upstream path, so the
    selected capability's composed fields and its override folder are the same
    references."""
    root = node(tmp_path)
    write_cap(root, "auth/login", overrides="cap-aaa111", Subject=["ghost"])
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    problems = FsCapabilitiesStore.open(root).check(identifier="auth/login")
    assert problems.count("auth/login: Subject → dangling ref 'ghost'") == 1, problems


def test_checking_an_inherited_capability_overridden_elsewhere_does_not_crash(tmp_path):
    root = node(tmp_path)
    override(root, Subject=["ghost"])
    problems = FsCapabilitiesStore.open(root).check(identifier="auth/login")
    assert "auth/login: Subject → dangling ref 'ghost'" in problems, problems
