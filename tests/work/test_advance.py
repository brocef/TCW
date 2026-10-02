"""Moving an item: `advance` and `discard` (TCW-69 Design 6; AC 6-12).

Everything runs through `advance` against the memory backend, with real hooks
run as shell commands from a temporary project root.
"""

import pytest

from tcw import exit as codes
from tcw.errors import NotFound, UsageError
from tcw.work.advance import advance, discard
from tcw.work.config import parse_work_config
from tcw.work.gates import Present
from tcw.work.layout import Layout
from tcw.work.model import Changes, Slug
from tests.work.fake_reader import FakeReader
from tests.work.memory_backend import MemoryBackend

JIRA_LIKE = frozenset({"request", "qa"})


class World:
    """One project: a backend, its configuration, layout and records reader."""

    def __init__(self, root, work=None, *, external=frozenset(), inbox_items=True,
                 reader=None):
        self.root = root
        self.config, problems = parse_work_config(work or {})
        assert problems == []
        self.backend = MemoryBackend(root / "work", external_stages=external,
                                     inbox_items=inbox_items, user="sam")
        self.layout = Layout(root / "work", self.config.enabled, frozenset(external))
        self.reader = reader or FakeReader()

    def item(self, stage, tags=()):
        item = self.backend.create("thing", Changes(add_tags=tuple(tags)),
                                   stage="request", request=None)
        self.backend.set_reported_stage(item.slug.folder, stage)
        self.backend.calls.clear()
        return item.slug

    def advance(self, slug, **kwargs):
        return advance(self.backend, self.config, self.layout, self.reader,
                       self.root, slug, **kwargs)

    def stage(self, slug):
        return self.backend.stage_of(slug.folder)

    def moves(self):
        return [c for c in self.backend.calls if c[0] == "set_stage"]

    def round(self, slug, stage, n, text=""):
        path = self.layout.stage_dir(slug, stage) / f"round-{n}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def declare(self, slug, text):
        self.layout.capabilities_file(slug).write_text(text)


def verdict(state, judges):
    return f"---\nverdict: {state}\njudges: {judges}\n---\n"


def stages(**per_stage):
    return {"stages": per_stage}


def pre(*commands, when=None):
    out = [{"command": c} for c in commands]
    if when:
        for binding in out:
            binding["when"] = when
    return out


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def refused(outcome, *words):
    assert outcome.code == codes.REFUSED, outcome
    text = " ".join(outcome.messages)
    for word in words:
        assert word in text, text


# -- AC 6: disabled stages ----------------------------------------------------

def test_with_review_and_qa_disabled_implement_moves_to_completed(tmp_path):
    w = World(tmp_path, stages(review={"enabled": False}, qa={"enabled": False}))
    slug = w.item("implement")
    w.declare(slug, "new: [x/y]\n")
    refused(w.advance(slug), "x/y")              # the records gate ran on it
    w.reader.capabilities["x/y"] = Present("Supported")
    outcome = w.advance(slug)
    assert (outcome.code, outcome.stage) == (codes.OK, "completed")
    assert w.stage(slug) == "completed"


def test_with_plan_disabled_spec_moves_to_implement(tmp_path):
    w = World(tmp_path, stages(plan={"enabled": False}))
    slug = w.item("spec")
    assert w.advance(slug).stage == "implement"


# -- AC 7: a bare advance -----------------------------------------------------

def test_request_goes_to_spec(world):
    slug = world.item("request")
    outcome = world.advance(slug)
    assert (outcome.code, outcome.stage) == (codes.OK, "spec")
    assert world.moves() == [("set_stage", slug.folder, "spec", None)]


def test_a_rejected_review_goes_back_to_implement(world):
    slug = world.item("review")
    world.round(slug, "review", 1, verdict("rejected", 0))
    assert world.advance(slug).stage == "implement"


def test_an_accepted_review_goes_to_qa(world):
    slug = world.item("review")
    world.round(slug, "review", 1, verdict("accepted", 0))
    assert world.advance(slug).stage == "qa"


@pytest.mark.parametrize("rounds, expected_file", [
    ([], "round-1.md"),
    (["oops"], "round-2.md"),
])
def test_review_without_a_usable_verdict_is_refused(world, rounds, expected_file):
    slug = world.item("review")
    for n, text in enumerate(rounds, start=1):
        world.round(slug, "review", n, text)
    refused(world.advance(slug), expected_file)
    assert world.moves() == []


def test_a_review_accepted_before_a_newer_implementation_is_stale(world):
    slug = world.item("review")
    world.round(slug, "implement", 1)
    world.round(slug, "review", 1, verdict("accepted", 1))
    world.round(slug, "implement", 2)
    refused(world.advance(slug), "stale", "round-2.md")


def test_a_rejected_qa_goes_back_to_implement(world):
    slug = world.item("qa")
    world.round(slug, "qa", 1, verdict("rejected", 0))
    assert world.advance(slug).stage == "implement"


def test_an_external_qa_needs_to(tmp_path):
    w = World(tmp_path, external=JIRA_LIKE)
    slug = w.item("qa")
    refused(w.advance(slug), "--to")


@pytest.mark.parametrize("stage", ["completed", "discarded", None])
def test_no_bare_advance_from_a_terminal_stage_or_from_no_stage(world, stage):
    slug = world.item(stage)
    refused(world.advance(slug))
    assert world.moves() == []


def test_an_unknown_item_is_not_found(world):
    with pytest.raises(NotFound):
        world.advance(Slug("tcw", "nope"))


# -- AC 8: skips, reasons and backward moves -----------------------------------

def test_a_skip_needs_force(world):
    slug = world.item("spec")
    refused(world.advance(slug, to="implement"), "--force")


def test_a_skip_to_completed_needs_force(tmp_path):
    w = World(tmp_path, stages(review={"enabled": False}, qa={"enabled": False}))
    slug = w.item("spec")
    refused(w.advance(slug, to="completed"), "--force")


def test_a_forced_skip_moves_with_a_note(world):
    slug = world.item("spec")
    outcome = world.advance(slug, to="implement", force=True, reason="plan is trivial")
    assert (outcome.code, outcome.stage) == (codes.OK, "implement")
    [(_, _, _, note)] = world.moves()
    assert "plan is trivial" in note and "forced" in note
    assert "spec" in note and "implement" in note


def test_moving_back_needs_no_force_and_records_no_note(world):
    slug = world.item("review")
    assert world.advance(slug, to="spec").code == codes.OK
    assert world.moves() == [("set_stage", slug.folder, "spec", None)]


def test_a_reason_on_an_ordinary_move_is_recorded(world):
    slug = world.item("request")
    world.advance(slug, reason="ready")
    assert "ready" in world.moves()[0][3]


def test_leaving_a_rejected_review_forward_needs_force(world):
    slug = world.item("review")
    world.round(slug, "review", 1, verdict("rejected", 0))
    refused(world.advance(slug, to="qa"))
    assert world.advance(slug, to="qa", force=True, reason="r").code == codes.OK


def test_discarding_needs_a_reason(world):
    slug = world.item("spec")
    with pytest.raises(UsageError):
        world.advance(slug, to="discarded")
    assert world.backend.calls == []


@pytest.mark.parametrize("stage", ["request", "review", "completed", None])
def test_discarding_works_from_any_stage_without_force(world, stage):
    slug = world.item(stage)
    outcome = discard(world.backend, world.config, world.layout, world.reader,
                      world.root, slug, "no longer wanted")
    assert (outcome.code, outcome.stage) == (codes.OK, "discarded")
    assert "no longer wanted" in world.moves()[0][3]


def test_reopening_a_finished_item_needs_a_reason(world):
    slug = world.item("completed")
    refused(world.advance(slug, to="implement"), "reason")
    outcome = world.advance(slug, to="implement", reason="regressed")
    assert outcome.code == codes.OK
    assert "regressed" in world.moves()[0][3]


def test_leaving_an_external_qa_needs_a_reason(tmp_path):
    w = World(tmp_path, external=JIRA_LIKE)
    slug = w.item("qa")
    refused(w.advance(slug, to="implement"), "reason")
    assert w.advance(slug, to="implement", reason="fails on Safari").code == codes.OK
    assert "fails on Safari" in w.moves()[0][3]


def test_an_external_qa_is_accepted_by_moving_to_completed(tmp_path):
    w = World(tmp_path, external=JIRA_LIKE)
    slug = w.item("qa")
    w.round(slug, "review", 1, verdict("accepted", 0))
    assert w.advance(slug, to="completed", reason="QA passed").code == codes.OK


def test_inbox_is_refused_when_the_backend_keeps_no_inbox_items(tmp_path):
    w = World(tmp_path, inbox_items=False)
    slug = w.item("request")
    refused(w.advance(slug, to="inbox"))
    filesystem_like = World(tmp_path / "fs")
    assert filesystem_like.advance(filesystem_like.item("request"),
                                   to="inbox").code == codes.OK


@pytest.mark.parametrize("kwargs", [
    {"to": "postmortem"},
    {"to": "bogus"},
    {"force": True},
    {"force": True, "reason": "  "},
])
def test_usage_errors_touch_nothing(world, kwargs):
    slug = world.item("spec")
    with pytest.raises(UsageError):
        world.advance(slug, **kwargs)
    assert world.backend.calls == []


def test_a_disabled_target_is_a_usage_error(tmp_path):
    w = World(tmp_path, stages(plan={"enabled": False}))
    with pytest.raises(UsageError):
        w.advance(w.item("spec"), to="plan")


def test_a_move_to_the_current_stage_is_refused(world):
    slug = world.item("spec")
    refused(world.advance(slug, to="spec"))


# -- AC 9: gates run for the target only ---------------------------------------

def test_a_failing_pre_refuses_the_move_into_its_stage(tmp_path):
    w = World(tmp_path, stages(review={"pre": pre("false")}))
    slug = w.item("implement")
    refused(w.advance(slug), "false")
    assert w.stage(slug) == "implement"
    assert w.moves() == []


def test_a_failing_pre_on_the_current_stage_does_not_matter(tmp_path):
    w = World(tmp_path, stages(spec={"pre": pre("false")}))
    slug = w.item("spec")
    assert w.advance(slug).stage == "plan"


def test_forced_gates_all_run_and_are_all_noted(tmp_path):
    w = World(tmp_path, stages(review={"pre": pre("false", "exit 7", "true")}))
    slug = w.item("implement")
    outcome = w.advance(slug, force=True, reason="hotfix")
    assert (outcome.code, outcome.stage) == (codes.OK, "review")
    assert len(outcome.overridden) == 2
    note = w.moves()[0][3]
    assert "`false`" in note and "`exit 7`" in note


def test_a_pre_whose_when_does_not_match_does_not_run(tmp_path):
    w = World(tmp_path, stages(review={"pre": pre("false", when={"tags": ["bug"]})}))
    assert w.advance(w.item("implement")).code == codes.OK
    refused(w.advance(w.item("implement", tags=["bug"])))


def test_not_tags_excludes(tmp_path):
    w = World(tmp_path, stages(review={"pre": pre("false", when={"not_tags": ["docs"]})}))
    assert w.advance(w.item("implement", tags=["docs"])).code == codes.OK
    refused(w.advance(w.item("implement")))


def test_hooks_get_the_callers_environment(tmp_path):
    w = World(tmp_path, stages(spec={"pre": pre(
        'python -c "import sys; sys.exit(0)"')}))
    assert w.advance(w.item("request")).code == codes.OK


def test_hooks_get_the_stage_variables_and_run_from_the_project_root(tmp_path):
    check = ('test "$TCW_STAGE" = review && test "$TCW_FROM_STAGE" = implement '
             '&& test "$TCW_SLUG" = tcw/1-thing '
             '&& test "$TCW_ITEM_PATH" = "$TCW_PROJECT_ROOT/work/1-thing" '
             '&& test "$(pwd -P)" = "$(cd "$TCW_PROJECT_ROOT" && pwd -P)" '
             '&& test -z "$TCW_FORCED"')
    w = World(tmp_path, stages(review={"pre": pre(check)}))
    assert w.advance(w.item("implement")).code == codes.OK


def test_forced_hooks_see_the_reason(tmp_path):
    check = 'test "$TCW_FORCED" = 1 && test "$TCW_REASON" = "why not"'
    w = World(tmp_path, stages(implement={"pre": pre(check)}))
    outcome = w.advance(w.item("spec"), to="implement", force=True, reason="why not")
    assert outcome.overridden == ()


def test_the_records_gate_refuses_a_move_into_review(world):
    slug = world.item("implement")
    world.declare(slug, "new: [x/y]\n")
    refused(world.advance(slug), "x/y")


def test_the_completion_gate_refuses_an_unaccepted_finish(world):
    slug = world.item("qa")
    world.round(slug, "review", 1, "no verdict")
    world.round(slug, "qa", 1, verdict("accepted", 0))
    refused(world.advance(slug), "completion")
    world.round(slug, "review", 2, verdict("accepted", 0))
    assert world.advance(slug).stage == "completed"


# -- AC 10: post hooks and the trace -------------------------------------------

def test_a_failing_post_keeps_the_move(tmp_path):
    w = World(tmp_path, stages(spec={"post": pre("false")}))
    slug = w.item("request")
    outcome = w.advance(slug)
    assert (outcome.code, outcome.stage) == (codes.MOVED_WITH_PROBLEM, "spec")
    assert w.stage(slug) == "spec"


def test_a_lost_note_gives_exit_6_and_post_still_runs(tmp_path):
    marker = tmp_path / "post-ran"
    w = World(tmp_path, stages(implement={"post": pre(f"touch {marker}")}))
    w.backend.lose_notes = True
    slug = w.item("spec")
    outcome = w.advance(slug, to="implement", force=True, reason="r")
    assert outcome.code == codes.MOVED_WITH_PROBLEM
    assert any("tcw work comment" in m for m in outcome.messages)
    assert marker.exists()
    assert w.stage(slug) == "implement"


def test_a_backend_refusal_moves_nothing_and_runs_no_post(tmp_path):
    marker = tmp_path / "post-ran"
    w = World(tmp_path, stages(spec={"post": pre(f"touch {marker}")}))
    w.backend.refuse_moves = True
    slug = w.item("request")
    outcome = w.advance(slug)
    assert outcome.code == codes.REFUSED
    assert w.stage(slug) == "request"
    assert not marker.exists()


def test_a_backend_reporting_another_stage_is_an_error(tmp_path):
    marker = tmp_path / "post-ran"
    w = World(tmp_path, stages(spec={"post": pre(f"touch {marker}")}))
    w.backend.report_stage = "plan"
    outcome = w.advance(w.item("request"))
    assert (outcome.code, outcome.stage) == (codes.ERROR, "plan")
    assert "plan" in outcome.messages[0] and "spec" in outcome.messages[0]
    assert not marker.exists()


# -- AC 11: dry run ------------------------------------------------------------

def test_a_dry_run_runs_the_gates_and_moves_nothing(tmp_path):
    w = World(tmp_path, stages(review={"pre": pre("false")}))
    slug = w.item("implement")
    refused(w.advance(slug, dry_run=True))
    ok = w.advance(w.item("request"), dry_run=True, reason="r")
    assert (ok.code, ok.stage) == (codes.OK, "spec")
    assert not [c for c in w.backend.calls if c[0] in ("set_stage", "comment")]


# -- AC 12: an item with no stage ------------------------------------------------

def test_an_item_with_no_stage_moves_only_when_forced(world):
    slug = world.item(None)
    refused(world.advance(slug, to="spec"), "--force")
    outcome = world.advance(slug, to="spec", force=True, reason="r")
    assert (outcome.code, outcome.stage) == (codes.OK, "spec")


# -- AC 21: the trace is a comment ---------------------------------------------

def test_a_forced_move_adds_its_trace_to_the_comments(world):
    slug = world.item("spec")
    world.advance(slug, to="implement", force=True, reason="trivial plan")
    assert "trivial plan" in world.backend.read_comments(slug.folder)[0].text
