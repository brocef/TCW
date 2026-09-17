# Spec: Fix the guide's taxonomy example and a stale README citation

## Capability changes

None. This corrects a guide's examples and two source comments; no command's
behavior changes, so the capability ledger is untouched.

## Problem

1. **The guide's examples refuse when run in order.** Running every
   `tcw taxonomy` and `tcw capabilities` line of
   `docs/guide/taxonomy-and-capabilities.md` in a fresh project
   (`git init`, `tcw init --id demo`) on 2026-09-17 gave three refusals, not the
   one the request names:
    - `:25` `tcw taxonomy add Permission -p admin` → "parent term does not exist:
      admin". Nothing adds `admin` first.
    - `:27` `tcw taxonomy add "User Authentication" --kind feature --vocab user` →
      "vocabulary ref 'user' does not resolve". Nothing adds `user` first. Found by
      the sibling sweep; not in the request.
    - `:83` `tcw capabilities set billing/invoices --field "Subject=invoice,billing"`
      → "Subject → dangling ref 'billing'". Nothing adds a `billing` term. Found by
      the sibling sweep; not in the request.

   `:28` `tcw taxonomy show admin/permission` then fails as a knock-on of `:25`.
   The README's copy (`README.md:306-309`) runs cleanly, confirmed the same way —
   it adds `Admin` before `Permission -p admin`.

2. **Two source comments cite README text that does not exist.**
    - `tcw/store/fs.py:4964` calls the retention backfill "the migration the README
      describes". The README does not describe it; `docs/guide/work.md:172-174`
      ("Adopting auto-delete on an older board … `tcw work tombstone add <slug>`
      backfills the ones already resolved") does.
    - `tcw/store/fs.py:290` says an unreachable declared parent is something
      "`README.md` promises does not happen". The README says nothing about it
      (`grep -i parent README.md` finds only a table row and unrelated prose);
      `docs/guide/multi-repo.md:117-119` makes that promise ("`tcw work nodes`
      lists it as a parent or a child that is not in this checkout, and
      `tcw work escalate` and `tcw work delegate` name it instead of calling the
      node a root or a leaf"). Found by the sibling sweep; not in the request.

3. **Added at code review:** `docs/guide/work.md:239`
   `tcw work new "Login crash" --tags bug,cli` → "unregistered tag 'cli'"; the
   block registers only `bug` and `tech-debt` (`:236`). Same defect, missed by
   this spec's sweep, which ran taxonomy and capabilities examples only.

## Goals

- Every `tcw taxonomy` and `tcw capabilities` command in the example blocks of
  `docs/guide/taxonomy-and-capabilities.md` lines 23-35 and 70-87 succeeds when run
  top to bottom in a fresh project, excluding the `extends` lines, which need a
  second registered project by design.
- `docs/guide/work.md`'s tag lines (`tags add` through `new --tags`) run in order.
- Both comments name the document that actually says what they claim.

## Non-goals

- The prose defects at `docs/guide/taxonomy-and-capabilities.md:53-54` —
  `2026-09-15-repair-sentences-references-and-headings-in-the-guides` owns them.
  That item is in `backlog`, not in flight, so there is no edit conflict.
- The federation examples at `:120-144` (`extends`, `reset`), which assume another
  registered project and are illustrative rather than a runnable sequence.
- Syntax lines with placeholders (`skills/taxonomy/SKILL.md:79,109-111`,
  `skills/setup/references/taxonomy.md:49-51`) and historical release notes and
  changelogs, which are not meant to run.
- Any change to what the commands accept.

## Design

- In the taxonomy block, add the missing terms before the lines that need them,
  matching the README's shape (`tcw taxonomy add Admin "…"`), plus a `User` term
  before the `--vocab user` line. Keep the lines that show `-p`, `-s` and `--vocab`
  so the block still illustrates each flag.
- In the capabilities block, make the multi-valued `Subject` example reference
  terms the taxonomy block created, so it still shows two values.
- Reword the two comments to cite `docs/guide/work.md` ("What happens to resolved
  work") and `docs/guide/multi-repo.md` ("When a declared project is not on this
  machine").

Litmus test: not applicable — no operation is added or changed.

## Acceptance criteria

1. In a fresh directory, after `git init` and `tcw init --id demo`, running every
   line that begins `tcw taxonomy` in `docs/guide/taxonomy-and-capabilities.md`
   lines 23-35 except the two `extends` lines, then every line that begins
   `tcw capabilities` in its 70-87 block, in file order, exits 0 on each command.
2. `git grep -n README tcw/` returns no comment claiming the README describes the
   retention backfill or promises the unreachable-parent behavior.
3. `tcw/store/fs.py`'s two comments name `docs/guide/work.md` and
   `docs/guide/multi-repo.md` respectively, and the cited passages say what the
   comments attribute to them.
4. The README's taxonomy example is unchanged and still runs.
5. In a fresh project, `tcw work tags add bug cli tech-debt`, `tcw work tags rm tech-debt`
   and `tcw work new "Login crash" --tags bug,cli` — the guide's lines as written —
   each exit 0.

## Risks

- A comment-only edit to `tcw/store/fs.py` cannot change behavior, but the full
  suite is still run to confirm nothing reads the file's text.
- Line numbers in this spec shift as soon as the guide gains lines; the criteria
  name blocks, and the plan re-derives the ranges.
