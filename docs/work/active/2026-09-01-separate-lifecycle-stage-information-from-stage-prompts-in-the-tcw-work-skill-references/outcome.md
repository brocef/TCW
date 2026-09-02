# Outcome: separate lifecycle stage information from stage prompts

All six plan tasks shipped, in five commits. `inbox` is no longer the stage TCW
has no instructions for: it ships a built-in prompt, `tcw work stage inbox`
prints it with no work item reference, and its skill document is a router like
the other six.

## What shipped, task by task

| Task | Commit | What landed |
| --- | --- | --- |
| 1 — move and relink | `c705af8` | 11 `git mv`s into `references/lifecycle/` and `references/procedures/`; every inbound link rewritten; test path constants follow |
| 2 — pointer sentence | `4027fda` | The six existing routers instruct rather than describe |
| 3 — the prompt and the command | `d5a3e09` | `tcw/work/prompts/inbox.md`; `resolve.py` ships all seven; `cli.py` gains the no-item path; `stage-inbox.md` becomes a router; tests replaced |
| 4 + 5 — defaults note and `SKILL.md` | `10889a4` | `references/lifecycle/default/README.md`; `SKILL.md` routes to it and restates the division of labour once |
| 6 — Documentation Sync | `63e66ad` | README, `commands.md`, release notes, changelog |

## Test result

`pytest -q` → **2184 passed, 5 failed**. All five fail identically on clean
`HEAD` with this item's work stashed, and none is caused by it:

- `test_atomic_write_preserves_prior_on_failure`,
  `test_atomic_write_temp_cleanup_on_failure`,
  `test_an_unwritable_target_reports_and_prints_no_path`,
  `test_invalid_utf8_is_replaced_rather_than_fatal` — this container runs as
  uid 0, and `chmod`-ing a directory read-only does not stop root writing to it.
- `test_the_prompts_are_in_the_built_wheel` — its `pip wheel
  --no-build-isolation` fails on this image's Debian-patched setuptools
  (`AttributeError: install_layout`) before reading anything.

That last one is the only pre-existing failure that guards something this item
changed, so its claim was verified by hand instead: a wheel built **with**
isolation contains all seven `tcw/work/prompts/*.md`, `inbox.md` among them and
non-empty. The packaging path is unchanged — `pyproject.toml` already ships
`"tcw.work" = ["prompts/*.md"]`, and the new file matches that existing glob.

### Acceptance criteria

Every criterion verified from command output, except as noted.

| # | Result |
| --- | --- |
| 1 | Pass — no test skipped, deleted, or weakened; the two inverted assertions have replacements |
| 2 | Pass — `tcw work stage inbox` exits 0, 47 lines on stdout, stderr empty |
| 3 | Pass — `tcw work stage inbox some-slug` exits 1, stdout empty, stderr says the stage takes no work item |
| 4 | Pass — `tcw work stage spec <slug>` output is **byte-identical** to the pre-change binary's, diffed directly |
| 5 | Pass — all seven ids |
| 6 | Pass — 47 lines, 40 non-blank |
| 7 | Pass — 24–37 lines, ceiling 40 |
| 8 | Pass — 7 of 7 |
| 9 | Pass — `git log --follow` reaches `dafbe8e`, a pre-item commit |
| 10 | Pass |
| 11 | Pass — the grep prints nothing |
| 12 | Pass, with corrections to the list itself (below) |
| **13** | **Not met, for a pre-existing reason — see below** |
| 14 | Pass — `tcw capabilities check` exits 0 |
| 15 | Deferred to `complete`, as the spec scheduled it |
| 16 | Pass — 60 lines, at budget |

## What the plan and spec got wrong

**Criterion 13 cannot be met by this item.** `tcw validate` exits **1**, on four
dangling `tcw://` references in three *other* backlog items, all pointing at two
work items that no longer exist. The output is byte-identical with this item's
changes stashed, and this item touches none of those files. The plan's measured
baseline recorded `tcw validate → exit 0` at the `plan` stage; that is no longer
true and was already untrue before this item's first commit. Fixing it means
either restoring those items or teaching `validate` to grade its exit codes —
the latter is already tracked as
`2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`.
Nothing was done here; widening this item to chase it would have been scope
growth.

**Criterion 11's grep is not the complete check the spec claims.** It matches
`references/<name>`, so it cannot see a link written as a bare sibling path.
Three real inbound links were invisible to it and would have dangled:
`commands.md` → `audit-backlog.md` and `consolidate-plans.md`, and
`cross-node-deltas.md` → `decompose.md`. They surfaced only by resolving every
relative Markdown link in `skills/`, `commands/`, and `agents/` against the
filesystem, which is what was actually used as the check. The grep is kept as a
criterion because it is what the spec promised, but it is the weaker of the two.

**Criterion 12's list was both incomplete and partly wrong.** It missed
`agents/tcw-backlog-auditor.md`, `commands/tcw-audit-work-backlog.md`,
`commands/tcw-consolidate-plans.md`, `commands/tcw-post-mortem.md`, and the
docstring in `tcw/work/templates.py`. It listed `skills/tcw-plugin/SKILL.md (1)`,
which needed no edit: that mention is a bare filename, not a path, and the
filename did not change. The repo-wide grep was used as the source of truth
rather than the list, as the spec itself directs.

**A dangling link pre-dated this work.** `decompose.md` pointed at
`cross-node-epic.md`, which has never existed in `references/`. Fixed to
`cross-node-deltas.md` — it was one word inside a file already being edited for
its new depth, and goal 5 asks for no dangling link.

**Task 2's replacement is one line longer per document, not "not longer".** The
pointer sentence has to stay unwrapped on one line, because criterion 8 asks for
a literal contiguous string and wrapping between "by" and "running" would break
it. Six documents each grew by one line; the tallest is now 37 against a ceiling
of 40.

**Task 5's "no line is added" was wrong in detail, right in outcome.** Folding
the `default/README.md` pointer into the existing bullet cost one line, not
zero. The spec flagged this as inference in its `## Notes`, and the rule it named
applied: the line was paid for by merging the two `procedures/` entries into one
`·`-separated bullet in the style the list already used. The body is still 60.

**The prompt does not say `docs/work/inbox/`.** The router it was condensed from
did. A filesystem path is the FS adapter's answer to "where is the inbox", and
this is text every store's users read, so the prompt says "the work inbox". A
deliberate deviation from a straight condensation, on the litmus test's terms.

**The `inbox` branch is a separate function, not an inline replacement.** The
plan described rewriting the refusal at `cli.py:785-790` in place. It became
`_stage_without_item`, called from a guard near the top of `_stage`. Inlining it
would have interleaved a path that skips the item lookup with one built around
it, and `_stage`'s docstring documents its order — `id → item → legality → checks
→ resolve → print` — as the contract. Same behavior, and both docstrings stay
true.

**The condensation risk did not materialize.** The plan's first risk was that the
70-line document would not fit 50 without losing a rule. It landed at 47 with all
six carried-over items intact — the one-item-or-several judgment, the tag step,
the `inbox accept` naming rules and `--title` override, `## References` with a
reason each, the instruction not to ask the requester here, and all three
`Exit badly` branches. Nothing was cut that the plan named as content.

## Notes

The end-to-end demonstration, run in a scratch node created with
`tcw init work --id scratch` and no lifecycle configuration at all:
`tcw work stage inbox` exits 0 and prints the built-in prompt, byte-identical to
what this repository prints. That is the state every node starts in, and it is
the case the whole item exists to fix.

`STAGE_STATUSES["inbox"]` is still `()`. Nothing now reads that emptiness as a
refusal — the branch is chosen by stage id — and both the table test and the
`_stage` docstring say so, so a later reader does not have to re-derive why an
empty legality row is not a rejection.

The full Cartesian legality sweep in `test_stage_verb.py` still covers
`inbox` × every status and still expects rejection, which is correct: with a
work item passed, `inbox` is refused. It passes unchanged, by a different code
path than before.
