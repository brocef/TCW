# Spec — Keep a reporter's private project details out of an upstream TCW report

## Capability changes

**New:** `plugin/report-an-issue-upstream` — "Report an issue or suggestion
upstream". The `tcw-report` skill is a shipped, user-facing surface with no
ledger entry, while its two siblings in the same namespace have one
(`plugin/triage-github-issues`, `plugin/run-a-post-mortem`). The gap is
pre-existing; this item closes it because it is editing the surface anyway, and
because the disclosure guidance is the part of that surface a user most needs
described. Seeded `Missing` at planning, flipped `Supported` when the skill
lands.

No changed or removed capabilities. Taxonomy: `tcw taxonomy search issue` and
`… search report` both return nothing, so no Vocabulary or Feature entry is
touched.

## Problem

`skills/tcw-report/SKILL.md` sends a report to a **public** tracker —
`https://github.com/brocef/TCW/issues` (`SKILL.md:18`) — while the agent writing
it is working inside somebody else's project, which may be a private repository.
Nothing in the file mentions that boundary.

The file does not merely omit the warning; it argues against it:

- `SKILL.md:76-77` — "Keep it concrete: a real command, a real error, a real
  scenario beats an abstract description."
- `SKILL.md:44` — the bug skeleton's first reproduction step is
  "`<exact command or action>`".
- `SKILL.md:51` — "Actual: `<what happened — paste the error / output
  verbatim>`".

Followed literally, those three lines produce a public issue carrying the
reporter's real node ids, work-item slugs, capability paths, absolute paths,
repository and branch names, and whatever domain vocabulary appears in a `tcw`
error message. There is no un-publishing that.

Two grounded facts shape the fix:

- **The skill drafts; it does not post.** `SKILL.md:5` grants
  `Bash(tcw *), Read` — no `gh`, no network. The agent hands the user a filled
  skeleton and the user files it. So the leak happens in the draft, and the
  intervention belongs in what the skill tells the drafter to write.
- **One real value is wanted and is not identifying.** `SKILL.md:28-29` asks for
  `tcw --version`, and the Environment block (`SKILL.md:36-40`) asks for OS and
  install method. Those stay exactly as they are.

**Sibling sweep, repo-wide.** The only other skill that writes to GitHub is
`tcw-triage-issues` (`SKILL.md:191-192`, `gh issue comment` / `gh issue close`),
and it writes to *the reporter's own* repository — nothing crosses a project
boundary there, so it is not a sibling of this defect and is untouched. No other
skill, command, or agent under `skills/`, `commands/`, or `agents/` sends project
content outward.

## Goals

- An agent drafting an upstream report reaches for a **generic example that
  mirrors the reporter's setup** by default, instead of the real thing.
- The report stays actionable: mirrored, not vague. The maintainer still gets a
  command, an error, and a shape they can act on.
- The reporter is encouraged to sketch **reproduction steps on a fresh
  environment**, and told how to get one without running anything in their own
  checkout.
- All of it reads as **guidance**. The skill's single requirement remains that
  TCW feedback is filed as a GitHub issue on the TCW repository rather than into
  the reporter's own `tcw work` store.

## Non-goals

- **No gate, refusal, or approval checkpoint.** The skill must not instruct an
  agent to withhold a report, demand permission before including a detail, or
  redact against the user's wishes. Contents are the reporter's call.
- **No automated redaction** — no scrubbing pass, no placeholder substitution
  tooling, no `tcw` subcommand.
- **No change to `tcw-triage-issues`**, which posts only to the reporter's own
  repository.
- **No change to the `tcw` CLI.** This is skill guidance.
- **No new tool grant.** `allowed-tools` stays as it is; see design item 8.

## Design

Eight changes, all inside `skills/tcw-report/SKILL.md`.

1. **A new section, `## What goes in the report`, placed after `## Before
   filing` and before the two skeletons.** It states the asymmetry in two
   sentences — the tracker is public, the reporter's project may not be — and
   names the mirrored generic example as what to write by default. It opens by
   saying these are guidelines and the reporter decides.

2. **The mirroring rule, made concrete rather than exhorted.** Name what to swap
   and what to keep, because "be generic" without a list produces vagueness:
    - _Swap_: repository, branch and directory names; node ids; work-item slugs;
      capability paths and wording; absolute paths; taxonomy terms and any other
      domain vocabulary.
    - _Keep_: the command's shape and flags, the config's shape, the error type
      and message template, the sequence that triggered it, and the Environment
      block's real values (`tcw --version`, OS, install method).

3. **Fresh-environment reproduction, encouraged.** A short instruction to sketch
   the steps from a clean install and a scratch project — and an explicit line
   that a report is welcome without them, since a clean-room reproduction is
   often impractical.

4. **Delegating the reproduction.** Suggest handing it to a subagent or an agent
   team member that works in a temporary directory, so nothing runs in the
   reporter's checkout. This is harness-neutral: both Claude and Codex have
   subagents, so a skill may instruct delegation outright
   (`docs/lifecycle/harness.md`, and `skills/tcw-work/references/procedures/delegation.md`
   for the existing precedent).

5. **Verbatim output: preference, not prohibition.** State that output captured
   from the generic reproduction is preferred, and that a reporter who wants to
   include output from their own system and environment may do so.

6. **Rewrite the closing paragraph (`SKILL.md:76-78`).** As written it opposes
   "real" to "abstract", which is the sentence that invites the leak. The
   replacement keeps its point — concreteness is what makes a report actionable
   — by locating concreteness in the *shape*: a command with its real flags, an
   error with its real type, a scenario with its real sequence, under names that
   are not the reporter's. The axis hint (taxonomy / capabilities / work) in the
   same paragraph survives unchanged.

7. **Skeleton placeholders re-phrased** so the skeleton itself carries the
   default rather than contradicting the new section: `SKILL.md:44`'s
   "`<exact command or action>`" and `SKILL.md:51`'s "`paste the error / output
   verbatim`" gain the mirrored framing. The Environment block (`SKILL.md:36-40`)
   is untouched.

8. **Frontmatter and tool surface unchanged.** `allowed-tools` stays
   `Bash(tcw *), Read`. Two reasons: the skill still posts nothing, and the
   reproduction it now suggests is precisely the work being handed to a subagent,
   which brings its own tool surface. `tcw-work` sets the precedent — it
   instructs delegation without naming a subagent tool in `allowed-tools`.

A single worked before/after example carries items 2 and 6; it belongs inline,
not in a `references/` file. The skill is 78 lines today against a 48–262 line
range across the nine shipped skills, and the whole change is one section plus a
rewritten paragraph.

## Abstraction litmus test

**No new operation.** Nothing here touches the store interface, the item model,
or any adapter: the change is prose inside a skill document, and the capability
delta is recorded with the existing `tcw capabilities add` / `set` operations,
which are already model-level and storage-abstracted. Nothing added assumes a
filesystem store.

## Acceptance criteria

1. `skills/tcw-report/SKILL.md` contains a section after `## Before filing` and
   before the bug skeleton that states the tracker is public, the reporter's
   project may not be, and that a generic example mirroring the setup is what to
   write by default.
2. That section says, in its own words, that this is guidance and that the
   reporter decides the report's contents. No sentence anywhere in the file
   instructs an agent to refuse a report, withhold it pending approval, or redact
   against the reporter's stated wish.
3. The file names both lists from design item 2 — what to swap and what to keep —
   with the Environment values on the keep side.
4. A single before/after example appears inline, at most 12 lines, showing one
   identifying command or error rewritten into its mirrored form.
5. The file encourages reproduction steps starting from a clean install and a
   scratch project, and states in a sentence that a report is fileable without
   them.
6. The file suggests delegating that reproduction to a subagent or agent team
   member working in a temporary directory, in wording that names no
   Claude-specific mechanism.
7. The file states the preference for output captured from the generic
   reproduction and states that the reporter may include output from their own
   system if they choose.
8. The closing paragraph no longer contains "a real command, a real error, a real
   scenario beats an abstract description"; the axis hint and the
   `tcw --version` instruction at `SKILL.md:28-29` survive; `allowed-tools` is
   byte-identical; the file is under 120 lines.
9. `tcw capabilities show plugin/report-an-issue-upstream` resolves, carries
   `Planning doc` = this item's slug, reads `Supported` at completion, and is
   listed under `new:` in the item's `capabilities.yaml`.
10. `pytest tests/test_plugin_manifests.py` passes, `tcw validate` exits 0, and
    the documentation entries that fire are updated: `docs/changelogs/upcoming.md`
    and `docs/release-notes/upcoming.md`. `README.md:279`'s `tcw-report` row is
    re-read and changed only if its one-line description became inaccurate.

### Coverage

Criteria (rows) against the eight design items (columns). Every cell is a read of
the finished file at review: this change adds no runtime behavior, so no cell can
honestly hold a pytest name — see `## Notes`. `—` means the criterion does not
reach that design item.

| #   | D1  | D2  | D3  | D4  | D5  | D6  | D7  | D8  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1   | read | —  | —   | —   | —   | —   | —   | —   |
| 2   | read | —  | read | —  | read | —  | —   | —   |
| 3   | —   | read | —  | —   | read | —  | read | —   |
| 4   | —   | read | —  | —   | —   | read | —  | —   |
| 5   | —   | —   | read | — | —   | —   | —   | —   |
| 6   | —   | —   | —   | read | — | —   | —   | read |
| 7   | —   | —   | —   | —  | read | —  | read | —   |
| 8   | —   | —   | —   | —   | —   | read | read | read |
| 9   | —   | —   | —   | —   | —   | —   | —   | —   |
| 10  | —   | —   | —   | —   | —   | —   | —   | read |

Criterion 9 is the capability ledger and criterion 10 the documentation gate;
neither reaches a design item, and both are checked by the commands they name.

## Risks

- **Generic collapses into vague.** The failure mode of "don't paste the real
  thing" is a report nobody can act on, which costs the project more than the
  disclosure it prevented. Design items 2 and 6 exist to prevent it: the keep-list
  and the reworded closing paragraph both insist the shape survives. Criterion 4's
  worked example is the check that it is teachable.
- **Guidance drifting into policy.** Wording like "never include" or "ask the
  user before" would turn encouragement into a gate the user did not ask for.
  Criterion 2 pins this; it is the criterion most likely to be violated by an
  otherwise well-written section.
- **Friction suppressing reports.** Every added expectation is a reason not to
  file. Mitigated by keeping items 3 and 4 explicitly optional and by leaving the
  skeletons short.
- **Recording a pre-existing ability as a `new:` capability.** Seeding
  `plugin/report-an-issue-upstream` as `Missing` is momentarily untrue — the
  ability exists today. It is the mechanism the ledger provides for adding an
  entry, and the window closes at completion; the alternative, adding it
  `Supported` before the guidance lands, misdescribes it for longer.

## Notes

- **Why no test.** The repository does test skill documents
  (`tests/test_skill_lifecycle_parity.py` pins the `tcw-work` skill against
  `LIFECYCLE_STEPS`, `tests/test_plugin_manifests.py` pins frontmatter and the
  Codex skill count), but those guard prose against a *machine-readable source*
  that can drift. This change has no such source: a test asserting a heading or a
  phrase exists would pin wording, not truth, and would fail on the next honest
  rewrite. The structural invariants that can rot — frontmatter, skill count —
  are already covered by `tests/test_plugin_manifests.py`, which criterion 10
  runs.
- The user was asked for reference material at the `request` stage and provided
  none; research started from the skill file and the repo-wide sweep recorded
  under `## Problem`.
