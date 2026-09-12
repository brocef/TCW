# Plan — Supplement filesystem TCW work with an external tracker bridge

An epic's plan is a **coordination plan**. It creates no code. Its tasks settle
the shared prerequisites, create the five children with their ordering recorded
as blockers, and define the checkpoints at which the initiative is re-read.
Every code task lives in a child's own `plan.md`.

Run every command from the primary checkout, not from a worktree.

**Revised 2026-09-12 after a three-way review** (this session, Codex, and a local
model). Ten findings were accepted, three narrowed, four rejected. The largest
structural change: the Jira experiment moved from seventh to first and became a
blocker, and the capability seeding moved out of the children into this plan.

## Task 1 — Run the Jira claim experiment, before anything else

**This is the first act of the epic and it can invalidate C2 entirely.** The
single-winner guarantee rests on a belief nothing in this repository proves: that
the configured claim transition cannot be applied twice. Goal 1 is the top goal.
The experiment needs no TCW code, so there is no reason for it to wait.

Observe two things, not one:

1. **The static property, which is the one that actually matters.** Apply the
   claim transition to a ticket, then attempt the *same* transition again from the
   state it landed in. Record the exact status code and response body. If the
   transition is still available, serialization buys nothing — a loser that
   retries also claims — and the claim boundary has to be redesigned.
2. **The race property.** Two simultaneous transition requests on one issue.
   Record which wins, and the exact shape of the loser's response, since C2 must
   translate it into "already claimed" rather than retrying it as transient.

Record both in this item's folder as `jira-claim-experiment.md`, with the date,
the instance, the issue key, and the verbatim responses.

**If the static property does not hold**, stop and bring the result back: the
claim boundary is redesigned before C2 is specced, and the candidate redesign is
a configured guard state plus a `tcw validate` assertion that the claim
transition is unavailable from the state it lands in. That assertion extends
criterion 9 and is cheaper and stronger than depending on race behavior.

Owner: whoever runs this epic's first session. Proves it:
`jira-claim-experiment.md` exists and quotes both responses verbatim.

## Task 2 — Start the epic

An initiative child cannot start until its epic is active
(`tcw/store/base.py:2692`), so this precedes every child's work.

```sh
tcw work start 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge
```

Proves it: `tcw work list --status active` names the epic, and
`tcw work show <epic>` prints `type: epic`. Check the second one — the type was
set by hand, no CLI verb maintains it, and the open-children gate at closeout
depends on it.

## Task 3 — Register the shared taxonomy Feature

All four planned capabilities name one Feature, and `tcw capabilities set` refuses
a `Feature` reference that does not resolve, so the Feature must exist before any
of them is written.

```sh
tcw taxonomy add "External work tracker" \
  "The coordination boundary between a project's TCW work store and an external tracker that owns ticket existence, assignment and claim state." \
  --kind feature --vocab work-item --vocab cli --vocab reference
```

Creates: one Feature entry in the taxonomy store (`tcw taxonomy path` resolves
where).

Proves it: `tcw taxonomy show external-work-tracker` prints `kind: Feature` with
all three vocabulary refs, and `tcw taxonomy check` exits zero.

## Task 4 — Create C1 and C2, the first delivery

Estimates are on every child deliberately. Without them the question "is five the
right decomposition" cannot be settled, and C1 is visibly the largest piece.

```sh
tcw work new "Configure an external tracker and read its tickets" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 70 --tag remote --tag work --tag cli \
  --effort high --complexity high

tcw work new "Claim an external tracker ticket and bind it to a work item" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 70 --tag remote --tag work --tag cli \
  --effort medium --complexity high
```

Then record the order and the experiment gate. `--initiative` carries no
dependency relation, so without the first command both read as workable at once:

```sh
tcw work edit <C2-slug> --blocked-by <C1-slug>
tcw work edit <C2-slug> --blocked-by "task 1 Jira claim experiment recorded in jira-claim-experiment.md"
```

The second is the enforcement for task 1. An external blocker is treated as
permanently unresolved (`unresolved_blockers`, `tcw/store/base.py:2648`), so
`start` refuses past it until someone removes it by name with `--unblocked-by`.
Task 1 was previously a task in a list that nothing forced to happen; now the tool
refuses C2 without it.

Proves it: `tcw work show <C2-slug>` lists `<C1-slug>` as a blocker **rendered as
a slug, not as `external: …`**. Read that carefully — a typo'd slug is silently
recorded as an external blocker rather than rejected (`_entry_for`,
`tcw/store/base.py:2526`), and every other check passes either way.

Do **not** use `tcw work start <C2-slug>` as the proof. If the gate fails to
refuse, C2 is `active`, and there is no `(active, backlog)` edge in
`LEGAL_TRANSITIONS` (`tcw/store/base.py:649`) — the only repair is hand-moving the
folder, which this repository's guide refuses. The gate is already covered by
`tests/test_work.py` and `tests/test_recursion.py`; re-proving it on the live
board buys nothing and risks an unrecoverable state.

## Task 5 — Create C3, C4 and C5

```sh
tcw work new "Synchronize the work lifecycle outward to the tracker" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 45 --tag remote --tag work --tag cli \
  --effort high --complexity high

tcw work new "Refuse local work that no claimed tracker ticket authorizes" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 40 --tag remote --tag work --tag cli \
  --effort medium --complexity medium

tcw work new "Surface an item's tracker binding in the board, the projection and the web app" \
  --initiative 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge \
  --priority 40 --tag remote --tag work --tag cli --tag web \
  --effort low --complexity medium
```

```sh
tcw work edit <C3-slug> --blocked-by <C2-slug>
tcw work edit <C4-slug> --blocked-by <C3-slug>
tcw work edit <C5-slug> --blocked-by <C2-slug>
```

C5 is blocked by C2 **only**, and that is now true rather than aspirational: the
sync-state indicator it used to carry moved into C3 during the review, so
everything C5 displays is produced by C2. Chaining it to C3 or C4 would be a false
blocker the tool then enforces.

Proves it: `tcw work show` on each of the three lists its blocker as a slug, and
`tcw work reconcile <epic>` lists five children with **Next** naming C1 alone.

## Task 6 — Seed all four capabilities now, not at each child's planning

**Moved here by the review, and the reason is the whole point of criterion 12.**
An absent `capabilities.yaml` reads as zero declared deltas
(`declared_capabilities` returns empty for a falsy value,
`tcw/store/base.py:303`) and the completion gate then reports no problems
(`tcw/work/recursion.py:43`). If the epic's sidecar is written only after every
child has seeded its own capability, the gate is **inert for almost the entire
life of the epic** — the fourth capability appears only after C3 completes, and
until then the epic is closeable over an untouched ledger, including through
`tcw work reconcile <epic> --complete-when-ready`. Seeding here, immediately after
tasks 4 and 5 supply the child slugs, arms the gate from the first day. It is the
same argument task 3 already makes for the shared Feature.

For each of the four:

```sh
tcw capabilities add <path> "<Name>" --status Missing
tcw capabilities set <path> --field "Planning doc=<child-slug>"
tcw capabilities set <path> --field "Feature=external-work-tracker"
tcw capabilities set <path> --field "Subject=work-item,cli,reference"
```

| Child | Capability path | Name |
| ----- | --------------- | ---- |
| C1 | `work/inspect-external-tracker-work` | Inspect external tracker work |
| C2 | `work/manage-external-tracker-intake` | Manage external tracker intake |
| C3 | `work/synchronize-external-tracker-work` | Synchronize external tracker work |
| C4 | `work/require-tracker-backed-work` | Require tracker-backed work |

C5 changes two existing capabilities rather than adding one, so it records
`work/read-a-work-item` and `work/open-a-work-item` under `changed:` in its own
`capabilities.yaml`.

Remember that seeding is one-way: `tcw capabilities` has no `rm` verb, so a
capability for a child that is later dropped ends as `Status: Omitted`.

Proves it: `tcw capabilities check` exits zero, and `tcw capabilities show <path>`
prints `Status: Missing` with the Feature and Planning doc set, for all four.

## Task 7 — Write the epic's own `capabilities.yaml`

Immediately after task 6, in the same session.

```yaml
new:
    - work/inspect-external-tracker-work
    - work/manage-external-tracker-intake
    - work/synchronize-external-tracker-work
    - work/require-tracker-backed-work
```

Modifies: the epic item's `capabilities.yaml` sidecar.

Proves it, and the command matters:

```sh
tcw work complete <epic> --resolution done --confirm
```

`--confirm` is required. Without it the Definition of Done gate refuses first
(`tcw/work/cli.py:1723`), before the capability gate ever runs
(`tcw/work/cli.py:1748`), and the refusal says nothing about capabilities — so the
check appears to pass while proving nothing. Require the message
`declared capabilities not reconciled:` naming **all four** paths. The open-children
gate will also refuse; read the text rather than the exit code.

## Task 8 — Rollup checkpoints

`tcw work reconcile <epic> --commit` before every coordination decision, after any
child status change, and before closeout. Pass `--commit`: `write_sidecar` writes
and *stages*, so a bare `reconcile` leaves a staged file in the index for someone
else to trip over.

1. After C1 completes — confirm C2 now reads as workable and nothing else does.
2. After C2 completes — **the decision point.** The first delivery is done. See
   task 10.
3. After C3 completes — re-read C4 against what C3 actually built; C4's drift
   check is C3's mechanism and its spec was written before that existed.
4. After C4 completes — confirm C5 is the only thing left.
5. After C5 completes — C5 is the only child that can complete out of order, so
   check the board rather than assuming.
6. Before closeout — every child resolved, then reconcile a final time.

## Task 9 — Re-check acceptance criterion 1 at every child's completion

Criterion 1 says a project with no tracker configured behaves exactly as it does
today, and no single child's suite can prove it stayed true after the next child
landed. At each child's `verify` stage:

```sh
python -m pytest -q
# Fails only if a line was REMOVED from tests/, which is where a weakened
# assertion shows up. A new test file only adds lines, so it passes.
git diff <child-branch-point>..HEAD -- tests/ | grep -q '^-[^-]' \
  && { echo "lines removed from tests/ — read them:"; \
       git diff <child-branch-point>..HEAD -- tests/ | grep '^-[^-]'; exit 1; } \
  || echo "no test lines removed"
```

**This check has now been wrong twice, so here is what each version got wrong.**
The first used `git diff --stat`, which exits zero whether or not files differ, so
it could never fail. The second used
`git diff --exit-code --quiet … || git diff … | grep '^-[^-]'`, and it fails on
exactly the clean addition its own comment claimed it passed: adding a test file
makes the first command exit non-zero, the `grep` then matches nothing and exits 1,
and the pipeline's status is the grep's. I built a throwaway repository, added one
test file, and measured it exiting 1.

The form above tests the one thing that matters — was any line removed from
`tests/` — and does not consult "did the directory change at all", which is true of
every honest child.

## Task 10 — Decide the end state before it arrives

The agreed first delivery is C1 plus C2. The plan previously said nothing about
what happens next, which left the epic open indefinitely with three children
blocking closeout and two capabilities nobody had committed to building. At
checkpoint 2, pick one, explicitly:

- **Keep the epic open** with a stated review date, C3 through C5 in backlog, and
  their capabilities left `Missing`. Honest only if someone actually intends to
  return; a `Missing` capability whose planning doc is a completed item is what
  `tcw capabilities drift` reports.
- **Close the epic after C2**, discard C3 through C5 into a successor epic, and
  mark their three capabilities `Omitted`. The epic's `capabilities.yaml` then
  names two paths, not four, and it must be edited before completion or the gate
  refuses.

The choice changes task 7's file, so it cannot be deferred past closeout.

## Open questions

Each needs a real answer; the first two block work.

1. **Does the Jira claim transition remain available from the state it lands in?**
   Task 1. Blocks C2. Owner: the epic's first session.
2. **Which Jira instance and credentials, and who has them?** Blocks task 1.
3. Does C1 depend on
   `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`
   landing first? Criterion 9 sits on exactly that surface. Answer at C1's spec.
4. Is `2026-09-10-let-a-node-declare-its-own-work-item-state-fields` the right
   vehicle for C5's projection problem, instead of a core `WorkItem` field for a
   feature most projects will not use? C5's spec must name it and say why not.
   Building both is the expensive outcome.
5. C1 and C2 are priority 70, above every other open item. Intended? What is being
   deferred to make room?

## Documentation Sync

**No trigger fires on the epic's own diff.** Not because the epic writes nothing —
tasks 3, 6 and 7 are ledger writes — but because none of the four configured
entries fires on a taxonomy or capability record. Checked against
`tcw-config.yaml` → `work.documentation`: the triggers are `Public-API`,
`Any-Code-Change` and `Skill-Driven-Component`, and a Feature or capability entry
is none of those.

Each child carries its own block. The table below is what this plan expects each
to schedule, so a missing entry at a child's plan stage is visible as a gap.

| Entry | Trigger | C1 | C2 | C3 | C4 | C5 |
| ----- | ------- | -- | -- | -- | -- | -- |
| `README.md` | Public-API | yes — configuration and two read commands | yes — import, link, unlink | yes — sync and the state indicator | yes — strict mode | yes — the new board fields |
| `docs/release-notes/upcoming.md` | Public-API | yes | yes | yes | yes | yes |
| `docs/changelogs/upcoming.md` | Any-Code-Change | yes | yes | yes | yes | yes |
| `skills/tcw-work/SKILL.md` | Skill-Driven-Component | yes — a gated reference for the tracker commands | yes | yes | yes | yes |

One judgment recorded here rather than five times: the skill entry says to update
the driving skill whenever the component's CLI surface, model, lifecycle or
guardrails change, and every child changes at least one. So the answer is `yes` in
every cell, and a child proposing otherwise has to argue for it.

The version cut is **not** per child. Batch it across the run and cut it when the
first delivery is publishable.

## Verification

What the test suite cannot settle, and who settles it.

1. **That Jira behaves as the claim design assumes.** Task 1, before any code.
2. **That two real clones cannot both claim one ticket.** The suite can prove two
   concurrent processes cannot. Two developers on two machines against one Jira
   project is a manual check at C2's verification.
3. **That no secret leaks.** Criterion 8's sentinel-token grep is automatable.
   What is not: a secret reaching a Jira comment or a log this repository does not
   own. Read the outbound payload construction by hand at C3's verification.
4. **That a non-developer can actually file a request.** Goal 2 is about a person.
   One real ticket filed by someone without a checkout, imported end to end, at
   C2's verification.
5. **That the epic's completion gate fires.** Task 7, with `--confirm`.
6. **That the binding is not trusted as proof of a claim.** Criterion 11. Write a
   binding by hand for an unclaimed ticket and confirm the next strict-mode
   mutation is refused on the tracker's answer.
7. **That no request can hang forever.** Risk 2. A timeout is only observable by
   pointing the client at something that accepts a connection and never answers;
   confirm at C1's verification that the CLI returns.

## Notes

**The first delivery is C1 and C2.** C3, C4 and C5 are ordered and no further. Do
not treat their boundaries in the epic spec as their specs; each still runs its own
`spec` stage, and checkpoints 2 and 3 exist because those boundaries were derived
from a request written before any of this was built.

**Child slugs are written as `<C1-slug>` and so on** because `tcw work new` mints
the date-prefixed slug and prints it. Substitute the printed slugs; do not guess
them.

**On citations.** Every `file:line` in this plan and in the spec was re-verified
after rebasing onto `main` on 2026-09-12. The first draft was grounded against a
worktree ninety commits behind `main`, and twelve of thirty-two citations had
already rotted — which is also how a review came to report a working command as
broken. Re-verify before executing, and read the symbol name next to each line
number rather than the number alone.

**A missing board row is not evidence.** `.gitignore:29` hides
`docs/work/completed/*`, so `tcw work list --all` cannot show resolved work in any
checkout. The first draft of the spec concluded a completed item was "stale" on
exactly that mistake.
