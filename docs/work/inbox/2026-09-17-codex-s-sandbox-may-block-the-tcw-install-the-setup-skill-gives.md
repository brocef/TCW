# Codex's sandbox may block the tcw install the setup skill gives

## Desired outcome

A Codex agent following `skills/setup/references/install.md` either succeeds in
installing `tcw`, or is told to ask for the permission the install needs.

## Context

Raised by review and verification of
`2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`, which added
the Codex command `bash "<plugin>/scripts/session_bootstrap.sh" "<plugin>"`.

The script runs `pipx install --force tcw-cli`, which needs network access and writes
outside the workspace. Codex's default sandbox normally blocks both. The script hides
pipx's output and prints only "automatic install of tcw-cli from PyPI failed
(offline?)", and its advice, `pipx install tcw-cli`, fails the same way inside the
sandbox.

## Notes

- **Not observed.** Inferred from Codex's default sandbox settings; nobody ran the
  install under Codex. Confirm first.
