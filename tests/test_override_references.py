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
from tcw.errors import TcwError
from tests.fullids import fid
from tests.statefiles import write_state, CAPABILITY_STATE, TAXONOMY_STATE

UPSTREAM = {"auth/login": {"Status": "Supported"}}


def T(slug: str) -> str:
    """A taxonomy entry of the project `child`, as a record stores it."""
    return fid("child", "taxonomy", slug)


def node(tmp_path: Path) -> Path:
    """A child node with a local taxonomy that inherits a `base` capabilities
    ledger holding `auth/login`."""
    _base, child = child_of(tmp_path, UPSTREAM)
    init(["taxonomy"], child, "child")
    return child


def term(root: Path, slug: str, kind: str = "") -> None:
    d = root / "docs" / "taxonomy" / slug
    d.mkdir(parents=True)
    meta = {"name": slug}
    if kind:
        meta["kind"] = kind
    write_state(d / TAXONOMY_STATE, yaml.safe_dump(meta))
    (d / "description.md").write_text("")
    subprocess.run(["git", "-C", str(root), "add", str(d)], check=True)


def override(root: Path, **fields) -> None:
    """The child's override of `auth/login`: its own object at the same path,
    holding only `fields` (TCW-112 Design 2.2)."""
    write_cap(root, "auth/login", complete=False, **fields)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)


def check(root: Path) -> list[str]:
    return FsCapabilitiesStore.open(root).check()


# ── criteria 1–3: check ──────────────────────────────────────────────────────

def test_check_reports_a_dangling_feature_and_subject_in_an_override(tmp_path):
    root = node(tmp_path)
    override(root, Subject=[T("ghost")], Feature=T("nope"))
    problems = [str(f) for f in check(root)]
    assert f"error: docs/capabilities/auth/login: Feature → dangling ref '{T('nope')}'" in problems, problems
    assert f"error: docs/capabilities/auth/login: Subject → dangling ref '{T('ghost')}'" in problems, problems


def test_check_reports_a_dangling_identifier_an_override_sets(tmp_path):
    root = node(tmp_path)
    override(root, **{"Blocked by": fid("child", "capabilities", "missing-cap")})
    missing = fid("child", "capabilities", "missing-cap")
    assert f"error: docs/capabilities/auth/login: Blocked by → dangling identifier '{missing}'" \
        in map(str, check(root))


def test_an_override_that_clears_fields_reports_nothing_for_them(tmp_path):
    """`null` clears an inherited field: it names nothing, and read as a value
    it would be the string 'None' — a bogus `Roles` slug."""
    root = node(tmp_path)
    override(root, Subject=None, Roles=None)
    assert not [p for p in map(str, check(root)) if "auth/login" in p], check(root)


def test_an_override_naming_a_real_term_reports_nothing(tmp_path):
    root = node(tmp_path)
    term(root, "zed")
    override(root, Subject=[T("zed")])
    assert not [p for p in map(str, check(root)) if "auth/login" in p], check(root)


# ── criteria 4–5: taxonomy rm ────────────────────────────────────────────────

@pytest.mark.parametrize("field, value, kind", [
    ("Subject", [T("zed")], ""), ("Feature", T("zed"), "Feature")])
def test_rm_refuses_a_term_an_override_names(tmp_path, monkeypatch, capsys,
                                             field, value, kind):
    root = node(tmp_path)
    term(root, "zed", kind)
    override(root, **{field: value})
    # An override is one of the project's own capabilities (TCW-112 Design 7.3).
    with pytest.raises(TcwError, match=rf"capability auth/login \({field}\)"):
        FsTaxonomyStore.open(root).remove("zed")
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["taxonomy", "rm", "zed"]) == 3
    assert f"capability auth/login ({field})" in capsys.readouterr().err
    assert FsTaxonomyStore.open(root).get_view("zed") is not None


def test_an_override_naming_another_term_does_not_block(tmp_path):
    root = node(tmp_path)
    term(root, "zed")
    term(root, "other")
    override(root, Subject=[T("other")])
    FsTaxonomyStore.open(root).remove("zed")
    assert FsTaxonomyStore.open(root).get_view("zed") is None


def test_a_malformed_override_refuses_the_removal_readably(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    term(root, "zed")
    override(root, Subject=[T("other")])
    write_state(root / "docs" / "capabilities" / "auth" / "login" / CAPABILITY_STATE,
                "Subject: [unclosed\n")
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["taxonomy", "rm", "zed"]) == 3
    err = capsys.readouterr().err
    assert "capabilities that might name it cannot be read" in err and "Traceback" not in err, err
    assert FsTaxonomyStore.open(root).get_view("zed") is not None


# ── review fold-in: check(identifier) on an inherited capability ────────────

def test_checking_an_overridden_capability_by_path_reports_each_problem_once(tmp_path):
    """An override is at the inherited path, so the selected capability's
    combined fields and its override's own declaration hold the same
    references."""
    root = node(tmp_path)
    override(root, Subject=[T("ghost")])
    problems = [str(f) for f in FsCapabilitiesStore.open(root).check(identifier="auth/login")]
    assert problems.count(f"error: docs/capabilities/auth/login: Subject → dangling ref '{T('ghost')}'") == 1, problems

