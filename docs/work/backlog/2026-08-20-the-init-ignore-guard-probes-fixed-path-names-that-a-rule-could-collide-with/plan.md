# Plan — the init ignore guard probes fixed path names that a rule could collide with

Planned against `a875de9`. Line numbers below are re-derived at that sha, not
copied from the spec.

**Size.** Two lines of behaviour plus a message string, plus tests. Two commits.
The spec settled every design question; nothing here reopens one.

## Where the change lands

The guard is the pre-flight leaf loop inside `init`, `tcw/store/fs.py`:

| Lines | What |
| --- | --- |
| `tcw/store/fs.py:676-700` | the comment block that bounds what the probe may be — **unchanged except its last paragraph** (see Task 1) |
| `tcw/store/fs.py:701-702` | the `component == "work" … leaf.name not in RESOLVED_STATUSES` condition — unchanged |
| `tcw/store/fs.py:703-704` | the single fixed probe — **replaced** |
| `tcw/store/fs.py:705` | `if git_ignored(ignore_root, probe, no_index=True):` — **replaced by `all(...)`** |
| `tcw/store/fs.py:706-709` | the refusal message — **reworded** |
| `tcw/store/fs.py:710` | `write_sentinel(root, project_id)` — the guard stays above it, so criterion 5 holds by placement |

Supporting facts confirmed at this sha: `git_ignored` is `tcw/store/fs.py:331-343`;
`WORK_STATUSES = ("backlog", "active", "review", "completed", "discarded")` and
`RESOLVED_STATUSES = ("completed", "discarded")` are `tcw/store/base.py:441,453`,
so the loop probes exactly four leaves (`inbox`, `backlog`, `active`, `review`),
`inbox` first.

## Task 1 — two probes, `all(...)`, reworded message (+ tests)

**Modifies:** `tcw/store/fs.py`, `tests/test_non_git_writes.py`.

1. Replace `tcw/store/fs.py:703-705` with the spec's decided shape: build the two
   probes for `("an-item", "some-slug")` — `leaf / f"{name}.md"` for `inbox`,
   `leaf / name / "state.yaml"` otherwise — and refuse only when
   `all(git_ignored(ignore_root, p, no_index=True) for p in probes)`.
2. Reword the message (`:706-709`) to describe the outcome for items rather than
   asserting the folder is inside an ignored path. It must contain the leaf path
   and the substring `gitignored`, and must not contain `work store folder is
   inside`. The spec's text is the reference: `f"items written in {leaf} would be
   gitignored, so work filed there would not be tracked"`.
3. Amend the comment paragraph at `:684-690` ("Asked of a representative payload
   rather than of the folder or its `.gitkeep`…") with one sentence saying two
   differently-named payloads are probed and both must be ignored, so a rule
   naming one literal slug does not refuse the store. Do **not** touch the
   `ponytail:` note at `:696-700` — its three named gaps are all still real.

**Tests, in the same commit** (`tests/test_non_git_writes.py`, appended beside
the existing guard block at `:598-772`):

- `test_init_accepts_a_store_a_rule_names_one_item_slug_in` — default store,
  `.gitignore` is the single line `an-item*`, committed; `init(["work"], code,
  "demo")` returns and `(code / "docs" / "work" / "backlog" / ".gitkeep").is_file()`.
  Confirm before the source edit that this test raises `ValueError` matching
  `gitignored` — it is the criterion-1 red test. (Verified at this sha:
  `inbox/an-item.md` is ignored under `an-item*`, and `inbox` is the first leaf
  probed, so today's guard raises there.)
- `test_init_accepts_an_external_store_a_rule_names_one_item_slug_in` — same
  `.gitignore`, `work_path=code / "external" / "work"`; succeeds.
- `test_init_still_refuses_every_broad_ignore_rule` — `pytest.mark.parametrize`
  over the six `.gitignore` bodies from acceptance criterion 3 (`docs/work/`;
  `*`; `docs/**`; `docs/work/backlog/`; `docs/work/backlog/*` +
  `!docs/work/backlog/.gitkeep`; `**/state.yaml`), default store, each asserting
  `pytest.raises(ValueError, match="gitignored")` **and** `manifest(code) ==
  before` (criterion 5). Reuse the existing `git_init` / `commit_all` /
  `manifest` helpers already used at `:598-720`; add no fixture.

Two of the six rules (`docs/work/backlog/` and `docs/work/backlog/*` +
`!.gitkeep`) leave `inbox` visible and refuse at the `backlog` leaf — that is the
per-leaf semantics working, not a weakness. `**/state.yaml` likewise refuses at
`backlog` while `inbox` passes.

**Proof:** `python -m pytest tests/test_non_git_writes.py -q` green (17 `init`
tests pass today at this sha — baseline recorded). The two acceptance tests
`test_init_still_accepts_the_resolved_status_rules_it_writes_itself:724` and
`test_init_re_runs_on_a_healthy_external_store:755` must pass **unedited**;
they are the guard against a probe strict enough to refuse TCW's own scaffolding.

**Not in scope for this task:** `git_stage`, `git_mv`, `git_ignored`,
`resolved_ignore_rules`, and which leaves are probed. All four are spec
non-goals.

## Task 2 — Documentation Sync

**Modifies:** `docs/changelogs/upcoming.md` only (see the section below for why
the other three entries do not fire).

Amend the existing **unreleased** bullet in place. At this sha it is
`docs/changelogs/upcoming.md:82-91`, under `## Fixed` (`:6`); the sentence to
edit is `:85` — "It now probes a representative item path, skipping
`completed`/`discarded`." Change it to say it probes **two differently-named**
representative item paths and refuses only when both are ignored, so a rule
naming one literal slug no longer refuses an otherwise usable store. Do not add a
second bullet: the entry has not shipped, and a second bullet would read as a
regression-then-fix that never happened publicly. Leave the ceiling sentence at
`:88-91` ("a rule naming one slug") intact — it is still true.

**Proof:** `grep -n "representative item path" docs/changelogs/upcoming.md` shows
the amended wording; `grep -rn "work store folder" tcw/ tests/` returns nothing
(criterion 6).

## Criterion → task

| # | Acceptance criterion | Task |
| --- | --- | --- |
| 1 | False refusal gone, default store (`an-item*`) | 1 — `test_init_accepts_a_store_a_rule_names_one_item_slug_in` |
| 2 | Same for an external store | 1 — `test_init_accepts_an_external_store_a_rule_names_one_item_slug_in` |
| 3 | All six broad rules still refuse | 1 — parametrised `test_init_still_refuses_every_broad_ignore_rule` |
| 4 | Existing suite unchanged (`:598,651,673,690,708,724,755`) | 1 — run unedited; `:724` and `:755` named explicitly |
| 5 | Nothing written on refusal | 1 — guard stays above `fs.py:710`; `manifest(code) == before` in the new parametrised test and in the existing `:598,651,673,690,708` |
| 6 | Message: leaf + `gitignored`, no `work store folder is inside` | 1 (rewording) + 2 (`grep` proof) |
| 7 | `pytest` green, `tcw validate` clean | Verification |

## Documentation Sync

The project's four declared entries (`tcw-config.yaml` → `work.documentation`,
printed by `tcw work docs`), each evaluated:

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | Public-API | **No.** README never documents this refusal — `grep -n "gitignore" README.md` hits only `:193` (the `completed/`/`discarded/` rules `init` writes), `:213`, `:218`, `:1148`, none about the guard. No CLI surface changes. |
| `docs/release-notes/upcoming.md` | Public-API | **No — verify, do not edit.** `:47-57` already covers the guard in user language ("It turns down a store your `.gitignore` excludes … whether it covers the whole store, one status folder inside it, or just the items in that folder"). That sentence describes broad rules and stays true; a rule naming one literal item slug was never what it promised to refuse. Nothing to add and nothing contradicted. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes** — Task 2, amend `:82-91` (sentence at `:85`) in place. |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **No.** No CLI surface, model, lifecycle, or guardrail change reaches a skill. The nearest mention is `skills/tcw-work/references/transitions.md:16`, which is about a gitignored *transition destination* (`git_mv`), not this guard, and is untouched. `grep -rn "an-item" skills/` returns nothing. |

Capability ledger: the spec settled this — **no delta**. The two entries that
describe the guard (`docs/capabilities/cli/scaffold-the-doc-trees/`,
`docs/capabilities/work/configure-the-work-store-location/`) describe it by
intent, not by probe, and neither quotes the message. `implement` re-runs the
check as usual.

## Verification

Beyond the suite:

1. `python -m pytest -q` — full suite green (criterion 7).
2. `tcw validate` on this repo — clean (criterion 7).
3. `grep -rn "work store folder" tcw/ tests/` — empty; `docs/` returns only this
   item's own spec/plan (criterion 6). The current single hit is
   `tcw/store/fs.py:707`.
4. Manual reproduction, in a throwaway repo under `/tmp` (never in this
   checkout): `git init`, `printf 'an-item*\n' > .gitignore`, commit, then
   `tcw init --components work` — succeeds after the change, refuses before it.
   Then `printf 'docs/work/\n' > .gitignore`, commit, re-run — still refuses,
   and the message names the leaf.
5. Not checkable by the suite: that the reworded message reads as a sentence
   about items rather than about the folder. A human reads the refusal once.

## Notes

**Item 2 — the spec's experiment table, independently re-run.** Throwaway repo
`/tmp/tcw-probe-plan-exp`, `git check-ignore -q --no-index` per probe, one
`.gitignore` per row, store at `docs/work/`:

| rule | `backlog/an-item/state.yaml` | `backlog/some-slug/state.yaml` | `inbox/an-item.md` | `inbox/some-slug.md` |
| --- | --- | --- | --- | --- |
| `an-item*` | IGN | ok | IGN | ok |
| `an-item` | IGN | ok | ok | ok |
| `docs/work/backlog/an-item/` + `docs/work/inbox/an-item.md` | IGN | ok | IGN | ok |
| `a*` | IGN | ok | IGN | ok |
| `*item*` | IGN | ok | IGN | ok |
| `*slug*` | ok | IGN | ok | IGN |
| `docs/work/backlog/2026-*` | ok | ok | ok | ok |
| `docs/work/` | IGN | IGN | IGN | IGN |
| `*` | IGN | IGN | IGN | IGN |
| `docs/**` | IGN | IGN | IGN | IGN |
| `backlog/` | IGN | IGN | ok | ok |
| `docs/work/backlog/*` + `!docs/work/backlog/.gitkeep` | IGN | IGN | **ok** | **ok** |
| `**/state.yaml` | IGN | IGN | ok | ok |
| `*.yaml` | IGN | IGN | ok | ok |
| `*.md` | ok | ok | IGN | IGN |
| `*-*` | IGN | IGN | IGN | IGN |

Every row that decides the design agrees with the spec, with **one cosmetic
correction, non-blocking**: the spec's `docs/work/backlog/*` + `!.gitkeep` row
records IGN in both `inbox` columns. It is `ok`/`ok` — a rule scoped to
`docs/work/backlog/` cannot touch `docs/work/inbox/`. The verdict for that row is
unchanged (the guard runs per leaf and refuses at `backlog`), and criterion 3
still holds, so no design decision moves. Worth fixing in the spec's table if it
is edited for another reason; not worth an edit on its own.

**Item 4 — message rewording, verdict: safe, no assertion breaks.**
`grep -rn "work store folder"` across `tcw/`, `tests/`, `docs/`, `skills/`,
`README.md` returns exactly one non-item hit: `tcw/store/fs.py:707`, the string
being reworded. Every `match=` assertion on this guard matches on `gitignored`
alone — `tests/test_non_git_writes.py:610, 668, 685, 703, 719` — and the new
message keeps that substring, so all five survive untouched. The other
`match=` patterns in the same block target different refusals
(`not inside a Git repository` at `:593,626`, `non-pristine` at `:645`,
`work.path must be a string` at `:751`, `not a directory` at `:787`) and are
unaffected. Nothing outside `tests/` asserts on the text. The rewording therefore
costs one line and breaks nothing — keep it.

**Item 3 — existing tests re-derived at `a875de9`.** The spec's line numbers are
still accurate: `:598` `test_init_refuses_a_work_path_git_would_never_track`,
`:651` `…_even_once_it_is_tracked`, `:673` `…_whose_status_folder_the_rules_hide`,
`:690` `…_whose_items_the_rules_hide`, `:708` `…_default_store_whose_items…`,
`:724` `test_init_still_accepts_the_resolved_status_rules_it_writes_itself`,
`:755` `test_init_re_runs_on_a_healthy_external_store`; refusal assertions at
`:610, 668, 685, 703, 719`. Both counterweight tests exist and say what the spec
claims. Baseline: `pytest tests/test_non_git_writes.py -k init` → 17 passed.

**Item 9 — collision with the write-time sibling: none; either order works.**
`2026-08-20-enforce-the-gitignore-trap-at-write-time-not-only-at-init` changes
`git_stage` (`tcw/store/fs.py:305`) and `git_mv` (`:359`), adding a stderr
advisory at each. This item changes only the pre-flight loop inside `init`
(`:703-709`). Same file, disjoint functions, no shared helper edited — that
sibling's non-goals explicitly exclude "the `init` guard's probe shape", and this
one's exclude write-time enforcement. Neither blocks the other; no
`--blocked-by` needed. The only contact points are textual: both will edit
`docs/changelogs/upcoming.md`, and the sibling edits
`docs/capabilities/work/configure-the-work-store-location/description.md` while
this item leaves it alone. Whichever lands second rebases over a changelog hunk.

**Batching.** The initial request batches this with four other `bug` items into
one patch release. The changelog amendment above is written for that shared
`upcoming.md`; do not cut a version as part of this item.
