# Outcome — Claim an external tracker ticket and bind it to a work item

Built 2026-09-14 in the worktree `.worktrees/2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`
on branch `work/2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`,
sequentially in one session, as the user chose. Ten commits on top of the start
commit `de5a8da8`.

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 | `fbbef0e3` | `tracker.yaml` in `WORK_SIDECARS`, `yaml_mapping`, `generated` |
| 2 | `27c81460` | `tcw/tracker/intake.py`: `read_binding` (unbound / malformed / bound), `validate_part`, `binding_of`, `find_binding` over unresolved items, `binding_document`, `unlink_document`, `unlinked_history` |
| 3 | `0b208531` | `JiraClient.apply_transition`, `assign`, `description` (v2); `issue` quotes its key |
| 4 | `98f6ee3c` | `read_ticket` and `claim` — the spec's step 1, 2 and 3 tables, a row id on every outcome; `tests/tracker_fake.py`, a stateful fake Jira with hooks |
| 5 | `9ab116a7` | `tcw work tracker import` |
| 6 | `43dbe709` | `tcw work tracker link` and `unlink` |
| 7 | `463f7857` | inbox note: `docs/work/inbox/2026-09-14-serve-accepts-writes-to-generated-sidecars.md` |
| — | `c1bd4b62` | `tracker.yaml` added to `OWNED_YAML_NAMES` — see "What the plan and spec got wrong", item 1 |
| 8 | `4319d247` | README, `docs/guide/work.md`, `skills/tcw-work/references/commands.md`, release notes, changelog |
| 9 | `a85aa73c` | `work/manage-external-tracker-intake` → `Supported`, with a description; one sentence of `work/inspect-external-tracker-work` corrected |

New test files: `tests/test_tracker_binding.py` (37), `tests/test_tracker_claim.py`
(19), `tests/test_tracker_import.py` (21), `tests/test_tracker_link.py` (14), and the
shared `tests/tracker_fake.py`. `tests/test_tracker_client.py` gained 7 tests and
three `OPERATIONS` entries.

## Test results

- **Full suite at `c1bd4b62`** (every code task, before docs and ledger):
  **2917 passed** in 15m06s, run in a throwaway checkout of that exact commit. The
  baseline before any change was **2815 passed**.
- Suites at `fbbef0e3` and `27c81460` each had **one failure**,
  `tests/test_validate.py::test_every_yaml_name_tcw_writes_is_owned_or_deliberately_not`,
  fixed in `c1bd4b62`. Suites were not run separately at `0b208531` through
  `463f7857`; the `c1bd4b62` run covers all of them.
- After docs: `tests/test_documented_cli_surface.py` — 224 passed.
- After the ledger change: `tcw capabilities check` → `capabilities OK`;
  `tcw validate`, run from the worktree's code → `validate OK`, exit 0.
- **Epic criterion 1 check** (epic plan task 9) against `de5a8da8`: "no test lines
  removed". Bare `pytest` also collects the new files and imports `tracker_fake`.

## Mutation checks

Each run red once, then restored; the red tests named the property.

| Property | Mutation | Red |
| -------- | -------- | --- |
| Resolved items are not consulted | drop the status filter in `find_binding` | 2 |
| A malformed binding refuses the lookup | skip it instead | 1 |
| Two items holding one key refuse | take the first match | 1 |
| Assign only after the transition | assign before transitioning | 7, including race orders (b) and (c) |
| Assign only after an **applied** transition | assign after a refused or unknown one | 4, including orders (b) and (c) |
| The read-back requires the landing status | accept the assignee alone | 1 (the refused-transition-on-a-ticket-already-yours test) |
| Row 1f gives no assign advice | add "Assign it to yourself" | 1 |
| `import` removes an item it could not bind | skip the `drop` | 2 |
| An existing binding is checked against the tracker | trust it | 1 |
| `import` finds an existing binding | skip the lookup | 2 |
| No token in output (import) | print the token | 1 |
| `link` writes with the file's revision | always `revision=""` | 1 (link after unlink) |
| `unlink` needs no tracker | require one | 1 |
| `link` refuses a bound item | rebind | 1 |
| No token in output (link) | print the token | 1 |
| `link` keeps the unlink history | pass `[]` | 1 |

Two mutation attempts were themselves wrong and redone. The first token mutation in
`link` was a syntax error that turned every test red. Changing `unlink_document` to
drop history left the link tests green, because they unlink only once;
`test_history_survives_a_second_binding_and_a_second_unlink` in the binding tests
covers repeated unlinks, and a separate mutation of `link`'s own history carry was
caught.

## Live verification

Run 2026-09-14 against `proposit.atlassian.net`, with the user's approval, in two
throwaway TCW nodes in the session scratchpad (not this repository's board), using
the worktree's code. Tickets were created for the purpose: `TCWCLAIM-7`,
`TCWCLAIM-8`, `TCWTEST-3`, each unassigned in `To Do` and described as safe to close.
They are left `In Progress`, assigned to the site account.

- **Criterion 18, workflow that excludes.** `import TCWCLAIM-7` → exit 0, "claimed
  by this run", item `2026-09-14-tcwclaim-7-c2-live-check-c18`. Jira then showed
  `In Progress`, assignee the signed-in account. The intake holds the ticket's
  description text and link; `tracker.yaml` has project, part, ticket id `10054`,
  key, URL and claiming account; `state.yaml` has no `owner`. `tracker show` after
  the claim: `claimable: not claimable`.
- **Idempotent, live.** `import TCWCLAIM-7` again → same slug, "already bound",
  exit 0.
- **Criterion 18, workflow that does not exclude.** `import TCWTEST-3` (claim
  `In Progress`) → exit 0, claimed and bound, nothing printed about exclusivity.
  `tracker show TCWTEST-3` separately reports `workflow: not exclusive`.
- **Criterion 11.** `TCWCLAIM-8` moved to `In Progress` and assigned by hand through
  the REST API, then `import TCWCLAIM-8` → exit 0, "not claimed by this run: …
  already in 'In Progress' and assigned to you", item bound.
- **unlink then link.** `unlink … --reason "live check"` → exit 0, "The ticket is
  unchanged in the tracker"; `link … TCWCLAIM-7` → exit 0, bound again, with the
  unlinked entry kept.
- **No token** in any file under either node.

## Not verified

- **Epic plan Verification item 2 — two developers on two machines, one Jira
  project.** No second Jira account is available (the user, 2026-09-14). The two-account race is
  proved only against the fake: claim-level orders (a), (b), (c) and command-level
  orders (a) and (c).
- **Epic plan Verification item 4 — a ticket filed by someone without a checkout,
  imported end to end.** Nobody available (the user, 2026-09-14). The live tickets
  above were created through the API by the same account that imported them.
- **Team-managed Jira projects.** Both fixtures are company-managed, as for C1.
- **Assign refused by Jira while the transition was allowed** (row 3e) — only
  against the fake; the site account has every permission.

## What the plan and spec got wrong

1. **The spec said `tcw validate` would not check bindings; it now checks one
   thing.** `tests/test_validate.py::test_every_yaml_name_tcw_writes_is_owned_or_deliberately_not`
   requires every YAML name TCW writes to be classified, and nobody had classified
   `tracker.yaml`. A binding has one valid shape and `write_sidecar` already enforces
   it, so it joined `OWNED_YAML_NAMES` (`c1bd4b62`), and `tcw validate` now reports a
   `tracker.yaml` that is not a mapping. That also means such a file fails
   `tcw validate` as a `pre` hook on `complete` — the effect the spec's non-goal
   wanted to avoid. It is narrower than what the spec rejected: duplicate keys and
   missing fields are still not validate's business, and a *syntax* error in any
   YAML file in the store already failed validate before this item. The alternative
   was listing `tracker.yaml` as a deliberate exception in that test, which would
   have edited an existing assertion for a file that has no second valid shape.
2. **The spec said `work/inspect-external-tracker-work` needed no change.** Its
   description ended "Claiming a ticket … [is a] separate capabilit[y] that [is] not
   yet built", which this item made false. One sentence corrected in `a85aa73c`.
3. **The plan's command-level race test for order (b) cannot be built.** It asked for
   B's claim to run inside A's request so that B reads back between A's transition and
   A's assign. A nested command runs its whole claim at one point in A's sequence;
   order (b) needs B's step 1 read *before* A's transition and B's transition
   *after* it, which no single nesting point gives. Order (b) is proved at claim
   level, where step 1 and the claim are separate calls; the command-level file tests
   orders (a) and (c).
4. **Not re-pointing the editable install.** The project guide says to
   `pip install -e <worktree>` for worktree work. Another session was working in this
   repository at the same time, and the install is shared, so this item followed C1
   instead: every test and CLI run was started with the worktree root first on the
   import path, and each run asserted `tcw.__file__` was in the worktree. The install
   was never changed, so there is nothing to restore.
5. **Plan task 2 named `unlink_document(existing: dict, …)`**; it takes the file's
   text, because every caller has text and not a parsed mapping. And plan task 5 named
   `FsProjectRegistry.open(...).current.id` for the project id; the CLI already had
   `registered_project_id(node, node)`, which does exactly that, and uses it.
6. **One gap the plan did not list:** a failed description read after a successful
   claim reported a bare tracker error, without saying the ticket was already claimed.
   Found while writing `import`; now says "claimed <KEY>, but its description could
   not be read … Run this command again", with a test.

## Notes

- **Row 3e's `detail:` line** carries C1's generic permission message, "the account
  is not permitted to see this", which reads oddly when the refused action was an
  assign. It is `_for_status`'s wording for every 403 and was left alone.
- **For the epic's checkpoint 2.** Carry: criterion 6 is narrowed to two accounts on
  a workflow that excludes; two runs by one account may both create an item (user
  decision); a second claimant on a workflow that does not exclude is not stopped
  (user decision); Verification items 2 and 4 are not verified.
- **Documentation overlaps** `2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key`,
  started in its own worktree during this build. Both edit the tracker sections of
  `README.md`, `commands.md`, `docs/guide/work.md` and `docs/changelogs/upcoming.md`.
  Whichever merges second rebases.
- **No version cut** in this item.
