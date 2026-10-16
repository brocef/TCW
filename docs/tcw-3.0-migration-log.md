# TCW 3.0 migration log

The record of TCW's own migration from 2.8 to 3.0.0, made by following
[the migration guide](migration-guide-2.8-to-3.0.0.md) (TCW-76, Tasks B4 to
B16). It is kept outside the work path, as the guide's rule 7 says. What
TCW-76 did before the freeze (the filesystem rehearsal, the guide's review,
the Jira checklist for the owner) is in TCW-76's own `outcome.md`, which
stays the item's implement document and is converted at step 7.

## Run 1

Started: 2026-10-16
Starting commit: 3b71ea7826cfabb7610e6fd01a0497edf78fec71

The starting commit is the freeze commit: `epic/tcw-3.0` after `main`
(`8b5a212b`) was merged into it (TCW-76 Task B3). The run is made in the
worktree `.worktrees/tcw-3-0-migration-run-1`, on the branch
`migrate/tcw-3.0-run-1`.

### Deviations from the plan

- **(a) A version was cut before Task B24.** 2.8.3 was cut and published on
  2026-10-16 at the owner's request, although TCW-76's plan said no version
  until B24. All five version files say 2.8.3 after Task B3.
- **(b) The agent applies the Jira changes.** The owner asked on 2026-10-16
  that the agent make the Jira workflow, status, screen and field changes
  itself, in the owner's personal Chrome profile, instead of the owner making
  them by hand (spec Design 2 step 2 and 6.2 said by hand). Each change is
  still listed in the step 1 plan, for approval before it is made.
- **(c) TCW gets its own screens.** The owner chose on 2026-10-16 that TCW
  gets its own copies of the screens it shares with `PRPI` (TCW-76's
  `outcome.md`, Jira checklist step 5).
- **(d) Where the log lives.** TCW-76's spec (Design 1.8) and plan (choice 5)
  made the log TCW-76's 2.x `outcome.md`, becoming `implement/round-1.md` at
  step 7. The guide's rule 7 keeps the log outside the work path, and the
  run follows the guide as written, so the log is this file,
  `docs/tcw-3.0-migration-log.md`. It also keeps one path through steps 4, 6
  and 7, which move and rename TCW-76's folder and its `outcome.md`.
- **(e) 2.8 for step 0.** The plan's rules name 2.8.1 for reading the 2.x
  board. Step 0 ran 2.8.3, the released version the board is on, from PyPI
  in a private virtual environment (`tcw76/venv-28` in the session's scratch
  folder; `tcw --version` printed `tcw 2.8.3`).

### Step 0: Prepare

**Before you start**, checked on 2026-10-16:

- On 2.8.x: `tcw --version` printed `tcw 2.8.3` (the shared install, and the
  private `venv-28` from PyPI).
- The 3.0 CLI beside it: the private virtual environment `tcw76/venv`, an
  editable install of this worktree. Run from outside the primary checkout,
  it imports `.worktrees/tcw-3-0-migration-run-1/tcw/__init__.py`, and
  `tcw work advance --help` prints `usage: tcw work advance [-h] [--to TO]
  [--force] [--reason REASON] [--dry-run]`, a 3.0 command. Its version string
  still reads 2.8.3, since 3.0.0 is cut later.
- No uncommitted changes: `git status --porcelain` printed nothing.
- No 2.x item worktree: `git worktree list | grep -E '\[work/'` printed
  nothing. The other worktrees, listed for the plan: the primary checkout
  (`main`, `8b5a212b`), `.worktrees/tcw-3-0-epic` (`epic/tcw-3.0`,
  `3b71ea78`), and this one.
- A branch or tag marking the 2.x state: `main` (frozen at `8b5a212b`) and
  `epic/tcw-3.0` (`3b71ea78`) mark it today, but both move later (B21, B24),
  and the tag `v2.8.3` is on `74b5913f`, four board commits before `main`'s
  tip. No tag was made in this step; the step 1 plan proposes one.
- Connected projects: the configuration declares none.
- Jira credentials: `TCW_JIRA_EMAIL` and `TCW_JIRA_API_KEY` are set (after
  `source ~/.bashrc`).
- `jq --version` printed `jq-1.7.1-apple`.

**2.8's `tcw validate`**, run in this worktree with `venv-28`: printed
`validate OK`, exit 0. Nothing to fix under 2.8. `git status --porcelain`
printed nothing afterwards.

**Ignored item folders.** In this worktree,
`git status --ignored --porcelain -- docs/work` printed nothing. In the
primary checkout, `git -C /Users/brian/Projects/TCW status --ignored --porcelain -- docs/work`
printed 37 lines, all under `docs/work/discarded/` (the `.gitignore` rule
`docs/work/discarded/*`, lines 29-30); 33 were counted on 2026-10-15. The
list is in the step 1 plan.

**Finished slices** (criterion 27): each one's `graveyard.yaml` `location`,
and `git cat-file -e <location>:docs/work/completed/<slug>/spec.md`:

| Slice | `location` | `git cat-file -e` |
| --- | --- | --- |
| TCW-69 | `0e4d406165a7ac84bb8d49376b06ac6a91df2f36` | exit 0 |
| TCW-70 | `3207f3103f73bcefe5fedfe7e3ed7d50b39bc8cb` | exit 0 |
| TCW-71 | `6599dd209f89ae87c403455129e783aeff49bad2` | exit 0 |
| TCW-72 | `a066ae201dc12928fbe06ad27dead370bfc85ed1` | exit 0 |
| TCW-73 | `e400dcfd046c6044d905c550902be9896899af20` | exit 0 |
| TCW-74 | `64a2eb9478ecf4d0eec7dc16a5e390161ee852bd` | exit 0 |
| TCW-75 | `560e312f1700893abbdf05d596d1817ae541916a` (deleted in `b5b7756f`) | exit 0 |
| TCW-77 | `0a23906fb743a41ebf6d1fb2227ebf122ad2d318` | exit 0 |

**Check.** Before the log was started, `git status --porcelain` printed
nothing and `git worktree list | grep -E '\[work/'` printed nothing.
Afterwards, `grep -E '^(Started|Starting commit): ' docs/tcw-3.0-migration-log.md | tail -n 2`
printed:

```text
Started: 2026-10-16
Starting commit: 3b71ea7826cfabb7610e6fd01a0497edf78fec71
```

### Amendments to the guide

None in step 0.
