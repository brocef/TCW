"""`tcw://` work references on the 3.0 backend (TCW-70 Design 12.1; the
library half of AC 17)."""

import shutil

import pytest

from tcw.refs import _resolve_work
from tests.work.projects import connect, make_project, write_item


@pytest.mark.parametrize("stage", ["request", "completed", "discarded"])
def test_an_item_at_any_stage_resolves(tmp_path, stage):
    p = make_project(tmp_path, "p")
    write_item(p, "2026-10-01-a", {"title": "a", "stage": stage})
    result = _resolve_work(p, None, "2026-10-01-a")
    assert result.ok and result.key == "2026-10-01-a" and result.project == ""


def test_a_missing_item_fails(tmp_path):
    p = make_project(tmp_path, "p")
    result = _resolve_work(p, None, "2026-10-01-nothing")
    assert not result.ok and "2026-10-01-nothing" in result.reason


def test_another_project_resolves_through_it(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "spec"})
    for namespace, ref in (("q", "2026-10-01-x"), (None, "q/2026-10-01-x")):
        result = _resolve_work(p, namespace, ref)
        assert result.ok and result.key == "q/2026-10-01-x" and result.project == "q"
    assert not _resolve_work(p, "q", "2026-10-01-nothing").ok


def test_an_absent_project_is_unresolved_and_an_unknown_one_missing(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    shutil.rmtree(q)
    absent = _resolve_work(p, "q", "2026-10-01-x")
    assert not absent.ok and absent.reason.startswith("unresolved")
    unknown = _resolve_work(p, "nobody", "2026-10-01-x")
    assert not unknown.ok and not unknown.reason.startswith("unresolved")
