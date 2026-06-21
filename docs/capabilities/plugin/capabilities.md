# Plugin — capabilities

## Install as a plugin
**Status:** Supported
**Subject:** cli

As a user, I add the tcw marketplace and run `/plugin install tcw` (Claude Code) or `codex plugin add tcw@tcw` (Codex) to install the tcw skills as a plugin.

## Bootstrap the CLI
**Status:** Supported
**Subject:** cli

As a user, I run `/tcw-init` (or, in Codex, ask the agent to run the `tcw-plugin` setup) to install the `tcw` CLI from the plugin's own clone via pipx, so the command is on my PATH without a separate manual install.

## Diagnose the install
**Status:** Supported
**Subject:** cli

As a user, I run `/tcw-doctor` to check whether `tcw` is on PATH, how it was installed (pipx / editable / missing), and whether it matches the active plugin version — and to re-point it if a plugin update left it stale.
