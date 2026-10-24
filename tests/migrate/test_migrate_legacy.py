"""`tcw migrate`'s copies of the TCW 3.x readers read as 3.x read (TCW-116
Design 4.1, 8.2; plan Step 2).

The listings are compared with what TCW 3.0.2 itself listed for the same
fixture, recorded once in `tests/migrate/golden/` by
`tests/migrate/record_3x_listings.py`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tcw.migrate import legacy
from tests.migrate.fixtures import build_f_single, user_file

GOLDEN = Path(__file__).resolve().parent / "golden"


def listed(name: str, command: str, key: str) -> list[str]:
    golden = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    return sorted(row["path"] for row in json.loads(golden["commands"][command]["stdout"])[key])


@pytest.mark.parametrize("name, backend", [("f-single", "jira"),
                                           ("f-single-files", "filesystem")])
def test_the_objects_are_the_ones_3x_listed(tmp_path, name, backend):
    root = build_f_single(tmp_path / "app", backend="jira" if backend == "jira" else "files",
                          git=False)
    assert legacy.objects_3x(root / "docs/taxonomy", "taxonomy") == \
        listed(name, "taxonomy list --json", "terms")
    assert legacy.objects_3x(root / "docs/capabilities", "capabilities") == \
        listed(name, "capabilities list --json", "capabilities")


def test_work_items_are_the_folders_holding_item_yaml(tmp_path):
    jira = build_f_single(tmp_path / "jira", git=False)
    files = build_f_single(tmp_path / "files", backend="files", git=False)
    assert legacy.objects_3x(jira / "docs/work", "work") == ["APP-1-a", "APP-2-b"]
    assert legacy.objects_3x(files / "docs/work", "work") == ["2026-10-01-a",
                                                               "2026-10-02-b"]


def test_a_hidden_folder_is_no_capability_and_a_missing_store_lists_nothing(tmp_path):
    store = tmp_path / "caps"
    (store / ".hidden/x").mkdir(parents=True)
    (store / ".hidden/x/meta.yaml").write_text("Status: Supported\n")
    assert legacy.objects_3x(store, "capabilities") == []
    assert legacy.objects_3x(tmp_path / "none", "taxonomy") == []


def test_the_layers_merge_as_3x_merged_them(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    root = build_f_single(tmp_path / "app", config_home=tmp_path / "xdg", git=False)
    layers = legacy.read_3x_layers(root)
    assert layers.user.path == user_file(tmp_path / "xdg")
    assert layers.problems == []
    merged = layers.merged()
    assert merged["user"] == {"name": "Ada"}
    assert merged["id"] == "app"
    # The user-wide file's spec prompt, a chain list, resolved its `inherit`.
    prompt = merged["work"]["stages"]["spec"]["prompt"]
    assert prompt[0] == {"blob": "Write the spec."}
    assert prompt[-1]["blob"] == "My own reminder."


def test_personal_layers_are_not_read_when_3x_would_not(tmp_path):
    root = build_f_single(tmp_path / "app", git=False)
    assert "user" not in legacy.read_3x_layers(root).merged()


def test_a_duplicate_key_is_a_problem_naming_it(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "tcw-config.yaml").write_text("id: app\nid: again\n")
    layers = legacy.read_3x_layers(root)
    assert layers.shared.data is None
    assert "duplicate key: 'id'" in layers.shared.problem
    assert layers.problems == [layers.shared]


def test_a_file_is_read_with_its_line_endings(tmp_path):
    (tmp_path / "tcw-config.yaml").write_bytes(b"id: app\r\n")
    layer = legacy.read_layer_3x(tmp_path / "tcw-config.yaml", "shared")
    assert layer.text == "id: app\r\n" and layer.data == {"id": "app"}


def test_a_file_that_is_not_utf8_or_not_a_mapping_is_a_problem(tmp_path):
    (tmp_path / "a.yaml").write_bytes(b"id: \xff\n")
    (tmp_path / "b.yaml").write_text("- a\n")
    assert "not valid UTF-8" in legacy.read_layer_3x(tmp_path / "a.yaml", "shared").problem
    assert legacy.read_layer_3x(tmp_path / "b.yaml", "shared").problem == \
        "must be a mapping, not a list"
    absent = legacy.read_layer_3x(tmp_path / "c.yaml", "shared")
    assert (absent.present, absent.problem) == (False, None)


def test_links_outside_code_are_found_with_their_place():
    text = ("See [x](tcw://C/cli/x) and `[y](tcw://C/cli/y)`.\n"
            "```\n[z](tcw://T/z)\n```\n[w](tcw://W/app/APP-1-a)\n")
    found = legacy.links_3x(text)
    assert [link.uri for link in found] == ["tcw://C/cli/x", "tcw://W/app/APP-1-a"]
    assert all(text[link.start:link.end] == link.uri for link in found)
    assert found[0].parsed == legacy.TcwRef3("", "C", "cli/x")
    assert found[1].parsed == legacy.TcwRef3("", "W", "app/APP-1-a")


def test_a_link_is_parsed_as_3x_parsed_it():
    assert legacy.parse_tcw_uri_3x("tcw://core/T/term") == legacy.TcwRef3("core", "T", "term")
    assert legacy.parse_tcw_uri_3x("tcw://c//cli/x") == legacy.TcwRef3("", "C", "cli/x")
    assert legacy.parse_tcw_uri_3x("tcw://x/y") is None
    assert legacy.parse_tcw_uri_3x("tcw://C/a/../b") is None


def _as_4_0(root: Path) -> None:
    """The project's two files moved into `.tcw/`, as a finished run leaves them."""
    (root / ".tcw").mkdir()
    for name in ("tcw-config.yaml", "tcw-config.local.yaml"):
        text = (root / name).read_text()
        (root / ".tcw" / name).write_text("tcw-version: 4\n" + text)
        (root / name).unlink()


def test_the_jira_settings_read_alike_from_either_form(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    three = build_f_single(tmp_path / "three", config_home=tmp_path / "xdg", git=False)
    four = tmp_path / "four"
    shutil.copytree(three, four)
    _as_4_0(four)
    a, b = legacy.own_jira_layers(three), legacy.own_jira_layers(four)
    assert a.jira == b.jira
    assert a.jira["project"] == "APP"
    assert a.jira["fields"] == {"project": "TCW Project", "item": "TCW Item"}
    assert a.file_of(("project",)) == three / "tcw-config.yaml"
    assert b.file_of(("project",)) == four / ".tcw/tcw-config.yaml"


def test_credential_names_come_from_a_3x_root_personal_file(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    root = build_f_single(tmp_path / "app", git=False)
    (root / "tcw-config.local.yaml").write_text(
        "work:\n  jira:\n    credentials:\n      email-env: MY_EMAIL\n"
        "    project: NOT-ALLOWED\n")
    found = legacy.own_jira_layers(root)
    assert found.jira["credentials"]["email-env"] == "MY_EMAIL"
    assert found.jira["project"] == "APP"            # a shared key, refused there
    assert found.file_of(("credentials", "email-env")) == root / "tcw-config.local.yaml"


def test_a_store_folder_is_placed_as_3x_placed_it(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    default = legacy.store_folder_3x(root, "work", None)
    assert (default.folder, default.form) == (root / "docs/work", None)
    inside = legacy.store_folder_3x(root, "work", {"path": "board/../board"})
    assert (inside.folder, inside.configured, inside.form) == (
        root / "board/../board", "board/../board", None)
    assert legacy.store_folder_3x(root, "work", {"path": "../board"}).form == "outside"
    assert legacy.store_folder_3x(root, "work", {"path": str(root / "b")}).form is None
    assert legacy.store_folder_3x(root, "work", {"path": str(tmp_path)}).form == "outside"
    assert legacy.store_folder_3x(
        root, "taxonomy", {"repository": {"url": "x"}}).form == "repository"
    assert legacy.store_folder_3x(root, "work", {"path": ""}).problem


# ---------------------------------------------------------------------------
# Part 2's readers on F-full's pieces (plan Step 15)


def full_golden(project: str, command: str) -> dict:
    golden = json.loads((GOLDEN / "f-full.json").read_text(encoding="utf-8"))
    return json.loads(golden["projects"][project][command]["stdout"])


@pytest.fixture
def f_full(tmp_path, monkeypatch):
    from tests.migrate.fixtures import build_f_full
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    build_f_full(tmp_path / "base", cache_home=tmp_path / "cache", git=False)
    return tmp_path / "base"


def _config(folder: Path) -> dict:
    data, problem = legacy.parse_mapping_3x((folder / "tcw-config.yaml").read_text(),
                                            folder / "tcw-config.yaml")
    assert problem is None
    return data


def test_the_relations_are_read_in_3x_order(f_full):
    from tests.migrate.fixtures import LIB_URL
    found, problems = legacy.relations_3x(_config(f_full / "ws/app"), "tcw-config.yaml")
    assert problems == []
    assert found == [
        legacy.Relation3("children", "kid", "../kid"),
        legacy.Relation3("parent", "ws", ".."),
        legacy.Relation3("upstream", "core", "../../core"),
        legacy.Relation3("upstream", "lib", None, legacy.RepoDecl3(LIB_URL))]
    ws, _ = legacy.relations_3x(_config(f_full / "ws"), "tcw-config.yaml")
    assert [(r.id, r.jira) for r in ws] == [("app", {"project": "APP"}), ("sib", None)]


def test_a_relation_3x_refused_is_a_problem_naming_the_file():
    found, problems = legacy.relations_3x(
        {"projects": {"parent": {"ws": {}}, "children": "x", "peers": {}}}, "a.yaml")
    assert found == []
    assert problems == ["a.yaml: unknown projects keys: peers",
                        "a.yaml: projects.children must be a mapping",
                        "a.yaml: projects.parent.ws: needs 'path', 'repository', or both"]


def test_extends_is_read_as_3x_read_it():
    assert legacy.extends_3x({"extends": ["core", "kid"]}, "x") == ["core", "kid"]
    assert legacy.extends_3x({}, "x") == []
    for bad, message in (({"extends": {"core": "../core"}}, "legacy extends map"),
                         ({"extends": ["core", "core"]}, "duplicate project IDs"),
                         ({"extends": ["Core"]}, "project ID must match")):
        with pytest.raises(ValueError, match=message):
            legacy.extends_3x(bad, "taxonomy.extends")


def test_each_related_project_is_placed_where_3x_placed_it(f_full, tmp_path):
    from tests.migrate.fixtures import lib_clone
    app = f_full / "ws/app"
    placed = {r.id: legacy.locate_3x(app, r)
              for r in legacy.relations_3x(_config(app), "tcw-config.yaml")[0]}
    assert placed == {"kid": (f_full / "ws/kid", "locator"),
                      "ws": (f_full / "ws", "locator"),
                      "core": (f_full / "core", "locator"),
                      "lib": (lib_clone(tmp_path / "cache"), "repository")}


def test_the_variable_comes_first_and_absent_names_the_first_place(f_full, tmp_path,
                                                                   monkeypatch):
    app = f_full / "ws/app"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setenv("TCW_PROJECT_CORE", str(elsewhere))
    core = legacy.Relation3("upstream", "core", "../../core")
    assert legacy.locate_3x(app, core) == (elsewhere.resolve(), "variable")
    monkeypatch.delenv("TCW_PROJECT_CORE")
    gone = legacy.Relation3("upstream", "gone", "../gone")
    assert legacy.locate_3x(app, gone) == (f_full / "ws/gone", "absent")


def test_the_cache_folder_is_3x_s(tmp_path, monkeypatch):
    """3.x prints no cache folder, so the expected values are written by hand
    from the tag's `_cache_key` (Decided 3)."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    url = legacy.RepoDecl3("https://example.invalid/lib.git")
    assert legacy.cache_folder_3x(tmp_path, url) == \
        tmp_path / "c/tcw/stores/https-example.invalid-lib-b26a43c0c94d"
    pinned = legacy.RepoDecl3("git@example.invalid:team/lib.git", ref="v1", path="sub")
    assert legacy.cache_folder_3x(tmp_path, pinned).relative_to(tmp_path / "c") == \
        Path("tcw/stores/example.invalid-team-lib-"
             + legacy._cache_key_3x(pinned).rsplit("-", 1)[1], "sub")
    checkout = legacy.RepoDecl3("https://x/lib.git", checkout="../lib")
    assert legacy.cache_folder_3x(tmp_path / "p", checkout) == tmp_path / "p/../lib"
    monkeypatch.delenv("XDG_CACHE_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert legacy.cache_folder_3x(tmp_path, url).parent == \
        tmp_path / "home/.cache/tcw/stores"


def _sources(f_full: Path, project: str) -> dict[str, dict[str, str]]:
    """Each `capabilities.extends` source of `project`'s capabilities, as
    `{cap-id: id-path}`."""
    from tests.migrate.fixtures import F_FULL_PROJECTS, lib_clone
    folders = {pid: f_full / rel for pid, rel in F_FULL_PROJECTS.items()}
    folders["lib"] = lib_clone(f_full.parent / "cache")
    names = legacy.extends_3x(_config(folders[project]).get("capabilities"), "x")
    return {alias: {i: p for p, i in legacy.ledger_3x(
        folders[alias] / "docs/capabilities").capabilities.items()} for alias in names}


@pytest.mark.parametrize("project", ["app", "sib", "core"])
def test_each_override_applies_where_3x_applied_it(f_full, project):
    """The capability each pointer matches is the one 3.0.2 showed with the
    override's own name or Status."""
    from tests.migrate.fixtures import F_FULL_PROJECTS
    folder = f_full / F_FULL_PROJECTS[project]
    ledger = legacy.ledger_3x(folder / "docs/capabilities")
    assert ledger.overrides
    sources = _sources(f_full, project)
    for path, (pointer, meta) in ledger.overrides.items():
        [(alias, target)] = legacy.override_target_3x(pointer, sources)
        shown = full_golden(project, f"capabilities show {alias}/{target} --json")
        shown = shown["capability"]
        if "name" in meta:
            assert shown["name"] == meta["name"], path
        assert shown["status"] == meta.get("Status", shown["status"]), path


def test_the_alias_form_matches_only_its_own_source():
    sources = {"core": {"cap-1": "billing"}, "ws": {"cap-2": "cli/shared"}}
    assert legacy.override_target_3x("core/cap-1", sources) == [("core", "billing")]
    assert legacy.override_target_3x("ws/cap-1", sources) == []
    assert legacy.override_target_3x("cap-1", sources) == [("core", "billing")]
    assert legacy.override_target_3x("cap-9", sources) == []


def test_a_bare_reference_has_the_owner_3x_gave_it(f_full):
    """Every capability 3.0.2 listed in `app`, read back by its bare path
    when it is unique: its own first, else the one source holding it."""
    own = set(legacy.ledger_3x(f_full / "ws/app/docs/capabilities").capabilities)
    sources = {alias: set(ids.values()) for alias, ids in _sources(f_full, "app").items()}
    for row in full_golden("app", "capabilities list --json")["capabilities"]:
        if row["origin"] == "local":
            assert legacy.bare_owner_3x(row["path"], own, sources) == (None, row["path"])
            continue
        prefixed = legacy.bare_owner_3x(row["path"], own, sources)
        assert prefixed == (row["origin"], row["path"].split("/", 1)[1])
    # Bare-wins-local: ws also has `cli/shared`.
    assert legacy.bare_owner_3x("cli/shared", own, sources) == (None, "cli/shared")
    assert legacy.bare_owner_3x("auth/login", own, sources) == ("core", "auth/login")
    assert legacy.bare_owner_3x("nothing/here", own, sources) == (None, "nothing/here")
    with pytest.raises(legacy.Ambiguous3):
        legacy.bare_owner_3x("x", set(), {"a": {"x"}, "b": {"x"}})


def test_a_bare_term_has_the_owner_3x_gave_it(f_full):
    from tests.migrate.fixtures import F_FULL_PROJECTS
    own = set(legacy.objects_3x(f_full / "ws/app/docs/taxonomy", "taxonomy"))
    sources = {alias: set(legacy.objects_3x(f_full / F_FULL_PROJECTS[alias]
                                            / "docs/taxonomy", "taxonomy"))
               for alias in ("core", "kid")}
    listed = full_golden("app", "taxonomy list --json")["terms"]
    for row in listed:
        if row["origin"] != "local":
            bare = row["path"].split("/", 1)[1]
            assert legacy.bare_owner_3x(bare, own, sources) == (row["origin"], bare)
    assert legacy.bare_owner_3x("core/money", own, sources) == ("core", "money")


def test_a_capabilities_yaml_entry_is_routed_as_3x_routed_it():
    def route(path, **kw):
        args = dict(extends={"core", "ws"}, children=["kid"], has_ledger=True,
                    own_namespaces={"cli"}, project_id="app") | kw
        return legacy.route_entry_3x(path, **args)
    assert route("core/billing") == (None, "core/billing")
    assert route("kid/k-thing") == ("kid", "k-thing")
    assert route("cli/x") == (None, "cli/x")
    assert route("kid") == "kid: names project 'kid' but no capability"
    assert "ambiguous" in route("kid/x", own_namespaces={"kid"})
    assert route("cli/x", has_ledger=False, children=[]) == (
        "cli/x: this project ('app') keeps no capabilities ledger; qualify the path "
        "with a child project id (it declares no child projects)")
    assert route("kid/k-thing", has_ledger=False) == ("kid", "k-thing")


def test_a_link_is_read_by_the_store_s_get(f_full):
    own = {"capabilities": {"cli/x"}, "taxonomy": {"invoice"}}
    sources = {"core": {"capabilities": {"billing"}, "taxonomy": {"money"}}}
    parse = legacy.parse_tcw_uri_3x
    assert legacy.link_owner_3x(parse("tcw://C/cli/x"), own, sources) == (None, "cli/x")
    assert legacy.link_owner_3x(parse("tcw://C/billing"), own, sources) == \
        ("core", "billing")
    assert legacy.link_owner_3x(parse("tcw://core/T/money"), own, sources) == \
        ("core", "money")
