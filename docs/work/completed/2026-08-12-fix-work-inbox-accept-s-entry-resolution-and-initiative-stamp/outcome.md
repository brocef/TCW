# Outcome — Fix work inbox accept's entry resolution and initiative stamp

Implemented directly on `main` (no worktree), sequentially, as the first of the
three queued items.

## What shipped

### Task 1-2: one deterministic inbox resolver (`aabd62e`, tests in the prior commit)

`FsWorkStore._resolve_inbox_ref` resolves an identifier in a fixed order — exact
ref, then `<ref>.md`, then a unique `InboxEntry.title` — and both `inbox_show` and
`inbox_accept` route through it. `inbox_accept` resolves **once** and reuses the
canonical ref for `_inbox_path` and `_inbox_detail`, so the two reads cannot
disagree about which entry is being consumed. The abstract `WorkStore` signatures
are untouched; relaxation stays a filesystem-adapter detail, per the spec.

### Task 3: delegated initiative survives acceptance (`3c1aeac`)

`_inbox_initiative` extracts the one key that crosses from intake into model
state. It runs **before** anything is created or consumed, so a bad value cannot
strand a half-accepted item. Absent, null, or whitespace-only writes no key at all
— the same item shape as before. A structured value raises.

Rather than write a second frontmatter parser, extracted
`FsWorkStore._frontmatter(content, label)` out of `_plan_manifest`, which now
calls it and is 5 lines shorter. Same behavior and error text for `plan.md`
(verified: the 25 manifest/stage tests pass untouched). Two callers is the
threshold this repo sets for extracting, so the parser is shared rather than
duplicated.

### Task 3b: `delegate --help` named the wrong identifier (`f25e048`)

Folded into this item before implementation began, per the user's instruction.
The help string promised `child node path (relative to this node)`; `delegate`
resolves the canonical project ID. Fixed the string only — the code was correct,
and accepting a path would have been the actual defect, since IDs are identity and
paths are adapter locators.

The behavioral half of the regression test passed before the fix and the help
assertion failed, which is exactly the right split for a documentation defect.

### Task 4: documentation (`599f942`)

`README.md` (both the inbox example and the cross-node section), the changelog,
the release notes, and `skills/tcw-work/references/commands.md`. Nothing was added
to `skills/tcw-work/SKILL.md` — its body is at the 60-line router budget, and both
details here are conditional, so they belong in `commands.md`.

## What the spec got wrong

**The spec contradicted itself, and implementing it surfaced the conflict.**

- Design (line 56): *"Exact reference wins even if a relaxed candidate would collide."*
- Acceptance criteria (line 74): *"If a folder and a Markdown file produce the same
  listed title, accepting that title fails with an ambiguity error."*

Both cannot hold. Given `inbox/example/` and `inbox/example.md`, the input
`example` **is** the folder's exact reference — so the Design says it resolves to
the folder while the criterion says it errors. I found this by writing the
criterion's test first and watching it fail for the wrong reason (`DID NOT RAISE`,
because today's code already resolves the folder).

Resolved toward the Design, and recorded in `spec.md` in its own commit before any
implementation: an exact reference always wins, and ambiguity is reserved for an
input that is neither an exact ref nor an `<input>.md` yet matches several listed
titles (`example.txt` + `example.rst`, input `example`). The alternative would make
a folder unaddressable by its own name the moment a file landed beside it, and the
ref is the first column `inbox list` prints.

The test was rewritten to match, and a `test_inbox_exact_reference_wins_over_a_colliding_title`
added to pin the case the old criterion got backwards.

## Verification

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **1267 passed** (was 1255; +12) |
| `pnpm exec tsc --noEmit` | clean |
| `pnpm run lint` | clean |
| `pnpm run test` | 50 passed, 11 files |
| `pnpm run build` / `check:build` | both built |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities check` | `capabilities OK` |
| `tcw validate` | `validate OK` |
| `git diff --check` / `git status --short` | clean |

### Verification beyond the suite

The plan asks for one judgment a test cannot make — whether the corrected help
string reads as "canonical project id" to someone who has not just read the
source. Rendered output, not the diff:

```
positional arguments:
  child                 child node's canonical project id (`tcw work nodes`
                        lists them)
```

It names the form and where to get valid values. Accepted.

## Notes

- The `_frontmatter` extraction is the only change in this item that touches code
  outside the inbox path. It is behavior-preserving and covered by the existing
  plan-manifest tests, but it is worth knowing it is in the diff.
- Capability ledger: unchanged, as `spec.md` said. This corrects existing
  work-inbox and delegation behavior rather than adding a user capability.
