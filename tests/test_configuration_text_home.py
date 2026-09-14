"""Declaring a setting is `tcw-configure`'s text, and it must match the CLI.

`skills/tcw-configure/references/` is where every "how to declare or change a
setting" lives; the usage skills keep only what a setting does at runtime. This
guards the one place a later change already put declaring text back into
`tcw-work` (tracker inheritance, v2.1.3), and left `tracker.md` saying every
key is required in a node's own block, which inheritance made untrue.

Text is compared with whitespace collapsed, so a sentence still matches after
it is rewrapped.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACKER = REPO / "skills/tcw-configure/references/tracker.md"
COMMANDS = REPO / "skills/tcw-work/references/commands.md"
ROUTER = REPO / "skills/tcw-configure/SKILL.md"

# The declaring rules for tracker inheritance, as `tracker.md` states them. Each
# must be in `tracker.md` and in no form in `tcw-work`'s `commands.md`.
DECLARING_RULES = (
    "tracker: {}",                      # a node with no tracker
    "same file as `base-url`",          # where credentials must come from
    "without a board",                  # where shared settings go
    "once the node's block is merged",  # what "required" means after inheritance
)


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def test_tracker_inheritance_is_declared_in_tcw_configure():
    text = _flat(TRACKER)
    for wanted in DECLARING_RULES:
        assert wanted in text, f"tracker.md does not say: {wanted!r}"
    # The true null rule, checked in `merge_tracker_blocks`: a nearer null does
    # not delete an inherited value, it lets the farther one through.
    assert "a nearer `null` lets the farther value through" in text, (
        "tracker.md no longer says a nearer null lets the farther value through")
    # An ancestor's empty block is skipped, so only the node writing it goes
    # without a tracker.
    assert "child projects still inherit" in text, (
        "tracker.md does not say tracker: {} leaves child projects inheriting")
    assert "All but the last are required. Unknown" not in text, (
        "tracker.md still says every key is required in the node's own block")


def test_tcw_work_keeps_only_the_runtime_tracker_text():
    text = _flat(COMMANDS)
    for moved in (*DECLARING_RULES, "Settings inherit from parent nodes"):
        assert moved not in text, (
            f"commands.md carries declaring text that belongs in tracker.md: {moved!r}")
    assert "A problem names the file its value came from" in text


def test_sharing_tracker_settings_routes_to_tracker_md():
    row = next(line for line in ROUTER.read_text(encoding="utf-8").splitlines()
               if "(references/tracker.md)" in line)
    assert "parent" in row, row
