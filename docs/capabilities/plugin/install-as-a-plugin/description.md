As a user, I add the tcw marketplace — from the command line, or from the plugin directory in the Claude web and desktop apps — and run `/plugin install tcw` (Claude Code) or `codex plugin add tcw@tcw` (Codex) to install the tcw skills as a plugin.

In Pi, I install the shared skills with `pi install git:github.com/brocef/TCW` (or a local checkout path), optionally adding `-l` for project scope. I invoke them with `/skill:<name>` and run `/skill:setup` to obtain the CLI. The package exposes skills; Claude hooks and custom agent definitions are not Pi resources.
