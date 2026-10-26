"""`extends` becomes parent links (TCW-116 Design 3, C8: E1 to E5; Design
6.1; D1, D6, D8, B4; criteria 25, 26, 32's D1 half, 65's D1 half; plan
Step 19).

Each case is a small 3.x family run with `tcw migrate` in-process; a
project's own `extends` is read with the related projects 3.x read.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tests.migrate.test_migrate_config import make, tree
from tests.objectcli import tcw  # noqa: F401  (a fixture)


def project(folder: Path, text: str, *, git: bool = False) -> Path:
    return make(folder, {"tcw-config.yaml": text}, git=git)


def migrate(tcw, root: Path, code: int = 0):
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == code, done.err
    return done


def shared(root: Path) -> dict:
    return yaml.safe_load((root / ".tcw/tcw-config.yaml").read_text())


def no_d8(done) -> bool:
    return not any(line.startswith("  D8 ") for line in done.err.splitlines())


# ── E1 to E4, one fixture each (criterion 25) ───────────────────────────────

def test_e1_an_ancestor_already_passing_the_axis_adds_nothing(tcw, tmp_path):
    project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n")
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    ws: ..\n"
                                       "capabilities:\n  extends:\n  - ws\n", git=True)
    done = migrate(tcw, app)
    data = shared(app)
    assert data["parents"] == ["ws"] and "capabilities" not in data
    assert "capabilities.extends: 'ws' is already inherited through parents" in done.err
    assert no_d8(done)


def test_e2_an_upstream_passes_each_axis_it_is_extended_for(tcw, tmp_path):
    project(tmp_path / "far/core", "id: core\n")
    app = project(tmp_path / "w/app",
                  "id: app\nprojects:\n  upstream:\n    core: ../../far/core\n"
                  "taxonomy:\n  extends:\n  - core\n  path: docs/terms\n"
                  "capabilities:\n  extends:\n  - core\n", git=True)
    done = migrate(tcw, app)
    data = shared(app)
    assert data["parents"] == [{"id": "core", "inherit": ["taxonomy", "capabilities"]}]
    assert data["taxonomy"] == {"path": "docs/terms"} and "capabilities" not in data
    assert "write .tcw/tcw-config.yaml: C1, C3, C8" in done.err.splitlines()
    assert no_d8(done)


def test_e3_a_listed_child_extended_becomes_a_parent(tcw, tmp_path):
    project(tmp_path / "p/k", "id: k\nprojects:\n  parent:\n    p: ..\n")
    p = project(tmp_path / "p", "id: p\nprojects:\n  children:\n    k: k\n"
                                "taxonomy:\n  extends:\n  - k\n", git=True)
    done = migrate(tcw, p)
    data = shared(p)
    assert data["parents"] == [{"id": "k", "inherit": ["taxonomy"]}]
    assert "children" not in data and "taxonomy" not in data
    assert ("  D6 tcw-config.yaml: projects.children.k: dropped; taxonomy.extends names "
            "it, so 'k' becomes a parent passing taxonomy instead") in done.err


def test_e4_a_sibling_becomes_one_more_parent(tcw, tmp_path):
    project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n    sib: sib\n")
    project(tmp_path / "ws/sib", "id: sib\nprojects:\n  parent:\n    ws: ..\n")
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    ws: ..\n"
                                       "capabilities:\n  extends:\n  - sib\n", git=True)
    done = migrate(tcw, app)
    assert shared(app)["parents"] == ["ws", {"id": "sib", "inherit": ["capabilities"]}]
    # sib is next to app's root, so 4.0's search finds it: no entry (M6).
    assert not (app / ".tcw/tcw-manifest.yaml").exists()
    assert no_d8(done)


def test_e4_an_ancestor_of_an_existing_parent_goes_before_it(tcw, tmp_path):
    """g is p1's upstream, extended by nobody, so it passes nothing to app
    through p1; app extending g makes g a parent, placed before p1 so that
    4.0's order keeps each project's own order of parents."""
    project(tmp_path / "far/g", "id: g\n")
    project(tmp_path / "ws", "id: p1\nprojects:\n  children:\n    app: app\n"
                             "  upstream:\n    g: ../far/g\n")
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    p1: ..\n"
                                       "capabilities:\n  extends:\n  - g\n", git=True)
    done = migrate(tcw, app)
    assert shared(app)["parents"] == [{"id": "g", "inherit": ["capabilities"]}, "p1"]
    assert yaml.safe_load((app / ".tcw/tcw-manifest.yaml").read_text())["projects"] == {
        "g": {"path": "../../far/g"}}
    assert no_d8(done)


def test_the_converted_family_has_tcw_4_s_load_order_with_no_warning(tcw, tmp_path):
    from tcw.store.project import FsProjectRegistry, forget_registries
    g = project(tmp_path / "far/g", "id: g\n")
    ws = project(tmp_path / "ws", "id: p1\nprojects:\n  children:\n    app: app\n"
                                  "  upstream:\n    g: ../far/g\n", git=True)
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    p1: ..\n"
                                       "capabilities:\n  extends:\n  - g\n")
    for root in (g, ws, app):
        migrate(tcw, root)
    forget_registries()
    order = FsProjectRegistry.open(app).load_order()
    assert (order.ids, order.warning) == (("g", "p1", "app"), None)


# ── E3 from both sides, either order (criterion 26) ─────────────────────────

def family_pk(base: Path) -> tuple[Path, Path]:
    p = project(base / "p", "id: p\nprojects:\n  children:\n    k: ../k\n"
                            "capabilities:\n  extends:\n  - k\n", git=True)
    k = project(base / "k", "id: k\nprojects:\n  parent:\n    p: ../p\n", git=True)
    return p, k


def test_e3_on_both_sides_in_either_order_gives_the_same_files(tcw, tmp_path):
    p1, k1 = family_pk(tmp_path / "one")
    p2, k2 = family_pk(tmp_path / "two")
    runs = [migrate(tcw, p1), migrate(tcw, k1), migrate(tcw, k2), migrate(tcw, p2)]
    for p, k in ((p1, k1), (p2, k2)):
        assert shared(p)["parents"] == [{"id": "k", "inherit": ["capabilities"]}]
        assert "children" not in shared(p)
        assert "parents" not in shared(k) and "children" not in shared(k)
    assert tree(p1) == tree(p2) and tree(k1) == tree(k2)
    for done in runs:
        assert "  D6 tcw-config.yaml: projects." in done.err, done.err


# ── Design 6.1: a related project in either form ────────────────────────────

def sib_family(base: Path) -> Path:
    project(base / "ws", "id: ws\nprojects:\n  children:\n    app: app\n    sib: sib\n"
                         "work:\n  tags:\n  - bug\n")
    project(base / "ws/sib", "id: sib\nprojects:\n  parent:\n    ws: ..\n")
    return project(base / "ws/app", "id: app\nprojects:\n  parent:\n    ws: ..\n"
                                    "capabilities:\n  extends:\n  - sib\n", git=True)


def test_a_related_project_migrated_or_not_gives_the_same_files(tcw, tmp_path):
    first = sib_family(tmp_path / "one")
    second = sib_family(tmp_path / "two")
    migrate(tcw, tmp_path / "two/ws")
    migrate(tcw, tmp_path / "two/ws/sib")
    assert (tmp_path / "two/ws/sib/.tcw/tcw-config.yaml").is_file()
    one, two = migrate(tcw, first), migrate(tcw, second)
    assert tree(first) == tree(second)

    def reports(done):
        return [l for l in done.err.splitlines() if l.startswith("  ")
                and not l.startswith("  A8 ")]
    assert reports(one) == reports(two)
    # Only the run whose sib and ws are still 3.x names them, parents first.
    assert [l.split(":", 1)[0] for l in one.err.splitlines() if l.startswith("  A8 ")] \
        == [f"  A8 {tmp_path / 'one/ws'}", f"  A8 {tmp_path / 'one/ws/sib'}"]
    assert f"migrate it with 'tcw -C {tmp_path / 'one/ws'} migrate'" in one.err
    assert "  A8 " not in two.err and "  A12 " not in one.err


def test_a8_in_a_workspace_lists_a_parent_before_its_child(tcw, tmp_path):
    """The workspace names `deep` before `sub`, `deep`'s parent; A8 lists
    `sub` first, parents first (TCW-116 Design 2.10, 6.2; TCW-118 fix 19)."""
    ws = project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n"
                                  "    deep: sub/deep\n    sub: sub\n", git=True)
    project(tmp_path / "ws/sub", "id: sub\nprojects:\n  parent:\n    ws: ..\n"
                                 "  children:\n    deep: deep\n")
    project(tmp_path / "ws/sub/deep", "id: deep\nprojects:\n  parent:\n    sub: ..\n")
    done = migrate(tcw, ws)
    assert [l.split(":", 1)[0] for l in done.err.splitlines() if l.startswith("  A8 ")] \
        == [f"  A8 {tmp_path / 'ws/sub'}", f"  A8 {tmp_path / 'ws/sub/deep'}"]


# ── E5 and loops: B4 ────────────────────────────────────────────────────────

def test_two_projects_extending_each_other_is_b4(tcw, tmp_path):
    project(tmp_path / "w/b", "id: b\nprojects:\n  upstream:\n    a: ../a\n"
                              "capabilities:\n  extends:\n  - a\n")
    a = project(tmp_path / "w/a", "id: a\nprojects:\n  upstream:\n    b: ../b\n"
                                  "capabilities:\n  extends:\n  - b\n", git=True)
    before = tree(a)
    done = migrate(tcw, a, 3)
    assert ("  B4 tcw-config.yaml: extends: the parent links it converts to make a loop: "
            "a -> b -> a") in done.err
    assert tree(a) == before


def test_extending_a_descendant_that_is_not_a_listed_child_is_b4(tcw, tmp_path):
    ws = project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n"
                                  "capabilities:\n  extends:\n  - kid\n", git=True)
    project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    ws: ..\n"
                                 "  children:\n    kid: ../kid\n")
    project(tmp_path / "ws/kid", "id: kid\nprojects:\n  parent:\n    app: ../app\n")
    done = migrate(tcw, ws, 3)
    assert ("  B4 tcw-config.yaml: capabilities.extends: 'kid' is a descendant of this "
            "project and not its listed child") in done.err


# ── D8: a load order with no consistent order ───────────────────────────────

def test_a_load_order_that_falls_back_is_d8(tcw, tmp_path):
    project(tmp_path / "w/a", "id: a\n")
    project(tmp_path / "w/b", "id: b\nprojects:\n  upstream:\n    a: ../a\n"
                              "capabilities:\n  extends:\n  - a\n")
    app = project(tmp_path / "w/app", "id: app\nprojects:\n  upstream:\n    b: ../b\n"
                                      "    a: ../a\ncapabilities:\n  extends:\n  - b\n"
                                      "  - a\n", git=True)
    done = migrate(tcw, app)
    [d8] = [l for l in done.err.splitlines() if l.startswith("  D8 ")]
    assert "load order: no order keeps every project's own order of parents" in d8


# ── D1 (criteria 32 and 65) ─────────────────────────────────────────────────

def test_d1_names_the_axes_and_keys_a_parent_now_passes(tcw, tmp_path):
    project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n"
                             "work:\n  tags:\n  - bug\n")
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    ws: ..\n",
                  git=True)
    done = migrate(tcw, app)
    said = done.err.splitlines()
    assert ("  D1 tcw-config.yaml: parents: now inherits taxonomy from 'ws', which TCW 3 "
            "did not pass to this project") in said
    assert ("  D1 tcw-config.yaml: parents: now inherits capabilities from 'ws', which "
            "TCW 3 did not pass to this project") in said
    assert ("  D1 tcw-config.yaml: work.tags: set by parent 'ws' and not by this "
            "project, which now inherits it") in said


def test_d1_names_a_jira_field_a_migrated_parent_sets(tcw, tmp_path):
    ws = tmp_path / "ws"
    make(ws, {".tcw/tcw-config.yaml": "tcw-version: 4.0.0\nid: ws\nchildren:\n- app\n"
                                       "work:\n  jira:\n    fields:\n      effort: Size\n"})
    from tests.migrate.fixtures import _CONFIG
    app = project(ws / "app", _CONFIG.replace("id: app\n",
                                              "id: app\nprojects:\n  parent:\n    ws: ..\n"),
                  git=True)
    done = migrate(tcw, app)
    assert ("  D1 tcw-config.yaml: work.jira.fields.effort: set by parent 'ws' and not "
            "by this project, which now inherits it") in done.err.splitlines()
    assert "work.jira.fields.item" not in done.err


# ── A related project this run must read and that is not here (48) ──────────

def test_an_absent_parent_named_for_its_location_converts(tcw, tmp_path):
    app = project(tmp_path / "w/app", "id: app\nprojects:\n  parent:\n    ws: ../../far/ws\n"
                                      "  upstream:\n    core: ../../far/core\n"
                                      "  children:\n    kid: ../../far/kid\n"
                                      "taxonomy:\n  extends:\n  - core\n  - kid\n", git=True)
    migrate(tcw, app)
    assert shared(app)["parents"] == ["ws", {"id": "core", "inherit": ["taxonomy"]},
                                      {"id": "kid", "inherit": ["taxonomy"]}]


def test_an_absent_project_e1_must_read_is_b5(tcw, tmp_path):
    project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n"
                             "    sib: sib\n")
    project(tmp_path / "ws/sib", "id: sib\nprojects:\n  parent:\n    ws: ..\n")
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    ws:\n"
                                       "      path: ..\n      repository:\n"
                                       "        url: https://example.invalid/ws.git\n"
                                       "capabilities:\n  extends:\n  - sib\n", git=True)
    shutil.move(tmp_path / "ws/tcw-config.yaml", tmp_path / "ws-config.yaml")
    before = tree(app)
    done = migrate(tcw, app, 3)
    assert "  B5 tcw-config.yaml: capabilities.extends: E1: project 'ws' is not on " \
           "this machine" in done.err
    assert f"'git clone https://example.invalid/ws.git {tmp_path / 'ws'}'" in done.err
    assert tree(app) == before


def test_a_parent_s_jira_fields_change_nothing_the_run_asks_jira(tcw, tmp_path,
                                                                 monkeypatch):
    """Criterion 65 (Decided 11): the search and the edits use this project's
    own `work.jira.fields`, also when its migrated parent names another
    field for the item."""
    from tests.migrate import fixtures
    from tests.work.jira.fake import FIELDS, FakeJira
    monkeypatch.setenv(fixtures.EMAIL_VARIABLE, "dev@example.invalid")
    monkeypatch.setenv(fixtures.TOKEN_VARIABLE, "token")
    fake = FakeJira(site=fixtures.SITE)
    fake.install(monkeypatch)
    fixtures.seed_tickets(fake)
    ws = tmp_path / "ws"
    make(ws, {".tcw/tcw-config.yaml": "tcw-version: 4.0.0\nid: ws\nchildren:\n- app\n"
                                       "work:\n  jira:\n    fields:\n      item: TCW Project\n"
                                       "      effort: Size\n"})
    app = project(ws / "app", fixtures._CONFIG.replace(
        "id: app\n", "id: app\nprojects:\n  parent:\n    ws: ..\n"), git=True)
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    searched = [b["jql"] for m, p, b in fake.log if p.endswith("/search/jql")]
    assert searched and all(f"cf[{FIELDS['TCW Item'].split('_')[-1]}]" in q
                            for q in searched)
    bodies = [b for m, p, b in fake.log if m == "PUT"]
    assert bodies and all(set(b["fields"]) == {FIELDS["TCW Item"]} for b in bodies)
