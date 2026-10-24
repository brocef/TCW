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
matching go is already written in `gates.md` and committed** (Design 10).
The dispatching session's own lifecycle moves and comments on TCW-118's
ticket are its work under the list above, not a write the gates cover. Each
step that needs a go names the gate in its "Who" line, and its first action is
the check `gate_go <gate> <commit>` (Tools), which stops the step unless the
latest answer the release folder's `gates.md` holds for that gate and commit
is the go, and a checkout's last commit holds that same `gates.md`. If it
stops, the step does not run. A block that undoes a live write (a way back)
starts with `gate_go <gate> <commit> way-back` instead, which needs the
user's word for the way back as the latest answer.

**`gate_go` cannot tell who wrote a line.** It checks that a line of the
fixed form is there and committed, nothing more: anyone able to write the
file could write a go. The protection is the rule that **only the
dispatching session writes `gates.md`**, in both copies, and only to record
an answer the user has just given, with the user's words quoted exactly
beneath the line. No agent writes, edits or commits `gates.md`; an agent
that finds it needs a go it does not have stops and says so.

**Paths.** `~` is the user's home folder. The primary checkout is
`~/Projects/TCW`; the `v4` worktree is `~/Projects/TCW/.claude/worktrees/v4`;
the merge clone is `~/tcw-4.0-merge`; the release folder is
`~/.tcw-4.0-release`.

## Which `tcw` runs what

- **The lifecycle `tcw`** is the bare `tcw` first on this machine's `PATH`.
  `which -a tcw` lists `~/.pyenv/shims/tcw` first and
  `~/.local/bin/tcw` second; the first is the primary checkout's
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
5. **The merge clone cannot push to GitHub.** `git clone ~/Projects/TCW`
   makes the primary checkout the clone's `origin`, so a `git ls-remote origin`
   run inside the clone reads the primary checkout, not GitHub. Every check
   of GitHub's refs in phases B and C is therefore run as
   `git -C ~/Projects/TCW ls-remote origin …`, and the clone's push
   address is set to an invalid one at once (`git remote set-url --push origin
   no-push`), so no push from it can land anywhere.
6. **M0 must be the primary checkout's `main`.** The clone copies the
   primary checkout's branches; GitHub's `main` reaches it only through the
   primary checkout's own `main`. Step 12 therefore checks that
   `git -C ~/Projects/TCW rev-parse main` equals M0 (after
   `git fetch origin`) and that the primary checkout is on `main` with no
   changes, which 5.5 needs anyway; if `main` is behind, it is brought to M0
   with `git -C ~/Projects/TCW merge --ff-only origin/main` before
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
repository (spec Terms). Step 9a makes the folder, `load.sh` and
`ci-suite.sh`; Step 12 makes the rest. None is committed.

**How every shell block from Step 9a on is run.** Values do not survive from
one shell to the next, and an agent started for a later step has none of an
earlier step's variables. So each block below is written to a file in the
release folder (`~/.tcw-4.0-release/step-<n>.sh`) and run as one
`bash <file>`, its output saved where the step says; its first line sources
`load.sh`, naming the values it uses, and every value a later step needs is
written to `refs.txt` with `record` before the block ends. A block that
must run for minutes (the suite, the board's conversion) is run in the
background with its output going to its file.

**`refs.txt`**: one line per value, `<name> <40-character commit hash> <date
-u>`: `M0`, `V` (Step 12), `CI` (Steps 10 and 30, the commit CI ran on), `A`
(Step 16) and `T` (Steps 28 and 35). A value recorded again (a defect at gate
1, a failed check at 6.3) is a new line, and the last line of each name is
the current value. Only `record` writes it.

**`load.sh [<name>…]`**, sourced (`. ~/.tcw-4.0-release/load.sh M0 T`) as the
first line of every block from Step 9a on. It turns on `set -euo pipefail`,
so a failing command stops the block; sets the fixed paths; defines the
helpers; and sets each named value from `refs.txt`, stopping the block when
that value is missing or is not a commit hash. With a value guaranteed to be
40 hexadecimal characters, no command below can receive it empty (an empty
`T` would turn Step 30's push into `:refs/heads/v4`, which deletes `v4` on
GitHub).

```sh
# Sourced, never run. TCW-118's release helpers (plan, "Tools").
set -euo pipefail
REL=~/.tcw-4.0-release; PRIMARY=~/Projects/TCW; C=~/tcw-4.0-merge
Q=$REL/qa; P=$REL/pushes.txt
stop() { echo "stop: $*" >&2; exit 1; }
is_hash() { [[ "$1" =~ ^[0-9a-f]{40}$ ]]; }
record() {   # record <name> <hash>: append a value to refs.txt
  is_hash "$2" || stop "record $1: '$2' is not a commit hash"
  printf '%s %s %s\n' "$1" "$2" "$(date -u +%FT%TZ)" >> "$REL/refs.txt"
}
value_of() {   # the last recorded hash of <name>, or a stop
  local v
  v=$(awk -v n="$1" '$1 == n { h = $2 } END { print h }' "$REL/refs.txt" 2>/dev/null || true)
  is_hash "$v" || stop "no commit hash recorded for $1 in $REL/refs.txt"
  printf '%s' "$v"
}
capture() {   # capture <file> <command…>: date, output and "exit <n>" into <file>
  local file=$1 rc=0; shift
  { date -u; "$@"; } > "$file" 2>&1 || rc=$?
  echo "exit $rc" >> "$file"
  return "$rc"
}
no_private_names() {   # <text on stdin> | no_private_names
  local names=$REL/private-names.txt rc=0
  [ -s "$names" ] || stop "$names is missing or empty; ask the user for the list"
  grep -n -i -F -f "$names" || rc=$?
  case $rc in
    1) return 0 ;;
    0) stop "a private project's name is in the text above" ;;
    *) stop "the private-name search itself failed" ;;
  esac
}
gate_go() {   # gate_go <gate> <commit> [<word>]: the latest answer is <word> (go), and committed
  local want=${3:-go} path=docs/work/TCW-118-tcw-4-0-release/gates.md last copy found=""
  last=$(grep -E "^gate $1: [a-z-]+ $2\$" "$REL/gates.md" | tail -n 1) || true
  [ "$last" = "gate $1: $want $2" ] ||
    stop "the latest gate $1 answer naming $2 in gates.md is '${last:-none}', not '$want'"
  for copy in "$PRIMARY" "$C"; do
    [ -d "$copy" ] || continue
    if git -C "$copy" cat-file -e "HEAD:$path" 2>/dev/null; then
      git -C "$copy" show "HEAD:$path" | cmp -s - "$copy/$path" ||
        stop "$copy's gates.md differs from its last commit"
      if git -C "$copy" show "HEAD:$path" | cmp -s - "$REL/gates.md"; then found=1; fi
    elif [ -e "$copy/$path" ]; then
      stop "$copy's gates.md is not committed"
    fi
  done
  [ -n "$found" ] || stop "no checkout's last commit holds gates.md exactly as $REL/gates.md"
}
dispatch_ci() {   # id=$(dispatch_ci <commit>): start test.yml on v4, print its run's id
  local since id i
  since=$(date -u -v-1M +%FT%TZ)          # a minute early, for clock difference
  gh workflow run test.yml --ref v4 >&2
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    sleep 10
    id=$(gh run list --workflow test.yml --branch v4 --event workflow_dispatch --limit 5 \
          --json databaseId,headSha,createdAt \
          --jq "map(select(.headSha == \"$1\" and .createdAt >= \"$since\"))[0].databaseId // empty")
    if [ -n "$id" ]; then echo "$id"; return 0; fi
  done
  stop "no workflow_dispatch run of test.yml on $1 appeared within two minutes"
}
retryable() {   # retryable <saved output>: the run stopped because Jira was unreachable or rate limiting
  grep -Eq 'could not reach the tracker|did not respond within|the connection to the tracker .* was lost|the tracker returned 5[0-9][0-9]|the tracker is rate limiting requests' "$1"
}
for name in "$@"; do
  [[ "$name" =~ ^[A-Z][A-Z0-9]*$ ]] || stop "load.sh: bad value name '$name'"
  printf -v "$name" '%s' "$(value_of "$name")"
  is_hash "${!name}" || stop "$name did not load"
done
```

`printf -v`, `[[ =~ ]]` and `${!name}` all work in the macOS system bash
(3.2). Inside `$( )` a `stop` ends only the substitution, which is why the
loop checks each value again after setting it.

**`gates.md`**: the master copy of every answer at every gate, written as it
is given (Design 10). Each entry starts with one line `gate <n>: <word>
<commit>`, where the commit is the full hash the answer names (gate 1 and
gate 2: A; gate 3: T) and the word is one of:

- `go`: the user's go; also a go given again, such as Step 22's answer to
  go ahead knowing about the emails;
- `declined` (gate 1, 2 or 3) or `defect` (gate 1): the user's answer at the
  gate;
- `stop`: the user's word, at any point after a go, that the live writes stop
  (Step 22's answer not to go ahead, or Step 24's answer not to run the way
  back);
- `way-back`: the user's word that the way back of Step 24 runs.

Then the date and time (UTC), the user's words quoted exactly, each line
starting `> ` so that no quoted line can take the fixed form, and what
followed. `gate_go` reads only the latest fixed line for the gate and commit
it is given, so a `stop` or `way-back` after a go ends that go, and only a
new `go` line restores it. Its whole content is copied to
`docs/work/TCW-118-tcw-4-0-release/gates.md` by the commit that records each
answer, and `gate_go` requires a checkout whose last commit holds exactly the
release folder's copy, with its working copy unchanged.

**`issue-24.md`**, the reply to issue #24 (Step 42), and the line in
`gates.md` recording its approval, `issue 24: approved <sha-256 of the
file>`, which Step 42 checks before posting.

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
# pnpm here is corepack's shim under nvm. With the scratch HOME it would look
# for pnpm in an empty cache, download it and may ask before doing so, which
# hangs a run nobody answers: point it at this machine's own corepack cache,
# which holds the pnpm 10.14.0 that package.json names, and refuse any prompt.
corepack_home="${COREPACK_HOME:-$HOME/.cache/node/corepack}"
run() {   # run <path> <command>
  env -i PATH="$1" \
    HOME="$scratch/home" XDG_CONFIG_HOME="$scratch/config" \
    XDG_DATA_HOME="$scratch/data" XDG_STATE_HOME="$scratch/state" \
    XDG_CACHE_HOME="$scratch/cache" LANG=en_US.UTF-8 \
    COREPACK_HOME="$corepack_home" COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    bash -c "cd '$repo' && $2" < /dev/null
}
system="/usr/bin:/bin:/usr/sbin:/sbin"
echo "== $(date -u) in $repo, HEAD $(git -C "$repo" rev-parse HEAD)"
echo "== TCW_ variables inside the run (nothing below this line means none):"
run "$scratch/venv/bin:$system" 'env | grep "^TCW_" || true'
echo "== HOME inside the run: $(run "$system" 'echo $HOME')"
run "$scratch/venv/bin:$system" "pip install -q -e '.[dev]'"
run "$scratch/venv/bin:$system" "pytest"      # bare pytest, no Node on PATH, test.yml:66-76
run "$nodebin:$system" "pnpm --version && pnpm install --frozen-lockfile && pnpm check:build"   # test.yml:103-104
echo "== suite and web build passed"
```

`env -i` starts the run with no inherited variable at all, which unsets every
`TCW_` variable by construction; the script prints the proof criteria 17 and
25 ask for. The pytest run has no Node on its `PATH`, as CI's pytest job has
none (`test.yml:72-74`). **CI's web build runs Node 22** (`test.yml:101`);
this machine has only Node 24 releases under nvm (24.16 to 24.21), so a local
`pnpm check:build` that passes is not proof that CI's does, and only Steps 10
and 30's `web-build` job proves the build. Its output is saved by each
caller, with `2>&1`, to the file the step names. Step 9a proves the script
on `v4` before anything relies on it.

**`private-names.txt`**: the names of the user's private projects, from the
maintainer's own notes, one per line, written by the user or the dispatching
session at Step 12 and never committed (spec 4.3 (f); the repository is
public). The search is `no_private_names` (`load.sh`), fed a diff or a log:
it stops the block when a name is found, when the file is missing or empty,
or when the search itself fails. If the file cannot be written because nobody
has the list, the step stops and asks the user.

**`way-back.py <project root> <project id> <folder of saved outputs>
[--runs <pattern>] [--read]`**, the tickets' way back (Design 9; TCW-116's
Step 27 comment, with Decided 2). `--runs` is the file pattern of the saved
runs inside the folder, `tcw116-step6*.txt` when left out; `--read` says a
person has read every key found in only one of the runs and the dry run.
Options may come before or after the three names. It exits 0 when every
edited ticket was put back, 1 when Jira left one out, 3 when it stops before
editing anything, and 2 on a bad argument:

```python
"""Put back the 3.x TCW Item of every ticket a `tcw migrate` run edited.
Run with the 4.0 `tcw`'s Python (the merge clone's .venv/bin/python), before
3.0.2 is reinstalled (TCW-116 review round 1). Exits 0 when every edited
ticket was put back, 1 when Jira left one out, 3 when it stops before
editing anything, 2 on a bad argument (argparse's own exit)."""
import argparse
import sys
from pathlib import Path
from tcw.errors import TcwError
from tcw.migrate.jira import edited_tickets, restore_tickets, settings
from tcw.work.jira.client import JiraClient


def stop(message):
    print("stop:", message)
    sys.exit(3)


parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
parser.add_argument("project_id")
parser.add_argument("saved", type=Path)
parser.add_argument("--runs", default="tcw116-step6*.txt")
parser.add_argument("--read", action="store_true")
args = parser.parse_args()

runs = sorted(args.saved.glob(args.runs))
dry_files = sorted(args.saved.glob("*dry-run*.txt"))
if not runs:
    stop(f"no saved run matches {args.runs!r} in {args.saved}")
if len(dry_files) != 1:
    stop(f"{len(dry_files)} files match '*dry-run*.txt' in {args.saved}; exactly one is needed")
if dry_files[0] in runs:
    stop(f"{args.runs!r} matches the dry run {dry_files[0].name}")
done = edited_tickets("\n".join(p.read_text() for p in runs))
dry = {k for k, _, _ in edited_tickets(dry_files[0].read_text().replace("would edit ", "edit "))}
print("runs read:", [p.name for p in runs], "dry run:", dry_files[0].name)
print("edited:", len(done), "in the dry run:", len(dry))
if not done and dry:
    stop(f"the runs name no edited ticket, though the dry run lists {len(dry)}: "
         "a person reads the runs; nothing is put back")
only_one = sorted({k for k, _, _ in done} ^ dry)
print("in only one of the two:", only_one)
if only_one and not args.read:
    stop("a person reads these keys first, then runs this again with --read")
try:
    print("put back:", restore_tickets(done, JiraClient(settings(args.root)), args.root,
                                       args.project_id))
except TcwError as error:
    print("put back:", getattr(error, "restored", None))
    print("left out:", getattr(error, "pending", None), error)
    sys.exit(1)
```

Before revision 3 the script read its pattern as the fourth word on the
command line, so `--read` given there became the pattern, matched nothing,
and the script exited 0 having put nothing back (`restore_tickets` of an
empty list returns at once, `tcw/work/jira/backend.py:1387-1388`); a block
would then have reset the files with every ticket still at its 4.0 value.
Now an empty match, or no edited ticket where the dry run lists some, stops
with exit 3, and the blocks below treat every exit but the one they expect
as a stop.

It builds the Jira client only when it runs (TCW-116's 21:30 handoff); it is
written at Step 12 and run only by Step 21 (on `TCWTEST`) or by section 9's
row "5.6-5.7" as Step 24 runs it ("The way back from Step 24"), in both
cases while the project still holds the 4.0 files the migration wrote, and
before those files are reset. Step 21's run of it is its rehearsal.

## The follow-ups

Each entry of `followups.md` (cited by its line, `F:n`; `F:2` holds three
entries, 2a-2c) was checked against `v4` at `bb6adc7e` on 2026-10-24, by
reading the code and, where cheap, reproducing it with the worktree's 4.0
`tcw` in scratch projects; F:62 to F:66, added while TCW-117's skills were
written, were checked the same way at `7af7343e`. Counts: **24 fixes in
this item** (covering 27 entries, three pairs being one defect), **3
documentation already answered by TCW-117**, **25 new work items to file
after release** (covering 28 entries; F:61 is also in the documentation
group), **10 dropped**: 67 entries in all. A fix is a verified, small defect in 4.0's
behaviour; a defect that is older than 4.0 is fixed here only when it damages
data or is a line or two, and is otherwise a new item. Web-app changes are new
items: each needs the committed web build rebuilt (`pnpm check:build`), which
is not small.

### Fixes, made by Step 2, each test first

| # | Entry | What is wrong (evidence) | Change | Test |
| --- | --- | --- | --- | --- |
| 1 | F:1 | `parse_address("tcw://demo.foo/x")` says `'demo.foo/x' is not a full identifier`, dropping the prefix; the fall-through `return parse_full_id(rest)` at `tcw/ids.py:300` | catch `MalformedId` there and raise it again quoting the whole address | `tests/test_ids.py`, `test_ac2_each_refusal_names_its_rule`: case `("tcw://p1.foo/x", "tcw://p1.foo/x is not")` |
| 2 | F:2c | a store `path` of `TCW://p1.path/other` is read as a folder (`is not a directory: …/TCW:/p1.path/other`); the scheme test is case-sensitive wherever a store `path` or a `-C` target is told apart from a folder: `tcw/store/fs.py:3681` and `:3760` (both `startswith(SCHEME)`), `tcw/config.py:498`, `tcw/validate.py:301` and `:930`, `tcw/migrate/stores.py:195` (each `startswith("tcw://")`), and `tcw/cli.py:540` and `:558` (`tcw -C TCW://p1.path/` is looked for as a folder and refused with `no such folder`) | a function `has_scheme(text)` in `tcw/ids.py` (`text[:len(SCHEME)].casefold() == SCHEME`) used at those eight places, so a mixed-case scheme reaches `parse_address`, whose refusal `… is not a tcw:// address` (`tcw/ids.py:262-263`) is the message wanted. Left case-sensitive on purpose: the parsers themselves (`tcw/ids.py:248`, `:262`, `:361`, `:364`), which refuse the mixed case; `tcw/cli.py:66`, which already uses `casefold()`; and the Markdown link readers (`tcw/validate.py:53`'s `_LINK_RE`, `tcw/migrate/legacy.py:513`, `:519`, `:541`, `tcw/migrate/references.py:158`), which do not read `](TCW://…)` as a TCW link at all, as 3.x did not either; noted in the round, not changed | a validate test: the message says `is not a tcw:// address` and not `not a directory`; a `-C` test: `tcw -C TCW://p1.path/ …` exits 2 with `is not a tcw:// address` |
| 3 | F:3, F:18 | validate's message names the config file twice (`.tcw/tcw-config.yaml: taxonomy: /abs/…/.tcw/tcw-config.yaml: …`): `_run_check` formats `{e}` at `tcw/validate.py:372`, `:377`, `:381`, `:383` instead of `_config_message`, which `:309`, `:681`, `:776` use | use `_config_message(e, project_root)` at those four lines | `tests/test_legacy_store_config.py` near `:330`: the absolute path is absent from the message |
| 4 | F:5 | `tcw capabilities set cli/a --parent cli/a` exits 0, as does a two-capability loop; only validate reports it (`tcw/store/fs.py:1246`); new in 4.0 (no `--parent` on `main`) | in `set` (`tcw/store/fs.py:3214-3222`) refuse a parent that is the object itself or whose parent chain in this project returns to it | `tests/test_capabilities_federation.py`: a self-parent `set` fails and the state file is unchanged; the same for a loop of two |
| 5 | F:6, F:55 | the work store's reserved-name finding (`tcw/object_folders.py:375-377`) no longer points a 2.x store to its guide, which `main:tcw/work/fs_backend.py:537` did; a 2.x `docs/work/inbox/x/` is told to run `tcw migrate`, which cannot convert 2.x; A12 copies the message | append `MIGRATION_GUIDE` (`tcw/store/base.py:1194`) to that finding when the store is the work store, the only one a 2.x layout fills with stage folders; the taxonomy and capabilities stores' finding keeps its words, which TCW-117's guide quotes (`docs/guide/linking-and-validation.md:258`, `'resources' is reserved in the taxonomy store`), so that line stays true | validate on a store holding `docs/work/inbox/x/` names `docs/migration-guide-2.8-to-3.0.0.md` |
| 6 | F:10 | `_merge`'s scalar branch at `tcw/config.py:796-798` clears `origins` but not `places`; nothing shows it today | add `_clear(places, here)` there | a unit test: a later layer writing `work.tags` as a non-list leaves no `places` entry under `("work", "tags")` |
| 7 | F:11 | with both `TCW_WORK_STAGES_SPEC__APP` and `…_SPEC_PROMPT__APP` set, the note names both though only the second's prompt is used: a list that replaces the one below still appends to `written` (`tcw/config.py:768-769`, `:800-801`) | when the list has no `inherit: true` entry, set `written[here] = [origin]` | `personal_variables(("work","stages","spec","prompt")) == ["TCW_WORK_STAGES_SPEC_PROMPT__APP"]` |
| 8 | F:14 | `rm`'s referrer message names bare id-paths (`billing/c (Blocked by)`) while `reset`'s names full identifiers (`tcw/store/fs.py:3022`); no spec asks for the bare form | build the full identifier at `tcw/store/fs.py:3018`, and at `:2442`, `:2477` for taxonomy | `tests/test_taxonomy.py:416`, `:426` and `tests/test_capabilities_rm.py` expect `app.capabilities/billing/c (Blocked by)` |
| 9 | F:15 | `capabilities rm a` succeeds while `b` names `a` as its `parent`, leaving `dangling parent ref` (reproduced): `_referrers` (`tcw/store/fs.py:3012`) skips `parent`, which `_cap_ref_rows` (`:2745`) leaves out. Older than 4.0, but it damages the records | also check `meta.get("parent")`, adding `"<p> (parent)"` | `tests/test_capabilities_rm.py`: add `a`, add `b --parent a`; `rm a` is refused naming `billing/b (parent)`, and `a` is still on disk |
| 10 | F:16, F:44 | `rm` and `reset` leave an empty organising folder, which 4.0's validate then warns about (`holds no TCW object`, `tcw/object_folders.py:381`); `move` already cleans up with `remove_emptied` (`:536`) | call `remove_emptied(self.root, id_path)` after `_rm` at `tcw/store/fs.py:2412`, `:2973`, `:3067`, and add each folder it returns to `self.changed` as `("removed", self.root / rel)`, so the command's report names every folder it deleted, as `move` reports each one (`tcw/move.py:377-378`, `removed the empty folder …`) | rm the only capability under `billing/`, and reset one: the folder is gone, the command's output has a `removed` line for it, and validate prints no warning |
| 11 | F:23 | `tcw taxonomy rename bill PAY` says `docs/taxonomy/PAY already exists` when the folder is `pay` (reproduced) | at `tcw/move.py:228-229`, name the spelling `exact_child` returns | `tests/test_tree_move.py`: with `pay` present, the message names `docs/taxonomy/pay` |
| 12 | F:30 | with two fetched projects each with a bad manifest, the advice names only the first one's folder: `tcw/provision.py:556-562` takes one `_holding()` (`:200`) though the error lists every file (`tcw/store/project.py:726`) | name each distinct holder of `error.files` | `tests/test_project_provision.py`: two fetched projects with unreadable manifests; both folders appear |
| 13 | F:33 | test docstrings still describe `list --local`, a flag 4.0 replaced with `--scope` (`tcw taxonomy list --help`): `tests/test_tree_parent_missing.py:58-59`, `:98`, `:193`; `tests/test_overrides_by_path.py:417` | reword each to the `--scope` form the test runs | none: text only; the module passes unchanged |
| 14 | F:45 | the `unreviewed` line of `tcw capabilities drift` still says "upstream default", a 3.x term (`tcw/capabilities/cli.py:199-200`) | the line becomes `unreviewed: <id>: inherited, and its status is still the one it inherits; never ruled on here`; **[after TCW-117]** the guide line that quotes it, `docs/guide/taxonomy-and-capabilities.md:413` in TCW-117's work, is changed to the same words in the same commit | `tests/work/test_drift_work.py` asserts the new line; `grep -rn 'upstream default' tcw docs/guide skills` prints nothing |
| 15 | F:48 | `tcw project config --origin`'s help says it "prints even when something is wrong" (`tcw/project_cli.py:94-97`), but it follows TCW-109 Design 7.1, printing nothing when an inherited key is undecided or broken (`tcw/config_cli.py:295-301`) | the help says an undecided or broken inherited key still stops it | the existing help test, if one pins the text; else none (help text) |
| 16 | F:51 | a `capabilities.yaml` entry for a project the manifest places at a missing folder is an error with exit 1 (reproduced); TCW-110's spec (`:567`) says unresolved | at `tcw/validate.py:729-730` and `:819-820`, report `unresolved` when the problem is an `_UncheckedProblem` (made only from an `Unchecked` answer, `tcw/work/gates.py:169-174`). An entry naming a project ID nobody knows is a `ProjectGraphError`, answered `Invalid` (`tcw/work/gates.py:376-377`), so it stays an error with exit 1, as TCW-117's `skills/work/SKILL.md:138` and `docs/guide/cli.md:193` say (`check the spelling`) | the same setup gives an `unresolved:` line and exit 0; an entry naming an unknown project ID still exits 1 with `check the spelling` |
| 17 | F:53 | no test covers A14's other source name (`tcw/migrate/config.py:666-667`) | none: test only | `tests/migrate/test_migrate_manifests.py`: the path comes from an ancestor's file and A14 names `<relative>/tcw-config.yaml` |
| 18 | F:57 | a package migrated before its related projects: the after-run check lists no A12 and the summary does not say the check was cut short; `collect_findings` (`tcw/cli.py:274-278`) returns only the configuration findings and the graph problem, and `check_after` (`tcw/migrate/execute.py:356-360`) drops that as A8 predicted (read in code, not run) | `check_after` returns a flag when `registry.check()` is not empty; `_check_after` (`tcw/migrate/cli.py:103-109`) adds a report line: `check after the run stopped: a related project is still TCW 3.x; run 'tcw validate' once it is migrated` | `tests/migrate/test_migrate_monorepo.py`: migrate `api` first; the line is printed |
| 19 | F:58 | A8 in a workspace's run lists descendants before a parent: Design 2.10 and 6.2 of TCW-116 say parents first, but `still_3x_reports` (`tcw/migrate/config.py:1050-1070`) keeps the order found | order the non-ancestors by the family's predicted parent links | the order of A8's lines in a workspace run with a parent and a child both 3.x |
| 20 | F:59 | `1 tickets edited`, `1 files written`: `tcw/migrate/report.py:111-112` never uses the singular | singular for a count of 1; **[after TCW-117]** the migration guide's template of that line (`docs/migration-guide-3.X-to-4.0.0.md:160`, `changed: <n> files written, … <n> tickets edited`) gains "(`file` and `ticket` when the count is 1)"; its example at `:98` (counts 6 and 0) is unchanged | `counts([one write], 1, dry=False) == "changed: 1 file written, 0 moved, 0 deleted; 1 ticket edited"`; `tests/migrate/test_migrate_command.py:163-167` still passes (it asserts `0 tickets edited`, and is changed only if one of its cases writes exactly one file) |
| 21 | F:60 | a refused run's planned lines describe C12 and D7 for a B9-refused override: it is missing from `resolved` (`tcw/migrate/stores.py:539`), so `_plan_object` plans them | at `tcw/migrate/stores.py:319` and `:345`, also require `"overrides" not in data` | a refused B9 run lists no C12 or D7 for that file |
| 22 | F:63 | `tcw project new --work-path tcw://…` is refused with `init takes a path relative to the project` (`tcw/cli.py:67-70`); 4.0 has no `init` command (`tcw --help`), and `run_init` is reached only from `tcw project new` (`tcw/project_cli.py:73`, `tcw/cli.py:249-253`) | the message says `` `tcw project new` takes a path relative to the project `` | a test of `tcw project new work --work-path tcw://x.path/board`: exit 2, the message names `tcw project new` and not `init` |
| 23 | F:64 | a credential name set aside from an override variable is recorded with its variable (`tcw/config.py:674-676`, `Setting.variable`, `:191`) but printed from its file alone, which a variable has none of: `where = … if s.file is not None else ""` (`tcw/config_cli.py:241`), giving `(Jira credential names apply only in a Jira-mode project, )` | when `s.file` is None and `s.variable` is set, name `environment <variable>`, the form the values' own comments use (`# app, environment TCW_USER_NAME__APP`) | `tests/config/test_config_show.py` (beside `:93`): `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__APP` set in a project without Jira; the `# skipped:` line ends `environment TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__APP)` |
| 24 | F:66 | the advice `run tcw project new <axis> --id <id>` names `--id` even inside a project that has one, where `tcw project new <axis>` reads the ID from `.tcw/tcw-config.yaml` (`tcw/cli.py:72-76`). It is given at four places: `tcw/project_cli.py:177`, `tcw/move.py:96-97`, `_missing()` in `tcw/taxonomy/cli.py:29-31` and `_missing()` in `tcw/capabilities/cli.py:30-32`. Reproduced with `tcw taxonomy path` and `tcw taxonomy move x --top` in a project holding only a work store (`store_folder` is also what `tcw project info` reads, `tcw/project_cli.py:241`). A search of `v4` at `0cf6e97f` for `--id <` in `tcw/` finds three more, left as they are because each is given where no project ID exists: `NO_PROJECT` (`tcw/errors.py:13`, no project here at all), `tcw/cli.py:75` (a new project with no ID) and `tcw/store/project.py:947` (a manifest with no `id`) | one helper names `--id <id>` only when no project with an ID is found here, and otherwise says `run tcw project new <axis> in the project folder`; the four places use it | in a project with only a work store, the advice of `tcw taxonomy path`, `tcw taxonomy move`, a taxonomy command that needs the store (`tcw taxonomy list`) and a capabilities one (`tcw capabilities list`) names no `--id`; outside any project the move's still does |

Fixes 18 to 21 are in `tcw migrate`, TCW-116's area, and are made before
Step 15 runs it on this repository. Any fix found at implement to be larger
than its row says becomes a new item instead (Decided 1), and Step 2's
record says so.

**Where TCW-117's documents quote what a fix changes.** Each fix's changed
text was searched for in TCW-117's work (its worktree at `a10e1226`,
`docs/` and `skills/`, `README.md`, leaving out `docs/work/`, the changelogs
and the release notes) with `grep -rnF`. Two quotations change with a fix:
`docs/guide/taxonomy-and-capabilities.md:413` (fix 14) and
`docs/migration-guide-3.X-to-4.0.0.md:160` (fix 20). The others found stay
true and are not changed: `docs/guide/linking-and-validation.md:258` (fix
5, the taxonomy store's words, kept); `:260` and `docs/guide/work.md:161`
(fix 10: they name the `holds no TCW object` warning, whose words do not
change); `docs/guide/linking-and-validation.md:300` (fix 2: the same refusal
for another address); `docs/guide/configuration.md:174-177` (fix 15: it
already says what the corrected help says); `skills/configure/references/personal.md:117-120`
and `docs/capabilities/cli/override-configuration-from-the-environment/description.md:7`
(fix 7: the more specific variable wins, which the fix keeps; neither quotes
the note); `docs/migration-guide-3.X-to-4.0.0.md:98` (fix 20: counts of 6
and 0); `skills/work/SKILL.md:138` and `docs/guide/cli.md:193` (fix 16:
an unknown project ID still exits 1 with `check the spelling`; no fix
changes that exit code). Nothing quotes the texts of fixes 1, 3, 4, 8, 9,
11, 12, 18, 19, 21, 22, 23 or 24 (searched for `init takes`, `# skipped:`,
`Jira-mode project, )` and `<axis> --id`). Step 2 searches again for each fix's old text before committing it,
since TCW-117 may have added a quotation after `a10e1226`.

### Documentation already answered by TCW-117

- **F:22** (`skills/work/SKILL.md`'s description and its delegation bullet,
  `:96`, name filing into another project and `projects:`): TCW-117 Step 19 (a)
  rewrites both (P117:1250-1254).
- **F:61** (4.0 accepts an unknown top-level config key silently; 3.x did
  too, `tcw/config.py:436-451`): a deliberate non-goal of TCW-109 (its spec
  `:173-177`) kept as S-9's known gap "unknown top-level keys", which TCW-117
  keeps with "No item yet" (S117:1056). Whether such a key should be an error
  or a warning is a decision, so a new item for it is listed below as well.
- **F:65** (`tcw validate` in a parent does not report a child project's
  broken entry): not a defect. `tcw validate` is "one aggregate soundness
  pass over the current project" (`tcw/validate.py:1`, the same words on
  `main`, so 3.x did not check every project below either); of a child it
  checks only what TCW-108 Design 6.5 (b) and (d) give, whether the child
  can be found and names this project as a parent; a child's own files are
  read only when a lookup consults them (TCW-115 Design 1.8, as for F:31),
  and the child's own `tcw validate` reports them. The old skill's sentence
  was wrong for 3.x as well; TCW-117's setup skill already says it as
  above.

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
- **F:62**: by design: "A move or rename never changes any object's
  `parent`, as changing a parent never moves a folder" (TCW-114's spec
  `:702-703`, from TCW-111 Design 3.4); `tcw/move.py` changes only the
  folder and the object's own `id:` (`_own_id`, called at `:365`). A term's
  parent is set with `tcw taxonomy add --parent` and changed by editing its
  record, since `tcw taxonomy` has no `set` (`tcw taxonomy --help`). If a TCW-117 skill says `--top`
  clears the parent, that sentence is TCW-117's to correct; Step 6's slice
  6 checks it.

## Phase A: ready on `v4` (Design 3)

Steps 1 to 11 run in the `v4` worktree, `~/Projects/TCW/.claude/worktrees/v4`,
with its `.venv`. TCW-118 moves to `implement` (the dispatching session, the
3.0.2 lifecycle `tcw`) after Step 1 and before Step 2's first change to code
(Design 2.1). The order is Design 3's, with the release-preparation step
(Decided 1) placed after 3.1 and the suite script's proof (Step 9a) before
CI: 3.1, preparation, 3.2, 3.9, 3.3, 3.4, 3.5, 3.6, 3.7, the documentation
entries, the suite script proved, 3.10, 3.8. A fix made at Step 6 (the combined
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
`TCW-118: <what was fixed>`, with only the files the entry names, plus any
line of a guide, a skill, a capability record or the migration guide that
quotes the text the fix changes. Before each commit, `grep -rnF '<the old
text>' docs skills README.md` (leaving out `docs/work/`, `docs/changelogs/`
and `docs/release-notes/`) is run, and every line it prints is either changed
in that commit to match the new text or named in the round as still true.

**Files:** those each fix names in "The follow-ups", the quoting lines found
as above, and
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

### Step 5 — TCW-118's own entry files (3.3) [after TCW-117]

It links TCW-117's migration guide (`docs/migration-guide-3.X-to-4.0.0.md`,
P117:677), which does not exist on `v4` until TCW-117 lands; the step checks
`test -f docs/migration-guide-3.X-to-4.0.0.md` first and stops if it fails.

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
5. the release's own changes (Steps 2-4);
6. **[after TCW-117]** TCW-117's guides, skills, use cases and migration
   guide against the code as it stands after Step 2's fixes: every command,
   flag, message and exit code a guide or skill quotes (`docs/guide/`,
   `skills/`, `docs/migration-guide-3.X-to-4.0.0.md`, `README.md`) is run or
   found in the code, and the failure to look for is a quotation that one of
   Step 2's fixes made untrue, or that was untrue already.

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

### Step 9a — the suite script proved on `v4` (Decided 7)

**Who:** an agent. It runs no `tcw` command itself; the suite does, in a
scratch clone outside this repository.

**Does:** makes the release folder, writes `load.sh` and `ci-suite.sh`
exactly as in "Tools", and runs the suite once on a fresh clone of `v4`, so
that a script that hangs or fails for a reason of its own is found here and
not at 4.3 (d), inside rule 4.0's window:

The folder is made first (`mkdir -p ~/.tcw-4.0-release`) and the two files
written into it; then:

```sh
. ~/.tcw-4.0-release/load.sh
test ! -e "$REL/suite-proof" || stop "$REL/suite-proof exists from an earlier run; delete it first"
git clone -q --branch v4 "$PRIMARY" "$REL/suite-proof"
test "$(git -C "$REL/suite-proof" rev-parse HEAD)" = "$(git -C "$PRIMARY" rev-parse v4)" || stop "the clone is not at v4"
bash "$REL/ci-suite.sh" "$REL/suite-proof" > "$REL/suite-proof.txt" 2>&1 || stop "the suite failed: see suite-proof.txt"
grep -q '^== suite and web build passed$' "$REL/suite-proof.txt" || stop "the suite did not finish"
```

It is run in the background, and its output file is watched. **If pnpm
hangs**, that is, the file shows `pnpm --version` as the last command and
gains no line for ten minutes, the run is stopped and the cause is one of
corepack's: a prompt (which `COREPACK_ENABLE_DOWNLOAD_PROMPT=0` and the
`/dev/null` input should already refuse) or a download (the cache at
`COREPACK_HOME` lacks `v1/pnpm/10.14.0`; on 2026-10-24 it holds it). The
fixes, in order: confirm `ls "$HOME/.cache/node/corepack/v1/pnpm/10.14.0/bin/pnpm.cjs"`;
if it is missing, run `corepack install` once in the `v4` worktree (outside
the scratch run, with the real HOME), which fills the cache; if pnpm still
hangs, change the script's last `run` line to call the cached pnpm directly,
`node "$corepack_home/v1/pnpm/10.14.0/bin/pnpm.cjs"` in place of `pnpm`, and
record the change in the round. A failing test, not a hang, is a 4.0 defect
and is fixed on `v4` as Step 10 fixes one. The run's Node is this machine's
24, not CI's 22 ("Tools"); Step 10 is the proof of the web build. The clone
`suite-proof` is deleted once the run passes.

**Files:** the release folder only; `implement/round-1.md` gets the run's
first lines (the `TCW_` and `HOME` proof), its last line, and any change made
to the script.

**Proves it:** `ci-suite.sh` runs to its last line on `v4` with this
machine's HOME replaced, so 4.3 (d), 5.8 and 6.2 (a) rely on a script that
has run.

### Step 10 — CI on `v4`, before the merge (3.10)

**Who:** the dispatching session (the user allowed pushing `v4`).

**Does,** with `v4` not moving and every Phase A commit in:

```sh
. ~/.tcw-4.0-release/load.sh
W=$PRIMARY/.claude/worktrees/v4
git -C "$W" push origin v4
head=$(git -C "$W" rev-parse v4)
test "$(git -C "$W" ls-remote origin refs/heads/v4 | cut -f1)" = "$head" || stop "GitHub's v4 is not v4's tip"
gh pr list --head v4 --json number,labels,state     # item 2: [] expected; any pull request is named in the record
id=$(dispatch_ci "$head")
gh run watch "$id" --exit-status || stop "CI failed on $head"
gh run view "$id" --json headSha,jobs
record CI "$head"
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
folder, `~/tcw-4.0-merge` (outside `~/Projects/TCW`).

### Step 12 — step 0: stop every `tcw`, record M0 and V (4.0)

**Who:** the dispatching session.

**Does:** sends every agent and session working in this repository a message
to run no `tcw` command until it says otherwise, and asks the user the same,
recording each recipient and the time; stops every agent that has finished.
Then:

```sh
. ~/.tcw-4.0-release/load.sh CI
git -C "$PRIMARY" fetch origin
test "$(git -C "$PRIMARY" branch --show-current)" = main || stop "the primary checkout is not on main"
test -z "$(git -C "$PRIMARY" status --porcelain)" || stop "the primary checkout has changes"
m0=$(git -C "$PRIMARY" rev-parse origin/main)
if [ "$(git -C "$PRIMARY" rev-parse main)" != "$m0" ]; then          # Decided 6
  git -C "$PRIMARY" merge --ff-only origin/main || stop "main cannot be fast-forwarded to origin/main"
fi
test "$(git -C "$PRIMARY" rev-parse main)" = "$m0" || stop "main is not GitHub's main (it is ahead of it)"
record M0 "$m0"
record V "$(git -C "$PRIMARY" rev-parse v4)"
. ~/.tcw-4.0-release/load.sh M0 V CI                                  # read back: the records hold
changed=$(git -C "$PRIMARY" diff --name-only "$CI" "$V") || stop "cannot compare CI's commit with V"
if printf '%s\n' "$changed" | grep -v -e '^docs/work/TCW-118-tcw-4-0-release/' -e '^$'; then
  stop "V differs from the commit CI ran on outside TCW-118's folder: run Step 10 again"
fi
git -C "$PRIMARY" rev-list --count "$M0..$V"; git -C "$PRIMARY" rev-list --count "$V..$M0"
```

and writes `way-back.py` and `private-names.txt` (Tools), and an empty
`gates.md`.

**Files:** the release folder only.

**Proves it:** criterion 12 (the messages and `refs.txt`); criterion 46's last
clause. A primary checkout that is not on `main` or has changes stops the
release here: the dispatching session brings it to the user.

### Step 13 — step 1: the merge clone (4.1)

**Who:** an agent.

```sh
. ~/.tcw-4.0-release/load.sh M0 V
test ! -e "$C" || stop "$C already exists; an old merge clone is deleted first"
git clone -q "$PRIMARY" "$C"
cd "$C"
git remote set-url --push origin no-push            # Decided 5
git checkout -q -b release-4.0.0 "$M0"
git merge --no-ff "$V" -m "Merge v4 into main: TCW 4.0"
python3.14 -m venv .venv && .venv/bin/pip install -q -e '.[dev]'
test -d .git || stop "the merge clone has no .git folder"
case "$(pwd -P)/" in "$(cd "$PRIMARY" && pwd -P)/"*) stop "the merge clone is inside the primary checkout" ;; esac
test "$(git rev-parse release-4.0.0^1)" = "$M0" || stop "the merge's first parent is not M0"
test "$(git rev-parse release-4.0.0^2)" = "$V" || stop "the merge's second parent is not V"
```

A conflict (a 3.x patch on `main` after the split; none today, `git rev-list
--count v4..main` printed 0) stops the block at the merge. It is resolved by
applying the patch's intent to the 4.0 code, committed with the same message,
and the resolution reviewed as Step 6 reviews; then the block's lines after
the merge are run, and only then Step 14.

**Proves it:** criterion 13: the block's last four checks.

### Step 14 — step 2: the dry run, then the files (4.2)

**Who:** an agent, with the Jira credentials (`source ~/.bashrc` for
`TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY`). The dry run only reads the board.

```sh
. ~/.tcw-4.0-release/load.sh V
cd "$C"
test "$(git rev-parse release-4.0.0^2)" = "$V" || stop "the merge clone is not the merge of V"
set +eu; source ~/.bashrc; set -eu                   # ~/.bashrc is not written for set -eu
dry=$REL/tcw116-dry-run.txt
capture "$dry" .venv/bin/tcw migrate --dry-run || stop "the dry run failed: see $dry"
keys=$(grep -o 'would edit [A-Z0-9_]*-[0-9]*' "$dry" | sort -u) || stop "the dry run names no ticket to edit"
printf '%s\n' "$keys" | wc -l                        # the count, recorded
if printf '%s\n' "$keys" | grep -v 'would edit TCW-[0-9]*$'; then stop "the dry run would edit a ticket outside TCW"; fi
capture "$REL/no-jira.txt" env -u TCW_JIRA_EMAIL -u TCW_JIRA_API_KEY \
  https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 \
  .venv/bin/tcw migrate --no-jira || stop "the --no-jira run failed: see no-jira.txt"
```

A dry run naming no ticket at all stops here too: the `TCW` board holds 3.x
values, so a count of 0 means the run did not read the board, and it is
brought to the dispatching session.

**Proves it:** criterion 14 (the dry run exited 0, every key `^TCW-[0-9]+$`,
the count recorded; the count is also what Decided 3 weighs against Jira's
rate limit); criterion 15 (`--no-jira` exited 0 and its summary says the
tickets were not converted).

### Step 15 — step 3: the files finished, the suite, validate (4.3) [after TCW-117]

**Who:** an agent, in `~/tcw-4.0-merge`. Items (d) to (f) run as one
block that starts `. ~/.tcw-4.0-release/load.sh M0` and `cd "$C"`.

- (a) `git rm -q tests/test_repo_config_pair.py`; delete the line
  `/tcw-config.local.yaml` from `.gitignore`.
- (b) delete `UNMIGRATED_RECORDS` and its comment from
  `tests/test_docs_describe_4_0.py`, with every use of it; run
  `.venv/bin/pytest tests/test_docs_describe_4_0.py`; count the hits; compare
  with Step 1's proof-2 count. A different count is explained in the record
  before anything is fixed.
- (c) fix every hit in `docs/taxonomy/` and `docs/capabilities/` by editing
  files (no `tcw` command), until that test passes.
- (d) `bash "$REL/ci-suite.sh" "$C" > "$REL/suite-4.3.txt" 2>&1 || stop
  "the suite failed"`, with no proxy setting.
- (e) `capture "$REL/validate-4.3.txt" .venv/bin/tcw validate || stop
  "validate failed"`.
- (f) `git add -A && git diff --cached "$M0" | no_private_names`, after
  `git add -A` so new files are in the diff.

**Proves it:** criteria 16, 17 and 18.

### Step 16 — step 4: one migration commit, `main` fast-forwarded (4.4)

**Who:** an agent, in `~/tcw-4.0-merge`.

```sh
. ~/.tcw-4.0-release/load.sh M0 V
cd "$C"
git add -A && git commit -qm "Migrate this repository to TCW 4.0 (tcw migrate --no-jira)"
git checkout -q main && git merge --ff-only release-4.0.0
test "$(git rev-parse main^1^1)" = "$M0" || stop "main^1^1 is not M0"
test "$(git rev-parse main^1^2)" = "$V" || stop "main^1^2 is not V"
record A "$(git rev-parse main)"
. ~/.tcw-4.0-release/load.sh A                                        # read back
test "$(git -C "$PRIMARY" ls-remote origin refs/heads/main | cut -f1)" = "$M0" ||
  stop "GitHub's main is not M0"                                      # Decided 5
```

**Proves it:** criterion 19: the block's checks: `main` is one commit past
the merge commit, and GitHub's `main` is M0.

### Step 17 — the acceptance tarball, checked (4.5)

**Who:** an agent.

```sh
. ~/.tcw-4.0-release/load.sh A
cd "$C"
test "$(git rev-parse HEAD)" = "$A" || stop "the merge clone is not at A"
test -z "$(git status --porcelain)" || stop "the merge clone has changes"
.venv/bin/pip install -q build && .venv/bin/python -m build
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

The answer is written to `~/.tcw-4.0-release/gates.md` as it is given, as an
entry whose first line is `gate 1: go <A>`, `gate 1: declined <A>` or
`gate 1: defect <A>` with A's full hash ("Tools"), copied to
`docs/work/TCW-118-tcw-4-0-release/gates.md` in `~/tcw-4.0-merge` and
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

The answer goes to both copies of `gates.md`, as an entry whose first line
is `gate 2: go <A>` (or `declined`), and is committed on
`~/tcw-4.0-merge`'s `main`, `TCW-118: gate 2, <answer>`, before Step 20. A
decline, or a failure at Step 20 or 21, runs section 9's row "5.1-5.2"; a
failure at 5.5 runs row "5.5"; at 5.6-5.7, row "5.6-5.7". A failure at Step 20
or 21 is a 4.0 defect, fixed as Step 18's "a defect found", so gate 1 is asked
again before gate 2 is.

**Proves it:** criterion 52.

### Step 20 — the live Jira scenario (5.1) — gate 2

**Who:** an agent, under gate 2's go, or the user.

```sh
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"
cd "$C"
past=$(git log --format=%H "$A..main" -- . ':!docs') || stop "cannot read the commits past A"
test -z "$past" || stop "main has commits past A outside docs/"
set +eu; source ~/.bashrc; set -eu
out=$REL/live-scenario.txt
capture "$out" env TCW_JIRA_LIVE=1 .venv/bin/pytest -s \
  tests/work/jira/test_jira_scenario.py::test_the_scenario_live || stop "the live scenario failed: see $out"
grep -q '1 passed' "$out" || stop "the live test did not run (skipped?)"
grep -q 'validate --remote exited 0' "$out" || stop "validate --remote did not pass in the scenario"
```

**Proves it:** criterion 48: the block's checks, `exit 0`, `1 passed` (not
`skipped`), and the printed `validate --remote exited 0`. It touches only `TCWTEST` and builds
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
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"
mkdir "$REL/rehearsal" && cd "$REL/rehearsal"
python3.14 -m venv venv-3 && venv-3/bin/pip install -q tcw-cli==3.0.2
mkdir proj && cd proj && git init -q && git config user.email t@t && git config user.name t
../venv-3/bin/tcw init work --id tcw-rehearsal
```

then `work:` of its `tcw-config.yaml` replaced with the `LIVE` dictionary of
`tests/work/jira/test_jira_scenario.py:19-40` (as
`main:tests/work/projects.py:36-40` does), and committed. Then, with 3.0.2,
the filing on `TCWTEST` (open item 3: the fields accepted):

```sh
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"
cd "$REL/rehearsal/proj"
set +eu; source ~/.bashrc; set -eu
T3=$REL/rehearsal/venv-3/bin/tcw
"$T3" validate --remote
for n in one two three; do "$T3" work new "rehearsal $n"; done | tee "$REL/rehearsal/filed.txt"
```

then, as a second block with the same first four lines, `"$T3" work advance
<key>` with the first ticket's key, read from `filed.txt` and written in (as
Step 38 writes in its run id). If the `TCW` board uses an issue
type the three tickets do not have, one ticket's type is changed to it in
Jira, on `TCWTEST` only, so that every type the board uses is edited by the
migration. **Every edit made by hand in Jira in this step** (that type
change, ticket three's value below, ticket three's value put back, the moves
to `Won't Do`) is made only right after
`bash -c '. ~/.tcw-4.0-release/load.sh A; gate_go 2 "$A"'` has exited 0,
and only on `TCWTEST`.

**The conversion,** with the merge clone's 4.0 `tcw` by full path:

```sh
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"
cd "$REL/rehearsal/proj"
set +eu; source ~/.bashrc; set -eu
T4=$C/.venv/bin/tcw; R=$REL/rehearsal
capture "$R/rehearsal-dry-run.txt" "$T4" migrate --dry-run || stop "the rehearsal's dry run failed"
capture "$R/rehearsal-step6.txt" "$T4" migrate || stop "the rehearsal's conversion failed"
capture "$R/rehearsal-lag-0.txt" "$T4" migrate --dry-run || true      # index lag, at once
sleep 60; capture "$R/rehearsal-lag-60.txt" "$T4" migrate --dry-run || true
```

Then ticket three's `TCW Item` is edited by hand in Jira to another value
(the check that the way back refuses it), and the way back runs:

```sh
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"
cd "$REL/rehearsal/proj"
set +eu; source ~/.bashrc; set -eu
rc=0
"$C/.venv/bin/python" "$REL/way-back.py" . tcw-rehearsal "$REL/rehearsal" --runs 'rehearsal-step6*.txt' \
  > "$REL/rehearsal/rehearsal-way-back.txt" 2>&1 || rc=$?
test "$rc" -eq 1 || stop "the rehearsal's way back exited $rc, not 1 (ticket three should be left out)"
grep -q '^left out:' "$REL/rehearsal/rehearsal-way-back.txt" || stop "the way back names nothing left out"
```

The rehearsal's dry run and its run name the same three tickets, so no key
is in only one and `--read` is not needed; an exit of 3 (a stop before any
edit) fails the block's check like any exit but 1.

It must put back tickets one and two and leave out three, naming it under
"left out" and exiting 1; a person reads the file to confirm the two keys
under "put back" and the one under "left out". Ticket three's own value is then put back by hand.
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
`gates.md` (both copies) as an entry whose first line is `gate 2: go <A>`
(go ahead, knowing it) or `gate 2: stop <A>` (do not), and committed on
`~/tcw-4.0-merge`'s `main`. After a `stop`, every later `gate_go 2` stops,
so Steps 23 to 25 cannot run; the release waits for the user, and nothing
on the `TCW` board has been touched. If the
index lag showed stale lines, Step 25 waits at least as long as the lag the
rehearsal saw before its checks.

### Step 23 — step 5: this machine's `tcw` becomes 4.0 (5.5) — gate 2

**Who:** the dispatching session, under gate 2's go.

```sh
. ~/.tcw-4.0-release/load.sh M0 A
gate_go 2 "$A"
cd "$PRIMARY"
test "$(git branch --show-current)" = main || stop "the primary checkout is not on main"
test -z "$(git status --porcelain)" || stop "the primary checkout has changes"
test "$(git rev-parse main)" = "$M0" || stop "the primary checkout's main is not M0"
py=$(head -1 "$(pyenv which tcw)" | sed 's/^#!//')    # the lifecycle tcw's own Python
test -x "$py" || stop "cannot find the lifecycle tcw's Python"
capture "$REL/install.txt" bash -c "git pull -q --ff-only '$C' main && '$py' -m pip install -q -e '.[dev]' && tcw --version" ||
  stop "the install failed: see install.txt; run section 9's row 5.5"
grep -q '^tcw 4\.0\.0$' "$REL/install.txt" || stop "the shared tcw is not 4.0.0"
test "$(git rev-parse main)" = "$(git -C "$C" rev-parse main)" || stop "the two mains differ"
```

**Proves it:** criterion 20: the block's checks: `tcw 4.0.0` in
`install.txt`, and the two `main`s equal. An untracked root `tcw-config.local.yaml`, if any, is
converted at Step 24.

### Step 24 — step 6: the live board converted (5.6) — gate 2

**Who:** the dispatching session or an agent, under gate 2's go, after Steps
20 and 21 passed (and Step 22's word, if asked).

```sh
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"
cd "$PRIMARY"
tcw --version | grep -q '^tcw 4\.0\.0$' || stop "the shared tcw is not 4.0.0 (Step 23)"
set +eu; source ~/.bashrc; set -eu
n=1; f=$REL/tcw116-step6.txt
until capture "$f" tcw migrate; do
  retryable "$f" && [ "$n" -le 3 ] ||
    stop "run $n stopped for another reason, or a fourth run stopped: bring $f to the user"
  wait=$(sed -n 's/.*Retry after \([0-9]*\)s.*/\1/p' "$f" | tail -n 1)
  [ "${wait:-0}" -gt 300 ] || wait=300
  sleep "$wait"
  n=$((n + 1)); f=$REL/tcw116-step6-$n.txt
done
```

**The re-run limit.** A run that stops is run again only when its saved
output names Jira as unreachable or rate limiting, in the Jira client's own
words (`retryable` in `load.sh`: `could not reach the tracker`, `did not
respond within`, `the connection to the tracker … was lost`, `the tracker
returned 5…`, `the tracker is rate limiting requests`;
`tcw/work/jira/client.py:225-240`, `:558-568`). It is run again at most
three times after the first run (four runs in all, saved as
`tcw116-step6.txt` and `tcw116-step6-2.txt` to `-4.txt`), waiting five
minutes before each, or longer when the output says `Retry after <n>s`. A
run never repeats an edit, since a converted ticket is skipped. **Any other
stop, or a fourth run that stops, ends the re-runs:** the block stops, and
the dispatching session brings every saved output to the user, with the way
back below offered. Running the way back writes to the live board, so the
user decides whether it is run, under gate 2; nothing is run until they
answer, and their answer is added to both copies of `gates.md`, as an entry
whose first line is `gate 2: way-back <A>` (run it) or `gate 2: stop <A>`
(do not), and committed. The block runs in the background, since the waits
can take twenty minutes.

Then the `C17` keys of all the runs are compared with the dry run's:

```sh
. ~/.tcw-4.0-release/load.sh
"$C/.venv/bin/python" - "$REL" <<'PY'
import sys
from pathlib import Path
from tcw.migrate.jira import edited_tickets
d = Path(sys.argv[1])
done = {k for k, _, _ in edited_tickets("\n".join(p.read_text() for p in sorted(d.glob("tcw116-step6*.txt"))))}
dry = {k for k, _, _ in edited_tickets((d / "tcw116-dry-run.txt").read_text().replace("would edit ", "edit "))}
print("only in step 6:", sorted(done - dry)); print("only in the dry run:", sorted(dry - done))
PY
```

Each key in only one is read, and its reason recorded, before Step 25.

**Proves it:** criterion 21.

**The way back from Step 24** (section 9's row "5.6-5.7", run at 5.6 or 5.7,
or at 6.1-6.4 when the release is abandoned, and only on the user's word).
**The tickets first, then the files**, in the order Step 21 rehearses:

```sh
. ~/.tcw-4.0-release/load.sh M0 A
gate_go 2 "$A" way-back                    # the user's word for the way back is the latest answer
for arg in "$@"; do [ "$arg" = --read ] || stop "the way back takes only --read, not '$arg'"; done
cd "$PRIMARY"
set +eu; source ~/.bashrc; set -eu
# 1. The tickets, while the primary checkout still holds the 4.0 files the
#    migration wrote and the 4.0 install, as in the rehearsal.
"$C/.venv/bin/python" "$REL/way-back.py" "$PRIMARY" tcw "$REL" "$@" > "$REL/way-back.txt" 2>&1 ||
  stop "the tickets' way back stopped or left tickets out: see way-back.txt, and bring it to the user"
grep -q '^put back: \[' "$REL/way-back.txt" || stop "way-back.txt names nothing put back"
# 2. Then the files, as for 5.5.
git reset --keep "$M0"
py=$(head -1 "$(pyenv which tcw)" | sed 's/^#!//')
"$py" -m pip install -q -e '.[dev]'
tcw --version | grep -q '^tcw 3\.0\.2$' || stop "the shared tcw is not 3.0.2 again"
```

The block is saved as `~/.tcw-4.0-release/way-back.sh` and run as `bash
~/.tcw-4.0-release/way-back.sh`, or `bash ~/.tcw-4.0-release/way-back.sh
--read` once a person has read the keys found in only one file; `load.sh`,
sourced with names, leaves the block's own `--read` in place for the loop
and the script. `way-back.py` reads the runs as `tcw116-step6*.txt` and the
dry run as the one `*dry-run*.txt` file in the release folder
(`tcw116-dry-run.txt`; the rehearsal's files are in `rehearsal/`, which the
search does not enter). It keeps its `getattr` reads of `restored` and
`pending` (Decided 2). Any exit but 0 stops the block before the files are
touched: 3 when no run is found, when the runs name no edited ticket though
the dry run lists some, or when a key is in only one of the two files and
`--read` was not given; 1 when Jira left a ticket out. Why this order: it is the order the rehearsal
proves; the script must run with the 4.0 code (its own docstring); and a
stop partway leaves the primary checkout exactly as it was before the way
back began, so the way back can be run again from the same state once the
cause is known (it edits only a ticket still holding the 4.0 value).
Resetting the files first would be likely to
work as well, since `settings(root)` reads the root `tcw-config.yaml` of a
3.x layout when it is present (`own_jira_layers`,
`tcw/migrate/legacy.py:355-370`), but that order is never rehearsed. The
spec's row lists the files before the tickets (Spec issues, 5).

### Step 25 — step 7: nothing left to migrate (5.7)

**Who:** the dispatching session.

```sh
. ~/.tcw-4.0-release/load.sh A
gate_go 2 "$A"                              # a real tcw migrate, which would edit any ticket left
cd "$PRIMARY"
set +eu; source ~/.bashrc; set -eu
capture "$REL/step7-migrate.txt" tcw migrate || stop "tcw migrate failed"
grep -q 'nothing to migrate' "$REL/step7-migrate.txt" || stop "something is still to migrate"
capture "$REL/step7-validate.txt" tcw validate --remote || stop "validate --remote failed"
capture "$REL/step7-list.txt" tcw work list || stop "work list failed"
```

**Proves it:** criterion 22: the checks, and `step7-list.txt` read for any
warning about tickets not converted (whose words the plan cannot know in
advance, so a person reads it).

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

In the primary checkout, on `main`. `Q` is the qa folder,
`~/.tcw-4.0-release/qa/`, set by `load.sh`. Every block from Step 29 on
starts `. ~/.tcw-4.0-release/load.sh T` (with `M0` or `A` added where it
uses them).

### Step 28 — the cut (6.1)

**Who:** an agent.

```sh
. ~/.tcw-4.0-release/load.sh
cd "$PRIMARY"
test "$(git branch --show-current)" = main || stop "not on main"
test -z "$(git status --porcelain)" || stop "the primary checkout has changes"
git fetch --tags origin
tags=$(git ls-remote --tags origin v4.0.0) || stop "cannot read GitHub's tags"
test -z "$tags" || stop "v4.0.0 is already on GitHub"
python scripts/cut_version.py 4.0.0     # not `major` (3.2 (c)); do not follow its push advice (Decided 8)
test "$(git log -1 --format=%s)" = "chore(release): cut v4.0.0" || stop "the cut's commit is not the last one"
test "$(git rev-parse 'v4.0.0^{commit}')" = "$(git rev-parse HEAD)" || stop "the tag is not on HEAD"
record T "$(git rev-parse 'v4.0.0^{commit}')"
. ~/.tcw-4.0-release/load.sh T                                        # read back
```

**Proves it:** criterion 24. Nothing is pushed.

### Step 29 — the suite on T, here (6.2 (a))

**Who:** an agent.

```sh
. ~/.tcw-4.0-release/load.sh T
mkdir -p "$Q"
test ! -e "$Q/clone" || stop "$Q/clone exists; after a failed check (Step 35) it is deleted first"
git clone -q "$PRIMARY" "$Q/clone" && git -C "$Q/clone" checkout -q "$T"
test "$(git -C "$Q/clone" rev-parse HEAD)" = "$T" || stop "the clone is not at T"
bash "$REL/ci-suite.sh" "$Q/clone" python3.14 > "$Q/suite-T.txt" 2>&1 || stop "the suite failed on T"
```

**Proves it:** criterion 25.

### Step 30 — CI on T, before the tag (6.2 (b))

**Who:** the dispatching session (pushing `v4` is allowed).

```sh
. ~/.tcw-4.0-release/load.sh T M0
cd "$PRIMARY"
git diff "$M0" "$T" | no_private_names                 # v4 is public once pushed
R=$(git ls-remote origin refs/heads/v4 | cut -f1)
is_hash "$R" || stop "cannot read GitHub's v4"
git merge-base --is-ancestor "$R" "$T" || stop "GitHub's v4 is not an ancestor of T: bring it to the user"
gh pr list --head v4 --json number,labels,state         # any pull request is named in the qa record
git push origin "$T:refs/heads/v4"
test "$(git ls-remote origin refs/heads/v4 | cut -f1)" = "$T" || stop "GitHub's v4 is not T"
id=$(dispatch_ci "$T")
gh run watch "$id" --exit-status || stop "CI failed on T"
gh run view "$id" --json headSha,jobs
record CI "$T"
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
  and the `3.x` branch. Then `git diff "$M0" "$T" | no_private_names`
  (criterion 29), in a block that loads `M0` and `T`.

### Step 32 — the tarball in a clean environment (6.2 (f))

**Who:** an agent.

```sh
. ~/.tcw-4.0-release/load.sh T
test "$(git -C "$Q/clone" rev-parse HEAD)" = "$T" || stop "the qa clone is not at T"
cd "$Q/clone" && python3.14 -m venv "$Q/build" && "$Q/build/bin/pip" install -q build && "$Q/build/bin/python" -m build
python3.14 -m venv "$Q/venv-4" && "$Q/venv-4/bin/pip" install -q "$Q/clone/dist/tcw_cli-4.0.0.tar.gz"
"$Q/venv-4/bin/tcw" --version | grep -q '^tcw 4\.0\.0$' || stop "the tarball's tcw is not 4.0.0"
test "$("$Q/venv-4/bin/tcw" --help | grep -cE '^\s+(project|migrate)\b')" -eq 2 || stop "project or migrate missing from --help"
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

The block is run as one file with its output saved to `$Q/tarball.txt`
(`bash "$REL/step-32.sh" > "$Q/tarball.txt" 2>&1`); `load.sh`'s `set -e`
stops it at the first command that fails, and the file's last line names it.

**Proves it:** criterion 30: every command exits 0 with the output 6.2 (f)
states.

### Step 33 — success criterion 3 (6.2 (g))

**Who:** an agent.

```sh
. ~/.tcw-4.0-release/load.sh
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
. ~/.tcw-4.0-release/load.sh T
test "$(git -C "$Q/clone" rev-parse HEAD)" = "$T" || stop "the qa clone is not at T"
cd "$Q" && PATH="$Q/venv-4/bin:$PATH" claude -p --plugin-dir "$Q/clone" \
  --output-format stream-json --verbose "Run tcw --version and report its output exactly." \
  > "$Q/plugin.jsonl"
"$Q/venv-4/bin/python" -c "import json,sys; e=[json.loads(l) for l in open('$Q/plugin.jsonl')]; \
  i=next(x for x in e if x.get('type')=='system' and x.get('subtype')=='init'); print(i.get('plugins'))"
said=$(PATH="$Q/venv-4/bin:$PATH" bash "$Q/clone/scripts/check_versions.sh" "$Q/clone")
test -z "$said" || stop "check_versions.sh printed: $said"
```

**Proves it:** criterion 32: one plugin, path `$Q/clone`, version `4.0.0`
(the fields `evals/run_evals.py:195-201` and `:261` read); the session's
answer holds `tcw 4.0.0`. If Claude Code's `init` event names those fields
differently, the step records the new names (spec Risks).

### Step 35 — a failed check (6.3)

**Who:** an agent for the fix; the dispatching session for the tag and push.

No tag is pushed. The fix is a new commit on `main` in the primary checkout
(in the child's area, briefed as Step 6), then `git tag -f v4.0.0 HEAD` and
`record T "$(git rev-parse 'v4.0.0^{commit}')"` (in a block that sources
`load.sh`), so every later step loads the new T; then the qa folder's
`clone`, `build`, `venv-4`, `venv-3`, `new` and `old` are deleted, Step 30's
fast-forward push of `v4` to the new T, and **every** check of Steps 29 to
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

The answer, naming T, is written to both copies of `gates.md`, as an entry
whose first line is `gate 3: go <T>` (or `declined`), and committed on
the primary checkout's `main` (`TCW-118: gate 3, <answer>`) before Step 37. A
decline: nothing is pushed; section 9's row "6.1-6.4".

**Proves it:** criterion 50 (that the commit adding it is not an ancestor of
T and is an ancestor of `origin/main` after Step 39).

## Phase E: publish, under gate 3 (Design 7)

### Step 37 — the tag alone (7.1) — gate 3

**Who:** the dispatching session, after reading gate 3's entry naming this T.

```sh
. ~/.tcw-4.0-release/load.sh T M0
gate_go 3 "$T"
cd "$PRIMARY"
test "$(git rev-parse 'v4.0.0^{commit}')" = "$T" || stop "the local tag v4.0.0 is not T"
remote_main() { git ls-remote origin refs/heads/main | cut -f1; }
{ echo "before 7.1"; date -u; remote_main; } >> "$P"
test "$(remote_main)" = "$M0" || stop "GitHub's main is not M0 before the tag"
git push origin v4.0.0
{ echo "after 7.1"; date -u; remote_main; } >> "$P"
test "$(remote_main)" = "$M0" || stop "GitHub's main moved while the tag was pushed"
```

Both checks find M0 (criterion 34).

### Step 38 — the upload confirmed (7.2) — gate 3

```sh
. ~/.tcw-4.0-release/load.sh T
gate_go 3 "$T"
gh run list --workflow release.yml --limit 5 --json databaseId,headSha,event,createdAt
# <id>: the run whose headSha is $T; read from the list above, then:
gh run watch <id> --exit-status || stop "the release run failed: follow 7.4"
gh run view <id> --json jobs
test "$(curl -sf https://pypi.org/pypi/tcw-cli/4.0.0/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])")" = 4.0.0 ||
  stop "PyPI does not list tcw-cli 4.0.0"
pipx run --spec tcw-cli==4.0.0 tcw --version | grep -q '^tcw 4\.0\.0$' || stop "the published tcw is not 4.0.0"
```

This step is run by hand in two parts, since the run's id is read from the
list: the list, then the rest with the id written in, each part a file that
starts with the block's first two lines.

**Proves it:** criteria 35 and 38. A failed run follows 7.4: a failed `test`
job stops for the user's decision (move the tag or cut 4.0.1); a `publish`
failure before upload is corrected and re-run under gate 3's go; a failure
after the upload ships the fix as 4.0.1 (criterion 37).

### Step 39 — `3.x` and `main`, at once (7.3) — gate 3

**Who:** the dispatching session, as soon as Step 38 passes, with no question
to the user.

```sh
. ~/.tcw-4.0-release/load.sh T M0
gate_go 3 "$T"
cd "$PRIMARY"
remote_main() { git ls-remote origin refs/heads/main | cut -f1; }
{ echo "before 7.3"; date -u; remote_main; } >> "$P"
test "$(remote_main)" = "$M0" || stop "GitHub's main is not M0: someone pushed to it"
x=$(git ls-remote origin refs/heads/3.x) || stop "cannot read GitHub's branches"
test -z "$x" || stop "3.x already exists on GitHub"
test "$(git branch --show-current)" = main || stop "not on main"
git merge-base --is-ancestor "$T" main || stop "T is not an ancestor of main"
after=$(git diff --name-only "$T" main) || stop "cannot compare T with main"
if printf '%s\n' "$after" | grep -v -e '^docs/work/TCW-118-tcw-4-0-release/' -e '^docs/work/TCW-99-' -e '^$'; then
  stop "main changes files past T outside TCW-118's and TCW-99's folders; gate 3 does not cover them"
fi
git diff "$T" main | no_private_names                   # what main adds past T
git log -p "$T..main" | no_private_names                # and every commit past T, messages included
git push origin "$M0:refs/heads/3.x"
git push origin main
git fetch origin
git merge-base --is-ancestor "$T" origin/main || stop "T is not on GitHub's main"
test "$(git ls-remote origin refs/heads/3.x | cut -f1)" = "$M0" || stop "GitHub's 3.x is not M0"
test -z "$(git ls-remote origin refs/heads/release-4.0.0)" || stop "release-4.0.0 reached GitHub"
```

The checks after the pushes report; nothing pushed can be taken back by
them, and a failure there goes to the user with section 9's row "7.2-7.3".

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
was), naming neither setup. TCW-118 does not wait for those records. The
comment is written to the live board, so it is posted only right after
`bash -c '. ~/.tcw-4.0-release/load.sh T; gate_go 3 "$T"'` has exited 0.

**Proves it:** criterion 40.

### Step 42 — GitHub issue #24 (8.3)

**Who:** the dispatching session drafts; **the user** approves the exact text;
then the dispatching session posts and closes.

**Does:** after Step 38, a reply naming 4.0.0 and what changed (TCW-113
Design 7.1: the `audit-backlog` procedure covers a project's family), shown
to the user in full, and posted only after the user approves that exact
text. The text is saved as `~/.tcw-4.0-release/issue-24.md` before it is shown; on the
user's approval the dispatching session adds the line `issue 24: approved
<sha-256 of issue-24.md>`, with the user's words quoted beneath it, to both
copies of `gates.md` and commits it; then:

```sh
. ~/.tcw-4.0-release/load.sh T
gate_go 3 "$T"
sum=$(shasum -a 256 "$REL/issue-24.md" | cut -d' ' -f1)
grep -qx "issue 24: approved $sum" "$REL/gates.md" || stop "issue-24.md is not the text the user approved"
gh issue comment 24 --body-file "$REL/issue-24.md"
gh issue close 24
```

A change to the text after its approval changes its digest, so the block
stops until the user approves the new text.

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
item**; its stage is read before and after and is the same. The filings, the
comments and the move all write to the live board, so the step starts only
after `bash -c '. ~/.tcw-4.0-release/load.sh T; gate_go 3 "$T"'` has exited
0.

**Proves it:** criterion 42.

## Documentation Sync

Run with the `documentation-sync` skill at Step 9, over Phase A's changes;
the release's later steps change no documented behaviour.

| Entry | Fires? | What this item does |
| --- | --- | --- |
| `README.md` [Public-API] | yes | Step 4: the session-start install takes the CLI of the plugin's own version (`:77-86`, as TCW-117 leaves it). |
| `docs/guide/jira.md` [Jira-Change] | no | No `tcw work` command's effect on a ticket changes; the conversion is TCW-116's and its guide entry is TCW-117's. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | Step 2: fix 14 changes `docs/guide/taxonomy-and-capabilities.md:413` (the `unreviewed` line it quotes) and fix 20 changes `docs/migration-guide-3.X-to-4.0.0.md:160` (the summary line's singular), both as TCW-117 leaves them; every other quotation found ("The follow-ups") stays true. No guide describes the plugin's install; Step 9 greps `docs/guide/` for `pipx` and `tcw-cli` and corrects any line saying the install floats. `docs/releasing.md` (Step 3) is contributor documentation, not a guide, and is updated anyway (criterion 6). |
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
8 → 6; 9, 49 → 7; 10 → 1; 11 → 9; (no criterion: 9a proves the suite
script that 17, 23 and 25 rely on); 43-45 → 4; 46 → 10, 12; 12 → 11, 12; 13 →
13; 14, 15 → 14; 16-18 → 15; 19 → 16; 54 → 17; 47 → 18; 52 → 19; 48 → 20; 53 →
21; 20 → 23; 21 → 24; 22 → 25; 23 → 27; 24 → 28; 25 → 29; 26 → 30; 27-29 → 31;
30 → 32; 31 → 33; 32 → 34; 33 → 35; 50 → 36; 34 → 37, 39; 35, 37, 38 → 38; 36,
51 → 39; 39 → 40; 40 → 41; 41 → 42; 42 → 43. Every step traces to a Design rule
or to a decision above (Step 2: Decided 1; Step 22: Decided 4; Step 26:
Design 2.2; Step 9a: Decided 7). No step repeats another: 4.5 and 6.2 (f)-(g) share their
commands by reference (Step 17 runs Steps 32 and 33's).

The gates are kept exactly: every block of Steps 20, 21, 23, 24 and 25
reads gate 2's entry first, and the way back from Step 24 reads the user's
`way-back` word; Steps 37-39 and 41-43 read gate 3's, and Step 42 also the
approved text's digest (the full list is in Revision 3); nothing before Step 18 leaves the machine but
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
5. **Section 9's row "5.6-5.7" names the files before the tickets** ("The
   files as for 5.5. The tickets: …"). This plan runs the tickets first and
   the files after ("The way back from Step 24"), because that is the order
   Step 21 rehearses and the script must run with the 4.0 code. If the row
   is read as an order, this departs from it; if it is read as a list, it
   does not. No rule of the row changes otherwise.
6. **5.6 says a stopped run "is run again to finish" with no limit.** This
   plan limits it (Step 24, "The re-run limit"): only a stop the run reports
   as Jira unreachable or rate limiting is run again, at most three times;
   anything else goes to the user, who decides whether the way back runs.

## Revision 1

The first plan review's findings, each checked against the plan by the
dispatching session and accepted (decided by the dispatching session); what
changed for each, and the choices made while answering them (decided by the
plan's author, as marked).

1. **[blocking] Values passed between steps lived only in shell variables,
   and T was never recorded.** "Tools" now says how every block is run (as
   one file, sourcing `load.sh` first) and adds `load.sh`: `set -euo
   pipefail`, the fixed paths (`REL`, `PRIMARY`, `C`, `Q`, `P`), and the
   helpers `stop`, `record`, `value_of`, `capture`, `no_private_names`,
   `gate_go`, `dispatch_ci` and `retryable`. Each named value is loaded from
   the last line of its name in `refs.txt` and refused unless it is a
   40-character hexadecimal hash; `refs.txt` now holds `M0`, `V`, `CI`, `A`
   and `T`, written only by `record`. Every block from Step 9a on loads the
   values it uses. Every comment-only guard is now a check that stops:
   Step 10 (GitHub's `v4` equals its tip; the run found by commit, not by
   a typed id), Step 12 (on `main`, no changes, `main` equal to M0, V
   differs from CI's commit only in TCW-118's folder), Step 13 (both merge
   parents, outside the primary checkout), Step 14 (dry-run exit and keys),
   Step 15 (d)-(f), Step 16 (parents and GitHub's `main`), Step 17 (clone at
   A), Step 20 (nothing past A outside `docs/`, `1 passed`), Step 21 (the way
   back's exit 1), Step 23 (branch, changes, M0, `tcw 4.0.0`, equal
   `main`s), Step 25, Step 28 (no tag on GitHub, read in a way that fails
   when GitHub cannot be read), Step 29, Step 30 (the ancestor check), Steps
   32 and 34, Step 37 (GitHub's `main` is M0 before and after) and Step 39
   (GitHub's `main` is M0, `3.x` absent, read so that a failed read stops).
   Running each block under `set -e` meant the old `{ …; echo "exit $?"; }`
   captures would stop before writing the exit code, so they all use
   `capture`. Choices (author): the gate entries' first line has a fixed
   form (`gate <n>: go <commit>`) so `gate_go` can check it; Step 38 keeps
   a typed run id, read from a list filtered by T, since the release
   workflow is started by the tag and not by this plan.
2. **The way back's order (row "5.6-5.7").** Choice (author): the tickets
   first, with the 4.0 files and install still in the primary checkout, then
   the files ("The way back from Step 24"), rather than passing the merge
   clone as the root. Why: it is the order Step 21 rehearses; it reads the
   primary checkout's own layers, including a personal file the clone does
   not have; and it does not depend on the merge clone, which Step 40 may
   delete. The script's `getattr` reads are kept. Narrowed while checking:
   `settings(root)` reads `own_jira_layers`, which reads the root 3.x
   `tcw-config.yaml` when present (`tcw/migrate/legacy.py:355-370`), so a
   reset to M0 first would probably not make it fail; the order is changed
   anyway, for the rehearsal's sake. Listed as Spec issue 5.
3. **Step 24's re-runs had no limit.** Choice (author): only a stop reported
   in the Jira client's words for unreachable or rate limiting is re-run, at
   most three times after the first run, five minutes apart or longer when
   Jira says `Retry after`; any other stop, or a fourth stopped run, goes to
   the user with the way back offered, and the user decides whether it runs.
   Spec issue 6.
4. **Fix 14 changes text that TCW-117's guide quotes.** Fix 14's row now
   gives the exact new line and changes `docs/guide/taxonomy-and-capabilities.md:413`
   in the same commit; the Documentation Sync table's guide row fires. Step
   2's rule now allows a fix to change a guide, skill, capability record or
   migration guide line that quotes what it changes, and requires a search
   for the old text before each commit. Every fix's text was searched for in
   TCW-117's worktree: one more quotation changes, the migration guide's
   summary template (`docs/migration-guide-3.X-to-4.0.0.md:160`, fix 20); the
   others found stay true and are listed under the fixes table (fix 5's row
   now limits the added guide link to the work store so that
   `docs/guide/linking-and-validation.md:258` stays true).
5. **Fix 2 missed `tcw/validate.py:930`.** A search of `tcw/` for every
   `startswith("tcw://")` and `startswith(SCHEME)` found eight places that
   tell a store `path` or a `-C` target from a folder: the four already
   listed, `tcw/validate.py:930`, `tcw/store/fs.py:3760`, and `tcw/cli.py:540`
   and `:558`. All eight are in the fix now, through one `has_scheme`
   function. The parsers in `tcw/ids.py` (`:248`, `:262`, `:361`, `:364`),
   `tcw/cli.py:66` (already case-blind) and the Markdown link readers are
   listed as left alone, with the reason.
6. **Fix 10 did not report the folders it removes.** The row now adds each
   folder `remove_emptied` returns to `self.changed`, as `move` reports them
   (`tcw/move.py:377-378`), and the test checks the `removed` line.
7. **`ci-suite.sh` had never run.** New Step 9a writes it and runs it once on
   a fresh clone of `v4` before CI. The script now passes this machine's
   corepack cache (`COREPACK_HOME`) and `COREPACK_ENABLE_DOWNLOAD_PROMPT=0`,
   and gives every run `/dev/null` as input, so pnpm cannot hang on a
   download or a question; Step 9a says what to do if it hangs anyway.
   "Tools" notes that CI builds the web app on Node 22 and this machine has
   only Node 24, so only CI's `web-build` job proves the build. Choice
   (author): pytest now runs with no Node on its `PATH`, as in CI's pytest
   job.
8. **The private-name search covered only M0 to T, and the plan held
   machine paths.** Step 39 now searches `git diff "$T" main` and `git log
   -p "$T..main"` (every commit after T, its message included) before
   pushing, and refuses files past T outside TCW-118's and TCW-99's folders.
   Choice (author): Step 30 also searches `git diff "$M0" "$T"` before it
   pushes T to the public `v4`, since Step 31's search came after that push.
   Every home-folder path is now written with `~`, and "Who does what" names
   the four folders once.
9. **Minor.** Step 5 is marked **[after TCW-117]** and first checks that the
   migration guide exists. Step 6 gains slice 6: TCW-117's guides, skills
   and migration guide against the code after Step 2's fixes.

## Revision 2

Five entries added to `followups.md` while TCW-117's skills were written
(F:62 to F:66), each checked against `v4` at `7af7343e` and reproduced
where it was a defect, with the worktree's 4.0 `tcw` in a scratch project
(placements decided by the plan's author):

- **F:62** (`taxonomy move --top` keeps `parent:`): dropped, by design
  (TCW-114's spec `:702-703`).
- **F:63** ("init takes a path"): fix 22, reproduced.
- **F:64** (empty file name in `--origin`'s `# skipped:` line): fix 23,
  reproduced (`(Jira credential names apply only in a Jira-mode project, )`).
- **F:65** (validate in a parent does not report a child's broken entry):
  documentation already answered by TCW-117; validate checks the current
  project only, in 3.x as in 4.0.
- **F:66** (`--id` named where it is not needed): fix 24, reproduced with
  `tcw taxonomy path` and `tcw taxonomy move`.

The dispatching session's note that TCW-117's skills say an unknown project
exits 1 (`check the spelling`) was checked against every fix: none changes
that exit code. Fix 16, the nearest, changes only a check that could not
run (`Unchecked`); an unknown ID is answered `Invalid` and still exits 1.
Its row now says so and the quotation list names the two lines.

## Revision 3

The second plan review's findings, each checked against the plan by the
dispatching session and accepted (decided by the dispatching session); what
changed for each, and the choices made while answering them (decided by the
plan's author, as marked).

1. **[blocking] `way-back.py` took `--read` as its file pattern.** Run as
   Step 24 runs it, `--read` was the fourth word, so the pattern matched
   nothing, `restore_tickets([])` returned at once, the script exited 0 and
   the block went on to reset the files with every ticket still at its 4.0
   value (reproduced with the old script against a stub: `runs read: []`,
   `put back: []`, exit 0). The script now parses its arguments with
   `argparse`: three names, `--runs <pattern>` (default
   `tcw116-step6*.txt`) and `--read`, in any order. It stops with exit 3 when
   no run matches, when the folder holds other than exactly one dry run, when
   the pattern matches the dry run, when the runs name no edited ticket
   though the dry run lists some, and when a key is in only one file and
   `--read` was not given; 1 stays the exit for a ticket Jira left out.
   Every call uses the new form: Step 21's rehearsal passes `--runs
   'rehearsal-step6*.txt'`; the way back from Step 24 passes its own
   arguments through (`bash way-back.sh` or `bash way-back.sh --read`),
   refusing any other, and also requires a `put back: [` line before the
   files are touched. Choices (author): the distinct exit 3, so that Step
   21's check for exit 1 cannot be met by a stop; the dry-run count and the
   pattern-overlap checks.
2. **[blocking] Live writes ran without `gate_go`.** Added: the filing on
   `TCWTEST`, the conversion and the way back of Step 21; the way back from
   Step 24 (`gate_go 2 "$A" way-back`); Step 25's real `tcw migrate`. Step
   22's answer has its own first lines (`gate 2: go <A>` or `gate 2: stop
   <A>`), and the answer to Step 24's offer of the way back too (`gate 2:
   way-back <A>` or `gate 2: stop <A>`). `gate_go` now reads only the latest
   fixed line for its gate and commit and requires it to be the word asked
   for (`go` unless a third argument says otherwise), so a later `stop` or
   `way-back` ends a go and only a new `go` restores it. Quoted words start
   `> ` so they cannot take the fixed form. Every command in the plan that
   writes outside the scratchpad, the merge clone or the release folder,
   and what guards it:
   - Jira, `TCWTEST`: Step 20's live scenario (`gate_go 2`); Step 21's
     filing, conversion and way back (each `gate_go 2`), and its edits by
     hand in Jira (each made only after a `gate_go 2` run exits 0).
   - Jira, the live `TCW` board: Step 24's conversion (`gate_go 2`); the way
     back from Step 24 (`gate_go 2 … way-back`); Step 25's `tcw migrate`
     (`gate_go 2`); Steps 41 and 43's comments, filings and move to
     `completed` (each after a `gate_go 3` run exits 0). Not gated: the
     dispatching session's lifecycle moves and comments on TCW-118 (Step 27
     and every earlier stage move), now said so under "Who does what"
     (choice, author); Step 14's dry run and Step 21's issue-type search,
     which only read.
   - This machine's shared install: Step 23 (`gate_go 2`); the way back's
     reinstall of 3.0.2 (`gate_go 2 … way-back`).
   - GitHub: the pushes of `v4` and `gh workflow run` in Steps 10, 30 and 35
     (allowed without a gate by the rule above, as the user allowed pushing
     `v4`); the tag and the pushes of `3.x` and `main`, Steps 37 and 39
     (`gate_go 3`); Step 42's comment and close (`gate_go 3`, and the
     approved text's digest, below).
   - PyPI: nothing is written; Step 38 only reads (`gate_go 3` anyway).
   Choice (author): Step 42 now posts from `~/.tcw-4.0-release/issue-24.md`
   only when `gates.md` holds `issue 24: approved <its sha-256>`, so the
   text posted is the text approved.
3. **`git diff --quiet HEAD` passed for an untracked `gates.md`.** `gate_go`
   now stops when a checkout's `gates.md` exists but its last commit has
   none, and when the working copy differs from the last commit's
   (`git show HEAD:<path> | cmp`); it passes only when some checkout's last
   commit holds exactly the release folder's copy. Choice (author): the
   whole file is compared with the release folder's copy rather than one
   line searched for, since "latest answer" needs the whole order.
4. **Fix 24 missed two places.** The row now names `_missing()` in
   `tcw/taxonomy/cli.py:29-31` and `tcw/capabilities/cli.py:30-32` beside
   `tcw/project_cli.py:177` and `tcw/move.py:96-97`, through one helper, and
   its test covers a taxonomy and a capabilities command. A search of
   `tcw/` on `v4` at `0cf6e97f` for `--id <` found three more, left as they
   are with the reason in the row: `tcw/errors.py:13`, `tcw/cli.py:75`,
   `tcw/store/project.py:947`.
5. **`gate_go` cannot tell who wrote a line.** Said plainly under "Who does
   what": only the dispatching session writes `gates.md`, only to record an
   answer just given, with the user's words quoted exactly; no agent writes
   or commits it.
6. **Minor.** Step 24's comparison block sources `load.sh` and reads the
   release folder from `$REL` and the clone's Python from `$C`. Step 38's
   two hand-run parts each start with the block's first two lines (author).

**Tests run** (2026-10-24, scratch folder
`/private/tmp/claude-501/-Users-brian-Projects-TCW/abc313a2-da1e-4eb6-ac45-d50b6c6dd99c/scratchpad/tp118/`;
the script and `load.sh` were cut from this file's own text, with
`restore_tickets` replaced by a function that prints and `load.sh`'s three
paths pointed at scratch folders; no Jira, no `tcw`):

- `way-back.py`, under `python3 -S` with stub modules: no `--read`, every
  key in both files: `restore_tickets` called with both, exit 0. `--read`
  after the names, and before them: the same, exit 0. No run found
  (`--runs 'nothing*.txt'`): `stop: no saved run matches…`, exit 3, no call.
  A key only in the dry run, no `--read`: exit 3, no call; with `--read`:
  called with the one edited ticket, exit 0. Pattern matching the dry run:
  exit 3. Runs with no edit line, dry run listing two: exit 3. Jira leaving
  one out: `put back:` and `left out:` printed, exit 1. `--reed`: argparse's
  usage, exit 2. The rehearsal's form (`. tcw-rehearsal … --runs …`): exit 0.
- `gate_go`, under `/bin/bash` 3.2.57 with two scratch git repositories:
  go written but never committed (untracked): stops, `is not committed`.
  Go committed: passes. Go for another commit: stops. `way-back` asked with
  only a go given: stops. Go then stop: stops. Go, stop, go: passes.
  `way-back` written and asked for: passes; asked as a go: stops. Committed
  copy changed afterwards (uncommitted): stops, `differs from its last
  commit`. Release copy newer than every commit: stops. A quoted `> gate 2:
  go <B>` line: not counted. An untracked copy in the primary checkout
  beside a committed one in the clone: stops. No copy in the primary
  checkout, committed in the clone: passes.
- The way back's block under `/bin/bash` 3.2: after `. load.sh M0 A`, the
  block still sees its own `--read` (`[--read]`) or nothing (`[]`), and
  refuses `--force`.
