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
- Taxonomy, capabilities and work store ids resolved **lexically only**, so a
  symlink planted inside a store was clean to `_safe_store_id` and the join
  landed wherever it pointed. `FsTreeStore._within_store` (with a cached
  `_resolved_root`) now bounds every id, and `_node_readable` bounds a node
  folder together with its own `meta.yaml`. Applied at taxonomy `get_local`,
  `add`, `_local_slugs` and `_validation_resources`; capabilities `get_local`,
  `add`, `_all_meta_dirs`, `_write_target`, `check`'s targeted branch and
  `_validation_resources`; and work `_item_dirs`. The escape was **not**
  read-only as first reported — `tcw taxonomy add --parent`, `tcw capabilities
  set`, and a fresh federated override all created or mutated files outside the
  store; only the `git add` failed, and it failed after the write.
- Containment reaches a node's **resources**, not just its folder — a folder can
  be legitimately inside a store while a file in it is a symlink out, which the
  folder guard cannot see. `_load_node`, `_compose_body`, `_node_texts` (moved
  up to `FsTreeStore`, since both components read a node the same way),
  `get_term_detail`, `update_term`, `_apply_override` and both component
  `_validation_resources` now ask the **owning** store before reading, which
  matters for an inherited entry whose files are bounded by its own root. Found
  by adversarial review after the first fix guarded only directories; an escaped
  `meta.yaml` had been turning into a *phantom* term named after its own slug
  rather than a miss.
- Work items likewise: `_item_dirs` bounds discovery through `state.yaml` (a
  symlink *named* `state.yaml` matches the glob by name — `rglob` never descends
  a symlinked *directory*, so the file is the exposure, not the folder), and
  `_present`, `read_artifact` and the work `_validation_resources` bound the
  artifacts, sidecars and plan documents inside an item that discovery accepted.
- `Path.exists()` follows symlinks, so a dangling or looping link at a write
  target read as absent: the "already exists" refusal was skipped and `mkdir`
  raised `FileExistsError` as a traceback out of both `tcw taxonomy add` and
  `tcw capabilities add`. `is_symlink()` joins `exists()` — the idiom `init`'s
  ancestor walk already uses. Note `_within_store` catches `RuntimeError` as
  well as `OSError`: a symlink loop raises `RuntimeError` below Python 3.13 and
  nothing at or above it, and the supported floor is 3.11.

- `tcw work delegate` and `tcw work escalate` *succeeded* outside a git
  repository, writing a complete but untracked request into the destination
  node's inbox that its own `inbox accept` would then refuse. `_inbox_write`
  (`tcw/work/recursion.py`) is the only adapter write that never stages, so the
  `_stage` guard could not reach it; it now checks the destination store's
  repository directly.
- Three writes reached a repository other than the one their guard checked, all
  of them only when `work.path` puts the work store in a different repository
  from the code node (found by adversarial review at `verify`; see the item's
  `rework.md`). `tcw work start --worktree` guarded the store and then called
  `ensure_worktree_ignored` on the *node*, so the item moved to `active/` and
  `.gitignore` gained `.worktrees/` before `git add` failed — `_start` now
  requires the node's repository ahead of the pre-hooks. `merge_worktree` read
  any non-zero `rev-parse --verify --quiet` as "branch already gone" and
  returned success, so `complete` skipped the merge-back and exited 0 with the
  branch unmerged — it now returns its existing error-message form when the
  primary checkout has no repository. `init` checked `git_root(base)` *after*
  writing the sentinel, rewriting `tcw-config.yaml` with `work.path`, and
  scaffolding every status folder — the check moved above all of it, probing the
  nearest *existing* ancestor of the target because `git_root` shells out to
  `git -C <path>` and fails on a path this call has not created yet.
- `init` decided its remaining refusals next to the writes they protect rather
  than ahead of all of them (second adversarial pass at `verify`). A `work.path`
  under a gitignored directory was accepted, and `git_stage` drops ignored paths
  from the `git add` it builds, so the store held items git never recorded;
  refused now. `Path.exists()` follows symlinks, so a dangling one read as absent
  and the nearest-existing-ancestor walk skipped past it to the enclosing
  repository, leaving `mkdir` to die on `FileExistsError` with the sentinel
  already written — `is_symlink()` joins `exists()` in the walk. And the
  non-pristine-`docs/work` refusal ran after `write_sentinel`, so declining left a
  new `tcw-config.yaml` behind; its check moved up, while the `shutil.rmtree` it
  authorizes stayed put.
- `init`'s last mutate-then-raise paths (third adversarial pass). `git_ignored`
  asks `check-ignore` about a path, and git calls a *tracked* path not ignored
  however the rules read — correct for the `git_stage`/`git_mv` callers, which
  mirror what `git add` will do, and the wrong question for `init`, so it now
  passes `no_index=True` at that one site; a store scaffolded, committed, and
  only then covered by an ignore rule was otherwise accepted. The status leaves
  are worked out once before any is created and pre-flighted, so a leaf occupied
  by a regular file refuses instead of raising from `mkdir` with the sentinel
  already written. A symlinked default `docs/work` counts as non-pristine —
  it read as pristine through the link and then met `shutil.rmtree`, which
  refuses a symlink. And reading the config ahead of `write_sentinel` moved its
  mapping check out from under that read, so a malformed config came back as
  `AttributeError`/`TypeError` rather than the `ValueError` the CLI renders.
- The ignore check `init` gained above probed only the store root, so a rule
  naming a single status folder (`external/work/backlog/`) left the root visible
  and hid everything filed in that folder (fourth adversarial pass). Asked of
  each leaf's `.gitkeep` now — the question that matters, and the only form that
  reads TCW's own `completed/*` / `discarded/*` rules correctly, since
  `check-ignore` matches a trailing-slash path against a `dir/*` rule and
  querying the folder would make the scaffolding refuse itself.
- A `work.path` present but not a non-empty string (`[]`, `false`) was skipped by
  a truthiness test and fell through to the default store silently. Note the
  remaining gap: `load_yaml` coerces any falsy YAML document to `{}`, so a
  `tcw-config.yaml` whose whole content is `[]` or `false` still reads as an
  empty config rather than a malformed one. That is `load_yaml`'s contract,
  shared by every caller, and is left alone here.
- That ignore check asked about each leaf's `.gitkeep`, which answered the wrong
  question (fifth adversarial pass): `<status>/*` with a `!<status>/.gitkeep`
  negation is TCW's own shape for the resolved statuses, and it leaves the marker
  visible while hiding every item. It now probes **two differently-named**
  representative item paths (`an-item` and `some-slug`) and refuses only when
  **both** are ignored, skipping `completed`/`discarded`. One fixed name left the
  question answerable by a rule naming that single literal — `an-item*` was
  enough to refuse a store in which every real item would have been tracked —
  while no plausible single glob matches both names unless it is the broad rule
  the guard exists to catch. The *file* name is deliberately not varied:
  `state.yaml` is fixed by the layout, so a rule hiding it hides every item's
  status record and must still refuse. The refusal now names the outcome for
  items rather than describing the folder as being inside an ignored path, which
  was the wrong subject — the folder is usually fine and one rule is not. It also
  ran only for a configured
  `work.path`, so the default `docs/work` got no check at all; `ignore_root`
  starts at the node's repository and moves only when the store does. The
  guard's ceiling is marked in the source: a configure-time check cannot see a
  `.gitignore` written after `init`, a rule naming one slug, or a rule arriving
  with a later pull — that would be a check in `git_stage`.
- `git_stage` built its `git add` list by filtering out ignored paths with no
  `else`, so a rule the `init` guard could not have seen — written after `init`,
  naming a single slug, or arriving with a later pull — produced an item that is
  real on disk, listed by `tcw work list`, and absent from every clone. A new
  module-level `_warn_hidden` reports the drop where it happens, on stderr,
  warn-and-proceed: the same shape as `_warn_off_trunk` and the channel
  `tcw work` already uses for its `→ created at …` hints. Refusing was rejected
  deliberately — `completed/`/`discarded/` are ignored on purpose and a node may
  ignore another status folder on purpose too.
- The same warning covers `git_mv`'s ignored-destination branch, which is the
  sharper defect and was found by this item's sweep rather than reported: that
  branch drops the source from the index and moves the folder outside git, so an
  accidental rule on a live status folder turns `tcw work submit` into a silent
  removal of an item git already tracked — auto-committed under a message
  reading `→ review` whose entire content is a deletion. `git_stage` loses a
  write that never landed; `git_mv` destroys a record that had.
- Three details are load-bearing. The deliberate-versus-accidental test is a
  component match on the **absolute** path (`set(p.parts) & set(RESOLVED_STATUSES)`)
  rather than a store-relative one, because `FsWorkStore.root` is resolved while
  `node_root` may not be, and a spurious `relative_to` raise would mean a
  spurious warning on every `complete` — the one failure mode this must not
  have; matching the absolute path can only fail toward silence. Existence is
  tested at each call site, not inside the helper: `git_stage` skips a dropped
  path that no longer exists (`start` stages the vacated source folder as a
  deletion, and warning there would be false), while `git_mv` tests `src` and
  reports `dst`, which does not exist yet. And there is no de-duplication — a
  single `tcw work submit` into an ignored `review/` reaches both call sites and
  prints two lines, one for the folder and one for the `state.yaml` in it.
- `main()`'s `CalledProcessError` handler rendered a string-valued `error.cmd`
  character by character (`g i t ' ' s t a t u s`) — `shlex.join` over a string
  iterates it. Latent, since every `check=True` git call in the adapter passes an
  argv list, but the handler's justification is that it assumes nothing about its
  caller.
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

- `FsWorkStore.inbox_accept` derived the accepted item's title from the entry's
  *filename*, date prefix and all, and then re-dated that filename-shaped title
  into the slug — `2026-08-19-another-raw-request.md` became
  `2026-08-19-2026-08-19-another-raw-request`, titled with its own slug. The
  entry's `# ` heading was ignored, although `_inbox_write` (`delegate`,
  `escalate`) writes exactly that heading into every entry it creates. The title
  is now `--title`, else the first ATX H1 of the entry's body, else the entry's
  name with a leading `YYYY-MM-DD-` removed — kept when stripping it would leave
  nothing, so an entry named `2026-08-19-.md` still has a title. Only the
  filename fallback is stripped, since an H1 or a `--title` is a human-authored
  string. The slug never falls back to the *unstripped* label, so no entry whose
  heading fails to slugify can put a second date in it. (An entry named nothing
  but a date and carrying no heading still can: the date *is* its title, and
  keeping it is criterion 19's `2026-08-19-` case.) The slug rule
  is unchanged (`<acceptance-date>-<slugified-title>`), and `InboxEntry.title`
  stays filename-derived, so `inbox list` prints the same addressable label. The
  standing "always pass `--title`" workaround is retired. (#20)
- `tcw.store.base.body_title` reads that heading, skipping leading frontmatter
  and fenced code blocks (a fence closes only on a line that is nothing but a
  run of the opener's own delimiter, at least as long as it — so neither a
  three-backtick line inside a four-backtick fence nor a ```` ```not-a-fence ````
  line ends one; a closing fence carries no info string). It sits in the store
  base, not the filesystem adapter:
  reading a title out of a body is storage-neutral. `frontmatter_end`, beside it,
  is now the single definition of "leading frontmatter" —
  `FsWorkStore._frontmatter` parses the block it delimits instead of computing
  the boundary a second time.
- `FsWorkStore._unique_slug` bounded neither end of its output, so
  `tcw work new "東京"` created `<date>-` (every non-ASCII title collapsing to one
  degenerate slug) and a 300-character title crashed with an uncaught
  `OSError: [Errno 63] File name too long`. The slug body is now capped at 120
  characters, right-stripped of hyphens, and falls back to `untitled`. Both
  `create_work` and `inbox_accept` route through it, so guarding only the inbox
  path would have left `tcw work new` broken. `state.yaml` keeps the full title;
  only the slug is bounded.

- `FsWorkStore.create_work` took its `created` argument on trust, and it
  prefixes the slug: `tcw serve`'s `POST` body passes the field straight
  through, so a long or non-date value produced a rejected path
  (`OSError: [Errno 63]`) or a `state.yaml` holding a non-date. It is parsed
  with `date.fromisoformat` now, which both validates and canonicalizes it, so
  the slug's prefix is bounded as well as its body. (Found reviewing this
  change's own claim that `_unique_slug` bounds its output — it bounded only
  the half derived from the title.)
- `tcw capabilities set` accepted a reference-bearing field whose value pointed
  at nothing and exited 0; only a later `tcw capabilities check` found it. The
  refusal now happens at write time, in `_validate_fields` — the one seam both
  `set` and `update_capability` call before touching disk — so the CLI and
  `tcw serve`'s PATCH inherit it without new plumbing. Six fields, not the two
  reported: `Superseded by`, `Blocked by`, `Roles` and `When` resolve against the
  capability store itself and were going through the same unvalidated call. All
  problems in one write are reported at once rather than first-wins, and none of
  the messages contains `no such`, so `_map_store_error` keeps them at 422.
  A new `_ref_problems` is the single renderer both `check` and the write path
  use, so the two cannot disagree about what a problem is; `_check_globals`,
  `_check_subject` and `_check_feature` lose their `where` parameter and return
  unprefixed tails. Only the refs a write *supplies* are validated, never the
  merged node, so a capability already holding a bad ref stays repairable with
  `--status Omitted`. A taxonomy store is opened only when `Subject` or `Feature`
  is actually supplied.
- `FsCapabilitiesStore.check()` called without a taxonomy silently skipped
  `Subject` and `Feature`, so the write path and `check` could disagree about
  *whether* a ref was checked even once they agreed about what a problem is. It
  now falls back to `self._taxonomy()`, the node's own. `is not None` rather than
  `or`, so an explicitly injected falsey store still wins. The two duplicate
  wirings this replaces are deleted (`_taxonomy_for` in `tcw/capabilities/cli.py`
  with its orphaned import, and the `tax = …` conditional in `tcw/validate.py`).
  Note `tcw serve` was **not** a third divergent wiring, as the item's spec
  claimed: it does construct a taxonomy store unconditionally, but never passes
  it to `capabilities.check` — its post-save warnings route through `validate()`,
  the guarded path — so the taxonomy-less behaviour was already aligned.
- `POST /api/capabilities` did add-then-`set`, so a field the store refused
  returned 422 with the capability already on disk — reachable before this change
  with an unknown field or an invalid `Status`. `add` takes an optional `fields`
  now and validates before `_write_node`, so the handler makes one call and the
  whole class is fixed rather than the ref case alone. This is
  validation-atomicity, not atomicity: `_write_node` still stages after writing
  and keeps written files when `git add` fails.
- A git refusal *after* the filesystem write left the partial write standing.
  The non-git work made a write refuse before touching disk when the repository
  is **absent**; one that exists and **refuses** — a held `index.lock`, a
  rejecting hook, a permissions error, a corrupt `.git` — was still only
  discovered when staging failed, which is after the content had landed.
  `main()` rendered it as `tcw: git command failed` rather than a traceback, so
  it was legible, and `docs/work/backlog/<slug>/` was still there afterwards. A
  precondition cannot close this — it cannot predict a lock acquired a
  millisecond later — so `FsTreeStore._write_staged` rolls back instead: it
  writes, stages, and on either failure removes what *this call* created before
  re-raising. Fifteen write-then-stage pairs across fourteen methods route
  through it, so a refused stage no longer leaves a partial term, capability,
  work item, draft, plan stage or config write behind.
- **Nothing that already existed is ever removed**, which is the boundary the
  whole design turns on. Ownership is proved two ways because a directory and a
  file have different failure costs. `_mkdir_owned` uses
  `mkdir(exist_ok=False)`, where exactly one process's call succeeds — an
  ownership proof with no check-then-act window, which retires the
  `existed = d.exists()` pattern at three sites along with the `ponytail:` note
  that named its TOCTOU. A file is owned if it was absent at entry; that *is* a
  check-then-act window, and it is acceptable where the directory one is not,
  because our own write has already replaced any competitor's content, so
  unlinking destroys nothing the call had not already overwritten. `rmtree` on a
  directory has no such argument — it would take sibling files nobody touched.


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

- `tcw capabilities set` and `update_capability` now **remove** an override
  folder they materialized when staging is refused, reversing the previous
  policy. The two tests that pinned the old behaviour are renamed
  `test_{set,update_capability}_removes_override_when_staging_fails` and their
  docstrings record the reversal, so `git log -S` finds it. An override folder
  that already existed is still never removed.
- `CapabilitiesStore.add` gains an optional trailing `fields` keyword
  (`tcw/store/base.py`). Backwards-compatible — every existing caller omits it —
  and it is the shape a remote adapter wants anyway, since a tracker creates an
  issue with its fields in one API call rather than two.
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

- `_atomic_write` is deleted: every production caller now routes through
  `_write_staged` → `_atomic_write_all`, which is the singular with a list
  around it and carries the same temp-file cleanup. Its three unit tests point
  at the plural. `dump_yaml` stays — `init`, `write_sentinel`, `inbox_accept`
  and `start` still use it, and none of those is a write-then-stage pair.
- Exactly three `self._stage(` calls remain in `tcw/store/fs.py`: the one inside
  `_write_staged`, `update_capability`'s directory stage (which records a
  *removal*, so there is no written content to undo), and `inbox_accept`'s
  (a whole-directory swap that already rolls back in its own `except`, and whose
  writes go to a temp dir rather than where they will sit).
- `tests/fixtures/*/_scratch/` is gitignored; the fixture capture scripts build
  a throwaway git node there by default, which otherwise lands a nested
  repository in the tree.
