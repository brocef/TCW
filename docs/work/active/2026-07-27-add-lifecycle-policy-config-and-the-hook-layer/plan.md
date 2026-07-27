# Implementation plan

Six ordered tasks, one commit each, suite green at every boundary.

The order follows the data: the model first, then the validation that rejects bad
input, then the read-only surface that displays it, and only then the executor
that acts on it. Nothing runs a configured command until every earlier stage can
prove what it parsed.

## Task 1 — the `LifecyclePolicy` model

Storage-neutral, in `base.py`. No config reading yet.

- `STAGE_IDS = ("inbox", "request", "spec", "plan", "implement", "verify",
  "postmortem")` and `TRANSITION_IDS = ("start", "submit", "complete", "rework",
  "discard")`. **These are public API** — a user's `tcw-config.yaml` keys on
  them, and renaming one later breaks their configuration silently. Cross-check
  `TRANSITION_IDS` against the CLI verbs before committing; they must be the same
  strings.
- `@dataclass Binding` with `skill: str = ""` and `command: str = ""`, exactly
  one non-empty. A `kind` property returning `"skill"` or `"command"` so callers
  branch on a value rather than on which attribute is truthy.
- `@dataclass LifecyclePolicy` with `stages: dict[str, list[Binding]]`,
  `transitions: dict[str, TransitionBindings]`, and `timeout: int = 300`.
  `TransitionBindings` holds `pre` and `post` lists.
- `WorkStore.lifecycle_policy()` abstract; an empty policy is the default and
  must be cheap to produce.
- A **pure parse function**, `parse_lifecycle_policy(raw) -> (policy, problems)`,
  taking the already-loaded mapping and returning both. Pure so `tcw validate`
  and the adapter share exactly one implementation of the rules — two would drift,
  which is the failure this whole epic exists to fix.

**Test:** `tests/test_lifecycle_policy.py` over `parse_lifecycle_policy` alone —
no filesystem. Valid shapes, declaration order preserved, and each of the eleven
rejections from the spec's table with its message naming the offending id.

**Green when:** the parser is fully tested and nothing reads config yet.

## Task 2 — the FS adapter reads `work.lifecycle`

- `FsWorkStore.lifecycle_policy()` reads `work.lifecycle` through the existing
  `_work_config()` and hands it to `parse_lifecycle_policy`, **discarding
  problems**. Reading is not validating: a malformed policy must not break
  `tcw work list`. `tcw validate` is where problems surface.
- Bindings round-trip in declared order. Nothing rewrites the config — this child
  adds no writer, and there is no `tcw work lifecycle set`.

**Tests:** a node with no `work.lifecycle` yields an empty policy; a valid one
round-trips in order; a malformed one yields a partial policy rather than raising;
`registered_tags()` and the 2a policy keys still read correctly alongside it.

## Task 3 — `tcw validate` rejects malformed policy

- `FsWorkStore.check()` appends `parse_lifecycle_policy`'s problems, prefixed so
  the source file is obvious (`tcw-config.yaml: …`).
- **Unrelated config must survive untouched.** Assert it against a config
  carrying a deliberately unsorted set of unrelated keys, read after validation.

`check()` already returns a problem list and `tcw validate` already prints and
counts it, so this task is wiring rather than design.

**Tests:** each rejection surfaces through `tcw validate` with a non-zero exit;
a valid policy exits 0; unrelated keys are byte-identical afterwards.

## Task 4 — `tcw work lifecycle`, human and `--json`

Read-only. Never executes, never writes.

- `tcw work lifecycle [work-ref]` prints every stage and transition id **in
  lifecycle order** with its objective, allowed inputs, required artifact,
  TCW-owned destination path, and configured bindings.
- The objectives and artifact names are a **static table in the model**, not
  prose duplicated from the skill. Child 4 writes the stage documents; this table
  is what those documents must agree with, and having it in one place is what
  makes agreement checkable.
- Without a work ref: the local node's policy. With a local or qualified ref:
  the item's owning node's policy, via `resolve_qualified_work_ref`.
- `--json` emits the same contract.

**Tests:** both modes expose the same ids and bindings; a qualified descendant
resolves its own node's policy, not the anchor's; an unresolvable ref exits
non-zero.

## Task 5 — `--directive`

Small, but the contract is exact and every clause is a test.

```
$ tcw work lifecycle --stage spec --directive
For this stage, invoke the superpowers:brainstorming skill.

$ tcw work lifecycle --stage implement --directive
                                        (unbound: empty stdout, exit 0)
```

- One **complete instruction line or nothing at all** — never a bare value, so an
  unbound id renders as empty rather than as a broken sentence.
- Bound and unbound are both **exit 0**.
- Every error — unreadable config, unknown id, unresolvable work ref — writes
  **nothing to stdout**, a diagnostic to stderr, and exits **non-zero**. A silent
  empty injection must never mask an error.
- `--stage` and `--transition` are mutually exclusive and exactly one is
  required.
- **Never executes a binding.** For a command binding it emits an instruction
  naming the command; running it stays the agent's step.

**Tests:** bound, unbound, all three error paths, a command binding emitting
rather than running, and mutual exclusivity.

## Task 6 — hook execution

Last, because it is the only task that runs anything.

Execution lives in `tcw/work/hooks.py`, called from `work/cli.py` — **not** from
the store. A store method that shells out is one no remote adapter could honor,
and the CLI is where the ordering constraint below can be satisfied.

- `run_hooks(policy, node_root, bindings, env) -> str | None` — runs command
  bindings in declared order, returns the first failure or `None`.
- Working directory is the **node root**, never the process cwd.
- Shell execution, so pipelines and `&&` work.
- Environment inherits the caller's plus `TCW_SLUG`, `TCW_STATUS`,
  `TCW_TRANSITION`, `TCW_NODE_ROOT`.
- Timeout defaults to 300s, from `policy.timeout`. A timeout is a failure.
- **Skill bindings are reported, never executed.** The CLI cannot invoke a skill.

### The ordering constraint, which is the whole risk

`complete()` writes the resolution with `set_field` **before** it moves the item.
A `pre` hook evaluated inside the store would therefore leave a resolution on an
unmoved item when it aborts — an item reading as closed while sitting in
`active`.

So each transition handler in `work/cli.py` runs `pre` hooks **before it calls
the store method at all**, and returns non-zero without touching the store if any
fails. No `WorkStore` change, no transaction concept — the ordering is entirely
within the CLI, which is precisely why execution belongs there.

`post` hooks run after the store call returns. **A `post` failure never rolls
back:** the move and its commit have happened, and unwinding a committed
transition is worse than the failure. Report it, exit non-zero, leave the item
where it moved.

**Tests:**

- A `pre` failure aborts: item unmoved **and no field written** — assert the
  resolution is absent after an aborted `complete`. "Did not move" alone would
  pass a broken implementation.
- Later `pre` hooks do not run after the first failure.
- A `post` failure leaves the item moved and committed, with a non-zero exit.
- cwd is the node root, and all four `TCW_*` variables are visible — assert by
  having the hook write them to a file.
- A hook exceeding the timeout is a failure.
- A skill binding is reported and never executed — assert with a skill ref whose
  name would be a valid command if anything tried to run it.
- `tcw serve` runs no hooks.

## Task 7 — documentation sync

| Entry | Fires | Why |
|---|---|---|
| `README.md` | yes | A new config section and a new read-only command. |
| `docs/release-notes/upcoming.md` | yes | A user-facing feature, though opt-in. |
| `docs/changelogs/upcoming.md` | yes | Code change. |
| `skills/tcw-work/SKILL.md` | yes | Agents must learn to consult bindings. |

Two things the skill must say, and both are easy to state wrongly:

- **Consult `tcw work lifecycle <slug>` for bindings.** That is the
  harness-neutral contract. `--directive` injection is Claude-only sugar, and the
  skill must not present it as the path.
- **A configured-but-missing skill cannot fail closed on Codex**, which cannot
  enumerate skills. The instruction is to report and stop, not to assume a check
  fired.

Also carried from 2a's outcome: **the web complete modal must say hooks did not
run.** `tcw serve` performs the transition without executing bindings, and a
`pre` hook that would block it does not block it there. Same surface as 2a's
deferred item — a refused auto-commit reaching only the server's stderr — so both
land in this task.

## Verification

1. `tcw validate` on this repo.
2. Configure a real binding in a scratch node, run a transition, watch the hook
   fire; make it exit 1 and confirm the item did not move **and has no
   resolution**.
3. `--directive` bound and unbound, checking stdout is empty rather than a
   fragment on the unbound path.
4. Confirm this repo's own `tcw-config.yaml` still validates with no
   `work.lifecycle` at all.

## Rollback

Tasks are independently revertible in reverse order. Task 6 is the only one that
changes what a transition does; reverting it leaves a policy that is read,
validated, and displayed but never acted on — which is a coherent state, not a
broken one.
