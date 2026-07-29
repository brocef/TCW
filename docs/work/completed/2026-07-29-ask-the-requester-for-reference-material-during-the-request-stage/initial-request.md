# Ask the requester for reference material during the request stage

## Origin

Requested by the user in chat, from their own habit:

> I often times write up a request and make inline Markdown links, but I should
> really just make this a formal step in the creation of the initial request
> document. That way, when it comes time to do the spec creation (where we should
> be doing the deeper research), we've already taken the time to get links to
> documentation that the author believes is relevant to the task.

So the observed behavior already happens — reference links land in requests
today, informally, as prose. The request is to make it a step rather than a
habit, and to make the `spec` stage actually consume the result.

## Product changes

The `request` stage's job is to capture intent that would otherwise be lost
between a conversation and a spec. Right now it captures the *ask* but not the
*sources* — the requester's links survive only if they happen to write them into
a sentence, and nothing prompts for them. The `spec` stage then does its research
from scratch, re-finding material the requester already had open.

The user-visible change: an agent running the `request` stage asks the requester
what reference material applies, and records it in the request document. An agent
running the `spec` stage starts from that list.

The value is specifically in *asking at request time* — that is the one moment
the requester is present and their sources are at hand.

## Technical changes

This is a skill-document change; nothing decided beyond the shape agreed in
chat:

- **`stage-request.md`** — `Produce` gains an optional `## References` section
  (each entry a link or path plus a one-line *why it matters*, since a bare URL
  list does not save the `spec` stage any work). `Steps` gains one step, after
  "Ask the user what is unclear", to solicit reference material. **Capture only**
  — no fetching, no validating, no summarizing, because the stage is explicitly
  told to resist doing `spec`'s job.
- **`stage-spec.md`** — `Inputs` names the `## References` section as the
  starting set for research, not the limit of it; the code-reading step says to
  read the references before hunting for sources independently.
- **`stage-inbox.md`** — carry-through only. A raw entry that already contains
  links or has attachments should not lose them on `accept`. No prompt here: the
  requester (a GitHub issue reporter, a child node) is usually not present to
  ask, which is why the `request` stage does the asking.

Open questions for the `spec` stage:

- **The empty case.** The user chose: omit `## References` when there is nothing,
  and note "asked; none provided" in the existing `## Notes`. That keeps the new
  section optional at the cost of a weaker signal — a `spec`-stage agent
  distinguishes "asked, none" from "never asked" only if the `Notes` line is
  actually written. Whether the stage doc can make that reliable with prose alone
  is the one real design question.
- **Does anything belong in the CLI?** Per the harness rule, guaranteed behavior
  belongs in `tcw`. The CLI does not validate artifact sections today
  (`tcw/work/cli.py` knows `initial-request.md` only as a presence marker), and
  "ask the user a question" is not a thing a CLI can do — so the expectation is
  no CLI change. The spec should confirm that rather than assume it.
- **Does `tcw-work/SKILL.md` name the request artifact's sections?** If so it
  needs the same addition, per the Documentation Sync rule for skill drift.

## Meta changes

Documentation Sync: `docs/changelogs/upcoming.md` and
`docs/release-notes/upcoming.md`. Possibly `skills/tcw-work/SKILL.md`.

No taxonomy or capability delta expected — this refines how an existing
capability behaves rather than adding one — but the `spec` stage runs the
capabilities check to confirm.

## References

- [`skills/tcw-work/references/stage-request.md`](../../../../skills/tcw-work/references/stage-request.md)
  — the stage being changed; its `Produce` and `Steps` sections are the edit site.
- [`skills/tcw-work/references/stage-spec.md`](../../../../skills/tcw-work/references/stage-spec.md)
  — the consumer; its `Inputs` currently names only `initial-request.md`.
- [`skills/tcw-work/references/stage-inbox.md`](../../../../skills/tcw-work/references/stage-inbox.md)
  — produces no artifact of its own, which is why its change is carry-through
  rather than a prompt.
- [`docs/work/completed/2026-07-29-close-the-originating-github-issue-when-a-work-item-completes/initial-request.md`](../../completed/2026-07-29-close-the-originating-github-issue-when-a-work-item-completes/initial-request.md)
  — a request written with inline links in the informal style this item
  formalizes; useful as the before-picture.

## Notes

**Constraints**

- The new step must not turn `request` into a research stage. Deeper research is
  `spec`'s job and pre-empting it hides alternatives.
- A Codex user must get the same behavior. Since the whole change is skill prose
  read identically by both harnesses, this should be free — but it is a
  constraint, not an accident.

**Out of scope**

- A `tcw work references` subcommand or any CLI surface for reference material.
- Link validation or rot detection.
- An attachments-folder convention for reference material.
- Re-asking for references at the `spec` stage. The `request` stage exists to
  prevent that re-interview.
