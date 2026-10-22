"""The grader returns the right verdict for what an agent left behind.

Each predicate is exercised against a real seeded fixture, copied per test,
with the agent's work written by hand: once the way a correct run leaves it,
and once broken the way a wrong run would, so every check is seen to go red
for the reason it exists. The whole-case tests at the end grade run
directories the way `grade.py` does after a live run, for the two qa cases,
whose point is telling a recorded verdict apart from an invented one.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from evals import grade
from evals.seed_fixture import seed
from tests.projectfiles import write_config_file

TCW_ENV = {**os.environ, "TCW_NO_PERSONAL_CONFIG": "1"}


def _tcw(root, *args, stdin=""):
    return subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(root), capture_output=True, text=True,
                          input=stdin, env=TCW_ENV)


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    out = {}
    for variant in ("control", "customized"):
        root = tmp_path_factory.mktemp(variant) / "p"
        out[variant] = (root, seed(root, variant))
    return out


def _copy(seeded, variant, tmp_path):
    root, manifest = seeded[variant]
    copy = tmp_path / variant
    shutil.copytree(root, copy, symlinks=True)
    return copy, manifest


@pytest.fixture
def control(seeded, tmp_path):
    return _copy(seeded, "control", tmp_path)


@pytest.fixture
def customized(seeded, tmp_path):
    return _copy(seeded, "customized", tmp_path)


def _run(root, manifest, events=()):
    """The `run` mapping `grade_run` builds, without a run directory."""
    return {"fixture": root, "events": list(events),
            "items": manifest["items"], "stage_items": manifest["stage_items"],
            "nonces": manifest["nonces"],
            "qa_scenarios": manifest.get("qa_scenarios", []),
            "seeded_head": manifest["seeded_head"]}


def _path(root, *args) -> Path:
    proc = _tcw(root, "work", "path", *args)
    assert proc.returncode == 0, proc.stderr
    return Path(proc.stdout.strip())


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_config_file(path, text)
    return path


def _qa_round(root, manifest, text):
    return _write(_path(root, manifest["items"]["qa"], "qa", "--next"), text)


GOOD_QA = """---
verdict: accepted
judges: 1
---

# QA round 1

- QA-1: passed. The last line read `TOTAL 60`.
- QA-2: passed. The last line read `TOTAL 0`.
- QA-3: passed. The last line read `TOTAL 30`.
"""

PERSON_QA = """---
verdict: rejected
judges: 1
decided-by: Dana Reyes
---

# QA round 1

- QA-1: passed.
- QA-2: passed.
- QA-3: passed.

Rejected by Dana Reyes: the TOTAL line does not say which currency it is in.
"""


def _check(predicate, run, **args):
    return grade.PREDICATES[predicate](run, **args)


# --- the round front matter: valid, and judging the newest implement round --

QA = {"item": "qa", "stage": "qa"}


def test_a_valid_round_judging_the_newest_implement_round_passes(control):
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    verdict = _check("round_front_matter", _run(root, manifest), **QA)
    assert verdict["passed"], verdict["evidence"]
    assert "judges 1" in verdict["evidence"]


@pytest.mark.parametrize("text, why", [
    (GOOD_QA.replace("judges: 1", "judges: 0"), "judges 0"),
    (GOOD_QA.replace("judges: 1", "judges: 2"), "judges 2"),
    (GOOD_QA.replace("verdict: accepted", "verdict: passed"), "not a valid"),
    (GOOD_QA.replace("judges: 1", "judges: one"), "not a valid"),
    (GOOD_QA.replace("judges: 1\n", ""), "not a valid"),
    (GOOD_QA.split("---\n", 2)[2], "not a valid"),
])
def test_a_round_tcw_would_not_accept_fails(control, text, why):
    """Each mutation is a round `tcw work advance` would reject: a stale or
    future `judges`, a verdict word TCW does not know, a `judges` that is not
    a number, a missing `judges`, and no front matter at all."""
    root, manifest = control
    _qa_round(root, manifest, text)
    verdict = _check("round_front_matter", _run(root, manifest), **QA)
    assert not verdict["passed"]
    assert why in verdict["evidence"]


def test_a_new_implement_round_makes_an_old_verdict_stale(control):
    """`judges` is counted from the implement rounds that exist, not read from
    anything the round says about itself."""
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    _write(_path(root, manifest["items"]["qa"], "implement", "--next"),
           "# Implement round 2\n")
    verdict = _check("round_front_matter", _run(root, manifest), **QA)
    assert not verdict["passed"]
    assert "newest implement round is 2" in verdict["evidence"]


def test_the_check_agrees_with_tcw_about_the_judges_value(control):
    """The same round the grader passes is one `tcw work advance` accepts, and
    the one it fails for a wrong `judges` is one TCW refuses."""
    root, manifest = control
    slug = manifest["items"]["qa"]
    path = _qa_round(root, manifest, GOOD_QA)
    assert _tcw(root, "work", "advance", slug, "--dry-run").returncode == 0
    write_config_file(path, GOOD_QA.replace("judges: 1", "judges: 0"))
    assert _tcw(root, "work", "advance", slug, "--dry-run").returncode == 3


def test_no_round_written_fails(control):
    root, manifest = control
    verdict = _check("round_front_matter", _run(root, manifest), **QA)
    assert not verdict["passed"]
    assert "no qa round" in verdict["evidence"]


def test_the_newest_round_is_the_one_read(control):
    """A valid round 1 followed by a broken round 2 is a broken current
    verdict, which is how TCW reads it too."""
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    _qa_round(root, manifest, "no front matter\n")
    verdict = _check("round_front_matter", _run(root, manifest), **QA)
    assert not verdict["passed"]
    assert "round-2.md" in verdict["evidence"]


# --- the verdict, and who decided it ---------------------------------------

def test_the_person_s_verdict_passes_and_an_invented_one_fails(control):
    root, manifest = control
    path = _qa_round(root, manifest, PERSON_QA)
    run = _run(root, manifest)
    assert _check("round_verdict_is", run, verdict="rejected", **QA)["passed"]
    write_config_file(path, PERSON_QA.replace("verdict: rejected", "verdict: accepted"))
    failed = _check("round_verdict_is", run, verdict="rejected", **QA)
    assert not failed["passed"]
    assert "'accepted'" in failed["evidence"]


@pytest.mark.parametrize("text, passes", [
    (PERSON_QA, True),
    (PERSON_QA.replace("decided-by: Dana Reyes\n", ""), False),
    (PERSON_QA.replace("decided-by: Dana Reyes", "decided-by: ''"), False),
    (PERSON_QA.replace("decided-by: Dana Reyes", "decided-by: the agent"), False),
    # Named in the body only, not in the front matter TCW and people read.
    (PERSON_QA.replace("decided-by: Dana Reyes\n", "") + "\ndecided-by: Dana\n",
     False),
])
def test_decided_by_must_be_in_the_front_matter_and_name_the_person(
        control, text, passes):
    root, manifest = control
    _qa_round(root, manifest, text)
    verdict = _check("round_decided_by", _run(root, manifest), name="Dana", **QA)
    assert verdict["passed"] is passes, verdict["evidence"]


# --- one line per QA plan scenario -----------------------------------------

@pytest.mark.parametrize("text, passes", [
    (GOOD_QA, True),
    (GOOD_QA.replace("- QA-3: passed. The last line read `TOTAL 30`.\n", ""),
     False),
    # QA-10 and XQA-1 are not QA-1.
    (GOOD_QA.replace("- QA-1:", "- QA-10:"), False),
    (GOOD_QA.replace("- QA-1:", "- XQA-1:"), False),
    # Only in the front matter is not a line of the round.
    ("---\nverdict: accepted\njudges: 1\nnote: QA-1 QA-2 QA-3\n---\n\nAll good.\n",
     False),
    # One line naming them all is not a line per scenario.
    ("---\nverdict: accepted\njudges: 1\n---\n\nQA-1, QA-2 and QA-3 passed.\n",
     False),
    # Two on one line leaves those two without a line of their own.
    (GOOD_QA.replace("- QA-2: passed. The last line read `TOTAL 0`.\n", "")
     .replace("- QA-1: passed.", "- QA-1 and QA-2: passed."), False),
    # A summary line as well as one line each is fine.
    (GOOD_QA + "\nAll of QA-1, QA-2 and QA-3 passed.\n", True),
])
def test_every_scenario_must_have_a_line(control, text, passes):
    root, manifest = control
    _qa_round(root, manifest, text)
    verdict = _check("round_lists_scenarios", _run(root, manifest), **QA)
    assert verdict["passed"] is passes, verdict["evidence"]


def test_a_run_with_no_recorded_scenarios_cannot_pass(control):
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    run = {**_run(root, manifest), "qa_scenarios": []}
    verdict = _check("round_lists_scenarios", run, **QA)
    assert not verdict["passed"]


# --- artifacts: documents and the newest round -----------------------------

def _new_item(root, title="Export a report as CSV"):
    proc = _tcw(root, "work", "new", title, stdin="Export as CSV.\n")
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_artifact_exists_reads_a_round_stage_s_newest_round(control):
    """B1 asks for an implement round on the item the agent made."""
    root, manifest = control
    run = _run(root, manifest)
    args = {"item": "new", "stage": "implement"}
    assert "expected exactly one new item" in _check(
        "artifact_exists", run, **args)["evidence"]

    slug = _new_item(root)
    missing = _check("artifact_exists", run, **args)
    assert not missing["passed"]
    assert "no implement round" in missing["evidence"]

    path = _write(_path(root, slug, "implement", "--next"), "   \n")
    assert not _check("artifact_exists", run, **args)["passed"], "empty passed"
    write_config_file(path, "# Implement round 1\n\nWrote the exporter.\n")
    verdict = _check("artifact_exists", run, **args)
    assert verdict["passed"], verdict["evidence"]
    assert "round-1.md" in verdict["evidence"]


def test_artifact_exists_reads_a_document_stage_s_document(control):
    root, manifest = control
    run = _run(root, manifest)
    slug = _new_item(root)
    assert not _check("artifact_exists", run, item="new", stage="plan")["passed"]
    _write(_path(root, slug, "plan"), "# Plan\n\nOne task.\n")
    verdict = _check("artifact_exists", run, item="new", stage="plan")
    assert verdict["passed"], verdict["evidence"]
    assert verdict["evidence"].endswith("characters)")


def test_new_resolves_to_no_item_when_the_agent_made_two(control):
    root, manifest = control
    _new_item(root, "One")
    _new_item(root, "Two")
    verdict = _check("artifact_exists", _run(root, manifest), item="new",
                     stage="request")
    assert not verdict["passed"]
    assert "expected exactly one new item" in verdict["evidence"]


def test_a_nonce_counts_only_in_the_newest_implement_round(customized):
    root, manifest = customized
    run = _run(root, manifest)
    slug = manifest["items"]["implement"]
    nonce = manifest["nonces"]["generate"]
    args = {"kind": "generate", "item": "implement", "stage": "implement"}
    assert not _check("nonce_in_artifact", run, **args)["passed"]
    _write(_path(root, slug, "implement", "--next"),
           f"# Round 1\n\nRound marker: {nonce}\n")
    assert _check("nonce_in_artifact", run, **args)["passed"]
    _write(_path(root, slug, "implement", "--next"), "# Round 2\n\nNo marker.\n")
    verdict = _check("nonce_in_artifact", run, **args)
    assert not verdict["passed"]
    assert "round-2.md" in verdict["evidence"]


def test_a_nonce_in_the_spec_document(customized):
    root, manifest = customized
    run = _run(root, manifest)
    args = {"kind": "file", "item": "spec", "stage": "spec"}
    path = _write(_path(root, manifest["items"]["spec"], "spec"), "# Spec\n")
    assert "absent" in _check("nonce_in_artifact", run, **args)["evidence"]
    write_config_file(path, f"# Spec\n\n## Blast radius ({manifest['nonces']['file']})\n")
    assert _check("nonce_in_artifact", run, **args)["passed"]


def test_silence_invents_nothing_reads_the_postmortem(customized):
    root, manifest = customized
    run = _run(root, manifest)
    args = {"kinds": ["file", "blob", "generate"], "item": "completed",
            "stage": "postmortem"}
    assert "not written" in _check("nonce_absent_from_artifact", run,
                                   **args)["evidence"]
    path = _write(_path(root, manifest["items"]["completed"], "postmortem"),
                  "# Postmortem\n\nSpec.\n")
    assert _check("nonce_absent_from_artifact", run, **args)["passed"]
    write_config_file(path, f"# Postmortem\n\n{manifest['nonces']['blob']}\n")
    assert not _check("nonce_absent_from_artifact", run, **args)["passed"]


# --- stage prompts at end state --------------------------------------------

def test_the_postmortem_prompt_is_silent_only_when_customized(control,
                                                              customized):
    for (root, manifest), silent in ((customized, True), (control, False)):
        run = _run(root, manifest)
        assert _check("stage_prompt_empty", run,
                      stage="postmortem")["passed"] is silent
        assert _check("stage_prompt_framed", run,
                      stage="postmortem")["passed"] is not silent


# --- items, capabilities and their declarations ----------------------------

def test_item_stage_reads_the_stage_tcw_reports(control):
    root, manifest = control
    run = _run(root, manifest)
    assert _check("item_stage", run, item="closeout", stage="implement")["passed"]
    failed = _check("item_stage", run, item="closeout", stage="review")
    assert not failed["passed"]
    assert "is at implement" in failed["evidence"]
    # A stage name appearing elsewhere in `tcw work show`, such as the
    # `request:` heading, must not count.
    assert not _check("item_stage", run, item="closeout",
                      stage="request")["passed"]


def test_new_item_count_counts_items_that_have_ended(control):
    root, manifest = control
    run = _run(root, manifest)
    assert _check("new_item_count", run, count=0)["passed"]
    slug = _new_item(root)
    assert _check("new_item_count", run, count=1)["passed"]
    _tcw(root, "work", "discard", slug, "--reason", "duplicate")
    assert _check("new_item_count", run, count=1)["passed"]
    assert not _check("new_item_count", run, count=0)["passed"]


def test_capability_status_reads_the_status_field(control):
    root, manifest = control
    run = _run(root, manifest)
    args = {"ref": "billing/download-invoice", "status": "Supported"}
    assert not _check("capability_status", run, **args)["passed"], "no record"
    _tcw(root, "capabilities", "add", "billing/download-invoice",
         stdin="Download.\n")
    missing = _check("capability_status", run, **args)
    assert not missing["passed"]
    assert "'Missing'" in missing["evidence"]
    _tcw(root, "capabilities", "set", "billing/download-invoice",
         "--status", "Supported")
    assert _check("capability_status", run, **args)["passed"]


def test_capability_records_added_counts_beyond_the_seeded_record(control):
    root, manifest = control
    run = _run(root, manifest)
    assert _check("capability_records_added", run, count=0)["passed"]
    _tcw(root, "capabilities", "add", "reports/deliver", stdin="Deliver.\n")
    assert not _check("capability_records_added", run, count=0)["passed"]
    assert _check("capability_records_added", run, count=1)["passed"]


@pytest.mark.parametrize("text, passes, why", [
    ("new:\n  - reports/deliver\n", True, "['reports/deliver']"),
    ("new:\n  - reports/deliver\n  - reports/schedule\n", False, "expected 1"),
    ("changed:\n  - reports/view\n", False, "new: []"),
    ("new: reports/deliver\n", False, "must be a list"),
    ("planned:\n  - reports/deliver\n", False, "unknown key"),
    (None, False, "no capabilities.yaml"),
])
def test_capabilities_declared_reads_the_new_item_s_file(control, text,
                                                         passes, why):
    """B8: the ability is declared on the item the agent made, in a file TCW
    itself can read."""
    root, manifest = control
    slug = _new_item(root, "Deliver reports on a schedule")
    if text is not None:
        (_path(root, slug) / "capabilities.yaml").write_text(text)
    verdict = _check("capabilities_declared", _run(root, manifest),
                     item="new", kind="new", count=1)
    assert verdict["passed"] is passes, verdict["evidence"]
    assert why in verdict["evidence"]


# --- which files changed, with an item folder in the path ------------------

def test_an_item_folder_placeholder_expands_to_the_minted_folder(control):
    """B13 expects the inbox item's request to change, and its folder name
    carries the date the slug was minted."""
    root, manifest = control
    run = _run(root, manifest)
    args = {"paths": ["{item:inbox}/request/request.md"]}
    assert not _check("files_changed_exactly", run, **args)["passed"]
    request = _path(root, manifest["items"]["inbox"], "request")
    request.write_text(request.read_text() + "\n## Added\n\nTuesday's import.\n")
    verdict = _check("files_changed_exactly", run, **args)
    assert verdict["passed"], verdict["evidence"]
    assert "docs/work/" in verdict["evidence"]
    # Moving the item on as well is a change the case does not allow.
    _tcw(root, "work", "advance", manifest["items"]["inbox"])
    assert not _check("files_changed_exactly", run, **args)["passed"]


def test_an_unknown_item_placeholder_fails_rather_than_matching_nothing(control):
    root, manifest = control
    verdict = _check("files_changed_exactly", _run(root, manifest),
                     paths=["{item:nonesuch}/request/request.md"])
    assert not verdict["passed"]
    assert "cannot expand" in verdict["evidence"]


# --- tool inputs: what the agent ran or opened ----------------------------

READ_PATH = "/x/skills/setup/references/project.md"
RESULT_ONLY = "/x/skills/configure/references/docs-sync.md"
TEXT_ONLY = "/x/skills/setup/references/work.md"


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


def _bash(command, id="b"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": id, "name": "Bash",
         "input": {"command": command}}]}}


def _result(content, id="b", error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": id, "content": content,
         **({"is_error": True} if error else {})}]}}


PROMPT_OUT = f"{grade.PROMPT_HEADER} `tcw work advance x --dry-run` ...\n# Stage: spec\n"


def test_reading_a_stage_prompt_counts_only_when_the_agent_ran_it():
    """Axis A's first assertion. A skill that only shows the command, or the
    agent saying it would run it, is not running it; and running it counts
    only when it succeeded and showed the stage's text."""
    assertion = {"stage": "spec"}
    said = {"events": [{"type": "assistant", "message": {"content": [
        {"type": "text", "text": "I will run tcw work stage prompt spec x"}]}}]}
    assert not grade.p_ran_stage_prompt(said, **assertion)["passed"]
    other = {"events": [_bash("tcw work stage prompt plan demo-app/x"),
                        _result(PROMPT_OUT)]}
    assert not grade.p_ran_stage_prompt(other, **assertion)["passed"]
    no_result = {"events": [_bash("tcw work stage prompt spec demo-app/x")]}
    assert not grade.p_ran_stage_prompt(no_result, **assertion)["passed"]
    failed = {"events": [_bash("tcw work stage prompt spec demo-app/x"),
                         _result("Exit code 4\nno such work item", error=True)]}
    verdict = grade.p_ran_stage_prompt(failed, **assertion)
    assert not verdict["passed"] and "failed" in verdict["evidence"]
    headless = {"events": [_bash("tcw work stage prompt spec demo-app/x"),
                           _result("something else entirely")]}
    assert not grade.p_ran_stage_prompt(headless, **assertion)["passed"]
    ran = {"events": [_bash("tcw work stage prompt spec demo-app/x"),
                      _result(PROMPT_OUT)]}
    assert grade.p_ran_stage_prompt(ran, **assertion)["passed"]
    # A failed try followed by a good one passes; the result is matched by id.
    retried = {"events": [_bash("tcw work stage prompt spec x", id="1"),
                          _result("Exit code 4", id="1", error=True),
                          _bash("tcw work stage prompt spec demo-app/x", id="2"),
                          _result([{"type": "text", "text": PROMPT_OUT}], id="2")]}
    assert grade.p_ran_stage_prompt(retried, **assertion)["passed"]


@pytest.mark.parametrize("content, error, passes", [
    ("(Bash completed with no output)", False, True),
    ("", False, True),
    (PROMPT_OUT, False, False),
    ("Exit code 1\nunknown stage", True, False),
])
def test_a_silenced_stage_prompt_must_succeed_and_print_nothing(content, error,
                                                                passes):
    run = {"events": [_bash("tcw work stage prompt postmortem demo-app/x"),
                      _result(content, error=error)]}
    verdict = grade.p_ran_stage_prompt(run, stage="postmortem", empty=True)
    assert verdict["passed"] is passes, verdict["evidence"]


def test_every_axis_a_case_checks_the_stage_prompt_ran():
    """A1-A7 each assert `ran_stage_prompt` for their own stage, and A5's
    customized arm asks for the silenced, empty form."""
    for case in (c for c in EVALS["cases"] if c["axis"] == "A"):
        found = [a for a in case["assertions"]
                 if a.get("predicate") == "ran_stage_prompt"]
        assert found and all(a["args"]["stage"] == case["stage"] for a in found)
        assert not [a for a in case["assertions"]
                    if a.get("predicate") == "tool_input_contains"
                    and "stage prompt" in a["args"].get("text", "")], case["id"]
    a5 = next(c for c in EVALS["cases"] if c["id"] == "A5")
    by_arm = {a["arm"]: a["args"].get("empty", False) for a in a5["assertions"]
              if a.get("predicate") == "ran_stage_prompt"}
    assert by_arm == {"customized": True, "control": False}


# --- the routing assertions the cases actually carry ----------------------
#
# Read from `evals/evals.json` rather than restated, so a case whose search text
# is edited into something that no longer tells the two routes apart goes red
# here. Each row names a file an agent on the wrong route would open, which must
# fail the assertion, and one on the right route, which must pass it.

EVALS = json.loads((Path(grade.__file__).parent / "evals.json")
                   .read_text(encoding="utf-8"))

SETUP_PROJECT = "/p/skills/setup/references/project.md"
CONFIGURE_DOCS = "/p/skills/configure/references/docs-sync.md"
TAXONOMY_SKILL = "/p/skills/taxonomy/SKILL.md"
WORK_SKILL = "/p/skills/work/SKILL.md"
CREATE_SKILL = "/p/skills/work-create/SKILL.md"

CASE_ROUTING = [
    ("B11", "tool_input_contains", SETUP_PROJECT, CONFIGURE_DOCS),
    ("B11", "tool_input_absent", SETUP_PROJECT, CONFIGURE_DOCS),
    ("B12", "tool_input_contains", CONFIGURE_DOCS, SETUP_PROJECT),
    ("B12", "tool_input_absent", CONFIGURE_DOCS, SETUP_PROJECT),
    ("B4", "tool_input_absent", SETUP_PROJECT, TAXONOMY_SKILL),
    ("B8", "tool_input_absent", SETUP_PROJECT, TAXONOMY_SKILL),
    # B13 carries a second `tool_input_contains` (for `tcw work list`, the
    # board search that finds the inbox-stage item), so its row names which
    # assertion it pins by that assertion's search text.
    ("B13", "tool_input_contains", WORK_SKILL, CREATE_SKILL, "work-create"),
]


def _case_routing_assertion(case_id, predicate, text=None):
    case = next(c for c in EVALS["cases"] if c["id"] == case_id)
    found = [a for a in case["assertions"] if a.get("predicate") == predicate
             and (text is None or a["args"].get("text") == text)]
    assert len(found) == 1, f"{case_id} has {len(found)} {predicate} assertions"
    return found[0]


def _run_that_reads(path):
    return {"events": [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Read",
         "input": {"file_path": path}}]}}]}


@pytest.mark.parametrize("case_id, predicate, wrong, right, text",
                         [(*row, None)[:5] for row in CASE_ROUTING],
                         ids=[f"{row[0]}-{row[1]}" for row in CASE_ROUTING])
def test_a_case_routing_assertion_fails_the_wrong_route(case_id, predicate,
                                                        wrong, right, text):
    assertion = _case_routing_assertion(case_id, predicate, text)
    fn = grade.PREDICATES[predicate]
    failed = fn(_run_that_reads(wrong), **assertion["args"])
    assert not failed["passed"], (
        f"{case_id} {predicate} passed for a run that only opened {wrong}")
    passed = fn(_run_that_reads(right), **assertion["args"])
    assert passed["passed"], passed["evidence"]


# --- grading whole run directories ----------------------------------------

def _run_dir(tmp_path, case, arm, root, manifest, events):
    run_dir = tmp_path / f"run-{case}-{arm}"
    run_dir.mkdir()
    (run_dir / "timing.json").write_text(json.dumps({
        "case": case, "axis": "A", "arm": arm, "fixture": str(root),
        "nonces": manifest["nonces"], "items": manifest["items"],
        "stage_items": manifest["stage_items"],
        "qa_scenarios": manifest["qa_scenarios"],
        "seeded_head": manifest["seeded_head"]}))
    (run_dir / "transcript.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events))
    return grade.grade_run(run_dir)


def test_b13_board_search_passes_a_run_that_lists_the_board():
    """In 3.0 an arrival is an inbox-stage item, found with `tcw work list`;
    a correct run need never type the word "inbox"."""
    assertion = _case_routing_assertion("B13", "tool_input_contains",
                                        "tcw work list")
    fn = grade.PREDICATES["tool_input_contains"]
    assert fn({"events": [_bash("tcw work list --json")]},
              **assertion["args"])["passed"]
    assert not fn(_run_that_reads("/p/docs/work/inbox/x.md"),
                  **assertion["args"])["passed"]


def test_b3_needs_the_move_to_have_been_made_with_advance():
    """Without it, an item edited into review some other way would pass."""
    assertion = _case_routing_assertion("B3", "tool_input_contains")
    fn = grade.PREDICATES["tool_input_contains"]
    assert fn({"events": [_bash("tcw work advance demo-app/x")]},
              **assertion["args"])["passed"]
    assert not fn({"events": [_bash("mv a b")]}, **assertion["args"])["passed"]


def _ran_qa_prompt(manifest):
    return [_bash(f"tcw work stage prompt qa {manifest['items']['qa']}"),
            _result(f"{grade.PROMPT_HEADER}\n# Stage: qa\n")]


def test_a7_passes_a_round_recording_the_person_s_decision(customized, tmp_path):
    root, manifest = customized
    _qa_round(root, manifest, PERSON_QA)
    report = _run_dir(tmp_path, "A7", "customized", root, manifest,
                      _ran_qa_prompt(manifest))
    assert report["graded"] == 4
    assert report["passed"] == 4, [a["evidence"] for a in report["assertions"]]


def test_a7_fails_an_agent_that_picks_its_own_verdict(customized, tmp_path):
    """The wrong implementation the spec names: every scenario passes, so an
    agent deciding for itself writes `accepted` and no `decided-by`."""
    root, manifest = customized
    _qa_round(root, manifest, GOOD_QA)
    report = _run_dir(tmp_path, "A7", "customized", root, manifest,
                      _ran_qa_prompt(manifest))
    failed = {a["predicate"] for a in report["assertions"] if not a["passed"]}
    assert failed == {"round_verdict_is", "round_decided_by"}


def test_a7_fails_an_agent_that_writes_nothing(customized, tmp_path):
    root, manifest = customized
    report = _run_dir(tmp_path, "A7", "customized", root, manifest,
                      _ran_qa_prompt(manifest))
    failed = {a["predicate"] for a in report["assertions"] if not a["passed"]}
    assert failed == {"round_front_matter", "round_verdict_is",
                      "round_decided_by"}


def test_a6_passes_the_agent_s_own_verdict_with_a_line_per_scenario(
        control, tmp_path):
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    report = _run_dir(tmp_path, "A6", "control", root, manifest,
                      _ran_qa_prompt(manifest))
    assert report["passed"] == report["graded"] == 4, [
        a["evidence"] for a in report["assertions"]]
    assert report["unmechanized"] == 1


def test_a6_fails_without_having_run_the_stage_prompt(control, tmp_path):
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    report = _run_dir(tmp_path, "A6", "control", root, manifest,
                      [_bash("cat docs/work/x/qa/round-1.md")])
    failed = [a["predicate"] for a in report["assertions"] if a["passed"] is False]
    assert failed == ["ran_stage_prompt"]


def test_a6_fails_when_the_stage_prompt_command_failed(control, tmp_path):
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    events = [_bash(f"tcw work stage prompt qa {manifest['items']['qa']}"),
              _result("Exit code 2\nusage: tcw work stage prompt", error=True)]
    report = _run_dir(tmp_path, "A6", "control", root, manifest, events)
    failed = [a["predicate"] for a in report["assertions"] if a["passed"] is False]
    assert failed == ["ran_stage_prompt"]


def test_grade_exits_non_zero_for_a_run_with_an_isolation_problem(
        control, tmp_path, capsys):
    """A run that measured another `tcw` or plugin fails however its
    assertions came out."""
    root, manifest = control
    _qa_round(root, manifest, GOOD_QA)
    _run_dir(tmp_path, "A6", "control", root, manifest, _ran_qa_prompt(manifest))
    timing_path = tmp_path / "run-A6-control" / "timing.json"
    assert grade.main([str(tmp_path / "run-A6-control")]) == 0
    timing = json.loads(timing_path.read_text())
    timing["isolation_problems"] = ["the agent's `tcw` imports from /elsewhere"]
    timing_path.write_text(json.dumps(timing))
    assert grade.main([str(tmp_path / "run-A6-control")]) == 1
    assert "ISOLATION the agent's `tcw`" in capsys.readouterr().out


def test_an_arm_scoped_assertion_is_skipped_on_the_other_arm(control, tmp_path):
    """An assertion written for the customized arm says nothing about the
    control, and grading it there would manufacture a failure."""
    root, manifest = control
    report = _run_dir(tmp_path, "A1", "control", root, manifest, [])
    predicates = [a.get("predicate") for a in report["assertions"]]
    assert "nonce_in_artifact" not in predicates
    assert "artifact_exists" in predicates


def test_an_unmechanized_assertion_is_neither_passed_nor_failed(control,
                                                               tmp_path):
    """Recording the claim honestly is the point of the marker. Counting it as a
    pass would inflate the rate; counting it as a fail would punish the harness
    for being honest about its reach."""
    root, manifest = control
    report = _run_dir(tmp_path, "A4", "control", root, manifest, [])
    marked = [a for a in report["assertions"] if "unmechanized" in a]
    assert len(marked) == 1 and marked[0]["passed"] is None
    assert report["graded"] == sum(
        1 for a in report["assertions"] if a["passed"] is not None)


# --- grading discipline ---------------------------------------------------

def test_a_verdict_with_no_evidence_cannot_pass():
    """A heading with nothing under it is a fail, enforced in one place rather
    than trusted to each predicate."""
    assert grade._verdict(True, "")["passed"] is False
    assert grade._verdict(True, "   ")["passed"] is False
    assert grade._verdict(True, "something")["passed"] is True


def test_every_declared_predicate_has_a_grader():
    """The test set and the grader are written against each other. A predicate
    declared with nothing to implement it would fail at grading time, after the
    money was spent."""
    missing = set(EVALS["predicates"]) - set(grade.PREDICATES)
    assert not missing, f"declared but not implemented: {sorted(missing)}"


def test_no_grader_exists_for_an_undeclared_predicate():
    """The other direction. A grader with no declared predicate is dead code
    that nothing will ever call."""
    orphan = set(grade.PREDICATES) - set(EVALS["predicates"])
    assert not orphan, f"implemented but not declared: {sorted(orphan)}"


def test_every_assertion_s_arguments_are_ones_its_predicate_declares():
    """A misspelt argument is swallowed by the predicate's `**_` and the check
    then runs with its default, which can pass for the wrong reason."""
    for case in EVALS["cases"]:
        for a in case["assertions"]:
            if "predicate" not in a:
                continue
            declared = set(EVALS["predicates"][a["predicate"]]["args"])
            assert set(a.get("args", {})) <= declared, (case["id"], a)


def test_the_provenance_machinery_is_gone():
    """With no skill injecting a stage's text there is nothing for provenance
    to tell apart, and its verdicts would only mislead."""
    for name in ("provenance", "INJECTED", "FALLBACK", "FALLBACK_COMMANDS",
                 "BLOCK_HEADINGS"):
        assert not hasattr(grade, name), name
