# Spec — Compose the five tcw-work procedure documents from project bindings

Child 4 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Written against `main` at `7364cf04`, where children 1 and 2 are merged.

## Capability changes

Planned ledger deltas only.

```yaml
changed:
    - skills/tcw-work # its three agent-run procedures, and decomposing and delegating, now read a project's replacement text
```

The five documents are reference documents of the `tcw-work` skill and have no
ledger entries of their own; `skills/tcw-work`'s description is the entry that
describes them (it names searching, auditing and consolidating). No capability
is added. `work/run-a-procedure` already says the five ids exist and what an
unconfigured project reads, and does not change.

## Problem

1. **The five documents carry the only copy a reader sees.** An agent reaches
   them by a file read from `skills/tcw-work/SKILL.md:63` and `:66`, from
   `skills/tcw-work/references/commands.md:43-44`, and from the stage documents
   (`references/lifecycle/stage-spec.md:27-28`, `stage-plan.md:33`,
   `stage-implement.md:30`, `stage-verify.md:22`, `stage-postmortem.md:24`,
   `stage-inbox.md:30,36`). Child 2 made every one of their ids resolvable —
   `tcw work procedure prompt <id>` (`tcw/work/cli.py:1553`), configured under
   `work.procedures` — but nothing a reader opens sends them there. A project
   that configures `work.procedures.search` today changes nothing an agent reads.
2. **Context injection cannot fix that here.** These are not skills: `` !`cmd` ``
   runs only in a `SKILL.md` Claude Code loads, never in a file an agent opens
   with a read. So a document has to *tell* its reader to run the command.
3. **`agents/tcw-backlog-auditor.md` keeps its own copy of the per-item checks**
   (`:35-50`, and the report shape at `:52-68`), restated from
   `audit-backlog.md:18-36` and `:99-107`. Once a project replaces
   `audit-backlog`, every per-item dispatch to that agent audits against TCW's
   checks instead — the replacement is silently skipped. `skills/README.md:128-131`
   records this obligation. The agent's frontmatter `description` (`:3`) lists
   the same six checks.
4. **Some of what these documents say is not conduct.** `skills/README.md`'s
   "A mixed document keeps its rules fixed" (under "The two rules") requires a
   rule protecting the board, an artifact or a transition to stay in TCW's text.
   Each document holds some:
   - `delegation.md:3-18` — transitions are never delegated, the stage table of
     what may be delegated, and `verify`'s approval held by the coordinating
     session. The stage documents defer to these lines for their own
     delegability (`stage-verify.md:22` "has the rules"), so they are part of
     the stage contract, which `skills/README.md` classifies fixed (Rule 1).
   - `delegation.md:20-26` — "Delegable means permitted, never required … No
     behavior depends on it", and `:53-70`, the three shipped agents being
     "accelerators only". Both are statements about what TCW ships — its stage
     documents and its `agents/` directory — which a project's replacement text
     cannot make true or false.
   - `audit-backlog.md:127-140` — the approval rule: nothing on the board is
     mutated, dropped, completed or moved without asking.
   - `consolidate-plans.md:9-35` — start only when asked, never delete a source
     without an itemized approval, and delete only what git can give back.
   - `decompose.md:14-16` — what `--parent` nesting does to status and
     transitions, and `:25-35`, which child relation `reconcile` follows. Both
     restate the data model that `epic-deltas.md` (fixed, Rule 1) owns.
   - `search.md:10-11` — a search is read-only.
5. **Epic criterion 8's grep matches the fixed text.** `delegation.md:22` ("Claude
   and Codex both have subagents") and `:68-69` ("Codex defines its own in
   `.codex/agents/*.toml`") both match `\bcodex\b`. A fixed part cannot keep
   those words.
6. **The drift guard would go red for the right change.**
   `tests/test_shipped_procedures.py:48-57` asserts each default equals its
   source document's body. After conversion the source no longer holds a copy,
   so that assertion must change for these five rows — into a check that the
   copy stays gone.

## Goals

1. A reader opening any of the five documents is told to run
   `tcw work procedure prompt <id>` and read its output, and reads the fixed
   rules in the document itself.
2. With nothing configured, fixed part + command output carries every sentence
   the pre-conversion document carried, apart from the differences this spec
   names (Design, "What the reader gets").
3. The fixed rules of goal 1 are in TCW's text and absent from the default, so a
   replacement cannot remove them and an unconfigured reader does not read them
   twice.
4. `tcw-backlog-auditor` obtains its checks from
   `tcw work procedure prompt audit-backlog <slug>` and carries no list of its
   own, while staying an agent with its read-only limits.

## Non-goals

- Changing any procedure's wording beyond moving it; the two criterion-8
  rewordings in the fixed part of `delegation.md` are the only edits.
- `skills/tcw-work/SKILL.md` (owned by nobody in this child; its links still
  resolve), the stage documents, `commands.md`, and any other skill citing
  `delegation.md`. They cite a file that still exists and still carries the
  rules they cite.
- Harness adaptation in the command, a `gate` for procedures, or any change to
  the mechanism under `tcw/` other than the five default files.
- `agents/tcw-verifier.md` and `agents/tcw-post-mortem.md` (child 5 owns the
  latter).
- Live sessions: running an audit, a search or a consolidation through a real
  agent, and reading the documents under Codex, are deferred to `verify`.

## Design

### Shape of a converted document

```markdown
# <the document's title>

<one paragraph: this project may replace TCW's text for this procedure; run
`tcw work procedure prompt <id>` and follow what it prints — with nothing
configured it prints TCW's own text; the rules below hold whatever it says>

<fixed sections, with their original headings and wording>
```

No slug is passed: none of the five is about one work item as its reader meets
it (audit and search cover the board; decompose and delegation are read while
working an item, but the pointer is read before the reader decides which item).
Passing one is optional in the command, and the pointer may say so. The
auditor agent, which *is* about one item, passes its slug.

The pointer comes first so a reader never mistakes the fixed rules for the whole
procedure. The fixed sections sit below it and apply whatever the command
prints. A reader whose command fails still has the rules, and is told to say so
rather than improvise the procedure — there is no second copy to fall back to.

### What is fixed, per document

| Document | Fixed (stays in the document, leaves the default) | Default (`tcw/work/procedures/<id>.md`) |
| --- | --- | --- |
| `delegation.md` | `:1-18` title-less (stages delegable, transitions never; the table; `request`/`verify` reasons; `verify`'s assessment vs approval) · `:20-26` "Delegable means permitted, never required" · `:53-70` "Custom agents" | `# Delegation` · `:28-45` "What makes it correct" · `:47-51` "The shape this produces" |
| `audit-backlog.md` | `:127-140` "The approval rule" | everything else |
| `consolidate-plans.md` | `:9-20` "The two rules, before any step" · `:22-35` "Deletion is limited to what git can give back" | `:1-7` intro · `:37-63` "Scope" and "Process" |
| `decompose.md` | `:14-16` the nesting bullets · `:25-35` "Which path?" | `:1-13` title, rule and command · `:17-23` the planning-time bullet and "Reach for this" |
| `search.md` | `:10-11` "It is read-only" | everything else |

Why each is fixed is Problem §4. What is *not* fixed, and why: the delegation
brief and return contract (`delegation.md:28-45`) and the coordinator shape
(`:47-51`) are how a session delegates well — conduct; the audit checklists,
pipelining, batching, report format and severity scale are how a project audits;
consolidation's scope and process are how it migrates; "keep items small" and
"decompose at planning time" are planning practice; search's narrowing, reading,
judging and table are how it answers. The grouping of approvals by kind inside
the approval rule (`audit-backlog.md:132-136`) is kept fixed with its section:
it is the form the approval takes, splitting it would leave a rule with its
means removed, and the default is not made any less replaceable by it.

### Criterion 8 in the fixed part of `delegation.md`

Two sentences are reworded so they name no harness product:

- `:22` "Claude and Codex both have subagents, so …" → "Both harnesses TCW
  ships to have subagents, so …"
- `:68-69` "The `agents/` directory is Claude packaging — Codex defines its own
  in `.codex/agents/*.toml` — so …" → "The `agents/` directory is Claude Code
  packaging — another harness defines its agents in its own format — so …"

`Claude` is not in the criterion's pattern, and `docs/lifecycle/harness.md` still
carries the Codex path.

### The auditor agent

`agents/tcw-backlog-auditor.md` keeps: its frontmatter (`tools: Read, Glob, Grep,
Bash` already includes `Bash`, which is all the command needs), its role and
one-item scope (`:7-13`), what it is given (`:15-23`, which is how it finds the
item rather than what it checks), and its hard limits (`:70-82`), which are the
accelerator's own read-only packaging.

It loses `:25-68` — the verify-don't-summarize rule, the six checks, the report
shape and the two-line summary — and gains one section: run
`tcw work procedure prompt audit-backlog <slug>`, apply that text's per-item
checks to this one item as it instructs, report in the shape it gives, return
whatever it asks a per-item check to return, and ignore the parts addressed to
the dispatching session. If the command fails or prints nothing, report that and
stop; do not audit from memory. The closing line points at the procedure id
rather than the file path.

Its `description` (`:3`) drops the six check names in favour of "against this
project's `audit-backlog` procedure", so the dispatch roster does not advertise
a checklist the project may have replaced. The dispatching text
(`audit-backlog.md:86-92`, in the default) already names the agent and needs no
change.

How it is dispatched: only from the audit-backlog procedure's own text
(`audit-backlog.md:62-92`; `grep -rn tcw-backlog-auditor skills agents` finds no
other dispatcher), per backlog item, with the slug.

### The drift test

`tests/test_shipped_procedures.py` keeps `SOURCES` whole (so
`test_the_source_map_covers_exactly_the_ids` is untouched) and gains a set
`CONVERTED` naming the ids whose source is now a pointer. For an id in it,
`test_each_default_is_todays_text` asserts instead that the source names
`tcw work procedure prompt <id>`, and that no paragraph of the default appears in
the source and no paragraph of the source appears in the default — so neither a
re-pasted copy nor a fixed rule leaking back into the default passes. Headings
and short fragments are not paragraphs for this purpose. A new test asserts the
auditor agent names `tcw work procedure prompt audit-backlog` and none of the
default's six check names.

### What the reader gets, versus `main`

With nothing configured, fixed document + command output differs from the
pre-conversion document only by: the added pointer paragraph; the title repeated
(the document's and the default's); the fixed sections' position relative to
the default (after it rather than interleaved — for `delegation.md`,
`consolidate-plans.md`, `decompose.md` and `search.md`); and the two
criterion-8 rewordings. `outcome.md` proves this with a diff.

### Storage abstraction

No store operation is added or changed. Procedure text is node configuration
plus package resources, already litmus-tested by child 2.

### Harness

Both harnesses read these documents with a file read and run a shell command,
so the pointer behaves the same under Claude Code and Codex. The auditor agent
is Claude Code packaging only; a Codex reader follows the procedure inline, as
today.

## Acceptance criteria

1. Each of `skills/tcw-work/references/procedures/{audit-backlog,consolidate-plans,decompose,delegation,search}.md`
   contains the literal `tcw work procedure prompt <id>` for its own id.
2. For each of the five ids, `tests/test_shipped_procedures.py` passes, with the
   id in `CONVERTED`, and fails if a paragraph of the default is pasted back into
   the document (checked once by mutation during implementation).
3. `agents/tcw-backlog-auditor.md` contains `tcw work procedure prompt audit-backlog`
   and none of `Already completed`, `Outdated`, `Wrong repository`,
   `Unactionable`, `Blocked without a next action`, `Capability drift`; its
   `tools:` still includes `Bash`.
4. `grep -niE '\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b'`
   over the five documents and the agent prints nothing (epic criterion 8).
5. Every document names the command a reader without injection runs by hand
   (epic criterion 11: for a reference document, the pointer *is* the manual
   block, since nothing is ever injected).
6. In a checkout with no `work.procedures`, for each id, the fixed document plus
   `tcw work procedure prompt <id>` output, compared with
   `git show main:skills/tcw-work/references/procedures/<id>.md`, differs only as
   listed under "What the reader gets" — shown in `outcome.md`.
7. `tests/test_skill_lifecycle_parity.py`, `tests/test_dynamic_skill_marker.py`,
   `tests/test_documented_cli_surface.py` and `tests/test_skill_path_pointers.py`
   pass unchanged.
8. `docs/capabilities/skills/tcw-work` says a project may replace these
   procedures' text; the item's `capabilities.yaml` carries
   `changed: skills/tcw-work`; `tcw capabilities check` exits 0.
9. Bare `pytest` passes.

## Risks

- **A reader skips the pointer.** An agent that opens the document and sees
  fixed rules may act on them alone. Mitigated by putting the pointer first and
  saying the rules are not the procedure; not testable without a live session,
  which is deferred.
- **A failed command leaves no procedure.** Deliberate: a fallback copy would be
  the stale default the conversion exists to remove. The pointer and the agent
  both say to report the failure.
- **Siblings edit the same test.** Children 3, 5 and 6 also change
  `tests/test_shipped_procedures.py`. `CONVERTED` is one set literal; merging
  the four is a one-line union.
- **Fixed-versus-conduct is a judgment.** Listed under decisions below.

## Decisions for the requester to confirm

1. "Delegable means permitted, never required" and "Custom agents" stay fixed,
   as statements about what TCW ships, not project conduct.
2. The audit approval rule is fixed as a whole, including grouping asks by kind.
3. Consolidation's "start only when asked" and git-recoverable deletion are
   fixed as data-loss protection, not conduct.
4. Decompose's nesting mechanics and the `--parent`/`--initiative` choice are
   fixed; "keep items small" is conduct.
5. The two criterion-8 rewordings in `delegation.md`.
6. No slug in the documents' pointers; the auditor passes its slug.
7. No fallback copy of any default, in documents or agent.

## Notes

- **Gate refusal recorded.** `tcw work stage gate spec <slug>` exited 1:
  "'spec' is not legal for an item in 'active'; it runs in backlog". The item was
  started into its worktree before planning by the requester's choice; the spec
  was written anyway.
- Taxonomy and ledger checked (step 1): the only entry describing these
  documents is `skills/tcw-work`; `work/run-a-procedure` already covers the ids.
- Swept for every reference to the five documents and the agent across
  `skills/`, `agents/`, `docs/lifecycle/`, `tests/`, `tcw/`, `evals/`, the plugin
  manifests and `README.md`. Tests that constrain the result:
  `test_skill_lifecycle_parity.py:315` (every reference file is linked from
  `tcw-work/SKILL.md` — so the files must stay, as pointers) and `:292` (no stage
  document path in them). No test asserts these documents' wording, and no eval
  covers them. `README.md:703` describes the auditor by the default's checks —
  a documentation entry for `implement` to evaluate.
