---
name: tcw-plugin
description: Use for TCW orientation across the plugin's skills, or when the `tcw` CLI is missing or broken — not found on PATH, `tcw --version` fails, or a plugin update left it stale — to install or repair it from this plugin's own clone. The `/tcw-init` and `/tcw-doctor` commands route here; Codex (no slash commands) uses this skill directly.
---

# TCW skill map

TCW has three project axes plus this plugin-maintenance skill:

1. **Taxonomy (`tcw-taxonomy`)** registers the project's language:
   - **Vocabulary** entries are conceptual terms.
   - **Feature** entries are user- or application-facing manifestations that
     operate on or involve vocabulary.
2. **Capabilities (`tcw-capabilities`)** describe what users can do. A
   capability can point loosely at a taxonomy `Subject` and strongly at a
   taxonomy `Feature`.
3. **Work (`tcw-work`)** tracks planned and completed changes to vocabulary,
   features, capabilities, code, and docs through the SDLC artifacts.

Use the skills in that order when the task changes product meaning:

`Vocabulary -> Features -> Capabilities -> Work`

Practical routing:

- If the user is naming or organizing project concepts, use `tcw-taxonomy`.
- If the user is describing user-visible behavior, use `tcw-capabilities`; check
  whether a registered taxonomy Feature should be linked.
- If the user is planning, implementing, verifying, or closing a change, use
  `tcw-work`; it invokes the capability gate for product deltas.
- If `tcw` itself is unavailable or the plugin install is stale, stay in this
  skill and follow the install/repair procedures below.

The axes point forward, not backward: taxonomy entries do not point to
capabilities or work; capabilities point to taxonomy and planning work; work
records the changes being made.

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
