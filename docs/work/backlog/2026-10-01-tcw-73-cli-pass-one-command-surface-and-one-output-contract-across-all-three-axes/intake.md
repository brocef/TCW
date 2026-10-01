# TCW-73 — CLI pass: one command surface and one output contract across all three axes

Imported on 2026-10-01 from [TCW-73](https://proposit.atlassian.net/browse/TCW-73) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review).

h1. What this delivers

A command line that is intuitive and predictable for people and agents alike: consistent names, useful {{--help}}, a clear stdout/stderr split and meaningful exit codes, across {{tcw work}}, {{tcw taxonomy}}, {{tcw capabilities}} and the top-level commands.

h1. Output contract

* *stdout is the command's product; stderr is narration about it.* Narration covers what happened, which files were written, and what to do next.
* Per command, stdout carries:
** {{new}}, {{tickets adopt}}, {{rename}}: the slug. When delegation stops at the target's inbox, {{new}} prints the ticket key.
** {{advance}}, {{discard}}: the new stage.
** {{list}}: one slug per line, or {{--json}}.
** {{show}}: the item's record, or {{--json}}.
** {{path}}: the path.
** {{stage prompt}}, {{procedure}}, {{lifecycle}}, {{docs}}, {{config show}}: their text.
** {{serve}}: the URL.
** {{edit}}, {{comment}}: nothing.
* stderr always names every file written or removed.
* Commands never prompt interactively.
* Long text ({{comment}}, the request on {{new}}) is read from stdin.
* Built-in help and message strings in the Python code that mention git are removed here.

h1. Exit codes (final)

||Code||Meaning||
|0|ok, including validate with only warnings, and delegation that stopped at the target's inbox|
|1|error, including config errors, a port already in use, and Jira errors other than not-found|
|2|usage, including an unknown stage name and a Jira-only command in filesystem mode|
|3|refused: a gate, no stage, a name collision, delegation conditions, or a transition Jira doesn't offer|
|4|not found|
|5|remote unreachable|
|6|moved, but a post hook failed|

h1. Slug input

Accepted exactly:

* the full slug;
* the bare folder name, within the current project;
* the Jira key, in Jira mode.

No prefix matching and no old-slug aliases. The full slug is always what's printed.

h1. Command surface

Naming is {{tcw noun [child-noun] verb}}. Single-purpose readers ({{lifecycle}}, {{docs}}, {{procedure}}) may stand without a verb.

{{tcw work}}

* {{new}}: {{--project}} to delegate, {{--stage inbox}} in filesystem mode.
* {{tickets list}} and {{tickets adopt <KEY>}}: Jira only.
* {{list}}: {{--stage}}, {{--parent}}, {{--assignee}}, {{--mine}}, {{--all}}, {{--json}}.
* {{show}} ({{--json}}), {{path <slug> [<stage> [--next]]}}, {{edit}}, {{advance}}, {{discard}}, {{comment}}, {{rename}}, {{stage prompt}}, {{lifecycle}}, {{docs}}, {{procedure}}, {{tags list|add|rm}}.

*Flags*

* {{edit}} takes {{--title}}, {{--priority}} (named), {{--effort}}, {{--complexity}}, {{--tag}}/{{--untag}}, {{--assignee}}, {{--assign-me}}, {{--parent}}, {{--blocked-by}}, {{--unblocked-by}} and {{--blocks}}.
* {{--initiative}}, {{--type}} and {{--epic}} are removed.
* {{advance}} takes {{--to}}, {{--force}}, {{--reason}} (required with {{--force}}) and {{--dry-run}}.

*Top level*

* {{tcw init [axis]}}
* {{tcw provision}}
* {{tcw validate [--remote]}}; {{--remote}} adds the Jira checks, including workflow compatibility.
* {{tcw projects list}} (was {{tcw work nodes}})
* {{tcw config show}} (behavior owned by TCW-72)
* {{tcw serve [--port] [--no-open]}} (behavior owned by TCW-77)

*Taxonomy and capabilities commands*

* Same output contract and {{--help}} standard.
* {{taxonomy check}} and {{capabilities check}} fold into {{tcw validate}}.
* {{extends}} subcommands stay; they write shared, tracked config.
* {{capabilities drift}} reads {{spec/capabilities.yaml}} (logic in TCW-69).
* None of them touch git.

*Removed or merged*

* start, submit, rework, complete and drop → {{advance}}
* {{stage gate}} → {{advance --dry-run}}
* delegate and escalate → {{new --project}}
* {{inbox}} → inbox-stage items (filesystem) or {{tickets}} (Jira)
* all {{tracker}} subcommands → removed
* {{reconcile}} → Jira hierarchy, or {{list --parent}}
* {{work init}}, {{taxonomy init}} and {{capabilities init}} → {{tcw init <axis>}}
* {{stage validate}}, {{tombstone}}, {{delete}}, {{scaffold}} → removed

h1. Update from TCW-69's spec (2026-10-01)

* Exit 6 now means "the item moved, but something after the move failed": a {{post}} hook, or recording the trace comment.
* The "node" to "project" rename belongs to this slice in full: commands, the {{connected-projects}} config keys, the {{TCW_NODE_ROOT}} hook variable, and internal code.
* {{capabilities drift}} reads {{<item>/capabilities.yaml}}, not {{spec/capabilities.yaml}}.
* The {{detect-capability-drift}} capability record must be rewritten: it promises drift never depends on the work axis, and 3.0 drift reads completed work items.
* {{tcw validate}} should call the new mid-work records check ({{records_problems(finished=False)}}) in place of today's {{capability_gate(in_progress=True)}}.
