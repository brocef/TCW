# Spec — Enforce the gitignore trap at write time, not only at init

## Capability changes

Planned ledger deltas only; no records are written at this stage.

| Capability | Delta |
| ---------- | ----- |
| `work/keep-resolved-work-out-of-git` (`cap-7e064f`) | **Text.** Its closing claim — _"Nothing about this is specific to `completed/` or `discarded/`: any transition destination I have ignored behaves the same way"_ — stays true of the *behaviour* and stops being true of the *output*: from here on, a destination outside the two resolved statuses prints an advisory line on stderr, because TCW cannot tell a deliberate rule from an accidental one. Add a paragraph saying so and naming `completed/`/`discarded/` as the silent pair. No status flip; still `Supported`. |
| `work/configure-the-work-store-location` (`cap-46e036`) | **Text.** It currently advertises only the `init`-time refusal (_"including a store whose items the repository's own ignore rules would hide"_). Add one sentence: a rule that arrives after `init` is no longer invisible — the write itself says so. No status flip. |

No new capability, no new taxonomy entry. The Vocabulary this touches
(`store/adapter`, `work-item/transition`) is already registered, and this adds no
term and no Feature.

## Problem

TCW writes an item to disk and tells the user it filed it, while git records
nothing. `tcw work list` shows the item; a fresh clone does not have it.

Two distinct code paths produce that outcome, and only the first is the one the
report names.

**1. `git_stage` drops ignored paths without saying so.**
`tcw/store/fs.py:305` builds its `git add` argument list by filtering:

```python
live = [str(p) for p in paths if not git_ignored(node_root, p)]
```

There is no `else`. Every store write in the adapter funnels here — the base
component store's `_stage` (`tcw/store/fs.py:942`), the work store's
(`tcw/store/fs.py:2178`), `start`'s two direct calls
(`tcw/store/fs.py:2240`, `:2309`), and `ensure_worktree_ignored`
(`tcw/store/fs.py:492`) — so a rule that hides a path silences every one of them.

Reproduced on a node scaffolded by `tcw init`, with a rule added afterwards:

```
$ printf 'docs/work/backlog/*-secret*\n' >> .gitignore && git commit -am 'rule'
$ tcw work new "Secret plan"
2026-08-20-secret-plan
→ created at docs/work/backlog/2026-08-20-secret-plan          # stderr
$ git status --porcelain          # empty
$ git ls-files docs/work/backlog/
docs/work/backlog/.gitkeep
$ tcw work list
2026-08-20-secret-plan | backlog | - | - | Secret plan
```

The item is on disk, the CLI reports success, `tcw work list` shows it, and git
has never heard of it.

**2. `git_mv` untracks an already-tracked item, and commits the deletion.**
`tcw/store/fs.py:359-368`: when the destination is ignored, `git_mv` drops the
source from the index (`git rm --cached --ignore-unmatch`) and moves the folder
with `shutil.move`. That is deliberate and correct for `completed/`/`discarded/`
— it is the mechanic behind `work/keep-resolved-work-out-of-git`. It is
indiscriminate about *which* destination, so an accidental rule on a live status
folder turns a routine transition into a silent removal. Reproduced:

```
$ git ls-files docs/work/ | grep mv-probe
docs/work/backlog/2026-08-20-mv-probe/state.yaml
$ printf 'docs/work/review/*\n' >> .gitignore && git commit -am 'rule'
$ tcw work start 2026-08-20-mv-probe && tcw work submit 2026-08-20-mv-probe
$ git ls-files docs/work/ | grep mv-probe          # nothing
$ git show --stat --oneline HEAD
578b1a2 tcw work: 2026-08-20-mv-probe → review
 docs/work/active/2026-08-20-mv-probe/state.yaml | 6 ------
 1 file changed, 6 deletions(-)
```

An item that git *did* have is deleted from the tracked tree, the deletion is
auto-committed under a message that says "→ review", and nothing is printed.
This is the sharper of the two: path 1 loses a write that never landed; path 2
destroys a record that had.

**Why the existing guard does not catch either.** `init` refuses a store whose
items the ignore rules would hide (`tcw/store/fs.py:705-709`), and its own
`ponytail:` note (`:696-700`) names the gap: it "cannot see a `.gitignore`
written after `init`, a rule naming a specific slug, or one that arrives with a
later `git pull`. Catching those means checking at write time, in `git_stage`."
All three reproductions above are exactly those cases.

**Why the commit does not catch it either.** `git_commit_result`
(`tcw/store/fs.py:410-440`) treats a pathspec with nothing committable as
"nothing to do — skip silently", which is right for a commit helper and means
auto-commit cannot be the place this is reported. The drop has to be reported
where the drop happens.

## Goals

1. When `git_stage` drops a path because an ignore rule hides it, say so on
   stderr and **stage what is left, proceeding as today**. The write is not
   refused, the exit code does not change, and no exception is raised.
2. When `git_mv` untracks a source because the destination is ignored, say so on
   stderr under the same conditions and in the same shape.
3. `completed/` and `discarded/` stay **silent**. Every `tcw work complete` and
   `tcw work discard` on a default-scaffolded node reaches an ignored path
   (proven below); a warning there would fire on the single most common command
   in the store's life and train the user to ignore the channel.
4. One change at the shared chokepoint, not one per caller.

## Non-goals

- **Refusing the write.** The requester chose warn-and-proceed explicitly.
- **Changing which paths TCW gitignores by default** (`resolved_ignore_rules`,
  `tcw/store/fs.py:570-580`) or changing `git_mv`'s untracking mechanic. Only the
  reporting changes; the git commands issued stay byte-identical.
- **The `init` guard's probe shape.** Its fixed probe names
  (`an-item/state.yaml`, `an-item.md`, `tcw/store/fs.py:706-707`) can collide
  with a repository rule — a separate item,
  `2026-08-20-the-init-ignore-guard-probes-fixed-path-names-that-a-rule-could-collide-with`.
- **Removing the `init` guard.** A configure-time refusal and a write-time
  warning answer different questions; the guard refuses a store you are about to
  create, this warns about a write you have already made.
- **Suppression, config, or a `--quiet` flag.** No knob until someone asks.
- **De-duplicating repeated warnings within one command.** See Risks.
- **Machine-readable reporting** (a return value, an exception type, a JSON
  channel, a `tcw serve` HTTP field). Advisory text only.

## Design

### Where the warning goes

`print(..., file=sys.stderr)`, from inside `tcw/store/fs.py`, with a `tcw: `
prefix. This reuses the channel that is already there rather than inventing one:

- The adapter **already** prints an advisory to stderr: `_warn_off_trunk`
  (`tcw/store/fs.py:3383-3384`) prints `tcw work: on branch '…', but
  work.trunk-branch is '…'; committing the transition here.` — an advisory that
  warns and proceeds, from the store layer, on stderr. This is the same shape,
  from the same file. `sys` is already imported (`tcw/store/fs.py:20`).
- `tcw work` already treats stderr as its advisory channel generally: the
  `→ created at …` / `→ next: …` hints go to stderr, not stdout
  (`tcw/work/cli.py:240,245,516,640,664`), which is why the reproduction above
  shows them under `2>`.
- The repository has **no** `warnings` module usage and no warn helper — grep for
  `warnings.warn` across `tcw/` returns nothing. Reaching for `warnings` or
  `logging` here would introduce a second convention for one message.

Prefix `tcw: ` rather than `tcw work: `, because `git_stage` also serves the
taxonomy and capabilities component stores (`tcw/store/fs.py:942`); `tcw: ` is the
CLI's existing generic prefix (`tcw/cli.py:188`).

**Under `tcw serve` this lands in the terminal running the server**, not in the
browser. `tcw serve` is a writing surface despite its help text — `do_POST` /
`do_PATCH` / `do_PUT` / `do_DELETE` (`tcw/serve/__init__.py:462-490`) reach the
same `FsWorkStore` methods, e.g. `POST /api/work` at
`tcw/serve/__init__.py:792` — so the warning fires there and is read by whoever
started the server. That is the honest answer and it is accepted: routing an
advisory into an HTTP response body would mean a new field on every mutating
endpoint and a new client-side surface, for a condition the operator is the only
one who can fix. Explicitly out of scope (see Non-goals).

### Distinguishing deliberate from accidental

**Deliberate = the path lies inside a `completed/` or `discarded/` folder.**
Those two, and only those two, are what TCW ignores on its own behalf:
`RESOLVED_STATUSES = ("completed", "discarded")` (`tcw/store/base.py:453`), and
`resolved_ignore_rules` (`tcw/store/fs.py:570-580`) writes rules for exactly
those. There is no other deliberate case TCW can recognise — a hand-written rule
on `review/` is indistinguishable, from inside the process, from an accident, and
warning on it is what the requester chose over refusing.

The test is a component match on the path:

```python
if not set(p.parts) & set(RESOLVED_STATUSES): ...warn...
```

Two alternatives were rejected. Making the caller declare intent would mean
touching all five `git_stage` call sites, which is the per-caller fix the
chokepoint rule forbids. Parsing `git check-ignore -v` to see whether the
matching pattern is one `resolved_ignore_rules` wrote is a second git invocation
and an output format to parse, and it would still warn on a hand-maintained
equivalent of TCW's own rule.

Match on `p.parts` of the **absolute** path rather than on
`p.relative_to(node_root).parts`. `FsWorkStore.root` is `.resolve()`d
(`tcw/store/fs.py:2164`) while `store_git_root`/`node_root` may not be, so
`relative_to` can raise spuriously where a symlink is in play (`/tmp` →
`/private/tmp` on macOS) — and a spurious raise means a spurious *warning* on
every `complete`, which is the one failure mode goal 3 forbids. Matching the
absolute path can only fail the other way: a checkout under a directory literally
named `completed` or `discarded` suppresses a warning it should have printed,
degrading to today's behaviour. Bias toward silence is the correct trade here.
Mark it: `# ponytail: component match, not store-relative — a repo path
containing 'completed' silences the warning; take the store root as an argument
if that ever bites.`

### Not warning about paths that were never written

`start` calls `git_stage(store_git_root, src, dst)` where `src` is the *vacated*
backlog folder (`tcw/store/fs.py:2240`, `:2309`) — it no longer exists, and the
call is staging a deletion. With a slug-scoped rule that path is dropped, and
warning about it would be false: nothing was lost there. Traced on the
reproduction above, `tcw work start 2026-08-20-secret-plan` drops
`docs/work/backlog/2026-08-20-secret-plan` (gone from disk) and stages
`docs/work/active/2026-08-20-secret-plan` correctly.

So: **skip a dropped path that does not exist.** This is sound, not merely
convenient — `git_stage` calls `git_ignored` without `no_index`, and plain
`check-ignore` reports a path in the index as *not* ignored however the rules read
(`tcw/store/fs.py:331-341` documents this; verified directly: a tracked file
deleted from the worktree still reports NOT-IGNORED under a matching `d/*` rule).
A dropped path is therefore always untracked, so a dropped path that is also
absent is a deletion git never had to record. Use `p.exists() or p.is_symlink()`,
the idiom already used at `tcw/store/fs.py:672-673` for exactly this reason (a
dangling symlink reads absent to `exists()`).

### The two edits

Both in `tcw/store/fs.py`, sharing one module-level helper — one helper, two
existing call sites, no new indirection:

1. **`git_stage` (`:300-306`).** Compute the dropped paths alongside `live`;
   warn about those that survive both filters (not resolved-status, and present
   on disk). `live` and the `git add` it feeds are unchanged.
2. **`git_mv` (`:346-370`).** In the ignored-destination branch (`:359`), warn
   about `dst` under the same two filters, before the `git rm --cached`. `dst` is
   the path that exists at the moment of the check — the folder is moved there
   afterwards — so the existence filter is applied to `src` here, which is what
   is on disk and about to become invisible.

One line per call, listing every warned path, rather than one line per path: a
slug-scoped rule makes `start` drop both of its arguments and two lines say
nothing the one line does not. Paths are printed relative to `node_root` when
possible (falling back to absolute) so the line is readable.

Message shape, one sentence, same for both sites:

```
tcw: a .gitignore rule hides docs/work/backlog/2026-08-20-secret-plan; it is on
disk but git will not record it. Remove the rule, or run `git add -f` on it.
```

### Abstraction litmus test

**Passes.** `git_stage` and `git_mv` are filesystem-adapter-private: they are
defined in `tcw/store/fs.py`, and grepping the repo for `git_stage` finds
references only in `tcw/store/fs.py` and in tests — nothing in `tcw/store/base.py`,
`tcw/work/`, `tcw/serve/`, or the CLI. No store-interface signature changes, no
new abstract operation, no field on `WorkItem`. "Is this path hidden by a
`.gitignore` rule" has no analog in a Jira or wiki adapter, and needs none: such
an adapter has nothing to warn about, so it simply never emits the line. This is
the same disposition `require_repository` already carries and documents
(`tcw/store/fs.py:318-329`): "A filesystem-adapter precondition, not a model
concept."

### Harness compatibility

**Passes.** The behaviour ships in the `tcw` CLI/library and is identical under
Claude and Codex. No hook, no skill, no dynamic context injection, no slash
command carries any part of it.

### Repo-wide sweep

Not narrowed. Three findings, all in `tcw/store/fs.py`:

| Site | Verdict |
| ---- | ------- |
| `git_stage` (`:305`) | **In scope** — the reported defect. |
| `git_mv` (`:359`) | **In scope** — a sibling of the same defect, and worse (it untracks something git already had). Not deliberate-and-silent as a whole: the *mechanic* is deliberate, the *scope* is not, and only the resolved-status destinations are silenced. |
| `init` guard (`:705`) | **Out of scope**, by the request's own Out-of-scope list; it is the third and last caller of `git_ignored` (`grep git_ignored tcw/` → `:305`, `:331`, `:359`, `:705` and nothing else). |

The sweep also confirms the chokepoint claim: every persisting write in the
adapter routes through `_stage`/`git_stage` or `_mv`/`git_mv` — item creation
(`:994`), field writes (`:3289`), artifact writes (`:3755`), body/re-parent
writes (`:3692-3701`), taxonomy `extends` (`:1207`, `:1221`), capabilities
config (`:1831`, `:1845`), tag registration (`:2917`), `.gitignore` staging
(`:492`). The only unstaged writes are `init`'s scaffolding, documented as such
(`tcw/store/fs.py:592`, "Unstaged, like everything else init writes") and
followed by the user's own commit, and the adapter-private `.claiming/` staging
folder (`:3227-3228`). Neither is a silent dropped write.

Outside `tcw/store/fs.py` there is no second implementation to fix: `git_commit_result`'s
silent skips (`:410-440`) are *consequences* of a dropped stage, not independent
instances, and each is a deliberate, documented no-op.

## Acceptance criteria

Each is checkable without asking the author what was meant. `N` below is
whatever the suite reports on `main` before the change.

1. **The reported case warns.** On a node scaffolded by `tcw init … work` and
   committed, appending `docs/work/backlog/*-secret*` to `.gitignore` and running
   `tcw work new "Secret plan"` prints a line on **stderr** containing both the
   substring `.gitignore` and the path `docs/work/backlog/2026-08-20-secret-plan`.
   (Today: nothing. Verified on `main` — the only stderr is the `→ created`/`→ next`
   hints.)
2. **…and still writes.** The same command exits `0`, and
   `docs/work/backlog/2026-08-20-secret-plan/state.yaml` exists on disk, and
   `tcw work list` lists the slug. No exception type changes and no new one is
   introduced.
3. **`complete` is silent.** On a default-scaffolded node,
   `tcw work new X && tcw work start <slug> && tcw work complete <slug>
   --resolution done --confirm` prints **no** line matching `.gitignore` on
   stderr — despite `git_stage` receiving `docs/work/completed/<slug>/state.yaml`,
   which `git check-ignore` reports as ignored. (Verified on `main` that this path
   really is reached and really is ignored, via both the `active → completed` and
   `review → completed` routes.)
4. **`discard` is silent.** Same as (3) with `--resolution wontfix`, landing in
   `docs/work/discarded/`.
5. **`git_mv` warns on a non-resolved ignored destination.** On a node with
   `docs/work/review/*` in `.gitignore`, `tcw work submit <slug>` prints a line on
   stderr containing `.gitignore` and `docs/work/review/<slug>`. (Today: nothing;
   the item is untracked and the deletion auto-committed.)
6. **`git_mv` stays silent on the resolved destinations.** Covered by (3) and (4),
   which both go through `git_mv`'s ignored-destination branch.
7. **No behavioural change.** For every case above, the set of files on disk and
   the output of `git status --porcelain` after the command are identical to what
   `main` produces. The warning adds a line to stderr and changes nothing else.
8. **A vacated source does not warn.** With `docs/work/backlog/*-secret*` in
   `.gitignore`, `tcw work start 2026-08-20-secret-plan` prints **no** line
   matching `.gitignore` — its dropped `backlog/` argument no longer exists on
   disk, and its `active/` destination is not hidden. (`git status --porcelain`
   after it must show the item staged under `docs/work/active/`.)
9. **Chokepoint, not per-caller.** `git diff` touches `tcw/store/fs.py` only, and
   within it only `git_stage`, `git_mv`, and the one shared helper. No `_stage`
   override, no `FsWorkStore` method, and no CLI module is modified.
10. **The suite is green and grew.** `python -m pytest -q` reports `≥ N passed`,
    `0 failed`. Criteria 1, 3, 5, and 8 each have a test that was watched **red**
    against the unfixed tree (`git stash push -q tcw/store/fs.py`) before the fix
    was written, and the red run's failure reason was checked to be the defect
    rather than a fixture bug.
11. **`tcw validate` and `tcw capabilities check` both pass**, and the two
    capability texts in "Capability changes" have been updated.
12. **Documentation.** `docs/changelogs/upcoming.md` and
    `docs/release-notes/upcoming.md` each carry an entry. `README.md` needs none
    (no command, flag, or exit code changes) and `skills/work/SKILL.md` needs none
    (no CLI surface, model, lifecycle, or guardrail changes) — but both must be
    evaluated and the evaluation recorded, per the `documentation-sync` entries.

## Risks

- **A false warning on `complete` would be worse than the bug.** It fires on the
  most-run command in the store's life and burns the channel. Mitigated by
  criteria 3, 4, and 6, and by the existing suite: `tests/test_work_autocommit.py:19-28`
  and its siblings scaffold with the real `init`, so the resolved-ignore rules are
  present throughout, and any test asserting `capsys.readouterr().err == ""`
  around a transition catches a regression. Also the reason the deliberate check
  matches on the absolute path — the only way it can be wrong is by staying quiet.
- **Existing tests that assert exact stderr.** 248 `capsys.readouterr()` sites in
  `tests/`. The ones asserting `err == ""` that were sampled are read-only
  commands (`tests/test_external_work_store.py:66,71`) or unrelated
  (`tests/test_stdin.py`). Expected blast radius: zero, since normal writes are
  not to ignored paths. Criterion 10 is the check.
- **Repeated warnings inside one command.** A write that stages two paths in two
  calls — `set_body` stages `state.yaml` and the body file separately
  (`tcw/store/fs.py:3692-3694`) — prints two lines when both are hidden. Accepted:
  it only happens in an already-broken setup, and a de-duplication cache is state
  this function does not otherwise carry. Worth a `ponytail:` note, not a fix.
- **The warning is easy to miss under `tcw serve`.** It reaches the server's
  terminal, not the browser. Accepted and named in Design; the operator is the
  only one who can act on it.
- **A user who deliberately ignores a live status folder now gets a line on every
  transition.** This is the trade the requester chose over refusing, and
  `work/keep-resolved-work-out-of-git` currently promises such a setup behaves
  identically — hence the capability text delta. If it turns out to bite, the
  answer is a config opt-out, not silence by default.
- **Concurrency.** None introduced: the check reads git state the surrounding
  code already reads, adds no write, and holds no lock.

## Notes

- `_warn_off_trunk` (`tcw/store/fs.py:3362-3384`), the precedent this design
  reuses, has **no test** — grepping `tests/` for `trunk-branch is` returns
  nothing. Worth knowing when copying its shape; do not copy its coverage.
- `tcw serve`'s help text calls it "a local **read-only** web viewer"
  (`tcw/cli.py:156`), which has not been true since the editing endpoints landed
  (`web/editing` is a `Supported` capability, and `do_POST`/`do_PATCH`/`do_PUT`/
  `do_DELETE` all exist at `tcw/serve/__init__.py:462-490`). Not this item's
  business, but it is a stale string a reader will trip over while checking the
  serve half of this design.
- The `active → completed` route is the one that proves the silencing is
  load-bearing rather than theoretical: `transition` clears `owner`/`started`
  whenever the item is leaving `active` (`tcw/store/base.py:1868-1869`), so
  `fields` is non-empty, so `_set_fields_at` runs `_stage` on
  `completed/<slug>/state.yaml` *after* the move (`tcw/store/fs.py:3289`,
  `:3328`). Traced live: `git_stage … completed/…/state.yaml ignored=True`.
- Batched with the other four `bug`-tagged items into a single patch release, per
  the initial request — so the version cut is not this item's decision.
