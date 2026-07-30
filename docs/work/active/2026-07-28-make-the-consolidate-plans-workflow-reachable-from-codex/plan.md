# Plan — Make the consolidate-plans workflow reachable from Codex

Four tasks. No Python changes: this is skill/command/doc motion plus two new
safety rules. The spec settled the safety question; this orders the work so the
migration is never half-done in a committed state.

Ordering rationale: task 1 creates the new home **with** its gates, so the
procedure never exists in `skills/` without the approval and recoverability rules
— a commit where the reference is reachable but ungated is exactly the safety
regression the request warned about, and this ordering makes that state
unreachable. Task 2 then reduces the command file, so `/tcw-consolidate-plans`
never points at nothing. Tasks 3 and 4 are documentation.

## Task 1 — create `skills/tcw-work/references/consolidate-plans.md`

**Changes:** new file. Content is `commands/tcw-consolidate-plans.md:6-37`
carried over verbatim in substance, plus the two additions below. Do **not**
redesign the procedure — same discovery heuristics, same document
classification, same artifact mapping (spec Non-goals).

Open the way `references/audit-backlog.md:3-6` does: state it is an AI-driven
workflow with no `tcw` verb, name the Claude slash command, and state that this
document is the procedure under any harness.

**The gate goes at the top, not the bottom** (spec D2), modeled on the approval
rule at `audit-backlog.md:125-138`:

- **Start only when asked.** Do not begin a consolidation run on your own
  initiative — not while doing adjacent work in `docs/`, not as tidy-up. This is
  the property `disable-model-invocation: true` gives Claude; written here, Codex
  gets it too.
- **Never delete without a grouped, itemized approval.** Every source document
  proposed for deletion, by path, with its destination slug, as **one** ask.
  Not per-file (unusable), not a blanket yes (`audit-backlog.md:129-134`).

**Recoverability rule** (spec D3) — this is where the real guarantee lands:
delete only files git has already committed, and only with `git rm`. A source
that is **untracked**, or tracked with **uncommitted modifications**, is reported
and left in place: its content exists nowhere else, so removing it is
unrecoverable. Name the two checks a third party can run —
`git ls-files --error-unmatch <path>` and `git status --porcelain <path>`.

This corrects `commands/tcw-consolidate-plans.md:34`, which says "use `git rm`
for tracked files" and thereby implies plain deletion for untracked ones — the
irreversible case.

**Verified by:** criteria pinning both rules' presence, and that the procedure
content survives the move.

## Task 2 — reduce `commands/tcw-consolidate-plans.md` to frontmatter + pointer

**Changes:** `commands/tcw-consolidate-plans.md`. Same shape as
`commands/tcw-audit-work-backlog.md:1-11`.

**`disable-model-invocation: true` STAYS.** Nothing about Codex parity requires
dropping it; keeping it costs nothing and leaves Claude's auto-invocation surface
strictly unchanged. Deleting the file entirely is also wrong — the slash command
would disappear and Claude's UX would regress for no gain.

The net-effect table from spec D5 is the acceptance bar: neither harness loses a
property, Claude gains two.

**Verified by:** the file still parses as a command, still carries the flag, and
points at the new reference.

## Task 3 — documentation sites (spec D7)

Four edits, all named with line numbers in the spec:

1. `skills/tcw-work/SKILL.md` — add a gate line for `consolidate-plans.md` to the
   "Read on demand" list (around `:66`). The gate condition must be clear enough
   that an agent knows when to open it, per the skill-authoring rule in
   `CLAUDE.md` (a router keeps always-relevant judgment inline and pushes rare
   sub-procedures behind a clear gate).
2. `skills/tcw-work/references/commands.md:27-33` — the "Not CLI subcommands"
   table says "**Two** workflows" and currently marks this one Claude-only.
   Update the count if it changes and rewrite the row to match the audit row
   (`:32`): `[consolidate-plans.md](consolidate-plans.md) — any harness ·
   /tcw-consolidate-plans in Claude`.
3. `skills/tcw-work/references/commands.md:50` — "Nothing is only available
   through a command" becomes **true** on completion. No edit needed; it is the
   assertion this item validates. Re-read it at verify rather than assuming.
4. `README.md:765-769` — drop "(This one is not yet reachable from Codex.)" and
   say the procedure lives in the `tcw-work` skill so it works under either
   harness, mirroring `README.md:762-763`. `README.md:114` lists
   `/tcw-consolidate-plans` among shipped commands and stays correct.

## Task 4 — add a `--confirm` gate to `tcw work drop`

**Folded in by the user's decision on 2026-07-30.** The spec listed this under
Non-goals as an adjacent observation belonging to no item; it is now in scope,
because it is the same subject as tasks 1-2 — guarding a destructive operation —
and leaving it unowned is how it gets forgotten.

**Changes:** `tcw/work/cli.py`, the `drop` verb and its subparser.

`tcw work drop <slug>` deletes a backlog item outright and, per
`skills/tcw-work/references/transitions.md:111-113`, "is not a transition and
leaves no record". That is the most destructive verb in the CLI and the only one
with no confirmation, while `complete` — which *preserves* the item — requires
`--confirm`. Verify that asymmetry still holds before changing anything
(`tcw work drop --help`).

Add `--confirm`, refusing without it, matching `complete`'s shape and error
wording so the two read alike. Print what will be deleted before refusing, so the
refusal is informative rather than merely obstructive.

**Check the sibling surfaces**, do not assume the CLI is the only caller: grep for
`drop` in `tcw/serve/` (the web editor commits transitions and may expose it) and
in `skills/`. If the web path can delete an item without confirmation, say so in
`outcome.md` — fixing it may belong here or may be a follow-up, but it must not go
unrecorded.

**Verified by:** `tcw work drop <slug>` without `--confirm` exits non-zero and
deletes nothing; with `--confirm` it behaves exactly as before. A test pins both
directions. Existing tests that call `drop` will need `--confirm` added — that is
a genuine interface change, not the "no test may be modified" violation the other
items guard against, so update them and say so.

**Documentation:** this is a breaking CLI change. It needs a `Changed` changelog
entry, a release note written as a behavior change, and an edit to
`skills/tcw-work/references/transitions.md:111-113`, whose current text describes
`drop` without a confirmation flag.

## Task 5 — capabilities axis and documentation sync

**REQUIRED SUB-SKILL: use `tcw-capabilities`.**

`docs/capabilities/work/consolidate-plans/description.md` per the spec's
Capability changes section — record it in this item's `capabilities.yaml` sidecar
under `changed:`.

**Do not re-fix the phantom verb.** Spec D8 establishes the body was already
rewritten by the sibling item and names no `tcw work consolidate-plans` verb.
Confirm that is still true rather than editing on the request's stale premise.

Then one documentation-sync pass over the finished diff:

| Entry | Trigger | Expected |
| --- | --- | --- |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **fires** — task 3.1 and 3.2 |
| `README.md` | `Public-API` | **fires** — task 3.4 |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fires** — `Changed`: procedure relocated into the `tcw-work` skill so it is reachable under Codex; command file reduced to a pointer and keeps `disable-model-invocation`; new approval and recoverability gates. Note that the flag was **not** the guard on the destructive act (see Notes). |
| `docs/release-notes/upcoming.md` | `Public-API` | **fires** — Codex users can now run plan consolidation; and, for all users, the workflow now asks before deleting and will not delete anything git cannot give back. |

## Verification

No Python changes, so the suite is a regression check rather than the evidence.
`python -m pytest -q` must be green — in particular
`tests/test_documented_cli_surface.py`, which now scans every non-archival
Markdown file by exclusion, so **the new reference file is in scope the moment it
exists, with no test edit** (spec D8). If the new document names a `tcw` verb
that does not exist, the suite catches it. That is a live check of this session's
earlier item, not a formality.

Also confirm `tests/test_skill_lifecycle_parity.py` is green — task 3.1 edits a
skill router.

By hand, and recorded in `outcome.md`:

1. **The Codex-reachability claim, argued concretely.** `.codex-plugin/plugin.json`
   exposes `"skills": "./skills/"` and no `commands` key — verify that is still
   true, then confirm the new reference is under `skills/` and reachable from the
   `tcw-work` router by a stated gate. State plainly what a Codex agent sees.
2. **The two gates are actually in the reference**, at the top, quoted into
   `outcome.md`.
3. **The recoverability rule's checks are runnable** — demonstrate
   `git ls-files --error-unmatch` and `git status --porcelain` distinguishing a
   committed, an uncommitted-modified, and an untracked file. Do this in a
   throwaway repo under the scratchpad, not in this one.
4. **`/tcw-consolidate-plans` still resolves for Claude** — the command file
   exists, parses, and points at the reference.

## Notes

**The request's central premise is wrong, and the spec corrected it.** The
request treats `disable-model-invocation: true` as the guard on the destructive
act, and concludes that moving the procedure into `skills/` would be a safety
regression. It is not that guard: it gates *discovery of one command file*, while
the destructive act is `git rm`/`rm` through Bash — and `skills/tcw-work/SKILL.md:5`
already declares `Bash(git *)` in the skill's tool surface today. The flag is also
inert under Codex, which never reads `commands/`, and it stops covering anything
once the user invokes the command, because the procedure body has no approval
step. A barrier at the door with an unguarded room behind it.

So the design keeps the flag **and** adds the rules, and neither harness ends up
worse. Implementation must not "simplify" by dropping the flag on the grounds
that the new rules supersede it — they cover different moments.

**This item closes the last instance of its defect class.** The spec swept all 13
files in `commands/`; every one except `tcw-consolidate-plans.md` already links
into `skills/`, and every link target exists.

**`tcw work drop`'s missing `--confirm` gate is now task 4**, folded in by the
user on 2026-07-30. The spec's Non-goals section still lists it as out of scope;
that section is stale and the implementation should correct it in place rather
than leave the spec and plan disagreeing.

It is a **breaking CLI change** and the only one in this item — everything else
here is documentation motion. If the batch needs to ship without it, task 4 is
the separable piece.
