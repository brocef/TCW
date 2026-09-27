# Outcome: make a refused tcw work edit change nothing

## What shipped

- **Tasks 1-3** — `cbc708e8`.
  - `tcw/store/base.py`: `add_blocker`'s self-block and cycle refusal moved into
    `_check_new_blocker(slug, entry, ref)`; new non-writing
    `check_blocker_edits(slug, add=, remove=, blocks=)` refuses what the
    equivalent sequence of `remove_blocker` / `add_blocker` / reverse
    `add_blocker` calls would refuse, taken together.
  - `tcw/store/fs.py` `update_work(blockers=...)`: runs `_check_new_blocker` for
    each entry the item does not already have — the web app's save path now
    refuses a new self-block or cycle.
  - `tcw/work/cli.py` `_edit`: type check → `check_blocker_edits` →
    `update_work` → the blocker writes.
  - Tests: `tests/test_edit_refusal.py`.
- **Documentation** — `c6cb0a90`: changelog, release notes, one comment line in
  `docs/guide/work.md`'s command block.
- **Review fixes** — `89279362` (see Autonomous decisions): `--blocks` is
  checked against the proposed blockers only (`_reaches(..., settled=)`),
  removal matching is shared through `_without`, direct store tests for
  `check_blocker_edits`, a stale docstring in `tests/test_work.py`.

## Tests

- New tests went red on the old code for the stated reason (the diff of
  `state.yaml` showed the blocker written, or `update_work` did not raise), and
  the false-cycle regression test went red with the review's exact message when
  the fix was reverted.
- `tests/test_edit_refusal.py`, `tests/test_edit_type.py`,
  `tests/test_store_editor.py`, `tests/test_work.py`: green.
- Full suite on the final code: 4494 passed, 3 skipped.
- Hands-on in a scratch repository with the worktree's `tcw`:
  `edit X --blocked-by Y --tag nope` → exit 1, `git status --porcelain` empty;
  `edit X --blocked-by Y --blocks Y` → exit 1 with the cycle message, status
  empty; `edit X --blocked-by Y --title Renamed` → exit 0, both applied.

## What the plan or spec got wrong

- **Spec criterion 4 could not be tested as written.** A bad `--effort` is
  refused by argument parsing before `_edit` runs, so it never writes anything.
  The test uses `--blocks Y --tag not-registered` instead, which is the case the
  criterion was after (a reverse link left behind).
- **Test location.** The plan put the tests in `tests/test_store_editor.py` and
  the CLI edit tests; they are all in one new file, `tests/test_edit_refusal.py`,
  so the property has one home.
- **Design gap found by review.** The first `check_blocker_edits` followed the
  item's *stored* blockers when a walk came back through it, so on an item
  already in a cycle it could refuse `--unblocked-by R --blocks T` although the
  edit removes the only route to T. Fixed and tested.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` [Public-API] | No | No surface change. |
| `docs/guide/jira.md` [Tracker-Change] | No | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Yes | `work.md`: flags combine; a refusal changes nothing. |
| `docs/release-notes/upcoming.md` [Public-API] | Yes | Two lines. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | Yes | Two Fixed entries. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | Checked, no | `skills/work` never described the partial write. |
| `skills/configure/references/<document>.md` | No | No key changed. |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Spec: validate everything in the CLI (A), or fold the check into the store
  and order the writes (B)?** Codex: B, but keep validation out of the CLI and
  never round-trip existing entries through `_entry_for` (it can turn an
  external entry into a slug). Opus: B, with the cycle check in the abstract
  base, checking only new entries, and noting the web app's missing guard.
  Chose B with both refinements; existing entries are never rebuilt.
- **Guarantee boundary.** Both advisors: promise "refusals the command decides
  write nothing", not atomicity against concurrent writers or I/O failure.
  Written into the spec's Non-goals.
- **Code review** (adversarial-code-reviewer): DONE, no blocking findings.
  Accepted and fixed: the false cycle refusal on an item already in a cycle;
  duplicated removal matching; missing direct store tests; a test without an
  error-text assertion; a stale docstring. Noted, not changed: a second storage
  adapter's `update_work` would have to call `_check_new_blocker` itself — true
  of every rule `FsWorkStore.update_work` enforces today.
- **Verify** (tcw:verifier): accept; all seven criteria met on its own runs
  (607 targeted tests; hands-on in a scratch repository, with the bug reproduced
  on the old install), criterion 4's replacement judged justified. Noted, not
  changed: `check_blocker_edits` defaults its list arguments to `()` (cosmetic).
  Decision: accept.
