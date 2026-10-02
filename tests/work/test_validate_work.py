"""`tcw validate`'s 3.0 work checks, called directly (TCW-70 Design 10.1; the
library half of AC 15). Each assertion checks that a finding names its file and
key, never how the line is laid out."""

import pytest

from tcw.store.fs import FsProjectRegistry
from tcw.validate import _shared_work_paths, _work_findings
from tcw.work.config import MIGRATION_GUIDE
from tests.work.projects import commit_all, connect, make_project, write_item

TAGS = {"tags": ["ui"]}


def findings(root):
    found, note = _work_findings(root, FsProjectRegistry.open(root))
    return found, note


def by_severity(found, severity):
    return [f for f in found if f.severity == severity]


def test_a_clean_store_has_no_findings(tmp_path):
    p = make_project(tmp_path, "p", config=TAGS)
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    assert findings(p) == ([], None)


def test_three_warnings_and_no_error(tmp_path):
    p = make_project(tmp_path, "p", config=TAGS)
    write_item(p, "2026-10-01-blocked", {"title": "b", "stage": "request",
                                        "blocked-by": ["2026-10-01-nothing"]})
    ahead = write_item(p, "2026-10-01-ahead", {"title": "c", "stage": "plan"})
    (ahead / "request").mkdir()
    (ahead / "request" / "request.md").write_text("Do it.\n")
    write_item(p, "2026-10-01-tagged", {"title": "d", "stage": "request",
                                       "tags": ["unregistered"]})
    found, _ = findings(p)
    assert by_severity(found, "error") == []
    warnings = by_severity(found, "warning")
    assert len(warnings) == 3
    where = {f.where.split("/")[-2]: f.message for f in warnings}
    assert "blocked-by" in where["2026-10-01-blocked"]
    assert "2026-10-01-nothing" in where["2026-10-01-blocked"]
    assert "stage" in where["2026-10-01-ahead"] and "spec" in where["2026-10-01-ahead"]
    assert "unregistered" in where["2026-10-01-tagged"]
    assert all(f.where.endswith("item.yaml") for f in warnings)


def test_references_into_other_projects(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request",
                                  "blocked-by": ["q/2026-10-01-x",
                                                 "nobody/2026-10-01-y"]})
    import shutil
    shutil.rmtree(q)
    found, _ = findings(p)
    assert by_severity(found, "error") == []
    [unresolved] = by_severity(found, "unresolved")
    assert "q/2026-10-01-x" in unresolved.message
    assert "blocked-by" in unresolved.message
    [missing] = by_severity(found, "warning")
    assert "nobody/2026-10-01-y" in missing.message


def test_a_reference_found_in_another_project_is_fine(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "discarded"})
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request",
                                  "parent": "q/2026-10-01-x"})
    assert findings(p) == ([], None)


def test_an_inbox_folder_names_the_guide(tmp_path):
    p = make_project(tmp_path, "p")
    (p / "docs" / "work" / "inbox").mkdir()
    [error] = by_severity(findings(p)[0], "error")
    assert error.where.endswith("inbox")
    assert MIGRATION_GUIDE in error.message


def test_a_bad_capabilities_file_on_an_unfinished_item_fails(tmp_path):
    p = make_project(tmp_path, "p")
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "implement"})
    for stage in ("request", "spec", "plan"):
        (folder / stage).mkdir()
        (folder / stage / f"{stage}.md").write_text("x")
    (folder / "capabilities.yaml").write_text("added: [x/y]\n")
    [error] = by_severity(findings(p)[0], "error")
    assert error.where.endswith("2026-10-01-a/capabilities.yaml")
    assert "added" in error.message


def test_a_finished_item_is_not_checked_mid_work(tmp_path):
    p = make_project(tmp_path, "p")
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "discarded"})
    (folder / "capabilities.yaml").write_text("added: [x/y]\n")
    assert by_severity(findings(p)[0], "error") == []


def test_one_unreadable_item_does_not_hide_the_rest(tmp_path):
    p = make_project(tmp_path, "p")
    write_item(p, "2026-10-01-bad", "title: [x\n")
    write_item(p, "2026-10-01-blocked", {"title": "b", "stage": "request",
                                        "blocked-by": ["2026-10-01-nothing"]})
    folder = write_item(p, "2026-10-01-caps", {"title": "c", "stage": "request"})
    (folder / "capabilities.yaml").write_text("added: [x/y]\n")
    found, note = findings(p)
    paths = {f.where for f in found}
    assert any(w.endswith("2026-10-01-bad/item.yaml") for w in paths)
    assert any(w.endswith("2026-10-01-blocked/item.yaml") for w in paths)
    assert any(w.endswith("2026-10-01-caps/capabilities.yaml") for w in paths)
    assert len(by_severity(found, "error")) == 2
    assert "2026-10-01-bad/item.yaml" in note


def test_a_config_error_is_one_finding(tmp_path):
    p = make_project(tmp_path, "p", config={"tracker": {}})
    [error] = findings(p)[0]
    assert error.severity == "error" and "work.tracker" in error.message


def test_two_projects_with_one_work_path(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q", config={"path": "../p/docs/work"})
    connect(p, q, "children")
    connect(q, p, "parent")
    [line] = _shared_work_paths(FsProjectRegistry.open(p))
    assert "'p'" in line and "'q'" in line
    assert str((p / "docs" / "work").resolve()) in line


def test_distinct_work_paths_are_fine(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    assert _shared_work_paths(FsProjectRegistry.open(p)) == []
