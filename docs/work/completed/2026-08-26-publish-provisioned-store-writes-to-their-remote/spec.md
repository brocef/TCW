# Spec — Publish provisioned-store writes to their remote

## Capability changes

**New**

- `work/publish-store-writes-to-the-remote` — a provisioned work store refreshes
  from its home repository before a transition and publishes to it after, so work
  done in an ephemeral environment survives the environment.

**Changed**

- `work/declare-the-work-stores-home-repository` — the declaration now governs
  writes as well as reads; the body must say when it does and when it does not.
- `cli/provision-declared-stores` — `--refresh` stops being the only way a
  provisioned store meets its remote, and the capability should say so rather
  than implying it.

**Taxonomy**

A new Feature, `published-store-writes` (vocabulary: `store`,
`store/home-repository`, `transition`). It is deliberately not folded into
`provisioned-component-stores`, whose description is about *reaching* a store —
"materializing it on demand… so a checkout that clones only the code repository
can still reach the store". Writing back is a different mechanism with different
failure modes, and one Feature covering both would describe neither. Registered
before any capability names it, because `tcw capabilities set` refuses a
`Feature=` that does not resolve.

## Problem

A cloud session can now reach a declared store and cannot keep anything it does
with it.

`tcw provision` clones the store's home repository into a working copy — a cache
directory, or wherever `checkout` names. Transitions then run against that copy:
`_effect_transition` (`tcw/store/fs.py:4154-4202`) moves the item folder and
`_commit_transition` (`4204-4222`) commits the move into
`self.store_git_root`, which for a provisioned store is the clone. Nothing
afterwards contacts the remote. The commit is real, the working copy is real, and
both are inside a container that gets reclaimed.

This is the last of the initiative's three children and the only one that makes
TCW write to a network. Today no code path does: the only `clone` and `fetch`
call sites in the package are inside `FsStoreProvisioner`
(`tcw/store/fs.py:2618`, `2668`), reached only from `tcw provision`.

## Goals

1. A transition on a provisioned work store is visible to anyone who provisions
   the same declaration afterwards.
2. A transition sees the remote's current state before it decides anything.
3. Every new failure mode says what landed, what did not, and what to do.
4. A store that is not provisioned behaves exactly as it does today.

## Non-goals

- **Resolving merge conflicts.** Detecting divergence and reporting it
  actionably is in scope; merging someone's work store for them is not.
- **Publishing tree-store writes — not as a boundary, but on purpose.** Child B
  made taxonomy and capabilities declarable, so it is natural to ask why they do
  not publish too. They should not, and the reason is worth stating so nobody
  re-raises it as a gap.

  A work item's state is the record of a *session's* activity. It changes
  independently of any code — `tcw work start` happens before a line is written —
  so a transition made in an ephemeral checkout has no other home, and losing it
  loses the only copy. That is the whole initiative.

  A taxonomy term or a capability status is a *claim about the code*. A
  capability is realized when the code implementing it merges, not before, so the
  edit belongs to the same change as the code and lands when that lands.
  Publishing it on its own would decouple the claim from its realization —
  announcing "capability X is `Supported`" to everyone reading the ledger while
  the code making it supported is still unmerged, or abandoned. The ledger would
  describe a product that does not exist.

  So the asymmetry is not an accident of this item's scope: **work is published
  because it is independent of the code; the trees are not published because they
  are not.** The store interface below still lives on the abstract store rather
  than on `WorkStore` alone, because "are my writes visible to anyone else?" is a
  fair question to ask any store — but for a tree store the honest answer is no,
  and it stays no.
- The provisioning verb's contract, the config schema, and `FsTreeStore.open` —
  consumed unchanged.
- Making transitions atomic across the network. They are not, cannot be, and the
  design says so rather than implying otherwise.

## Design

### A. Which stores publish

The resolution ladder (`resolve_store`, `tcw/store/fs.py`) can produce a store
four ways. Publication follows the ladder rather than sitting beside it:

1. **Resolved through the declaration** (ladder rule 2, the provisioned
   location) — **publishes.** This is the store `tcw provision` obtained, on a
   machine that has no other copy. It is the case the initiative exists for.
2. **Resolved from a local `work.path` while a declaration also exists** (rule 1)
   — **does not publish.** The declaration was not consulted for resolution, and
   "a declaration is a fallback, never an override" is already this design's
   stated rule. A declaration that did not answer the read does not get to cause
   a write. The user has the store on their own disk and can push it themselves.
3. **Resolved with no declaration at all** (rule 4) — **does not publish**, and
   this is the one that must be provably true rather than assumed. Such a store's
   Git repository may well have an `origin` — it is often the user's own project
   — and a store that consulted `origin` rather than the declaration would make
   TCW start pushing the user's repository on every status change.
4. **Publication disabled by config** — does not publish, whatever the above.

Rule 2's asymmetry with rule 1 is deliberate and worth stating plainly: the
requester's laptop, which has the orchestrator folder, will not publish, while
their cloud session will. That is the right way round. The laptop's copy persists
and its owner can push it; the cloud session's disappears.

### B. The transition sequence

Four steps. Which step fails determines what the user is told, because what is on
disk differs at each point:

1. **Refresh** — bring the working copy to the remote's current state, before
   anything moves.
2. **Move** the item folder, and write any fields.
3. **Commit** the move, scoped to the two folders it touched.
4. **Publish** the commit to the remote.

Steps 2 and 3 are today's `_effect_transition` and `_commit_transition`,
unchanged. Steps 1 and 4 are new and run only for a store that publishes.

The failure story falls out of the ordering rather than being invented for it:

| Fails | On disk at that moment | Answer |
| --- | --- | --- |
| 1 refresh | nothing has changed | **refuse the transition.** There is no partial state, so there is nothing to explain and nothing to undo. |
| 2 move | the folder may have moved | today's behaviour, unchanged |
| 3 commit | moved, uncommitted | today's behaviour: `TransitionCommitError`, no rollback |
| 4 publish | moved and committed locally | **report it, exit non-zero, change nothing back** |

Step 4 follows a precedent already in this file. `_commit_transition`
(`tcw/store/fs.py:4213-4217`) refuses to roll back a landed `git mv` when the
commit fails, in its own words: _"undoing it introduces a second failure mode
worse than the first — so the error says the item moved and the commit did not."_
A failed push is that situation one step further out and gets the same treatment
for the same reason.

**Refresh is fast-forward only.** `FsStoreProvisioner._refresh`
(`tcw/store/fs.py:2893-2909`) already fetches and then `merge --ff-only`, never
`pull`. Divergence therefore surfaces as a refused fast-forward at step 1 —
before anything moves — rather than as an automatic merge commit in someone's
work store. That is the whole divergence design, and it is inherited rather than
built.

**A push contacts only the declared remote.** `_require_declared_checkout`
(`2861-2891`) already verifies a checkout's `origin` against the declaration
before any fetch, precisely because a `checkout` directory is arbitrary and can
hold an unrelated repository. A push needs that check at least as much, and
reuses it.

### C. Where publication lives

Per the initiative spec's litmus table, publication is **a property of the store,
not a verb on each transition**. Three additions to the `WorkStore` ABC
(`tcw/store/base.py:1615`):

- `publishes` — whether writes to this store are published anywhere.
- `refresh()` — bring this store up to date with wherever it comes from.
- `publish()` — make this store's committed writes visible to others.

`_effect_transition` calls `refresh()` first and `publish()` last, both guarded by
`publishes`. The filesystem adapter realizes them as fetch/ff-merge and push; a
tracker-backed store answers `publishes = True` with both methods as no-ops,
because a tracker write is published by definition.

### D. Turning it off

`work.publish-transitions`, mirroring `work.auto-commit-transitions`
(`tcw/store/fs.py:3658-3666`) exactly — including its rule that a non-boolean
reads as the default rather than as false, for the reason given there: a typo
silently disabling the mechanism is worse than one that is ignored, because
nothing looks wrong until someone notices.

Default **true**. A provisioned store exists only because someone ran
`tcw provision`, which is already an explicit opt-in to the declaration; a
default of false would mean nobody gets the feature without a second opt-in they
have no reason to know about.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| `WorkStore.publishes` | **Model.** "Are writes here visible to anyone else?" is a question every backing store answers — trivially `True` for a tracker, conditionally for a filesystem store. |
| `WorkStore.refresh()` | **Model / store interface.** "Bring yourself up to date with your source of truth" has an analog in any store: a fetch, a cache invalidation, or a no-op for a store that is never stale. |
| `WorkStore.publish()` | **Model / store interface**, as the litmus table in the initiative spec already ruled. A tracker's write is published by definition, so a no-op is a legitimate implementation rather than a stub. |
| Fetch, `merge --ff-only`, `push`, `origin` comparison | **Filesystem-adapter private detail.** No signature above names a remote, a ref, or a branch. |
| Which ladder rule resolved the store | **Filesystem-adapter private detail.** `publishes` is the abstract question; "rule 2 produced me" is how one adapter answers it. |
| `work.publish-transitions` | **No new operation.** Node configuration, read the way `auto-commit-transitions` already is. |
| Refusing a transition when refresh fails | **Model.** "This write cannot proceed" is a store-level refusal; that the reason is a diverged Git history is the adapter's business. |

Nothing here requires the store to be a filesystem. The place the filesystem
shows through — what refresh and publish physically do — is inside the adapter
behind abstract methods, which is where the prime directive puts it.

## Acceptance criteria

1. **A published transition is visible to a fresh provisioning.** After a
   transition on a provisioned store, provisioning the same declaration into a
   different directory shows the item in its new status.
2. **Nothing moves until the store is up to date.** A transition on a store whose
   remote has advanced sees the remote's state first; the refresh precedes any
   filesystem change.
3. **A refused refresh leaves the item exactly as it was** — same status, same
   folder, no commit, no partial write — and says why.
4. **A failed publish reports what landed and what did not, exits non-zero, and
   changes nothing back.** The item is in its new status locally and the message
   says so explicitly rather than implying failure of the whole transition.
5. **Divergence is reported, never merged.** A remote that has moved
   incompatibly produces a refusal naming the divergence; no merge commit is
   created in the store repository under any circumstances.
6. **Only a store that publishes performs any network operation on a transition,
   and only at steps 1 and 4.** Asserted as a property over the whole transition
   surface — every status-changing command, not one of them — in the shape of the
   package-wide rule in `tests/test_subprocess_stdin.py`.
7. **A store that does not publish is byte-for-byte unchanged.** No new network
   call, no new failure mode, no new configuration required, for every ladder rule
   in section A that does not publish. The existing suites pass with no test
   rewritten to accommodate this work.
8. **A push contacts only the declared remote**, verified against the declaration
   before the push, and refuses rather than contacting an unexpected one.
9. **`work.publish-transitions: false` disables steps 1 and 4 entirely**, and a
   non-boolean value reads as the default rather than as false.
10. **Git is invoked with stdin closed** for every new network call, so a remote
    demanding credentials fails rather than hanging.
11. **Every criterion is reproducible from a bare shell**, with no Claude hook and
    no slash command involved.

### Coverage

Two numbered lists in the Design section, so two tables. A cell is the test that
covers it, or `n/a` with the line that makes it so.

**Criteria × section A (which stores publish).** Rules 2 and 3 are the row that
must be provably empty, not assumed empty.

| # | A1 rule-2 (publishes) | A2 rule-1 (declared, unused) | A3 rule-4 (no declaration) | A4 disabled by config |
| - | --- | --- | --- | --- |
| 1 | `test_a_transition_reaches_the_remote` | n/a — A2 does not publish, so there is nothing to be visible; covered instead by 7 | n/a — same, via 7 | n/a — same, via 9 |
| 2 | `test_the_refresh_precedes_any_filesystem_change` | n/a — via 7 | n/a — via 7 | n/a — via 9 |
| 3 | `test_a_refused_refresh_leaves_the_item_untouched` | n/a — via 7 | n/a — via 7 | n/a — via 9 |
| 4 | `test_a_failed_publish_says_what_landed` | n/a — via 7 | n/a — via 7 | n/a — via 9 |
| 5 | `test_divergence_is_refused_not_merged` | n/a — via 7 | n/a — via 7 | n/a — via 9 |
| 6 | `test_only_steps_one_and_four_touch_the_network` | `test_no_transition_on_a_non_publishing_store_touches_the_network[rule-1]` | `…[rule-4]` | `…[disabled]` |
| 7 | n/a — 7 is about the stores that do **not** publish | `test_a_non_publishing_store_is_unchanged[rule-1]` | `…[rule-4]` | `…[disabled]` |
| 8 | `test_a_push_verifies_the_remote_before_contacting_it` | n/a — via 7 | n/a — via 7 | n/a — via 9 |
| 9 | `test_publication_can_be_switched_off` | n/a — nothing to switch off | n/a — nothing to switch off | the criterion itself |
| 10 | `test_subprocess_stdin.py` (package-wide) | covered by the same package-wide rule | same | same |
| 11 | bare-shell walk, recorded in `outcome.md` | same | same | same |

**Criteria × section B (the transition sequence).**

| # | B1 refresh | B2 move | B3 commit | B4 publish |
| - | --- | --- | --- | --- |
| 1 | `test_a_transition_reaches_the_remote` | — | — | `test_a_transition_reaches_the_remote` |
| 2 | `test_the_refresh_precedes_any_filesystem_change` | asserted by the same test, as the ordering's other half | n/a | n/a |
| 3 | `test_a_refused_refresh_leaves_the_item_untouched` | asserted by it (nothing moved) | asserted by it (no commit) | n/a — never reached |
| 4 | n/a — step 1 succeeded | asserted by `test_a_failed_publish_says_what_landed` (item moved) | asserted by it (commit landed) | `test_a_failed_publish_says_what_landed` |
| 5 | `test_divergence_is_refused_not_merged` | asserted by it (nothing moved) | n/a — never reached | n/a — never reached |
| 6 | `test_only_steps_one_and_four_touch_the_network` | asserted by it: **zero** network calls at step 2 | asserted by it: zero at step 3 | asserted by it |
| 7 | `test_a_non_publishing_store_is_unchanged` — step 1 does not run | unchanged from today: `_effect_transition` `fs.py:4154-4202` | unchanged: `_commit_transition` `fs.py:4204-4222` | step 4 does not run |
| 8 | n/a — refresh already verifies, `_require_declared_checkout` `fs.py:2861-2891` | n/a | n/a | `test_a_push_verifies_the_remote_before_contacting_it` |
| 9 | `test_publication_can_be_switched_off` — step 1 skipped | n/a | n/a | asserted by it — step 4 skipped |
| 10 | package-wide rule | n/a — no subprocess | n/a — no network | package-wide rule |
| 11 | bare-shell walk | bare-shell walk | bare-shell walk | bare-shell walk |

**What the tables surfaced, before any code was written.**

Filling them changed the spec twice:

- **Criterion 7 had no meaning for column A1.** It was originally worded "a store
  that is not provisioned behaves exactly as today", which is a claim about three
  of the four columns and silent about the fourth. Reworded so its scope is the
  non-publishing rules, with criterion 6 carrying A1 — otherwise the row reads as
  covered while nothing checks the publishing case at all.
- **Criterion 5 × B3 and B4 are unreachable**, because divergence is detected at
  step 1. That is only true while refresh is fast-forward-only; if refresh ever
  learns to merge, those two cells become live and criterion 5 stops being
  checkable where it is written. Recorded as a risk below rather than discovered
  later.

The `n/a — via 7` cells are the ones to distrust at implement: they are load
bearing only if criterion 7's test really does parametrize over all three
non-publishing rules. If it covers one and is assumed to cover three, this table
is decorative — which is exactly the failure it exists to prevent.

## Risks

- **Refresh's fast-forward-only behaviour is load-bearing in a direction the code
  does not know about.** Criterion 5 is checkable at step 1 *because* refresh
  cannot merge. `_refresh` documents "no `pull`" as being about tags and commits,
  not about conflict semantics, so a future change could reasonably relax it and
  silently move divergence from a clean refusal into a merge inside a work store.
  Whatever this item builds should state the dependency where `_refresh` lives.
- **A network hop inside a state machine that is currently local and atomic** —
  the initiative spec's own words. Transitions today either happen or do not.
  After this they can happen locally and fail to publish, which is a state the CLI
  has never had to describe.
- **The pull half makes routine commands network-dependent.** `tcw work start` on
  a provisioned store now requires connectivity. This was the requester's explicit
  choice over a push-only design, and criterion 9's off switch is the mitigation.
- **`work.publish-transitions` defaulting true means an upgrade changes behaviour
  for anyone already using a provisioned store.** The population is small — the
  feature shipped in v1.1.0 — but it is not zero, and the release note has to lead
  with this rather than mention it.
- **Two working copies of one store on one machine can drift**, and publication
  makes the drift consequential rather than merely confusing: the cache clone
  publishes, the `work.path` copy does not. Section A makes which-one-publishes
  deterministic; it does not make the second copy go away.

## Notes

- The four numbered failure modes in section B are ordered by *when* they occur,
  not by severity, because when is what determines the answer. That ordering is
  what made the refuse/report asymmetry fall out rather than be chosen.
- The tree-store question was raised at this stage, briefly filed as a follow-up
  item, and then dropped once the reasoning above was worked out: it is not
  deferred work, it is a thing that should not be built.
- This is the first spec written under the `### Coverage` requirement added after
  the post-mortem on children A and B. Two observations for
  [the upstream item](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage):
  the grid genuinely did surface two defects on paper, and splitting one 11 × 4 × 4
  cube into two 11 × 4 tables was necessary — a single combined table would have
  been 176 cells and nobody would have read it. If the rule is upstreamed it must
  say to cross against each numbered list separately.
