<!-- Bound to the `spec` and `implement` stages of `tcw work`; see `tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# Harness compatibility (Claude and Codex)

_Applies at `spec`, where a mechanism is chosen, and again at `implement`, where
it is built. A requirement carried only by a Claude-only mechanism is a
requirement a Codex user does not get._

TCW ships to **both** Claude Code and Codex, and their plugin standards differ: Claude's system is far richer, while Codex follows the [Agentskills specification](https://agentskills.io/specification.md). Both are first-class targets — a task a Claude user can accomplish, a Codex user must also be able to accomplish.

**Claude-only features are welcome as _enhancements_, never as the sole carrier of a requirement.** Dynamic context injection (`` !`cmd` ``), skill/command arguments, and hooks are Claude-only; their syntax is inert in Codex rather than fatal, so using them does not break a skill. That makes them safe to reach for — but only for ergonomics.

**Subagents are _not_ Claude-only.** Codex has them too — TOML agent definitions in `.codex/agents/`, model-driven spawning, parallel execution capped by `[agents] max_concurrent_threads_per_session` — and it "respects applicable `AGENTS.md` or skill instructions that request delegation" ([docs](https://learn.chatgpt.com/docs/agent-configuration/subagents)). So a skill may instruct delegation directly without a single-session fallback. The `agents/` **directory** is still Claude-specific packaging, which keeps the usual rule intact: a custom agent is an accelerator, and the skill document it accelerates must stand alone.

The rule that follows: **anything that must be guaranteed belongs in the `tcw` CLI**, which behaves identically under both harnesses. If a behavior only happens because Claude injected a line of context or fired a hook, a Codex user does not get it. Ask of every mechanism: _what does a Codex agent see here, and can it still finish the job?_ If the answer is no, the requirement is in the wrong layer.

Codex has no slash commands, so anything reachable via `commands/` must also be reachable by invoking the skill directly (the `tcw-plugin` skill is the existing pattern).
