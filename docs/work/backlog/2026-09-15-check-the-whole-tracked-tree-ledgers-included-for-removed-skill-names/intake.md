## Inbox manifest

- `2026-09-11-a-linked-worktree-under-dot-claude-makes-the-parity-test-fail.md`

## Inbox body

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

## Triage (2026-09-15)

Merged at triage because every part changes which files the skill-parity tests
read (`tests/test_skill_lifecycle_parity.py` and the tests that share its
frontmatter parsing): walking the tree from `git ls-files` rather than hand-kept
exclusion lists, and covering every live folder — `agents/`, `hooks/`, `scripts/`,
`evals/`, `tests/`, the agent guides, `docs/capabilities` and `docs/taxonomy`. The
maintainer asked for items touching the same feature to be combined.

- **In scope:** the entry above, parts 1 and 5 of the skill restructure guards, and
  §3 of the skill capability overlaps, all folded in below.
- The other parts of those two entries are tracked elsewhere: guards 2 and 6 with the
  eval harness defects item, guards 3 and 4 and overlaps §1 and §2 with the skill
  documentation item.

## Folded in: from inbox entry `2026-09-14-guards-and-gaps-the-skill-restructure-review-left.md` (Guards and gaps the skill restructure's review left for separate changes)

1. **The removed-names test scans only part of the repository.** It covers
   `skills/`, the two manifest folders, `README.md`, `docs/guide/` and
   `docs/lifecycle/`, as the item's spec asked. `agents/`, `hooks/`, `scripts/`,
   `evals/`, `tests/`, `AGENTS.md` and `CLAUDE.md` are clean today, but nothing
   stops a removed skill or command name coming back there.

5. **Small duplication in tests.** The "body after the frontmatter" slice and the
   frontmatter parse are written three times (`tests/test_skill_lifecycle_parity.py`,
   `tests/test_documentation_sync_wiring.py`, `tests/test_plugin_manifests.py`).
   A shared helper would keep the rule for what counts as a skill body in one place.

## Folded in: from inbox entry `2026-09-14-skill-capability-overlaps-the-per-skill-review-left.md` (Skill capability overlaps the per-skill ledger review left)

### 3. No test keeps removed skill and command names out of the ledger

`tests/test_skill_lifecycle_parity.py` checks `DELETED_NAMES` against
`LIVE_ROUTES`, which does not include `docs/capabilities` or `docs/taxonomy`. The
per-skill item checked those folders with a one-off `git grep` (its acceptance
criterion 8), which misses names written without a leading slash, such as
`tcw-audit-work-backlog`. A hand scan with the whole-name matcher found both
folders clean on 2026-09-14. Adding both folders to `LIVE_ROUTES` would keep them
clean. Exempt `tcw://C/skills/...` links, which contain skill names on purpose.
