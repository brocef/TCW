"""TCW-113 (plan Step 9): `tcw taxonomy` and `tcw capabilities` `list`,
`show` and `search` across a scope (spec Design 1, 2, 4). Each test names
the acceptance criterion it proves, on the family `F` of
`tests/families.py`. Every command passes `--scope` (or `--project`)
explicitly: the default stays what each did before until Step 11."""

from __future__ import annotations

import shutil

import pytest

from tests.families import build_family, item_folder
from tests.statefiles import CAPABILITY_STATE

ABC, DEF, GHI = ("shared.capabilities/abc", "desktop.capabilities/def",
                 "shared.capabilities/ghi")


@pytest.fixture
def family(tmp_path):
    return build_family(tmp_path, docs_passes="none")


def warned(result, project_id: str) -> list[str]:
    return [line for line in result.err_lines
            if line.startswith(f"warning: '{project_id}' is unavailable")]


def record(result, key: str, full_id: str) -> dict:
    [found] = [r for r in result.json[key] if r["full-id"] == full_id]
    return found


def entry(project, status, inherited, full_id):
    return {"project": project, "status": status, "inherited": inherited,
            "full-id": full_id}


# -- AC 1 ------------------------------------------------------------------------------


def test_ac1_the_six_tree_commands_take_scope_down(family):
    for argv in (["taxonomy", "list"], ["taxonomy", "show", "invoice"],
                 ["taxonomy", "search", "inv"], ["capabilities", "list"],
                 ["capabilities", "show", "abc"], ["capabilities", "search", "abc"],
                 ["work", "list"], ["work", "show", item_folder("shared")]):
        ran = family.run("shared", *argv, "--scope", "down")
        assert ran.code == 0, (argv, ran.err)
    assert family.run("shared", "capabilities", "drift", "--scope", "up").code == 2
    assert family.run("shared", "capabilities", "list", "--scope", "sideways").code == 2


# -- AC 8 ------------------------------------------------------------------------------


def test_ac8_an_unavailable_child_in_taxonomy_and_capabilities(family):
    for axis in ("capabilities", "taxonomy"):
        ran = family.run("shared", axis, "list", "--scope", "down")
        assert ran.code == 0, ran.err
        assert len(warned(ran, "mobile")) == 1
    shown = family.run("shared", "capabilities", "show", "abc", "--scope", "down")
    assert shown.code == 0, shown.err
    assert "  unavailable: mobile" in shown.lines
    [line] = warned(shown, "mobile")
    assert line.startswith("warning: 'mobile' is unavailable, so its status is not shown")
    term = family.run("shared", "taxonomy", "show", "invoice", "--scope", "down")
    assert warned(term, "mobile")[0].startswith(
        "warning: 'mobile' is unavailable, so its taxonomy entries are not included")


# -- AC 9-11 ---------------------------------------------------------------------------


def test_ac9_up_is_the_view(family):
    ran = family.run("desktop", "capabilities", "list", "--scope", "up")
    assert ran.lines == ["desktop.capabilities/abc", DEF, GHI]
    document = family.run("desktop", "capabilities", "list", "--scope", "up", "--json").json
    overrides = {r["full-id"]: r["overrides"] for r in document["capabilities"]}
    assert overrides == {"desktop.capabilities/abc": ABC, DEF: None, GHI: None}
    assert not any("statuses" in r for r in document["capabilities"])


def test_ac10_an_ancestor_that_passes_nothing_is_listed_only_by_project(family):
    up = family.run("desktop", "taxonomy", "list", "--scope", "up")
    assert up.lines == ["shared.taxonomy/invoice"]
    projects = family.run("desktop", "taxonomy", "list", "--scope", "up", "--json").json[
        "projects"]
    assert projects == [{"id": "docs", "relation": "ancestor"},
                        {"id": "shared", "relation": "ancestor"},
                        {"id": "desktop", "relation": "current"}]
    docs = family.run("desktop", "taxonomy", "list", "--scope", "up", "--project", "docs")
    assert docs.lines == ["docs.taxonomy/plan"]
    assert family.run("desktop", "taxonomy", "show", "plan", "--scope", "up").code == 4
    named = family.run("desktop", "taxonomy", "show", "docs.taxonomy/plan", "--json")
    assert named.json["term"]["full-id"] == "docs.taxonomy/plan"
    family.remove("docs")
    gone = family.run("desktop", "taxonomy", "list", "--scope", "up")
    assert gone.code == 0, gone.err
    assert gone.lines == ["shared.taxonomy/invoice"]
    assert "docs" not in gone.err
    only = family.run("desktop", "taxonomy", "list", "--scope", "up", "--project", "docs")
    assert only.code == 0 and only.out == ""
    assert len(warned(only, "docs")) == 1


def test_ac11_project_keeps_an_override_and_its_original_apart(family):
    shared = family.run("desktop", "capabilities", "list", "--scope", "up",
                        "--project", "shared")
    assert shared.lines == [ABC, GHI]
    desktop = family.run("desktop", "capabilities", "list", "--scope", "up",
                         "--project", "desktop")
    assert desktop.lines == ["desktop.capabilities/abc", DEF]


# -- AC 12-16 --------------------------------------------------------------------------


def test_ac12_grouped_rows_in_down(family):
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert ran.lines == [ABC, DEF, GHI]


def test_ac13_statuses_and_overridden_by(family):
    ran = family.run("shared", "capabilities", "list", "--scope", "down", "--json")
    abc = record(ran, "capabilities", ABC)
    assert abc["statuses"] == [entry("shared", "Missing", False, ABC),
                               entry("desktop", "Supported", False, "desktop.capabilities/abc"),
                               entry("server", "Omitted", False, "server.capabilities/abc")]
    assert abc["overridden-by"] == ["desktop.capabilities/abc", "server.capabilities/abc"]
    ghi = record(ran, "capabilities", GHI)
    assert ghi["statuses"] == [entry("shared", "Missing", False, GHI),
                               entry("desktop", "Missing", True, GHI),
                               entry("server", "Missing", True, GHI)]
    assert ghi["overridden-by"] == []
    assert record(ran, "capabilities", DEF)["statuses"] == [
        entry("desktop", "Supported", False, DEF)]


BLOCK = ["status by project:", "  Missing: shared", "  Supported: desktop",
         "  Omitted: server", "  unavailable: mobile"]


@pytest.mark.parametrize("named", ["abc", ABC])
def test_ac14_show_prints_the_status_by_project(family, named):
    ran = family.run("shared", "capabilities", "show", named, "--scope", "down")
    assert ran.code == 0, ran.err
    at = ran.lines.index("status by project:")
    assert ran.lines[at:at + 5] == BLOCK
    assert ("overridden by: desktop.capabilities/abc, server.capabilities/abc"
            in ran.lines)


def test_ac14_own_prints_neither(family):
    ran = family.run("shared", "capabilities", "show", "abc", "--scope", "own")
    assert ran.code == 0, ran.err
    assert "status by project:" not in ran.lines
    assert not [line for line in ran.lines if line.startswith("overridden by:")]


def test_ac15_a_status_inherited_without_a_ruling(family):
    family.capability("server", "abc", Priority="P2")
    ran = family.run("shared", "capabilities", "list", "--scope", "down", "--json")
    # Marked inherited, and naming server's own object, which its view comes
    # from (review round 5, finding 1).
    assert (entry("server", "Missing", True, "server.capabilities/abc")
            in record(ran, "capabilities", ABC)["statuses"])
    shown_json = family.run("shared", "capabilities", "show", "abc", "--scope", "down",
                            "--json")
    assert (entry("server", "Missing", True, "server.capabilities/abc")
            in shown_json.json["capability"]["statuses"])
    shown = family.run("shared", "capabilities", "show", "abc", "--scope", "down")
    at = shown.lines.index("status by project:")
    assert shown.lines[at:at + 3] == ["status by project:",
                                      "  Missing: shared, server (inherited)",
                                      "  Supported: desktop"]


def add_grandchild(family) -> None:
    """`tablet`, a child of `desktop`, whose own `abc` holds only a
    Priority: an override of `desktop`'s that sets no Status."""
    from tests.families import _project
    family.roots["tablet"] = _project(family.base, "tablet")
    family.add_parent("tablet", "desktop")
    family.add_child("desktop", "tablet")
    family.capability("tablet", "abc", Priority="P2")


def test_ac15_a_grandchilds_override_that_sets_no_status(family):
    # The record's `overridden-by` names only direct overrides, so the
    # entry's `full-id` is what says tablet has an object of its own here.
    add_grandchild(family)
    ran = family.run("shared", "capabilities", "list", "--scope", "down", "--json")
    assert ran.code == 0, ran.err
    abc = record(ran, "capabilities", ABC)
    assert "tablet.capabilities/abc" not in abc["overridden-by"]
    assert (entry("tablet", "Supported", True, "tablet.capabilities/abc")
            in abc["statuses"])


def test_ac16_status_across_the_scope(family):
    ran = family.run("shared", "capabilities", "list", "--scope", "down",
                     "--status", "Supported")
    assert ran.lines == [ABC, DEF]
    own = family.run("shared", "capabilities", "list", "--scope", "own",
                     "--status", "Supported")
    assert own.out == ""


# -- explicit `own` (plan choice 12) ----------------------------------------------------


def test_explicit_own_show_by_id_path_names_the_projects_own_object(family):
    hint = family.run("desktop", "capabilities", "show", "ghi", "--scope", "own")
    assert hint.code == 4
    assert "--scope up" in hint.err and GHI in hint.err
    abc = family.run("desktop", "capabilities", "show", "abc", "--scope", "own", "--json")
    assert abc.json["capability"]["full-id"] == "desktop.capabilities/abc"
    assert family.run("desktop", "capabilities", "list", "--scope", "own").lines == [
        "desktop.capabilities/abc", DEF]
    up = family.run("desktop", "capabilities", "show", "ghi", "--scope", "up", "--json")
    assert up.json["capability"]["full-id"] == GHI
    family.remove("shared")
    gone = family.run("desktop", "capabilities", "show", "ghi", "--scope", "own")
    assert gone.code == 4, gone.err
    # The hint is left out (Design 4.8); the warning `list` gives says why
    # (Design 4.9).
    assert "there: add --scope up" not in gone.err
    assert "showing only 'desktop''s own declarations" in gone.err


# -- AC 18, 19, 32 ---------------------------------------------------------------------


def _zz(family):
    for pid in ("desktop", "server"):
        family.capability(pid, "zz", description="", name="Zz", Status="Supported")


def test_ac18_two_groups_at_one_path(family):
    _zz(family)
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert "desktop.capabilities/zz" in ran.lines and "server.capabilities/zz" in ran.lines
    both = family.run("shared", "capabilities", "show", "zz", "--scope", "down")
    assert both.code == 2
    assert "desktop.capabilities/zz" in both.err and "server.capabilities/zz" in both.err
    assert "'zz' names 2 objects in --scope down" in both.err
    one = family.run("shared", "capabilities", "show", "zz", "--scope", "down",
                     "--project", "server", "--json")
    assert one.code == 0, one.err
    found = one.json["capability"]
    assert found["full-id"] == "server.capabilities/zz"
    assert "statuses" not in found and "overridden-by" not in found
    listed = family.run("shared", "capabilities", "list", "--scope", "down",
                        "--project", "desktop", "--json")
    assert listed.json["capabilities"]
    assert not any("statuses" in r or "overridden-by" in r
                   for r in listed.json["capabilities"])
    mixed = family.run("shared", "capabilities", "show", "desktop.capabilities/zz",
                       "--scope", "down", "--project", "server")
    assert mixed.code == 2
    assert "'desktop'" in mixed.err and "'server'" in mixed.err


def test_ac32_row_order(family):
    _zz(family)
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert ran.lines == [ABC, DEF, GHI, "desktop.capabilities/zz", "server.capabilities/zz"]


def test_ac19_what_down_leaves_out_all_puts_back(tmp_path):
    family = build_family(tmp_path, docs_passes="all")
    family.capability("docs", "xyz", description="", name="Xyz", Status="Missing")
    family.capability("desktop", "xyz", Status="Supported")
    family.capability("server", "xyz", Status="Omitted")
    down = family.run("shared", "capabilities", "list", "--scope", "down")
    assert down.code == 0, down.err
    assert "desktop.capabilities/xyz" in down.lines
    assert "server.capabilities/xyz" in down.lines
    assert "docs.capabilities/xyz" not in down.lines
    every = family.run("shared", "capabilities", "list", "--scope", "all", "--json")
    assert every.code == 0, every.err
    ids = [r["full-id"] for r in every.json["capabilities"]]
    assert ids.count("docs.capabilities/xyz") == 1
    assert "desktop.capabilities/xyz" not in ids and "server.capabilities/xyz" not in ids
    statuses = record(every, "capabilities", "docs.capabilities/xyz")["statuses"]
    assert [e["project"] for e in statuses] == ["docs", "shared", "desktop", "server"]
    assert statuses[1]["inherited"] is True


# -- AC 20, 21, 29 ---------------------------------------------------------------------


def test_ac20_a_descendant_whose_view_cannot_be_built(family):
    family.add_parent("desktop", "ext", inherit=["capabilities"])
    ran = family.run("shared", "capabilities", "list", "--scope", "down", "--json")
    assert ran.code == 0, ran.err
    assert [r["full-id"] for r in ran.json["capabilities"]] == [ABC, GHI]
    [line] = warned(ran, "desktop")
    assert "'desktop' inherits its capabilities from project 'ext'" in line
    assert "desktop" not in [e["project"] for e in
                             record(ran, "capabilities", ABC)["statuses"]]
    assert family.run("desktop", "capabilities", "list", "--scope", "up").code == 7


@pytest.mark.parametrize("scope", ["up", "down", "all"])
def test_ac21_the_view_is_needed_outside_own(family, scope):
    family.remove("shared")
    assert family.run("desktop", "capabilities", "list", "--scope", scope).code == 7


def test_ac21_a_failure_on_the_active_side_is_not_put_on_a_descendant(tmp_path):
    family = build_family(tmp_path, docs_passes="all")
    family.remove("docs")
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert ran.code == 7
    assert not [line for line in ran.err_lines if "is unavailable" in line]


def test_ac29_a_descendant_whose_own_store_is_not_provisioned(family):
    document = family.config("server")
    document["capabilities"] = {
        "path": "docs/capabilities-elsewhere",
        "repository": {"url": "https://example.invalid/server-caps.git",
                       "path": "docs/capabilities"}}
    family.write_config("server", document)
    shutil.rmtree(family["server"] / "docs" / "capabilities")
    ran = family.run("shared", "capabilities", "list", "--scope", "down", "--json")
    assert ran.code == 0, ran.err
    assert [r["full-id"] for r in ran.json["capabilities"]] == [ABC, DEF, GHI]
    [line] = warned(ran, "server")
    assert "has not been provisioned here" in line and "provision" in line
    assert "server" not in [e["project"] for e in
                            record(ran, "capabilities", ABC)["statuses"]]


def test_ac29_a_state_file_that_is_not_yaml(family):
    state = family["desktop"] / "docs" / "capabilities" / "def" / CAPABILITY_STATE
    state.write_text("Status: [unclosed\n", encoding="utf-8")
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    [line] = warned(ran, "desktop")
    assert str(state) in line


# -- AC 31, 40 -------------------------------------------------------------------------


def test_ac31_search_up(family):
    family.capability("shared", "ghi", description="Ledger text", name="Ghi",
                      Status="Missing")
    up = family.run("desktop", "capabilities", "search", "Ledger text", "--scope", "up")
    assert up.lines == [GHI]
    own = family.run("desktop", "capabilities", "search", "Ledger text", "--scope", "own")
    assert own.out == ""


def test_ac40_namespace_and_search_match_a_rows_own_text(family):
    family.capability("shared", "cli/run", description="", name="Run", Status="Missing")
    family.capability("desktop", "cli/run", description="Desktop words")
    ns = family.run("shared", "capabilities", "list", "--scope", "down", "--namespace", "cli")
    assert ns.lines == ["shared.capabilities/cli/run"]
    found = family.run("shared", "capabilities", "search", "Desktop words", "--scope", "down")
    assert found.code == 0 and found.out == ""
    only = family.run("shared", "capabilities", "search", "Desktop words", "--scope", "down",
                      "--project", "desktop")
    assert only.lines == ["desktop.capabilities/cli/run"]


# -- one store per project, axis and kind (plan choice 4) ------------------------------


def test_each_store_is_opened_once(family, monkeypatch):
    from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
    opened = []
    for cls in (FsCapabilitiesStore, FsTaxonomyStore):
        real = cls.open.__func__

        def open_(cls, root, locator=None, real=real):
            store = real(cls, root, locator=locator)
            opened.append((store.project_id, cls.COMPONENT, locator is not None))
            return store
        monkeypatch.setattr(cls, "open", classmethod(open_))
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    assert opened and len(opened) == len(set(opened)), opened


def test_a_state_file_whose_version_cannot_be_read_makes_its_project_unavailable(family):
    state = family["desktop"] / "docs" / "capabilities" / "def" / CAPABILITY_STATE
    state.write_text("tcw-version: 99.0.0\nStatus: Supported\n", encoding="utf-8")
    ran = family.run("shared", "capabilities", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    assert DEF not in ran.lines
    [line] = warned(ran, "desktop")
    assert str(state) in line


def test_under_all_an_ancestor_counts_through_the_chain(tmp_path):
    # `shared` overrides `docs`'s `xyz`, so `docs`'s object is reached only
    # through V(X)'s chain, and `docs` still has its entry in `statuses`.
    family = build_family(tmp_path, docs_passes="all")
    family.capability("docs", "xyz", description="", name="Xyz", Status="Missing")
    family.capability("shared", "xyz", Status="Supported")
    ran = family.run("shared", "capabilities", "list", "--scope", "all", "--json")
    assert ran.code == 0, ran.err
    statuses = record(ran, "capabilities", "shared.capabilities/xyz")["statuses"]
    assert [e["project"] for e in statuses] == ["docs", "shared", "desktop", "server"]


def test_show_under_up_needs_the_view_for_an_own_object(family):
    family.remove("shared")
    assert family.run("desktop", "capabilities", "show", "abc", "--scope", "up").code == 7
    own = family.run("desktop", "capabilities", "show", "abc", "--scope", "own", "--json")
    assert own.code == 0, own.err
    assert own.json["capability"]["partial"] is True


def test_own_and_another_projects_listing_need_no_view(family):
    family.remove("shared")
    own = family.run("desktop", "capabilities", "list", "--scope", "own", "--json")
    assert own.code == 0, own.err
    assert all(r["partial"] for r in own.json["capabilities"])



def test_another_projects_listing_needs_no_view_of_the_active_one(family):
    # `desktop`'s view cannot be built (`ext` is not here); `shared`'s own
    # capabilities are still listed for `--project shared`.
    family.add_parent("desktop", "ext", inherit=["capabilities"])
    ran = family.run("desktop", "capabilities", "list", "--scope", "up",
                     "--project", "shared")
    assert ran.code == 0, ran.err
    assert ran.lines == [ABC, GHI]


@pytest.mark.parametrize("scope", ["own", "down"])
def test_a_path_not_found_keeps_find_trees_hints(family, scope):
    ran = family.run("shared", "capabilities", "show", "desktop/abc", "--scope", scope)
    assert ran.code == 4
    assert ("to name an object in project 'desktop', write desktop.capabilities/abc"
            in ran.err)


def test_up_and_own_keep_each_commands_order_today(family):
    # A taxonomy listing puts the project's own entries first (TCW-110 AC 4);
    # only the grouped rows of `down` and `all` take Design 4.4's order.
    family.term("desktop", "zebra", description="", name="Zebra", kind="vocabulary")
    up = family.run("desktop", "taxonomy", "list", "--scope", "up")
    assert up.lines == ["desktop.taxonomy/zebra", "shared.taxonomy/invoice"]
    assert up.lines == family.run("desktop", "taxonomy", "list", "--scope", "up").lines


# -- `own` is the default (plan Step 11) ------------------------------------------------


def test_ac2_own_is_the_default_on_the_trees(family):
    ran = family.run("desktop", "capabilities", "list")
    assert ran.lines == ["desktop.capabilities/abc", DEF]
    assert ran.lines == family.run("desktop", "capabilities", "list", "--scope", "own").lines
    assert family.run("desktop", "taxonomy", "list").out == ""
    for axis, key in (("capabilities", "capabilities"), ("taxonomy", "terms")):
        document = family.run("desktop", axis, "list", "--json").json
        assert "projects" not in document and key in document


def test_ac14_show_with_no_scope_prints_neither(family):
    ran = family.run("shared", "capabilities", "show", "abc")
    assert ran.code == 0, ran.err
    assert "status by project:" not in ran.lines
    assert not [line for line in ran.lines if line.startswith("overridden by:")]


def test_ac16_status_with_no_scope_lists_only_the_projects_own(family):
    assert family.run("shared", "capabilities", "list", "--status", "Supported").out == ""


def test_ac17_show_by_id_path_follows_the_default_scope(family):
    hint = family.run("desktop", "capabilities", "show", "ghi")
    assert hint.code == 4
    assert "--scope up" in hint.err and GHI in hint.err
    up = family.run("desktop", "capabilities", "show", "ghi", "--scope", "up", "--json")
    assert up.json["capability"]["full-id"] == GHI
    family.remove("shared")
    assert family.run("desktop", "capabilities", "show", "ghi").code == 4


def _unfetched(family, project_id: str, axis: str) -> None:
    """`project_id`'s `axis` store declared in a repository and not fetched."""
    document = family.config(project_id)
    document[axis] = {"path": f"docs/{axis}-elsewhere",
                      "repository": {"url": f"https://example.invalid/{axis}.git",
                                     "path": f"docs/{axis}"}}
    family.write_config(project_id, document)
    shutil.rmtree(family[project_id] / "docs" / axis)


@pytest.mark.parametrize("axis, given", [("taxonomy", "invoice"), ("capabilities", "ghi")])
def test_show_under_own_of_a_path_not_its_own_warns_when_the_view_cannot_be_built(
        family, axis, given):
    # Design 4.9: under `own` an inherited store that cannot be read is a
    # warning, as `list` gives it, naming the command that fetches it; the
    # path the project does not own is still not found (exit 4).
    _unfetched(family, "shared", axis)
    ran = family.run("desktop", axis, "show", given)
    assert ran.code == 4, ran.err
    fetch = f"tcw -C {family['shared'].resolve()} project provision --component {axis}"
    [warning] = [line for line in ran.err_lines if line.startswith("warning: ")]
    assert fetch in warning and "showing only 'desktop''s own declarations" in warning
    listed = family.run("desktop", axis, "list")
    assert warning in listed.err_lines
    assert ran.err_lines.index(warning) < len(ran.err_lines) - 1


def test_ac21_own_keeps_working_without_the_view(family):
    family.remove("shared")
    ran = family.run("desktop", "capabilities", "list", "--json")
    assert ran.code == 0, ran.err
    assert ran.json["capabilities"]
    assert all(r["partial"] is True for r in ran.json["capabilities"])


def test_ac31_search_with_no_scope_finds_only_the_projects_own(family):
    family.capability("shared", "ghi", description="Ledger text", name="Ghi",
                      Status="Missing")
    assert family.run("desktop", "capabilities", "search", "Ledger text").out == ""


EIGHT = (["taxonomy", "list"], ["taxonomy", "show", "word"], ["taxonomy", "search", "wo"],
         ["capabilities", "list"], ["capabilities", "show", "cap"],
         ["capabilities", "search", "ca"], ["work", "list"],
         ["work", "show", "2026-10-01-solo-item"])


def test_ac7_a_single_project_opens_no_other(tmp_path, monkeypatch):
    import subprocess

    from tcw.store.fs import FsTreeStore, init
    from tcw.store.project import FsProjectRegistry
    from tests.families import Family
    solo = tmp_path / "solo"
    solo.mkdir()
    subprocess.run(["git", "init", "-q", str(solo)], check=True)
    init(["taxonomy", "capabilities", "work"], solo, "solo")
    family = Family(tmp_path, {"solo": solo})
    family.capability("solo", "cap", description="", name="Cap", Status="Missing")
    family.term("solo", "word", description="", name="Word", kind="vocabulary")
    family.item("solo", "2026-10-01-solo-item")
    asked, opened = [], []
    real_folder = FsProjectRegistry.project_folder
    monkeypatch.setattr(FsProjectRegistry, "project_folder",
                        lambda self, pid, named_by: asked.append(pid)
                        or real_folder(self, pid, named_by))
    real_init = FsTreeStore.__init__

    def init_(self, root, *a, **kw):
        real_init(self, root, *a, **kw)
        opened.append(self.project_id)
    monkeypatch.setattr(FsTreeStore, "__init__", init_)
    for argv in EIGHT:
        own = family.run("solo", *argv, "--scope", "own")
        assert own.code == 0, (argv, own.err)
        assert family.run("solo", *argv).out == own.out
        for scope in ("up", "down", "all"):
            ran = family.run("solo", *argv, "--scope", scope)
            assert ran.code == 0 and ran.out == own.out, (argv, scope, ran.err)
            if "--json" not in argv:
                assert ran.err == own.err, (argv, scope)
    assert set(asked) <= {"solo"}
    assert set(opened) == {"solo"}


# -- AC 30: `--local` is removed (plan Step 12b) ----------------------------------------


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities"])
def test_ac30_local_is_refused_before_anything_is_read(family, monkeypatch, axis):
    from tcw.store.fs import FsTreeStore
    opened = []
    real_init = FsTreeStore.__init__

    def init_(self, *a, **kw):
        opened.append(a)
        real_init(self, *a, **kw)
    monkeypatch.setattr(FsTreeStore, "__init__", init_)
    ran = family.run("desktop", axis, "list", "--local")
    assert ran.code == 2
    assert "--scope own" in ran.err and "drop --local" in ran.err
    assert ran.out == ""
    assert opened == []


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities"])
def test_ac30_help_does_not_name_local(family, axis):
    ran = family.run("desktop", axis, "list", "--help")
    assert ran.code == 0
    assert "--local" not in ran.out
