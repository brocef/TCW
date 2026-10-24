"""Overrides by path (TCW-112): an object of a project at the same id-path as
an object it inherits is an override of it, holding only what it changes.

Each test names the acceptance criterion ("AC n", spec.md) it proves, and
which part of it. The commands run in process through `tcw.cli.main`, as
`tests/test_tree_full_identifiers.py` runs them; the suite's own fixtures
(`tests/conftest.py`) keep personal configuration and the cache inside the
test's folder.

Every fixture project is a git repository with both stores at their
defaults, its parents named under `parents:` and located by a manifest entry.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.errors import NotFound, Refused
from tcw.ids import FullId
from tcw.locate import find_tree_writable
from tcw.project_files import VERSION_KEY
from tcw.store.fs import FsCapabilitiesStore, write_sentinel
from tests.projectfiles import connect_projects, write_config, write_manifest
from tests.statefiles import CAPABILITY_STATE, TAXONOMY_STATE, write_state_data


# -- running the CLI ---------------------------------------------------------------------


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(argv)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


def show(tcw, root: Path, axis: str, target: str) -> dict:
    """`tcw <axis> show <target> --json`'s record, after checking it exited 0."""
    ran = tcw([axis, "show", target, "--json"], root)
    assert ran.code == 0, ran.err
    return json.loads(ran.out)["capability" if axis == "capabilities" else "term"]


def findings(result: Result) -> list[str]:
    """The finding lines `tcw validate` printed."""
    return [line for line in result.out.splitlines()
            if line.startswith(("error:", "warning:", "unresolved:"))]


def warnings(result: Result) -> list[str]:
    return [line for line in findings(result) if line.startswith("warning:")]


# -- writing fixture projects ------------------------------------------------------------


def project(tmp_path: Path, name: str, *parents, inherit="all") -> Path:
    """A project `name` with both stores, naming each of `parents` as a
    parent passing `inherit`, each located by a manifest entry."""
    root = tmp_path / name
    (root / "docs" / "taxonomy").mkdir(parents=True)
    (root / "docs" / "capabilities").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write_sentinel(root, name)
    write_config(root, f"id: {name}\n")
    if parents:
        connect_projects(root, "parent", *parents, inherit=inherit)
        write_manifest(root, {p: f"../{p}" for p in parents})
    return root


def cap(root: Path, path: str, *, description: str | None = None, **fields) -> Path:
    """A capability holding exactly `fields`, and a `description.md` only when
    `description` is given. Returns its state file."""
    folder = root / "docs" / "capabilities" / path
    state = write_state_data(folder / CAPABILITY_STATE, fields)
    if description is not None:
        (folder / "description.md").write_text(description)
    return state


def complete_cap(root: Path, path: str, name: str, status: str, description: str = "",
                 **fields) -> Path:
    """A capability that needs nothing inherited: a name, a Status and a
    `description.md`."""
    return cap(root, path, description=description, name=name, Status=status, **fields)


def term(root: Path, slug: str, *, description: str | None = None, **fields) -> Path:
    """A term holding exactly `fields`, and a `description.md` only when
    `description` is given. Returns its state file."""
    folder = root / "docs" / "taxonomy" / slug
    state = write_state_data(folder / TAXONOMY_STATE, fields)
    if description is not None:
        (folder / "description.md").write_text(description)
    return state


def keys(state: Path) -> set[str]:
    """Every key of a state file, `tcw-version` included."""
    return set(yaml.safe_load(state.read_text(encoding="utf-8")) or {})


def mapping(state: Path) -> dict:
    data = yaml.safe_load(state.read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if k != VERSION_KEY}


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file under a project's two stores, by path, with its bytes."""
    out = {}
    for tree in ("taxonomy", "capabilities"):
        base = root / "docs" / tree
        for f in sorted(base.rglob("*")):
            if f.is_file():
                out[str(f.relative_to(root))] = f.read_bytes()
    return out


CAP_X = "docs/capabilities/cli/x/" + CAPABILITY_STATE


def ac5_family(tmp_path: Path, *, override: bool = True, **override_fields):
    """AC 5: `core`'s `cli/x` has `Status: Missing`, `Priority: P1` and the
    description `Core body`; `app` inherits from `core` and, with `override`,
    has its own `cli/x` holding only `Status: Supported` (and any
    `override_fields`), with no `description.md`."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing", "Core body", Priority="P1")
    app = project(tmp_path, "app", "core")
    if override:
        cap(app, "cli/x", Status="Supported", **override_fields)
    return core, app


def ac9_family(tmp_path: Path):
    """AC 9: `bb` has `X` with `Status: Missing`; `cc` and `dd` inherit from
    `bb`; `cc` has its own `X` holding `Status: Supported`; `dd` has none;
    `ee` has `parents: [cc, dd]`."""
    bb = project(tmp_path, "bb")
    complete_cap(bb, "X", "X", "Missing", "Bb body")
    cc = project(tmp_path, "cc", "bb")
    cap(cc, "X", Status="Supported")
    dd = project(tmp_path, "dd", "bb")
    ee = project(tmp_path, "ee", "cc", "dd")
    return bb, cc, dd, ee


def ac10_family(tmp_path: Path, order=("cc", "dd")):
    """AC 10: `cc` and `dd` have no parents in common; `ee` has `parents:
    [cc, dd]` (or `order`); `cc`'s `X` has `name: C`, `Status: Supported`,
    `Priority: P1`; `dd`'s `X` has `name: D`, `Status: Missing`. Each also
    holds a term `t` (`cc`'s `name: C`, `dd`'s `name: D`)."""
    cc = project(tmp_path, "cc")
    complete_cap(cc, "X", "C", "Supported", Priority="P1")
    term(cc, "t", description="", name="C")
    dd = project(tmp_path, "dd")
    complete_cap(dd, "X", "D", "Missing")
    term(dd, "t", description="", name="D")
    ee = project(tmp_path, "ee", *order)
    return cc, dd, ee


# == Step 7: reading by path ==============================================================


def test_ac5_show_combines_the_partial_override_with_core(tcw, tmp_path):
    """AC 5, sentence 2: `show cli/x` in `app` has `app`'s full identifier and
    owner, `core`'s name, `app`'s Status, `core`'s Priority and body, and
    `overrides` `core.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path)
    record = show(tcw, app, "capabilities", "cli/x")
    assert record["full-id"] == "app.capabilities/cli/x"
    assert record["owner"] == "app"
    assert record["name"] == "X"
    assert record["fields"]["Status"] == "Supported"
    assert record["fields"]["Priority"] == "P1"
    assert record["body"] == "Core body"
    assert record["overrides"] == "core.capabilities/cli/x"


def test_ac5_text_show_has_the_overrides_line(tcw, tmp_path):
    """AC 5: the text `show` has the line `overrides: core.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "show", "cli/x"], app)
    assert ran.code == 0, ran.err
    assert "overrides: core.capabilities/cli/x" in ran.out.splitlines()


def test_ac5_list_prints_the_override_once_and_never_the_original(tcw, tmp_path):
    """AC 5: `list` prints `app.capabilities/cli/x` once and never
    `core.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "list"], app)
    assert ran.code == 0, ran.err
    lines = ran.out.splitlines()
    assert lines.count("app.capabilities/cli/x") == 1
    assert "core.capabilities/cli/x" not in lines


def test_ac5_list_json_record_has_overrides_and_no_partial(tcw, tmp_path):
    """AC 5: the `list --json` record for it has the same `overrides` and no
    `partial` key."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "list", "--json"], app)
    assert ran.code == 0, ran.err
    records = [r for r in json.loads(ran.out)["capabilities"]
               if r["full-id"] == "app.capabilities/cli/x"]
    assert len(records) == 1
    assert records[0]["overrides"] == "core.capabilities/cli/x"
    assert "partial" not in records[0]


def test_ac5_search_matches_the_combined_body(tcw, tmp_path):
    """AC 5, last sentence: `tcw capabilities search "Core body"` in `app`
    lists `app.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "search", "Core body"], app)
    assert ran.code == 0, ran.err
    assert ran.out.splitlines() == ["app.capabilities/cli/x"]


def test_ac6_a_null_value_removes_the_inherited_field(tcw, tmp_path):
    """AC 6, sentence 1: `app`'s `cli/x` also holding `Priority: null` makes
    `show cli/x` have no `Priority` field."""
    _, app = ac5_family(tmp_path, Priority=None)
    assert "Priority" not in show(tcw, app, "capabilities", "cli/x")["fields"]


def test_ac6_a_list_replaces_the_inherited_list_whole(tcw, tmp_path):
    """AC 6, sentence 2: `Subject: [app.taxonomy/money]` over `core`'s
    `Subject: [core.taxonomy/invoice, core.taxonomy/payment]` gives exactly
    `[app.taxonomy/money]`."""
    core = project(tmp_path, "core")
    term(core, "invoice", description="", name="Invoice")
    term(core, "payment", description="", name="Payment")
    complete_cap(core, "cli/x", "X", "Missing", "Core body", Priority="P1",
                 Subject=["core.taxonomy/invoice", "core.taxonomy/payment"])
    app = project(tmp_path, "app", "core")
    term(app, "money", description="", name="Money")
    cap(app, "cli/x", Status="Supported", Subject=["app.taxonomy/money"])
    assert show(tcw, app, "capabilities", "cli/x")["fields"]["Subject"] == \
        ["app.taxonomy/money"]


def _ac7_family(tmp_path, **override_fields):
    """AC 7: AC 5's family, `core`'s `cli/x` also having `prependedDocs:
    [resources/a.md]` with that file."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing", "Core body", Priority="P1",
                 prependedDocs=["resources/a.md"])
    (core / "docs/capabilities/cli/x/resources").mkdir()
    (core / "docs/capabilities/cli/x/resources/a.md").write_text("Text of a")
    app = project(tmp_path, "app", "core")
    cap(app, "cli/x", Status="Supported", **override_fields)
    return core, app


def test_ac7_an_override_without_prepended_docs_keeps_the_originals(tcw, tmp_path):
    """AC 7, sentence 2, first case: `app`'s override with no
    `prependedDocs` gives a body starting with `a.md`'s text."""
    _, app = _ac7_family(tmp_path)
    assert show(tcw, app, "capabilities", "cli/x")["body"].startswith("Text of a")


def test_ac7_prepended_docs_null_drops_the_originals(tcw, tmp_path):
    """AC 7, sentence 2, second case: with `prependedDocs: null`, a body
    without `a.md`'s text."""
    _, app = _ac7_family(tmp_path, prependedDocs=None)
    body = show(tcw, app, "capabilities", "cli/x")["body"]
    assert "Text of a" not in body
    assert body == "Core body"


def test_ac7_own_prepended_docs_are_read_from_the_overrides_resources(tcw, tmp_path):
    """AC 7, sentence 2, third case: `prependedDocs: [resources/b.md]` with
    `b.md` in `app`'s `cli/x/resources/` gives a body starting with `b.md`'s
    text and not holding `a.md`'s."""
    _, app = _ac7_family(tmp_path, prependedDocs=["resources/b.md"])
    (app / "docs/capabilities/cli/x/resources").mkdir()
    (app / "docs/capabilities/cli/x/resources/b.md").write_text("Text of b")
    body = show(tcw, app, "capabilities", "cli/x")["body"]
    assert body.startswith("Text of b")
    assert "Text of a" not in body


def test_ac7_an_own_description_is_the_middle_of_the_body(tcw, tmp_path):
    """AC 7, sentence 3, first case: an `app` `description.md` holding `App
    body` gives the middle `App body` (after `a.md`'s text, in place of
    `core`'s description)."""
    _, app = _ac7_family(tmp_path)
    (app / "docs/capabilities/cli/x/description.md").write_text("App body")
    body = show(tcw, app, "capabilities", "cli/x")["body"]
    assert body == "Text of a\n\nApp body"


def test_ac7_an_empty_own_description_keeps_the_originals(tcw, tmp_path):
    """AC 7, sentence 3, second case: an empty `app` `description.md` gives
    the middle `Core body`."""
    _, app = _ac7_family(tmp_path)
    (app / "docs/capabilities/cli/x/description.md").write_text("")
    body = show(tcw, app, "capabilities", "cli/x")["body"]
    assert body == "Text of a\n\nCore body"


def _ac8_family(tmp_path):
    """AC 8: `core`'s `invoice` has the description `Core text` and
    `resources/d.png`; `app` has its own `invoice` holding only `relatesTo:
    [app.taxonomy/money]`, and its own term `money`."""
    core = project(tmp_path, "core")
    term(core, "invoice", description="Core text", name="Invoice", kind="Vocabulary")
    (core / "docs/taxonomy/invoice/resources").mkdir()
    (core / "docs/taxonomy/invoice/resources/d.png").write_bytes(b"\x89PNG\r\n")
    app = project(tmp_path, "app", "core")
    term(app, "invoice", relatesTo=["app.taxonomy/money"])
    term(app, "money", description="", name="Money", kind="Vocabulary")
    return core, app


def test_ac8_a_term_override_combines_with_cores_term(tcw, tmp_path):
    """AC 8: `show invoice` in `app` has `app`'s full identifier, `core`'s
    name, kind, description and attachments, `app`'s `relatesTo`, and
    `overrides` `core.taxonomy/invoice`."""
    _, app = _ac8_family(tmp_path)
    record = show(tcw, app, "taxonomy", "invoice")
    assert record["full-id"] == "app.taxonomy/invoice"
    assert record["name"] == "Invoice"
    assert record["kind"] == "Vocabulary"
    assert record["description"] == "Core text"
    assert record["relatesTo"] == ["app.taxonomy/money"]
    assert record["attachments"] == ["resources/d.png"]
    assert record["overrides"] == "core.taxonomy/invoice"


def test_ac9_only_a_declaring_project_replaces(tcw, tmp_path):
    """AC 9, sentence 2: in `ee`, `show X` has `fields.Status` `Supported`
    (`cc`'s, though `dd` comes later and declares nothing), `full-id`
    `cc.capabilities/X` and `overrides` `bb.capabilities/X`."""
    *_, ee = ac9_family(tmp_path)
    record = show(tcw, ee, "capabilities", "X")
    assert record["fields"]["Status"] == "Supported"
    assert record["full-id"] == "cc.capabilities/X"
    assert record["overrides"] == "bb.capabilities/X"


def test_ac9_validate_gives_no_warning_about_x(tcw, tmp_path):
    """AC 9, last sentence: `tcw validate` in `ee` reports no warning
    containing `X`."""
    *_, ee = ac9_family(tmp_path)
    ran = tcw(["validate"], ee)
    assert not [w for w in warnings(ran) if "X" in w], ran.out


def test_ac26_a_full_identifier_names_the_owners_own_object(tcw, tmp_path):
    """AC 26, sentence 1: in AC 5, `show core.capabilities/cli/x` in `app` has
    `fields.Status` `Missing`, `full-id` `core.capabilities/cli/x` and
    `overrides` `null` (`core`'s object, never `app`'s override)."""
    _, app = ac5_family(tmp_path)
    record = show(tcw, app, "capabilities", "core.capabilities/cli/x")
    assert record["fields"]["Status"] == "Missing"
    assert record["full-id"] == "core.capabilities/cli/x"
    assert record["overrides"] is None


def test_ac26_an_ancestors_full_identifier_names_its_object(tcw, tmp_path):
    """AC 26, sentence 2, first half: in AC 9's `ee`, `show bb.capabilities/X`
    has `fields.Status` `Missing`."""
    *_, ee = ac9_family(tmp_path)
    assert show(tcw, ee, "capabilities", "bb.capabilities/X")["fields"]["Status"] \
        == "Missing"


def test_ac26_an_owner_seen_as_it_sees_itself_agrees_with_the_view(tcw, tmp_path):
    """AC 26, sentence 2, second half: in AC 9's `ee`, `show
    cc.capabilities/X` has the same `name`, `fields` and body as `show X`."""
    *_, ee = ac9_family(tmp_path)
    by_owner = show(tcw, ee, "capabilities", "cc.capabilities/X")
    by_path = show(tcw, ee, "capabilities", "X")
    assert by_owner["name"] == by_path["name"]
    assert by_owner["fields"] == by_path["fields"]
    assert by_owner["body"] == by_path["body"]


def test_ac26_the_projects_own_identifier_for_a_path_it_only_inherits_exits_4(
        tcw, tmp_path):
    """AC 26, sentence 3: `show app.capabilities/cli/z` for an id-path `app`
    only inherits exits 4."""
    core, app = ac5_family(tmp_path)
    complete_cap(core, "cli/z", "Z", "Missing")
    assert tcw(["capabilities", "show", "app.capabilities/cli/z"], app).code == 4


def test_ac27_list_local_prints_the_override_not_the_original(tcw, tmp_path):
    """AC 27: in AC 5, `tcw capabilities list --local` in `app` prints
    `app.capabilities/cli/x` and not `core.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "list", "--local"], app)
    assert ran.code == 0, ran.err
    lines = ran.out.splitlines()
    assert "app.capabilities/cli/x" in lines
    assert "core.capabilities/cli/x" not in lines


def test_ac10_show_uses_the_later_unrelated_project_whole(tcw, tmp_path):
    """AC 10, sentence 2: in `ee`, `show X` has `name` `D`, `full-id`
    `dd.capabilities/X`, no `Priority` field (`cc`'s is not mixed in), and
    `overrides` `null`; it exits 0, with no ambiguity error (Design 3.6)."""
    *_, ee = ac10_family(tmp_path)
    ran = tcw(["capabilities", "show", "X", "--json"], ee)
    assert ran.code == 0, ran.err
    record = json.loads(ran.out)["capability"]
    assert record["name"] == "D"
    assert record["full-id"] == "dd.capabilities/X"
    assert "Priority" not in record["fields"]
    assert record["overrides"] is None


def test_ac10_list_names_the_path_once(tcw, tmp_path):
    """AC 10, sentence 4, the listing: `tcw capabilities list` in `ee` lists
    `dd.capabilities/X` once and never `cc.capabilities/X`."""
    *_, ee = ac10_family(tmp_path)
    ran = tcw(["capabilities", "list"], ee)
    assert ran.code == 0, ran.err
    lines = ran.out.splitlines()
    assert lines == ["dd.capabilities/X"]


def test_ac10_terms_at_one_path_show_the_later_projects_term(tcw, tmp_path):
    """AC 10, last sentence: the same two projects each holding a term `t`,
    `tcw taxonomy show t` in `ee` exits 0 with `full-id` `dd.taxonomy/t` and
    `name` `D`; and `tcw taxonomy list` lists `dd.taxonomy/t` once."""
    *_, ee = ac10_family(tmp_path)
    record = show(tcw, ee, "taxonomy", "t")
    assert record["full-id"] == "dd.taxonomy/t"
    assert record["name"] == "D"
    listed = tcw(["taxonomy", "list"], ee)
    assert listed.code == 0, listed.err
    assert listed.out.splitlines() == ["dd.taxonomy/t"]


def _ac11_family(tmp_path):
    """AC 11: AC 9's family, `dd` also having its own `X` holding `Priority:
    P2`."""
    bb, cc, dd, ee = ac9_family(tmp_path)
    cap(dd, "X", Priority="P2")
    return bb, cc, dd, ee


def test_ac11_siblings_overriding_a_common_parent_show_the_later_one(tcw, tmp_path):
    """AC 11, sentence 2: in `ee`, `show X` has `fields.Status` `Missing`
    (`bb`'s: `cc`'s `Supported` is not used), `fields.Priority` `P2`,
    `full-id` `dd.capabilities/X` and `overrides` `bb.capabilities/X`."""
    *_, ee = _ac11_family(tmp_path)
    record = show(tcw, ee, "capabilities", "X")
    assert record["fields"]["Status"] == "Missing"
    assert record["fields"]["Priority"] == "P2"
    assert record["full-id"] == "dd.capabilities/X"
    assert record["overrides"] == "bb.capabilities/X"


# == Step 12: two unrelated projects at one path ==========================================


def test_ac10_validate_warns_once_at_the_configuration(tcw, tmp_path):
    """AC 10, sentence 3: `tcw validate` in `ee` exits 0 with exactly one
    warning about `X`, whose `where` is `.tcw/tcw-config.yaml` and whose
    message contains `'cc' and 'dd'` and `uses the one from 'dd'`."""
    *_, ee = ac10_family(tmp_path)
    ran = tcw(["validate"], ee)
    assert ran.code == 0, ran.out + ran.err
    about_x = [w for w in warnings(ran) if "capabilities X" in w]
    assert len(about_x) == 1, ran.out
    assert about_x[0].startswith("warning: .tcw/tcw-config.yaml: "), about_x[0]
    assert "'cc' and 'dd'" in about_x[0]
    assert "uses the one from 'dd'" in about_x[0]


def test_ac10_list_prints_the_same_warning_on_standard_error(tcw, tmp_path):
    """AC 10, sentence 4: `tcw capabilities list` in `ee` prints the same
    message on standard error after `warning: `, and standard output holds
    only the identifier."""
    *_, ee = ac10_family(tmp_path)
    validated = tcw(["validate"], ee)
    message = next(w for w in warnings(validated) if "capabilities X" in w) \
        .split(": ", 2)[2]
    ran = tcw(["capabilities", "list"], ee)
    assert ran.code == 0, ran.err
    assert f"warning: {message}" in ran.err.splitlines()
    assert ran.out.splitlines() == ["dd.capabilities/X"]


def test_ac10_reversing_the_parents_reverses_the_choice(tcw, tmp_path):
    """AC 10, sentence 5: with `parents: [dd, cc]` the warning says `uses the
    one from 'cc'` and `show X` has `name` `C`."""
    *_, ee = ac10_family(tmp_path, order=("dd", "cc"))
    ran = tcw(["validate"], ee)
    about_x = [w for w in warnings(ran) if "capabilities X" in w]
    assert len(about_x) == 1, ran.out
    assert "uses the one from 'cc'" in about_x[0]
    assert show(tcw, ee, "capabilities", "X")["name"] == "C"


def test_ac11_validate_warns_once_that_nothing_from_cc_is_used(tcw, tmp_path):
    """AC 11, last sentence: `tcw validate` in `ee` warns once, naming `'cc'
    and 'dd'`, `uses the one from 'dd'` and `nothing from 'cc''s`."""
    *_, ee = _ac11_family(tmp_path)
    ran = tcw(["validate"], ee)
    about_x = [w for w in warnings(ran) if "capabilities X" in w]
    assert len(about_x) == 1, ran.out
    assert "'cc' and 'dd'" in about_x[0]
    assert "uses the one from 'dd'" in about_x[0]
    assert "nothing from 'cc''s" in about_x[0]


def test_ac12_an_override_is_never_a_warning(tcw, tmp_path):
    """AC 12: in AC 5, `tcw validate` in `app` reports no warning about
    `cli/x`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["validate"], app)
    assert not [w for w in warnings(ran) if "cli/x" in w], ran.out


def test_ac43_a_complete_own_object_silences_the_warning(tcw, tmp_path):
    """AC 43, sentence 1: in AC 10's family, `ee` with its own complete `X`
    (`name: E`, `Status: Supported`, a `description.md`) gets no warning about
    `X` from `tcw validate` or `tcw capabilities list`, and `show X` has
    `full-id` `ee.capabilities/X` and `overrides` `dd.capabilities/X`."""
    *_, ee = ac10_family(tmp_path)
    complete_cap(ee, "X", "E", "Supported", "Ee body")
    validated = tcw(["validate"], ee)
    assert not [w for w in warnings(validated) if "capabilities X" in w], validated.out
    listed = tcw(["capabilities", "list"], ee)
    assert listed.code == 0, listed.err
    assert "warning:" not in listed.err
    record = show(tcw, ee, "capabilities", "X")
    assert record["full-id"] == "ee.capabilities/X"
    assert record["overrides"] == "dd.capabilities/X"


def test_ac43_a_partial_own_object_does_not_silence_the_warning(tcw, tmp_path):
    """AC 43, sentence 2: with `ee`'s `X` holding only `Status: Supported`,
    the warning is still given, and contains `a complete object of its own`."""
    *_, ee = ac10_family(tmp_path)
    cap(ee, "X", Status="Supported")
    ran = tcw(["validate"], ee)
    about_x = [w for w in warnings(ran) if "capabilities X" in w]
    assert len(about_x) == 1, ran.out
    assert "a complete object of its own" in about_x[0]
    listed = tcw(["capabilities", "list"], ee)
    assert "a complete object of its own" in listed.err


def test_ac43_a_complete_object_in_a_project_not_inheriting_both_does_not_silence(
        tcw, tmp_path):
    """AC 43, last sentence: in AC 11's family, `dd`'s own `X` being complete
    does not stop the warning in `ee`, since `cc` does not pass the axis to
    `dd`."""
    _, _, dd, ee = _ac11_family(tmp_path)
    complete_cap(dd, "X", "Dd", "Missing", "Dd body", Priority="P2")
    ran = tcw(["validate"], ee)
    about_x = [w for w in warnings(ran) if "capabilities X" in w]
    assert len(about_x) == 1, ran.out
    assert "'cc' and 'dd'" in about_x[0]


# == Step 8: writing by path ==============================================================


def test_ac20_set_on_an_inherited_capability_writes_only_the_field_given(
        tcw, tmp_path):
    """AC 20, sentence 1: in AC 5's family before `app` has `cli/x`, `tcw
    capabilities set cli/x --status Supported` writes
    `docs/capabilities/cli/x/tcw-capability.yaml`, named on standard error,
    whose keys are exactly `tcw-version` and `Status`, and no other file."""
    _, app = ac5_family(tmp_path, override=False)
    before = snapshot(app)
    ran = tcw(["capabilities", "set", "cli/x", "--status", "Supported"], app)
    assert ran.code == 0, ran.err
    state = app / CAP_X
    assert "cli/x/" + CAPABILITY_STATE in ran.err
    assert keys(state) == {VERSION_KEY, "Status"}
    assert mapping(state) == {"Status": "Supported"}
    after = snapshot(app)
    assert set(after) - set(before) == {CAP_X}
    assert {k: v for k, v in after.items() if k != CAP_X} == before


def test_ac20_set_by_the_originals_full_identifier_writes_the_same_file(
        tcw, tmp_path):
    """AC 20, sentence 2 and 3: `tcw capabilities set core.capabilities/cli/x
    --field Priority=P2` then adds `Priority: P2` to the same file and writes
    nothing else; no folder named `core` is created in `app`'s store."""
    _, app = ac5_family(tmp_path, override=False)
    assert tcw(["capabilities", "set", "cli/x", "--status", "Supported"], app).code == 0
    before = snapshot(app)
    ran = tcw(["capabilities", "set", "core.capabilities/cli/x", "--field",
               "Priority=P2"], app)
    assert ran.code == 0, ran.err
    assert mapping(app / CAP_X) == {"Status": "Supported", "Priority": "P2"}
    after = snapshot(app)
    assert set(after) == set(before)
    assert {k: v for k, v in after.items() if k != CAP_X} == \
        {k: v for k, v in before.items() if k != CAP_X}
    assert not (app / "docs/capabilities/core").exists()


def test_ac20_set_writes_into_an_organising_folder(tcw, tmp_path):
    """AC 20, last sentence: when `app`'s store already has a folder `cli/x`
    with no state file (holding `app`'s own object `cli/x/z`), the first `set`
    writes the state file into that folder, and `cli/x/z` is unchanged and
    still listed."""
    _, app = ac5_family(tmp_path, override=False)
    complete_cap(app, "cli/x/z", "Z", "Missing", "Z body",
                 parent="core.capabilities/cli/x")
    z_files = {k: v for k, v in snapshot(app).items() if "cli/x/z/" in k}
    ran = tcw(["capabilities", "set", "cli/x", "--status", "Supported"], app)
    assert ran.code == 0, ran.err
    assert mapping(app / CAP_X) == {"Status": "Supported"}
    assert {k: v for k, v in snapshot(app).items() if "cli/x/z/" in k} == z_files
    listed = tcw(["capabilities", "list"], app)
    assert "app.capabilities/cli/x/z" in listed.out.splitlines()


def test_ac21_set_of_a_project_not_inherited_from_is_refused(tcw, tmp_path):
    """AC 21: `app` has `parents: [{id: core, inherit: [taxonomy]}]`; `tcw
    capabilities set core.capabilities/cli/x --status Supported` exits 3 with
    a message containing `'app' does not inherit it`, and writes nothing."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing", "Core body")
    app = project(tmp_path, "app", "core", inherit=["taxonomy"])
    before = snapshot(app)
    ran = tcw(["capabilities", "set", "core.capabilities/cli/x", "--status",
               "Supported"], app)
    assert ran.code == 3, ran.err
    assert "'app' does not inherit it" in ran.err
    assert snapshot(app) == before


def test_ac22_parent_on_an_inherited_capability_writes_only_parent(tcw, tmp_path):
    """AC 22: in AC 5's family before `app` has `cli/x`, `tcw capabilities set
    cli/x --parent core.capabilities/cli` exits 0 and `app`'s new `cli/x`
    state file holds `parent: core.capabilities/cli` and no `Status`.

    `core` is also given a capability `cli`, so that the parent named is an
    object (AC 5's family as written has only the folder `cli`, and a parent
    must name an object, TCW-111)."""
    core, app = ac5_family(tmp_path, override=False)
    complete_cap(core, "cli", "Cli", "Supported")
    ran = tcw(["capabilities", "set", "cli/x", "--parent", "core.capabilities/cli"], app)
    assert ran.code == 0, ran.err
    held = mapping(app / CAP_X)
    assert held == {"parent": "core.capabilities/cli"}
    assert "Status" not in held


def _ac1_family(tmp_path):
    """AC 1, with AC 23's addition: `core` has a term `invoice` (`name:
    Invoice`, `kind: Vocabulary`, description `Core text`) and a capability
    `cli/x` (`name: X`, `Status: Missing`); `app` inherits from `core` and has
    neither."""
    core = project(tmp_path, "core")
    term(core, "invoice", description="Core text", name="Invoice", kind="Vocabulary")
    complete_cap(core, "cli/x", "X", "Missing")
    app = project(tmp_path, "app", "core")
    return core, app


def test_ac23_capabilities_add_at_an_inherited_path_is_refused(tcw, tmp_path):
    """AC 23, bullet 1: `tcw capabilities add cli/x` in `app` exits 3 with a
    message containing `core.capabilities/cli/x` and `tcw capabilities set`,
    and writes nothing."""
    _, app = _ac1_family(tmp_path)
    before = snapshot(app)
    ran = tcw(["capabilities", "add", "cli/x"], app)
    assert ran.code == 3, ran.err
    assert "core.capabilities/cli/x" in ran.err
    assert "tcw capabilities set" in ran.err
    assert snapshot(app) == before


def test_ac23_taxonomy_add_with_nothing_differing_is_refused(tcw, tmp_path):
    """AC 23, bullet 2: `tcw taxonomy add Invoice` with nothing on standard
    input exits 3 with a message containing `core.taxonomy/invoice` and
    `nothing given differs`, and writes nothing."""
    _, app = _ac1_family(tmp_path)
    before = snapshot(app)
    ran = tcw(["taxonomy", "add", "Invoice"], app, stdin="")
    assert ran.code == 3, ran.err
    assert "core.taxonomy/invoice" in ran.err
    assert "nothing given differs" in ran.err
    assert snapshot(app) == before


def test_ac23_taxonomy_add_with_a_description_writes_an_override(tcw, tmp_path):
    """AC 23, bullet 3: `printf 'App text' | tcw taxonomy add Invoice` exits
    0, writes `app`'s `docs/taxonomy/invoice/tcw-taxonomy.yaml` whose keys are
    exactly `tcw-version`, and `description.md` holding `App text`; standard
    error has `app.taxonomy/invoice overrides core.taxonomy/invoice`; `show
    invoice` then has `name` `Invoice`, `kind` `Vocabulary`, description `App
    text` and `overrides` `core.taxonomy/invoice`."""
    _, app = _ac1_family(tmp_path)
    ran = tcw(["taxonomy", "add", "Invoice"], app, stdin="App text")
    assert ran.code == 0, ran.err
    folder = app / "docs/taxonomy/invoice"
    assert keys(folder / TAXONOMY_STATE) == {VERSION_KEY}
    assert (folder / "description.md").read_text() == "App text"
    assert "app.taxonomy/invoice overrides core.taxonomy/invoice" in ran.err
    record = show(tcw, app, "taxonomy", "invoice")
    assert record["name"] == "Invoice"
    assert record["kind"] == "Vocabulary"
    assert record["description"] == "App text"
    assert record["overrides"] == "core.taxonomy/invoice"


def test_ac23_taxonomy_add_writes_a_differing_name_and_never_relates_to(
        tcw, tmp_path):
    """AC 23, bullet 4: with `core`'s `invoice` holding `relatesTo:
    [core.taxonomy/money]`, `tcw taxonomy add 'Bill' --slug invoice` writes a
    state file whose keys are exactly `tcw-version` and `name` (`Bill`), and
    `show invoice` keeps `relatesTo` `["core.taxonomy/money"]`."""
    core = project(tmp_path, "core")
    term(core, "money", description="", name="Money", kind="Vocabulary")
    term(core, "invoice", description="Core text", name="Invoice", kind="Vocabulary",
         relatesTo=["core.taxonomy/money"])
    app = project(tmp_path, "app", "core")
    ran = tcw(["taxonomy", "add", "Bill", "--slug", "invoice"], app, stdin="")
    assert ran.code == 0, ran.err
    state = app / "docs/taxonomy/invoice" / TAXONOMY_STATE
    assert keys(state) == {VERSION_KEY, "name"}
    assert mapping(state) == {"name": "Bill"}
    assert show(tcw, app, "taxonomy", "invoice")["relatesTo"] == ["core.taxonomy/money"]


def test_ac24_reset_removes_the_override_by_its_path(tcw, tmp_path):
    """AC 24, sentence 1, by id-path: after AC 20, `tcw capabilities reset
    cli/x` in `app` removes `app`'s `docs/capabilities/cli/x`, and `show
    cli/x` then has `full-id` `core.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path, override=False)
    assert tcw(["capabilities", "set", "cli/x", "--status", "Supported"], app).code == 0
    ran = tcw(["capabilities", "reset", "cli/x"], app)
    assert ran.code == 0, ran.err
    assert not (app / "docs/capabilities/cli/x").exists()
    assert show(tcw, app, "capabilities", "cli/x")["full-id"] == "core.capabilities/cli/x"


@pytest.mark.parametrize("target", ["core.capabilities/cli/x", "app.capabilities/cli/x"])
def test_ac24_reset_by_a_full_identifier_in_the_chain(tcw, tmp_path, target):
    """AC 24, sentence 1, `the same with reset core.capabilities/cli/x`; and
    choice 9's other accepted input, the project's own full identifier."""
    _, app = ac5_family(tmp_path, override=False)
    assert tcw(["capabilities", "set", "cli/x", "--status", "Supported"], app).code == 0
    ran = tcw(["capabilities", "reset", target], app)
    assert ran.code == 0, ran.err
    assert not (app / "docs/capabilities/cli/x").exists()
    assert show(tcw, app, "capabilities", "cli/x")["full-id"] == "core.capabilities/cli/x"


def test_ac24_reset_of_a_standalone_capability_points_at_rm(tcw, tmp_path):
    """AC 24, sentence 2, first case: `reset cli/y` of a standalone `cli/y`
    exits 3 with a message containing `tcw capabilities rm`."""
    _, app = ac5_family(tmp_path)
    complete_cap(app, "cli/y", "Y", "Missing")
    before = snapshot(app)
    ran = tcw(["capabilities", "reset", "cli/y"], app)
    assert ran.code == 3, ran.err
    assert "tcw capabilities rm" in ran.err
    assert snapshot(app) == before


def test_ac24_reset_with_no_own_object_is_refused(tcw, tmp_path):
    """AC 24, sentence 2, second case: `reset cli/x` with no `app` object
    exits 3."""
    _, app = ac5_family(tmp_path, override=False)
    before = snapshot(app)
    assert tcw(["capabilities", "reset", "cli/x"], app).code == 3
    assert snapshot(app) == before


def test_ac24_reset_refuses_while_another_own_object_references_the_override(
        tcw, tmp_path):
    """AC 24, last sentence: with `app`'s `cli/y` holding `Blocked by:
    app.capabilities/cli/x`, `reset cli/x` exits 3 with a message naming
    `app.capabilities/cli/y` and `Blocked by`, and removes nothing."""
    _, app = ac5_family(tmp_path)
    complete_cap(app, "cli/y", "Y", "Blocked",
                 **{"Blocked by": ["app.capabilities/cli/x"]})
    before = snapshot(app)
    ran = tcw(["capabilities", "reset", "cli/x"], app)
    assert ran.code == 3, ran.err
    assert "app.capabilities/cli/y" in ran.err
    assert "Blocked by" in ran.err
    assert snapshot(app) == before


def test_ac25_rm_of_a_capability_override_says_what_the_path_now_shows(
        tcw, tmp_path):
    """AC 25, sentence 1, the capability: `tcw capabilities rm cli/x` of
    `app`'s override exits 0, removes the folder, and standard error has
    `cli/x now shows core.capabilities/cli/x`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "rm", "cli/x"], app)
    assert ran.code == 0, ran.err
    assert not (app / "docs/capabilities/cli/x").exists()
    assert "cli/x now shows core.capabilities/cli/x" in ran.err


def test_ac25_rm_of_a_term_override_says_what_the_path_now_shows(tcw, tmp_path):
    """AC 25, sentence 1, the term: `tcw taxonomy rm invoice` of AC 8's
    override likewise names `core.taxonomy/invoice`."""
    _, app = _ac8_family(tmp_path)
    ran = tcw(["taxonomy", "rm", "invoice"], app)
    assert ran.code == 0, ran.err
    assert not (app / "docs/taxonomy/invoice").exists()
    assert "invoice now shows core.taxonomy/invoice" in ran.err


def test_ac25_rm_of_another_projects_object_is_refused(tcw, tmp_path):
    """AC 25, last sentence: `tcw capabilities rm core.capabilities/cli/x` in
    `app` exits 3 with a message containing `belongs to project 'core'`, and
    removes nothing (in `app` or in `core`)."""
    core, app = ac5_family(tmp_path)
    before_app, before_core = snapshot(app), snapshot(core)
    ran = tcw(["capabilities", "rm", "core.capabilities/cli/x"], app)
    assert ran.code == 3, ran.err
    assert "belongs to project 'core'" in ran.err
    assert snapshot(app) == before_app
    assert snapshot(core) == before_core


def _three_levels(tmp_path):
    """`app` over `lib` over `core`, `lib` overriding `core`'s `cli/x` with
    only `Priority: P1`."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing", "Core body")
    lib = project(tmp_path, "lib", "core")
    cap(lib, "cli/x", Priority="P1")
    app = project(tmp_path, "app", "lib")
    return core, lib, app


def test_choice9_set_and_reset_by_any_member_of_a_three_level_chain(tcw, tmp_path):
    """Plan Step 8, choice 9: in `app` over `lib` over `core` (`lib` overriding
    `core`'s `cli/x`), `tcw capabilities set core.capabilities/cli/x --field
    Priority=P2` writes `app`'s own `cli/x` (any member of the chain, not only
    the second), and `reset core.capabilities/cli/x` then removes it."""
    core, lib, app = _three_levels(tmp_path)
    before_core, before_lib = snapshot(core), snapshot(lib)
    ran = tcw(["capabilities", "set", "core.capabilities/cli/x", "--field",
               "Priority=P2"], app)
    assert ran.code == 0, ran.err
    assert mapping(app / CAP_X) == {"Priority": "P2"}
    assert snapshot(core) == before_core and snapshot(lib) == before_lib
    record = show(tcw, app, "capabilities", "cli/x")
    assert record["full-id"] == "app.capabilities/cli/x"
    assert record["overrides"] == "lib.capabilities/cli/x"
    ran = tcw(["capabilities", "reset", "core.capabilities/cli/x"], app)
    assert ran.code == 0, ran.err
    assert not (app / "docs/capabilities/cli/x").exists()


def test_ac42_clearing_a_field_writes_null_on_an_object_that_overrides_nothing(
        tcw, tmp_path):
    """AC 42 at the CLI, first half (plan Step 8): `app` has no parents and
    its own complete `cli/y` holding `Priority: P1`; `tcw capabilities set
    cli/y --field Priority=` leaves `Priority: null` in the file and no
    `Priority` in `show`."""
    app = project(tmp_path, "app")
    state = complete_cap(app, "cli/y", "Y", "Missing", Priority="P1")
    ran = tcw(["capabilities", "set", "cli/y", "--field", "Priority="], app)
    assert ran.code == 0, ran.err
    held = mapping(state)
    assert "Priority" in held and held["Priority"] is None
    assert "Priority" not in show(tcw, app, "capabilities", "cli/y")["fields"]


def test_ac42_clearing_a_field_on_an_override_writes_null_over_the_original(
        tcw, tmp_path):
    """AC 42 at the CLI, last sentence's shape (plan Step 8): the same `set`
    on `app`'s override `cli/x` leaves `Priority: null` in `app`'s file, and
    `show cli/x` has no `Priority` although `core`'s `cli/x` has `Priority:
    P1`."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["capabilities", "set", "cli/x", "--field", "Priority="], app)
    assert ran.code == 0, ran.err
    held = mapping(app / CAP_X)
    assert "Priority" in held and held["Priority"] is None
    assert held["Status"] == "Supported"
    assert "Priority" not in show(tcw, app, "capabilities", "cli/x")["fields"]


def test_design27_inherited_at_answers_with_and_without_an_own_object(tmp_path):
    """Design 2.7 directly (plan Step 8): `inherited_at("cli/x")` in `app` is
    `core.capabilities/cli/x` with and without `app`'s own `cli/x`, and None
    for a path nothing inherits."""
    _, app = ac5_family(tmp_path, override=False)
    expected = FullId("core", "capabilities", "cli/x")
    assert FsCapabilitiesStore.open(app).inherited_at("cli/x") == expected
    cap(app, "cli/x", Status="Supported")
    cap(app, "cli/own", name="Own", Status="Missing")
    st = FsCapabilitiesStore.open(app)
    assert st.inherited_at("cli/x") == expected
    assert st.inherited_at("cli/own") is None
    assert st.inherited_at("cli/nothing") is None


def _choice9_family(tmp_path):
    """AC 5's family with `app`'s override `cli/x`, `core` also holding
    `cli/z` (which `app` only inherits), and a project `zz`, not one of
    `app`'s sources, holding `cli/x`."""
    core, app = ac5_family(tmp_path)
    complete_cap(core, "cli/z", "Z", "Missing")
    zz = project(tmp_path, "zz")
    complete_cap(zz, "cli/x", "Zz", "Missing")
    write_manifest(app, {"zz": "../zz"})
    return core, app, zz


APP_X = FullId("app", "capabilities", "cli/x")
APP_Z = FullId("app", "capabilities", "cli/z")


@pytest.mark.parametrize("target, expected", [
    ("cli/x", APP_X),                                       # the own override
    ("app.capabilities/cli/x", APP_X),                      # its own full identifier
    ("core.capabilities/cli/x", APP_X),                     # a member of the chain
    ("cli/z", APP_Z),                                       # inherited, no own object
    ("core.capabilities/cli/z", APP_Z),                     # inherited, by its owner
    ("zz.capabilities/cli/x", Refused),                     # not a source
    ("app.capabilities/cli/z", NotFound),                   # own identifier, no object
    ("cli/nothing", NotFound),                              # nothing there
])
def test_choice9_override_target_at_the_store(tmp_path, monkeypatch, target, expected):
    """Choice 9 at the store (plan Step 8): `override_target` called with each
    input form gives the active project's own full identifier or the
    refusal, and `find_tree_writable(..., removing=False)` returns what it
    returns."""
    _, app, _ = _choice9_family(tmp_path)
    monkeypatch.chdir(app)
    st = FsCapabilitiesStore.open(app)
    if isinstance(expected, FullId):
        assert st.override_target(target) == expected
        assert find_tree_writable(st, target, removing=False) == expected
    else:
        with pytest.raises(expected):
            st.override_target(target)
        with pytest.raises(expected):
            find_tree_writable(st, target, removing=False)


@pytest.mark.parametrize("target, expected", [
    ("cli/x", APP_X),                                       # the own override
    ("app.capabilities/cli/x", APP_X),                      # its own full identifier
    ("core.capabilities/cli/x", Refused),                   # another project's
    ("cli/z", Refused),                                     # shown as core's
    ("zz.capabilities/cli/x", Refused),                     # another project's
    ("app.capabilities/cli/z", NotFound),                   # own identifier, no object
    ("cli/nothing", NotFound),                              # nothing there
])
def test_choice9_removal_target_at_the_store(tmp_path, monkeypatch, target, expected):
    """Choice 9 at the store (plan Step 8): `removal_target` called with each
    input form gives the active project's own full identifier or the
    refusal, and `find_tree_writable(..., removing=True)` returns what it
    returns."""
    _, app, _ = _choice9_family(tmp_path)
    monkeypatch.chdir(app)
    st = FsCapabilitiesStore.open(app)
    if isinstance(expected, FullId):
        assert st.removal_target(target) == expected
        assert find_tree_writable(st, target, removing=True) == expected
    else:
        with pytest.raises(expected):
            st.removal_target(target)
        with pytest.raises(expected):
            find_tree_writable(st, target, removing=True)


@pytest.mark.parametrize("verb", [
    ["set", "app.capabilities/cli/z", "--status", "Supported"],
    ["reset", "app.capabilities/cli/z"],
    ["rm", "app.capabilities/cli/z"],
])
def test_choice9_own_identifier_of_a_path_only_inherited_is_not_found(
        tcw, tmp_path, verb):
    """Choice 9's not found (plan Step 8): `set`, `reset` and `rm` of
    `app.capabilities/cli/z` in `app`, which only inherits `cli/z`, exit 4
    and write nothing, as `show` of that identifier does (AC 26)."""
    core, app, _ = _choice9_family(tmp_path)
    before_app, before_core = snapshot(app), snapshot(core)
    ran = tcw(["capabilities", *verb], app)
    assert ran.code == 4, ran.err
    assert snapshot(app) == before_app
    assert snapshot(core) == before_core


def test_choice9_set_of_a_project_that_is_not_a_source_is_refused(tcw, tmp_path):
    """Choice 9's early refusal (plan Step 8): `set zz.capabilities/cli/x`,
    `zz` not one of `app`'s sources, exits 3 with Design 4.2's message, and
    writes nothing."""
    _, app, zz = _choice9_family(tmp_path)
    before_app, before_zz = snapshot(app), snapshot(zz)
    ran = tcw(["capabilities", "set", "zz.capabilities/cli/x", "--status",
               "Supported"], app)
    assert ran.code == 3, ran.err
    assert ("zz.capabilities/cli/x belongs to project 'zz', and 'app' does not "
            "inherit it, so it cannot be overridden here; change it in 'zz'") in ran.err
    assert snapshot(app) == before_app
    assert snapshot(zz) == before_zz


# == Step 9: the `overrides:` key is reported =============================================


def test_ac29_an_overrides_key_is_an_error_and_the_object_still_combines(
        tcw, tmp_path):
    """AC 29: `app`'s `cli/x` holding `overrides: core/cap-1a2b3c` and
    `Status: Supported` makes `tcw validate` report an error at that file
    containing `'overrides' was removed in TCW 4.0`, and `show cli/x` in
    `app` still combines it with `core`'s `cli/x` (AC 5's result)."""
    _, app = ac5_family(tmp_path, override=False)
    cap(app, "cli/x", overrides="core/cap-1a2b3c", Status="Supported")
    ran = tcw(["validate"], app)
    assert ran.code == 1, ran.out + ran.err
    errors = [f for f in findings(ran)
              if f.startswith("error:") and "'overrides' was removed in TCW 4.0" in f]
    assert len(errors) == 1, ran.out
    assert CAP_X in errors[0]
    record = show(tcw, app, "capabilities", "cli/x")
    assert record["full-id"] == "app.capabilities/cli/x"
    assert record["name"] == "X"
    assert record["fields"]["Status"] == "Supported"
    assert record["fields"]["Priority"] == "P1"
    assert "overrides" not in record["fields"]
    assert record["body"] == "Core body"
    assert record["overrides"] == "core.capabilities/cli/x"


# == Step 10: the opaque `id` goes ========================================================


def test_ac28_show_has_no_id(tcw, tmp_path):
    """AC 28, sentence 1: `show --json` of a capability has no `id` key and
    the text `show` no `id:` line (an own one, an override and an inherited
    one)."""
    core, app = ac5_family(tmp_path)
    complete_cap(app, "cli/y", "Y", "Missing")
    complete_cap(core, "cli/z", "Z", "Missing")
    for target in ("cli/x", "cli/y", "cli/z"):
        record = show(tcw, app, "capabilities", target)
        assert "id" not in record and "id" not in record["fields"], record
        text = tcw(["capabilities", "show", target], app)
        assert text.code == 0, text.err
        assert not [line for line in text.out.splitlines() if line.startswith("id:")]


def test_ac28_an_opaque_id_in_a_state_file_is_an_error_at_that_file(tcw, tmp_path):
    """AC 28, sentence 2: a `tcw-capability.yaml` in folder `cli/x` holding
    `id: cap-1a2b3c` makes `tcw validate` report TCW-111's row k error at
    that file."""
    app = project(tmp_path, "app")
    complete_cap(app, "cli/x", "X", "Missing", id="cap-1a2b3c")
    ran = tcw(["validate"], app)
    assert ran.code == 1, ran.out + ran.err
    errors = [f for f in findings(ran) if f.startswith("error:") and CAP_X in f
              and "id 'cap-1a2b3c' is not its folder's name, 'x'" in f]
    assert len(errors) == 1, ran.out


def test_ac28_an_id_equal_to_the_folders_name_is_no_error(tcw, tmp_path):
    """AC 28, sentence 3: `id: x` in folder `cli/x` gives no error."""
    app = project(tmp_path, "app")
    complete_cap(app, "cli/x", "X", "Missing", id="x")
    ran = tcw(["validate"], app)
    assert not [f for f in findings(ran) if "cli/x" in f], ran.out
    assert ran.code == 0, ran.out + ran.err


def test_ac28_no_id_gives_no_missing_id_finding(tcw, tmp_path):
    """AC 28, last sentence: a capability with no `id` gives no `missing id`
    finding."""
    app = project(tmp_path, "app")
    complete_cap(app, "cli/x", "X", "Missing")
    ran = tcw(["validate"], app)
    assert "missing id" not in ran.out + ran.err
    assert ran.code == 0, ran.out + ran.err


def test_ac23_capabilities_add_writes_no_id(tcw, tmp_path):
    """AC 23, last bullet: `tcw capabilities add cli/new` writes a state file
    with no `id` key."""
    _, app = _ac1_family(tmp_path)
    ran = tcw(["capabilities", "add", "cli/new"], app)
    assert ran.code == 0, ran.err
    state = app / "docs/capabilities/cli/new" / CAPABILITY_STATE
    assert "id" not in keys(state)


# == Step 11: an object that overrides nothing must be complete ===========================


def test_ac13_an_orphaned_partial_capability_is_incomplete(tcw, tmp_path):
    """AC 13, sentence 1-2: `app` has its own `cli/x` holding only `Status:
    Supported`, and no source has `cli/x`; `tcw validate` exits 1 with an
    error at `docs/capabilities/cli/x/tcw-capability.yaml` whose message
    contains `app.capabilities/cli/x is incomplete`, `name` and
    `description.md` (and not `Status`, which it has)."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/other", "Other", "Missing")
    app = project(tmp_path, "app", "core")
    cap(app, "cli/x", Status="Supported")
    ran = tcw(["validate"], app)
    assert ran.code == 1, ran.out + ran.err
    errors = [f for f in findings(ran) if "app.capabilities/cli/x is incomplete" in f]
    assert len(errors) == 1, ran.out
    assert errors[0].startswith(f"error: {CAP_X}: "), errors[0]
    message = errors[0].split(": ", 2)[2]
    assert "name" in message and "description.md" in message
    assert "Status" not in message


def test_ac13_an_orphaned_partial_term_is_incomplete(tcw, tmp_path):
    """AC 13, sentence 3: a term `invoice` holding only `relatesTo` in `app`,
    with no source having `invoice`, gives the same error with `name` and
    `description.md`."""
    core = project(tmp_path, "core")
    term(core, "other", description="", name="Other")
    app = project(tmp_path, "app", "core")
    term(app, "money", description="", name="Money")
    term(app, "invoice", relatesTo=["app.taxonomy/money"])
    ran = tcw(["validate"], app)
    assert ran.code == 1, ran.out + ran.err
    errors = [f for f in findings(ran) if "app.taxonomy/invoice is incomplete" in f]
    assert len(errors) == 1, ran.out
    assert errors[0].startswith(
        f"error: docs/taxonomy/invoice/{TAXONOMY_STATE}: "), errors[0]
    message = errors[0].split(": ", 2)[2]
    assert "name" in message and "description.md" in message


def test_ac13_complete_objects_with_an_empty_description_are_not_incomplete(
        tcw, tmp_path):
    """AC 13, last sentence: a capability with `name`, `Status` and an empty
    `description.md`, and a term with `name` and an empty `description.md`,
    give no such error."""
    app = project(tmp_path, "app")
    complete_cap(app, "cli/x", "X", "Supported", "")
    term(app, "invoice", description="", name="Invoice")
    ran = tcw(["validate"], app)
    assert "incomplete" not in ran.out + ran.err
    assert ran.code == 0, ran.out + ran.err


def test_ac13_an_override_missing_parts_is_never_incomplete(tcw, tmp_path):
    """AC 13 by contrast (Coverage row 6.2): AC 5's override, which has no
    name and no `description.md`, is not reported incomplete."""
    _, app = ac5_family(tmp_path)
    ran = tcw(["validate"], app)
    assert "incomplete" not in ran.out + ran.err


def test_ac14_a_full_copy_whose_original_moved_stands(tcw, tmp_path):
    """AC 14: `app`'s `cli/x` has `name`, `Status` and a `description.md`;
    `core` has no `cli/x`; `tcw validate` in `app` reports nothing about
    `cli/x`."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/moved", "X", "Missing", "Core body")
    app = project(tmp_path, "app", "core")
    complete_cap(app, "cli/x", "X", "Missing", "Core body")
    ran = tcw(["validate"], app)
    assert not [f for f in findings(ran) if "cli/x" in f], ran.out


# == Step 15: each own object is checked as the project sees it ===========================


def test_ac34_a_nested_override_is_not_a_misplaced_folder(tcw, tmp_path):
    """AC 34: `core` has `cli/x` and `cli/x/y` (whose `parent` is
    `core.capabilities/cli/x`); `app` overrides both, holding only `Status` in
    each; `tcw validate` in `app` gives no TCW-111 Design 3.2 warning for
    `cli/x/y`."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing")
    complete_cap(core, "cli/x/y", "Y", "Missing", parent="core.capabilities/cli/x")
    app = project(tmp_path, "app", "core")
    cap(app, "cli/x", Status="Supported")
    cap(app, "cli/x/y", Status="Supported")
    ran = tcw(["validate"], app)
    assert not [f for f in findings(ran) if "sits in the folder of" in f], ran.out
    assert not [w for w in warnings(ran) if "cli/x/y" in w], ran.out


def test_ac40_a_term_named_only_by_an_override_cannot_be_removed(tcw, tmp_path):
    """AC 40: `app`'s term `money` is named only in the `Subject` of `app`'s
    override `cli/x` (which `core`'s `cli/x` does not name); `tcw taxonomy rm
    money` in `app` exits 3 with a message naming `cli/x` and `Subject`, and
    removes nothing."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing", "Core body")
    app = project(tmp_path, "app", "core")
    term(app, "money", description="", name="Money")
    cap(app, "cli/x", Subject=["app.taxonomy/money"])
    before = snapshot(app)
    ran = tcw(["taxonomy", "rm", "money"], app)
    assert ran.code == 3, ran.err
    assert "cli/x" in ran.err and "Subject" in ran.err
    assert snapshot(app) == before


def test_ac41_partial_requires_gaps_on_the_combined_object(tcw, tmp_path):
    """AC 41, sentence 1: `app`'s override `cli/x` holding only `Status:
    Partial`, over `core`'s `cli/x` with no `Gaps`, makes `tcw validate` in
    `app` report `Partial requires Gaps` at `app`'s `cli/x`."""
    _, app = ac5_family(tmp_path, override=False)
    cap(app, "cli/x", Status="Partial")
    ran = tcw(["validate"], app)
    assert ran.code == 1, ran.out + ran.err
    hits = [f for f in findings(ran) if "Partial requires Gaps" in f]
    assert len(hits) == 1, ran.out
    # `check` places a field problem at the object's folder.
    assert hits[0].startswith("error: docs/capabilities/cli/x"), hits[0]


def test_ac41_gaps_in_the_original_satisfy_the_check(tcw, tmp_path):
    """AC 41, sentence 2: `core`'s `cli/x` holding `Gaps: something` makes it
    pass."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing", "Core body", Gaps="something")
    app = project(tmp_path, "app", "core")
    cap(app, "cli/x", Status="Partial")
    ran = tcw(["validate"], app)
    assert "Partial requires Gaps" not in ran.out + ran.err
    assert ran.code == 0, ran.out + ran.err


def test_ac41_an_inherited_reference_is_not_checked_in_the_inheritor(tcw, tmp_path):
    """AC 41, last sentence: `core`'s `cli/x` holding `Blocked by:
    core.capabilities/gone` (no such object) gives `app`'s `tcw validate` no
    finding naming `core.capabilities/gone`, since `app` does not declare
    that reference."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Blocked", "Core body",
                 **{"Blocked by": ["core.capabilities/gone"]})
    app = project(tmp_path, "app", "core")
    cap(app, "cli/x", Priority="P2")
    ran = tcw(["validate"], app)
    assert "core.capabilities/gone" not in ran.out + ran.err


def test_ac42_validate_reports_nothing_about_a_cleared_field(tcw, tmp_path):
    """AC 42, `tcw validate` sentence: after `Priority` is cleared to `null`
    on `app`'s own `cli/y`, `tcw validate` reports nothing about `cli/y`
    (the value checks read the combined object, where `null` leaves no
    field)."""
    app = project(tmp_path, "app")
    complete_cap(app, "cli/y", "Y", "Missing", Priority=None)
    ran = tcw(["validate"], app)
    assert not [f for f in findings(ran) if "cli/y" in f], ran.out
    assert ran.code == 0, ran.out + ran.err


# == Step 16: drift =======================================================================


def test_ac32_drift_names_an_override_that_never_set_status(tcw, tmp_path):
    """AC 32: `app` inherits `cli/x` and `cli/y` from `core`; `app`'s own
    `cli/x` sets `Status`, and its own `cli/y` sets only `Priority`; `tcw
    capabilities drift` prints an `unreviewed:` line for `cli/y` and none for
    `cli/x`."""
    core = project(tmp_path, "core")
    complete_cap(core, "cli/x", "X", "Missing")
    complete_cap(core, "cli/y", "Y", "Missing")
    app = project(tmp_path, "app", "core")
    cap(app, "cli/x", Status="Supported")
    cap(app, "cli/y", Priority="P2")
    ran = tcw(["capabilities", "drift"], app)
    unreviewed = [line for line in ran.out.splitlines() if line.startswith("unreviewed:")]
    assert [line for line in unreviewed if "cli/y" in line], ran.out + ran.err
    assert not [line for line in unreviewed if "cli/x" in line], ran.out
