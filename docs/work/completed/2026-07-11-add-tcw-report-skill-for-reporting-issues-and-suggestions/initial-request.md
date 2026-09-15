# Add tcw-report skill for reporting issues and suggestions

Give TCW users a skill that teaches them how to report issues or suggestions
back to the TCW project, by filing a GitHub issue on the TCW repository, and
hand them a small skeleton for what each kind of issue should contain.

## Product changes

- New `tcw-report` skill (agent-facing). No `tcw` CLI surface change — reporting
  targets the upstream TCW GitHub repo, not the local store, so nothing here
  belongs in the store interface (litmus test: this is not a store operation at
  all, it is guidance for talking to GitHub).

## Technical changes

- `skills/tcw-report/SKILL.md` — a thin, mostly-always-relevant router. Keep it
  inline (no `references/` split — the whole thing is short and always relevant).
- Point at `https://github.com/brocef/TCW/issues`.
- Provide two skeletons:
  - **Bug:** environment, steps to reproduce, expected vs actual, remediation.
  - **Suggestion / feature:** motivation, description, benefits.
- Tell reporters to search existing issues first to avoid duplicates.

## Meta changes

- Add `tcw-report` to the `tcw-plugin` skill map so it is discoverable.
- Documentation sync: README (mention how to report issues) and the developer
  changelog / release notes upcoming entries.
