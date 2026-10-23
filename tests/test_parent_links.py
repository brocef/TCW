"""The registry follows parent links (TCW-108 Design 3, 4, 6.6, 7.1), called
as a library on projects written with `parents:` and `children:`.

Each test is named after the criterion or the design rule it proves. The
same criteria seen from the command line are in
`tests/test_parent_links_cli.py`."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import tcw.store.project as project_module
from tcw.errors import ProjectGraphError, Unreachable, UnknownProject
from tcw.store.base import ParentLink, load_order_of
from tcw.store.project import FsProjectRegistry
from tests.projectfiles import write_config, write_manifest


def proj(root: Path, project_id: str, parents=None, children=None) -> Path:
    """A 4.0 project at `root` declaring `project_id`, with the `parents:`
    and `children:` given."""
    data: dict = {"id": project_id}
    if parents is not None:
        data["parents"] = parents
    if children is not None:
        data["children"] = children
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def texts(registry) -> str:
    return "\n".join(f"{f.where}: {f.message}" for f in registry.check())


def ids(projects) -> list[str]:
    return [p.id for p in projects]


@pytest.fixture
def reads(monkeypatch):
    """Every file the registry reads, by path."""
    seen: list[Path] = []
    real = project_module._read_text

    def counted(path):
        seen.append(Path(path))
        return real(path)

    monkeypatch.setattr(project_module, "_read_text", counted)
    return seen


# -- the walk and the family (Design 3.1, 3.3) ------------------------------------------


def test_ac9_never_a_sibling(tmp_path):
    proj(tmp_path / "ws", "ws", children=["a", "b"])
    a = proj(tmp_path / "a", "a", parents=["ws"])
    proj(tmp_path / "b", "b", parents=["ws"])
    registry = FsProjectRegistry.open(a).require_valid()
    assert registry.get("b") is None
    assert registry.descendants() == []
    assert ids(registry.ancestors()) == ["ws"]
    assert ids(registry.projects()) == ["a", "ws"]


def test_a_sibling_not_here_is_not_on_this_machine_and_a_stranger_is_unknown(tmp_path):
    """Design 3.4, the 2.12 rows: `ws`'s `children:` names `b`."""
    proj(tmp_path / "ws", "ws", children=["a", "b"])
    a = proj(tmp_path / "a", "a", parents=["ws"])
    registry = FsProjectRegistry.open(a).require_valid()
    with pytest.raises(Unreachable, match="project 'b' is not on this machine"):
        registry.project_folder("b", a)
    with pytest.raises(UnknownProject):
        registry.project_folder("nobody", a)


def test_ac16_a_descendants_load_order(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["a"])
    proj(tmp_path / "a", "a", parents=["core", "ws"])
    proj(tmp_path / "core", "core")
    registry = FsProjectRegistry.open(ws).require_valid()
    assert registry.load_order("a").ids == ("core", "ws", "a")
    assert registry.get("core") is None
    assert ids(registry.descendants()) == ["a"]
    assert ids(registry.projects()) == ["ws", "a"]


def test_descendants_are_breadth_first(tmp_path):
    root = proj(tmp_path / "root", "root", children=["a", "b"])
    proj(tmp_path / "a", "a", parents=["root"], children=["aa"])
    proj(tmp_path / "b", "b", parents=["root"], children=["bb"])
    proj(tmp_path / "aa", "aa", parents=["a"])
    proj(tmp_path / "bb", "bb", parents=["b"])
    registry = FsProjectRegistry.open(root).require_valid()
    assert ids(registry.descendants()) == ["a", "b", "aa", "bb"]
    assert ids(registry.descendants("a")) == ["aa"]


def test_the_answers_for_one_project(tmp_path):
    app = proj(tmp_path / "app", "app",
               parents=[{"id": "ws", "inherit": "none"}, "core"],
               children=["kid", "gone"])
    proj(tmp_path / "ws", "ws")
    proj(tmp_path / "core", "core", parents=["base"])
    proj(tmp_path / "base", "base")
    proj(tmp_path / "kid", "kid", parents=["app"])
    registry = FsProjectRegistry.open(app).require_valid()
    assert registry.parents() == [ParentLink("ws", frozenset()), ParentLink("core")]
    assert registry.declared_child_ids() == ["kid", "gone"]
    assert ids(registry.children()) == ["kid"]
    assert ids(registry.ancestors()) == ["ws", "base", "core"]
    assert registry.load_order().ids == ("ws", "base", "core", "app")
    assert ids(registry.projects()) == ["app", "ws", "core", "base", "kid"]


# -- AC 10-14 at the registry level ------------------------------------------------------


@pytest.mark.parametrize("graph, start", [
    ({"cc": ["aa", "bb"], "ff": ["dd", "ee"], "gg": ["cc", "ff"]}, "gg"),        # AC 10
    ({"bb": ["aa"], "cc": ["bb"], "dd": ["bb"], "ee": ["cc", "dd"]}, "ee"),       # AC 11
    ({"xx": ["bb"], "yy": ["aa", "bb"], "zz": ["xx", "yy"]}, "zz"),               # AC 12
    ({"xx": ["aa", "bb"], "yy": ["bb", "aa"], "zz": ["xx", "yy"]}, "zz"),         # AC 13
    ({"dd": ["cc"], "ee": ["dd", "cc"]}, "ee"),                                    # AC 14
    ({"dd": ["cc"], "ee": ["dd", "cc"], "hh": ["gg"], "ii": ["hh", "gg"],
      "pp": ["ii", "ee"]}, "pp"),                                                  # AC 14
])
def test_the_load_order_through_real_projects_is_the_functions(tmp_path, graph, start):
    names = {*graph, *(p for ps in graph.values() for p in ps)}
    for name in names:
        proj(tmp_path / name, name, parents=graph.get(name))
    registry = FsProjectRegistry.open(tmp_path / start).require_valid()
    links = {name: [ParentLink(p) for p in graph.get(name, [])] for name in names}
    assert registry.load_order() == load_order_of(start, links)


# -- AC 15: loops (Design 4.7) -----------------------------------------------------------


def test_ac15_a_two_project_loop(tmp_path):
    aa = proj(tmp_path / "aa", "aa", parents=["bb"])
    proj(tmp_path / "bb", "bb", parents=["aa"])
    registry = FsProjectRegistry.open(aa)
    assert "loop in parents: aa -> bb -> aa" in texts(registry)
    with pytest.raises(ValueError):
        registry.require_valid()


def test_ac15_a_project_its_own_parent(tmp_path):
    aa = proj(tmp_path / "aa", "aa", parents=["aa"])
    assert "loop in parents: aa -> aa" in texts(FsProjectRegistry.open(aa))


def test_ac15_a_loop_among_descendants(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["cc"])
    proj(tmp_path / "cc", "cc", parents=["ws", "ee"], children=["dd"])
    proj(tmp_path / "dd", "dd", parents=["cc"], children=["ee"])
    proj(tmp_path / "ee", "ee", parents=["dd"], children=["cc"])
    found = texts(FsProjectRegistry.open(ws))
    assert "loop in parents: cc -> ee -> dd -> cc" in found
    assert "named both" not in found


def test_a_loop_met_after_the_walk_is_a_graph_problem(tmp_path):
    """Choice 5: a loop among a descendant's other parents is found when its
    load order is asked for."""
    ws = proj(tmp_path / "ws", "ws", children=["a"])
    proj(tmp_path / "a", "a", parents=["ws", "p"])
    proj(tmp_path / "p", "p", parents=["q"])
    proj(tmp_path / "q", "q", parents=["p"])
    registry = FsProjectRegistry.open(ws).require_valid()
    with pytest.raises(ProjectGraphError, match="loop in parents"):
        registry.load_order("a")
    assert "loop in parents" in texts(registry)


# -- TCW-107's lookup with parent links (Design 3.4) ------------------------------------


def test_ac22_the_ancestor_whose_values_would_win_places_first(tmp_path):
    gg = proj(tmp_path / "gg", "gg", parents=["cc", "ff"], children=["xx"])
    cc = proj(tmp_path / "cc", "cc")
    ff = proj(tmp_path / "ff", "ff")
    proj(tmp_path / "far" / "one" / "xx", "xx", parents=["gg"])
    proj(tmp_path / "far" / "two" / "xx", "xx", parents=["gg"])
    write_manifest(cc, {"xx": "../far/one/xx"})
    write_manifest(ff, {"xx": "../far/two/xx"})
    registry = FsProjectRegistry.open(gg).require_valid()
    assert registry.found("xx") == {"by": "manifest",
                                    "file": str(ff / ".tcw/tcw-manifest.yaml")}


def test_ac22_every_ancestor_is_found_before_a_child_is_looked_up(tmp_path):
    gg = proj(tmp_path / "gg", "gg", parents=["cc", "ff"], children=["xx"])
    proj(tmp_path / "cc", "cc", parents=["aa"])
    proj(tmp_path / "ff", "ff")
    aa = proj(tmp_path / "aa", "aa")
    proj(tmp_path / "far" / "xx", "xx", parents=["gg"])
    write_manifest(aa, {"xx": "../far/xx"})
    registry = FsProjectRegistry.open(gg).require_valid()
    assert registry.found("xx") == {"by": "manifest",
                                    "file": str(aa / ".tcw/tcw-manifest.yaml")}


@pytest.mark.parametrize("local", [True, False])
def test_ac29_a_one_sided_parents_own_parents_through_the_readers_manifests(
        tmp_path, monkeypatch, local):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    app = proj(tmp_path / "app", "app", parents=["lib"])
    proj(tmp_path / "lib", "lib", parents=["core"])
    core = proj(tmp_path / "far" / "away" / "core", "core")
    write_manifest(app, {"core": "../far/away/core"}, local=local)
    registry = FsProjectRegistry.open(app).require_valid()
    assert Path(registry.get("core").locator) == core
    order = registry.load_order()
    assert order.ids == ("core", "lib", "app") and order.complete
    found = [f for f in [*registry.availability_findings(), *registry.manifest_findings()]
             if "core" in f.message]
    assert found == []


@pytest.mark.parametrize("listing, decides", [(["a", "b", "kid"], "a"),
                                              (["b", "a", "kid"], "b")])
def test_ac30_descendants_manifests_in_order(tmp_path, listing, decides):
    ws = proj(tmp_path / "ws", "ws", children=listing)
    roots = {name: proj(tmp_path / "x" / name, name, parents=["ws"]) for name in "ab"}
    proj(tmp_path / "far" / "one" / "kid", "kid", parents=["ws"])
    proj(tmp_path / "far" / "two" / "kid", "kid", parents=["ws"])
    write_manifest(ws, {"a": "../x/a", "b": "../x/b"})
    write_manifest(roots["a"], {"kid": "../../far/one/kid"})
    write_manifest(roots["b"], {"kid": "../../far/two/kid"})
    registry = FsProjectRegistry.open(ws).require_valid()
    assert registry.found("kid")["file"] == str(roots[decides] / ".tcw/tcw-manifest.yaml")


def test_ac35_a_manifest_that_disagrees_with_the_search(tmp_path, monkeypatch):
    """Design 3.4, decided 2026-10-23."""
    app = proj(tmp_path / "app", "app", parents=["core", "lib"])
    lib = proj(tmp_path / "lib", "lib")
    core = proj(tmp_path / "repos" / "core", "core")
    write_manifest(app, {"core": "../repos/core"})
    write_manifest(core, {"lib": "../lib"})
    registry = FsProjectRegistry.open(app)
    found = texts(registry)
    assert str(lib) in found and str(tmp_path.resolve() / "repos" / "lib") in found
    assert ".tcw/tcw-manifest.local.yaml" in found
    assert registry.unreachable_project("lib") is None
    with pytest.raises(ValueError):
        registry.require_valid()
    # An entry in the asking project's own manifests settles it.
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    write_manifest(app, {"lib": "../lib"}, local=True)
    registry = FsProjectRegistry.open(app).require_valid()
    assert registry.found("lib") == {
        "by": "manifest", "file": str(app / ".tcw/tcw-manifest.local.yaml")}


def test_ac35_without_the_other_entry_the_search_decides(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["core", "lib"])
    proj(tmp_path / "lib", "lib")
    proj(tmp_path / "repos" / "core", "core")
    write_manifest(app, {"core": "../repos/core"})
    registry = FsProjectRegistry.open(app).require_valid()
    assert registry.found("lib") == {"by": "search"}
    assert registry.check() == []


def test_ac35_a_search_answer_found_first_is_checked_after_the_walk(tmp_path):
    """The search answered `lib` before `late`'s manifest was read."""
    app = proj(tmp_path / "app", "app", parents=["lib", "late"])
    lib = proj(tmp_path / "lib", "lib")
    late = proj(tmp_path / "repos" / "late", "late")
    write_manifest(app, {"late": "../repos/late"})
    write_manifest(late, {"lib": "../lib"})          # `<tmp>/repos/lib`, not here
    found = texts(FsProjectRegistry.open(app))
    assert str(lib) in found and str(tmp_path.resolve() / "repos" / "lib") in found


# -- Design 6.6: a problem in another project's links ----------------------------------


def test_a_parents_problem_in_a_parent_does_not_stop_the_reader(tmp_path, reads):
    app = proj(tmp_path / "app", "app", parents=["lib"])
    lib = proj(tmp_path / "lib", "lib", parents="core")
    # Where only a lookup through `lib` would read it.
    core = proj(tmp_path / "far" / "core", "core")
    write_manifest(lib, {"core": "../far/core"})
    registry = FsProjectRegistry.open(app).require_valid()
    order = registry.load_order()
    assert order.ids == ("lib", "app") and order.unreadable == ("lib",)
    assert not order.complete
    assert core / ".tcw/tcw-config.yaml" not in reads


def test_in_the_parent_itself_it_is_a_graph_problem(tmp_path):
    proj(tmp_path / "app", "app", parents=["lib"])
    lib = proj(tmp_path / "lib", "lib", parents="core")
    with pytest.raises(ValueError, match="parents"):
        FsProjectRegistry.open(lib).require_valid()


def test_named_both_in_a_parent_is_not_checked(tmp_path):
    """AC 31's last sentence: a `children:` problem, so an ancestor's."""
    app = proj(tmp_path / "app", "app", parents=["lib"])
    proj(tmp_path / "lib", "lib", parents=["top"], children=["top"])
    proj(tmp_path / "top", "top")
    registry = FsProjectRegistry.open(app).require_valid()
    order = registry.load_order()
    assert order.ids == ("top", "lib", "app") and order.complete
    assert registry.check() == []


# -- Design 7.1: the write rule ---------------------------------------------------------


def test_ac21_the_write_rule(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["lib", "ws"])
    proj(tmp_path / "lib", "lib", parents=["top"])
    proj(tmp_path / "ws", "ws", children=["app", "sib"])
    proj(tmp_path / "top", "top", children=["lib"])
    proj(tmp_path / "sib", "sib", parents=["ws"])
    registry = FsProjectRegistry.open(app).require_valid()
    assert registry.read_only_reason("lib") == (
        "'lib' is read-only from here: 'lib' does not list 'app' among its children")
    assert registry.read_only_reason("ws") is None
    assert registry.read_only_reason("top") == (
        "'top' is read-only from here: 'lib' does not list 'app' among its children")
    assert registry.get("sib") is None
    assert FsProjectRegistry.open(tmp_path / "ws").read_only_reason("sib") is None
