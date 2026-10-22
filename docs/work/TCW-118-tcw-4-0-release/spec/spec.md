# Spec — TCW 4.0: release

Child 13 of 13 of TCW-99, and its last. It releases TCW 4.0: it checks that the
twelve other children work together, merges the branch `v4` into `main`,
migrates this repository with `tcw migrate`, cuts version 4.0.0, publishes it,
and checks the epic's three success criteria
(`docs/work/TCW-99-…/design.md:795-807`). Almost all of it is a procedure
carried out once; the only code it changes is `scripts/cut_version.py`
(Design 3.2).

Every comment posted on this ticket by the other children is mapped, in Notes
("Handoffs answered"), to the rule below that carries it out and the criterion
that checks it. References to a sibling's rule are written "TCW-1nn Design m";
"Design 9.2", "Design 9.3" and "Design 9.5" alone mean TCW-116's; Design 9.3
(`docs/work/TCW-116-tcw-4-0-tcw-migrate-from-3-x/spec/spec.md:1413-1497`) is
the merge procedure this item carries out. Every other bare number, such as
"Design 3.2", "4.3 (b)" or "section 9", is a rule of this spec's own Design.
File and line references are at `v4` on 2026-10-22, while TCW-107 is being
built and TCW-108 to TCW-117 are at the plan stage; the plan re-finds each one
by its words.

Terms used throughout:

- **PyPI** is the Python Package Index, the public site from which
  `pip install tcw-cli` downloads TCW.
- **A tag** is a name git attaches to one commit; `v4.0.0` names the commit
  released as 4.0.0. **Pushing** sends commits or tags from this machine to the
  GitHub repository.
- **CI** (continuous integration) is the set of GitHub Actions workflows under
  `.github/workflows/`, which run on GitHub's machines.
- **The lifecycle `tcw`** is the `tcw` command on this machine's `PATH`, which
  drives this repository's own work items. Today it is the editable install
  (an install that runs the source files of a checkout in place) of the
  primary checkout `/Users/brian/Projects/TCW`, at 3.0.2 (`tcw --version`
  prints `tcw 3.0.2`).
- **The merge clone** is a separate `git clone` of this repository, made only
  for the merge, outside the primary checkout and the `v4` worktree
  (Design 9.3 step 1).
- **A fast-forward** moves a branch forward to a later commit that already
  contains it, creating no new commit.
- **The release folder** is `~/.tcw-4.0-release/`, outside every repository:
  it keeps the files the ways back need (section 9), which must outlive any one
  session's scratch folder.
- **M0** is the commit `origin/main` (GitHub's `main`) points to when the
  release starts; **V** is the commit `v4` points to when it is merged; **T**
  is the commit tagged `v4.0.0`.
- **"Run as CI runs it"** means, for the Python suite: in a fresh clone, a new
  virtual environment (a private Python installation in a folder),
  `pip install -e '.[dev]'`, then bare `pytest`, not `python -m pytest`
  (`.github/workflows/test.yml:75-76`), with `TCW_JIRA_EMAIL` and
  `TCW_JIRA_API_KEY` unset; and, for the web app, `pnpm install
  --frozen-lockfile` then `pnpm check:build` (`test.yml:78-104`), which fails
  when the committed web build differs from the source. Bare `pytest` and
  `python -m pytest` put different folders on Python's search path, which
  once made CI collect no tests while local runs passed (`pyproject.toml:36-44`).

## Capability changes

None. No user-facing capability is added, changed or removed by this item; the
children declare theirs. `scripts/cut_version.py` is contributor tooling, not
part of the product, and no capability record describes it
(`grep -rl cut_version docs/capabilities docs/taxonomy` prints nothing). So
this item writes no `capabilities.yaml`.

## Problem

TCW 4.0 is built on `v4`, 69 commits ahead of `main` and with nothing on
`main` it lacks (`git rev-list --count main..v4` and `v4..main`, 2026-10-22).
Nothing on `v4` reaches a user until it is merged and published, and five
things stand in the way of doing that safely:

1. **The version cannot be cut as the script stands.** On `v4` the five
   version files already read `4.0.0` (`pyproject.toml:7`,
   `tcw/__init__.py:1`, `.claude-plugin/plugin.json:3`,
   `.claude-plugin/marketplace.json:13`, `.codex-plugin/plugin.json:3`),
   because a 4.0 file must record a version this TCW reads (TCW-106
   Design 3.5, `docs/work/TCW-106-…/spec/spec.md:216-220`).
   `scripts/cut_version.py:168-169` refuses to cut the version the files
   already hold, and `cut_version.py major` would compute `5.0.0` from them
   (`:68-69`). No tag `v4.0.0` exists (`git tag --list 'v4*'` prints nothing).
2. **The repository's own records are 3.x.** Its configuration, ledgers and
   work items stay in the 3.x format until `tcw migrate` converts them, and
   its Jira tickets hold 3.x values in the `TCW Item` field. TCW-116 wrote the
   procedure that converts them at the merge (Design 9.3), and left its order
   against pushing and publishing to this item (Design 9.3 step 4).
3. **Pushing the tag is the publish, and nothing announces a failed one.**
   `release.yml` runs on any `v*` tag (`.github/workflows/release.yml:5-7`);
   its `publish` job uploads to PyPI only if the `test` job, which is
   `test.yml`, passes (`:13-14`). A red suite blocks the upload without a
   message anywhere a person looks; it happened to v2.0.3 and v2.1.0 in
   September 2026, which sat unpublished for two days (the maintainer's notes).
   **A version can be uploaded only once** (`docs/releasing.md:29-31`).
4. **The plugin and the CLI reach users by different roads.** The Claude
   plugin's marketplace is this repository's `.claude-plugin/marketplace.json`
   (`"source": "./"`), read from GitHub's `main`; the CLI comes from PyPI.
   When a session starts with a changed plugin version, `session_bootstrap.sh`
   installs the newest `tcw-cli` on PyPI and records the plugin's version
   (`scripts/session_bootstrap.sh:115-119`), and while that record matches the
   plugin it installs nothing more (`:92-96`). So if `main` reaches GitHub
   with the 4.0 plugin before PyPI has 4.0.0, a user starting a session in
   between gets the 3.0.2 CLI under 4.0 skills, and keeps it.
5. **One `tcw` serves this whole machine.** The lifecycle `tcw` is also the
   `tcw` every other project on this machine runs. When it becomes 4.0
   (Design 9.3 step 5), it refuses every 3.x project (TCW-106 Design 4),
   except to migrate it with `tcw migrate` (TCW-116), including the user's own setups, which the epic says
   migrate only after publication (Design 9.5).

## Goals

1. Check, before anything leaves the `v4` branch, that the children work
   together: every child completed, a review of their combined change, and
   every case in `docs/use-cases.md` answered in a child's spec (TCW-99
   success criterion 1).
2. Merge `v4` into `main` and migrate this repository in one step, as
   Design 9.3 orders it, so that `main` never holds 4.0 code with 3.x records,
   and no lifecycle command runs in between.
3. Change `cut_version.py` so it cuts a version the files already hold when
   that version has no tag, and refuses the mistakes around it.
4. Name every check made before the tag is pushed, each one something a
   reader can run, and push the tag only when all pass.
5. Order the publish so that PyPI has 4.0.0 before GitHub's `main` carries the
   4.0 plugin.
6. Keep a stop and a way back ready at every step, and say which steps have
   none.
7. After publication: retire the other checkouts, have the user's two setups
   migrated with nothing fixed by hand (success criterion 2), answer the one
   GitHub issue 4.0 settles, and complete TCW-118 and then TCW-99.

## Non-goals

- **Any change to 4.0's behavior.** A defect the combined review (Design 3.4)
  finds in a child's work is fixed on `v4` before the merge, in that child's
  area; a disagreement with the TCW-99 design is raised on TCW-99
  (the request's Constraints).
- **The 4.0 documents.** The guides, skills, use cases and migration guide are
  TCW-117's; this item checks only that the combined release notes say what
  the handoffs ask (Design 6.2 (e)).
- **The eval run** of TCW-117 Design 9.6: optional, not part of any child's
  acceptance (TCW-117's handoff). If the user asks for one before the release,
  it is the optional check in TCW-117's QA plan, run on the merged code
  before Design 6.1; nothing here waits for it.
- **The general race between plugin and CLI** (Problem 4) in every later
  release. This item orders its own publish around it; a change to
  `docs/releasing.md`'s usual `git push origin main --tags`
  (`docs/releasing.md:12`) or to `session_bootstrap.sh` is a separate item
  (Notes, "Follow-ups").
- **GitHub issue #25** (a `tcw://` reference written as a Markdown link is
  reported missing). No TCW-99 child names it; it stays open, untouched.
- **Naming the user's setups.** They are private; this repository is public.
  Every record of them gives counts only.

## Design

### 1. The order, at a glance

| Phase | Steps | Where | Lifecycle `tcw` | What leaves this machine | Stage of TCW-118 |
| --- | --- | --- | --- | --- | --- |
| A. Ready on `v4` | 3.1-3.8 | `v4` worktree | 3.0.2 | nothing | implement |
| B. Merge and migrate the files | 4.0-4.4 (Design 9.3 steps 0-4) | the merge clone | 3.0.2 (not run: rule 4.0) | the dry run reads the board | implement |
| C. Switch the CLI, convert the tickets | 5.5-5.7 (steps 5-7) | primary checkout | 4.0 from 5.5 | ticket edits on the live board | implement |
| Review | 5.8 | primary checkout | 4.0 | nothing | review |
| D. Cut and check | 6.1-6.3 | primary checkout, a fresh clone | 4.0 | a branch, not `main`, for CI | qa |
| E. Publish | 7.1-7.4 | primary checkout | 4.0 | the tag, then `main` | qa |
| F. After publication | 8.1-8.4 | this machine, the user's setups, GitHub | 4.0 | an issue reply | qa, then completed |

Each phase starts only when the previous one's last check has passed. Every
step has a stop: a check that fails stops the release at that step, and
section 9 says what undoes what was done so far.

### 2. TCW-118's own lifecycle

2.1. Request, spec and plan are driven by the 3.0.2 lifecycle `tcw`. TCW-118
moves to `implement` (still 3.0.2) before the first code change of
Design 3.2.

2.2. From rule 4.0 to the end of 5.7, no `tcw` command runs anywhere in this
repository (Design 9.3 step 0), TCW-118's included. It stays at `implement`;
the implement round records what each step did, written as files after 5.7.

2.3. After 5.7 the 4.0 lifecycle `tcw` moves TCW-118 to `review` (5.8). The
accepted review is the gate for phase D, which, with E and F, is TCW-118's
`qa` stage: qa confirms the product as a user receives it. The move to
`completed` runs `tcw validate` (`CLAUDE.md`, lifecycle table) and waits for
8.2 and 8.3.

2.4. Every move after `inbox` runs `docs/guide/examples/commit-item-after-move.sh`,
which commits the item's folder on `main` in the primary checkout. Those
commits land on top of the migrated `main` and are pushed with it (7.3) or
afterwards; they never land between the merge and the migration.

Decided by the dispatching session, 2026-10-22: the request lists publishing
as out of scope, "a person's step". The user's standing rule for this
repository, recorded 2026-09-13, is that a verified-ready release is pushed
without asking, and that publishing here is not a human-only step, because CI
publishes and needs no one's login; the request's line came from the general
rule for npm packages, which need the user's two-factor login. So this item
pushes the tag itself once every check of Design 6.2 passes, and the
publishing step stays inside its scope, as qa.

### 3. Phase A: ready on `v4`

3.1. **Every other child is completed.** `tcw work show` gives
`stage: completed` for each of TCW-106 to TCW-117, and every agent working
in the `v4` worktree has finished and been stopped, so `v4` is not moving.
TCW-116's implement rounds record its two proofs (Design 9.2, TCW-116 plan
Steps 14 and 25), including the number of hits the scan of
`tests/test_docs_describe_4_0.py` reports once `UNMIGRATED_RECORDS` is
deleted, or a sentence that the rehearsal could not be made; and TCW-116's
Step 27 comment, with the concrete commands of Design 9.3 and the way-back
script, is on this ticket. TCW-118's plan uses those commands as written.

3.2. **`scripts/cut_version.py` cuts a version the files already hold.** Its
rule at `:166-169` becomes:

- (a) An explicit version equal to the current one, with no tag
  `v<version>` in the repository: the cut proceeds. The five version files
  are left as they are (they already hold it), the `upcoming/` entries are
  combined into `v<version>.md` (`:128-157`), and the script commits and tags
  as today (`:179-181`).
- (b) An explicit version equal to the current one, with a tag `v<version>`
  in the repository: refused, with `cut_version: v<version> is already
  tagged`, before any file changes.
- (c) `patch`, `minor` or `major` while the current version has no tag:
  refused, with `cut_version: v<current> has no tag yet; cut it with
  'python scripts/cut_version.py <current>'`, before any file changes. This
  is what stops `major` from computing `5.0.0` and skipping 4.0.0
  (Problem 1).
- (d) Every other case behaves as today.

"In the repository" means the local tags (`git tag --list v<version>`); the
script reads no network, and the procedure fetches tags first (6.1).
`docs/releasing.md` gains a paragraph saying how to cut a version the files
already hold, and why a relative bump is refused then. Decided by the
dispatching session, 2026-10-22: (c) was not asked for by TCW-106's handoff,
but it costs one test and prevents the exact mistake of running `major` here;
the alternative, a warning, would not stop a commit and a tag.

3.3. **TCW-118's own entry files**, named by its folder,
`TCW-118-tcw-4-0-release.md`:

- **Release notes** (`docs/release-notes/upcoming/`): a leading paragraph
  (text before the first `##` heading, which `combine` places right after
  the title, `cut_version.py:99-125`) saying that 4.0 is a major release that
  changes where a project keeps its files and how projects relate, and that a
  3.x project must be migrated before 4.0 will work in it. Then a section
  `## Upgrading`, which `cut_version.py` places first (`:35`), saying, in
  plain words:
  - how to move across: a link to `../migration-guide-3.X-to-4.0.0.md`
    (TCW-117's handoff);
  - to keep any CI job or other automation that installs `tcw-cli` below 4
    (`tcw-cli<4`) until that project is migrated (TCW-117 Design 2.3 (f),
    TCW-117's handoff);
  - that everyone working on a project upgrades together, and that 4.0
    refuses a 3.x project's files except to migrate them;
  - to commit or back up before running `tcw migrate` for real.
- **Changelog** (`docs/changelogs/upcoming/`): under `## Changed`, the
  `cut_version.py` rules of 3.2; under `## Removed`,
  `tests/test_repo_config_pair.py` and the root `.gitignore` line
  `/tcw-config.local.yaml`; under `## Internal`, this repository migrated to
  4.0 and the ledger records brought into the documentation scan
  (`UNMIGRATED_RECORDS` deleted).

It edits no other item's entry file (`docs/release-notes/upcoming/README.md`).
What 6.2 (e) finds missing from another child's entry, this item's entry
adds.

3.4. **A review of the combined change.** Several children change the same
files, and a review of each child alone cannot see what only their
combination does. The `adversarial-code-reviewer` agent reviews
`git diff main...v4` (the change since the two branches parted), sliced by
concern rather than by file, with TCW-99's design and each child's spec as
its reading. It sorts its findings into "belongs to 4.0" and "needs a
separate change", and ends with a literal `DONE` or `NOT DONE`. A finding
that belongs to 4.0 is checked against the code first, then fixed on `v4`
by an agent briefed for it, and the slice it touched is reviewed again. A
separate change becomes a proposed work item. The review stops after two
rounds: if the second still ends `NOT DONE`, the split is brought to the
user, who decides. Decided by the dispatching session, 2026-10-22: one
reviewer rather than a three-reviewer review, since each child already had
its own reviews; the user's rule on reviews gated on a clean result requires
the stopping point to be agreed before it starts, and two rounds is it.

3.5. **Success criterion 1, checked.** For every heading `### UC-n` or
`### S-n` in `docs/use-cases.md` at `v4`'s tip, at least one spec of TCW-106
to TCW-117 names that id in its `## Use cases` section (whole word, so `S-1`
does not count as `S-10`). The check is a short script (in the plan); its
output, one line per id with the number of specs naming it, is recorded in
the implement round. At 2026-10-22 every id is named at least five times.

3.6. **The combined release notes, previewed.** `combine` (the function
`cut_version.py` uses) is run on the `upcoming/` entries without cutting, and
the preview is read against 6.2 (e), so that a missing sentence is added to
TCW-118's entry now rather than after the cut.

3.7. **The user-wide personal file.** If `$XDG_CONFIG_HOME/tcw/config.yaml`
or `~/.config/tcw/config.yaml` exists and holds `not_tags`, it is changed to
4.0's spelling before 5.5, using the line TCW-116's report A5 names: the
`tcw migrate` of 5.6 does not stop on it, but every other 4.0 command refuses
it (TCW-116's handoff). On 2026-10-22 this machine has no such file
(`~/.config/tcw` does not exist), so the step is a check.

3.8. **The user is told** before 4.0, what rule 4.0 below says, and also that
from 5.5 until 8.2 the `tcw` on this machine is 4.0, so every 3.x project on
it that runs that `tcw` is refused until migrated. Decided by the
dispatching session, 2026-10-22: TCW-116 already orders the switch at step 5,
before publication, and keeping a second, 3.x `tcw` on this machine would put
two programs under one name; the window is kept short instead, by running
phases B to E in one sitting and 8.2 right after 7.2.

### 4. Phase B: merge and migrate the files (Design 9.3 steps 0-4)

The steps are TCW-116's; this section adds only what TCW-116's comments on
this ticket ask and what the release needs.

4.0. **(Step 0)** The session carrying out the release tells every agent and
session working in this repository, by message, to run no `tcw` command until
5.7 is done, and asks the user to run none here or on another machine. It
records `git rev-parse origin/main` as M0 and `git rev-parse v4` as V in
`~/.tcw-4.0-release/refs.txt`, after `git fetch origin`.

4.1. **(Step 1)** `git clone /Users/brian/Projects/TCW <folder>` outside both
checkouts makes the merge clone (a clone, not a worktree, so that its `.git`
is its own folder and the primary checkout's editable install stays 3.0.2).
In it: a branch `release-4.0.0` from `origin/main` (M0), then
`git merge --no-ff v4`. A conflict with a 3.x patch that reached `main` after
the split is resolved in the clone by applying the patch's intent to the 4.0
code, and the resolution is reviewed as 3.4 reviews, before 4.2. A virtual
environment in the clone holds its code (`python -m venv .venv`,
`.venv/bin/pip install -e '.[dev]'`, run from the clone's root, as
`CLAUDE.md` says for worktrees), and **its `tcw` is run by its full path**,
never as a bare `tcw` and never with `.venv/bin` first on `PATH` (Design 9.2;
TCW-116's handoff).

4.2. **(Step 2)** In the clone, `tcw migrate --dry-run` with the Jira
credentials set; its output is saved as `~/.tcw-4.0-release/tcw116-dry-run.txt`
and read: every ticket it lists is in the Jira project `TCW` (UC-5), each
with its old and new value. Then `tcw migrate --no-jira`, with `https_proxy`
and `HTTPS_PROXY` set to `http://127.0.0.1:9`, an address nothing listens on,
so that no request could leave the machine even by mistake; the flag is what
keeps the step off the board, the setting only proves it. It converts the
files only and exits 0.

4.3. **(Step 3)** In the clone:

- (a) delete `tests/test_repo_config_pair.py` and the root `.gitignore`
  line `/tcw-config.local.yaml` (TCW-116 A4);
- (b) delete `UNMIGRATED_RECORDS` from `tests/test_docs_describe_4_0.py`
  (its comment names TCW-118; TCW-117 spec, `:1230-1237`), run that test, and
  compare its hits with the count TCW-116's second proof recorded (3.1). A
  different count is explained before anything is fixed: it means something
  changed the records after the proof;
- (c) fix every hit in `docs/taxonomy/` and `docs/capabilities/` by editing
  files, which runs no `tcw` command and so keeps rule 4.0;
- (d) run the suite as CI runs it (Terms), in the clone, with the Jira
  credential variables unset and no proxy setting (the suite's own servers
  listen on this machine), and `pnpm check:build`;
- (e) run 4.0's `tcw validate` by its full path;
- (f) search `git diff M0` in the clone for the names of the user's private
  projects, from the maintainer's own notes (not repeated here, since this
  repository is public). Nothing may match.

4.4. **(Step 4)** Commit the migration as one commit after the merge commit,
then, in the clone, fast-forward `main` to it (`git checkout main` and
`git merge --ff-only release-4.0.0`), so the merge and the migration reach
`main` together. Nothing is pushed: `git ls-remote origin main` still prints
M0.

### 5. Phase C: switch the CLI and convert the tickets (steps 5-7)

5.5. **(Step 5)** In the primary checkout, which is on `main` with no changes
and at M0: `git pull --ff-only <merge clone folder> main`, then
`pip install -e '.[dev]'` again, since 4.0 may change its dependencies. The
lifecycle `tcw` is now 4.0: `tcw --version` prints `tcw 4.0.0`. An untracked
root `tcw-config.local.yaml`, if any, is still 3.x; 5.6 converts it.

5.6. **(Step 6)** The first write to the live Jira board: `tcw migrate` in the
primary checkout with the credentials set. It reads its Jira settings from
`.tcw/tcw-config.yaml`'s `work.jira` (TCW-116 Design 5.1), converts the
personal file and then every ticket's `TCW Item`. Its whole output is saved as
`~/.tcw-4.0-release/tcw116-step6.txt`: its `C17` lines are the edits this run
really made. Its ticket keys are compared with the dry run's; a key in only
one of the two files is read, and the reason recorded, before anything else
happens. A run that stops partway says what it did and is run again to
finish (TCW-116 Design 2, S-8); it never repeats an edit it made.

5.7. **(Step 7)** `tcw migrate` once more prints `nothing to migrate`;
`tcw validate --remote` exits 0, and `tcw work list` lists every ticket with
no warning about unconverted ones. Rule 4.0 ends here, and the session tells
the agents and the user so.

5.8. **The review.** The 4.0 lifecycle `tcw` moves TCW-118 to `review`. The
review stage follows `docs/lifecycle/review.md`: the suite run as CI runs it
on the migrated `main`, and the documentation entries
(`tcw work docs`) evaluated, before an accepted verdict. Phase D starts only
on an accepted verdict.

### 6. Phase D: cut and check, before the tag

6.1. **The cut.** In the primary checkout: `git fetch --tags origin`;
`git ls-remote --tags origin v4.0.0` prints nothing; then
`python scripts/cut_version.py 4.0.0` (rule 3.2 (a); not `major`, which
3.2 (c) refuses). It combines the entries into `docs/changelogs/v4.0.0.md`
and `docs/release-notes/v4.0.0.md`, commits `chore(release): cut v4.0.0` and
tags that commit, T, locally. Nothing is pushed.

6.2. **The checks on T.** All of them pass before 7.1:

- (a) **The suite as CI runs it, here.** A fresh `git clone` of T into a new
  folder; the suite as CI runs it (Terms) with Python 3.14, credentials
  unset; and `pnpm check:build`. Both exit 0.
- (b) **The suite in CI itself, before the tag.** T is pushed to a branch,
  never `main`: `git push origin T:refs/heads/release-4.0.0`; then
  `gh workflow run test.yml --ref release-4.0.0` (the workflow accepts a
  manual start, `test.yml:42`; a branch push alone starts nothing,
  `test.yml:32-33`). The run's commit is T, and its three jobs, `pytest` on
  3.11, `pytest` on 3.14 and `web-build`, all succeed. Decided by the
  dispatching session, 2026-10-22: this machine has no Python 3.11
  (`pyenv versions` lists 3.12.13 and 3.14.6), and the release's gate is this
  same workflow (`release.yml:10-14`), so running it before the tag is the
  only way to know the gate will open before the tag is on GitHub. A branch
  other than `main` is not what the plugin marketplace reads (Problem 4).
- (c) **`tcw validate` with the 4.0 CLI.** In the primary checkout at T,
  `tcw validate` and `tcw validate --remote` exit 0.
- (d) **The five version files agree.** Each of the five files of `CLAUDE.md`
  "Versioning" reads `4.0.0`, `.agents/plugins/marketplace.json` carries no
  version, and the tag's name without its `v` equals `pyproject.toml`'s
  version, the comparison `release.yml:34-44` makes.
  `tests/test_plugin_manifests.py`, part of (a), guards the agreement.
- (e) **The release notes.** `docs/release-notes/v4.0.0.md` and
  `docs/changelogs/v4.0.0.md` exist, each starting `# v4.0.0`; both
  `upcoming/` folders hold only `README.md`. The release notes' first `##`
  section is `## Upgrading`; they link `migration-guide-3.X-to-4.0.0.md`, and
  that file exists under `docs/`; they say to keep automation that installs
  `tcw-cli` below 4 until a project is migrated; they name the
  `tcw project` command group and the four 3.x commands it replaces, each
  with its replacement (TCW-115's handoff); and they say, in plain words
  (TCW-115's handoff of 19:45, which revises the one of 18:49):
  - a clone made from a manifest other than the active project's own is
    placed only directly beside that project, never at or above the home
    folder, and never inside a hidden folder below it;
  - a folder holding only `.git` is refused;
  - projects already on the machine are never moved by a manifest fetched
    during the run;
  - a store whose `ref` names no branch, tag or commit now fails rather
    than being read as a file.

  The private-name search of 4.3 (f), run on `git diff M0 T`, finds nothing.
- (f) **An install from a local tarball, in a clean virtual environment.** In
  the fresh clone of (a), `python -m build` writes
  `dist/tcw_cli-4.0.0.tar.gz` (the source archive, the tarball) and a wheel.
  A new virtual environment, in a folder outside every project, installs the
  tarball with `pip install`. Its `tcw --version` prints `tcw 4.0.0`;
  `tcw --help` lists `project` and `migrate`; the installed package holds
  `tcw/serve/dist/index.html` and the stage prompts under `tcw/work/prompts/`
  (`pyproject.toml:32-34`). In a new, empty git repository it creates a
  project with `tcw project new` (with the arguments TCW-115 gives it), files
  a work item with `tcw work new`, lists it with `tcw work list`, and passes
  `tcw validate`. A second virtual environment installs `tcw-cli==3.0.2` from
  PyPI, creates a 3.x project with `tcw init` and one work item; the
  tarball's `tcw migrate --no-jira` migrates it (exit 0), and its
  `tcw validate` then passes. Decided by the dispatching session,
  2026-10-22: the user's publishing rule (test with a local tarball first)
  is written for npm, and applies here unchanged in spirit: what PyPI will
  serve is the built archive, not the checkout.
- (g) **Success criterion 3: a single project needs no more configuration
  than in 3.x.** With the two projects of (f) made with the same answers:
  every top-level key of the 4.0 project's `.tcw/tcw-config.yaml`, apart from
  `tcw-version`, is a key of the 3.0.2 project's `tcw-config.yaml`; and the
  migrated 3.x project's `.tcw/tcw-config.yaml` holds the same values as its
  3.x file plus the `tcw-version` line (TCW-116, UC-1:
  `spec.md:1528-1530`).
- (h) **The plugin, from the checkout.** With the tarball environment's
  `bin` first on `PATH`, a Claude Code session started as
  `claude -p --plugin-dir <fresh clone> --output-format stream-json --verbose`
  with a prompt asking it to run `tcw --version` and report the output: its
  `init` event lists exactly one plugin, whose path is the fresh clone and
  whose version is `4.0.0` (the fields `evals/run_evals.py:195-199` and
  `:261` read); the session reports `tcw 4.0.0`; and
  `bash scripts/check_versions.sh <fresh clone>` prints nothing, since the
  plugin and the CLI agree. Codex and Pi load the same `skills/` tree from
  the same manifests (`.codex-plugin/plugin.json`, `package.json`'s `pi`),
  checked by (a)'s `tests/test_plugin_manifests.py`; no live Codex or Pi
  session is part of the release. Decided by the dispatching session,
  2026-10-22: TCW-117 owns whether the skills work in each harness; this
  check only proves the package and the plugin come from the same release.

6.3. **A failed check.** No tag is pushed. The fix is a new commit on `main`
in the primary checkout (in the child's area, briefed as 3.4 does); while the
tag is not on GitHub, it is moved to the new commit with
`git tag -f v4.0.0 HEAD`, the branch `release-4.0.0` is pushed again, and
every check of 6.2 runs again on the new T, not only the one that failed.

### 7. Phase E: publish

7.1. **Push the tag alone:** `git push origin v4.0.0`. This is the publish:
`release.yml` runs the suite and, only if it passes, builds and uploads
(`release.yml:5-7`, `:13-14`, `:46-50`). It is pushed without asking, by the
user's standing rule, once 6.2 passed. `main` is not pushed yet.

7.2. **Confirm the upload landed.** `gh run watch` on the release run for
`v4.0.0`: its `test` and `publish` jobs succeed. Then
`https://pypi.org/pypi/tcw-cli/4.0.0/json` returns the release, with
`info.version` `4.0.0`. The versioned address is used because the package's
top-level address keeps reporting the previous version for a while.

7.3. **Then push `main`:** `git push origin main`, a fast-forward from M0.
`origin/main` then contains T, the plugin marketplace reads the 4.0 plugin,
and a session that installs the CLI because the plugin changed finds 4.0.0
on PyPI (Problem 4). Then the branch `release-4.0.0` is deleted from GitHub
(`git push origin --delete release-4.0.0`). Decided by the dispatching
session, 2026-10-22: the tag first and `main` after PyPI has the release,
rather than `git push origin main --tags` (`docs/releasing.md:12`), because
the usual order lets the plugin reach users before the CLI does; the cost is
a few minutes in which PyPI has 4.0.0 and the marketplace still has 3.0.2,
during which nothing installs the CLI on its own.

7.4. **If the release run fails:**

- (a) its `test` job fails: nothing is uploaded, but `v4.0.0` is on GitHub.
  `main` stays unpushed. The session stops and asks the user whether to move
  the tag to a fixed commit or to cut 4.0.1, since rewriting a tag already on
  GitHub is the user's decision (their standing rule names it). 6.2 (b) makes
  this unlikely, since it ran the same workflow on the same commit.
- (b) `publish` fails before uploading (for example a Trusted Publishing
  mismatch, `docs/releasing.md:20-27`): the configuration is corrected and
  the job re-run on the same tag.
- (c) anything fails after the upload: 4.0.0 is spent; the fix ships as
  4.0.1 (`docs/releasing.md:29-31`).

### 8. Phase F: after publication

8.1. **Other checkouts (step 8).** Each worktree in `git worktree list` is
either removed with `git worktree remove`, once every agent working in it has
been stopped, or brought to `main` and migrated with `tcw migrate` before any
other `tcw` command runs in it. The `v4` worktree is removed. A locked
worktree belongs to another session: it is left alone and named to the user.
A branch still in progress that merges into `main` later brings 3.x files
with it, and `tcw migrate` after that merge converts them (TCW-116
Design 2.11).

8.2. **The user's two setups (success criterion 2).** After 7.2, in each of
the user's two multi-repository setups, `tcw migrate --dry-run`, then
`tcw migrate`, then `tcw validate`, with 4.0.0. The user runs them, or an
agent does at the user's word for each setup, since they are the user's
projects and their tickets are on the user's boards. A comment on TCW-118
records, for each setup and without naming it, the dry run's counts, both
exit codes, and whether anything had to be fixed by hand. If anything did,
that is a 4.0 defect: it becomes a work item, and criterion 2 is unmet until
a patch release fixes it and the setup migrates without it.

8.3. **GitHub issue #24** ("Audit backlog: spawn an auditor subagent per TCW
work root"), filed against TCW-22, which TCW-99 folded into TCW-113, whose
Design 7.1 makes the `audit-backlog` procedure cover a project's family. It
is the only open issue a TCW-99 child answers (Notes, "GitHub issues"). After
7.2, a reply naming 4.0.0 and what changed is drafted, the user approves its
exact text, and only then is it posted (`gh issue comment 24`) and the issue
closed. Nothing is posted to an issue without the user approving the exact
words (`CLAUDE.md`).

8.4. **Completing.** TCW-118's qa records the QA plan's results, then the
move to `completed`, which runs `tcw validate`, after 8.2 and 8.3. **TCW-99
is completed after TCW-118:** a comment on TCW-99 records the three success
criteria with their evidence (3.5's output, 8.2's records, 6.2 (g)'s
comparison), and the 4.0 lifecycle `tcw` moves it to `completed`.

### 9. The ways back

| After | What has left the machine | The way back |
| --- | --- | --- |
| Phase A | nothing | Ordinary commits on `v4`. |
| 4.1-4.3 | the dry run read the board | Delete the merge clone. |
| 4.4 | nothing | Delete the merge clone; the primary checkout is untouched. |
| 5.5 | nothing | In the primary checkout, `git reset --keep M0` (the commits are on no other machine) and `pip install -e '.[dev]'` again: the lifecycle `tcw` is 3.0.2. |
| 5.6-5.7 | ticket edits | The files as for 5.5. The tickets: the way-back script of TCW-116's Step 27 reads the `C17` lines of `tcw116-step6.txt` into pairs, stops on any key found in only one of it and `tcw116-dry-run.txt` until a person has read it, and calls the Jira backend's restore method with the pairs the other way round and a Jira client built by hand from `.tcw/tcw-config.yaml` only on the day it is needed (TCW-116 Design 5.4, its handoffs). It puts every 3.x value back and edits no other field. |
| 6.1-6.3 | the branch `release-4.0.0` | Delete the local tag (`git tag -d v4.0.0`) and the branch on GitHub; then as for 5.6. |
| 7.1 | the tag | 7.4. Withdrawing 4.0 entirely means the user deleting the tag on GitHub; nothing was published if 7.2 failed. |
| 7.2-7.3 | the release on PyPI, `main` | None that unpublishes. The fix is 4.0.1. Hiding 4.0.0 from installers (PyPI's "yank") is done only on pypi.org, logged in as the user, with their two-factor login. `main` is reverted with new commits (the migration and then the merge), never rewritten. |

### 10. What the user does

- **For PyPI: nothing.** CI publishes with Trusted Publishing, which needs no
  password, token or login (`release.yml:16-21`, `docs/releasing.md:15-18`).
- **For the plugins: nothing.** No marketplace needs a separate publish: the
  Claude marketplace is `.claude-plugin/marketplace.json` in this repository,
  read from `main`; Codex reads `.agents/plugins/marketplace.json` from the
  repository; Pi reads `package.json`'s `pi` declaration, and that
  `package.json` is marked `"private": true` and published to no package
  registry, so there is no npm step and no two-factor login.
- **Approve** the exact text of the reply to issue #24 (8.3).
- **Migrate, or let an agent migrate,** their two setups (8.2), and run no
  `tcw` command during 4.0-5.7 (3.8).
- **Decide** only if 7.4 (a) happens (move the tag or cut 4.0.1), if 3.4's
  second round ends `NOT DONE`, or if 4.0 must ever be hidden from installers
  (9, the yank).

## Abstraction litmus test

No new operation. The release's own steps (merging, committing, tagging,
pushing) are the maintainer's, carried out by people and agents, never by
TCW, which changes no git state (`docs/lifecycle/abstraction.md`, "any
operation that changes git state"). `scripts/cut_version.py` is contributor
tooling outside the `tcw` package (`pyproject.toml:29-30` packages only
`tcw*`), so it is in neither the model nor a backend. `tcw migrate` and the
Jira restore method are TCW-116's, and pass there (TCW-116, "Abstraction
litmus test").

## Use cases

This repository is a UC-1 project (a single project in its own repository,
work in Jira); the release touches the cases below. The others are answered by
the children's specs, which 3.5 checks.

- **UC-1.** This repository is migrated as one; success criterion 3 is
  checked on a new and a migrated single project (6.2 (g)).
- **UC-2 and UC-7 (libraries others read).** Readers of a published library
  keep their automation below 4 until migrated (3.3, the release notes); a
  4.0 project reading a 3.x one reports it as needing `tcw migrate`
  (design.md:709-711).
- **UC-5 (a shared Jira project).** The dry run lists only tickets in the
  `TCW` project (4.2), and the conversion edits only this project's tickets'
  `TCW Item` (TCW-116 Design 5).
- **S-2 (harness).** The plugin check runs under Claude (6.2 (h)); Codex and
  Pi read the same skills from the same release, checked by the manifests
  test. Nothing required of a user is carried by a Claude-only feature.
- **S-3 (backend).** The files store is exercised by 6.2 (f)'s new project,
  Jira by 4.2 and 5.6.
- **S-4 (copies of a checkout).** The merge clone is a clone, not a worktree
  (4.1); other worktrees are removed or migrated (8.1).
- **S-6 (unattended runs).** CI publishes on the tag (7.1); automation that
  installs `tcw-cli` is told to stay below 4 until migrated (3.3).
- **S-7 (several people at once).** Rule 4.0 stops every agent and session
  while the format changes underneath them.
- **S-8 (partial failure).** A stopped `tcw migrate` is run again to finish
  (5.6); a failed check stops the release before anything is published
  (6.3); a failed release run is handled by 7.4.
- **S-9 (upgrades).** The plugin and CLI are released together at one
  version, and ordered so the CLI reaches PyPI before the plugin reaches
  `main` (7.3).
- **S-11 (version control).** Every git action here is the maintainer's.

The checklist of `docs/use-cases.md`: 1 (where it looks) — no lookup changes;
2 (whose things) — only this repository, and the user's setups only at the
user's word (8.2); 3 (reading across projects) — no change; 4 (backends) —
S-3 above; 5 (who decides) — the user decides 7.4 (a), 8.2, 8.3 and a
`NOT DONE` second review (10); 6 (harness) — S-2 above; 7 (stopping halfway)
— section 9 and 7.4; 8 (single project) — 6.2 (g); 9 (older and newer TCW) —
S-9 above and Problem 5; 10 (testing the setup claimed) — the real repository,
the real board and the built archive, not fixtures.

## Acceptance criteria

Phase A

1. Before 4.0, `tcw work show TCW-1nn` prints `stage: completed` for each of
   TCW-106 to TCW-117, and the implement round records the twelve outputs.
2. `tests/test_cut_version.py` has a test in which the files hold `X`, no tag
   `vX` exists, and `cut_version.main(["X"])` exits 0, leaves the five files
   at `X`, writes `docs/changelogs/vX.md` and `docs/release-notes/vX.md`,
   makes the commit `chore(release): cut vX` and the tag `vX`, and leaves
   `git status --porcelain` empty.
3. A test in which tag `vX` exists and `cut_version.main(["X"])` exits
   non-zero with a message containing `vX is already tagged`, and HEAD, the
   tags and `git status --porcelain` are as before.
4. A test, for each of `patch`, `minor` and `major`, in which the files hold
   `X` with no tag `vX`: the call exits non-zero with a message containing
   `cut_version.py X`, and nothing changes as in 3.
5. With a tag for the current version, `patch`, `minor`, `major` and an
   explicit higher version bump as before: every test in
   `tests/test_cut_version.py` that existed before this item passes, its
   fixture adding the tag where it needs one.
6. `docs/releasing.md` says how to cut a version the files already hold and
   that a relative bump is refused while the current version has no tag.
7. `docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md` exists, with a
   leading paragraph and an `## Upgrading` section holding the four points
   of 3.3; `docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md` has the
   entries of 3.3 under `## Changed`, `## Removed` and `## Internal`. No
   other item's entry file is changed by this item (`git log` of
   `docs/*/upcoming/` shows TCW-118's commits touching only its own files).
8. The implement round holds the combined review's reports: each ends with
   `DONE` or `NOT DONE`; each "belongs to 4.0" finding is marked accepted,
   narrowed or rejected with a reason, and each accepted one names its fix
   commit on `v4`; the last report ends `DONE`, or the user's decision on a
   second `NOT DONE` is recorded.
9. The implement round holds 3.5's output: a line for every `UC-n` and `S-n`
   heading of `docs/use-cases.md` at V, each with a count of at least 1.
10. The implement round records TCW-116's proof-2 hit count (or that the
    rehearsal could not be made), and this ticket carries TCW-116's Step 27
    comment, before 4.0.
11. Before 5.5, neither `$XDG_CONFIG_HOME/tcw/config.yaml` nor
    `~/.config/tcw/config.yaml` holds `not_tags` (or the round records the
    line changed).

Phase B

12. The implement round records when the messages of 4.0 and 3.8 were sent,
    and to whom; and `~/.tcw-4.0-release/refs.txt` holds M0 and V.
13. In the merge clone, `.git` is a folder, the clone's folder is outside
    `/Users/brian/Projects/TCW`, and the commit after M0 on
    `release-4.0.0` is a merge whose parents are M0 and V.
14. `~/.tcw-4.0-release/tcw116-dry-run.txt` exists; the dry run exited 0;
    every ticket key it names matches `^TCW-[0-9]+$`; the round records how
    many.
15. `tcw migrate --no-jira`, run by the clone's `.venv/bin/tcw` with the dead
    proxy set, exited 0 and its summary says the tickets were not converted.
16. In the clone after 4.3: `tests/test_repo_config_pair.py` does not exist;
    `grep -n 'tcw-config.local' .gitignore` prints nothing;
    `grep -n UNMIGRATED_RECORDS tests/test_docs_describe_4_0.py` prints
    nothing; and the round gives the hit count, the proof's count, and the
    reason for any difference.
17. In the clone after 4.3, with the Jira variables unset: bare `pytest` in
    the clone's environment exits 0, `pnpm check:build` exits 0, and
    `.venv/bin/tcw validate` exits 0.
18. The private-name search of `git diff M0` in the clone prints nothing.
19. After 4.4, the clone's `main` is one commit after the merge commit, and
    `git ls-remote origin main` prints M0.

Phase C

20. After 5.5, the primary checkout's `git rev-parse main` equals the clone's,
    and `tcw --version` prints `tcw 4.0.0`.
21. `~/.tcw-4.0-release/tcw116-step6.txt` exists and `tcw migrate` exited 0
    (after re-runs, if it stopped); the round lists any key found in only
    one of it and the dry run, with the reason.
22. After 5.7: `tcw migrate` printed `nothing to migrate` and exited 0;
    `tcw validate --remote` exited 0; `tcw work list` printed no warning
    about unconverted tickets.
23. TCW-118's review round is accepted before 6.1, and records the suite run
    as CI runs it on the migrated `main`.

Phase D

24. Before the cut, `git ls-remote --tags origin v4.0.0` printed nothing;
    `python scripts/cut_version.py 4.0.0` exited 0; HEAD's subject is
    `chore(release): cut v4.0.0`, and the local tag `v4.0.0` points at it.
25. 6.2 (a): in a fresh clone of T, with Python 3.14 and the Jira variables
    unset, bare `pytest` exits 0 and `pnpm check:build` exits 0.
26. 6.2 (b): `gh run view` of the `test` workflow started on
    `release-4.0.0` shows head commit T, and `pytest (3.11)`,
    `pytest (3.14)` and `web-build` all with conclusion `success`.
27. 6.2 (c): at T, `tcw validate` and `tcw validate --remote` exit 0.
28. 6.2 (d): `grep` finds `4.0.0` as the version in each of the five files;
    `.agents/plugins/marketplace.json` has no `version` key; the tag name
    without `v` equals `pyproject.toml`'s `project.version`.
29. 6.2 (e): every statement of 6.2 (e) holds of the two shipped files and
    the two `upcoming/` folders at T, checked one by one in the qa record;
    and the private-name search of `git diff M0 T` prints nothing.
30. 6.2 (f): the tarball `tcw_cli-4.0.0.tar.gz` built from T installs in a
    new virtual environment, and every command named in 6.2 (f), the
    3.0.2-to-4.0 migration included, exits 0 with the output stated there.
31. 6.2 (g): the two key comparisons of 6.2 (g) hold; the qa record shows
    both files.
32. 6.2 (h): the session's `init` event lists one plugin, path the fresh
    clone, version `4.0.0`; the session reports `tcw 4.0.0`;
    `scripts/check_versions.sh` prints nothing.
33. If a check of 6.2 failed, the qa record shows the fix commit, the moved
    local tag, and every check of 6.2 run again on the new T.

Phase E

34. The tag was pushed by itself: until 7.2 passed, `git ls-remote origin main`
    printed M0.
35. The release run for `v4.0.0` shows `test` and `publish` with conclusion
    `success`, and `https://pypi.org/pypi/tcw-cli/4.0.0/json` returns
    `info.version` `4.0.0`.
36. After 35, `git merge-base --is-ancestor T origin/main` succeeds, and
    `git ls-remote origin release-4.0.0` prints nothing.
37. If the release run failed, the record shows 7.4 followed: for a failed
    `test` job, the user's decision before any tag was moved.
38. A clean install from PyPI works: `pipx run --spec tcw-cli==4.0.0 tcw --version`
    prints `tcw 4.0.0`.

Phase F

39. After 8.1, `git worktree list` shows the primary checkout and only
    worktrees that are locked (named to the user) or in which `tcw validate`
    passes.
40. A comment on TCW-118 records, for each of the user's two setups and
    without naming it, the dry run's counts, the exit codes of
    `tcw migrate` and `tcw validate`, and that nothing was fixed by hand, or
    the work item filed for what was.
41. Issue #24 is closed, after 35, with a reply whose text the user approved
    in this conversation; the approval and the text are in TCW-118's qa
    record.
42. TCW-118 is completed after 40 and 41, and its move ran `tcw validate`
    successfully. TCW-99 then has a comment giving the three success
    criteria with their evidence, and is completed.

### Coverage

Each numbered rule of the Design, with the criteria that check it. A cell is
a criterion number, or `n/a` with the line that makes it so.

| Design rule | Criteria |
| --- | --- |
| 1 the order | 1, 12, 23, 24, 34, 36 (each phase's gate) |
| 2.1 lifecycle to implement before code | n/a: a lifecycle move, checked by `tcw work advance`'s own gate (`CLAUDE.md:41-44`) |
| 2.2 no `tcw` from 4.0 to 5.7 | 12, 22 |
| 2.3 review gates D; qa holds D-F | 23, 42 |
| 2.4 hook commits after the migration | 19 (one commit after the merge), 36 |
| 2.4 decision: the tag is pushed by this item | 34, 35 |
| 3.1 children completed, TCW-116's records | 1, 10 |
| 3.2 (a) | 2 |
| 3.2 (b) | 3 |
| 3.2 (c) | 4 |
| 3.2 (d) | 5 |
| 3.2 releasing.md | 6 |
| 3.3 entry files | 7, 29 |
| 3.4 combined review | 8 |
| 3.5 success criterion 1 | 9, 42 |
| 3.6 preview of the notes | 29 (the same statements, on the shipped file) |
| 3.7 user-wide file | 11 |
| 3.8 the user told | 12 |
| 4.0 step 0 | 12 |
| 4.1 step 1 | 13 |
| 4.2 step 2 | 14, 15 |
| 4.3 (a) | 16 |
| 4.3 (b) | 16 |
| 4.3 (c) | 17 (the suite and validate pass only when the hits are fixed) |
| 4.3 (d) | 17 |
| 4.3 (e) | 17 |
| 4.3 (f) | 18 |
| 4.4 step 4 | 19 |
| 5.5 step 5 | 20 |
| 5.6 step 6 | 21 |
| 5.7 step 7 | 22 |
| 5.8 review | 23 |
| 6.1 cut | 24 |
| 6.2 (a) | 25 |
| 6.2 (b) | 26 |
| 6.2 (c) | 27 |
| 6.2 (d) | 28 |
| 6.2 (e) | 29 |
| 6.2 (f) | 30 |
| 6.2 (g) | 31 |
| 6.2 (h) | 32 |
| 6.3 failed check | 33 |
| 7.1 tag alone | 34 |
| 7.2 upload confirmed | 35, 38 |
| 7.3 `main` after PyPI | 36 |
| 7.4 (a)-(c) | 37 |
| 8.1 other checkouts | 39 |
| 8.2 user's setups | 40 |
| 8.3 issue #24 | 41 |
| 8.4 completing | 42 |
| 9 ways back | n/a as criteria: a way back is run only when a step fails; each row's inputs are checked to exist by 12 (M0), 14 (dry-run file), 21 (step-6 file) and 10 (the way-back script) |
| 10 what the user does | 37, 40, 41 (the three user decisions that can arise) |

## Risks

- **This machine's other 3.x projects are refused from 5.5 until migrated**
  (Problem 5). Met by telling the user first (3.8) and migrating their setups
  right after publication (8.2).
- **The board is converted before GitHub's `main` is.** From 5.6 to 7.3 the
  tickets hold 4.0 values while `origin/main` is 3.x; anyone pulling
  `origin/main` and using 3.0.2 on this board in that window would see items
  it cannot read. Assumption, not checked: no one but the user and this
  machine's agents works on the `TCW` board. Rule 4.0 and one sitting keep the
  window short.
- **A remote tag with a red release run** (7.4 (a)). Made unlikely by 6.2 (b)
  running the same workflow on the same commit.
- **A merge conflict with a late 3.x patch on `main`** (4.1). Today `main` has
  nothing `v4` lacks; any later patch is reviewed in its 4.0 form.
- **The scan finds more than the proof did** (4.3 (b)). The count is
  compared before fixing, so a change made after the proof is found, not
  fixed blind.
- **A private name reaches the public repository.** Searched for twice
  (4.3 (f), 6.2 (e)) before anything is pushed.
- **Rule 3.2 (c) refuses a cut in a clone made without tags.** Its message
  names the explicit command, and `git fetch --tags` fixes it.
- **The plugin check reads fields of Claude Code's `init` event**
  (`plugins`, each with `path` and `version`), which the eval runner already
  reads (`evals/run_evals.py:195-199`, `:261`); if the fields change, the
  plan names the new ones. Assumption, checked only by the eval runner's use.

## Notes

### Decisions, each decided by the dispatching session, 2026-10-22

1. The tag is pushed by this item, not left to a person (2.4): the user's
   standing rule for this repository.
2. `cut_version.py` refuses a relative bump while the current version has no
   tag (3.2 (c)): it prevents cutting 5.0.0 by mistake.
3. One reviewer, two rounds, for the combined review (3.4).
4. The window in which this machine's `tcw` refuses 3.x projects is
   accepted and kept short, rather than keeping a second 3.x `tcw` (3.8).
5. `--no-jira` at 4.2 also runs with a dead proxy, as proof (4.2).
6. The files the ways back need are kept in `~/.tcw-4.0-release/`, not a
   session's scratch folder, since a way back may be needed after the session
   ends (Terms).
7. Before 7.3, the files' way back is `git reset --keep M0`, not a revert,
   because no other machine has those commits; after 7.3, only reverts
   (section 9).
8. CI is run on a `release-4.0.0` branch before the tag (6.2 (b)): no
   Python 3.11 here, and the marketplace does not read that branch.
9. The tag is pushed before `main`, and `main` only after PyPI has 4.0.0
   (7.3).
10. The tarball rule of the user's npm publishing instructions is applied to
    PyPI (6.2 (f)).
11. No live Codex or Pi session in the release (6.2 (h)).
12. The release's phases D to F are TCW-118's qa stage (2.3): the review must
    come before anything is published, and qa is where the product as a user
    gets it is confirmed.
13. TCW-99 completes after TCW-118, which completes after the user's setups
    and issue #24 (8.4).

### Handoffs answered

Every comment on this ticket, oldest first.

| From | What it asks | Design rule | Criteria |
| --- | --- | --- | --- |
| TCW-106 (16:07) | `cut_version.py` cuts the current version when no tag exists, and still refuses when one does | 3.2 (a), (b); also (c) | 2, 3, 4, 5 |
| TCW-106 review round 1, S1 and S2 (not a comment here; for TCW-116) | a partly migrated monorepo; an empty `.tcw/` file | answered by TCW-116 (its "Handoffs answered", rows "TCW-106 review (17:48) S1/S2"); nothing left for the release | n/a: `docs/work/TCW-116-…/spec/spec.md:2342-2343` |
| TCW-115 (18:49) | the release notes say three more things beyond the `tcw project` group and the four removed commands | 6.2 (e), 3.3, 3.6 | 29 |
| TCW-115 (19:45) | revised wording: beside the project, never at or above home or inside a hidden folder below it; `.git`-only folder refused; a `ref` naming nothing fails | 6.2 (e) | 29 |
| TCW-116 (20:35) | Design 9.3 steps 0-8 in order | 4.0-4.4, 5.5-5.7, 8.1 | 12-22, 39 |
| TCW-116 (20:35) | pushing `main`, and the marketplace reading `main` before PyPI has 4.0 | 7.1-7.3 | 34, 35, 36 |
| TCW-116 (20:35) | the way back for files and tickets | 9 | 12, 14, 21, 10 |
| TCW-116 (20:35) | migrate the user's setups after publication | 8.2 | 40 |
| TCW-117 (21:23) | delete `UNMIGRATED_RECORDS` at step 3, fix the hits, bare `pytest` passes | 4.3 (b)-(d) | 16, 17 |
| TCW-117 (21:23) | release notes link the migration guide and say to keep automation below 4 | 3.3, 6.2 (e) | 7, 29 |
| TCW-117 (21:23) | the eval run is optional | Non-goals | n/a: TCW-117's handoff says nothing depends on it |
| TCW-116 (21:30) | the 4.0 `tcw` by full path | 4.1 | 15, 17 |
| TCW-116 (21:30) | compare trees by git's file list and digests | n/a for the release: the comparison is TCW-116's proof (Design 9.2 step 4); the release compares commits (13, 19, 20) | n/a: `docs/work/TCW-116-…/spec/spec.md:1387-1398` is the proof's step 4, which this item does not repeat |
| TCW-116 (21:30) | step 6 reads `.tcw/`'s `work.jira`; fix `not_tags` in the user-wide file before step 5 | 5.6, 3.7 | 11, 21 |
| TCW-116 (21:30) | the tickets' way back takes the client; build it only when needed | 9 | 10 |
| TCW-116 (21:53) | step 3 deletes `UNMIGRATED_RECORDS`, fixes in `docs/taxonomy/` and `docs/capabilities/`, credentials unset, the proof's count | 4.3 (b)-(d), 3.1 | 10, 16, 17 |
| TCW-116 (21:53) | save step 6's output as `tcw116-step6.txt` | 5.6 | 21 |
| TCW-116 (21:53) | the way back undoes step 6's `C17` edits; the dry run is a cross-check; a key in one file only is read | 5.6, 9 | 21 |
| The dispatching session's brief | the plugin marketplace version; any marketplace or MFA step | 6.2 (d), 10 | 28 |

Also found by reading the siblings, with no comment naming them:

- TCW-116 Design 9.3 step 5's root `tcw-config.local.yaml` left 3.x: 5.5,
  converted at 5.6 (criterion 21).
- TCW-116 Design 9.5: the user's setups are the user's to migrate after
  publication: 8.2 (40).
- TCW-109 spec, Notes (`:1656`): "nothing beyond the release notes": 6.2 (e).
- TCW-108, TCW-112 and TCW-113 leave their documentation to TCW-117, which
  lands before this item (TCW-108 spec `:205`, TCW-112 spec `:1636-1643`,
  TCW-113 spec `:945-953`): checked by 3.1 (TCW-117 completed).
- The `web-build` job is part of the release's gate (`release.yml:10-11`
  calls the whole of `test.yml`), and TCW-113 changes the web app: 4.3 (d),
  6.2 (a) and (b).

### GitHub issues

No TCW-99 child, and not TCW-99, links a GitHub issue (`tcw work show` of
each, 2026-10-22; TCW-106's ticket says it came from none). Of the items
TCW-99 folded in or settled (design.md:835-841): TCW-22 came from issue #24,
open, and is folded into TCW-113: 8.3. TCW-85 mentions issue #27 and TCW-87
mentions #70; both issues are already closed. Issue #25 is open and named by
no item: left alone (Non-goals).

### Follow-ups

- **The plugin-before-CLI race in every release** (Problem 4): a proposed
  item to change `docs/releasing.md`'s push order or `session_bootstrap.sh`'s
  record, so that a session that installed an older CLI tries again. For the
  dispatching session to file; not part of 4.0.
