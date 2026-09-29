# Spec — Make start, submit, rework and complete print the true next step, the item's new folder, and what --confirm acknowledged

## Capability changes

Planned ledger changes only; nothing is written to the ledger at this stage.

- **changed:** `work/open-a-work-item` — after `tcw work new`, the next step it
  prints is the `request` stage, not `tcw work start`.
- **changed:** `work/manage-the-work-inbox` — `tcw work inbox accept` of a raw
  entry prints the same next step as `new`.
- **changed:** `work/start-a-work-item` — after `start`, the next step is the
  first planning stage still missing, or `implement`; never `complete`.
- **changed:** `work/submit-a-work-item-for-review` — `submit` prints the item's
  new location and points at the `verify` stage.
- **changed:** `work/rework-a-reviewed-work-item` — `rework` prints the item's
  new location and points at the `implement` stage.
- **changed:** `work/complete-a-work-item` — with `--confirm`, the Definition of
  Done is printed only once the item has actually been closed, as acknowledged
  items, saying `--confirm` acknowledged them.
- **changed:** `work/customize-the-definition-of-done` — its description of when
  the checklist is printed follows the change above.

No new capabilities. No taxonomy entries are touched: "next step", "stage",
"transition" and "Definition of Done" are already the project's words for these
things.

## Problem

`tcw work` prints a line after it creates or moves an item. Agents treat those
lines as instructions. Four of them are wrong or incomplete today (all
references are to the tree at `3bd7c53a`):

1. **`new` skips the planning stages.** `tcw/work/cli.py:774` prints
   `→ next: when you begin implementing, run tcw work start <slug>`. A new item
   holds at most `intake.md`; the next step is the `request` stage. This is the
   hint that misled the triage session that filed this item.
   `tcw work inbox accept` of a raw entry prints no next step at all
   (`tcw/work/cli.py:945-951`), only `→ now at <path>`.
2. **`start` skips submit and verify** (GitHub #68). Both `start` paths call
   `_complete_hint` (`tcw/work/cli.py:1571`, `:1627`), which prints
   `→ next: when done & verified, run tcw work complete <slug> --resolution done --confirm`
   (`tcw/work/cli.py:1348-1350`). `complete` accepts an `active` item, so an
   agent following the hint closes it without the `implement` or `verify`
   stages running.
3. **`submit` names a file that does not exist** (GitHub #68). Its hint
   (`tcw/work/cli.py:1656-1659`) says to "delete refined-outcome.md" to send the
   work back. Right after `submit` that file has never been written — the
   `verify` stage writes it, on acceptance only — and rejecting means writing
   `rework.md`, which the hint never mentions.
4. **`submit` and `rework` report a status, not where the item went**
   (GitHub #58, point 1). They print `submitted <slug> → review` and
   `reworking <slug> → active` (`tcw/work/cli.py:1655`, `:1687`), while `start`
   prints the location from `st.locate` (`tcw/work/cli.py:1570`) and so does
   `complete` (`tcw/work/cli.py:4232`). The guide already claims every command
   that moves an item names where it now lives (`docs/guide/work.md:377-381`),
   which is false for these two — and they are the two after which a stage
   writes into the folder that just moved.
5. **`complete --confirm` prints the Definition of Done unticked, then
   completes** (GitHub #67). `tcw/work/cli.py:4110-4117` prints
   `Definition of Done — acknowledge each item:` followed by `  [ ] <entry>`
   lines whenever the resolution is `done`, whether or not `--confirm` was
   given. With `--confirm`, eight refusals can still follow that print
   (`--already-integrated` without a worktree at `:4123-4127`, strict tracker
   mode at `:4132-4135`, and further ones at `:4152`, `:4159`, `:4166`, `:4178`,
   `:4198`, `:4204`), so the unticked list appears directly above an unrelated
   refusal and reads as its cause.

The stages already end with a correct "what comes next" line, generated from
`STAGE_NEXT_STEPS` (`tcw/store/base.py:2294-2320`) and guarded by tests that
check each named command exists and each named stage is legal where the reader
stands (`tests/test_stage_verb.py:95-215`). The transitions have no such table
and no such tests, which is how their hints drifted.

## Goals

1. Every next-step line printed after `new`, `inbox accept` (raw entry),
   `start`, `submit` and `rework` names a step that is legal for the item's
   status at that moment and is the next step of the lifecycle.
2. `submit` and `rework` print the item's new location in the same form `start`
   uses.
3. With `--confirm`, the Definition of Done is printed only after the item has
   closed, and says the entries were acknowledged by `--confirm`. Without
   `--confirm`, the refusal is unchanged.
4. The transition hints are guarded by tests of the same kind that guard the
   stage footers, so they cannot drift again unnoticed.

## Non-goals

- The rest of GitHub #58 (`complete` checking for `refined-outcome.md`,
  `validate` finding a slug under two statuses, stage text about where to
  write). That is item
  `2026-09-29-make-a-stale-item-path-fail-loudly-complete-checks-for-the-verify-artifact-validate-finds-a-slug-under-two-statuses-and`.
- Whether `start` should refuse an item with no spec or plan, and whether the
  planning gates should accept an `active` item (GitHub #71). That is item
  `2026-09-29-let-a-started-item-still-pass-its-planning-gates-or-stop-start-from-letting-it-past-them`.
  This item only makes the hint point at whichever stage is legal today.
- Epics. `new --epic` prints no next step on purpose (`tcw/work/cli.py:773`:
  an epic's next step is delegation, not `start`), and that stays as it is.
- Accepting a tracker ticket through `inbox accept`, which runs
  `tracker import` (`tcw/work/cli.py:954-957`) and has its own output.
- What the transitions do: what they refuse, move or commit is unchanged. The
  one behavioral difference is *when* the checklist is printed under
  `--confirm`.
- The discard path of `complete` (a non-`done` resolution), which prints no
  checklist and is unchanged.
- Changing which stream a line is written to. Next-step lines stay on standard
  error; the transition result lines and the checklist stay on standard output.

## Design

### A table of next steps after transitions

Add `TRANSITION_NEXT_STEPS` to `tcw/store/base.py`, directly after
`STAGE_NEXT_STEPS`, for the same reason that table lives there: it is sentence
text about the lifecycle's order, kept beside the tables it must agree with.
Keys and text (`<slug>` is substituted as in `STAGE_NEXT_STEPS`):

| Key      | Item lands in | Next-step text                                                                                                  |
| -------- | ------------- | --------------------------------------------------------------------------------------------------------------- |
| `new`    | `backlog`     | run `tcw work stage gate request <slug>`                                                                        |
| `start`  | `active`      | run `tcw work stage gate {stage} <slug>` — `{stage}` chosen as below                                             |
| `submit` | `review`      | run `tcw work stage gate verify <slug>`; it ends in `refined-outcome.md` (accept) or `rework.md` (send back)     |
| `rework` | `active`      | address rework.md: run `tcw work stage gate implement <slug>`                                                   |

`inbox accept` of a raw entry uses the `new` row: both create a backlog item
holding only its intake.

**`start` chooses its stage from the item's artifacts**, because an item can be
started before it is specified or planned (the `start` warning at
`tcw/work/cli.py:1466-1472` already says so), and in that case `implement` is
not yet the next stage — this project's own `implement` gate refuses without a
spec and plan. The rule: the first of `spec`, `plan`, `implement` whose artifact
(`spec`, `plan`, `outcome`) is not present, read through `st.artifacts(slug)`.
`request` is not considered, because it is not legal in `active`
(`STAGE_STATUSES`, `tcw/store/base.py:2270-2278`). All three candidates are legal in
`active`. If reading the artifacts fails, the hint falls back to `implement`
rather than printing nothing.

The `start` hint does not name `submit`, for the reason `STAGE_NEXT_STEPS`
gives for `implement`: `verify` is legal from `active`, and the stage footers
already carry the reader from there.

The `submit` text states both endings and neither tells the reader to delete
anything. The `verify` stage's own footer already names `complete` and
`rework`, so the hint does not repeat those commands.

`_complete_hint` is removed; both `start` paths print the table's text instead.
Next-step lines keep the `→ next: ` prefix and stay on standard error.

**Abstraction check.** The hints read only the item's status and its artifact
presence, both of which the abstract store already answers (`artifacts`,
`tcw/store/base.py:3478`). No filesystem path enters the table. A non-filesystem
store gets correct hints with no new operation.

### Location after submit and rework

`submit` prints `submitted <slug> → <location>` and `rework` prints
`reworking <slug> → <location>`, where `<location>` is `st.locate(slug)`
(`tcw/store/base.py:3497`) — the same source `start` uses. When `locate` returns
nothing (a store with no notion of a location), they fall back to the status
name, so the line is never worse than it is today. Both lines stay on standard
output.

### The Definition of Done under --confirm

For a `done` resolution:

- **Without `--confirm`:** unchanged — the unticked checklist and the refusal
  naming `--confirm`, at the point in the sequence where it is printed today.
- **With `--confirm`:** nothing is printed before the checks. After the item has
  closed — immediately before the existing `completed <slug> …` line at
  `tcw/work/cli.py:4232` — print
  `Definition of Done — acknowledged with --confirm:` followed by one
  `  [x] <entry>` line per entry, on standard output. If any refusal or failure
  happens first, the checklist is not printed at all.

The heading still begins `Definition of Done`, which keeps existing tests that
look for that phrase on the success path meaningful (`tests/test_work.py:887`,
`:2308`); tests asserting it is absent on refusals (`:1313`, `:2282`, `:2287`)
must stay green.

### Documentation

- `docs/guide/work.md` "What the commands print" (`:373-381`): replace the old
  example hint and name `submit` and `rework` among the commands that print the
  item's location.
- `docs/guide/work.md` "The completion gate" (`:548-561`): say what `--confirm`
  prints and when.
- The capability descriptions listed under **Capability changes**.
- Changelog and release-note entries under `docs/{changelogs,release-notes}/upcoming/`.

## Acceptance criteria

Each is checked in a scratch project made with `tcw init` in an empty git
repository, unless it names a test.

1. `echo body | tcw work new "Thing"` prints on standard error a line beginning
   `→ next:` that contains `tcw work stage gate request <slug>` and does not
   contain `tcw work start`.
2. Accepting a raw inbox entry with `tcw work inbox accept <entry>` prints the
   same `→ next:` line as criterion 1, for the accepted item's slug.
3. `tcw work new --epic "E"` prints no `→ next:` line (unchanged).
4. `tcw work start <slug>` on an item with neither `spec.md` nor `plan.md`
   prints a `→ next:` line naming `tcw work stage gate spec <slug>`; with
   `spec.md` only, `plan`; with both, `implement`. None of the three names
   `tcw work complete`. The same holds for `tcw work start <slug> --worktree`.
5. `tcw work submit <slug>` prints on standard output
   `submitted <slug> → docs/work/review/<slug>`, and on standard error a
   `→ next:` line naming `tcw work stage gate verify <slug>`, mentioning both
   `refined-outcome.md` and `rework.md`, and not containing the word `delete`.
6. `tcw work rework <slug>` prints on standard output
   `reworking <slug> → docs/work/active/<slug>`, and on standard error a
   `→ next:` line naming `rework.md` and `tcw work stage gate implement <slug>`.
7. `tcw work complete <slug> --resolution done --confirm` on a completable item
   prints on standard output `Definition of Done — acknowledged with --confirm:`
   then one `  [x] <entry>` line per Definition of Done entry, then the
   `completed …` line; and prints no `[ ]`.
8. `tcw work complete <slug> --resolution done --confirm --already-integrated`
   on an item not started with `--worktree` exits 1 with its existing refusal,
   and its standard output contains neither `Definition of Done` nor `[ ]`.
9. `tcw work complete <slug> --resolution done` (no `--confirm`) prints the
   unticked checklist and `Refused: re-run with --confirm…` exactly as before,
   and exits 1.
10. A test asserts that `TRANSITION_NEXT_STEPS` has exactly the keys `new`,
    `start`, `submit`, `rework`; that every `tcw …` command it names is a
    shipped command (by the method of `tests/test_stage_verb.py:102-133`); and
    that every stage it names is legal in the status that key lands the item in
    (`STAGE_STATUSES`) — covering each stage `start` can choose.
11. `grep -rn "when done & verified\|delete refined-outcome\|when you begin implementing" tcw/ docs/guide/ skills/ README.md`
    finds nothing.
12. The full test suite passes, run as CI runs it (bare `pytest`).

## Risks

- **A script parsing `submitted <slug> → review`.** The status name disappears
  from that line when a location exists. Nothing in this repository parses it
  (`tests/test_work_review.py:306` and `:310` assert the substring and are
  updated). The same change was made to `start` earlier without complaint;
  accepted.
- **The `start` hint reads artifacts** for the first time. A read failure must
  not turn a successful `start` into a failure, so it falls back to
  `implement` (Design).
- **Printing the checklist later changes the output order** of a successful
  `--confirm` completion: the checklist now follows every warning printed during
  the checks. Anything reading the checklist before the `completed` line still
  finds it there.
- **A project that replaced a stage's instructions** still gets TCW's hint,
  which names only stage ids and transitions — both fixed by TCW, not by
  project configuration (`LIFECYCLE_STEPS`, `tcw/store/base.py:2173`). Projects
  add checks to stages; they cannot rename or remove them, so the hint cannot
  name a stage a project lacks.

## Notes

- Sibling sweep, repo-wide: `grep -rn "→ next" tcw/` finds exactly the four
  print sites this spec changes (`tcw/work/cli.py:774`, `:1349`, `:1656`,
  `:1688`). The stage footers were checked and are already correct. No skill
  quotes a transition hint; `docs/guide/work.md:375` does and is updated.
- `complete` from `active` already prints a note that the verify stage was
  skipped (`tcw/work/cli.py:4080-4093`); unchanged.
