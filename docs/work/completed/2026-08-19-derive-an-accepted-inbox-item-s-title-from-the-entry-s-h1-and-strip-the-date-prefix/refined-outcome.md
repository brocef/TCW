# Refined outcome — Derive an accepted inbox item's title from the entry's H1 and strip the date prefix

**Accepted** by the user on 2026-08-20, after a verification pass run in a
session resumed from a crash. All 26 acceptance criteria hold; the ledger is
reconciled; no rework was needed. The version stays at `v1.0.0` and the
changelog entries stay in `upcoming.md` — this change ships in a later cut.

## What the crash cost, and what it hid

The crashed session had committed `outcome.md` and the `→ review` transition,
then run a review of its own diff and **left three fixes uncommitted in the
working tree**. Nothing was lost — the fixes were intact and their tests were
written — but nothing was recorded either, so the diff the item claimed to have
shipped and the diff on disk had diverged.

The fixes, committed at the head of this verification:

| Commit | Defect the review found |
| --- | --- |
| `cb1c624` | A fence closed on *any* run of its delimiter, so ```` ```not-a-closing-fence ```` inside a ```` ```sh ```` fence ended it and `body_title` selected `# Fake title` from inside the code block. A closing fence carries no info string; the rule now requires the line be nothing but the run. |
| `ecbb2d7` | `inbox_accept`'s slug fallback used the entry's **unstripped** filename, so an entry whose title does not slugify put the entry's own date back beside the acceptance date — the exact bug this item exists to kill, surviving inside the fix for it. |
| `eb7fb53` | `FsWorkStore.create_work` took `created` on trust and it prefixes the slug; `tcw serve`'s `POST /api/work` passes the field straight through, so a long value produced `OSError: [Errno 63]` and any other string produced a non-date in `state.yaml`. Parsed with `date.fromisoformat` now, which validates and canonicalizes; `serve` maps the `ValueError` to a 400. |
| `682d024`, `1797319` | The capability sentence, README, `stage-inbox.md`, changelog and release notes for the above. |

**Two of those were acceptance-criteria failures, not polish.** Criteria 14 and
15 specify that an H1 of `# 東京` or `# !!! ???` in a label that also slugifies
to empty produces `<today>-untitled`. Before `ecbb2d7` they produced
`<today>-2026-08-01`. `outcome.md` reported the item as shipped-as-planned with
1850 tests green, and it was wrong on this point — the hand checks it recorded
covered the reporter's reproduction and the delegate/escalate round trip, but
not the degenerate-label corner, and no test covered it either until the review
wrote one. See `## Where the process nearly let this through`.

## Evidence

Every claim below is output from a command run during this verification, on the
tree at `8832a93`, not a number carried forward from `outcome.md`.

**Full suite: `1859 passed` in 448.42s (7m28s), 0 failed.** `outcome.md` recorded
1850; the difference is exactly the nine tests the review fixes added (two fence
cases in `tests/test_inbox_title.py`, a four-way parameterized delegate
round-trip in `tests/test_recursion.py`, a two-way parameterized slug test and
the `created` test in `tests/test_work.py`).

**Fresh scratch node, `tcw` from this working tree.** Criteria checkable by
running the command, all observed today:

| Criterion | Observed |
| --- | --- |
| 1 — the reporter's bug | title `Another Raw Request`, slug `2026-08-20-another-raw-request`. One date. |
| 4 — no H1 | title `no-heading`, slug `2026-08-20-no-heading`. One date. |
| 5 — H1 inside a fence | title `Real title` — the fence fix; `# Fake title` stayed in the code block. |
| 8 — `--title` wins | `Clean Title` over a body declaring `# A Competing Heading`. |
| 9 — `inbox list` unmoved | `2026-08-19-list-check.md \| file \| 2026-08-19-list-check`. Still filename-derived. |
| 14, 15 — degenerate labels | `2026-08-20-untitled` (title `東京`) and `2026-08-20-untitled-2` (title `!!! ???`). |
| 16 — 300-char H1 | slug component `len == 131`, `state.yaml` title `len == 300`. No `OSError`. |
| 17, 18 — `tcw work new` | 300 a's → a 131-char slug; `東京` → `2026-08-20-untitled-3`; a normal title unchanged. All exit 0. |
| 19 — behavior that must not move | `2026-08-19.md` → title `2026-08-19`; `2026-08-18-.md` → title `2026-08-18-`. Neither raises. |

Criteria 2, 3, 6, 7, 10–13 and 20–23 are carried by the suite. Criteria 24–26
were verified by reading the files: `stage-inbox.md` step 5 no longer mandates
`--title`, `README.md` states the precedence including the date-only exception,
`docs/work-inbox-template.md` opens with the placeholder
`# <one-line title of this request>` (which discharges the spec's second Risk —
a user copying the template no longer inherits a literal title), and both
`upcoming.md` files carry entries.

`tcw validate` → `validate OK`, exit 0. `tcw capabilities check` →
`capabilities OK`, exit 0. `tcw capabilities drift` → `no capability drift`.

## Capability reconciliation

`capabilities.yaml` declares two `changed:` entries and no `new:`, so there is
no `Missing → Supported` flip to make; both were and remain `Supported`, and the
completion gate has nothing to block on. Both descriptions were read as a user
and both are true of what shipped:

- `work/manage-the-work-inbox` states the three-step precedence and now the
  date-only exception ("An entry named nothing *but* a date keeps it, since
  stripping it would leave no name at all").
- `work/open-a-work-item` states the slug floor.

**The `created` refusal needs no ledger statement.** It is not reachable from
the CLI — `tcw work new` exposes no `--created` — and on the surface where it
*is* reachable, `web/editing` already says a save the store refuses "comes back
as that refusal in plain words, and nothing is written". The new `ValueError`
is an instance of that standing sentence, not a new user-visible capability.

## A documentation defect found during verification, and fixed

Cross-reading the changelog against observed behavior turned up two claims the
review fixes had outdated — the code was right, the prose was not:

1. *"The slug never falls back to the unstripped label, so **no entry name can
   put a second date in it**."* The second clause overstates the first. An entry
   named nothing but a date and carrying no heading still produces a doubled
   date, because the date *is* its title and slugifies fine — the label fallback
   is never consulted. That is criterion 19's accepted case, so the behavior is
   correct and the sentence was wrong.
2. The `body_title` bullet still described the fence rule as it stood *before*
   `cb1c624` tightened it. The docstring in `tcw/store/base.py` had been updated;
   the changelog had not.

Both corrected in `8832a93`. Worth naming as a pattern: when a review fix
changes behavior, the changelog paragraph written for the *original* behavior is
the artifact most likely to be left behind, because it reads as already-done.

## Accepted residual behavior

`2026-08-19.md` with no H1 still yields `2026-08-20-2026-08-19`. The spec's
Risks section named this and accepted it; `--title` covers it; the changelog now
describes it accurately rather than claiming it away. Not filed as a follow-up —
it is documented intent, not debt.

## Where the process nearly let this through

Recorded here rather than in a post-mortem, which the user did not ask for.

`outcome.md` asserted "Shipped as planned… no task was abandoned, no design was
improvised" and backed it with 1850 green tests and four hand checks. Two
acceptance criteria were failing at that moment. The gap is specific and
cheap to close: **the hand checks the plan reserved for `submit` were chosen to
demonstrate the fix, not to attack it.** They ran the reporter's reproduction and
the delegate/escalate round trip — the paths the item was *about* — and the
degenerate-label corner that criteria 14 and 15 exist for was left to a test
that had not been written, in a file (`test_recursion.py`) that approximated
delegated entries by hand instead of calling the real `delegate`. The
review-written test now goes through `delegate` end to end, and its docstring
says why: *"Approximating these entries by hand is what let that case through
the first time."*

The `implement` stage's own claim of green is not verification. This item is the
argument for the `verify` stage reading the diff against the criteria one at a
time rather than trusting the outcome's summary of itself.

## Notes

Five follow-ups filed at the previous item's closeout (`1c7e7cd`) sit in the
backlog and are untouched by this item. No new follow-ups were opened here.

The version stays `v1.0.0`, which is tagged and pushed, so folding this work
into it is not available. `docs/changelogs/upcoming.md` and
`docs/release-notes/upcoming.md` keep accumulating; the cut is a later decision.
