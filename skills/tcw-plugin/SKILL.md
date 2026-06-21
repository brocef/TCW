---
name: tcw-plugin
description: Use when the `tcw` CLI is missing or broken — not found on PATH, `tcw --version` fails, or a plugin update left it stale — to install or repair it from this plugin's own clone. The `/tcw-init` and `/tcw-doctor` commands route here; Codex (no slash commands) uses this skill directly.
---

# Installing & repairing the `tcw` CLI

The plugin ships the skills; `tcw` itself is a Python package that has to be on
your PATH. **Most of the time it already is — so check first, and only read the
detailed procedure if there's a problem:**

```
tcw --version      # works? → nothing to do. stop here.
```

If `tcw` is **missing or broken**, read the matching procedure in this skill's
`docs/` and follow it:

- **Install** `tcw` from the plugin clone → read [`docs/setup.md`](docs/setup.md)
- **Diagnose / repair** a stale, wrong, or shadowed install →
  read [`docs/doctor.md`](docs/doctor.md)
