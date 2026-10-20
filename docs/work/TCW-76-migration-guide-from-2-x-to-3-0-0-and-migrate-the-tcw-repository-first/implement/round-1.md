# Outcome (TCW-76): implement round 1

This file is TCW-76's first implement round, its 2.x `outcome.md`. The plan
(choice 5) meant it to be the migration log as well; Part A wrote the
sections below before the freeze. The migration itself, from step 0 on, is
logged elsewhere, in `docs/tcw-3.0-migration-log.md`, outside the work path
as the guide's rule 7 says (that log's "Deviations from the plan", item d).

## Part A: work-branch commits

On `work/2026-10-01-tcw-76-migration-guide-from-2-x-to-3-0-0-and-migrate-the-tcw-repository-first`:

- A1 `251569a6`, A2 `6235ead9`, A3 `794a740b`, A4 `40dfdb3c`, A5 `5ab7bd32`,
  A6 `3170763a`, A7 `06d9a8e5` (the guide corrected after the rehearsal),
  A10 `617743d9`, A9 `59f3abf8`, `dd750f6d`, `9801a77c`, `d38255cc`.

## Task A3: the composed prompts, checked by hand

In a scratch project whose `tcw-config.yaml` binds Design 6's files, with
`HOME` and `XDG_CONFIG_HOME` in scratch folders and `TCW_NO_PERSONAL_CONFIG=1`,
on the work branch's CLI:

- `tcw validate`: 0 errors.
- `tcw work stage prompt spec <plain item>`: exit 0; ends, before TCW's
  closing advance line, with `docs/lifecycle/templates/spec.md` (one
  `# Spec —` heading), after `abstraction.md` and `harness.md`.
- `tcw work stage prompt spec <item tagged bug>`: exit 0; ends with
  `spec-bug.md` only (one `# Spec —` heading).
- `tcw work stage prompt review <item>`: exit 0; ends with
  `docs/lifecycle/review.md`.
- `tcw work procedure create-work`: exit 0; ends with
  `docs/procedures/create-work.md`.

The `<slug>` in each template's first line is printed with the item's slug
filled in.

## Rehearsal

A filesystem-mode rehearsal of the guide (Task A7), in
`/private/tmp/claude-501/-Users-brian-Projects-TCW/156ae1ae-43a5-40bd-8529-f024d3ff909c/scratchpad/tcw76/rehearsal/`, with its own `HOME` and `XDG_CONFIG_HOME`. 2.8.1 came from
PyPI into its own virtual environment (`pip install tcw-cli==2.8.1`,
`tcw --version` printed `tcw 2.8.1`). The 3.0 CLI was the work branch's,
whose version string still reads `2.8.1` because the version is cut later;
its `tcw work advance --help` confirms it is 3.0.

### How the 2.8 project was built

With 2.8.1's own commands (each move ran the 2.x hooks and committed, as 2.x
did by default):

```sh
#!/bin/bash
# Builds the TCW-76 filesystem rehearsal: a 2.8.1 project holding one of every
# case Task A7 lists. Every command is echoed, so the log records it.
set -euo pipefail
B=/private/tmp/claude-501/-Users-brian-Projects-TCW/156ae1ae-43a5-40bd-8529-f024d3ff909c/scratchpad/tcw76
R=$B/rehearsal
rm -rf "$R"; mkdir -p "$R/home" "$R/xdg"
export HOME=$R/home XDG_CONFIG_HOME=$R/xdg
export PATH=$B/venv-28/bin:/usr/bin:/bin:/usr/sbin:/sbin
export GIT_CONFIG_NOSYSTEM=1
git config --global user.name "Rehearsal User"
git config --global user.email rehearsal@example.com
git config --global init.defaultBranch main
set -x

# The connected project.
mkdir "$R/other"; cd "$R/other"; git init -q
tcw init --id other
printf 'connected-projects:\n  parent:\n    shop: ../shop\n' >> tcw-config.yaml
git add -A; git commit -qm "other: tcw init"

# The project to migrate.
mkdir "$R/shop"; cd "$R/shop"; git init -q
tcw init --id shop
mkdir -p hooks prompts templates
cat > hooks/check.sh <<'EOF'
#!/bin/sh
# A 2.x hook: compares TCW_STATUS with a 2.x status and tests TCW_TRANSITION.
echo "hook: slug=$TCW_SLUG status=$TCW_STATUS transition=$TCW_TRANSITION root=$TCW_NODE_ROOT"
if [ "$TCW_TRANSITION" = start ] && [ "$TCW_STATUS" = backlog ]; then
  echo "starting from the backlog"
fi
if [ "$TCW_TRANSITION" = rework ]; then echo "rework of $TCW_SLUG"; fi
if [ -n "$TCW_RESOLUTION" ]; then echo "resolution $TCW_RESOLUTION"; fi
exit 0
EOF
chmod +x hooks/check.sh
cat > prompts/spec.md <<'EOF'
Write the spec for this request:

{{tcw:body}}
> {{line}}
{{/tcw:body}}
EOF
printf 'Bug spec outline.\n' > templates/spec-bug.md
printf 'Chore spec outline.\n' > templates/spec-chore.md
printf 'Spec outline.\n' > templates/spec.md
printf 'Plan prompt.\n' > prompts/plan.md
printf 'Post-mortem prompt.\n' > prompts/postmortem.md
cat > tcw-config.yaml <<'EOF'
id: shop
connected-projects:
  children:
    other: ../other
work:
  tags: [bug, chore, billing]
  lifecycle:
    timeout: 60
    output-cap: 4000
    stages:
      spec:
        prompt:
          - builtin: true
          - file: prompts/spec.md
      plan:
        - file: prompts/plan.md
        - command: echo plan-generated
      postmortem:
        pre:
          - command: sh hooks/check.sh
        prompt:
          - builtin: true
          - file: prompts/postmortem.md
    transitions:
      start:
        pre:
          - command: sh hooks/check.sh
      submit:
        post:
          - command: sh hooks/check.sh
      rework:
        pre:
          - command: sh hooks/check.sh
      complete:
        pre:
          - command: sh hooks/check.sh
      discard:
        post:
          - command: sh hooks/check.sh
      auto-delete:
        pre:
          - command: sh hooks/check.sh
    artifacts:
      spec:
        - file: templates/spec-bug.md
          when: { tags: [bug] }
        - file: templates/spec-chore.md
          when: { not_tags: [billing] }
        - file: templates/spec.md
EOF
printf '.claude/settings.local.json\n' >> .gitignore   # init wrote the completed/ and discarded/ rules
git add -A; git commit -qm "shop: tcw init and 2.x configuration"
tcw validate

# Items, made and moved with 2.8.1.
A=$(tcw work new "Add refunds" --priority 35 --effort medium --tag billing)
tcw work start "$A"                                           # active/
Rv=$(tcw work new "Show receipts" --priority 5 --tag billing)
tcw work start "$Rv"
printf '# Outcome\n\nReceipts shown.\n' > "$(tcw work path "$Rv")/outcome.md"
git add -A; git commit -qm "outcome"
tcw work submit "$Rv"                                         # review/ with outcome.md
D=$(tcw work new "Old idea" --priority 12)
tcw work complete "$D" --resolution wontfix --confirm                   # discarded/
git add -f "docs/work/discarded/$D"; git commit -qm "track $D"   # tracked despite the rule
X=$(tcw work new "Secret experiment")
tcw work complete "$X" --resolution superseded --confirm                # discarded/, ignored
I=$(tcw work new "Payments epic" --epic --priority 40)
C=$(tcw work new "Refund email" --initiative "$I" --blocked-by "$A" --blocked-by "legal sign-off")
RW=$(tcw work new "Fix rounding" --tag bug --complexity high)
tcw work start "$RW"
printf '# Outcome\n\nRounded.\n' > "$(tcw work path "$RW")/outcome.md"
git add -A; git commit -qm "outcome"
tcw work submit "$RW"
printf '# Rework\n\nStill off by one.\n' > "$(tcw work path "$RW")/rework.md"
git add -A; git commit -qm "rework note"
tcw work rework "$RW"
tcw work submit "$RW"
printf '# Refined outcome\n\nAccepted after the fix.\n' > "$(tcw work path "$RW")/refined-outcome.md"
git add -A; git commit -qm "accepted"
tcw work complete "$RW" --resolution done --confirm                     # completed/, rework + refined
git add -f "docs/work/completed/$RW"; git commit -qm "track $RW"
NO=$(tcw work new "Tidy docs")
tcw work start "$NO"
tcw work submit "$NO" || true
printf '# Refined outcome\n\nAccepted without an outcome.\n' > "$(tcw work path "$NO")/refined-outcome.md"
rm -f "$(tcw work path "$NO")/outcome.md"
git add -A; git commit -qm "accepted, no outcome"
tcw work complete "$NO" --resolution done --confirm || true
PM=$(tcw work new "Outage review")
printf '# Post-mortem\n\nWhat went wrong.\n' > "$(tcw work path "$PM")/post-mortem.md"
printf '# Spec\n\nThe spec.\n' > "$(tcw work path "$PM")/spec.md"
git add -A; git commit -qm "post-mortem"
RN=$(tcw work new "Rename me")
tcw work rename "$RN" 2026-10-15-renamed-item                 # renames.yaml
git add -A; git commit -qm "rename" || true
set +x
echo "A=$A Rv=$Rv D=$D X=$X I=$I C=$C RW=$RW NO=$NO PM=$PM RN=$RN" > "$R/slugs.txt"
```

Then by hand, for the cases 2.8.1 has no command for, and the step 12 plants
(in the scratch home folder, never the real one):

```sh
#!/bin/bash
# Hand placements for the TCW-76 rehearsal: the cases 2.8.1 has no command for,
# and the step 12 plants (in the scratch HOME, never the real one).
set -euo pipefail
B=/private/tmp/claude-501/-Users-brian-Projects-TCW/156ae1ae-43a5-40bd-8529-f024d3ff909c/scratchpad/tcw76
R=$B/rehearsal
export HOME=$R/home XDG_CONFIG_HOME=$R/xdg
export PATH=$B/venv-28/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd "$R/shop"
W=docs/work
set -x

# A child nested inside its parent's folder, with no `parent:` (pre-2.x layout).
mkdir -p $W/backlog/2026-10-15-payments-epic/2026-10-15-card-refunds
printf "slug: 2026-10-15-card-refunds\ntitle: Card refunds\ncreated: '2026-10-15'\nresolution: null\npriority: 25\n" \
  > $W/backlog/2026-10-15-payments-epic/2026-10-15-card-refunds/state.yaml
# A leftover blocked/ folder holding one item.
mkdir -p $W/blocked/2026-10-15-waiting-item
printf "slug: 2026-10-15-waiting-item\ntitle: Waiting item\ncreated: '2026-10-15'\nresolution: null\n" \
  > $W/blocked/2026-10-15-waiting-item/state.yaml
# Both request files on one item, a list-form capabilities.yaml, and `added:`.
printf '# Add refunds\n\nCustomers need refunds.\n' > $W/active/2026-10-15-add-refunds/initial-request.md
printf '# Intake\n\nFrom the support queue: refunds by card.\n' > $W/active/2026-10-15-add-refunds/intake.md
printf -- '- path: work/refunds\n  status: Supported\n' > $W/active/2026-10-15-add-refunds/capabilities.yaml
printf 'added:\n  - work/receipts\n' > $W/review/2026-10-15-show-receipts/capabilities.yaml
printf '# Notes\n\nScratch notes kept beside the documents.\n' > $W/review/2026-10-15-show-receipts/notes.md
# A link between one item's documents.
printf '# Plan\n\nFollows [the spec](spec.md).\n' > $W/backlog/2026-10-15-outage-review/plan.md
# An inbox entry whose name is not a date and words.
printf '# Invoices by email\n\nA customer asks for invoices by email.\n' > $W/inbox/invoices-by-email.md
# The project's agent guide names a removed command.
printf '# Shop\n\nStart work with `tcw work start <slug> --worktree`.\n' > CLAUDE.md
git add -A; git commit -qm "hand placements"

# Step 12 plants. The ignored per-user settings file in the primary checkout:
mkdir -p .claude
printf '{\n  "permissions": {"allow": ["Bash(tcw work submit:*)"]}\n}\n' > .claude/settings.local.json
# A Claude Code project folder found by its transcript's cwd, not its name.
P=$(pwd -P)
M=$HOME/.claude/projects/-unrelated-name
mkdir -p "$M/memory"
printf '{"type":"user","cwd":"%s","message":"hi"}\n' "$P" > "$M/0001.jsonl"
cat > "$M/memory/MEMORY.md" <<'EOF'
# Memory

- Check the board with `tcw work list` before starting.
- Write the user's acceptance into a file in the item's folder before closing it.
- [Reviews](reviews.md) — how acceptance is recorded
EOF
cat > "$M/memory/reviews.md" <<'EOF'
Acceptance is recorded in refined-outcome.md, written by the reviewer.
EOF
# A second project folder with no transcript for this project: not searched.
mkdir -p "$HOME/.claude/projects/-other-project/memory"
printf '{"type":"user","cwd":"/somewhere/else","message":"hi"}\n' > "$HOME/.claude/projects/-other-project/0001.jsonl"
printf 'Run tcw work submit for another project.\n' > "$HOME/.claude/projects/-other-project/memory/MEMORY.md"
# A user skill naming a removed command.
mkdir -p "$HOME/.claude/skills/ship-it"
printf -- '---\nname: ship-it\ndescription: Finish an item.\n---\n\nRun `tcw work submit <slug>` when the tests pass.\n' \
  > "$HOME/.claude/skills/ship-it/SKILL.md"
set +x
git status --short --ignored
tcw validate
```

2.8.1's `tcw validate` first refused `added: [work/receipts]` (no such
capability), so a capability was made with
`tcw taxonomy add Work "Work features" -s work` and
`tcw capabilities add work Receipts -s Supported`, the declaration became
`added: [work]`, and `Planning doc:` and `Tracker:` lines were appended to
that record. 2.8.1's `tcw validate` then printed `validate OK`, and the state
was tagged `tcw-2.x-final`.

The migration ran in a worktree, `git worktree add ../shop-migrate -b
migrate-to-3`, so the primary checkout's ignored `.claude/settings.local.json`
and the two ignored item folders existed only there.

### Each step, and its check

- **Step 0.** `tcw --version` → `tcw 2.8.1`; `git status --porcelain` → nothing;
  `git worktree list | grep -E '\[work/'` → nothing (grep exit 1); 2.8.1's
  `tcw validate` → `validate OK`. From the worktree,
  `git status --ignored --porcelain -- docs/work` printed nothing, and
  `git -C <primary> status --ignored --porcelain -- docs/work` printed
  `!! docs/work/completed/2026-10-15-tidy-docs/` and
  `!! docs/work/discarded/2026-10-15-secret-experiment/`. Check:
  `grep -E '^(Started|Starting commit): ' <log> | tail -n 2` printed both lines.
- **Step 1.** The plan below, answered by the rehearsal itself. Check:
  `grep -c '^## Approved plan' <log>` → `1`.
- **Step 2.** Filesystem mode: nothing.
- **Step 3.** Configuration rewritten. In the scratch folder, `tcw validate`
  first reported `other` as unresolved (exit 0); with `TCW_PROJECT_OTHER` set,
  two errors in `other`'s own 2.x configuration (`connected-projects` renamed,
  nonreciprocal connection); after `other`'s own key was renamed, four errors
  from `other`'s path back to the real `shop`; with `TCW_PROJECT_SHOP` set to
  the scratch folder as well, `0 errors, 0 warnings, 0 unresolved`, exit 0
  (repeated with `$SCRATCH` unresolved, as the guide now writes it: exit 0).
  Check: the old-key `grep` printed nothing.
- **Step 4.** Check: the status-folder `find` and the `item.yaml` loop printed
  nothing. **But the kept ignored item had been lost**: my own move loop used
  `git mv -k`, which skipped the untracked copy without a word, and deleting
  `completed/` took it; the check could not see it. Restored from the primary
  checkout, and the guide amended.
- **Step 5.** Check: `find … state.yaml tracker.yaml` and
  `grep -nE '^priority: [0-9]'` printed nothing. My first `item.yaml` writer
  produced one-line mappings, which that `grep` cannot read; rewritten one key
  per line, and the guide amended.
- **Step 6.** Filesystem mode: `find docs/work -name tracker.yaml` printed
  nothing.
- **Step 7.** Check: the document-name `find` and the verdict loop printed
  nothing. `qa/round-1.md` (rejected) and `qa/round-2.md` (accepted) with
  `judges: 1` for `fix-rounding`; `qa/round-1.md` with `judges: 0` for
  `tidy-docs`; both request files combined under `## Original intake`.
- **Step 8.** `invoices-by-email.md` became `2026-10-15-invoices-by-email` at
  `inbox`. Check: `ls docs/work | grep -x inbox` printed nothing.
- **Step 9.** The old-names `grep` printed nothing **before any rewrite**:
  the one live reference was `[the spec](spec.md)` in `outage-review`'s plan,
  which moved into `plan/` and only a separate search found. Rewritten to
  `../spec/spec.md`; the guide amended with that search as part of the check.
- **Step 10.** `hooks/check.sh` rewritten for `TCW_STAGE` and
  `TCW_FROM_STAGE`; `Planning doc:` and `Tracker:` removed; the `completed/`
  and `discarded/` rules, their `.gitkeep` exceptions and 2.x's comment line
  removed from `.gitignore`; `CLAUDE.md` rewritten. Checks: the variable
  `grep` over `<hook files>`, the capability `grep` and the `.gitignore`
  `grep` printed nothing; `grep -cx '/tcw-config.local.yaml' .gitignore` → `1`.
- **Step 11.** `tcw validate` → `0 errors, 7 warnings, 0 unresolved`, exit 0.
  The seven warnings are items placed at `implement` and `qa` with nothing
  written for earlier stages, listed in the log. `tcw work list --all --json`
  listed all twelve items at the plan's stages. Also exercised:
  `tcw work stage prompt spec 2026-10-15-card-refunds --no-exec` matched
  `spec-chore.md` only, as 2.x's first match did; `tcw work advance
  2026-10-15-renamed-item --to implement --force --reason … --dry-run` ran the
  rewritten hook (`stage=implement from=request`, "starting from the
  backlog").
- **Step 12.** The places command found `CLAUDE.md`, `~/.claude/skills`, the
  primary checkout's `.claude/`, and the memory folder of the project folder
  named `-unrelated-name` (found by its transcript's `cwd`); the folder
  `-other-project`, whose transcript names another path, was not searched.
  The files-to-read search printed all five planted files: `CLAUDE.md`, the
  `ship-it` skill, the primary checkout's `settings.local.json`, `MEMORY.md`
  and `reviews.md`. The prose line in `MEMORY.md` ("Write the user's
  acceptance into a file in the item's folder before closing it.") matched no
  name, and was found by reading the file in full. Decisions: the skill
  deleted; `settings.local.json` and the prose line rewritten; `reviews.md`
  rewritten as history, still naming `refined-outcome.md`; three lines kept.
  Check: `grep -c '^## Agent instructions'` → `1`; the `diff` printed nothing
  (exit 0); `tcw validate` exit 0. Replanting the deleted skill made the
  `diff` print it (exit 1), and removing it again made it pass.

### The rehearsal project's own log

Indented, so that none of its headings or blocks is read as this log's own:

    # TCW 3.0 migration log

    ## Run 1

    Started: 2026-10-15
    Starting commit: 79cf360799be6f5dcc30a0b636b768c6966a4cdc

    ## Approved plan

    **Backend:** filesystem mode. **Stages:** spec, plan, review, qa and postmortem all on.

    **Items** (folder → stage; fields; notes):

    - `2026-10-15-add-refunds` (active/) → `implement`; priority 35 → `high`, effort `medium`, tags `billing`, owner `rehearsal@example.com` → assignee. Request: `initial-request.md`, with `intake.md` appended under `## Original intake`. `capabilities.yaml` is a list → deleted.
    - `2026-10-15-show-receipts` (review/, outcome.md) → `qa`; priority 5 → `lowest`, tags `billing`. `outcome.md` → `implement/round-1.md`. `capabilities.yaml` `added:` → `new:`. `notes.md` stays. Review is on: completing it needs a review round first.
    - `2026-10-15-old-idea` (discarded/, tracked) → `discarded`; priority 12 → `low`; comment `Carried over from TCW 2.x: discarded as wontfix`.
    - `2026-10-15-secret-experiment` (discarded/, ignored, primary checkout only) → not kept: moved to `../ignored-items/`.
    - `2026-10-15-tidy-docs` (completed/, ignored, primary checkout only) → kept: copied in, `completed`; `refined-outcome.md` → `qa/round-1.md`, accepted, `judges: 0`.
    - `2026-10-15-payments-epic` (backlog/, `type: epic`) → `request`; priority 40 → `highest`; `type` dropped.
    - `2026-10-15-card-refunds` (nested in payments-epic) → moved to the top, `request`, parent `shop/2026-10-15-payments-epic`, priority 25 → `medium`.
    - `2026-10-15-refund-email` (backlog/) → `request`; `initiative` → parent `shop/2026-10-15-payments-epic`; blocked-by `shop/2026-10-15-add-refunds`; the free-text blocker "legal sign-off" is dropped.
    - `2026-10-15-fix-rounding` (completed/, tracked) → `completed`; outcome → `implement/round-1.md`; rework → `qa/round-1.md` rejected; refined → `qa/round-2.md` accepted; both `judges: 1`.
    - `2026-10-15-outage-review` (backlog/, spec, plan, post-mortem) → `plan`; documents to `spec/`, `plan/`, `postmortem/`.
    - `2026-10-15-renamed-item` (backlog/) → `request`. `2026-10-15-waiting-item` (blocked/) → `request`.
    - Inbox `invoices-by-email.md` → item `2026-10-15-invoices-by-email` at `inbox`.
    - No folder needs renaming at step 4. Prune list: none.

    **Configuration:** `connected-projects` → `projects`; `work.lifecycle.timeout`/`output-cap` → `work.hooks`; spec prompt keeps `inherit: true` + `prompts/spec.md`; plan's bare list → `prompt` with `prompts/plan.md` and the `command` entry as `generate`; postmortem keeps its prompt, its `pre` is removed; start and rework `pre` → `implement.pre` (once); submit `post` → `review.post`; complete `pre` → `completed.pre`; discard `post` → `discarded.post`; auto-delete removed. Templates: `spec-bug.md` when tags bug; `spec-chore.md` when not_tags [billing, bug]; `spec.md` when tags [billing], not_tags [bug]. Git example: not adopted.

    **Hooks:** `hooks/check.sh` rewritten for `TCW_STAGE`/`TCW_FROM_STAGE`/`TCW_PROJECT_ROOT`; the `TCW_RESOLUTION` test becomes a test of `TCW_STAGE`. `prompts/spec.md`'s `{{tcw:body}}` pair → `{{tcw:request}}`.

    **Project files:** capability `work`: `Planning doc:` and `Tracker:` removed. `.gitignore`: the completed/ and discarded/ rules removed, `/tcw-config.local.yaml` added. `CLAUDE.md` rewritten.

    **`<hook files>`:** `tcw-config.yaml`, `hooks/check.sh`, `prompts/spec.md`, `prompts/plan.md`, `prompts/postmortem.md`, `templates/spec-bug.md`, `templates/spec-chore.md`, `templates/spec.md`, `CLAUDE.md`.

    **Step 9 skips:** this log. **Log:** `docs/tcw-3.0-migration-log.md`.

    User's answer: "Approved as written." (The rehearsal answers its own question.)

    ### Renamed slugs (from renames.yaml, step 4)

    2026-10-15-rename-me -> 2026-10-15-renamed-item

    ## Step 11

    `tcw validate` exits 0 with seven warnings, each an item placed at a stage whose earlier documents 2.x never asked for (`stage is at implement but has nothing from spec`, and the like): `2026-10-15-add-refunds` (spec, plan), `2026-10-15-outage-review` (request), `2026-10-15-show-receipts` (request, spec, plan, review). Kept: they are true, and go when each item is finished. `tcw work list --all --json` lists all twelve items at the stages the plan gave.

    ## Agent instructions

    - `CLAUDE.md:3` (`tcw work advance <slug>`, rewritten at step 10): kept, correct for 3.0.
    - `~/.claude/skills/ship-it/SKILL.md:6` (`tcw work submit <slug>`): deleted, with the skill, which said nothing else.
    - `<primary checkout>/.claude/settings.local.json:2` (`Bash(tcw work submit:*)`): rewritten to `Bash(tcw work advance:*)`.
    - `~/.claude/projects/-unrelated-name/memory/MEMORY.md:3` (`tcw work list`): kept, correct for 3.0.
    - `~/.claude/projects/-unrelated-name/memory/MEMORY.md:4` (acceptance written into a file in the item's folder; found only by reading the file in full): rewritten to name a qa round and `tcw work path <slug> qa --next`.
    - `~/.claude/projects/-unrelated-name/memory/MEMORY.md:5` (link to `reviews.md`): kept.
    - `~/.claude/projects/-unrelated-name/memory/reviews.md:1` (`refined-outcome.md`, no `tcw` in the file): rewritten as history; the approved text still names `refined-outcome.md`.

    ```expected-names
    /private/tmp/claude-501/-Users-brian-Projects-TCW/156ae1ae-43a5-40bd-8529-f024d3ff909c/scratchpad/tcw76/rehearsal/home/.claude/projects/-unrelated-name/memory/reviews.md:Before TCW 3.0, acceptance was recorded in refined-outcome.md; it is now a qa round with a verdict.
```

### Where the guide was wrong or unclear, and what it says now (commit `06d9a8e5`)

1. 2.x's `tcw init` ignored `completed/` as well as `discarded/`. The guide
   only knew about ignored discarded folders. Now: both, at step 0, in the
   plan, in step 4 and in step 10's `.gitignore` check.
2. In a worktree, ignored folders exist only in the primary checkout. Now:
   kept ones are copied from there, others are moved out of it, and a plain
   `mv` is used because `git mv` skips an untracked folder.
3. A status folder could be deleted with an item still in it, and step 4's
   check could not see that. Now: a command shows each holds nothing but
   `.gitkeep` before it is deleted.
4. `{{tcw:body}}` was replaced with the request document's name in 2.x;
   `{{tcw:request}}` is replaced with the request's text in 3.0. The row
   now says so and asks for each sentence to be reread.
5. The template rule refused an earlier entry with `not_tags` alone, which can
   be converted by giving the later entry `tags`. Now it says so.
6. `graveyard.yaml` recorded every resolved item, not only deleted ones.
7. 3.0 reports a missing connected project as unresolved (exit 0), not exit 5;
   a connected project still on 2.x makes `tcw validate` fail on its key; and
   the scratch check of step 3 needs this project's own `TCW_PROJECT_<ID>` set
   to the scratch folder. Now: connected projects are migrated together, and
   step 3 says both.
8. Links between one item's documents break when step 7 moves them, and step
   9's check did not look for them. Now it does.
9. `item.yaml` written as a one-line mapping defeats step 5's check. Now: one
   key per line.
10. Items placed at `implement` and `qa` always warn about earlier stages with
    nothing written; the status-folder note claimed otherwise. Now it says the
    warnings are expected and are listed at step 11.
11. `blocked_by` entries are `slug:` and `external:` mappings; an inbox entry
    has no date, so it takes the date of the commit that added it.

## Criterion 10

Every `tcw` command the guide names, from `tests/test_migration_guide.py`'s
own list of invocations outside a mapping table's first column plus the
commands its tables call unchanged, run with `--help` on the work branch's
CLI:

```text
tcw work advance --help: exit 0
tcw work discard --help: exit 0
tcw validate --help: exit 0
tcw --help: exit 0
tcw provision --help: exit 0
tcw work rename --help: exit 0
tcw work list --help: exit 0
tcw work show --help: exit 0
tcw work path --help: exit 0
tcw init --help: exit 0
tcw work stage prompt review --help: exit 0
tcw work stage prompt qa --help: exit 0
tcw work stage prompt postmortem --help: exit 0
tcw work stage prompt --help: exit 0
tcw projects list --help: exit 0
tcw taxonomy show --help: exit 0
tcw capabilities show --help: exit 0
tcw init work --help: exit 0
tcw taxonomy add --help: exit 0
tcw capabilities list --help: exit 0
tcw capabilities add --help: exit 0
tcw capabilities extends add --help: exit 0
tcw capabilities extends rm --help: exit 0
tcw work tickets list --help: exit 0
tcw work tickets adopt --help: exit 0
tcw work new --help: exit 0
tcw work edit --help: exit 0
tcw work lifecycle --help: exit 0
tcw work procedure --help: exit 0
tcw config show --help: exit 0
tcw work comment --help: exit 0
tcw serve --help: exit 0
tcw taxonomy list --help: exit 0
tcw taxonomy search --help: exit 0
tcw taxonomy path --help: exit 0
tcw taxonomy rm --help: exit 0
tcw taxonomy extends add --help: exit 0
tcw taxonomy extends rm --help: exit 0
tcw capabilities search --help: exit 0
tcw capabilities path --help: exit 0
tcw capabilities set --help: exit 0
tcw capabilities reset --help: exit 0
tcw capabilities rm --help: exit 0
tcw capabilities drift --help: exit 0
tcw work docs --help: exit 0
tcw work tags list --help: exit 0
tcw work tags add --help: exit 0
tcw work tags rm --help: exit 0
tcw --version: exit 0
```

## Task A10: validating the reworded records

In a scratch project (`tcw init --id tcw` on the work branch's CLI, with the
work branch's `docs/taxonomy` and whole `docs/capabilities` copied in),
`tcw validate` printed `13 errors, 0 warnings, 0 unresolved`, every one a
retired `Planning doc` or `Tracker` field, which migration step 10 removes.
The only finding naming one of the three reworded records is that field on
`work/configure-the-work-store-location`; no link or other finding names
them.

## Task A9: the guide's review

Bounded adversarial review (`adversarial-code-reviewer`; the handoff chose it
over the plan's spec reviewer, since the questions were whether the guide
matches the code) of `e301bef5..617743d9`, run 2026-10-16. Rule: one review,
one fix round, one confirming round, then the owner decides.

- **Review: NOT DONE, 9 findings, all accepted.** REST version 2 reads text
  as Jira wiki markup (now version 3 with Atlassian's document format, built
  by `jq` functions checked against `mapping.py`); a rerun of step 6 could
  duplicate tickets once `tracker.yaml` is gone; `initial-request.md` was
  posted twice; inbox tickets had no summary; step 12 copied private memory
  lines into the committed log; three read-before-write lookups were
  incomplete (custom fields, comment paging, the time zone of the create
  search); the issue type, screen fields, option values and `ticket.key`;
  four 2.x names missing from step 12's search; the folder pattern and the
  credential variables. Fixed in `59f3abf8`, which also added the five
  behavior changes from the pre-freeze clean-up item.
- **Confirming review: NOT DONE, 2 findings plus 5 notes, all accepted.** A
  2.x import's `intake.md` never compared as contained; step 3's check was
  overstated (it reads only the configured and sub-task issue types). Fixed in
  `dd750f6d`.
- **The owner chose one more short review of those edits.** It found that
  the rule added in `9801a77c` (trust an import with no content-changing
  commit) could still delete an edited import unread in three cases. Fixed
  in `d38255cc`: an import is trusted only while it is byte for byte what
  2.x's import commit added, uncommitted changes included, checked in a
  scratch repository for an untouched, moved, edited-and-uncommitted, and
  moved-and-edited file; plus its notes (create-screen paging, "at most two
  issue types", deleting the saved check output, the `jq` note). This last
  commit was checked by its tests and a mutation (removing the comparison
  turns `test_a_2x_import_of_the_ticket_counts_as_contained_without_comparing`
  red), not by another review round.
- **Separate change, not done here:** `tests/test_migration_guide.py` can pass
  while the guide is wrong (its 2.x names are typed by hand, no 3.0 name is
  checked against the code, no check command is run). Generating the names
  from v2.8.1's source would close that.
- Tests: the guide's five test files, 991 passed, 6 skipped.

## Jira checklist (for the owner)

**Do not apply any line until told the freeze has begun** (migration step 2).
The released 2.8.x CLI that still moves `main`'s board names the `Start`
transition and finds its routes by the old transitions, so it breaks as soon
as they change.

Read on 2026-10-15 with REST `GET` only (nothing was written): project `TCW`
(id 10037, company-managed) uses the workflow scheme `TCW work scheme`
(10039), whose only workflow, for every issue type, is `TCW work`. Its
statuses are `Triage`, `To Do`, `In Progress`, `In Review`, `Done` and
`Won't Do`. Its transitions are `Create` (initial, to Triage), `Accept`,
`Start`, `Submit`, `Complete`, `Rework`, `Cancel`, `Stop` and `Reopen`, all
directed and none with a screen. The statuses `Specifying` (10042),
`Planning` (10043) and `In QA` (10044) already exist in the site but are not
in this workflow. The issue types are `Task`, `Sub-task`, `Bug` and `Epic`.
The custom fields `TCW Project` (`customfield_10076`, text), `TCW Item`
(`customfield_10042`, text), `Effort` (`customfield_10077`, single choice) and
`Complexity` (`customfield_10078`, single choice) all exist, each with one
global context. `Effort` and `Complexity` offer `low`, `medium`, `high` and
`very-high`, which 3.0 reads and writes as they are (it compares option names
ignoring case, with spaces read as `-`), so their options need no change. The
project's screens (`PRPI: Kanban Default Screen`, `… Bug Screen`, `… Epic
Screen`, ids 10010, 10011 and 10012, each one tab used for create, edit and
view) carry `TCW Item` but not `TCW Project`, `Effort` or `Complexity`. **They
belong to the issue type screen scheme `PRPI: Kanban Issue Type Screen
Scheme` (10002), which the `PRPI` project uses too**, so a field added to them
also appears on PRPI's tickets. The link type `Blocks` exists.

Each line below says how to confirm it was done. In Jira's settings, a
company-managed workflow is edited as a draft and then published.

1. Add the existing statuses `Specifying`, `Planning` and `In QA` to the
   workflow `TCW work`. Confirm: the project's statuses (Project settings,
   Issue types, or `GET /rest/api/3/project/TCW/statuses`) list all nine:
   Triage, To Do, Specifying, Planning, In Progress, In Review, In QA, Done,
   Won't Do.
2. In `TCW work`, add one global transition (the "allow all statuses to
   transition to this one" option) into each of the nine statuses: Triage,
   To Do, Specifying, Planning, In Progress, In Review, In QA, Done, Won't Do.
   Give each no screen, no condition and no validator, and name it after its
   status. Confirm: on any ticket, `GET
   /rest/api/3/issue/<KEY>/transitions` lists exactly one transition to each of
   the nine statuses other than the ticket's own, each with no fields beyond
   the comment.
3. In `TCW work`, delete the directed transitions `Accept`, `Start`,
   `Submit`, `Complete`, `Rework`, `Cancel`, `Stop` and `Reopen`. Keep
   `Create`. Confirm: the published workflow's transitions are `Create` and
   the nine global ones, and no status is reached by two transitions.
4. Publish the draft. Confirm: the workflow scheme `TCW work scheme` still
   maps every issue type to `TCW work`, and a ticket in each old status keeps
   its status (adding statuses and transitions maps nothing).
5. Put `TCW Project`, `Effort` and `Complexity` on the create and edit screen
   of every issue type the TCW project uses (Task, Sub-task, Bug, Epic). The
   screens 10010, 10011 and 10012 are shared with `PRPI`. **The owner chose
   on 2026-10-16 to give TCW its own copies first**, so PRPI is not touched:
   copy the three screens (`TCW: Kanban Default Screen`, `… Bug Screen`,
   `… Epic Screen`), copy the screen schemes that use them and point the
   copies at the new screens, copy the issue type screen scheme
   `PRPI: Kanban Issue Type Screen Scheme` (10002) as `TCW: Kanban Issue Type
   Screen Scheme` and point it at the copied screen schemes, assign that copy
   to the `TCW` project only, and then add the three fields to the copied
   screens. Confirm: `GET /rest/api/3/issuetypescreenscheme/project?projectId=10037`
   shows the copy, and PRPI's still shows 10002. Then: `GET
   /rest/api/3/issue/createmeta/TCW/issuetypes/<id>` lists all four TCW fields
   for each of the four issue types, and an existing ticket's edit
   metadata (`GET /rest/api/3/issue/<KEY>/editmeta`) lists them too.
6. No other workflow needs the same changes: no issue type in `TCW` uses
   another workflow. Confirm: `GET
   /rest/api/3/workflowscheme/project?projectId=10037` shows `TCW work
   scheme` with `defaultWorkflow: TCW work` and no issue type mappings.

After the changes, migration step 3's `tcw validate --remote` is the reading
that confirms them together.
