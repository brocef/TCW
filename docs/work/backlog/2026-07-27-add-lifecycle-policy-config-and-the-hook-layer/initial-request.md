# Add lifecycle policy config and the hook layer

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

**The configuration half of the original child 2**, split out because it shares
no code with the behavior half. Depends on child 1 for the transition ids it
binds to.

Owns the schema, its validation, its inspection surface, and the contract for
executing what it declares. Changes no transition behavior.

## Scope

- **`LifecyclePolicy` + `WorkStore.lifecycle_policy()`** — storage-neutral; the
  FS adapter reads node-local `work.lifecycle` from `tcw-config.yaml`, following
  the `registered_tags()` pattern.
- Keyed by the epic's **fixed ids**. Stages: `inbox`, `request`, `spec`, `plan`,
  `implement`, `verify`, `postmortem`. Transitions: `start`, `submit`,
  `complete`, `rework`, `discard`.
- A binding is **`{skill: <ref>}` or `{command: <shell>}`, declared, never
  inferred from a bare string.** Neither key or both keys fails validation.
  Declaration order is significant and round-trips unchanged.
- **`tcw validate` rejects eleven distinct malformed shapes**, each with a
  message naming the offending id, and never reorders bindings or disturbs
  unrelated config keys.
- **The hook execution contract:** node-root cwd; shell execution; environment
  inheriting the caller's plus `TCW_SLUG`, `TCW_STATUS`, `TCW_TRANSITION`,
  `TCW_NODE_ROOT`; a 300s default timeout; `pre` hooks running in declared order
  with the first non-zero exit aborting; **a failing `post` hook never rolling
  back** — TCW reports it and exits non-zero, and the item stays where it moved.
- **`pre` hooks run before the store is touched at all.** `complete()` writes the
  resolution before it moves the item, so a hook evaluated inside it would leave
  a resolution on an unmoved item. Execution therefore lives in the CLI, which
  controls the ordering — no `WorkStore` change and no transaction concept.
- **Skill bindings are reported, never executed.** The CLI cannot invoke a skill;
  only the agent can.
- **`tcw work lifecycle [work-ref]`** in three modes: human, `--json`, and
  `--directive`. `--directive` emits **one complete instruction or nothing at
  all** — never a fragment — exits 0 for both bound and unbound, and on every
  error path writes nothing to stdout, a diagnostic to stderr, and exits
  non-zero. It never executes a binding.

## Done when

- A node with no `work.lifecycle` behaves exactly as it does today.
- A valid policy round-trips in declared order with unrelated config untouched.
- Every rejected shape has a test and an actionable message.
- A qualified descendant item resolves its own node's policy, not the anchor's.
- `--directive` emits one complete instruction or nothing, exits 0 for both, and
  exits non-zero with empty stdout on every error.
- A `pre` hook exiting non-zero aborts the transition, the item does not move,
  **and no field was written**.
- A `post` hook exiting non-zero leaves the item moved and committed while `tcw`
  exits non-zero.
- A hook runs with cwd at the node root and sees all four `TCW_*` variables; a
  hook exceeding the timeout is treated as a failure.
- A skill binding is reported and never executed.

## Notes

**`tcw serve` runs no hooks**, and this is an accepted asymmetry rather than an
oversight: the same action has different side effects depending on the surface.
Running configured shell from an HTTP handler on a button click is a
meaningfully worse posture than a CLI the user invoked deliberately. But it is a
real gap — a `pre` hook that would block a transition does not block it from the
web app — so the web-complete modal must say hooks did not run rather than
leaving the user to infer it.

**Skill bindings cannot fail closed on Codex**, which cannot enumerate skills to
check one exists. Nothing may depend on that check firing. This is the assumption
most likely to be quietly reintroduced.

The config lives in the user's own repository and is trusted exactly as much as
any other file there. This is stated so nobody mistakes it for a sandbox.
