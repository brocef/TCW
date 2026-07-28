# Specification

The **configuration half** of the original child 2, split because it shares no
code with the behavior half. Sibling:
[Commit every work transition; trunk-branch and DoD cleanup](tcw://W/2026-07-27-commit-every-work-transition-trunk-branch-and-dod-cleanup).
Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks).

The design below was written and reviewed as one document before the split; the
sections are carried over unchanged rather than rewritten, so the review that
produced them still applies.

This child changes **no transition behavior**. It adds a schema, its validation,
its inspection surface, and the contract for executing what it declares.

## Capability changes

- **New:** configure the work lifecycle; inspect the effective lifecycle
  contract.

## Current state

- The node config pattern is established: `_config()` (`fs.py:1860`) reads the
  `tcw-config.yaml` sentinel tolerantly and raises a path-naming error on
  malformed YAML; `_write_tags` (`fs.py:1879`) shows the read-modify-write that
  preserves unrelated keys. `work.lifecycle` follows both.
- The transition ids this binds to — `start`, `submit`, `complete`, `rework`,
  `discard` — are exactly the CLI verbs child 1 finished establishing.
- `complete()` writes the resolution via `set_field` **before** it calls
  `transition()` (`base.py:1025`). That ordering is what forces hook execution
  into the CLI rather than the store; see below.
- Nothing in `tcw/` executes a configured subprocess today. This child
  introduces that capability, so its trust model has to be stated rather than
  assumed.

## Design

### `LifecyclePolicy`

A storage-neutral model plus `WorkStore.lifecycle_policy()`. The FS adapter
reads node-local config:

```yaml
work:
    lifecycle:
        stages:
            spec: [{skill: superpowers:brainstorming}]
            plan: [{skill: superpowers:writing-plans}]
        transitions:
            complete:
                pre: [{command: "pytest -q"}]
                post: [{command: "./notify.sh"}]
```

Keyed by the epic's fixed ids. Stages: `inbox`, `request`, `spec`, `plan`,
`implement`, `verify`, `postmortem`. Transitions: `start`, `submit`, `complete`,
`rework`, `discard`.

A binding is `{skill: <ref>}` **or** `{command: <shell>}`, never a bare string.
Neither key or both keys is a validation error. Guessing which a bare string
meant is a class of bug bought for nothing.

Declaration order is significant and must round-trip unchanged.

### `tcw validate` rejections

Each needs a test and a message naming the offending key:

| Rejected | Message must name |
|---|---|
| unknown stage or transition id | the id, and the legal set |
| `work.lifecycle` not a mapping | the key and the found type |
| `stages`/`transitions` not a mapping | the key |
| a stage value that is not a list | the stage id |
| a transition value that is not a mapping of `pre`/`post` | the transition id |
| `pre`/`post` not a list | the transition id and which phase |
| a binding that is not a mapping | the id and the position |
| a binding with neither `skill` nor `command` | the id and the position |
| a binding with both | the id and the position |
| a blank ref | the id and the position |
| a duplicate ref within one id | the id and the ref |

Validation must not reorder bindings or disturb unrelated `tcw-config.yaml`
keys. That is asserted by round-tripping a config with a deliberately unsorted,
comment-free set of unrelated keys.

### Hook execution

**Execution lives in the CLI, not the store.** The store owns the *policy* — a
Jira adapter could serve the same mapping. Running a shell command is a local
concern, and a store method that shells out would be one no remote adapter could
honor.

This has a consequence worth stating rather than discovering: **`tcw serve` does
not run hooks.** A status changed by clicking a button in the web app performs
the transition and its commit, and runs no configured command. Executing
arbitrary shell from an HTTP handler on a click is not a behavior to add by
accident, and the web app is a viewer/editor, not an automation surface.

**This is an accepted asymmetry, not an oversight:** the same user action has
different side effects depending on which surface performs it. It is the right
trade — a locally-served HTTP endpoint that runs configured shell on request is a
meaningfully worse security posture than a CLI the user invoked deliberately —
but it is a real gap, and the web-complete modal should say that hooks did not
run rather than leaving the user to infer it. Documenting it is part of criterion
23; a `pre` hook that would have *blocked* a transition does not block it from
the web app.

For CLI transitions:

- **Working directory** is the node root — the directory holding
  `tcw-config.yaml`. Never the process cwd.
- **Commands run through the shell**, so pipelines and `&&` work. The config
  lives in the user's own repository and is trusted exactly as much as any other
  file there. This is stated so nobody mistakes it for a sandbox.
- **Environment** inherits the caller's, plus `TCW_SLUG`, `TCW_STATUS`,
  `TCW_TRANSITION`, `TCW_NODE_ROOT`.
- **Timeout** defaults to 300s per command, configurable via
  `work.lifecycle.timeout`. A timeout is a failure, and on a `pre` hook it
  aborts.
- **`pre` hooks run in declared order; the first non-zero exit aborts the
  transition.** Remaining hooks do not run and the item does not move.
- **A failing `post` hook never rolls back.** The move and its commit have
  happened; unwinding a committed transition is worse than the failure. TCW
  reports it and exits non-zero so a caller notices, and the item stays where it
  moved to. The exit code is the only signal — this must be tested, because
  "reports the failure but succeeded anyway" is the kind of thing that silently
  regresses to a swallowed exception.
- **Skill bindings are never executed by the CLI.** It cannot invoke a skill;
  only the agent can. A skill binding is reported, never run.
- **TCW waits for the command and nothing more.** If a hook backgrounds a
  process, TCW does not track, wait on, or kill it; the timeout applies to the
  command TCW launched. Reaping stray grandchildren is the hook author's
  problem, and pretending otherwise would mean process-group management for a
  case that has not come up.

#### `pre` hooks run before the store is touched at all

This is an **ordering constraint on the CLI**, and it is the one place the hook
layer can corrupt state if implemented casually. `complete()` writes the
resolution with `set_field` *before* it calls `transition()`. If a `pre` hook ran
inside `complete()`, an aborting hook would leave the item unmoved but already
carrying a resolution — an item that reads as closed while sitting in `active`.

So: the CLI evaluates every `pre` hook for a transition, and only if all of them
pass does it call the store method at all. No `WorkStore` interface change and no
transaction concept is needed — the ordering is entirely within the CLI's
control, which is precisely why hook execution lives there.

Acceptance criterion 15 asserts the item's *fields* as well as its status after
an aborted `complete`, because "did not move" alone would pass even if the
resolution had been written.

**What is deliberately not solved:** a crash, `SIGKILL`, or disk failure
*between* the store's own `set_field` and `_effect_transition` still leaves a
resolution on an unmoved item. That window exists today, is not created by this
change, and closing it needs transactional multi-file writes in the FS store —
which is already tracked as
[Transactional multi-file writes in the Fs store](tcw://W/2026-07-03-transactional-multi-file-writes-in-the-fs-store).
This child must not grow into that.

### `tcw work lifecycle [work-ref]`

Read-only. Never executes, never changes state.

- **Human** (default): every id in lifecycle order with its objective, allowed
  inputs, required artifact, TCW-owned destination path, and configured bindings.
- **`--json`**: the same contract, stable enough for tooling and tests.
- **`--directive [--stage <id> | --transition <id>]`**: for Claude's dynamic
  context injection. Emits **one complete instruction line or nothing at all** —
  never a bare value — so an unbound id renders as empty rather than as a broken
  sentence.

```
$ tcw work lifecycle --stage spec --directive
For this stage, invoke the superpowers:brainstorming skill.

$ tcw work lifecycle --stage implement --directive
                                    (unbound: empty, exit 0)
```

Bound and unbound are **both success** (exit 0). Failure is distinguishable: on
an unreadable config, an unknown id, or an unresolvable work reference,
`--directive` writes **nothing to stdout**, a diagnostic to stderr, and exits
non-zero. A silent empty injection must never mask an error.

`--directive` never executes a binding. For a command binding it emits an
instruction naming the command; running it stays the agent's step.

Without a work reference it reports the local node's policy. With a local or
qualified reference it resolves the item's owning node and reports that node's
policy — so a qualified descendant uses its own configuration.

## Out of scope

- Any new status or transition — child 1 shipped those.
- **Auto-commit, `trunk-branch`, `dod:` removal, and `--already-integrated`** —
  the sibling child owns all four. This child neither commits nor changes what a
  transition does.
- What a methodology *document* contains, and `tcw work methodology` — child 3.
  This child ships the binding **mechanism**; child 3 ships resolution on top of
  it.
- Stage documents, the skill restructure, and commands — child 4.
- A repo-local `docs/work/lifecycle/<stage>.md` override or any
  `bare-wins-local` resolution tiering. Those slot in ahead of a configured
  binding later without changing this schema.
- Built-in methodology presets. A Superpowers-style workflow may be documented
  as an example, but must not become a maintained preset.

## Acceptance criteria

1. A node with no `work.lifecycle` behaves exactly as it does today.
2. A valid policy round-trips in declared order, with unrelated
   `tcw-config.yaml` keys untouched — asserted against a config carrying a
   deliberately unsorted set of unrelated keys.
3. Every row of the rejection table has a test whose message names the
   offending id.
4. `tcw work lifecycle` and `--json` expose the same contract.
5. `--directive` emits one complete instruction when bound, empty when unbound,
   exit 0 for both; and on every error path — unreadable config, unknown id,
   unresolvable work reference — exits non-zero with empty stdout and stderr
   output.
6. `--directive` never executes a binding, including a command binding.
7. A qualified descendant item resolves its own node's policy, not the
   anchor's.
8. A `pre` hook exiting non-zero aborts the transition, the item does not move,
   **and no field was written** — an aborted `complete` leaves no `resolution`
   on the item. Later `pre` hooks do not run.
9. A `post` hook exiting non-zero leaves the item moved and committed, and
   `tcw` exits non-zero.
10. A hook runs with cwd at the node root and sees all four `TCW_*` variables.
11. A hook exceeding the timeout is treated as a failure.
12. A skill binding is reported and never executed.
13. `tcw serve` runs no hooks, and its complete modal says so.
14. README, release notes, changelog, and `skills/tcw-work/SKILL.md` describe the
    shipped behavior.

## Risks

- **The `pre`-abort ordering is the one place this can corrupt state.** Running a
  hook inside `complete()` rather than before it would leave a resolution on an
  unmoved item. Criterion 8 asserts fields as well as status, because "did not
  move" alone would pass a broken implementation.
- **Skill bindings cannot fail closed on Codex**, which cannot enumerate skills.
  Nothing may depend on that check firing. This is the assumption most likely to
  be quietly reintroduced.
- **Config-driven shell execution is new to TCW.** The trust model — the config
  is a file in the user's own repository, trusted exactly as much as any other
  file there — must be documented, not implied.
- **Id stability.** Once released, renaming a stage or transition id breaks user
  configuration. The set should be reviewed hard before it ships.

## Notes

The `--directive` mode exists for Claude's dynamic context injection, which Codex
does not have. Per the harness-compatibility rule in `AGENTS.md` it is therefore
an **accelerator only**: `tcw work lifecycle <slug>` is the contract both
harnesses can run, and injection is sugar on top. Child 3 makes this concrete by
giving every stage document one harness-neutral command to run.
