"""A project located through the manifest of a project another manifest
located (TCW-99 Design, "Locating a project", step 1: "then, going down, in
the manifests of the children already found").

The family the evaluation of TCW-118 met: a planning workspace `ws` lists
`app` and `srv`, each in its own folder beside it; `srv` lists its child
`plug`, a subfolder of `srv`'s folder. `app`'s manifest lists only `ws`. From
`app`, `plug` is in no manifest of `app` or its ancestors, and no folder next
to `app` or enclosing it is `plug`; only `srv`'s manifest, which `ws`'s
located, places it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tcw.errors import ProjectGraphError, UnknownProject
from tcw.store.project import LEGACY_SENTINEL, FsProjectRegistry
from tests.families import Family, _project, build_family, item_folder
from tests.projectfiles import write_manifest
from tests.test_project_lookup import lookup, proj, reads  # noqa: F401  (a fixture)

MISSING = "no project with ID 'zz' is known or found near this one; check the spelling"


def workspace(tmp_path: Path) -> Family:
    family = Family(tmp_path)
    for project_id in ("ws", "app", "srv"):
        family.roots[project_id] = _project(tmp_path, project_id)
    family.roots["plug"] = _project(tmp_path / "srv", "plug")
    family.write_config("ws", {**family.config("ws"), "children": ["app", "srv"]})
    family.write_config("app", {**family.config("app"), "parents": ["ws"]})
    family.write_config("srv", {**family.config("srv"), "parents": ["ws"],
                                "children": ["plug"]})
    family.write_config("plug", {**family.config("plug"), "parents": ["srv"]})
    write_manifest(family["ws"], {"app": "../app", "srv": "../srv"})
    write_manifest(family["app"], {"ws": "../ws"})
    write_manifest(family["srv"], {"ws": "../ws", "plug": "plug"})
    for project_id in family.roots:
        family.item(project_id, item_folder(project_id))
    return family


def test_a_child_of_a_sibling_is_found_from_the_command_line(tmp_path):
    family = workspace(tmp_path)
    plug_item = f"plug.work/{item_folder('plug')}"
    path = family.run("app", "project", "path", "plug")
    assert (path.code, path.out.strip()) == (0, str(family["plug"].resolve()))
    shown = family.run("app", "work", "show", plug_item)
    assert shown.code == 0, shown.err
    assert item_folder("plug") in shown.out
    edited = family.run("app", "work", "edit", f"app.work/{item_folder('app')}",
                        "--blocked-by", plug_item)
    assert edited.code == 0, edited.err
    validated = family.run("app", "validate")
    assert validated.code == 0, validated.out + validated.err


def test_a_project_found_this_way_is_in_no_view(tmp_path):
    family = workspace(tmp_path)
    before = family.run("app", "project", "list")
    assert family.run("app", "project", "path", "plug").code == 0
    family.run("app", "work", "edit", f"app.work/{item_folder('app')}",
               "--blocked-by", f"plug.work/{item_folder('plug')}")
    after = family.run("app", "project", "list")
    assert before.code == after.code == 0
    assert before.out == after.out
    assert "plug" not in after.out
    listed = family.run("app", "work", "list")
    assert listed.code == 0, listed.err
    assert item_folder("plug") not in listed.out


def test_the_designs_example_reaches_a_sibling_through_the_parents_manifest(tmp_path):
    family = build_family(tmp_path, docs_passes="all")
    path = family.run("desktop", "project", "path", "server")
    assert (path.code, path.out.strip()) == (0, str(family["server"].resolve()))
    assert "server" not in family.run("desktop", "project", "list").out


def test_a_deeper_cousin_and_the_manifest_that_placed_it(tmp_path):
    """A child of a child of a sibling, listed only by its own parent's
    manifest, two manifests below the one `app`'s ancestor holds."""
    ws = proj(tmp_path / "ws", "ws", children=["app", "srv"])
    app = proj(tmp_path / "app", "app", parent=["ws"])
    srv = proj(tmp_path / "srv", "srv", parent=["ws"], children=["plug"])
    plug = proj(tmp_path / "srv" / "plug", "plug", parent=["srv"], children=["ext"])
    ext = proj(tmp_path / "srv" / "plug" / "x" / "ext", "ext", parent=["plug"])
    write_manifest(ws, {"app": "../app", "srv": "../srv"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(srv, {"plug": "plug"})
    write_manifest(plug, {"ext": "x/ext"})
    registry = FsProjectRegistry.open(app)
    assert registry.project_folder("ext", app) == ext
    assert registry.project_folder("plug", app) == plug
    assert registry.found("ext") is None              # located, not in the graph
    assert registry.get("ext") is None
    assert registry.placement("ext", app).owner == plug
    assert registry.check() == []


def test_the_nearest_manifest_decides(tmp_path):
    """Breadth first: an entry one manifest down decides over one two
    manifests down, whichever is listed first."""
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    deep = proj(tmp_path / "deep", "deep")
    near = proj(tmp_path / "near", "near")
    one = proj(tmp_path / "x" / "lib", "lib")
    proj(tmp_path / "y" / "lib", "lib")
    deeper = proj(tmp_path / "deeper", "deeper")
    write_manifest(ws, {"deep": "../deep", "near": "../near"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(deep, {"deeper": "../deeper"})
    write_manifest(deeper, {"lib": "../y/lib"})
    write_manifest(near, {"lib": "../x/lib"})
    assert lookup(app, "lib") == one


def test_a_stale_entry_in_an_unrelated_manifest_never_overrules_the_search(tmp_path):
    """The combined review of TCW-118: `srv`, a sibling of `app`, has an
    entry for `lib` naming a folder that is not on this machine, and the
    search from `app` finds `lib` beside it. The manifests reached only in
    passing are read after the search, so the search's answer stands and
    every command of `app` works, as it does with no such entry."""
    family = workspace(tmp_path)
    family.roots["lib"] = _project(tmp_path, "lib")
    family.write_config("lib", {**family.config("lib"), "children": ["app"]})
    family.write_config("app", {**family.config("app"), "parents": ["ws", "lib"]})
    write_manifest(family["srv"], {"ws": "../ws", "plug": "plug",
                                   "lib": "../elsewhere/lib"})
    family.item("lib", item_folder("lib"))
    path = family.run("app", "project", "path", "lib")
    assert (path.code, path.out.strip()) == (0, str(family["lib"].resolve())), path.err
    for args in (("work", "list"), ("validate",)):
        result = family.run("app", *args)
        assert result.code == 0, (args, result.out + result.err)


def test_the_search_decides_over_an_entry_reached_in_passing(tmp_path):
    """Two folders declare `lib`: one beside `app`, which the search finds,
    and one that only a sibling's manifest places. The search's answer is
    used, with no problem recorded."""
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    srv = proj(tmp_path / "srv", "srv", parent=["ws"])
    beside = proj(tmp_path / "lib", "lib")
    proj(tmp_path / "far" / "lib", "lib")
    write_manifest(ws, {"app": "../app", "srv": "../srv"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(srv, {"ws": "../ws", "lib": "../far/lib"})
    assert lookup(app, "lib") == beside


def test_a_wrong_entry_reached_in_passing_is_passed_over_for_a_right_one(tmp_path):
    """The search finds nothing. `srv`'s manifest places `lib` at a folder
    that declares another project, and `tools`'s, read after it, places it
    where it is: the wrong entry is passed over, unrecorded, and the right
    one decides."""
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    srv = proj(tmp_path / "srv", "srv", parent=["ws"])
    tools = proj(tmp_path / "tools", "tools", parent=["ws"])
    real = proj(tmp_path / "real" / "lib", "lib")
    write_manifest(ws, {"app": "../app", "srv": "../srv", "tools": "../tools"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(srv, {"lib": "../tools"})
    write_manifest(tools, {"lib": "../real/lib"})
    registry = FsProjectRegistry.open(app)
    assert registry.project_folder("lib", app) == real
    assert registry.check() == []


def test_an_entry_reached_in_passing_for_a_folder_not_here_gives_way(tmp_path):
    """A first entry naming a folder not on this machine gives way to a
    later one that finds the project."""
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    srv = proj(tmp_path / "srv", "srv", parent=["ws"])
    tools = proj(tmp_path / "tools", "tools", parent=["ws"])
    real = proj(tmp_path / "real" / "lib", "lib")
    write_manifest(ws, {"app": "../app", "srv": "../srv", "tools": "../tools"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(srv, {"lib": "../gone/lib"})
    write_manifest(tools, {"lib": "../real/lib"})
    assert lookup(app, "lib") == real


def test_a_3x_copy_the_search_finds_is_not_overruled_in_passing(tmp_path):
    """The search finds a 3.x `lib` beside `app`; a sibling's manifest
    places a 4.0 `lib` elsewhere. The search's answer stands: the lookup
    says to migrate the copy beside `app`, as it does with no such entry."""
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    srv = proj(tmp_path / "srv", "srv", parent=["ws"])
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / LEGACY_SENTINEL).write_text("id: lib\n")
    proj(tmp_path / "far" / "lib", "lib")
    write_manifest(ws, {"app": "../app", "srv": "../srv"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(srv, {"ws": "../ws", "lib": "../far/lib"})
    with pytest.raises(ProjectGraphError, match="tcw migrate"):
        FsProjectRegistry.open(app).project_folder("lib", app)


def test_a_cycle_of_manifests_ends_and_an_id_nowhere_is_unknown(tmp_path):
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    a = proj(tmp_path / "c" / "a", "a")
    b = proj(tmp_path / "c" / "b", "b")
    write_manifest(ws, {"a": "../c/a"})
    write_manifest(app, {"ws": "../ws"})
    write_manifest(a, {"b": "../b", "ws": "../../ws", "app": "../../app"})
    write_manifest(b, {"a": "../a", "ws": "../../ws"})
    registry = FsProjectRegistry.open(app)
    with pytest.raises(UnknownProject):
        registry.project_folder("zz", app)
    assert registry.project_folder("b", app) == b


def test_an_id_nowhere_keeps_todays_message(tmp_path):
    family = workspace(tmp_path)
    shown = family.run("app", "work", "show", f"zz.work/{item_folder('zz')}")
    assert shown.code == 1
    assert MISSING in shown.err
    assert family.run("app", "project", "path", "zz").code == 1


def test_forty_projects_read_each_manifest_once(tmp_path, reads):
    """Each project's manifests are read once for the whole command, however
    many lookups pass through them: a family of forty costs reads in
    proportion to forty, not to forty squared."""
    size = 40
    ws = proj(tmp_path / "ws", "ws")
    app = proj(tmp_path / "app", "app", parent=["ws"])
    write_manifest(app, {"ws": "../ws"})
    names = [f"p{n:02d}" for n in range(size)]
    for name in names:
        proj(tmp_path / "m" / name, name)
    write_manifest(ws, {name: f"../m/{name}" for name in names[:10]})
    for index, name in enumerate(names):
        listed = names[10 + index * 3: 13 + index * 3]
        if listed:
            write_manifest(tmp_path / "m" / name, {n: f"../{n}" for n in listed})
    registry = FsProjectRegistry.open(app)
    reads["read"].clear()
    for missing in ("zz", "zy", "zx"):
        with pytest.raises(UnknownProject):
            registry.project_folder(missing, app)
    for name in names:
        assert registry.project_folder(name, app) == (tmp_path / "m" / name).resolve()
    manifests = [p for p in reads["read"] if p.name.startswith("tcw-manifest")]
    assert len(manifests) == len(set(manifests))
    assert len(reads["read"]) <= 8 * (size + 2)
