# Refined outcome — Restructure TCW's skills

## Decision

**Accepted.** On 2026-09-14 the requester had first kept this item for their own
review. They then told the coordinating agent to finish the skills work and merge
each piece into `main` once it is ready. Readiness was judged the way it was for
the eval-checks item: a multi review plus the test suite, capped at two rounds.

After round 2, Codex still had one finding about how strong a test was. The
requester was shown it and chose to tighten the test, run the suite and merge,
with no third round.

Merged into `main` as `8342925b`.

## Evidence

- **Full suite.** Bare `pytest` in the worktree:
  - **3067 passed** at `feb4771b`, after the rebase onto `main` after v2.1.3;
  - **3070 passed** at `0c095335`, after the round 1 fixes;
  - **3070 passed** at `02f43514`, after the round 2 test tightening.

  The only commit after that, `124019bc`, edits `outcome.md`.
- **After the merge into `main`.** `tcw validate` printed `validate OK`, and these
  test files gave 167 passed: `test_plugin_manifests`,
  `test_skill_lifecycle_parity`, `test_configuration_text_home`,
  `test_repo_lifecycle` and `test_eval_coverage`.
- **Shape.** `ls skills` lists the fifteen skills in the spec, and `commands/` no
  longer exists.
- **Acceptance criteria.** ACs 1–19 are recorded in `outcome.md`. AC 17 is
  narrowed, as departure 4 records.

## Review

**Developer's own adversarial review.** Recorded in `outcome.md` § Review.

**Rebase.** The coordinating agent rebased the branch onto `main` twice, after
v2.1.2 and after v2.1.3. What happened is recorded in `outcome.md` § Rebased onto
main after v2.1.3:
- the notes to two items were dropped, because those items had completed;
- the `upcoming.md` files were rebuilt to hold only this item's entries;
- `main`'s version number was kept in `marketplace.json`.

**Round 1 (`main..feb4771b`).**
- **Codex (read-only sandbox confirmed; worktree unchanged): NOT DONE.**
  - *Accepted:* `tcw-configure`'s `tracker.md` did not document tracker settings
    inheritance, or the rule that `credentials` must come from the same file as
    `base-url` or a nearer one.
  - *Accepted:* the rule about where to put shared tracker settings was still in
    `tcw-work`'s `commands.md`.
  - No defect was found in the other checks:
    - no live reference to a deleted name;
    - all thirteen deleted command procedures are reachable from a named skill
      document;
    - `tcw-work-stage` and the four `tcw-commands-*` skills work under Codex;
    - the eval cases name paths and skills that exist.
- **Adversarial code reviewer: NOT DONE.**
  - *Accepted:* the same tracker inheritance finding. v2.1.3 landed while this
    item was in review, and the spec's Risks section assigns the move to whichever
    item lands second.
  - *Accepted:* `outcome.md` did not reflect the rebase.
  - *Narrowed to a case note:* B11 can fail a correctly routed run when the agent
    creates `docs/release-notes/upcoming.md`.
  - *Filed as separate:* B4 and B8 only catch a wrong route into `tcw-setup`. This
    is a gap in the spec, not a departure from it.
- **`bllm`: no answer.** It reported "temporarily disabled for maintenance".

Fixes: `71cbf89b`, `0c095335` and `2ae0a860`.

**Round 2 (`feb4771b..2ae0a860`).**
- **Adversarial code reviewer: DONE.**
  - It ran `_resolved_tracker` on a parent-and-child project in a scratch folder.
    The results matched every rule `tracker.md` states.
  - It reverted each document in a copy and confirmed the matching test failed.
  - Its one small note (`tracker: {}` does not reach child projects) was acted on.
- **Codex (read-only confirmed): NOT DONE, on test strength only.**
  - It agreed the documents are correct.
  - `tests/test_configuration_text_home.py` still passed when "keep shared
    settings in a node without a board" was put back into `commands.md`, or when
    the `null` rule was made false.
  - Fixed in `02f43514`, after the requester's decision. Eleven deliberate
    breakages each turned a test red.

## Deferred follow-ups

- `docs/work/inbox/2026-09-14-guards-and-gaps-the-skill-restructure-review-left.md`:
  - the deleted-names test only covers the folders the spec named;
  - nothing checks that `EXCLUSIONS` and `PARTIAL` name shipped skills;
  - `install.md` doesn't say how to run the bootstrap script under Codex;
  - `tcw-work-stage`'s `<plugin>` placeholder has no Codex instruction;
  - the test helpers repeat each other;
  - B4 and B8 don't catch a wrong route into `tcw-configure`.
- **Not verified here:** whether agents actually route correctly, which needs the
  paid eval run, and behavior in a real Codex session.

## Closeout

- **Capability ledger.** The spec named two changed capabilities,
  `plugin/bootstrap-the-cli` and `work/run-a-lifecycle-stage`. Their bodies were
  updated on the branch. The item had no `capabilities.yaml`, so one was added at
  verify, listing both under `changed:`. Both resolve, and
  `tcw capabilities check` prints `capabilities OK`. The taxonomy Features and
  one-capability-per-skill work belong to
  `2026-09-14-consolidate-the-setup-skills-into-a-single-tcw-setup-skill`, which
  this item unblocks.
- **No GitHub issue** is attached.
- **Version:** at the requester's direction, the skill changes ship together in a
  later version. No version is cut here.
