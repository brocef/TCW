# Outcome — Publish provisioned-store writes to their remote

All nine planned tasks landed, each as its own commit. A transition on a
provisioned work store now refreshes before it moves anything and publishes after
it commits, and the work a cloud session does survives the session.

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 | `a33af26` | the `published-store-writes` Feature |
| 2, 4 | `34742a9` | `publishes` / `refresh()` / `publish()` on `WorkStore`; the ladder passes the declaration on rule 2 only; `work.publish-transitions` |
| 3 | `a8b7ac9` | the no-network property, pinned across every non-publishing rule |
| 5 | `0be482c` | refresh before the move, and the ff-only coupling note at `_refresh` |
| 6 | `b551c54` | publish after the commit |
| 7 | `cb48669` | one named assertion per property; the subsumed test removed |
| 8 | `e25d23a` | README, changelog, release notes, two skill documents |
| 9 | `c4c7026` | the error-reporting defect the bare-shell walk found |

Plus `256d7f8` and `2145400`, recording that the tree stores are deliberately
never published, and `2cb6caa`, correcting the plan.

## Acceptance criteria

Every one walked from a bare shell against a real two-repository fixture.

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | a transition is visible to a fresh provisioning | `test_a_transition_reaches_the_remote[start\|submit\|complete]`; by hand, a fresh `git clone` of the remote showed the item in `active/` |
| 2 | nothing moves until the store is up to date | `test_the_refresh_precedes_any_filesystem_change` — the refresh observes whether the item has already moved |
| 3 | a refused refresh leaves the item untouched, and says why | `test_a_refused_refresh_leaves_the_item_untouched`, `test_an_unreachable_remote_at_refresh_says_why` |
| 4 | a failed publish reports what landed, exits non-zero, rolls nothing back | `test_a_failed_publish_says_what_landed`, `test_an_unreachable_remote_at_publish_says_where_the_work_is`; read cold by hand against a read-only remote |
| 5 | divergence is refused, never merged | `test_divergence_is_refused_not_merged` — asserts no merge commit exists, not merely that it failed |
| 6 | only a publishing store touches the network, at steps 1 and 4 | `test_no_transition_on_a_non_publishing_store_touches_the_network_anywhere`, 3 rules × 3 transitions, adapter Git calls asserted **empty** |
| 7 | a non-publishing store is unchanged | `test_a_non_publishing_store_is_unchanged[rule-1\|rule-4\|disabled]`; no test outside this module rewritten |
| 8 | a push contacts only the declared remote | `test_a_push_verifies_the_remote_before_contacting_it`; by hand, a mismatched origin refused with "nothing was contacted" |
| 9 | the off switch works, and a non-boolean reads as the default | `test_publication_can_be_switched_off` |
| 10 | git invoked with stdin closed | `tests/test_subprocess_stdin.py`, unchanged |
| 11 | reproducible from a bare shell | every row above |

### Verified by hand

An orchestrator repository holding a work store, a bare clone as the remote, and
a code repository declaring it with no local copy. `tcw provision`, then
`tcw work start` — and a fresh `git clone` of the remote showed the item in
`active/`. Then each failure: the remote moved away (refresh refuses, item
untouched, `git fetch failed: fatal: … does not appear to be a git repository`);
the checkout's origin repointed (refused, "nothing was contacted", both URLs
named); the remote made read-only (push fails, message below).

And the case the safety story is really about — a store with **no declaration**
whose repository has a real `origin`, which is what an ordinary project looks
like. `GIT_TRACE=1 tcw work start` produced no push, fetch or clone, and the
remote's log was unchanged.

## What the plan and spec got wrong

**`_effect_transition` is not the seam.** The plan called it "one function
through which every status change passes". `FsWorkStore.start`
(`tcw/store/fs.py:3080`) has its own claim-based path with its own two
`_commit_transition` calls — the `.claiming/` rename is what makes concurrent
starts safe — and never touches it. A refresh hooked into `_effect_transition`
alone left `tcw work start` unrefreshed and unpublished: the transition most
likely to happen in a fresh cloud session, which is the case this whole
initiative exists for.

It was found by luck. The first test written happened to use `start`. The
correction is `_refresh_before_transition()`, called from both paths, and tests
parametrized over `start` / `submit` / `complete` — which is what replaces the
luck. `2cb6caa` records it in the plan.

**Criterion 4's test was passing against a fiction.** It monkeypatched `publish`
to raise a clean `ValueError`, so it exercised the message *wrapper* and never
the message a real failure produces. The bare-shell walk produced:

```
tcw work: work.repository: git -C failed: and the repository exists.
```

Two pre-existing defects in child A's `_run`, invisible until publication put
them in front of ordinary commands rather than only an explicit `tcw provision`:
`argv[1]` named the subcommand, but every argv is `["git", "-C", <path>, <verb>]`,
so every failure the adapter has ever produced said "git -C failed"; and
`detail[-1]` took git's *last* stderr line, which for an unreachable remote is
the boilerplate "and the repository exists." rather than the diagnosis. Fixed in
`c4c7026`, with tests that drive the real path.

The general lesson is sharper than "test the real thing": **a test that injects
its own error is testing the handler, and should be labelled as such**, because it
reads exactly like a test of the failure.

**A cell neither Coverage table enumerated.** `work.publish-transitions` and
`work.auto-commit-transitions` are independent in config, and I first placed the
publish call beside the auto-commit branch rather than inside it — so with
auto-commit off, a push would contact the remote and publish nothing. Found while
wiring step 4, not by the tables, and now covered by
`test_nothing_is_published_when_nothing_is_committed`. The tables crossed criteria
against section A and section B; they did not cross the two config switches
against each other, because only one of them was in the Design section.

**The documentation task broke a rule the docs themselves state.** Task 8 added
four lines to `skills/tcw-work/SKILL.md`, and
`test_the_router_stays_within_its_line_budget` failed at 64 against a budget of
60 — the router was already exactly at budget, so any addition breaks it. The
test's own words are *"the rule on breach is extract, never grow"*, and
`docs/lifecycle/implementation.md` says a `SKILL.md` is a thin router with rare
sub-procedures pushed into `references/`.

Trimming to two lines still overflowed. The right answer was that this belongs in
the router not at all: it is conditional detail — only provisioned stores publish
— so it lives in `references/commands.md`, which already had it, and the router's
existing pointer line grew four words instead. Zero new lines.

Worth noting because the mistake was not carelessness about the budget; it was
adding to the router without asking whether the content was *always* relevant,
which is the actual rule the budget enforces.

## Did the Coverage requirement earn its cost?

Recorded for
[the upstream item](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage).

**Yes, twice, before any code was written.** Filling the tables found that
criterion 7 had no meaning in its own first column, and that criterion 5's
step-3 and step-4 cells are unreachable only while refresh stays fast-forward
only — which became the spec's first risk and a note in `_refresh`.

**And it has a clear limit, now demonstrated.** It crosses criteria against what
the Design section *numbered*. The auto-commit/publish interaction was missed
precisely because `auto-commit-transitions` is prior behaviour and appeared in no
numbered list. The rule finds contradictions between a spec's own sections; it
does not find contradictions with the code the spec did not describe.

**A 3-axis grid does not fit one table.** 11 × 4 × 4 is 176 cells. Splitting into
two 11 × 4 tables was necessary and should be part of the rule if it is
upstreamed.

## Suite

The full run passed **2159 tests** with no failures and no skips, outside the
restricted sandbox — the server suites bind loopback sockets, and the sandboxed
run's `PermissionError` cluster is an artefact of that rather than a result.
`tests/test_store_publication.py` is new and holds 31 cases; no test outside it
was rewritten to accommodate this work, which is criterion 7's other half.

## Decisions worth carrying forward

- **Publication follows the resolution ladder.** A declaration that did not answer
  the read does not get to cause a write. That single rule settles all three
  cases, including the one that matters — a store with no declaration never
  publishes, so TCW cannot push a user's own repository because they changed an
  item's status.
- **Where a failure happens decides what is said.** Refresh-fails and push-fails
  are not two error messages for one event; they are two different states of the
  world, and the ordering is what makes them distinguishable without a rollback.
- **Work publishes; the trees do not.** An item's state is the record of a
  session and changes independently of the code. A capability's status is a claim
  about the code, true when the code lands, so it travels with that change.
