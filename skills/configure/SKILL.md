---
name: configure
description: Changes how a project that already uses TCW is configured. Use when a user wants to set up or change the stages a project uses, the text or commands bound to a stage, hook limits, procedures, the Jira backend, documentation entries that track which documents a change must update, where a store lives, a project's parents and children, where related projects are on this machine, what a project inherits from its parents, or their own personal configuration. Getting TCW working in the first place is the `setup` skill.
when_to_use: Use when a working TCW project should behave differently — setting up or changing work.stages (enabled, status, prompt, pre, post), work.hooks, work.procedures, work.backend and work.jira, work.tags, work.documentation entries, a store's path or repository, parents and children, manifests and TCW_PROJECT_<ID>, inherited taxonomy, capabilities and configuration, user.name, a personal .tcw/tcw-config.local.yaml, or an override variable. Also when a request says "set up" but names one of those areas.
allowed-tools: Bash(tcw *), Read, Edit, Write, Grep, Glob
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# Configuring TCW

This skill changes the configuration of a project where TCW already works:
what `.tcw/tcw-config.yaml`, the project's manifests, a person's own
configuration files and per-machine environment variables say. Getting TCW
working where it does not work yet — a new repository, a new machine, a
missing or broken `tcw` — is the `setup` skill.

Find the user's request in the table and open that document. Each key has its
own heading there, which says what the key does, shows its shape, and says
whether one person may set it for themselves.

| The user wants to…                                                                                                                                    | Open                                      |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| turn stages on or off, bind text or commands to a stage, change hook limits, register tags, or change a procedure's text                              | [`work.md`](references/work.md)           |
| keep the project's work items in Jira, or change how stages map to Jira statuses                                                                      | [`jira.md`](references/jira.md)           |
| set up documentation tracking: which documents must be updated when which kind of change lands                                                        | [`docs-sync.md`](references/docs-sync.md) |
| keep a component's store in another folder or another repository                                                                                      | [`stores.md`](references/stores.md)       |
| name a project's parents or children, choose what a parent passes down, or say where a related project is on this machine                             | [`projects.md`](references/projects.md)   |
| set their own name, credentials or additions for themselves only, with a personal file or an override variable, or see which file a setting came from | [`personal.md`](references/personal.md)   |

`personal.md` also holds one table of every configuration key, with who may
set it.

Two settings are not changed here by hand. The project `id` is written once by
`tcw project new` and is not changed afterwards. Tags are registered with
`tcw work tags add` while filing work, which the `work` skill covers.

Two commands show what a project's configuration has become.
`tcw project config --origin` prints the configuration commands actually use,
with a comment after each value naming the project, the layer and the file or
variable it came from. `tcw project info` prints the project's parents and
what each passes, its children, its load order (the order in which its
parents are read), its stores and its overrides.

An item for another project is made in that project, by running the command
there with `tcw -C <folder>`; the `work` skill covers it. Where a related
project is missing, `tcw project provision` fetches it, but a manifest other
than the active project's own two may place a clone only in a non-hidden
folder directly inside the folder holding its owner's repository, never in
or above the home folder; `tcw -C <folder> project provision <id>`, or an
entry in that project's `.tcw/tcw-manifest.local.yaml`, is the way out, and
the guide [Related projects](../../docs/guide/multi-repo.md) in the TCW
repository has the rest.

After any change, run `tcw validate`. The document you opened says which
mistakes it reports and which it cannot see.
