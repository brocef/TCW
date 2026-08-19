"""A node that configures nothing must see byte-identical stage instructions.

The baseline in `tests/fixtures/prompt_fallback/` was captured from the CLI
**before** documentation entries could reach a prompt, in its own commit. That
ordering is the whole value: the expected bytes could not be edited into
agreement with a regression without the edit showing up in the diff as a fixture
change.

It passes trivially on the tree it was captured from. That is the point — it is a
tripwire armed ahead of the change, not a description of it.

The `spec` and `plan` entries were **re-baselined once**, by
`2026-08-19-name-the-item-s-actual-body-artifact-in-the-builtin-spec-and-plan-stage-prompts`,
which rewrote those two prompts to name the item's own body artifact. Only those
two stdouts were replaced, and only after asserting the other four were
byte-identical — so what this fixture still proves about the documentation
substitution is intact. A prompt rewrite is the one reason to touch these bytes;
a *substitution* changing them is the regression, and re-baselining to hide that
is the thing the file exists to prevent.
"""

import json
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "prompt_fallback"
BASELINE = json.loads((FIXTURES / "unconfigured.json").read_text(encoding="utf-8"))

# Mirrors capture.py; duplicated rather than imported so a change to the capture
# script cannot silently redefine what the replay checks.
WALK = [("request", "backlog"), ("spec", "backlog"), ("plan", "backlog"),
        ("implement", "active"), ("verify", "review"), ("postmortem", "review")]
INTO = {"active": "start", "review": "submit"}


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    root = tmp_path_factory.mktemp("fallback") / "unconfigured"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(root), "config", k, v], check=True)
    subprocess.run(["tcw", "init", "--id", "fallback", "work"], cwd=root,
                   capture_output=True, check=True, stdin=subprocess.DEVNULL)
    slug = subprocess.run(["tcw", "work", "new", "Baseline item"], cwd=root,
                          capture_output=True, text=True, check=True,
                          stdin=subprocess.DEVNULL).stdout.strip()

    out, current = {}, "backlog"
    for stage, status in WALK:
        if status != current:
            subprocess.run(["tcw", "work", INTO[status], slug], cwd=root,
                           capture_output=True, check=True,
                           stdin=subprocess.DEVNULL)
            current = status
        r = subprocess.run(["tcw", "work", "stage", stage, slug], cwd=root,
                           capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        out[stage] = {"returncode": r.returncode, "stdout": r.stdout,
                      "stderr": r.stderr}
    return out


@pytest.mark.parametrize("expected", BASELINE, ids=lambda e: e["argv"][2])
def test_an_unconfigured_node_sees_the_recorded_bytes(expected, replayed):
    stage = expected["argv"][2]
    actual = replayed[stage]
    assert actual["returncode"] == expected["returncode"]
    assert actual["stdout"] == expected["stdout"], (
        f"stage '{stage}' output changed for a node that configures nothing")


def test_the_baseline_covers_the_two_prompts_that_will_change():
    """Guards the fixture itself: if the corpus ever stopped covering `plan` and
    `implement`, the tripwire would pass while protecting nothing."""
    covered = {e["argv"][2] for e in BASELINE}
    assert {"plan", "implement"} <= covered


def test_the_documentation_sentence_is_where_the_spec_says_it_is():
    """The fallback text this item preserves lives in exactly two prompts.
    Recorded so that 'byte-identical' has a named subject rather than being a
    claim about opaque bytes."""
    carrying = {e["argv"][2] for e in BASELINE if "Documentation Sync" in e["stdout"]}
    assert carrying == {"plan", "implement"}
