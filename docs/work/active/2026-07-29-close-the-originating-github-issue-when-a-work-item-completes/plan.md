# Plan: Close the originating GitHub issue when a work item completes

Five tasks. No `tcw/` diff, so suite-greenness never constrains the ordering;
what does is that **task 1 is the only one that can break something silently**,
so it goes first and gets proven in a throwaway repo before anything leans on it.

## Task 1 — `docs/work/dod.yaml`

**Changes:** new file — the five `DEFAULT_DOD` entries verbatim, plus one line
for the originating issue.

The risky task, and the reason it is first. The file **replaces** the defaults
rather than extending them (`fs.py:2012-2020`), so a typo or a short list deletes
checks from every completion in this repo with no error and no test failure. Copy
`DEFAULT_DOD` (`tcw/store/base.py:774`) exactly — do not retype it.

**Verified by:** criteria 1-3, empirically and in that order:

```bash
python3 -c "from tcw.store.base import DEFAULT_DOD; print(DEFAULT_DOD)"   # copy source
tcw work complete <slug> --resolution done      # (no --confirm) prints checklist, refuses
```

Criterion 3 — that a discard prints **no** checklist — gets a throwaway `tcw
init` repo under the scratchpad, not this one: verifying it here would leave a
junk item in `docs/work/discarded/` permanently, and `tcw work drop` only takes
items from `backlog`.

This also settles the spec's one open assumption: that `self.root / "dod.yaml"`
resolves to `docs/work/dod.yaml` rather than the node root. Running `complete` is
the check; reading the line again is not.

## Task 2 — closeout section in `skills/tcw-triage-issues/SKILL.md`

**Changes:** a new final section covering all four resolutions per spec §3.

Three things it must get right, all of which the spec grounds:

- **`superseded` closes the issue only when the ask was absorbed.** A deferred
  ask left open. This is the same defect `4364a5a` fixed reading the other
  direction, and repeating it here would be worse — that one only mis-triaged,
  this one closes someone's issue.
- **The exact-text approval rule is restated, not referenced.** It is the skill's
  core guarantee and a reader arriving at closeout may not have read §6.
- **The item is located with `tcw work path <slug>`**, then its
  `initial-request.md` read for the `## Origin` URL. No new field (spec §2).

**Verified by:** criterion 4, and `pytest tests/test_documented_cli_surface.py`
— it scans `skills/**/*.md` and fails on any `tcw` verb or flag that does not
exist, which is the check that `tcw work path` is real and spelled right.

## Task 3 — pointers in `skills/tcw-work/references/transitions.md`

**Changes:** a line in the `complete` section and a line in the `discard`
section.

**The `discard` pointer is the load-bearing one.** `checklist = st.dod_checklist()
if shipping else []` (`cli.py:810`) means a discard prints no checklist at all,
so three of the four resolutions get no automatic prompt and this pointer is the
only thing standing in for it. A plan that treated the two sections as symmetric
would leave the majority of the cases silently uncovered.

**Verified by:** criterion 5; `pytest tests/test_skill_lifecycle_parity.py`,
which asserts every transition has a section in this file.

## Task 4 — capability ledger

**Changes:** three, per spec §0.

1. `tcw capabilities add work/customize-the-definition-of-done "Customize the Definition of Done" --status Missing`,
   `Planning doc` → this slug, `Subject=work-item/definition-of-done` to match
   `work/complete-a-work-item`. Body: `docs/work/dod.yaml`, that it **replaces**
   the defaults, and the five defaults themselves.
2. `work/complete-a-work-item` — correct "the same fixed checklist on every item".
3. `plugin/triage-github-issues` — extend the body to cover closeout.
4. `capabilities.yaml` in the item folder: `new:` the first, `changed:` the other
   two.

**Verified by:** criterion 7; `tcw capabilities check` and `tcw validate`.

## Documentation Sync

Evaluated against `CLAUDE.md`. All four entries fire. One block, after the code
tasks, answered in a single pass over the finished diff.

### Task 5 — `README.md` [Public-API] and `skills/tcw-work/` [Skill-Driven-Component]

`dod.yaml` appears in **no** README, skill, or doc today (spec §5) — this item
depends on it, so it gets documented in the same change. Both surfaces must say
that the file **replaces** rather than extends the defaults; that is the part
that costs someone four silent checks if they meet it by guessing.

`skills/tcw-work/SKILL.md` is a thin router with a line budget enforced by
`test_the_router_stays_within_its_line_budget`, so the detail goes in the
reference it already routes to (`transitions.md`, already open in task 3) rather
than the router.

### Task 6 — `docs/changelogs/upcoming.md` [Any-Code-Change]

Fires: no `tcw/` diff, but `docs/work/dod.yaml` changes what `tcw work complete`
does in this repo, which is behavior, not cosmetics. Note the no-code-change
result explicitly — "we added a config file instead of a feature" is the useful
part for a developer reading it later.

### Task 7 — `docs/release-notes/upcoming.md` [Public-API]

Two user-facing things: issues get answered when the work ships, and the
completion checklist was configurable all along.

## Verification

Beyond the suite:

- **The `done` path is proven by this item's own completion** (criterion 2).
  Convenient, but it means the check happens at closeout — if the line is wrong,
  it is found at the last possible moment. Task 1's `--confirm`-less dry
  invocation is what moves that discovery to the front.
- **The discard path needs a throwaway repo** (criterion 3). There is no way to
  exercise it here without leaving residue.
- **Criterion 8 is a `git diff --stat -- tcw/` returning empty.** State it, do
  not assume it.
- **Criterion 10** — issues #9 and #8 stay open. Nothing in this item should
  touch them; their work has not shipped. Check at the end that no `gh` write
  ran.
- **Full suite** — `python -m pytest`, ~150s, in the background.

## Notes

The DoD is `[prompted]`, never `[gated]` (`transitions.md:70`). Nothing in this
plan changes that, and no task should try: enforcement would mean `tcw` making a
network call, which the spec rules out. The deliverable is a reliable prompt, not
a guarantee — and the plan should not end up claiming otherwise in the release
notes.
