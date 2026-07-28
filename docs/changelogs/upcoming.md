# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `skills/tcw-work/references/audit-backlog.md` — the backlog-audit procedure,
  reached by a gate line in the `tcw-work` router. The checklist is split into a
  **per-item** list (already completed, outdated, wrong node, unactionable,
  stale blockers, capability drift) and an **inter-item** list (duplicate or
  superseded, missing relationship edges, tag hygiene), with pipelined subagent
  dispatch — one agent per item feeding its findings plus a two-line summary to
  one set-wide agent — capped at 8 concurrent as a sliding window.
- **Missing relationship edges** as an audit check: a dependency stated in an
  item's prose but never recorded with `tcw work edit --blocked-by`, so the
  board shows both items as equally pickable.
- `agents/tcw-backlog-auditor.md` — read-only agent (`Read, Glob, Grep, Bash`)
  for the per-item half of the audit. Enforces by tool set what was previously a
  prompt request.
- `tests/test_documented_cli_surface.py` — walks the real `tcw --help` tree and
  asserts every `tcw` invocation in `README.md`, `skills/**`, `commands/**`, and
  `agents/**` names a verb and flags that exist. Parses both backtick spans and
  fenced blocks.
- `docs/migration-guide-0.15.X-to-0.16.0.md` — covers the changelog hash-range
  removal. It documents a relaxation rather than a required migration, so it
  states up front that no action is needed, then describes the optional cleanup
  for projects holding `<changes>` wrappers. The plugin cache carries `docs/`
  verbatim, so plugin users can read it without any packaging change.

## Removed

- The commit-hash-range requirement for changelog entries. The
  `## Changelog Entry Format` section of
  `skills/documentation-sync/references/release-notes-and-changelogs.md` is
  gone in full — the `<changes starting-hash= ending-hash=>` wrapper, the
  `git rev-parse --short HEAD` recipe, and the "Skip hash wrappers" escape
  hatch, which had nothing left to escape from. No project adopting the skill
  inherits the requirement.
- Fold step 5 of `references/cut-version.md` ("Extend the commit-hash ranges")
  and its Common Mistakes row. The step existed only to repair ranges the fold
  itself invalidated; remaining steps renumber `1.`–`6.`.

## Changed

- The recommended Documentation Sync entry for `docs/changelogs/upcoming.md`
  now reads "Developer changelog; technical, grouped by category" in both
  copies — `skills/documentation-sync/SKILL.md` and
  `references/release-notes-and-changelogs.md`.
- `scripts/cut_version.py`'s `UPCOMING` header template for
  `docs/changelogs/upcoming.md` drops its hash clause, and the live
  `docs/changelogs/upcoming.md` header was matched to it so a rotation is not a
  surprise diff.
- Every commit hash stripped from this file — 12 per-entry `` (`hash`) ``
  suffixes and a trailing `Commit range:` footer — so the next release ships a
  changelog consistent with the rule it announces. Entry prose is unchanged, and
  released `docs/changelogs/v*.md` are untouched: they describe versions that
  already shipped.
- The end-of-`implement` documentation gate keeps its position but rests on one
  reason instead of two: `skills/documentation-sync/SKILL.md` and
  `skills/tcw-work/references/stage-implement.md` step 6 both drop the
  commit-range clause and argue solely from shape drift.
- `AGENTS.md` (and `CLAUDE.md`, its symlink) no longer asks for commit hash
  ranges in TCW's own changelog entries.

## Fixed

- Three documented CLI surfaces that never existed: `tcw work
  audit-work-backlog` (`README.md`, `skills/tcw-work/references/commands.md`),
  `tcw work consolidate-plans` with `--apply`/`--delete` (same two files), and
  `--pr` on `tcw work edit` (`commands.md`). The first two are AI-driven
  workflows that live as slash commands and are now documented as such.
- The backlog-audit procedure was unreachable from Codex: it lived only in
  `commands/tcw-audit-work-backlog.md`, and `.codex-plugin/plugin.json` exposes
  `skills/` but has no `commands` key. Moved under `skills/`; the command file
  is reduced to a pointer so the Claude slash command still works.
- `AGENTS.md` and `skills/tcw-work/references/delegation.md` asserted that Codex
  has no subagents and no custom agents. Codex has both — `.codex/agents/*.toml`,
  model-driven spawning, `[agents] max_concurrent_threads_per_session`. The
  surrounding doctrine (delegation is an optimization, never load-bearing) is
  unchanged; only the factual claim moved.
- `.codex-plugin/plugin.json` `longDescription` said the plugin ships six
  skills; it ships seven (`tcw-post-mortem` was missing).
- `docs/capabilities/work/consolidate-plans/description.md` still claimed a
  `tcw work consolidate-plans` CLI verb — the one phantom the first sweep missed,
  because the guard's scan roots excluded the capability ledger. The guard now
  scans `docs/capabilities/**`; capability bodies are user-facing documentation
  and name commands like any other doc. Found by a trial run of the new audit
  procedure.
- Gaps in the new audit procedure, all found by that same trial run: the
  inter-item pass read `--status active`/`--status completed` but not
  `--status review` (the likeliest near-duplicate, since it is the work that just
  happened); "cap concurrency at 8 as a sliding window" prescribed a mechanism no
  harness offers, now "batches of at most 8"; `tcw-backlog-auditor` had no
  fallback for sessions on a release that predates it; `<severity>` had no
  defined scale; a healthy item had no rendering; approvals had no grouping rule;
  and nothing asked a read-only pass to verify it had changed nothing.
- `agents/tcw-verifier.md` and `agents/tcw-backlog-auditor.md` claimed "you have
  no write tools" while holding `Bash`, which can write. Both now state what the
  tool set actually gives (no file editing) and that the rest is a prohibition
  honored, not a wall. `delegation.md` says the same.

## Internal

- `delegation.md`'s custom-agent test now records three passes rather than two,
  and names the read-only tool set as the strongest reason to define an agent:
  it enforces what a prompt can only request.
