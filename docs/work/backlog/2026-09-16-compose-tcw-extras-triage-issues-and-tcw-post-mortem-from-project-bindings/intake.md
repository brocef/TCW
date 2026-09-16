# Compose tcw-extras-triage-issues and tcw-post-mortem from project bindings

Child 5 of the epic
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Blocked by children 1 and 2. Spec this against what child 2 actually shipped.

## What to deliver

- Convert `skills/tcw-extras-triage-issues/SKILL.md` and
  `skills/tcw-post-mortem/SKILL.md` to compose from the procedure mechanism,
  today's text as the default.
- **Answer the forge question.** `gh` is hard-required by
  `tcw-extras-triage-issues` ("Do not fall back to scraping the web UI") and
  honestly declared in its frontmatter, while the tracker axis is abstracted
  behind `work.tracker`. Decide whether the forge becomes a binding or stays
  declared and required, and record why.
- For `tcw-post-mortem`, the stage ladder it reasons over is fixed under Rule 1;
  only the conduct moves. Update `agents/tcw-post-mortem.md` to match whatever the
  skill becomes.
- Ledger: `changed:` entries for both skills.

## Constraints

- Do not change the marker key (child 1 owns it).

## Acceptance criteria carried from the epic

Epic criteria 8 and 11 for these two skills.

## Origin

Opened by the epic's `implement` stage (plan task 5) on 2026-09-16.
