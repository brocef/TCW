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
the user's local `tcw work` store. (`tcw work` tracks changes to _their_
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

## What goes in the report

These are guidelines, not rules — what the report contains is your call.

The tracker at https://github.com/brocef/TCW/issues is **public**, and the
project you are reporting from may not be. So write the report from a **generic
example that mirrors your setup** rather than from the real thing, and keep
whatever real detail you do want in it.

- **Swap** repository, branch and directory names; node ids; work-item slugs;
  capability paths and wording; absolute paths; taxonomy terms and any other
  domain vocabulary.
- **Keep** the command's shape and its flags, the config's shape, the error type
  and the fixed part of its message, and the sequence that triggered it — and the
  real values in the Environment block (`tcw --version`, OS, install method),
  which describe the install rather than the project.

Written down, the swap is small:

```text
# yours:    tcw work new --initiative q3-pci-audit "Rotate the payment keys"
# mirrored: tcw work new --initiative example-epic "Rotate the service keys"
#
# yours:    work store root does not exist: ~/acme/payments-api/docs/work
# mirrored: work store root does not exist: ~/example-project/docs/work
```

Output works the same way: the output of a generic reproduction is the more
useful one to receive, and you may paste output from your own system and
environment instead if you would rather.

Where you can, sketch the steps that reproduce the problem on a **fresh
environment** — a clean install and a scratch project, starting from nothing.
Those steps are generic already, and they tell the maintainer the problem is not
something local to you. A clean-room reproduction is often impractical, and a
report is welcome without one. It is also worth delegating: a subagent or an
agent team member can run it in a temporary directory, leaving your own checkout
untouched.

## Bug skeleton

```markdown
**Title:** <one line: what breaks, where>

### Environment

- tcw version: <output of `tcw --version`>
- OS / platform: <e.g. macOS 14, Ubuntu 24.04>
- Install method: <pipx / pip --user / editable / other>

### Steps to reproduce

1. <the exact command or action, under mirrored names>
2. <...>
3. <...>

### Expected vs. actual

- Expected: <what should have happened>
- Actual: <what happened — the error / output verbatim, from the mirrored run>

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

Keep it concrete in the shape: a real command with its real flags, a real error
with its real type, the real sequence that produced it — under names that are not
your project's. When it touches TCW's design, note which axis it concerns
(taxonomy / capabilities / work) so it lands with the right maintainer context.
