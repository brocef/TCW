# Refined outcome

Accepted on 2026-08-12, on the second pass, after `rework.md` returned the item
on 2026-08-11.

## Acceptance evidence

The three criteria CI rejected:

- **Criterion 1** — exactly one success and one typed `AlreadyClaimed`. The test
  that failed on CI,
  `test_two_store_claim_has_one_winner_and_visible_metadata`, passes, and the
  crash beneath it is closed where it originated rather than at the call site.
- **Criterion 2** — repeated stress races. Now 25 rounds per session instead of
  one, asserting a single winner, exclusive residence in `active`, and visible
  claim metadata each round.
- **Criterion 3** — a loser is told the winner without a stack trace. Four
  deterministic tests plus a six-case manual operator check; every path exits
  cleanly, and `no such work item` now appears only for slugs that really are
  absent.

Criteria 4–11 were delivered in the first pass and are unchanged; the full
suite, the web suites, the Playwright suite, and all node validation pass.

## The limit on this acceptance, stated plainly

**CI is what rejected this item twice**, on `ubuntu-latest` / Python 3.14 with 2
cores, and neither failure ever reproduced on the maintainer's machine. 1221
tests pass locally, but a many-core laptop cannot schedule threads the way that
runner does. The deterministic tests are the real evidence — they force the gap
between two calls rather than hoping to land in it — while the stress test is
evidence only where the scheduler is constrained.

So this acceptance is on the reasoning and the deterministic coverage, not on a
green local suite. The confirming signal is CI on the pushed commit, which is
why the release tag waits for it.

## Closeout

- **Route:** committed directly on `main`, 28 commits. No branch or PR.
- **Review:** self-reviewed before submission (Opus, Codex, and a local-LLM pass
  concurrently) at the user's request. Six findings — one real defect
  (`_claiming_dirs` matching `{slug}-*`, where `*` spans `-`), two test gaps
  that mattered because the untested branch was the one CI crashed on, and one
  confirmation of the design. All fixed. Two verified findings deferred with
  reasons. Three local-LLM findings rejected on verification. Full record in
  `outcome.md`.
- **Documentation:** `docs/changelogs/upcoming.md` [Any-Code-Change] and
  `docs/release-notes/upcoming.md` [Public-API] updated. `README.md` did not
  fire — no CLI surface change, and it already documents contention and
  takeover. `skills/tcw-work/SKILL.md` did not fire — no change to the CLI
  surface, model, lifecycle, or guardrails it teaches.
- **Capabilities:** reconciled in the first pass and unaffected by the rework;
  `tcw capabilities check` and `tcw validate` pass.
- **Follow-up:**
  `2026-08-12-teach-the-remaining-readers-to-tell-a-vanished-item-from-an-absent-one`
  carries the deferred findings — readers that treat a transient `None` as
  absence. Filed rather than folded in because the fix is a layering decision
  (`.claiming/` is a filesystem-adapter private detail that `base.py` must not
  consult), and because improvising one more site-by-site patch is the exact
  mistake `rework.md` was written about.
- **Version:** folded into `v0.20.1` rather than cut as `v0.20.2`. That tag was
  cut but never pushed, so it exists nowhere but this machine and can still be
  re-pointed — and as it stood it named a commit that still contained this
  item's bug. Pushing it unchanged would have run the release workflow against
  the defect, which is how `v0.20.0` came to be withdrawn.

## Notes

`rework.md`'s release-impact section is stale in one respect and correct in
spirit: it says the version files read `0.20.0` and that the release should be
re-tagged rather than re-cut. `v0.20.1` has since been cut, so the specific
instruction no longer applies — but its underlying point, that an unpublished
release should be corrected in place rather than stacked on, is what was done.

TCW's first PyPI publish was blocked on this item.
