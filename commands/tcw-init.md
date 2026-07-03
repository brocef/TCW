---
description: Install the tcw CLI from this plugin's own clone (pipx), so `tcw` is available without a separate manual install step.
allowed-tools: Bash(tcw *), Bash(command -v *), Bash(pipx *), Bash(python3 *)
disable-model-invocation: true
---

Read `skills/tcw-plugin/references/setup.md` in this plugin and follow it: resolve the
plugin clone root, `pipx install` it (with the pipx-absent fallback ladder), verify
`tcw --version`, and warn against a separate `pip install tcw`.

Ground each step in the user's actual environment — check what's already present
before acting, and skip steps already done. After setup, recommend `/tcw-doctor`.
