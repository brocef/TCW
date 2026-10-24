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
from bisect import bisect_right
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
    end: int         # clamped to that line, for a match that runs onto the next
    text: str        # what matched
    reason: str


# A line that starts a table row, a list item or a heading starts a block of
# its own, so nothing on the line before it joins it. A table row and a
# heading are one line each in Markdown, so nothing after them joins either.
_STARTS_BLOCK = re.compile(r"[ \t]*(\||[-*+][ \t]|[-*+]$|\d+[.)]([ \t]|$)|#)")
_ONE_LINE = re.compile(r"[ \t]*(\||#)")
_FENCE = re.compile(r"[ \t]*```")


def blocks(text: str) -> list[list[tuple[int, str]]]:
    """`text` cut into blocks of `(line number, line)`, the lines Markdown
    joins into one paragraph, so a phrase or a code span wrapped across a line
    break is read whole (pre-freeze clean-up, Designs 11 and 16).

    A block ends at a blank line and at a fenced code block's fence, and before
    a line that starts a table row (`|`), a list item (`-`, `*`, `+`, or a
    number followed by `.` or `)`) or a heading (`#`), so nothing can reach
    from one table row, list item or heading into the next. A fence line, and
    each line inside a fenced block, is a block of its own: code is read line
    by line, as it always was. So is a table row or a heading, which Markdown
    never continues onto the next line."""
    out: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        fence = bool(_FENCE.match(line))
        if fence or fenced or not line.strip() or _STARTS_BLOCK.match(line):
            if current:
                out.append(current)
            current = []
        if fence:
            fenced = not fenced
        if fence or fenced or _ONE_LINE.match(line):
            out.append([(number, line)])
        elif line.strip():
            current.append((number, line))
    if current:
        out.append(current)
    return out


def joined(block: list[tuple[int, str]]) -> tuple[str, list[tuple[int, int, int]]]:
    """The block's lines as one string, each line break read as one space and
    a continuation line's indentation dropped, as Markdown reads them; and for
    each line `(offset in the string, line number, columns dropped)`."""
    parts, where, at = [], [], 0
    for index, (number, line) in enumerate(block):
        text = line.rstrip()
        dropped = 0
        if index:
            stripped = text.lstrip()
            dropped = len(text) - len(stripped)
            text = stripped
            parts.append(" ")
            at += 1
        where.append((at, number, dropped))
        parts.append(text)
        at += len(text)
    return "".join(parts), where


def scan(text: str, patterns=PATTERNS) -> list[Hit]:
    """Every match of every pattern in `text`, read a block at a time (see
    `blocks`), so a phrase wrapped across a line break is found. Each hit is
    reported at the line where it starts, with its columns in that line and
    its end clamped to that line, ordered as a line-by-line scan orders them:
    by line, then pattern, then column."""
    compiled = [(re.compile(p, re.IGNORECASE), why) for p, why in patterns]
    lines = text.splitlines()
    found = []
    for block in blocks(text):
        whole, where = joined(block)
        offsets = [at for at, _, _ in where]
        for order, (regex, why) in enumerate(compiled):
            for m in regex.finditer(whole):
                at, number, dropped = where[bisect_right(offsets, m.start()) - 1]
                width = len(lines[number - 1])
                start = min(m.start() - at + dropped, width)
                end = min(m.end() - at + dropped, width)
                found.append((number, order, start,
                              Hit(number, start, end, m.group(0), why)))
    return [hit for *_, hit in sorted(found, key=lambda f: f[:3])]


def without_chdir(tokens: list[str]) -> list[str]:
    """`tokens` after each leading `-C <target>` (TCW-114 Design 4.1). The
    target is one token, so a placeholder written as a phrase is read as
    the command and fails (`chdir_problem`)."""
    while len(tokens) >= 2 and tokens[0] == "-C":
        tokens = tokens[2:]
    return tokens


def chdir_problem(tokens: list[str]) -> str | None:
    """Why the `-C` targets at the start of `tokens` are not one token each:
    what follows the last of them must be the command group."""
    rest = without_chdir(tokens)
    if rest is not tokens and rest and not re.match(r"[a-z][a-z0-9-]*$", rest[0]):
        return f"tcw -C takes one token as its target, not a phrase: {rest[0]}"
    return None
