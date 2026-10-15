"""The 2.x vocabulary no 3.0 document may use (TCW-75 spec, acceptance
criterion 2; TCW-74 spec, Design 6.5).

One table, imported by every test that scans for it, so the slices' lists
cannot drift apart: TCW-74's scan of the shipped skills, agents, prompts and
procedures (`tests/test_shipped_text.py`), and TCW-75's scan of the README and
guides. Each entry is a regular expression, matched case-insensitively,
Markdown code included, and the reason it goes.

`builtin: true` is deliberately not here: `tcw config show` prints it for a
built-in entry, so TCW-75's documents show it in that output (TCW-75 spec,
criterion 2). TCW-74's own scan adds it, with its other extra patterns.
"""

import re
from typing import NamedTuple

PATTERNS: tuple[tuple[str, str], ...] = (
    (r"tcw work (start|submit|rework|complete|drop|inbox|tracker|delegate|escalate"
     r"|reconcile|nodes|tombstone|delete|scaffold)\b",
     "removed or merged commands (TCW-73)"),
    (r"stage gate|stage validate|taxonomy init|capabilities init|taxonomy check"
     r"|capabilities check",
     "removed or merged commands (TCW-73)"),
    (r"graveyard|dod\.yaml|definition of done|renames\.yaml",
     "removed store files (TCW-70)"),
    (r"state\.yaml|tracker\.yaml|intake\.md|initial-request\.md|refined-outcome\.md"
     r"|rework\.md|\boutcome\.md",
     "2.x item files (TCW-70)"),
    (r"work\.lifecycle|work\.tracker|auto-commit-transitions|publish-transitions"
     r"|trunk-branch|work\.retain",
     "removed keys (TCW-69)"),
    (r"connected-projects|connected-project-registry",
     "renamed to `projects` and `project-registry` (TCW-73; owner, 2026-10-01)"),
    (r"TCW_NODE_ROOT|TCW_STATUS|TCW_TRANSITION|TCW_RESOLUTION|TCW_WORK_OWNER",
     "removed variables (TCW-69, TCW-72)"),
    (r"--worktree|--initiative|--epic|--resolution",
     "removed flags (TCW-73)"),
    (r"docs/work/(inbox|backlog|active|review|completed|discarded)/",
     "status folders (TCW-70)"),
    (r"spec/capabilities\.yaml",
     "wrong location (TCW-69 Design 4.4)"),
    (r"\bnodes?\b(?!\.js)",
     'renamed to "project" (TCW-73)'),
    (r"\bno longer\b|\bpreviously\b|\bsince 3\.0\b",
     "a document describing a difference from 2.x"),
    (r"\b(never|does not|doesn't) runs? git\b",
     'false: TCW reads git and `provision` clones; the rule is "never changes '
     'git state" (review decision R4)'),
)


class Hit(NamedTuple):
    line: int        # 1-based
    start: int       # column of the match in that line
    end: int
    text: str        # what matched
    reason: str


def scan(text: str, patterns=PATTERNS) -> list[Hit]:
    """Every match of every pattern in `text`, by line."""
    compiled = [(re.compile(p, re.IGNORECASE), why) for p, why in patterns]
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        for regex, why in compiled:
            for m in regex.finditer(line):
                hits.append(Hit(number, m.start(), m.end(), m.group(0), why))
    return hits
