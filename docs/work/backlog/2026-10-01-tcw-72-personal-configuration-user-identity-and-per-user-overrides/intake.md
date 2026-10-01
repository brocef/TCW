# TCW-72 — Personal configuration: user identity and per-user overrides

Imported on 2026-10-01 from [TCW-72](https://proposit.atlassian.net/browse/TCW-72) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review).

h1. What this delivers

A way for each person to tell TCW who they are and to adjust how TCW behaves for them (for example their own stage prompts) without changing it for the rest of the team.

h1. Layers

The config layers, lowest first:

{noformat}built-in  →  tcw-config.yaml  →  ~/.config/tcw/config.yaml  →  tcw-config.local.yaml{noformat}

* The user-wide file honors {{XDG_CONFIG_HOME}}.
* {{tcw-config.local.yaml}} sits next to {{tcw-config.yaml}} and is never tracked.
* {{TCW_NO_PERSONAL_CONFIG=1}} skips both personal layers, for tests and CI. With no home directory, the user-wide layer is skipped.
* Personal layers apply only to the project a command acts on. Other projects (upstreams, delegation targets) are read from their tracked config only.

h1. Merging, and the {{inherit}} chain

* Mappings merge key by key.
* {{prompt}}, {{pre}}, {{post}} and {{procedures}} lists resolve through the chain:
** a layer that does not set the key keeps what the layer below resolved;
** a layer that sets the key replaces it, unless its list contains an {{inherit: true}} entry, which is replaced by the list the layer below resolved. Its position decides the order:

{code:yaml}prompt:
  - file: docs/lifecycle/house-rules.md   # before the inherited text
  - inherit: true                         # everything from the layer below
  - file: docs/lifecycle/after.md         # after it{code}

* {{builtin: true}} is removed: at the team layer, {{inherit: true}} is the built-in content. There is no {{inherit: false}}; leaving the marker out means replace.
* Other lists are replaced whole.

h1. What can be overridden

* *One allowlist of overridable key paths.* Anything not on it is shared. A key added later is shared unless it is added to the list.
* Overridable: stage {{prompt}} and {{post}}, {{procedures}}, credential variable names, {{user.*}}.
* Shared, among others: {{id}}, backend, work path, Jira site and project, stage {{enabled}}, {{status}} and {{pre}}, field and priority mappings, inbox query, tag registry, {{extends}}, documentation entries, connected-project entries. {{pre}} resolves only through built-in and {{tcw-config.yaml}}.
* {{user.*}} is personal-only: refused in {{tcw-config.yaml}}.
* A personal file that sets a shared key makes every command that loads config exit 1, naming the file and key. The exception is {{tcw config show --origin}}, which still runs so the problem can be diagnosed.
* Each key's documentation states whether it is shared or overridable. The configure skill's references are the canonical home of that table (TCW-75 links to it).

h1. {{tcw config show}}

{{tcw config show [--origin]}} prints the effective configuration. {{--origin}} shows the layer each value, and each resolved list entry, came from. This ticket owns its behavior. {{stage prompt}} notes on stderr when personal layers changed the prompt, and {{advance}} names the layer of any {{post}} hook that failed.

h1. Identity

* Jira mode uses the Jira credentials.
* Filesystem mode uses {{user.name}} from personal config, matched exactly (case-sensitive) against {{assignee}}.
* No fallback: {{TCW_WORK_OWNER}} and the git {{user.name}} / {{user.email}} fallback are removed. Commands that need an identity ({{list --mine}}, {{--assign-me}} on {{new}} and {{edit}}) say how to set one.

h1. Other rules

* Secrets never go in config files; config names environment variables.
* Commands that edit config write only {{tcw-config.yaml}}; personal files are edited by hand.
* {{tcw init}} adds {{tcw-config.local.yaml}} to the {{.gitignore}} next to {{tcw-config.yaml}}, or skips with a notice outside a git repository. {{tcw validate}} warns if the file is tracked.
* Relative paths in a personal file resolve from that file's own directory.

h1. Open questions for the spec

* Whether "where project X lives on this machine" moves from {{TCW_PROJECT_<ID>}} into personal config, or both stay.

h1. Update from TCW-69's spec (2026-10-01)

{{advance}}'s outcome has no field yet for which config layer a failed {{post}} hook came from; this slice adds it. The 3.0 config parser ({{tcw/work/config.py}}) still uses {{builtin: true}}, and this slice replaces it with {{inherit: true}}.
