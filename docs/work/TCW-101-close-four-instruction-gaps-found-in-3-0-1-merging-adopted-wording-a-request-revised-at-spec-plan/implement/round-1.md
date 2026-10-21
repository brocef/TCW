# Implement round 1 — TCW-101

Commits `a9af1395`, `721c5128` and `abc2e66c`, plus the rename that removed a
private project's name from this item's folder and title.

## What was done, by plan step

1. **Tests first.** Four prompt tests and one delegation-message assertion,
   all red against the old text before the change.
2. **Request** (Jira passage): change only what the requester adopted, and
   keep everything else in the description.
3. **Spec**, "Exit badly": the requester revising the request keeps the item
   at spec. The change is recorded as an amendment: a dated `## Added`
   section on files, an `Added` comment in Jira. This is the existing rule in
   `skills/work/references/commands.md`, "Amending a request".
4. **Cross-project parts**, plan step 6 and the `work` skill:
   - file with `--project`;
   - a ticket key printed instead of a slug means no item exists there yet;
   - otherwise, from inside that project, set `--parent` and `--blocked-by`
     with `tcw work edit` (a Jira project takes only a ticket on its own site);
   - then record everything TCW wrote there in that project's version
     control before filing there again.

   The Jira filing message now says the next filing waits until those files
   are recorded. `skills/configure/references/projects.md` gains the same
   sentence.
5. **commands-plan-work** says the plan prompt's advance line does not apply
   under it. The capability description says the same.
6. **Documentation entries**:
   - changelog and release notes;
   - `docs/guide/multi-repo.md` (case 3, and a paragraph on filing an epic's
     part);
   - the `work` skill;
   - Configuration-Key-Change does not fire.
7. **Suite.** The first full run found four failures. One was another item's
   mid-run edit. Two were real:
   - the message named git, which code strings may not do;
   - the recorded prompt copy (`tests/fixtures/prompt_fallback`) predated
     the change.

   Both fixed, and the recorded copy re-captured twice, each time checked
   by a diff showing only this item's passages moved. Current targeted runs:
   `tests/test_shipped_prompts.py`, `tests/test_shipped_text.py`,
   `tests/test_prompt_fallback.py`, all passed. The final full run is
   recorded in the review round.

## What the plan or spec got wrong

- **Design 4 put "record" before "edit".** In a project that keeps its work
  in files, `tcw work edit` writes the item's `item.yaml`, so the next filing
  was refused. The edit now comes first.
- **Design 4 assumed every filing makes an item.** Several outcomes return
  only a ticket key.
- **Design 2's bullet invented a second amendment rule** ("description and
  comment") that contradicted the existing one. It now follows the existing
  rule.
- **Design 4 said "commit".** Shipped text and code strings may not name git,
  so the wording says "record … in that project's version control".
- **The spec named a private project and ticket.** Removed. The folder and
  title were renamed.

## Records changed

`docs/capabilities/skills/commands-plan-work/description.md`.

## Rejections answered

None written; the review's findings are listed in the review round.
