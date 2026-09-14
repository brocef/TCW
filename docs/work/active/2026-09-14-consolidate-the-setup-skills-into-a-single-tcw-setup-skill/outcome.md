# Outcome — Give every TCW skill a taxonomy Feature and exactly one capability

**`<base>` for AC 9 is `e29f67bf`**, the commit that moved this item to
`active`. It is the last commit before the first implementation commit, and the
nine deleted bodies were read as they stood there.

The work was started by one developer, paused for a reboot after task 2, and
finished by a second. The second checked tasks 1 and 2 against the plan before
building on them (every acceptance criterion below was re-run after the pause).

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| 1 | `b61a41f5` | The `skill` Vocabulary term and fifteen `<skill>-skill` Features, with the `relatesTo` links from the spec's table. |
| 2, group 1 | `fd2fa882` | `skills/tcw-work`, `skills/tcw-commands-plan-work`, `skills/tcw-commands-drive-work-to-completion`; deleted `work/consolidate-plans`, `work/search-the-work-items`, `work/audit-work-backlog`, `plugin/work-lifecycle`. |
| 2, group 2 | `4beacf96` | `skills/tcw-extras-report`, `skills/tcw-post-mortem`, `skills/tcw-extras-triage-issues`; deleted `plugin/report-an-issue-upstream`, `plugin/run-a-post-mortem`, `plugin/triage-github-issues`; moved the link in `work/complete-a-work-item`. |
| 2, group 3 | `6eca67c4` | `skills/tcw-setup`; deleted `taxonomy/bootstrap-the-taxonomy`, `capabilities/bootstrap-the-capabilities`. |
| 2, group 4 | `16e0f4c2` | The remaining eight capabilities, deleting nothing. |
| 3 | `ce8ab3df` | The item's `capabilities.yaml`: fifteen paths under `new:`, `work/complete-a-work-item` under `changed:`, the nine deleted paths under `removed:`. |
| 4 | `2e5cfaad` | A note on `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` saying its capability delta should name `skills/tcw-work`. |
| Documentation | `f1eb6878` | Entries in `docs/changelogs/upcoming.md` (under "Changed") and `docs/release-notes/upcoming.md`, appended to what the restructure item wrote. |
| Review fixes | `be9c0fc6` | Three wording corrections in capability bodies; see "Review" below. |

Each new capability carries `Status: Supported`, `Feature: <skill>-skill`,
`Subject: skill`, and also `Planning doc` set to this item's slug. The plan did
not ask for `Planning doc`; it was set so each capability points back at the item
that created it, as the ledger's other capabilities do.

### Documentation entries

- `docs/changelogs/upcoming.md` [Any-Code-Change]: fired, written.
- `docs/release-notes/upcoming.md` [Public-API]: fired, written.
- `README.md` [Public-API]: did not fire. `git grep` for the nine deleted paths
  outside `docs/work/` and past changelogs finds nothing in the README, guides,
  skills or tests; the only similar strings are procedure file names in
  `skills/tcw-work` (`audit-backlog.md`, `consolidate-plans.md`), which are not
  capability paths.
- `skills/<component>/SKILL.md` [Skill-Driven-Component]: did not fire; no CLI
  change.
- `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change]: did
  not fire; no configuration key changed.

## Tests

Acceptance criteria, run from the worktree root after the last content commit:

- **AC 1.** `tcw taxonomy show skill` exits 0.
- **AC 2.** A loop over the fifteen Feature paths: every `tcw taxonomy show`
  exits 0, prints `kind: Feature`, and prints a `vocabulary:` line with exactly
  the row's terms.
- **AC 3.** Every `relatesTo` in the table is printed by `tcw taxonomy show` for
  its Feature; `tcw taxonomy check` prints `taxonomy OK` and exits 0.
- **AC 4.** A loop over `ls skills` (fifteen directories): every
  `tcw capabilities show skills/<s>` exits 0 and prints `**Status:** Supported`
  and `**Feature:** <s>-skill` once each.
- **AC 5.** `tcw capabilities show` exits 1 for all nine deleted paths.
- **AC 6.** `grep -rl -- '-skill' $(tcw capabilities path) | grep -v '/skills/'`
  prints nothing, and `git grep -nE '^- skill$|Subject: skill' -- docs/capabilities`
  finds nothing outside `docs/capabilities/skills/`. The reviewer separately
  parsed every `meta.yaml` outside `skills/` and found no `-skill` Feature and no
  `skill` Subject.
- **AC 7.** `description.md:22` of `work/complete-a-work-item` contains
  `tcw://C/skills/tcw-extras-triage-issues`; `grep -rn
  'tcw://C/plugin/triage-github-issues' docs/capabilities` finds nothing.
- **AC 8 (narrowed, see Corrections).** The narrowed grep prints nothing (exit 1).
  The spec's own grep prints exactly one line, the AC 7 link.
- **AC 9.** Checked by reading; see below.
- **AC 10.** `tcw capabilities check` prints `capabilities OK`; `tcw validate`
  prints `validate OK`; bare `pytest` from the worktree root at `be9c0fc6`:
  `3092 passed in 772.57s (0:12:52)`, exit 0.

Task 3's gate. `tcw work show <slug>` reads the item without error (the plan's
proof), but `show` does not exercise `capabilities.yaml`, so the completion gate
itself was also called: `capability_gate` from `tcw/work/recursion.py` returned
`[]`. To confirm it actually reads the `removed:` list, a still-existing path
(`work/complete-a-work-item`) was added under `removed:` temporarily; the gate
then reported `declared (removed) but still resolves`, and the file was restored
before committing.

### AC 9 — nothing lost

Each deleted body at `e29f67bf`, against its successor. Mentions of slash commands
(`/tcw-consolidate-plans`, `/tcw-work-search`, `/tcw-audit-work-backlog`,
`/tcw-post-mortem`, `/tcw-triage-issues`, `/tcw-taxonomy-init`,
`/tcw-capabilities-init`) and of the old skill names were dropped on purpose,
because the restructure item removed them.

- **`plugin/work-lifecycle`**, split:
  - planning a request into a work item, recording artifacts in the item folder,
    and asking for reference material while writing the request →
    `skills/tcw-commands-plan-work`, both paragraphs;
  - driving an existing item through the remaining stages and stopping for
    explicit verification before closeout → `skills/tcw-commands-drive-work-to-completion`,
    paragraph 1;
  - bounded stage documents, reading the manifest first, loading only the relevant
    stage with its checks before and after, and dependencies giving order and
    parallelism without becoming lifecycle state → the same, paragraph 2.
- **`work/consolidate-plans`** → `skills/tcw-work`, "Consolidating external plans
  into work items": agent-driven because it needs judgment; same under either
  harness (the section's introduction); default search excluding `docs/work/`;
  one backlog item per accepted plan with content kept as artifacts; the old-file
  to new-slug report; optional deletion with one grouped approval naming every
  path; only committed files deleted; untracked or uncommitted sources reported and
  left.
- **`work/search-the-work-items`** → `skills/tcw-work`, "Searching the work items
  by description": what to look for, ignore and sort by; judgment over substring
  matching; live board by default and closed work when asked; connected projects
  with qualified addresses; the board's columns copied rather than recomputed;
  saying how the description was read and when nothing matched; changing nothing.
- **`work/audit-work-backlog`** → `skills/tcw-work`, "Auditing and pruning the
  backlog": the structured report; the categories (completed, stale, outdated,
  misplaced, duplicated, blocked without a next step, too vague); unrecorded
  dependencies stated in prose; recommending actions rather than changing items.
- **`plugin/report-an-issue-upstream`** → `skills/tcw-extras-report`: feedback
  about TCW goes to its GitHub tracker, not the local work store; the two
  skeletons; searching for duplicates; asking for the version for a bug; the
  generic example that keeps private project details out; reproduction from a
  clean install in a subagent; all of it guidance. "There is no slash command"
  became "Claude and Codex both invoke the skill directly".
- **`plugin/run-a-post-mortem`** → `skills/tcw-post-mortem`: the triggers;
  reading the artifacts backwards with `## Notes` as the trail; "nobody could have
  known" against "nobody checked"; writing `post-mortem.md` without changing
  status, so it runs in review and after completion; the read-only agent under
  Claude and inline under Codex.
- **`plugin/triage-github-issues`** → `skills/tcw-extras-triage-issues`, all four
  paragraphs carried, including the link to `work/customize-the-definition-of-done`
  and the closing rules for each resolution.
- **`taxonomy/bootstrap-the-taxonomy`** → `skills/tcw-setup`, "Starting a
  taxonomy".
- **`capabilities/bootstrap-the-capabilities`** → `skills/tcw-setup`, "Starting a
  capabilities ledger". Its added sentence, that a missing taxonomy is started
  first, is backed by `skills/tcw-setup/references/capabilities.md` ("## 0.
  Taxonomy first").

Fields lost with the deleted `meta.yaml` files: the old ids, the old `Planning doc`
values, and `Subject: work-item/lifecycle-stage` on `plugin/run-a-post-mortem`.
The Subject now reaches the capability through its Feature,
`tcw-post-mortem-skill`, which lists that term; the rest only pointed at history.

## Corrections

- **AC 8's grep matches the link AC 7 requires.** `/tcw-[a-z-]+` matches the
  `/tcw-extras-triage-issues` inside `tcw://C/skills/tcw-extras-triage-issues`, so
  the two criteria cannot both hold as written. AC 8 was narrowed to exclude only
  that link form, by replacing `/tcw-[a-z-]+` with
  `(?<!tcw://C/skills)/tcw-[a-z-]+`:

  ```sh
  git grep -nP 'tcw-plugin|(?<!tcw://C/skills)/tcw-[a-z-]+|tcw-work-stage-(request|spec|plan|implement|verify)|(?<![-\w])autonomous-work|(?<![-\w])tcw-triage-issues|(?<![-\w])tcw-report' -- docs/capabilities docs/taxonomy
  ```

  To confirm the narrowing still catches a slash command, `echo 'run
  /tcw-audit-work-backlog' | grep -P '(?<!tcw://C/skills)/tcw-[a-z-]+'` matches.
- **The link is on line 22, not line 20.** The spec and plan both say
  `docs/capabilities/work/complete-a-work-item/description.md:20`; the link is on
  line 22.
- **`Planning doc` was also set** on each new capability, which the plan did not
  list (see "What shipped").
- **The deletion form.** The plan deferred to "the form the delete item defined".
  That form is a `removed:` key in `capabilities.yaml`
  (`skills/tcw-capabilities/SKILL.md:37-39`, enforced by `capability_gate` in
  `tcw/work/recursion.py`), which is what task 3 used.
- **Task 4's target had no `## Notes` section**, and its body document is
  `intake.md` (the item has no `initial-request.md`). The section was added at the
  end of `intake.md`, after the quoted issue, leaving `## Origin` untouched.
- **The plan's documentation section names "Task 5" and "Task 6"**, which do not
  exist. They were done as the documentation pass after task 4.
- **Task 3's stated proof was too weak** to show the gate reads the file; the gate
  was run directly, as described under "Tests".

## Review

One `adversarial-code-reviewer` round over `git diff main..HEAD`, with `spec.md`
and `plan.md`. It found no structural defect (taxonomy, `capabilities.yaml`,
references to deleted paths, AC 6 and AC 9 all clean) and ended NOT DONE on three
wording findings. Each was checked against the skill it describes.

- **Accepted: `skills/tcw-configure` said the skill "points me to one document for
  each area".** `skills/tcw-configure/SKILL.md` sends about twelve areas to five
  documents, `work.md` alone answering five rows of its routing table. Now "the document that covers each
  area". Fixed in `be9c0fc6`.
- **Accepted: `skills/tcw-work` said the skill "never has me edit the work store by
  hand".** `skills/tcw-work/SKILL.md:14` says never hand-edit the store *when a
  command exists*, and lifecycle documents are written by hand. Now qualified "where
  a `tcw` command does the job". Fixed in `be9c0fc6`.
- **Accepted: `skills/tcw-extras-report` said it "asks for the installed version
  first".** `skills/tcw-extras-report/SKILL.md` lists searching for an existing issue
  first and asks for the version only for a bug, third. The claim came word for word
  from the deleted body, so AC 9's reading did not catch it. Reordered. Fixed in
  `be9c0fc6`.
- **Rejected: the drive capability's "what can run in parallel" might be
  unsupported.** `docs/guide/work.md:397-398` says stage-document dependencies
  "communicate ordering and parallelism", so the sentence is backed.
- **Not changed, a judgment call: the deletions are listed under "Changed" in the
  changelog** rather than "Removed". The plan put them under "Changed", and they sit
  in one entry with the successors they folded into, which reads more clearly than
  splitting them.
- **Needs a separate change: `work/run-a-lifecycle-stage` still has two paragraphs
  mainly about the `tcw-work-stage` skill**
  (`docs/capabilities/work/run-a-lifecycle-stage/description.md`), overlapping
  `skills/tcw-work-stage`. The spec left that capability to the restructure item on
  purpose, but Goal 2 ("no second capability describes the same skill") is only
  partly met there, and the two texts can drift apart.
- **Needs a separate change, already true before this item:** the issue-closing
  rules appear in both `work/complete-a-work-item` and
  `skills/tcw-extras-triage-issues`.

## Notes

- `tcw work show` prints only the start of an item's body, so the note added by
  task 4 does not appear in its output; it is in the committed `intake.md`.
- `tcw work scaffold outcome` writes `outcome.draft.md` and stages it; it was
  renamed to `outcome.md` with `git mv`.
