# Spec — Stop tcw-extras-autonomous-work mandating a specific advisor, closeout and version policy

Child 3 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Written against the tree child 2 merged (`tcw work procedure prompt`,
`work.procedures`, `tcw/work/procedures/`), not against the epic plan.

## Capability changes

Planned ledger deltas only.

```yaml
changed:
    - skills/tcw-extras-autonomous-work # its advisors, review, closeout and version policy become TCW's replaceable default
```

`tcw capabilities show skills/tcw-extras-autonomous-work` resolves (cap-0c9094,
Supported). Its description names "two advisors, Codex and a separate Opus
subagent" and says the run "never cuts a version or pushes to a remote". Those
stay true for a project that configures nothing, so the status does not move;
the description gains that they are the default a project can replace.
`work/run-a-procedure` and `work/configure-procedures` already describe the
mechanism (child 2) and are not changed.

## Problem

`skills/tcw-extras-autonomous-work/SKILL.md` is one maintainer's practice
shipped as a requirement to every project and to both harnesses. Its body
(line numbers in the file as it stands in this worktree):

- names the Codex CLI and its exact invocation (`:23`) and an Opus subagent
  through the `Agent` tool (`:27`);
- builds its adjudication rule on the count of two — "not a majority (there is
  no majority of two)" (`:33-34`);
- names `SendMessage` (`:39`) and says "Codex is the reliable half" (`:41`);
- names `adversarial-code-reviewer` (`:50`), an agent this repository does not
  ship;
- fixes one version policy, "Never cut one" (`:55`), and one closeout, "merge the
  feature branch into main **locally**. Never `git push`" (`:56`).

Its frontmatter (`:1-5`) declares neither `allowed-tools:` nor `compatibility:`,
unlike `skills/tcw-setup/SKILL.md:5,8` and
`skills/tcw-extras-triage-issues/SKILL.md:5,8`, so its hardest dependency — a
second agent CLI on the PATH — is undeclared.

Child 2 made the text replaceable in principle: `tcw work procedure prompt
unattended-work` prints `tcw/work/procedures/unattended-work.md`, today a
verbatim copy of the skill body (`tests/test_shipped_procedures.py:22,49-54`
enforces the copy). Nothing reads that command yet, so a project's
`work.procedures.unattended-work` binding changes nothing an agent sees.

## Goals

1. The skill body names no advisor, model, harness tool, review agent, branch
   or version policy, and states what an advisor must be and how many are
   wanted.
2. The roster, the review, the closeout and the version policy reach the reader
   through `tcw work procedure prompt unattended-work`, whose shipped default
   keeps today's words for them.
3. A project that configures nothing reads the same instructions it reads
   today, with only the differences `outcome.md` lists and explains.
4. The frontmatter declares what TCW's shipped default needs, and the body tells
   a reader that a replacement may need something else.
5. A harness that runs no injected commands is told exactly what to run.

## Non-goals

- Changing the default's behaviour: its advisors, closeout and version policy
  stay what they are.
- Making the default defer to `work.trunk-branch` or `work.publish-transitions`
  (see Design, "Closeout keys").
- Changing the procedure mechanism (`tcw/work/*.py`), the `dynamic_skill` key or
  any verdict in `skills/README.md`.
- The user's private `autonomous-work` skill outside this repository, and the
  Proposit workspace's copy.
- `evals/coverage.py:34-38`: its exclusion reason ("spawning advisor subagents
  and a `codex exec` call per checkpoint") describes the default run and stays
  true.
- Running the converted skill live, unattended, or under Codex — deferred to
  verify by the requester's decision.

## Design

### What is fixed and what is the project's

Rule 1 (`skills/README.md`) gives conduct to the project. What stays in the
skill body is what an override must not be able to switch off, plus what makes
the skill this skill:

| Part of today's text | Where it goes | Why |
| --- | --- | --- |
| Title, the opening paragraph, "Ask once, at the start" | skill body | The definition of the skill: run items through the lifecycle, the advisors stand in for the human, one question at the start. A replacement that asks mid-run is no longer unattended work. |
| `## The advisors` (roster, invocation, brief, adjudication, idle agents) | default | Which advisors, how they are called and how their answers are weighed is conduct. |
| `## Checkpoint map` (review, QA, version, closeout rows) | default | Conduct; the four mandates the item names live here. |
| `## Hard blockers — stop, report, wait` | skill body | Safety floors — credentials, anything irreversible, spending, product direction. A project may add blockers in its own text; it must not be able to delete these. |
| `## Leave the audit trail` | skill body | Writes a section into `outcome.md`, an artifact (TCW's shape), and is what makes an unattended run reviewable at all. |

The default therefore loses exactly the opening, "Ask once", the hard blockers
and the audit trail, and keeps its two middle sections word for word.

Two words in the moved text are count-specific and are generalized: "ask **the
two advisors**" becomes "ask **the advisors**", and the blocker "Advisors split
on an irreversible choice, or both call the item's premise wrong" becomes
"...or all of them call the item's premise wrong". For two advisors each reads
the same.

### What an advisor must be, and how many

A new fixed section states the contract any roster must meet:

- **Independent of this session** — a separate agent or program that does not
  share the session's context and sees only the brief it is given. Otherwise it
  is the session agreeing with itself.
- **Read-only** — it reads and answers; it never edits, commits, runs a
  transition or pushes. The session acts; the advisor advises.
- **An answer is text that was read** — silence, or a report nobody read, is no
  answer.
- **How many: two**, different from each other where the harness allows (a
  different model or tool), so they do not share blind spots. The procedure
  names them.

**Adjudication does not depend on the count.** Today's rule is "agreement → act;
split → the stronger argument, not a majority". Stated as "an answer is an
argument to weigh, never a vote", it holds for any number. The fixed body says
exactly that, once: with one advisor its answer is weighed against the session's
own reading; with three, two agreeing do not outvote the third. The default
keeps its own adjudication paragraph, including "there is no majority of two",
because it is the default's statement about its own pair. This adds one
sentence of overlap in the no-configuration reading; it is kept rather than
editing the default, whose words the requester wants unchanged.

### How the text is delivered

As `skills/tcw-work-stage/SKILL.md` does it:

- The body injects `` !`tcw work procedure prompt unattended-work || true` ``
  where `## The advisors` and `## Checkpoint map` stood, so the reading order
  matches today's.
- `|| true` keeps a failing command from blanking the whole skill
  (`tests/test_skill_lifecycle_parity.py:423-441` explains why), and
  `Bash(tcw *)` must be in `allowed-tools` or the injection aborts the skill
  (`:445-453`).
- A `## Document command summary` block closes the file, naming the command and
  telling a reader whose harness did not run it to run it themselves.

**No slug is passed.** The skill has no `arguments:` today (`:1-5`) and works a
set of items it confirms with the user *after* it loads, so there is no item at
injection time. The one thing lost is `when:` matching, which never matches
without an item (`skills/tcw-configure/references/work.md:105-107`). The body
covers that in one sentence: if `tcw work procedure prompt unattended-work
--no-exec` reports a binding `skipped (condition)`, re-read the procedure with
each item's slug before working that item.

### Frontmatter

- `allowed-tools: Bash(tcw *), Bash(codex *), Bash(git merge *), Agent, SendMessage`
  — the injected command, then what the default runs: the Codex CLI, its
  subagent tools, and the local merge its closeout performs. `git push` is
  deliberately not pre-approved.
- `compatibility:` says the shipped default needs the Codex CLI and a harness
  with subagents, that a project replacing `work.procedures.unattended-work`
  may need different tools, and that the skill needs a `tcw` new enough to have
  `tcw work procedure prompt`.
- `description:` keeps its trigger words and says the advisors are Codex and an
  Opus subagent *by default*.

**The tension.** The declaration describes TCW's default, not whatever a project
configures, and frontmatter cannot be composed. A reader learns a replacement's
needs in two places: the `compatibility:` text says so, and the body says the
declaration covers TCW's shipped procedure only, and that a harness asks before
running a tool not declared.

**Criterion 8 against criterion 9.** The epic's grep runs over whole `SKILL.md`
files, but criterion 9 requires frontmatter declaring the default's
dependencies, which must name `codex`, `Agent` and `SendMessage`. Criterion 8's
own words are "every converted skill's *body*". This child applies the grep to
the text after the frontmatter, and the test does the same.

### Closeout keys

`work.trunk-branch` and `work.publish-transitions`
(`skills/tcw-configure/references/work.md:158-166`) were considered and the
default does **not** defer to them:

- `work.trunk-branch` only warns when a transition happens off that branch; it
  never merges. It names the trunk, but not the act of merging into it.
- `work.publish-transitions` governs pushing a *provisioned work store* after a
  transition. "Never `git push`" is about the project's code branch, which that
  key does not cover; in this repository it is unset (default `true`) and the
  store is not provisioned, so deferring to it would not express "never push".
- Rewording the closeout row to read those keys would change today's text,
  which Goal 3 forbids.

A project that wants its closeout to follow those keys writes that in its own
procedure text.

### Tests

- `tests/test_shipped_procedures.py::test_each_default_is_todays_text` compares
  each default with its source verbatim. For a converted source that is no
  longer true by design. Its `SOURCES` row keeps naming the skill; the test
  recognizes a converted source by its injecting `tcw work procedure prompt
  <id>`, and then asserts the source carries none of the default's paragraphs —
  the drift that matters once the skill reads the default instead of copying it.
- A new `tests/test_unattended_work_skill.py` checks this skill's own
  obligations: the criterion 8 grep over the body, the injection with `|| true`
  and `Bash(tcw *)` declared, `allowed-tools:` and `compatibility:` present, and
  the fallback naming the command.

### Storage abstraction

No store operation is added or changed. The skill reads configuration through
an existing CLI verb, which a non-filesystem store serves the same way.

### Harness

Under Claude Code the procedure is injected. Under Codex the injection line is
inert and the fallback block names the command; nothing the reader must do is
carried only by injection.

## Acceptance criteria

1. The text of `skills/tcw-extras-autonomous-work/SKILL.md` after its closing frontmatter
   `---` produces no output from
   `grep -niE '\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b'`,
   and contains neither `majority of two` nor `git push` nor `upcoming.md`.
2. The body contains a section stating what an advisor must be (independent,
   read-only, an answer is text read) and that two are wanted, and says an answer
   is weighed, never counted, for any number of advisors.
3. The body contains the line `` !`tcw work procedure prompt unattended-work || true` ``,
   and the frontmatter `allowed-tools:` contains `Bash(tcw *)`.
4. The frontmatter has `allowed-tools:` naming `Bash(codex *)`, `Agent` and
   `SendMessage`, and a `compatibility:` stating that it describes the shipped
   default and that a replacement may need other tools.
5. The body ends with a `## Document command summary` block naming
   `tcw work procedure prompt unattended-work`.
6. `tcw work procedure prompt unattended-work` in this checkout (nothing
   configured) exits 0 and prints `## The advisors` and `## Checkpoint map` with
   the Codex invocation, "no majority of two", `adversarial-code-reviewer`,
   "Never cut one" and "Never `git push`" unchanged from `main`.
7. The skill body with the injection line replaced by that output, diffed
   against `git show main:skills/tcw-extras-autonomous-work/SKILL.md`, differs
   only as `outcome.md` lists, each difference explained.
8. `pytest tests/test_shipped_procedures.py tests/test_unattended_work_skill.py
   tests/test_dynamic_skill_marker.py tests/test_plugin_manifests.py
   tests/test_skill_lifecycle_parity.py` passes, and bare `pytest` passes.
9. The item's `capabilities.yaml` carries `changed: skills/tcw-extras-autonomous-work`
   and `tcw capabilities check` exits 0.

## Risks

- **Sibling merge on `tests/test_shipped_procedures.py`.** Children 4–6 change
  the same drift test for their own sources. The content-based recognition of a
  converted source is written to serve all of them, but two siblings can write
  it differently; the merge picks one.
- **Injected text sits mid-document.** A harness that runs injection but a
  reader that skims may take the fixed hard blockers as the end of the
  procedure's text. Headings make the boundary visible; no more is done.
- **Pre-approving `git merge`.** It pre-approves any merge while the skill is
  active, not only the closeout's. Accepted: the default already instructs one,
  and unattended runs stall on a permission prompt otherwise.
- **The overlap sentence on adjudication** reads twice when nothing is
  configured. Accepted over editing the default's words.

## Notes

- **Gate refusal.** `tcw work stage gate spec <slug>` refused: "'spec' is not
  legal for an item in 'active'; it runs in backlog". The item was started into
  its worktree before planning by the requester's choice; the stage was followed
  anyway.

## Decisions for the requester to confirm

1. The hard blockers, the audit trail, the opening and "ask once" are fixed in
   the skill body; the advisors and checkpoint map are the replaceable default.
2. Two advisors are wanted; the adjudication rule is stated count-free in the
   body ("weighed, never counted"), and the default keeps its own two-advisor
   wording, so one sentence overlaps when nothing is configured.
3. "the two advisors" → "the advisors" and "both call" → "all of them call" in
   the moved text.
4. No slug is passed; a project with `when:` bindings is told to re-read per item.
5. The closeout does not defer to `work.trunk-branch` / `work.publish-transitions`.
6. Criterion 8's grep applies to the body, not the frontmatter, because
   criterion 9 requires the frontmatter to name the default's tools.
7. `allowed-tools` pre-approves `Bash(git merge *)` and not `git push`.
