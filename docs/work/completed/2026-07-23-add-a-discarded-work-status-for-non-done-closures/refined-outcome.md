# Refined outcome

## Verification decision

User verified and approved closeout. Resolution: `done`.

## Refinements made after the initial implementation

Three follow-ups were raised in `outcome.md` rather than acted on unilaterally;
the user directed that all three be addressed in-item instead of deferred to
backlog items.

### 1. Blockers no longer gate a discard — a deliberate spec divergence

The approved spec had unresolved blockers gating both closure routes. Reviewing
the shipped behavior, that was wrong, and it is the one place this item diverges
from the design the user signed off on.

The gate's purpose is "don't claim you shipped this while its dependency is
unfinished." That says nothing about giving up — and being blocked indefinitely
is one of the most common reasons to abandon work. Requiring `--force` to
discard a blocked item put friction on exactly the path the `discarded` status
exists to remove. `complete()` now evaluates blockers only when
`dest == "completed"`.

The **epic open-children gate deliberately still applies to both routes**. That
asymmetry is not an oversight: an initiative child cannot start until its epic is
active, so closing an epic by either route strands its open children. Pinned by
`test_blockers_gate_a_completion_but_not_a_discard` and
`test_epic_children_gate_applies_to_a_discard_too`.

### 2. Repo-wide formatting drift cleared

`pnpm prettify:check` had been failing on 25 files before this item — verified
pre-existing by stashing all work and confirming the failing set was
byte-identical with and without the changes. The user chose to format them
rather than extend `.prettierignore`. `prettify:check` now passes repo-wide for
the first time.

### 3. Web status vocabulary deduplicated

`WORK_STATUSES` now has one definition in `web/client/src/model/types.ts`.
`WORK_STATUS_ORDER` stays a separate export in `model/tree.ts`, because display
precedence (live work first, closed work last) is a genuinely different concern
from the canonical vocabulary — with a test asserting the order map covers every
status so the two cannot drift when a fifth status appears.

**This surfaced a bug introduced earlier in this same item.** The sort's
unknown-status fallback was a hard-coded `3`, which meant "after everything"
while there were three statuses but silently tied with `discarded` once it took
index 3. Now `WORK_STATUS_ORDER.size`. Caught only because deduplication forced
a second look at the constant — worth noting as evidence that the follow-up was
more than cosmetic.

## Final verification

```
python -m pytest        733 passed   (568 before this item)
pnpm vitest run          43 passed
pnpm prettify:check      clean  (repo-wide, for the first time)
pnpm typecheck           clean
tcw taxonomy check       taxonomy OK
tcw capabilities check   capabilities OK
tcw capabilities drift   no capability drift
tcw validate             validate OK
git diff --check         clean
```

## Closeout decisions

- **Completion route:** direct on `main`. No worktree or branch was used, so
  there is nothing to merge and no PR.
- **Version bump:** none, by explicit user decision. Changelog and release-note
  entries remain in `docs/changelogs/upcoming.md` and
  `docs/release-notes/upcoming.md` for whichever release picks them up. The
  migration guide is named `docs/migration-guide-0.14.X-to-0.15.0.md` on the
  assumption that the next release is a minor — **rename it if that changes.**
- **Documentation:** all four Documentation Sync triggers fired and were
  satisfied (README, release notes, changelog, `tcw-work` skill + its two
  lifecycle references), plus the migration guide.
- **Follow-up items:** none created. All three follow-ups were resolved inside
  this item.
- **Capabilities:** `work/discard-a-work-item` flipped `Missing` → `Supported`;
  `work/drop-a-work-item`, `work/complete-a-work-item`, `work/view-the-board`,
  and `web/editing` updated to shipped behavior.

## Carried forward

Not follow-ups for this item, but constraints the next two items in this
sequence inherit:

- `2026-07-23-capability-first-lifecycle-…` adds a capability/tests attestation
  to the completion gate. It attaches to the **`done` route only** — the discard
  route has no Definition-of-Done checklist to extend.
- `2026-07-22-planning-agnostic-tcw-lifecycle-orchestration` freezes a `complete`
  checkpoint contract. That checkpoint now has two destinations and two gate
  sets, and its stated non-goal "no new work statuses" predates this item.
- `2026-07-23-emit-new-location-when-cli-commands-move-a-tcw-object` assumes in
  its `plan.md` that `complete` moves an item to `completed/`. That is now
  resolution-dependent, so that plan needs a refresh before implementation.
