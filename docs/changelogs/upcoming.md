# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `work.tracker.transitions` accepts `submit`, `rework`, `complete` and `discard`
  alongside `claim`, naming the transition each move applies. `discard` takes one
  name or one per discard resolution, and may be partial. A named transition that
  the ticket does not offer, that matches more than one offered transition, or that
  leads to a status other than the mapped one is refused before anything is sent.
  Validation is shape-only, as for `statuses`.
- `tcw work tracker link --sync-status`: for an item past `backlog`, records a
  `pending`/`claim: owed` sync record and delivers it at once — the claim, then one
  transition straight to the item's mapped status when offered, otherwise one per
  mapped status, re-reading between hops, and writes `catch-up: true` on the binding.
  Forward-only: no claim transition is applied to a ticket already past `active`
  (one assigned to the caller carries on from where it is — refused if resolved, and
  under strict mode, when it is on the `active` status itself, only if the claim would
  be exclusive; any other is refused), a
  ticket past its item is refused, and a resolved ticket is never moved. Refused for
  an item somebody else started. What does not arrive stays recorded for `tracker
  sync`, which resumes a walk the claim finished but a later hop did not, and aims at
  the item's current status rather than the recorded move's. Only a `catch-up`
  binding is walked through more than one status; every other delivery, including
  an owed claim from a failed `start`, is followed by one transition as before.
- A shared rung in the ladder (two local statuses mapped to one tracker status) is
  named for the higher local status, so its hop uses that move's named transition.
- A plain `link` of an item past `backlog` changes nothing in the tracker. When the
  ticket's status differs from the item's mapped one, it warns and writes
  `status-synced: false` on the binding (not part of `--json`). While that note
  stands, a move refused only because the ticket's status is out of its window is
  `held` with the `--sync-status` repair instead of `conflicting`, and records
  nothing; another holder, an unclaimed ticket whose status is in step, and
  transition-name refusals stay `conflicting`. Strict mode's refusal names the same
  repair. The note clears once a delivery — or a checking `sync` — finds the ticket
  where its item says.
- **`tcw work stage validate [words…]`** (`tcw/work/cli.py`): reports whether a
  `tcw-work-stage` invocation's arguments are ones `tcw work stage prompt` would
  accept — a known stage id, no item for `inbox`, otherwise an optional
  reference resolving to exactly one item; status is not judged. Valid: no
  output, exit 0. Invalid: a Markdown usage error plus the reason on stdout,
  exit 1 (`_resolve`'s stderr message is captured into the reason). Under a
  harness other than Claude Code, a notice that injected commands must be run
  by hand is printed first, even when valid.
- **`tcw/harness.py`**: `ancestor_programs()` walks the process's ancestors via
  `ps`, falling back to `/proc`, and never raises; `detect()` returns the
  nearest `claude`/`codex` ancestor's harness, else `other` when
  `CODEX_THREAD_ID`, `CODEX_SANDBOX` or `CODEX_SESSION_ID` is set, else
  `claude`.

## Changed

- `skills/tcw-work-stage/SKILL.md` injects
  `` tcw work stage validate -- $stage $item 2>/dev/null || true `` ahead of its
  heading. `2>/dev/null` keeps an older `tcw` without the verb silent; named
  arguments rather than `$ARGUMENTS`, because extra words reaching the shell
  unquoted could make the line exit non-zero and cancel the skill load.
- `skills/tcw-work/SKILL.md` and `references/commands.md` no longer link or name
  the `references/lifecycle/stage-*.md` documents. The router sends agents to
  `tcw-work-stage` in an emphasized note; `commands.md` gains a `validate` row.
- `tcw-commands-plan-work`, `tcw-commands-verify-work`,
  `tcw-commands-process-inbox`, `tcw-commands-drive-work-to-completion`,
  `tcw-post-mortem` and `tcw-extras-triage-issues` invoke `tcw-work-stage`
  instead of reading stage documents. `agents/tcw-verifier.md` names the
  `verify` stage rather than its file.
- `skills/tcw-work/references/procedures/delegation.md`, `epic-deltas.md` and
  `commands.md` no longer describe "the stage documents" as what to follow or
  hand a subagent; they name the stage as `tcw-work-stage` delivers it.
- `stage` subparser metavar is `{prompt,gate,validate}`.
- `skills/tcw-work-stage/SKILL.md` headings renamed: "How to work it" →
  "Lifecycle stage contract", "What this project asks for" → "Stage
  instructions", "Before you act on any of that" → "Stage pre-checks" (now one
  line: run `tcw work stage gate` if not done). The command block moved to a
  "Document command summary" section listing the injected commands in order,
  with `gate` shown separately as the one to run yourself. `evals/grade.py`
  `BLOCK_HEADINGS` and the `evals/evals.json` case text follow the new headings.

## Fixed

- A discard moves a ticket nobody is assigned; every other move still refuses one,
  and a ticket assigned to another account is still never moved. The post-transition
  read-back no longer demands the ticket be assigned to the caller for resolved work,
  which had turned a successful unassigned discard into `did not reach 'Won't Do': it
  is in 'Won't Do'`, and the progress comment for such a discard is posted rather
  than skipped.
- Drift is judged against the whole path from where the ticket was left to the move's
  target, so a hand move to an intermediate mapped status is accepted instead of
  reported as drift. The path is walked toward the target rather than derived by
  inverting the status mapping, which is ambiguous when `completed` and `discarded`
  map to one name.
- `tcw work tracker sync <slug>` exits 1 when the named item was started by somebody
  else and still carries a sync or comment record, naming it and `TCW_WORK_OWNER`;
  with nothing recorded, and under `--all`, it still exits 0. Strict
  mode's refusal names the owner to run as, so its "run sync" advice can no longer
  end in a silent success.
- Messages distinguish an unassigned ticket from one somebody else holds.
- `skills/documentation-sync/SKILL.md` cited steps 4, 6 and 9 of the stage
  documents; they are steps 1, 3 and 5.

## Removed

- `skills/tcw-work/references/lifecycle/default/README.md`, which pointed at
  `tcw/work/prompts/*.md` — files that ship with the Python package, not the
  plugin.

## Internal

- `ladder_steps`/`ladder`/`forward_from` in `tcw/tracker/sync.py` express the mapped
  statuses as an ordered ladder, used both for the drift window and for the walk.
  `MOVE_ONTO` (the inverse of `MOVE_STATUS`) is shared by the walk and `link`.
- `transitions` keys other than `claim` are unknown to 2.3.0 and earlier, which
  reject the whole tracker block when one is set.
  `assess_move` takes the move it is serving and the transition named for it.
- `tests/tracker_fake.py` records applied transition ids and gains the `AMBIGUOUS`,
  `STRICT_LADDER` and `BROKEN_LADDER` workflows.
- `tests/test_skill_lifecycle_parity.py`: the router test now asserts that
  nothing in `tcw-work` outside `references/lifecycle/` names a stage document,
  the orphan check exempts `references/lifecycle/`, and new tests require the
  bold `tcw-work-stage` note and the validation line as the stage skill's first
  injected command. New `tests/test_harness.py` and
  `tests/test_stage_validate.py`. `tests/test_eval_grading.py` checks that the
  grader's block headings appear in the stage skill.
