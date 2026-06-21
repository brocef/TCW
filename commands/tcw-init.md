---
description: Install the tcw CLI from this plugin's own clone (pipx), so `tcw` is available without a separate manual install step.
---

Read `skills/tcw-plugin/docs/setup.md` in this plugin and follow it: resolve the
plugin clone root, `pipx install` it (with the pipx-absent fallback ladder), verify
`tcw --version`, and warn against a separate `pip install tcw`.

Ground each step in the user's actual environment — check what's already present
before acting, and skip steps already done. After setup, recommend `/tcw-doctor`.
