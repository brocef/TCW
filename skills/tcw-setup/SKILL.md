---
name: tcw-setup
description: Gets TCW working where it does not work yet. Use when a project does not use TCW yet, when the `tcw` CLI is missing, broken, or stale (not on PATH, `tcw --version` fails, or a plugin update left it behind), when an existing TCW project needs its stores or connected projects on a new machine, or when starting a taxonomy or capabilities ledger from an existing codebase. Changing the configuration of a project that already works is tcw-configure.
when_to_use: Use when a user asks to install or repair tcw, start tracking a repository with TCW, run tcw init or tcw provision, get a cloned TCW project working on this machine, or seed a first taxonomy or capabilities ledger from the code. Under Claude a SessionStart hook installs the CLI automatically, so a missing CLI means that hook did not finish; Codex has no hook and uses this skill directly.
allowed-tools: Bash(tcw *), Bash(command -v *), Bash(realpath *), Bash(head *), Bash(pipx *), Bash(python3 *), Bash(node --version), Bash(*/scripts/session_bootstrap.sh *), Read, Grep, Glob
metadata:
    author: Brian Cefali
compatibility: Requires Python 3.11+ and network access to PyPI on first install; `tcw serve` additionally requires Node.js 22.12+; installs the `tcw-cli` distribution via pipx.
license: Apache-2.0
---

# Setting up TCW

This skill gets TCW working where it does not work yet: the CLI, a repository,
a machine, and a first taxonomy or capabilities ledger. Changing how a working
project behaves is the `tcw-configure` skill.

**First-time setup runs in this order**, and each document says when it is done:

1. [`install.md`](references/install.md) — `tcw --version` works.
2. [`project.md`](references/project.md) — `tcw validate` passes.
3. [`taxonomy.md`](references/taxonomy.md) — the project's terms are recorded.
4. [`capabilities.md`](references/capabilities.md) — what users can do is recorded.

Skip a step that is already done. Steps 3 and 4 are optional, and 4 needs 3.

| The user wants to… | Open |
| --- | --- |
| install `tcw`, or fix one that is missing, broken or out of date | [`install.md`](references/install.md) |
| start tracking a repository with TCW | [`project.md`](references/project.md) |
| get a TCW project cloned from elsewhere working on this machine | [`project.md`](references/project.md) |
| write down the project's terms and features from its existing code | [`taxonomy.md`](references/taxonomy.md) |
| write down what users can already do, from the existing code | [`capabilities.md`](references/capabilities.md) |
| set up documentation entries (which documents a change must update) | the `tcw-configure` skill |
| set up lifecycle bindings (skills or commands run at a stage) | the `tcw-configure` skill |
| set up a Definition of Done | the `tcw-configure` skill |
| set up an external tracker | the `tcw-configure` skill |
| set up store locations, or keep a store in another repository | the `tcw-configure` skill |
| set up connected or inherited projects | the `tcw-configure` skill |

A request that says "set up" but names one of the last six areas is a
configuration change to a project that already works, not first-time setup.
