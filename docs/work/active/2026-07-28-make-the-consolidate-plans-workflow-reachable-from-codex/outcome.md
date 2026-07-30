# Outcome — Make the consolidate-plans workflow reachable from Codex

Six commits, one per plan task plus a budget fix and the documentation-sync pass.
No design change from the plan; two documents were corrected in place (below).

## What shipped

| Task | Commit | Subject |
|---|---|---|
| 1 | `eb340ea` | `feat(consolidate-plans): move the procedure into the tcw-work skill, gated` |
| 2 | `fbc206b` | `refactor(consolidate-plans): reduce the command file to frontmatter plus a pointer` |
| 3 | `5ec2558` | `docs(consolidate-plans): point the three doc sites at the new reference` |
| 4 | `ad7d2ef` | `feat(work)!: require --confirm on tcw work drop` |
| 5 | `ea965f0` | `caps(consolidate-plans): body works under either harness; record both deltas` |
| 5a | `6b53b82` | `fix(tcw-work): keep the router inside its 60-line budget` |
| sync | `08c26a2` | `docs: changelog and release notes for the consolidate-plans move and drop --confirm` |

**Task 1** — `skills/tcw-work/references/consolidate-plans.md` (new). The
procedure from `commands/tcw-consolidate-plans.md:6-37` carried over in substance,
opened the way `audit-backlog.md:3-6` does, with the two gates placed **before**
any procedural step and the recoverability rule as its own section. Created with
its gates in the same commit — the reference has never existed ungated in a
committed state.

**Task 2** — `commands/tcw-consolidate-plans.md` reduced to frontmatter plus a
pointer, the `tcw-audit-work-backlog` shape. `disable-model-invocation: true`
retained. The file was not deleted; `/tcw-consolidate-plans` still exists.

**Task 3** — `skills/tcw-work/SKILL.md` gate line; `commands.md`'s row rewritten
to the audit row's `any harness ·` format; `README.md:765-769` rewritten to drop
the Codex note and state both new safety properties.

**Task 4** — `--confirm` on `tcw work drop` (`tcw/work/cli.py:909-928`, subparser
at `:1071`). Without it: prints `Would delete <slug> (<locate()>)`, refuses on
stderr, exits 1, deletes nothing. `tests/test_work.py::test_drop_refuses_without_confirm`
pins both directions. **Four doc sites carried the old syntax and were updated**
— `skills/tcw-work/references/transitions.md:117`, `commands.md:15`,
`README.md:658`, and `docs/capabilities/work/drop-a-work-item/description.md`.

**Task 5** — `docs/capabilities/work/consolidate-plans/description.md`: the
harness claim replaced with "works the same under either harness" (the sibling's
wording, `audit-work-backlog/description.md:4-5`), and the surviving confirmation
sentence extended with the grouped-approval and recoverability guarantees now
backing it. Confirmed spec D8 still holds: the body names no
`tcw work consolidate-plans` verb, so the phantom verb was not re-fixed.
`capabilities.yaml` created (planning wrote none) recording both changed entries.

## Test result

```
1161 passed in 167.54s (0:02:47)
```

Baseline was 1062 at the sibling item's close and 1160 immediately before this
item; +1 is `test_drop_refuses_without_confirm`. `tcw validate` → `validate OK`,
`tcw capabilities check` → `capabilities OK`.

**One intermediate failure, fixed in `6b53b82`.** Adding a `consolidate-plans.md`
bullet to the router pushed `SKILL.md`'s body to 61 lines against a 60-line
budget:

```
E       AssertionError: SKILL.md body is 61 lines, budget is 60 — extract, don't grow
tests/test_skill_lifecycle_parity.py:191: AssertionError
```

The rule on breach is "extract, never grow", so the two AI-driven workflows now
share one bullet under the gate they share — *only when the user asks for it* —
rather than one bullet each. Both gate conditions survive; no line was added.

## Manual verifications

### 1. The Codex-reachability claim

`.codex-plugin/plugin.json` still carries `"skills": "./skills/"` and **no**
`commands` key (verified by reading the whole file — the only top-level keys are
`name`, `version`, `description`, `author`, `homepage`, `repository`, `keywords`,
`skills`, `interface`). The new reference is at
`skills/tcw-work/references/consolidate-plans.md`, inside that tree, and the
`tcw-work` router reaches it at `SKILL.md:66`:

```
- **Only when the user asks for it** — [`audit-backlog.md`](references/audit-backlog.md): reviewing the whole backlog for stale, duplicate, or misplaced items · [`consolidate-plans.md`](references/consolidate-plans.md): migrating planning documents from outside `docs/work/` into work items, then deleting the sources
```

What a Codex agent sees: the `tcw-work` skill loads, its "Read on demand" list
names `consolidate-plans.md` with a gate it can evaluate ("the user asked for
it"), and following the relative link reaches the full procedure — discovery
scope, classification, item creation, artifact mapping, source→slug report, both
safety rules. Nothing on that path passes through `commands/`.

### 2. The two gates are in the reference, at the top

Both appear under `## The two rules, before any step`, ahead of `## Scope` and
`## Process`:

> **Start only when asked.** Do not begin a consolidation run on your own
> initiative — not while doing adjacent work in `docs/`, not as a tidy-up pass,
> not because you noticed a stray `plans/` folder. The user asks for it, or it
> does not run.
>
> **Never delete a source without a grouped, itemized approval.** Present every
> document proposed for deletion by path, with its destination slug, as **one**
> ask covering the whole run. Not one ask per file — that is unusable on a real
> run — and not a blanket "may I clean up?", which is a yes to decisions the user
> has not seen. Deletion happens after the answer, never before.

### 3. The recoverability checks are runnable

Throwaway repo under the scratchpad, three files in the three states:

```
committed.md   ls-files: tracked(exit 0)            status --porcelain: []
modified.md    ls-files: tracked(exit 0)            status --porcelain: [ M modified.md]
untracked.md   ls-files: UNTRACKED(exit non-zero)   status --porcelain: [?? untracked.md]
```

The two checks separate all three cases exactly as the reference's table claims:
only `committed.md` passes both, and it is the only one git could give back.

### 4. `/tcw-consolidate-plans` still resolves

Frontmatter parses and retains the flag:

```
{'description': 'Find planning documents outside TCW work, migrate them into TCW work items, and remove the old documents after successful migration.', 'disable-model-invocation': True}
```

The link target resolves (`commands/../skills/tcw-work/references/consolidate-plans.md`
exists, 3219 bytes) and no copy of the procedure remains in the command file
(`grep -c "tcw work new"` → `0`).

### 5. Task 4's own verification (throwaway repo)

```
--- help ---
usage: tcw work drop [-h] [--confirm] slug
options:
  -h, --help  show this help message and exit
  --confirm
--- without --confirm ---
Would delete 2026-07-30-a-mistake (docs/work/backlog/2026-07-30-a-mistake)
Refused: dropping 2026-07-30-a-mistake erases it outright and leaves no record. Re-run with --confirm.
exit=1
--- item still there ---
2026-07-30-a-mistake | backlog | R | - | a mistake
--- with --confirm ---
dropped 2026-07-30-a-mistake
exit=0
--- board now ---
```

(The two lines under "without `--confirm`" arrive on stdout and stderr
respectively and interleave by buffering; the ordering above is the logical one.)

### 6. AC6's standing assertion, re-read

`commands.md:50` says "Nothing is only available through a command." All 13 files
in `commands/` link into `skills/`:

```
OK   commands/tcw-audit-work-backlog.md      OK   commands/tcw-plan-work.md
OK   commands/tcw-capabilities-init.md       OK   commands/tcw-post-mortem.md
OK   commands/tcw-consolidate-plans.md       OK   commands/tcw-process-inbox.md
OK   commands/tcw-cut-version.md             OK   commands/tcw-taxonomy-init.md
OK   commands/tcw-docs-sync-setup.md         OK   commands/tcw-triage-issues.md
OK   commands/tcw-doctor.md                  OK   commands/tcw-verify-work.md
OK   commands/tcw-drive-work-to-completion.md
```

The sentence was false for weeks; it is true now.

## Acceptance criteria

| # | Status | Evidence |
|---|---|---|
| 1 | **met** | `skills/tcw-work/references/consolidate-plans.md` carries discovery scope + exclusions, the three-way classification, `tcw work new`, the artifact mapping, and the source→slug report. Command file holds none of it (verification 4). |
| 2 | **met** | Verification 2, first rule, above `## Scope`. |
| 3 | **met** | Verification 2, second rule, plus `## Deletion is limited to what git can give back` with the two named checks — both as their own headed prose, not implied. |
| 4 | **met** | Verification 4: 12 lines, frontmatter + pointer, `disable-model-invocation: True`. |
| 5 | **met** | `SKILL.md:66`, gate = *only when the user asks for it*. Shares the bullet with `audit-backlog.md` (see the budget failure above) — the spec expected its own line; the gate condition it required is present either way. |
| 6 | **met** | `commands.md:33` now `[consolidate-plans.md](consolidate-plans.md) — any harness · /tcw-consolidate-plans in Claude`; line 50 re-read and true (verification 6). |
| 7 | **met** | `README.md:765-770` — no Codex note; "the procedure lives in the `tcw-work` skill, so it works under either harness". |
| 8 | **met** | Body drops the line, states either harness, and the confirmation sentence survives and now names the grouped approval and the git limit. `tcw capabilities check` → OK. |
| 9 | **met** | `.codex-plugin/plugin.json` unmodified (verification 1). `tcw work drop --confirm` is a **flag**, not a verb; `tcw work --help`'s verb list is unchanged. |
| 10 | **met** | 1161 passed; `tcw validate` OK. |

**Task 4's own criteria** (plan `:114-118`): drop without `--confirm` exits
non-zero and deletes nothing — verified above; with `--confirm` behaves as before
— verified; a test pins both directions —
`tests/test_work.py::test_drop_refuses_without_confirm`; the one existing caller
(`test_drop_via_qualified_slug`, `tests/test_work.py:1595`) had `--confirm`
added. **That test edit is a legitimate interface change**, not the
"no test may be modified" violation the sibling items in this batch guard
against: the flag *is* the change, so a test asserting the old call signature is
asserting the behavior being replaced. No assertion was weakened — the same test
still asserts exit 0 and the item's disappearance.

## The `tcw serve` drop path

`tcw/serve/__init__.py:1250-1268` exposes `DELETE /api/work/<slug>` → `work.drop(slug)`
with no confirmation parameter. **A CLI-only gate would be theatre if the web
editor deleted silently — it does not.** `web/client/src/ui/app.tsx:963-975`
puts a Radix `AlertDialog` in front of it ("Drop Work Item … This permanently
drops <slug>"), and `web/e2e/parity.spec.ts:580` ("drops a backlog Work item
through the confirmation modal") holds that in place. The confirmation exists on
both surfaces at the layer facing the user; the HTTP verb itself is an
already-explicit `DELETE`.

**Decision: in scope, nothing to change.** Adding a `?confirm=1` query parameter
would guard the API against a caller that must already construct a `DELETE` by
hand, while the actual user-facing path is covered. Recorded rather than deferred
— this is not a follow-up item.

## Corrections to the spec and plan

1. **`spec.md` Non-goals listed `tcw work drop --confirm` as out of scope.** The
   user folded it in on 2026-07-30 as plan task 4, so the spec and plan
   disagreed. Corrected in place (`spec.md`, Non-goals, in commit `ad7d2ef`):
   the entry is struck through and points at task 4.
2. **The plan's header says "Four tasks"; there are five.** Task 4 was appended
   without updating the count and task 5 exists below it. Not edited — the task
   bodies are unambiguous and the count is cosmetic. Noted here so a reader of
   the plan alone is not misled.
3. **`SKILL.md` could not take a new "Read on demand" line.** Spec D7 and plan
   task 3.1 both assume adding one; the router's 60-line budget forbids it. The
   gate condition landed by merging bullets instead. The spec's AC5 wording ("its
   'Read on demand' list carries a line for `consolidate-plans.md` with a gate
   condition") is satisfied in substance, not literally — a shared line, not its
   own.
4. **Task 4's documentation footprint was larger than the plan named.** The plan
   named `transitions.md:111-113`; `commands.md:15`, `README.md:658`, and the
   `work/drop-a-work-item` capability body also carried the flagless syntax. All
   four updated. The capability body change is why `capabilities.yaml` records
   **two** changed entries rather than the one the spec anticipated.

## Notes

- The spec's claim that `disable-model-invocation` appears in exactly two command
  files (`spec.md:276-281`) still holds after this change:
  `commands/tcw-consolidate-plans.md:3` and `commands/tcw-doctor.md:4`.
- Documentation Sync triggers fired: `skills/<component>/SKILL.md`
  [Skill-Driven-Component], `README.md` [Public-API],
  `docs/changelogs/upcoming.md` [Any-Code-Change], `docs/release-notes/upcoming.md`
  [Public-API] — all four, all answered in `08c26a2` (README in `5ec2558`/`ad7d2ef`,
  skills across `5ec2558`/`ad7d2ef`/`6b53b82`). No version cut; that is a closeout
  call.
