# Refined outcome: Triage GitHub issues into TCW work items

**Accepted** by the user at `verify`, after a live sweep run at their direction
to close the two criteria the dry run had left unverified.

## The decision

The user rejected accepting on the dry run alone and asked for the live half
first. That was the right call: the live sweep found a **third** defect, and it
was the worst of the three.

## Evidence

All 11 acceptance criteria are now met.

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Skill + command exist, command adds nothing | `4527460`, `7483b60` |
| 2 | Grant covers every instructed verb | Cross-read twice; two gaps fixed pre-commit |
| 3 | Three preconditions stated | SKILL.md §1 |
| 4 | Four outcomes, only one creates an item | SKILL.md §4 |
| 5 | Nothing posted without exact-text approval | Honored in practice — three comments, three approvals |
| 6 | Defers to `stage-inbox.md`; pointer back | `7483b60` |
| 7 | Created items record their issue URL | **Verified live** — `#9` and `#8` items both carry it |
| 8 | Second sweep creates no duplicates | **Verified live** — all three issues report tracked |
| 9 | Capability declared, sidecar lists it | `cap-2c9a74`, now `Supported` |
| 10 | Docs updated | `ed1c71c` |
| 11 | Suite green | `python -m pytest` → **1094 passed** |

`tcw validate` OK · `tcw capabilities check` OK · `tcw capabilities drift` → none.

### What the live sweep did

Two real TCW bugs converted to backlog items (`3defa51`):

- `2026-07-29-resolve-relative-connected-projects-paths-against-the-main-worktree-root` ← issue #9
- `2026-07-29-make-the-reconcile-rollup-read-the-canonical-capabilities-yaml-schema` ← issue #8

Three replies posted, each approved individually:
[#9](https://github.com/brocef/TCW/issues/9#issuecomment-5122247414) ·
[#8](https://github.com/brocef/TCW/issues/8#issuecomment-5122248161) ·
[#5](https://github.com/brocef/TCW/issues/5#issuecomment-5122249289). All three
left open — #9 and #8 until they ship, #5 because its request is postponed rather
than declined.

## The third defect, found only by the live run — `4364a5a`

`outcome.md` records two corrections. The live sweep found a third, and it is the
one worth remembering.

§3 said a `discarded` item means the issue was **rejected**.
`tcw work complete --resolution` takes `{duplicate, superseded, wontfix}` and all
three land in `discarded/`. Only `wontfix` is a rejection.

Issue #5's item was discarded `superseded` by the lifecycle-redefinition epic —
which did **not** absorb the request. It explicitly deferred both asks and wrote
them down "so it is not lost", instructing that they be recreated as a follow-up
that was never created. Under the old rule the sweep would have closed #5 telling
the reporter the project decided against a request that was merely postponed.

That is the worst reply the skill can produce, it is public and on someone else's
report, and **the folder name alone leads you straight to it.** §3 now branches on
`resolution`.

The pattern across all three findings: every one came from running the procedure
on real input, none from reading it.

## Follow-ups

- **`2026-07-29-close-the-originating-github-issue-when-a-work-item-completes`**
  (`dedf3c5`) — requested during this verification. Back-sync was an explicit
  non-goal of this item's spec, so reversing it got its own request rather than a
  spec widened after its own verification. #9 and #8 were both told "leaving this
  open until it ships", which that item has to make good on.
- **Issue #5's deferred asks remain untracked.** The reply says so publicly. No
  item was recreated for them; the user did not ask for one.
- **Trigger separation from `tcw-report` is still unfalsifiable.** Whether the
  right skill fires on "check my GitHub issues" is only observable in use — this
  session invoked the skill by name, so it proves nothing about triggering.

## Closeout

- **Merge route:** none. All work committed directly to `main`; no branch, no PR.
- **Docs:** current as of `ed1c71c`; implementation's step 6 handled them.
- **Version:** fold into **v0.17.0**. The gate reports `FOLDABLE` — the tag is
  absent from `origin`, so nothing published gets rewritten. Honest as a fold:
  v0.17.0 is a minor already carrying a feature, so a second one does not
  mislabel it.
