# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Changed

- **Documentation headings.** Twenty-four headings inserted across `README.md`,
  `docs/guide/work.md`, `docs/guide/configuration.md`,
  `docs/guide/multi-repo.md`, and `docs/guide/taxonomy-and-capabilities.md`, so
  that every span of prose sits under a heading that names it. No prose was
  edited, moved, or removed — the change is heading lines and the blank lines
  around them, pinned by a diff check that must show no removed line.

    The sections repaired: `## Tags`, `## Automation and piping` and
    `## Cross-node recursion` in `work.md`, which between them covered command
    output conventions, inbox entry rules, intake promotion, plan stage
    documents, the board, the JSON projection, descendants, graph-wide
    addressing, claim recovery, initiative gating and `--worktree`;
    `## Binding your own skills and commands to the lifecycle` in
    `configuration.md`, which covered `tcw work stage gate`, `stage prompt` and
    `scaffold`; `## Connected projects` and
    `## Keeping a provisioned store in step` in `multi-repo.md`, the first of
    which answered six separate questions in 159 lines;
    `## tcw taxonomy — the nouns` and `## tcw capabilities — the user stories` in
    `taxonomy-and-capabilities.md`; and
    `### Reading a lifecycle stage` in `README.md`.

- **`tcw work tags add|rm "a,b"` now means two tags**, where it previously meant
  the single tag `a-b`. Non-additive, as is `--tag a,b` going from failure to
  success.
- **`--ta` and `--unta` no longer resolve.** Python's parser accepts unambiguous
  long-option prefixes, and adding `--tags` / `--untags` makes those two
  ambiguous. `--tag` and `--untag` still match exactly; `--t` was already
  ambiguous with `--title`.
- **`--tags ""` is an error rather than "no tags".** A script passing a
  possibly-empty variable must omit the option instead.

## Added

- **`autonomous-work` skill.** Ships the unattended-run procedure that was
  previously a personal skill: it drives named work items through
  `/tcw-drive-work-to-completion` back to back, and at every point the lifecycle
  would ask the user it consults two read-only advisors instead — a `codex exec`
  run and an Opus subagent — then decides, recording each consult in the item's
  `outcome.md`. Hard blockers (credentials, unrecoverable actions, product
  direction, spend) still stop the run. `evals/coverage.py` excludes it with a
  reason rather than covering it: grading a case would cost a full multi-item
  run and would mostly re-measure the skills it delegates to.

- **`--tags` / `--untags`, and comma-separated tag values.** Accepted wherever
  `--tag` / `--untag` are — `work new`, `work list`, `work edit` — and on the
  `work tags add` / `work tags rm` positionals. One converter, `_tag_list`, with
  a thin argparse wrapper; the options use `action="extend"` so `dest` and every
  command handler are unchanged. Spellings compose, blank segments are ignored,
  and a value yielding no tag is refused.

## Fixed

- **`_claiming_dirs` globbed with the caller's slug unescaped.** A slug holding
  `*`, `?` or `[` matched another item's interrupted claim. **Through the store
  API** the take-over branch then rewrote that item's owner, moved it into
  `active/` under the pattern as its name, and only afterwards failed in
  `git add`, so the move was already done. **Not reachable from the CLI**, where
  `_start` evaluates `st.get(bare)` before `st.start` and that read raises first,
  nor from `tcw serve`, which never passes `take_over`. The CLI-reachable half is
  the ordinary path: `start` on an absent slug stalled about 0.6 s and reported
  an interrupted claim belonging to a different item.
  Now `glob.escape(slug)`, with the `[0-9a-f]` suffix concatenated after it.
  Nothing recoverable stops matching: a claim directory is only ever created as
  `f"{slug}-{uuid4().hex}"` after `_find` matched that exact name.
- **The take-over branch composed its destination from the caller's slug.** It
  now derives it from the claim directory that was found. Redundant behind the
  escape, and deliberately so.

- **An empty `.claiming/` made a default work store non-pristine.** `init`
  compares the work root's entries against `{"inbox", *WORK_STATUSES}`, and
  `start` creates `.claiming/` without ever removing it. Relocating a store with
  `--work-path` was therefore refused on any node an item had ever been started
  in. The name is now discarded from that comparison; the per-child check below
  it is unchanged, so a claim in flight still reads as work and still refuses.
  `FsWorkStore.start` is untouched — removing the directory after a claim would
  race the next one and report an interrupted claim on an item nobody touched.

- **A comma in a tag value silently produced a joined tag.** `normalize_tag`
  collapses every run of `[^a-z0-9]+` to a hyphen, so `cli,docs` became the
  single tag `cli-docs` everywhere a tag was read. Applying was caught only by
  the registration check, whose message told the user to register the joined
  tag; **registering was not caught at all**, and `tcw validate` reported the
  resulting config sound. A node poisoned this way is not repaired by this
  change — see the release note.
