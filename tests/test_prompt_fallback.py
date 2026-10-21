"""A project that configures nothing must see byte-identical stage instructions.

The baseline in `tests/fixtures/prompt_fallback/` was captured from the CLI in
a commit of its own. That ordering is the whole value: the expected bytes could
not be edited into agreement with a regression without the edit showing up in
the diff as a fixture change.

It passes trivially on the tree it was captured from. That is the point: it is
a tripwire armed ahead of later changes, not a description of them.

The recorded bytes normalize the item's slug to `<slug>`, and the replay
normalizes the same way, because the header and footer quote the slug and a
slug carries the date it was created.

**Re-captured by TCW-74**, which rewrote every prompt for the 3.0 stages and
added the generated footer. That moved the text deliberately, so the 2.x bytes
would have asserted something false. A prompt rewrite is the one reason to
touch these bytes; a *substitution* changing them is the regression, and
re-baselining to hide that is what this file exists to prevent.

**Re-captured again by TCW-76**, for one paragraph only: TCW-74's review fixes
(`e411e681`) added "Who reviews" to the review prompt after the capture, and
the recorded bytes were never brought up to it. Nothing else moved.

**Re-captured again by TCW-101**, for two passages it added on purpose: the
spec prompt's "The requester revises the request" bullet, and the plan
prompt's step 6 on filing a part into another project. A diff of the old and
new bytes showed nothing else moved.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "prompt_fallback"
BASELINE = json.loads((FIXTURES / "unconfigured.json").read_text(encoding="utf-8"))

# Mirrors capture.py; duplicated rather than imported so a change to the capture
# script cannot silently redefine what the replay checks.
STAGES = ["inbox", "request", "spec", "plan", "implement", "review", "qa",
          "postmortem"]


@pytest.fixture(scope="module")
def replayed(tmp_path_factory):
    scratch = tmp_path_factory.mktemp("fallback")
    env = {**os.environ, "HOME": str(scratch / "home"),
           "XDG_CONFIG_HOME": str(scratch / "home" / "xdg"),
           "TCW_NO_PERSONAL_CONFIG": "1"}
    root = scratch / "unconfigured"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["tcw", "init", "--id", "fallback", "work"], cwd=root,
                   capture_output=True, check=True, stdin=subprocess.DEVNULL,
                   env=env)
    slug = subprocess.run(["tcw", "work", "new", "Baseline item"], cwd=root,
                          capture_output=True, text=True, check=True,
                          stdin=subprocess.DEVNULL, env=env).stdout.strip()
    out = {}
    for stage in STAGES:
        reference = [] if stage == "inbox" else [slug]
        r = subprocess.run(["tcw", "work", "stage", "prompt", stage, *reference],
                           cwd=root, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, env=env)
        out[stage] = {"returncode": r.returncode,
                      "stdout": r.stdout.replace(slug, "<slug>"),
                      "stderr": r.stderr.replace(slug, "<slug>")}
    return out


@pytest.mark.parametrize("expected", BASELINE, ids=lambda e: e["argv"][3])
def test_an_unconfigured_project_sees_the_recorded_bytes(expected, replayed):
    stage = expected["argv"][3]
    actual = replayed[stage]
    assert actual["returncode"] == expected["returncode"] == 0
    assert actual["stdout"] == expected["stdout"], (
        f"stage '{stage}' output changed for a project that configures nothing")


def test_the_baseline_covers_every_stage_with_a_prompt():
    """Guards the fixture itself: a corpus that stopped covering a stage would
    pass while protecting nothing."""
    from tcw.work.model import STAGES as TABLE
    assert [e["argv"][3] for e in BASELINE] == [s.name for s in TABLE if s.prompt]


def test_the_documentation_sentence_is_where_the_spec_says_it_is():
    """The fallback text of the documentation span lives in exactly two
    prompts. Recorded so that 'byte-identical' has a named subject."""
    carrying = {e["argv"][3] for e in BASELINE if "Documentation Sync" in e["stdout"]}
    assert carrying == {"plan", "implement"}
