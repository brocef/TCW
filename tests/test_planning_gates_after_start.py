"""An item started before it was planned can still pass its planning gates,
and a stage refused for an item's status says how to go on (spec:
2026-09-29-let-a-started-item-still-pass-its-planning-gates-or-stop-start-from-letting-it-past-them)."""

import pytest

from tcw.store.base import STAGE_STATUSES, start_next_stage
from tcw.store.fs import FsWorkStore

from test_transition_hints import _item, _next_lines, _node, _tcw

def _started(root, *artifacts):
    slug = _item(root, *artifacts)
    out = _tcw(root, "start", slug)
    assert out.returncode == 0, out.stderr
    return slug, out


# ── 1: request is legal on an active item ────────────────────────────────────

def test_the_request_gate_passes_on_an_active_item(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root)
    out = _tcw(root, "stage", "gate", "request", slug)
    assert out.returncode == 0, out.stderr
    assert "not legal" not in out.stderr, out.stderr


# ── 2, 3: what start says ────────────────────────────────────────────────────

def test_start_without_a_request_warns_of_all_three_and_points_at_request(tmp_path):
    root = _node(tmp_path)
    slug, out = _started(root)
    warning = next(l for l in out.stderr.splitlines() if "warning" in l)
    for name in ("initial-request.md", "spec.md", "plan.md"):
        assert name in warning, warning
    assert f"tcw work stage gate request {slug}" in warning, warning
    assert f"tcw work stage gate request {slug}" in _next_lines(out.stderr)[0]


def test_start_with_a_request_but_no_spec_is_as_before(tmp_path):
    root = _node(tmp_path)
    slug, out = _started(root, "initial-request")
    warning = next(l for l in out.stderr.splitlines() if "warning" in l)
    assert "spec.md" in warning and "plan.md" in warning, warning
    assert "initial-request" not in warning, warning
    assert f"tcw work stage gate spec {slug}" in _next_lines(out.stderr)[0]


@pytest.mark.parametrize("artifacts, stage", [
    (("spec",), "plan"),
    (("spec", "plan"), "implement"),
    (("spec", "plan", "outcome"), "verify"),
])
def test_a_specified_item_is_never_sent_back_for_its_request(artifacts, stage):
    """A spec supersedes the request's job; work written up after it started
    should not be told to go back and write what was asked."""
    assert start_next_stage(set(artifacts)) == stage


# ── 4, 5: a refused stage says how to go on ──────────────────────────────────

def test_a_planning_stage_on_a_reviewed_item_names_rework_and_prompt(tmp_path):
    root = _node(tmp_path)
    slug = _item(root, "initial-request", "spec", "plan", "outcome")
    assert _tcw(root, "start", slug).returncode == 0
    assert _tcw(root, "submit", slug).returncode == 0
    out = _tcw(root, "stage", "gate", "spec", slug)
    assert out.returncode == 1
    assert f"'spec' is not legal for an item in 'review'" in out.stderr   # kept
    assert f"tcw work rework {slug}" in out.stderr, out.stderr
    assert f"tcw work stage prompt spec {slug}" in out.stderr, out.stderr


def test_implement_on_a_backlog_item_names_start(tmp_path):
    root = _node(tmp_path)
    slug = _item(root, "initial-request", "spec", "plan")
    out = _tcw(root, "stage", "gate", "implement", slug)
    assert out.returncode == 1
    assert f"tcw work start {slug}" in out.stderr, out.stderr


def test_a_resolved_item_is_told_nothing_runs_on_it(tmp_path):
    root = _node(tmp_path)
    slug = _item(root)
    FsWorkStore.open(root).complete(slug, "wontfix", [])
    out = _tcw(root, "stage", "gate", "spec", slug)
    assert out.returncode == 1
    assert "tcw work rework" not in out.stderr and "tcw work start" not in out.stderr
    assert "no stage runs on it" in out.stderr, out.stderr


# ── 6: the model says so ─────────────────────────────────────────────────────

def test_request_is_legal_in_backlog_and_active():
    assert STAGE_STATUSES["request"] == ("backlog", "active")


# ── review follow-ups ────────────────────────────────────────────────────────

def test_start_with_a_spec_but_no_request_does_not_warn_of_the_request(tmp_path):
    root = _node(tmp_path)
    slug, out = _started(root, "spec")
    warning = next(l for l in out.stderr.splitlines() if "warning" in l)
    assert "plan.md" in warning and "initial-request" not in warning, warning


def test_request_on_a_reviewed_item_says_to_write_it_directly(tmp_path):
    root = _node(tmp_path)
    slug = _item(root, "spec", "plan", "outcome")
    assert _tcw(root, "start", slug).returncode == 0
    assert _tcw(root, "submit", slug).returncode == 0
    out = _tcw(root, "stage", "gate", "request", slug)
    assert out.returncode == 1
    assert "write initial-request.md directly" in out.stderr, out.stderr
    assert "tcw work rework" not in out.stderr, out.stderr


def test_rework_advice_on_accepted_work_names_the_file_in_the_way(tmp_path):
    root = _node(tmp_path)
    slug = _item(root, "initial-request", "spec", "plan", "outcome")
    assert _tcw(root, "start", slug).returncode == 0
    assert _tcw(root, "submit", slug).returncode == 0
    FsWorkStore.open(root).write_artifact(slug, "refined-outcome", "# accepted\n")
    out = _tcw(root, "stage", "gate", "spec", slug)
    assert "after deleting refined-outcome.md" in out.stderr, out.stderr


def test_postmortem_on_an_active_item_names_submit(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root, "initial-request", "spec", "plan")
    out = _tcw(root, "stage", "gate", "postmortem", slug)
    assert out.returncode == 1
    assert f"tcw work submit {slug}" in out.stderr, out.stderr


def test_a_completed_item_is_told_only_postmortem_runs(tmp_path):
    root = _node(tmp_path)
    slug = _item(root)
    st = FsWorkStore.open(root)
    st.start(slug)
    st.complete(slug, "done", [])
    out = _tcw(root, "stage", "gate", "spec", slug)
    assert "no stage runs on it except `postmortem`" in out.stderr, out.stderr
