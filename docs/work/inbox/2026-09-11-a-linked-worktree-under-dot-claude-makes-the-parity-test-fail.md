# A linked worktree under `.claude/` turns the skill-parity test red

Found while running the suite for
`2026-08-20-load-yaml-reads-a-falsy-yaml-document-as-an-empty-mapping`. Not
caused by that item, and **already fixed in that item's branch** — this note
records the decision rather than asking for the fix.

## What happened

`tests/test_skill_lifecycle_parity.py::test_no_reference_to_a_deleted_document_survives`
walks every `*.md` under the repository and asserts that no live route still
names a lifecycle document that was deleted. It skips archives by path prefix
(`docs/work/`, `docs/changelogs/`, `docs/release-notes/`) and skips directories
by name: `.git`, `node_modules`, `build`, `.venv`, `.worktrees`.

An agent harness put a linked worktree at
`.claude/worktrees/<id>/`. Inside it is a second full checkout, archived
changelogs included. The prefix check compares a path relative to the repository
root, so those read as `.claude/worktrees/<id>/docs/changelogs/v0.3.1.md` and
never match `docs/changelogs/`. Four of the test's parameters went red on files
the test already means to ignore.

The suite is therefore red for anyone holding a worktree in that location, with
nothing wrong in the tree.

## What was done

`.claude` added to the skipped directory names, beside `.worktrees` which is
there for exactly this reason. One line, in the item's branch.

## Why this is worth a look anyway

**The exclusion is expressed twice, in two different shapes** — a prefix list
for archives and a name set for directories — and only the second one composes
with nesting. A repository-walking test is the kind that should decide what it
is looking at from git rather than from a hand-kept list of directory names:
`git ls-files` yields exactly the tracked, live tree and no second checkout,
which would make both lists unnecessary.

Worth checking whether any other test walks the tree the same way before
deciding this is settled.
