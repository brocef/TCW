---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-117

Reviewed by three separate read-only agents (the `tcw:reviewer` agent) on
2026-10-26, in a frozen worktree at `6055731f` (branch `v4` with TCW-117
landed after its rebase), over `87959dac..6055731f`, one each on the guides
(the eight guides, the migration guide, README, use cases, AGENTS.md, the
lifecycle documents), the skills (skills, agents, procedures, evals and every
test the change touches), and the ledger with the acceptance criteria. The
dispatching session checked each finding against the files before writing
this round.

## Checks run

- The full suite as CI runs it, run by the dispatching session on the
  rebased branch at `28e5f555`, recorded in implement round 1: `2246 passed,
  2 skipped` and `5839 passed, 111 skipped, 1 failed` (the worktree's
  `node_modules` link; 120 passed in `v4`); the web checks clean.
- By the reviewers, running each claim through a guarded wrapper in scratch
  families, no Jira: 66 claims in the guides, 58 in the skills, about 15 in
  the ledger. The migration guide followed end to end on a project made with
  3.0.2, and on a child and its parent. Five mutation checks on the changed
  tests, each red for the right reason; 675 and 586 passed on the named test
  files. The released 3.0.2 `tcw validate` on a scratch clone: `0 errors,
  0 warnings, 0 unresolved`. 4.0's `tcw validate` there: 315 errors, each a
  3.x form, as spec 9.8 expects until TCW-118 migrates the repository.
- No private name, machine path or credential in the change.

## Acceptance criteria

Met: 31, 32, 34, 37, 38, 42 (ledger reviewer); 2.3 to 2.10's content is
present in the guides; no test asserts less than before without a reason.
Partly met: 36 (finding 7); 19 and 1.6 (b) (finding 3). Not met as written,
already said by the round: 43. 35 is qa's; 39 is the suite, above.

## Findings

Guides:
1. `docs/migration-guide-3.X-to-4.0.0.md:455-457` and `:584` say a missing
   related project gives exit 7 and that scripts checking 5 should check 7;
   the commonest cases give 5 (`work show core.work/…`, `-C
   tcw://core.path/`, `project path core`, `project provision <id>`), as
   `cli.md:449` and `multi-repo.md:291` say. Exit 7 is for a command that
   needs something the project inherits.
2. `docs/guide/cli.md:202-205` says a covered project that cannot be read
   never stops the command, which exits 0; `capabilities list|show --scope
   up` and `taxonomy list --scope up` exit 7 when the parent is missing.
3. `docs/guide/work.md:238-244`: the example `capabilities.yaml` holds bare
   3.x entries, which 4.0's `tcw validate` refuses.
4. `docs/migration-guide-3.X-to-4.0.0.md:232-233`: the way back restores the
   commit but leaves the untracked `.tcw/` folder and new state files; it
   must say to remove what the run added.
5. Terms used undefined: "gate" (`cli.md:447`,
   `linking-and-validation.md:244`), "deciding manifest entry"
   (`multi-repo.md:315`, `:453`), "load order" (`README.md:277`).

Skills:
6. `skills/setup/references/taxonomy.md:59-61` says a leaf slug may name a
   parent's term; `--vocab` with a parent's term exits 2. The project's own
   terms only.
7. `skills/configure/references/personal.md:28` and the work skill's
   `work.md:42` say the user-wide file "needs no `tcw-version` line"; a
   `tcw-version` line there stops every command (exit 1, `tcw/config.py:648`).
   Say it must not hold one.
8. `skills/capabilities/SKILL.md:204` says exit 5 for a project not on this
   machine; for an unrelated project no manifest lists, it is exit 1.
9. `skills/work/SKILL.md:142` says the refusal names the command to run;
   it prints `tcw -C <folder> …` with a literal "…".
10. Plain language: `skills/setup/references/project.md:68` reads as if three
    commands are spared (only `tcw migrate` is); `skills/work/SKILL.md:150-157`
    in one dense sentence; `agents/backlog-auditor.md:17` writes `<folder>`
    where spec 5.6 (b) gives `<id-path>` and the tracker key.

Ledger:
11. `docs/capabilities/work/open-a-work-item/description.md:1`,
    `docs/capabilities/capabilities/detect-capability-drift/description.md:16`,
    `README.md:256` and `:470` say a work item's folder never moves; 4.0's
    `tcw work move` and `rename` move it. Say it does not move when its stage
    changes.
12. Implement round 1: the commit table names hashes from before the rebase;
    the scan's output is not pasted (criterion 36), and "only P8 hits" holds
    only with the migration exemption: the spec's plain scan finds 14 more,
    each in a paragraph naming `tcw migrate` or the guide (Decision 5).
13. The changelog puts the test-only entries under `## Added`; spec 10.1 says
    `## Internal`. "The epic-parts flow of 3.0.1 and 3.0.2" is unexplained.

## Needs a separate change

Decided by the dispatching session, kept on the 4.0 run's list of small
follow-ups for TCW-118: an unknown project id exits 1 in a full identifier
but 2 under `--project`; a `capabilities.yaml` entry for a project not on
this machine is an error while the item's parent link is unresolved (so
`validate` fails where a sibling is absent); whether the user-wide file
should accept `tcw-version`; `project provision` printing "Nothing to
provision" and then provisioning; the Jira credentials error naming 4.0's
file in a 3.x project; "1 files written".

## What implement must do

Fix 1 to 13 in the files named, checking each new sentence by running it;
write `implement/round-2.md`.
