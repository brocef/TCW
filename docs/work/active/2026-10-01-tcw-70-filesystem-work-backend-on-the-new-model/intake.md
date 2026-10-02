# TCW-70 — Filesystem work backend on the new model

Imported on 2026-10-01 from [TCW-70](https://proposit.atlassian.net/browse/TCW-70) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review). Builds on TCW-69.

h1. What this delivers

"Vanilla" TCW: the backend that keeps in the repository what Jira mode keeps in Jira. It is a first-class way to use TCW, not a fallback.

h1. Scope

This backend implements TCW-69's backend operations for what Jira owns in the other mode: properties and stage in {{item.yaml}}, the request file, the inbox, comments, rename, and delegation into filesystem-mode projects. Folder layout, stage folders, rounds, handoffs and {{path}} are TCW-69's shared layer, used by both backends.

h1. Decisions

* A project uses exactly one work backend; filesystem mode and Jira mode never mix.
* {{item.yaml}}:

{code:yaml}title: Formalize Jira in the work lifecycle
stage: spec
priority: medium
effort: high
complexity: medium
tags: [work, cli]
assignee: brian
parent: tcw/2026-09-12-jira-first-tcw
blocked-by:
  - tcw/2026-09-15-check-the-tracker-s-workflow{code}

* Required: {{title}}, {{stage}}. Defaults from {{new}}: priority {{medium}}; everything else absent until set. Tags are checked against the project's tag registry.
* *Folder names* are {{YYYY-MM-DD-<title words>}}. The date prefix is the creation date (no separate {{created}} field). A name that already exists is refused (exit 3).
* *Each branch carries its own* {{stage}}. Status is whatever the checked-out tree says. Teams that want one shared view commit and push stage changes, e.g. with the opt-in example in TCW-75. With no {{history}} list, two branches only conflict when both moved the same item, which is a real disagreement.
* The request is {{request/request.md}}; QA rounds are {{qa/round-N.md}}.
* Comments are {{comments/<UTC timestamp>.md}}, one file per comment. Forced moves and discards write their reason here.
* *Inbox:* items at the inbox stage (folders). {{list}} shows them by default; {{list --stage inbox}} shows only them. This replaces {{tcw work inbox}}.
* *Rename:* a plain filesystem move of the folder; the date prefix stays. Rewrites {{parent}} and {{blocked-by}} in this project's items only, and prints any other mentions it finds on stderr. No {{renames.yaml}}, no lock, no old-slug alias.
* *Delegation into a filesystem-mode project* ({{tcw work new --project <id>}}, and {{edit --blocks}} writing another project's item) needs: the project's path resolved, its work store present, and no uncommitted changes in that store. Otherwise it refuses (exit 3) and says which condition failed. A delegated item lands at the inbox stage. Files written in another repository are left uncommitted, and stderr names them.
* Work stores kept in a separate repository remain supported: {{tcw provision}} clones them, and keeping them fresh is the project's job through hooks. TCW never pulls or pushes.
* Removed from the store root: status directories, {{graveyard.yaml}}, {{dod.yaml}}, {{renames.yaml}}.
