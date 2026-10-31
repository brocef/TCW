# Implement round 2 — TCW-117

Answers [review round 1](../review/round-1.md), findings 1 to 13, on the
branch `v4` in its worktree, with the worktree's own virtual environment. The
4.0 `tcw` was run only through the session's wrapper, which unsets every
`TCW_*` variable and gives each run its own home, configuration and cache
folders, from scratch projects in the scratchpad; the released 3.0.2 `tcw`
only inside scratch folders there, with its own home and configuration
folders and every `TCW_*` variable unset. Never against this repository, and
never against Jira. No lifecycle command was run and no ticket was touched:
the dispatching session makes every move.

## Commits

| Commit     | Findings                                                                                     |
| ---------- | -------------------------------------------------------------------------------------------- |
| `bc47d1e3` | 1, 2, 3, 4, 5, and 11 for `README.md`: the migration guide, four guides and the README       |
| `57a2a13d` | 6, 7, 8, 9, 10: four skills, two configure references and the backlog auditor               |
| `993c11ff` | 11 for the ledger: two capability descriptions                                               |
| `77b10d95` | 13: the changelog and release-note entries                                                   |

Finding 12 is answered in this document (below).

## The scratch projects

- **A family**: `core` (one term `vocab-refund`, one capability
  `billing/refund`, one work item) and `app`, with `parents: [core]` and a
  shared manifest placing `core` at `../core` with a `repository`. `core` was
  then renamed away, so it was not on this machine, and later put back and
  given `children: [app]`, with `app` renamed away, for the `--scope down`
  cases.
- **A 3.0.2 project** `p3`, made with the released `tcw init`, holding a term,
  a capability, two work items, a 3.x `capabilities.yaml` and a personal
  `tcw-config.local.yaml`; committed, then migrated with 4.0 `tcw migrate`.

## Findings, and what changed

### 1. Exit 5 and exit 7 for a missing related project

`docs/migration-guide-3.X-to-4.0.0.md`, "What reads differently with no name
change": the bullet now says a missing related project gives 5 or 7
depending on what the command needed. 5 when the command names that project
or reaches its objects or folder; 7 when it needs something the active
project inherits from a missing parent. "Scripts, hooks and agent
instructions", item 3, now says a script checks both 5 and 7, which is which,
and that an unknown project ID exits 1 with `check the spelling`. The 3.x
codes ("where 3.x gave 5 or 1") were dropped rather than rechecked.

Checked, in `app` with `core` missing:

| Command                                              | Exit |
| ---------------------------------------------------- | ---- |
| `tcw work show core.work/2026-10-26-shared-epic`     | 5    |
| `tcw -C tcw://core.path/ work list`                  | 5    |
| `tcw project path core`                              | 5    |
| `tcw project provision core` (entry with no `repository`) | 5 |
| `tcw capabilities list --scope up`                   | 7    |
| `tcw capabilities show billing/refund --scope up`    | 7    |
| `tcw taxonomy list --scope up`, `taxonomy show … --scope up` | 7 |
| `tcw project config`                                 | 7    |
| `tcw work tags list`                                 | 7    |
| `tcw work show zzz.work/x`, `tcw -C tcw://zzz.path/ work list` | 1, "check the spelling" |

Each 5 and 7 message named the manifest and the folder TCW looked in, and,
with a `repository` in the entry, ended `fetch it with 'tcw project provision core'`.

### 2. A covered project that cannot be read

`docs/guide/cli.md`: the paragraph that said such a project never stops the
command is now two cases. Left out with one warning and exit 0 when the
command does not need its content; exit 7 with nothing on stdout when the
active project's own entries need it. Checked:

- with `core` (a parent) missing, run in `app`: `tcw work list --scope up`
  and `--scope all` exit 0 with `warning: 'core' is unavailable, so its work
  items are not listed: …`; `tcw capabilities list --scope up`,
  `tcw capabilities show <id-path> --scope up` (an inherited and an own
  capability alike), `tcw taxonomy list --scope up` and
  `tcw taxonomy show <path> --scope up` exit 7 with
  `tcw capabilities list: 'app' inherits its capabilities from project 'core', which is not on this machine: …`;
- with `app` (a child) missing, run in `core`: `tcw capabilities list`,
  `tcw capabilities show`, `tcw taxonomy list` and `tcw work list`, each with
  `--scope down`, exit 0 with one warning line.

The Related projects guide's list of the listings' words lacked the taxonomy
listing's; `so its taxonomy entries are not listed` was added, as printed by
`tcw taxonomy list --scope down`.

### 3. A `capabilities.yaml` in 3.x form

`docs/guide/work.md`: the example is written with full identifiers
(`app.capabilities/billing/refund-a-payment`, `app.taxonomy/refund`), and the
sentence before it says entries are full identifiers, linking the linking
guide. Checked in `app`: the old example in an item's folder gave `tcw validate`
exit 1, three errors `… is a TCW 3.x reference; TCW 4 writes
<project>.capabilities/<id-path> (run 'tcw migrate' in this project)`; the
new one, exactly as written, `0 errors, 0 warnings, 0 unresolved`.

Every other fenced block in `docs/` (but `docs/work/`) and `skills/` was
searched by a script for a `new:`, `changed:` or `removed:` list with an
entry that is not a full identifier. It found the work guide's example and
one in `docs/release-notes/v2.1.2.md`, a release note for 2.1.2, which
describes that version and was left. Its other hits were words of a YAML
comment after a full identifier.

### 4. The way back after `tcw migrate`

`docs/migration-guide-3.X-to-4.0.0.md`, "The way back": it now says that
restoring the commit is not enough, names what the run adds (the `.tcw/`
folder and what it holds, and the state files `tcw-taxonomy.yaml`,
`tcw-capability.yaml`, `tcw-work-item.yaml`), says the personal file is moved
into `.tcw/` and given a `tcw-version` line and that no commit brings it
back, and gives the commands:

```sh
mv .tcw/tcw-config.local.yaml tcw-config.local.yaml   # only if you have a personal file
rm -rf .tcw
git restore --staged --worktree -- .
git clean -fd
```

then deleting the `tcw-version` line, with a warning that `git clean -fd`
deletes every untracked file (run `git clean -nd` first), and, for a copied
folder, to replace the folder with the copy.

Checked on `p3`: 3.0.2 `tcw validate` gave `0 errors, 0 warnings, 0 unresolved`
before the run; `tcw migrate` exited 0; `git status --ignored` then showed
the untracked `.tcw/.gitignore`, `.tcw/tcw-config.yaml`,
`.tcw/tcw-migration.yaml`, the four state files, and the ignored
`.tcw/tcw-config.local.yaml`, which held `tcw-version: 4.0.0` above the
user's setting. After the steps: 3.0.2 `tcw validate` exit 0,
`0 errors, 0 warnings, 0 unresolved`; no `.tcw` folder and no `tcw-*.yaml`
file but the 3.x `tcw-config.yaml` and `tcw-config.local.yaml` remained;
`git status` clean but for the ignored personal file. Without the last step,
3.0.2 `tcw validate` exits 1:
`error: tcw-config.local.yaml: tcw-version: a shared key; a personal file cannot set it`,
which is why the guide gives it.

### 5. Terms used without a definition

- "gate", `docs/guide/cli.md` exit table, code 3: the meaning reads "a rule or
  a check", and the example names a `pre` hook (a command a stage runs before
  an item moves into it) and a built-in check of a move, linking the work
  guide's "Built-in gates", where a gate is defined.
- "the records gate", `docs/guide/linking-and-validation.md`: defined in
  place as the check TCW itself runs before an item moves into the stage after
  `implement`, with the same link.
- "deciding manifest entry", `docs/guide/multi-repo.md` (twice): "the manifest
  entry that decides where the project is", the first time with a link to
  step 2 of "How TCW looks for a project", which says an entry decides.
- "load order", `README.md`'s command table: "the order its ancestors are read
  in, a later one's value winning", as the Related projects guide defines it.

No behaviour is stated anew here; each definition repeats the guide it links.

### 6. A leaf slug in `--vocab`

`skills/setup/references/taxonomy.md`: a `<ref>` is a full identifier, a
whole path (a parent's included), or a leaf slug of this project's own terms;
a leaf slug of a parent's term exits 2. Checked in `app`, with `core`
declaring `vocab-refund` and `vocab-refund/nested`:
`--vocab nested` exit 2, `vocabulary ref 'nested' does not resolve`;
`--vocab vocab-refund/nested`, `--vocab vocab-refund` (the parent's term by its
whole path, which is also its slug) and `--vocab core.taxonomy/vocab-refund`
exit 0, storing `core.taxonomy/vocab-refund`; `--vocab deep`, the leaf slug of
`app`'s own `own-term/deep`, exit 0, storing `app.taxonomy/own-term/deep`.
So the review's "the project's own terms only" holds for a leaf slug, not for
a path.

### 7. `tcw-version` in the user-wide file

`skills/configure/references/personal.md` and
`skills/configure/references/work.md` (the review's "work skill's `work.md:42`"
is the configure skill's): the file must not hold the line; one there stops
every command with exit 1. Checked with a user-wide file holding
`tcw-version: 4.0.0` and `user.name`: `tcw work list` and `tcw validate` each
exit 1, `<file>: tcw-version: a shared key; a personal file cannot set it`
(`tcw validate` as `1 error, 0 warnings, 0 unresolved` and the same line).

### 8. Asking a project not on this machine

`skills/capabilities/SKILL.md`: exit 5 when a manifest here places the
project, exit 1 ending `check the spelling` when nothing here knows its ID.
Checked: `tcw -C tcw://core.path/ work list` with `core` placed but missing,
exit 5; `tcw -C tcw://zzz.path/ work list`, exit 1, `no project with ID 'zzz'
is known or found near this one; check the spelling`.

### 9. The exit-3 message's command

`skills/work/SKILL.md`: the message ends `run the command there:` followed by
`tcw -C <folder>` and an ellipsis standing for the refused command; run the
same command with `tcw -C <folder>` before it. Checked: `tcw work edit
core.work/… --title X` and `tcw work comment core.work/…` in `app` each exit
3, `… belongs to project 'core'; run the command there: tcw -C <core's folder> …`.
The message is described in words rather than quoted whole, because the
shipped-text command check reads a quoted `tcw -C <folder> …` as a command
whose `-C` target is a phrase (both checks went red on the first wording).

### 10. Plain language

- `skills/setup/references/project.md`: "every command except `tcw migrate`
  exits 1 …, `tcw validate` and `tcw project new` among them". Checked on
  `p3` before its migration: `tcw validate`, `tcw project new --id p3` and
  `tcw work list` each exit 1 with the line ending
  `run 'tcw migrate' in it to move it to TCW 4`; `tcw migrate --dry-run` exit 0.
- `skills/work/SKILL.md`, the provisioning bound: the one sentence is now six,
  with the manifest's owner defined; their content is the Related projects
  guide's "Where a clone may be placed", including that the entry needs a
  `repository` as well as a `path`.
- `agents/backlog-auditor.md`: the input is the full identifier
  `<project>.work/<id-path>`, with `<id-path>` defined, or the tracker key,
  as spec 5.6 (b) and `agents/reviewer.md` give it. `tcw work show` takes a
  tracker key (`tcw/work/cli.py:253`); not run, as no Jira was used.

### 11. A work item's folder

"never moves" is now "does not move when its stage changes" in
`docs/capabilities/work/open-a-work-item/description.md`,
`docs/capabilities/capabilities/detect-capability-drift/description.md` and
`README.md` (twice; the second also names `tcw work move` and
`tcw work rename`). Both records are already under `changed:` in the item's
`capabilities.yaml`. Checked in `app`: `tcw work advance` moved an item to
`spec` with its folder unchanged; `tcw work rename <item> renamed-item`
printed `app.work/2026-10-26-app-item -> app.work/2026-10-26-renamed-item`
and the folder was renamed.

### 12. The commit table and criterion 36

Round 1's commit table names the hashes from before the rebase. The rebased
commits, `git log --oneline --reverse 87959dac..6055731f`, with round 1's
hash for each:

| Rebased    | Round 1    | Subject                                                                                     |
| ---------- | ---------- | ------------------------------------------------------------------------------------------- |
| `3bfa1e33` | `749d4b55` | format the documents TCW-117 changes, with no change to their content                       |
| `54e8cb7e` | `7a28e17c` | the 3.x to 4.0 migration guide, its test, and the scan's table                              |
| `c9eb3f7c` | `a8c88208` | keep a quoted --origin listing exactly as tcw prints it                                     |
| `44794447` | `1b59bebf` | keep each skill's version check on the line after its front matter                          |
| `99e4d679` | `a7290540` | the README, guides, use cases and agent documents describe TCW 4.0                          |
| `14a11f0e` | `a10e1226` | let the 3.x document scan's samples name an overrides pointer                               |
| `a5acb345` | `eadf8e37` | the evals name the configuration file at .tcw/tcw-config.yaml                               |
| `9cb6dabe` | `49c921a5` | the work skill describes TCW 4.0                                                            |
| `5b047a84` | `6ea6e437` | the taxonomy and capabilities skills describe TCW 4.0                                       |
| `596e7e2f` | `fd563698` | the configure skill describes TCW 4.0's configuration                                       |
| `8013950f` | `a0ab58d7` | the setup skill, agents, procedures and other shipped text describe TCW 4.0                 |
| `86016e0f` | `b35e3a37` | the ledger's prose describes TCW 4.0                                                        |
| `331f3902` | `7a5e4607` | no live document names a 3.x form outside a passage about migrating                         |
| `9e7f3e9a` | `bc5f848d` | the changelog and release-note entries                                                      |
| `d08a5f1f` | `d4726761` | the test docstrings that named the removed --local describe a plain list                    |
| `4ad183b6` | `7e031269` | the command-line guide gives each command's words for what it left out                      |
| `5809d248` | `98487393` | the migration guide's way past a provisioning refusal says the entry needs a repository     |
| `411fb175` | —          | implement round 1                                                                           |
| `770ad282` | —          | the migration guide names A14, after the rebase onto TCW-116's round 2                      |
| `6055731f` | —          | record the suite on the rebased branch                                                      |

**The scan of spec 9.8, criterion 36.** A script calling
`doc_vocabulary.scan(text, THREE_X_PATTERNS, 0)` over every `.md` file under
`docs/taxonomy/` and `docs/capabilities/`, printing each hit but P8's, the
paragraph (`doc_vocabulary.blocks`) it sits in, and which of the live scan's
two allowances (`tcw migrate`, `migration-guide-3.X-to-4.0.0`) that paragraph
names. Run at `77b10d95`; its output, whole:

```text
docs/capabilities/capabilities/remove-a-capability/description.md:34: P7 'meta.yaml'; paragraph lines 34-34 names ['tcw migrate']
docs/capabilities/capabilities/remove-a-capability/description.md:34: P7 'item.yaml'; paragraph lines 34-34 names ['tcw migrate']
docs/capabilities/cli/get-a-suggestion-for-a-mistyped-command/description.md:12: P1 'tcw init'; paragraph lines 11-16 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/get-a-suggestion-for-a-mistyped-command/description.md:13: P1 'tcw projects'; paragraph lines 11-16 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/get-a-suggestion-for-a-mistyped-command/description.md:14: P1 'tcw config'; paragraph lines 11-16 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/get-a-suggestion-for-a-mistyped-command/description.md:14: P1 'tcw provision'; paragraph lines 11-16 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/list-connected-projects/description.md:6: P1 'tcw projects'; paragraph lines 1-8 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/provision-declared-stores/description.md:11: P1 'tcw provision'; paragraph lines 1-13 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/rely-on-one-output-contract/description.md:49: P11 '<project-id>/<'; paragraph lines 43-52 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/scaffold-the-doc-trees/description.md:14: P1 'tcw init'; paragraph lines 13-17 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/cli/show-the-effective-configuration/description.md:1: P1 'tcw config'; paragraph lines 1-1 names ['migration-guide-3.X-to-4.0.0']
docs/capabilities/taxonomy/remove-a-local-term/description.md:5: P7 'meta.yaml'; paragraph lines 5-5 names ['tcw migrate']
docs/capabilities/taxonomy/remove-a-local-term/description.md:5: P7 'item.yaml'; paragraph lines 5-5 names ['tcw migrate']
docs/capabilities/work/read-a-work-item/description.md:11: P11 '<project-id>/<'; paragraph lines 11-11 names ['migration-guide-3.X-to-4.0.0']
hits by pattern: {'P1': 8, 'P11': 2, 'P7': 4, 'P8': 95}
```

So round 1's "only P8 hits" was true only with the live scan's exemption for
a paragraph about migrating. The plain scan of spec 9.8 finds 14 more hits,
in 9 paragraphs, one in each of 9 records, each paragraph describing how 4.0 refuses or
replaces a 3.x form and naming `tcw migrate` or linking the migration guide,
as round 1's Decision 5 chose. None is a 3.x form stated as what 4.0 does,
so none was changed. No taxonomy record has a hit.

### 13. The upcoming entries

`docs/changelogs/upcoming/TCW-117-….md`: `## Added` keeps only the migration
guide; the guide's test, `THREE_X_PATTERNS` with `scan`'s `flags` and the live
scan, the index test, and the `KEY_PATHS` and `GIT_ALLOWED` changes are under
`## Internal`, as spec 10.1 lists them. `docs/release-notes/upcoming/TCW-117-….md`:
"the epic-parts flow of 3.0.1 and 3.0.2" is replaced by a plain description:
how a large item split into parts (an epic) gets a part in another project,
for an agent taught the 3.x way of filing the part into the other project's
inbox from the epic's own project. `test_upcoming_entries.py` passes.

## Decisions

Each decided by the implementing agent.

1. The migration guide's missing-project bullet no longer says what 3.x gave;
   rechecking 3.x's codes for every case would add a claim the reader does not
   need, and the scripts advice now says what to check in 4.0.
2. The way back gives commands for git and one sentence for a copied folder;
   it does not cover a Jira project's tickets beyond what the guide already
   said (no command puts them back).
3. The exit-3 message in the work skill is described in words, since the
   command check cannot tell a quoted message from a command to run.
4. The 2.1.2 release note's 3.x-form example was left: it describes 2.1.2.
5. The Related projects guide's list of listing warnings gained the taxonomy
   listing's words, a small gap found while checking finding 2.

## Tests

Run in the foreground, every `TCW_*` variable unset:

```text
.venv/bin/pytest -q -p no:cacheprovider tests/test_docs_describe_4_0.py tests/test_docs_describe_3_0.py tests/test_migration_guide_4_0.py tests/test_doc_vocabulary.py tests/test_documented_cli_surface.py tests/test_cli_guide.py tests/test_shipped_text.py tests/test_configuration_text_home.py tests/test_upcoming_entries.py tests/test_check_versions.py tests/test_skill_path_pointers.py
1358 passed, 2 skipped
```

Every named file exists. The first run was red in two tests, both on the
first wording of finding 9 (above), and green after it was reworded. The
search for bare `capabilities.yaml` entries (finding 3) and the ledger scan
(finding 12) were rerun after the commits, with the same output.

## The suite

Not run here. The dispatching session runs the full suite as CI runs it.

The full suite as CI runs it, run by the dispatching session at `5e5a7643`
(2026-10-26) in two halves by folder, every `TCW_*` variable unset: `2246 passed, 2 skipped`
and `5840 passed, 111 skipped`. `pnpm test` `247 passed`; `tsc --noEmit`,
`pnpm lint` and `pnpm check:build` clean.
