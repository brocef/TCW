# Delegation

**This page holds only the part of this procedure a project cannot replace.**
For the rest, run `tcw work procedure prompt delegation` and follow what it
prints: this project's text if it configured one, TCW's own otherwise. The rules
on this page hold whatever it prints. If the command fails, say so rather than
working from memory.

**Stages are delegable to a subagent. Transitions never are.** A transition
carries the gates, and those are evaluated once, by the session that holds the
user relationship and the primary checkout.

| Stage                                     | Delegable        |
| ----------------------------------------- | ---------------- |
| `inbox`, `request`, `verify`              | no — interactive |
| `spec`, `plan`, `implement`, `postmortem` | yes              |

`request` and `verify` are excluded for a different reason than transitions: a
subagent cannot ask the user, and both stages exist to obtain user input.

`verify` is non-delegable because it _ends_ in a user decision, not because all
of its work is interactive. Its **assessment** — reading the diff, running
checks, forming an opinion — is delegable read-only work; its **approval** is
not. Dispatch the assessment, present the result, hold the answer yourself.

## Delegable means permitted, never required

Both harnesses TCW ships to have subagents, so a stage's instructions may instruct delegation
outright. A session that cannot dispatch — or should not, because the work is too
coupled to split — runs the same stage in the main session, following the same
instructions. Delegation is an optimization for context isolation. **No behavior
depends on it**, and where it is unavailable only the token saving is lost.

## Custom agents

A custom agent earns its place only when it needs a different tool set or model
than the default; otherwise the stage, as the `work-stage` skill delivers it, is already the brief. That test
passes three times, all read-only: `verifier` for the `verify` stage's
assessment, `post-mortem` for `postmortem`, and `backlog-auditor` for the
per-item half of [`audit-backlog.md`](audit-backlog.md).

A read-only tool set is the strongest reason to define one — but be precise about
how much it buys. Withholding `Write`/`Edit` genuinely removes the ability to
change a file. It does **not** make an agent read-only, because all three of
these need `Bash` to do their job at all, and `Bash` can write. So the tool set
narrows the blast radius; the agent's own hard limits carry the rest. Say that in
the agent, rather than claiming a guarantee the tool set does not give.

The `agents/` directory is Claude Code packaging — another harness defines its
agents in its own format — so all three are **accelerators only**. Every document
they serve stands alone without them.
