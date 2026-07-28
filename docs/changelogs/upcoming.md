# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `skills/tcw-work/references/audit-backlog.md` — the backlog-audit procedure,
  reached by a gate line in the `tcw-work` router. The checklist is split into a
  **per-item** list (already completed, outdated, wrong node, unactionable,
  stale blockers, capability drift) and an **inter-item** list (duplicate or
  superseded, missing relationship edges, tag hygiene), with pipelined subagent
  dispatch — one agent per item feeding its findings plus a two-line summary to
  one set-wide agent — capped at 8 concurrent as a sliding window. (`a5bc076`)
- **Missing relationship edges** as an audit check: a dependency stated in an
  item's prose but never recorded with `tcw work edit --blocked-by`, so the
  board shows both items as equally pickable. (`a5bc076`)
- `agents/tcw-backlog-auditor.md` — read-only agent (`Read, Glob, Grep, Bash`)
  for the per-item half of the audit. Enforces by tool set what was previously a
  prompt request. (`a5bc076`)
- `tests/test_documented_cli_surface.py` — walks the real `tcw --help` tree and
  asserts every `tcw` invocation in `README.md`, `skills/**`, `commands/**`, and
  `agents/**` names a verb and flags that exist. Parses both backtick spans and
  fenced blocks. (`6e63405`)

## Fixed

- Three documented CLI surfaces that never existed: `tcw work
  audit-work-backlog` (`README.md`, `skills/tcw-work/references/commands.md`),
  `tcw work consolidate-plans` with `--apply`/`--delete` (same two files), and
  `--pr` on `tcw work edit` (`commands.md`). The first two are AI-driven
  workflows that live as slash commands and are now documented as such.
  (`dbb2340`)
- The backlog-audit procedure was unreachable from Codex: it lived only in
  `commands/tcw-audit-work-backlog.md`, and `.codex-plugin/plugin.json` exposes
  `skills/` but has no `commands` key. Moved under `skills/`; the command file
  is reduced to a pointer so the Claude slash command still works. (`a5bc076`)
- `AGENTS.md` and `skills/tcw-work/references/delegation.md` asserted that Codex
  has no subagents and no custom agents. Codex has both — `.codex/agents/*.toml`,
  model-driven spawning, `[agents] max_concurrent_threads_per_session`. The
  surrounding doctrine (delegation is an optimization, never load-bearing) is
  unchanged; only the factual claim moved. (`dbb2340`)
- `.codex-plugin/plugin.json` `longDescription` said the plugin ships six
  skills; it ships seven (`tcw-post-mortem` was missing). (`dbb2340`)

## Internal

- `delegation.md`'s custom-agent test now records three passes rather than two,
  and names the read-only tool set as the strongest reason to define an agent:
  it enforces what a prompt can only request. (`dbb2340`)

Commit range: `24f4bc6..dbb2340`.
