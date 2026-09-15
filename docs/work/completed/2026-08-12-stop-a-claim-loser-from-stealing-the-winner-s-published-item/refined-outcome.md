# Refined outcome

Accepted on 2026-08-12. The user declined to review the diff and authorized
completion, the tag move, and the push.

## Acceptance evidence

Each acceptance criterion, against what was actually run:

- **Four contenders, exactly one success.** A standalone reproducer at 150
  rounds × 4 contenders went from 7 violations to 0, then 0 across 600 further
  rounds. The suite's stress test now races four contenders over 25 items.
- **A loser handed the winner's published item.**
  `test_a_loser_cannot_claim_the_winner_s_already_published_item` publishes the
  winner between `start()`'s two lookups and asserts `AlreadyClaimed` naming the
  winner, the item still in `active` with the winner's owner, and no residue in
  `.claiming/`.
- **Two status folders in one walk resolve to one item; a genuine duplicate
  still raises.** Both pinned, the second deliberately passing with and without
  the fix — it guards against the re-walk swallowing the condition it preserves.
- **A walk that hits a vanished directory returns the rest of the board.**
  Pinned.
- **CI green on every supported Python.** Two consecutive runs on 3.11 and 3.14,
  after the first run before these fixes failed outright on both.

## Why the evidence is stronger than last time

The previous item was accepted on a green local suite and reasoning, and that
was not enough. What is different here is not the volume of tests but where the
evidence comes from: each defect has a deterministic test that fails without its
fix, the severe one has a measured before/after rate rather than an absence of
failures, and CI — the only place two of the three ever appeared — has now run
the fixed code twice.

That still is not proof. A race that appears once in twenty rounds cannot be
proven absent by any number of green runs. It is the difference between "we did
not see it" and "we saw it, we measured it, and we no longer see it".

## Closeout

- **Route:** committed directly on `main`. No branch or PR.
- **Review:** none. The user declined, having seen the failure analysis.
- **Documentation:** `docs/changelogs/v0.20.1.md` [Any-Code-Change] and
  `docs/release-notes/v0.20.1.md` [Public-API] updated — the fold into `v0.20.1`
  was already in flight, so these entries joined it rather than opening a new
  `upcoming.md`. `README.md` and `skills/tcw-work/SKILL.md` did not fire: no CLI
  surface, model, lifecycle, or guardrail change.
- **Capabilities:** none declared or changed. `work/start-a-work-item` already
  describes single-winner behavior — it was describing something the
  implementation did not guarantee, and now does.
- **Follow-ups:** none new. The two deferred reader findings remain tracked as
  `2026-08-12-teach-the-remaining-readers-to-tell-a-vanished-item-from-an-absent-one`.
- **Version:** folded into `v0.20.1`, whose tag moves from the commit CI failed
  on to the accepted HEAD.

## Notes

Worth carrying forward, since it cost two CI rejections and one premature
acceptance: an enumeration of *reads* will not find a defect in a *rename*. The
claim lookup was never classified as a window because it did not look like one.
