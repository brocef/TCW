"""When inherited content cannot be read (TCW-112 Design 1.3, 1.4, 3.1, 3.4,
3.5, 4.4, 6.5 and 7.2; AC 16, 18's `--local`, 26's last three sentences, 35
and 39), and the order in which a write is refused when it cannot be
(the plan's choice 9).

A parent "not on this machine" is one whose manifest entry names a folder
that does not exist. The helpers, and the `tcw` and `home` fixtures, are
`tests/test_tree_inheritance.py`'s."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests.projectfiles import write_manifest
from tests.statefiles import CAPABILITY_STATE, read_state, write_state
from tests.test_tree_inheritance import (capability, core_with_unprovisioned_taxonomy,
                                         findings, home, inherits, listed, project,
                                         tcw, term)  # noqa: F401  (fixtures)

NOT_HERE = "'app' inherits its taxonomy from project 'core', which is not on this machine"
SHOWING_ONLY = "showing only 'app''s own declarations"


def tree_hash(root: Path) -> str:
    """Every file under `root`'s `docs/`, by path and content."""
    h = hashlib.sha256()
    for f in sorted((root / "docs").rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(root)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


# -- AC 16: a parent not on this machine --------------------------------------------------


@pytest.fixture
def app(tmp_path) -> Path:
    """AC 16's `app`: it inherits from `core`, whose manifest entry names a
    folder that does not exist; it has its own term `money`, its own
    complete capability `cli/y`, and an override `cli/x` holding only
    `Status: Supported`."""
    app = project(tmp_path, "app")
    term(app, "money", name="Money", kind="Vocabulary", description="")
    capability(app, "cli/y", name="Y", Status="Missing", description="")
    capability(app, "cli/x", Status="Supported")
    inherits(app, tmp_path / "core")
    assert not (tmp_path / "core").exists()
    return app


def test_ac16_list_local_prints_the_projects_own_objects(app, tcw):
    """AC 16, first bullet: `tcw taxonomy list --local` prints
    `app.taxonomy/money`, and `tcw capabilities list --local` prints
    `app.capabilities/cli/x` and `app.capabilities/cli/y`."""
    assert listed(tcw(app, "taxonomy", "list")) == ["app.taxonomy/money"]
    assert sorted(listed(tcw(app, "capabilities", "list"))) == [
        "app.capabilities/cli/x", "app.capabilities/cli/y"]


@pytest.mark.parametrize("given", ["money", "app.taxonomy/money"])
def test_ac16_show_of_an_own_term_works_with_a_warning(app, tcw, given):
    """AC 16, second bullet: `tcw taxonomy show money` and `tcw taxonomy show
    app.taxonomy/money` exit 0 with a standard error line containing
    `showing only 'app''s own declarations`."""
    ran = tcw(app, "taxonomy", "show", given)
    assert ran.code == 0, ran
    assert [line for line in ran.err.splitlines() if SHOWING_ONLY in line], ran
    assert "full-id: app.taxonomy/money" in ran.out.splitlines()


def test_ac16_show_json_of_an_override_is_partial_with_no_overrides_key(app, tcw):
    """AC 16, second bullet: `tcw capabilities show cli/x --json` exits 0 and
    its record has `"partial": true` and no `overrides` key."""
    ran = tcw(app, "capabilities", "show", "cli/x", "--json")
    assert ran.code == 0, ran
    shown = json.loads(ran.out)["capability"]
    assert shown["partial"] is True
    assert "overrides" not in shown


def test_ac16_text_show_has_a_partial_line_and_no_overrides_line(app, tcw):
    """AC 16, second bullet: the text `show cli/x` has a `partial:` line and
    no `overrides:` line."""
    ran = tcw(app, "capabilities", "show", "cli/x")
    assert ran.code == 0, ran
    lines = ran.out.splitlines()
    assert "partial: inherited content could not be read" in lines, lines
    assert not any(line.startswith("overrides:") for line in lines), lines


def test_ac16_every_list_local_json_record_is_partial(app, tcw):
    """AC 16, second bullet: each record of `tcw capabilities list --local
    --json` has `"partial": true`."""
    ran = tcw(app, "capabilities", "list", "--json")
    assert ran.code == 0, ran
    records = json.loads(ran.out)["capabilities"]
    assert len(records) == 2
    assert all(r["partial"] is True and "overrides" not in r for r in records), records


@pytest.mark.parametrize("argv", [
    ("taxonomy", "list", "--scope", "up"), ("taxonomy", "search", "a", "--scope", "up"),
    ("taxonomy", "show", "invoice", "--scope", "up"), ("taxonomy", "add", "Invoice"),
], ids=["list", "search", "show-inherited", "add"])
def test_ac16_taxonomy_commands_needing_the_view_exit_7(app, tcw, argv):
    """AC 16, third bullet: `tcw taxonomy list`, `search a`, `show invoice`
    and `add Invoice` exit 7 with a message containing `'app' inherits its
    taxonomy from project 'core', which is not on this machine` (and `add`
    writes nothing)."""
    before = tree_hash(app)
    ran = tcw(app, *argv)
    assert ran.code == 7, ran
    assert NOT_HERE in ran.err, ran
    assert tree_hash(app) == before


def test_ac16_set_and_rm_of_an_own_complete_capability_work(app, tcw):
    """AC 16, fourth bullet: `tcw capabilities set cli/y --status Supported`
    and `tcw capabilities rm cli/y` exit 0."""
    state = app / "docs" / "capabilities" / "cli" / "y" / CAPABILITY_STATE
    ran = tcw(app, "capabilities", "set", "cli/y", "--status", "Supported")
    assert ran.code == 0, ran
    assert read_state(state)["Status"] == "Supported"
    ran = tcw(app, "capabilities", "rm", "cli/y")
    assert ran.code == 0, ran
    assert not state.parent.exists()


@pytest.mark.parametrize("argv", [
    ("capabilities", "set", "cli/z", "--status", "Supported"),
    ("capabilities", "reset", "cli/x"),
    ("capabilities", "drift"),
], ids=["set-of-an-id-path-not-own", "reset", "drift"])
def test_ac16_capability_commands_needing_the_view_exit_7(app, tcw, argv):
    """AC 16, fourth bullet: `set cli/z --status Supported` (an id-path `app`
    has no object at), `reset cli/x` and `drift` exit 7, and change
    nothing; and (Step 16) `drift` prints nothing on standard output."""
    before = tree_hash(app)
    ran = tcw(app, *argv)
    assert ran.code == 7, ran
    assert "'app' inherits its capabilities from project 'core'" in ran.err, ran
    assert ran.out == ""
    assert tree_hash(app) == before


def test_ac16_rm_of_an_id_path_with_no_own_object_is_not_found(app, tcw):
    """AC 16, fourth bullet: `tcw capabilities rm cli/z` exits 4."""
    before = tree_hash(app)
    ran = tcw(app, "capabilities", "rm", "cli/z")
    assert ran.code == 4, ran
    assert tree_hash(app) == before


def test_ac16_validate_reports_one_could_not_check_finding_and_exits_0(app, tcw):
    """AC 16, fifth bullet: `tcw validate` exits 0, with one `unresolved`
    finding for `core` containing `could not check the taxonomy inherited
    from it` and `could not check the capabilities inherited from it`, and
    no `incomplete` error for `cli/x`."""
    ran = tcw(app, "validate")
    assert ran.code == 0, ran
    unresolved = [line for line in findings(ran) if line.startswith("unresolved:")]
    assert len(unresolved) == 1, findings(ran)
    assert "'core'" in unresolved[0]
    assert "could not check the taxonomy inherited from it" in unresolved[0]
    assert "could not check the capabilities inherited from it" in unresolved[0]
    assert not any("incomplete" in line for line in findings(ran)), findings(ran)


def test_ac16_validate_still_checks_what_app_declares(app, tcw):
    """AC 16, fifth bullet, last sentence: with `app`'s `cli/y` also holding
    the unknown field `Foo: 1`, `tcw validate` exits 1 with that field's
    error at `cli/y`'s state file."""
    capability(app, "cli/y", name="Y", Status="Missing", Foo=1, description="")
    ran = tcw(app, "validate")
    assert ran.code == 1, ran
    errors = [line for line in findings(ran) if line.startswith("error:")]
    assert len(errors) == 1, findings(ran)
    assert errors[0].split(": ", 2)[1].endswith(f"docs/capabilities/cli/y/{CAPABILITY_STATE}")
    assert "Foo" in errors[0]


# -- AC 18: `--local` with a parent whose store cannot be read ---------------------------


def test_ac18_list_local_works_when_a_parents_store_cannot_be_read(tmp_path, tcw):
    """AC 18, the `--local` sentence: with opening `core`'s taxonomy store
    raising `StoreNotProvisioned`, `tcw taxonomy list --local` in `app`
    exits 0 (and prints `app`'s own term)."""
    app = core_with_unprovisioned_taxonomy(tmp_path)
    assert listed(tcw(app, "taxonomy", "list")) == ["app.taxonomy/money"]


# -- AC 26: a full identifier when an ancestor of its owner is missing --------------------


@pytest.fixture
def family(tmp_path) -> Path:
    """AC 9's family: `bb` has `X` with `Status: Missing`; `cc` and `dd`
    inherit from `bb`; `cc` has its own `X` holding `Status: Supported`;
    `ee` has `parents: [cc, dd]`. And AC 26's `zz`, with no parents, whose
    manifest locates `cc`, with its own capability `q` holding `Blocked by:
    cc.capabilities/X` and a description linking to it. Returns the folder
    holding them."""
    bb = project(tmp_path, "bb")
    capability(bb, "X", name="X", Status="Missing", description="")
    cc, dd = project(tmp_path, "cc"), project(tmp_path, "dd")
    inherits(cc, bb)
    inherits(dd, bb)
    capability(cc, "X", Status="Supported")
    ee = project(tmp_path, "ee")
    inherits(ee, cc, dd, located={"bb": "../bb"})
    zz = project(tmp_path, "zz")
    capability(zz, "q", name="Q", Status="Blocked", **{"Blocked by": "cc.capabilities/X"},
               description="Waits for tcw://cc.capabilities/X.\n")
    write_manifest(zz, {"cc": "../cc", "bb": "../bb"})
    return tmp_path


def test_ac26_premise_the_full_identifier_resolves_with_everything_present(family, tcw):
    """AC 26's premise: with every folder present, `show cc.capabilities/X`
    in `ee` works and `zz`'s `tcw validate` names nothing about it."""
    assert tcw(family / "ee", "capabilities", "show", "cc.capabilities/X").code == 0
    ran = tcw(family / "zz", "validate")
    assert not any("cc.capabilities/X" in line for line in findings(ran)), findings(ran)


def test_ac26_show_of_a_full_identifier_whose_owners_parent_is_gone_exits_7(family, tcw):
    """AC 26: with `bb`'s folder removed (its manifest entry kept), `show
    cc.capabilities/X` in `ee` exits 7 with a message containing `'cc'
    inherits its capabilities from project 'bb'`."""
    shutil.rmtree(family / "bb")
    ran = tcw(family / "ee", "capabilities", "show", "cc.capabilities/X")
    assert ran.code == 7, ran
    assert "'cc' inherits its capabilities from project 'bb'" in ran.err, ran


def test_ac26_show_of_a_full_identifier_whose_owner_is_gone_exits_5(family, tcw):
    """AC 26: with `cc`'s folder removed instead, `show cc.capabilities/X` in
    `ee` exits 5."""
    shutil.rmtree(family / "cc")
    ran = tcw(family / "ee", "capabilities", "show", "cc.capabilities/X")
    assert ran.code == 5, ran


def test_ac26_a_reference_needs_only_its_owners_own_store(family, tcw):
    """AC 26, last sentence: with `bb`'s folder removed, `tcw validate` in
    `zz` reports no finding that names `cc.capabilities/X` (the `Blocked by`
    reference)."""
    shutil.rmtree(family / "bb")
    ran = tcw(family / "zz", "validate")
    assert not any("cc.capabilities/X" in line for line in findings(ran)), findings(ran)


def test_step13_a_link_needs_only_its_owners_own_store(family, tcw):
    """Plan Step 13 (Design 3.1, existence without the view): a
    `tcw://cc.capabilities/X` link in `zz`'s description, with `bb`'s folder
    removed, gives `tcw validate` in `zz` no finding for the link."""
    shutil.rmtree(family / "bb")
    ran = tcw(family / "zz", "validate")
    assert not any("tcw://cc.capabilities/X" in line for line in findings(ran)), \
        findings(ran)
    assert ran.code == 0, ran


# -- the refusal order (plan choice 9), in AC 5's family with `core` gone -----------------


@pytest.fixture
def app_of_ac5(tmp_path) -> Path:
    """AC 5's `app` (its own `cli/x` holding only `Status: Supported`) with
    `core`'s folder removed, its manifest entry kept; and a project `zz`
    with its own `cli/x`, located by `app`'s manifest but not one of
    `app`'s parents."""
    app = project(tmp_path, "app")
    capability(app, "cli/x", Status="Supported")
    inherits(app, tmp_path / "core", located={"zz": "../zz"})
    zz = project(tmp_path, "zz")
    capability(zz, "cli/x", name="X", Status="Missing", description="")
    assert not (tmp_path / "core").exists()
    return app


@pytest.mark.parametrize("argv, full_id", [
    (("capabilities", "rm", "core.capabilities/cli/x"), "core.capabilities/cli/x"),
    (("taxonomy", "rm", "core.taxonomy/invoice"), "core.taxonomy/invoice"),
], ids=["capability", "term"])
def test_choice9_rm_of_another_projects_object_is_refused_before_reading(
        app_of_ac5, tcw, argv, full_id):
    """Plan choice 9 (Design 4.4): `rm` of `core`'s full identifier in `app`,
    `core` not on this machine, exits 3 with `<fid> belongs to project
    'core'` (TCW-114 Design 1.3's one shape), not 7."""
    before = tree_hash(app_of_ac5)
    ran = tcw(app_of_ac5, *argv)
    assert ran.code == 3, ran
    assert f"{full_id} belongs to project 'core'; project 'core' is not on this " \
           f"machine" in ran.err, ran
    assert "cannot remove" not in ran.err
    assert tree_hash(app_of_ac5) == before


def test_choice9_set_of_a_project_not_inherited_from_is_refused_before_reading(
        app_of_ac5, tcw):
    """Plan choice 9 (Design 4.2): `set zz.capabilities/cli/x --status
    Supported`, `zz` not one of `app`'s sources, exits 3 with `belongs to
    project 'zz', and 'app' does not inherit it`, not 7."""
    before = tree_hash(app_of_ac5)
    ran = tcw(app_of_ac5, "capabilities", "set", "zz.capabilities/cli/x",
              "--status", "Supported")
    assert ran.code == 3, ran
    assert ("zz.capabilities/cli/x belongs to project 'zz', and 'app' does not "
            "inherit it") in ran.err, ran
    assert tree_hash(app_of_ac5) == before


def test_choice9_set_of_a_sources_full_identifier_needs_the_view(app_of_ac5, tcw):
    """Plan choice 9: `set core.capabilities/cli/x --status Supported` exits
    7, since whether it is in the chain needs the view."""
    before = tree_hash(app_of_ac5)
    ran = tcw(app_of_ac5, "capabilities", "set", "core.capabilities/cli/x",
              "--status", "Supported")
    assert ran.code == 7, ran
    assert tree_hash(app_of_ac5) == before


# -- AC 35: a single project opens no other ---------------------------------------------


@pytest.fixture
def opened(monkeypatch):
    """Records each tree store root opened (`FsTreeStore.__init__`) and each
    project ID looked up (`FsProjectRegistry.project_folder`)."""
    from tcw.store.fs import FsTreeStore
    from tcw.store.project import FsProjectRegistry
    seen = {"roots": [], "ids": []}
    real_init, real_folder = FsTreeStore.__init__, FsProjectRegistry.project_folder

    def init(self, root, *args, **kwargs):
        seen["roots"].append(Path(root).resolve())
        return real_init(self, root, *args, **kwargs)

    def folder(self, project_id, named_by):
        seen["ids"].append(project_id)
        return real_folder(self, project_id, named_by)

    monkeypatch.setattr(FsTreeStore, "__init__", init)
    monkeypatch.setattr(FsProjectRegistry, "project_folder", folder)
    return seen


@pytest.mark.parametrize("argv, trees", [
    (("taxonomy", "list"), {"taxonomy"}),
    (("capabilities", "list"), {"taxonomy", "capabilities"}),
    (("validate",), {"taxonomy", "capabilities"}),
], ids=["taxonomy-list", "capabilities-list", "validate"])
def test_ac35_a_project_with_no_parents_opens_no_other_store(
        tmp_path, tcw, opened, argv, trees):
    """AC 35: in a project with no parents, each of `tcw taxonomy list`, `tcw
    capabilities list` and `tcw validate` opens only stores whose root is the
    project's own `docs/taxonomy` or `docs/capabilities` (`tcw taxonomy list`
    no capabilities store), and calls `project_folder` with no ID other
    than the project's own."""
    solo = project(tmp_path, "solo")
    term(solo, "money", name="Money", kind="Vocabulary", description="")
    capability(solo, "cli/x", name="X", Status="Missing", description="")
    project(tmp_path, "other")                     # a neighbour that must stay unread
    ran = tcw(solo, *argv)
    assert ran.code == 0, ran
    allowed = {(solo / "docs" / tree).resolve() for tree in trees}
    assert opened["roots"], "the recording saw no store opened"
    assert set(opened["roots"]) <= allowed, opened["roots"]
    if argv == ("taxonomy", "list"):
        assert (solo / "docs" / "capabilities").resolve() not in opened["roots"]
    assert set(opened["ids"]) <= {"solo"}, opened["ids"]


# -- AC 39: a source object with a version problem ---------------------------------------


@pytest.fixture
def newer(tmp_path) -> Path:
    """AC 39's `core`: its `cli/x` state file says `tcw-version: 99.0.0`, and
    it has `cli/w`; `app` inherits from it. Returns `app`."""
    core = project(tmp_path, "core")
    folder = core / "docs" / "capabilities" / "cli" / "x"
    write_state(folder / CAPABILITY_STATE, "tcw-version: 99.0.0\nname: X\nStatus: Missing\n")
    (folder / "description.md").write_text("")
    capability(core, "cli/w", name="W", Status="Missing", description="")
    app = project(tmp_path, "app")
    inherits(app, core)
    return app


CORE_X_STATE = f"cli/x/{CAPABILITY_STATE}"


def test_ac39_list_leaves_the_unreadable_object_out_and_exits_1(newer, tcw):
    """AC 39, first sentence: `tcw capabilities list` in `app` exits 1, lists
    `core.capabilities/cli/w` and not `cli/x` in any form, and prints a
    message naming `core`'s `cli/x/tcw-capability.yaml` on standard error."""
    ran = tcw(newer, "capabilities", "list", "--scope", "up")
    assert ran.code == 1, ran
    assert ran.out.splitlines() == ["core.capabilities/cli/w"], ran
    assert "cli/x" not in ran.out
    assert f"core/docs/capabilities/{CORE_X_STATE}" in ran.err, ran


@pytest.fixture
def newer_overridden(newer) -> Path:
    """AC 39 with `app` holding its own `cli/x` with only `Status:
    Supported`."""
    capability(newer, "cli/x", Status="Supported")
    return newer


def test_ac39_validate_reports_could_not_check_and_no_incomplete(newer_overridden, tcw):
    """AC 39: `tcw validate` in `app` reports no `incomplete` error for
    `cli/x` and one `unresolved` finding containing `could not check
    capabilities cli/x`."""
    ran = tcw(newer_overridden, "validate")
    assert not any("incomplete" in line for line in findings(ran)), findings(ran)
    matching = [line for line in findings(ran)
                if "could not check capabilities cli/x" in line]
    assert len(matching) == 1, findings(ran)
    assert matching[0].startswith("unresolved: ")


@pytest.mark.parametrize("argv", [("capabilities", "show", "cli/x"),
                                  ("capabilities", "reset", "cli/x")],
                         ids=["show", "reset"])
def test_ac39_show_and_reset_raise_the_version_problem(newer_overridden, tcw, argv):
    """AC 39: `tcw capabilities show cli/x` and `tcw capabilities reset
    cli/x` exit 1 with the version message and change nothing."""
    before = tree_hash(newer_overridden)
    ran = tcw(newer_overridden, *argv)
    assert ran.code == 1, ran
    assert "99.0.0" in ran.err and CORE_X_STATE in ran.err, ran
    assert tree_hash(newer_overridden) == before


def test_ac39_set_of_the_own_override_works(newer_overridden, tcw):
    """AC 39: `tcw capabilities set cli/x --field Priority=P2` exits 0 and
    changes `app`'s file."""
    state = newer_overridden / "docs" / "capabilities" / CORE_X_STATE
    ran = tcw(newer_overridden, "capabilities", "set", "cli/x", "--field", "Priority=P2")
    assert ran.code == 0, ran
    assert read_state(state) == {"Status": "Supported", "Priority": "P2"}


def test_ac39_add_at_the_unreadable_path_raises_the_version_problem(newer, tcw):
    """AC 39, last sentence: with `app` having no `cli/x`, `tcw capabilities
    add cli/x` exits 1 with the version message and writes nothing."""
    before = tree_hash(newer)
    ran = tcw(newer, "capabilities", "add", "cli/x")
    assert ran.code == 1, ran
    assert "99.0.0" in ran.err and CORE_X_STATE in ran.err, ran
    assert tree_hash(newer) == before
    assert not (newer / "docs" / "capabilities" / "cli" / "x").exists()
