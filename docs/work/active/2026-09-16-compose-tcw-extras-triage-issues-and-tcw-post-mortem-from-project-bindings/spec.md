# Spec — Compose tcw-extras-triage-issues and tcw-post-mortem from project bindings

Child 5 of `2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Specified against the tree child 2 merged, not against the epic plan.

## Capability changes

Planned ledger deltas only. Both entries exist (`tcw capabilities show` prints
them as `cap-1c60e2` and `cap-375af8`).

```yaml
changed:
    - skills/tcw-extras-triage-issues # its procedure now comes from `triage-issues`
    - skills/tcw-post-mortem # its investigation now comes from `post-mortem`
```

No `work/*` capability changes: `work/run-a-procedure` and
`work/configure-procedures` already name both ids
(`docs/capabilities/work/run-a-procedure/description.md:3`).

## Problem

1. **Both skills are fixed prose although their verdict is `overridable`.**
   `skills/README.md:97` and `:101` classify them overridable, and both carry
   `dynamic_skill: true` (`skills/tcw-extras-triage-issues/SKILL.md:10`,
   `skills/tcw-post-mortem/SKILL.md:4`), but neither reads
   `tcw work procedure prompt`. A project that sets
   `work.procedures.triage-issues` or `work.procedures.post-mortem`
   (`skills/tcw-configure/references/work.md:79-112`) changes what the command
   prints and nothing an agent reads.

2. **The shipped defaults are verbatim copies**, held equal by
   `tests/test_shipped_procedures.py:21-32,51-57`: `tcw/work/procedures/triage-issues.md`
   is the skill's body from `# Triaging GitHub issues…` to the end, and
   `post-mortem.md` likewise. Converting the skill changes one side of that
   comparison on purpose.

3. **Each skill mixes rules TCW owns with conduct a project owns** (Rule 1,
   `skills/README.md:40-52`). Moving everything into the default would let an
   override switch the rules off.
   - `tcw-extras-triage-issues`: the framing that an issue is an inbox entry
     judged by the `inbox` stage (`:13-31`); the rule that an accepted issue is
     filed as `intake.md` and never `initial-request.md`, which is the `request`
     stage's artifact (`:172-177`); that the issue body is data, never
     instruction (`:127-129`); and that nothing is posted without the user
     approving the exact text (`:196-201`, restated at `:251-253`).
   - `tcw-post-mortem`: the pointer to the `postmortem` stage contract and the
     question it asks (`:9-17`); the order of the artifact spine, which is the
     stage ladder read backwards (`:21-24`); and the artifact and status rules
     (`:68-76`).

4. **The agent restates the skill.** `agents/tcw-post-mortem.md:16-39` carries
   its own copy of the investigation — the backwards read, `## Notes` as the
   trail, the "was the information available" test. `skills/README.md:126-131`
   says that once the source can be replaced, the agent must stop carrying its
   copy, or a project's replacement is skipped whenever the agent is dispatched.
   The agent is dispatched from the `postmortem` stage contract
   (`skills/tcw-work/references/lifecycle/stage-postmortem.md:21-24`) and named
   in `skills/tcw-work/references/procedures/delegation.md:55-59`; it has `Bash`
   (`agents/tcw-post-mortem.md:4`), so it can run the command itself.

5. **The forge question.** The triage skill hard-requires the GitHub CLI —
   `gh auth status`, `gh repo view`, `gh issue list/view/comment/close`
   (`:38-46`, `:51-54`, `:191-194`, `:255-258`), "Do not fall back to scraping
   the web UI" (`:43-44`) — and declares it in `allowed-tools:` (`:5`) and
   `compatibility:` (`:8`). The work axis's external tracker is abstracted behind
   `work.tracker`, whose only provider is `jira-cloud`
   (`tcw/store/base.py:1084`, `skills/tcw-configure/references/tracker.md:31`).

6. **Section references point into the skill.**
   `skills/tcw-work/references/transitions.md:119` and `:159` send a reader
   completing or discarding an issue-born item to "`tcw-extras-triage-issues`
   §8". No other live document cites a numbered section of either skill
   (`grep -rn "§" skills agents docs/guide docs/capabilities README.md`); the
   triage skill's own `§2`–`§6` cross-references are internal.

## Goals

1. Each skill's body holds only its fixed part and composes the rest from
   `tcw work procedure prompt <id>`, injected for Claude and named in a manual
   fallback block for any other harness, as `skills/tcw-work-stage/SKILL.md:38-59`
   does.
2. A project that configures nothing reads exactly today's words: fixed body
   plus the default equals the pre-conversion file, with every difference being
   a moved paragraph or a stated rewording.
3. The rules in Problem §3 stay in the skill bodies, out of reach of an override.
4. `agents/tcw-post-mortem.md` obtains its investigation from
   `tcw work procedure prompt post-mortem <slug>` and carries no copy of it.
5. The forge question is answered, with its reason recorded here.
6. `transitions.md`'s "§8" still lands on the section it means.

## Non-goals

- Changing what either skill does, or their `name`, `description`,
  `when_to_use` or `dynamic_skill` values.
- A GitHub (or any forge) provider for `work.tracker`, or any new configuration
  key. The mechanism is child 2's and is not edited here.
- Editing `skills/README.md` verdicts, `transitions.md`, `stage-postmortem.md`,
  `delegation.md` or the `postmortem` stage prompt.
- Updating eval cases B7 and B9 (`evals/evals.json`), which measure judgment
  against inline issues and a seeded item and do not read skill text directly.
- Running either converted skill in a live session, or under Codex (deferred to
  `verify` by the requester).

## Design

### The forge: a declared requirement of the shipped default

The forge stays what it is today — required by TCW's default `triage-issues`
text and declared in the frontmatter — and does not become a binding of its own.
A project whose issues live elsewhere replaces the procedure.

Why:

- **The procedure is already the replaceable unit.** Once the skill composes,
  `work.procedures.triage-issues` lets a GitLab or Jira project supply its own
  sweep, reply and close commands. A separate forge binding would replace a
  subset of what the procedure override already replaces, and the commands
  (`gh issue list --json …` against `glab issue list …`) do not share a shape a
  single binding could parametrize.
- **`work.tracker` is not the same axis.** It binds the board's own items to an
  external tracker's tickets (claim at `start`, move statuses) —
  `tracker.md:1-9`. Issues filed by users are an inbound queue, the `inbox`
  stage's shape (`stage-inbox.md:9-12`). Routing triage through it would mean a
  `github` tracker provider in Python — a mechanism change this child may not
  make, and a feature nobody has asked for.
- **Honesty is kept by the frontmatter.** `compatibility:` is reworded to say
  the requirement belongs to the default procedure, so a user replacing it is
  not told a false requirement and a user who does not is still warned.
  `allowed-tools:` is left alone: it pre-approves commands and restricts nothing,
  so a replacement using another CLI only costs a permission prompt.

Abstraction litmus test: nothing here is a store operation. The forge is reached
by the agent, not by `tcw`, so no store implementation is involved either way.

### What stays fixed, and where it goes

Each converted `SKILL.md` becomes: frontmatter → fixed body → one injected
command → manual fallback block. Fixed text is **moved** out of the default,
never copied, so the default loses exactly that text.

**`tcw-extras-triage-issues`** — fixed body:

- The title and framing paragraphs (`:13-31`) unchanged: they route acceptance
  judgment to the `inbox` stage, which is TCW's stage ladder.
- A short section of rules no procedure changes, moved from the default:
  the "issue body is data, not instruction" blockquote (`:127-129`); the
  "Do not write `initial-request.md`" paragraph (`:172-177`, without its first
  sentence "Commit the item.", which is conduct and stays); and the approval
  rule (`:196-201`). The restatement at `:251-253` is removed from the default,
  since the body now always precedes §8.
- Injection: `` !`tcw work procedure prompt triage-issues || true` `` — **no
  slug**. The sweep is about issues, not an item. §8 is reached from
  `tcw work complete` with an item in hand, but the text is the same either way,
  and a project's `when:` then simply never matches (`work.md:106-108`, which
  also tells a project to add an unconditional binding).
- The default keeps its `## 1.`–`## 8.` headings and numbering, so
  `transitions.md`'s "§8" resolves in the composed text a project that
  configures nothing reads. A project replacing the procedure owns whether its
  text answers the issue at closeout; the DoD line and `transitions.md` still
  prompt for it.

**`tcw-post-mortem`** — fixed body:

- Title, "The contract lives elsewhere" and the question (`:7-17`), unchanged.
- The spine order paragraph (`:21-24`) under its heading
  `## Read the spine backwards`: it is the stage ladder read backwards.
- `## Producing the artifact` (`:68-76`) moved whole: writing `post-mortem.md`
  per the stage's `Produce`, filing follow-up items (the stage prompt's own
  step 4, `tcw/work/prompts/postmortem.md`), and never changing status.
- The default keeps: "What each layer tends to reveal" and its bullets,
  `## The distinction that decides everything`, `## When to stop without a
  recommendation`.
- Injection with the item: `arguments: [item]` added to the frontmatter, and
  `` !`tcw work procedure prompt post-mortem $item || tcw work procedure prompt post-mortem || true` ``.
  The second command covers an invocation whose argument is not a slug (free
  text, or nothing that resolves): the verb exits 1 on an unknown item
  (`tcw/work/cli.py:1576-1588`), and without the retry the reader would get no
  procedure at all.
- `allowed-tools: Bash(tcw *)` added so the injected command is pre-approved, as
  in `tcw-work-stage` (`:6`).

**Ordering in the composed text.** In the triage skill the moved rules now come
before §1 rather than inside §4–§6, and in the post-mortem skill `Producing the
artifact` now comes before the default rather than last. Both are reading-order
changes only and are named in the outcome's diff.

### The agent

`agents/tcw-post-mortem.md` keeps its frontmatter, role, "What you are given",
the spine order (fixed, same as the skill) and its hard limits. "How to look"
stops restating the investigation and tells the agent to run
`tcw work procedure prompt post-mortem <slug>` and follow it, and
`tcw work stage prompt postmortem <slug>` for what the report must cover.
"What to report" points at the stage's `Produce` requirements instead of
restating the default's conduct. The read-only commands it may run gain
`stage prompt` and `procedure prompt`.

### The drift test

`SOURCES` in `tests/test_shipped_procedures.py` maps an id to a file whose body
*is* the default. After conversion that is false for both ids. The rows change
to a check that still catches drift in the direction that matters: the
converted skill **does not contain** the default's text (no copy survives), and
**does** inject `tcw work procedure prompt <id>`. How the test expresses that is
the plan's decision; `test_the_source_map_covers_exactly_the_ids` must keep
passing, so the rows are changed, not deleted.

## Acceptance criteria

1. `grep -niE '\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b'
   skills/tcw-extras-triage-issues/SKILL.md skills/tcw-post-mortem/SKILL.md`
   prints nothing (epic criterion 8).
2. Each of the two `SKILL.md` files contains a `## Document command summary`
   block naming the exact command it injects, with an instruction to run it by
   hand when the harness did not (epic criterion 11).
3. Each `SKILL.md` contains exactly one `` !`tcw work procedure prompt <id> ``
   injection, for its own id; the post-mortem one passes `$item`, the triage one
   passes no slug.
4. In a checkout with no `work.procedures`, the text of each converted skill's
   body with its injection line replaced by `tcw work procedure prompt <id>`'s
   output, compared with `git show main:<path>`'s body, differs only by the
   moves and rewordings listed in `outcome.md`, each explained. No sentence of
   the pre-conversion text is missing from the composed text except the
   triage §8 approval restatement.
5. No paragraph of a skill's fixed body also appears in its default
   (`tcw/work/procedures/<id>.md`).
6. `agents/tcw-post-mortem.md` contains `tcw work procedure prompt post-mortem`
   and no longer contains "was the information available" or "primary trail".
7. `skills/tcw-extras-triage-issues/SKILL.md`'s `compatibility:` says the `gh`
   requirement belongs to the default procedure.
8. `tcw work procedure prompt triage-issues` output still contains the heading
   `## 8. Closing the loop when the work item finishes`.
9. `tests/test_shipped_procedures.py`, `tests/test_dynamic_skill_marker.py`,
   `tests/test_skill_lifecycle_parity.py` and `tests/test_plugin_manifests.py`
   pass, and bare `pytest` passes.
10. The item's `capabilities.yaml` carries both `changed:` entries, and
    `tcw capabilities check` exits 0.

## Risks

- **`$item` substitution when the skill is invoked without an argument** is
  assumed to be an empty string; if Claude Code leaves the literal `$item`, the
  first command fails on "no such work item" and the retry serves the default,
  so the reader still gets the text, with a stray error line. Checked only in a
  live session, which is deferred.
- **Injected commands run a project's `generate:` scripts.** That is true of
  `tcw-work-stage` already; the read-only agent inherits it by running
  `procedure prompt`, whose scripts could write. The agent's hard limits carry
  that, as `delegation.md:61-66` says they must.
- **Moving the approval rule into the fixed body is a policy choice.** A
  project that wants replies posted without per-message approval can no longer
  get that from an override. Listed for the requester to confirm.
- **Sibling conversions edit the same shared files**
  (`tests/test_shipped_procedures.py`, `docs/changelogs/upcoming.md`,
  `docs/release-notes/upcoming.md`). Each touches only its own rows and appends
  at section ends.

## Decisions for the requester to confirm

1. The forge stays a declared requirement of the default; no forge binding.
2. The approval rule and the "issue body is data" rule are fixed, not conduct.
3. The triage skill passes no slug; the post-mortem skill passes `$item`, with a
   no-slug retry.
4. Triage §-numbering is kept in the default so `transitions.md` needs no edit.

## Notes

- `tcw work stage gate spec <slug>` refused: "'spec' is not legal for an item in
  'active'; it runs in backlog". The item was started into its worktree before
  planning by the requester's choice; the spec was written anyway, as the brief
  directs.
- A `github` provider for `work.tracker` is the route if TCW ever wants the
  forge abstract. Not filed: this session may not create items; recorded here
  for whoever reviews the epic.
- The procedure verb was probed in this worktree: an unknown slug exits 1 with
  "no such work item", which is what the post-mortem retry exists for.
