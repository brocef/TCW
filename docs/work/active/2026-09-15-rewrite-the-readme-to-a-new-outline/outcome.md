# Outcome: Rewrite the README to a new outline

All work is on branch `work/2026-09-15-rewrite-the-readme-to-a-new-outline`, in
its worktree, starting from `10b4d34b` (the `start` commit).

## What shipped, task by task

| Task | What                                                                       | Commit     |
| ---- | -------------------------------------------------------------------------- | ---------- |
| 1    | `docs/guide/work.md` formatted with prettier, on its own                   | `6776cfd3` |
| 2    | New `docs/guide/jira.md`, every sentence checked against the tracker code  | `34aec8a4` |
| 3    | `work.md`'s out-of-date tracker section replaced by a 7-line pointer       | `317cf30a` |
| 4    | README rebuilt to the outline: foreword, Problem Statement, Installation   | `39c59550` |
| 5    | Overview, Taxonomy, Capabilities                                           | `5f543bf9` |
| 6    | Work › Overview, Lifecycle with the Mermaid diagram and both tables        | `8ff01351` |
| 7    | Work › Lifecycle › Jira integration                                        | `2a34e439` |
| 8    | Work › Usage, Skills and Agents, TCW Local Web App                         | `8a246796` |
| 9    | Documentation, Development, Further Reading                                | `ea60d264` |
| 10   | Contents                                                                   | `098ba3e8` |
| 11   | `tcw-config.yaml`: README entry reworded; `docs/guide/jira.md` entry added | `775524bf` |
| 12   | `.claude/settings.json`: `skill-cefailures` no longer enabled              | `028307a1` |
| —    | `tests/test_repo_lifecycle.py` expects the new entry (see below)           | `5848e410` |
| 13   | Plain-language pass: "slug" defined where first used                       | `9352bcbc` |
| —    | Inbox entry for three defects found along the way                          | `f33e3c96` |
| —    | Plan corrected to record the missed test                                   | `3873aa1a` |

`README.md` went from 660 lines to 845.

## Test and check results

Run in the worktree, from its root, just before writing this document:

- **`pytest`**: 3363 passed, 0 failed (15 min 22 s). README.md changed once during
  that run (`9352bcbc`), so the four test files that read the README and the
  config were run again afterwards: `test_skill_lifecycle_parity.py`,
  `test_documented_cli_surface.py`, `test_documentation_sync_wiring.py` and
  `test_repo_lifecycle.py`, 387 passed.
- **The throwaway checker** (criteria 1, 3, 6, 7, 8, 19): all pass. The CLI
  coverage and skill-row checks were mutation-checked by deleting the
  `tcw work tombstone` row and the `tcw-setup` link; both went red, naming the
  missing entry.
- **Prettier** (criterion 20): `prettier --check README.md docs/guide/jira.md docs/guide/work.md`
  passes. The worktree has no `node_modules`, so the primary checkout's
  `node_modules/.bin/prettier` was run against the worktree's files and its
  `.prettierrc.json`.
- **Mermaid** (criterion 9): `npx -y @mermaid-js/mermaid-cli@11` rendered the
  block to PNG with no error, and the image was inspected.
- **`tcw validate`**: exit 0 in the primary checkout; **exit 1 in the worktree**,
  for a reason that predates this item (see below).
- **Criterion 5**: the Problem Statement body is byte-identical to
  `README.md:42-53` at `0633e7b4` (`diff` printed nothing).
- **Criterion 14**: `git diff 0633e7b4 -- docs/guide/web-viewer.md` prints nothing.
- **Criteria 2 and 18**: no dropped heading; no match for `not built`.
- **Criterion 21**: `tcw work docs` prints the reworded README entry and
  `docs/guide/jira.md [Tracker-Change]`.
- **Criterion 22**: `.claude/settings.json` parses with only `tcw@tcw` enabled;
  `git grep skill-cefailures -- README.md AGENTS.md .claude skills scripts`
  prints nothing.
- **Examples**: every `tcw taxonomy` and `tcw capabilities` example except the two
  `extends` lines was run in a scratch git repository and exited 0, followed by
  `tcw validate` (OK). The `extends` examples need a second connected project and
  were checked against `--help` only. The Jira configuration block was parsed with
  `parse_tracker_config` and returned no problems.

Criteria checked by reading, not by a command: 4, 10, 11, 12, 13, 15, 16, 17.

## What the plan or spec got wrong

1. **A test pinned the documentation entries.** The spec's non-goals and the plan
   both said no test would change. Adding the `docs/guide/jira.md` entry (request
   decision 9) broke
   `tests/test_repo_lifecycle.py::test_this_repos_documentation_entries_parse`,
   which asserts the exact list of paths and triggers. Its expected list gained
   the new path and `Tracker-Change`. The plan now records this.
2. **`tcw validate` does not pass in a fresh checkout.** Criterion 20 assumed it
   passes. It does in the primary checkout, but in the worktree it reports that
   `tcw://W/2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`
   (linked from a backlog item's request) does not exist: that item is completed,
   its folder is gitignored, and `graveyard.yaml` has no record of it. Not caused
   by this item; filed in the inbox. `complete`'s `pre: tcw validate` runs in the
   primary checkout, where it passes.
3. **A documented example is broken.** `tcw taxonomy add Permission -p admin`
   refuses unless `admin` exists. The spec told Task 5 to take examples from
   `docs/guide/taxonomy-and-capabilities.md`, which has this sequence at line 25.
   The README's copy adds `tcw taxonomy add Admin …` first; the guide still has
   the broken version (filed in the inbox).
4. **Task 1's formatting was not whitespace-only.** The plan expected
   `git diff -w` to show whitespace alone. Prettier also changed two `*emphasis*`
   markers to `_emphasis_`. Still formatting only.
5. **The first diagram was unreadable.** The plan's shape attached stage labels
   to status boxes with dotted lines; rendered, the postmortem line appeared to
   run to `discarded`. The stages now sit inside each status box. Every stage,
   status and transition the criteria require is still named.
6. **The plan's `drop` row wording was incomplete.** `tcw work drop` also refuses
   without `--confirm` (it prints "Would delete…" and exits 1); the table says so.
7. **Overview claims needed narrowing during writing.** Blockers stop `start` and
   `complete --resolution done`, not discards, and `--force` overrides them;
   status changes commit themselves by default, not always; an imported ticket
   does not pass through the inbox. The README says these precisely.

No disagreement was found between the tracker skill references
(`skills/tcw-configure/references/tracker.md`, `skills/tcw-work/references/commands.md`)
and the code. Beyond the three false claims the spec named, no other sentence
from the old `work.md` section was dropped for being false; the rest was
rewritten or carried over.

## Documentation Sync

Evaluated over the finished diff (`tcw work docs`, source `config`):

- `README.md` [Public-API] and `docs/guide/jira.md` [Tracker-Change]: these are
  the deliverables.
- `docs/release-notes/upcoming.md` [Public-API]: not triggered. No CLI surface or
  behavior changed.
- `docs/changelogs/upcoming.md` [Any-Code-Change]: not triggered. The only
  change outside documentation and configuration is a test's expected list,
  which changes no runtime behavior.
- `skills/<component>/SKILL.md` [Skill-Driven-Component]: not triggered.
- `skills/tcw-configure/references/<document>.md` [Configuration-Key-Change]: not
  triggered. No key was added or changed meaning.

## Notes

- **The other active item adds a skill.**
  `2026-09-15-add-a-tcw-work-create-skill-that-checks-for-overlap-before-creating-a-work-item`
  creates `skills/tcw-work-create`. At the time of writing, `main` still has 15
  skills. Whichever of the two items merges second must add that skill to the
  README's Skills and Agents tables, or criterion 8's check fails.
- GitHub rendering (Mermaid, the Contents anchors, the tables) has not been seen
  on GitHub itself. That is verification item 1 in the plan, and needs the work
  branch pushed.
