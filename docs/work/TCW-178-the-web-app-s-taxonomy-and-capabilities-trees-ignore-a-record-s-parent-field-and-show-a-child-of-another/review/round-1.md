---
verdict: accepted
judges: 1
---

# Review — round 1

**Who reviewed.** A separate read-only reviewer agent (`tcw:reviewer`) read
commit `df04cad5` against the spec, plan, implement round 1 and
`capabilities.yaml`, and recommended **accepted**. The author then made the
two small changes it asked for in commit `05c3e3ac` (a test for criterion 6,
and rewrapping one long line in the capability description). The reviewer
did not see those; the author checked them, as recorded below.

## Checks run for this round

- Bare `pytest`, as CI runs it: 8306 passed, 115 skipped. (An earlier run
  stopped on one failure in `tests/test_no_extends.py`: its text search over
  `tcw/` matched a stale, git-ignored Python 3.12 bytecode file,
  `tcw/store/__pycache__/fs.cpython-312.pyc`, compiled from old source. With
  the stale 3.12 caches deleted the test passes; CI never has them.)
- `tcw validate`: 0 errors, 0 warnings, 0 unresolved.
- `pnpm test`: 17 files, 261 tests passed. `tsc --noEmit` and `pnpm lint`
  clean. The reviewer saw one of four runs exit non-zero from an unhandled
  timer error in `scope-control.test.tsx`, a file this change does not touch.
- The reviewer rebuilt the bundle to a scratch folder and found it
  byte-identical to the committed `tcw/serve/dist/client`.

## Acceptance criteria

1. **Met.** `tree.test.ts`, "a child of another project's listed record sits
   under it".
2. **Met.** "a child of a record that is not listed sits under labels for
   it": both labels have no item.
3. **Met.** "a flat child of this project's own record sits under it".
4. **Met.** Existing path-tree tests unchanged and passing, plus a test
   comparing against the two-argument call.
5. **Met.** The two-record cycle test; the reviewer's probe also covered a
   three-record cycle and a cycle through a label, each key appearing once.
6. **Met.** Now tested: `route-utils.test.ts`, "parent text … that is not a
   full identifier names no parent" (null, empty, `not an id`, `a/b`).
   Mutation-checked: with the full-identifier check removed, two cases fail.
7. **Met.** `pathTreeAncestors` asserted in the criterion-1 test.
8. **Met, with a caveat.** In the Claude Chrome profile against two fixture
   projects, the author saw each re-parented term and capability under its
   parent's row (scope up) or its labels (scope own). The app test checks
   the same shape in both axes. The caveat: opening a record's URL on a
   fresh page load expands every row anyway (the existing "expand on first
   sight" effect), so that browser step did not exercise
   `pathTreeAncestors` inside `navigateTo`; only in-app navigation does, and
   it has no app-level test. Its logic is unit-tested and the reviewer read
   `navigateTo` as correct for both axes, so this does not block.
9. **Met.** Unit tests, type check, lint, `check:build` (after staging the
   bundle) and bare `pytest` all pass.

## capabilities.yaml

`changed: tcw.capabilities/web` — its description now says entries sit under
the entry their `parent:` names, under labels when it is not listed, which is
what the code does.

## Documentation entries

Evaluated by hand against `tcw work docs` (the `documentation-sync` skill
was not invoked): web-viewer guide, capability description, release-notes
and changelog entries written; README, jira guide, skills, configure
references and use-cases do not fire.

## Left for separate changes

- The occasional unhandled timer error in `scope-control.test.tsx`.
- `pathAncestors` is no longer used in production code (kept on purpose).
- Labels made for parents that are not listed come after the other rows at
  their level, not in the server's order. Cosmetic.
