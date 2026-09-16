# Route agents to tcw-work-stage for stage instructions and validate its arguments

Agents looking for how to do a lifecycle stage should invoke the `tcw-work-stage`
skill, which composes TCW's stage document with the project's own instructions.
Today they can instead find and open `skills/tcw-work/references/lifecycle/*.md`
directly, which skips the project's instructions. The skill also has no guard
against being invoked with missing or wrong arguments.

What should change:

1. **Hide the stage documents.** `skills/tcw-work/SKILL.md`, and the reference
   documents under `skills/tcw-work/references` that it links to, must not link
   to or name the files in `skills/tcw-work/references/lifecycle/`, so an agent
   cannot discover them by following the skill.
2. **Point at the stage skill, with emphasis.** Add an emphasized note to
   `skills/tcw-work/SKILL.md`: an agent looking for instructions on *how* to
   perform a particular stage (the instructional prompt for that stage) must
   invoke the `tcw-work-stage` skill with the correct arguments.
3. **Validate the stage skill's arguments.** Add a new command,
   `tcw work stage prompt validate $stage $item`, injected very early in
   `skills/tcw-work-stage/SKILL.md` (right after the frontmatter, under a
   "(Claude-only) Skill invocation validation" heading):
   - stage and item present and valid → prints nothing;
   - either or both missing or invalid → prints a Markdown usage error, e.g.
     **Skill Invocation Error: The tcw-work-stage skill must be invoked with one
     to two arguments: `tcw-work-stage stage-id [work-slug]`**
4. **Adapt the message to the agent harness.** Use environment variables to tell
   which harness ran the command: `CLAUDE_CODE_SESSION_ID` for Claude Code,
   `CODEX_SESSION_ID` for Codex. Dynamic context injection (the `` !`command` ``
   lines a skill runs at load time) is a Claude Code feature, so under another
   harness emit a different message, e.g. "Your AI agent harness does not support
   dynamic context injection. You will need to manually run all commands with
   !`command` to interpret this skill."

## Origin

Chat request from the user on 2026-09-16, after confirming that
`skills/tcw-work-stage/SKILL.md` still injects the stage documents while the five
per-stage skills were deleted in `a0cb1848`.

## References

- https://code.claude.com/docs/en/skills.md — Claude Code skills reference: argument substitution and dynamic context injection syntax.
- https://code.claude.com/docs/en/env-vars.md — Claude Code environment variables, including the session id variable used to detect the harness.
- https://learn.chatgpt.com/docs/config-file/environment-variables.md — Codex environment variables, including `CODEX_SESSION_ID`.
- `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names` — related: renames `tcw-work-stage` to `work-stage`, so whichever lands second updates the other's names.
- `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability` — related: edits `tcw-work-stage`'s manual fallback for Codex.
- `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings` — related: the eval harness measures whether injection reached the agent; a new injection line may affect its parity guard.
