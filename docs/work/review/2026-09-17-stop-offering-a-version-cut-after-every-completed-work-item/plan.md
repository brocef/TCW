# Plan — Stop offering a version cut after every completed work item

Eight code tasks, then one documentation block. Ordered so bare `pytest` is
green at every commit boundary: each task that moves text also moves whatever
pins that text, in the same commit.

## Task 1 — Delete step 9 from the default `verify` prompt, and re-baseline the fixture

**Modifies:** `tcw/work/prompts/verify.md`,
`tests/fixtures/prompt_fallback/unconfigured.json`.

Delete step 9 in full (`tcw/work/prompts/verify.md:30-31`). Step 8, the
post-mortem offer, becomes the last numbered step; nothing renumbers. Leave the
`## Exit badly` and `## When this stage's output is written` sections alone.

The fixture embeds this prompt verbatim, so it moves in the same commit. It is a
tripwire, not a description — `tests/test_prompt_fallback.py`'s docstring and
`tests/fixtures/prompt_fallback/capture.py`'s both say re-capture only when a
release intends the text to move, and say which one. This release does. Follow
the precedent those docstrings set:

```sh
python tests/fixtures/prompt_fallback/capture.py /tmp/pf-after
python - <<'PY'
import json
old = json.load(open("tests/fixtures/prompt_fallback/unconfigured.json"))
new = json.load(open("/tmp/pf-after/unconfigured.json"))
# Assert ONLY the verify entry moved.
PY
```

**Proves it:** the diff of `unconfigured.json` touches the `verify` entry and no
other stage's recorded stdout; `pytest tests/test_prompt_fallback.py` passes.
Add a paragraph to `capture.py`'s docstring naming this re-capture and its
reason, as the three previous re-captures each did.

## Task 2 — Delete step 5 from the `work` skill's verify reference

**Modifies:** `skills/work/references/lifecycle/stage-verify.md`.

Delete item 5 (`:31-38`), the one naming the option menu and routing to the
documentation-sync procedure. Renumber any items that follow it. The stage has
no version responsibility left to describe, so nothing replaces it.

**Proves it:** `grep -n "version" skills/work/references/lifecycle/stage-verify.md`
returns nothing; `pytest tests/test_skill_lifecycle_parity.py` passes.

## Task 3 — Rewrite the documentation-sync procedure's version section

**Modifies:** `tcw/work/procedures/documentation-sync.md`.

Replace the heading `## When to offer version and changelog options` (`:50`) and
its body (`:50-75`) with `## When the user asks to cut a version`. What is
deleted, and what survives, is fixed by the spec's Design item 3:

- **Delete** the numbered four-option menu and every sentence that instructs
  presenting it — "present the user with these four options", "Before
  presenting the list", "Don't offer mid-flow, and don't offer for trivial
  in-isolation edits".
- **Keep** the bump-size choice, still deferring first to the project's own
  documented version-cut process and only then to the manual ritual.
- **Keep** the `scripts/unpushed-version.sh` gate, re-framed: run it when the
  user asks for a cut, and tell them if the last version was never published.
  Exit codes are unchanged — `0` foldable, `1` not foldable, `2` remote
  unreachable, ask rather than guess.
- **Keep** both judgments: do not fold work larger than the version it would
  join, and never rewrite a published tag.

Also edit the companion-references table row for `references/cut-version.md`
(`:48`), dropping the clause "or picked a `patch`/`minor`/`major` bump from the
completion options below" — there are no completion options below any more.

**Proves it:** the file contains no form of "offer"; it still contains the
`unpushed-version.sh` invocation and all three exit codes;
`pytest tests/test_documentation_sync_wiring.py` passes.

## Task 4 — Repoint the two cross-references into the renamed section

**Modifies:** `skills/documentation-sync/references/cut-version.md`,
`skills/documentation-sync/scripts/unpushed-version.sh`.

`cut-version.md:3-5` opens by citing the old section by name ("… see 'When to
offer version and changelog options'"). Repoint it at the renamed section and
drop "or has chosen a bump from the completion options" framing; it is now read
when the user asks. The body of the file is untouched — it is the thing being
preserved.

`unpushed-version.sh:4`'s header comment says it "answers the gate for option 5
of documentation-sync's version options". There is no option 5. Reword it to
describe what it answers: whether the last version tag is still local, and so
whether work since it can join it instead of stacking a new release on top.
**The script's behavior and exit codes do not change.**

**Proves it:** `pytest tests/test_unpushed_version_script.py` passes unchanged;
`bash skills/documentation-sync/scripts/unpushed-version.sh; echo $?` still
exits `0`, `1` or `2`.

## Task 5 — Drop `version offered` from the Definition of Done

**Modifies:** `tcw/store/base.py`, `web/client/src/ui/content-views.tsx`,
`tests/test_serve_write.py`, `docs/work/dod.yaml`.

`DEFAULT_DOD` (`tcw/store/base.py:2480-2481`) becomes four items:
`("tests pass", "docs synced", "capabilities reconciled", "reviewed")`. The
comment directly beneath it, about tuple order driving the stage-letter string
in `tcw work list`, describes `WORK_ARTIFACTS` below — not `DEFAULT_DOD` — so
it stays where it is and removing the last DoD entry does not shift any
display. Confirm that by reading the comment's position before editing.

`web/client/src/ui/content-views.tsx:1216-1223` hard-codes the same five strings
as the completion dialog's fallback when a node has no `dod.yaml`. Drop
`"version offered"` there too, or the web app and the CLI disagree.

`tests/test_serve_write.py:1064` passes the five strings as `dod_ack`; drop the
fifth so the test states the current checklist.

`docs/work/dod.yaml:16` — delete the `- version offered` line, by the
requester's decision recorded in the spec. This file **replaces** the built-in
list, so leaving it would keep this repo asking after the default stopped. The
file's header comment says "The five entries below are `DEFAULT_DOD` verbatim";
update it to four.

**Proves it:**
`python -c "from tcw.store.base import DEFAULT_DOD; print(DEFAULT_DOD)"` prints
the four-item tuple; `pytest tests/test_serve_write.py` passes.

## Task 6 — Remove the after-completion row from the documentation-sync skill

**Modifies:** `skills/documentation-sync/SKILL.md`.

Three edits plus one pre-existing error to fix:

- `:25` — delete the `**After `complete`**` table row entirely, leaving `plan`
  and end-of-`implement`. The sentence beneath the table ("One pass at the end,
  not per-task…") still reads correctly with two rows; verify that it does.
- `:3` — the `description` frontmatter ends "Use when offering to cut a new
  version of a project." Reword to the user-asks form, e.g. "Use when the user
  asks to cut a new version of a project." The description is what triggers the
  skill, so it must still match a request to cut one.
- `:60` — "tasks, and offering a version" in the document-command summary;
  reword to drop the offer.
- While in the table: the surviving rows cite `stage-plan.md` step 1 and
  `stage-implement.md` step 3. The deleted row cited `stage-verify.md` **step
  5** while the prompt numbers it step 9 — that mismatch is being deleted with
  the row, so nothing to fix, but do not copy the wrong citation style into the
  rows that remain.

**Proves it:** the file contains no "offer" in a version sense; the lifecycle
table has two rows; `pytest tests/test_documentation_sync_wiring.py` and
`tests/test_skill_lifecycle_parity.py` pass.

## Task 7 — Sweep the descriptive sites

**Modifies:** `README.md`, `skills/commands-drive-work-to-completion/SKILL.md`,
`skills/work/references/commands.md`, `tcw/work/cli.py`,
`skills/work/references/transitions.md`, `skills/configure/references/work.md`,
`docs/guide/work.md`, `tcw/work/procedures/unattended-work.md`.

Each of these describes the offer from a distance and is wrong once it is gone:

- `README.md:689` — the documentation-sync row says it "offers a version bump
  when work is done". Drop that clause; the row's first half still describes
  what the skill does.
- `skills/commands-drive-work-to-completion/SKILL.md:36` — closeout confirms
  "the merge or PR route, the documentation updates, any follow-up items, and
  the version choice". Drop "and the version choice".
- `skills/work/references/commands.md:77` and `tcw/work/cli.py:1909-1917` — both
  justify the `tcw work docs` verb by the gate running at **three** points, the
  third being the version offer after `complete`. The verb stays; **rewrite**
  the justification rather than trimming it to "two points, both stages", which
  would invite the next reader to delete a verb the skill and the web app both
  call. Say plainly that it is the read-only accessor for a node's
  documentation entries, used by the skill before any stage prompt is resolved
  and by the web app, and that the stage prompts inline the same entries.
- `skills/work/references/transitions.md:116` and
  `skills/configure/references/work.md:118` — both list the five built-in DoD
  items. Make them four.
- `docs/guide/work.md:203` and `:508` — the sample `dod.yaml` and the sample
  printed checklist. Drop the line from both. The surrounding prose says "those
  five are the defaults" (`:206-207`); make it four.
- `tcw/work/procedures/unattended-work.md:37` — the row "Version choice — Never
  cut one. Accumulate into `upcoming.md` and move on." Delete the row: it
  answers a question the unattended run is no longer asked. Keep the
  `upcoming.md` accumulation instruction if it is not already stated elsewhere
  in that table; check before deleting, and move it into the neighbouring
  documentation row if it would otherwise be lost.

**Proves it:** the spec's acceptance criteria 1, 2 and 3 — the three greps —
return clean.

## Task 8 — Reconcile the capability ledger

**Modifies:** `docs/capabilities/work/customize-the-definition-of-done/description.md`,
`docs/capabilities/work/read-the-documentation-gate-for-a-change/description.md`,
`docs/capabilities/skills/documentation-sync/description.md`,
`docs/capabilities/skills/extras-autonomous-work/description.md`.

Four changed records, as the spec's Capability changes section names them. Each
is a description edit, not a new or removed record:

- `customize-the-definition-of-done` — "the built-in five apply" and the list
  become four.
- `read-the-documentation-gate-for-a-change` — the "version offer *after* an
  item completes" clause goes; the gate has two invocation points, both stages.
- `skills/documentation-sync` — "uses it three times" becomes twice; delete the
  after-completion clause and the "offers a version" phrasing in both
  paragraphs.
- `skills/extras-autonomous-work` — "and when a version is cut" goes from the
  list of what the unattended procedure decides.

Run this task with the `capabilities` skill rather than editing blind, so the
ledger's own conventions are followed.

**Proves it:** `tcw validate` reports no new problems; the four descriptions
contain no version-offer wording.

## Documentation Sync

One pass over the finished diff, after Tasks 1–8, before `outcome.md`.
Evaluated against this node's entries (`tcw work docs`):

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | **Public-API** | **Yes** — user-facing behavior changes and the skill table is edited. Already handled in Task 7; re-read the surrounding section for anything else that promises the offer. |
| `docs/guide/jira.md` | **Tracker-Change** | No. No tracker command, ticket behavior, or `work.tracker` key changes. |
| `docs/release-notes/upcoming.md` | **Public-API** | **Yes.** Plain-language entry: TCW no longer offers a version cut when a work item completes, and `version offered` is no longer a Definition of Done item. Say that cutting a version still works and is done by asking. **Do not** add the caveat about projects whose own `dod.yaml` restates the defaults — the requester was asked and declined it. |
| `docs/changelogs/upcoming.md` | **Any-Code-Change** | **Yes.** Grouped entries: **Removed** — verify step 9, stage-verify step 5, the after-completion row, `version offered` from `DEFAULT_DOD`. **Changed** — the documentation-sync procedure's version section, the `tcw work docs` rationale, the web completion dialog's fallback checklist. |
| `skills/<component>/SKILL.md` | **Skill-Driven-Component** | **Yes** — `documentation-sync` (Task 6), `work`'s references (Tasks 2, 7), `commands-drive-work-to-completion` (Task 7). Confirm each is done, not merely planned. |
| `skills/configure/references/<document>.md` | **Configuration-Key-Change** | **Yes** — `docs/work/dod.yaml`'s built-in default changes meaning, so `skills/configure/references/work.md` is updated (Task 7). |

## Verification

What the suite cannot check, to be confirmed by hand at `verify`:

1. **The three acceptance greps** (spec criteria 1–3) run from the repo root,
   with `--exclude-dir=dist`. No test runs them.
2. **The four-item checklist in a real completion.** Run
   `tcw work complete <a throwaway item> --resolution done` and read the printed
   checklist. Nothing asserts the printed text.
3. **The cut still works when asked for.** Confirm by reading, not running:
   `cut-version.md` still describes the whole ritual, still reaches
   `unpushed-version.sh`, and its opening cross-reference resolves to a heading
   that exists. Do **not** run an actual version cut as verification.
4. **The web dialog.** `web/client/src/ui/content-views.tsx` is checked by
   reading; there is no test asserting the dialog's fallback list. Run
   `pnpm prettify:check` and confirm it is no worse than on a clean checkout —
   it is known to fail there, per a separate backlog item.
5. **Bare `pytest` from the repo root**, which is how CI runs it. A green
   `python -m pytest` is not evidence about CI.

## Notes

**Do not drive the lifecycle with the `tcw` CLI once Task 1 begins.** Tasks 1,
3, 5 and 7 edit `tcw/`, which is the CLI that would be driving. Per this repo's
agent guide, from that point the work system is maintained by editing
`docs/work/` directly — writing `outcome.md` by hand, moving the folder between
status directories, editing `state.yaml` — and the gates, Definition of Done
and tracker sync those commands would have run are performed by hand instead.
Reading verbs (`tcw work show`, `tcw work docs`) stay safe.

**Follow-up, not this item.** The backlog item
`2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
contains prose referring to "the completion options" that this item removes.
It stays open and its premise is strengthened, not invalidated. Record the
wording fix on that item at closeout rather than editing it here.
