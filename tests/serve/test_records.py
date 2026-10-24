"""Taxonomy and capability routes and `tcw://` resolution on the one-process
server: today's behavior, kept, with Design 11's error bodies."""

from __future__ import annotations

import pytest

import tcw.cli
from tcw.cli import main
from tcw.serve.records import RESOLVE_MAX_URIS
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
from tests.projectfiles import config_file, write_config_file


def detail(served, axis: str, ref: str) -> dict:
    answer = served.get(f"/api/{axis}/{ref}")
    assert answer.status == 200, answer.body
    return answer.json


def assert_error(answer, status: int, code: str):
    assert answer.status == status, answer.body
    assert answer.json["code"] == code and answer.json["error"]
    assert "Traceback" not in answer.text


# -- taxonomy ------------------------------------------------------------------------------


def test_list_terms(records):
    full_ids = {t["full-id"] for t in records.get("/api/taxonomy").json}
    assert {"r.taxonomy/work-item", "r.taxonomy/admin"} <= full_ids


def test_create_a_vocabulary_term(records):
    answer = records.post("/api/taxonomy", {"name": "Security"})
    assert answer.status == 201
    assert answer.json["term"]["kind"] == "Vocabulary" and answer.json["coreRevision"]


def test_create_a_feature(records):
    answer = records.post("/api/taxonomy", {"name": "Local web app", "kind": "Feature",
                                            "vocabulary": ["work-item"]})
    assert answer.status == 201 and answer.json["term"]["kind"] == "Feature"


def test_update_a_term(records):
    revision = detail(records, "taxonomy", "work-item")["coreRevision"]
    answer = records.patch("/api/taxonomy/work-item", {
        "revision": revision, "fields": {"name": "Renamed", "relatesTo": ["admin"]}})
    assert answer.status == 200
    assert answer.json["term"]["name"] == "Renamed"
    assert answer.json["term"]["relates_to"] == ["r.taxonomy/admin"]   # stored in full


def test_a_stale_term_edit_is_409(records):
    revision = detail(records, "taxonomy", "work-item")["coreRevision"]
    FsTaxonomyStore.open(records.root).update_term("work-item", description="elsewhere")
    answer = records.patch("/api/taxonomy/work-item", {
        "revision": revision, "fields": {"description": "mine"}})
    assert_error(answer, 409, "stale-revision")


@pytest.mark.parametrize("ref", ["taxonomy/work-item", "capabilities/web"])
def test_a_save_without_a_revision_is_400(records, ref):
    """Pre-freeze clean-up, V1: no save skips the stale check."""
    answer = records.patch(f"/api/{ref}", {"body": "Changed.\n"})
    assert_error(answer, 400, "usage")
    assert answer.json["error"] == "revision is required"


@pytest.mark.parametrize("ref", ["taxonomy/work-item", "capabilities/web"])
def test_a_save_with_a_stale_revision_is_409(records, ref):
    answer = records.patch(f"/api/{ref}", {"body": "Changed.\n", "revision": "stale"})
    assert_error(answer, 409, "stale-revision")


def test_an_unknown_term_is_404(records):
    assert_error(records.get("/api/taxonomy/nonexistent"), 404, "not-found")
    assert_error(records.patch("/api/taxonomy/nonexistent", {"fields": {"name": "x"},
                                                      "revision": "r"}),
                 404, "not-found")


def test_a_duplicate_term_is_refused(records):
    answer = records.post("/api/taxonomy", {"name": "Dup", "slug": "admin"})
    assert_error(answer, 409, "refused")


@pytest.mark.parametrize("slug", ["A B", "a/b"])
def test_a_slug_that_is_not_one_is_400_without_naming_a_flag(records, slug):
    """Pre-freeze clean-up, C2: the store's message, which names no
    command-line flag."""
    answer = records.post("/api/taxonomy", {"name": "X", "slug": slug})
    assert_error(answer, 400, "usage")
    assert "is not a slug" in answer.json["error"]
    assert "--slug" not in answer.json["error"]
    assert not (records.root / "docs" / "taxonomy" / "a").exists()


def test_a_term_needs_a_name(records):
    assert_error(records.post("/api/taxonomy", {}), 400, "usage")


def test_a_feature_with_an_unknown_vocabulary_term_is_refused_and_writes_nothing(records):
    answer = records.post("/api/taxonomy", {"name": "Broken", "slug": "broken",
                                            "kind": "Feature",
                                            "vocabulary": ["no-such-term"]})
    assert answer.status in (400, 404), answer.body
    assert not (records.root / "docs" / "taxonomy" / "broken").exists()


def test_an_encoded_slash_names_a_nested_term(records):
    FsTaxonomyStore.open(records.root).add("Adapter", slug="adapter", parent="admin")
    assert detail(records, "taxonomy", "admin%2Fadapter")["term"]["full-id"] == \
        "r.taxonomy/admin/adapter"
    revision = detail(records, "taxonomy", "admin%2Fadapter")["coreRevision"]
    answer = records.patch("/api/taxonomy/admin%2Fadapter",
                           {"revision": revision, "fields": {"description": "nested"}})
    assert answer.status == 200 and answer.json["term"]["description"] == "nested"


# -- capabilities ---------------------------------------------------------------------------


def test_create_a_capability(records):
    answer = records.post("/api/capabilities", {"path": "auth", "name": "User login",
                                                "status": "Missing"})
    assert answer.status == 201
    assert answer.json["capability"]["status"] == "Missing"


def test_create_a_nested_capability_without_a_name(records):
    answer = records.post("/api/capabilities", {"path": "web/editing"})
    assert answer.status == 201
    assert answer.json["capability"]["full-id"] == "r.capabilities/web/editing"
    assert {"r.capabilities/web", "r.capabilities/web/editing"} <= {
        c["full-id"] for c in records.get("/api/capabilities").json}
    assert detail(records, "capabilities", "web%2Fediting")["capability"]["full-id"] \
        == "r.capabilities/web/editing"


def test_update_a_capability(records):
    revision = detail(records, "capabilities", "web")["coreRevision"]
    answer = records.patch("/api/capabilities/web", {
        "revision": revision, "fields": {"Status": "Supported"}, "body": "New body."})
    assert answer.status == 200
    assert answer.json["capability"]["fields"]["Status"] == "Supported"


def test_a_stale_capability_edit_is_409(records):
    revision = detail(records, "capabilities", "web")["coreRevision"]
    FsCapabilitiesStore.open(records.root).set("web", {"Status": "Supported"})
    answer = records.patch("/api/capabilities/web", {
        "revision": revision, "fields": {"Priority": "P1"}})
    assert_error(answer, 409, "stale-revision")


def test_an_unknown_capability_is_404(records):
    assert_error(records.patch("/api/capabilities/nonexistent",
                               {"fields": {"Status": "Supported"}, "revision": "r"}),
                 404, "not-found")


def test_a_capability_needs_a_path(records):
    assert_error(records.post("/api/capabilities", {"name": "No path"}), 400, "usage")


@pytest.mark.parametrize("fields", [{"Status": "InvalidStatus"}, {"BogusField": "x"}])
def test_an_invalid_capability_field_is_a_usage_error(records, fields):
    revision = detail(records, "capabilities", "web")["coreRevision"]
    answer = records.patch("/api/capabilities/web", {"revision": revision,
                                                     "fields": fields})
    assert_error(answer, 400, "usage")


# -- validation notices ------------------------------------------------------------------------


def test_text_that_is_not_valid_utf8_is_refused_and_writes_nothing(records):
    before = detail(records, "capabilities", "web")
    answer = records.patch("/api/capabilities/web", {
        "revision": before["coreRevision"], "body": "broken \ud800 text"})
    assert_error(answer, 400, "usage")
    assert detail(records, "capabilities", "web") == before
    assert_error(records.post("/api/taxonomy", {"name": "Bad \ud800"}), 400, "usage")


def test_a_clean_save_has_no_warnings(records):
    FsCapabilitiesStore.open(records.root).add("unrelated", status="Partial")
    answer = records.post("/api/taxonomy", {"name": "Clean", "slug": "clean"})
    assert answer.status == 201 and "warnings" not in answer.json


def test_a_saved_object_problem_is_a_finding(records):
    answer = records.post("/api/capabilities", {"path": "broken-cap", "name": "Broken",
                                                "status": "Partial"})
    assert answer.status == 201
    warnings = answer.json["warnings"]
    assert all(set(w) == {"severity", "where", "message"} for w in warnings)
    assert any("Partial requires Gaps" in w["message"] for w in warnings)


def test_a_failed_check_never_fails_the_save(records, monkeypatch):
    import tcw.serve.records as module

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "validate", boom)
    answer = records.post("/api/taxonomy", {"name": "Committed"})
    assert answer.status == 201 and answer.json["term"]["name"] == "Committed"
    assert answer.json["warnings"][0]["message"] == "validation could not complete: boom"


def test_every_write_route_works_outside_a_repository(records_root, serve_project):
    import shutil
    shutil.rmtree(records_root / ".git")
    served = serve_project(records_root)
    assert served.post("/api/taxonomy", {"name": "Gadget", "slug": "gadget"}).status == 201
    assert served.post("/api/capabilities", {"path": "a/b", "name": "Thing"}).status == 201
    assert (records_root / "docs" / "taxonomy" / "gadget" / "meta.yaml").is_file()


def test_a_project_without_a_taxonomy_lists_none(tmp_path, personal_on, serve_project):
    from tests.serve.conftest import fs_project
    served = serve_project(fs_project(tmp_path))
    assert served.get("/api/taxonomy").json == []


# -- links ---------------------------------------------------------------------------------------


def resolve(served, uris):
    answer = served.post("/api/resolve", {"uris": uris})
    assert answer.status == 200, answer.body
    return answer.json


def test_resolve_local_and_broken_links(records):
    found = resolve(records, ["tcw://r.capabilities/web", "tcw://r.capabilities/nope",
                              "tcw://garbage", "tcw://r.work/2026-01-01-never-created",
                              "tcw://C/web", "tcw://r.path/docs"])
    assert found["tcw://r.capabilities/web"] == {"ok": True, "axis": "capabilities",
                                                "key": "web"}
    assert found["tcw://r.capabilities/nope"] == {
        "ok": False, "reason": "unresolved", "detail": "no capability r.capabilities/nope"}
    assert found["tcw://garbage"]["reason"] == "unresolved"
    assert found["tcw://r.work/2026-01-01-never-created"]["reason"] == "unresolved"
    assert "TCW 3.x reference" in found["tcw://C/web"]["detail"]
    assert found["tcw://r.path/docs"] == {
        "ok": False, "reason": "unresolved",
        "detail": "tcw://r.path/docs names a folder, not an object"}


def test_resolve_caps_the_batch(records):
    found = resolve(records, [f"tcw://r.capabilities/x{i}"
                              for i in range(RESOLVE_MAX_URIS + 50)])
    assert len(found) == RESOLVE_MAX_URIS


def test_resolve_needs_a_list(records):
    assert_error(records.post("/api/resolve", {"uris": "tcw://r.capabilities/web"}),
                 400, "usage")


def test_the_configuration_is_read_again_while_serving(records_root, monkeypatch):
    """`tcw serve` outlives its start-up, so the per-command read of the
    configuration (TCW-72 Design 2.3) ends before serving."""
    from tcw.refs import resolve_address
    seen = []

    def fake_serve(root, **_):
        seen.append(resolve_address(root, "tcw://r.work/2026-01-01-x").reason)
        config = config_file(root)
        write_config_file(config, config.read_text() + "work:\n  hooks:\n    timeout: -1\n")
        seen.append(resolve_address(root, "tcw://r.work/2026-01-01-x").reason)
        return 0

    monkeypatch.setattr(tcw.cli, "serve", fake_serve)
    monkeypatch.chdir(records_root)
    assert main(["serve", "--no-open"]) == 0
    assert "work.hooks.timeout" not in seen[0]
    assert "work.hooks.timeout" in seen[1], seen


# -- refused values (Design 9's table, the server half of criterion 12) ------------------------
#
# One case per field the table refuses. Where the store already refuses, its
# message is the answer; the viewer adds only what the store accepts.


@pytest.fixture
def refusing(records_root, serve_project):
    """The records project with a Feature, a role and a condition."""
    FsTaxonomyStore.open(records_root).add("Search", slug="search", kind="Feature",
                                           vocabulary=["work-item"])
    FsCapabilitiesStore.open(records_root).add("roles/admin", "Admin", status="Supported")
    FsCapabilitiesStore.open(records_root).add("conditions/offline", "Offline",
                                               status="Supported")
    return serve_project(records_root)


def term_patch(served, ref, fields):
    revision = detail(served, "taxonomy", ref)["coreRevision"]
    return served.patch(f"/api/taxonomy/{ref}", {"fields": fields, "revision": revision})


def capability_patch(served, ref, fields):
    revision = detail(served, "capabilities", ref)["coreRevision"]
    return served.patch(f"/api/capabilities/{ref}", {"fields": fields,
                                                      "revision": revision})


@pytest.mark.parametrize(("name", "body"), [
    ("parent", {"name": "Child", "slug": "child", "parent": "no-such-term"}),
    ("vocabulary", {"name": "F", "slug": "f", "kind": "Feature",
                    "vocabulary": ["no-such-term"]}),
    ("vocabulary", {"name": "F", "slug": "f", "kind": "Feature",
                    "vocabulary": ["search"]}),
    ("kind", {"name": "K", "slug": "k", "kind": "Gadget"}),
])
def test_a_refused_term_value_creates_nothing(refusing, name, body):
    answer = refusing.post("/api/taxonomy", body)
    assert_error(answer, 400, "usage")
    assert not (refusing.root / "docs" / "taxonomy" / body["slug"]).exists()


@pytest.mark.parametrize("fields", [
    {"relatesTo": ["no-such-term"]},
    {"kind": "Feature", "vocabulary": ["search"]},
])
def test_a_refused_term_edit_is_400(refusing, fields):
    assert_error(term_patch(refusing, "admin", fields), 400, "usage")


@pytest.mark.parametrize("fields", [
    {"Feature": "work-item"}, {"Feature": "no-such-term"},
    {"Subject": ["search"]}, {"Subject": ["no-such-term"]},
    {"Roles": ["admin"]}, {"Roles": ["roles/nobody"]},
    {"When": ["offline"]}, {"When": ["conditions/never"]},
    {"Blocked by": "no/such/capability"}, {"Superseded by": "no/such/capability"},
    {"Status": "Sideways"},
])
def test_a_refused_capability_value_is_400_and_writes_nothing(refusing, fields):
    meta = refusing.root / "docs" / "capabilities" / "web" / "meta.yaml"
    before = meta.read_text()
    assert_error(capability_patch(refusing, "web", fields), 400, "usage")
    assert meta.read_text() == before
    created = refusing.post("/api/capabilities", {"path": "fresh", "name": "Fresh",
                                                  "fields": fields})
    assert_error(created, 400, "usage")
    assert not (refusing.root / "docs" / "capabilities" / "fresh").exists()


def test_negation_is_accepted_on_roles_and_when(refusing):
    answer = capability_patch(refusing, "web", {"Roles": ["!roles/admin"],
                                                "When": ["!conditions/offline"]})
    assert answer.status == 200, answer.body
    fields = answer.json["capability"]["fields"]
    assert (fields["Roles"], fields["When"]) == (["!r.capabilities/roles/admin"],
                                                 ["!r.capabilities/conditions/offline"])


def test_accepted_reference_values(refusing):
    answer = capability_patch(refusing, "web", {
        "Feature": "search", "Subject": ["work-item"], "Blocked by": "roles/admin"})
    assert answer.status == 200, answer.body


# -- inherited entries and other projects (criterion 13) -----------------------------------------


@pytest.fixture
def inheriting(tmp_path, serve_project):
    """`child` extends `base`'s taxonomy and capabilities, so `base` is its
    parent passing both; `base` names nothing."""
    from tcw.store.fs import init
    from tests.work.projects import connect, git
    roots = {}
    for name in ("base", "child"):
        root = tmp_path / name
        root.mkdir()
        git(root, "init", "-q")
        init(["taxonomy", "capabilities", "work"], root, name)
        roots[name] = root
    connect(roots["child"], roots["base"], "parent")
    FsTaxonomyStore.open(roots["base"]).add("Shared", slug="shared")
    FsCapabilitiesStore.open(roots["base"]).add("shared-cap", "Shared", status="Supported")
    FsTaxonomyStore.open(roots["child"]).extends_add("base")
    FsCapabilitiesStore.open(roots["child"]).extends_add("base")
    return serve_project(roots["child"])


def test_an_inherited_capability_is_listed_with_its_owner_and_read_only(inheriting):
    listed = {c["full-id"]: c for c in inheriting.get("/api/capabilities").json}
    assert listed["base.capabilities/shared-cap"]["owner"] == "base"
    meta = inheriting.root.parent / "base" / "docs" / "capabilities" / "shared-cap" / \
        "meta.yaml"
    before = meta.read_text()
    answer = inheriting.patch("/api/capabilities/shared-cap",
                              {"fields": {"Status": "Partial", "Gaps": "x"},
                               "revision": "r"})
    assert_error(answer, 403, "read-only")
    assert meta.read_text() == before
    assert not (inheriting.root / "docs" / "capabilities" / "shared-cap").exists()


def test_an_inherited_term_is_read_only(inheriting):
    listed = {t["full-id"]: t for t in inheriting.get("/api/taxonomy").json}
    assert listed["base.taxonomy/shared"]["owner"] == "base"
    answer = inheriting.patch("/api/taxonomy/shared", {"fields": {"name": "Mine"},
                                                       "revision": "r"})
    assert_error(answer, 403, "read-only")


def test_an_inherited_capability_can_be_named_in_a_reference(inheriting):
    from tcw.store.fs import FsCapabilitiesStore
    FsCapabilitiesStore.open(inheriting.root).add("local", "Local", status="Missing")
    answer = capability_patch(inheriting, "local", {"Blocked by": "shared-cap"})
    assert answer.status == 200, answer.body


def test_a_link_to_another_projects_item_is_other_project(tmp_path, personal_on,
                                                         serve_project, tcw):
    from tests.serve.conftest import fs_project
    from tests.serve.test_work_read import new
    from tests.work.projects import commit_all, connect, make_project
    root = fs_project(tmp_path)
    other = make_project(tmp_path, "q")
    connect(root, other, "children")
    connect(other, root, "parent")
    folder = new(tcw, other, "Theirs")
    commit_all(other)
    found = resolve(serve_project(root), [f"tcw://q.work/{folder}"])
    assert found[f"tcw://q.work/{folder}"] == {"ok": False, "reason": "other-project",
                                               "project": "q"}


# -- references through an encoded slash (2.x's coverage, kept) ---------------------------------


def test_an_inherited_term_reads_by_an_encoded_slash(inheriting):
    found = detail(inheriting, "taxonomy", "base.taxonomy%2Fshared")
    assert (found["term"]["full-id"], found["term"]["owner"]) == \
        ("base.taxonomy/shared", "base")


def test_an_inherited_capability_reads_by_an_encoded_slash(inheriting):
    found = detail(inheriting, "capabilities", "base.capabilities%2Fshared-cap")
    assert found["capability"]["owner"] == "base"


def test_a_link_into_an_inherited_store_resolves(inheriting):
    found = resolve(inheriting, ["tcw://base.capabilities/shared-cap"])
    assert found["tcw://base.capabilities/shared-cap"] == {
        "ok": True, "axis": "capabilities", "key": "base.capabilities/shared-cap"}


def test_a_nested_capability_is_edited_by_an_encoded_slash(records):
    FsCapabilitiesStore.open(records.root).add("web/editing", "Editing", status="Missing")
    answer = capability_patch(records, "web%2Fediting", {"Status": "Partial", "Gaps": "x"})
    assert answer.status == 200, answer.body
    assert answer.json["capability"]["full-id"] == "r.capabilities/web/editing"
    assert answer.json["capability"]["status"] == "Partial"


# -- the commands a refusal names exist ----------------------------------------------------------


def _named_commands(message: str) -> list[list[str]]:
    import re
    import shlex
    return [shlex.split(found)[1:] for found in re.findall(r"`(tcw [^`]+)`", message)]


def test_an_inherited_capabilitys_refusal_names_a_command_that_overrides_it(
        inheriting, tcw):
    """The 403 names `tcw capabilities set`; the real parser takes it, and
    run as named it makes a local override, leaving the inherited record."""
    from tcw.cli import build_parser
    answer = inheriting.patch("/api/capabilities/shared-cap", {"fields": {"Gaps": "x"},
                                                                 "revision": "r"})
    assert_error(answer, 403, "read-only")
    named = _named_commands(answer.json["error"])
    assert named and named[0][:2] == ["capabilities", "set"], answer.json["error"]
    for argv in named:
        build_parser().parse_args(argv)
    base_meta = inheriting.root.parent / "base" / "docs" / "capabilities" / "shared-cap" / \
        "meta.yaml"
    before = base_meta.read_text()
    argv = [part.replace("<name>=<value>", "Status=Partial") for part in named[0]]
    ran = tcw(argv, inheriting.root)
    assert ran.code == 0, ran.err
    assert base_meta.read_text() == before
    shown = FsCapabilitiesStore.open(inheriting.root).get_view("shared-cap")
    assert shown.status == "Partial"


def test_an_inherited_terms_refusal_names_no_command_the_cli_lacks(inheriting):
    from tcw.cli import build_parser
    answer = inheriting.patch("/api/taxonomy/shared", {"fields": {"name": "Mine"},
                                                       "revision": "r"})
    assert_error(answer, 403, "read-only")
    assert "override" not in answer.json["error"]
    for argv in _named_commands(answer.json["error"]):
        build_parser().parse_args(argv)
