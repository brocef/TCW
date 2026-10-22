"""The eval fixture still seeds, and its bindings still resolve.

This is what stops CLI drift from rotting the harness. The nonce half stops a
binding-schema change from rotting axis A specifically: the eval measures
whether a bound instruction reaches an agent, and a fixture whose bindings no
longer resolve would report that as a delivery failure rather than as a broken
instrument.

Slow by construction — each fixture is a real git repo driven through the real
CLI — so each variant is seeded once per module. A test that has to change a
fixture changes a copy of it.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from evals import grade
from evals.seed_fixture import QA_SCENARIOS, REVIEW_SKILL, seed
from tests.projectfiles import write_config, write_config_file

TCW_ENV = {**os.environ, "TCW_NO_PERSONAL_CONFIG": "1"}


def _tcw(root, *args, stdin="") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", *args],
                          cwd=str(root), capture_output=True, text=True,
                          input=stdin, env=TCW_ENV)


def _stage(root, slug) -> str:
    return json.loads(_tcw(root, "work", "show", slug, "--json").stdout)[
        "item"]["stage"]


@pytest.fixture(scope="module")
def control(tmp_path_factory):
    root = tmp_path_factory.mktemp("control") / "p"
    return root, seed(root)


@pytest.fixture(scope="module")
def customized(tmp_path_factory):
    root = tmp_path_factory.mktemp("customized") / "p"
    return root, seed(root, "customized")


@pytest.fixture(scope="module")
def bare(tmp_path_factory):
    root = tmp_path_factory.mktemp("bare") / "p"
    return root, seed(root, "bare")


@pytest.fixture
def control_copy(control, tmp_path):
    """A copy of the control fixture a test may change. The slugs and paths
    the CLI prints are relative to wherever the copy lives, so the manifest
    still applies."""
    root, manifest = control
    copy = tmp_path / "p"
    shutil.copytree(root, copy, symlinks=True)
    return copy, manifest


def test_the_bare_variant_is_a_repository_that_does_not_use_tcw(bare):
    """For a case about setting TCW up in a fresh repository."""
    root, manifest = bare
    assert (root / ".git").is_dir()
    assert (root / "src/reports.py").is_file(), "the code files are there"
    assert not (root / ".tcw/tcw-config.yaml").exists()
    assert manifest["variant"] == "bare"
    assert manifest["items"] == {}
    assert manifest["nonces"] == {}
    assert manifest["stage_items"] == {}
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    assert manifest["seeded_head"] == head
    assert _tcw(root, "validate").returncode != 0
    verdict = grade.p_files_changed_exactly(
        {"fixture": root, "seeded_head": manifest["seeded_head"]}, paths=[])
    assert verdict["passed"], verdict["evidence"]


def test_a_bare_fixture_inside_a_tcw_project_is_refused(tmp_path):
    """`tcw` looks for `tcw-config.yaml` in every parent folder. A bare fixture
    under a TCW project, such as the runner's default `eval-runs/` inside this
    checkout, would resolve to that project and stop being a repository that
    does not use TCW."""
    write_config(tmp_path, "id: outer\n")
    with pytest.raises(ValueError, match="tcw-config.yaml"):
        seed(tmp_path / "runs" / "fixture", "bare")
    assert not (tmp_path / "runs").exists(), "refused before building anything"


@pytest.mark.parametrize("variant", ["control", "customized", "bare"])
def test_a_folder_that_is_not_empty_is_refused(variant, tmp_path):
    """Re-seeding a used folder, as `run_one` does when `--out` is reused,
    would commit whatever was left there into the seeded commit."""
    dest = tmp_path / "used"
    dest.mkdir()
    write_config(dest, "id: left-over\n")
    with pytest.raises(ValueError, match="not empty"):
        seed(dest, variant)
    assert sorted(p.name for p in dest.iterdir()) == ["tcw-config.yaml"], (
        "refused before writing anything")


def test_an_unknown_variant_is_refused(tmp_path):
    with pytest.raises(ValueError, match="nonsense"):
        seed(tmp_path / "x", "nonsense")
    assert not (tmp_path / "x").exists(), "refused before building anything"


def test_the_seeder_writes_no_builtin_binding():
    """TCW 3.0 refuses `builtin:` in a configuration file; `inherit: true` is
    how a list keeps TCW's own text. The word has no business in the seeder at
    all, so a stray one is caught before it reaches a fixture."""
    source = (Path(grade.__file__).with_name("seed_fixture.py")
              .read_text(encoding="utf-8"))
    assert "builtin" not in source


# --- the project itself ----------------------------------------------------

@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_seeded_project_validates(variant, request):
    root, _ = request.getfixturevalue(variant)
    result = _tcw(root, "validate")
    assert result.returncode == 0, result.stderr


def test_the_customized_project_keeps_tcw_s_own_text_with_inherit(customized):
    """Every bound stage but postmortem composes after TCW's own text, which
    is what `inherit: true` asks for. Read back through `tcw work lifecycle`
    so the check is the CLI's reading of the file, not the seeder's intent."""
    root, _ = customized
    stages = {s["name"]: s["bindings"]["prompt"] for s in json.loads(
        _tcw(root, "work", "lifecycle", "--json").stdout)["stages"]}
    for name in ("spec", "plan", "implement", "review", "qa"):
        assert stages[name][0] == {"builtin": True}, (name, stages[name])
        assert len(stages[name]) == 2, (name, stages[name])
    assert stages["postmortem"] == [{"blob": ""}]


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_every_stage_case_has_an_item_at_that_stage(variant, request):
    """An axis A case works one stage of one item, so the item has to be at
    that stage — except postmortem, a side stage worked on an item that has
    already ended. Without this a case would address an item with nothing to
    work, and the failure would surface as an agent that produced nothing."""
    root, manifest = request.getfixturevalue(variant)
    for stage, slug in manifest["stage_items"].items():
        want = "completed" if stage == "postmortem" else stage
        assert _stage(root, slug) == want, (variant, stage, slug)


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_inbox_item_waits_at_inbox(variant, request):
    """Cases B2 and B13 act on an arrival nobody has decided on yet."""
    root, manifest = request.getfixturevalue(variant)
    slug = manifest["items"]["inbox"]
    assert _stage(root, slug) == "inbox"
    request_text = json.loads(_tcw(root, "work", "show", slug, "--json")
                              .stdout)["request"]
    assert "eight seconds" in request_text
    assert "import" not in request_text, (
        "B13's new fact must not already be in the request")


def test_the_closeout_item_is_refused_until_its_record_exists(control_copy):
    """Case B3 asks an agent to move the closeout item into review. That is
    only a measurement while the move is refused for want of the capability
    record, and allowed once the record is added with a real status — and
    still refused when it is added at the default, `Missing`."""
    root, manifest = control_copy
    slug = manifest["items"]["closeout"]
    assert _stage(root, slug) == "implement"

    refused = _tcw(root, "work", "advance", slug, "--dry-run")
    assert refused.returncode == 3, refused.stderr
    assert "billing/download-invoice" in refused.stderr

    added = _tcw(root, "capabilities", "add", "billing/download-invoice",
                 stdin="An account holder downloads an invoice.\n")
    assert added.returncode == 0, added.stderr
    still = _tcw(root, "work", "advance", slug, "--dry-run")
    assert still.returncode == 3, "a record left Missing passed the gate"

    flipped = _tcw(root, "capabilities", "set", "billing/download-invoice",
                   "--status", "Supported")
    assert flipped.returncode == 0, flipped.stderr
    allowed = _tcw(root, "work", "advance", slug, "--dry-run")
    assert allowed.returncode == 0, allowed.stderr
    assert allowed.stdout.strip() == "review"


def test_the_qa_item_carries_a_qa_plan_and_waits_for_a_verdict(control_copy):
    """Cases A6 and A7 work qa on this item. It must carry a QA plan comment
    naming every scenario the grader looks for, and its move out of qa must
    wait for a round — one whose `judges` is 1, the item's only implement
    round, which is the value the round checks expect."""
    root, manifest = control_copy
    slug = manifest["items"]["qa"]
    assert manifest["qa_scenarios"] == list(QA_SCENARIOS)
    comments = json.loads(_tcw(root, "work", "show", slug, "--json")
                          .stdout)["comments"]
    plans = [c["text"] for c in comments
             if c["text"].splitlines()[0].strip() == "QA plan"]
    assert len(plans) == 1
    for scenario in QA_SCENARIOS:
        assert scenario in plans[0]

    assert _tcw(root, "work", "advance", slug, "--dry-run").returncode == 3
    qa_round = Path(_tcw(root, "work", "path", slug, "qa", "--next")
                    .stdout.strip())
    qa_round.parent.mkdir(parents=True, exist_ok=True)
    write_config_file(qa_round, "---\nverdict: accepted\njudges: 1\n---\n\nQA-1 passed\n")
    allowed = _tcw(root, "work", "advance", slug, "--dry-run")
    assert allowed.returncode == 0, allowed.stderr


def test_the_review_item_has_one_implement_round_to_judge(control):
    """Case A4's round check expects `judges: 1`."""
    root, manifest = control
    slug = manifest["items"]["review"]
    folder = Path(_tcw(root, "work", "path", slug, "implement").stdout.strip())
    assert [n for n, _ in grade.rounds(folder)] == [1]
    assert not grade.rounds(Path(_tcw(root, "work", "path", slug, "review")
                                 .stdout.strip()))


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_completed_item_carries_a_defect_found_after_acceptance(
        variant, request):
    """Cases A5 and B9 ask for a postmortem, which needs something to find."""
    root, manifest = request.getfixturevalue(variant)
    slug = manifest["items"]["completed"]
    assert _stage(root, slug) == "completed"
    shown = json.loads(_tcw(root, "work", "show", slug, "--json").stdout)
    assert any("Defect found after acceptance" in c["text"]
               for c in shown["comments"])
    postmortem = Path(_tcw(root, "work", "path", slug, "postmortem")
                      .stdout.strip())
    assert not postmortem.exists(), "no postmortem is seeded"


@pytest.mark.parametrize("variant", ["control", "customized", "bare"])
def test_a_freshly_seeded_project_shows_no_changes(variant, request):
    """`files_changed_exactly` compares the working tree with `seeded_head` and
    counts untracked files. Anything the seeder leaves behind uncommitted, such
    as `manifest.json`, would otherwise be charged to every agent — and so would
    the bytecode and pytest caches an agent leaves just by importing or testing
    the fixture's code."""
    root, manifest = request.getfixturevalue(variant)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    assert manifest["seeded_head"] == head
    caches = [root / "src/__pycache__/reports.cpython-314.pyc",
              root / ".pytest_cache/v/cache/lastfailed"]
    for cache in caches:
        cache.parent.mkdir(parents=True, exist_ok=True)
        write_config_file(cache, b"\0cache")
    try:
        verdict = grade.p_files_changed_exactly(
            {"fixture": root, "seeded_head": manifest["seeded_head"]}, paths=[])
    finally:
        for cache in caches:
            cache.unlink()
    assert verdict["passed"], verdict["evidence"]


@pytest.mark.parametrize("variant", ["control", "customized"])
def test_the_project_declares_documentation_entries(variant, request):
    """Case B10 asks an agent to close out a code change against a project that
    declares documentation entries. A project declaring none gives it nothing
    to act on, and `tcw work docs` says exactly that rather than failing, so
    the case would have graded against an empty trigger set."""
    root, _ = request.getfixturevalue(variant)
    result = _tcw(root, "work", "docs")
    assert result.returncode == 0, result.stderr
    assert "README.md" in result.stdout
    assert "docs/changelogs/upcoming.md" in result.stdout
    # The entries have to name files that exist, or the agent has nothing to edit.
    assert (root / "README.md").is_file()
    assert (root / "docs/changelogs/upcoming.md").is_file()


def test_no_capability_is_seeded_missing(control):
    """3.0 adds a capability record during implement with the status it then
    has. A record seeded `Missing` would teach the 2.x habit the B3 and B8
    cases exist to measure the absence of."""
    root, _ = control
    paths = _tcw(root, "capabilities", "list").stdout.split()
    assert paths == ["reports/view"]
    for path in paths:
        assert "Status: Missing" not in _tcw(root, "capabilities", "show",
                                             path).stdout


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
    # Composed after TCW's own text, not in place of it.
    assert f"# Stage: {stage}" in result.stdout


@pytest.mark.parametrize("kind,stage", NONCE_STAGES)
def test_the_control_carries_no_nonce(kind, stage, customized, control):
    """The control is a project that configured nothing, so its stages print
    TCW's own text. A nonce appearing here would mean it came from somewhere
    other than the binding."""
    croot, cmanifest = control
    _, manifest = customized
    result = _tcw(croot, "work", "stage", "prompt", stage,
                  cmanifest["stage_items"][stage])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
    assert manifest["nonces"][kind] not in result.stdout


def test_the_skill_binding_resolves_to_a_pointer_and_not_a_body(
        customized, control):
    """A `skill` binding prints `Invoke the <name> skill.` and never reads the
    named skill. Asserted rather than assumed, because case A4 reads exactly
    this line, and the control must not carry it."""
    pointer = f"Invoke the {REVIEW_SKILL} skill."
    root, manifest = customized
    result = _tcw(root, "work", "stage", "prompt", "review",
                  manifest["stage_items"]["review"])
    assert pointer in result.stdout
    croot, cmanifest = control
    assert pointer not in _tcw(croot, "work", "stage", "prompt", "review",
                               cmanifest["stage_items"]["review"]).stdout


def test_the_person_decides_binding_reaches_qa_only_when_customized(
        customized, control):
    """Case A7 depends on the qa prompt saying a person decides; case A6
    depends on the control's qa prompt not saying it."""
    marker = "a person decides the qa verdict"
    root, manifest = customized
    assert marker in _tcw(root, "work", "stage", "prompt", "qa",
                          manifest["stage_items"]["qa"]).stdout
    croot, cmanifest = control
    control_qa = _tcw(croot, "work", "stage", "prompt", "qa",
                      cmanifest["stage_items"]["qa"]).stdout
    assert "# Stage: qa" in control_qa
    assert marker not in control_qa


def test_the_generate_script_survives_having_no_work_item(customized):
    """The payload's `item` is null when the prompt is read without an item.
    An unguarded script raises there, and a raise produces no stdout at all —
    which the harness would read as the instructions not reaching the agent
    rather than as a broken fixture."""
    root, _ = customized
    result = _tcw(root, "work", "stage", "prompt", "implement")
    assert result.returncode == 0, result.stderr
    assert "TCW_EVAL_NO_ITEM" in result.stdout


def test_the_silence_opt_out_is_silent_against_a_speaking_control(
        customized, control):
    """The only form of this contrast that is not vacuous.

    Asserting "no project instruction appears" would pass in the control too,
    because the control has no project instructions anywhere — the never-fails
    shape the mutation rule exists to catch. What actually differs is that the
    customized project resolves `postmortem` to nothing at all, while the
    control prints TCW's own text with its header.
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
    assert grade.PROMPT_HEADER in floor.stdout
    assert "# Stage: postmortem" in floor.stdout


def test_the_manifest_records_what_grading_cannot_guess(customized):
    root, manifest = customized
    on_disk = json.loads((root / "manifest.json").read_text())
    assert on_disk == manifest
    assert set(manifest["nonces"]) == {"file", "blob", "generate"}
    assert all(len(n) == 16 for n in manifest["nonces"].values())
    # Every minted slug, because they carry today's date.
    assert set(manifest["items"]) == {
        "inbox", "spec", "plan", "implement", "closeout", "review", "qa",
        "completed"}
    assert set(manifest["stage_items"]) == {
        "spec", "plan", "implement", "review", "qa", "postmortem"}
