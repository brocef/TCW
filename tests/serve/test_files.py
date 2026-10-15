"""An item's files through the API: documents, rounds, handoffs and the
declaration file (TCW-77 criteria 6, 7 and 15)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
import yaml

from tcw.errors import Unreachable
from tests.serve.conftest import fs_project
from tests.serve.test_work_read import new, ok


@pytest.fixture
def item(tmp_path, personal_on, serve_project, tcw):
    """A served filesystem project holding one item, and that item's folder."""
    root = fs_project(tmp_path)
    folder = new(tcw, root, "Thing", request="please\n")
    return serve_project(root), folder


def folder_of(served, folder):
    return served.root / "docs" / "work" / folder


def put(served, folder, path, content, revision):
    return served.put(f"/api/work/{folder}/files/{path}",
                      {"content": content, "revision": revision})


def assert_stale(answer):
    assert answer.status == 409, answer.body
    assert answer.json["code"] == "stale-revision"


# -- reading and writing a document ----------------------------------------------------------


def test_read_then_write_a_document(item):
    served, folder = item
    found = ok(served.get(f"/api/work/{folder}/files/request/request.md"))
    assert found["content"] == "please\n"
    saved = ok(put(served, folder, "request/request.md", "better\n", found["revision"]))
    assert saved["revision"] != found["revision"]
    assert (folder_of(served, folder) / "request" / "request.md").read_text() == "better\n"


def test_creating_a_document_makes_its_stage_folder(item):
    served, folder = item
    spec = folder_of(served, folder) / "spec"
    assert not spec.exists()
    ok(put(served, folder, "spec/spec.md", "# Spec\n", None))
    assert (spec / "spec.md").read_text() == "# Spec\n"
    assert_stale(put(served, folder, "spec/spec.md", "# Spec\n", None))


def test_a_stale_write_changes_nothing(item):
    served, folder = item
    target = folder_of(served, folder) / "request" / "request.md"
    answer = put(served, folder, "request/request.md", "mine\n", "0" * 64)
    assert_stale(answer)
    assert target.read_text() == "please\n"


def test_the_write_renames_from_beside_the_target(item, monkeypatch):
    served, folder = item
    renamed = []
    real = os.replace

    def recording(src, dst, *args, **kwargs):
        renamed.append((os.fspath(src), os.fspath(dst)))
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", recording)
    ok(put(served, folder, "spec/spec.md", "x\n", None))
    target = str(folder_of(served, folder) / "spec" / "spec.md")
    assert renamed and all(dst == target and os.path.dirname(src) == os.path.dirname(dst)
                           for src, dst in renamed), renamed


def test_a_write_needs_a_revision_key(item):
    served, folder = item
    answer = served.put(f"/api/work/{folder}/files/spec/spec.md", {"content": "x"})
    assert answer.status == 400


def test_a_reading_of_a_missing_file_is_404(item):
    served, folder = item
    assert served.get(f"/api/work/{folder}/files/spec/spec.md").status == 404


@pytest.mark.parametrize("path", ["item.yaml", "comments/x.md", "spec/notes.md",
                                  "spec/../item.yaml", "..%2Fitem.yaml", "spec",
                                  "completed/completed.md", "spec/round-1.md",
                                  "implement/implement.md", "nope/nope.md"])
def test_paths_the_layout_does_not_name_are_404(item, path):
    served, folder = item
    before = sorted(p.name for p in folder_of(served, folder).iterdir())
    assert served.get(f"/api/work/{folder}/files/{path}").status == 404
    answer = put(served, folder, path, "x", None)
    assert answer.status == 404 and answer.json["code"] == "not-found"
    assert sorted(p.name for p in folder_of(served, folder).iterdir()) == before


def test_a_disabled_stage_has_no_files(tmp_path, personal_on, serve_project, tcw):
    root = fs_project(tmp_path, config={"stages": {"spec": {"enabled": False}}})
    folder = new(tcw, root, "Thing")
    served = serve_project(root)
    assert put(served, folder, "spec/spec.md", "x", None).status == 404
    assert not (folder_of(served, folder) / "spec").exists()


# -- new rounds and handoffs ---------------------------------------------------------------------


def test_a_new_review_round_judges_the_latest_implementation(item, tcw):
    served, folder = item
    for n in (1, 2):
        ok(put(served, folder, f"implement/round-{n}.md", "work\n", None))
    for n in (1, 2):
        ok(put(served, folder, f"review/round-{n}.md",
               f"---\njudges: {n}\nverdict: rejected\n---\n", None))
    answer = ok(served.post(f"/api/work/{folder}/files", {"stage": "review",
                                                          "kind": "round"}))
    assert answer["path"] == "review/round-3.md"
    path = tcw(["work", "path", folder, "review", "--next"], served.root).out.strip()
    assert path == str(folder_of(served, folder) / "review" / "round-3.md")
    assert answer["template"] == "---\njudges: 2\nverdict:\n---\n"


def test_an_implement_round_starts_empty(item):
    served, folder = item
    answer = ok(served.post(f"/api/work/{folder}/files", {"stage": "implement",
                                                          "kind": "round"}))
    assert answer == {"path": "implement/round-1.md", "template": ""}


def test_a_handoff_is_the_clis_handoff_path(item, tcw, monkeypatch):
    served, folder = item
    import tcw.work.layout as layout

    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 14, 12, 30, 5, tzinfo=timezone.utc)

    monkeypatch.setattr(layout, "datetime", Fixed)
    answer = ok(served.post(f"/api/work/{folder}/files", {"stage": "implement",
                                                          "kind": "handoff"}))
    path = tcw(["work", "path", folder, "implement", "--handoff"], served.root).out.strip()
    assert answer == {"path": "implement/handoff-20261014T123005Z.md", "template": ""}
    assert path == str(folder_of(served, folder) / answer["path"])


@pytest.mark.parametrize(("body", "status"), [
    ({"stage": "completed", "kind": "document"}, 400),
    ({"stage": "spec", "kind": "round"}, 400),
    ({"stage": "implement", "kind": "document"}, 400),
    ({"stage": "spec", "kind": "sidecar"}, 400),
    ({"stage": "nonsense", "kind": "document"}, 400),
])
def test_files_a_stage_cannot_have_are_refused(item, body, status):
    served, folder = item
    assert served.post(f"/api/work/{folder}/files", body).status == status


# -- the declaration file -------------------------------------------------------------------------


@pytest.fixture
def ledger(tmp_path, personal_on, serve_project, tcw):
    """A project keeping every axis, with capabilities `web` and `cli` and the
    term `widget`; one item."""
    from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
    root = fs_project(tmp_path)
    init(["taxonomy", "capabilities"], root, "p")
    FsCapabilitiesStore.open(root).add("web", "Web", status="Supported")
    FsCapabilitiesStore.open(root).add("cli", "CLI", status="Supported")
    FsTaxonomyStore.open(root).add("Widget", slug="widget")
    folder = new(tcw, root, "Thing")
    return serve_project(root), folder


SIX = {"capabilities": {"new": ["web/new-thing"], "changed": ["web"], "removed": ["cli"]},
       "taxonomy": {"new": ["gadget"], "changed": ["widget"], "removed": ["widget"]}}


def test_the_declaration_round_trips(ledger):
    served, folder = ledger
    empty = ok(served.get(f"/api/work/{folder}/declaration"))
    assert empty["present"] is False and empty["problem"] is None
    ok(served.put(f"/api/work/{folder}/declaration", {**SIX, "revision": None}))
    found = ok(served.get(f"/api/work/{folder}/declaration"))
    assert {k: found[k] for k in SIX} == SIX
    written = (folder_of(served, folder) / "capabilities.yaml").read_text()
    assert list(yaml.safe_load(written)) == ["new", "changed", "removed", "taxonomy"]


def test_the_declaration_is_written_without_empty_lists(ledger):
    served, folder = ledger
    ok(served.put(f"/api/work/{folder}/declaration", {
        "capabilities": {"new": [], "changed": ["web"]}, "taxonomy": {},
        "revision": None}))
    written = (folder_of(served, folder) / "capabilities.yaml").read_text()
    assert yaml.safe_load(written) == {"changed": ["web"]}


def test_a_changed_entry_must_exist_and_a_new_one_need_not(ledger):
    served, folder = ledger
    refused = served.put(f"/api/work/{folder}/declaration", {
        "capabilities": {"changed": ["no/such/path"]}, "revision": None})
    assert refused.status == 400 and "no/such/path" in refused.json["error"]
    assert not (folder_of(served, folder) / "capabilities.yaml").exists()
    ok(served.put(f"/api/work/{folder}/declaration", {
        "capabilities": {"new": ["no/such/path"]}, "revision": None}))


def test_an_entry_already_in_the_file_is_not_checked_again(ledger):
    served, folder = ledger
    path = folder_of(served, folder) / "capabilities.yaml"
    path.write_text("changed: [gone/away]\n")
    revision = ok(served.get(f"/api/work/{folder}/declaration"))["revision"]
    ok(served.put(f"/api/work/{folder}/declaration", {
        "capabilities": {"changed": ["gone/away", "web"]}, "revision": revision}))


def test_a_taxonomy_entry_must_exist_to_be_changed(ledger):
    served, folder = ledger
    refused = served.put(f"/api/work/{folder}/declaration", {
        "taxonomy": {"removed": ["nothing"]}, "revision": None})
    assert refused.status == 400 and "nothing" in refused.json["error"]


def test_a_file_the_parser_rejects_comes_back_as_text(ledger):
    served, folder = ledger
    path = folder_of(served, folder) / "capabilities.yaml"
    path.write_text("added: [x]\n")
    found = ok(served.get(f"/api/work/{folder}/declaration"))
    assert "unknown key(s) added" in found["problem"]
    assert found["content"] == "added: [x]\n"
    fixed = ok(put(served, folder, "capabilities.yaml", "new: [x]\n", found["revision"]))
    assert fixed["revision"]


def test_a_stale_declaration_save_is_409(ledger):
    served, folder = ledger
    (folder_of(served, folder) / "capabilities.yaml").write_text("new: [a]\n")
    assert_stale(served.put(f"/api/work/{folder}/declaration", {
        "capabilities": {"new": ["b"]}, "revision": None}))


# -- validation notices -----------------------------------------------------------------------------


def test_a_dangling_link_is_a_warning_and_the_file_is_saved(ledger):
    served, folder = ledger
    answer = ok(put(served, folder, "spec/spec.md",
                    "See [the term](tcw://T/no-such-term).\n", None))
    assert any("tcw://T/no-such-term" in w["message"] for w in answer["warnings"]), answer
    assert set(answer["warnings"][0]) == {"severity", "where", "message"}
    assert "tcw://T/no-such-term" in (folder_of(served, folder) / "spec" / "spec.md").read_text()


def test_a_round_without_a_verdict_is_warned_invalid(item):
    served, folder = item
    answer = ok(put(served, folder, "review/round-1.md", "---\njudges: 0\nverdict:\n---\n",
                    None))
    assert any("invalid" in w["message"] for w in answer["warnings"]), answer


def test_a_clean_save_has_no_warnings(item):
    served, folder = item
    assert "warnings" not in ok(put(served, folder, "spec/spec.md", "# Spec\n", None))


# -- Jira mode ---------------------------------------------------------------------------------------


def test_a_stage_the_backend_keeps_has_no_files(jira):
    served = jira.served
    for path in ("qa/round-1.md", "request/request.md"):
        answer = served.put(f"/api/work/TCW-1-first/files/{path}",
                            {"content": "x", "revision": None})
        assert answer.status == 404
        assert served.get(f"/api/work/TCW-1-first/files/{path}").status == 404
    work = jira.root / "docs" / "work" / "TCW-1-first"
    assert not (work / "qa").exists() and not (work / "request").exists()


def test_files_stay_editable_while_the_backend_cannot_answer(jira):
    for name in ("list", "read", "read_request", "read_comments"):
        jira.backend.fail[name] = Unreachable("Jira is unreachable")
    served = jira.served
    answer = ok(served.put("/api/work/TCW-1-first/files/spec/spec.md",
                           {"content": "# Spec\n", "revision": None}))
    assert "warnings" not in answer, answer
    found = ok(served.get("/api/work/TCW-1-first/files/spec/spec.md"))
    assert found["content"] == "# Spec\n"
