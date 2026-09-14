"""Declaring a setting is `tcw-configure`'s text, and it must match the CLI.

`skills/tcw-configure/references/` is where every "how to declare or change a
setting" lives; the usage skills keep only what a setting does at runtime. This
guards the one place a later change already put declaring text back into
`tcw-work` (tracker inheritance, v2.1.3), and left `tracker.md` saying every
key is required in a node's own block, which inheritance made untrue.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACKER = REPO / "skills/tcw-configure/references/tracker.md"
COMMANDS = REPO / "skills/tcw-work/references/commands.md"
ROUTER = REPO / "skills/tcw-configure/SKILL.md"


def test_tracker_inheritance_is_declared_in_tcw_configure():
    text = TRACKER.read_text(encoding="utf-8")
    for wanted in ("tracker: {}",                     # how a node has no tracker
                   "same file as `base-url`",          # the credentials rule
                   "without a board",                  # where shared settings go
                   "once the node's block is merged"):  # what "required" means now
        assert wanted in text, f"tracker.md does not say: {wanted!r}"
    assert "All but the last are required. Unknown" not in text, (
        "tracker.md still says every key is required in the node's own block")


def test_tcw_work_keeps_only_the_runtime_tracker_text():
    text = COMMANDS.read_text(encoding="utf-8")
    assert "Settings inherit from parent nodes" not in text
    assert "must come from the same file as `base-url`" not in text
    assert "A problem names the file its value came from" in text


def test_sharing_tracker_settings_routes_to_tracker_md():
    row = next(line for line in ROUTER.read_text(encoding="utf-8").splitlines()
               if "(references/tracker.md)" in line)
    assert "parent" in row, row
