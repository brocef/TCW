# Plan — Publish provisioned-store writes to their remote

Nine tasks. The ordering principle is that **the network arrives last**: every
piece of machinery that decides *whether* to publish lands, and is tested, before
anything actually pushes. That way the riskiest change — a network call inside a
state machine that is currently local and atomic — goes in on top of a tree where
its guards already exist and are already green.

## Ordering constraints

1. **The taxonomy Feature is registered before any capability names it.**
   `tcw capabilities set` refuses an unresolvable `Feature=`. Task 1.
2. **`publishes` is correct, and proven correct, before `publish()` does
   anything.** Section A of the spec is the whole safety story: rule-4 stores
   must never push. Tasks 2-3 land that with its tests; task 6 is the first task
   that can reach a remote.
3. **The tests that pin "no network" are written before the code that could
   perform one.** Task 3's parametrized non-publishing tests are green against a
   tree where publication does not exist yet — trivially, which is the point:
   they must still be green after task 6.
4. **The CLI keeps working throughout.** Every task touches `_effect_transition`
   or its neighbours, which is the path `tcw work` runs on to record this very
   item. Each task lands green.

## Tasks

### 1 — Register the `published-store-writes` Feature

`tcw taxonomy add` with vocabulary `store`, `store/home-repository`,
`transition`. Deliberately its own Feature rather than folded into
`provisioned-component-stores` — the spec's Capability-changes section gives the
reason.

**Files.** `docs/taxonomy/published-store-writes/` (new).
**Proves it.** `tcw taxonomy check` and `tcw validate` pass; the slug resolves.

### 2 — The store-interface members, with no behaviour

`publishes`, `refresh()`, `publish()` on the `WorkStore` ABC, and a filesystem
implementation in which `publishes` answers section A correctly and the two
methods are not yet called by anything.

`resolve_store` has to tell the store which rule produced it — that is how
`publishes` distinguishes ladder rule 2 from rule 1. Kept to a private attribute
set at construction; no abstract signature learns about ladder rules, per the
litmus table.

**Files.** `tcw/store/base.py` (the three members), `tcw/store/fs.py`
(`resolve_store`, `FsWorkStore.__init__`/`_open_at`, the `publishes` property),
new `tests/test_store_publication.py`.
**Proves it.** `publishes` is `True` for a rule-2 store and `False` for rule 1,
rule 4, and a node with no declaration — the four columns of the spec's first
Coverage table, parametrized, not four separate tests.

### 3 — The "no network" property, pinned before it can be violated

Criterion 6 and criterion 7, written now, against a tree where they hold
trivially. Their value is entirely in task 6 not breaking them.

Criterion 7's test **parametrizes over all three non-publishing rules**. The
spec's Coverage table flags this as the assumption its `n/a — via 7` cells rest
on; if this test covers one rule and is assumed to cover three, that table is
decorative. So the parametrization is the task, not a detail of it.

**Files.** `tests/test_store_publication.py`.
**Proves it.** `test_a_non_publishing_store_is_unchanged[rule-1|rule-4|disabled]`
and `test_no_transition_on_a_non_publishing_store_touches_the_network[…]`, with
the adapter's Git invocation intercepted and asserted **empty** — not merely
"no push".

### 4 — `work.publish-transitions`

Read exactly as `auto_commit_transitions` is (`tcw/store/fs.py:3658-3666`),
including its non-boolean-reads-as-default rule and the reasoning comment. Feeds
`publishes`.

**Files.** `tcw/store/fs.py`, `tests/test_store_publication.py`.
**Proves it.** Criterion 9, including the non-boolean case, which is the half
that would otherwise be forgotten.

### 5 — Refresh before the move

Step 1 of the spec's section B. `refresh()` on a publishing store, called at the
top of `_effect_transition`, before any filesystem change.

The fast-forward-only behaviour is inherited from `FsStoreProvisioner._refresh`
(`tcw/store/fs.py:2893-2909`) rather than rewritten. **Add a comment at
`_refresh` recording that transition-divergence semantics now depend on its
ff-only behaviour** — the spec's first risk is precisely that a future reader
relaxes it for the tags-and-commits reason its docstring gives, not knowing what
else rests on it.

**Files.** `tcw/store/fs.py` (`_effect_transition`, a note at `_refresh`),
`tests/test_store_publication.py`.
**Proves it.** Criteria 2, 3 and 5. Criterion 3's test asserts *all* of: same
status, same folder, no commit — the spec's wording, not a subset of it.

### 5a — CORRECTION, found at task 5

The plan below said `_effect_transition` is the one seam every transition passes
through. **It is not.** `FsWorkStore.start` (`tcw/store/fs.py:3080`) has its own
claim-based path with its own two `_commit_transition` calls — the `.claiming/`
rename is what makes concurrent starts safe — and never touches
`_effect_transition`.

A refresh hooked into `_effect_transition` alone therefore left `tcw work start`
unrefreshed and unpublished: the transition most likely to happen in a fresh
cloud session, which is the scenario this whole initiative exists for.

Corrected by a named `_refresh_before_transition()` called as the first statement
after `_require_repository()` in **both** paths, and by parametrizing the
transition tests over `start` / `submit` / `complete` rather than the one command
that was convenient. It was found by luck — the first test written happened to
use `start` — and the parametrization is what replaces the luck.

### 6 — Publish after the commit

Step 4, and the first task that pushes. `publish()` after `_commit_transition`,
reusing `_require_declared_checkout` (`tcw/store/fs.py:2861-2891`) to verify the
remote before contacting it.

On failure: report what landed and what did not, exit non-zero, roll nothing
back — following `_commit_transition`'s stated precedent
(`tcw/store/fs.py:4213-4217`).

**Files.** `tcw/store/fs.py`, `tcw/work/cli.py` (what the user is told),
`tests/test_store_publication.py`.
**Proves it.** Criteria 1, 4, 8. Tasks 3's tests must still be green — that is
the real acceptance test for this task.

### 7 — One named assertion per property

The implementation rule added after the A/B post-mortem: a family of tests for one
criterion calls one named assertion, so a sibling that skips it shows in the diff.
Here that is `_assert_nothing_moved(item)` for criterion 3 and
`_assert_no_network(calls)` for criterion 6.

Folded in as its own task because doing it inline is how it gets skipped.

**Files.** `tests/test_store_publication.py`.
**Proves it.** Every criterion-3 and criterion-6 test routes through one helper.

### 8 — Documentation

The block below, once tasks 1-7 are done and the suite is green.

### 9 — Full suite, bare-shell walk, `outcome.md`

Full run outside the restricted sandbox. Then the bare-shell walk of all eleven
criteria against a real two-repository fixture — **and specifically the cells the
Coverage table marks `n/a`**, because the tables' honesty is what this item is
also testing. Then `outcome.md`, including what this plan got wrong and whether
the Coverage requirement earned its cost.

## Documentation Sync

Evaluated against this node's declared entries (`tcw work docs`; source: config).

| Entry | Trigger | Fires | What it needs |
| --- | --- | --- | --- |
| `README.md` | Public-API | **yes** | The external-store section says `tcw provision` is "the **only** command that reaches the network". That becomes false. It must now say which transitions publish, which stores they publish for, and how to switch it off. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | **Leads with the behaviour change**, not mentions it: anyone already using a provisioned store gets pushes on upgrade. Plain language, and the off switch named in the same breath. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Added/Changed. The `publishes`/`refresh()`/`publish()` interface, the ladder-rule dependency, and the `_refresh` ff-only coupling as Internal. |
| `skills/tcw-work/SKILL.md` and `references/commands.md` | Skill-Driven-Component | **yes** | Transitions can now fail *after* succeeding locally, which is a new state the skill's transition guidance does not describe. `commands.md` § "Claims and external work stores" is where the store-location rules already live. |

Entries go to `upcoming.md`. `v1.1.0` is tagged, so this belongs to the next
version. No version is cut during implementation; the choice is offered at
`verify`, after acceptance — the epic's first child recorded two premature cuts
and this plan does not make a third.

## Verification

What the suite cannot check, and who checks it:

- **The `n/a` cells are real.** Read the Coverage tables against the finished
  tests and confirm every `n/a — via 7` is actually carried by a parametrized
  criterion-7 test. This is the one check that decides whether the new spec
  section is a mechanism or a ritual, and it cannot be automated because the
  question is whether a human's claim was true.
- **The upgrade story.** Read the release note cold as someone running v1.1.0 with
  a provisioned store: does it tell them their transitions will start pushing,
  before they find out by pushing?
- **Error text when publication fails.** The state "your item moved, it is
  committed here, and it is not on the remote" has never been described by this
  CLI. Read it cold: does the user know whether their work is safe, and what to
  run next?
- **The abstraction seam.** Confirm no signature in `tcw/store/base.py` names a
  remote, a ref, a branch, or a ladder rule.
- **Codex parity.** Every criterion from a bare shell with no hook and no slash
  command, per `docs/lifecycle/harness.md`.

## Notes

- Task 3 deliberately writes tests that pass on an unchanged tree. They are not
  redundant: they are the definition of "task 6 did not break anything", and
  writing them after task 6 would mean writing them to fit whatever task 6 did.
- No blocker is recorded against any other item, and nothing is blocked by this
  one. Children A and B are complete. Publishing the taxonomy and capabilities
  trees was briefly filed as a follow-up and then dropped — see the spec's
  Non-goals: those trees describe the code and land with it, so publishing them
  separately would announce a capability before the code realizing it exists.
