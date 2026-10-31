# Plan — TCW 4.0: guides, skills, use cases and the 3.x-to-4.0 migration guide

Child 12 of TCW-99. This plan carries out the spec
(`spec/spec.md`, revised after review and corrected after the plan review,
43 acceptance criteria) on the `v4`
branch, in the worktree `/Users/brian/Projects/TCW/.claude/worktrees/v4`.

**When it runs.** Implement starts after TCW-106, 107, 110, 108, 111, 109,
112, 114, 113, 115 and 116 have landed on `v4`, in that order, and before
TCW-118. Every step below plans from the state those items leave, as their
final plans (`docs/work/TCW-1{06..16}-*/plan/plan.md`) describe it; TCW-116's
plan was read as it stood on 2026-10-22 (1705 lines, "Revision 2"). Where a
sibling's implement round, once written, says the code departs from its
plan, the code wins (spec Design 1.1).

**Citations.** File and line references are at `2adac9c9` (the commit that
holds this item's revised spec). At that commit only TCW-106 and TCW-107 have
landed, and no live document differs from `b2fa5810` except
`skills/work/SKILL.md` (TCW-107), so the spec's citations still hold there.
The siblings move them; Step 0 re-finds every passage by its words, and every
step names the words it looks for.

**Words used below.**

- `<S>` is the implementing session's scratchpad folder; every scratch file
  and scratch project goes there, never in the worktree.
- **The 4.0 CLI** is `.venv/bin/tcw`, run from the worktree's root, which
  prints `tcw 4.0.0`. **The lifecycle CLI** is the bare `tcw` first on the
  path, the primary checkout's 3.0.2, which reads this repository's 3.x
  ledgers and root `tcw-config.yaml`. They are never swapped.
- **The three command checks** are `tests/test_documented_cli_surface.py`
  (`_check`), `tests/test_shipped_text.py` (`command_problem`) and
  `tests/test_docs_describe_3_0.py` (`command_problems`), which TCW-114
  Step 6 taught to skip `-C` and exactly one following word.
- **The scan** is `THREE_X_PATTERNS` (spec Design 9.2) as Step 1 writes it.
  **The grep** is spec Design 9.3's `git grep` command, copied byte for byte
  into `<S>/grep-9-3.sh` at Step 0.
- **A document step's red-to-green check**: before the step changes a file,
  `<S>/scan_one.py <file>` (Step 0) and the grep are run on it and their hits
  recorded; after, both print nothing for that file outside a passage that
  names `tcw migrate` or links the migration guide (grep: nothing at all).
  That is the "test written first" of a step that changes prose: the
  recorded hits are what goes red, and they are seen before the change.
- **Checked on `v4`**: the method of "How every claim about a command is
  checked", below.
- **A scratch run** is any command run for this item outside the suite. It
  runs in `<S>/runs/<step>/`, always through `<S>/scratch-env.sh <command>`
  (Step 0 item 2), which runs the command with `HOME=<S>/home`,
  `XDG_CONFIG_HOME=<S>/xdg` and `XDG_CACHE_HOME=<S>/cache`, and with every
  `TCW_JIRA_*` and `TCW_PROJECT_*` variable of the calling shell removed.
  `XDG_CONFIG_HOME` is what decides where TCW reads the user-wide file
  (`$XDG_CONFIG_HOME/tcw/config.yaml`, else `~/.config/tcw/config.yaml`;
  `tcw/config.py:192-205`, the same in 3.0.2), so a scratch run's user-wide
  file is `<S>/xdg/tcw/config.yaml` and never the person's own.
  `XDG_CACHE_HOME` decides where TCW keeps working copies of stores held in
  another repository (`tcw/store/checkouts.py:60-68`). `HOME` is moved too,
  so that nothing else under the person's home folder is read or written; git
  then reads `<S>/home/.gitconfig`, which holds a scratch `user.name` and
  `user.email` for scratch commits. `TCW_CONFIG_DIR` is not used for any of
  this: it is only the folder TCW tells a hook its `file:` binding is read
  from (`tcw/config.py:76`, `tcw/work/hooks.py:54`, `:77`), and it moves no
  file (decided while planning, 14).

## How the steps are grouped

The spec's Design 11 fixes one formatting-only commit and then three parts,
each one commit with the suite as CI runs it green after it (criterion 43):

| Part                                                                                    | Steps    | What it holds                                                                                                                                                                                       |
| --------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0. Formatting only                                                                      | 0b       | `prettier --write` over every Markdown file in scope that the item will change, and nothing else (decided while planning, 13)                                                                       |
| 1. The migration guide and its test                                                     | 0 to 5   | Step 0's inventory; `THREE_X_PATTERNS`, `scan`'s `flags`, and the scan's own tests; `tests/test_migration_guide_4_0.py`; `docs/migration-guide-3.X-to-4.0.0.md`; the README index line and its test |
| 2. README, guides, use cases, agent and lifecycle documents, design amendments          | 6 to 18  | spec Design 3 (but 3.6), 4, 6, 7 and 8                                                                                                                                                              |
| 3. Skills, other shipped text, evals, the ledger, and the scan over every live document | 19 to 30 | spec Design 5, 9.6 (a) and (b), 9.8, the live half of `tests/test_docs_describe_4_0.py`, the upcoming entries, the Documentation Sync                                                               |

Inside each part the order is: tests that can be written first, then the
riskiest document (the one with most facts) while its sources are fresh, then
the documents that link to it. Within Part 2 the guides come before the
README and the use cases, because both link into the guides' headings, and a
heading a guide renames is fixed in every inbound link in the same step
(below, "Links"). Part 3's live scan goes in last, because it fails until
every live document is rewritten (spec Design 11).

## How every claim about a command is checked

The request asks that every claim a document makes about a command is checked
against the real 4.0 CLI, not against a sibling's spec. Four layers, each used
where it applies:

1. **The surface, dumped once.** Step 0 runs `<S>/dump_help.py`, which walks
   `tcw.cli.build_parser()` (the same walk `tests/test_documented_cli_surface.py:173-194`
   makes) and writes `<S>/cli-4.0/index.txt` (every command path with every
   flag it accepts) and one `<S>/cli-4.0/<path>.txt` per command holding its
   `--help`. Every command, verb, flag and exit code a step writes is looked
   up there before it is written, and the help text is the source for what a
   command says it prints and writes (`Prints:`, `Writes:`). The dump is
   remade if any sibling commit lands after Step 0 (`git log -1` is
   compared at the start of each part), and Step 30 checks once more after
   the last sibling commit (decided while planning, 19).
2. **The code spans, automatically.** Every `tcw …` in a code span or fenced
   block of a live document is checked by the three command checks in the
   suite; every `tcw …` the migration guide writes outside its two exempt
   columns is checked by `tests/test_migration_guide_4_0.py` (Step 2)
   against the surface read from `--help`, so a flag 4.0 hides from `--help`
   is refused (decided while planning, 16). A command written in plain prose,
   outside any code span, is checked by no test: the grep of spec 9.3 catches
   only removed commands and flags there, and the review reads the rest.
3. **Behavior, by running it.** Every claim about what a command does (an exit
   code, a printed line or heading, a file it writes, a refusal's wording) is
   run once as a scratch run (above), in a scratch project under
   `<S>/runs/<step>/`, and the command,
   its exit code and the lines quoted are pasted into the implement round's
   table "Checked on v4", one row per claim, named by the document and the
   spec letter it answers. A 4.0 project is made with
   `.venv/bin/tcw project new --id <id>`; a 3.x project, for `tcw migrate`,
   with the lifecycle CLI's `tcw init --id <id>` (3.0.2, called by the
   absolute path Step 0 item 2 records), then edited by hand
   to the 3.x shape needed. Wording a document quotes is copied from that
   output, never from a spec.
4. **What cannot be run here** (anything that needs a live Jira site, or a
   network clone) is checked against the test in `tests/` that proves it,
   and that test's ID is the row's evidence. A test usually asserts only a
   fragment of a message, so the wording a document quotes is copied from
   the message's source in `tcw/` (its file and line in the row), and the
   test is the evidence that the message is produced. Nothing in implement
   contacts Jira or the network.
5. **A claim nothing proves is not written.** A claim that is neither run
   (layer 3) nor covered by a test (layer 4) is left out of the document,
   listed in the implement round, and reported to the dispatching session.

A difference found between the code and a sibling's spec is written as the
code behaves, listed in the implement round under "Departures found", and
reported to the dispatching session (spec Design 1.1). It is not fixed here.

## Rules every document step follows

- **Plain language** (spec Design 1.3, criterion 41): each technical term is
  defined in the sentence where the document first uses it; "full identifier"
  is the proper name, and a document that says "slug" says once that it is a
  nickname for it. None of the shorthand the user's instructions forbid.
- **One token after `-C`** (spec Design 1.4): `tcw -C <folder> …` or
  `tcw -C tcw://<id>.path/ …`, never a phrase.
- **One home per fact** (spec Design 1.5): the step that owns a fact's home
  states it in full; every other step states it in a sentence and links the
  home.
- **3.x forms** (spec Design 1.6): only in a paragraph, list item or table row
  that also names `tcw migrate` or links `migration-guide-3.X-to-4.0.0.md`;
  never a removed command or flag outside the migration guide (a removed
  command is named by its verb alone, in a table whose header says the verbs
  are removed); never a 3.x example in a fenced block; never "no longer",
  "previously" or "since 3.0" (they are in `PATTERNS`,
  `tests/doc_vocabulary.py:46-47`, which both the 3.0 scan and the shipped-text
  scan read). A passage about 3.x is written "In 3.x, …; in 4.0, …".
- **A mistyped command is never written in a code span.** `_check`
  (`tests/test_documented_cli_surface.py:197-216`) fails on `tcw new` in
  backticks ("no such verb"), so a word typed in error is written in prose
  ("typing new straight after tcw") and only its suggestions go in code
  spans (decided while planning, 9).
- **Two layers** (spec Design 1.7): where a document describes manifests,
  locating a project, `.path` addresses, provisioning or worktrees, it says
  these concern folders on this machine, and that parent links, full
  identifiers, ownership, inheritance, overrides and `--scope` are what every
  store keeps.
- **Every harness** (spec Design 1.8): no skill step depends on a
  Claude-only feature; every `` !`cmd` `` keeps its line in the skill's
  "Document command summary" (`tests/test_shipped_text.py:358-369`).
- **Links.** A step that renames or removes a heading runs
  `git grep -n '<file name>#'` over the live documents and fixes every
  inbound anchor in the same step, so `link_problems`
  (`tests/test_docs_describe_3_0.py:204-231`) stays green at each boundary.
- **Formatting.** Every file in scope is formatted once, in Step 0b's
  formatting-only commit, before any content changes. Each later step runs
  `pnpm exec prettier --write <file>` on the files it changed, which then
  changes only what that step wrote, and the step's diff is read after it
  (criterion 39). At `a9f316a8` prettier alone changes about 108 lines of
  `README.md`, 131 of the TCW-99 `design.md`, 72 of
  `skills/configure/references/personal.md` and 39 of `skills/README.md`
  (the plan review's measurement; the first draft's 278 and 66 were wrong).
  A file first found to need a change after Step 0b (by the scans of Steps
  24 and 25, or the grep of decided while planning, 20) and not formatted
  there is formatted in its content step, and the round names it and gives
  its `git diff --word-diff -w`, so the review can read its content apart
  from its formatting.
- **Starting points** (spec Design 1.2): before a step changes a file, it
  reads that file's rows of Step 0's list 2 (the passages siblings changed
  only partway) and rewrites each for 4.0; the implement round records, per
  row, what the passage now says. A passage a sibling rewrote in full for
  4.0 (its own prompts and procedures, list 3) is kept as written, unless
  the scan or the grep finds a 3.x form in it, which is then fixed here
  (decided while planning, 15).
- **Placeholders.** A 4.0 folder path is never written `<project>/<…>`,
  which P11 refuses; it uses other names, such as `<parent folder>/<folder>`.
- **`tcw capabilities add` keeps `--status`.**
  `test_the_capabilities_skill_changes_records_with_the_code`
  (`tests/test_shipped_text.py:404-410`) requires `--status` on every line
  naming that command, so a line about `--parent` on `add` either writes
  `--status` too or does not name the command.

## Decided while planning

Each settled here, preferring the simpler and safer option.

1. **The scan's self-tests land in Part 1; its scan of every live document
   lands last.** `tests/test_docs_describe_4_0.py` is created in Step 1 with
   `UNMIGRATED_RECORDS`, `three_x_problems` and the tests of spec 9.2 "Its own
   tests" (scratch documents only), and Step 28 adds the one test that scans
   every live document. Reason: 9.4 (h) needs `THREE_X_PATTERNS` in Part 1,
   and the self-tests can be written red first and pass at once, while the
   live test fails until Part 3 ends. Spec Design 11 places "the scan's test"
   in Part 3 for that last reason only, which this keeps.
2. **`THREE_X_PATTERNS` has 18 entries, one per regular expression**, each a
   `(pattern, reason)` pair as `PATTERNS` is, so `scan` reads it unchanged.
   Each reason starts with its row's label (`P5:`) and ends
   `(scan: TCW-117)`. Reason: spec 9.4 (h) counts 18 entries, and one shape
   for both tables keeps `scan` simple.
3. **The allowance is found by block, after the scan.** `three_x_problems`
   runs `scan(text, THREE_X_PATTERNS, flags=0)` over the whole file, then
   drops a hit whose block (from `doc_vocabulary.blocks`, the one that holds
   the hit's line) contains `tcw migrate` or `migration-guide-3.X-to-4.0.0`,
   unless that block is a line of a fenced block, which is never dropped
   (decided while planning, 17). Reason: `scan`'s line numbers stay true, and
   a fenced line can borrow the allowance neither from another line nor from
   its own comment.
4. **The migration guide links guides by file in Part 1**, and Part 2 adds an
   `#anchor` only once the heading exists (Step 9 adds
   `multi-repo.md#…` for the provisioning bound). Reason: `link_problems`
   checks an anchor into an owned guide against its headings, which Part 2
   writes.
5. **The removed commands' printed lines are given word for word, split at
   the command.** "Scripts, hooks and agent instructions" holds a mapping
   table whose header is `3.x command typed | the rest of the line`, one row
   per removed command, each copied from a scratch run on `v4` (for example
   `tcw init` | is now `tcw project new`), and says each is refused with the
   exit code the run shows (2 when planned). Decided by the dispatching
   session, 2026-10-22 (plan review Q1.2): the header's first cell begins
   `3.x`, so its first column is exempt from Step 2 (d) and the reader gets
   the exact line; the first draft's "by their shape" lost the words. The
   spec now says so (Design 2.10 (d), 4.1 (g)).
6. **TCW-116's handoffs of 2026-10-22 21:30 and 21:53, which came after the
   spec's revision (21:23), are answered in the migration guide** as Design
   2.4 (m) to (s), and the quoted line of (f), in Step 3. Reason: they state
   TCW-116 behavior the guide's reader meets (a move across filesystems,
   `--no-jira` needing no credentials, whose Jira settings a run uses, a hand
   edit between runs, what A12 and B10 mean, and three printed lines to quote
   as written); they add facts, not decisions. The spec now holds them as
   rows H19 and H20 and in criterion 3.
7. **`KEY_PATHS` in `tests/test_configuration_text_home.py` follows the 4.0
   keys.** When `projects.md` loses its `projects.*` headings (Step 22), the
   24 `projects.*` paths leave `KEY_PATHS`, and `parents` and `children`
   join it, each with one heading and a label read from the code's
   `PERSONAL_KEYS`; the count assertion (`:63`, 57 at `2adac9c9`) becomes 33:
   57, less TCW-112's two `extends` paths, less the 24 `projects.*` paths,
   plus `parents` and `children`. `children`, which TCW-108 and TCW-109 put
   in `LOCAL_ONLY_KEYS` rather than `PERSONAL_KEYS`, is labelled `Shared:`
   (forced, not chosen: the test's rule is that every label but `Shared`
   equals `PERSONAL_KEYS`, `tests/test_configuration_text_home.py:8-10`), and
   its section says it may also be listed in `.tcw/tcw-config.local.yaml`. `tcw-version` is not added: the
   list is hand-kept and need not hold every key (its docstring), and its
   section in `work.md` is enough. Reason: the test's expected text is a 3.x
   key list this item removes (spec Design 9.1 allows such a change, listed
   with its reason).
8. **Existing `GIT_ALLOWED` phrases are kept in place.** The sentences in
   `personal.md` ("git worktree of the project") and `stores.md` ("opened
   from a linked worktree", and the anchor of configuration.md's example)
   are kept, reworded around the phrase for 4.0, and the heading
   "Example: keeping git in step with each stage change (something your
   project adds)" in `docs/guide/configuration.md` keeps its exact words.
   Reason: removing a phrase fails `test_every_git_allowance_is_still_needed`,
   and changing `GIT_ALLOWED` beyond the one new phrase breaks criterion 42.
   If a kept sentence would be false in 4.0, it is reported to the
   dispatching session, not edited around.
9. **A mistyped command is written in prose, its suggestions in code spans**
   (rule above). Reason: `_check` fails on `tcw new` in backticks. Spec 4.1
   (g) wrote "`tcw new`" with backticks; the spec now says prose (plan
   review Q1.3).
10. **P12 matches only a 3.x pointer.** 4.0's `tcw capabilities show` and
    `tcw taxonomy show` print `overrides: <full id>` for an override (TCW-112
    plan, choice 7 and its "Records" step; TCW-113 plan choice 8 only puts
    `overridden by:` on the line after it), and the first P12,
    `^\s*overrides:`, refused that line in a fenced example. P12 is now
    `^\s*overrides:\s*[^\s./]+/` (spec 9.2): a 3.x pointer's first part has
    no dot (`core/cap-…`, `<alias>/<…>`), and a 4.0 full identifier always
    has one before its first `/` (`<project>.<namespace>/<id-path>`, TCW-110
    spec, Goals 1). So a document may show real `show` output, `overrides:`
    line included, in a fenced block. Step 0 item 8 checks on `v4` that a
    printed full identifier holds that dot; if one does not, the case is
    reported and P12 is not loosened. Decided by the dispatching session,
    2026-10-22 (plan review D1): it keeps the one thing only P12 catches, a
    placeholder pointer, and drops the first draft's ban on showing real
    output where readers of the taxonomy guide will look for it.
11. **No reference file of a skill is renamed or split.** The eval routing
    checks name reference files by path (`tests/test_skill_path_pointers.py`;
    `evals/evals.json`'s `opened` assertions), and the configure router must
    link every reference (`tests/test_configuration_text_home.py:72-82`).
12. **`docs/use-cases.md`'s UC-3 gap "TCW-98 and TCW-99 will change how a
    parent sees children" is removed without saying TCW-99 is done**, since
    TCW-99 completes only at TCW-118; the document describes 4.0, where that
    change has landed. Reason: the spec's first "removed: TCW-99 is done"
    (Design 6.4) would be false on `v4` at the time of writing; the spec now
    says so.
13. **One formatting-only commit comes before Part 1** (Step 0b). It formats
    every Markdown file in scope that this item will change, the TCW-99
    `design.md` included, and changes nothing else; each part's commit then
    shows only content. Decided by the dispatching session, 2026-10-22 (plan
    review D2): CI does not run prettier (`.github/workflows/test.yml` runs
    `pytest` and `pnpm check:build`; `prettify:check` is reached only through
    `pnpm typecheck`, `package.json:15-17`), so criterion 39 is a local rule,
    but formatting mixed into the content commits would bury about 30 "the
    review lists" criteria under table padding. The spec's Design 11 and
    criterion 43 now say so.
14. **Every scratch run is isolated from the person's own files** (Words
    used below, "A scratch run"; Step 0 items 2 and 9). Decided by the
    dispatching session, 2026-10-22 (plan review M1): the first draft asked
    for "a user-wide file holding `not_tags`" without saying where, and the
    only place it could land was the person's real
    `~/.config/tcw/config.yaml`, which every `tcw` on this machine, 3.0.2
    included, would then read. Moving `HOME`, `XDG_CONFIG_HOME` and
    `XDG_CACHE_HOME` into `<S>` is checked, not assumed: the state of the
    real user-wide file and store cache is recorded before the first run and
    compared at Steps 5, 18 and 30.
15. **A 3.x form in a list 3 passage is fixed here.** If a passage a sibling
    rewrote in full still holds a 3.x form when Steps 16, 24 or 25 reach it,
    this item fixes it in place with the smallest change of wording, lists
    the fix under "Departures found" in the implement round with the sibling
    it came from, and tells the dispatching session; Part 3 then ends with
    the suite passing. Decided by the dispatching session, 2026-10-22 (plan
    review M2): Step 28's scan of every live document fails on any hit left
    unfixed, so "report, do not change" could never end Part 3 green, and
    every sibling is complete by the time this item is implemented. At
    `2adac9c9` three list 3 files have such hits (`docs/lifecycle/abstraction.md:92`,
    `tcw/work/prompts/plan.md:38`, `tcw/work/procedures/audit-backlog.md:27`),
    which TCW-111 Step 15, TCW-114 Step 20 and TCW-113 Step 17 plan to
    rewrite.
16. **The migration guide's command test reads the surface `--help` shows**
    (Step 2 (d)). Decided by the dispatching session, 2026-10-22 (plan review
    M3): `command_problem` collects every option the parser registers
    (`tests/test_shipped_text.py:305`), including those registered with
    `help=argparse.SUPPRESS`, which TCW-113 and TCW-114 keep (`--local`, and
    `--project` and `--blocks` on `tcw work`) so that they can print a
    refusal; so `tcw work new "t" --project app` would pass it. `_check`
    against the tree `_walk` reads from `--help`
    (`tests/test_documented_cli_surface.py:173-216`) refuses them, is the
    check every live document is already held to, and needs no list of
    removed flags kept by hand, which an explicit list would. (d) runs both,
    since `command_problem` also checks procedure and stage names.
17. **A fenced line never carries the allowance.** `three_x_problems` drops
    a hit only when its block is a paragraph, list item or table row naming
    `tcw migrate` or the guide; a hit on a fenced line always stays, even
    when that same line names `tcw migrate`. Decided by the dispatching
    session, 2026-10-22 (plan review D3): spec Design 1.6 (b) forbids a 3.x
    example in a fenced block, and the first revision's "one line of a
    fenced block" let one pass by its own comment; the spec's 9.2 now says
    so.
18. **A Markdown file under `tests/` that describes test data is fixed only
    in its words.** Step 28 scans every tracked Markdown file outside the
    archival trees, which includes descriptions such as TCW-116's planned
    `tests/migrate/data/README.md`. If one names a 3.x form, the paragraph
    holding it gains the words that the data is what `tcw migrate` converts
    (true of every such file), so the allowance covers it; no data file
    changes. The fix is listed as in decided 15. Decided by the dispatching
    session, 2026-10-22 (plan review Q2): it keeps TCW-116's test data
    byte for byte and keeps the scan whole, with no list of excluded files.
    At `a9f316a8` the only such file with a hit is
    `tests/cli/scenarios/13-release-integrity.md`, which Step 25 rewrites.
19. **Each sibling is past review before Step 0, and the guide is checked
    again after the last sibling commit.** Step 0 item 1 requires each of
    TCW-106 to TCW-116 at qa or completed, not merely past implement; and
    Step 30 runs `git log <base>..HEAD -- tcw/`, leaving out this item's own
    commits, and, if anything changed, redoes Step 3's dry run and the other
    runs whose output a document quotes, and compares. Decided by the
    dispatching session, 2026-10-22 (plan review S2): a review or qa fix to
    a sibling during Part 3 (TCW-116's plan was still being fixed when this
    plan was written) would otherwise never reach the guide written in
    Part 1.
20. **The root `tcw-config.yaml` wording is found by a grep.** Step 24 runs
    `git grep -nE '(^|[^/.a-z-])tcw-config(\.local)?\.yaml'` over the live
    documents and decides each line: a line meaning the project's file says
    `.tcw/tcw-config.yaml`; a line about a 3.x project names `tcw migrate`.
    At `2adac9c9` it reaches lines no step names:
    `skills/documentation-sync/SKILL.md:15`, `:31`,
    `skills/setup/references/jira.md:33` and `docs/procedures/create-work.md:1`.
    Decided by the dispatching session, 2026-10-22 (plan review S4): the
    scan has no pattern for that name, which is still the file's name in
    4.0, so no other check finds those lines.

## Step 0 — start from what the earlier items left

No file in the repository changes. Everything goes to `<S>` and into the
implement round.

1. **Confirm the order.** `git log --oneline` on `v4` shows each of TCW-106
   to TCW-116 completed (its last implement commit, and its ticket at qa or
   completed, read with `tcw work show <key>`, so no review fix is still to
   come; decided while planning, 19); if one has not, stop and report it.
2. **Tools**, in this order. First `pnpm install --frozen-lockfile` (the
   worktree has no `node_modules` at `2adac9c9`, so `pnpm exec prettier`
   fails there), then `pnpm exec prettier --version` prints 3.9.9;
   `.venv/bin/tcw --version` prints `tcw 4.0.0`; `tcw --version` prints
   `tcw 3.0.2`. The lifecycle CLI's absolute path is recorded as
   `LIFECYCLE_TCW` (`pyenv which tcw` where the `tcw` on the path is a pyenv
   shim, else `command -v tcw`), because a shim looks for its own files under
   `$HOME`, which a scratch run moves. The scratch environment is made:
   `<S>/home/.gitconfig` (a scratch `user.name` and `user.email`), the empty
   folders `<S>/xdg` and `<S>/cache`, and `<S>/scratch-env.sh`, which runs
   its arguments under `env` with `HOME`, `XDG_CONFIG_HOME` and
   `XDG_CACHE_HOME` set as "A scratch run" says and with `-u` for each
   `TCW_JIRA_*` and `TCW_PROJECT_*` name that `env` lists in the calling
   shell. It is checked once: `<S>/scratch-env.sh .venv/bin/tcw project
config --origin` in a scratch project names `<S>/xdg/tcw/config.yaml` as the
   user-wide file, and `<S>/scratch-env.sh env | grep -c '^TCW_JIRA'` prints 0.
3. **Record `<base>`**: `git rev-parse HEAD`, the commit before this item's
   first (criterion 42's `<base>`).
4. **The surface dump** (`<S>/dump_help.py`, above). Also the exit codes:
   `tcw/exit.py` (TCW-108 adds 7), `tcw/cli_help.py`'s `EXIT_CODES`.
5. **Scratch tools**: `<S>/scan_one.py <file>…` (the scan of Step 1 run over
   named files, with the allowance, printing `file:line: text — reason`),
   `<S>/scan_records.py` (the same over `docs/taxonomy/` and
   `docs/capabilities/`, used in Step 27), `<S>/grep-9-3.sh` (the spec's
   grep, byte for byte). Baselines: the grep's output (125 lines at
   `2adac9c9`; expected far fewer once TCW-112 to TCW-115 have run) and the
   scan's output over every live document, both saved as
   `<S>/baseline-grep.txt` and `<S>/baseline-scan.txt`. At `a9f316a8` the
   scan finds about 282 hits in 30 live documents (the plan review's count;
   the first draft's 230 was a slip in adding them up), the most in
   `skills/configure/references/projects.md` (50), `personal.md` (30),
   `docs/use-cases.md` (25) and `README.md` (22).
6. **List 1: what each sibling left in live documents, and the tests it
   changed that read documents.** From each implement round, and where a
   round has no list, from the plan step named. The implement round of this
   item copies it, one row per passage, with a column for what this item
   makes it say:

    | Sibling | What it changed in live documents (plan step)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Kind                                                                |
    | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
    | TCW-106 | `.tcw/tcw-config.yaml` and `tests/test_repo_config_pair.py` (Step 5a); records (Step 7); no live document (Step 8 defers all)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | records only                                                        |
    | TCW-107 | `skills/work/SKILL.md:115`, the exit-5 sentence (Documentation Sync); records (Step 11)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | partway (D107, H2)                                                  |
    | TCW-108 | the exit-code tables of `docs/guide/cli.md:140-148`, `skills/work/references/commands.md:33-41` and the record `cli/rely-on-one-output-contract` (Step 3, with row 7 and rows 3 and 5 stripped of `upstream` and the `jira` block); new `tests/test_exit_code_tables.py`; records (Step 14)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | partway (H4)                                                        |
    | TCW-109 | records only (Step 12); `tcw config show`'s help (Step 9, then renamed by TCW-115)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | records only                                                        |
    | TCW-110 | records (Step 16); `tests/test_identifier_sweep.py` (code only)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | records only                                                        |
    | TCW-111 | `tcw/work/prompts/plan.md` step 6's `--nest` sentence, `docs/lifecycle/abstraction.md` (interface list, the bounded-folder bullet, one "Abstract spine" sentence) and their tests in `tests/test_shipped_prompts.py` and `tests/test_docs_describe_3_0.py` (Step 15); `docs/guide/examples/commit-item-after-move.sh` (Step 16); records (Step 18)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | its own, in full                                                    |
    | TCW-112 | Step 5a: `README.md:360`, `:371`, `:421`, `:432`; `skills/taxonomy/SKILL.md:86`, `:111-115`, `:132`; `skills/capabilities/SKILL.md:26`, `:89`, `:94`, `:122-123`, `:130`, `:138`, `:175`; `skills/configure/SKILL.md:4`; `skills/configure/references/stores.md:108-114`, `projects.md:6`, `:55`, `:117`, `:343-371`, `personal.md:145-148`; `skills/setup/references/taxonomy.md:18`; `docs/guide/taxonomy-and-capabilities.md:37-38`, `:57-64`, `:212-213`; `docs/guide/cli.md:14`; `docs/guide/multi-repo.md:257-269`; `docs/guide/linking-and-validation.md:17`, `:139`; `KEY_PATHS` loses the two `extends` keys. Step 19: `skills/capabilities/SKILL.md:29`, `:141-147`; `docs/guide/taxonomy-and-capabilities.md:79`, `:222-227`. Step 23: the command-table rows of the taxonomy and capabilities skills. New `tests/test_no_3x_inheritance.py` (code and tests only)        | partway (H12, D112)                                                 |
    | TCW-113 | Step 12b: `README.md:413`, `skills/capabilities/SKILL.md:176`, `docs/guide/taxonomy-and-capabilities.md:32`, `:98` (as far as `--local`); Step 17: `tcw/work/procedures/audit-backlog.md` and `agents/backlog-auditor.md` (full identifiers, `--scope down`), with `tests/test_shipped_procedures.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | partway (H16) for Step 12b; its own, in full, for Step 17           |
    | TCW-114 | Step 7: `skills/work/SKILL.md:4`, `:93-100`, `:107-110`, `:111-112`; `skills/work/references/commands.md:11`, `:19`; `skills/capabilities/SKILL.md:153`, `:181`; `skills/configure/references/projects.md:170`, `:199`; `docs/guide/cli.md:150`; `docs/guide/jira.md:235`; `docs/guide/multi-repo.md:141`, `:179-184`, `:187`; `docs/guide/work.md:332`, `:351`; `README.md:608`; `docs/use-cases.md:161`, `:213-216`; records (its change to `tcw/work/procedures/audit-backlog.md:28` is left out here: TCW-113 Step 17, which lands after it, rewrites those lines in full, so they are list 3 only). Step 20: `tcw/work/prompts/plan.md` step 6 (final form), `docs/lifecycle/abstraction.md` (**move** entry). Step 6: the three command checks skip `-C <one token>`. Removed rows in `tests/test_migration_guide.py` and `tests/doc_vocabulary.py`'s text references (Step 7) | partway (H14) for Step 7's documents; its own, in full, for Step 20 |
    | TCW-115 | Step 3: every live Markdown file naming `tcw init`, `tcw projects list`, `tcw config show` or `tcw provision`, by script, as far as the new name (43 files at `d2d02829`: `README.md`, 18 capability and 2 taxonomy descriptions, 4 guides, `docs/use-cases.md`, 15 files under `skills/`, `tcw/work/procedures/search.md`, `tests/cli/scenarios/13-release-integrity.md`); the list is in its implement round, copied from `rename-report.txt`                                                                                                                                                                                                                                                                                                                                                                                                                                      | partway (H15)                                                       |
    | TCW-116 | records (Step 13); `tests/test_ledger_3_0.py` reads either state-file name (Step 12); no live document (Step 28 defers all)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | records only                                                        |

    For every row marked "partway", the passages are re-found by their words
    on `v4` and listed as **list 2** (file, line on `v4`, the words now
    there). The rows marked "its own, in full" are **list 3**: they are read,
    scanned and left as their sibling wrote them, unless the scan or the grep
    finds a 3.x form, which is then fixed here with the smallest change of
    wording, listed under "Departures found" with the sibling it came from,
    and reported to the dispatching session (decided while planning, 15).

7. **Tests whose expected text this item will change**, read on `v4` and
   listed: `KEY_PATHS` and its count (`tests/test_configuration_text_home.py:38-63`;
   57 now, 33 after Step 22, decided while planning, 7);
   the index test (`tests/test_docs_describe_3_0.py:438-444`); any test that
   asserts a phrase in a document this item rewrites: at `2adac9c9`,
   `test_the_capabilities_skill_changes_records_with_the_code`
   (`tests/test_shipped_text.py:396-410`: every `tcw capabilities add` line
   has `--status`, and "same change as the code" and "No flipping at
   completion" stay), `test_the_pause_skill_places_the_handoff_by_stage`
   (`:372-380`), `MOVED_PHRASES` and the README structure tests
   (`tests/test_docs_describe_3_0.py:324-330`, `:407-435`: "Overview" is
   followed by "Why taxonomy and capabilities live in the repository", every
   Contents link resolves, the Work section has a Filesystem then a Jira
   heading), `test_harness_points_at_where_a_subagent_is_never_required`
   (`:343-357`, the work skill's heading "Rules: no project text changes"),
   `tests/test_exit_code_tables.py` (TCW-108), and any added by TCW-109 to
   TCW-116 that a fresh `grep -rln 'README.md\|docs/guide\|skills/' tests/`
   finds. Every one keeps passing unless its expected text is a 3.x passage
   this item rewrites, which is then changed in the step that rewrites the
   passage and listed with its reason (criterion 33).

8. **The facts each document needs, re-found in the code**, recorded as a
   short table per document, each fact with the file and line on `v4` that
   shows it: for example the manifest entry's shape
   (`tcw/store/manifest.py`, `_TOP_KEYS` at `:37` and the entry parser at
   `:36-58` at `2adac9c9`), the allowed personal keys (`PERSONAL_KEYS` and
   `LOCAL_ONLY_KEYS` in `tcw/config.py`), `INHERITED_KEYS` (TCW-109), the
   exit codes, `REMOVED_COMMANDS` (`tcw/cli_suggest.py`, TCW-115), the
   provisioning bound (`tcw/provision.py`'s `_bound_problem`, TCW-115), the
   migration headings and line forms (`tcw/migrate/`, TCW-116), the
   finding wordings of `tcw validate` (`tcw/validate.py`, `tcw/object_folders.py`),
   and that a full identifier as `show` prints it after `overrides:` holds a
   dot before its first `/` (a scratch run; decided while planning, 10).
9. **The person's own files, before any scratch run.** The state of
   `~/.config/tcw/config.yaml` (its `shasum -a 256`, or that it does not
   exist, as on 2026-10-22) and `ls -A ~/.cache/tcw/stores`, read with the
   real `HOME`, saved as `<S>/real-files-before.txt`. Steps 5, 18 and 30
   read them again and compare; a difference stops the work and is reported
   (decided while planning, 14).
10. **The formatting list** for Step 0b: every Markdown file a step of this
    plan names, every live document with a hit in the two baselines or in the
    grep of decided while planning, 20, and the TCW-99 `design.md`, less what
    `.prettierignore` excludes and less the files this item creates; saved
    as `<S>/format-list.txt`.

**Done when:** the implement round holds lists 1 to 3, the tests list, the
two baselines, the surface dump's path, `<base>`, the real files' state and
the formatting list.

## Step 0b — the formatting-only commit

Spec Design 11; criteria 39, 43; decided while planning, 13.

1. `pnpm exec prettier --write $(cat <S>/format-list.txt)`.
2. `git diff --word-diff -w` is read whole. It must show only Markdown
   markup: table padding and dividers, list markers and indentation, blank
   lines, emphasis markers and escapes. A file whose diff changes a word is
   restored (`git checkout -- <file>`), left out of this commit and
   formatted in its content step instead, and named in the round.
3. Bare `.venv/bin/pytest` from the worktree's root. A test that fails
   because it compares captured text (the prompt fallback capture in
   `tests/fixtures/prompt_fallback/`, which holds procedure and skill text)
   is fixed by regenerating that capture with its own script
   (`tests/fixtures/prompt_fallback/capture.py`), and the difference is read:
   only formatting. Any other failure: the file that causes it is restored
   and left out as in 2.
4. Commit only the formatted files and any regenerated capture, with a
   message saying the commit formats the documents TCW-117 changes and
   changes no content.

**Done when:** the round names the commit, the number of files, the files
left out and why, and the suite's last line; `git diff --word-diff -w` of the
commit shows only markup (criterion 43).

## Part 1 — the migration guide and its test

### Step 1 — the 3.x table, `scan`'s case, and the scan's own tests

Spec Design 9.2; criteria 31 (the table, the self-tests), 42.

**Tests first**, new `tests/test_docs_describe_4_0.py`, written before the
table exists, so the import fails (red), then the table is added:

- `test_the_table_is_p1_to_p12`: 18 entries; their labels, read from each
  reason's prefix, are `P1 P2 P3 P4 P5 P5 P5 P6 P6 P6 P7 P8 P8 P9 P10 P11 P11
P12` in order; each pattern is exactly the spec's (the 18 strings written
  into the test); every reason ends `(scan: TCW-117)`.
- `test_unmigrated_records_are_the_two_ledgers`: `UNMIGRATED_RECORDS ==
("docs/taxonomy/", "docs/capabilities/")`, and the file's text holds the
  comment of spec 9.2 naming TCW-118.
- `test_each_pattern_fails_a_scratch_document` (parametrized, 18 cases): one
  sample per entry, put in a paragraph of a document named
  `docs/guide/scratch.md`, gives a problem from `three_x_problems`. The
  samples: `` `tcw init --id x` ``; `` `tcw work new "t" --project core` ``;
  `` `--blocks` ``; `` `--local` ``; `extends add core`; `taxonomy.extends`;
  `extends: [core]`; `an upstream project`; `upstream:`;
  `projects.upstream`; `item.yaml`; `tcw://C/billing`; `tcw://core/T/billing`;
  `cap-1a2b3c`; `not_tags`; `<project>/<folder>`; `tcw/TCW-12-add-export`;
  and a fenced line `overrides: core/billing`, which no other entry matches.
  Each case asserts that a problem's reason starts with its own entry's
  label (`P12:` for the last), not only that some problem is given, so a
  sample another entry also matches cannot hide a broken pattern (plan
  review S1).
- `test_the_same_hit_beside_tcw_migrate_passes`: each sample with
  "Run `tcw migrate` to convert it." in the same paragraph, and each with a
  link to `../migration-guide-3.X-to-4.0.0.md` instead, gives no problem.
  For P12 the paragraph is unfenced: its first line is
  `overrides: core/billing` and its second the `tcw migrate` sentence, since
  `^` matches at the start of a block.
- `test_a_fenced_line_cannot_borrow_the_allowance`: a fenced block whose
  first line is `item.yaml` and whose second is `tcw migrate` gives one
  problem, and so does a fenced block of the one line
  `item.yaml  # tcw migrate converts this` (spec Design 1.6 (b), 9.2;
  decided while planning, 17).
- `test_the_ledgers_are_left_out_while_unmigrated`: a sample under
  `docs/capabilities/x/description.md` and `docs/taxonomy/x/description.md`
  gives no problem.
- `test_4_0_forms_pass`: `tcw-work-item.yaml`; a fenced manifest with a
  top-level `projects:` line and an entry below it; the prose "the four TCW
  projects:"; the fenced 4.0 `show` lines `overrides: app.capabilities/billing`
  and `overrides: <full id>`; `tcw work list --project app` after a `tcw work new` code span
  in the same paragraph (P2 stops at a backtick); and
  `.tcw/tcw-config.local.yaml` and `.tcw/tcw-manifest.local.yaml` (P4 needs
  `--` before `local`).
- `test_case_is_kept_for_the_3_0_table_and_dropped_for_the_3_x_table`:
  `scan("TCW WORK START", PATTERNS)` gives a hit;
  `scan("TCW projects list", THREE_X_PATTERNS, flags=0)` gives none, and
  `scan("tcw projects list", THREE_X_PATTERNS, flags=0)` gives one.

**Changes**

- `tests/doc_vocabulary.py`: `THREE_X_PATTERNS` after `PATTERNS`
  (`:19-51`), its 18 `(pattern, reason)` pairs in the spec's order with the
  reasons "P1: removed commands (TCW-115) (scan: TCW-117)" and so on, each
  naming the item the spec's table names; a comment above it saying it is
  matched case-sensitively and why ("TCW projects" is prose, `tcw projects`
  a command). `scan` (`:122-142`) gains `flags=re.IGNORECASE` and compiles
  with it (`:128`); its docstring and the module's (`:1-13`) say so. No entry
  of `PATTERNS` changes (criterion 42).
- `tests/test_docs_describe_4_0.py`: the module docstring (what a live
  document is, the allowance, why the ledgers wait for TCW-118);
  `UNMIGRATED_RECORDS` with the spec's comment, verbatim; `ALLOWANCE =
("tcw migrate", "migration-guide-3.X-to-4.0.0")`;
  `three_x_problems(rel, text) -> list[str]` (decided while planning, 3 and
  17: a hit on a fenced line is never dropped);
  the tests above. It imports `DOC_FILES`, `REPO` from
  `tests.test_documented_cli_surface` only in Step 28.

**Proves it:** the new tests (red on import first, then green);
`tests/test_doc_vocabulary.py`, `tests/test_docs_describe_3_0.py` and
`tests/test_shipped_text.py` unchanged and green (every caller keeps the
case-insensitive default); `git diff <base> -- tests/doc_vocabulary.py`
shows `PATTERNS` untouched.

### Step 2 — the migration guide's test, red

Spec Design 9.4; criteria 1, 5, 7 (their tested halves).

**Creates** `tests/test_migration_guide_4_0.py`, built like
`tests/test_migration_guide.py`, importing its `sections`, `section`,
`cells` and `tables` (`:36-76`), `link_problems`
(`tests/test_docs_describe_3_0.py:204`), `command_problem`
(`tests/test_shipped_text.py:283`), `_invocations`, `_walk` and `_check`
(`tests/test_documented_cli_surface.py:173-216`) and `THREE_X_PATTERNS`. A
module-scoped fixture builds the help-derived tree with `_walk([], tree)`,
as that module's `tree` fixture does (`:186-191`). Its own
helpers: `mapping_tables()` (tables whose header's first cell, backticks
removed, begins `3.x`), `first_cells()`, `epic_table()` (the one table in
`## The epic-parts flow, step by step` whose header is `# | 3.x step | 4.0`),
and `exempt_blanked(text)`, which blanks every mapping table's first cell
and the epic table's second cell keeping offsets (as
`_without_first_cells`, `tests/test_migration_guide.py:1056`, does for the
2.x guide).

- (a) `test_the_sections_are_in_order`: the level-2 headings are exactly
  spec 2.2's eight, in order.
- (b) `test_every_3x_name_has_a_row` (parametrized over `THREE_X_NAMES`): the
  name is a substring of a first cell, backticks removed. `THREE_X_NAMES`:
  `tcw init`, `tcw projects list`, `tcw config show`, `tcw provision`,
  `tcw work new --project`, `tcw work edit --blocks`, `--local`,
  `tcw taxonomy extends add`, `tcw taxonomy extends rm`,
  `tcw capabilities extends add`, `tcw capabilities extends rm`,
  `taxonomy.extends`, `capabilities.extends`, `tcw-config.yaml`,
  `tcw-config.local.yaml`, `not_tags`, `projects.parent`,
  `projects.children`, `projects.upstream`, `projects.<id>.repository`,
  `projects.<id>.jira`, `work.path: /`, `work.path: ~`,
  `<component>.repository`, `meta.yaml`, `item.yaml`, `overrides:`,
  `cap-1a2b3c`, `<project>/<folder>`, `tcw://C/`, `tcw://W/`, `tcw://T/`,
  `tcw://core/T/`, `TCW Item`, `"schema": 1`, and the 3.x `--origin`
  comment's shape, `# <layer>: <file>` (3.x's `_Writer.comment`, `git show
v3.0.2:tcw/config_cli.py`, lines 119-137).
- (c) `test_every_row_says_what_replaces_it`: no mapping row's second cell
  is empty.
- (d) `test_every_4_0_command_resolves`: every invocation `_invocations`
  finds in `exempt_blanked(GUIDE)` gives `_check(span, tree) is None` and
  `command_problem(span) is None` (decided while planning, 16).
- `test_a_hidden_flag_is_refused`: the (d) check, run on
  `tcw work new "t" --project app`, `tcw work edit x --blocks y` and
  `tcw capabilities list --local`, gives a problem for each. A flag the code
  on `v4` does not hide from `--help` is dropped from the case and reported
  (Design 1.1).
- (e) `test_the_epic_table_has_rows_a_to_f`: its first cells are `a` to `f`.
- (f) `test_the_exit_table_is_0_1_2_3_5`: the one table in
  `## Migrating one project` whose header's first cell is `Exit` has rows
  `0`, `1`, `2`, `3`, `5`, in that order.
- (g) `test_every_link_resolves`: `link_problems(GUIDE_REL, GUIDE) == []`.
- (h) `test_every_scan_pattern_has_a_row` (parametrized over the 18
  entries): the pattern, compiled with no flags, `search`es at least one
  first cell with its backticks removed and its spaces trimmed.
- `test_before_you_start_links_the_2_8_guide`: the section holds a link to
  `migration-guide-2.8-to-3.0.0.md` (criterion 2's link).
- `test_related_projects_come_first`: the first paragraph of
  `## Migrating one project` links or names `## Migrating related projects`
  (spec 2.4 (k)).

The module reads `docs/migration-guide-3.X-to-4.0.0.md` at import, so every
test errors until Step 3 writes it: the red state. It is committed with
Step 3, never alone.

**Proves it:** `.venv/bin/pytest tests/test_migration_guide_4_0.py` errors
(no file), recorded in the round.

### Step 3 — the migration guide

Spec Design 2.1 to 2.10; criteria 1 to 10. **Creates**
`docs/migration-guide-3.X-to-4.0.0.md`, written for a person and an agent
alike: steps in order, each command written out. Its path starts
`docs/migration-guide-`, which `ARCHIVAL`
(`tests/test_documented_cli_surface.py:38-51`) excludes from the live
checks, so Step 2's test is what checks it.

Each section, with the spec letters it holds and how each fact is checked on
`v4` (layer 3 or 4 of the method above; every run is in `<S>/runs/3/`):

- `## Before you start` (2.3 (a) to (f)): (a) links
  `migration-guide-2.8-to-3.0.0.md`; (b) commit or back up, "a folder that
  is not in git has no way back"; (c) everyone upgrades the CLI and the
  plugin together, since 4.0 refuses a 3.x project (run: `.venv/bin/tcw work
list` in a 3.x scratch project, exit 1, TCW-106's refusal quoted); (d) the
  install commands, copied from the README's "Installation" section
  (`README.md:64-138`) as Step 14 leaves it, re-copied at Step 14 if they
  change; (e) Jira credentials or `--no-jira`; (f) CI and automation: limit
  to `tcw-cli<4` (`pipx install 'tcw-cli<4'`) until migrated, raise in the
  same change.
- `## Migrating one project` (2.4 (a) to (s), (k) first; (m) to (s) as
  decided while planning, 6):
    - (k) the opening sentence sends a project with parents or children to
      `## Migrating related projects` before anything is run;
    - (a) `tcw migrate --dry-run` first; (b) the three printed lists by their
      headings (`refused:`, `needs attention:`, `reads differently in TCW 4:`),
      each with what it means, and the line forms (`write <path>: …`,
      `move <old> -> <new>: …`, `delete <path>: …`,
      `edit <KEY>: … TCW Item: <old> -> <new>`, `would ` first in a dry run;
      `<An|Dn> <where>: <text>`; `<Bn> <where>: <why>; <what to do>`), shown
      in a fenced block copied from a real dry run (run: a scratch 3.x project
      made with the lifecycle CLI's `tcw init --id old`, with a `meta.yaml`,
      an `item.yaml` and the scratch user-wide file
      `<S>/xdg/tcw/config.yaml` holding `not_tags`, never the person's own
      `~/.config/tcw/config.yaml` (decided while planning, 14), so all three
      lists print; every command a scratch run; the output pasted in the
      round, criterion 3);
    - (c) `--no-jira`: files only, never contacts Jira, keeps a run off a live
      board; a later `tcw migrate` converts only the tickets; until then
      4.0's `tcw work list` leaves out tickets still holding a 3.x value with
      one warning naming their keys and `tcw migrate` (checked against
      TCW-116's and TCW-110's tests, named in the round);
    - (d) a real run whose plan cannot reach Jira writes nothing and says to
      use `--no-jira` (TCW-116's test, named);
    - (e) the exit table, rows 0, 1, 2, 3, 5, meanings copied from
      `tcw migrate --help` and TCW-116 Design 1.6; a Jira failure keeps 5
      (unreachable, limiting) or 1 (credentials missing or refused);
    - (f) `.tcw/tcw-migration-progress.yaml`: what it is, never committed
      (ignored inside git), a stopped run is finished by running again,
      deleting it mid-run means restoring from (b) first, and a stopped run
      names it and prints, quoted as written (H20),
      `do not save these files in version control until 'tcw migrate' finishes`
      (run: interrupt a scratch run the way TCW-116's stop tests do, or cite
      them);
    - (g) a second person runs `tcw migrate` after pulling; anyone runs it
      again after merging a branch made before the migration;
    - (h) `.tcw/tcw-migration.yaml`: what it holds, committed, kept through
      4.x, a library must keep it, a project whose readers have all migrated
      may delete it;
    - (i) `not_tags` in the user-wide file is reported, not changed, with the
      line to change once no 3.x `tcw` is used (from the dry run's A5 line);
    - (j) `tcw migrate` does not check git and commits nothing;
    - (l) the way back: the files from (b) at any time, never the tickets; so
      a Jira project runs `--no-jira` first, checks with `tcw validate`, and
      converts the tickets last;
    - (m) a store with a mount point inside it is refused with a message, and
      is finished by moving the folder by hand and running `tcw migrate`
      again; (n) `--no-jira` builds no Jira client, so it needs no credentials
      and cannot reach Jira, and a dry run cannot edit a ticket; (o) the Jira
      settings a run uses are the project's own `work.jira`, never a parent's,
      and a problem elsewhere in the configuration does not stop the ticket
      conversion; (p) a hand edit to a file between a stopped run and its
      re-run stops the re-run (B17), whether that file was to be rewritten or
      deleted; (q) A12 lists findings the project already had in 3.x, and a
      `capabilities.yaml` entry 3.x could not route is B10 (H19, each checked
      against TCW-116's tests); (r) with `--no-jira` in a project whose work
      is kept in Jira, the check after the run leaves out the work store, and
      the summary prints
      `work store not checked after the run (--no-jira): run 'tcw validate' to check it`;
      (s) a stopped run run again while Jira cannot be reached writes nothing
      more, exits with Jira's code, and prints
      `nothing more was written; 'tcw migrate --no-jira' finishes the files without Jira`
      (H20; (r) by a scratch run, (s) against TCW-116's
      test, named, since it needs Jira to fail; each quoted line copied from
      its source in `tcw/migrate/`, layer 4). The quoted lines are code
      spans that Step 2 (d) reads; if (d) reports one (a quotation mark can
      end a command word early), the line is quoted in prose between double
      quotation marks instead, still word for word, which (d) does not read.
- `## Migrating related projects` (2.5 (a) to (f)): each run in its own
  project (`tcw migrate` there, or `tcw -C <folder> migrate`), never
  changing another; parents before children and why (exit 7 below a 3.x
  parent, every Jira-reaching command in a Jira-backed package; commands
  reading only the package's own records and keys work); the summary's list
  of family projects still in 3.x, parents first, each with its
  `tcw -C <folder> migrate`; a planning workspace's stores ("left in
  another repository", worded as `v4` prints it); a related project not on
  this machine stops the run naming its `git clone`, and `tcw project
provision` fetches related projects afterwards; `extends` to a sibling
  becomes a parent link with the axes it named, `upstream` becomes a parent
  link, each printed for review. Each fact checked against the TCW-116 test
  for it, listed by ID in the round (criterion 4).
- `## What each 3.x name becomes` (2.6 (a) to (k) and "New in 4.0"):
  mapping tables, header first cell `3.x …`, one table each for commands,
  flags, configuration, files, names and addresses, and output a script
  reads, holding every `THREE_X_NAMES` entry and an example for each scan
  pattern (Step 2 (b), (h)); the second cells are copied from `v4`'s
  behavior (`--origin`'s new shape `# <project>, <layer> <file>` from a
  scratch run of `tcw project config --origin`; JSON `"schema": 2` with
  `full-id` and `owner` from `tcw work list --json`). A store's
  `repository` row says it stays on the store (TCW-116 decision 4). The
  `overrides:` row's first cell is a 3.x pointer,
  `overrides: core/cap-1a2b3c`, so the narrowed P12 matches it (Step 2 (h)). After
  the tables, (h) to (k) in prose: plain `list` shows only the project's own
  entries and `--scope up` adds inherited ones, `show <id-path>` of an
  inherited entry needs `--scope up` (run); no override mark and no status
  summary in a plain listing, both in `--json` and `show`; exit 7 instead of
  5 or 1 for a related project or a setting only it could give, with how to
  fetch it; only the owning project changes an object. Then the table
  "New in 4.0": `tcw project path`, `tcw project info`, `tcw -C`, `--scope`,
  `--project`, `tcw work move`, `tcw taxonomy rename|move`,
  `tcw capabilities rename|move`, `tcw work new --nest`, each linking its
  home guide by file (decided while planning, 4).
- `## The epic-parts flow, step by step` (2.7): the table of TCW-114 Design
  3.1 rows a to f (`docs/work/TCW-114-*/spec/spec.md:449-470` at
  `2adac9c9`), its 3.x and 4.0 columns, compared with TCW-114's implement
  round for any change; and the sentence that an agent taught the 3.0.1 or
  3.0.2 flow changes one thing: it runs each part's command in the part's own
  project with `tcw -C`.
- `## Personal settings and environment variables` (2.8 (a) to (g)): the two
  personal files; the rule `TCW_<KEY>__<PROJECT>` with
  `TCW_USER_NAME__MY_PROJ` (a hyphenated ID) and
  `TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__APP` (a key two levels deep), each
  set in a scratch project with that ID and seen to change
  `tcw project config --origin` (its `environment: <NAME>` label quoted;
  criterion 8); merging rules; the allowed list by a relative link to
  `skills/configure/references/personal.md`, which `link_problems` checks;
  `TCW_NO_PERSONAL_CONFIG=1`; the variables named without `__`; a
  credential variable name starting `TCW_` and holding `__` must be renamed.
- `## Where provisioning may place a clone` (2.9 (a) to (i)), each rule
  checked against `tcw/provision.py`'s `_bound_problem` and TCW-115's tests
  for it (named), with the refusal wording copied from those tests.
- `## Scripts, hooks and agent instructions` (2.10 (a) to (e)), with (d) as
  decided while planning, 5.

**Proves it:** Step 2's tests all pass; the round holds the dry run, the two
variable runs and the table of TCW-116 and TCW-115 test IDs.

### Step 4 — the README's index links the guide

Spec Design 3.6, 9.5; criterion 11 (index half).

**Tests first:** `test_the_documentation_index_links_the_guides_it_must`
(`tests/test_docs_describe_3_0.py:438-444`) gains
`docs/migration-guide-3.X-to-4.0.0.md` in its tuple; red.

**Changes** `README.md:760`, the "Migration guides" row: `[3.x → 4.0]
(docs/migration-guide-3.X-to-4.0.0.md)` first, before `0.10 → 0.11`.
Nothing else in the README changes in this step.

**Proves it:** the index test green; `pnpm exec prettier --check README.md`
passes after `--write` (Step 0b formatted the rest of the file, so the run
changes only this cell).

### Step 5 — Part 1's suite and commit

Bare `.venv/bin/pytest` from the worktree's root (never `python -m pytest`),
and `pnpm exec prettier --check docs/migration-guide-3.X-to-4.0.0.md`.
The person's own files are compared with `<S>/real-files-before.txt` (Step 0
item 9). Commit: `tests/doc_vocabulary.py`, `tests/test_docs_describe_4_0.py`,
`tests/test_migration_guide_4_0.py`, the guide, `README.md`,
`tests/test_docs_describe_3_0.py`. The round records the commit and the
suite's last line (criterion 43).

## Part 2 — the README, the guides, the use cases, the agent and lifecycle documents, the design

Each step below: the red-to-green check on its files; list 2's rows for
those files rewritten; every claim checked on `v4`; inbound anchors fixed;
`prettier --write`; the suite's document tests run
(`tests/test_documented_cli_surface.py tests/test_docs_describe_3_0.py
tests/test_cli_guide.py tests/test_exit_code_tables.py
tests/test_configuration_text_home.py`) before the next step.

### Step 6 — `docs/guide/cli.md`

Spec Design 4.1 (a) to (g); criterion 12.

- (a) a new `## Running a command in another project's folder: -C`
  section after "How commands are named" (`:11-24`): `-C <folder or
address>`, as if started there, as that project, its own settings and
  checks; only for a project on this machine (from `<S>/cli-4.0/tcw.txt`
  and runs of TCW-114 Step 6's cases).
- (b) "Naming a work item" (`:120-133`) becomes "Naming an object": the
  input forms of TCW-110 Design 3.1, and that output always prints full
  identifiers; "slug" defined as the nickname.
- (c) `--scope own|up|down|all` (default `own`, never a sibling) and
  `--project <id>` (one owner's results, never grouped: no `statuses`, no
  `overridden-by`) on every list and show command, the commands read from
  the surface dump.
- (d) the output records: `"schema": 2`, `full-id`, `owner`, and
  `projects`, `statuses`, `overridden-by`, `partial` where they occur, each
  shown from a scratch `--json` run.
- (e) "Exit codes" (`:134-157`): the examples for 3, 4 and 5 (`:144-146`,
  as TCW-108 Step 3 left them), row 7 (as TCW-108 added it), and the
  passage under the table (`:148-150`, as TCW-114 Step 7 left it) say what
  3, 5 and 7 mean in 4.0. `test_cli_guide` keeps one row per `tcw/exit.py`
  constant. Before row 5 is written, `tests/test_exit_code_tables.py` on
  `v4` is read for whether its refusal of `jira` in rows 3 and 5 ignores
  case; if it does, row 5 says "the issue tracker" rather than "Jira".
- (f) `tcw work new --parent <epic> --nest`.
- (g) a mistyped or removed command gets a suggestion: a table headed
  "3.x commands 4.0 removed" with `init`, `projects`, `config`,
  `provision` by verb and their replacements; a link to the migration
  guide; and, in prose (decided while planning, 9), that typing new
  straight after tcw suggests `tcw work new` or `tcw project new`, and list
  alone suggests no project command, each run on `v4` and its line quoted.
- TCW-112 Step 5a's `:14` passage (list 2) rewritten.

**Proves it:** the red-to-green check (11 scan hits and 8 grep lines at
`2adac9c9`); `tests/test_cli_guide.py`, `tests/test_exit_code_tables.py`,
the three command checks.

### Step 7 — `docs/guide/configuration.md`

Spec Design 4.2 (a) to (j); criterion 13. The home of the `.tcw/` folder,
layers, inherited keys, `null`, `inherit: true`, environment overrides and
the allowed list (spec 1.5).

- (a) `:3`'s "a `tcw-config.yaml`" becomes `.tcw/tcw-config.yaml` and
  `.tcw/tcw-config.local.yaml`, at a fixed place; a 3.x project with a root
  `tcw-config.yaml` is refused naming `tcw migrate`, linking the guide (one
  paragraph that names `tcw migrate`).
- (b) `tcw-version` on every file TCW writes; **migration** defined.
- (c) "Layers" (`:29-42`): built-in, the project's file, the user-wide file,
  the personal file, environment variables, then inherited by children.
- (d) the inherited keys, `work.backend` never inherited, `null`,
  `inherit: true` in `work.tags` (from `INHERITED_KEYS` on `v4`).
- (e) environment overrides and the allowed list, a sentence each, linking
  `skills/configure/references/personal.md` and the migration guide's
  section by file.
- (f) exit 7 for a setting only a missing parent could give, and its two
  remedies (run).
- (g) whose problem a mistake is, and the "broken inherited value" warning
  (its wording from a scratch run with a broken parent file).
- (h) `tcw project config --origin` and its comment shape (run).
- (i) `not-tags` (the documentation entry key).
- (j) filesystem versus Jira-mode with a missing parent, and the five
  commands that never stop on one (`tcw work path`, `lifecycle`, `docs`,
  `stage prompt` and `procedure` with no item), each run with a parent
  missing.
- `:141` and `:322`, the fenced comments `# tcw-config.yaml` and
  `# tcw-config.local.yaml`, name `.tcw/`. The heading of `:190` keeps its
  exact words (decided while planning, 8).

**Proves it:** the red-to-green check; link check (stores.md's anchor
`#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds`
still resolves).

### Step 8 — `docs/guide/linking-and-validation.md`

Spec Design 4.4 (a) to (f); criterion 15. The home of full identifiers,
`tcw://` addresses and `tcw validate`'s findings.

- (a) the grammar `tcw://<project>.<namespace>/<id-path>` and
  `tcw://<project>[.<namespace>].path/<folder>`, no `.` or `..` folder;
- (b) a link names an object in any project TCW can locate;
- (c) 3.x links are reported as needing `tcw migrate` (run, quoted);
- (d) a reference into a project not here is "could not check" (run);
- (e) the findings 4.0 adds, as a table, each worded as `v4` prints it: rows
  a to n of TCW-111 (`docs/work/TCW-111-*/spec/spec.md:442-455` at
  `2adac9c9`), the incomplete override and two unrelated projects at one
  path (TCW-112), stores that nest, coincide or loop (TCW-110), manifest
  entries that cannot be reached or declare another ID (TCW-107), load-order
  warnings and loops (TCW-108). Each wording is copied from a scratch run
  that provokes it, or from the test that asserts it where a run needs a
  layout too costly to build (named). Row f's message names `tcw migrate`,
  so its row may say `meta.yaml`.
- (f) "A leftover inheritance file from before 2.5.0" (`:130`) is kept only
  if `v4` still reports that file (`grep -rn 'before 2.5.0\|2\.5\.0'
tcw/validate.py tcw/store/`), worded as it prints.
- TCW-112 Step 5a's `:17` and `:139` (list 2) rewritten.

**Proves it:** the red-to-green check (10 scan hits at `2adac9c9`).

### Step 9 — `docs/guide/multi-repo.md`, rewritten whole as "Related projects"

Spec Design 4.5 (a) to (l), 2.9; criteria 9 (its guide half), 16. The
riskiest guide: every 3.x mechanism (`projects`, `upstream`, filing into
another project, `extends`) is in it, and it is the home of parent links,
manifests, locating, the load order, provisioning and its bound, and
worktrees. The file name stays (spec Design 4.5).

Outline, each section checked on `v4`:

1. `# Related projects` and an opening that states the two layers (1.7).
2. A project and the active project (a).
3. Parent links: `parents:` in order, `inherit` (`all`, `none`, or a list of
   `taxonomy`, `capabilities`, `config`); children in either file, combined;
   a listed child names the parent back (b) (runs: a scratch family of three
   made with `.venv/bin/tcw project new`).
4. The load order and its warning, shown by `tcw project info` (c) (run,
   quoted).
5. Manifests: the two files, an entry's shape (`path`, `repository`
   written `<url>` or `<url>#<branch>`, `subfolder`), and that a manifest
   says where a project is and nothing else (d) (from `tcw/store/manifest.py`).
6. Locating a project with no entry (e): beside, then enclosing, never
   downwards; two matches an error naming both; an empty or `.git`-only
   folder is not on this machine; `TCW_PROJECT_<ID>` (runs).
7. A related project not on this machine (f): what still works, exit 7,
   "could not check", "unavailable, exit 0" in a `--scope` view, and the
   three `show` warnings, worded as `v4` prints them (TCW-113 choice 6:
   `… so its status is not shown: <reason>`, `… so its items are not counted
in children and blocks: <reason>`, `… so its taxonomy entries are not
included: <reason>`) (runs).
8. Family views with `--scope` (g), linking `cli.md`.
9. Changing another project's object (h): only the owner; `tcw project path
<id>` and `tcw -C`; a blocker in another project is the exception (run:
   the exit 3 refusal quoted).
10. Stores in another repository (i): relative path or `.path` address;
    absolute or `~` refused in the shared file; no nesting, coinciding or
    loops; a store's `repository` stays on the store (runs).
11. `tcw project provision` and where it may place a clone (j), stated in
    full: the spec's 2.9 (a) to (i), with `.git`-only refused and
    `.tcw-staging-<hex>` explained; the wording from TCW-115's tests.
12. Git worktrees (k).

The old headings that other documents link (`#tcw-provision`,
`#connecting-projects-projects` and the rest, found by `git grep -n
'multi-repo.md#'`) are re-pointed to the new headings in this step, and the
migration guide's provisioning link gains its anchor (decided while
planning, 4). The README's link text "Working across repositories"
(`:235`, `:300`, `:755`) becomes "Related projects" in Step 14.

**Proves it:** the red-to-green check (15 scan hits and 8 grep lines at
`2adac9c9`); link check over every live document.

### Step 10 — `docs/guide/taxonomy-and-capabilities.md`

Spec Design 4.6 (a) to (g); criterion 17. The home of inheritance,
overrides and mixed status.

- (a) inheritance through every parent whose `inherit` includes the axis,
  every level up;
- (b) "Federating and overriding a capability" (`:205`) becomes "Inheriting
  and overriding": an override is an object at the same path, holds only
  what it changes, merges field by field; `tcw capabilities set` and
  `tcw taxonomy add` at an inherited path write one; `reset` and `rm`; an
  override whose original moved is reported as incomplete; two unrelated
  parents at one path warn (runs, each wording quoted). Real `show` output
  for an override, its `overrides: <full id>` line included, may be shown in
  a fenced block, which the narrowed P12 passes (decided while planning,
  10);
- (c) records mark overrides, and plain `list` stays one identifier per line;
- (d) mixed status under `--scope down` and `all`, from `--json` or `show`
  (run: a scratch family whose projects give one capability different
  statuses);
- (e) no capability `id`; `--parent` on `add` and `set`; `rename` and
  `move`;
- (f) `tcw capabilities drift` exits 7 in a Jira-mode project whose Jira
  settings come from a missing parent (checked against TCW-109's test,
  named, since drift with Jira settings needs a Jira-mode scratch project:
  run if `drift` reaches the exit before any network call, else the test);
- (g) "A project with no ledger of its own" (`:169`) says what 4.0 does
  (run).
- list 2's rows from TCW-112 (Steps 5a, 19) and TCW-113 (Step 12b's `:32`,
  `:98`) rewritten.

**Proves it:** the red-to-green check (13 scan hits and 8 grep lines at
`2adac9c9`).

### Step 11 — `docs/guide/jira.md`

Spec Design 4.3 (a) to (i); criterion 14. The home of what a command does to
a ticket.

- (a) `TCW Item` holds the full identifier, nested id-path included; a key at
  any depth; `tcw-work-item.yaml`;
- (b) tickets still holding a 3.x value: left out of `tcw work list` with one
  warning, reported by `tcw validate --remote`;
- (c) `work.jira` may come from a parent; `work.backend: jira` is the
  project's own; a credential variable name may come from a variable;
- (d) one search per Jira project, account and stage mapping in one scope; a
  write makes the next search ask again;
- (e) a parent or blocker Jira cannot link is recorded in the item's folder,
  and Jira does not show it;
- (f) a move or rename edits each ticket's `TCW Item`;
- (g) "Creating an item in another project" (`:233`, as TCW-114 left `:235`)
  becomes "Working on another project's items": `tcw -C`; the `jira` block's
  filing is gone; the web create form accepts a blocker in another project;
- (h) no `upstream` project (`:245`);
- (i) `tcw migrate` edits each ticket's `TCW Item` and no other field, and
  the window in which tickets are hidden, linking the migration guide.

Each fact is checked against the fake-Jira test that proves it (layer 4),
named in the round; nothing contacts Jira.

**Proves it:** the red-to-green check.

### Step 12 — `docs/guide/work.md`

Spec Design 4.8 (a) to (d); criterion 19. The home of the item folder, nested
items, and moving and renaming items.

- (a) "The item folder" (`:105-121`): `tcw-work-item.yaml`, the bounded set,
  child item folders, `resources/`, and a long design in `resources/`;
- (b) "Creating and changing items" (`:320-363`): `--parent` with `--nest`,
  `tcw work move`, `rename` of an item holding nested items, and the
  passages at `:332` and `:351` (as TCW-114 Step 7 left them) rewritten
  (runs);
- (c) "References, and what `tcw validate` reports" (`:364-385`) and the
  passages at `:383` and `:414` (runs);
- (d) `tcw work tags add` in a child writes `inherit: true` first; `rm` in a
  child removes only the child's own and refuses a parent's tag with exit 3
  (run, the refusal quoted).

**Proves it:** the red-to-green check (8 scan hits and 5 grep lines at
`2adac9c9`); `DOCUMENTED_VERBS` (`tests/test_documented_cli_surface.py:260`)
still found.

### Step 13 — `docs/guide/web-viewer.md`

Spec Design 4.7 (a) to (c); criterion 18. Read against the client on `v4`
(`web/client/src/`, the scope control and project filter of TCW-113 Steps 15
and 16, the create form of TCW-111 Step 10 and TCW-114 Step 8) and, where a
person must see it, against `tcw serve` started in a scratch family and
opened in the Claude Chrome profile, never the default one; each claim with
the component file and line that shows it.

- (a) `:17-19` ("The app serves one project") becomes the scope control, the
  project filter, read-only display of other projects' objects, followed
  links, and that the app's records carry the CLI's `--json` keys;
- (b) the reference pickers offer the served project's view; one project in
  the filter shows no status summary;
- (c) the create form's "inside the parent's folder"; no project choice, no
  "Blocks (add)"; a body edit changes only the capability's own description.

`web-viewer.md` is outside the 3.0 scan's owned set
(`tests/test_docs_describe_3_0.py:73`), but the 4.0 scan and the command
check read it.

**Proves it:** the red-to-green check (2 scan hits at `2adac9c9`).

### Step 14 — `README.md`, but the index

Spec Design 3.1 to 3.5; criterion 11.

- 3.1 the command table (`:263-273`): `tcw project` with its six verbs,
  `tcw migrate`, `tcw validate`, `tcw serve`, the three axis groups, no
  removed command; the adoption example `tcw project new --id my-project`
  writing `.tcw/tcw-config.yaml` (`:275-282`) (run);
- 3.2 the overview (`:255-257`): the full identifier with an example, "slug"
  its nickname; a link is `tcw://` and the full identifier, linking the
  linking guide; the state files and `resources/`, linking the work guide;
- 3.3 "Many repositories, one model" (`:289-300`) rewritten, linking
  "Related projects" and the configuration guide;
- 3.4 the cloud section (`:231-235`): `tcw project provision` and what it
  fetches;
- 3.5 each axis's CLI table (`:339-375`, `:401-436`, `:589-661`): `--scope`,
  `rename`, `move`; `tcw work new --parent <epic> --nest`, `tcw work move`;
  the `tcw capabilities list` row of TCW-113 Step 12b (`:413`) and
  TCW-112 Step 5a's rows (`:360`, `:371`, `:421`, `:432`) rewritten;
  TCW-114's `:608` cell rewritten;
- every link text "Working across repositories" becomes "Related projects";
  the Documentation table's rows for the guides say what each now covers.

The structure tests stay green (Step 0 item 7). Step 0b formatted the file,
so `prettier --write` here changes only what this step wrote.

**Proves it:** the red-to-green check (22 scan hits and 15 grep lines at
`2adac9c9`); `tests/test_docs_describe_3_0.py`'s README tests; the command
checks.

### Step 15 — `docs/use-cases.md`

Spec Design 6.1 to 6.6; criteria 25 to 28. Every requirement stays a
statement a reviewer can check against the code, with the file that shows
it, re-found on `v4` (Step 0 item 8).

- 6.1 the opening (`:19-20`) and the dimension table (`:83-98`, the rows at
  `:90` and `:92`);
- 6.2 UC-1 to UC-8 (`:101-424`), each as the spec gives it, with TCW-114
  Step 7's `:161` and `:213-216` sentences (list 2) rewritten and UC-6
  retitled "A related project that is not on this machine";
- 6.3 S-3, S-4, S-5, S-6, S-8, S-9 (gains the 3.x-to-4.0 migration, linking
  the guide; its first requirement cites `tcw/project_files.py`'s refusal),
  S-10, S-11 (the check on `v4` that still depends on git, found with `grep
-rn 'git_root\|rev-parse' tcw/`, or the sentence removed if none does);
- 6.4 every known gap of the spec's table decided against the code: removed,
  re-marked with the item that narrows it, or kept with "No item yet"; the
  round gives, per gap, the file and line on `v4` that decided it
  (criterion 27). The UC-3 TCW-99 gap per decided while planning, 12; the
  UC-4 "two places rebuild a store's path" gap by checking whether
  `store_location` (TCW-110 Step 13) serves both callers; the S-9 "2.x work
  store listed as empty" gap by running the 4.0 CLI and `tcw migrate
--dry-run` on a scratch 2.x store (a root `tcw-config.yaml` with a 2.x
  status folder);
- 6.5 the checklist (`:669-698`), questions 1 to 3;
- 6.6 the closing paragraph (`:713-715`) replaced.

**Proves it:** the red-to-green check (25 scan hits and 7 grep lines at
`2adac9c9`); link check.

### Step 16 — `AGENTS.md` and the lifecycle documents

Spec Design 7.1, 7.2; criterion 29.

- `AGENTS.md:39`, `:52`, `:170`: `.tcw/tcw-config.yaml`. The "Working in a
  git worktree" section checked against TCW-107 Design 4 and changed only
  if it says otherwise (it is owned by the 3.0 scan through
  `agents_worktree_section`). No temporary sentence about the two files
  (spec 7.1).
- `docs/lifecycle/implementation.md:16-24`: the layout shows
  `.tcw/tcw-config.yaml` and `work.path` as whichever of a relative path
  or a `.path` address 4.0 accepts for a store outside the project (checked
  by loading that configuration in a scratch layout with `.venv/bin/tcw
project config`); `:41-44` names the functions that walk projects as they
  are on `v4` (`grep -n 'def find_project_root\|def descendant' tcw/`).
- The comment line at the top of each lifecycle document
  (`implementation.md:1`, and the same line in `abstraction.md`,
  `harness.md`, `review.md` and the templates) names `.tcw/tcw-config.yaml`.
  `abstraction.md` is TCW-111's and TCW-114's (list 3): its comment line
  changes here, and the scan reads the rest; a 3.x form the scan still finds
  there (at `2adac9c9`, `item.yaml` at `:92`, which TCW-111 Step 15 plans to
  rewrite) is fixed as decided while planning, 15.

**Proves it:** the red-to-green check; `MOVED_PHRASES` and
`test_harness_points_at_where_a_subagent_is_never_required` green.

### Step 17 — the TCW-99 design's amendments

Spec Design 8.1 to 8.7; criterion 30. In
`docs/work/TCW-99-tcw-4-0-overhaul-how-tcw-projects-relate-and-how-they-are-deployed/design.md`,
each passage re-found by its words (lines at `2adac9c9`):

- 8.1 `:466-470` ("Listings, `show` and `tcw project info` mark each
  object");
- 8.2 `:648-651` ("a list shows a short summary such as");
- 8.3 `:657-665`, the sketch's command gains `--scope down`;
- 8.4 `:745-746` ("A connection's or a store's `repository`");
- 8.5 `:484-485` (`work.backend` in the inherited keys);
- 8.6 `:517-518` (`TCW_WORK_PATH__MY_PROJ=/other/path`), with
  `TCW_USER_NAME__MY_PROJ` run on `v4` first;
- 8.7 `:532-534` (`TCW_WORK_JIRA__APP`, `TCW_WORK_JIRA_SITE__APP`), with the
  two replacement variables run on `v4` first.

Each gets the dated line the spec gives it, naming who decided and where it
is recorded. Step 0b formatted the file, so this step's diff holds only the
seven amendments.

**Proves it:** the review reads each amendment (no check reads `docs/work/`);
the round pastes the step's diff and the three variable runs.

### Step 18 — Part 2's suite and commit

Bare `.venv/bin/pytest`; `pnpm exec prettier --check` over every Markdown
file of Steps 6 to 17. The grep and the scan over the files of Part 2 print
nothing outside the allowance. The person's own files are compared with
`<S>/real-files-before.txt`. Commit; the round records the commit and the
suite result.

## Part 3 — skills, shipped text, evals, the ledger, the live scan

Each skill step: the red-to-green check; `tests/test_shipped_text.py` (git
words, the 2.x vocabulary, commands, injections) and the three command
checks after it. A sentence the git check refuses is reworded, or moved to
its home guide and linked (spec 5.7 (c)); no `GIT_ALLOWED` phrase is added
except Step 22's.

### Step 19 — the `work` skill and its references

Spec Design 5.1 (a) to (k); criterion 20. `skills/work/SKILL.md`,
`skills/work/references/commands.md`, `skills/work/references/tags.md`.

- (a) the description (`:4`) and the "Delegation" bullet (`:93-101`, as
  TCW-114 Step 7 left them): a part in another project is made there,
  `tcw -C <folder> work new "<title>" --parent <epic> --nest`, and `tcw
project path <id>` gives the folder; a blocker in another project with
  `--blocked-by` on the blocked item;
- (b) "Epics are parents" (`:90-92`) and `commands.md:10`: `--nest` with
  `--parent` always;
- (c) "Another project's exit codes" (`:103-115`, with TCW-107's `:115`
  sentence): exit 3 names the folder to run it in; exit 7, report which
  project and how to fetch it, do not retry; exit 7 naming a setting,
  report its project and the two remedies;
- (d) `--scope` and `--project`; (e) names and input forms; (f) the backlog
  audit by full identifier and `tcw -C`; (g) `move` and nested `rename`;
  (h) `tags add` and `rm` in a child;
- (i) `commands.md:11`, `:19`, `:28` and the exit-code table (as TCW-108
  Step 3 left it); (j) a project refused as 3.x: `tcw migrate`, naming the
  migration guide by its file and its GitHub address,
  `https://github.com/brocef/TCW/blob/main/docs/migration-guide-3.X-to-4.0.0.md`;
  (k) where provisioning may place a clone, in one sentence without the git
  words (spec 5.7 (b)), linking the guide on related projects.
- The heading "Rules: no project text changes" keeps its words (Step 0
  item 7).

**Proves it:** the red-to-green check (6 scan hits and 4 grep lines in
`SKILL.md`, 5 and 4 in `commands.md`, at `2adac9c9`);
`tests/test_shipped_text.py`; `tests/test_exit_code_tables.py`.

### Step 20 — the `taxonomy` skill

Spec Design 5.2; criterion 21. `skills/taxonomy/SKILL.md`: "Inheritance
(federation)" (`:105-110`, as TCW-112 Step 5a left `:111-115`) becomes
inheritance through parent links passing `taxonomy`; an override at an
inherited path; `--scope up`; the nesting bullet (`:91`) says `--parent`
also records `parent:`; `rename` and `move`; exit 7. The command table rows
TCW-112 Step 23 added are kept and checked against the surface dump.

**Proves it:** the red-to-green check (12 scan hits at `2adac9c9`).

### Step 21 — the `capabilities` skill

Spec Design 5.3; criterion 21. `skills/capabilities/SKILL.md`: "Federation"
(`:118-125`) as Step 20; no opaque `id` (`:29`, as TCW-112 Step 19 left it);
`set` on an inherited capability and what `tcw validate` checks
(`:141-147`); mixed status from `--json` or `show`; `--project` with no
`statuses` and no `overridden-by`; `--parent` on `add` and `set`; the
wording flow (`:153`, `:181`, as TCW-114 Step 7 left them) becomes `tcw -C`
into that project when it is on this machine, else that project's own issue
tracker; TCW-113 Step 12b's `:176` rewritten. Every `tcw capabilities add`
line keeps `--status` (`tests/test_shipped_text.py:404-410`), so the
sentence on `--parent` with `add` either writes `--status` too or names the
option without the command.

**Proves it:** the red-to-green check (19 scan hits at `2adac9c9`);
`test_the_capabilities_skill_changes_records_with_the_code`.

### Step 22 — the `configure` skill and its references, `KEY_PATHS`, the one `GIT_ALLOWED` phrase

Spec Design 5.4 (a) to (f), 5.7 (a); criteria 22, 42. The home of every
key's exact shape.

**Tests first** (red), in this order:

- `tests/test_shipped_text.py`: `GIT_ALLOWED` gains, for
  `skills/configure/references/projects.md`, the phrase `` `<url>#<branch>` ``
  with the spec's reason verbatim. `test_every_git_allowance_is_still_needed`
  fails until `projects.md` holds it.
- `tests/test_configuration_text_home.py`: `KEY_PATHS` per decided while
  planning, 7, and its count; red until the headings change.

**Changes**

- (a) `references/projects.md`: parent links and `inherit`, `parents` and
  `children` each under its own heading with its label line, the
  manifests and their entries (`path`, `repository` as `<url>` or
  `<url>#<branch>`, `subfolder`, from `tcw/store/manifest.py`), locating in
  a sentence linking "Related projects"; no `projects:` locators,
  `upstream` or `--project` (`:157-163`, `:170`, `:199`, `:380`, and
  TCW-112's `:343-371` section);
- (b) `references/stores.md`: relative path or `.path` address, never
  absolute or `~` in the shared file; no nesting, coinciding or loops;
  `repository` on a store (`:88`); its two `GIT_ALLOWED` phrases kept;
- (c) `references/personal.md`: the allowed list as `PERSONAL_KEYS` and
  `LOCAL_ONLY_KEYS` are on `v4`, its table rows (minus the 24 `projects.*`
  rows and their anchors at `:174-197`, plus `parents` and `children`), the
  override variable rule, `TCW_NO_PERSONAL_CONFIG`, `.tcw/` locations; its
  `GIT_ALLOWED` phrase kept; the `VOCABULARY_ALLOWED` line
  (`- builtin: true  # built-in, tcw/work/prompts/spec.md`) kept only if
  `tcw project config` still prints that shape, else reported;
- (d) `references/work.md`: `not-tags` and `tcw-version`, records with
  `full-id` and `owner`, the inherited keys;
- (e) `references/jira.md` and `docs-sync.md`: `.tcw/tcw-config.yaml`;
- (f) `SKILL.md`: `tcw project config --origin`, `tcw project info`, and the
  provisioning bound in one sentence (5.7 (b)), linking the guide; its
  front matter's `description` and `when_to_use` scanned
  (`test_the_router_frontmatter_names_no_2x_vocabulary`).

**Proves it:** the two tests green; `tests/test_configuration_text_home.py`
whole; the red-to-green check (50, 30, 10, 5 and 2 scan hits in
`projects.md`, `personal.md`, `stores.md`, `work.md`, `SKILL.md` at
`2adac9c9`); `git diff <base> -- tests/test_shipped_text.py` shows one added
entry and no change to `GIT_WORDS`.

### Step 23 — the `setup` skill and its references

Spec Design 5.5; criterion 23. `skills/setup/SKILL.md`,
`references/project.md` (`:51-70`), `references/install.md` (`:59`),
`references/taxonomy.md`, `references/capabilities.md`: `tcw project new`;
`tcw project provision`; a project refused as 3.x is moved over with
`tcw migrate`, naming the guide by its file in the TCW repository and its
GitHub address (as `skills/configure/references/jira.md:9` names the Jira
guide and `skills/extras-report/SKILL.md:20` gives an address); the bound
in one sentence. `skills/README.md`'s `setup` row names `tcw project new`
(5.6 (c)).

**Proves it:** the red-to-green check (16 scan hits in `project.md` at
`2adac9c9`); `tests/test_skill_path_pointers.py`.

### Step 24 — the other shipped text

Spec Design 5.6 (a), (b), (d); criterion 24.

- `tcw/work/procedures/search.md:25-28` (as TCW-115 Step 3 left it) and
  `pause-work.md:22`: full identifiers and `--scope`;
- `agents/reviewer.md` and `agents/backlog-auditor.md`: "a work item's full
  identifier or tracker key" where either still says "a work item slug"
  (`backlog-auditor.md` as TCW-113 Step 17 left it is list 3: only its
  remaining "slug" wording changes);
- every other skill, prompt and procedure: `<S>/scan_one.py` over
  `skills/ agents/ tcw/work/prompts/ tcw/work/procedures/`, and each hit
  fixed; a hit in a list 3 passage is fixed with the smallest change of
  wording, listed under "Departures found" with the sibling it came from,
  and reported to the dispatching session (decided while planning, 15);
- the grep of decided while planning, 20, over the live documents, each
  line decided and the decision listed in the round;
- `tests/fixtures/prompt_fallback/unconfigured.json` regenerated with
  `tests/fixtures/prompt_fallback/capture.py` if its test fails after the
  procedures change, and the difference read (only the changed lines).

**Proves it:** the red-to-green check; `tests/test_shipped_procedures.py`,
`tests/test_shipped_prompts.py`, `tests/test_shipped_text.py`.

### Step 25 — `tests/cli/scenarios/` and the remaining live documents

The scan over every live document outside the ledgers (Step 0's baseline
re-run) lists what Steps 6 to 24 did not reach:
`tests/cli/scenarios/13-release-integrity.md` (2 hits at `2adac9c9`, which
TCW-115 Step 3 renames; its walk is re-read for 4.0: `tcw project new --id
walk` writes `.tcw/`), `docs/releasing.md`, `docs/procedures/`,
`docs/lifecycle/templates/`, `evals/assets/`, and any other. Each is fixed,
or named in the round with why its hit names `tcw migrate`. A Markdown file
under `tests/` that describes test data is fixed only in its words, never in
its data (decided while planning, 18).

**Proves it:** the scan prints nothing outside the ledgers.

### Step 26 — the evals

Spec Design 9.6 (a), (b); criterion 34. `evals/evals.json`: B11's
`files_changed_exactly` path (`:975`) becomes `.tcw/tcw-config.yaml` and its
text (`:978`) says so; every assertion text and `note` naming
`tcw-config.yaml` (`:458`, `:1012`, `:1020`), `tcw init`, `item.yaml` or
`meta.yaml` names the 4.0 form, worded as `evals/seed_fixture.py` behaves on
`v4` (`:615`: it looks for `.tcw/tcw-config.yaml`, or a 3.x project's root
configuration file, which a note names in words, since criterion 34's grep
allows `tcw-config.yaml` only after `/`).

**Proves it:** criterion 34's grep prints nothing;
`.venv/bin/python -m evals.run_evals --axis a --dry-run` and `--axis b
--dry-run` print every arm and an `agent's tcw:` line naming the worktree
(`evals/run_evals.py:340-347`), spending nothing; `tests/test_eval_*.py`
pass. No paid run (spec 9.6 (c)).

### Step 27 — the ledger

Spec Capability changes, Design 9.8; criterion 36. In 3.x form, by hand,
never with `.venv/bin/tcw`.

1. `<S>/scan_records.py` over `docs/taxonomy/` and `docs/capabilities/`
   (`scan` with `THREE_X_PATTERNS`, `flags=0`, the allowance applied); its
   output pasted in the round. At `2adac9c9` it finds about 70 hits outside
   P8, most of which TCW-107 to TCW-116 change; the run on `v4` is the list.
2. The five records `docs/capabilities/skills/{work,taxonomy,capabilities,configure,setup}/description.md`
   rewritten in prose for 4.0, each to the spec's Capability changes
   sentence; `meta.yaml` and every `tcw://C/…` link unchanged.
3. Every other hit outside P8 fixed in prose; each capability record so
   changed added to `capabilities.yaml` under `changed:`; each taxonomy
   record listed in the round.
4. The descriptions name only commands that exist on `v4`, since
   `tests/test_documented_cli_surface.py` reads them.

**Proves it:** the scan re-run prints only P8 hits; `tcw validate` (the
lifecycle CLI, `tcw --version` printing 3.0.2) from the worktree's root
exits 0 with "0 errors, 0 warnings, 0 unresolved"; `tests/test_ledger_3_0.py`
green.

### Step 28 — the scan over every live document, and the grep

Spec Design 9.2, 9.3; criteria 31, 32, 37.

**Changes** `tests/test_docs_describe_4_0.py`:
`test_no_live_document_names_a_3x_form`, parametrized over
`tests.test_documented_cli_surface.DOC_FILES`, asserting
`three_x_problems(rel, text) == []` for each.

**Proves it:** the test green (it would have failed at Step 1, as Step 0's
baseline shows); the grep prints nothing (pasted, criterion 32);
`git grep -n 'tcw -C' -- <the live documents>` read line by line, each
target one word (criterion 37).

### Step 29 — Documentation Sync

Every entry of `tcw work docs` (lifecycle CLI) evaluated with the
`documentation-sync` skill, and the verdicts recorded in the round. This item
is where the siblings' deferrals land, so every entry fires:

| Entry                                                                  | Fires? | Answer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `README.md` [Public-API]                                               | yes    | Steps 4 and 14 (spec Design 3); answers D106 to D116's README rows.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `docs/guide/jira.md` [Jira-Change]                                     | yes    | Step 11 (spec 4.3).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `docs/guide/<topic>.md` [Guide-Topic-Change]                           | yes    | Steps 6 to 13 (spec 4.1 to 4.8).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `docs/release-notes/upcoming/<folder>.md` [Public-API]                 | yes    | Written: `docs/release-notes/upcoming/TCW-117-tcw-4-0-guides-skills-use-cases-and-the-3-x-to-4-0-migration-guide.md`, under `##` headings, in plain language: a guide for moving a project from 3.x to 4.0, and the guides and skills describe 4.0.                                                                                                                                                                                                                                                                                                                            |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]               | yes    | Written: `docs/changelogs/upcoming/TCW-117-tcw-4-0-guides-skills-use-cases-and-the-3-x-to-4-0-migration-guide.md`, under **Changed** (the README, the guides, `docs/use-cases.md`, `AGENTS.md`, the lifecycle documents, the five skills and the other shipped text, `evals/evals.json`, the ledger records, the TCW-99 design's amendments) and **Internal** (`THREE_X_PATTERNS`, `scan`'s `flags` argument, `tests/test_docs_describe_4_0.py` and its `UNMIGRATED_RECORDS`, `tests/test_migration_guide_4_0.py`, the index test, `KEY_PATHS`, the one `GIT_ALLOWED` phrase). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component]                 | yes    | Steps 19 to 23 (spec 5.1 to 5.5).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes    | Step 22 (spec 5.4).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `docs/use-cases.md` [Project-Setup-Change]                             | yes    | Step 15 (spec Design 6).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

Both entry files are formatted with `prettier`, and checked by
`tests/test_upcoming_entries.py` (criterion 38). They are named by the
item's folder name, never its slug, and no other item's file is touched.

### Step 30 — Part 3's suite and commit

The suite as CI runs it: bare `.venv/bin/pytest` from the worktree's root;
`pnpm exec prettier --check` over every Markdown file this item changed
(`git diff --name-only <base> -- '*.md'` plus the new files) that
`.prettierignore` does not exclude (criterion 39). Then criterion 42's two
diffs, pasted: `git diff <base> -- tests/doc_vocabulary.py` (no `PATTERNS`
entry changed; `scan` gains only `flags`; `THREE_X_PATTERNS` added) and
`git diff <base> -- tests/test_shipped_text.py` (no `GIT_WORDS` change; one
`GIT_ALLOWED` entry added). Every fenced block in a live document that is
tagged `yaml`, that has no language tag, or that is tagged `text` and holds a
line shaped like YAML (a `<key>:` at its start) is listed
(`<S>/fenced_yaml.py`) for the review, which reads each for a 3.x shape; the
untagged and `text` blocks are included because `docs/use-cases.md` holds
3.x keys inside tree diagrams, and the scan no longer has `\bprojects:`.
Then the re-check of decided while planning, 19: `git log <base>..HEAD --
tcw/`, this item's own commits left out; if any commit is listed, Step 3's
dry run and every other run whose output a document quotes are redone, the
output compared with what the documents quote, and each difference fixed in
the document before the commit. The person's own files are compared with
`<S>/real-files-before.txt` a last time. Commit; the round records it and the suite result (criterion 43).
The records gate is checked with `tcw work advance <item> --dry-run` (the
lifecycle CLI) before the move to review.

## Verification the tests cannot do

- **The review lists, document by document**: criteria 2 to 4, 6, 8 to 30,
  40 and 41 are "the review lists"; the round gives the reviewer, per
  criterion, the file and line on `v4` of each lettered item, and the
  "Checked on v4" table.
- **Handoffs answered** (criterion 40): the round marks each row H1 to H20
  and D106 to D116 (H19 and H20 as decided while planning, 6), with the step and line
  that answers it.
- **The cold read** (spec Design 9.7; criterion 35) is **for qa only, never
  run in implement**. The QA plan on the ticket (2026-10-22 21:23,
  scenario 2) holds its exact preparation: a `git clone` of `main` into the
  qa session's scratchpad, its remote removed
  (`git -C <copy> remote remove origin`); its `tcw-config.yaml` with
  `work.jira.site: https://jira.invalid` and
  `work.jira.credentials.email-env: TCW_COLDREAD_NO_EMAIL`,
  `token-env: TCW_COLDREAD_NO_TOKEN`; a fresh session started in the copy
  with every `TCW_JIRA_*` variable removed (`env -u …`, each name
  `env | grep '^TCW_JIRA'` lists), without `~/.bashrc`, with
  `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` set to two new empty folders in the
  qa session's scratchpad, and
  `/Users/brian/Projects/TCW/.claude/worktrees/v4/.venv/bin` first on
  `PATH`; and, recorded before handing over, `env | grep -c '^TCW_JIRA'`
  printing 0, `tcw --version` printing `tcw 4.0.0`, and the state of the
  person's own `~/.config/tcw/config.yaml` (its checksum, or that it does not
  exist) and `~/.cache/tcw/stores`, both recorded again after the session
  and unchanged. `HOME` is not moved for the reader's session, which keeps
  its own sign-in there (spec 9.7 (c); decided while planning, 14). The
  corrected QA plan text is posted on the ticket by the dispatching
  session, replacing the setup of scenario 2. The one instruction:
  "Move this project to TCW 4.0 by following the guide at
  /Users/brian/Projects/TCW/.claude/worktrees/v4/docs/migration-guide-3.X-to-4.0.0.md".
  It must reach `tcw validate` exit 0; every guess and failed command is a
  finding.
- **The optional eval run** (spec Design 9.6 (c)) is **for qa only, if the
  user chooses it, and never run in implement**: its expected cost stated to
  the user first; then, from the worktree's root,
  `.venv/bin/python -m evals.run_evals --case B1 --case B3 --case B4 --case B11 --case B12 --out <a folder outside this checkout> --dry-run`
  (its `agent's tcw:` line must name the worktree), the same without
  `--dry-run`, and `.venv/bin/python -m evals.grade <that folder>`. It
  measures routing and the single-project flows, not any 4.0 feature.
- **The web guide's claims** (Step 13) seen in a browser, in the Claude
  Chrome profile only, where a component file alone does not show them.
- **The formatting commit** (Step 0b): its `git diff --word-diff -w` read
  by the reviewer, apart from the content commits, so the formatting hides
  no content change.

## Self-review against the spec

**Every criterion has a step.**

| Criterion | Step(s)                                                |
| --------- | ------------------------------------------------------ |
| 1         | 2 (a), 3                                               |
| 2         | 2 (2.8 link), 3                                        |
| 3         | 2 (f), 3 (dry run in the round)                        |
| 4         | 3 (TCW-116 test IDs)                                   |
| 5         | 2 (b), (c), (d), (h); 3                                |
| 6, 7      | 2 (d), (e); 3                                          |
| 8         | 3 (the two runs)                                       |
| 9         | 3, 9                                                   |
| 10        | 3                                                      |
| 11        | 4, 14                                                  |
| 12        | 6                                                      |
| 13        | 7                                                      |
| 14        | 11                                                     |
| 15        | 8                                                      |
| 16        | 9                                                      |
| 17        | 10                                                     |
| 18        | 13                                                     |
| 19        | 12                                                     |
| 20        | 19                                                     |
| 21        | 20, 21                                                 |
| 22        | 22                                                     |
| 23        | 23                                                     |
| 24        | 23 (5.6 (c)), 24, 28 (5.6 (d))                         |
| 25 to 28  | 15                                                     |
| 29        | 16                                                     |
| 30        | 17                                                     |
| 31        | 1, 28                                                  |
| 32, 37    | 28                                                     |
| 33        | every step's test run; Step 0 item 7's list; 5, 18, 30 |
| 34        | 26                                                     |
| 35        | Verification (qa)                                      |
| 36        | 27                                                     |
| 38        | 29                                                     |
| 39        | 0b; every step's prettier run; 30                      |
| 40, 41    | every document step; Verification                      |
| 42        | 1, 22, 30                                              |
| 43        | 0b, 5, 18, 30                                          |

**Every step traces to the spec**: Step 0 to Design 1.1 and 1.2; Step 0b to
Design 11; Steps 1 and
28 to 9.2 and 9.3; Steps 2 and 3 to 2 and 9.4; Step 4 to 3.6 and 9.5; Steps
6 to 13 to 4; Step 14 to 3; Step 15 to 6; Step 16 to 7; Step 17 to 8; Steps
19 to 25 to 5; Step 26 to 9.6; Step 27 to 9.8; Step 29 to 10; Steps 5, 18
and 30 to 11.

**The suite at every boundary.** Step 0b changes only formatting and runs
the suite before its commit. Step 1's tests pass when written (red only
on import). Step 2's test is never committed without Step 3's guide. Step 4's
test and change are one step. Each Part 2 and Part 3 step fixes the inbound
anchors of any heading it renames, keeps every test of Step 0 item 7 green
or changes it with the passage, and leaves the three command checks green
(it writes only commands in the surface dump). Step 22's two test changes go
red and green inside the step. The live scan, the only test that needs every
document done, is Step 28, after the last document step.

**Names**: `THREE_X_PATTERNS`, `THREE_X_NAMES`, `UNMIGRATED_RECORDS`,
`three_x_problems`, `ALLOWANCE`, `tests/test_docs_describe_4_0.py`,
`tests/test_migration_guide_4_0.py`, `docs/migration-guide-3.X-to-4.0.0.md`
are spelled the same in every step.

## Spec defects and gaps found while planning

Reported to the dispatching session, which corrected the spec after the
plan review (2026-10-22). Each item says what became of it.

1. **Gap: a handoff after the revision.** TCW-116's comment of 2026-10-22
   21:30 came after the spec's revision (21:23) and is not in "Handoffs
   answered". Answered in Step 3 as 2.4 (m) to (q) (decided while planning,
   6). **Fixed in the spec:** rows H19 and H20 (the 21:53 comment), items
   2.4 (m) to (s), and criterion 3.
2. **Defect: the suggestion lines cannot be written verbatim in the
   migration guide.** Design 4.1 (g) puts "the full suggestion lines" there,
   but each holds `tcw init` (and so on) in a code span, which 9.4 (d)
   refuses outside a mapping table's first column. **Fixed in the spec**
   (2.10 (d), 4.1 (g)): the lines are given word for word, split at the
   command (decided while planning, 5).
3. **Defect: `tcw new` in backticks fails the command check.** Design 4.1 (g)
   and H10 (5) write the mistyped commands in code spans, which `_check`
   reports as "no such verb". **Fixed in the spec** (4.1 (g)): prose
   (decided while planning, 9).
4. **Defect: P12 refuses a 4.0 output line.** `show` prints
   `overrides: <full id>` for an override (TCW-112 plan, choice 7 and its
   "Records" step; this plan first cited TCW-113 choice 8, which only places
   `overridden by:` after it), so the first P12 (`^\s*overrides:`) flagged a
   fenced example of 4.0 output. **Fixed in the spec** (9.2): P12 is
   narrowed to `^\s*overrides:\s*[^\s./]+/` (decided while planning, 10).
5. **Defect: "removed: TCW-99 is done"** (Design 6.4, UC-3's third gap) is
   false on `v4` until TCW-118. **Fixed in the spec** (6.4's table; decided
   while planning, 12).
6. **Wording: Design 9.3** says "at `b2fa5810` it prints 125 lines at
   `5a9ca9b7`", naming two commits for one count. At `2adac9c9` the grep
   prints 125 lines. **Fixed in the spec.**
7. **Gap: `KEY_PATHS`.** The spec's Design 9.1 allows a test whose expected
   text is a 3.x passage to change, but does not name
   `tests/test_configuration_text_home.py`'s `KEY_PATHS`, whose 24
   `projects.*` paths must go when `projects.md` is rewritten. **Already
   handled:** the plan review found this overstated, since spec 9.1 already
   allows "a test whose expected text is a 3.x passage this item rewrites"
   to change. No spec change; the count becomes 33 (decided while planning,
   7).
8. **Gap: blockers.** TCW-117 is blocked by TCW-106 to TCW-116 in fact, but
   its ticket records no blocker (`tcw work show TCW-117`, `blocked-by:`
   empty). The plan stage's step 5 asks for them to be recorded with
   `tcw work edit TCW-117 --blocked-by <ref>`; this planning session was
   told not to run `edit`, so the dispatching session records them (at
   least TCW-116, which itself follows TCW-106 to TCW-115). **Already
   handled:** `tcw work show TCW-117` now shows
   `blocked-by: tcw/TCW-116-tcw-4-0-tcw-migrate-from-3-x`.
