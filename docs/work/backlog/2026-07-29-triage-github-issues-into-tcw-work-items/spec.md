# Spec: Triage GitHub issues into TCW work items

## Capability changes

**New:** `plugin/triage-github-issues` — "Triage GitHub issues into work items".
Seeded `Status: Missing` with `Planning doc` pointing at this item; flipped to
`Supported` at `complete`.

It belongs in the `plugin/` namespace, not `work/`. Every `work/*` capability
names a `tcw work` verb (`work/manage-the-work-inbox` is "I inspect raw work
requests with `tcw work inbox list`…"), and this change adds no CLI verb. The
`plugin/*` namespace is where skill- and command-driven workflows live —
`plugin/work-lifecycle`, `plugin/run-a-post-mortem`, `plugin/diagnose-the-install`
— and none of them carries a `Feature` pointer, because the thing they describe
is a procedure the agent follows rather than a registered feature of the tool.
Same here: no new taxonomy entry, no `Feature` link.

**Changed:** none. `work/manage-the-work-inbox` keeps its current meaning; this
does not route through `docs/work/inbox/`.

**Contradiction check:** `tcw capabilities search issue|github|triage` returns
nothing, and `tcw capabilities check` is clean. No existing entry conflicts.

## Problem

TCW has exactly one intake path for third-party requests: a file dropped into
`docs/work/inbox/`, triaged by the `inbox` stage
(`skills/tcw-work/references/stage-inbox.md`). Projects that take bug reports on
GitHub have a second queue that nothing reads.

TCW is itself such a project. `skills/tcw-report/SKILL.md:18` sends every user
report to `https://github.com/brocef/TCW/issues`, and nothing in the repo reads
from there — the skill that *produces* upstream issues has no counterpart that
*consumes* them. The maintainer either retypes issues into work items by hand or
lets the backlog drift from what people are actually asking for.

The conversion is the easy half. The hard half is judgment: most issues should
not become work items, and every issue is somebody's report that deserves an
answer.

## Goals

1. One invocation sweeps a project's open GitHub issues, drops the ones already
   tracked, and walks the rest through triage.
2. Triage distinguishes at least four outcomes — **worth doing**, **duplicate**,
   **not worth doing**, **ill-defined** — and only the first creates a work item.
3. Each triaged issue gets an offered reply appropriate to its outcome, and
   **nothing is posted to GitHub without the user approving the exact text**.
4. An accepted issue produces a work item whose `initial-request.md` carries the
   issue's number and URL, and preserves the reporter's own words as evidence
   rather than paraphrasing them into first person.
5. Generic to any project. TCW dogfoods it; nothing in it is TCW-specific.
6. A Codex user can do all of the above by invoking the skill directly.

## Non-goals

- **No CLI change.** No `tcw work inbox fetch`, no `source`/`external-ref` field
  on the work model, no change to the store interface.
- **No new lifecycle stage.** Like `inbox`, this runs before an item exists and
  produces no lifecycle artifact, so `tcw work lifecycle` is untouched.
- **No routing through `docs/work/inbox/`.** That would triage twice.
- **No back-sync.** Completing the work item does not close the issue. The link
  is one-directional and written once.
- **No automation.** No polling, no scheduled run, no webhook. It runs when a
  user asks.
- **No GitHub labels.** See Design §5 for why.
- **No non-GitHub trackers.** GitLab, Jira, Linear are out.

## Design

### 1. Shape: standalone skill + routing command

`skills/tcw-triage-issues/SKILL.md` plus `commands/tcw-triage-issues.md`.

This follows the `tcw-post-mortem` precedent exactly. That workflow is *also* a
tcw-work concern, and the repo resolved it by putting the contract in
`skills/tcw-work/references/stage-postmortem.md`, the *how* in a standalone
skill, and a command that names both (`commands/tcw-post-mortem.md`). The
standalone skill exists for triggering: `tcw-work`'s description says nothing
about GitHub, so a reference buried inside it would never fire on "check GitHub
for issues".

The division of labor is the same:

- **Reused, not restated.** `stage-inbox.md` already holds the judgment for
  turning someone else's raw text into an item — retitle to a change rather than
  a symptom, split one drop into several items, don't invent scope, choose tags
  from `tcw work tags list`. The new skill points at it and does not repeat it.
  `stage-inbox.md` gains one line pointing back, so the pair stays connected.
- **New.** Everything GitHub-shaped: reaching the issues, deciding which are
  already tracked, the reject outcomes, and the reply.

Single `SKILL.md`, no `references/`. Per `CLAUDE.md`, a router earns its
indirection only once the conditional detail is large enough; this is one linear
procedure.

`allowed-tools` must cover every `gh` verb the skill instructs — including the
write verbs. Commit `daef4da` in this repo fixed the inverse bug in `tcw-plugin`
(procedures instructing a script the grant did not permit), so the failure mode
is known and local.

### 2. Preconditions

Check before sweeping, and fail with a stated reason rather than an obscure
error: `gh` on PATH, `gh auth status` clean, and a resolvable GitHub repo for
the project (`gh repo view`). Any of the three missing is a legitimate state —
say which one and stop.

### 3. The sweep

`gh issue list --state open` with the fields triage needs (number, title, body,
author, labels, URL, comments). Cap the fetch and, if the cap truncates, **say
what was dropped** rather than reporting a clean sweep.

### 4. The already-tracked filter

Grep `docs/work/` for the issue URL. An accepted issue writes that URL into its
`initial-request.md` (§6), so the URL is the join key and the check needs no new
state anywhere.

This is a filesystem read, and deliberately not a store-interface operation —
`tcw work` has no search verb and this spec does not add one. It is skill-level
repository discovery, which every stage document already permits, and it stays
outside the model.

### 5. What keeps a *rejected* issue from resurfacing

The request flagged this as the thing spec must settle. `tcw work inbox accept`
consumes the entry (`stage-inbox.md:37`), so a processed inbox entry is gone;
a GitHub issue is not ours to consume.

**Resolution: the reply is the record, and the sweep only lists open issues.**

| Outcome | Why it doesn't resurface |
|---|---|
| Worth doing | Work item carries the URL → filtered by §4 |
| Duplicate | Issue is closed as part of the reply |
| Not worth doing | Issue is closed with the stated reason |
| Ill-defined | **Stays open on purpose** — waiting on the reporter |
| User declined to decide | **Should resurface.** Nothing was decided. |

Only the ill-defined row costs anything, and it costs a re-read: the skill sees
its own earlier comment asking for information, sees the reporter has not
answered, and moves on. That is one issue re-read per sweep, and it is also the
correct prompt to ping a stale request.

A `needs-info` label would mechanize that one row, and is rejected: it needs the
label to exist, needs write scope to create it, and buys a skip the agent can
make by reading a comment it already fetched.

### 6. The accept path

1. `tcw work new "<retitled>"` with tags and estimates, per `stage-inbox.md`.
2. Write `initial-request.md` with the issue number, URL and reporter recorded
   at the top, and the reporter's text preserved as an attributed quote — not
   rewritten into first person, because the maintainer did not ask for this.
3. Run the `request` stage over it (`stage-request.md`), which is where the
   reporter's words become an actual request.
4. Commit the item.

### 7. The reply path

Per issue, the skill proposes the reply that fits the outcome — a comment naming
the duplicate and closing, a closure with a stated reason, a request for the
specific missing information, or an acknowledgement carrying the new item's slug
— and shows the **exact text** before anything is sent. The user approves each
one individually; no batch approval, no "reply to all of these". A declined reply
leaves the issue untouched.

These are public, attributed, and visible to everyone watching the issue, which
is why the approval is per-message and not per-run.

### 8. Codex parity

The command carries no logic the skill lacks — `commands.md:45-50` states the
rule for this repo ("Nothing is only available through a command"). The command
is a router plus `$ARGUMENTS`; everything runs through `gh` and `tcw` in Bash,
both of which behave identically under either harness.

### 9. Documentation

- `README.md:109-116` — the command inventory and skill count; `README.md:844`
  neighborhood — the skill list, where the new entry must state the direction
  that distinguishes it from `tcw-report` (that one files issues *upstream to
  TCW*; this one reads issues *on your own project*).
- `skills/tcw-plugin/SKILL.md:26-47` — the skill map and its routing list.
- `.codex-plugin/plugin.json` — `longDescription` enumerates the seven skills.
- `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`.

## Acceptance criteria

1. `skills/tcw-triage-issues/SKILL.md` exists with `name`, `description`,
   `when_to_use`, and `allowed-tools` frontmatter; `commands/tcw-triage-issues.md`
   routes to it and contains no instruction absent from the skill.
2. Every `gh` and `tcw` verb the skill instructs — reads *and* writes — is
   permitted by its `allowed-tools`. Checkable by listing the commands in the
   skill body against the grant.
3. The skill states its three preconditions (`gh` present, authenticated, repo
   resolvable) and what to tell the user when each fails.
4. The skill names all four triage outcomes and states that only "worth doing"
   creates a work item.
5. The skill states that no GitHub comment or closure is posted without the user
   approving the exact text, per message.
6. The skill defers to `stage-inbox.md` for retitling, splitting, and tag choice
   rather than restating that judgment; `stage-inbox.md` carries a pointer back.
7. A dogfood sweep against `brocef/TCW`: every created item's
   `initial-request.md` contains its issue's URL, and no item is created for an
   issue that was rejected.
8. Re-running that sweep reports the accepted issues as already tracked and
   creates no duplicate items.
9. `plugin/triage-github-issues` exists at `Status: Missing` with this item as
   its `Planning doc`, and `capabilities.yaml` lists it under `new:`.
10. `README.md`, `skills/tcw-plugin/SKILL.md`, `.codex-plugin/plugin.json`
    `longDescription`, `docs/changelogs/upcoming.md`, and
    `docs/release-notes/upcoming.md` all reflect the new skill and command.
11. `pytest` is green, including `tests/test_plugin_manifests.py`.

## Risks

- **Irreversible public action on someone else's report.** A wrong close or a
  brusque comment is visible to everyone watching the issue. Mitigated by
  per-message approval of exact text (§7); accepted as residual risk that the
  user can still approve a bad message.
- **Trigger collision with `tcw-report`.** Both skills are about GitHub issues
  and point in opposite directions. If the descriptions do not make the
  direction explicit, the wrong one fires. Mitigated by criterion 1 and the
  README/skill-map wording; genuinely testable only in use.
- **Unbounded sweep.** A repo with hundreds of open issues turns one invocation
  into a very long session. Mitigated by the cap in §3, at the cost of a
  partial sweep the skill must report honestly.
- **Filesystem-coupled tracked-check.** §4 greps `docs/work/`. It is
  skill-level discovery rather than a model operation, so the abstraction
  litmus test is not violated — but a non-filesystem work store would need a
  different check, and there is no store-level search to fall back on.
- **The reporter's text is untrusted input.** Issue bodies are written by
  strangers and may contain text shaped like instructions. The skill treats
  issue content as data to be judged, never as direction to follow.

## Notes

**Assumptions**

- `gh issue list --json comments` returns enough of the comment thread to tell
  "I already asked for information and the reporter has not answered" (§5). Not
  verified against the API here; if it does not, §5's ill-defined row degrades
  to a re-read the user must dismiss, which is annoying but not wrong.
- The skill name `tcw-triage-issues` and command `/tcw-triage-issues` are a
  proposal. GitHub-specificity lives in the description rather than the name,
  on the theory that the name should not need changing if a second tracker is
  ever supported. Easy to change at review; hard to change after release.

**Environment confirmed**

`gh` 2.94.0 is on PATH and the repo's `origin` is `git@github.com:brocef/TCW.git`,
so the dogfood sweep in criteria 7-8 is runnable on this machine.
