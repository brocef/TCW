# Spec: split `tcw work stage` into `prompt` and `begin`

## Capability changes

Two entries in the standing ledger change. No records are written here.

- `work/run-a-lifecycle-stage` — the verb becomes `tcw work stage begin`, a new
  `tcw work stage prompt` is added, and the published guarantee that an illegal
  stage is "refused **before any hook runs**" narrows to `begin`.
- `work/read-the-documentation-gate-for-a-change` — the sentence naming
  `tcw work stage plan` / `implement` becomes `begin`, and documentation entries
  now also reach a reader through `prompt`, whether or not the gate would pass.

No capability is removed. `prompt` is an addition; `begin` is a rename of the
existing one.

## Problem

`tcw work stage <id> <slug>` answers two different questions with one command,
and you cannot ask the first without paying for the second.

- **What does this stage ask me to produce?** For most projects the answer is
  constant — whatever the stage's `prompt:` bindings resolve to.
- **May I enter this stage for this item right now?** A gate, decided by the
  item's status and by the stage's `pre:` bindings.

The second is always answered first, and answering it has side effects. This
repository is its own example (`tcw-config.yaml:46-48`):

```yaml
plan:
    pre:
        - command: "python scripts/require_artifact.py spec"
```

Asking "what does the plan stage involve?" for an item whose spec is unwritten
runs a Python script and then refuses, printing nothing. The instructions were
never the thing being gated, but they are what you do not get.

Two further consequences:

- Reading a stage's instructions requires naming a work item, even when the
  resolved text does not depend on one.
- `--no-exec` looks like a read-only mode and is not one: with `execute=False`,
  both `file:` and `generate:` bindings resolve to the empty string
  (`tcw/work/resolve.py:197-205`), so its text is incomplete. It answers "what
  would run", not "what does this say".

## Goals

1. A reader can obtain any stage's instructions without entering that stage and
   without TCW running a gate of its own.
2. That works with no work item named, and with one named, for all seven stages.
3. Everything an agent does today keeps working identically, gates included.
4. One spelling per operation: no alias, no flag that changes a verb's meaning.

## Design

`tcw work stage` gains two subcommands and stops accepting a bare stage id.

| Command | Legality check | `pre` checks | Prompt resolved | Slug |
| --- | --- | --- | --- | --- |
| `tcw work stage prompt <stage> [<slug>]` | no | no | yes | optional |
| `tcw work stage begin <stage> <slug>` | yes | yes | yes | required |
| `tcw work stage <stage> <slug>` | — | — | — | **removed** |

`begin` is exactly today's behavior under a new name. `prompt` is today's
behavior with the gate removed, split at a seam that already exists inside
`_stage` (`tcw/work/cli.py:816-903`).

#### `prompt` — read, without entering

Resolves the stage's `prompt:` bindings and prints the result on stdout. It does
**not** check status legality and does **not** run `pre:` bindings.

It does run `file:` and `generate:` bindings, because those are how instruction
text is produced. The promise is therefore narrower than "no side effects", and
is stated that way: **`prompt` runs no gate or check of its own; it runs only
what producing the text requires.** A `generate:` script's own effects are that
script's contract. TCW still decides to spawn it, so the wider claim would be
false.

**The slug is optional and does two things, not one.**

- *Omitted* — resolution runs against the **local anchor node** (`_store()`,
  `tcw/work/cli.py:91-95`) with `item=None`. `when:` conditions never match
  (`Condition.matches` returns `False` for no item), a `generate:` hook receives
  `{"item": null, …}`, and `{{tcw:body}}` falls back to its no-body text.
- *Given* — the reference goes through `_resolve` (`tcw/work/cli.py:98-112`),
  which accepts a `<project-id>/<slug>` qualifier and resolves to **that node's
  store**. So a qualified slug selects a different `tcw-config.yaml`, different
  `prompt:` bindings, and a different set of documentation entries. The item is
  then resolved and the prompt personalizes. Still no legality check, still no
  `pre` checks.

A slug that names no item is an error, as everywhere else.

**When the stage is illegal for the item's status, `prompt` still prints, and
says so on stderr.** The built-in prompts are not inert descriptive text: they
contain state-changing instructions — `prompts/verify.md:16` opens with
`tcw work submit <slug>` and line 27 says `tcw work complete <slug>`;
`prompts/implement.md:16` says `tcw work start <slug>` before the first code
edit. Today the legality check guarantees those are never shown out of context.
`prompt` gives that up deliberately, so it must not do so silently:

```
tcw work stage prompt: note — 'verify' is not legal for an item in 'backlog';
printing its instructions anyway because you asked to read them
```

stdout stays byte-pure and the exit code stays 0. A reader who piped the output
is unaffected; a reader who did not is told.

**Documentation entries** are part of prompt resolution, so `prompt` includes
them. They therefore reach a reader whether or not the gate would have passed.

#### `begin` — the gate and then the instructions

Today's behavior, with the ordering contract preserved exactly:
`stage → item → legality → checks → resolve → print`. Legality is decided before
any hook runs. **A failed legality check or a failed `pre` binding aborts before
anything is resolved**: nothing on stdout, the reason on stderr, exit 1. stdout
carries the resolved prompt and nothing else, emitted once at the end after
everything that could fail has succeeded.

#### The `inbox` stage

`inbox` runs before an item exists, so a slug is refused rather than optional:

| Command | Result |
| --- | --- |
| `tcw work stage prompt inbox` | prints the inbox instructions, no checks |
| `tcw work stage begin inbox` | runs inbox's `pre:` bindings, then prints |
| either, with a slug | exit 1, "runs before an item exists" |

`begin inbox` is the direct successor of what the in-flight branch ships as
`tcw work stage inbox`. Its legality check is skipped because
`STAGE_STATUSES["inbox"]` is empty and there is no status to judge — the branch
is selected on the stage id, never on that emptiness.

### Removing the bare form

**This is a choice, not a constraint.** The repository already contains the
mechanism to avoid it: `_normalize` (`tcw/cli.py:271-278`) rewrites
`tcw <component> <path>` into `tcw <component> show <path>` before `parse_args`
runs, and `STAGE_IDS` (`tcw/store/base.py:599`) is a closed set of seven, none
of which is `prompt` or `begin`, so an alias could be added unambiguously in
about three lines.

It is removed anyway, on the deliberate decision that one spelling is worth more
than a legacy path. The costs being accepted:

- Every downstream repository's own `CLAUDE.md`, `AGENTS.md`, hook scripts, CI
  steps, and slash commands that invoke the bare form break on upgrade.
- Rollback is a further release, and anyone who migrated their own repository
  must migrate back.

`tcw work stage spec my-item` therefore fails as an argparse unknown
subcommand. The error must name the replacement:

```
tcw work stage: 'spec' is not a subcommand; run `tcw work stage begin spec my-item`
```

#### The real migration scope

The earlier figure of 143 was wrong: it was the repository-wide match count
*including* `docs/work/`, and it double-counted `CLAUDE.md`, which is a symlink
to `AGENTS.md`.

| Measurement | Count |
| --- | --- |
| Repo-wide matching lines, including `docs/work/` | 143 |
| Outside `docs/work/` | ~100 |
| Inside the scope that must actually change | ~75, across 33 files |

**What must not be rewritten is already defined in the repository.** `ARCHIVAL`
(`tests/test_documented_cli_surface.py:36-42`) lists `docs/work/`, `docs/plan/`,
`docs/superpowers/`, `docs/changelogs/`, and `docs/release-notes/` as documents
that record what was true at a point in time. A changelog naming a command that
existed when it was written is a true historical statement. The migration keys
off that constant rather than an ad-hoc list.

#### Which verb replaces the bare form

This is the decision that determines whether the change is worth its cost, so it
is stated rather than left to the implementer:

- **The seven lifecycle routers** (`skills/tcw-work/references/lifecycle/*.md`),
  `skills/tcw-work/SKILL.md`, `commands/`, `agents/`, `AGENTS.md`, and both
  capability descriptions say **`begin`**. The agent path is unchanged: legality
  is checked, this repository's `plan.pre` gate still fires, and the published
  guarantee below stays true where agents work.
- **`prompt` appears only where inspection rather than entry is intended** —
  `README.md` examples that demonstrate reading, and
  `references/lifecycle/default/README.md`.

The honest scope of this work is therefore **an added inspection path, not a
change to how agents drive the lifecycle.**

#### A published guarantee narrows

`docs/capabilities/work/run-a-lifecycle-stage/description.md:39-40` publishes:
"A stage that makes no sense for the item's current status is refused **before
any hook runs**." After this change that is true of `begin` and not of
`prompt`. The description must say so.

### Two capability descriptions change, not one

- `docs/capabilities/work/run-a-lifecycle-stage/description.md` — the verbs, the
  narrowed guarantee, and (from the in-flight item's deferred criterion) the
  claim that `tcw work stage inbox` is refused.
- `docs/capabilities/work/read-the-documentation-gate-for-a-change/description.md:5-6`
  — states "`tcw work stage plan` and `tcw work stage implement` render them
  into the stage's instructions", which names the bare form and describes the
  behavior that now differs between the two verbs.

### Release shape

The in-flight branch never reaches `main` on its own: this work lands on
`claude/tcw-work-list-zx961v`, and that branch merges to `main` once this item
completes. Both items therefore ship in **one release, version 2.0.0**, and this
item owns the reconciliation:

- `docs/release-notes/upcoming.md` currently says the inbox stage "is the one
  stage you run without naming a work item" and that "Every other stage is
  unchanged and still takes its work item." Both become false and must be
  rewritten, not appended to.
- `docs/changelogs/upcoming.md` documents the `nargs="?"` change this work
  replaces. Same.
- A migration guide is required. The repository has five
  (`docs/migration-guide-*.md`), including one for the last major release;
  removing a published command without one breaks the house pattern.

Because nothing ships between the two items, the two review findings from the
in-flight branch that this work deletes — the `_stage`/`_stage_without_item`
duplication and the untested `'<stage>' needs a work item` branch whose exit
code moved from 2 to 1 — are correctly left unfixed there.

### Error message prefixes

Messages from the two verbs are prefixed `tcw work stage prompt:` and
`tcw work stage begin:` respectively; the unknown-subcommand error keeps
`tcw work stage:`. Tests assert on these strings, and criterion 9's byte
identity covers stdout only, so this is stated rather than discovered.

## Acceptance criteria

1. `tcw work stage prompt <stage>` exits 0 for all seven stages in a node with
   no lifecycle configuration, and prints the built-in prompt.
2. `tcw work stage prompt <stage> <slug>` exits 0 for an item in **any** status,
   including one where that stage is not legal.
3. In a scratch node whose `plan.pre` binds a command that creates a sentinel
   file, `tcw work stage prompt plan <slug>` exits 0 on an item with no
   `spec.md`, **and the sentinel does not exist afterwards**. The gate is a
   throwaway fixture, not this repository's `require_artifact.py`, which creates
   no sentinel and so could never evidence its own non-execution.
4. In that same scratch node, `tcw work stage begin plan <slug>` on the same
   item exits 1, prints nothing on stdout, and **does** create the sentinel —
   so criterion 3 is not passing merely because the gate never worked.
5. When the stage is illegal for the item's status, `prompt` exits 0, prints the
   instructions on stdout, and prints the "not legal … printing anyway" notice
   on stderr.
6. `tcw work stage prompt <stage> <slug>` stdout is byte-identical to
   `tcw work stage begin <stage> <slug>` stdout, for an item whose stage is legal
   and whose checks pass, **in a fixture node whose bindings are deterministic**
   (no `generate:`), run from the same node.
7. A `when:`-conditioned prompt binding is skipped by `prompt <stage>` and
   matched by `prompt <stage> <slug>` when the item's tags match.
8. `tcw work stage prompt <stage> <project-id>/<slug>` resolves that node's
   `prompt:` bindings, not the anchor node's — demonstrated with two nodes whose
   bindings differ.
9. `tcw work stage begin <stage> <slug>` stdout is byte-identical to that of the
   pre-change `tcw work stage <stage> <slug>`, compared against the recorded
   baseline in `tests/fixtures/prompt_fallback/unconfigured.json` with only the
   `argv` fields updated.
10. `begin` with a failing gate exits 1 with empty stdout and the reason on
    stderr; nothing is resolved.
11. `tcw work stage <stage> <slug>` exits **2** (argparse's unknown-subcommand
    exit) and its stderr names `begin`. Criterion 12's "exit 1" does not apply
    to it.
12. Every error originating in the two verbs' own handlers exits 1 with empty
    stdout and the message on stderr.
13. Both verbs refuse a slug for `inbox` and accept its absence; `begin inbox`
    runs inbox's `pre:` bindings.
14. `tcw work stage prompt <stage> --no-exec` is rejected, because `--no-exec`
    suppresses `file:` and `generate:` and would make `prompt` print incomplete
    text — not because there is nothing to report.
15. `tests/test_documented_cli_surface.py` passes with `DOCUMENTED_VERBS`
    updated to the two verbs, and no non-archival document names the bare form.
    Archival scope is `ARCHIVAL` in that module, not a hand-written list.
16. `tests/fixtures/prompt_fallback/unconfigured.json` has its six recorded
    `argv` entries changed from `["work","stage",…]` to
    `["work","stage","begin",…]`, and **every recorded `stdout` byte is
    unchanged** — verified by diffing the file with the `argv` lines excluded.
    The fixture is never re-captured; its docstring says why.
17. `tests/test_skill_lifecycle_parity.py`'s router assertion is rewritten: the
    literal it checks becomes `tcw work stage begin <stage_id>`, and it fails if
    a router names the bare form or `prompt`.
18. The seven lifecycle routers name `begin`; the grep for the bare form across
    non-archival documents returns nothing **and** the JSON fixture check in
    criterion 16 passes, because a textual grep cannot see argv stored as
    separate tokens.
19. The version is `2.0.0` in all five files; `tests/test_plugin_manifests.py`
    passes.
20. `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` contain
    no statement contradicting the shipped behavior, specifically not "every
    other stage is unchanged and still takes its work item".
21. A migration guide `docs/migration-guide-1.X-to-2.0.0.md` exists and shows
    the before/after for both verbs.
22. Both capability descriptions name the two verbs, and
    `run-a-lifecycle-stage` states that the refusal guarantee applies to
    `begin`. `tcw capabilities check` exits 0.
23. `tcw validate` exits 0 and the full suite passes.

### Alternatives considered and rejected

1. **Make the slug optional and change nothing else** — the requester's own
   first formulation. Rejected because it leaves the gate firing on every read:
   `tcw work stage plan <slug>` would still run `require_artifact.py` and refuse,
   which is the actual complaint.
2. **A sibling `tcw work prompt <stage> [<slug>]` verb**, leaving
   `tcw work stage` untouched. Cheapest option — no migration, no major version.
   Rejected in favor of vocabulary that matches the `prompt:` configuration key
   under `stage`, at a cost this spec states plainly rather than hides.
3. **A `--prompt-only` flag** on the existing command. Rejected: a flag that
   changes what a command fundamentally does is worse than a named verb.
4. **Keeping the bare form as an alias for `begin`** via `_normalize`. Viable
   and cheap; rejected on the explicit decision that one spelling is worth the
   migration.
5. **A `pre` verb**, running the gate alone. Specified, then dropped: no CI job,
   script, hook, config, skill, or test would call it, and gate bindings are
   already inspectable with `tcw work lifecycle --phase pre`. `begin` contains
   it, so it can be added the day someone asks.
6. **An environment variable disabling the gate.** Rejected: invisible at the
   call site, with none of the discoverability of a verb.

### The abstraction litmus test

Both verbs are expressed in the abstract vocabulary — stage id, item reference,
status, and the policy's `pre` and `prompt` bindings. A non-filesystem store
implements them by answering `lifecycle_policy()`, `get()`, `artifacts()`, and
`documentation()`, all of which it must already answer. The split changes which
of those a verb calls, never how it asks. `file:`, `generate:`, and `pre`
commands need a local project root and a process runner, but those are existing
CLI-side binding mechanics, not new work-store capabilities.

### Harness compatibility

Entirely in the CLI, which behaves identically under Claude and Codex. It moves
instruction-reading further into the guaranteed layer rather than relying on a
harness feature, which is the direction `harness.md` asks for.

## Non-goals

- Changing what any stage's instructions **say**.
- Changing `--no-exec` on `begin`.
- Changing the transition verbs or their `pre` bindings.
- A deprecation period or alias for the bare form.
- Shipping a `pre` verb.

## Risks

- **The migration is most of the item.** ~75 occurrence edits, five version
  files, two capability descriptions, both `upcoming.md` files, a migration
  guide, `tests/test_stage_verb.py`, three `tests/cli/scenarios/` documents, and
  the JSON fixture — against a comparatively small amount of new plumbing. Plans
  habitually under-count this half.
- **The golden fixture is the sharpest edge.** Re-capturing it instead of
  hand-editing `argv` would destroy the back-compat evidence and still pass.
- **`prompt` can print state-changing instructions out of context.** Mitigated
  by the stderr notice, not eliminated. An agent that reads stdout only will not
  see the warning.

## Notes

If, after shipping, the routers' `begin` path is what everyone uses and `prompt`
is invoked only by the author, the change bought a major version and a migration
for an inspection path nobody needed — and the sibling-verb alternative (2)
would have been the better trade.
