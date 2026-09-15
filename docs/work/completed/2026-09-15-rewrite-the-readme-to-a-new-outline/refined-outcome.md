# Refined outcome: Rewrite the README to a new outline

## Decision

**Accepted** by the requester on 2026-09-15, after the fixes listed below and
after reviewing the rendered README on GitHub from the pushed work branch.

## Evidence

- **Verifier assessment** (read-only `tcw-verifier` agent, at `ed90d92a`): 20 of
  22 acceptance criteria met. Of the two not met:
    - **Criterion 11** (the Jira example was 15 lines, over the 12-line limit) is
      now fixed. The example is 10 lines, Prettier leaves it unchanged, and
      `parse_tracker_config` reports no problems with it.
    - **Criterion 20** (`tcw validate` failed in the worktree) predated this item.
      After merging `main`, whose graveyard now records the referenced slug,
      `tcw validate` prints `validate OK` in the worktree.
- **Verifier's spot checks:** 18 of 20 factual claims were accurate. Both
  inaccurate ones are fixed (`15fa688a`):
    - `docs/guide/jira.md` said epics are "never gated" under strict mode. It now
      says an epic cannot start with `--worktree` (`tcw/work/cli.py:1005-1013`).
    - The README said the web app accepts changes only from `127.0.0.1`. It now
      names `localhost` and `::1` as well (`tcw/serve/__init__.py:44-46`).
- **Wording fixes in the same commit:**
    - Example 2 said "anyone may hold the ticket" at `link` without saying that
      `start` only claims a ticket that is unassigned or already yours.
    - Undefined terms in `jira.md`: JQL is spelled out, "board" is defined, and
      "landing status" and "gated" are replaced.
- **Lifecycle diagram styled at the requester's request:**
    - Status nodes are one style, and the nodes that are not statuses another
      (`be4b563b`).
    - Transition labels are styled through a Mermaid theme setting, since edge
      labels cannot take a class (`afc5f250`).
    - Rendered in light and dark themes with `@mermaid-js/mermaid-cli@11`, and
      viewed by the requester on GitHub.
- **GitHub rendering:** the branch was pushed with the requester's approval.
  GitHub's rendered HTML for `README.md` has all 28 Contents anchors.
- **Merge with `main`** (`861e907f`):
    - `main` had completed `2026-09-15-add-a-tcw-work-create-skill-that-checks-for-overlap-before-creating-a-work-item`,
      which added `skills/tcw-work-create` and a row for it in the old README's
      skill table. The rewrite's README was kept, with a `tcw-work-create` row
      added to Work › Usage › Skills (a work-axis skill).
    - `outcome.md` followed the item's folder from `active/` to `review/`.
    - `tcw-config.yaml` merged cleanly, gaining `main`'s `work.retain`.
- **Checks after the merge**, run in the worktree:
    - `pytest`: 3369 passed in 14 min 11 s, run at `861e907f`. The two later
      commits only edit an inbox note.
    - The README checker: headings, Contents, Overview length, CLI coverage for
      all three groups, skill and agent rows (16 skills, 3 agents), and relative
      links all pass.
    - Prettier passes on `README.md`, `docs/guide/jira.md` and `docs/guide/work.md`.
    - `tcw validate` prints `validate OK`.

## Capability reconciliation

None needed. The spec declares no capability changes and the item has no
`capabilities.yaml`. `tcw capabilities` entries describing the plugin, the CLI
and the skills are unchanged.

## Definition of Done

- **tests pass:** `pytest` 3369 passed after the merge with `main`.
- **docs synced:** the README and Jira guide are this item's deliverables. No
  other documentation entry was triggered: no CLI surface, behavior,
  configuration key or skill changed.
- **capabilities reconciled:** nothing to reconcile (above).
- **reviewed:** adversarial spec review before planning; `tcw-verifier`
  assessment; requester review on GitHub.
- **version offered:** yes. The requester chose to keep the current version with
  no release-note or changelog entry; the changes ship in the next release.
- **originating GitHub issue:** none; the item came from an inbox entry.

## Deferred follow-ups

All in `docs/work/inbox/2026-09-15-follow-ups-the-readme-rewrite-found.md`:

1. `tcw validate` in a fresh checkout. Resolved on `main` already, and kept in
   the note for the record.
2. The broken `tcw taxonomy add Permission -p admin` example in
   `docs/guide/taxonomy-and-capabilities.md:25`.
3. `tcw/store/fs.py:4964` citing README text that does not exist.
4. `tcw work tracker link --help` saying nothing moves a linked ticket, although
   `start` claims it.

Also still open and outside this item: items 3 and 4 of
`docs/work/inbox/2026-09-11-prose-defects-the-heading-sweep-found.md`, about
`docs/guide/web-viewer.md`, which this item was told not to change.

## Closeout choices

- **Merge route:** `tcw work complete` from the primary checkout merges the work
  branch into `main` and removes the worktree. Then push `main` and delete the
  remote work branch.
- **Version:** keep the current version; no release-note or changelog entry.
- **Retention:** this repository now sets `work.retain.completed: false`, so
  completing removes the item's folder after the completion commit. The
  graveyard entry names that commit.
