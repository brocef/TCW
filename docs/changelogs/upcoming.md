# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- Writes to a filesystem-backed store outside a git repository raised an
  unhandled `subprocess.CalledProcessError` out of `git_stage` — a traceback,
  after the item folder, the moved item, or the rewritten config had already
  landed. A `require_repository` precondition (`tcw/store/fs.py`) now refuses
  first, raising `ValueError` so every existing CLI and HTTP handler reports it
  unchanged. It is applied at both `FsTreeStore`'s and `FsWorkStore`'s
  `_stage`/`_rm`/`_mv`, so no git failure escapes as a traceback and the
  delete-shaped methods need nothing else, and at the nineteen public write
  methods that mutate the filesystem before they stage. Two placements are
  load-bearing: `FsWorkStore.start` guards as its literal first statement,
  because both its take-over branch and its main claim call `git_stage`
  directly and both rename before staging; `update_work` guards *after* its
  no-change early return, which writes nothing. The guard is deliberately
  stateless — `FsWorkStore.__init__` does not chain to `FsTreeStore.__init__`,
  so a cached flag on the base would be absent on every work store, and a store
  instance outlives one write in `tcw serve` and in tests.
- `tcw work delegate` and `tcw work escalate` *succeeded* outside a git
  repository, writing a complete but untracked request into the destination
  node's inbox that its own `inbox accept` would then refuse. `_inbox_write`
  (`tcw/work/recursion.py`) is the only adapter write that never stages, so the
  `_stage` guard could not reach it; it now checks the destination store's
  repository directly.
- `main()` caught only `ValueError`, so any `CalledProcessError` from the
  adapter's seven `check=True` git calls exited as a traceback. A generic
  handler now renders `tcw: git command failed (exit N): <argv>` and exits
  non-zero. It names no component or subcommand, and does not re-print
  `error.stderr` — no `check=True` git call captures output, so git's own
  diagnostic has already reached the terminal. `run_init` prints the shared
  `NOT_A_REPOSITORY` constant rather than its own copy of the sentence.
- The built-in `spec` and `plan` stage prompts named `initial-request.md` as
  their input unconditionally. Since 1.0.0 stopped creating that file on every
  item, an item from piped stdin or `tcw work inbox accept` carries only
  `intake.md`, so the prompt pointed at a document that did not exist and said
  nothing about the intake beside it. Both now resolve the body the way
  `tcw work show` does and name what they found. (#22)
- The `spec` prompt's `## References` rule concluded "nobody asked" from a
  missing section. On an intake-only item that section cannot exist — the
  `request` stage has not run — so the conclusion is now scoped to
  `initial-request.md`, and the intake branch says to read the intake as the
  request.
- The `postmortem` prompt's backwards spine ended at `initial-request.md`,
  omitting the `intake.md` that is the earliest artifact on an inbox-adopted
  item — the one a post-mortem most often needs.
- The shipped skills, commands, and agents carried the same assumption:
  `tcw-triage-issues` §5 wrote `initial-request.md` at acceptance and *then* ran
  the `request` stage over it; the post-mortem spine and backlog-audit artifact
  lists omitted `intake.md`; `tcw-process-inbox` described the `request` stage as
  reading its own output; and the `## Origin` lookups pointed at a fixed filename
  instead of the item's body.
- `cross-node-deltas.md` said `tcw work reconcile` writes its table into the
  epic's `initial-request.md`. It has written the `rollup.md` sidecar since the
  release that added `_evict_legacy_rollup`.
- The capability descriptions for `plugin/triage-github-issues` and
  `work/complete-a-work-item` made the same claim as standing behavior.
- `tests/test_serve.py` reached the `/open` success path on a real artifact
  without stubbing the opener, so every `pytest` run executed
  `open <tmp>/post-mortem.md` and launched the developer's GUI editor.

## Added

- Taxonomy: `work-item/body-surface` and `work-item/intake` are registered
  Vocabulary terms. Both were load-bearing model concepts with no entry in the
  registry — the body surface especially, since it is the rule `tcw work show`,
  the `R`/`i` board letters, and now the stage prompts all resolve through.
- `{{tcw:body}}` … `{{/tcw:body}}` — a prompt span replaced by the item's
  resolved body artifact, or by its own inner text when the item has no body.
  Inline replacement, deliberately not `substitute_documentation`'s block walk,
  which inserts a newline and the span's indent. Usable from a project's own
  `file:` or `blob:` prompt.
- `tcw.store.base.BODY_ORDER` — the read-resolution order for an item's body,
  promoted out of the filesystem adapter so the prompt resolver and every store
  adapter share one rule.
- `tests/conftest.py` — an autouse guard failing any test that spawns
  `open`/`xdg-open` or a browser, with a `stub_desktop_opener` fixture for tests
  that mean to reach that path. Both are argv-aware and delegate everything else
  to the real `Popen`; `tcw.serve.subprocess` is the stdlib module, so a blanket
  stub also breaks `FsWorkStore`'s `git` calls.

## Changed

- `LIFECYCLE_STEPS` `inputs` for `spec`, `plan`, and `postmortem` now list
  `intake.md` alongside `initial-request.md`. `inputs` is what a stage *may*
  read, not a checklist. `tcw work lifecycle` and its `--json` change
  accordingly, and `tests/fixtures/lifecycle_baseline/` was regenerated.
- `tests/fixtures/prompt_fallback/unconfigured.json` re-baselined for `spec`,
  `plan`, and `postmortem` only, after asserting the remaining stages are
  byte-identical — what that tripwire proves about the documentation
  substitution is intact.
- The `spec` prompt's `**Inputs.**` line breaks after the span's own sentence.
  Nothing re-flows a resolved prompt, so a span whose sentence ran past the
  source line break stranded a fragment (`… read as filed. An`) whenever it
  resolved to something shorter than its fallback. `substitute_body`'s docstring
  now states the rule for anyone writing a prompt with the span.
- The capability description for `work/run-a-lifecycle-stage` states that the
  shipped `spec` and `plan` instructions name the item's own body rather than a
  fixed filename.

## Internal

- `tests/fixtures/*/_scratch/` is gitignored; the fixture capture scripts build
  a throwaway git node there by default, which otherwise lands a nested
  repository in the tree.
