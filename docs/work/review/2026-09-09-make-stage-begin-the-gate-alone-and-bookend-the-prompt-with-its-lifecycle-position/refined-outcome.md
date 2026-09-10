# Refined outcome: `stage gate` alone, with bookended prompts

**Accepted** on 2026-09-10, verified against `f355e02` on
`feat/stage-gate-and-prompt-verbs`.

## The decision

Accepted. All sixteen criteria hold, with two deviations recorded below. This is
the last item on the branch, so HEAD is its final state.

Known defects are left unfixed, deliberately. Most of the round's defects
originate in this item's rename commit `1ecce6a`; they are recorded in
`docs/work/inbox/2026-09-10-verification-findings-on-the-stage-verb-branch.md`.

## Evidence

All CLI evidence came from a throwaway node with `pre` and `prompt` bindings bound
to sentinel files.

| Check | Result |
| --- | --- |
| `tcw validate` | exit 0 |
| `tcw capabilities check` | exit 0 |
| Targeted test files | 390 passed, then 50 passed |
| `pytest -q` (run for item 1, same HEAD) | 2450 passed, 0 failed |

The gate exits 0 with zero bytes on stdout and one stderr line naming the reading
verb. It refuses an illegal status with exit 1 and empty stdout. It runs `pre`
bindings and creates their sentinel; a bound `exit 7` gives exit 1 with the reason
on stderr. It resolves no prompt at all: the `generate:` sentinel stays absent
under the gate and appears under the reading verb.

`bookend()` is defined in `tcw/work/resolve.py` and its only caller in the package
is `tcw/work/cli.py:1026`, inside `_stage_tail`, behind `if res.text:`.
`resolve_prompts` returns unwrapped text, so a stage that resolves to nothing
stays nothing rather than becoming a header and footer around an empty middle.
`test_a_stage_that_resolves_to_nothing_is_not_bookended` pins it. This confirms
`outcome.md`'s claim that the wrapper is the CLI's rather than the resolver's.

`STAGE_NEXT_STEPS` is complete for all seven stages and guarded three ways at
`tests/test_stage_verb.py:94`, `:101` and `:136`: coverage of every id in
`STAGE_IDS`, every cited command resolving against the real parser by longest
matching prefix, and a transition named only where `STAGE_STATUSES` says one is
needed.

The recorded fixture is correct: all six `argv` arrays carry the reading verb, the
frozen stdout carries both bookends, and the slug is normalised to `<slug>` so the
fixture expires when the text changes rather than at midnight.

## The two deviations

**The spec's footer table is wrong and the shipped code is right.** The spec's
`implement` row says the footer should read ``tcw work submit <slug>``, then
``tcw work stage gate verify <slug>``. `tcw/store/base.py:1177` ships only the
second, and that is correct: `verify` is legal from `active` as well as `review`,
so naming `submit` would move items to `review` for no reason and would preempt a
decision the `verify` instructions already own. The third guard derives this from
`STAGE_STATUSES` and is what caught it. `outcome.md` does not list this among the
four decisions it says moved during implementation; it should have.

**One sentence in the migration guide is false**, and it is new in `1ecce6a`:

> A stage you have deliberately silenced with `{blob: ""}` stays silent and is not
> wrapped.

Both halves are false. `_parse_binding` rejects the empty string, the binding is
dropped, and the stage falls back to the built-in floor — which the CLI then
wraps in both bookends. Reproduced: validation reports
`binding 'blob' must be a non-blank string`, and the stage prints 2540 bytes.

True replacement: *a stage whose bindings all carry a `when:` condition that does
not match resolves to nothing, and nothing is not wrapped.*

The root cause predates this branch. `tcw/store/base.py:1362` gives the same bad
advice in an error message, and this item copied it into a user-facing document.
Filed as
`docs/work/inbox/2026-09-10-untested-skill-guards-and-the-blob-silencing-advice.md`,
because whether silencing a stage should be supported at all is a design question
rather than a patch.

## The rename missed five places

This item's commit message says it set out to name the right one of the two verbs
everywhere. Five places still put the reading verb where the meaning is the
refusal:

- Two lines in `docs/changelogs/upcoming.md` describing the refusal guarantee,
  among five stale lines in that file overall.
- `docs/capabilities/work/read-the-documentation-gate-for-a-change/description.md`,
  which asserts the reading verb is "correctly refused because the item is
  closed". It refuses nothing; it exits 0 with a note on stderr.
- `tests/fixtures/prompt_fallback/capture.py`, whose docstring says `tcw work
  stage` refuses out-of-status stages — true of the gate, false of the verb the
  script captures.

Any fix should sweep for the pattern rather than patch the named lines. The
changelog matters most: it is the changelog for the version about to be cut, not
an archive.

## Also deferred

The removed-form message hands every stage the same `<slug>` placeholder, so
`tcw work stage inbox` advises a command that is itself refused on **both** verbs,
because `inbox` takes no reference. Two wrong turns. No criterion covers it:
criterion 5 only requires the handler to name both verbs and exit 2, and criterion
6 tests the two verbs directly rather than the advice string.

## Capability reconciliation

This item edited two capability descriptions in `1ecce6a` and declared neither, as
it carries no `capabilities.yaml`. `run-a-lifecycle-stage` came out correct; the
documentation-gate description did not, and the false statement in it survived
every review of this branch precisely because nothing pointed a reviewer there.
See the note in the split item's refined outcome.

## Closeout

- **Merge route:** merged locally into `main`, no pull request.
- **Version:** 2.0.0 offered separately, after all four items complete. A multi
  review runs before the cut.
- **Originating issue:** none.
- **Post-mortem:** not run.
