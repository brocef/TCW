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

- **`load_yaml` returns a mapping or raises.** It ended in `return data or {}`,
  which kept neither half of its documented contract: a falsy document (`[]`,
  `false`, `0`) became `{}` and a truthy non-mapping came back unchanged. It now
  returns `{}` only for an absent, empty or `null` file and raises
  `yaml.YAMLError` naming the path and the type found for anything else.
  `yaml.YAMLError` deliberately, not `ValueError` — ten call sites already catch
  it around a load, `_safe_yaml` above all, so the board's promised tolerance
  now applies to this case without touching any of them.

- **`tcw validate`'s YAML pass parses directly rather than through
  `load_yaml`.** It must keep accepting any shape: `docs/work/dod.yaml` is a
  top-level list on purpose and an attachment may hold anything. Alongside it,
  a file whose name is one TCW writes as a record — `state.yaml`, `meta.yaml`,
  `graveyard.yaml`, `config.yaml`, `.config.yaml`, listed as
  `OWNED_YAML_NAMES` — is reported when it is not a mapping, and skips the
  component checks the way a syntax error does, since they re-read the same
  file. A test asserts the set covers every YAML filename the source writes bar
  three deliberate absences: `dod.yaml`, the node sentinel, and a work item's
  `capabilities.yaml`, which is a mapping for the Definition-of-Done gate or a
  list when `reconcile` wrote it.

- **One reader for the node sentinel, `load_config`.** A config a user has
  broken is a `ValueError` naming the path, which is the channel `tcw`'s top
  level already renders and the contract two existing tests assert. Six sites go
  through it: `write_sentinel`, `init` (twice), `resolve_store`, and
  `FsWorkStore._config`, which did the conversion by hand and now does not.
  `declared_repository` and `declared_connected_projects` deliberately do not —
  they exist to answer for a graph that cannot be fully loaded, so an unreadable
  config declares nothing.

- **`load_yaml` raises `NotAMapping`, a subclass of `yaml.YAMLError`.** Every
  site that catches the parent still catches it; the subclass only lets
  `load_config` distinguish "not a mapping" from "not YAML".

- **`tcw` prints a message for a malformed YAML file instead of a traceback.**
  `main()` catches `yaml.YAMLError`, covering the thirteen sites that read
  records rather than config — a corrupt `meta.yaml` reached the terminal as a
  traceback through the component check.

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

- **A work item's list-form `capabilities.yaml` failed its own completion
  gate.** `_read_item` read the sidecar through `load_yaml`, so the list form
  `reconcile` writes raised, was caught, and became the `_tcw_parse_error`
  sentinel — which `declared_capabilities` turns into a `SidecarError` so the
  Definition-of-Done gate fails closed. A sound sidecar would have blocked
  completing its own item. The sidecar is now parsed directly, and both
  documented shapes survive the read. Introduced in this release and fixed in
  it; never shipped.

- **A corrupt work item read as healthy, and `tcw validate` agreed.** A
  `state.yaml` containing `[]` was coerced to `{}`, so `tcw work show` printed a
  title fabricated from the directory name and `tcw validate` reported the node
  clean. Nothing anywhere said the file was not a state file. `validate` now
  names it.

- **One corrupt work item took the whole board down.** A `state.yaml` containing
  `- a` was returned as a list and reached `.get`, so `tcw work list`,
  `tcw work show` and `tcw validate` all died with an `AttributeError` —
  precisely what `_safe_yaml` exists to prevent. It catches `yaml.YAMLError`,
  and a well-formed non-mapping never raised one, so its promised tolerance had
  never applied to this case. The board now lists the item.

- **`tcw init` silently overwrote a malformed `tcw-config.yaml`.** A config
  holding `[]`, `false` or `0` read as "no configuration" and was written over
  without a word, while the same file holding `- a` was refused and left alone.
  Every shape is now refused, the file is left byte-identical, and the message
  names it.

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
