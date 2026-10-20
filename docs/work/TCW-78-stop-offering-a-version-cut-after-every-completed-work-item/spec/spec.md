# Spec — Stop offering a version cut after every completed work item

## Capability changes

**Changed.** Four existing records under `docs/capabilities/`, all describing
behavior that is being narrowed rather than removed:

- `work/customize-the-definition-of-done` — the built-in checklist drops from
  five items to four; the description names all five verbatim.
- `work/read-the-documentation-gate-for-a-change` — the gate's "three invocation
  points, only two of them stages" framing becomes two points, both stages.
- `skills/documentation-sync` — "in a TCW project the lifecycle uses it three
  times" becomes twice, and the after-completion use is deleted.
- `skills/extras-autonomous-work` — its description says the unattended
  procedure decides "when a version is cut"; nothing decides that any more.

**New.** None. **Removed.** None — no capability disappears. A user can still
cut a version; they ask for one.

No records are written at this stage; the ledger is reconciled at completion.

## Problem

TCW tells an agent to volunteer a version cut every time a work item completes.
The requester dismisses it every time, which is the definition of a prompt that
costs attention and returns nothing.

The instruction is stated in **`tcw/work/prompts/verify.md:30`**, step 9 of the
default `verify` stage:

> 9. After `complete`, **offer** a version cut if the change set warrants one —
>    the user's call, after the item closes, never during implementation.

"if the change set warrants one" is the only brake, and it is a judgment the
agent makes about the user's release cadence — a thing the agent cannot know.
The practical result is that the offer fires on essentially every completion.

Four further layers restate or enforce it, so deleting only the prompt line
would leave the behavior intact:

1. **`skills/work/references/lifecycle/stage-verify.md:31`** — step 5 names the
   option menu ("major / minor / patch, or keep the current version …, or —
   when the last tag was cut locally and never pushed — fold this work into that
   unpublished version") and routes to the documentation-sync procedure.
2. **`tcw/work/procedures/documentation-sync.md:50`** — the section
   `## When to offer version and changelog options`, which holds the substance:
   the four options, the fifth fold-in option, and the
   `scripts/unpushed-version.sh` exit-code gate that decides whether to show it.
3. **`tcw/store/base.py:2481`** — `version offered` is the fifth entry of
   `DEFAULT_DOD`, the built-in Definition of Done every node inherits.
   `tcw/store/fs.py:5189` returns it when no `dod.yaml` exists, so
   `tcw work complete --resolution done` prints it as a checklist line and will
   not accept `--confirm` until it is acknowledged. **This is the part that
   makes the offer feel mandatory rather than advisory.**
4. **`skills/documentation-sync/SKILL.md:25`** — the lifecycle table row
   "After `complete` — Offer the version options; run the cut if the user picks
   a bump", plus the skill's `description` (`:3`) and its summary line (`:60`).

The same five words are copied into places that must move with them:
`docs/work/dod.yaml:16` (this repo's own checklist, which **replaces** the
built-in list rather than extending it), `web/client/src/ui/content-views.tsx:1222`
(the web app hard-codes the default checklist for its completion dialog),
`docs/guide/work.md:203` and `:508`, `skills/work/references/transitions.md:116`,
`skills/configure/references/work.md:118`, and
`tests/test_serve_write.py:1064`. The default `verify` prompt is embedded
verbatim in `tests/fixtures/prompt_fallback/unconfigured.json:59`, so the prompt
and that fixture move together or the fallback test fails.

Two more sites describe the offer from a distance:
`skills/commands-drive-work-to-completion/SKILL.md:36` tells a closeout to
confirm "the version choice"; `README.md:689` advertises that documentation-sync
"offers a version bump when work is done".

## Goals

1. No instruction anywhere tells an agent to **volunteer**, **offer**, or
   **present options for** a version cut — at completion or at any other point.
2. `version offered` is no longer a Definition of Done item, built-in or in this
   repo's `dod.yaml`, so no completion asks about it.
3. Everything needed to **perform** a cut when the user asks remains present,
   reachable, and correct: `skills/documentation-sync/references/cut-version.md`,
   `scripts/cut_version.py`, and
   `skills/documentation-sync/scripts/unpushed-version.sh` with its test.
4. The fold-into-an-unpushed-tag judgment survives the removal of the menu it
   was an option on. It is a real question when the user asks for a cut; it must
   not be deleted along with the offer that used to raise it.
5. Documentation, the guide, the README, the web app and the capability ledger
   describe the behavior that now exists.

## Non-goals

- Changing how a version is cut: the five-file lockstep, `cut_version.py`, or
  the changelog/release-note rotation. Untouched.
- Deleting `unpushed-version.sh`, `tests/test_unpushed_version_script.py`, or
  `skills/documentation-sync/references/cut-version.md`.
- Removing the `tcw work docs` verb. Its docstring justifies it by the gate's
  *three* invocation points; the count changes, the verb does not. It is still
  the read-only accessor the skill calls first and the web app reads.
- Changing the documentation gate at `plan` or at the end of `implement`. Those
  two invocation points are unaffected — this item removes only the third.
- The backlog item
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
  It serves *how* a project cuts a version from config, which matters more once
  cuts are only ever user-initiated. It stays open; only its prose that refers
  to "the completion options" needs a later touch, recorded as a follow-up.

## Design

**The offer is deleted; the procedure is rewritten, not deleted.**

1. **`tcw/work/prompts/verify.md`** — delete step 9 entirely. Step 8 (the
   post-mortem offer) is unaffected and stays the last step. Regenerate
   `tests/fixtures/prompt_fallback/unconfigured.json` from the new prompt text.

2. **`skills/work/references/lifecycle/stage-verify.md`** — delete step 5. The
   remaining four items renumber. Nothing replaces it: the stage no longer has
   a version responsibility to describe.

3. **`tcw/work/procedures/documentation-sync.md`** — replace
   `## When to offer version and changelog options` with
   `## When the user asks to cut a version`, keeping only what a requested cut
   needs and dropping every volunteering instruction:
   - the four-option menu goes (it existed to be presented);
   - the bump-size choice stays, still deferring first to the project's own
     documented version-cut process before the manual ritual;
   - the `unpushed-version.sh` gate stays, re-framed from "before presenting
     the list, run this" to "when the user asks for a cut, run this and say so
     if the last version was never published", with the exit codes
     (`0` foldable · `1` not · `2` remote unreachable — ask) unchanged;
   - the judgment against folding work too large for the version it would join,
     and the absolute bar on rewriting a published tag, both stay.
   The companion-references table row for `references/cut-version.md` (`:48`)
   loses its "or picked a `patch`/`minor`/`major` bump from the completion
   options below" clause.

4. **`tcw/store/base.py`** — `DEFAULT_DOD` becomes four items. The adjacent
   comment about tuple order shifting the stage-letter display belongs to
   `WORK_ARTIFACTS` below it, not to `DEFAULT_DOD`, so removing the last DoD
   entry does not affect `tcw work list`. Mirror the change in
   `web/client/src/ui/content-views.tsx` and in `tests/test_serve_write.py`.

5. **`skills/documentation-sync/SKILL.md`** — drop the `After complete` table
   row, leaving `plan` and end-of-`implement`; reword the `description` line's
   final clause from "Use when offering to cut a new version of a project" to
   the user-asks form; fix `:60`'s summary. Also correct the surviving
   `stage-verify.md` step citation, which already points at the wrong step
   number today.

6. **`skills/documentation-sync/references/cut-version.md`** — its opening
   cross-reference to the removed section is repointed at the renamed one. The
   file's body is otherwise unchanged; it is the thing being preserved.

7. **Descriptive sites** — `README.md:689`,
   `skills/commands-drive-work-to-completion/SKILL.md:36`,
   `skills/work/references/commands.md:77`, `tcw/work/cli.py:1914`'s docstring,
   `skills/work/references/transitions.md:116`,
   `skills/configure/references/work.md:118`, `docs/guide/work.md:203` and
   `:508`, `skills/documentation-sync/scripts/unpushed-version.sh:4`'s header
   comment, and `tcw/work/procedures/unattended-work.md:37`'s "Version choice —
   never cut one" row, which answers a question that will no longer be asked.

8. **History is not rewritten.** `docs/changelogs/v*.md`,
   `docs/release-notes/v*.md`, and completed or backlogged work items keep their
   existing wording; they record what was true then.

### The abstraction litmus test

Nothing here adds or changes a store operation. `DEFAULT_DOD` shrinks by one
string; the Definition of Done is already an abstract list a non-filesystem
store answers identically (`fs.py:5189` is the filesystem adapter's answer, and
a tracker-backed store would answer from its own configuration). No new
filesystem behavior is relied on.

### Harness compatibility

The removal is text in prompts, procedures and skill documents plus one Python
constant, all of which the `tcw` CLI serves identically to Claude and Codex.
Nothing here depends on a Claude-only mechanism, and no requirement moves into
one.

## Acceptance criteria

Each of these is a command whose output decides it.

1. **No offer instruction survives in shipped text.** From the repo root:
   ```sh
   grep -rniE "offer[a-z]*[^.]{0,40}version|version[^.]{0,20}offer" \
     tcw/ skills/ README.md docs/guide/ web/client/src/ --exclude-dir=dist
   ```
   returns no matches. `--exclude-dir=dist` is required: `tcw/serve/dist/`
   holds the minified web bundle, which matches this pattern on unrelated text
   and is a build artifact, not shipped instruction. Run against the tree
   today the same grep returns **14** matches, and every one of them is a site
   this item changes — that list is the work.
2. **The offer is gone from the sites that pattern cannot reach.** It requires
   "offer" within 20 characters of "version", so it misses
   `skills/work/references/lifecycle/stage-verify.md:31` ("the version cut the
   prompt says to offer"). Check that separately:
   ```sh
   grep -rn "version cut" tcw/ skills/ docs/guide/ --exclude-dir=dist
   ```
   returns matches **only** under `skills/documentation-sync/` — the how-to
   deliberately kept — and in the renamed procedure heading. No match in any
   `prompts/`, `lifecycle/` or guide file.
3. **`version offered` is gone from every live checklist.**
   ```sh
   grep -rn "version offered" tcw/ skills/ web/client/src/ docs/guide/ \
     docs/work/dod.yaml tests/ --exclude-dir=dist
   ```
   returns no matches. (`docs/changelogs/`, `docs/release-notes/` and existing
   work items are excluded — they are history.)
4. **The built-in Definition of Done has four items.**
   `python -c "from tcw.store.base import DEFAULT_DOD; print(DEFAULT_DOD)"`
   prints exactly `('tests pass', 'docs synced', 'capabilities reconciled', 'reviewed')`.
5. **A completion prints no version line.** `tcw work complete <slug>
   --resolution done` on a test item prints a four-item checklist and no line
   mentioning a version.
6. **The `verify` prompt ends at step 8.**
   `tcw work stage prompt verify <slug>` contains the post-mortem offer as its
   last numbered step and contains no occurrence of "version".
7. **The cut still works when asked for.**
   `skills/documentation-sync/references/cut-version.md`,
   `scripts/cut_version.py` and
   `skills/documentation-sync/scripts/unpushed-version.sh` all still exist; the
   documentation-sync procedure contains a section whose heading names a
   user-requested cut; and `bash skills/documentation-sync/scripts/unpushed-version.sh`
   still exits `0`, `1` or `2` as before.
8. **The suite is green the way CI runs it:** bare `pytest` from the repo root
   passes, including `tests/test_unpushed_version_script.py`,
   `tests/test_documentation_sync_wiring.py`, `tests/test_skill_lifecycle_parity.py`
   and the prompt-fallback fixture test.
9. **The web completion dialog offers four boxes**, not five, when a node has no
   `dod.yaml` — read from `content-views.tsx`, and `pnpm prettify:check` is no
   worse than it is on a clean checkout today.

## Risks

- **Over-deletion.** The obvious failure is deleting the fold-into-an-unpushed-
  tag logic along with the menu it hung off, leaving a user who asks for a cut
  silently stacking a second release on an unpublished one. Goal 4 and
  criterion 7 exist to catch this. `unpushed-version.sh` and its test are named
  as non-goals for the same reason.
- **A shrinking default checklist is silent.** `dod.yaml` replaces rather than
  extends the built-in list, so any node that copied the five defaults into its
  own file keeps asking about a version cut after this lands. That is correct —
  their file, their checklist — but it means the change does not propagate to
  existing configured nodes. The requester was asked and **declined** a release
  note calling this out, so the changelog entry states the change plainly and
  says nothing about configured nodes. This repo's own `docs/work/dod.yaml`
  does drop the line, by the same decision.
- **Under-removal.** The instruction is restated in eight or nine places; a
  partial removal leaves an agent reading a menu that the prompt no longer
  introduces, which is more confusing than leaving it alone. Criteria 1 and 2 are
  repo-wide greps rather than a file list for exactly this reason.
- **Prompt/fixture skew.** `unconfigured.json` embeds the verify prompt
  verbatim; forgetting it turns a documentation change into a red suite.
- **`tcw work docs`'s rationale weakens.** Its docstring justifies the verb by a
  third, non-stage invocation point that is being deleted. The verb is still
  needed, but the justification has to be rewritten rather than trimmed, or the
  next reader will propose removing the verb.

## Notes

The sweep for sibling sites was repo-wide (`grep` across `tcw/`, `skills/`,
`docs/`, `web/`, `tests/`, `.codex-plugin/`, `.agents/`), not narrowed to the
files named in the request. It found five sites the request did not: the
Definition of Done default, the web app's hard-coded copy, the guide's two
listings, the drive-to-completion command skill, and the unattended-work
procedure's "never cut one" row.

Two scoping decisions were taken by the requester before this spec was written
and are recorded in `initial-request.md`: the removal comes out of TCW's shipped
defaults rather than this repo's configuration alone, and the version-cut
machinery is kept and stays reachable on request.
