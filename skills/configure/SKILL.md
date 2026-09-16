---
name: configure
description: Changes how a project that already uses TCW is configured. Use when a user wants to set up or change lifecycle bindings (skills or commands run at a stage or transition), hook limits, the Definition of Done, documentation entries that track which documents a change must update, an external tracker, where a store lives, connected projects, or inherited taxonomy or capabilities. Getting TCW working in the first place is the `setup` skill.
when_to_use: Use when a working TCW project should behave differently — setting up or changing work.lifecycle bindings, docs/work/dod.yaml, work.documentation entries, work.tracker, work.retain, work.auto-commit-transitions, work.trunk-branch, work.publish-transitions, a store's path or repository, connected-projects, TCW_PROJECT_<ID>, or taxonomy and capabilities extends. Also when a request says "set up" but names one of those areas.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write, Grep, Glob
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---

# Configuring TCW

This skill changes the configuration of a project where TCW already works: what
`tcw-config.yaml`, a component's own config file, `dod.yaml` and a per-machine
environment variable say. Getting TCW working where it does not work yet — a
new repository, a new machine, a missing or broken `tcw` — is
the `setup` skill.

Find the user's request in the table and open that document. Each one says what
the setting does, shows its shape, and names the check to run.

| The user wants to… | Open |
| --- | --- |
| run a skill or command at a stage or transition, or change the prompt a stage prints | [`work.md`](references/work.md) |
| change the template `tcw work scaffold` writes for a lifecycle document | [`work.md`](references/work.md) |
| change how long a hook may run or how much a `generate:` script may print | [`work.md`](references/work.md) |
| set the Definition of Done, the checklist `tcw work complete` prints | [`work.md`](references/work.md) |
| stop transitions committing themselves, set a trunk branch, keep transitions local, or delete resolved items | [`work.md`](references/work.md) |
| set up documentation tracking: which documents must be updated when which kind of change lands | [`docs-sync.md`](references/docs-sync.md) |
| connect an external tracker such as Jira, or share tracker settings from a parent project | [`tracker.md`](references/tracker.md) |
| keep a component's store in another folder or another repository | [`stores.md`](references/stores.md) |
| connect a parent or child project, or say where a project is on this machine | [`projects.md`](references/projects.md) |
| inherit another project's taxonomy or capabilities | [`projects.md`](references/projects.md) |

Two settings are not here. The project `id` is written once by `tcw init` and is
not changed afterwards. Tags are registered with `tcw work tags add` while
filing work, which the `work` skill covers.

After any change, run `tcw validate`. The document you opened says which
mistakes it reports and which it cannot see.
