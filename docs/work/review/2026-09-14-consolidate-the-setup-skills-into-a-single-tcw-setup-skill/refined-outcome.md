# Refined outcome — Give every TCW skill a taxonomy Feature and exactly one capability

## Decision

**Accepted.** On 2026-09-14 the requester told the coordinating agent to finish the
skills work and merge each piece into `main` once it is ready. Readiness was
judged the same way as for the two earlier items: a multi review plus the test
suite, capped at two rounds. Both reviewers that answered ended round 1 with
DONE, so no second round was needed.

Merged into `main` as `88d3f418`, after `main` was fast-forwarded to `origin/main`
(`92028ab1`, eight documentation-only commits planning the tracker-link change,
none touching a file this item touches).

## Evidence

- **Full suite.**
  - Bare `pytest` in the worktree at `be9c0fc6`: **3092 passed**. The developer
    ran this.
  - Bare `pytest` on merged `main` at `88d3f418`: **3092 passed**.
  - The commits after `be9c0fc6` change only `outcome.md`, the item's status, one
    release-note line and one inbox note.
- **After the merge.** `tcw validate` printed `validate OK`, and
  `tcw capabilities check` printed `capabilities OK`.
- **Acceptance criteria.** ACs 1–10 are recorded in `outcome.md`. AC 8 was
  narrowed, because its grep also matched the link AC 7 requires. The reviewer
  re-ran ACs 1–8 and 10 and got the same results. It also scanned both ledger
  folders with the full deleted-names list, including names written without a
  slash, and found no hits.
- **Nothing points at a deleted path.** Outside completed and discarded items and
  versioned changelogs, the nine deleted paths appear only in the two
  `upcoming.md` entries, the backlog note, and this item's own documents. That is
  also true on `origin/main`'s open items.

## Review

**Developer's own adversarial review.** Recorded in `outcome.md` § Review.

**Round 1 (`main..421e43d4`).**

- **Codex (read-only sandbox confirmed; worktree unchanged): DONE.** It found no
  defect in any of its five checks:
  - every capability body matches its skill;
  - nothing from the nine deleted bodies is lost;
  - the taxonomy matches the spec table;
  - the completion gate accepts `capabilities.yaml`;
  - the changelog entries are accurate.
- **Adversarial code reviewer: DONE.** It ran `capability_gate` itself and got
  `[]`. It had two notes about this change:
  - *Narrowed, no change:* commit `2e5cfaad` appends a `## Notes` section to the
    backlog item's `intake.md`. `docs/guide/work.md:383-388` says an intake is
    "left byte-for-byte as it arrived". That rule describes what `tcw work edit`
    does when it promotes an intake. It does not forbid a dated note: the
    requester added one to a backlog intake in `9a57885d`. Writing
    `initial-request.md` instead would wrongly mark that item's request stage as
    done. So the note stays.
  - *Accepted:* the release note said each skill "is now one entry", but
    `work/run-a-lifecycle-stage` still describes `tcw-work-stage`. It now says
    each skill "has its own entry" (`82c38519`).
  - *Noted, no change:* the spec credits declaring stage documents to the drive
    capability rather than the plan capability. That was the spec's choice, and
    nothing is lost.
- **`bllm`: no answer.** All four slices returned "bllm is temporarily disabled
  for maintenance". That outage is already filed in `/Users/brian/llama/docs/work/inbox`.

## Deferred follow-ups

`docs/work/inbox/2026-09-14-skill-capability-overlaps-the-per-skill-review-left.md`
(`794386a3`) lists three follow-ups:

- `work/run-a-lifecycle-stage` still has two paragraphs about the
  `tcw-work-stage` skill, so Goal 2 is only partly met.
- `work/complete-a-work-item` and `skills/tcw-extras-triage-issues` both state
  the rules for closing an issue. That was already true before this item.
- No test keeps removed names out of `docs/capabilities` and `docs/taxonomy`.

## Closeout

- **Capability ledger.** `capabilities.yaml` lists 15 `new:` paths, all
  `Supported`; one `changed:` path, `work/complete-a-work-item`; and nine
  `removed:` paths, none of which exists.
- **No GitHub issue** is attached to this item.
- **Worktree.** This item was not started with `--worktree`. Its branch
  `worktree-agent-a06b6a37976aa5912` lives in a Claude agent worktree, which is
  left in place.
- **Version:** at the requester's direction, the skill changes ship together in a
  later version. No version is cut here.
