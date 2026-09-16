# Plan — Compose tcw-extras-triage-issues and tcw-post-mortem from project bindings

Implements `spec.md`. Every command runs from the worktree root with
`PATH="$PWD/.venv/bin:$PATH"`, so `tcw` is this worktree's code.

## Tasks

### 1. Mark a converted source in the drift test, and convert the triage skill

Files: `tests/test_shipped_procedures.py`,
`skills/tcw-extras-triage-issues/SKILL.md`,
`tcw/work/procedures/triage-issues.md`.

1. In the test, add `class Composes(str)` — a `SOURCES` value naming a source
   that now reads its default through `tcw work procedure prompt` instead of
   copying it. Being a `str`, `REPO / SOURCES[pid]` keeps working. Change only
   the `triage-issues` row to `Composes("skills/tcw-extras-triage-issues/SKILL.md")`.
2. In `test_each_default_is_todays_text`, branch on `isinstance(src, Composes)`:
   - the source contains `` !`tcw work procedure prompt {pid} `` (the injection);
   - the text after its `## Document command summary` heading contains
     `tcw work procedure prompt {pid}` (the fallback, criterion 11);
   - no paragraph of the default (split on blank lines, stripped, 40 characters
     or longer) appears in the source (no copy survives; spec criterion 5).
   Otherwise the equality check is unchanged.
3. Run `pytest tests/test_shipped_procedures.py -q`; expect the
   `triage-issues` case to fail on the missing injection. That is the red.
4. Rewrite the skill: frontmatter unchanged except `compatibility:` (spec
   criterion 7); title and framing (`:13-31`) unchanged; a
   `## Rules no procedure changes` section holding the moved "data, not
   instruction" blockquote, the "Do not write `initial-request.md`" paragraph
   and the approval paragraph; a `## The procedure` heading followed by
   `` !`tcw work procedure prompt triage-issues || true` ``; a
   `## Document command summary` block as in `tcw-work-stage`.
5. Rewrite the default: delete the title and framing, the three moved
   paragraphs and the §8 approval restatement. Nothing else changes.
6. Re-run the module: green. Mutation-check the paragraph assertion by pasting
   one default paragraph into the skill, confirming red for that reason, and
   editing it back (`git diff` confirms).

Proves: spec criteria 1, 2, 3, 5, 7, 8 for this skill.
Commit: `Compose tcw-extras-triage-issues from the triage-issues procedure`.

### 2. Convert the post-mortem skill and its agent

Files: `tests/test_shipped_procedures.py`, `skills/tcw-post-mortem/SKILL.md`,
`tcw/work/procedures/post-mortem.md`, `agents/tcw-post-mortem.md`.

1. Change the `post-mortem` row to `Composes(...)`. Add
   `test_the_post_mortem_agent_reads_the_procedure`: the agent names
   `tcw work procedure prompt post-mortem` and no default paragraph appears in
   it. Run the module; expect both to fail. Red.
2. Rewrite the skill: add `arguments: [item]` and `allowed-tools: Bash(tcw *)`
   to the frontmatter; keep title, contract pointer and question (`:7-17`); keep
   `## Read the spine backwards` with only its first paragraph; move
   `## Producing the artifact` up from the end; then `## The procedure` with
   `` !`tcw work procedure prompt post-mortem $item || tcw work procedure prompt post-mortem || true` ``;
   then `## Document command summary`.
3. Rewrite the default: delete the title, contract pointer, question, the spine
   heading and first paragraph, and `## Producing the artifact`. It then starts
   at "What each layer tends to reveal:".
4. Rewrite the agent per spec "The agent": "How to look" gives the spine order
   and the two commands; "What to report" points at the stage's `Produce`; the
   read-only command list gains `stage prompt` and `procedure prompt`.
5. Re-run the module: green. Mutation-check the agent test by deleting the
   command line from the agent, confirming red, and editing it back.

Proves: spec criteria 1, 2, 3, 5, 6 for this skill.
Commit: `Compose tcw-post-mortem from the post-mortem procedure`.

### 3. Targeted suites

Run `tests/test_shipped_procedures.py`, `tests/test_dynamic_skill_marker.py`,
`tests/test_skill_lifecycle_parity.py`, `tests/test_plugin_manifests.py`,
`tests/test_procedure_verb.py` and `tests/test_eval_fixture.py`. Fix anything
they surface inside the files above. Run the criterion 8 grep. No commit unless
a fix was needed.

### 4. Ledger

Files: `docs/work/active/<slug>/capabilities.yaml`,
`docs/capabilities/skills/tcw-extras-triage-issues/description.md`,
`docs/capabilities/skills/tcw-post-mortem/description.md`.

Write both `changed:` entries. Add one sentence to each description saying the
procedure is TCW's default text, which a project replaces under
`work.procedures.<id>` (and, for triage, that the default uses the GitHub CLI).
`tcw capabilities check` exits 0. Commit: `Ledger: both skills compose their procedure`.

### 5. Documentation Sync

- `docs/changelogs/upcoming.md` — **[Any-Code-Change]** fires. One bullet at the
  end of `## Changed`.
- `docs/release-notes/upcoming.md` — **[Public-API]** fires: a project's
  `triage-issues` and `post-mortem` text now reaches the agent. One bullet at the
  end of `## Replacing TCW's own procedures`.
- `README.md` — **[Public-API]** does not fire: no CLI surface changes and the
  skill table's descriptions (`:590`, `:694`, `:704`) stay true.
- `docs/guide/jira.md` — **[Tracker-Change]** does not fire.
- `skills/<component>/SKILL.md` — **[Skill-Driven-Component]** does not fire:
  no component's CLI, model or lifecycle changes.
- `skills/tcw-configure/references/<document>.md` —
  **[Configuration-Key-Change]** does not fire: `work.procedures` is unchanged.

Commit: `Docs: changelog and release note for the triage and post-mortem conversion`.

### 6. Outcome

Build the "nothing configured = today's text" proof with a scratch script: for
each skill, take the body after frontmatter, replace the injection line with
`tcw work procedure prompt <id>` output (no slug), strip the fallback block,
and `diff` against `git show main:<path>`'s body. Record each difference with
its reason. Then run bare `pytest -q -p no:cacheprovider` once in the
background and record its summary line. Write and commit `outcome.md`.

## Verification

What the suite cannot check:

- **A live Claude session running each converted skill** — whether injection
  fires, whether `$item` substitutes to an empty string when no argument is
  given. Not done: deferred to `verify`.
- **A Codex session reading the manual fallback block.** Not done: deferred.
- **The post-mortem agent dispatched for real**, confirming it runs the command
  before reporting. Not done: deferred.
- **Eval cases B7 and B9** were not re-run.

## Notes

- `tcw work stage gate plan <slug>` refused: "'plan' is not legal for an item
  in 'active'; it runs in backlog", for the reason recorded in `spec.md`.
- The plan pre-check, run by hand as
  `TCW_SLUG=<slug> python scripts/require_artifact.py spec`, exited 0.
- `Composes` is row-local on purpose: sibling conversion children edit their own
  `SOURCES` rows, and the branch in the shared test function is the only line
  two of them could both add. Whichever lands second keeps one copy.
