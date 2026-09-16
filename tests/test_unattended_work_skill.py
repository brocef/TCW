"""`tcw-extras-autonomous-work` mandates no advisor, review, closeout or version
policy of its own: those come from `tcw work procedure prompt unattended-work`,
whose shipped default is TCW's practice. The skill body keeps only what a
project's replacement must still honor.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "tcw-extras-autonomous-work" / "SKILL.md"
COMMAND = "tcw work procedure prompt unattended-work"


def _split():
    """(frontmatter, body) of the skill."""
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.index("\n---\n", 3)
    return text[4:end], text[end + len("\n---\n"):]


def _front_line(key):
    front, _ = _split()
    return next((l for l in front.splitlines() if l.startswith(f"{key}:")), "")


def test_the_body_names_no_advisor_review_agent_closeout_or_version_policy():
    """Epic criterion 8, over the body only: criterion 9 requires the
    frontmatter to declare the default's tools, which names them."""
    _, body = _split()
    named = re.findall(
        r"\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b",
        body, flags=re.IGNORECASE)
    assert not named, f"the skill body still names {sorted(set(named))}"
    for phrase in ("majority of two", "git push", "upcoming.md"):
        assert phrase not in body, f"the skill body still mandates {phrase!r}"


def test_the_body_says_what_an_advisor_must_be_and_how_many():
    """Epic criterion 9: a project replacing the default knows what its
    replacement has to supply, and the weighing rule holds for any count."""
    _, body = _split()
    assert re.search(r"^## What an advisor must be", body, flags=re.MULTILINE)
    lowered = " ".join(body.lower().split())
    assert "read-only" in lowered
    assert "two advisors are wanted" in lowered
    assert "weighed, never counted" in lowered


def test_the_procedure_is_injected_and_its_tools_are_declared():
    """An injected command that is not pre-approved aborts the whole skill, and
    one that exits non-zero blanks it; the frontmatter declares what TCW's
    default needs and says a replacement may need other tools."""
    _, body = _split()
    assert f"!`{COMMAND} || true`" in body.splitlines()
    allowed = _front_line("allowed-tools")
    for tool in ("Bash(tcw *)", "Bash(codex *)", "Agent", "SendMessage"):
        assert tool in allowed, f"allowed-tools does not declare {tool}"
    assert "work.procedures.unattended-work" in _front_line("compatibility")


def test_the_manual_fallback_names_the_command():
    """Epic criterion 11: a harness that runs no injected commands is told what
    to run."""
    _, body = _split()
    sections = re.split(r"^## ", body, flags=re.MULTILINE)
    last = sections[-1]
    assert last.startswith("Document command summary"), \
        "the skill does not end with its manual fallback block"
    assert COMMAND in last
