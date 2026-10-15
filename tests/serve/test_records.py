"""Taxonomy and capability routes and `tcw://` resolution on the one-process
server: today's behavior, kept, with Design 11's error bodies."""

from __future__ import annotations

import pytest

import tcw.cli
from tcw.cli import main
from tcw.serve.records import RESOLVE_MAX_URIS
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore


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
    slugs = {t["slug"] for t in records.get("/api/taxonomy").json}
    assert {"work-item", "admin"} <= slugs


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
    assert answer.json["term"]["relates_to"] == ["admin"]


def test_a_stale_term_edit_is_409(records):
    revision = detail(records, "taxonomy", "work-item")["coreRevision"]
    FsTaxonomyStore.open(records.root).update_term("work-item", description="elsewhere")
    answer = records.patch("/api/taxonomy/work-item", {
        "revision": revision, "fields": {"description": "mine"}})
    assert_error(answer, 409, "stale-revision")


def test_an_unknown_term_is_404(records):
    assert_error(records.get("/api/taxonomy/nonexistent"), 404, "not-found")
    assert_error(records.patch("/api/taxonomy/nonexistent", {"fields": {"name": "x"}}),
                 404, "not-found")


def test_a_duplicate_term_is_refused(records):
    answer = records.post("/api/taxonomy", {"name": "Dup", "slug": "admin"})
    assert_error(answer, 409, "refused")


def test_a_term_needs_a_name(records):
    assert_error(records.post("/api/taxonomy", {}), 400, "usage")


def test_a_feature_with_an_unknown_vocabulary_term_is_refused_and_writes_nothing(records):
    answer = records.post("/api/taxonomy", {"name": "Broken", "slug": "broken",
                                            "kind": "Feature",
                                            "vocabulary": ["no-such-term"]})
    assert answer.status in (400, 404), answer.body
    assert not (records.root / "docs" / "taxonomy" / "broken").exists()


def test_an_encoded_slash_names_a_nested_term(records):
    FsTaxonomyStore.open(records.root).add("Adapter", slug="admin/adapter")
    assert detail(records, "taxonomy", "admin%2Fadapter")["term"]["slug"] == "admin/adapter"
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
    assert answer.status == 201 and answer.json["capability"]["path"] == "web/editing"
    assert {"web", "web/editing"} <= {c["path"] for c in
                                      records.get("/api/capabilities").json}
    assert detail(records, "capabilities", "web%2Fediting")["capability"]["path"] \
        == "web/editing"


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
                               {"fields": {"Status": "Supported"}}), 404, "not-found")


def test_a_capability_needs_a_path(records):
    assert_error(records.post("/api/capabilities", {"name": "No path"}), 400, "usage")


@pytest.mark.parametrize("fields", [{"Status": "InvalidStatus"}, {"BogusField": "x"}])
def test_an_invalid_capability_field_is_a_usage_error(records, fields):
    revision = detail(records, "capabilities", "web")["coreRevision"]
    answer = records.patch("/api/capabilities/web", {"revision": revision,
                                                     "fields": fields})
    assert_error(answer, 400, "usage")


# -- validation notices ------------------------------------------------------------------------


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
    found = resolve(records, ["tcw://C/web", "tcw://C/nope", "tcw://garbage",
                              "tcw://W/2026-01-01-never-created"])
    assert found["tcw://C/web"] == {"ok": True, "axis": "capabilities", "key": "web"}
    assert found["tcw://C/nope"] == {"ok": False, "reason": "unresolved",
                                     "detail": "no capability: nope"}
    assert found["tcw://garbage"]["reason"] == "unresolved"
    assert found["tcw://W/2026-01-01-never-created"]["reason"] == "unresolved"


def test_resolve_caps_the_batch(records):
    found = resolve(records, [f"tcw://C/x{i}" for i in range(RESOLVE_MAX_URIS + 50)])
    assert len(found) == RESOLVE_MAX_URIS


def test_resolve_needs_a_list(records):
    assert_error(records.post("/api/resolve", {"uris": "tcw://C/web"}), 400, "usage")


def test_the_configuration_is_read_again_while_serving(records_root, monkeypatch):
    """`tcw serve` outlives its start-up, so the per-command read of the
    configuration (TCW-72 Design 2.3) ends before serving."""
    from tcw.refs import resolve_tcw_ref
    seen = []

    def fake_serve(root, **_):
        seen.append(resolve_tcw_ref(root, "tcw://W/2026-01-01-x").reason)
        config = root / "tcw-config.yaml"
        config.write_text(config.read_text() + "work:\n  hooks:\n    timeout: -1\n")
        seen.append(resolve_tcw_ref(root, "tcw://W/2026-01-01-x").reason)
        return 0

    monkeypatch.setattr(tcw.cli, "serve", fake_serve)
    monkeypatch.chdir(records_root)
    assert main(["serve", "--no-open"]) == 0
    assert "work.hooks.timeout" not in seen[0]
    assert "work.hooks.timeout" in seen[1], seen
