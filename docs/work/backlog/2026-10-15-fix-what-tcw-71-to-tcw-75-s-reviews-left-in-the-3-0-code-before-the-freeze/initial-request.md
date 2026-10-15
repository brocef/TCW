# Fix what TCW-71 to TCW-75's reviews left in the 3.0 code, before the freeze

A child of the TCW 3.0 epic (TCW-68). The reviews of TCW-71, 72, 73, 74, 77
and 75 filed findings that each child sorted as "needs a separate change".
They are in code under `tcw/` (and a few tests), so they must land on
`epic/tcw-3.0` before TCW-76's code freeze (its Task B3), after which nothing
under `tcw/` changes until the epic merges.

The owner's decision (2026-10-15), asked whether to fix only text before the
freeze and behavior later: **"Everything now"** — every finding below,
including the ones that change behavior, goes in before the freeze, and the
freeze waits for this item.

Out of scope: `docs/work/inbox/2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md`
(`evals/` only, which the freeze does not cover).

Each section below is one inbox entry, moved here verbatim; the entries are
removed from the inbox.

---

<!-- from docs/work/inbox/2026-10-13-tidy-what-tcw-71-s-reviews-left-for-the-jira-backend.md -->

## Tidy what TCW-71's reviews left for the Jira backend

Separate-change findings from TCW-71's verify review (2026-10-13), none of
them blocking:

1. **A dropped connection while posting a note invites a duplicate.** After a
   move with no screen, the note is posted on its own (`_post_note` in
   `tcw/work/jira/backend.py`). If that request drops after Jira received it,
   `MovedWithoutNote` says posting failed, which suggests posting again and so
   duplicating the comment. It could say the note may have been posted, or
   check the newest comments first.
2. **Two shapes of Jira's answers were never seen live.** `TCWTEST` has only
   global transitions and never needed a second results page, so
   `tests/work/jira/recorded/` has no `links.*.fromStatusReference` in the
   workflow definition, no `nextPageToken` from a search, and no transition
   screen that lists fields. The fake's versions of these are unchecked against
   Jira. A transition restricted to some statuses and a search over more than
   100 tickets on `TCWTEST` would record them.
3. **The user objects in `recorded/` keep `timeZone` and `locale`.** Not
   identifying on their own, but `capture.py` could replace them too.

---

<!-- from docs/work/inbox/2026-10-13-tidy-what-tcw-72-s-reviews-left-for-personal-configuration.md -->

## Tidy what TCW-72's reviews left for personal configuration

Separate-change findings from TCW-72's verify review (2026-10-13). None blocks
the epic.

1. **A YAML key that is itself a list crashes every command.** `? [a]\n: 1` in
   `tcw-config.yaml` or a personal file raises `TypeError` in
   `tcw/store/yaml_source.py`'s `_no_dup_keys`, which prints a traceback. It
   predates TCW-72. It should be a configuration problem naming the file.
2. **Two layers writing the same empty mapping blame the lower one.** If the
   project writes `completed: {}` and the local file writes `completed: {}`,
   `config show --origin` names the project file. The non-empty guard in
   `_merge` (`tcw/config.py`) keeps the first origin. Cosmetic.
3. **Only the first bad Jira credential key is reported.**
   `parse_jira_credentials` stops at the first one; with both
   `token-env` and `email-env` wrong, `validate` names one.
4. **`tcw work new --stage inbox` in a Jira project reads piped input before
   its usage error** (`tcw/work/cli.py`), so it can wait up to two seconds
   for nothing. TCW-72 moved the `--project` checks first; this one remains.
5. **`config show` writes a `!!binary` or `!!set` value under an unknown key
   over several lines.** Nothing TCW reads takes one.

---

<!-- from docs/work/inbox/2026-10-13-tidy-what-tcw-73-s-reviews-left-for-the-cli.md -->

## Tidy what TCW-73's reviews left for the CLI

Separate-change findings from TCW-73's verify review (2026-10-13). Each was
already true before TCW-73; none blocks the epic.

1. **`tcw capabilities reset` deletes local capabilities nested inside the
   override folder.** Inherit `auth/login`, override it, add
   `auth/login/nested`, then `reset auth/login`: the nested local capability is
   removed with no refusal. `reset` calls `_rm` on the override folder with no
   nested or referrer check (`tcw/store/fs.py`, `reset`). It should refuse as
   `rm` does.
2. **`--slug` is not checked.** `tcw taxonomy add --slug 'A B'` creates a
   folder named `A B` and exits 0. TCW-73's Design 4 lists a malformed slug as
   a usage error (exit 2).
3. **The scan for git commands that change state is incomplete**
   (`tests/work/test_git_write_scan.py`). Its verb list lacks `switch`,
   `restore`, `rebase`, `cherry-pick`, `update-ref`, `update-index`, `init`
   and `branch`; a `-c key=value` option would be read as the verb; the
   `FsStoreProvisioner: checkout` allowance covers the whole class rather than
   `_obtain`; and nothing checks that `status` keeps `--no-optional-locks`.
   Nothing in the code uses any of these gaps today.
4. **`tcw provision` can still ask for a password.** Git asks for HTTPS
   credentials and SSH passphrases on the terminal, not on standard input, so
   a private remote can prompt even though standard input is closed. Setting
   `GIT_TERMINAL_PROMPT=0` (and `BatchMode=yes` for ssh) in the environment
   `_git` passes would stop it. Suspected from reading the code, not run.
5. **This repository's implement-stage instructions name code that no longer
   exists.** `docs/lifecycle/implementation.md` names `descendant_nodes` and the
   2.x `--include-descendants` flag. The text is composed into
   `tcw work stage prompt implement`.
6. **`tests/test_upstream_projects.py` runs whatever `tcw` is first on PATH.**
   With the shared pyenv shim first, ten tests fail with a 2.x message. It
   should run the `tcw` of the interpreter under test (`sys.executable -m tcw`
   or the same folder's script).

7. **`list` and `rm` disagree about a sub-folder with no `meta.yaml`.**
   `_local_slugs` (`tcw/store/fs.py`) counts any readable folder as a term, so
   `taxonomy list` shows `invoice/sub`; but `rm invoice` treats it as part of
   `invoice` and deletes it (naming each file) when nothing refers to it.
   TCW-73 Design 8.2 defines a nested term by its `meta.yaml`, so `list`
   should probably agree.
8. **The retired-key message names a bare `tcw-config.yaml`.** Run from a
   sub-folder such as `p/docs`, `refuse_retired_config` names a file that is
   not in the current directory. It should name the path from the project root.
9. **`tcw work list` does not notice a child project's retired key.** The
   parent's own key is refused by every command, and `projects list`,
   `provision`, `taxonomy list` and `validate` refuse a child's; `work list`
   never opens the registry, so it exits 0.

Already assigned elsewhere, listed so they are not lost: `tcw serve` prints
`Serving TCW at <url>` rather than only the URL and never flushes standard
output, so a piped URL arrives only when the server exits (TCW-77); the
`review` and `qa` built-in prompts (TCW-74).

---

<!-- from docs/work/inbox/2026-10-15-tidy-what-tcw-74-and-tcw-77-s-reviews-left-elsewhere.md -->

## Tidy what TCW-74's and TCW-77's reviews left elsewhere

Separate-change findings from the verify reviews of TCW-74 (stage prompts and
skills) and TCW-77 (web viewer), 2026-10-15. None blocks the epic.

## Viewer (`tcw serve`)

1. **Taxonomy and capability edits skip the stale check when no revision is
   sent.** `revision` is optional on PATCH (`tcw/serve/records.py`, the two
   update routes), so a hand-made request without it overwrites another
   writer's change. The 2.x server behaved the same.
2. **A symbolic link inside the work path lets a file save write outside the
   project.** Nothing checks that the resolved path stays inside the item
   folder. Editing with the CLI or an editor has the same exposure. Low.
3. **`_ANCHOR_CACHE` (`tcw/store/project.py`) now lives for the whole server
   process**, though its comment assumes one CLI run. Harmless today (a few
   keys, thread-safe access); fix the comment or scope it.
4. **The stage-name scan in `tests/serve/test_no_stage_names.py` misreads some
   TypeScript.** It skips expressions inside `${...}`, ignores unquoted object
   keys and member access (`tabs.review`), and reads a regex after a keyword as
   a string. Nothing is hidden today.
5. **`Conflict` (`web/client/src/ui/content-views.tsx`) nests a `<div>` inside
   a `<p>`**, and React logs a DOM-nesting warning in tests. Cosmetic.

## Commands named in passing

6. **Commands wrapped across a line inside backticks are never checked** by
   `tests/test_documented_cli_surface.py` (the BACKTICKED pattern), e.g.
   `tcw/work/procedures/audit-backlog.md` and `plan.md`. Both are valid today.

## Lifecycle

7. **`tcw work advance` moves an item out of spec and plan with no document
   written.** No gate checks that a stage's document exists. Decide whether it
   should.
8. **Unattended runs have no rule for an item sitting at request**, the one
   stage that asks the user. Neither the autonomous skill nor the
   unattended-work procedure says what to do.

---

<!-- from docs/work/inbox/2026-10-15-tidy-what-tcw-75-s-reviews-left-in-code-text.md -->

## Tidy what TCW-75's reviews left in code text

Separate-change findings from TCW-75's round-1 review (2026-10-15). Each is
text in `tcw/` (or a test helper) that TCW-75, a documentation item, does not
own. Most are small enough to fix before TCW-76's code freeze, after which
nothing under `tcw/` changes until the epic merges.

1. **Error messages name removed keys.** `tcw/work/generate.py:180` and `:184`
   name `work.lifecycle.output-cap` and `work.lifecycle.timeout`; the keys are
   `work.hooks.output-cap` and `work.hooks.timeout`. An agent reading the
   message would set a key `tcw validate` refuses.
2. **A doubled quote in a refusal.** `tcw/work/open.py:108` builds
   `who = f"'{project_id}'"` and then appends `'s`, printing `'child''s work
   store is not in a git repository`.
3. **Out-of-date docstrings.**
   - `tcw/work/hooks.py:8-10` says `tcw serve` never runs hooks, but adopting a
     ticket through the viewer runs request `post` hooks
     (`docs/guide/web-viewer.md:86`, `tickets.adopt`).
   - `tcw/cli.py`'s `run_provision` says it is "the only command that reaches
     the network", which stopped being true with the Jira backend.
   - `tcw/store/base.py:5-6` says remote adapters are "possible but unbuilt".
   - `skills/README.md:85` still says "TCW-75 rewrites this skill" (TCW-74's
     file).
4. **An unreachable or missing Jira site is reported as "the tracker has no
   such resource"** by `tcw work list` (the client's message), which reads as
   a missing ticket rather than a missing site.
5. **Offline `tcw validate` in Jira mode skips the item-folder checks.**
   `tcw/validate.py:556-560` returns early for a `JiraBackend`, so references,
   stage-ahead warnings and each item's `capabilities.yaml` are checked only
   under `--remote` (`tcw/work/jira/remote.py:508-533`). The item folders are
   local files in both backends, so at least the `capabilities.yaml` check
   could run offline. TCW-75 documents the current behavior; deciding whether
   the code should change is this entry's question.
6. **The shared vocabulary scan reads one line at a time.**
   `tests/doc_vocabulary.py:61-68` (TCW-74) misses a 2.x phrase split across a
   line wrap (`TCW no` / `longer`). No owned document has one today; scanning
   each paragraph joined onto one line, with hits mapped back to line numbers,
   closes it.
7. **Offline Jira-mode validation reports `qa/` rounds it says are ignored.**
   With `backend: jira`, a `qa/round-1.md` with a bad verdict gets both "Jira
   keeps the qa record, so this folder is ignored" and "the latest qa round is
   invalid … `tcw work advance` refuses past qa until it has them"; the second
   is false, since advance does not read qa verdicts in Jira mode. Fix in
   `tcw/validate.py` `round_findings`: skip stages the layout marks external.
   (Found by TCW-75's confirming review.)
