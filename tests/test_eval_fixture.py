"""The eval fixture still seeds, and its bindings still resolve.

This is what stops CLI drift from rotting the harness. The nonce half stops a
binding-schema change from rotting axis A specifically: the eval measures
whether a bound instruction reaches an agent, and a fixture whose bindings no
longer resolve would report that as a delivery failure rather than as a broken
instrument.

Slow by construction — each fixture is a real git repo driven through the real
CLI — so both variants are seeded once per module.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.seed_fixture import seed
from tcw.store.base import LIFECYCLE_STEPS


def _tcw(root, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(root), capture_output=True, text=True)


@pytest.fixture(scope="module")
def control(tmp_path_factory):
    root = tmp_path_factory.mktemp("control")
    return root, seed(root)


@pytest.fixture(scope="module")
def customized(tmp_path_factory):
    root = tmp_path_factory.mktemp("customized")
    return root, seed(root, customized=True)


# --- the node itself -------------------------------------------------------

@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_seeded_node_validates(variant, request):
    root, _ = request.getfixturevalue(variant)
    assert _tcw(root, "validate").returncode == 0


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_every_stage_case_has_an_item_the_gate_accepts(variant, request):
    """Stage legality (`STAGE_STATUSES`) restricts each stage to certain
    statuses, so an axis A case needs an item in the right one. Without this the
    verify case would address an item with no outcome to verify, and the failure
    would surface as an agent that produced nothing."""
    root, manifest = request.getfixturevalue(variant)
    for stage, slug in manifest["stage_items"].items():
        result = _tcw(root, "work", "stage", "gate", stage, slug)
        assert result.returncode == 0, (
            f"{stage} gate refused {slug} in the {variant} variant: "
            f"{result.stderr}")


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_mid_flight_item_still_fails_completion_closed(variant, request):
    """Case B3 asks an agent to close out the active item. The point of the case
    is that closing it requires flipping the ledger first, so the fixture is
    only useful while `tcw work complete` still refuses."""
    root, manifest = request.getfixturevalue(variant)
    result = _tcw(root, "work", "complete", manifest["items"]["active"],
                  "--resolution", "done", "--confirm")
    assert result.returncode != 0, "completion no longer fails closed"
    assert "billing/download-invoice" in result.stderr
    assert "still Missing" in result.stderr


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_inbox_request_is_untriaged(variant, request):
    root, _ = request.getfixturevalue(variant)
    assert (root / "docs/work/inbox/slow-login.md").is_file()


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_node_declares_documentation_entries(variant, request):
    """Case B10 asks an agent to close out a code change against a node that
    declares documentation entries. A node declaring none gives it nothing to
    act on, and `tcw work docs` says exactly that rather than failing, so the
    case would have graded against an empty trigger set."""
    root, _ = request.getfixturevalue(variant)
    result = _tcw(root, "work", "docs")
    assert result.returncode == 0, result.stderr
    assert "README.md" in result.stdout
    assert "docs/changelogs/upcoming.md" in result.stdout
    # The entries have to name files that exist, or the agent has nothing to edit.
    assert (root / "README.md").is_file()
    assert (root / "docs/changelogs/upcoming.md").is_file()


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_completed_item_carries_a_defect_found_after_acceptance(
        variant, request):
    """Case B9 asks for a post-mortem, which needs something to find."""
    root, manifest = request.getfixturevalue(variant)
    item = root / "docs/work/completed" / manifest["items"]["completed"]
    assert (item / "outcome.md").is_file()
    refined = (item / "refined-outcome.md").read_text()
    assert "Defect found after acceptance" in refined


# --- the bindings, which is what axis A rests on ---------------------------

NONCE_STAGES = [("file", "spec"), ("blob", "plan"), ("generate", "implement")]


@pytest.mark.parametrize("kind,stage", NONCE_STAGES)
def test_each_nonce_reaches_its_stage_prompt(kind, stage, customized):
    root, manifest = customized
    result = _tcw(root, "work", "stage", "prompt", stage,
                  manifest["stage_items"][stage])
    assert result.returncode == 0, result.stderr
    assert manifest["nonces"][kind] in result.stdout, (
        f"the {kind!r} binding resolved without its nonce")


@pytest.mark.parametrize("kind,stage", NONCE_STAGES)
def test_the_control_carries_no_nonce(kind, stage, customized, control):
    """The control is a node that configured nothing, so its stages fall back to
    the builtin floor. A nonce appearing here would mean it came from somewhere
    other than the binding."""
    croot, _ = control
    _, manifest = customized
    result = _tcw(croot, "work", "stage", "prompt", stage,
                  manifest["stage_items"][stage])
    assert manifest["nonces"][kind] not in result.stdout


def test_the_skill_binding_resolves_to_a_pointer_and_not_a_body(customized):
    """`_resolve_one` returns `Invoke the <name> skill.` and never reads the
    named skill. This is asserted rather than assumed because the plan's first
    draft expected a nonce here, and the whole verify case had to be restated
    when it turned out no nonce could ride this kind."""
    root, manifest = customized
    result = _tcw(root, "work", "stage", "prompt", "verify",
                  manifest["stage_items"]["verify"])
    assert "Invoke the eval-verify-marker skill." in result.stdout


def test_the_generate_script_survives_having_no_work_item(customized):
    """`hook_payload` sets `item` to null when the verb runs without a
    reference, which every per-stage skill documents. An unguarded script raises
    there, and a raise produces no stdout at all — which the harness would read
    as failure mode I1 rather than as a broken fixture."""
    root, _ = customized
    result = _tcw(root, "work", "stage", "prompt", "implement")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), "the stage rendered nothing"
    assert "TCW_EVAL_NO_ITEM" in result.stdout


def test_the_silence_opt_out_is_silent_against_a_speaking_control(
        customized, control):
    """The only form of this contrast that is not vacuous.

    Asserting "no project instruction appears" would pass in the control too,
    because the control has no project instructions anywhere — the never-fails
    shape the mutation rule exists to catch. What actually differs is that the
    customized node resolves `postmortem` to nothing at all, while the control
    falls back to the bookended builtin floor.
    """
    croot, cmanifest = control
    root, manifest = customized

    silenced = _tcw(root, "work", "stage", "prompt", "postmortem",
                    manifest["stage_items"]["postmortem"])
    assert silenced.returncode == 0, silenced.stderr
    assert silenced.stdout == "", (
        f"expected zero bytes, got {len(silenced.stdout)}")

    floor = _tcw(croot, "work", "stage", "prompt", "postmortem",
                 cmanifest["stage_items"]["postmortem"])
    assert floor.returncode == 0, floor.stderr
    assert floor.stdout.strip(), "the control's postmortem resolved to nothing"
    # The bookend is what makes it non-empty, and it is applied whenever the
    # resolved text is. Asserted by shape rather than by byte count, which moves
    # whenever a builtin prompt is edited.
    assert "tcw work stage gate postmortem" in floor.stdout


def test_a_commit_pattern_an_assertion_matches_on_really_appears(control):
    """`git_order` takes commit-subject patterns, and a pattern that matches
    nothing fails every run regardless of what the agent did.

    B1 originally looked for the literal word `start`. The transition commit's
    subject is `tcw work: <slug> → active` and never contains it, so that
    assertion would have reported a false negative on every run and looked like
    a skill defect. Pinned here against the shape the CLI actually writes, so a
    change to the transition commit message fails this rather than silently
    rotting the assertion.
    """
    root, _ = control
    log = subprocess.run(["git", "-C", str(root), "log", "--oneline"],
                         capture_output=True, text=True).stdout

    cases = json.loads(
        (Path(__file__).resolve().parent.parent / "evals/evals.json").read_text())
    patterns = {a["args"][end]
                for c in cases["cases"] for a in c["assertions"]
                if a.get("predicate") == "git_order" for end in ("before", "after")}

    # Two shapes are checkable against a seeded log, and between them they cover
    # the trap. A pattern that *looks like* a transition commit must match one.
    # And a pattern that is a bare transition verb must ALSO match one — which it
    # cannot, because TCW writes `tcw work: <slug> → <status>` and never the verb.
    # The second half is the whole point: filtering bare verbs out as
    # "unmatchable" would exclude precisely the mistake this guards against.
    transitions = {s.id for s in LIFECYCLE_STEPS if s.kind == "transition"}
    for pattern in patterns:
        looks_like_a_transition = "→" in pattern or "tcw work:" in pattern
        is_a_bare_verb = pattern.strip().lower() in transitions
        if looks_like_a_transition or is_a_bare_verb:
            assert pattern in log, (
                f"no commit in a seeded fixture matches {pattern!r}, so the "
                f"assertion using it fails every run regardless of what the "
                f"agent did. TCW writes `tcw work: <slug> → <status>`, never "
                f"the bare verb. Log:\n{log[:400]}")


def test_the_manifest_records_what_grading_cannot_guess(customized):
    root, manifest = customized
    on_disk = json.loads((root / "manifest.json").read_text())
    assert on_disk == manifest
    assert set(manifest["nonces"]) == {"file", "blob", "generate"}
    assert all(len(n) == 16 for n in manifest["nonces"].values())
    # Every minted slug, because they carry today's date.
    assert set(manifest["stage_items"]) == {
        "spec", "plan", "implement", "verify", "postmortem"}
