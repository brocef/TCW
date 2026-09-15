# Refined outcome — Add a tcw-work-create skill that checks for overlap before creating a work item

## Decision

**Accepted by the user on 2026-09-15**, after a second verify pass. The first
pass was rejected. `rework.md` recorded six findings (A–F) from the
`tcw-verifier` assessment, and all six were fixed (`ec821671`, `ab6e4c3b`).

## Evidence

- **Acceptance criteria 1–7 are met.** The AC 1–3 checks were re-run after the
  rework. The six targeted test files pass (192 passed).
- **Criterion 8 is partly met.**
  - Met: `tcw capabilities check` prints `capabilities OK`,
    `tcw capabilities drift` reports none, `git diff --stat 8b870e96 -- tcw/ agents/`
    is empty, and bare `pytest` passed (3368 at `ab6e4c3b`).
  - Not met: `tcw validate` exits 1 in the worktree over a link to a
    gitignored completed item with no tombstone. That problem predates this item
    and does not occur in the primary checkout.
- **Criterion 9 is met by hand.**
  - Read-only runs (a)–(f). Case (c) ran on an eval fixture, because this
    board's inbox emptied during implementation.
  - The rework's write-path runs (g)–(i) committed a created item, a raw inbox
    entry and an append, with a clean status after each.
  - Run (d) found the active/review ordering defect, fixed in `37037769`.
- **Criterion 10 is open**, as planned. Whether agents invoke the skill on their
  own is **unverified**. B13 and the next backlog audit are the checks, owned by
  `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`.

## Definition of Done

- **Tests pass:** 3368, bare `pytest` at `ab6e4c3b`. The commits after it touch
  only this item's folder.
- **Docs synced:** the README, release notes and changelog (`9ce322ac`, with the
  release note corrected in `ec821671`), evaluated with the `documentation-sync`
  skill.
- **Capabilities reconciled:** `skills/tcw-work-create` is `Supported`, with
  Feature `tcw-work-create-skill`. The `new:` delta in `capabilities.yaml`
  resolves, and no contradiction was found with `tcw-commands-process-inbox` or
  `work/open-a-work-item`.
- **Reviewed:**
  - the spec by a multi review (adversarial spec reviewer and Codex; `bllm` was
    disabled for maintenance);
  - the implementation by `tcw-verifier`, then re-checked after the rework.
- **Version offered:** after `complete`, as the lifecycle requires.
- **GitHub issue:** not applicable. The item came from a chat request.

## Deferred follow-ups

The user chose **not to file** either candidate. Both are recorded here and in
`outcome.md` only:

- no CLI verb adds or amends a work inbox entry, so the skill writes files under
  `tcw work inbox path`;
- `tcw validate` fails outside the primary checkout on a `tcw://W/` link to a
  completed item that `.gitignore` keeps out of Git and that has no tombstone.

## Closeout choices

- **Route:** `tcw work complete --resolution done`, run from the primary
  checkout. It merges `work/2026-09-15-add-a-tcw-work-create-skill-that-checks-for-overlap-before-creating-a-work-item`
  into `main` and removes the worktree. No pull request.
- **Merge overlap:** `2026-09-15-rewrite-the-readme-to-a-new-outline` is active
  on its own worktree and rebuilds the same README skills section. Whichever
  merges second adds the `tcw-work-create` row.
- **Version:** offered after completion.
