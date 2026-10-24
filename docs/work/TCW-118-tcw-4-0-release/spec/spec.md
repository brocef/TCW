# Spec — TCW 4.0: release

Child 13 of 13 of TCW-99, and its last. It releases TCW 4.0: it checks that the
twelve other children work together, merges the branch `v4` into `main`,
migrates this repository with `tcw migrate`, cuts version 4.0.0, publishes it,
and checks the epic's three success criteria
(`docs/work/TCW-99-…/design.md:795-807`). Almost all of it is a procedure
carried out once; the only code it changes is `scripts/cut_version.py`
(Design 3.2) and the plugin's install path, `scripts/session_bootstrap.sh`
with the advice `scripts/check_versions.sh` prints (Design 3.9). Publishing
happens only at the user's go (Design 10).

Every comment posted on this ticket by the other children is mapped, in Notes
("Handoffs answered"), to the rule below that carries it out and the criterion
that checks it. References to a sibling's rule are written "TCW-1nn Design m";
"Design 9.2", "Design 9.3" and "Design 9.5" alone mean TCW-116's; Design 9.3
(`docs/work/TCW-116-tcw-4-0-tcw-migrate-from-3-x/spec/spec.md:1413-1497`) is
the merge procedure this item carries out. Every other bare number, such as
"Design 3.2", "4.3 (b)" or "section 9", is a rule of this spec's own Design.
File and line references are at `v4` commit `82cdb4f9` on 2026-10-24, before
every child is completed (TCW-116 and TCW-117 were still being built), and
were checked again at `f41f91af` for the second revision (the only commit
between them changes this spec); the plan re-finds each one by its words.

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
  release starts; **V** is the commit `v4` points to when it is merged; **A**
  is the merge clone's `main` after the migration commit (4.4), the commit
  the user accepts at gate 1; **T** is the commit tagged `v4.0.0`.
- **"Run as CI runs it"** means, for the Python suite: in a fresh clone, a new
  virtual environment (a private Python installation in a folder),
  `pip install -e '.[dev]'`, then bare `pytest`, not `python -m pytest`
  (`.github/workflows/test.yml:75-76`), with **every** environment variable
  whose name starts with `TCW_` unset (the Jira credentials, `TCW_JIRA_LIVE`,
  every `TCW_PROJECT_<ID>` and any other; `env | grep '^TCW_'` prints nothing
  inside the run), and with `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
  `XDG_STATE_HOME` and `XDG_CACHE_HOME` each set to a new, empty folder made
  for that run, so that no personal file on this machine (such as
  `~/.config/tcw/config.yaml`) is read; and, for the web app,
  `pnpm install --frozen-lockfile` then `pnpm check:build`
  (`test.yml:78-104`), which fails when the committed web build differs from
  the source. This holds for every run of the suite in this spec (4.3 (d),
  5.8, 6.2 (a)); a run that leaves any of it out is not one. Bare `pytest` and
  `python -m pytest` put different folders on Python's search path, which
  once made CI collect no tests while local runs passed (`pyproject.toml:36-44`).
- **A go** is the user's explicit permission, in their own words, for the
  steps a gate names. The dispatching session asks for it, quotes the user's
  words, and records them with the date and time (UTC) in
  `docs/work/TCW-118-tcw-4-0-release/gates.md`, committed before the first
  of those steps runs (Design 10). A go covers only the steps and the
  commits it names; nothing else stands in for it, including this
  repository's standing rule on pushing releases (Design 2.4). The three
  gates of this release are gate 1 (acceptance), gate 2 (live writes) and
  gate 3 (publishing), in that order (Design 10).
- **The acceptance tarball** is the source archive `tcw_cli-4.0.0.tar.gz`
  built from the merge clone's `main` after 4.4 (Design 4.5), the 4.0 the
  user reviews and tests at gate 1.

## Capability changes

Changed, two (declared in `capabilities.yaml`; implement changes the records):

- **`plugin/bootstrap-the-cli`** (`cap-17ca61`). Its description says the
  session-start install "takes the newest release on PyPI"
  (`docs/capabilities/plugin/bootstrap-the-cli/description.md:1`). After
  Design 3.9 it installs the release whose version equals the plugin's own,
  so a plugin update brings the matching CLI and holding the plugin back
  holds the CLI back.
- **`cli/install-from-pypi`** (`cap-f118a5`). Its description says the plugin
  "runs `pipx install tcw-cli` on my behalf"
  (`docs/capabilities/cli/install-from-pypi/description.md:6-7`); it becomes
  `tcw-cli==<the plugin's version>`.

Nothing is added or removed, and no taxonomy term changes. The children
declare their own changes. `scripts/cut_version.py` is contributor tooling, not
part of the product, and no capability record describes it
(`grep -rl cut_version docs/capabilities docs/taxonomy` prints nothing).
`plugin/warn-when-skills-and-cli-versions-differ` stays as written: it promises
"the command that brings them into line", and Design 3.9 changes only which
command that is.

## Problem

TCW 4.0 is built on `v4`, 291 commits ahead of `main` and with nothing on
`main` it lacks, as of 2026-10-24 (`git rev-list --count main..v4` prints the
first number and `git rev-list --count v4..main` prints `0`; run both again
for the count on the day). Nothing on `v4` reaches a user until it is merged
and published, and five things stand in the way of doing that safely:

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
4. **The plugin and the CLI reach users by different roads, and the plugin's
   install does not follow the plugin.** The Claude plugin's marketplace is
   this repository's `.claude-plugin/marketplace.json` (`"source": "./"`),
   read from GitHub's `main`; the CLI comes from PyPI. When a session starts
   with no record of an install, or with a changed plugin version,
   `session_bootstrap.sh` runs `pipx install --force tcw-cli` with no version
   and then copies the plugin's `tcw/__init__.py` as its record (the
   sentinel file) (`scripts/session_bootstrap.sh:115-119`); while that record
   matches the plugin's file it installs nothing more (`:93-97`). Two things
   follow. First, whatever plugin a user runs, its install takes the newest
   `tcw-cli` on PyPI: once 4.0.0 is there, a user who keeps a 3.x plugin and
   starts on a new machine, or whose record is lost, gets the 4.0 CLI, which
   refuses their 3.x project. Second, if `main` reaches GitHub with the 4.0
   plugin before PyPI has 4.0.0, a user starting a session in between gets
   the 3.0.2 CLI under 4.0 skills and keeps it, since the record then matches.
5. **One `tcw` serves this whole machine.** The lifecycle `tcw` is also the
   `tcw` every other project on this machine runs. When it becomes 4.0
   (Design 9.3 step 5), it refuses every 3.x project (TCW-106 Design 4),
   except to migrate it with `tcw migrate` (TCW-116), including the user's
   own setups, which the epic says migrate only after publication
   (Design 9.5).

Two more facts shape the order. **Publishing is the user's to allow.** The
request lists publishing as out of scope, "a person's step"; during the 4.0
run the user said "After then, I will review and test it myself to decide if
I'm accepting the epic as a whole"; and TCW-99's ticket keeps anything
outward-facing as the user's, naming "the release's tag push is the publish". **The 3.x line has
no branch of its own.** The request says `main` keeps taking 3.x patches
until `v4` merges; after the merge no branch on GitHub holds 3.x's code
(`git ls-remote --heads origin` lists `main`, `v4` and Dependabot's update
branches on 2026-10-24, and no `3.x`), while `release.yml` publishes whatever `v*` tag is pushed
(`.github/workflows/release.yml:5-7`).

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
   4.0 plugin, and make the plugin install the CLI of its own version, so
   the two move together in this and every later release.
6. Keep a stop and a way back ready at every step, and say which steps have
   none.
7. Let nothing leave this machine, other than pushes of `v4`, before the
   user has reviewed and tested 4.0 and accepted it (gate 1); take no step
   that writes to a live Jira site or installs 4.0 as this machine's shared
   `tcw` without gate 2's go, and none that publishes or changes GitHub's
   `main` without gate 3's (Design 10); and keep the 3.x line a branch of its
   own.
8. After publication: retire the other checkouts, answer the one GitHub issue
   4.0 settles, and complete TCW-118. The user's two setups (success
   criterion 2) and TCW-99 itself are the user's (Design 8.2, 8.4).

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
- **`docs/releasing.md`'s usual order** for later releases,
  `git push origin main --tags` (`docs/releasing.md:12`). With the install
  pinned to the plugin's version (Design 3.9), a plugin that reaches users
  before its CLI is on PyPI fails to install, says so, and tries again next
  session, rather than keeping an older CLI, so the usual order needs no
  change; this release still pushes the tag first (7.1), to keep even that
  failure window closed.
- **The cloud-session examples in `README.md`** (`:160`, `:218`): they are
  hooks a user writes in their own repository, not the plugin's install
  path, and stay as they are.
- **A 3.x patch release that pins the 3.x plugin's install.** The Claude
  marketplace reads `main` (Problem 4), so a 3.x plugin with a pinned
  install could reach no one through it; this item cuts no 3.x release
  (Notes, "Follow-ups", keeps it optional).
- **GitHub issue #25** (a `tcw://` reference written as a Markdown link is
  reported missing). No TCW-99 child names it; it stays open, untouched.
- **Naming the user's setups.** They are private; this repository is public.
  Every record of them gives counts only.

## Design

### 1. The order, at a glance

| Phase | Steps | Where | Lifecycle `tcw` | What leaves this machine | Stage of TCW-118 |
| --- | --- | --- | --- | --- | --- |
| A. Ready on `v4` | 3.1-3.10 | `v4` worktree | 3.0.2 | `v4` pushed and its CI run | implement |
| B. Merge, migrate the files, accept | 4.0-4.4 (Design 9.3 steps 0-4), 4.5, then gate 1 (4.6) | the merge clone | 3.0.2 (not run: rule 4.0) | the dry run reads the board | implement |
| C. Live writes | gate 2 (5.0), 5.1-5.2, 5.5-5.7 (steps 5-7) | a scratch folder, then the primary checkout | 4.0 from 5.5 | the scenario's and the rehearsal's tickets on the test project, then ticket edits on the live board | implement |
| Review | 5.8 | primary checkout | 4.0 | nothing | review |
| D. Cut and check | 6.1-6.3, then gate 3 asked (6.4) | primary checkout, a fresh clone | 4.0 | `v4` pushed again, at T, for CI | qa |
| E. Publish | 7.1-7.4, under gate 3 | primary checkout | 4.0 | the tag, then `3.x` and `main` | qa |
| F. After publication | 8.1-8.4 | this machine, GitHub | 4.0 | an issue reply; commits to `main` in TCW-118's and TCW-99's folders (gate 3) | qa, then completed |

Each phase starts only when the previous one's last check has passed. Every
step has a stop: a check that fails stops the release at that step, and
section 9 says what undoes what was done so far. At each of the three gates
of Design 10 the release stops until the user's go is recorded: agents may
prepare everything up to a gate, and stop there. **Nothing leaves this
machine before gate 1 except pushes of `v4`:** no write to any Jira site
(the dry run of 4.2 only reads), no install of 4.0 as this machine's shared
`tcw`, no push of any other branch or of a tag.

### 2. TCW-118's own lifecycle

2.1. Request, spec and plan are driven by the 3.0.2 lifecycle `tcw`. TCW-118
moves to `implement` (still 3.0.2) before the first code change of
Design 3.2.

2.2. From rule 4.0 to the end of 5.7, no `tcw` command runs anywhere in this
repository (Design 9.3 step 0), TCW-118's included. It stays at `implement`;
the implement round records what each step did, written as files after 5.7.
That stretch now holds gates 1 and 2, which wait on the user, so it lasts as
long as the user's review and test of 4.0 takes. It cannot be shortened by
letting lifecycle commands run during the wait: a command in this repository
commits to the primary checkout's `main` or edits a ticket, after which 5.5's
`git pull --ff-only` no longer applies and the dry run of 4.2 no longer lists
the board as 5.6 finds it. The user's own testing at gate 1 runs outside
this repository and off the `TCW` board (4.6).

2.3. After 5.7 the 4.0 lifecycle `tcw` moves TCW-118 to `review` (5.8). The
accepted review is the gate for phase D, which, with E and F, is TCW-118's
`qa` stage: qa confirms the product as a user receives it. The move to
`completed` runs `tcw validate` (`CLAUDE.md`, lifecycle table) and waits for
7.2 (publication) and 8.3 (issue #24); it does not wait for the user's setups
(8.2).

2.4. Every move after `inbox` runs `docs/guide/examples/commit-item-after-move.sh`,
which commits the item's folder on `main` in the primary checkout. Those
commits land on top of the migrated `main` and are pushed with it (7.3) or
afterwards; they never land between the merge and the migration. So do the
commits of `gates.md` (Design 10): the goes of gates 1 and 2 are committed
on the merge clone's `main`, after the migration commit, and reach the
primary checkout with it at 5.5; gate 3's is committed on the primary
checkout's `main` after T. A push to `main` after 7.3 that touches only
`docs/work/TCW-118-tcw-4-0-release/` and `docs/work/TCW-99-…/` (these
commits, and the qa record) is covered by gate 3's go.

Decided by the dispatching session, 2026-10-24 (replacing the decision of
2026-10-22, which had this item push the tag without asking under the
repository's standing rule that a verified-ready release is pushed): the
request keeps publishing "a person's step"; the user said, during the 4.0
run, "After then, I will review and test it myself to decide if I'm
accepting the epic as a whole"; and TCW-99's ticket keeps the release's tag
push among the outward actions that stay the user's. The standing rule was
written for routine releases, not for one the user said they would test
first. So this item prepares every step and carries them out, but they
pass three gates, each at the user's go, recorded in `gates.md` with its
date (Design 10). That decision's order (live writes first, the user's test
second) is replaced by the next one. The publishing steps stay inside this
item's scope, as qa, carried out at the user's word. The user completes
TCW-99; this item never moves the epic.

Decided by the dispatching session, 2026-10-24 (second revision): the gates
are reordered so that nothing leaves this machine before the user has
accepted 4.0. Gate 1, acceptance, comes first, after the merge clone is
built and checked and the acceptance tarball built from it (4.5, 4.6);
gate 2, live writes, covers the live Jira scenario, the rehearsal of the
ticket conversion on the test project, the install of 4.0 as this
machine's shared `tcw` and the conversion of the live board (5.0-5.7);
gate 3, publishing, is one go for the tag, the confirmation of the upload,
and the pushes of `3.x` and `main` (6.4, 7.1-7.3). Reason: the user said
"I will review and test it myself to decide if I'm accepting the epic as a
whole"; if they decline, nothing has left the machine that needs undoing,
whereas in the first revision's order the live board had been converted
before they tested anything.

### 3. Phase A: ready on `v4`

The steps run in this order: 3.1, the two code changes (3.2 and 3.9), 3.3,
the combined review (3.4), 3.5, 3.6, 3.7, CI on `v4` (3.10), and last the
message to the user (3.8), just before 4.0. A fix that 3.4 or 3.10 makes on
`v4` sends the steps after it round again: CI runs on the new commit.

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
  - to commit or back up before running `tcw migrate` for real;
  - that, from 4.0, the plugin installs the CLI of its own version
    (`tcw-cli==<the plugin's version>`), so a plugin update brings the
    matching CLI, and that the way to stay on 3.x is to keep the plugin below
    4.0, with, for each harness the notes name (Claude Code, Codex and Pi),
    how a user does that in that harness, or a plain statement that the
    harness offers no way. **This is an open item that blocks writing those
    notes:** the plan finds each harness's way (from the harness's own
    documentation or by trying it), and until it is found for all three the
    point cannot be written and criterion 7 cannot pass. The Claude
    marketplace reads `main` (Problem 4), so a Claude Code user whose
    plugin updates itself gets the 4.0 plugin, and with it the 4.0 CLI, as
    soon as `main` is pushed (7.3), unless that harness's way is used. One
    case is named: a 3.x plugin's own install still takes the
    newest CLI when it installs on a machine for the first time (Problem 4),
    so on such a machine `pipx install --force 'tcw-cli<4'` is run once,
    after which the 3.x plugin leaves it alone;
  - that 3.x keeps a home: the branch `3.x` holds the last 3.x code (M0),
    and a 3.x patch, if one is ever needed, is cut on that branch and
    published by pushing its tag, since `release.yml` publishes any `v*` tag
    (`.github/workflows/release.yml:5-7`).
- **Changelog** (`docs/changelogs/upcoming/`): under `## Changed`, the
  `cut_version.py` rules of 3.2, and `session_bootstrap.sh` installing
  `tcw-cli==<the plugin's version>` with `check_versions.sh`'s advice to match
  (3.9); under `## Removed`,
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
its reading. One slice is how the projects of a family work together (parent
links, inheritance, scope, changes only in the owning project); for it the
reviewer reads `tests/families.py`, the shared fixture that builds one
family of projects in the 4.0 layout, and the tests that use it, as the
place where the children's multi-project behavior is exercised together. It sorts its findings into "belongs to 4.0" and "needs a
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

The same step confirms the use cases' **Known gaps**. Each gap that 4.0
claims to close or narrow, as listed in TCW-117 Design 6.4's table
(`docs/work/TCW-117-…/spec/spec.md:1040-1059`), is checked in
`docs/use-cases.md` at `v4`'s tip: a gap marked "removed" is gone from its
case's `**Known gaps**` list, one marked "narrowed" or "kept" carries the item
the table names. Updating the document is TCW-117's job (its criterion 27);
this item only confirms it, one line per gap in the implement round, and a gap
that does not match goes back to TCW-117's area as a 3.4 finding would.

3.6. **The combined release notes, previewed.** `combine` (the function
`cut_version.py` uses) is run on the `upcoming/` entries without cutting, and
the preview is read against 6.2 (e), so that a missing sentence is added to
TCW-118's entry now rather than after the cut. TCW-115's comment of
2026-10-24 says its entry already names the `tcw project` group, the four
removed commands, the bound on where a clone goes and the `.git`-only
refusal. At `82cdb4f9` that entry
(`docs/release-notes/upcoming/TCW-115-tcw-4-0-the-tcw-project-command-group.md`)
holds three of 6.2 (e)'s four statements: the bound (`:44-46`), the
`.git`-only refusal (`:39-40`) and the `ref` that names nothing (`:51-52`).
The third, that a project already on the machine is never fetched again and
that a manifest fetched during the run that would place it elsewhere stops
the run, is not there in those words; the nearest is "It never overwrites
anything" (`:39`). The check stays: the preview decides, and TCW-118's
entry adds that sentence if the shipped text still lacks it.

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
phases C to E in one sitting once gate 2 is given. The window now holds
gate 3, which waits on the user, and it ends only when the user migrates
their setups (8.2); the message says so. It also says that rule 4.0 lasts
through gates 1 and 2, however long the user's review and test takes (2.2),
and that the shared `tcw` stays 3.0.2 until gate 2's go.

3.9. **The plugin installs the CLI of its own version.** A change to the
published install path, made in this item (Problem 4).

- (a) `scripts/session_bootstrap.sh` reads the plugin's version from the
  plugin's `tcw/__init__.py`, the file whose presence it already checks
  (`:83`) and which it copies as its sentinel (`:118`): the `X.Y.Z` of the
  line `__version__ = "X.Y.Z"` (today `tcw/__init__.py:1`). Its install
  (`:115`) becomes `pipx install --force tcw-cli==X.Y.Z`. Nothing else in the
  order of its checks changes: the steady state (`:93-97`), the guard that
  leaves an editable or unidentifiable `tcw` alone (`:101-104`), and the stop
  when there is no `pipx` (`:108`) all come first, as now.
- (b) **When that version is not on PyPI** (not yet uploaded, or PyPI cannot
  be reached), `pipx install` exits non-zero and the script takes its
  existing failure path (`:120-121`): it prints its one line, now naming
  `pipx install tcw-cli==X.Y.Z`, leaves the sentinel as it was, so the next
  session tries again, and exits 0; the version check that runs on every
  exit (`:81`) then also warns that the CLI and the plugin differ, as now
  (`test_failed_install_prints_both_lines`). Whether a failed
  `pipx install --force` leaves the CLI that was already installed in place
  depends on pipx: pipx 1.17.2, on this machine, resolves the package before
  it touches the existing environment
  (`pipx/commands/install.py`, `_resolve_package_names` before the
  environment is built). Older pipx releases are not checked: an assumption,
  named in Risks.
- (c) A `tcw/__init__.py` with no line of that form installs nothing and
  exits as when the file is missing (`:83`), after the version check.
- (d) `scripts/check_versions.sh`'s advice when the CLI is older than the
  skills, today `pipx upgrade tcw-cli` (`:96-97`), becomes
  `pipx install --force tcw-cli==<skills>`, the command it already gives when
  the CLI is newer (`:94`): a pipx install made with a pinned version may not
  move on `pipx upgrade`, and the explicit form works either way.
- (e) The passages that describe the floating install change with it: the
  comment at `session_bootstrap.sh:85-92`, whose `:88` also advises
  `pipx upgrade tcw-cli`; `skills/setup/references/install.md` (`:3-8`, and
  step 3 at `:39-44`, which advises `pipx upgrade tcw-cli` and says "the
  installed CLI floats"); `README.md` (`:77-86`); and the two capability
  records of "Capability changes". Every `pipx upgrade` among them is
  replaced with the pinned `pipx install --force tcw-cli==<version>`, for the
  reason (d) gives. On 2026-10-24 `README.md` holds no `pipx upgrade`; it is
  searched anyway (criterion 45), so that one added before the release is
  found. Codex
  and Pi run the same script through the `setup` skill
  (`skills/setup/references/install.md:9-13`), so the pin reaches all three
  harnesses.
- (f) Tests, in `tests/test_session_bootstrap.py`, with its stub `pipx` (no
  test may run the real one, `:4-7`): an install calls exactly
  `install --force tcw-cli==<the fixture's version>`; a failed install prints
  one line naming `pipx install tcw-cli==<version>`, leaves the sentinel
  unchanged, and a second run calls `pipx` again; a `tcw/__init__.py`
  without a version line calls no `pipx`. The existing tests that assert the
  unpinned command (`:201`, `:215`) change to the pinned one. In
  `tests/test_check_versions.py`, the older-CLI advice
  (`OLDER_ADVICE`, `:32`) becomes the pinned command.

Decided by the dispatching session, 2026-10-24: pinning the install to the
plugin's own version makes the plugin and the CLI move together, which
removes the race of Problem 4 (a plugin that arrives first fails to install,
says so, and retries, instead of keeping an older CLI) and lets a user hold
back by holding the plugin back. It changes the published install path, and
is done in this item because 4.0 is the first release where an unpinned
install breaks a user's project.

3.10. **CI on `v4`, before the merge.** This machine has no Python 3.11
(`pyenv versions` lists 3.12.13 and 3.14.6), and a push to `v4` starts no CI
(`.github/workflows/test.yml:32-34`: `push` runs only for `main`; a pull
request from `v4` would start one only if labelled `run-ci`, `:35-40`,
`:49-52`), so 4.0 has never been tested on the
lowest Python it supports. After 3.1-3.7, with `v4` not moving:
`git push origin v4` (the user allowed pushing `v4`; running a workflow on it
is within that), then `git ls-remote origin v4` equals `git rev-parse v4`,
then `gh workflow run test.yml --ref v4` (the workflow accepts a manual
start, `test.yml:42`, and its jobs' conditions let one through,
`test.yml:49-52`, `:90-93`). The run is found with
`gh run list --workflow test.yml --branch v4 --event workflow_dispatch`,
followed with `gh run watch <id> --exit-status`, and recorded in the
implement round from `gh run view <id> --json headSha,jobs`: its head commit
is `v4`'s tip, and `pytest (3.11)`, `pytest (3.14)` and `web-build` each have
conclusion `success`. V, recorded at 4.0, is that commit or differs from it
only in files under `docs/work/TCW-118-tcw-4-0-release/`
(`git diff --name-only <the run's commit> V`); otherwise CI is run again.

3.11. **Moved.** The go for writing to Jira is gate 2, asked at 5.0, after
the user has accepted 4.0 at gate 1 (Design 2.4, second revision).

3.12. **Moved.** The live Jira scenario is 5.1, under gate 2.

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
- (d) run the suite as CI runs it (Terms: every `TCW_` variable unset and
  scratch `HOME` and XDG folders), in the clone, with no proxy setting (the
  suite's own servers listen on this machine), and `pnpm check:build`;
- (e) run 4.0's `tcw validate` by its full path;
- (f) search `git diff M0` in the clone for the names of the user's private
  projects, from the maintainer's own notes (not repeated here, since this
  repository is public). Nothing may match.

4.4. **(Step 4)** Commit the migration as one commit after the merge commit,
then, in the clone, fast-forward `main` to it (`git checkout main` and
`git merge --ff-only release-4.0.0`), so the merge and the migration reach
`main` together. Nothing is pushed: `git ls-remote origin main` still prints
M0. The clone's `main` is now A (Terms), recorded in
`~/.tcw-4.0-release/refs.txt`.

4.5. **The acceptance tarball, checked.** In the merge clone at A,
`python -m build` writes `dist/tcw_cli-4.0.0.tar.gz` (the version files
already read `4.0.0`, Problem 1), copied to `~/.tcw-4.0-release/acceptance/`
with its SHA-256 digest (a fingerprint of the file's bytes) beside it. A new
virtual environment in that folder installs it, and the commands of 6.2 (f)
and the comparison of 6.2 (g) are run with it, as they will be again on T:
the new project, the work item, `tcw validate`, and the 3.0.2 project
migrated with `--no-jira`. These are scratch projects in that folder, with
no Jira backend. A failure is a 4.0 defect, handled as 4.6 says for a
defect the user finds.

4.6. **Gate 1: the user accepts 4.0.** The dispatching session tells the
user where the acceptance tarball, its digest and its ready virtual
environment are, that A is the commit it was built from, and what 3.4, 3.5,
3.10, 4.3 and 4.5 found, and stops. The user reviews and tests 4.0
themselves, in their own environment. What they do there is theirs; the
release's own rules for the wait are that rule 4.0 still holds in this
repository (2.2), so their testing runs outside it and off the `TCW` board,
and that the release installs nothing as this machine's shared `tcw` before
gate 2 (the user installing the tarball elsewhere is their choice, and is
not 5.5). Their answer is recorded in `gates.md` (Design 10) and committed on
the merge clone's `main`, and it has one of three outcomes:

- **Accepted.** The go names A. The release goes on to gate 2 (5.0).
- **Declined.** Nothing has left the machine that needs undoing: `v4`'s
  pushes are the only things on GitHub, and the board was only read (4.2).
  The release stops; the merge clone and `~/.tcw-4.0-release/` are kept
  until the user says otherwise; rule 4.0 is lifted, and the agents and the
  user are told so; and the items the user names go back to `implement` as
  the user directs. TCW-118 stays at `implement`.
- **A defect found.** It is fixed on `v4` in the child's area, by an agent
  briefed as 3.4 briefs, which runs no `tcw` command (rule 4.0 still holds);
  then 3.10 (CI on the new commit), and phase B again from 4.1 in a new
  merge clone (the old one deleted, V and A recorded again), 4.5, and gate 1
  is asked again. A go given for one A does not cover another.

Decided by the dispatching session, 2026-10-24: the user tests from a
tarball built from the merge clone, the commit that `main` will become apart
from the cut and the item's own records, rather than from `v4`, because A
holds the migrated records and V does not; the tarball is what PyPI would
serve (6.2 (f)'s reason).

### 5. Phase C: live writes, the CLI switched, the tickets converted (steps 5-7)

5.0. **Gate 2: the go for the live writes.** After gate 1's go, the
dispatching session asks for one go covering, in this order, 5.1 and 5.2 on
the Jira test project, then 5.5 (4.0 installed as this machine's shared
`tcw`, which refuses every 3.x project on the machine, 3.8) and 5.6-5.7 (the
conversion of every ticket's `TCW Item` on the live `TCW` board). It gives
the user the dry run of 4.2, what 5.6 will change, and how it is undone
(section 9), and says plainly:

- **TCW-116's way back for the tickets has never run against a live
  board.** TCW-116 decided that the first live write rests on its in-process
  fake (a stand-in for Jira inside the test run) and on the request `rename`
  already sends, "not on a throwaway Jira project"
  (`docs/work/TCW-116-…/spec/spec.md:2254-2257`), and its plan runs the way
  back once, against the fake only (`docs/work/TCW-116-…/plan/plan.md:1762-1769`).
  On 2026-10-24 the method it calls, `restore_tickets` (plan `:1151`), is
  not yet on the branch `impl-116`, whose one commit adds the command
  alone. That is why 5.2 exists.

The go is recorded in `gates.md` and committed on the merge clone's `main`
before 5.1 runs. If the user declines, or any step of gate 2 fails, the
release stops there and section 9's row for the last step done is run: a
decline, or a failure at 5.1 or 5.2, leaves only the test project's own
tickets behind (row "5.1-5.2"); a failure at 5.5 runs row "5.5"; one at 5.6
or 5.7 runs row "5.6-5.7". A failure at 5.1 or 5.2 is a 4.0 defect, fixed
as 4.6 says, which means gate 1 is asked again before gate 2 is.

5.1. **The live Jira scenario** (TCW-114's comment of 2026-10-24: the
scenario now expects `rename` to print `<old> -> <new>` and has run only
against the fake). In the merge clone at A, the code that is released, with
the clone's own environment: `TCW_JIRA_LIVE=1` with `TCW_JIRA_EMAIL` and
`TCW_JIRA_API_KEY` set,
`.venv/bin/pytest -s tests/work/jira/test_jira_scenario.py::test_the_scenario_live`.
The test runs only when those three are set
(`tests/work/jira/test_jira_scenario.py:51-55`) and works on the Jira project
`TCWTEST` of the site its `LIVE` configuration names (`:19-40`), with the
epic `TCWCLAIM-7` as its other parent (`:16`); it builds its own project in a
scratch folder (`:60`) and touches no ticket of the `TCW` board. The user runs
it, or an agent does under gate 2's go. Its output, with `date -u` first,
is saved as `~/.tcw-4.0-release/live-scenario.txt`; it passes when pytest
exits 0 and reports `1 passed`, not `skipped`, and its printed
`validate --remote exited 0`. The `TCWTEST` board is assumed to be set up as
the test's comment says ("exactly as `tcwtest-checklist.md` ends"), a file not
in this repository: an assumption, checked by the run itself.

5.2. **The ticket conversion and its way back, rehearsed on the test
project.** In a scratch folder under `~/.tcw-4.0-release/rehearsal/`,
outside every repository: a virtual environment with `tcw-cli==3.0.2` from
PyPI makes a 3.x project whose work backend is Jira on `TCWTEST` (the
settings of 5.1's `LIVE`, in 3.x's form) and files two work items, moving
one a stage. Then, with the merge clone's `.venv/bin/tcw` by its full path:
`tcw migrate --dry-run`, then `tcw migrate`, each output saved, with
`date -u` first, as `rehearsal-dry-run.txt` and `rehearsal-step6.txt`; then
TCW-116's way-back script (Step 27's comment, 3.1) on those two files, with
a client built for `TCWTEST` from that project's configuration. It passes
when the migration converts both tickets' `TCW Item`, and after the way
back each ticket's `TCW Item` reads as the 3.x value the dry run listed and
3.0.2's `tcw work list` lists both items with no warning. The two tickets
are then moved to `Won't Do`. Decided by the dispatching session,
2026-10-24: TCW-116's own acceptance rests on the fake, which this item does
not reopen; but the release is the first time the way back would be run
for real, against the one board this repository has, so it is run once
first where a failure costs nothing. Assumption, checked by the run: the
`TCWTEST` project accepts the 3.x configuration's fields as it accepts
5.1's.

5.3, 5.4. Not used: the numbers 5.5-5.7 follow TCW-116's steps 5-7.

5.5. **(Step 5)** In the primary checkout, which is on `main` with no changes
and at M0: `git pull --ff-only <merge clone folder> main`, then
`pip install -e '.[dev]'` again, since 4.0 may change its dependencies. The
lifecycle `tcw` is now 4.0: `tcw --version` prints `tcw 4.0.0`; that output,
after a first line from `date -u` taken before the `pip install`, is saved as
`~/.tcw-4.0-release/install.txt`. An untracked root `tcw-config.local.yaml`,
if any, is still 3.x; 5.6 converts it.

5.6. **(Step 6)** The first write to the live `TCW` board, run only under
gate 2's go (5.0), after 5.1 and 5.2 have passed: `tcw migrate` in the primary checkout with the
credentials set. It reads its Jira settings from
`.tcw/tcw-config.yaml`'s `work.jira` (TCW-116 Design 5.1), converts the
personal file and then every ticket's `TCW Item`. Its whole output is saved as
`~/.tcw-4.0-release/tcw116-step6.txt`, after a first line from `date -u`: its `C17` lines are the edits this run
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
(Terms) on the migrated `main`, and the documentation entries
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
  folder; the suite as CI runs it (Terms: every `TCW_` variable unset,
  scratch `HOME` and XDG folders) with Python 3.14; and `pnpm check:build`.
  Both exit 0.
- (b) **The suite in CI itself, before the tag, on `v4` at T.** T contains
  V (the merge commit's second parent), so moving GitHub's `v4` to T is a
  fast-forward. First, the commit `git ls-remote origin v4` prints is an
  ancestor of T (`git merge-base --is-ancestor <it> T`); if not, someone
  pushed to `v4` during the release, and the session stops and brings it to
  the user. Then `git push origin T:refs/heads/v4`, and
  `gh workflow run test.yml --ref v4`. That push starts no run by itself:
  `test.yml`'s `push` trigger names only `main` (`test.yml:32-34`), and the
  `workflow_dispatch` start (`:42`) is what runs it, whatever paths the
  commit touches, since GitHub applies a `paths-ignore` filter only to push
  and pull request events (its documentation; the comment at `:19-24` says
  the same of `workflow_call`). (A pull request from `v4` labelled `run-ci`
  would also start a run on the push, `:35-40`, `:49-52`; the plan checks
  with `gh pr list --head v4` whether one is open.) The run's commit is T,
  and its three jobs, `pytest` on 3.11, `pytest` on 3.14 and `web-build`,
  all succeed. Decided by the dispatching session, 2026-10-22: this machine
  has no Python 3.11 (`pyenv versions` lists 3.12.13 and 3.14.6), and the
  release's gate is this same workflow (`release.yml:10-14`), so running it
  before the tag is the only way to know the gate will open before the tag
  is on GitHub. Decided by the dispatching session, 2026-10-24 (second
  revision): on `v4` rather than a new `release-4.0.0` branch, because the
  user's permission covers pushing `v4` only; `v4` is not what the plugin
  marketplace reads (Problem 4). Should a separate branch ever be truly
  needed, pushing it falls under gate 3.
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
  - a project already on the machine is never fetched again, and a
    manifest fetched during the run that would place it elsewhere stops the
    run (TCW-115 Design 7.4, `docs/work/TCW-115-…/spec/spec.md:663-706`;
    in the code, `_changed_answer` in `tcw/provision.py:405-426`, called
    after each round's clones at `:547-551`, refuses with
    `<id>: was at <folder> when this run started, but …`, and the run exits
    1; tested by `test_ac35_a_kept_answer_that_changes_stops_the_run`,
    `tests/test_project_provision.py:782`). Decided by the dispatching
    session, 2026-10-24 (second revision): this replaces the first
    revision's wording, "never moved by a manifest fetched during the run",
    which said less than the code does and could be read as a promise that
    nothing stops;
  - a store whose `ref` names no branch, tag or commit now fails rather
    than being read as a file.

  TCW-115's entry already holds three of these four (3.6, with its lines);
  the check stays, and is made on the shipped file. The notes also say what
  3.3 lists on the pinned install and the `3.x` branch.

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
  whose version is `4.0.0` (the fields `evals/run_evals.py:195-201` and
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
`git tag -f v4.0.0 HEAD`, `v4` is pushed again at the new T (a fast-forward,
as in 6.2 (b)), and every check of 6.2 runs again on the new T, not only the
one that failed.

6.4. **Gate 3 asked: the go for publishing.** Once every check of 6.2 has
passed on T, the dispatching session gives the user 6.2's results and
`git diff --name-only A T`, the files changed since the commit they
accepted at gate 1. That list is expected to hold only files under
`docs/work/TCW-118-tcw-4-0-release/` (the lifecycle hook's commits and
`gates.md`), `docs/changelogs/` and `docs/release-notes/` (the cut). Any
other file is a fix made after gate 1 (6.3); each is named to the user, who
decides whether to test again, and the go covers it only if the user's
words say so. It also tells the user two things in plain words:

- **A plugin that updates itself gets 4.0 when `main` is pushed** (7.3),
  pin or no pin: the Claude marketplace reads `main` (Problem 4), and from
  4.0 the plugin installs the CLI of its own version (3.9), so such a user's
  next session installs `tcw-cli==4.0.0`, and their 3.x projects are
  refused until migrated. Only a user who has kept the plugin below 4.0, by
  the harness's own way that the release notes name (3.3), stays on 3.x.
- **The one go covers, with no wait between them:** pushing the tag (7.1),
  which is the publish; confirming the upload (7.2); and, as soon as 7.2
  passes, checking that GitHub's `main` is M0 and pushing `3.x` and `main`
  (7.3). It also covers every later push to `main` that touches only
  `docs/work/TCW-118-tcw-4-0-release/` and `docs/work/TCW-99-…/` (the
  lifecycle hook's commits and the qa record, 2.4).

The go names T, is recorded in `gates.md`, and is committed on the primary
checkout's `main` before 7.1. A go given for one T does not cover another:
after a fix under 6.3, it is asked again. If the user declines, nothing is
pushed; the release waits at this point, with section 9's row "6.1-6.4"
describing what can be undone.

### 7. Phase E: publish, under gate 3

7.1. **Push the tag alone:** `git push origin v4.0.0`. This is the publish:
`release.yml` runs the suite and, only if it passes, builds and uploads
(`release.yml:5-7`, `:13-14`, `:45-50`). It is pushed only once gate 3's go
for this T is committed. `main` is not pushed yet. Right before and right
after the push, `date -u` and `git ls-remote origin main` are saved to
`~/.tcw-4.0-release/pushes.txt`; both print M0.

7.2. **Confirm the upload landed.** `gh run watch` on the release run for
`v4.0.0`: its `test` and `publish` jobs succeed. Then
`https://pypi.org/pypi/tcw-cli/4.0.0/json` returns the release, with
`info.version` `4.0.0`. The versioned address is used because the package's
top-level address keeps reporting the previous version for a while.

7.3. **Then, at once, `3.x` and `main`.** As soon as 7.2 passes, under the
same go and with no further question to the user:

- first, `date -u` and `git ls-remote origin main` are saved to
  `~/.tcw-4.0-release/pushes.txt`, and the hash must equal M0. If it does
  not, someone pushed to `main` during the release: the session stops,
  pushes nothing, and brings it to the user, since the merge was made on M0
  and must be made again on the new commit (4.1), and `3.x` would belong
  there too;
- `git ls-remote origin refs/heads/3.x` prints nothing, and
  `git push origin M0:refs/heads/3.x` makes the branch `3.x` at M0, the last
  3.x code, so that 3.x patches keep a home (3.3);
- `git push origin main`, a fast-forward from M0.

`origin/main` then contains T, the plugin marketplace reads the 4.0 plugin,
and a session that installs the CLI because the plugin changed finds 4.0.0
on PyPI (Problem 4). Decided by the dispatching session, 2026-10-22: the tag
first and `main` after PyPI has the release, rather than
`git push origin main --tags` (`docs/releasing.md:12`), because the usual
order lets the plugin reach users before the CLI does. Decided by the
dispatching session, 2026-10-24 (second revision): one go for 7.1 to 7.3,
with no wait between them, replacing the first revision's separate go for
the tag and for `main`. Reason: the user's decision to publish is made
once, at gate 3, and a wait between the upload and `main` only lengthens
the stretch in which PyPI has 4.0.0 and the marketplace still has 3.0.2,
in which a 3.0.2 plugin installing on a machine for the first time already
takes 4.0.0 (Problem 4; the release notes name the one command that fixes
it).

7.4. **If the release run fails:**

- (a) its `test` job fails: nothing is uploaded, but `v4.0.0` is on GitHub.
  `main` stays unpushed. The session stops and asks the user whether to move
  the tag to a fixed commit or to cut 4.0.1, since rewriting a tag already on
  GitHub is the user's decision (their standing rule names it). 6.2 (b) makes
  this unlikely, since it ran the same workflow on the same commit.
- (b) `publish` fails before uploading (for example a Trusted Publishing
  mismatch, `docs/releasing.md:20-27`): the configuration is corrected and
  the job re-run on the same tag, under gate 3's go, since it publishes the
  same T; 7.3 follows as soon as it passes.
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

8.2. **The user's two setups (success criterion 2) are the user's, on
TCW-99.** After 7.3, in each of the user's two multi-repository setups,
`tcw migrate --dry-run`, then `tcw migrate`, then `tcw validate`, with 4.0.0.
The user runs them, or an agent does at the user's word for each setup, since
they are the user's projects and their tickets are on the user's boards. The
record goes on **TCW-99**, not on this item: a comment giving, for each setup
and without naming it, the dry run's counts, the exit codes of all three
commands, and either that nothing had to be fixed by hand or the work item
filed for what had to be. Something fixed by hand is a 4.0 defect, and
criterion 2 stays unmet until a patch release fixes it and the setup migrates
without it. TCW-118 does not wait for this. What it does is hand the step
over: the comment on TCW-99 of 8.4 names the three commands and what the
record of each setup must hold. Decided by the dispatching session,
2026-10-24: the setups are the user's projects, and the criterion is the
epic's, which the user decides; tying the release item's completion to them
would hold a finished release open for work it does not do.

8.3. **GitHub issue #24** ("Audit backlog: spawn an auditor subagent per TCW
work root"), filed against TCW-22, which TCW-99 folded into TCW-113, whose
Design 7.1 makes the `audit-backlog` procedure cover a project's family. It
is the only open issue a TCW-99 child answers (Notes, "GitHub issues"). After
7.2, a reply naming 4.0.0 and what changed is drafted, the user approves its
exact text, and only then is it posted (`gh issue comment 24`) and the issue
closed. Nothing is posted to an issue without the user approving the exact
words (`CLAUDE.md`).

8.4. **Completing.** TCW-118's qa findings, a comment on its Jira ticket
(this project keeps qa there), record the QA plan's results and point to
`gates.md` for the three gates' goes; then the move to `completed`, which
runs `tcw validate`,
after publication (7.2) and issue #24's answer (8.3), posted only with text
the user approved. Before that move, a comment on TCW-99 gives success
criteria 1 and 3 with their evidence (3.5's output, 6.2 (g)'s comparison)
and hands over criterion 2 as 8.2 says. **This item never moves TCW-99:** the
user completes the epic, after their own review and test (Problem, "Publishing
is the user's to allow") and their setups' migration. Decided by the
dispatching session, 2026-10-24, answering the open question of the spec's
handoff of 2026-10-22.

### 9. The ways back

| After | What has left the machine | The way back |
| --- | --- | --- |
| Phase A | `v4` and its CI run | Ordinary commits on `v4`. Nothing on any Jira board was touched. |
| 4.1-4.3 | the dry run read the board | Delete the merge clone. |
| 4.4-4.6 (gate 1 declined, or a defect found) | nothing | Delete the merge clone and the acceptance folder when the user says so; the primary checkout and the board are untouched (4.6). |
| 5.1-5.2 (gate 2 declined, or the scenario or the rehearsal failed) | tickets on the `TCWTEST` project only | The scenario moves the item it files to `Won't Do` itself (the fake run checks that it does, `tests/work/jira/test_jira_scenario.py:48`); the rehearsal's two tickets are moved to `Won't Do` by hand if the run stopped before doing it. Nothing on the `TCW` board was touched, and this machine's `tcw` is still 3.0.2. |
| 5.5 | nothing | In the primary checkout, `git reset --keep M0` (the commits are on no other machine) and `pip install -e '.[dev]'` again: the lifecycle `tcw` is 3.0.2. |
| 5.6-5.7 | ticket edits on the `TCW` board | The files as for 5.5. The tickets: the way-back script of TCW-116's Step 27, rehearsed at 5.2, reads the `C17` lines of `tcw116-step6.txt` into pairs, stops on any key found in only one of it and `tcw116-dry-run.txt` until a person has read it, and calls the Jira backend's restore method with the pairs the other way round and a Jira client built by hand from `.tcw/tcw-config.yaml` only on the day it is needed (TCW-116 Design 5.4, its handoffs). It puts every 3.x value back and edits no other field. |
| 6.1-6.4 (gate 3 declined, or a check failed) | `v4` at T | Delete the local tag (`git tag -d v4.0.0`); `v4` at T is harmless to leave, since nothing reads it; then as for 5.6, if the release is abandoned. |
| 7.1 | the tag | 7.4. Withdrawing 4.0 entirely means the user deleting the tag on GitHub; nothing was published if 7.2 failed. |
| 7.2-7.3 | the release on PyPI, `3.x`, `main` | None that unpublishes. The branch `3.x` is harmless to leave, and deleting it on GitHub undoes it. The fix is 4.0.1. Hiding 4.0.0 from installers (PyPI's "yank") is done only on pypi.org, logged in as the user, with their two-factor login. `main` is reverted with new commits (the migration and then the merge), never rewritten. |

### 10. What the user does

- **Gives three goes, in this order**; agents prepare everything up to each
  gate and stop there (Decided by the dispatching session, 2026-10-24,
  second revision, Design 2.4):
  - **Gate 1, acceptance** (4.6): after reviewing and testing 4.0 from the
    acceptance tarball, the user accepts commit A, declines, or names a
    defect. Before it, nothing leaves the machine but pushes of `v4`.
  - **Gate 2, live writes** (5.0): the live Jira scenario and the rehearsal
    on the test project (5.1, 5.2), 4.0 installed as this machine's shared
    `tcw` (5.5), and the conversion of the `TCW` board (5.6-5.7).
  - **Gate 3, publishing** (6.4): one go, naming T, for the tag's push, the
    confirmation of the upload, then at once the pushes of `3.x` and `main`
    (7.1-7.3), and the later pushes to `main` that touch only TCW-118's and
    TCW-99's folders.

  **Where the goes are recorded.** Each answer, accepted or not, is written
  as it is given to `~/.tcw-4.0-release/gates.md` (so that it survives a
  merge clone being deleted) and copied, by the commit that records it, to
  `docs/work/TCW-118-tcw-4-0-release/gates.md`, committed before the first
  step it covers: gates 1 and 2 on the merge clone's `main`, gate 3 on the
  primary checkout's `main`. Each entry gives the gate, the commit it names
  (A for gate 1 and 2, T for gate 3), the date and time (UTC), and the
  user's words quoted exactly. The qa findings, on TCW-118's Jira ticket,
  point to that file rather than repeating it.
- **For PyPI: no login.** CI publishes with Trusted Publishing, which needs no
  password, token or login (`release.yml:16-21`, `docs/releasing.md:15-19`);
  the user's part is gate 3.
- **For the plugins: nothing.** No marketplace needs a separate publish: the
  Claude marketplace is `.claude-plugin/marketplace.json` in this repository,
  read from `main`; Codex reads `.agents/plugins/marketplace.json` from the
  repository; Pi reads `package.json`'s `pi` declaration, and that
  `package.json` is marked `"private": true` and published to no package
  registry, so there is no npm step and no two-factor login.
- **Approve** the exact text of the reply to issue #24 (8.3).
- **Migrate, or let an agent migrate,** their two setups, recording it on
  TCW-99 (8.2), and run no `tcw` command in this repository during
  4.0-5.7, which spans gates 1 and 2 (2.2, 3.8).
- **Complete TCW-99**, when they accept the epic as a whole (8.4).
- **Decide** only if 7.4 (a) happens (move the tag or cut 4.0.1), if 3.4's
  second round ends `NOT DONE`, or if 4.0 must ever be hidden from installers
  (9, the yank).

## Abstraction litmus test

No new operation. The release's own steps (merging, committing, tagging,
pushing) are the maintainer's, carried out by people and agents, never by
TCW, which changes no git state (`docs/lifecycle/abstraction.md`, "any
operation that changes git state"). `scripts/cut_version.py` is contributor
tooling outside the `tcw` package (`pyproject.toml:29-30` packages only
`tcw*`), so it is in neither the model nor a backend. `session_bootstrap.sh`
and `check_versions.sh` are the deployment layer, the plugin's install of the
CLI, and are outside the package too; pinning a version there adds no
operation to the model. `tcw migrate` and the
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
- **S-1 (who decides).** The user is present and gives three goes, in
  order: gate 1, acceptance; gate 2, live writes; gate 3, publishing
  (Design 10). An agent that reaches a gate stops; nothing stands in for the
  go.
- **S-2 (harness).** The plugin check runs under Claude (6.2 (h)); Codex and
  Pi read the same skills from the same release, checked by the manifests
  test, and install the CLI by the same script through the `setup` skill, so
  the pin of 3.9 holds in all three. Nothing required of a user is carried by
  a Claude-only feature. How a user keeps the plugin below 4.0 differs by
  harness, and the plan finds it for each of the three before the release
  notes are written (3.3).
- **S-3 (backend).** The files store is exercised by 4.5's and 6.2 (f)'s
  new projects, Jira by 4.2, 5.1, 5.2 and 5.6.
- **S-4 (copies of a checkout).** The merge clone is a clone, not a worktree
  (4.1); other worktrees are removed or migrated (8.1).
- **S-6 (unattended runs).** CI publishes on the tag (7.1); automation that
  installs `tcw-cli` is told to stay below 4 until migrated (3.3).
- **S-7 (several people at once).** Rule 4.0 stops every agent and session
  while the format changes underneath them.
- **S-8 (partial failure).** A stopped `tcw migrate` is run again to finish
  (5.6); a declined or failed gate leaves only what section 9 lists for it,
  and before gate 1 nothing outward but `v4` (4.6, 5.0); a failed check stops
  the release before anything is published (6.3); a failed release run is
  handled by 7.4.
- **S-9 (upgrades).** The plugin and CLI are released together at one
  version, and ordered so the CLI reaches PyPI before the plugin reaches
  `main` (7.3). From 4.0 the plugin installs the CLI of its own version
  (3.9), so a user holds back by holding the plugin back, and a 3.x patch has
  a branch to be cut on (`3.x`, 7.3). A 3.x plugin's own install still floats
  on a machine where it installs for the first time; the release notes name
  the fix (3.3).
- **S-11 (version control).** Every git action here is the maintainer's.

The checklist of `docs/use-cases.md`: 1 (where it looks) — no lookup changes;
2 (whose things) — only this repository, and the user's setups only at the
user's word (8.2); 3 (reading across projects) — no change; 4 (backends) —
S-3 above; 5 (who decides) — the user gives the three goes, in order, and decides 7.4 (a), 8.2,
8.3, a `NOT DONE` second review, and TCW-99's completion (10); 6 (harness) — S-2 above; 7 (stopping halfway)
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
   leading paragraph and an `## Upgrading` section holding the six points
   of 3.3, the fifth naming, for each of Claude Code, Codex and Pi, how a
   user keeps the plugin below 4.0, or that the harness offers no way;
   `docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md` has the
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
43. (3.9 (a)-(c), (f)) `tests/test_session_bootstrap.py` has tests in which,
    with a fixture plugin whose `tcw/__init__.py` reads
    `__version__ = "X.Y.Z"` and which holds no `scripts/check_versions.sh`,
    so that the version check on exit (`session_bootstrap.sh:81`) prints
    nothing, as the fixture of `_clone` (`:31-36`) does for the one-line
    assertion at `:198`: an install calls the stub `pipx` with exactly
    `install --force tcw-cli==X.Y.Z` and then writes the sentinel; a failed
    install exits 0, prints exactly one line, containing
    `pipx install tcw-cli==X.Y.Z`, leaves the sentinel's bytes unchanged, and
    a second run calls `pipx` again; and a `tcw/__init__.py` with no
    `__version__` line calls no `pipx`. No test in the file asserts the
    unpinned `install --force tcw-cli`.
44. (3.9 (d)) `tests/test_check_versions.py`: when the CLI is older than the
    skills, the advice contains `pipx install --force tcw-cli==<skills>`, and
    `grep -n 'pipx upgrade' scripts/check_versions.sh` prints nothing.
45. (3.9 (e)) `grep -rn 'floats\|newest release\|pipx upgrade' scripts/session_bootstrap.sh
    skills/setup/references/install.md README.md docs/capabilities/plugin/bootstrap-the-cli`
    prints nothing (on 2026-10-24 it finds `pipx upgrade` at
    `session_bootstrap.sh:88` and `install.md:39`, each corrected by this
    item); `docs/capabilities/cli/install-from-pypi/description.md`
    and `docs/capabilities/plugin/bootstrap-the-cli/description.md` say the
    plugin installs `tcw-cli` at the plugin's own version; and
    `docs/work/TCW-118-tcw-4-0-release/capabilities.yaml` lists exactly
    those two under `changed:`.
46. (3.10) The implement round holds `gh run view`'s output for a
    `workflow_dispatch` run of `test.yml` on `v4`: its `headSha`, and
    `pytest (3.11)`, `pytest (3.14)` and `web-build` each with conclusion
    `success`; and `git diff --name-only <that headSha> V` lists only files
    under `docs/work/TCW-118-tcw-4-0-release/`.
47. (4.6, gate 1) `docs/work/TCW-118-tcw-4-0-release/gates.md` on `main`
    holds gate 1's go: the user's words quoted, a date and time (UTC), and
    the commit A it names, equal to the merge clone's `main` after 4.4 (the
    one recorded in `refs.txt`). That time is earlier than the `date -u`
    line at the top of each of `~/.tcw-4.0-release/live-scenario.txt`, the
    rehearsal's two files (5.2), `install.txt`, `tcw116-step6.txt` and
    `pushes.txt`. A gate 1 answer that was a decline or a defect is in the
    file too, with what followed (4.6).
48. (5.1) `~/.tcw-4.0-release/live-scenario.txt` shows
    `test_the_scenario_live` passed (`1 passed`, not `skipped`), and its
    printed `validate --remote exited 0`, run in the merge clone at A.
49. (3.5, Known gaps) The implement round has one line for each row of
    TCW-117 Design 6.4's table, giving the gap's state in
    `docs/use-cases.md` at V (gone, or the item it names), and every line
    agrees with the table's outcome or names the fix that made it agree.

Phase B

12. The implement round records when the messages of 4.0 and 3.8 were sent,
    and to whom; and `~/.tcw-4.0-release/refs.txt` holds M0, V and A.
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
17. In the clone after 4.3, with the suite run as CI runs it (Terms; the
    round records `env | grep '^TCW_'` printing nothing and the scratch
    `HOME`): bare `pytest` in the clone's environment exits 0, `pnpm check:build` exits 0, and
    `.venv/bin/tcw validate` exits 0.
18. The private-name search of `git diff M0` in the clone prints nothing.
19. After 4.4, the clone's `main` is one commit after the merge commit, and
    `git ls-remote origin main` prints M0.
54. (4.5) `~/.tcw-4.0-release/acceptance/` holds `tcw_cli-4.0.0.tar.gz`
    and its SHA-256 digest; the commands of 6.2 (f) and the comparison of
    6.2 (g), run with it, passed, as recorded in the implement round, before
    gate 1 was asked.

Phase C

52. (5.0, gate 2) `gates.md` holds gate 2's go, quoted, dated, naming A,
    later than gate 1's and earlier than the `date -u` line at the top of
    `live-scenario.txt`, the rehearsal's two files, `install.txt` and
    `tcw116-step6.txt`; and the request for it, as recorded in the implement
    round, says that TCW-116's way back for the tickets had never run
    against a live board.
53. (5.2) `rehearsal-dry-run.txt` and `rehearsal-step6.txt` exist; the
    migration converted both test tickets' `TCW Item`; after the way-back
    script ran, each ticket's `TCW Item` equals the 3.x value the dry run
    listed for it, and 3.0.2's `tcw work list` in the rehearsal project
    lists both items with no warning; both tickets end in `Won't Do`.
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
25. 6.2 (a): in a fresh clone of T, with Python 3.14 and the suite run as CI
    runs it (Terms, recorded as for 17), bare `pytest` exits 0 and
    `pnpm check:build` exits 0.
26. 6.2 (b): before the push, the commit GitHub's `v4` held is an ancestor
    of T (recorded in the qa findings); `gh run view` of the
    `workflow_dispatch` run of `test.yml` on `v4` shows head commit T, and
    `pytest (3.11)`, `pytest (3.14)` and `web-build` all with conclusion
    `success`.
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
50. (6.4, gate 3) `gates.md` on `main` holds gate 3's go, quoted, with a
    date and time, naming a commit equal to `git rev-parse v4.0.0^{commit}`;
    that time is earlier than the first `date -u` line of
    `~/.tcw-4.0-release/pushes.txt` (right before the tag's push); the
    commit that added it is an ancestor of `origin/main` and not of T; and
    the request for it, as recorded in the qa findings, gave
    `git diff --name-only A T`, named every file in that list outside
    `docs/work/TCW-118-tcw-4-0-release/`, `docs/changelogs/` and
    `docs/release-notes/`, and said that a plugin which updates itself gets
    4.0 when `main` is pushed.

Phase E

34. The tag was pushed by itself: `~/.tcw-4.0-release/pushes.txt` holds,
    each under its own `date -u` line, the output of
    `git ls-remote origin main` right before 7.1's push, right after it, and
    right before 7.3's pushes; each prints M0, and the times are in
    that order, with 7.2's successful run between the second and the third.
35. The release run for `v4.0.0` shows `test` and `publish` with conclusion
    `success`, and `https://pypi.org/pypi/tcw-cli/4.0.0/json` returns
    `info.version` `4.0.0`.
36. After 35, `git merge-base --is-ancestor T origin/main` succeeds,
    `git ls-remote origin refs/heads/3.x` prints M0, and
    `git ls-remote origin release-4.0.0` prints nothing (no branch but `v4`,
    `3.x` and `main` was pushed).
51. (7.3, under gate 3) `gates.md` holds no separate go for 7.3: gate 3's
    covers it. In `pushes.txt`, the line saved right before 7.3's pushes
    follows 7.2's successful run, its `git ls-remote origin main` equals M0
    (34), and no question to the user is recorded between 7.2 and 7.3. Every
    push to `main` after 7.3 and before TCW-118's completion changes only
    files under `docs/work/TCW-118-tcw-4-0-release/` and
    `docs/work/TCW-99-…/` (`git diff --name-only <main as pushed at 7.3>
    origin/main`).
37. If the release run failed, the record shows 7.4 followed: for a failed
    `test` job, the user's decision before any tag was moved.
38. A clean install from PyPI works: `pipx run --spec tcw-cli==4.0.0 tcw --version`
    prints `tcw 4.0.0`.

Phase F

39. After 8.1, `git worktree list` shows the primary checkout and only
    worktrees that are locked (named to the user) or in which `tcw validate`
    passes.
40. (8.2) Before TCW-118 moves to `completed`, TCW-99 has a comment that
    names, for the user's two setups, the three commands
    (`tcw migrate --dry-run`, `tcw migrate`, `tcw validate`) and the record
    each setup's migration must leave on TCW-99: the dry run's counts, the
    exit codes of all three commands, and either that nothing was fixed by
    hand or the work item filed for what was, without naming the setup.
    TCW-118's completion does not wait for those records.
41. Issue #24 is closed, after 35, with a reply whose text the user approved
    in this conversation; the approval and the text are in TCW-118's qa
    record.
42. TCW-118 is completed after 35, 40 and 41, and its move ran
    `tcw validate` successfully. TCW-99 has a comment giving success
    criteria 1 and 3 with their evidence (9, 31). TCW-99's stage is the same
    after TCW-118's completion as before it: this item never moves the
    epic.

Criteria 43 to 51 were added on 2026-10-24, and 52 to 54 in the second
revision of the same day, which also rewrote 47, 48, 50 and 51 for the
reordered gates; each is listed beside the criteria of its phase, and the
numbers of 1 to 42 are kept so that every reference to them still holds.

### Coverage

Each numbered rule of the Design, with the criteria that check it. A cell is
a criterion number, or `n/a` with the line that makes it so.

| Design rule | Criteria |
| --- | --- |
| 1 the order; nothing but `v4` leaves before gate 1 | 1, 12, 23, 24, 34, 36 (each phase's gate); 47, 52, 50, 51 (the user's gates, in order: 47's times precede every outward step's file) |
| 2.1 lifecycle to implement before code | n/a: a lifecycle move, checked by `tcw work advance`'s own gate (`CLAUDE.md:41-44`) |
| 2.2 no `tcw` from 4.0 to 5.7, through gates 1 and 2 | 12, 22 |
| 2.3 review gates D; qa holds D-F; completion waits for 7.2 and 8.3 only | 23, 42 |
| 2.4 hook and `gates.md` commits after the migration; later pushes under gate 3 | 19 (one commit after the merge), 36, 50 (gate 3's commit after T), 51 (later pushes) |
| 2.4 decisions (2026-10-24, both revisions): three gates, acceptance first; the epic is the user's | 47, 52, 50, 51, 42 |
| 3.1 children completed, TCW-116's records | 1, 10 |
| 3.2 (a) | 2 |
| 3.2 (b) | 3 |
| 3.2 (c) | 4 |
| 3.2 (d) | 5 |
| 3.2 releasing.md | 6 |
| 3.3 entry files | 7, 29 |
| 3.4 combined review | 8 |
| 3.5 success criterion 1 | 9, 42 |
| 3.5 known gaps confirmed | 49 |
| 3.6 preview of the notes | 29 (the same statements, on the shipped file) |
| 3.7 user-wide file | 11 |
| 3.8 the user told | 12 |
| 3 order of Phase A's steps | 46 (CI on the final commit), 47 (the go before the scenario and V), 48 |
| 3.9 (a) pinned install | 43 |
| 3.9 (b) version not on PyPI | 43 (the failed-install test) |
| 3.9 (c) no version line | 43 |
| 3.9 (d) `check_versions.sh` advice | 44 |
| 3.9 (e) passages and records | 45 |
| 3.9 (f) tests | 43, 44 |
| 3.10 CI on `v4` | 46 |
| 3.11, 3.12 moved | n/a: pointers to 5.0 and 5.1 |
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
| 4.5 acceptance tarball | 54 |
| 4.6 gate 1 and its three outcomes | 47 |
| 5.0 gate 2, and what the user is told of the way back | 52 |
| 5.1 live Jira scenario | 48 |
| 5.2 rehearsal on the test project | 53 |
| 5.5 step 5 | 20 |
| 5.6 step 6 | 21, 52 (only after gate 2) |
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
| 6.4 gate 3 asked | 50 |
| 7.1 tag alone, under gate 3 | 34, 50 |
| 7.2 upload confirmed | 35, 38 |
| 7.3 at once after 7.2, same go: `main` checked at M0, then `3.x` and `main` pushed | 34, 36, 51 |
| 7.4 (a)-(c) | 37 |
| 8.1 other checkouts | 39 |
| 8.2 user's setups, handed to TCW-99 | 40 |
| 8.3 issue #24 | 41 |
| 8.4 completing; TCW-99 not moved | 42 |
| 9 ways back | n/a as criteria: a way back is run only when a step fails; each row's inputs are checked to exist by 12 (M0), 14 (dry-run file), 21 (step-6 file) and 10 (the way-back script) |
| 10 what the user does; where goes are recorded | 47, 52, 50 (the three goes, each in `gates.md`); 37, 40, 41 (the decisions that can arise) |

## Risks

- **This machine's other 3.x projects are refused from 5.5 until migrated**
  (Problem 5). Met by telling the user first (3.8) and migrating their setups
  right after publication (8.2).
- **The board is converted before GitHub's `main` is.** From 5.6 to 7.3 the
  tickets hold 4.0 values while `origin/main` is 3.x; anyone pulling
  `origin/main` and using 3.0.2 on this board in that window would see items
  it cannot read. Assumption, not checked: no one but the user and this
  machine's agents works on the `TCW` board. The user's review and test of
  4.0 now comes before the board is converted (gate 1), so the window holds
  only the review, phase D and gate 3's wait.
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
- **A 3.x plugin's install still floats.** The pin of 3.9 is in 4.0's
  script; a user who keeps a 3.x plugin runs 3.x's script, which takes the
  newest `tcw-cli` when it installs on a machine for the first time
  (Problem 4). Met by the release notes' one command (3.3); a follow-up
  could carry the pin to a 3.x patch (Notes, "Follow-ups").
- **How a user keeps a plugin below 4.0 is the harness's matter.** The
  release notes tell a user who must stay on 3.x to keep the plugin below
  4.0; the Claude marketplace reads `main`, so this depends on each
  harness's own way of holding a plugin's version or turning off its
  updates. Not yet known for any of the three: the plan finds it for Claude
  Code, Codex and Pi, and until it has, the release notes' fifth point
  cannot be written (3.3, an open item). If a harness offers no way, the
  notes say so plainly, and that harness's users who must stay on 3.x are
  told to stop using the plugin's automatic install until they migrate.
- **The way back for the tickets has never run against a live board**
  (5.0). Met by the rehearsal on the test project (5.2) before the live
  conversion. Were the way back ever needed on the `TCW` board itself, that
  would still be its first run on that board.
- **A failed pinned install with an older pipx.** If an older pipx release
  removed the existing environment when a `pipx install --force` fails,
  a session started while the plugin's version is not yet on PyPI would
  leave the user with no `tcw` until the next session. pipx 1.17.2 resolves
  first (3.9 (b)); older releases are not checked. The release order keeps
  that window closed for 4.0.0 itself (the tag, and PyPI, before `main`).
- **The live scenario writes to a real Jira site** (5.1). It runs only
  under gate 2, in the `TCWTEST` project, with tickets it makes itself; so
  does the rehearsal (5.2).
- **The plugin check reads fields of Claude Code's `init` event**
  (`plugins`, each with `path` and `version`), which the eval runner already
  reads (`evals/run_evals.py:195-201`, `:261`); if the fields change, the
  plan names the new ones. Assumption, checked only by the eval runner's use.

## Notes

### Decisions, each decided by the dispatching session

Decisions 2 to 13 were made on 2026-10-22; decision 1 was replaced, and 14 to
19 added, on 2026-10-24; in the second revision of 2026-10-24, decisions 1,
8, 9 and 17 were replaced and 20 to 25 added.

1. Decided by the dispatching session, 2026-10-24 (second revision),
   replacing both earlier texts: three gates, each at the user's go,
   recorded in `gates.md` and committed before its first step, in this
   order: gate 1, acceptance, after the merge clone and the acceptance
   tarball are built and checked (4.5, 4.6), before which nothing leaves the
   machine but pushes of `v4`; gate 2, live writes (5.0-5.7); gate 3,
   publishing, one go for 7.1-7.3 (6.4) (2.4, 10). Reason: the user said "I
   will review and test it myself to decide if I'm accepting the epic as a
   whole", and if they decline nothing outward needs undoing; the request
   keeps publishing a person's step, and TCW-99's ticket keeps the tag's
   push as the user's.
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
8. Replaced in the second revision: CI is run before the tag on `v4`, moved
   to T by a fast-forward, with `gh workflow run test.yml --ref v4`
   (6.2 (b)): no Python 3.11 here, the user's permission covers pushing `v4`
   only, and the marketplace does not read `v4`. A separate branch, if ever
   truly needed, is pushed under gate 3.
9. Replaced in the second revision: the tag is pushed before `main`, and
   `main` only after PyPI has 4.0.0 (7.3), all three under gate 3's one go,
   with no wait between 7.2 and 7.3.
10. The tarball rule of the user's npm publishing instructions is applied to
    PyPI (6.2 (f)).
11. No live Codex or Pi session in the release (6.2 (h)).
12. The release's phases D to F are TCW-118's qa stage (2.3): the review must
    come before anything is published, and qa is where the product as a user
    gets it is confirmed.
13. Replaced on 2026-10-24 by 15.
14. Decided by the dispatching session, 2026-10-24: the plugin installs
    `tcw-cli==<its own version>` (3.9), so plugin and CLI move together and
    a user holds back by holding the plugin back; the follow-up on the race
    is dropped, since the pin settles it.
15. Decided by the dispatching session, 2026-10-24: TCW-118 completes at
    publication plus issue #24's answer (8.4); success criterion 2, the
    user's setups, is the user's, recorded on TCW-99 (8.2); the user
    completes TCW-99. Reason: the setups and the epic are the user's to
    decide, and the release does not do that work.
16. Decided by the dispatching session, 2026-10-24: a branch `3.x` is
    pushed at M0 as part of gate 3, so 3.x patches keep a home; one is cut
    on that branch and published by its tag (7.3, 3.3).
17. Replaced in the second revision: CI runs on `v4` before the merge
    (3.10), so Python 3.11 is tested before the user is asked to accept
    4.0; the live Jira scenario runs under gate 2, in the merge clone at A
    (5.1), as TCW-114 asked.
18. Decided by the dispatching session, 2026-10-24: every suite run unsets
    every `TCW_` variable and uses scratch `HOME` and XDG folders (Terms), so
    no setting of this machine reaches a run that is meant to be CI's.
19. Decided by the dispatching session, 2026-10-24: `tests/families.py`
    serves the combined review's multi-project slice (3.4), not the tarball
    check of 6.2 (f), which stays a single new project.

Added in the second revision, each decided by the dispatching session,
2026-10-24:

20. The user tests 4.0 from a tarball built from the merge clone at A
    (4.5, 4.6), since A holds the migrated records and is what `main`
    becomes apart from the cut and the item's own records.
21. Rule 4.0 lasts through gates 1 and 2 (2.2), since a lifecycle command
    during the wait would move the primary checkout's `main` or the board
    out from under 5.5 and 5.6.
22. The ticket conversion and its way back are rehearsed on the test
    project before the live board (5.2), since TCW-116's way back has run
    only against its fake; TCW-116's own acceptance is not reopened.
23. 6.2 (e)'s third statement follows TCW-115 Design 7.4: a project already
    on the machine is never fetched again, and a manifest fetched during the
    run that would place it elsewhere stops the run; confirmed against
    `tcw/provision.py`'s `_changed_answer` and its test.
24. Criterion 45 also searches for `pipx upgrade`, across
    `skills/setup/references/install.md`, `README.md` and
    `scripts/session_bootstrap.sh`, and this item corrects each one found.
25. How a user keeps the plugin below 4.0 in Claude Code, Codex and Pi is an
    open item for the plan that blocks writing the release notes' fifth
    point (3.3); no 3.x pinned patch release is made in this item
    (Non-goals), since the marketplace reads `main`.

### Handoffs answered

Every comment on this ticket, oldest first: nine comments, from
2026-10-22 16:07 to 2026-10-24 15:15 (UTC), re-read on 2026-10-24. Times
without a date are on 2026-10-22.

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
| TCW-114 (2026-10-24 12:06) | the live Jira scenario expects `rename` to print `<old> -> <new>` and has run only against the fake; run it against a real site before the release | 5.1, under gate 2 | 48 |
| TCW-115 (2026-10-24 15:15) | its release-note entry already names the group, the four removed commands, the bound and the `.git`-only refusal | 3.6, 6.2 (e): three of the four statements are there, the check stays | 29 |
| TCW-115 (2026-10-24 15:15) | a Ctrl-C during any `tcw` command prints a Python traceback; worth a ticket of its own | Notes, "Follow-ups" | n/a: a separate item, by the comment's own words |
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

For the dispatching session to file; none is part of 4.0.

- **A Ctrl-C during any `tcw` command prints a Python traceback** (TCW-115's
  comment of 2026-10-24): a proposed ticket, so that an interrupt ends with a
  short message and the usual exit code for an interrupt.
- **Carry the pin to a 3.x patch** (Risks, "A 3.x plugin's install still
  floats"): optional, cut on the `3.x` branch, if a user holding 3.x asks for
  it. The 2026-10-22 follow-up on the plugin-before-CLI race is dropped: the
  pin of 3.9 settles it.

## Revision 2026-10-24

Revised after the spec review, with the dispatching session's decisions of
2026-10-24 (Notes, "Decisions", 1 and 14 to 19).

(The gate order and lettering below, gates (a) to (c), are those of this
first revision; the second revision, at the end of this section, replaces
them with gates 1 to 3.)

- **Publishing waits for the user.** Decision 1's 2026-10-22 text, which had
  this item push the tag without asking, is replaced: three steps run only at
  the user's go, recorded with its date in the item's folder: gate (a)
  before 5.6 (3.11), gate (b) before 7.1, after the user has reviewed and
  tested 4.0 (6.4), and gate (c) before 7.3. Section 10 lists them;
  criteria 47, 50 and 51 check that each go is recorded before its step.
  TCW-118 completes at publication plus issue #24's answer; the user's setups
  are recorded on TCW-99 (8.2), and the user completes TCW-99 (8.4). This
  answers the open question of the spec's handoff.
- **The plugin installs the CLI of its own version** (3.9), so a plugin
  update brings the matching CLI and holding the plugin back holds the CLI
  back. It is a change to the published install path, so "Capability
  changes" now declares two changed records, and `capabilities.yaml` exists.
  The release notes say so and how to hold back (3.3). The follow-up on the
  plugin-before-CLI race is dropped.
- **Phase A gains** CI on `v4` with Python 3.11 before gate (a) (3.10), and,
  after it, the live Jira scenario TCW-114 asked for (3.12).
- **The 3.x line keeps a home:** a branch `3.x` at M0, pushed under
  gate (c) (7.3); the release notes say a 3.x patch is cut there.
- **7.3 checks** that GitHub's `main` is still M0 right before pushing, and
  stops if not; criterion 34 now requires the timestamped `git ls-remote`
  output.
- **Criteria 40 and 8.2 now agree** (the record lives on TCW-99, with the exit
  codes of all three commands); criterion 42 no longer moves TCW-99.
- **3.5 also confirms the use cases' Known gaps** against TCW-117 Design 6.4
  (criterion 49); **3.4's multi-project slice** reads `tests/families.py`.
- **Every suite run** unsets every `TCW_` variable and uses scratch `HOME`
  and XDG folders (Terms).
- **Notes** cover all nine comments on the ticket, with their date range,
  including TCW-114's and TCW-115's of 2026-10-24; the Ctrl-C traceback is a
  follow-up.
- **Stale text corrected:** the state of the children at the time of writing,
  the commit count (291, with the command that recounts it), and 3.6's note
  that TCW-115's entry holds three of 6.2 (e)'s four statements; the fourth,
  that projects already on the machine are never moved, is not there in those
  words, so the check stays. Line references re-checked at `82cdb4f9`.

### Second revision, 2026-10-24

Revised after spec review round 2, with the dispatching session's decisions
of 2026-10-24 (Notes, "Decisions", 1, 8, 9 and 17 replaced, 20 to 25 added).

- **The gates are reordered so that nothing leaves the machine before the
  user accepts 4.0.** Gate 1, acceptance (4.6), comes after the merge clone
  is built and checked and the acceptance tarball built from it (4.5);
  before it, nothing leaves the machine but pushes of `v4`. Its three
  outcomes are written out: accepted, declined (nothing outward to undo;
  the items the user names go back to `implement` as the user directs), and
  a defect (fixed on `v4`, phase B again, gate 1 asked again). Gate 2, live
  writes (5.0), covers the live Jira scenario (moved from 3.12 to 5.1), a new
  rehearsal of the ticket conversion and its way back on the test project
  (5.2), the install of 4.0 as this machine's shared `tcw` (5.5) and the
  board's conversion (5.6-5.7), with a decline or failure running section
  9's rows. It says plainly that TCW-116's way back has never run against a
  live board. Gate 3, publishing (6.4), is one go for the tag, the upload's
  confirmation and, at once after it, the pushes of `3.x` and `main`, and
  covers later pushes to `main` that touch only TCW-118's and TCW-99's
  folders; at it the user is told that a plugin which updates itself gets
  4.0 when `main` is pushed.
- **The goes are recorded in `gates.md`** in the item's folder, committed
  before each gate's first step (Design 10); qa findings stay on the Jira
  ticket. Criteria 47, 48, 50 and 51 are rewritten for this, and 52 (gate 2),
  53 (the rehearsal) and 54 (the acceptance tarball) added.
- **Rule 4.0 lasts through gates 1 and 2** (2.2), and the message of 3.8
  says so.
- **CI before the tag runs on `v4`** moved to T by a fast-forward, started
  with `gh workflow run test.yml --ref v4` (6.2 (b)); no `release-4.0.0`
  branch is pushed. `test.yml`'s triggers are cited: its `push` names only
  `main`, and `workflow_dispatch` is what starts the run.
- **6.2 (e)'s third statement** now says what TCW-115 Design 7.4 and the
  code say: a project already on the machine is never fetched again, and a
  manifest fetched during the run that would place it elsewhere stops the
  run (`tcw/provision.py:405-426`, `:547-551`;
  `tests/test_project_provision.py:782`).
- **Criterion 45 also searches for `pipx upgrade`**, found today at
  `scripts/session_bootstrap.sh:88` and `skills/setup/references/install.md:39`;
  3.9 (e) corrects both. **Criterion 43** says its fixture keeps
  `check_versions.sh` silent, as the test asserting one line at
  `tests/test_session_bootstrap.py:198` does.
- **Holding back** in each of Claude Code, Codex and Pi is an open item for
  the plan, blocking the release notes' fifth point (3.3, criterion 7, Risks);
  no 3.x pinned patch release is made here (Non-goals).
