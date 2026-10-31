<!-- Bound to the `spec` and `implement` stages of `tcw work`; see `.tcw/tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# Harness compatibility (Claude Code, Codex, and Pi)

_Applies at `spec`, where a mechanism is chosen, and again at `implement`, where
it is built. A requirement carried only by a Claude-only mechanism is a
requirement a Codex or Pi user does not get._

TCW ships shared skills to Claude Code, Codex, and Pi. Their packaging differs:
Claude and Codex use their existing plugin manifests, while Pi uses the `pi`
resource declaration in `package.json`. All three load the same `skills/` tree.
Required lifecycle behavior must be accessible in each harness. Claude's plugin
system is the richest of the three; Codex follows the
[Agentskills specification](https://agentskills.io/specification.md).

**Claude-only features are welcome as _enhancements_, never as the sole carrier of a requirement.** Dynamic context injection (`` !`cmd` ``), skill/command arguments, and Claude Code's own hooks (the harness's, not TCW's `pre` and `post` hooks) are Claude-only; their syntax is inert in Codex and Pi rather than fatal, so using them does not break a skill. That makes them safe to reach for — but only for ergonomics. Keep explicit command fallbacks in the skills, using the actual skill path to locate the plugin root. Pi invokes skills as `/skill:<name>`; Claude and Codex keep their own invocation syntax. Where a harness does not substitute a skill's argument placeholders, use the task text the user supplied.

**Subagents are _not_ Claude-only.** Codex has them too — TOML agent definitions in `.codex/agents/`, model-driven spawning, parallel execution capped by `[agents] max_concurrent_threads_per_session` — and it "respects applicable `AGENTS.md` or skill instructions that request delegation" ([docs](https://learn.chatgpt.com/docs/agent-configuration/subagents)). So a skill may instruct delegation directly, as long as it also says what a session that cannot delegate does: a Pi session without a delegation tool runs the stage itself (below), and a subagent is permitted, never required: a session that cannot dispatch runs the same stage itself (the `work` skill's [Rules no project text changes](../../skills/work/SKILL.md#rules-no-project-text-changes)). The `agents/` **directory** is still Claude-specific packaging, which keeps the usual rule intact: a custom agent is an accelerator, and the skill document it accelerates must stand alone.

When a Pi session has no delegation tool, run ordinary lifecycle stages inline
with the same gates and instructions. Do not pretend that an inline review is
an independent advisor: `extras-autonomous-work` still requires its configured
advisors. TCW does not install Claude's `agents/` files as Pi agents.

The rule that follows: **anything that must be guaranteed belongs in the `tcw`
CLI**, which behaves identically under all three harnesses. Ask of every
mechanism: _what do Codex and Pi see here, and can they still finish the job?_
If not, the requirement is in the wrong layer.

This plugin ships no separate slash-command files. Every entry point is a
skill, which all three harnesses can invoke.
