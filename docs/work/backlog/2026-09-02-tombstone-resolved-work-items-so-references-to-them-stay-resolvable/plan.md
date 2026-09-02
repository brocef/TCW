# Plan — Tombstone resolved work items so references to them stay resolvable

Nine tasks. The suite is green at every boundary: tasks 1–3 add mechanism
nothing reads yet, 4–7 switch readers onto it one at a time, 8 applies it to
this repository, 9–10 close the documentation and ledger.

**Settled during planning, and it removes a spec risk:** resolved statuses are
**terminal**. `tcw work start` and `tcw work rework` on a completed item both
refuse with `completed → active is not a legal transition`, and `rework` is
declared `review → active` only (`tcw/store/base.py:2186-2187`). So a tombstone
never has to be removed, and task 6 can refuse a tombstoned slug outright with
no resurrection case to handle.

**Also settled:** a `graveyard/` folder holding a YAML file inside the work
store does not trip `tcw validate` (checked on a scratch node — `validate OK`).
No bounds work is needed.

---

## Task 1 — The tombstone record and the abstract read

**Files.** `tcw/store/base.py` — a frozen `Tombstone` dataclass (`slug`,
`resolution`, `resolved`), and a `WorkStore.tombstone(slug) -> Tombstone | None`
abstract method beside `get` (:1696). `tcw/store/fs.py` — `FsWorkStore.tombstone`,
reading `<store root>/graveyard/<slug>.yaml` through the tolerant `_safe_yaml`
(:3558-3561). `tests/test_tombstone.py` — new.

**Proves.** An entry written into `graveyard/` by hand comes back with its three
fields; an absent slug returns `None`; malformed YAML returns `None` rather than
raising, matching `_safe_yaml`'s stated degrade-don't-crash rule. Full suite
green — `FsWorkStore` is the only concrete `WorkStore`, and
`tests/test_stage_verb.py:206` only introspects the class rather than
subclassing it, so a new abstract method breaks nothing.

**No locator field.** Omitted by decision (see spec Non-goals), not oversight.

## Task 2 — Completing and discarding record a tombstone

**Files.** `tcw/store/fs.py` — `_effect_transition` (:4431): when `to_status` is
in `RESOLVED_STATUSES`, write the tombstone before the move, and add
`graveyard/<slug>.yaml` to the commit pathspec. `tests/test_tombstone.py`.

**Why there.** `_effect_transition` is the one primitive every resolving route
passes through: the normal path via `transition` (`base.py:2115`) and the
backlog-epic bypass (`base.py:2265`). `start`'s separate claim-based path
(fs.py:3901-3903) never targets a resolved status, so it needs no hook.

**Proves.** After `complete --resolution done`, `graveyard/<slug>.yaml` records
`done`; a discarding resolution records that resolution with the item in
`discarded/`; the backlog-epic route records one too; and `git show --name-only`
on the transition commit contains the tombstone — the assertion that it reaches
another clone at all, which is the whole point.

**Watch.** The commit stays scoped — pathspec becomes `{item folder,
graveyard/<slug>.yaml}`, both item-specific, so the promise in
`work/complete-a-work-item` that unrelated working-tree edits are never swept in
still holds. Assert it: an unrelated dirty file is not in the transition commit.

## Task 3 — `tcw work tombstone add`

**Files.** `tcw/work/cli.py` — handler plus subparser under `work`.
`tests/test_tombstone.py`.

**Proves.** Records an entry for a slug with no live item. Refuses non-zero and
writes nothing when the slug is live. Refuses a resolution outside
`done|wontfix|duplicate|superseded`. `--resolved` defaults to today and accepts
an explicit ISO date.

**Required, not convenience.** The four references failing in this repository
name items resolved before any graveyard existed; without this command spec
Goal 2 is unreachable. Deriving entries from git history instead would be the
"reconstruct state from history" trick the prime directive forbids.

## Task 4 — References resolve through the tombstone

**Files.** `tcw/refs.py` — the `store.get(bare) is None` branch (:132-134):
consult `tombstone()` before failing, returning success carrying the resolution.
`tests/test_refs.py`.

**Proves.** `tcw://W/<slug>` for a tombstoned slug resolves; for a slug that
never existed it still fails with today's wording (spec criterion 3). **The
litmus check:** a stub exposing only `get()` and `tombstone()` — no filesystem
anywhere — drives the same resolution, demonstrating the resolver needs nothing
storage-specific and that spec criterion 10's second half holds in code.

## Task 5 — `tcw validate` is reproducible across checkouts

**Files.** `tests/test_validate.py` only — the behaviour falls out of task 4;
this task exists because the headline criteria are unproven without it.

**Proves.** Spec criteria 1 and 2: build a node, complete an item that a tracked
file references, then assert `tcw validate` exits **0** both in place and in a
`git clone` of that repository — the two-verdict split reproduced in the spec is
gone. Also asserts an unknown slug still fails in both.

## Task 6 — Slug assignment never reuses a resolved slug

**Files.** `tcw/store/fs.py` — `_unique_slug` (:3552), whose
`while self._find(slug) is not None` sees live items only; also reject a slug
with a tombstone. `tests/test_work.py`.

**Proves.** In a clone with no `completed/` folder, creating an item whose date
and title would generate a tombstoned slug yields a **suffixed** slug. The same
test against today's code yields the identical slug, silently repointing every
existing reference — run it before the fix to watch it fail.

## Task 7 — `tcw serve` renders an archived target

**Files.** `tcw/serve/__init__.py` — `/api/resolve` (the handler near :969).
`tests/test_serve_resolve.py`.

**Proves.** The payload marks a tombstoned target as resolved-and-archived,
carrying its resolution — not an error, not a live link. Consistent with the
existing off-board treatment, so a reference `tcw validate` accepts never renders
as broken in the viewer.

## Task 8 — Backfill this repository and unblock completion

**Files.** `docs/work/graveyard/*.yaml` — four entries, **written by
`tcw work tombstone add`**, never by hand.

**Proves.** Spec criterion 9: `tcw validate` exits 0 in this repository, and
`tcw work complete 2026-09-02-restore-the-ci-test-suite-to-green --resolution
done --confirm` — refused today by its own `pre` hook — succeeds. That last
step is the end-to-end demonstration that the gate is unbricked.

**The four slugs** are those named by the current `tcw validate` output:
`2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it`
and `2026-08-26-publish-provisioned-store-writes-to-their-remote`; re-run
`tcw validate` at task time for the live list rather than trusting this one.

## Task 9 — Capability ledger reconciliation

**Files.** the capabilities store, via `tcw capabilities` commands.

**Proves.** The four amendments the spec planned are applied — `cli/validate-a-node`
(cap-2bd014), `cli/reference-a-tcw-object` (cap-65e549),
`work/complete-a-work-item` (cap-24543d), `work/discard-a-work-item` — each
still **Supported**, no new capability, no status flips. `tcw capabilities check`
and `tcw capabilities drift` both clean.

## Task 10 — Documentation Sync

Every declared entry, evaluated as one pass over the finished diff. All four
triggers fire.

- **`README.md`** — [Public-API] **fires.** `tcw work tombstone add` is a new
  public CLI command; add it to the work command listing.
- **`docs/release-notes/upcoming.md`** — [Public-API] **fires.** Plain language:
  references to finished work stop being reported as mistakes; validate now
  gives the same answer in every checkout; existing repositories need
  `tcw work tombstone add` to backfill before they see the benefit; a new
  `graveyard/` directory appears and is kept permanently.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change] **fires.** Grouped
  Added/Fixed/Internal, naming the abstract method, the `_effect_transition`
  hook, the `_unique_slug` collision, and the two negative sweep results.
- **`skills/tcw-work/SKILL.md`** — [Skill-Driven-Component] **fires.** The work
  component's CLI surface changes, so the skill and its
  `references/commands.md` and `references/transitions.md` gain the new command
  and the fact that resolving an item records a tombstone.

---

## Verification

What the suite cannot check, to be done by hand at `implement`:

1. **The prime directive, as review not test.** Read the finished
   `WorkStore.tombstone` signature and docstring: it must not mention a file, a
   path, a commit, or git (spec criterion 10, first half). A test asserting
   word-absence would be brittle theatre; task 4's stub-store test covers the
   half that *is* mechanizable.
2. **Codex parity.** Confirm every new behaviour is reachable from the `tcw`
   CLI alone, with nothing carried by a Claude hook or injected context.
3. **The real end-to-end.** Task 8 run against this repository is itself the
   verification that the gate is unbricked; record its output rather than
   asserting it.
4. **CI on both legs** (spec criterion 11) — green on 3.11 and 3.14, which only
   the runner can settle.
5. **A judgment call for the user at review:** whether `graveyard/` should be
   gitignorable at all. This plan makes it tracked unconditionally, because an
   ignorable graveyard reproduces the exact defect one level up. Worth confirming
   that is wanted before it ships.

## Notes

- **Naming**, left open by the spec and settled here: `Tombstone` /
  `tombstone()` for the model, `graveyard/` for the folder. The record is a
  tombstone; the place they live is the graveyard. If the requester prefers one
  word throughout, change it in task 1 before anything depends on it.
- Task 6 is the only task fixing a *silent wrong answer* rather than a noisy
  one, and it is sequenced after the mechanism it needs but before the
  documentation pass, so it cannot be dropped for time.
- `tests/test_tombstone.py` is new and carries tasks 1, 2 and 3; tasks 4–7 add to
  existing suites. That keeps the new mechanism's tests in one readable place
  and the reader-integration tests beside the readers they change.
