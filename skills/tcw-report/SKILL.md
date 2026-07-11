---
name: tcw-report
description: Teaches a TCW user how to report a bug, issue, or suggestion back to the TCW project by filing a GitHub issue on the TCW repository, and hands them a ready-to-fill skeleton for each kind of report. Use when a user hits a `tcw` bug, wants to request a feature, or has feedback on TCW itself — not for tracking the user's own project work (that is tcw-work).
when_to_use: Use when a user wants to report a problem with the `tcw` CLI or the TCW plugin/skills, request a feature, or send a suggestion upstream to the TCW project — i.e. feedback about TCW itself, filed as a GitHub issue. Do not use it for the user's own project work items (that is tcw-work).
allowed-tools: Bash(tcw *), Read
metadata:
  author: Brian Cefali
license: Apache-2.0
---

# Reporting an issue or suggestion to TCW

Feedback about **TCW itself** — a `tcw` bug, a rough edge in a skill, a feature
idea, a suggestion — goes to the project's issue tracker on GitHub, **not** into
the user's local `tcw work` store. (`tcw work` tracks changes to *their*
project; it is not a channel to the TCW maintainers.)

**File it here:** https://github.com/brocef/TCW/issues

## Before filing

1. **Search first.** Skim the open (and recently closed) issues for the same
   symptom or idea; if one exists, add your detail there instead of opening a
   duplicate.
2. **Pick the kind:** a **bug** (something is broken or behaves wrong) or a
   **suggestion / feature** (something should exist or work differently). Use
   the matching skeleton below.
3. **Grab the version.** For a bug, run `tcw --version` and include the output —
   most reports are unactionable without it.

## Bug skeleton

```markdown
**Title:** <one line: what breaks, where>

### Environment
- tcw version: <output of `tcw --version`>
- OS / platform: <e.g. macOS 14, Ubuntu 24.04>
- Install method: <pipx / pip --user / editable / other>

### Steps to reproduce
1. <exact command or action>
2. <...>
3. <...>

### Expected vs. actual
- Expected: <what should have happened>
- Actual: <what happened — paste the error / output verbatim>

### Remediation
<proposed fix, workaround you found, or "unknown — needs investigation">
```

## Suggestion / feature skeleton

```markdown
**Title:** <one line: the change you want>

### Motivation
<the problem or friction today — why the status quo falls short>

### Description
<what you are proposing, concretely — the command, flag, behavior, or wording>

### Benefits
<who it helps and how; what it unlocks or simplifies>
```

Keep it concrete: a real command, a real error, a real scenario beats an
abstract description. When it touches TCW's design, note which axis it concerns
(taxonomy / capabilities / work) so it lands with the right maintainer context.
