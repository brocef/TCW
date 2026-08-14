# Ship built-in stage prompts with the CLI

Child **C6** of `2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`.

## Product changes

Today an agent only knows how to run a lifecycle stage because a *skill* told
it. That makes the methodology a plugin artifact: a Codex user, or anyone
driving `tcw` without the plugin installed, gets the state machine and none of
the judgment for operating it. The epic's fix is for the CLI to answer the
question itself.

So: **ship the default stage instructions inside `tcw`.** With nothing
configured, asking the CLI for a stage should print usable instructions for that
stage. A node that binds its own prompt still wins; the built-in is the floor,
not a ceiling.

`inbox` is deliberately excluded — it runs before an item exists.

## Technical changes

The mechanism already exists. C3 shipped the `builtin` kind and the resolution
library; C4 shipped the stage verb that prints what resolves. **C6 ships only
the content and its packaging** — the prompt files themselves, and whatever it
takes for them to survive into an installed wheel rather than existing only in
a source checkout.

## Meta changes

None. C7 rewrites the skill and README to point at this; C6 does not.

## Constraints

Decided by the requester at this stage, so `spec` is not re-litigating them:

1. **Content comes from TCW's own stage documents, condensed.**
   `skills/tcw-work/references/stage-*.md` already encode this project's
   methodology, and C7 is going to reduce those same documents to routers. The
   content should *move*, not be re-invented — a fresh rewrite risks the CLI and
   the skill disagreeing at exactly the seam C7 has to reconcile. Borrow from
   superpowers only where it says something the stage documents do not.

2. **Each prompt is terse — roughly 25–40 lines.** This is text an agent reads
   at every single stage entry; the full 60–90-line treatment is too expensive
   for that position. Purpose, what to produce, and the handful of steps that
   actually change behavior.

3. **The tension in (1) + (2) is real and `spec` must resolve it explicitly.**
   Condensing 60–90 lines into 25–40 leaves judgment behind. The epic's
   criterion 18 says C7's routers must not restate what the prompts say — so
   whatever C6 drops is either genuinely droppable, or it is TCW-specific
   judgment the skill legitimately keeps (delegability, epic deltas,
   `[gated]`/`[judgment]` markers). The spec should say which is which, per
   stage, rather than leaving C7 to discover the gap.

4. **Verification cannot depend on C4.** C6 and C4 are parallel and C6 may land
   first; the epic already requires criterion 14 be tested against C3's
   resolution library rather than through `tcw work stage`. An installed-wheel
   check is also required — "the file is in the source tree" is not the claim.

## References

- `/Users/brian/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0`
  — the locally installed [obra/superpowers] plugin the epic names as the
  inspiration. Readable without network access. Requested by the requester as
  the one outside source worth reading.
- `skills/tcw-work/references/stage-*.md` — the seven stage documents whose
  content this item condenses, and which C7 later reduces to routers.
- The epic's `spec.md` §"Default prompts" and acceptance criterion 14, and its
  `plan.md` §C6 — the boundary, and what "verified" means here.

## Notes

- Asked for reference material; the requester named the superpowers plugin.
  Everything else above is in-repo.
- The stage/prompt registry is C3's and C4's shipped code, not this item's to
  change. If writing the content exposes a defect in either, that is an
  escalation, not a quiet fix here.

[obra/superpowers]: https://github.com/obra/superpowers
