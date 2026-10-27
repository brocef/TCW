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
    """x and y list a and b in opposite orders, so no order of app's own
    parents keeps both."""
    both = "capabilities:\n  extends:\n  - a\n  - b\n"
    above = [project(tmp_path / "w/a", "id: a\n", git=True),
             project(tmp_path / "w/b", "id: b\n", git=True),
             project(tmp_path / "w/x", "id: x\nprojects:\n  upstream:\n    a: ../a\n"
                                       "    b: ../b\n" + both, git=True),
             project(tmp_path / "w/y", "id: y\nprojects:\n  upstream:\n    b: ../b\n"
                                       "    a: ../a\n" + both, git=True)]
    app = project(tmp_path / "w/app", "id: app\nprojects:\n  upstream:\n    x: ../x\n"
                                      "    y: ../y\ncapabilities:\n  extends:\n  - x\n"
                                      "  - y\n", git=True)
    for root in above:
        migrate(tcw, root)
    done = migrate(tcw, app)
    [d8] = [l for l in done.err.splitlines() if l.startswith("  D8 ")]
    assert "load order: no order keeps every project's own order of parents" in d8
    # D8 predicts the check after the run's warning, so it is not an A12 too.
    assert not [l for l in done.err.splitlines() if l.startswith("  A12 ")], done.err
    assert shared(app)["parents"] == [{"id": "x", "inherit": ["capabilities"]},
                                      {"id": "y", "inherit": ["capabilities"]}]


def test_an_upstream_listed_after_a_project_that_inherits_it_goes_first(tcw, tmp_path):
    """3.x listed b before a, but b inherits a, so every order 4.0 could keep
    loads a first: written a first, the order has no fallback, and no value
    changes."""
    project(tmp_path / "w/a", "id: a\n")
    project(tmp_path / "w/b", "id: b\nprojects:\n  upstream:\n    a: ../a\n"
                              "capabilities:\n  extends:\n  - a\n")
    app = project(tmp_path / "w/app", "id: app\nprojects:\n  upstream:\n    b: ../b\n"
                                      "    a: ../a\ncapabilities:\n  extends:\n  - b\n"
                                      "  - a\n", git=True)
    done = migrate(tcw, app)
    assert no_d8(done), done.err
    assert shared(app)["parents"] == [{"id": "a", "inherit": ["capabilities"]},
                                      {"id": "b", "inherit": ["capabilities"]}]


def middle_family(base: Path) -> tuple[Path, Path, Path]:
    """b's parent is a, and both name core as their upstream: a needs core
    before it, so b's 3.x order (its parent, then its upstream) cannot be
    kept."""
    core = project(base / "far/core", "id: core\n", git=True)
    a = project(base / "ws", "id: a\nprojects:\n  children:\n    b: b\n"
                             "  upstream:\n    core: ../far/core\n", git=True)
    b = project(base / "ws/b", "id: b\nprojects:\n  parent:\n    a: ..\n"
                               "  upstream:\n    core: ../../far/core\n")
    return core, a, b


@pytest.mark.parametrize("first", ["child", "parents"])
def test_a_middle_project_s_upstream_goes_before_its_parent(tcw, tmp_path, first):
    from tcw.store.project import FsProjectRegistry, forget_registries
    core, a, b = middle_family(tmp_path)
    order = [b, core, a, b] if first == "child" else [core, a, b]
    for root in order:
        done = migrate(tcw, root)
        assert no_d8(done), done.err
    assert shared(b)["parents"] == [{"id": "core", "inherit": "none"}, "a"]
    assert shared(a)["parents"] == [{"id": "core", "inherit": "none"}]
    forget_registries()
    found = FsProjectRegistry.open(b).load_order()
    assert (found.ids, found.warning) == (("core", "a", "b"), None)
    checked = tcw(["validate"], b)
    assert "load order" not in checked.out + checked.err, checked.out + checked.err



def test_a_reorder_that_would_change_the_load_order_is_not_written(tcw, tmp_path):
    """p lists n0, n1, n3; n0 names n3, n1 names n2 then n3. As written the
    depth-first order n3, n0, n2, n1, p is used, n2 winning over n3; listing
    n3 first would give C3's n2, n3, n0, n1, p, n3 winning. That changes a
    value, so the list is written as converted and D8 is reported."""
    ext = "capabilities:\n  extends:\n"
    roots = [project(tmp_path / "w/n3", "id: n3\n", git=True),
             project(tmp_path / "w/n2", "id: n2\n", git=True),
             project(tmp_path / "w/n0", "id: n0\nprojects:\n  upstream:\n    n3: ../n3\n"
                                        + ext + "  - n3\n", git=True),
             project(tmp_path / "w/n1", "id: n1\nprojects:\n  upstream:\n    n2: ../n2\n"
                                        "    n3: ../n3\n" + ext + "  - n2\n  - n3\n",
                     git=True)]
    p = project(tmp_path / "w/p", "id: p\nprojects:\n  upstream:\n    n0: ../n0\n"
                                  "    n1: ../n1\n    n3: ../n3\n" + ext
                                  + "  - n0\n  - n1\n  - n3\n", git=True)
    for root in roots:
        migrate(tcw, root)
    done = migrate(tcw, p)
    [d8] = [l for l in done.err.splitlines() if l.startswith("  D8 ")]
    assert "using depth-first order n3, n0, n2, n1, p" in d8, d8
    assert [e["id"] for e in shared(p)["parents"]] == ["n0", "n1", "n3"]



def test_a_reorder_that_would_change_a_grandchild_s_load_order_is_not_written(tcw,
                                                                            tmp_path):
    """p lists n0, n2, and n0 names n1 then n2: listing n2 first keeps p's own
    load order (n1, n2, n0, p), but its grandchild grand, whose other parent
    is n2, would load n2 before n1 instead of after it. So p is written as
    converted, and D8 is reported."""
    for name in ("n1", "n2"):
        migrate(tcw, project(tmp_path / f"far/{name}", f"id: {name}\n", git=True))
    migrate(tcw, project(tmp_path / "far/n0", "id: n0\nprojects:\n  upstream:\n"
                                              "    n1: ../n1\n    n2: ../n2\n", git=True))
    p = project(tmp_path / "ws", "id: p\nprojects:\n  children:\n    kid: kid\n"
                                 "  upstream:\n    n0: ../far/n0\n    n2: ../far/n2\n",
                git=True)
    project(tmp_path / "ws/kid", "id: kid\nprojects:\n  parent:\n    p: ..\n"
                                 "  children:\n    grand: grand\n")
    project(tmp_path / "ws/kid/grand", "id: grand\nprojects:\n  parent:\n    kid: ..\n"
                                       "  upstream:\n    n2: ../../../far/n2\n")
    done = migrate(tcw, p)
    [d8] = [l for l in done.err.splitlines() if l.startswith("  D8 ")]
    assert "using depth-first order n1, n2, n0, p" in d8, d8
    assert [e["id"] for e in shared(p)["parents"]] == ["n0", "n2"]


def _random_family(rng):
    """Up to six projects above "p", each with parents only among those
    after it, so no loop can form; p's own parents in a random order; and
    one or two projects below p, each with p or the one before it as a
    parent, and another project or two as well."""
    from tcw.store.base import ParentLink
    names = [f"n{i}" for i in range(rng.randint(2, 6))]
    links = {}
    for index, name in enumerate(names):
        later = names[index + 1:]
        links[name] = [ParentLink(pid) for pid in
                       rng.sample(later, rng.randint(0, min(3, len(later))))]
    links["p"] = [ParentLink(pid) for pid in
                  rng.sample(names, rng.randint(2, min(4, len(names))))]
    below = []
    for name in ("d0", "d1")[:rng.randint(1, 2)]:
        others = rng.sample(names, rng.randint(0, 2))
        own = [rng.choice(["p", *below]), *others]
        rng.shuffle(own)
        links[name] = [ParentLink(pid) for pid in own]
        below.append(name)
    return links, below


def _below_graphs(links, below):
    return [(pid, links) for pid in below]


def test_a_reorder_is_written_only_when_it_keeps_the_load_order():
    """Over random families: whenever the parents of p are reordered, the
    reordered list's load order is the one 4.0 would use for the list as
    written (its depth-first fallback), with no warning, so no value
    changes. Some families are reordered, so the check is not empty."""
    import random
    from tcw.migrate.config import order_keeping_values
    from tcw.store.base import load_order_of
    rng = random.Random(118)
    reordered = 0
    for _ in range(300):
        links, below = _random_family(rng)
        written = load_order_of("p", links)
        kept = order_keeping_values("p", links, below=_below_graphs(links, below))
        if kept is None:
            continue
        reordered += 1
        assert written.warning is not None
        assert sorted(kept) == list(range(len(links["p"])))
        trial = {**links, "p": [links["p"][i] for i in kept]}
        found = load_order_of("p", trial)
        assert (found.ids, found.warning) == (written.ids, None), links
        for pid in below:
            assert load_order_of(pid, trial).ids == load_order_of(pid, links).ids, links
    assert reordered > 0


def test_the_counterexample_and_the_middle_project_unit():
    from tcw.migrate.config import order_keeping_values
    from tcw.store.base import ParentLink as L
    counter = {"p": [L("n0"), L("n1"), L("n3")], "n0": [L("n3")],
               "n1": [L("n2"), L("n3")], "n2": [], "n3": []}
    assert order_keeping_values("p", counter) is None
    middle = {"b": [L("a"), L("core")], "a": [L("core")], "core": []}
    assert order_keeping_values("b", middle) == [1, 0]
    child = {"p": [L("n0"), L("n2")], "n0": [L("n1"), L("n2")], "n1": [], "n2": [],
             "g": [L("n2"), L("p")]}
    assert order_keeping_values("p", child) == [1, 0]
    assert order_keeping_values("p", child, below=[("g", child)]) is None

# ── D1 (criteria 32 and 65) ─────────────────────────────────────────────────

TERM = "name: T\n"
CAPABILITY = "name: C\n"


def stocked(folder: Path, text: str, *, git: bool = False) -> Path:
    """A 3.x project holding one term and one capability of its own."""
    return make(folder, {"tcw-config.yaml": text,
                         "docs/taxonomy/t/meta.yaml": TERM,
                         "docs/capabilities/c/meta.yaml": CAPABILITY}, git=git)


def d1_lines(done, axis: str) -> list[str]:
    return [line for line in done.err.splitlines()
            if line.startswith("  D1 ") and f"now inherits {axis} from" in line]


def test_d1_names_the_axes_and_keys_a_parent_now_passes(tcw, tmp_path):
    stocked(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n"
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


def test_d1_leaves_out_a_parent_with_nothing_of_the_axis_to_pass(tcw, tmp_path):
    """Inheriting from a project whose store is missing or empty changes
    nothing, so D1 does not name it; a parent with an object is named."""
    ws = project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n")
    (ws / "docs/taxonomy").mkdir(parents=True)
    make(ws, {"docs/capabilities/c/meta.yaml": CAPABILITY}, git=False)
    app = project(ws / "app", "id: app\nprojects:\n  parent:\n    ws: ..\n", git=True)
    done = migrate(tcw, app)
    assert d1_lines(done, "taxonomy") == []
    assert d1_lines(done, "capabilities") == [
        "  D1 tcw-config.yaml: parents: now inherits capabilities from 'ws', which "
        "TCW 3 did not pass to this project"]


def test_d1_counts_one_level_of_extends_as_passed(tcw, tmp_path):
    stocked(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n"
                             "    sib: sib\n")
    stocked(tmp_path / "ws/sib", "id: sib\nprojects:\n  parent:\n    ws: ..\n")
    app = project(tmp_path / "ws/app", "id: app\nprojects:\n  parent:\n    ws: ..\n"
                                       "taxonomy:\n  extends:\n  - sib\n"
                                       "capabilities:\n  extends:\n  - sib\n", git=True)
    done = migrate(tcw, app)
    for axis in ("taxonomy", "capabilities"):
        assert d1_lines(done, axis) == [
            f"  D1 tcw-config.yaml: parents: now inherits {axis} from 'ws', which "
            f"TCW 3 did not pass to this project"], axis


def test_d1_follows_a_chain_of_taxonomy_extends_as_3_x_did(tcw, tmp_path):
    """3.x's taxonomy `extends` is followed through each extended project's
    own; capabilities `extends` is one level only."""
    stocked(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    a: a\n    b: b\n"
                             "    e: e\n    d: d\n")
    for pid, nxt in (("b", "e"), ("e", "d"), ("d", None)):
        text = f"id: {pid}\nprojects:\n  parent:\n    ws: ..\n"
        if nxt:
            text += (f"taxonomy:\n  extends:\n  - {nxt}\n"
                     f"capabilities:\n  extends:\n  - {nxt}\n")
        stocked(tmp_path / "ws" / pid, text)
    a = project(tmp_path / "ws/a", "id: a\nprojects:\n  parent:\n    ws: ..\n"
                                   "taxonomy:\n  extends:\n  - b\n"
                                   "capabilities:\n  extends:\n  - b\n", git=True)
    done = migrate(tcw, a)
    assert d1_lines(done, "taxonomy") == [
        "  D1 tcw-config.yaml: parents: now inherits taxonomy from 'ws', which TCW 3 "
        "did not pass to this project"]
    assert d1_lines(done, "capabilities") == [
        "  D1 tcw-config.yaml: parents: now inherits capabilities from 'd', 'e', 'ws', "
        "which TCW 3 did not pass to this project"]


def family_rls(base: Path) -> dict[str, Path]:
    """A root with nothing of its own, a library `l`, and `s`, which
    extends `l` and is extended by its child `k`."""
    r = project(base, "id: r\nprojects:\n  children:\n    l: l\n    s: s\n", git=True)
    l = stocked(base / "l", "id: l\nprojects:\n  parent:\n    r: ..\n", git=True)
    s = stocked(base / "s", "id: s\nprojects:\n  parent:\n    r: ..\n"
                            "  children:\n    k: k\n"
                            "taxonomy:\n  extends:\n  - l\n"
                            "capabilities:\n  extends:\n  - l\n", git=True)
    k = stocked(base / "s/k", "id: k\nprojects:\n  parent:\n    s: ..\n"
                              "taxonomy:\n  extends:\n  - s\n"
                              "capabilities:\n  extends:\n  - s\n", git=True)
    return {"r": r, "l": l, "s": s, "k": k}


@pytest.mark.parametrize("migrated_first", [False, True])
def test_d1_through_a_middle_project_names_only_what_3_x_did_not_pass(
        tcw, tmp_path, migrated_first):
    """`k` read `l`'s terms in 3.x, through `s`'s taxonomy `extends`, and
    none of `l`'s capabilities; `r` has neither to pass. The same whether
    the projects above `k` are still 3.x or already migrated."""
    fam = family_rls(tmp_path / "r")
    if migrated_first:
        for pid in ("r", "l", "s"):
            migrate(tcw, fam[pid])
    done = tcw(["migrate", "--dry-run", "--no-jira"], fam["k"])
    assert done.code == 0, done.err
    assert d1_lines(done, "taxonomy") == []
    assert d1_lines(done, "capabilities") == [
        "  D1 tcw-config.yaml: parents: now inherits capabilities from 'l', which "
        "TCW 3 did not pass to this project"]


def test_parents_first_the_check_stops_only_in_a_project_with_3_x_children(tcw, tmp_path):
    """The check after a run reads the project's parents and theirs, and its
    children and theirs, never a sibling; so, parents first, each run in a
    project with children stops, and each run in one without lists its own
    findings while its siblings are still 3.x (the guide's "Migrating related
    projects", item 2)."""
    from tcw.migrate.report import CHECK_STOPPED
    base = tmp_path / "r"
    roots = {"r": project(base, "id: r\nprojects:\n  children:\n    l: l\n    s: s\n",
                          git=True),
             "l": project(base / "l", "id: l\nprojects:\n  parent:\n    r: ..\n", git=True),
             "s": project(base / "s", "id: s\nprojects:\n  parent:\n    r: ..\n"
                                      "  children:\n    k1: k1\n    k2: k2\n", git=True)}
    for kid in ("k1", "k2"):
        roots[kid] = project(base / "s" / kid, f"id: {kid}\nprojects:\n  parent:\n"
                                               f"    s: ..\n", git=True)
    stopped = {pid: CHECK_STOPPED in migrate(tcw, roots[pid]).err.splitlines()
               for pid in ("r", "l", "s", "k1", "k2")}
    assert stopped == {"r": True, "l": False, "s": True, "k1": False, "k2": False}


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
