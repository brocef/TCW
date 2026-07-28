# Delegation

**Stages are delegable to a subagent. Transitions never are.** A transition
carries the gates, and those are evaluated once, by the session that holds the
user relationship and the primary checkout.

| Stage | Delegable |
|---|---|
| `inbox`, `request`, `verify` | no — interactive |
| `spec`, `plan`, `implement`, `postmortem` | yes |

`request` and `verify` are excluded for a different reason than transitions: a
subagent cannot ask the user, and both stages exist to obtain user input.

`verify` is non-delegable because it *ends* in a user decision, not because all
of its work is interactive. Its **assessment** — reading the diff, running
checks, forming an opinion — is delegable read-only work; its **approval** is
not. Dispatch the assessment, present the result, hold the answer yourself.

## Delegable means permitted, never required

A harness without subagents — Codex has none — runs the same stage in the main
session, following the same document. Delegation is an optimization for context
isolation. **No behavior depends on it**, and where it is unavailable only the
token saving is lost.

## What makes it correct

- **`Inputs` is the subagent's context brief.** The section that exists for token
  efficiency is the same one that makes delegation safe.
- **`Produce` is the return contract**, and must be specific enough to check. A
  subagent returning "done" gives the coordinating session nothing.
- **The coordinating session re-reads the artifact.** Isolation is not free, and
  pretending otherwise is how a delegated stage ships unverified. The win is
  reading a few hundred lines instead of a multi-thousand-line transcript — large,
  but not total. Where `Produce` names required sections, the check can be
  structural rather than a full read.
- **A subagent's context is discarded when it returns.** Everything it noticed and
  did not write down is lost. `## Notes` is the only channel for the part of that
  knowledge with no home in the required sections.

If a delegated stage fails to produce its artifact, that is a `[judgment]`
failure caught by the coordinating session, not a `[gated]` one — no transition
was attempted, so nothing refused. Check `Produce`, then re-dispatch or escalate.

## The shape this produces

The main session becomes a coordinator: it owns the transitions and the two
interactive stages, and dispatches the rest. `implement` is the largest token
sink and the most valuable delegation.

## Custom agents

A custom agent earns its place only when it needs a different tool set or model
than the default; otherwise the stage document is already the brief. That test
passes twice, both read-only: `tcw-verifier` for the `verify` stage's assessment,
and `tcw-post-mortem` for `postmortem`.

Codex has no custom agents, so both are **accelerators only**. Every stage
document stands alone without them.
