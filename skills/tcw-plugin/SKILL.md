---
name: tcw-plugin
description: TCW orientation across the plugin's skills, plus install/repair of the `tcw` CLI from the plugin's own clone. Use for cross-skill orientation, or when `tcw` is missing or broken — not on PATH, `tcw --version` fails, or a plugin update left it stale. The `/tcw-init` and `/tcw-doctor` commands route here; Codex (no slash commands) uses this skill directly.
when_to_use: Use for TCW orientation across the plugin's skills, or when the `tcw` CLI is missing or broken — not found on PATH, `tcw --version` fails, or a plugin update left it stale — to install or repair it from this plugin's own clone.
allowed-tools: Bash(tcw *), Bash(command -v *), Bash(pipx list *), Read
metadata:
    author: Brian Cefali
compatibility: Requires Python 3.11+; `tcw serve` additionally requires Node.js 22.12+; installs the tcw CLI via pipx from the plugin clone.
license: Apache-2.0
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

Plus a feedback skill, orthogonal to the three axes:

- **Report (`tcw-report`)** teaches a user how to send feedback about TCW
  _itself_ — a `tcw` bug or a suggestion — upstream as a GitHub issue, with a
  ready-to-fill skeleton. It is not for the user's own project work (that is
  `tcw-work`).

Use the axis skills in that order when the task changes product meaning:

`Vocabulary -> Features -> Capabilities -> Work`

Practical routing:

- If the user is naming or organizing project concepts, use `tcw-taxonomy`.
- If the user is describing user-visible behavior, use `tcw-capabilities`; check
  whether a registered taxonomy Feature should be linked.
- If the user is planning, implementing, verifying, or closing a change, use
  `tcw-work`; it invokes the capability gate for product deltas.
- If the user wants to report a `tcw` bug or send a suggestion upstream to the
  TCW project, use `tcw-report`.
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
`references/` and follow it:

- **Install** `tcw` from the plugin clone → read [`references/setup.md`](references/setup.md)
- **Diagnose / repair** a stale, wrong, or shadowed install →
  read [`references/doctor.md`](references/doctor.md)

Node.js is not a general TCW prerequisite. Check for Node 22.12 or newer only
when the user intends to run or diagnose `tcw serve`. Installed TCW already
contains the prebuilt Fastify/React assets; pnpm and `node_modules` are
contributor-only requirements and must not be added to setup or repair steps.
