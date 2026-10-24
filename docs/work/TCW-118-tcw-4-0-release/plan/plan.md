# Plan — TCW 4.0: release

The spec is `spec/spec.md` beside this folder, settled after three review
rounds (its "Revision" sections). "Design n" and "criterion n" are that spec's;
"TCW-1nn Design m" is a sibling's. Every file and line cited here was checked
on `v4` at `bb6adc7e` (2026-10-24), while TCW-117 was still being implemented
in another worktree; a step that depends on what TCW-117 leaves is marked
**[after TCW-117]** and is written against TCW-117's spec and plan
(`docs/work/TCW-117-tcw-4-0-guides-skills-use-cases-and-the-3-x-to-4-0-migration-guide/`,
cited `P117:L` for line L of its `plan/plan.md` and `S117:L` for its
`spec/spec.md`). Step 1 re-finds every citation once TCW-117 has landed; a
line that moved is found again by its words.

## Who does what

Three kinds of actor appear in every step:

- **An agent**: a subagent the dispatching session starts with a
  self-contained brief, for one step or a few. It works only where the step
  says, commits only the files the step names, and stops at the end of the
  step. It never runs a lifecycle command (`tcw work …`), never touches Jira
  or GitHub except where the step says so under a recorded go, and never
  pushes anything but `v4`.
- **The dispatching session**: the session carrying out the release. It makes
  every lifecycle move of TCW-118, sends the messages the spec requires, asks
  for each gate's go, records the answer in `gates.md`, and decides what the
  spec leaves to it.
- **The user**: gives the three goes (gate 1 acceptance, gate 2 live writes,
  gate 3 publishing, Design 10), approves the exact text of the reply to issue
  #24, and decides the questions Design 10 lists.

**No step below may publish, push a tag, push `main` or `3.x`, write to the
live `TCW` Jira board, run the live Jira scenario, install 4.0 as this
machine's shared `tcw`, post to a GitHub issue, or move TCW-99, unless the
matching go is already written in `gates.md` and committed** (Design 10). Each
step that needs a go names the gate in its "Who" line, and its first action is
to read `gates.md` and confirm the entry is there and names the right commit.
If it is not, the step does not run.

## Which `tcw` runs what

- **The lifecycle `tcw`** is the bare `tcw` first on this machine's `PATH`.
  `which -a tcw` lists `/Users/brian/.pyenv/shims/tcw` first and
  `/Users/brian/.local/bin/tcw` second; the first is the primary checkout's
  editable install at 3.0.2 (spec Terms). Only the dispatching session runs
  it, and only outside rule 4.0's window (Design 2.2).
- **The `v4` worktree's `tcw`** is `.claude/worktrees/v4/.venv/bin/tcw`, run by
  its full path, only in scratch folders and in the suite.
- **The merge clone's `tcw`** is `<merge clone>/.venv/bin/tcw`, always by its
  full path, never with `.venv/bin` first on `PATH` (Design 4.1).
- **The acceptance and tarball environments' `tcw`**: `~/.tcw-4.0-release/acceptance/venv/bin/tcw`
  and `<qa folder>/venv-4/bin/tcw`, by full path.
- **`tcw-cli==3.0.2` from PyPI**, in scratch virtual environments only (4.5,
  5.2, 6.2 (f)).

## What this plan relies on

- Every child but TCW-117 and TCW-118 is completed on `v4`; TCW-117 lands
  before Step 2 begins (Step 1 checks it).
- **[after TCW-117]** `tests/test_docs_describe_4_0.py` exists with
  `UNMIGRATED_RECORDS` naming the two ledgers and a comment naming TCW-118
  (P117:542-544, P117:595-597). It does not exist on `v4` today.
- **[after TCW-117]** `docs/migration-guide-3.X-to-4.0.0.md` exists (P117:677)
  and `README.md`'s index links it (P117:826-835).
- **[after TCW-117]** `docs/use-cases.md`'s Known gaps match the table of
  S117:1040-1059 (P117:1150-1178, Step 15 item 6.4).
- **[after TCW-117]** TCW-117 rewrites `skills/setup/references/install.md`
  (`:59` only, P117:1353-1366) and `README.md` (P117:1120-1148), and the five
  skill records of the ledger (P117:1423-1444). This plan's Step 4 edits those
  files after TCW-117, in passages TCW-117 does not plan to change (the
  floating install), so the two do not collide; Step 4 re-finds each passage
  by its words.
- **TCW-116's way-back snippet** (its Step 27 comment on this ticket,
  2026-10-24 20:47) names `edited_tickets`, `restore_tickets` and `settings`
  in `tcw/migrate/jira.py` (`:161`, `:178`, `:59`) and `JiraClient` in
  `tcw/work/jira/client.py:148`, all present on `v4`.
- **`tcw migrate` writes its report to standard error** (`tcw migrate --help`:
  "Prints: nothing; every change, report and blocker on stderr"), so every
  saved output below is captured with `2>&1`.
- **The Jira scenario** is `tests/work/jira/test_jira_scenario.py`; its live
  test `test_the_scenario_live` is skipped unless `TCW_JIRA_LIVE=1`,
  `TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY` are set (`:51-55`), and its `LIVE`
  configuration (`:19-40`) is the same on `main` and `v4`, so it is also the
  3.x form of the configuration (it is written under `work:` of a 3.x
  `tcw-config.yaml` by `main:tests/work/projects.py:27-41`).
- **This machine**: pipx 1.17.2, Node 24 with pnpm, Python 3.12 and 3.14 (no
  3.11), Claude Code 2.1.310; no `~/.config/tcw/` and no
  `$XDG_CONFIG_HOME` set; no `~/.tcw-4.0-release/` yet.

## The open items the spec left to the plan

### 1. How each harness lets a user keep the plugin below 4.0 (Design 3.3)

Settled; every harness has a way, by pinning the plugin's source to the tag
`v3.0.2`, which is on GitHub (`git ls-remote --tags origin v3.0.2` prints
`faf5d29d…`) and whose four manifests (`.claude-plugin/marketplace.json`,
`.agents/plugins/marketplace.json`, `.codex-plugin/plugin.json`,
`package.json`) all exist and read 3.0.2. Today every user follows `main`:
`README.md:71` installs Claude Code's marketplace unpinned, `:91` Codex's with
`--ref main`, `:103` Pi's unpinned.

| Harness | How a user holds the plugin at 3.0.2 | Updates itself by default? | Source, and how sure |
| --- | --- | --- | --- |
| Claude Code | `claude plugin marketplace remove tcw` (this also uninstalls the plugin), `claude plugin marketplace add brocef/TCW#v3.0.2`, `claude plugin install tcw@tcw`. To be doubly sure: `/plugin` → Marketplaces → tcw → disable auto-update, or `DISABLE_AUTOUPDATER=1`. | No: automatic updates are off by default for a marketplace that is not Anthropic's own; but `claude plugin update tcw@tcw` on an unpinned install moves to 4.0. | Claude Code's plugin documentation (`code.claude.com/docs/en/plugins`, install: "`#ref` to pin a branch or tag"; loading: "When auto-update runs"). Verified in the documentation. |
| Codex | `codex plugin marketplace remove tcw`, `codex plugin marketplace add brocef/TCW --ref v3.0.2`, `codex plugin add tcw@tcw`. | Yes: Codex re-fetches each git marketplace at its configured ref when it starts, with no switch to turn it off found, so the pin is the only hold; a tag does not move. | `codex plugin marketplace add --help` (codex-cli 0.160.1 on this machine: "owner/repo[@ref]", `--ref <REF>`); the start-up refresh read from Codex's source (`codex-rs/core-plugins/src/manager.rs`), not its documentation. Pin verified; start-up refresh from source only. |
| Pi | `pi remove git:github.com/brocef/TCW`, then `pi install git:github.com/brocef/TCW@v3.0.2` (`-l` for one project only). | No: packages update only through `pi update --extensions` or `pi update <source>`, and "Git tags and commits are also pinned; package updates reconcile the checkout but do not move a configured ref". | Pi 1.0.2's own `docs/packages.md:13-38` and `docs/cli.md:257-266`, installed on this machine. Pin verified; no start-up update inferred from the documentation's silence. |

After 7.3 a user may pin to the branch `3.x` instead of the tag, to receive a
3.x patch if one is ever cut. **The release notes' fifth point (3.3,
criterion 7) is therefore unblocked**, and reads, under the pinned-install
sentence: "To stay on 3.x, keep the plugin at 3.0.2 by pinning it to the tag
`v3.0.2`. Claude Code: `claude plugin marketplace remove tcw`, then `claude
plugin marketplace add brocef/TCW#v3.0.2` and `claude plugin install tcw@tcw`.
Codex: `codex plugin marketplace remove tcw`, then `codex plugin marketplace
add brocef/TCW --ref v3.0.2` and `codex plugin add tcw@tcw`; Codex refreshes
its marketplaces every time it starts, so without the pin it moves to 4.0 on
its own. Pi: `pi remove git:github.com/brocef/TCW`, then `pi install
git:github.com/brocef/TCW@v3.0.2`." The QA plan's scenario 7 (b) runs exactly
these commands; the dispatching session adds them to the QA plan comment.
The one claim not read in published documentation, Codex's refresh at start,
is the reason the notes tell Codex users the pin is needed, which is the safe
reading either way.

### 2. Is a pull request from `v4` with the `run-ci` label open? (Design 6.2 (b))

No. `gh pr list --head v4 --state all --json number,labels,state,title`
printed `[]` on 2026-10-24: no pull request from `v4` has ever been opened, so
the pushes of `v4` at 3.10 and 6.2 (b) start no run by themselves, and each
run is started with `gh workflow run test.yml --ref v4` (`test.yml:42`,
`workflow_dispatch`). Step 10 and Step 30 run the same command again right
before pushing, since a pull request opened in between would start a second
run on the push; if one is open then, the step names it in the record and
follows the `workflow_dispatch` run only.

### 3. Does the test Jira project accept the 3.x setup's fields? (Design 5.2)

Settled by running it, in Step 21 (the rehearsal), under gate 2: the 3.0.2
`tcw work new` filing two items on `TCWTEST` with `LIVE`'s fields
(`TCW Project`, `TCW Item`, `Effort`, `Complexity`), and 3.0.2's
`tcw validate --remote` passing before the migration, is the check. A filing
that `TCWTEST` refuses is a stop under gate 2 (Design 5.0): nothing on the
`TCW` board has been touched, the rehearsal's tickets are moved to `Won't Do`,
and the session brings the refusal to the user, since it means the test
project is not set up as `tcwtest-checklist.md` ends, which no step here can
fix.

## Decided while planning

1. **The release-preparation step, and the follow-ups list.** Decided by the
   dispatching session, 2026-10-24: before the merge clone is built, one step
   folds in the small follow-ups gathered during the 4.0 run. The list is
   `followups.md` in this folder, copied unchanged from the dispatching
   session's notes. Each entry is triaged in "The follow-ups" below as a fix
   in this item, documentation already answered by TCW-117, a new work item
   to file after release, or dropped. The fixes are Step 2. Each is a
   verified, small defect in 4.0's behaviour, made test first; one that turns
   out not to be small at implement becomes a new item instead, and the
   step's record says so. Placing it before 3.4 means the combined review
   sees the fixes, and before 3.10 means CI tests them.
2. **The way-back snippet reads both of its error's added attributes with
   `getattr`.** The dispatching session's note on the ticket says
   `error.pending` is absent on an error raised before the loop.
   `restore_tickets` (`tcw/migrate/jira.py:178-197`) calls `settings(root)`
   and `backend_for(…)` before its `try`, so an error from either carries
   neither `pending` nor `restored`. The script of "Tools" below reads both
   with `getattr(error, "…", None)`.
3. **The rehearsal (5.2) also makes the checks TCW-116's review round 1 left
   for gate 2** (its note on this ticket, 2026-10-24 20:00, posted after the
   spec's last revision): every issue type the `TCW` board uses is edited,
   whether an edit emails watchers, the search index lag right after a run,
   and the way back refusing a ticket edited by hand. To keep the spec's pass
   rule for "both tickets" exactly, the hand-edited ticket is a third one,
   made for that check alone (Step 21). The behaviour under Jira's rate limit
   (HTTP 429) is checked against the live board's ticket count by the dry
   run's count (Step 13) and by 5.6's own re-run rule (S-8).
4. **If the rehearsal shows that an edit emails watchers, the dispatching
   session tells the user, with the number of tickets 5.6 will edit, before
   5.5, and waits for their word.** Gate 2's go was given before that was
   known; the user decides whether the live conversion goes ahead knowing
   it. This adds a question inside gate 2, not a new gate.
5. **The merge clone cannot push to GitHub.** `git clone /Users/brian/Projects/TCW`
   makes the primary checkout the clone's `origin`, so a `git ls-remote origin`
   run inside the clone reads the primary checkout, not GitHub. Every check
   of GitHub's refs in phases B and C is therefore run as
   `git -C /Users/brian/Projects/TCW ls-remote origin …`, and the clone's push
   address is set to an invalid one at once (`git remote set-url --push origin
   no-push`), so no push from it can land anywhere.
6. **M0 must be the primary checkout's `main`.** The clone copies the
   primary checkout's branches; GitHub's `main` reaches it only through the
   primary checkout's own `main`. Step 12 therefore checks that
   `git -C /Users/brian/Projects/TCW rev-parse main` equals M0 (after
   `git fetch origin`) and that the primary checkout is on `main` with no
   changes, which 5.5 needs anyway; if `main` is behind, it is brought to M0
   with `git -C /Users/brian/Projects/TCW merge --ff-only origin/main` before
   the clone is made.
7. **One script runs the suite as CI runs it**, `~/.tcw-4.0-release/ci-suite.sh`
   (Tools), so that every run of Terms' definition (4.3 (d), 5.8, 6.2 (a)) is
   the same run. At 4.3 (d) it runs in the merge clone itself, which was made
   by `git clone` for the release and is that run's fresh clone, because the
   migration is not committed until 4.4; everywhere else it makes its own
   clone.
8. **The CLI's closing advice after a cut is left as it is.** `cut_version.py`
   prints `Push with: git push origin main --tags` (`:186`). This release
   pushes differently (7.1-7.3), but the advice is right for every later
   release (Non-goals, `docs/releasing.md`'s usual order), so it is not
   changed; Step 30 says not to follow it.

## Tools used by several steps

All live in the release folder `~/.tcw-4.0-release/`, outside every
repository (spec Terms), made by Step 12. None is committed.

**`refs.txt`**: one line per value, `M0 <hash>`, `V <hash>`, `A <hash>`, each
with the `date -u` it was recorded; a value recorded again (a defect at gate
1) is a new line, and the last line of each name is the current value.

**`gates.md`**: the master copy of every answer at every gate, written as it
is given (Design 10): the gate, the commit it names, the date and time (UTC),
the user's words quoted exactly, and what followed. Its whole content is
copied to `docs/work/TCW-118-tcw-4-0-release/gates.md` by the commit that
records each answer.

**`ci-suite.sh <checkout> [<python>]`**, the suite as CI runs it:

```sh
#!/bin/bash
# The suite as CI runs it (TCW-118 spec, Terms). <checkout> is used in place
# when it is the merge clone before its migration commit (4.3 (d)); every
# other caller passes a fresh clone.
set -euo pipefail
repo="$(cd "$1" && pwd)"; py="${2:-python3.14}"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/tcw-ci.XXXXXX")"
mkdir -p "$scratch"/{home,config,data,state,cache}
"$py" -m venv "$scratch/venv"
nodebin="$(dirname "$(command -v pnpm)")"
run() {
  env -i PATH="$scratch/venv/bin:$nodebin:/usr/bin:/bin:/usr/sbin:/sbin" \
    HOME="$scratch/home" XDG_CONFIG_HOME="$scratch/config" \
    XDG_DATA_HOME="$scratch/data" XDG_STATE_HOME="$scratch/state" \
    XDG_CACHE_HOME="$scratch/cache" LANG=en_US.UTF-8 \
    bash -c "cd '$repo' && $1"
}
echo "== $(date -u) in $repo, HEAD $(git -C "$repo" rev-parse HEAD)"
echo "== TCW_ variables inside the run (nothing below this line means none):"
run 'env | grep "^TCW_" || true'
echo "== HOME inside the run: $(run 'echo $HOME')"
run "pip install -q -e '.[dev]'"
run "pytest"                      # bare pytest, test.yml:76
run "pnpm install --frozen-lockfile && pnpm check:build"   # test.yml:103-104
echo "== suite and web build passed"
```

`env -i` starts the run with no inherited variable at all, which unsets every
`TCW_` variable by construction; the script prints the proof criteria 17 and
25 ask for. Its output is saved by each caller, with `2>&1`, to the file the
step names.

**`private-names.txt`**: the names of the user's private projects, from the
maintainer's own notes, one per line, written by the user or the dispatching
session at Step 12 and never committed (spec 4.3 (f); the repository is
public). The search is `git -C <repo> diff <from> <to> | grep -n -i -F -f
~/.tcw-4.0-release/private-names.txt`, which must print nothing. If the file
cannot be written because nobody has the list, the step stops and asks the
user.

**`way-back.py <project root> <project id> <folder of saved outputs>`**, the
tickets' way back (Design 9; TCW-116's Step 27 comment, with Decided 2):

```python
"""Put back the 3.x TCW Item of every ticket a `tcw migrate` run edited.
Run with the 4.0 `tcw`'s Python (the merge clone's .venv/bin/python), before
3.0.2 is reinstalled (TCW-116 review round 1)."""
import sys
from pathlib import Path
from tcw.errors import TcwError
from tcw.migrate.jira import edited_tickets, restore_tickets, settings
from tcw.work.jira.client import JiraClient

root, project_id, saved = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
runs = sorted(saved.glob(sys.argv[4] if len(sys.argv) > 4 else "tcw116-step6*.txt"))
done = edited_tickets("\n".join(p.read_text() for p in runs))
dry_file = sorted(saved.glob("*dry-run*.txt"))[-1]
dry = {k for k, _, _ in edited_tickets(dry_file.read_text().replace("would edit ", "edit "))}
only_one = sorted({k for k, _, _ in done} ^ dry)
print("runs read:", [p.name for p in runs], "dry run:", dry_file.name)
print("in only one of the two:", only_one)
if only_one and "--read" not in sys.argv:
    sys.exit("stop: a person reads these keys first, then re-runs with --read")
try:
    print("put back:", restore_tickets(done, JiraClient(settings(root)), root, project_id))
except TcwError as error:
    print("put back:", getattr(error, "restored", None))
    print("left out:", getattr(error, "pending", None), error)
    sys.exit(1)
```

It builds the Jira client only when it runs (TCW-116's 21:30 handoff); it is
written at Step 12 and run only by Step 21 (on `TCWTEST`) or by section 9's
row "5.6-5.7". Step 21's run of it is its rehearsal.

## The follow-ups

Each entry of `followups.md` (cited by its line, `F:n`; `F:2` holds three
entries, 2a-2c) was checked against `v4` at `bb6adc7e` on 2026-10-24, by
reading the code and, where cheap, reproducing it with the worktree's 4.0
`tcw` in scratch projects. Counts: **21 fixes in this item** (covering 24
entries, three pairs being one defect), **2 documentation already answered
by TCW-117**, **25 new work items to file after release** (covering 28
entries; F:61 is also in the documentation group), **9 dropped**: 62 entries in
all. A fix is a verified, small defect in 4.0's
behaviour; a defect that is older than 4.0 is fixed here only when it damages
data or is a line or two, and is otherwise a new item. Web-app changes are new
items: each needs the committed web build rebuilt (`pnpm check:build`), which
is not small.

### Fixes, made by Step 2, each test first

| # | Entry | What is wrong (evidence) | Change | Test |
| --- | --- | --- | --- | --- |
| 1 | F:1 | `parse_address("tcw://demo.foo/x")` says `'demo.foo/x' is not a full identifier`, dropping the prefix; the fall-through `return parse_full_id(rest)` at `tcw/ids.py:300` | catch `MalformedId` there and raise it again quoting the whole address | `tests/test_ids.py`, `test_ac2_each_refusal_names_its_rule`: case `("tcw://p1.foo/x", "tcw://p1.foo/x is not")` |
| 2 | F:2c | a store `path` of `TCW://p1.path/other` is read as a folder (`is not a directory: …/TCW:/p1.path/other`); the scheme test is case-sensitive at `tcw/store/fs.py:3681`, `tcw/config.py:498`, `tcw/validate.py:301`, `tcw/migrate/stores.py:195` | compare the scheme without regard to case at those four places | a validate test: the message says `is not a tcw:// address` and not `not a directory` |
| 3 | F:3, F:18 | validate's message names the config file twice (`.tcw/tcw-config.yaml: taxonomy: /abs/…/.tcw/tcw-config.yaml: …`): `_run_check` formats `{e}` at `tcw/validate.py:372`, `:377`, `:381`, `:383` instead of `_config_message`, which `:309`, `:681`, `:776` use | use `_config_message(e, project_root)` at those four lines | `tests/test_legacy_store_config.py` near `:330`: the absolute path is absent from the message |
| 4 | F:5 | `tcw capabilities set cli/a --parent cli/a` exits 0, as does a two-capability loop; only validate reports it (`tcw/store/fs.py:1246`); new in 4.0 (no `--parent` on `main`) | in `set` (`tcw/store/fs.py:3214-3222`) refuse a parent that is the object itself or whose parent chain in this project returns to it | `tests/test_capabilities_federation.py`: a self-parent `set` fails and the state file is unchanged; the same for a loop of two |
| 5 | F:6, F:55 | the work store's reserved-name finding (`tcw/object_folders.py:375-377`) no longer points a 2.x store to its guide, which `main:tcw/work/fs_backend.py:537` did; a 2.x `docs/work/inbox/x/` is told to run `tcw migrate`, which cannot convert 2.x; A12 copies the message | append `MIGRATION_GUIDE` (`tcw/store/base.py:1194`) to that finding | validate on a store holding `docs/work/inbox/x/` names `docs/migration-guide-2.8-to-3.0.0.md` |
| 6 | F:10 | `_merge`'s scalar branch at `tcw/config.py:796-798` clears `origins` but not `places`; nothing shows it today | add `_clear(places, here)` there | a unit test: a later layer writing `work.tags` as a non-list leaves no `places` entry under `("work", "tags")` |
| 7 | F:11 | with both `TCW_WORK_STAGES_SPEC__APP` and `…_SPEC_PROMPT__APP` set, the note names both though only the second's prompt is used: a list that replaces the one below still appends to `written` (`tcw/config.py:768-769`, `:800-801`) | when the list has no `inherit: true` entry, set `written[here] = [origin]` | `personal_variables(("work","stages","spec","prompt")) == ["TCW_WORK_STAGES_SPEC_PROMPT__APP"]` |
| 8 | F:14 | `rm`'s referrer message names bare id-paths (`billing/c (Blocked by)`) while `reset`'s names full identifiers (`tcw/store/fs.py:3022`); no spec asks for the bare form | build the full identifier at `tcw/store/fs.py:3018`, and at `:2442`, `:2477` for taxonomy | `tests/test_taxonomy.py:416`, `:426` and `tests/test_capabilities_rm.py` expect `app.capabilities/billing/c (Blocked by)` |
| 9 | F:15 | `capabilities rm a` succeeds while `b` names `a` as its `parent`, leaving `dangling parent ref` (reproduced): `_referrers` (`tcw/store/fs.py:3012`) skips `parent`, which `_cap_ref_rows` (`:2745`) leaves out. Older than 4.0, but it damages the records | also check `meta.get("parent")`, adding `"<p> (parent)"` | `tests/test_capabilities_rm.py`: add `a`, add `b --parent a`; `rm a` is refused naming `billing/b (parent)`, and `a` is still on disk |
| 10 | F:16, F:44 | `rm` and `reset` leave an empty organising folder, which 4.0's validate then warns about (`holds no TCW object`, `tcw/object_folders.py:381`); `move` already cleans up with `remove_emptied` (`:536`) | call `remove_emptied(self.root, id_path)` after `_rm` at `tcw/store/fs.py:2412`, `:2973`, `:3067` | rm the only capability under `billing/`, and reset one: the folder is gone and validate prints no warning |
| 11 | F:23 | `tcw taxonomy rename bill PAY` says `docs/taxonomy/PAY already exists` when the folder is `pay` (reproduced) | at `tcw/move.py:228-229`, name the spelling `exact_child` returns | `tests/test_tree_move.py`: with `pay` present, the message names `docs/taxonomy/pay` |
| 12 | F:30 | with two fetched projects each with a bad manifest, the advice names only the first one's folder: `tcw/provision.py:556-562` takes one `_holding()` (`:200`) though the error lists every file (`tcw/store/project.py:726`) | name each distinct holder of `error.files` | `tests/test_project_provision.py`: two fetched projects with unreadable manifests; both folders appear |
| 13 | F:33 | test docstrings still describe `list --local`, a flag 4.0 replaced with `--scope` (`tcw taxonomy list --help`): `tests/test_tree_parent_missing.py:58-59`, `:98`, `:193`; `tests/test_overrides_by_path.py:417` | reword each to the `--scope` form the test runs | none: text only; the module passes unchanged |
| 14 | F:45 | the drift message still says "upstream default", a 3.x term (`tcw/capabilities/cli.py:199-200`) | "the status it inherits" | `tests/work/test_drift_work.py` asserts the new line |
| 15 | F:48 | `tcw project config --origin`'s help says it "prints even when something is wrong" (`tcw/project_cli.py:94-97`), but it follows TCW-109 Design 7.1, printing nothing when an inherited key is undecided or broken (`tcw/config_cli.py:295-301`) | the help says an undecided or broken inherited key still stops it | the existing help test, if one pins the text; else none (help text) |
| 16 | F:51 | a `capabilities.yaml` entry for a project the manifest places at a missing folder is an error with exit 1 (reproduced); TCW-110's spec (`:567`) says unresolved | at `tcw/validate.py:729-730` and `:819-820`, report `unresolved` when the problem is an `_UncheckedProblem` | the same setup gives an `unresolved:` line and exit 0 |
| 17 | F:53 | no test covers A14's other source name (`tcw/migrate/config.py:666-667`) | none: test only | `tests/migrate/test_migrate_manifests.py`: the path comes from an ancestor's file and A14 names `<relative>/tcw-config.yaml` |
| 18 | F:57 | a package migrated before its related projects: the after-run check lists no A12 and the summary does not say the check was cut short; `collect_findings` (`tcw/cli.py:274-278`) returns only the configuration findings and the graph problem, and `check_after` (`tcw/migrate/execute.py:356-360`) drops that as A8 predicted (read in code, not run) | `check_after` returns a flag when `registry.check()` is not empty; `_check_after` (`tcw/migrate/cli.py:103-109`) adds a report line: `check after the run stopped: a related project is still TCW 3.x; run 'tcw validate' once it is migrated` | `tests/migrate/test_migrate_monorepo.py`: migrate `api` first; the line is printed |
| 19 | F:58 | A8 in a workspace's run lists descendants before a parent: Design 2.10 and 6.2 of TCW-116 say parents first, but `still_3x_reports` (`tcw/migrate/config.py:1050-1070`) keeps the order found | order the non-ancestors by the family's predicted parent links | the order of A8's lines in a workspace run with a parent and a child both 3.x |
| 20 | F:59 | `1 tickets edited`, `1 files written`: `tcw/migrate/report.py:111-112` never uses the singular | singular for a count of 1 | `counts([one write], 1, dry=False) == "changed: 1 file written, 0 moved, 0 deleted; 1 ticket edited"` |
| 21 | F:60 | a refused run's planned lines describe C12 and D7 for a B9-refused override: it is missing from `resolved` (`tcw/migrate/stores.py:539`), so `_plan_object` plans them | at `tcw/migrate/stores.py:319` and `:345`, also require `"overrides" not in data` | a refused B9 run lists no C12 or D7 for that file |

Fixes 18 to 21 are in `tcw migrate`, TCW-116's area, and are made before
Step 15 runs it on this repository. Any fix found at implement to be larger
than its row says becomes a new item instead (Decided 1), and Step 2's
record says so.

### Documentation already answered by TCW-117

- **F:22** (`skills/work/SKILL.md`'s description and its delegation bullet,
  `:96`, name filing into another project and `projects:`): TCW-117 Step 19 (a)
  rewrites both (P117:1250-1254).
- **F:61** (4.0 accepts an unknown top-level config key silently; 3.x did
  too, `tcw/config.py:436-451`): a deliberate non-goal of TCW-109 (its spec
  `:173-177`) kept as S-9's known gap "unknown top-level keys", which TCW-117
  keeps with "No item yet" (S117:1056). Whether such a key should be an error
  or a warning is a decision, so a new item for it is listed below as well.

### New work items, filed after release by the dispatching session

Each with the evidence above, under TCW, not under TCW-99:

- web app (each needs a rebuilt bundle): **F:2a** back/forward does not
  clear `fileStage` (`web/client/src/ui/app.tsx:389-405`, new in 4.0);
  **F:2b** the link picker's caret moves a frame late
  (`shared-components.tsx:531`, older); **F:9 with F:37** a date-only created
  value shown a day early west of UTC (`modified-at.tsx:5`, older); **F:21**
  the create form ignores the answer's warnings (`work-forms.tsx:488-505`);
  **F:38 with F:39** the served project's capability detail fetched twice
  (older; not reproduced); **F:40** "its objects are not listed" where
  TCW-113's spec (`:1115`) says "work items" (`app.tsx:468`); **F:41** an
  inherited Status shown without saying so (`shared-components.tsx:459`);
- **F:13** the e2e specs' readiness check accepts any server on the port
  (`web/e2e/missing-parent.spec.ts:37-50` and two more; test tooling, older);
- **F:8** broken YAML in an object folder hides the `resources/` finding
  (`tcw/validate.py:447`, `:587`): which files may stop a check is a decision;
- **F:12** `work new --blocked-by app.work/<item>` exits 7 while `app`'s
  `work.jira` is undecided: the write must confirm the blocker exists
  (`tcw/work/cli.py:85-86`); a design question;
- **F:17** `'cc''s`: the doubled quote is TCW-112's spec's template (`:448`,
  `:584`), pinned by tests;
- **F:19** `show` of an orphaned override prints a name made from its folder
  (older, `main:tcw/store/fs.py:2316`, documented in `add --help`);
- **F:20** a two-parent clash's unset fields come from the winner: a risk
  TCW-112's spec records, the design the user confirmed; filed only to keep
  it visible;
- **F:24** a recorded-reference warning can show an absolute path
  (`tcw/work/jira/backend.py:876`, by `shown()`'s documented rule); which
  folder `serve` shows paths from is a design question;
- **F:26** a ticket edit whose answer was lost is "still to be set": TCW-114's
  spec (`:865`, `:1559`) asks for those words; a re-run recovers;
- **F:27 with F:46** the rename mention list matches a bare one-part name
  (`An invoice.`, `name: invoice`; `tcw/rewrite.py:496-497`): TCW-114
  Design 6.4 asks for it;
- **F:28** rename's mention lines print absolute paths (`tcw/rewrite.py:507`;
  older);
- **F:32** a Ctrl-C prints a Python traceback, TCW-wide (spec Notes,
  "Follow-ups");
- **F:34** the placement bound's first refusal says "outside <folder>" for a
  hidden or nested folder (`tcw/provision.py:142-164`; TCW-115 Design 7.8's
  words);
- **F:35** the personal-manifest way out does not say the entry needs
  `repository:` (`tcw/provision.py:119-121`; the spec's words, `:981-985`);
- **F:36** `tcw project info core` prints the top-level usage: argparse's
  root reports leftover arguments for every command (`tcw/cli.py:483`;
  older);
- **F:42** TCW-113 Design 2.2's message template lists two endings, the code
  three: a documentation item, not in TCW-117's plan (no match in P117);
- **F:47** `taxonomy move --top` on an object already at the top prints the
  wrong message (reproduced on any object; `tcw/move.py:224-225`, the words
  of TCW-114 Design 5.4 (c));
- **F:52** a filesystem-mode parent holding `work.jira` is an error in the
  parent: TCW-109 AC 9 makes it so (`tcw/work/config.py:513-514`);
- **F:61** whether an unknown top-level key is an error or a warning
  (above).

### Dropped

- **F:4**: `tcw taxonomy extends` no longer exists; its exit 2 is argparse's
  `invalid choice`.
- **F:7**: true since TCW-114: renaming an item holding a nested item
  succeeds and rewrites the child's parent (reproduced).
- **F:25**: not reproduced: with two copies of `core` not named as a parent,
  writes naming it exit 3 and `work list` exits 0; with `parents: [core]` every
  command exits 1, which TCW-114's spec (`:506`) gives for a graph problem.
- **F:29**: wrong: full validate checks `capabilities.yaml` (`tcw/validate.py:819`
  → `tcw/work/gates.py:220`); only "a change not yet made" is left to the
  advance check (`gates.py:224-227`).
- **F:31**: by design (TCW-115 Design 1.8): a manifest is read only when a
  lookup consults it; the parent's own validate reports the key.
- **F:49, F:54**: the two `write .tcw/.gitignore` lines are two writes the
  spec requires (TCW-116 review round 2).
- **F:50**: `tcw migrate` exiting 0 on a 2.x store is out of scope by
  TCW-116's decision 13, and A12 reports it (now pointing to the 2.x guide,
  fix 5).
- **F:56**: answered by this plan (Decided 2, and the `way-back.py` script).

## Phase A: ready on `v4` (Design 3)

Steps 1 to 11 run in the `v4` worktree, `/Users/brian/Projects/TCW/.claude/worktrees/v4`,
with its `.venv`. TCW-118 moves to `implement` (the dispatching session, the
3.0.2 lifecycle `tcw`) after Step 1 and before Step 2's first change to code
(Design 2.1). The order is Design 3's, with the release-preparation step
(Decided 1) placed after 3.1: 3.1, preparation, 3.2, 3.9, 3.3, 3.4, 3.5, 3.6,
3.7, the documentation entries, 3.10, 3.8. A fix made at Step 6 (the combined
review) or Step 10 (CI) sends the steps after it round again, and CI runs on
the new commit (Design 3).

The implement round, `implement/round-1.md`, is written as Phase A goes: each
step below appends its record under a heading named for the step, and
commits it with the step. Records of Steps 12 to 26 are kept in the release
folder while rule 4.0 holds and written into the round after Step 26
(Design 2.2).

### Step 1 — every other child is completed (3.1)

**Who:** the dispatching session.

**Does:** for each of TCW-106 to TCW-117, `tcw work show tcw/<folder>`
(the 3.0.2 lifecycle `tcw`) and keeps the `stage:` line; confirms that no
agent is running in the `v4` worktree (TCW-117's implementer and every
reviewer stopped), so `v4` is not moving; reads TCW-116's implement rounds for
its two proofs (TCW-116 plan Steps 14 and 25) and keeps the proof-2 hit count
of the scan of `tests/test_docs_describe_4_0.py` with `UNMIGRATED_RECORDS`
deleted, or the sentence that the rehearsal could not be made; confirms
TCW-116's Step 27 comment is on this ticket (it is: 2026-10-24 20:47). Then
re-finds every line this plan cites (`git grep -n` of each passage's words),
and notes in the round each one that moved.

**Files:** creates `docs/work/TCW-118-tcw-4-0-release/implement/round-1.md`
with the twelve `stage:` lines, the proof-2 count and the moved citations.

**Proves it:** twelve lines reading `stage: completed` (criterion 1); the
count and the comment's date recorded (criterion 10). A child not completed
stops the release here.

### Step 2 — release preparation: the small follow-ups (Decided 1)

**Who:** one agent per fix, or one agent for all of them, briefed by the
dispatching session with this step and the fix's entry in "The follow-ups";
the dispatching session moves TCW-118 to `implement` before it starts.

**Does:** for each fix in "The follow-ups", in the order listed: the test
first, run and seen to fail for the reason the entry gives; then the change;
then the test and its module pass. The full suite (`.venv/bin/pytest` from the
worktree's root) passes after the last fix. One commit per fix,
`TCW-118: <what was fixed>`, with only the files the entry names.

**Files:** those each fix names in "The follow-ups", and
`docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md` (created here, under
`## Fixed`, one line per fix; Step 5 adds the rest). A fix a user would notice
also gets a line in `docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md`
under `## Fixes`.

**Proves it:** each fix's test red before and green after (the red run's
failing line pasted in the round); the suite green.

### Step 3 — `scripts/cut_version.py` cuts a version the files already hold (3.2)

**Who:** an agent.

**Tests first, in `tests/test_cut_version.py`:**

- `make_repo` (`:23`) gains `tagged: bool = True`; when true it runs
  `git tag v<version>` after its commit, so every existing test keeps a tag
  for its current version and goes on bumping as before (criterion 5).
- `test_an_untagged_current_version_is_cut_by_name` (criterion 2):
  `make_repo(tmp_path, "4.0.0", tagged=False)`; `cv.main(["4.0.0"], root=root)`
  returns 0; `cv.current_version(root) == "4.0.0"`; the five files' bytes
  equal what they were; `docs/changelogs/v4.0.0.md` and
  `docs/release-notes/v4.0.0.md` exist; `_assert_cut_is_clean(root, "4.0.0")`
  (`:95-103`: the commit subject, the tag, an empty `git status --porcelain`).
- `test_a_tagged_current_version_is_refused` (criterion 3):
  `make_repo(tmp_path, "4.0.0")` (tagged); `pytest.raises(SystemExit,
  match="v4.0.0 is already tagged")`; HEAD, `git tag` and
  `git status --porcelain` equal their values before the call.
- `test_a_relative_bump_is_refused_while_the_current_version_has_no_tag`,
  parametrized over `patch`, `minor`, `major` (criterion 4):
  `make_repo(tmp_path, "4.0.0", tagged=False)`; `pytest.raises(SystemExit,
  match=r"cut_version\.py 4\.0\.0")`; nothing changes, as above.
- The existing `match="already the current version"` expectation, if any
  test holds it, is replaced by the two refusals above.

Run: the three new tests fail (the first with "already the current version",
the others with no refusal or a different message).

**Change, `scripts/cut_version.py`:**

- a function `_tagged(root, version) -> bool`: `git -C <root> tag --list
  v<version>` prints a line (local tags only, no network; Design 3.2);
- in `main` (`:160-186`), before `next_version`'s result is used: if
  `args.bump` is `patch`, `minor` or `major` and `not _tagged(root, old)`,
  exit with `cut_version: v<old> has no tag yet; cut it with 'python
  scripts/cut_version.py <old>'` (3.2 (c));
- the rule at `:168-169` becomes: if `new == old` and `_tagged(root, old)`,
  exit with `cut_version: v<old> is already tagged` (3.2 (b)); if `new == old`
  and not tagged, the cut goes on without calling `bump_files` (3.2 (a));
- every refusal comes before `bump_files` and `combine_upcoming`, as the
  missing-folder refusal at `:171-175` already does;
- the final message says `cut v<new>` and, when `new == old`, `(the version
  files already held it)` in place of `(was v<old>)`.

`docs/releasing.md`, after the code block at `:10-13`, gains a paragraph: when
the version files already hold the version to release (as on a major branch
whose files record the version they write), cut it by naming it, `python
scripts/cut_version.py X.Y.Z`; the script then leaves the five files alone,
combines the entries, commits and tags; and while the current version has no
tag, `patch`, `minor` and `major` are refused, because they would skip the
untagged version (criterion 6).

**Files:** `scripts/cut_version.py`, `tests/test_cut_version.py`,
`docs/releasing.md`. Commit `TCW-118: cut_version.py cuts a version the files
already hold`.

**Proves it:** the new tests green, every earlier test in the file green
(criteria 2-5); `grep -n 'already hold\|no tag yet' docs/releasing.md` finds
the paragraph (criterion 6).

### Step 4 — the plugin installs the CLI of its own version (3.9) [after TCW-117]

**Who:** an agent.

**Tests first.** In `tests/test_session_bootstrap.py`, the fixture `_clone`
(`:31-36`) already writes `__version__ = "<version>"` and no
`scripts/check_versions.sh`, so the version check on exit prints nothing
(criterion 43):

- `test_install_pins_the_plugin_version`: `_clone(tmp_path, "9.9.9")`, a
  recording pipx (`_recording_pipx`, `:54-65`) that installs a `tcw` stub; the
  pipx log equals exactly `install --force tcw-cli==9.9.9`; the sentinel's
  bytes equal the clone's `tcw/__init__.py`.
- `test_failed_pinned_install_names_the_version_and_retries`: as
  `test_failed_install_prints_one_line_and_retries_next_time` (`:184-201`),
  with `_recording_pipx(…, rc=1)`: exit 0, exactly one line on stdout,
  containing `pipx install tcw-cli==9.9.9`; the sentinel's bytes unchanged;
  a second `_run` calls pipx again (the log has two lines).
- `test_no_version_line_installs_nothing`: a clone whose `tcw/__init__.py`
  holds `x = 1` and a recording pipx; exit 0, empty stdout, no pipx log.
- The existing assertions of the unpinned command, `log.read_text().strip()
  == "install --force tcw-cli"` (`:215`, `:368`), `endswith("tcw-cli")`
  (`:201`) and `"pipx install tcw-cli" in …` (`:198`, `:386`), change to the
  pinned forms for their fixture's version (`9.9.9` from `_clone`; `2.4.0`
  from `_plugin`).

In `tests/test_check_versions.py`, `OLDER_ADVICE` (`:32`) becomes
`"pipx install --force tcw-cli=="`, and `test_cli_older` (`:98`) asserts the
full `pipx install --force tcw-cli==<skills>` for its fixture's skills
version (criterion 44).

Run: these fail against today's scripts.

**Change, `scripts/session_bootstrap.sh`:**

- after the marker test at `:83`, read the version:
  `version="$(sed -n 's/^__version__ = "\([0-9][0-9.]*\)"$/\1/p' "$root/tcw/__init__.py" | head -n 1)"`
  and `[ -n "$version" ] || exit 0` (3.9 (c): nothing installed, exits as
  when the file is missing, after the version check that the trap runs);
- `:115` becomes `pipx install --force "tcw-cli==$version"`;
- `:121`'s message names `pipx install tcw-cli==$version` in place of
  `pipx install tcw-cli`;
- the comment at `:85-92` says the install takes the release whose version
  equals the plugin's own, so the sentinel now does say which CLI was asked
  for, and drops "which floats" and "`pipx upgrade tcw-cli` is how a user
  moves ahead of this";
- the comment at `:110-114` adds that a version not yet on PyPI fails the
  same way, and the next session tries again.

The order of the checks (steady state `:93-97`, the guard `:101-104`, no pipx
`:108`) is not changed. `scripts/check_versions.sh:96` becomes `echo "To bring
them into line, match the CLI to the skills: pipx install --force
tcw-cli==$skills (for a development checkout, update the checkout
instead)."`; `:97` stays.

**Change, the passages (3.9 (e)):**

- `skills/setup/references/install.md`: the opening (`:3-8`) says the plugin
  installs `tcw-cli` at its own version; step 3 (`:39-44`, "Behind the latest
  release?") becomes "Behind the plugin?", advising
  `pipx install --force tcw-cli==<the plugin's version>`, and no longer says
  the installed CLI floats;
- `README.md` (`:77-86`, as TCW-117 leaves it): the session-start install
  takes the CLI of the plugin's own version;
- `docs/capabilities/plugin/bootstrap-the-cli/description.md:1`: "That
  install takes the newest release on PyPI" becomes "That install takes the
  release whose version equals the plugin's own, so a plugin update brings
  the matching CLI and holding the plugin back holds the CLI back";
- `docs/capabilities/cli/install-from-pypi/description.md:6-7`: "runs `pipx
  install tcw-cli` on my behalf" becomes "runs `pipx install
  tcw-cli==<the plugin's version>` on my behalf".

These two records are edited by hand, in whatever format TCW-117 leaves them
(3.x on `v4`, Design 9.1 of TCW-116), never with a `tcw capabilities`
command. `capabilities.yaml` already lists exactly the two under `changed:`.

**Files:** `scripts/session_bootstrap.sh`, `scripts/check_versions.sh`,
`tests/test_session_bootstrap.py`, `tests/test_check_versions.py`,
`skills/setup/references/install.md`, `README.md`, the two `description.md`
files. Commit `TCW-118: the plugin installs the CLI of its own version`.

**Proves it:** the tests green (criteria 43, 44); `grep -n 'pipx upgrade'
scripts/check_versions.sh` prints nothing (44); `grep -rn 'floats\|newest
release\|pipx upgrade' scripts/session_bootstrap.sh
skills/setup/references/install.md README.md
docs/capabilities/plugin/bootstrap-the-cli` prints nothing (45); no test
asserts the unpinned `install --force tcw-cli` (`grep -n '"install --force
tcw-cli"' tests/test_session_bootstrap.py` prints nothing).

### Step 5 — TCW-118's own entry files (3.3)

**Who:** an agent; the harness paragraph is copied from "The open items",
item 1, word for word.

**Files:**

- `docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md`. A leading
  paragraph, before any `##` line (`combine` puts it right after the title,
  `cut_version.py:99-125`): 4.0 is a major release; it changes where a project
  keeps its files (a `.tcw/` folder) and how projects relate (parent links
  in place of `projects:` and `extends`); a 3.x project must be migrated with
  `tcw migrate` before 4.0 will work in it. Then `## Upgrading` (placed first,
  `cut_version.py:35`), six points in plain words:
  1. how to move across: [the migration guide](migration-guide-3.X-to-4.0.0.md),
     the link written relative to `docs/release-notes/v4.0.0.md`, that is
     `../migration-guide-3.X-to-4.0.0.md`;
  2. keep any CI job or other automation that installs `tcw-cli` at
     `tcw-cli<4` until that project is migrated;
  3. everyone working on a project upgrades together; 4.0 refuses a 3.x
     project's files except to migrate them;
  4. commit, or back up, before running `tcw migrate` for real;
  5. from 4.0 the plugin installs the CLI of its own version
     (`tcw-cli==<the plugin's version>`), so a plugin update brings the
     matching CLI, and the way to stay on 3.x is to keep the plugin below 4.0:
     the paragraph of "The open items", item 1, one sentence or two per
     harness; then the one named case: a 3.x plugin installing on a machine
     for the first time still takes the newest CLI, so there run `pipx
     install --force 'tcw-cli<4'` once, after which the 3.x plugin leaves it
     alone;
  6. 3.x keeps a home: the branch `3.x` holds the last 3.x code, and a 3.x
     patch, if one is ever needed, is cut there and published by its tag.

  Plus a line under `## Fixes` for each user-visible fix of Step 2.
- `docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md` (begun at Step 2):
  `## Changed`: the rules of 3.2 (a)-(c); `session_bootstrap.sh` installs
  `tcw-cli==<the plugin's version>` and `check_versions.sh`'s older-CLI
  advice matches it. `## Removed`: `tests/test_repo_config_pair.py` and the
  root `.gitignore` line `/tcw-config.local.yaml` (removed at Step 15 in the
  merge clone). `## Internal`: this repository migrated to 4.0; the ledger
  records brought into the documentation scan (`UNMIGRATED_RECORDS` deleted).

No other item's entry file is touched (`docs/release-notes/upcoming/README.md`).
Commit `TCW-118: release notes and changelog entries`.

**Proves it:** `grep -c '^## Upgrading' <release-notes entry>` prints 1; the
six points read one by one in the round against 3.3 (criterion 7); `git log
--name-only --format= -- 'docs/*/upcoming/'` over this item's commits lists
only the two TCW-118 files (criterion 7); the suite green. **[after TCW-117]**
If TCW-117's live-document scan (`DOC_FILES`, P117:1446-1458) reads the
`upcoming/` entries, a line naming a 3.x form (`projects:`, `extends`) passes
only when it also names `tcw migrate` or the migration guide (its
`ALLOWANCE`, P117:596-597), so the leading paragraph's sentence that names
them also names `tcw migrate`.

### Step 6 — the combined review (3.4)

**Who:** the dispatching session starts one `adversarial-code-reviewer` agent
per round; fix agents as below.

**Does:** the reviewer reads `git diff main...v4`, sliced by concern (not by
file), with TCW-99's design (`docs/work/TCW-99-…/design.md`) and each child's
spec as its reading. The slices, each a numbered question naming the files
and the failure to look for:

1. the `.tcw/` folder and version stamps across every writer (TCW-106, with
   TCW-111's state files and TCW-116's migration);
2. a project family together: parent links, inheritance, scope, changes only
   in the owning project (TCW-107, 108, 109, 112, 113, 114), reading
   `tests/families.py` and the tests that import it (`grep -rl
   'tests.families\|from tests import families' tests/`);
3. identifiers and addresses across the CLI, the web app and Jira (TCW-110,
   113, 114, `tcw/work/jira/`);
4. `tcw project` and `tcw migrate` against what the other children write
   (TCW-115, 116);
5. the release's own changes (Steps 2-4).

It sorts its findings into "belongs to 4.0" and "needs a separate change" and
ends with a literal `DONE` or `NOT DONE`. Each "belongs to 4.0" finding is
checked against the code by the dispatching session (accepted, narrowed or
rejected, with the reason), then fixed on `v4` by an agent briefed for that
finding alone, test first, in the child's area, one commit
`TCW-118: combined review: <finding>`; the slice it touched is reviewed again
in round 2. A "separate change" becomes a proposed work item in the round.
At most two rounds; a second `NOT DONE` is brought to the user with the split,
and the user decides (Design 3.4).

**Files:** the fixes' files; `implement/round-1.md` gets both reports and the
verdict on each finding with its fix commit.

**Proves it:** criterion 8.

### Step 7 — success criterion 1 and the Known gaps (3.5) [after TCW-117]

**Who:** an agent.

**Does:** at `v4`'s tip, runs this from the worktree's root and pastes its
output in the round:

```sh
.venv/bin/python - <<'PY'
import re
from pathlib import Path
ids = re.findall(r"^### ((?:UC|S)-\d+)\b", Path("docs/use-cases.md").read_text(), re.M)
specs = sorted(p for p in Path("docs/work").glob("TCW-1*/spec/spec.md")
               if 106 <= int(p.parts[2].split("-")[1]) <= 117)
assert len(specs) == 12, specs
def use_cases(text):
    m = re.search(r"^## Use cases\n(.*?)(?=^## )", text, re.M | re.S)
    return m.group(1) if m else ""
sections = [use_cases(p.read_text()) for p in specs]
for i in ids:
    n = sum(bool(re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", s)) for s in sections)
    print(i, n)
PY
```

Every line must have a count of at least 1; `S-1` does not count `S-10`,
because the pattern refuses a following digit or hyphen. Then, for each row
of S117:1040-1059's table, one line in the round giving the gap's state in
`docs/use-cases.md` at `v4`'s tip (gone from its case's `**Known gaps**`
list, or the item it names) and whether it agrees with the row's outcome. A
row that does not agree goes back to TCW-117's area as a Step 6 finding would.

**Files:** `implement/round-1.md`.

**Proves it:** criteria 9 and 49.

### Step 8 — the combined release notes, previewed (3.6)

**Who:** an agent.

**Does:** from the worktree's root,

```sh
.venv/bin/python - <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("cv", "scripts/cut_version.py")
cv = importlib.util.module_from_spec(spec); spec.loader.exec_module(cv)
for rel, order in cv.UPCOMING.items():
    entries = sorted(p for p in Path(rel).glob("*.md") if p.name != cv.GUIDANCE)
    print(f"===== {rel}\n# v4.0.0\n\n" + cv.combine([p.read_text() for p in entries], order))
PY
```

saved to `<scratchpad>/notes-preview.md`, and reads it against every statement
of 6.2 (e), one line each in the round: `## Upgrading` first; the migration
guide linked; automation kept below 4; the `tcw project` group and the four
3.x commands it replaces, each with its replacement; the clone bound (beside
the project, never at or above home, never in a hidden folder below it); the
`.git`-only refusal; a project already on the machine never fetched again and
a manifest fetched during the run that would place it elsewhere stopping the
run; a `ref` naming nothing failing; the pinned install; the `3.x` branch. At
`bb6adc7e` the TCW-115 entry's "never fetched again … stops the run" sentence
is still missing (spec 3.6; the nearest is "It never overwrites anything");
whatever the preview still lacks is added to TCW-118's release-notes entry,
never to another item's file.

**Files:** `docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md` (only if
a statement is missing); `implement/round-1.md`.

**Proves it:** every 6.2 (e) statement found in the preview (checked again on
the shipped file by criterion 29).

### Step 9 — the user-wide personal file (3.7), and the documentation entries

**Who:** an agent.

**Does:** `ls "${XDG_CONFIG_HOME:-$HOME/.config}/tcw/config.yaml"
~/.config/tcw/config.yaml`; if either exists and `grep -n not_tags` finds a
line, it is changed to 4.0's spelling, the line TCW-116's report A5 names, and
the change recorded. On 2026-10-24 neither exists. Then runs the
`documentation-sync` skill over Phase A's changes (the "Documentation Sync"
block below) and makes what it finds.

**Files:** none for 3.7 when the file is absent; the documentation entries'
files; `implement/round-1.md`.

**Proves it:** criterion 11; the Documentation Sync block's every row
answered.

### Step 10 — CI on `v4`, before the merge (3.10)

**Who:** the dispatching session (the user allowed pushing `v4`).

**Does,** with `v4` not moving and every Phase A commit in:

```sh
git -C /Users/brian/Projects/TCW/.claude/worktrees/v4 push origin v4
test "$(git ls-remote origin refs/heads/v4 | cut -f1)" = "$(git rev-parse v4)"
gh pr list --head v4 --json number,labels,state     # item 2: expected []
gh workflow run test.yml --ref v4
gh run list --workflow test.yml --branch v4 --event workflow_dispatch --limit 1
gh run watch <id> --exit-status
gh run view <id> --json headSha,jobs
```

**Files:** `implement/round-1.md` gets `gh run view`'s output.

**Proves it:** criterion 46: `headSha` is `v4`'s tip, and `pytest (3.11)`,
`pytest (3.14)` and `web-build` each have conclusion `success`. A failure is
fixed on `v4` (an agent, in the child's area, test first) and the step runs
again on the new commit.

### Step 11 — the user is told (3.8)

**Who:** the dispatching session, to the user.

**Does:** one message saying: from Step 12 (rule 4.0) until Step 26 (5.7), no
`tcw` command runs in this repository, by any agent or session, and the user
is asked to run none here or on another machine; that window holds gates 1
and 2 and lasts as long as their review and test of 4.0 takes; the shared
`tcw` on this machine stays 3.0.2 until gate 2's go; from 5.5 until the user
migrates their setups (8.2), this machine's `tcw` is 4.0 and refuses every 3.x
project on it except to migrate it; and the window then also holds gate 3.

**Files:** the time and recipients go in the round (criterion 12).

## Phase B: merge, migrate the files, accept (Design 4; TCW-116 Design 9.3 steps 0-4)

Rule 4.0 holds from Step 12 to Step 26: no `tcw` command anywhere in this
repository, TCW-118's own included. Every step from here to Step 26 records
what it did in the release folder; the dispatching session writes those
records into `implement/round-1.md` after Step 26. Let `C` be the merge clone's
folder, `~/tcw-4.0-merge` (outside `/Users/brian/Projects/TCW`).

### Step 12 — step 0: stop every `tcw`, record M0 and V (4.0)

**Who:** the dispatching session.

**Does:** sends every agent and session working in this repository a message
to run no `tcw` command until it says otherwise, and asks the user the same,
recording each recipient and the time; stops every agent that has finished.
Then:

```sh
mkdir -p ~/.tcw-4.0-release
git -C /Users/brian/Projects/TCW fetch origin
git -C /Users/brian/Projects/TCW status --porcelain --branch   # "## main...origin/main" and nothing else
M0=$(git -C /Users/brian/Projects/TCW rev-parse origin/main)
test "$(git -C /Users/brian/Projects/TCW rev-parse main)" = "$M0" ||
  git -C /Users/brian/Projects/TCW merge --ff-only origin/main   # Decided 6
V=$(git -C /Users/brian/Projects/TCW rev-parse v4)
printf 'M0 %s %s\nV %s %s\n' "$M0" "$(date -u +%FT%TZ)" "$V" "$(date -u +%FT%TZ)" >> ~/.tcw-4.0-release/refs.txt
git rev-list --count "$M0..$V"; git rev-list --count "$V..$M0"
```

and writes `ci-suite.sh`, `way-back.py` and `private-names.txt` (Tools), and
an empty `gates.md`. `V` differs from Step 10's run commit only in files under
`docs/work/TCW-118-tcw-4-0-release/` (`git diff --name-only <run commit> $V`);
otherwise Step 10 runs again first.

**Files:** the release folder only.

**Proves it:** criterion 12 (the messages and `refs.txt`); criterion 46's last
clause. A primary checkout that is not on `main` or has changes stops the
release here: the dispatching session brings it to the user.

### Step 13 — step 1: the merge clone (4.1)

**Who:** an agent.

```sh
git clone /Users/brian/Projects/TCW ~/tcw-4.0-merge
cd ~/tcw-4.0-merge
git remote set-url --push origin no-push            # Decided 5
git checkout -b release-4.0.0 "$M0"
git merge --no-ff "$V" -m "Merge v4 into main: TCW 4.0"
python3.14 -m venv .venv && .venv/bin/pip install -q -e '.[dev]'
```

A conflict (a 3.x patch on `main` after the split; none today, `git rev-list
--count v4..main` printed 0) is resolved by applying the patch's intent to the
4.0 code, and the resolution reviewed as Step 6 reviews, before Step 14.

**Proves it:** criterion 13: `test -d .git`; the folder is outside
`/Users/brian/Projects/TCW`; `git rev-parse release-4.0.0^1` is M0 and
`release-4.0.0^2` is V.

### Step 14 — step 2: the dry run, then the files (4.2)

**Who:** an agent, with the Jira credentials (`source ~/.bashrc` for
`TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY`). The dry run only reads the board.

```sh
cd ~/tcw-4.0-merge
{ date -u; .venv/bin/tcw migrate --dry-run; echo "exit $?"; } > ~/.tcw-4.0-release/tcw116-dry-run.txt 2>&1
grep -o 'would edit [A-Z0-9]*-[0-9]*' ~/.tcw-4.0-release/tcw116-dry-run.txt | sort -u | wc -l
grep -o 'would edit [A-Z0-9]*-[0-9]*' ~/.tcw-4.0-release/tcw116-dry-run.txt | grep -v 'would edit TCW-[0-9]*$'  # nothing
env -u TCW_JIRA_EMAIL -u TCW_JIRA_API_KEY https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 \
  .venv/bin/tcw migrate --no-jira > ~/.tcw-4.0-release/no-jira.txt 2>&1; echo "exit $?" >> ~/.tcw-4.0-release/no-jira.txt
```

**Proves it:** criterion 14 (the dry run exited 0, every key `^TCW-[0-9]+$`,
the count recorded; the count is also what Decided 3 weighs against Jira's
rate limit); criterion 15 (`--no-jira` exited 0 and its summary says the
tickets were not converted).

### Step 15 — step 3: the files finished, the suite, validate (4.3) [after TCW-117]

**Who:** an agent, in `~/tcw-4.0-merge`.

- (a) `git rm -q tests/test_repo_config_pair.py`; delete the line
  `/tcw-config.local.yaml` from `.gitignore`.
- (b) delete `UNMIGRATED_RECORDS` and its comment from
  `tests/test_docs_describe_4_0.py`, with every use of it; run
  `.venv/bin/pytest tests/test_docs_describe_4_0.py`; count the hits; compare
  with Step 1's proof-2 count. A different count is explained in the record
  before anything is fixed.
- (c) fix every hit in `docs/taxonomy/` and `docs/capabilities/` by editing
  files (no `tcw` command), until that test passes.
- (d) `bash ~/.tcw-4.0-release/ci-suite.sh ~/tcw-4.0-merge >
  ~/.tcw-4.0-release/suite-4.3.txt 2>&1`, with no proxy setting.
- (e) `.venv/bin/tcw validate > ~/.tcw-4.0-release/validate-4.3.txt 2>&1`,
  exit 0.
- (f) `git diff "$M0" | grep -n -i -F -f ~/.tcw-4.0-release/private-names.txt`
  prints nothing, run after `git add -A` so new files are in the diff
  (`git diff --cached "$M0"`).

**Proves it:** criteria 16, 17 and 18.

### Step 16 — step 4: one migration commit, `main` fast-forwarded (4.4)

**Who:** an agent, in `~/tcw-4.0-merge`.

```sh
git add -A && git commit -qm "Migrate this repository to TCW 4.0 (tcw migrate --no-jira)"
git checkout -q main && git merge --ff-only release-4.0.0
A=$(git rev-parse main); printf 'A %s %s\n' "$A" "$(date -u +%FT%TZ)" >> ~/.tcw-4.0-release/refs.txt
git -C /Users/brian/Projects/TCW ls-remote origin refs/heads/main    # prints M0 (Decided 5)
```

**Proves it:** criterion 19: `main` is one commit past the merge commit
(`git rev-parse main^1^1` is M0 and `git rev-parse main^1^2` is V), and
GitHub's `main` is M0.

### Step 17 — the acceptance tarball, checked (4.5)

**Who:** an agent.

```sh
cd ~/tcw-4.0-merge && .venv/bin/pip install -q build && .venv/bin/python -m build
mkdir -p ~/.tcw-4.0-release/acceptance && cp dist/tcw_cli-4.0.0.tar.gz ~/.tcw-4.0-release/acceptance/
cd ~/.tcw-4.0-release/acceptance && shasum -a 256 tcw_cli-4.0.0.tar.gz > tcw_cli-4.0.0.tar.gz.sha256
python3.14 -m venv venv && venv/bin/pip install -q ./tcw_cli-4.0.0.tar.gz
```

then the commands of Step 32 (6.2 (f)) and Step 33 (6.2 (g)), with this
folder in place of the qa folder and the merge clone in place of `$Q/clone`, writing their output to
`~/.tcw-4.0-release/acceptance/results.txt`. Every scratch project is under
`~/.tcw-4.0-release/acceptance/`, with no Jira backend. A failure is a 4.0
defect, handled as Step 18's "a defect found".

**Proves it:** criterion 54.

### Step 18 — gate 1: the user accepts 4.0 (4.6)

**Who:** the dispatching session asks; **the user** answers.

**Does:** tells the user where the acceptance tarball, its digest and its
ready environment are (`~/.tcw-4.0-release/acceptance/`), that A is the
commit it was built from, and what Steps 6, 7, 10, 15 and 17 found; and says
how to test without touching anything outside this machine, in the words of
spec 4.6 (the skills with `claude --plugin-dir ~/tcw-4.0-merge` and the
acceptance `venv/bin` first on `PATH`; the environment's `tcw` by full path,
since `which -a tcw` lists two; a copy of a project, never the project
itself, migrated with `--no-jira` or pointed at the test Jira project; never
inside this repository). Then stops.

The answer is written to `~/.tcw-4.0-release/gates.md` as it is given, copied
to `docs/work/TCW-118-tcw-4-0-release/gates.md` in `~/tcw-4.0-merge` and
committed on its `main`, `TCW-118: gate 1, <accepted|declined|defect>`:

- **Accepted**, naming A: on to Step 19.
- **Declined:** the release stops; the clone and the release folder are kept
  until the user says otherwise; rule 4.0 is lifted and every agent and the
  user told; the decline is also committed to `gates.md` in the primary
  checkout's `main`; the items the user names go back to `implement` as they
  direct. TCW-118 stays at `implement`.
- **A defect found:** fixed on `v4` in the child's area by an agent briefed
  as Step 6 briefs, which runs no `tcw` command; then Step 10 on the new
  commit, a new merge clone from Step 13 (the old one deleted; V and A
  recorded again; the whole of `~/.tcw-4.0-release/gates.md` copied into the
  new clone's `gates.md`), Step 17, and gate 1 asked again.

**Proves it:** criterion 47.

## Phase C: live writes (Design 5; TCW-116 Design 9.3 steps 5-7)

### Step 19 — gate 2 asked (5.0)

**Who:** the dispatching session asks; **the user** answers.

**Does:** asks for one go covering, in order, Steps 20 and 21 on `TCWTEST`,
then Step 23 (4.0 installed as this machine's shared `tcw`, which refuses
every 3.x project on the machine) and Steps 24-25 (every ticket's `TCW Item`
on the live `TCW` board converted). It gives the user
`~/.tcw-4.0-release/tcw116-dry-run.txt`, what 5.6 will change (the count and
the keys), section 9's ways back, and says plainly that **TCW-116's way back
for the tickets has never run against a live board**, which is why Step 21
rehearses it; and that whether an edit emails watchers is not known yet,
and Step 21 finds out (Decided 4).

The answer goes to both copies of `gates.md` and is committed on
`~/tcw-4.0-merge`'s `main`, `TCW-118: gate 2, <answer>`, before Step 20. A
decline, or a failure at Step 20 or 21, runs section 9's row "5.1-5.2"; a
failure at 5.5 runs row "5.5"; at 5.6-5.7, row "5.6-5.7". A failure at Step 20
or 21 is a 4.0 defect, fixed as Step 18's "a defect found", so gate 1 is asked
again before gate 2 is.

**Proves it:** criterion 52.

### Step 20 — the live Jira scenario (5.1) — gate 2

**Who:** an agent, under gate 2's go, or the user.

```sh
cd ~/tcw-4.0-merge && git log --format=%H "$A..main" -- . ':!docs' | wc -l   # 0: past A only in docs/
source ~/.bashrc
{ date -u; TCW_JIRA_LIVE=1 .venv/bin/pytest -s \
    tests/work/jira/test_jira_scenario.py::test_the_scenario_live; echo "exit $?"; } \
  > ~/.tcw-4.0-release/live-scenario.txt 2>&1
```

**Proves it:** criterion 48: `exit 0`, `1 passed` (not `skipped`), and the
printed `validate --remote exited 0`. It touches only `TCWTEST` and builds
its own project in pytest's scratch folder.

### Step 21 — the ticket conversion and its way back, rehearsed (5.2) — gate 2

**Who:** an agent, under gate 2's go.

**Before filing:** a read-only search of the `TCW` board for the issue types
its tickets use (`curl -s -u "$TCW_JIRA_EMAIL:$TCW_JIRA_API_KEY"
"<site>/rest/api/3/search/jql?jql=project%3DTCW&fields=issuetype&maxResults=100"`,
paging with `nextPageToken`, the site from `.tcw/tcw-config.yaml`'s
`work.jira.site` in the merge clone), keeping the distinct names (Decided 3).

**The rehearsal project,** in `~/.tcw-4.0-release/rehearsal/`:

```sh
cd ~/.tcw-4.0-release/rehearsal
python3.14 -m venv venv-3 && venv-3/bin/pip install -q tcw-cli==3.0.2
mkdir proj && cd proj && git init -q && git config user.email t@t && git config user.name t
../venv-3/bin/tcw init work --id tcw-rehearsal
```

then `work:` of its `tcw-config.yaml` replaced with the `LIVE` dictionary of
`tests/work/jira/test_jira_scenario.py:19-40` (as
`main:tests/work/projects.py:36-40` does), and committed. With 3.0.2:
`tcw validate --remote` (open item 3: the fields accepted); `tcw work new`
three items, "rehearsal one", "two" and "three"; `tcw work advance` on the
first. If the `TCW` board uses an issue type the three tickets do not have,
one ticket's type is changed to it in Jira, on `TCWTEST` only, so that every
type the board uses is edited by the migration.

**The conversion,** with the merge clone's 4.0 `tcw` by full path:

```sh
T4=~/tcw-4.0-merge/.venv/bin/tcw
{ date -u; $T4 migrate --dry-run; echo "exit $?"; } > ../rehearsal-dry-run.txt 2>&1
{ date -u; $T4 migrate; echo "exit $?"; } > ../rehearsal-step6.txt 2>&1
{ date -u; $T4 migrate --dry-run; echo "exit $?"; } > ../rehearsal-lag-0.txt 2>&1      # index lag, at once
sleep 60; { date -u; $T4 migrate --dry-run; echo "exit $?"; } > ../rehearsal-lag-60.txt 2>&1
```

Then ticket three's `TCW Item` is edited by hand in Jira to another value
(the check that the way back refuses it), and the way back runs:

```sh
~/tcw-4.0-merge/.venv/bin/python ~/.tcw-4.0-release/way-back.py . tcw-rehearsal .. 'rehearsal-step6*.txt' \
  > ../rehearsal-way-back.txt 2>&1
```

It must put back tickets one and two and leave out three, naming it under
"left out" and exiting 1. Ticket three's own value is then put back by hand.
Then the files' way back in `proj`, its own throwaway repository
(`git reset -q --hard HEAD && git clean -fdq`, which returns it to the 3.x
commit, since `tcw migrate` commits nothing), and 3.0.2's
`../venv-3/bin/tcw work list` lists all three items with no warning. The user, as a watcher of the three tickets, says
whether the edits sent them email. All three tickets are then moved to
`Won't Do` in Jira.

**Proves it:** criterion 53 for tickets one and two: both `TCW Item` values
converted by the migration, both back to the dry run's 3.x values after the
way back, 3.0.2's list clean, both in `Won't Do`. Ticket three's refusal, the
issue types edited, the emails, and the two lag files (whether the index
showed stale `would edit` lines at once, and after a minute) are recorded for
Decided 3 and 4. A failure stops the release (Step 19's rows).

### Step 22 — what the rehearsal found, told (Decided 4)

**Who:** the dispatching session; **the user** if emails were sent.

**Does:** if the edits emailed watchers, tells the user how many tickets Step
24 will edit and waits for their word before Step 23; their answer is added to
`gates.md` (both copies) and committed on `~/tcw-4.0-merge`'s `main`. If the
index lag showed stale lines, Step 25 waits at least as long as the lag the
rehearsal saw before its checks.

### Step 23 — step 5: this machine's `tcw` becomes 4.0 (5.5) — gate 2

**Who:** the dispatching session, under gate 2's go.

```sh
cd /Users/brian/Projects/TCW
git status --porcelain --branch                         # on main, no changes, at M0
py=$(head -1 "$(pyenv which tcw)" | sed 's/^#!//')    # the lifecycle tcw's own Python
{ date -u; git pull --ff-only ~/tcw-4.0-merge main && "$py" -m pip install -q -e '.[dev]' && tcw --version; } \
  > ~/.tcw-4.0-release/install.txt 2>&1
test "$(git rev-parse main)" = "$(git -C ~/tcw-4.0-merge rev-parse main)"
```

**Proves it:** criterion 20: `tcw 4.0.0` in `install.txt`, and the two
`main`s equal. An untracked root `tcw-config.local.yaml`, if any, is
converted at Step 24.

### Step 24 — step 6: the live board converted (5.6) — gate 2

**Who:** the dispatching session or an agent, under gate 2's go, after Steps
20 and 21 passed (and Step 22's word, if asked).

```sh
cd /Users/brian/Projects/TCW && source ~/.bashrc
{ date -u; tcw migrate; echo "exit $?"; } > ~/.tcw-4.0-release/tcw116-step6.txt 2>&1
```

A run that stops partway is run again, each run saved as its own file
(`tcw116-step6-2.txt`, `-3`, …), until one exits 0; it never repeats an edit.
Then the `C17` keys of all the runs are compared with the dry run's:

```sh
~/tcw-4.0-merge/.venv/bin/python - <<'PY'
from pathlib import Path
from tcw.migrate.jira import edited_tickets
d = Path.home() / ".tcw-4.0-release"
done = {k for k, _, _ in edited_tickets("\n".join(p.read_text() for p in sorted(d.glob("tcw116-step6*.txt"))))}
dry = {k for k, _, _ in edited_tickets((d / "tcw116-dry-run.txt").read_text().replace("would edit ", "edit "))}
print("only in step 6:", sorted(done - dry)); print("only in the dry run:", sorted(dry - done))
PY
```

Each key in only one is read, and its reason recorded, before Step 25.

**Proves it:** criterion 21.

### Step 25 — step 7: nothing left to migrate (5.7)

**Who:** the dispatching session.

```sh
cd /Users/brian/Projects/TCW
tcw migrate          # prints "nothing to migrate", exit 0
tcw validate --remote
tcw work list        # no warning about unconverted tickets
```

Each output saved to `~/.tcw-4.0-release/step7.txt`.

**Proves it:** criterion 22.

### Step 26 — rule 4.0 ends; the round written

**Who:** the dispatching session.

**Does:** tells every agent and the user that `tcw` may run again; writes the
records of Steps 12 to 25 into `implement/round-1.md` from the release
folder's files (counts only for anything about the user's setups), and
commits it on the primary checkout's `main`. TCW-118 is still at
`implement`; the 4.0 lifecycle `tcw` moves it to `review` (Step 27), and the
move's hook commits the folder.

## Review (Design 5.8)

### Step 27 — the review

**Who:** the dispatching session moves TCW-118 to `review` with the 4.0
lifecycle `tcw`; a `tcw:reviewer` agent assesses; the dispatching session
writes the round.

**Does:** follows `docs/lifecycle/review.md`: `bash
~/.tcw-4.0-release/ci-suite.sh <a fresh clone of the primary checkout's main>`
saved to `~/.tcw-4.0-release/suite-review.txt`; `tcw work docs` evaluated;
every criterion of Phases A to C checked against the round.

**Proves it:** criterion 23. Phase D starts only on an accepted verdict;
TCW-118 then moves to `qa`.

## Phase D: cut and check (Design 6)

In the primary checkout, on `main`. Let `Q` be the qa folder,
`~/.tcw-4.0-release/qa/`.

### Step 28 — the cut (6.1)

**Who:** an agent.

```sh
cd /Users/brian/Projects/TCW
git fetch --tags origin
test -z "$(git ls-remote --tags origin v4.0.0)"
python scripts/cut_version.py 4.0.0     # not `major` (3.2 (c)); do not follow its push advice (Decided 8)
git log -1 --format=%s                  # chore(release): cut v4.0.0
T=$(git rev-parse v4.0.0^{commit}); test "$T" = "$(git rev-parse HEAD)"
```

**Proves it:** criterion 24. Nothing is pushed.

### Step 29 — the suite on T, here (6.2 (a))

**Who:** an agent.

```sh
git clone -q /Users/brian/Projects/TCW "$Q/clone" && git -C "$Q/clone" checkout -q "$T"
bash ~/.tcw-4.0-release/ci-suite.sh "$Q/clone" python3.14 > "$Q/suite-T.txt" 2>&1
```

**Proves it:** criterion 25.

### Step 30 — CI on T, before the tag (6.2 (b))

**Who:** the dispatching session (pushing `v4` is allowed).

```sh
cd /Users/brian/Projects/TCW
R=$(git ls-remote origin refs/heads/v4 | cut -f1)
git merge-base --is-ancestor "$R" "$T"      # else stop and bring it to the user
gh pr list --head v4 --json number,labels,state
git push origin "$T:refs/heads/v4"
gh workflow run test.yml --ref v4
gh run list --workflow test.yml --branch v4 --event workflow_dispatch --limit 1
gh run watch <id> --exit-status; gh run view <id> --json headSha,jobs
```

**Proves it:** criterion 26: head commit T; `pytest (3.11)`, `pytest (3.14)`
and `web-build` all `success`; the ancestor check recorded in the qa
findings.

### Step 31 — validate, versions, notes (6.2 (c)-(e))

**Who:** an agent.

- (c) in the primary checkout at T: `tcw validate` and `tcw validate
  --remote`, exit 0 (criterion 27).
- (d) `grep -n '4.0.0'` of the five files of `CLAUDE.md` "Versioning";
  `python -c` over `.agents/plugins/marketplace.json` finds no `version` key
  at any depth; `v4.0.0` without `v` equals `tomllib`'s `project.version`
  (criterion 28).
- (e) each statement of 6.2 (e) checked on `docs/release-notes/v4.0.0.md`
  and `docs/changelogs/v4.0.0.md`, one line each in the qa record: both start
  `# v4.0.0`; both `upcoming/` folders hold only `README.md`; the first `##`
  is `## Upgrading`; the guide linked and `docs/migration-guide-3.X-to-4.0.0.md`
  present; automation below 4; the `tcw project` group and the four commands
  with their replacements; the four TCW-115 statements; the pinned install
  and the `3.x` branch. Then `git diff "$M0" "$T" | grep -n -i -F -f
  ~/.tcw-4.0-release/private-names.txt` prints nothing (criterion 29).

### Step 32 — the tarball in a clean environment (6.2 (f))

**Who:** an agent.

```sh
cd "$Q/clone" && python3.14 -m venv "$Q/build" && "$Q/build/bin/pip" install -q build && "$Q/build/bin/python" -m build
python3.14 -m venv "$Q/venv-4" && "$Q/venv-4/bin/pip" install -q "$Q/clone/dist/tcw_cli-4.0.0.tar.gz"
"$Q/venv-4/bin/tcw" --version                       # tcw 4.0.0
"$Q/venv-4/bin/tcw" --help | grep -E '^\s+(project|migrate)\b'
"$Q/venv-4/bin/python" -c "import tcw, pathlib; r = pathlib.Path(tcw.__file__).parent; \
  assert (r/'serve/dist/index.html').is_file() and any((r/'work/prompts').iterdir())"
mkdir "$Q/new" && cd "$Q/new" && git init -q && git config user.email t@t && git config user.name t
"$Q/venv-4/bin/tcw" project new --id demo && "$Q/venv-4/bin/tcw" work new "first item" \
  && "$Q/venv-4/bin/tcw" work list && "$Q/venv-4/bin/tcw" validate
python3.14 -m venv "$Q/venv-3" && "$Q/venv-3/bin/pip" install -q tcw-cli==3.0.2
mkdir "$Q/old" && cd "$Q/old" && git init -q && git config user.email t@t && git config user.name t
"$Q/venv-3/bin/tcw" init --id demo && "$Q/venv-3/bin/tcw" work new "first item"
cp tcw-config.yaml "$Q/old-3x-tcw-config.yaml" && git add -A && git commit -qm 3.x
"$Q/venv-4/bin/tcw" migrate --no-jira && "$Q/venv-4/bin/tcw" validate && "$Q/venv-4/bin/tcw" work list
```

All saved to `$Q/tarball.txt`.

**Proves it:** criterion 30: every command exits 0 with the output 6.2 (f)
states.

### Step 33 — success criterion 3 (6.2 (g))

**Who:** an agent.

```sh
"$Q/venv-4/bin/python" - "$Q" <<'PY'
import sys, yaml
from pathlib import Path
q = Path(sys.argv[1])
new = yaml.safe_load((q / "new/.tcw/tcw-config.yaml").read_text())
old = yaml.safe_load((q / "old-3x-tcw-config.yaml").read_text())
migrated = yaml.safe_load((q / "old/.tcw/tcw-config.yaml").read_text())
extra = set(new) - set(old) - {"tcw-version"}
print("4.0 keys not in 3.x:", sorted(extra)); assert not extra
rest = {k: v for k, v in migrated.items() if k != "tcw-version"}
print("migrated == 3.x plus tcw-version:", rest == old); assert rest == old and "tcw-version" in migrated
PY
```

Both files shown in the qa record. **Proves it:** criterion 31.

### Step 34 — the plugin from the checkout (6.2 (h))

**Who:** an agent.

```sh
cd "$Q" && PATH="$Q/venv-4/bin:$PATH" claude -p --plugin-dir "$Q/clone" \
  --output-format stream-json --verbose "Run tcw --version and report its output exactly." \
  > "$Q/plugin.jsonl"
"$Q/venv-4/bin/python" -c "import json,sys; e=[json.loads(l) for l in open('$Q/plugin.jsonl')]; \
  i=next(x for x in e if x.get('type')=='system' and x.get('subtype')=='init'); print(i.get('plugins'))"
PATH="$Q/venv-4/bin:$PATH" bash "$Q/clone/scripts/check_versions.sh" "$Q/clone"   # prints nothing
```

**Proves it:** criterion 32: one plugin, path `$Q/clone`, version `4.0.0`
(the fields `evals/run_evals.py:195-201` and `:261` read); the session's
answer holds `tcw 4.0.0`. If Claude Code's `init` event names those fields
differently, the step records the new names (spec Risks).

### Step 35 — a failed check (6.3)

**Who:** an agent for the fix; the dispatching session for the tag and push.

No tag is pushed. The fix is a new commit on `main` in the primary checkout
(in the child's area, briefed as Step 6), then `git tag -f v4.0.0 HEAD`, Step
30's fast-forward push of `v4` to the new T, and **every** check of Steps 29 to
34 again on the new T (criterion 33).

### Step 36 — gate 3 asked (6.4)

**Who:** the dispatching session asks; **the user** answers.

**Does:** gives Steps 29-34's results and `git diff --name-only "$A" "$T"`,
naming every file in it outside `docs/work/TCW-118-tcw-4-0-release/`,
`docs/changelogs/` and `docs/release-notes/` (a fix after gate 1, which the go
covers only if the user's words say so); says that a plugin which updates
itself gets 4.0 when `main` is pushed, pin or no pin, so only a user who kept
the plugin below 4.0 by their harness's way stays on 3.x; and that the one go
covers, with no wait between them, the tag's push, the upload's confirmation,
and at once the check of GitHub's `main` and the pushes of `3.x` and `main`,
plus later pushes to `main` touching only TCW-118's and TCW-99's folders.

The answer, naming T, is written to both copies of `gates.md` and committed on
the primary checkout's `main` (`TCW-118: gate 3, <answer>`) before Step 37. A
decline: nothing is pushed; section 9's row "6.1-6.4".

**Proves it:** criterion 50 (that the commit adding it is not an ancestor of
T and is an ancestor of `origin/main` after Step 39).

## Phase E: publish, under gate 3 (Design 7)

### Step 37 — the tag alone (7.1) — gate 3

**Who:** the dispatching session, after reading gate 3's entry naming this T.

```sh
cd /Users/brian/Projects/TCW
P=~/.tcw-4.0-release/pushes.txt
{ echo "before 7.1"; date -u; git ls-remote origin refs/heads/main; } >> $P
git push origin v4.0.0
{ echo "after 7.1"; date -u; git ls-remote origin refs/heads/main; } >> $P
```

Both `ls-remote` lines print M0 (criterion 34).

### Step 38 — the upload confirmed (7.2) — gate 3

```sh
gh run list --workflow release.yml --limit 1     # the run for v4.0.0
gh run watch <id> --exit-status; gh run view <id> --json jobs
curl -sf https://pypi.org/pypi/tcw-cli/4.0.0/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
pipx run --spec tcw-cli==4.0.0 tcw --version
```

**Proves it:** criteria 35 and 38. A failed run follows 7.4: a failed `test`
job stops for the user's decision (move the tag or cut 4.0.1); a `publish`
failure before upload is corrected and re-run under gate 3's go; a failure
after the upload ships the fix as 4.0.1 (criterion 37).

### Step 39 — `3.x` and `main`, at once (7.3) — gate 3

**Who:** the dispatching session, as soon as Step 38 passes, with no question
to the user.

```sh
{ echo "before 7.3"; date -u; git ls-remote origin refs/heads/main; } >> $P   # must be M0, else stop
test -z "$(git ls-remote origin refs/heads/3.x)"
git push origin "$M0:refs/heads/3.x"
git push origin main
git fetch origin && git merge-base --is-ancestor "$T" origin/main
git ls-remote origin refs/heads/3.x refs/heads/release-4.0.0   # 3.x at M0; no release-4.0.0
```

**Proves it:** criteria 34, 36 and 51.

## Phase F: after publication (Design 8)

### Step 40 — other checkouts (8.1)

**Who:** the dispatching session.

**Does:** for each line of `git worktree list` but the primary checkout: a
locked worktree is left alone and named to the user; one whose agents have
all been stopped is removed with `git worktree remove` (the `v4` worktree
among them), or brought to `main` and migrated with `tcw migrate` before any
other `tcw` command, if the user wants it kept. The merge clone
`~/tcw-4.0-merge` is deleted when the user says so (section 9 needs only the
release folder after Step 39).

**Proves it:** criterion 39.

### Step 41 — the user's setups handed over, on TCW-99 (8.2)

**Who:** the dispatching session.

**Does:** a comment on TCW-99 (`tcw work comment`) naming the three commands
(`tcw migrate --dry-run`, `tcw migrate`, `tcw validate`, with 4.0.0) and what
each setup's record must hold (the dry run's counts, the three exit codes,
and either that nothing was fixed by hand or the work item filed for what
was), naming neither setup. TCW-118 does not wait for those records.

**Proves it:** criterion 40.

### Step 42 — GitHub issue #24 (8.3)

**Who:** the dispatching session drafts; **the user** approves the exact text;
then the dispatching session posts and closes.

**Does:** after Step 38, a reply naming 4.0.0 and what changed (TCW-113
Design 7.1: the `audit-backlog` procedure covers a project's family), shown
to the user in full; only after the user approves that exact text, `gh issue
comment 24 --body-file <the approved text>` and `gh issue close 24`.

**Proves it:** criterion 41: the approval and the text in the qa record.

### Step 43 — completing (8.4)

**Who:** the dispatching session.

**Does:** the qa findings, as a comment on TCW-118's ticket, giving every
criterion of Phases D to F with its evidence and pointing to `gates.md` for
the goes, after filing, with `tcw work new` and the evidence of "The follow-ups", the
25 new items listed there and the spec's two follow-ups (the Ctrl-C item is
F:32's), and naming their keys;
a comment on TCW-99 giving success criteria 1 (Step 7's output) and 3 (Step
33's comparison) with their evidence; then `tcw work advance` to
`completed`, which runs `tcw validate`. **TCW-99 is never moved by this
item**; its stage is read before and after and is the same.

**Proves it:** criterion 42.

## Documentation Sync

Run with the `documentation-sync` skill at Step 9, over Phase A's changes;
the release's later steps change no documented behaviour.

| Entry | Fires? | What this item does |
| --- | --- | --- |
| `README.md` [Public-API] | yes | Step 4: the session-start install takes the CLI of the plugin's own version (`:77-86`, as TCW-117 leaves it). |
| `docs/guide/jira.md` [Jira-Change] | no | No `tcw work` command's effect on a ticket changes; the conversion is TCW-116's and its guide entry is TCW-117's. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | checked | No guide describes the plugin's install; Step 9 greps `docs/guide/` for `pipx` and `tcw-cli` and corrects any line saying the install floats. `docs/releasing.md` (Step 3) is contributor documentation, not a guide, and is updated anyway (criterion 6). |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Step 5 (and Steps 2, 8): `TCW-118-tcw-4-0-release.md`. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Steps 2 and 5: `TCW-118-tcw-4-0-release.md`. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | checked | No component's CLI changes. The `setup` skill's reference `install.md` changes (Step 4); `skills/setup/SKILL.md` is grepped for "newest" and `pipx upgrade` and corrected if either is there. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No configuration key is added, removed or changes meaning. |
| `docs/use-cases.md` [Project-Setup-Change] | checked | S-9 (upgrades) gains, if TCW-117 has not written it, one requirement: the plugin installs the CLI of its own version, citing `scripts/session_bootstrap.sh`. Known gaps are TCW-117's; Step 7 only confirms them. |

The two capability records (Step 4) are the item's declared record changes,
not a documentation entry.

## Verification the tests cannot do

- **The harness hold-back instructions** (open item 1) are checked by the QA
  plan's scenario 7 (b) after publication, in each harness, on a scratch
  machine profile: install the plugin held at 3.0.2 by the way the notes
  give, start a session, and see `tcw 3.0.2` and no install of 4.0.
- **The live scenario, the rehearsal and the board's conversion** (Steps 20,
  21, 24) are the real Jira site; the suite cannot do them. Their pass rules
  are in the steps.
- **Whether a failed pinned install keeps the old CLI** depends on pipx; this
  machine's 1.17.2 resolves first (spec 3.9 (b)); older releases are not
  checked (spec Risks).
- **The plugin from the checkout** (Step 34) is a live Claude Code session;
  Codex and Pi are not run live (spec Decision 11).
- **The private-name search** depends on `private-names.txt` being complete,
  which only the maintainer's notes can say.

## Self-review against the spec

Every criterion and the step that meets it: 1 → 1; 2-5 → 3; 6 → 3; 7 → 5;
8 → 6; 9, 49 → 7; 10 → 1; 11 → 9; 43-45 → 4; 46 → 10, 12; 12 → 11, 12; 13 →
13; 14, 15 → 14; 16-18 → 15; 19 → 16; 54 → 17; 47 → 18; 52 → 19; 48 → 20; 53 →
21; 20 → 23; 21 → 24; 22 → 25; 23 → 27; 24 → 28; 25 → 29; 26 → 30; 27-29 → 31;
30 → 32; 31 → 33; 32 → 34; 33 → 35; 50 → 36; 34 → 37, 39; 35, 37, 38 → 38; 36,
51 → 39; 39 → 40; 40 → 41; 41 → 42; 42 → 43. Every step traces to a Design rule
or to a decision above (Step 2: Decided 1; Step 22: Decided 4; Step 26:
Design 2.2). No step repeats another: 4.5 and 6.2 (f)-(g) share their
commands by reference (Step 17 runs Steps 32 and 33's).

The gates are kept exactly: Steps 20, 21, 23, 24 read gate 2's entry first;
Steps 37-39 read gate 3's; nothing before Step 18 leaves the machine but
Step 10's push of `v4`; Step 30 pushes only `v4`; Step 14's dry run and Step
21's issue-type search only read; Step 41 and 43 comment on TCW-99 and never
move it; Step 42 posts only approved text.

## Spec issues found while planning

1. **The ticket's notes from TCW-116 (20:00, 20:47) postdate the spec's last
   revision.** The spec's 5.2 does not name the issue types, the emails, the
   index lag or the hand-edited ticket; this plan adds them (Decided 3, 4)
   without changing 5.2's pass rule.
2. **The way-back snippet needs `getattr` for `restored` as well as
   `pending`** (Decided 2): an error raised by `settings` or `backend_for`
   carries neither.
3. **Inside the merge clone, `origin` is the primary checkout** (Decided 5),
   so the spec's `git ls-remote origin main` at 4.4 is run from the primary
   checkout. No rule changes.
4. **Line references that moved since `82cdb4f9`:** the unpinned-command
   assertions in `tests/test_session_bootstrap.py` are at `:198`, `:201`,
   `:215`, `:368` and `:386` (spec 3.9 (f) cites `:201`, `:215`); the spec
   says the plan re-finds them by their words, and Step 4 does.
