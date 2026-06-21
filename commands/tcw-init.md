---
description: Install the tcw CLI from this plugin's own clone (pipx), so `tcw` is available without a separate manual install step.
---

Run the **Setup** procedure in this plugin's `skills/tcw-plugin/SKILL.md`: resolve
the plugin clone root (prefer `$CLAUDE_PLUGIN_ROOT`, else the nearest ancestor with
`pyproject.toml`), `pipx install` it (using the pipx-absent fallback ladder if
needed), verify `tcw --version`, and warn against a separate `pip install tcw`.

Ground each step in the user's actual environment — check what's already present
before acting, and skip steps already done. After setup, recommend `/tcw-doctor`.
