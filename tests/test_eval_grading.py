"""The grader returns the right verdict on each committed example run.

Four run directories under `tests/fixtures/eval_grading/`, one per verdict the
axis A core can produce. Two of them — `injected` and `fallback` — have **byte
identical artifacts**, carrying the same nonce in the same heading, and differ
only in what the transcript shows. That pair is the whole point: without reading
provenance the grader cannot tell them apart, and a run where injection failed
and the manual fallback rescued it would grade as injection working.
"""

import json
from pathlib import Path

import pytest

from evals import grade

FIXTURES = ["injected", "fallback", "nonce_absent", "blocks_missing"]


@pytest.fixture(scope="module")
def graded(request):
    root = request.config.rootpath / "tests/fixtures/eval_grading"
    return {name: grade.grade_run(root / name) for name in FIXTURES}


def _nonce_assertion(report):
    return next(a for a in report["assertions"]
                if a.get("predicate") == "nonce_in_artifact")


# --- the pair that only provenance separates ------------------------------

def test_the_injected_and_fallback_runs_have_identical_artifacts(request):
    """The premise the provenance read exists for. If these ever diverge, the
    pair stops testing what it was built to test."""
    root = request.config.rootpath / "tests/fixtures/eval_grading"
    bodies = {
        name: (root / name / "fixture/docs/work/backlog/item-one/spec.md").read_text()
        for name in ("injected", "fallback")
    }
    assert bodies["injected"] == bodies["fallback"]


def test_an_injected_nonce_passes(graded):
    verdict = _nonce_assertion(graded["injected"])
    assert verdict["provenance"] == grade.INJECTED
    assert verdict["passed"] is True
    assert verdict["evidence"], "a pass with no evidence is not a pass"


def test_a_fallback_sourced_nonce_fails_despite_being_present(graded):
    """The confound this module exists to close. The nonce is in the artifact,
    and that is not enough: the agent ran the prompt command by hand before it
    appeared, so the injection layer may have done nothing."""
    verdict = _nonce_assertion(graded["fallback"])
    assert verdict["provenance"] == grade.FALLBACK
    assert verdict["passed"] is False
    assert "a1b2c3d4e5f60718" in verdict["evidence"], (
        "the evidence should still show the nonce was found")


def test_running_the_gate_is_not_read_as_a_fallback(graded):
    """`tcw work stage gate` appears before the nonce in the injected run, and
    the fenced fallback names it. It prints a legality result and never the
    instructions, so it cannot be where a nonce came from. Treating it as one
    marked every well-behaved run fallback-sourced, because running the gate
    first is the behaviour case A7 rewards."""
    assert "tcw work stage gate" not in grade.FALLBACK_COMMANDS
    assert _nonce_assertion(graded["injected"])["provenance"] == grade.INJECTED


# --- the other two verdicts -----------------------------------------------

def test_an_absent_nonce_fails_as_unknown_not_as_injected(graded):
    """A nonce that never arrived has no provenance to report. `unknown` is
    never a pass."""
    verdict = _nonce_assertion(graded["nonce_absent"])
    assert verdict["provenance"] == grade.UNKNOWN
    assert verdict["passed"] is False
    assert "absent" in verdict["evidence"]


def test_a_nonce_the_transcript_never_shows_is_unknown(graded):
    """Reachable and distinct from the artifact being absent: the artifact can
    carry the nonce while the transcript never does, if the transcript was
    truncated or the capture failed. Nothing can then say how it arrived, and
    a run whose transcript was not captured cannot be graded for provenance.

    Tested directly because `p_nonce_in_artifact` returns early when the
    artifact lacks the nonce, so that path never reaches this branch.
    """
    events = [{"type": "assistant",
               "message": {"content": [{"text": "wrote the spec"}]}}]
    assert grade.provenance(events, "deadbeefdeadbeef") == grade.UNKNOWN
    assert grade.provenance([], "deadbeefdeadbeef") == grade.UNKNOWN


def test_provenance_only_counts_a_manual_call_that_came_first(graded):
    """An agent that writes the nonce and *then* runs the command by hand, to
    check its work, was still supplied by injection. Ordering is the whole
    discriminator, so a later call must not retroactively condemn the run."""
    def ev(text):
        return {"type": "assistant", "message": {"content": [{"text": text}]}}

    before = [ev("tcw work stage prompt spec x"), ev("marker abc123")]
    after = [ev("marker abc123"), ev("tcw work stage prompt spec x")]
    assert grade.provenance(before, "abc123") == grade.FALLBACK
    assert grade.provenance(after, "abc123") == grade.INJECTED


def test_a_silent_empty_render_fails_the_blocks_read(graded):
    """Failure mode I1, visible in the transcript and nowhere else."""
    report = graded["blocks_missing"]
    blocks = next(a for a in report["assertions"]
                  if a.get("predicate") == "transcript_blocks_present")
    assert blocks["passed"] is False
    for heading in grade.BLOCK_HEADINGS:
        assert heading in blocks["evidence"]


# --- tool inputs: what the agent ran or opened ----------------------------

READ_PATH = "/x/skills/tcw-setup/references/project.md"
RESULT_ONLY = "/x/skills/tcw-configure/references/docs-sync.md"
TEXT_ONLY = "/x/skills/tcw-setup/references/work.md"


def _routing_run() -> dict:
    """One opened file, one path that only a tool result mentions, and one that
    only the agent's prose mentions — the `stream-json` shape `load_events`
    reads."""
    return {"events": [
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": f"I might need {TEXT_ONLY} later."},
            {"type": "tool_use", "id": "t1", "name": "Read",
             "input": {"file_path": READ_PATH}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": f"# Project setup\n\nSee {RESULT_ONLY} for docs."},
        ]}},
    ]}


def test_tool_input_contains_finds_an_opened_file():
    verdict = grade.p_tool_input_contains(_routing_run(), text=READ_PATH)
    assert verdict["passed"], verdict["evidence"]


@pytest.mark.parametrize("mentioned_only", [RESULT_ONLY, TEXT_ONLY])
def test_a_path_only_mentioned_is_not_an_opened_file(mentioned_only):
    """The defect these predicates exist for: the whole-transcript read counts a
    path a loaded skill merely mentions as if the agent had opened it."""
    run = _routing_run()
    assert grade.p_transcript_contains(run, text=mentioned_only)["passed"]
    assert not grade.p_tool_input_contains(run, text=mentioned_only)["passed"]
    verdict = grade.p_tool_input_absent(run, text=mentioned_only)
    assert verdict["passed"], verdict["evidence"]


def test_tool_input_absent_fails_for_an_opened_file():
    verdict = grade.p_tool_input_absent(_routing_run(), text=READ_PATH)
    assert not verdict["passed"]
    assert READ_PATH in verdict["evidence"]


def test_tool_input_absent_fails_when_there_are_no_tool_calls_at_all():
    """A transcript in a shape the helper does not recognise yields no tool
    inputs, and "absent" would then pass for everything. No tool calls at all
    is treated as that, not as a clean result."""
    run = {"events": [{"type": "assistant", "message": {"content": [
        {"type": "text", "text": "done"}]}}]}
    verdict = grade.p_tool_input_absent(run, text=READ_PATH)
    assert not verdict["passed"]
    assert "no tool calls found" in verdict["evidence"]


# --- the routing assertions the cases actually carry ----------------------
#
# Read from `evals/evals.json` rather than restated, so a case whose search text
# is edited into something that no longer tells the two routes apart goes red
# here. Each row names a file an agent on the wrong route would open, which must
# fail the assertion, and one on the right route, which must pass it.

EVALS = json.loads((Path(grade.__file__).parent / "evals.json")
                   .read_text(encoding="utf-8"))

SETUP_PROJECT = "/p/skills/tcw-setup/references/project.md"
CONFIGURE_DOCS = "/p/skills/tcw-configure/references/docs-sync.md"
TAXONOMY_SKILL = "/p/skills/tcw-taxonomy/SKILL.md"

CASE_ROUTING = [
    ("B11", "tool_input_contains", SETUP_PROJECT, CONFIGURE_DOCS),
    ("B11", "tool_input_absent", SETUP_PROJECT, CONFIGURE_DOCS),
    ("B12", "tool_input_contains", CONFIGURE_DOCS, SETUP_PROJECT),
    ("B12", "tool_input_absent", CONFIGURE_DOCS, SETUP_PROJECT),
    ("B4", "tool_input_absent", SETUP_PROJECT, TAXONOMY_SKILL),
    ("B8", "tool_input_absent", SETUP_PROJECT, TAXONOMY_SKILL),
]


def _case_routing_assertion(case_id, predicate):
    case = next(c for c in EVALS["cases"] if c["id"] == case_id)
    found = [a for a in case["assertions"] if a.get("predicate") == predicate]
    assert len(found) == 1, f"{case_id} has {len(found)} {predicate} assertions"
    return found[0]


def _run_that_reads(path):
    return {"events": [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Read",
         "input": {"file_path": path}}]}}]}


@pytest.mark.parametrize("case_id, predicate, wrong, right", CASE_ROUTING,
                         ids=[f"{c}-{p}" for c, p, _, _ in CASE_ROUTING])
def test_a_case_routing_assertion_fails_the_wrong_route(case_id, predicate,
                                                        wrong, right):
    assertion = _case_routing_assertion(case_id, predicate)
    fn = grade.PREDICATES[predicate]
    failed = fn(_run_that_reads(wrong), **assertion["args"])
    assert not failed["passed"], (
        f"{case_id} {predicate} passed for a run that only opened {wrong}")
    passed = fn(_run_that_reads(right), **assertion["args"])
    assert passed["passed"], passed["evidence"]


# --- grading discipline ---------------------------------------------------

def test_a_pass_always_carries_evidence(graded):
    for name, report in graded.items():
        for a in report["assertions"]:
            if a["passed"]:
                assert a["evidence"].strip(), f"{name}: {a['text']}"


def test_a_verdict_with_no_evidence_cannot_pass():
    """A heading with nothing under it is a fail, enforced in one place rather
    than trusted to each predicate."""
    assert grade._verdict(True, "")["passed"] is False
    assert grade._verdict(True, "   ")["passed"] is False
    assert grade._verdict(True, "something")["passed"] is True


def test_an_unmechanized_assertion_is_neither_passed_nor_failed(graded):
    """Recording the claim honestly is the point of the marker. Counting it as a
    pass would inflate the rate; counting it as a fail would punish the harness
    for being honest about its reach."""
    verify = {"case": "A4", "assertions": [
        {"unmechanized": "x", "why": "y"}]}
    report = graded["injected"]
    for a in report["assertions"]:
        if "unmechanized" in a:
            assert a["passed"] is None
    assert report["graded"] == sum(
        1 for a in report["assertions"] if a["passed"] is not None)


def test_an_arm_scoped_assertion_is_skipped_on_the_other_arm(graded):
    """An assertion written for the customized arm says nothing about the
    control, and grading it there would manufacture a failure."""
    report = graded["injected"]
    assert report["arm"] == "customized"
    texts = [a["text"] for a in report["assertions"]]
    assert not any("control" in t for t in texts)


def test_every_declared_predicate_has_a_grader(request):
    """The test set and the grader are written against each other. A predicate
    declared with nothing to implement it would fail at grading time, after the
    money was spent."""
    evals = json.loads(
        (request.config.rootpath / "evals/evals.json").read_text())
    missing = set(evals["predicates"]) - set(grade.PREDICATES)
    assert not missing, f"declared but not implemented: {sorted(missing)}"


def test_no_grader_exists_for_an_undeclared_predicate(request):
    """The other direction. A grader with no declared predicate is dead code
    that nothing will ever call."""
    evals = json.loads(
        (request.config.rootpath / "evals/evals.json").read_text())
    orphan = set(grade.PREDICATES) - set(evals["predicates"])
    assert not orphan, f"implemented but not declared: {sorted(orphan)}"
