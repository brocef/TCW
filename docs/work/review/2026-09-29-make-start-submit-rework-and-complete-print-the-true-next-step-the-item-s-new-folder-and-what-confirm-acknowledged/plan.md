# Plan — Make start, submit, rework and complete print the true next step, the item's new folder, and what --confirm acknowledged

Implements `spec.md` in this folder. Every task leaves the suite green at its
commit. Tests are written in the same task as the code they cover, and each new
assertion is checked by breaking what it observes and watching it fail
(`docs/lifecycle/implementation.md`).

New CLI tests go in one new file, `tests/test_transition_hints.py`, built on the
same helpers as `tests/test_unplanned_start.py:12-35` (a git-initialised node
from `init(["work"], root, "repo")`, and `tcw work …` run as a subprocess so
standard output and standard error are captured separately). Copy those two
helpers rather than importing across test modules, as the existing test files
do.

## Task 1 — The table and the `start` rule, with the guard test

**Modifies** `tcw/store/base.py`, `tests/test_stage_verb.py`.

- In `tcw/store/base.py`, directly after `STAGE_NEXT_STEPS` (currently ending at
  line 2320), add:
  - `TRANSITION_NEXT_STEPS: dict[str, str]` with the keys `new`, `start:spec`,
    `start:plan`, `start:implement`, `start:verify`, `submit`, `rework`. The
    `start:<stage>` keys hold one entry per stage `start` can choose, so no
    entry is a template with an unfilled stage. Text, with `<slug>` as the only
    placeholder:
    - `new`: `` run `tcw work stage gate request <slug>` ``
    - `start:<stage>`: `` run `tcw work stage gate <stage> <slug>` `` (the stage
      spelled out in each entry)
    - `submit`: `` run `tcw work stage gate verify <slug>`; it ends in refined-outcome.md to accept the work or rework.md to send it back ``
    - `rework`: `` address rework.md: run `tcw work stage gate implement <slug>` ``
  - `TRANSITION_LANDS_IN: dict[str, str]` mapping each key to the status the
    item is in when the hint prints (`new` → `backlog`, every `start:*` and
    `rework` → `active`, `submit` → `review`). The guard test reads it; the CLI
    does not.
  - `start_next_stage(present: Collection[str]) -> str`, a pure function over
    the set of present artifact names implementing the spec's four-step rule:
    no `spec` → `"spec"`; else no `plan` → `"plan"`; else no `outcome` or
    `rework` present → `"implement"`; else `"verify"`.
  - A comment block in the style of the one above `STAGE_NEXT_STEPS`, saying why
    `start` picks from artifacts (it can run on an `active` item) and why no
    entry names `spec.md` or `plan.md` (the assertions at
    `tests/test_unplanned_start.py:58,65`).
- In `tests/test_stage_verb.py`, beside
  `test_every_next_step_names_a_command_that_exists` (line 102), add:
  - a test that `TRANSITION_NEXT_STEPS` and `TRANSITION_LANDS_IN` have the same
    keys, and that the `start:*` keys are exactly
    `{f"start:{s}" for s in ("spec", "plan", "implement", "verify")}`;
  - a test that substitutes `<slug>` with a sample slug in every entry, asserts
    no `<` or `{` placeholder remains, asserts **at least one** `` `tcw … `` match
    per entry, and checks each match with the same longest-shipped-prefix method
    as line 102-133 (factor that method into a module-level helper both tests
    call, rather than copying it);
  - a test that every stage named by `` `tcw work stage gate <stage> `` in an
    entry is in `STAGE_STATUSES[stage]` for `TRANSITION_LANDS_IN[key]`;
  - a test of `start_next_stage` for the five cases: `{}` → spec,
    `{spec}` → plan, `{spec, plan}` → implement,
    `{spec, plan, outcome, rework}` → implement,
    `{spec, plan, outcome}` → verify.

**Proves:** spec criterion 10. Mutation checks: add an entry with an unfilled
`{stage}` (the test must fail on "no match"), and change `submit`'s stage to
`implement` (the legality test must fail, since `implement` is not legal in
`review`).

## Task 2 — Hints after creating an item

**Modifies** `tcw/work/cli.py`, creates `tests/test_transition_hints.py`.

- Add a small helper in `tcw/work/cli.py`, next to where `_complete_hint` is
  now (line 1348), `_next_hint(key: str, ref: str) -> None`, printing
  `→ next: ` + `TRANSITION_NEXT_STEPS[key]` with `<slug>` replaced by `ref`, to
  standard error. `ref` is always the reference as the user typed it.
- `_new` (line 772-775): drop the `if not args.epic` condition and its comment;
  call `_next_hint("new", item.slug)` for every item.
- `_inbox_accept` raw-entry branch (lines 945-951): after the `→ now at` line,
  call `_next_hint("new", item.slug)`. The ticket branch (line 954-957) is not
  touched.
- Tests in `tests/test_transition_hints.py`: criterion 1 (`new` with a piped
  body: stderr has `tcw work stage gate request <slug>`, not `tcw work start`),
  criterion 2 (write a raw entry into the inbox folder given by
  `tcw work inbox path`, accept it, same line), criterion 3 (`new --epic`, same
  line).

**Proves:** criteria 1–3.

## Task 3 — Hint after `start`

**Modifies** `tcw/work/cli.py`, `tests/test_transition_hints.py`.

- Change `_unwritten_plan` (line 1452-1472) so the artifact read happens once:
  split it into a reader returning the set of present artifact names (or `None`
  when the read raises `OSError`/`ValueError`, its current handling) and the
  warning text built from that set. The warning is already computed once, at
  line 1566, before the plain and `--worktree` paths divide (lines 1568-1571
  and 1620-1627); read the set there, once, and use it for both the warning
  and the hint on either path.
- Replace both `_complete_hint(args.slug)` calls with
  `_next_hint(f"start:{stage}", args.slug)`, where `stage` is
  `start_next_stage(present)`, or `"implement"` when the read returned `None`.
- Delete `_complete_hint`.
- Tests: the five artifact cases of criterion 4. For the two `outcome.md` cases,
  make the item `active` and unowned before running `start` again — start it,
  write the artifacts with `write_artifact`, then clear the owner with
  `FsWorkStore.set_field(slug, "owner", …)`. First confirm which empty value
  (`""` or `None`) `start` treats as "nobody holds it" at
  `tcw/store/base.py:4234-4237` and use that one. Also: the three planning cases
  with `--worktree`; a qualified reference, reusing the parent/child node setup
  of the test at `tests/test_unplanned_start.py:154`, asserting the hint shows
  `kid/<slug>`; and in every case, no `tcw work complete` on stderr.
- `tests/test_unplanned_start.py` must pass unchanged.

**Proves:** criterion 4.

## Task 4 — Location and hints after `submit` and `rework`

**Modifies** `tcw/work/cli.py`, `tests/test_work_review.py`,
`tests/test_transition_hints.py`.

- `_submit` (line 1655-1659): print
  `submitted {args.slug} → {st.locate(bare) or "review"}` to standard output,
  then `_next_hint("submit", args.slug)`.
- `_rework` (line 1687-1689): the same with `reworking`, `"active"`, and
  `_next_hint("rework", args.slug)`.
- `tests/test_work_review.py:306` and `:310`: assert the new location
  (`→ docs/work/review/<slug>`, `→ docs/work/active/<slug>`) rather than
  `→ review` / `→ active`.
- Tests: criteria 5 and 6, including that the `submit` hint contains neither
  `delete` nor `tcw work complete`.

**Proves:** criteria 5–6.

## Task 5 — The Definition of Done under `--confirm`

**Modifies** `tcw/work/cli.py`, `tests/test_transition_hints.py`.

This is the riskiest task, since it moves output across eight refusal paths, so
it comes after the hint work is in and green.

- In `_complete` (lines 4110-4117): print the unticked checklist and the refusal
  only when `shipping and not args.confirm`. When `shipping and args.confirm`,
  print nothing there.
- Immediately before the `completed …` print at line 4232, when `shipping`,
  print `Definition of Done — acknowledged with --confirm:` and one
  `  [x] <entry>` line per entry of the `checklist` already computed at line
  4109, to standard output. `--confirm` is guaranteed there, because the
  non-confirm path returned earlier.
- The `TransitionCommitError` path (lines 4203-4207) is left returning before
  that print, as the spec decides.
- Tests: criterion 7 (a plain completable item, started and submitted);
  criterion 8 (`--already-integrated` on an item without a worktree: exit 1,
  stdout has neither `Definition of Done` nor `[ ]`); criterion 9 (no
  `--confirm`: unticked list and the `Refused: re-run with --confirm` line,
  exit 1). Also run `tests/test_work.py`; its assertions at lines 887, 1313,
  2282, 2287 and 2308 must pass unchanged.

**Proves:** criteria 7–9.

## Task 6 — Documentation Sync

One pass over the finished diff. Each trigger in the project's documentation
entries was evaluated:

- **Skill-Driven-Component** fires (the `work` component's lifecycle output
  changes):
  - `skills/work/SKILL.md:45-48` — "Finding your place" gains the reworked case:
    with `rework.md` present, the next stage is `implement`, matching the
    `start` rule.
  - `skills/work/references/transitions.md:145` — the checklist is printed
    before `--confirm` only when `--confirm` is absent; with it, it is printed
    after the item closes, as acknowledged.
- **Configuration-Key-Change** fires, because it covers what `docs/work/dod.yaml`
  means: `skills/configure/references/work.md:121-139` — the same correction
  about when the checklist appears.
- **Guide-Topic-Change** fires: `docs/guide/work.md` "What the commands print"
  (`:373-381`: "next transition" becomes "next step", the example becomes the
  `request` hint, and `submit` and `rework` join the commands that print the
  item's location), and "The completion gate" (`:548-561`: add what `--confirm`
  prints and when).
- **Public-API** fires:
  - `docs/release-notes/upcoming/2026-09-29-make-start-submit-rework-and-complete-print-the-true-next-step-the-item-s-new-folder-and-what-confirm-acknowledged.md`,
    following that folder's `README.md`.
  - `README.md`: checked, no change — it quotes no hint text and does not say
    when the checklist is printed (its lifecycle table at line 486 and examples
    at lines 588 and 711 stay true).
- **Any-Code-Change** fires:
  `docs/changelogs/upcoming/<same slug>.md`, grouped under `## Changed`
  and `## Fixed`.
- **Tracker-Change** does not fire: no `tracker` command or bound-ticket
  behavior changes.
- **Capability descriptions** (the spec's Capability changes), edited in place:
  `docs/capabilities/work/open-a-work-item/description.md`,
  `manage-the-work-inbox`, `start-a-work-item`,
  `submit-a-work-item-for-review`, `rework-a-reviewed-work-item`,
  `complete-a-work-item` (lines 7 and 22), `customize-the-definition-of-done`
  (lines 1 and 5), and `docs/capabilities/skills/extras-triage-issues/description.md:4`.
  Record them as `changed:` in this item's `capabilities.yaml` so the completion
  gate reconciles them.

**Proves:** criterion 11 — run the grep from the spec and expect no output.

## Task 7 — Full suite

Run bare `pytest` from the repository root, as CI does, and expect it green.

**Proves:** criterion 12.

## Verification

What the suite cannot show, checked by hand in a scratch project (`tcw init`
in an empty git repository), reading the actual output rather than grepping it:

- Walk one item through `new` → the stage gates → `start` → `submit` →
  `rework` → `submit` → `complete --confirm`, and read every line printed at
  each step. Each `→ next:` line must name something that works when run as
  printed, and each location printed must exist.
- Run the `submit` hint's gate command exactly as printed; it must pass.
- Run `complete --confirm` once where a refusal fires late (an unreconciled
  declared capability) and confirm nothing about the Definition of Done appears
  above the refusal.

## Notes

- The mutation checks named in Tasks 1–5 are recorded in `outcome.md` with what
  was broken and how the test failed.
- No blockers: the sibling items for #58 and #71 touch neighboring code
  (`complete`'s checks, `start`'s refusal) but neither is required first. If the
  #71 item later makes `start` refuse an unplanned item, the `start:spec` and
  `start:plan` hints become rarer or unreachable, but stay correct wherever they
  are printed.
