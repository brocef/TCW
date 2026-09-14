# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw work tracker import <ticket> [--part <id>] [--title <title>]`**, **`link
  <slug> <ticket> [--part <id>]`** and **`unlink <slug> --reason <text>`**, for
  claiming a Jira ticket and binding it to a work item.
  - The claim (`tcw/tracker/intake.py`, `read_ticket` then `claim`): refuse a done
    or someone else's ticket; apply the `transitions.claim` transition; `assign`
    only after it applied and only if unassigned; re-read and require the landing
    status (the matched transition's destination) and this account's `accountId`.
    Every outcome carries a row id (`1a`–`1f`, `3a`–`3f`) matching the spec's
    decision tables. Transition errors are carried as `detail`, never interpreted;
    auth, permission, rate-limit and not-found errors on the transition propagate.
  - A ticket assigned to this account that no longer offers the claim is bound
    without a transition (row `1e`), which is how an interrupted import completes.
  - The binding: new `tracker.yaml` entry in `WORK_SIDECARS` (`yaml_mapping`,
    `generated`), keyed by `(project, provider, ticket id, part)`. `find_binding`
    queries unresolved items only and raises `BindingProblem` on a malformed binding
    or two items holding one key. `unlink` moves the binding into an `unlinked`
    history and makes no tracker call.
  - `import` drops the item it created if the binding write fails, and names the
    item with `tcw work drop <slug> --confirm` if the drop fails too.
- **`JiraClient.apply_transition`, `assign`, and `description`**, the last reading
  the v2 endpoint so a description arrives as a wiki-markup string rather than a
  rich-text document tree.
- **Eval harness: `tool_input_contains` and `tool_input_absent` predicates.**
  They search only the `input` of `tool_use` content blocks (a `Read`'s
  `file_path`, a `Bash` command), not assistant text, user messages or tool
  results, so a routing check no longer passes because a loaded skill merely
  mentions a path. `tool_input_absent` fails with "no tool calls found" when a
  transcript has no tool calls at all, so an unrecognised transcript shape
  cannot pass it vacuously. The shape is checked against hand-built transcripts
  only; the first real run must confirm it.
- **Eval harness: a `bare` fixture variant and a per-case `fixture` key.**
  `python evals/seed_fixture.py --bare <dir>` commits the fixture's code files
  to a repository with no TCW set up. A case in `evals/evals.json` can name the
  variant it runs against in every arm. Seeding a bare fixture inside a TCW
  project raises `ValueError`, because `tcw` searches parent folders for
  `tcw-config.yaml` and would resolve to the outer project; the runner's default
  `eval-runs/` inside this checkout is such a place, so run bare cases with
  `--out` outside it. `run_evals` checks every bare arm's output folder before
  the dry run or any spawn, and exits 1 naming the case and arm, so a misplaced
  bare case can no longer stop a paid run partway through.

## Changed

- **`JiraClient.issue` URL-quotes the key** it puts in the request path.
- **`tracker.yaml` is in `OWNED_YAML_NAMES`**, so `tcw validate` reports one that is
  not a mapping, as it does for `state.yaml`.
- The `tcw work tracker` group's help no longer says read-only.
- **Eval harness: `files_changed_exactly` compares against the seeded commit.**
  It used to run `git diff --name-only HEAD~1 HEAD`, which measured whether the
  agent committed, and read the seeder's own last commit when the agent made
  none. It now takes the union of `git diff --name-only --no-renames
  <seeded_head>` (the working tree against the seeded commit) and `git ls-files
  --others --exclude-standard` (with `core.excludesFile` set to the null device,
  so the grading machine's global ignore file cannot change the answer), reads
  git's output as bytes so unusual file names survive, and fails with git's
  error if either command fails. `seed()` records `seeded_head` in its manifest, the
  runner copies it into `timing.json`, and `grade_run` passes it on. **A run
  directory recorded before this change has no `seeded_head` and now fails this
  check**, with evidence saying so, instead of returning the old misleading
  answer. The seeder excludes its own untracked `manifest.json`, and the
  `__pycache__/` and `.pytest_cache/` folders an agent leaves by importing or
  testing the code, through `.git/info/exclude`, so none is counted as a change. Case B10 no longer
  expects `src/reports.py`, which the seeded fixture never changes.
- **Eval harness: fixture variants are names.** `seed(dest, variant="control")`
  takes `"customized"`, `"control"` or `"bare"` in place of `customized: bool`,
  and raises `ValueError` on anything else. It also raises `ValueError`, before
  writing anything, when the destination folder exists and is not empty, since
  whatever was left there would be committed into the seeded commit; reusing an
  `--out` folder for `run_evals` now fails for that reason.
  `run_evals.variant_for` returns the name rather than a boolean.

## Fixed

- **A connection dropped after a tracker request was sent crashed the command.**
  `http.client.RemoteDisconnected` (and any `ConnectionError` or
  `http.client.HTTPException`) escaped `JiraClient._request` as a traceback; it now
  raises `TrackerUnavailable`, so a claim whose write may have landed reads the
  ticket back and reports the result as unknown.
- **Two `tcw work tracker show` notes overstated what one ticket can show**
  (GitHub issue #36). Both are `Assessment.detail` strings in
  `tcw/tracker/claim.py`.
  - The `CLAIM_NOT_OFFERED` note named two explanations, a wrong
    `transitions.claim` name or a ticket past the claim, and missed a ticket that
    has not reached it yet (for example, one still in Triage). It now names all
    three.
  - The note for an offered claim said exclusivity "can only be read from a
    ticket already in that status". On an exclusive workflow that is false: `show`
    never passes `landing_status` to `assess()`, so the landed ticket still reports
    `NOT_DETERMINED`. The note now says a landed ticket can reveal a workflow that
    is not exclusive, never one that is, and that exclusivity is confirmed only
    when a claim is made or from the workflow definition.
  - `docs/guide/work.md` and `skills/tcw-work/references/commands.md` repeated both
    two-case explanations and are corrected to match. Two tests in
    `tests/test_tracker_claimability.py` assert the new wording and the absence of
    the old.
