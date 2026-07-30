"""Every `tcw` verb and flag named in the docs actually exists in the CLI.

The defect this catches shipped three times undetected: `tcw work
audit-work-backlog`, `tcw work consolidate-plans --apply --delete`, and `tcw work
edit --pr` were all documented in `README.md` and the agent-facing
`skills/tcw-work/references/commands.md` without ever existing. Two of them were
AI-driven workflows that live as slash commands, written up as if they were CLI
subcommands; the third was pure invention.

Agent-facing docs are the worst place for this: an agent reads `commands.md`,
runs the verb, and gets an argparse error instead of the workflow.

Scope, files: every Markdown file git knows about — tracked or merely untracked
and not ignored — except the archival trees named in `ARCHIVAL`. Derived by
exclusion on purpose: an inclusion list is a scope that can be got wrong, and
this one was, twice. A new documentation tree is covered the moment the file
exists, with no edit here.

Scope, parsing: this parses `tcw`-prefixed invocations out of backtick spans and
fenced blocks. Prose that describes a command without writing it out slips past,
so a green run means "names no nonexistent verb", not "the docs are correct".
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Documents that record what was true at a point in time, and are therefore
# expected to name commands that no longer exist. Trailing slashes are
# load-bearing: without one, `docs/work/` would also swallow the live
# `docs/work-inbox-template.md`.
ARCHIVAL = (
    "docs/work/",           # lifecycle artifacts, frozen once written
    "docs/plan/",           # the retired build-phase specs
    "docs/superpowers/",    # archived specs and plans from a prior workflow
    "docs/changelogs/",     # historical entries, correct as of their version
    "docs/release-notes/",  # same
)


def _doc_files() -> list[Path]:
    """Every non-archival Markdown file, per git.

    git rather than `rglob` for three reasons: `.gitignore` already declares what
    is not source (`node_modules/`, `.venv/`, build output, the gitignored
    `docs/work/completed/`), so the exclusions above stay a short list of
    *archives* rather than growing a second list of *junk*; `--others` keeps a
    brand-new unstaged doc in scope, which is what makes "a new tree is covered
    immediately" literally true; and the `plugins/tcw` symlink back to the repo
    root is one index entry to git rather than an infinite tree.
    """
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files",
         "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"],
        capture_output=True, text=True, check=True,
    ).stdout
    # Repo-relative POSIX paths, so matching does not depend on the invoking cwd.
    return sorted(REPO / p for p in out.split("\0")
                  if p and not p.startswith(ARCHIVAL))


DOC_FILES = _doc_files()

BACKTICKED = re.compile(r"`([^`\n]*\btcw\b[^`\n]*)`")
FENCE = re.compile(r"^```.*?^```", re.M | re.S)
WORD = re.compile(r"[a-z][a-z0-9-]*$")
FLAG = re.compile(r"--[a-z][a-z-]*")


def _invocations(text: str) -> list[str]:
    """Every documented `tcw …` command, from backticks and fenced blocks alike.

    Fenced blocks matter as much as backticks: README's command reference is one,
    and two of the three phantom verbs this test exists for live there.
    """
    found = BACKTICKED.findall(text)
    for block in FENCE.findall(text):
        for line in block.splitlines()[1:-1]:
            line = line.split("#", 1)[0].strip()      # drop trailing comments
            if line.startswith("tcw "):
                found.append(line)
    return found


def _help(argv: list[str]) -> str:
    """`--help` text, or "" when the command path doesn't exist."""
    r = subprocess.run(["tcw", *argv, "--help"], capture_output=True, text=True)
    return r.stdout + r.stderr if r.returncode == 0 else ""


def _subcommands(text: str) -> list[str]:
    """The subcommand names in a `--help`, or [] for a leaf command.

    argparse spells subparser choices `{a,b,c}` in the usage line's positional
    slot — but it spells a *flag's* choices the same way. Two disguises to strip
    before looking, or a value set gets walked as if it were a subcommand:

    - optional flags, bracketed — `[--status {backlog,active,…}]`
    - **required** flags, which argparse renders bare — `--resolution
      {done,duplicate,…}` on `tcw work complete`. This one bites hardest:
      `tcw work complete done --help` returns `complete`'s own help rather than
      failing, so a bad walk recurses until the stack gives out.

    What survives both is positional, i.e. genuine subcommands.
    """
    usage = text.split("\n\n", 1)[0]
    positional = re.sub(r"--[a-z][a-z-]*\s*\{[^}]*\}", "", usage, flags=re.S)
    positional = re.sub(r"\[[^\]]*\]", "", positional, flags=re.S)
    choices = re.search(r"\{([a-z0-9,-]+)\}", positional)
    return choices.group(1).split(",") if choices else []


def _walk(path: list[str], tree: dict[tuple, set[str]]) -> None:
    """Record {command path: its flags} for `path` and every subcommand under it.

    Recursing is what makes nested groups like `tcw work inbox accept` resolve,
    instead of reading `accept` as a flag-bearing verb of `inbox`.
    """
    if tuple(path) in tree or len(path) > 4:   # tcw's real depth is 3; cap so a
        return                                 # formatting change can't hang CI
    text = _help(path)
    if not text:
        return
    tree[tuple(path)] = set(FLAG.findall(text))
    for child in _subcommands(text):
        _walk([*path, child], tree)


@pytest.fixture(scope="module")
def tree() -> dict[tuple, set[str]]:
    """Every valid `tcw …` command path mapped to the flags it accepts."""
    out: dict[tuple, set[str]] = {}
    _walk([], out)
    return out


def _check(span: str, tree: dict[tuple, set[str]]) -> str | None:
    """The problem with this documented invocation, or None."""
    tokens = span[span.index("tcw") + 3:].split()
    path: list[str] = []
    for token in tokens:
        if not WORD.match(token):        # <slug>, "text", |, #comment → args start
            break
        if tuple([*path, token]) in tree:
            path.append(token)
            continue
        # An unknown word where the current node has children is a phantom verb.
        if any(len(k) == len(path) + 1 and k[:len(path)] == tuple(path) for k in tree):
            return f"no such verb: tcw {' '.join([*path, token])}"
        break                            # a positional arg, not a subcommand
    known = tree.get(tuple(path), set())
    for flag in FLAG.findall(span):
        if flag not in known:
            return f"no such flag: {flag} on tcw {' '.join(path)}"
    return None


@pytest.mark.parametrize("doc", DOC_FILES, ids=lambda p: str(p.relative_to(REPO)))
def test_documented_verbs_and_flags_exist(doc, tree):
    problems = []
    for span in _invocations(doc.read_text(encoding="utf-8")):
        if (problem := _check(span, tree)) is not None:
            problems.append(f"`{span}` — {problem}")
    assert not problems, (
        f"{doc.relative_to(REPO)} documents a nonexistent CLI surface:\n  "
        + "\n  ".join(problems)
    )
