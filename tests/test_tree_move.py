"""`rename` and `move` of terms and capabilities (TCW-114 Design 5, 6, 8;
AC 15 to AC 21, AC 25's tree half; plan Step 19)."""

from __future__ import annotations

import shutil

import pytest
import yaml

from tests.objectcli import findings, item, obj, project, tcw  # noqa: F401
from tests.statefiles import CAPABILITY_STATE, TAXONOMY_STATE, write_state


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


def changed_lines(before: bytes, after: bytes) -> list[tuple[str, str]]:
    a, b = before.decode().splitlines(), after.decode().splitlines()
    assert len(a) == len(b)
    return [(x, y) for x, y in zip(a, b) if x != y]


# -- AC 15 ---------------------------------------------------------------------------


def make_taxonomy(tmp_path):
    root = project(tmp_path, "demo", work={})
    obj(root, "taxonomy", "vocab", name="Vocab", kind="Vocabulary")
    obj(root, "taxonomy", "invoice", name="Invoice", kind="Vocabulary")
    obj(root, "taxonomy", "invoice/refund", name="Refund", kind="Vocabulary",
        parent="demo.taxonomy/invoice")
    obj(root, "taxonomy", "pay", name="Pay", kind="Feature",
        relatesTo=["demo.taxonomy/invoice"], vocabulary=["demo.taxonomy/invoice/refund"])
    obj(root, "capabilities", "cli", name="CLI", Status="Supported")
    obj(root, "capabilities", "cli/x", name="X", Status="Supported",
        parent="demo.capabilities/cli", Subject=["demo.taxonomy/invoice/refund"])
    (root / "docs/capabilities/cli/x/description.md").write_text(
        "About [refunds](tcw://demo.taxonomy/invoice/refund).\n")
    folder = item(root, "2026-10-22-a")
    (folder / "capabilities.yaml").write_text(
        "taxonomy: {changed: [demo.taxonomy/invoice]}\n")
    return root


@pytest.fixture
def taxonomy(tmp_path):
    return make_taxonomy(tmp_path)


def test_ac15_a_taxonomy_rename_rewrites_every_reference(tcw, taxonomy):
    assert tcw(["validate"], taxonomy).code == 0
    before = snapshot(taxonomy)
    name = tcw(["taxonomy", "show", "invoice", "--json"], taxonomy).out
    result = tcw(["taxonomy", "rename", "invoice", "bill"], taxonomy)
    assert result.code == 0, result.err
    assert result.out.splitlines() == [
        "demo.taxonomy/invoice -> demo.taxonomy/bill",
        "demo.taxonomy/invoice/refund -> demo.taxonomy/bill/refund"]
    after = snapshot(taxonomy)
    refund = "docs/taxonomy/bill/refund/" + TAXONOMY_STATE
    assert changed_lines(before["docs/taxonomy/invoice/refund/" + TAXONOMY_STATE],
                         after[refund]) == [("parent: demo.taxonomy/invoice",
                                             "parent: demo.taxonomy/bill")]
    pay = "docs/taxonomy/pay/" + TAXONOMY_STATE
    assert len(changed_lines(before[pay], after[pay])) == 2
    cap = "docs/capabilities/cli/x/" + CAPABILITY_STATE
    assert changed_lines(before[cap], after[cap]) == [
        ("- demo.taxonomy/invoice/refund", "- demo.taxonomy/bill/refund")]
    assert after["docs/capabilities/cli/x/description.md"] == (
        b"About [refunds](tcw://demo.taxonomy/bill/refund).\n")
    assert after["docs/work/2026-10-22-a/capabilities.yaml"] == (
        b"taxonomy: {changed: [demo.taxonomy/bill]}\n")
    def named(out: str) -> str:
        answer = yaml.safe_load(out)
        return (answer.get("term") or answer)["name"]
    assert named(tcw(["taxonomy", "show", "bill", "--json"], taxonomy).out) == named(name)
    assert tcw(["validate"], taxonomy).code == 0

    moved = tcw(["taxonomy", "move", "bill/refund", "--top"], taxonomy)
    assert moved.code == 0, moved.err
    assert moved.out.splitlines() == ["demo.taxonomy/bill/refund -> demo.taxonomy/refund"]
    assert "warning" not in moved.err
    state = yaml.safe_load((taxonomy / "docs/taxonomy/refund" / TAXONOMY_STATE).read_text())
    assert state["parent"] == "demo.taxonomy/bill"
    assert "demo.taxonomy/refund" in (taxonomy / "docs/taxonomy/pay" /
                                      TAXONOMY_STATE).read_text()
    checked = tcw(["validate"], taxonomy)
    assert checked.code == 0, checked.out


def test_a_rename_onto_a_case_variant_names_the_folder_as_spelled(tcw, taxonomy):
    """`pay` is there: renaming to `PAY` is refused naming `pay`, the folder
    that is in the way, not the spelling typed."""
    before = snapshot(taxonomy)
    result = tcw(["taxonomy", "rename", "invoice", "PAY"], taxonomy)
    assert result.code == 3, result.err
    assert "docs/taxonomy/pay already exists" in result.err
    assert snapshot(taxonomy) == before


def test_ac15_the_renamed_terms_own_id_follows(tcw, taxonomy):
    path = taxonomy / "docs/taxonomy/invoice" / TAXONOMY_STATE
    path.write_text(path.read_text() + "id: invoice\n")
    assert tcw(["taxonomy", "rename", "invoice", "bill"], taxonomy).code == 0
    assert "id: bill" in (taxonomy / "docs/taxonomy/bill" / TAXONOMY_STATE).read_text()


def test_ac15_a_failed_folder_move_is_finished_by_running_again(tcw, taxonomy,
                                                                 monkeypatch):
    import tcw.object_folders as folders
    real = folders.os.rename

    def rename(a, b):
        raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(folders.os, "rename", rename)
    result = tcw(["taxonomy", "rename", "invoice", "bill"], taxonomy)
    assert result.code == 1, result.err
    assert "demo.taxonomy/bill" in (taxonomy / "docs/taxonomy/pay" /
                                    TAXONOMY_STATE).read_text()
    assert (taxonomy / "docs/taxonomy/invoice").is_dir()
    assert "run the same command again" in result.err
    monkeypatch.setattr(folders.os, "rename", real)
    before = snapshot(taxonomy)
    again = tcw(["taxonomy", "rename", "invoice", "bill"], taxonomy)
    assert again.code == 0, again.err
    assert "rewrote" not in again.err
    after = snapshot(taxonomy)
    assert {k.replace("/bill", "/invoice"): v for k, v in after.items()} == before


# -- AC 16 ---------------------------------------------------------------------------


def make_capabilities(tmp_path):
    root = project(tmp_path, "demo", work={})
    obj(root, "capabilities", "cli", name="CLI", Status="Supported")
    obj(root, "capabilities", "cli/x", name="X", Status="Supported")
    obj(root, "capabilities", "cli/x/z", name="Z", Status="Supported")
    obj(root, "capabilities", "roles", name="Roles", Status="Supported")
    obj(root, "capabilities", "roles/admin", name="Admin", Status="Supported")
    obj(root, "capabilities", "cli/y", name="Y", Status="Supported",
        **{"Superseded by": "demo.capabilities/cli/x",
           "Blocked by": "demo.capabilities/cli/x/z",
           "Roles": ["!demo.capabilities/roles/admin"]})
    return root


@pytest.fixture
def caps(tmp_path):
    return make_capabilities(tmp_path)


def y_state(root):
    return yaml.safe_load((root / "docs/capabilities/cli/y" / CAPABILITY_STATE).read_text())


def test_ac16_capabilities_rename_and_a_refused_move(tcw, caps):
    result = tcw(["capabilities", "rename", "cli/x", "w"], caps)
    assert result.code == 0, result.err
    assert len(result.out.splitlines()) == 2
    state = y_state(caps)
    assert state["Superseded by"] == "demo.capabilities/cli/w"
    assert state["Blocked by"] == "demo.capabilities/cli/w/z"
    assert tcw(["validate"], caps).code == 0
    result = tcw(["capabilities", "rename", "roles/admin", "owner"], caps)
    assert result.code == 0, result.err
    assert y_state(caps)["Roles"] == ["!demo.capabilities/roles/owner"]
    before = snapshot(caps)
    result = tcw(["capabilities", "move", "roles/owner", "--into", "cli"], caps)
    assert result.code == 3, result.err
    assert "Roles" in result.err and "cli/y" in result.err
    assert snapshot(caps) == before
    assert tcw(["validate"], caps).code == 0


# -- AC 17 ---------------------------------------------------------------------------


@pytest.fixture
def inherited(tmp_path):
    from tests.projectfiles import connect_projects, write_manifest
    core = project(tmp_path, "core", work={})
    app = project(tmp_path, "app", work={})
    obj(core, "capabilities", "cli", name="CLI", Status="Supported")
    obj(core, "capabilities", "cli/x", name="X", Status="Supported")
    obj(core, "capabilities", "cli/v", name="V", Status="Supported")
    connect_projects(app, "parent", "core")
    write_manifest(app, {"core": "../core"})
    obj(app, "capabilities", "cli/x", Status="Stable")
    obj(app, "capabilities", "cli/y", name="Y", Status="Supported")
    obj(app, "capabilities", "work", name="Work", Status="Supported")
    return app, core


def test_ac17_an_override_is_not_moved(tcw, inherited):
    app, _ = inherited
    before = snapshot(app)
    result = tcw(["capabilities", "move", "cli/x", "--into", "work"], app)
    assert result.code == 3, result.err
    assert "core.capabilities/cli/x" in result.err
    assert snapshot(app) == before


def test_ac17_a_move_does_not_make_an_override(tcw, inherited):
    app, _ = inherited
    before = snapshot(app)
    result = tcw(["capabilities", "rename", "cli/y", "v"], app)
    assert result.code == 3, result.err
    assert "core.capabilities/cli/v" in result.err
    assert snapshot(app) == before


def test_ac17_an_ancestor_not_here_stops_with_exit_7(tcw, inherited):
    app, core = inherited
    shutil.rmtree(core)
    result = tcw(["capabilities", "rename", "cli/y", "v"], app)
    assert result.code == 7, result.err


# -- AC 19, AC 20 ------------------------------------------------------------------------


def test_ac19_an_unreadable_capability_stops_a_taxonomy_rename(tcw, taxonomy):
    path = taxonomy / "docs/capabilities/cli/x" / CAPABILITY_STATE
    path.write_text("tcw-version: banana\n" + path.read_text().split("\n", 1)[1])
    before = snapshot(taxonomy)
    result = tcw(["taxonomy", "rename", "invoice", "bill"], taxonomy)
    assert result.code == 1, result.err
    assert "cli/x/" + CAPABILITY_STATE in result.err
    assert snapshot(taxonomy) == before


def test_ac19_an_unreadable_capabilities_yaml_stops_a_rename(tcw, caps):
    folder = item(caps, "2026-10-22-a")
    (folder / "capabilities.yaml").write_text("new: [unclosed\n")
    result = tcw(["capabilities", "rename", "cli/x", "w"], caps)
    assert result.code == 1, result.err
    assert "2026-10-22-a/capabilities.yaml" in result.err


def test_ac20_a_folder_whose_name_breaks_the_grammar(tcw, caps):
    obj(caps, "capabilities", "cli/has.dot", name="Dot", Status="Supported")
    result = tcw(["capabilities", "rename", "cli/has.dot", "has-dot"], caps)
    assert result.code == 0, result.err
    assert result.out.splitlines() == [
        "demo.capabilities/cli/has.dot -> demo.capabilities/cli/has-dot"]
    assert tcw(["capabilities", "show", "cli/has.dot"], caps).code == 2
    before = snapshot(caps)
    assert tcw(["capabilities", "rename", "cli/x", "has.dot"], caps).code == 2
    assert snapshot(caps) == before


# -- AC 21 ---------------------------------------------------------------------------


def test_ac21_other_projects_are_left_and_reported_there(tcw, tmp_path):
    from tests.projectfiles import write_manifest
    core = project(tmp_path, "core", work={})
    app = project(tmp_path, "app", work={})
    obj(core, "capabilities", "cli", name="CLI", Status="Supported")
    obj(core, "capabilities", "cli/x", name="X", Status="Supported")
    obj(app, "capabilities", "a", name="A", Status="Supported")
    write_manifest(app, {"core": "../core"})
    (app / "docs/capabilities/a/description.md").write_text(
        "See [x](tcw://core.capabilities/cli/x).\n")
    before = snapshot(app)
    result = tcw(["capabilities", "rename", "cli/x", "y"], core)
    assert result.code == 0, result.err
    assert result.out.splitlines() == ["core.capabilities/cli/x -> core.capabilities/cli/y"]
    assert snapshot(app) == before
    checked = tcw(["validate"], app)
    assert checked.code == 1
    assert "tcw://core.capabilities/cli/x" in checked.out


# -- AC 25 (the tree half) -------------------------------------------------------------


@pytest.mark.parametrize("argv", [["taxonomy", "rename", "invoice", "bill"],
                                  ["capabilities", "move", "cli/x", "--top"]])
def test_ac25_tree_moves_start_no_process(tcw, taxonomy, monkeypatch, argv):
    import subprocess
    from tests.processes import allowed_read_only_git
    started = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def run(cmd, *a, **k):
        started.append(list(cmd))
        return real_run(cmd, *a, **k)

    class Popen(real_popen):
        def __init__(self, cmd, *a, **k):
            started.append(list(cmd))
            super().__init__(cmd, *a, **k)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "Popen", Popen)
    result = tcw(argv, taxonomy)
    assert result.code == 0, result.err
    assert all(allowed_read_only_git(a) for a in started), started


def test_a_path_with_no_own_object_and_no_view_is_not_found(tcw, inherited):
    """Reusing `removal_target` brings TCW-112's rule for `rm` (plan Step 19)."""
    app, core = inherited
    shutil.rmtree(core)
    result = tcw(["capabilities", "rename", "cli/v", "u"], app)
    assert result.code == 4, result.err


# -- every stop ----------------------------------------------------------------------


def test_every_stop_of_a_taxonomy_rename(tcw, tmp_path):
    from tests.move_stops import Fixture, every_stop
    made = []

    def make():
        folder = tmp_path / f"run-{len(made)}"
        folder.mkdir()
        made.append(folder)
        return Fixture(make_taxonomy(folder))
    total = every_stop(pytest.MonkeyPatch.context, make,
                       lambda f: tcw(["taxonomy", "rename", "invoice", "bill"], f.root))
    # refund, pay, cli/x, its description, the capabilities.yaml, the folder.
    assert total == 6


def test_every_stop_of_a_capabilities_move(tcw, tmp_path):
    """Review S1 c: the stops cover a capabilities.yaml rewrite, a Roles value
    keeping its `!`, and an organising folder made inside `roles/`."""
    from tests.move_stops import Fixture, every_stop
    made = []

    def make():
        folder = tmp_path / f"run-{len(made)}"
        folder.mkdir()
        made.append(folder)
        root = project(folder, "demo", work={})
        obj(root, "capabilities", "roles/admin", name="Admin", Status="Supported")
        obj(root, "capabilities", "cli", name="CLI", Status="Supported")
        obj(root, "capabilities", "cli/y", name="Y", Status="Supported",
            Roles=["!demo.capabilities/roles/admin"])
        work = item(root, "2026-10-22-a")
        (work / "capabilities.yaml").write_text("changed: [demo.capabilities/roles/admin]\n")
        return Fixture(root)
    total = every_stop(pytest.MonkeyPatch.context, make,
                       lambda f: tcw(["capabilities", "move", "roles/admin", "--into",
                                      "roles/staff"], f.root))
    # cli/y, the capabilities.yaml, roles/staff/ made, the folder, and the
    # tidy step's try at removing roles/, which still holds staff/.
    assert total == 5


# -- AC 26: every row of the table is rewritten by a rename -------------------------------

from tcw.reference_fields import FIELDS, Field  # noqa: E402

ROWS = [f for f in FIELDS if f.record in ("term", "capability", "capabilities-yaml",
                                          "markdown")]


def _target(row: Field) -> tuple[str, str, str]:
    """The namespace, the old id-path and the new last part a row's case
    renames."""
    if row.namespace == "taxonomy":
        return "taxonomy", "t", "t2"
    if row.group:
        return "capabilities", f"{row.group}/a", "b"
    return "capabilities", "a", "b"


def _hold(root, row: Field, value: str):
    """A record holding `value` at `row`; returns the file."""
    many = [value] if row.many else value
    if row.record == "term":
        return obj(root, "taxonomy", "h", name="H", kind="Vocabulary",
                   **{row.name: many}) / TAXONOMY_STATE
    if row.record == "capability":
        return obj(root, "capabilities", "h", name="H", Status="Supported",
                   **{row.name: many}) / CAPABILITY_STATE
    if row.record == "capabilities-yaml":
        folder = item(root, "2026-10-22-a")
        kind = row.name.split(".")[-1]
        body = {kind: [value]} if "." not in row.name else {"taxonomy": {kind: [value]}}
        (folder / "capabilities.yaml").write_text(yaml.safe_dump(body))
        return folder / "capabilities.yaml"
    folder = obj(root, "capabilities", "h", name="H", Status="Supported")
    (folder / "description.md").write_text(f"See [it](tcw://{value}).\n")
    return folder / "description.md"


@pytest.mark.parametrize("row", ROWS, ids=lambda r: f"{r.record}-{r.name}")
def test_ac26_every_row_is_rewritten(tcw, tmp_path, row):
    root = project(tmp_path, "demo", work={})
    namespace, old, new_last = _target(row)
    if namespace == "taxonomy":
        obj(root, "taxonomy", old, name="T", kind="Vocabulary")
    else:
        obj(root, "capabilities", old, name="A", Status="Supported")
    path = _hold(root, row, f"demo.{namespace}/{old}")
    result = tcw([namespace, "rename", old, new_last], root)
    assert result.code == 0, result.err
    new = f"demo.{namespace}/{old.rpartition('/')[0] + '/' if '/' in old else ''}{new_last}"
    assert new in path.read_text()


def test_ac26_an_added_row_is_rewritten(tcw, tmp_path, monkeypatch):
    import tcw.reference_fields as table
    monkeypatch.setattr(table, "FIELDS", (*table.FIELDS, Field(
        "capability", "Reviewed by", False, "capabilities")))
    root = project(tmp_path, "demo", work={})
    obj(root, "capabilities", "a", name="A", Status="Supported")
    holder = obj(root, "capabilities", "h", name="H", Status="Supported",
                 **{"Reviewed by": "demo.capabilities/a"})
    assert tcw(["capabilities", "rename", "a", "b"], root).code == 0
    assert "Reviewed by: demo.capabilities/b" in (holder / CAPABILITY_STATE).read_text()
