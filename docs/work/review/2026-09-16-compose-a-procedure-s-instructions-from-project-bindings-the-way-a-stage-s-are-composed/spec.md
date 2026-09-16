# Spec — Compose a procedure's instructions from project bindings the way a stage's are composed

Child 2 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
It builds the mechanism only. No skill is converted to use it here; that is
children 3–6.

## Capability changes

Planned ledger deltas, reserved for this child by the epic. Nothing is written
to the ledger at this stage.

```yaml
new:
    - work/run-a-procedure # read a procedure's instructions, composed for this project
    - work/configure-procedures # declare a project's own text for a procedure
changed:
    - work/configure-the-work-lifecycle # the limits under work.lifecycle now also bound procedure generators
```

Taxonomy checked first. The Feature `configurable-work-lifecycle` already
covers "binding a node's own skills or commands to named lifecycle stages and
transitions"; both new capabilities link to it rather than to a new Feature,
because the binding grammar, the resolver and the limits are the same feature
reached from a new id space. No taxonomy term for "procedure" exists
(`tcw taxonomy search procedure` finds none) and none is added: a procedure is
named only by its configuration key and its command, and a vocabulary entry
nobody else references would be an orphan. `work/run-a-lifecycle-stage` is
**not** changed — the epic's spec gives the reason, and it still holds.

## Problem

1. **Only lifecycle stages compose.** `resolve_prompts`
   (`tcw/work/resolve.py:429-467`) reads
   `policy.stage(stage_id) or [Binding(kind="builtin")]` (`:445`): the project's
   bindings if it wrote any, TCW's shipped text otherwise. Its id space is
   `STAGE_IDS` (`tcw/store/base.py:932`), its built-in text is loaded by
   `load_builtins()` from `tcw/work/prompts/<id>.md` (`tcw/work/resolve.py:47-81`),
   its configuration is `work.lifecycle`, whose top-level keys are fixed at
   `tcw/store/base.py:2267`, and its command is `tcw work stage prompt`
   (`tcw/work/cli.py:1413-1477`). There is no id, no key and no command for any
   instruction text that is not one of the seven stages.
2. **So every other procedure TCW ships is fixed prose** in a skill file, which
   is the epic's whole problem. The epic cannot convert a single skill until this
   mechanism exists.

## Goals

1. A fixed set of **procedure ids**, independent of skill names, each with
   TCW's default text shipped inside the `tcw` package.
2. **`work.procedures`** in `tcw-config.yaml`, a sibling of `work.lifecycle`,
   holding a list of bindings per procedure id in the grammar stage prompts
   already use.
3. **`tcw work procedure prompt <id> [slug]`**, which prints the composed text.
4. **`tcw validate`** reports every mistake in `work.procedures` that it already
   reports for a stage's prompt bindings.
5. **A project that configures nothing sees no change at all**, and each
   procedure's default text is, today, byte-for-byte the text the matching skill
   or reference document already ships — so "unchanged" can be checked by a
   test rather than asserted.

## Non-goals

- **Converting any skill** to read its text from the new command (children 3–6).
- **`procedure gate` and `procedure validate`.** Decided by the requester: a
  procedure has no status to be legal in, and a converted skill always serves one
  fixed id.
- **Project-defined procedure ids.** A project replaces the *text* of TCW's
  procedures; it cannot add procedures to TCW.
- **Executing procedure bindings as checks.** There is no `pre` for a procedure.
  `generate:` still runs, because that is how its text is produced — exactly as
  for a stage prompt.
- **Listing procedures in `tcw work lifecycle`.** That command reports the
  lifecycle contract, and its `--json` output is guarded by a compatibility
  baseline (`tests/test_lifecycle_baseline.py`). Procedures are not lifecycle
  steps. A listing can be added when someone asks for one.
- **A header or footer around the output.** See Design.
- **Harness detection in the new command.** See Design.
- **A `dynamic_skill` frontmatter key** (child 1).

## Design

### Procedure ids

`PROCEDURE_IDS` sits beside `STAGE_IDS` in `tcw/store/base.py`, and is public
API for the same reason: projects type these ids into `tcw-config.yaml`.

| Id | Default text is today's… |
| --- | --- |
| `unattended-work` | `skills/tcw-extras-autonomous-work/SKILL.md` body |
| `triage-issues` | `skills/tcw-extras-triage-issues/SKILL.md` body |
| `documentation-sync` | `skills/documentation-sync/SKILL.md` body |
| `post-mortem` | `skills/tcw-post-mortem/SKILL.md` body |
| `create-work` | `skills/tcw-work-create/SKILL.md` body |
| `audit-backlog` | `skills/tcw-work/references/procedures/audit-backlog.md` |
| `consolidate-plans` | `skills/tcw-work/references/procedures/consolidate-plans.md` |
| `decompose` | `skills/tcw-work/references/procedures/decompose.md` |
| `delegation` | `skills/tcw-work/references/procedures/delegation.md` |
| `search` | `skills/tcw-work/references/procedures/search.md` |

A skill's **body** is everything after its YAML frontmatter. Frontmatter is how a
harness finds and describes the skill, not procedure, and it stays in the skill.

Each id names what the procedure does, never the skill that carries it, so the
planned skill rename
(`2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`)
changes no project's configuration.

### Default text

`tcw/work/procedures/<id>.md`, beside `tcw/work/prompts/`, packaged the same way
(`pyproject.toml:32-34` gains `procedures/*.md`). `load_builtins()` gains a third
map, `procedures`, derived from `PROCEDURE_IDS` rather than from a literal list,
and refuses a missing or empty file with the same `ResolveError` it raises for a
stage prompt (`tcw/work/resolve.py:70-79`). So an id added without its file fails
when anything loads the built-ins, not when a user first asks for it.

**Verbatim copies now, not placeholders.** Each file is today's text, copied
unchanged. That makes the mechanism testable end to end today, and makes
"nothing configured behaves as today" something a test checks: a parity test
compares each default with the skill body or reference document it was copied
from, and fails if either changes without the other. A placeholder cannot ship
silently because there is none — and the parity test is also what stops a
default drifting from its skill in the weeks before a conversion child lands.
Each conversion child changes both sides together and updates that test's
expectation for its ids, deliberately.

### Configuration: `work.procedures`

```yaml
work:
    procedures:
        unattended-work:
            - file: docs/procedures/unattended-work.md
        documentation-sync:
            - builtin: true
            - blob: "Also update docs/guide/ when a CLI flag changes."
```

- A **sibling** of `work.lifecycle`, not inside it. Procedures have no gate, no
  artifact, no `pre` and no place in the stage ladder.
- Each id maps to a **plain list** of bindings. A stage needs `prompt:` because it
  also has `pre:`; a procedure has one role only, so a second level of nesting
  would say nothing. There is no "legacy bare list" meaning here, and `command:`
  is refused with the same hint to use `generate:` a stage's `prompt:` gets.
- Kinds allowed: `blob`, `file`, `generate`, `builtin`, `skill` — exactly
  `PROMPT_KINDS` (`tcw/store/base.py:963`).
- Parsed by the same `_parse_binding_list` (`tcw/store/base.py:1890-1913`), so
  blank references, duplicates, unknown keys, several kinds at once and a
  malformed `when:` are refused by the code that refuses them for stages.
- An **empty list is refused**, for the reason `_empty_prompt`
  (`tcw/store/base.py:1949-1956`) gives: after parsing it cannot be told apart
  from not writing the key, which falls back to TCW's text. `[{blob: ""}]` is the
  explicit way to make a procedure say nothing.
- `file:` bindings are checked for existence and for leaving the node by the
  same adapter check that covers stage bindings
  (`tcw/store/fs.py:5499-5535`).
- **Limits:** a `generate:` binding for a procedure runs under
  `work.lifecycle.timeout` and `work.lifecycle.output-cap`, the same two limits
  every other `generate:` uses. They are not duplicated under `work.procedures`:
  two timeouts for one kind of script would be a second way to say one thing.

Parsed into the existing `LifecyclePolicy` (`tcw/store/base.py:1560-1590`) as a
`procedures` map with a `procedure(id)` accessor returning `[]` when unset, filled
by the adapter's `lifecycle_policy()` (`tcw/store/fs.py:5372-5381`). No new
abstract store method: `WorkStore.lifecycle_policy()` already promises "the
node's configured bindings", and the resolver needs the limits from the same
object.

**Abstraction litmus test.** A procedure's bindings are node configuration read
through the path that already serves `work.lifecycle`, and resolution reads
package resources and node files. A tracker-backed node could hold a mapping of
procedure ids to text exactly as it holds stage bindings, so nothing here is a
filesystem-only operation. `file:` stays the node-local kind it already is.

### Resolution

`resolve_procedure(policy, procedure_id, item, node_root, builtins, artifacts,
env, *, execute, documentation)` in `tcw/work/resolve.py`, sharing its loop with
`resolve_prompts` rather than copying it: bindings are
`policy.procedure(id) or [Binding(kind="builtin")]`, every matching binding is
resolved through `_resolve_one` in declaration order and joined by `_join`, and
the `{{tcw:documentation}}` and `{{tcw:body}}` spans are substituted over the
joined text. None of today's ten default texts contains either token (checked by
`grep -rn '{{tcw:'` over the source files, which prints nothing), so
substitution cannot change a default.

A `generate:` script receives `TCW_HOOK_ROLE=procedure`, `TCW_HOOK_ID=<id>` and
`TCW_HOOK_PHASE=prompt`, and the same values in the `hook` object on stdin, so a
script shared between a stage and a procedure can tell them apart.

### The command

`tcw work procedure prompt <id> [slug] [--no-exec]`, added as a new `procedure`
subcommand group so the grammar reads the same as `tcw work stage prompt`.

| Case | Behaviour |
| --- | --- |
| known id, no slug | resolves against the local work node with no item; exit 0 |
| known id, slug | the slug goes through the same `_resolve` a stage prompt uses (`tcw/work/cli.py:130`), so `<project-id>/<slug>` reads that node's `work.procedures`; `when:` can match the item; `generate:` gets it on stdin |
| unknown id | `tcw work procedure prompt: unknown procedure '<id>'; expected one of …` on stderr, exit 1, nothing on stdout |
| slug that matches no item | `tcw work procedure prompt: no such work item: <slug>`, exit 1 |
| slug matching several | the `MultipleMatch` message, exit 1 |
| outside a work node | the same refusal `tcw work stage prompt` gives, exit 1 |
| a binding fails to resolve | `tcw work procedure prompt: <reason>`, exit 1, nothing on stdout |
| `--no-exec` | the binding plan on stderr, nothing resolved, nothing on stdout, exit 0 |

stdout carries the composed text and nothing else, written once after
everything that could fail has succeeded — the stream discipline of
`_stage_tail` (`tcw/work/cli.py:1263-1323`).

**No bookend.** `tcw work stage prompt` wraps its text in a header and footer
(`bookend`, `tcw/work/resolve.py:386-426`), but both halves are about the stage
ladder: the header names the `gate` command to run first and the footer names the
next stage. A procedure has neither a gate nor a next stage, so there is nothing
for either to say. Printing the text unwrapped is also what lets a test compare a
default with its source file byte-for-byte.

**No harness detection.** `tcw work stage prompt` does none either; detection
lives only in `tcw work stage validate` (`tcw/work/cli.py:1528-1550`), which prints
a notice that injected lines must be run by hand. Every reader of
`procedure prompt` output gets the same text under every harness, because an
injected line inside *resolved output* is not run by Claude either. A converted
skill's own manual fallback block is where a Codex reader is told to run the
command, and that belongs to the children converting skills.

No status note: a procedure has no status it is legal in.

### A procedure whose only bindings are conditional, asked without a slug

`Condition.matches` answers false when there is no item
(`tcw/store/base.py:981-997`). So a project that writes only conditional bindings
for a procedure, then asks for it without a slug, gets **nothing** — not TCW's
default. That is the resolver's rule for stages too: the floor applies to a
procedure with no bindings, not to one whose bindings did not match, because a
project that configured a procedure has taken it over.

**The rule is kept, and made visible.** Changing it only for procedures would
give one resolver two answers to "when does `builtin` apply", which is the drift
the epic exists to remove; a project wanting a fallback writes an unconditional
`builtin: true` or `blob:` last. But for a procedure an empty result matters more
than for a stage, because a converted skill will read nothing and carry on. So
when the composed text is empty **and** at least one binding was skipped by its
condition, the command prints a note on stderr and still exits 0 with empty
stdout:

```
tcw work procedure prompt: note — every binding for 'search' carries a when: that did not match, so nothing resolved. Without a work item a when: never matches; add an unconditional binding (for example {builtin: true}) to cover that case.
```

The second sentence appears only when no slug was given. A procedure silenced
with `[{blob: ""}]` skips no binding and prints no note.

## Acceptance criteria

The epic's criteria 4, 5, 6 and 7, made concrete, then this child's own.

1. *(epic 4)* In a work node whose `tcw-config.yaml` has no `work.procedures`,
   `tcw work procedure prompt <id>` exits 0 for **every** id in `PROCEDURE_IDS`
   and prints exactly the contents of `tcw/work/procedures/<id>.md`, with trailing
   whitespace removed.
2. For every id, the shipped default equals the source it was copied from — the
   skill body after its frontmatter, or the reference document — once leading and
   trailing whitespace is removed from both. A test asserts it for all ten.
3. *(epic 5)* With `work.procedures.<id>: [{blob: A}, {builtin: true}, {blob: B}]`,
   the command prints `A`, then the default text, then `B`, separated by one blank
   line each, in that order; with only `[{blob: A}]` it prints `A` and no default
   text.
4. With a slug: a binding with `when: {tags: [bug]}` resolves for an item tagged
   `bug` and is skipped for one that is not; a `generate:` binding's script
   receives that item's JSON on stdin with `hook.role == "procedure"` and
   `hook.id == <id>`, and `TCW_HOOK_ROLE=procedure` in its environment.
5. Without a slug, a procedure whose only binding is conditional prints nothing on
   stdout, exits 0, and prints on stderr the note naming the procedure and saying
   a `when:` never matches without a work item.
6. An unknown id, an unknown slug, and a `file:` binding whose file was deleted
   after validation each exit 1 with nothing on stdout and a message on stderr
   naming the id, the slug, or the file respectively.
7. `--no-exec` prints nothing on stdout, runs no `generate:` script (a script that
   would create a file creates none), and lists each binding with `matched` or
   `skipped (condition)` on stderr.
8. *(epic 6)* `tcw validate` exits non-zero and names the offending location for
   each of: `work.procedures` not a mapping; an unknown procedure id (naming the
   known ones); an id whose value is not a list; an empty list; a bare string
   binding; a blank `file:`; the same binding twice; `command:` (naming
   `generate:`); a malformed `when:`; a `file:` that does not exist or resolves
   outside the node. A valid `work.procedures` block adds no problem.
9. *(epic 7)* Removing any one id's default file, or emptying it, makes
   `load_builtins()` raise `ResolveError` naming that id and the file.
10. The default files are inside the built wheel, checked the way
    `tests/test_shipped_prompts.py` checks the stage prompts.
11. A config with a malformed `work.procedures` block does not break
    `tcw work list` or `tcw work stage prompt`: problems are discarded outside
    `tcw validate`, as for `work.lifecycle`.
12. `pytest` passes, run bare from the repository root.
13. `tcw capabilities check` exits 0 with `work/run-a-procedure` and
    `work/configure-procedures` present, and the item's `capabilities.yaml`
    records the three deltas above.

## Risks

- **Ten copies of skill text now live in two places** until the conversion
  children land. The parity test (criterion 2) turns a silent drift into a
  failing test, at the cost of a skill edit elsewhere needing a matching edit in
  `tcw/work/procedures/`. That cost ends as each conversion child makes the skill
  read the command instead.
- **Verbatim defaults carry skill-relative wording.** Some bodies link to files
  by paths relative to the skill folder (`references/…`) or say "this skill".
  Printed by a CLI they read slightly out of place. That is today's text and the
  conversion children decide how their skill's default should read; this child
  does not edit it.
- **`post-mortem` beside the stage `postmortem`.** Two ids a hyphen apart, in
  different keys. The procedure id follows the artifact name `post-mortem.md`;
  `tcw validate` names the known ids when either is misspelled in the wrong
  place, so a mix-up is reported rather than silent.
- **`LifecyclePolicy` now holds something that is not lifecycle.** Accepted to
  avoid a second policy object and a second abstract method for the same kind of
  read; the class docstring already says "a node's configured bindings".
- **An empty result is still possible** (conditional-only bindings without a
  slug). The stderr note makes it visible; it does not make it impossible, by
  design.

## Notes

- **Stage gate not run.** `tcw work stage gate spec <slug>` refused — "'spec' is
  not legal for an item in 'active'; it runs in backlog" — because the
  coordinating session started the item before planning, and the requester chose
  to proceed without moving it back. The spec prompt was read with
  `tcw work stage prompt spec <slug>` and followed.
- **Nothing was skipped by not running that gate.** `tcw work lifecycle` shows
  the `spec` stage has only `bind:` entries (`builtin`, `abstraction.md`,
  `harness.md`) and no `pre:` check, so the refused gate would have run the status
  legality check alone.
- **The `tcw` CLI is not driving this item's lifecycle.** This item edits `tcw/`,
  so per `CLAUDE.md` the work folder is maintained by hand; only read-only `tcw`
  commands were run, and before any `tcw/` edit.
- **Decisions for the requester to confirm:**
  1. The id list and names above — especially `unattended-work` for
     `tcw-extras-autonomous-work`, `create-work` for
     `tcw-work-create`, `post-mortem` for `tcw-post-mortem`, and the unprefixed
     `search`.
  2. Defaults are verbatim copies now, guarded by a parity test, rather than
     placeholders.
  3. A plain list per id, not a `prompt:` sub-key.
  4. No header/footer and no harness notice in `procedure prompt` output.
  5. Conditional-only bindings without a slug keep the stage rule (resolve to
     nothing) with an added stderr note, rather than falling back to the default.
  6. Procedure `generate:` scripts share `work.lifecycle.timeout` and
     `output-cap`, and see `TCW_HOOK_ROLE=procedure`.
- **Where the epic is out of date.** Its line citations into `resolve.py` have
  moved (`load_builtins` is now `:47-81`, `_resolve_one` `:186-215`). Its
  intake says the command's "output adapts to the harness using the detection
  `tcw work stage validate` already has" — but `stage prompt`, the verb being
  mirrored, has no harness adaptation, and the requester has since ruled out a
  `procedure validate`. Its spec also says a procedure "is not item-scoped, which
  is also why it needs no gate"; the requester later made the item optional, so a
  procedure may be item-scoped — it still needs no gate, because it has no status
  legality. And it says the `timeout`/`output-cap` limits are reused without
  noting they live under `work.lifecycle`, so a project that configures only
  procedures still sets its limits there.
- The `tcw-work` skill body is 59 lines against a budget of 60
  (`tests/test_skill_lifecycle_parity.py:50`), so the new verb is documented in
  `references/commands.md` and `references/hooks.md`, not in `SKILL.md`.
- **Changed during `implement`: `autonomous-work` became `unattended-work`.**
  The spec first used the requester's example id `autonomous-work`, but that is
  a skill name TCW removed, and `tests/test_skill_lifecycle_parity.py`
  (`DELETED_NAMES`) refuses any live document naming it — so every place this
  id is documented would have failed that guard. A user-level skill called
  `autonomous-work` also exists on the requester's machine. A procedure id that
  reads as a skill name is the confusion the id rule exists to avoid, so the id
  was renamed rather than the guard loosened.
