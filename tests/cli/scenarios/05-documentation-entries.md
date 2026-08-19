# 05 — Documentation entries from `tcw-config.yaml`

New in 1.0.0: a node declares which documents must move with code as
configuration, and TCW serves it. Previously an agent scraped a Markdown section
out of the agent guide.

## Functionality covered

- `work.documentation` in `tcw-config.yaml` — a list of
  `{path, trigger, description}`
- `tcw work docs` and `tcw work docs --json`
- The `{{tcw:documentation}}` span in the `plan` and `implement` stage prompts
- The unconfigured fallback, which must be **byte-identical** to the pre-1.0.0
  output
- `tcw validate` on malformed entries

## What is tested

| # | Assertion |
| - | --------- |
| 1 | On a node configuring three entries, `tcw work docs` exits 0 and prints every `path` and `trigger`. |
| 2 | `tcw work docs --json` parses, and carries `schema`, `source: "config"`, and an `entries` array whose `path` values are **in the configured order**. |
| 3 | On an **unconfigured** node, `tcw work docs --json` reports `source: "agent-guide"` and `entries: []`, exit 0. |
| 4 | On an unconfigured node, `tcw work docs` (human form) prints **nothing on stdout** and names the agent guide on **stderr**, exit 0. This split is what lets a script gate on emptiness. |
| 5 | `tcw work stage plan $SLUG` on a configured node contains every entry's path, trigger and description, and does **not** mention the agent guide. |
| 6 | `tcw work stage implement $SLUG` likewise. |
| 7 | `tcw work stage spec $SLUG` — a stage carrying no span — contains **none** of the entry paths. |
| 8 | On an unconfigured node, `plan` and `implement` still name the agent guide and contain **no** `{{tcw:documentation}}` token. |
| 9 | `tcw work docs` writes nothing: a `path → sha256` manifest of the whole node is identical before and after running both forms. |
| 10 | `tcw work docs` outside a node exits non-zero with empty stdout. |
| 11 | A description containing a `|` character survives rendering intact in `stage plan` output. (It renders as a list, not a table, for exactly this reason.) |
| 12 | A multi-line YAML block-scalar description is collapsed to one line and does not break out of its bullet. |
| 13 | A malformed entry (missing `trigger`, or `documentation:` given a mapping instead of a list) is reported by `tcw validate` as a problem; `tcw work docs` does **not** crash. |
| 14 | An entry whose `path` does not exist on disk is accepted — validation is shape-only, because a path may legitimately be a pattern like `skills/<component>/SKILL.md`. |
| 15 | An **empty** `documentation: []` list behaves as unconfigured (`source: "agent-guide"`) — or as configured-but-empty. Pin whichever it is. |

## Refusals asserted

- outside a node (10)
- malformed config surfaced by `validate` without crashing `docs` (13)

## Explicitly not covered here

The `documentation-sync` skill's own prose, which is not executable.

## Notes for the implementer

Assertion 8 is the back-compat guarantee and the most valuable line in this file.
The in-process suite pins it against a fixture captured before any prompt was
touched (`tests/fixtures/prompt_fallback/`). The shell version should compare
`tcw work stage plan` output on an unconfigured node against that **same
fixture**, not against a fresh capture — a fresh capture would pass even if both
sides drifted together.

Assertion 15 is genuinely unknown to the author of this document. Find out.
