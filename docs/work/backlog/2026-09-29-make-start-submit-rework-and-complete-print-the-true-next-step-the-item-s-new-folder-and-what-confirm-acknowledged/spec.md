# Spec — Make start, submit, rework and complete print the true next step, the item's new folder, and what --confirm acknowledged

## Capability changes

Planned ledger changes only; nothing is written to the ledger at this stage.

- **changed:** `work/open-a-work-item` — after `tcw work new`, the next step it
  prints is the `request` stage, not `tcw work start`.
- **changed:** `work/manage-the-work-inbox` — `tcw work inbox accept` of a raw
  entry prints the same next step as `new`.
- **changed:** `work/start-a-work-item` — after `start`, the next step is the
  first stage whose artifact is still missing (`spec`, `plan`, `implement`,
  `verify`, in the order below); never `complete`.
- **changed:** `work/submit-a-work-item-for-review` — `submit` prints the item's
  new location and points at the `verify` stage.
- **changed:** `work/rework-a-reviewed-work-item` — `rework` prints the item's
  new location and points at the `implement` stage.
- **changed:** `work/complete-a-work-item` — with `--confirm`, the Definition of
  Done is printed only once the item has actually been closed, as acknowledged
  items, saying `--confirm` acknowledged them.
- **changed:** `work/customize-the-definition-of-done` — its description of when
  the checklist is printed follows the change above, and no longer calls it a
  prompt on the `--confirm` path.
- **changed:** `skills/extras-triage-issues` — its description says the
  issue-closing reminder "rides on the completion checklist"; under `--confirm`
  that checklist now appears after the item has closed.

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
   work back. Right after `submit` that file normally does not exist — the
   `verify` stage writes it, on acceptance only (it can exist already only if
   `verify` was run from `active`, which `STAGE_STATUSES` allows) — and
   rejecting means writing `rework.md`, which the hint never mentions.
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
| `start`  | `active`      | one entry per stage `start` can choose — `spec`, `plan`, `implement`, `verify` — each reading run `tcw work stage gate <stage> <slug>`; chosen as below |
| `submit` | `review`      | run `tcw work stage gate verify <slug>`; it ends in `refined-outcome.md` (accept) or `rework.md` (send back)     |
| `rework` | `active`      | address rework.md: run `tcw work stage gate implement <slug>`                                                   |

`inbox accept` of a raw entry uses the `new` row: both create a backlog item
holding only its intake.

**Epics get the `new` hint too.** `new --epic` prints no next step today, with
the reason "epic's next step is delegate, not start" (`tcw/work/cli.py:773`).
That reason was about the `start` hint. Epics run `request`, `spec` and `plan`
like any item (`skills/work/references/epic-deltas.md:14-16`), so the `request`
hint is correct for them and the exemption is removed.

**`<slug>` is the reference the user typed** (`args.slug`, which may be
qualified, such as `kid/<slug>`), and the bare slug is used only to read the
item — the same split `_unwritten_plan` makes (`tcw/work/cli.py:1455-1472`,
asserted by `tests/test_unplanned_start.py:154`).

**`start` chooses its stage from the item's artifacts.** Two facts make a
fixed answer wrong. An item can be started before it is specified or planned
(the warning built by `_unwritten_plan`, `tcw/work/cli.py:1455-1472`, printed at
`:1567`), and this project's own `implement` gate refuses without a spec and
plan. And `start` is not limited to `backlog`: it takes an `active` item with
`--take-over`, or with no flag when nobody holds it — the state
`tcw work tracker release` leaves (`tcw/store/base.py:4234-4243`). Such an item
may already hold `outcome.md`, with or without `rework.md`.

The rule is the work skill's own "Finding your place" order
(`skills/work/SKILL.md:45-48`), restricted to stages legal in `active`, and
extended for a reworked item the way the `rework` row below already is:

1. no `spec.md` → `spec`
2. else no `plan.md` → `plan`
3. else no `outcome.md`, **or** `rework.md` present → `implement`
4. else → `verify`

`request` is not considered, because it is not legal in `active`
(`STAGE_STATUSES`, `tcw/store/base.py:2270-2278`). All four candidates are legal
in `active`. The hint and the skill paragraph must agree; the skill paragraph
gains the `rework.md` case so they do.

The artifacts are read once, shared with `_unwritten_plan`, under its existing
error handling (`OSError`, `ValueError`). If the read fails the hint falls back
to `implement` rather than printing nothing. When spec or plan is missing, the
warning and the hint both name the same gate command; that repetition is
accepted. The hint text never contains the words `spec.md` or `plan.md`, because
`tests/test_unplanned_start.py:58,65` assert those do not appear on standard
error in cases where they should not.

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
- **The move lands but its commit fails** (`TransitionCommitError`,
  `tcw/work/cli.py:4203-4207`): the command returns 1 without the `completed`
  line today, and it also returns without the checklist. Its error message
  already says the item moved; printing an acknowledgement beside a failure
  would read as success.

Every other path after a successful move reaches line 4232 — `post` hooks,
tracker delivery, the tracker-owed "kept rather than removed" branch, and the
automatic deletion — so none of them loses the checklist.

**Under `--confirm` the checklist is a record, not a prompt.** It says what was
acknowledged, after the fact. A reader who wants to see it *before* committing
to it runs `complete` without `--confirm`, which is unchanged. One consequence:
the `extras-triage-issues` reminder to answer the originating GitHub issue
"rides on the completion checklist" (`docs/work/dod.yaml`) and now reaches the reader
only after the item has closed. That is acceptable because this repository
answers issues only after the version carrying the fix is published
(`CLAUDE.md`, "Closing the originating GitHub issue waits for publication"), so
the reminder was never meant to be acted on before closing.

The heading still begins `Definition of Done`, which keeps existing tests that
look for that phrase on the success path meaningful (`tests/test_work.py:887`,
`:2308`); tests asserting it is absent on refusals (`:1313`, `:2282`, `:2287`)
must stay green.

### Documentation

- `docs/guide/work.md` "What the commands print" (`:373-381`): it says `new` and
  `start` print "the **next transition** to run"; they now print a stage. Replace
  that wording and the old example, and name `submit` and `rework` among the
  commands that print the item's location.
- `docs/guide/work.md` "The completion gate" (`:548-561`): say what `--confirm`
  prints and when.
- `skills/work/references/transitions.md:145` ("printed before `--confirm`.
  `[prompted]`"), `skills/configure/references/work.md:121-139`, and
  `skills/work/SKILL.md:45-48` (the `rework.md` case).
- The capability descriptions listed under **Capability changes**, including
  `complete-a-work-item`'s sentence "the checklist is still printed before I
  confirm", `customize-the-definition-of-done`'s "prints before it accepts
  `--confirm`" and "it prompts me", and
  `docs/capabilities/skills/extras-triage-issues/description.md:4`.
- Changelog and release-note entries under `docs/{changelogs,release-notes}/upcoming/`.

## Acceptance criteria

Criteria 1–9 are automated CLI tests, run against a scratch project made with
`tcw init` in an empty git repository, in the style of `tests/test_work.py` and
`tests/test_unplanned_start.py`.

1. `echo body | tcw work new "Thing"` prints on standard error a line beginning
   `→ next:` that contains `tcw work stage gate request <slug>` and does not
   contain `tcw work start`.
2. Accepting a raw inbox entry with `tcw work inbox accept <entry>` prints the
   same `→ next:` line as criterion 1, for the accepted item's slug.
3. `tcw work new --epic "E"` prints the same `→ next:` line as criterion 1, for
   the epic's slug.
4. `tcw work start <slug>` prints a `→ next:` line naming
   `tcw work stage gate <stage> <slug>`, where `<stage>` is: `spec` with neither
   `spec.md` nor `plan.md`; `plan` with `spec.md` only; `implement` with both;
   and, on an unowned `active` item started again, `implement` with `outcome.md`
   and `rework.md`, and `verify` with `outcome.md` and no `rework.md`. None of
   these names `tcw work complete`. The first three cases also hold for
   `tcw work start <slug> --worktree`, and for a qualified reference
   (`kid/<slug>`) the hint shows the reference as typed.
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
10. A test asserts that `TRANSITION_NEXT_STEPS` covers `new`, `submit`, `rework`
    and each of `start`'s four candidate stages; that every `tcw …` command in
    every entry, **with `<slug>` substituted and no unfilled placeholder left**,
    is a shipped command (by the method of `tests/test_stage_verb.py:102-133`);
    and that every stage an entry names is legal in the status that transition
    lands the item in (`STAGE_STATUSES`). The test fails if any entry yields no
    command match at all, so an entry the pattern cannot read is not silently
    skipped.
11. `grep -rn "when done & verified\|delete refined-outcome\|when you begin implementing\|printed before \`--confirm\`\|prints before it accepts\|next transition\*\* to" tcw/ docs/guide/ docs/capabilities/ skills/ README.md`
    finds nothing.
12. The full test suite passes, run as CI runs it (bare `pytest`).

## Risks

- **A script parsing `submitted <slug> → review`.** The status name disappears
  from that line when a location exists. Nothing in this repository parses it
  (`tests/test_work_review.py:306` and `:310` assert the substring and are
  updated). The same change was made to `start` earlier without complaint;
  accepted.
- **The `start` hint reads artifacts.** It shares the read `_unwritten_plan`
  already does, so there is no second read with different failure rules; a
  failure falls back to `implement` (Design).
- **The `--worktree` hint does not say to work inside the worktree.** It names
  the stage, not where to run it. That predates this item and belongs to the
  stale-path theme of the #58 item; noted, not changed.
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
- Other callers, checked: none of `new`, `start`, `submit`, `rework`, `complete`
  has a JSON output mode. `tcw serve` calls the store directly and prints no
  hints; its checklist is its own web form. `reconcile --complete-when-ready`
  (`tcw/work/recursion.py:432-437`) completes an epic and prints no checklist;
  unchanged here, though `complete-a-work-item`'s claim that the
  Definition-of-Done gate "still runs either way" is inaccurate for it and is
  left for a separate item.
- Adversarial spec review, round 1 (after `1b6ac687`): all three blocking
  findings accepted — the `start` rule gained the `outcome.md` cases, the
  documentation list gained the "printed before `--confirm`" statements, and
  criterion 10 no longer lets a templated row pass unchecked. The "could be
  noted" findings were accepted except the `--worktree` location, recorded in
  Risks as out of scope.
