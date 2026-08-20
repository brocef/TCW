# Plan — Enforce the gitignore trap at write time, not only at init

Line numbers verified against **`406b043`**. Every one below is written
`file:NNN (406b043)` and every one was re-derived against that tree, not copied
from the spec. **Address the code by symbol first** — `tcw/store/fs.py` moved
twice while this plan was being written (`a875de9` → `7a7d735` → `406b043`,
shifting `_warn_off_trunk` by +117 lines), and it will move again before Task 1
starts. Re-derive before editing; the symbols are stable, the numbers are not.

The empirical checks in the next section were run against **`a875de9`**. The
commits since (`0d6ac4d` "containment: bound work-item resources", plus two
work-tracking commits) touched `tcw/store/fs.py` and added
`tests/test_store_bounds.py`; none of them touched `git_stage`, `git_mv`,
`git_ignored`, or `tests/test_work_autocommit.py`, and every citation in those
checks was re-verified against `406b043`. The findings stand.

**Baseline suite size: re-measure it, do not copy it.** At `a875de9` it was
**1859 passed** (7m17s); at `406b043` `pytest --collect-only -q` reports **1883
collected**. Run `python -m pytest -q` immediately before Task 1 and use *that*
number as criterion 10's `N`.

---

## Empirical re-checks (done at plan time, in throwaway repos under `/tmp`)

The spec's load-bearing claims were re-run, not re-read. Method: a `trace.py`
that monkeypatches `tcw.store.fs.git_stage` / `git_mv` to print
`(node_root, path, ignored, exists)` before delegating, plus a full prototype of
the change applied to a `git archive HEAD` copy at `/tmp/tcwcopy`. **Nothing was
written to `/Users/brian/Projects/TCW`.**

### R1 — `complete` really does reach `git_stage` with an ignored `completed/…/state.yaml`. **CONFIRMED.**

On a node scaffolded by `tcw init --id … work` (whose `.gitignore` carries the
default `docs/work/completed/*` rule), both completion routes were traced:

```
# active → completed
TRACE git_mv    src=…/docs/work/active/<slug>   dst=…/docs/work/completed/<slug>  dst_ignored=True  src_exists=True
TRACE git_stage path=…/docs/work/completed/<slug>/state.yaml                      ignored=True      exists=True

# review → completed  (second item, submitted first)
TRACE git_mv    src=…/docs/work/review/<slug>   dst=…/docs/work/completed/<slug>  dst_ignored=True  src_exists=True
TRACE git_stage path=…/docs/work/completed/<slug>/state.yaml                      ignored=True      exists=True
```

So criterion 3's silencing is load-bearing at **both** guard sites, on **both**
routes — not only via `_set_fields_at` as the spec traced, but also via
`git_mv`'s ignored-destination branch. Without the `RESOLVED_STATUSES` filter
every `tcw work complete` on a default node would print **two** warning lines.

### R2 — `git_mv`'s ignored-destination branch is reached by `submit` when `docs/work/review/*` is ignored. **CONFIRMED, and worse than the spec says.**

```
TRACE git_mv    src=…/docs/work/active/<slug>  dst=…/docs/work/review/<slug>  dst_ignored=True  src_exists=True
TRACE git_stage path=…/docs/work/review/<slug>/state.yaml                     ignored=True      exists=True
tracked before: docs/work/active/<slug>/state.yaml
tracked after:  (none)
HEAD: "tcw work: <slug> → review"      # the deletion, auto-committed
```

**`submit` hits BOTH sites, so criterion 5 will produce TWO warning lines**, one
naming `docs/work/review/<slug>` (from `git_mv`) and one naming
`docs/work/review/<slug>/state.yaml` (from `git_stage`). Verified against the
prototype:

```
tcw: a .gitignore rule hides docs/work/review/2026-08-20-gamma; …
tcw: a .gitignore rule hides docs/work/review/2026-08-20-gamma/state.yaml; …
```

This is the "repeated warnings inside one command" risk the spec accepted, and
it is not hypothetical — it fires on the *headline* `git_mv` scenario. **The
criterion-5 test must assert a substring over the whole `err`, never
`err.count("\n") == 1` or an exact-string equality.** Recorded so the
implementation does not "fix" it into a de-duplication cache the spec forbids.

### R3 — Blast radius on the 248 `capsys.readouterr()` sites. **ZERO. Measured, not predicted.**

Two independent checks:

1. **Static.** Every assertion of the form `err == ""` was read in context.
   All eight are either read-only commands or unit tests of `read_piped_stdin`,
   with **no write** anywhere in the test body:

   | Site (406b043) | What it runs | Writes? |
   | --- | --- | --- |
   | `tests/test_capabilities.py:76` | `tcw capabilities path` | no |
   | `tests/test_work.py:579,584` | `tcw work path`, `tcw work inbox path` | no |
   | `tests/test_taxonomy.py:450` | `tcw taxonomy path` | no |
   | `tests/test_external_work_store.py:66,71` | `tcw work path`, `tcw work inbox path` | no |
   | `tests/test_stdin.py:61,106,117,261` | `read_piped_stdin` unit tests | no |

2. **Dynamic.** The full change was prototyped on `/tmp/tcwcopy` (a
   `git archive HEAD` copy) and the whole suite run against it — twice:

   | Prototype | Result |
   | --- | --- |
   | `git_stage` guard only | **1859 passed**, 0 failed, 0 errors (437s) |
   | `git_stage` **+** `git_mv` guards (the shipping shape) | **1858 passed, 1 skipped**, 0 failed, 0 errors (432s) |

   The one skip is **environmental, not caused by the change**:
   `tests/test_session_bootstrap.py:353` — _"no editable tcw install here —
   nothing for the guard to protect"_. The `/tmp` copy is not an editable
   install; in the primary checkout that test runs, which is why the `a875de9`
   baseline was 1859. Confirmed by `-rs`.

   `tests/test_work_autocommit.py:606 (406b043)` — the one existing test that deliberately
   gitignores a destination folder — makes **no** stderr assertion, so it is
   unaffected.

### R4 — Implementation trap found while prototyping. **Read this before writing Task 2.**

The first prototype put the *existence* filter inside the shared helper. That
silently killed the `git_mv` warning: at the moment of the check `dst` does
**not** exist yet (the folder is moved there afterwards), so the helper filtered
its own only argument away and `submit` printed nothing.

**The shared helper must do the `RESOLVED_STATUSES` filter and the rendering
only. Each call site applies its own existence test** — exactly as the spec's
Design says ("skip a dropped path that does not exist" in `git_stage`; "the
existence filter is applied to `src` here" in `git_mv`). This is still one
helper and two call sites; the per-site guard is one line each.

### R5 — Two factual corrections to the spec, found while executing its criteria

Neither changes the design. Both change what a test may be written against.

- **There is no `tcw work discard` command.** Goal 3 names one. The real route
  to `docs/work/discarded/` is **`tcw work complete <slug> --resolution wontfix
  --confirm`** (`tcw/work/cli.py:1273,1480 (406b043)` — "anything else →
  discarded"). `tcw work drop` is a *hard delete*: it removed the item from disk
  entirely and left `docs/work/discarded/` empty. Criterion 4's own wording
  ("Same as (3) with `--resolution wontfix`") is already correct; only Goal 3's
  prose is wrong. **Task 1's discard test must use `complete --resolution
  wontfix`, not `drop`.**
- **The skill path is `skills/tcw-work/SKILL.md`, not `skills/work/SKILL.md`.**
  Criterion 12 names the latter; `ls skills/` gives `tcw-work`. Cosmetic, but
  the Documentation Sync section below uses the real path.

Also observed: criterion 8 says "`git status --porcelain` after it must show the
item staged under `docs/work/active/`". It will not — `start` **auto-commits**,
so `git status --porcelain` is *empty* and the item is at `HEAD`. Assert
`git ls-files docs/work/active/<slug>/state.yaml` is non-empty instead (verified
both on `main` and on the prototype).

---

## The exact message string

One `print`, one f-string, byte for byte. Copy this into the implementation and
into the tests; do not retype it from memory.

```python
print(f"tcw: a .gitignore rule hides {', '.join(shown)}; it is on disk but "
      f"git will not record it. Remove the rule, or run `git add -f` on it.",
      file=sys.stderr)
```

Rendered, for a single path (this is the literal line the prototype emitted and
the line the tests assert against):

```
tcw: a .gitignore rule hides docs/work/backlog/2026-08-20-secret-plan/state.yaml; it is on disk but git will not record it. Remove the rule, or run `git add -f` on it.
```

- `shown` is the warned paths rendered **relative to `node_root` when
  `Path.relative_to` succeeds, absolute otherwise**, joined with `", "`.
- The singular "it is on disk" is kept for the multi-path case too. Accepted:
  one string beats two, and the multi-path case only occurs in an
  already-broken setup.
- Tests should assert on the **substrings** `".gitignore"` and the path, not on
  the whole line — see R2.

---

## Tasks

Four tasks, four commits, `pytest` green at every boundary. No task adds code
that no later task calls.

### Task 1 — `_warn_hidden` + the `git_stage` guard, with its tests

**Modifies:** `tcw/store/fs.py`, `tests/test_work_autocommit.py`.

1. Add a module-level `_warn_hidden(node_root: Path, *paths: Path) -> None`
   immediately above `git_stage` (`tcw/store/fs.py:301 (406b043)`). It:
   - drops any `p` where `set(p.parts) & set(RESOLVED_STATUSES)` — the
     **absolute** path's components, per the spec's Design;
   - returns early if nothing survives;
   - renders each survivor via `p.relative_to(node_root)` inside
     `try/except ValueError`, falling back to `str(p)`;
   - emits **the exact string above**, once, to `sys.stderr`.
     `sys` is already imported (`tcw/store/fs.py:20 (406b043)`);
     `RESOLVED_STATUSES` is already imported (`tcw/store/fs.py:34 (406b043)`,
     from `tcw/store/base.py:453 (406b043)`).
   - **It does not test existence** — see R4.
   - Carry the two `ponytail:` notes the spec calls for: the component-match
     ceiling (`# ponytail: component match, not store-relative — a repo path
     containing 'completed' silences the warning; take the store root as an
     argument if that ever bites.`) and the no-de-duplication note.
2. In `git_stage` (`tcw/store/fs.py:301-308 (406b043)`), compute the ignored set
   once instead of twice, and warn about the ones that exist:

   ```python
   ignored = [p for p in paths if git_ignored(node_root, p)]
   _warn_hidden(node_root, *(p for p in ignored if p.exists() or p.is_symlink()))
   live = [str(p) for p in paths if p not in ignored]
   ```

   `p.exists() or p.is_symlink()` is the idiom already used at
   `tcw/store/fs.py:674 (406b043)` for the dangling-symlink case. The
   `git add` invocation and the paths it receives are unchanged — that is
   criterion 7.
3. Tests go in `tests/test_work_autocommit.py`, in a **new section appended
   after** the existing `# ── a gitignored destination status folder ──` block
   (`tests/test_work_autocommit.py:604-632 (406b043)`). Reuse that file's
   existing `node()`, `make_item()`, `committed()`, `porcelain()` helpers — its
   `node()` already runs the **real** `init`, so the default resolved-ignore
   rules are present, which is exactly what the silencing tests need. **No new
   test file, no new fixture.**

   Four tests:

   | Test | Criterion | Asserts |
   | --- | --- | --- |
   | `test_a_hidden_write_warns_on_stderr_and_still_writes` | 1, 2 | append `docs/work/backlog/*-secret*` to `.gitignore`, commit, `st.create("Secret plan", created="2026-08-20")`; `capsys.readouterr().err` contains `".gitignore"` **and** `"docs/work/backlog/2026-08-20-secret-plan"`; `state.yaml` exists on disk; the slug appears in `st.list()`; no exception |
   | `test_completing_into_the_ignored_default_is_silent` | 3 | default node, `make_item` → `start` → `complete(slug, "done", [])`; `".gitignore" not in capsys.readouterr().err`; run it for **both** routes (`active → completed` and `submit` first, then `review → completed`) — R1 proved both reach the guard |
   | `test_discarding_into_the_ignored_default_is_silent` | 4 | same, `complete(slug, "wontfix", [])` — **not** `tcw work drop`, see R5; assert the item landed under `docs/work/discarded/<slug>` |
   | `test_a_vacated_source_does_not_warn` | 8 | with `docs/work/backlog/*-secret*` ignored, `st.start(slug)`; `".gitignore" not in err`; `git ls-files docs/work/active/<slug>/state.yaml` is non-empty (**not** `porcelain()` — `start` auto-commits, see R5) |

   Criterion 7 rides along: each of the four asserts `porcelain(root)` matches
   what the same sequence leaves on `main` (empty for the auto-committing
   transitions; the hidden-write test's tree is untouched because the path was
   never stageable).

4. **Red first (criterion 10).** Before writing step 1–2, write the tests, run
   `python -m pytest -q tests/test_work_autocommit.py -k gitignore_or_hidden`,
   watch tests 1 and 2 of the table **fail for the right reason** (empty `err`,
   not a fixture error). Tests 3 and 4 pass on `main` — that is fine and
   expected; they are regression locks, not red-first tests. Then implement.
   Do not use `git stash push -q tcw/store/fs.py` as the spec suggests — other
   agents are working in this repo concurrently; write the tests first instead,
   which gives the same evidence without touching the stash.

**Commit 1:** `fix: warn when a .gitignore rule hides a staged store write`

**Green at this boundary?** Yes. `git_mv` is untouched; `_warn_hidden` has a
caller.

---

### Task 2 — the `git_mv` guard, with its tests

**Modifies:** `tcw/store/fs.py`, `tests/test_work_autocommit.py`.

1. In `git_mv`'s ignored-destination branch (`tcw/store/fs.py:360 (406b043)`),
   **before** the `git rm --cached`:

   ```python
   if src.exists() or src.is_symlink():
       _warn_hidden(node_root, dst)
   ```

   The existence test is on `src` (what is on disk and about to become
   invisible); the *reported* path is `dst` (where it is going, and the path the
   rule actually names). `RESOLVED_STATUSES` filtering inside `_warn_hidden`
   keeps `completed/`/`discarded/` silent. The two `_git` calls and the
   `shutil.move` are byte-identical — criterion 7.
2. Two tests, appended to the same section:

   | Test | Criterion | Asserts |
   | --- | --- | --- |
   | `test_an_ignored_non_resolved_destination_warns` | 5 | node with `docs/work/review/*` appended to `.gitignore` and committed; `make_item` → `start` → `submit`; `err` contains `".gitignore"` and `"docs/work/review/<slug>"`. **Substring over the whole `err`** — R2 proved this command emits two lines |
   | `test_the_resolved_destinations_stay_silent_through_git_mv` | 6 | direct `git_mv(root, active/<slug>, completed/<slug>)` on a default node; `".gitignore" not in err` — an explicit unit-level lock on top of the command-level coverage in Task 1 |

3. **Red first.** Write both, watch test 1 fail on empty `err` against the
   Task-1 tree, then implement.

**Commit 2:** `fix: warn when git_mv untracks an item into an ignored destination`

**Green at this boundary?** Yes. Task 1's tests still pass — nothing in Task 1's
four scenarios reaches `git_mv` with a non-resolved ignored destination, and
Task 1's tests assert substrings, never line counts (R2 is the reason that
constraint is written into Task 1 rather than discovered here).

---

### Task 3 — the two capability text deltas

**Modifies:**
`docs/capabilities/work/keep-resolved-work-out-of-git/description.md`,
`docs/capabilities/work/configure-the-work-store-location/description.md`.

Text only. **No status flip, no new record, no `meta.yaml` change, no taxonomy
entry.** Follow `tcw capabilities` conventions — first person, `tcw://C/…` refs.

1. **`work/keep-resolved-work-out-of-git` (`cap-7e064f`).** Its closing claim
   currently reads _"Nothing about this is specific to `completed/` or
   `discarded/`: any transition destination I have ignored behaves the same
   way, and a node that ignores nothing sees no change whatsoever."_ That stays
   true of the *behaviour* and stops being true of the *output*. Add one
   paragraph immediately after it: a destination outside `completed/` and
   `discarded/` now prints an advisory line on stderr, because TCW cannot tell a
   deliberate rule from an accidental one; those two, and only those two, stay
   silent.
2. **`work/configure-the-work-store-location` (`cap-46e036`).** It advertises
   only the `init`-time refusal at `description.md:18`
   (_"including a store whose items the repository's own ignore rules would
   hide"_). Add one sentence there: a rule that arrives *after* `init` — written
   by hand, naming one slug, or pulled in — is no longer invisible; the write
   itself says so.
3. Run `tcw validate` and `tcw capabilities check`; both must pass (criterion 11).

**Commit 3:** `capabilities: a hidden write now announces itself`

**Green at this boundary?** Yes — no code touched.

---

### Task 4 — Documentation Sync pass

**Modifies:** `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`.

Run `tcw work docs`, then write both entries against the **finished** diff (not
against this plan). See the Documentation Sync section for the per-entry
evaluation this task discharges.

- `docs/changelogs/upcoming.md` — a bullet under the existing `## Fixed`
  heading. Technical: name `git_stage`, `git_mv`, `_warn_hidden`,
  `RESOLVED_STATUSES`, the absolute-path component match and why, the
  existence filter and why (a vacated source staged as a deletion), and the
  known multi-line output on a single command (R2).
- `docs/release-notes/upcoming.md` — a new `##` section. Plain language, **no**
  internal module names. Roughly: "an item TCW writes but Git will not record
  now says so". Name the reproduction (a `.gitignore` rule added after setup),
  say the write still happens and the exit code is unchanged, and say that
  `completed/` and `discarded/` stay quiet because that is TCW's own doing.
- **Do not bump the version.** Per the spec's Notes, this ships batched with the
  other four `bug`-tagged items in a single patch release; the cut is not this
  item's decision.

**Commit 4:** `docs: record the write-time gitignore warning`

**Green at this boundary?** Yes.

---

## Acceptance criteria → task

Every criterion has a task; every task is required by a criterion.

| # | Criterion (abbreviated) | Discharged by |
| --- | --- | --- |
| 1 | The reported case warns on stderr | **Task 1**, `test_a_hidden_write_warns_on_stderr_and_still_writes` |
| 2 | …and still writes, exit 0, no new exception | **Task 1**, same test |
| 3 | `complete` is silent | **Task 1**, `test_completing_into_the_ignored_default_is_silent` (both routes, per R1) |
| 4 | `discard` is silent | **Task 1**, `test_discarding_into_the_ignored_default_is_silent` (via `--resolution wontfix`, per R5) |
| 5 | `git_mv` warns on a non-resolved ignored destination | **Task 2**, `test_an_ignored_non_resolved_destination_warns` |
| 6 | `git_mv` stays silent on the resolved destinations | **Task 2**, `test_the_resolved_destinations_stay_silent_through_git_mv`, plus Task 1's criteria 3 and 4 tests |
| 7 | No behavioural change (disk + `git status --porcelain`) | **Task 1** step 2 and **Task 2** step 1 keep the git invocations byte-identical; asserted by the `porcelain()` / `ls-files` checks in both tasks' tests |
| 8 | A vacated source does not warn | **Task 1**, `test_a_vacated_source_does_not_warn` |
| 9 | Chokepoint, not per-caller | **Tasks 1 and 2** are scoped to `tcw/store/fs.py` + one test file; checked in Verification (V1) |
| 10 | Suite green and grew (≥ the freshly measured `N`) | **Tasks 1 and 2** (red-first discipline, six new tests); checked in Verification (V2) |
| 11 | `tcw validate` and `tcw capabilities check` pass; both capability texts updated | **Task 3** |
| 12 | Changelog + release notes carry an entry; README and the work SKILL evaluated and the evaluation recorded | **Task 4** + the Documentation Sync section below |

No task exists that no criterion needs.

---

## Documentation Sync

`tcw work docs` on `406b043` returns four entries. All four evaluated:

| Entry | Trigger | Fires? | Reason |
| --- | --- | --- | --- |
| `README.md` | `[Public-API]` | **No** | No command, subcommand, flag, argument, or exit code is added or changed. The public CLI surface is byte-identical; the only difference is one advisory line on stderr in a misconfigured repository. README documents install, commands, and quickstart — none of which move. |
| `docs/release-notes/upcoming.md` | `[Public-API]` | **Yes** | User-visible behaviour change: a command that was silent now prints an advisory. A user who has ignored a live status folder will see new output. **Task 4.** |
| `docs/changelogs/upcoming.md` | `[Any-Code-Change]` | **Yes** | `tcw/store/fs.py` changes. Unconditional trigger. **Task 4.** |
| `skills/tcw-work/SKILL.md` | `[Skill-Driven-Component]` | **No** | The trigger is "the component it drives changes — its CLI surface, model/fields, lifecycle, or guardrails". None of the four move: no CLI surface change (criterion 9 forbids touching any CLI module), no field on `WorkItem`, no lifecycle transition added or altered, and no guardrail — the warning **does not refuse or gate anything** (Non-goals: "Refusing the write"), so there is nothing new for the skill to teach an agent to satisfy or work around. Checked: `skills/tcw-work/SKILL.md` says nothing about `.gitignore` today. (Path note: the spec's criterion 12 writes `skills/work/SKILL.md`; the real path is `skills/tcw-work/SKILL.md` — R5.) |

Matches the spec's prediction. The two "no" verdicts are recorded here, which is
what criterion 12 asks for.

---

## Verification

What `pytest` cannot prove, to be done by hand before `tcw work submit`.

- **V1 — criterion 9 (chokepoint).** `git diff --stat main...HEAD` for the code
  commits must list **exactly** `tcw/store/fs.py` and
  `tests/test_work_autocommit.py`. Then `git diff main...HEAD -- tcw/store/fs.py`
  and confirm the hunks fall only inside `_warn_hidden`, `git_stage`, and
  `git_mv` — no `_stage`/`_mv` override at `tcw/store/fs.py:994,1002,2282,2290
  (406b043)`, no `FsWorkStore` method, no `tcw/work/cli.py`, no `tcw/cli.py`,
  no `tcw/serve/`. A test suite cannot assert the *shape* of a diff.
- **V2 — criterion 10 (grew, and the red runs were real).** `python -m pytest -q`
  reports `≥ N passed` (with `N` measured on the branch point, not copied from
  this plan — see the header), `0 failed`. Separately, record for each of the
  criterion-1 and criterion-5 tests what the **red** run printed, and confirm
  the failure was an empty/short `err`, not a fixture error. A green suite
  cannot prove a test was ever red.
- **V3 — criterion 7 (byte-identical git behaviour), by hand.** For each of the
  five scenarios, run the command on a `/tmp` node against `main` and against
  the branch and `diff` the outputs of `git status --porcelain`,
  `git ls-files docs/work`, `git log --oneline`, and `find docs/work -type f`.
  The suite checks `porcelain` at a few points; only this proves the *whole*
  observable git state is unchanged.
- **V4 — the `tcw serve` path, by hand.** `tcw serve` reaches the same
  `FsWorkStore` methods (`tcw/serve/__init__.py` `do_POST`/`do_PATCH`/`do_PUT`/
  `do_DELETE`). Start a server on a node with `docs/work/review/*` ignored,
  `POST /api/work`, and confirm the warning appears **in the server's terminal**
  and the HTTP response is unchanged. This is the accepted-but-unpleasant half
  of the design; it should be seen once rather than assumed.
- **V5 — the message reads well to a human.** A test can only assert
  substrings. Read the rendered line in a terminal and confirm the remedy
  (`git add -f`) is actually actionable for the user who will see it.
- **V6 — `tcw validate` and `tcw capabilities check`** (criterion 11) are run
  as part of Task 3 but must be re-run at the end, after the docs commit.

---

## Notes

- **Do not run `tcw work` transitions or `git stash` in this checkout while
  other agents are active.** The red-first evidence for criterion 10 comes from
  writing tests before implementation (Task 1 step 4), not from stashing
  `tcw/store/fs.py` as the spec suggests.
- **Reuse, don't create.** `tests/test_work_autocommit.py` already has
  `node()` (running the real `init`, so the resolved-ignore rules are live),
  `make_item()`, `committed()`, `porcelain()`, and a section dedicated to a
  gitignored destination folder (`:604-632 (406b043)`). Six new tests append to
  it. No new test module, no new conftest fixture.
- `_warn_off_trunk` (`tcw/store/fs.py:3479-3501 (406b043)`, printing at `:3500`)
  is the precedent for shape only. It has **no test** — grepping `tests/` for
  `trunk-branch is` returns nothing. Copy the shape, not the coverage.
- The `init` guard's `ponytail:` note (`tcw/store/fs.py:697-701 (406b043)`)
  names this exact gap and says "Catching those means checking at write time, in
  `git_stage`". Once Task 1 lands, that sentence describes something that now
  exists. Updating it is a two-word edit inside `tcw/store/fs.py`, so it stays
  within criterion 9's scope — do it in Commit 1 or leave it; it is not an
  acceptance criterion either way.
- `tcw serve`'s help text still calls it "a local **read-only** web viewer"
  (`tcw/cli.py:156 (406b043)`), which has not been true since the editing
  endpoints landed. A reader checking V4 will trip over it. Not this item's
  business; noted so nobody fixes it here and blows criterion 9.
- Version cut is **not** this item's decision — batched with the other four
  `bug`-tagged items into one patch release.
- Throwaway artefacts from the plan-time checks live at `/tmp/tcwprobe`,
  `/tmp/tcwprobe2`, `/tmp/pv`, `/tmp/pv2`, and `/tmp/tcwcopy` (the prototype).
  They can be deleted; nothing depends on them.
