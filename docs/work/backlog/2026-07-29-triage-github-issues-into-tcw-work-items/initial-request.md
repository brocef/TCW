# Triage GitHub issues into TCW work items

## Product changes

A project that takes bug reports and feature requests on GitHub has two
trackers: the issues its users file, and the `tcw work` backlog its agents
actually work from. Nothing today bridges them. A maintainer either
hand-copies issues into work items, or the backlog quietly drifts out of step
with what people are asking for.

The request: a new command and skill that reads the project's open GitHub
issues and converts the ones worth acting on into `tcw work` items.

**Triage is the point, not the conversion.** Most of the value is in the
issues that do *not* become work items. Each issue gets judged before anything
is created, and the recognized outcomes are at least:

- **Worth doing** — becomes a work item.
- **Duplicate** — of another open issue, or of a work item that already
  exists. No new item.
- **Not worth doing** — out of scope, contrary to the project's design, or
  simply not wanted.
- **Ill-defined** — the report may be real but there is not enough in it to
  act on. Not enough to spec, so not yet an item.

Only the first outcome creates a work item. The backlog is not a landfill for
everything that arrives.

**A GitHub issue is an inbox entry that happens to live on GitHub.** That is
the model to reason from. Like an inbox entry, it is a raw drop that gets
**accepted or rejected**, and — unlike anything else in `tcw work` — it was
**written by someone other than the person triaging it**. Both properties
carry consequences the skill has to honor:

- The reporter's title is a symptom, not a change. Retitle on accept, the way
  the inbox stage does.
- The reporter's words are evidence, not a request document. Preserve what
  they said; do not silently rewrite it into first person as though the
  maintainer had asked for it.
- One issue may be several items, or duplicate an item that already exists.
- Rejection is a first-class outcome, not a failure.

**Replying to the issue is part of the job.** An issue that gets triaged and
then sits there silently is a worse experience for the reporter than one that
never got read. For each issue, the skill asks the user whether to respond, and
what response fits: a comment linking the duplicate and closing it, a closure
with a stated reason for something not being taken on, a request for the
specific missing information, or an acknowledgement that it is now tracked
(with the work item's slug). The user decides — the skill proposes.

**Nothing is posted to GitHub without the user approving it.** Comments and
closures are public, on someone else's report, and irreversible in the sense
that everyone watching the issue sees them. The user approves each one.

## Technical changes

Shape requested, from the discussion:

- **A command + a skill**, following the existing pattern: `commands/` routes
  to the skill, and the skill stands alone so a Codex user can invoke it
  directly.
- **Generic to any project.** It triages issues on whatever repo the current
  project points at, not TCW's own repo. TCW dogfoods it against its own
  issues — including ones filed by the `tcw-report` skill — but nothing about
  it is TCW-specific.
- **Sweep all open, untriaged issues** in one invocation. It lists the open
  issues, drops the ones already tracked, and walks the rest through triage.
- **Straight to `tcw work new`** for the keepers, seeding `initial-request.md`
  from the issue's own text. It does not route through `docs/work/inbox/` —
  that would mean triaging twice, once here and once at the inbox stage.
- **The link back to the issue is a line in `initial-request.md`** — the issue
  number and URL, written as prose. No new field on the work model, no new
  CLI verb. That line is also what "already tracked" is determined from on the
  next sweep.

The GitHub side is the `gh` CLI, which both harnesses can run through Bash.

## Meta changes

New skill and command, so the usual surfaces: the command inventory in
`README.md`, the skill map in `skills/tcw-plugin/`, the changelog, and the
release notes.

The relationship to the two neighbors needs to be unambiguous in each skill's
description, or the wrong one will fire:

- **`tcw-report`** files an issue *upstream to TCW*. This new skill reads
  issues *on your own project*. They point in opposite directions.
- **`tcw-process-inbox`** triages `docs/work/inbox/` entries. This is the same
  verb against a different source, and deliberately does not feed into it —
  but it is the closest relative, and its judgment (`stage-inbox.md`) is the
  material to start from rather than invent alongside.

## Notes

**Constraints**

- Codex has no slash commands and no command arguments, so everything the
  command does must be reachable by invoking the skill directly.
- `gh` may be absent, unauthenticated, or the project may have no GitHub
  remote at all. The skill needs to say so plainly rather than fail obscurely.
- Triage is judgment, so it lives in the skill. But if any part of this turns
  out to need a *guarantee* — the same result under both harnesses — that part
  belongs in the `tcw` CLI, not in skill prose.

**Out of scope**

- No change to the work model or the store interface. No `source` /
  `external-ref` field, no `tcw work inbox fetch` verb.
- No closing the GitHub issue when the work item later completes. The link is
  one-directional and one-time; keeping the two in sync afterwards is a
  separate ask.
- Not a GitHub sync. It is a one-way, human-approved conversion run when the
  user asks for it — no polling, no automation, no webhook.

**Assumptions to confirm at spec**

- That grepping `docs/work/` for the issue URL is a sufficient "already
  tracked" check, including for issues that were triaged and *rejected* —
  those leave no work item, so a rejected issue would resurface on every
  subsequent sweep unless something records the decision.
- That a triage decision this skill makes needs no durable record anywhere in
  `docs/work/` beyond the item it does or does not create.
