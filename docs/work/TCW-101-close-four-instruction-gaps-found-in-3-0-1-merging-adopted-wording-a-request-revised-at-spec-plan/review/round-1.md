---
verdict: accepted
judges: 1
---
# Review round 1 — TCW-101

A multi review by a separate, read-only agent (its own review, Codex, and the
local model `bllm`), of `a9af1395`. Its findings were fixed in `abc2e66c`;
this round records them and the state at `6a91ff29`.

## The three reviews

- **Codex**: two read-only runs (header `sandbox: read-only`). The general
  review found nothing. A second run with five numbered questions agreed with
  findings 2, 3 and 4; its one other claim, about a capability record, was
  rejected because the text predates this change.
- **bllm**: no answer. It waited about 30 minutes behind other sessions'
  reviews; the reviewer stopped it and filed a `bllm report`.
- **The reviewer's own findings**, all confirmed against the code:
  1. Plan step 6 put "record" before "edit". In a project that keeps its work
     in files, the edit writes `item.yaml`, so the next filing was refused.
     **Fixed**: edit, then record.
  2. The spec's new bullet contradicted the existing amendment rule
     (`skills/work/references/commands.md`). **Fixed**: it points to that rule.
  3. The steps assumed every filing makes an item. **Fixed**: a ticket key in
     place of a slug means no item exists there yet.
  4. A Jira child project accepts as parent only a ticket on its own site.
     **Noted** in step 6 and in the multi-repo guide; the real fix is recorded
     on TCW-103.
  - Notes, fixed: `skills/configure/references/projects.md` gains the
    next-filing sentence; a repeated sentence in `commands-plan-work` removed.

## Acceptance criteria, at `6a91ff29`

1. **Met.** The Jira request passage says to keep everything else in the
   description (`test_jira_request_keeps_what_the_requester_did_not_change`).
2. **Met.** The spec prompt's "Exit badly" has the revision bullet: stays at
   spec, recorded as an amendment, both backends' forms
   (`test_spec_says_what_to_do_when_the_requester_revises_the_request`).
3. **Met.** `commands-plan-work` says the plan prompt's advance line does not
   apply under it (read).
4. **Met.** Plan step 6 gives `--project`, then `tcw work edit`, then version
   control, and covers a ticket key in place of a slug
   (`test_plan_says_how_to_file_a_part_into_another_project`). The `work`
   skill says the same (read).
5. **Met.** A Jira filing that makes an item reports the next-filing warning
   (`test_a_creatable_folder_makes_the_item`).
6. **Met, with two exceptions explained.** Full suite, bare `pytest`, at
   `6a91ff29`: `2 failed, 5160 passed, 118 skipped`. The two failures are
   `test_a_hanging_cli_is_abandoned_silently`, a timing test. Neither it nor
   the script it tests has changed since v3.0.1, which passed it locally and
   in CI. It fails on this machine now at a load average of 7, taking 6
   seconds against a 4-second limit. CI judges it on publication.
   `tcw validate`: clean.

## Repository review rules

- Suite as CI runs it: above.
- `documentation-sync`: fired entries answered (changelog, release notes,
  multi-repo guide, `work` skill, projects reference); no configuration key
  changed.
- Not from a GitHub issue.
