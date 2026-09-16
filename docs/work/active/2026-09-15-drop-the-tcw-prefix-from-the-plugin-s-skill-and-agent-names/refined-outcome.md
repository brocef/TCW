# Refined outcome — Drop the `tcw-` prefix from the plugin's skill and agent names

**Accepted** by the requester at verification, with the version cut deliberately
held. The implementation is `824c4b0`…`9d5ecc5` on
`claude/tcw-prefix-dropping-bug-jtxgtq`, pushed.

## Acceptance criteria

All 16 met. Each line is output from a command run against the finished tree, not
a restatement of intent.

| #   | Criterion                                   | Evidence                                                                                                           |
| --- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | 16 skill directories, none prefixed         | `ls skills \| wc -l` = 16; `ls skills \| grep -c '^tcw-'` = 0                                                      |
| 2   | Skill `name` equals its directory           | `test_skill_frontmatter_name_matches_its_directory`, 16 cases green; `documentation-sync` still reads itself       |
| 3   | 3 agents, each `name` equal to its basename | `backlog-auditor.md`, `post-mortem.md`, `verifier.md`; `test_agent_frontmatter_name_matches_its_file` green        |
| 4   | The guards mutation-checked, red for cause  | Five arms, each reverted; the exact failure text is in `outcome.md`'s table                                        |
| 5   | 16 `-skill` Features, none prefixed         | `tcw taxonomy list \| grep -c -- -skill` = 16, prefixed = 0; display names, `relatesTo` and `vocabulary` carried   |
| 6   | 16 `skills/` capabilities, none prefixed    | `tcw capabilities list` = 16, prefixed = 0; `tcw capabilities show skills/work` reproduces the old entry           |
| 7   | The three checks exit 0                     | `tcw taxonomy check`, `tcw capabilities check`, `tcw validate` — all OK                                            |
| 8   | Suite green, no fewer than baseline         | **3404 passed, 2 skipped** vs. a 3367/2 baseline; the +37 are exactly the new guard cases                          |
| 9   | No live file names an old name              | `test_no_live_route_names_a_removed_skill_or_command` with 17 names and the widened routes, plus the one-time grep |
| 10  | Exclusion tokens intact                     | 13 of 14 unchanged against a worktree of the pre-change commit; `tcw-config` +2, both added by task 11             |
| 11  | History untouched                           | `git diff --stat 632d382..HEAD` touches nothing under the protected paths; `docs/work/` limited to this item       |
| 12  | Codex description counts and names them     | `test_the_codex_description_counts_the_skills_it_ships` green, unweakened — it reads the `skills/` glob            |
| 13  | Eval coverage keys name shipped skills      | `tests/test_eval_coverage.py` green                                                                                |
| 14  | Eval arms resolve, nothing spawned          | `python -m evals.run_evals --axis a --dry-run` — 13 arms, no unresolved name, no old name in the output            |
| 15  | Every fired documentation trigger addressed | Six entries; five fire and are answered in `fb2ca5b`, `jira.md` correctly does not                                 |
| 16  | Release note gives the full mapping         | `docs/release-notes/upcoming.md` states the breaking change and maps all 18 names                                  |

**Beyond the criteria:** the spec listed host resolution as unverifiable here. It
was verified — a headless session loading the plugin from the working tree resolves
all 16 skills unprefixed, with no `tcw:tcw-…` address. Codex remains unverified,
and that is stated rather than implied.

## Definition of Done

- **tests pass** — 3404 passed, 2 skipped, 0 failed.
- **docs synced** — the `documentation-sync` pass is `fb2ca5b`; five of six entries
  fired and each is answered, including one evaluated and found already correct.
- **capabilities reconciled** — 15 entries migrated through the CLI; `tcw
capabilities check` and `tcw taxonomy check` green. No capability was added or
  removed, which matches the spec's **New — none. Removed — none.**
- **reviewed** — accepted by the requester at this stage.
- **version offered** — offered, and **declined in favour of holding 2.3.0**. The
  `upcoming.md` entries are written and waiting, so the cut is a one-command step
  whenever the batch is ready. Worth flagging at that point: this is a breaking
  change to every skill entry point, so the batch it joins should be cut as a
  major.
- **originating GitHub issue answered and closed, if the item came from one** —
  **not applicable.** This item came from a chat request, not an issue; nothing in
  `initial-request.md` records an `## Origin` issue. Nothing is deferred here.

## Follow-up filed

`2026-09-16-add-a-rename-verb-to-tcw-capabilities-and-tcw-taxonomy` — the
`tcw capabilities mv` / `tcw taxonomy mv` verb both the spec and the plan name as
a follow-up to file rather than fold in. Its intake records what the missing verb
cost this item specifically: 30 regenerated ids, a by-hand body copy per entry, and
three ordered passes with `check` after every removal because
`tcw taxonomy rm` only warns about a dangling `relatesTo`.

## What verification would tell the next item

Two things worth carrying forward, both already in `outcome.md`:

- **A `tcw://` ref is a capability path, not prose.** `tcw validate` resolves refs
  inside a capability body, so a rename that rewrites a skill name inside one
  breaks validation until the ledger moves. The plan asserted the opposite and was
  wrong; task 8 found it.
- **"Exclude the work board" and "exclude the work board's artifacts" are
  different rules**, and the looser one hid a stale pointer in `docs/work/dod.yaml`
  until closeout. Rule 7 protects lifecycle artifacts; it does not protect a node's
  live configuration that happens to live beside them.
