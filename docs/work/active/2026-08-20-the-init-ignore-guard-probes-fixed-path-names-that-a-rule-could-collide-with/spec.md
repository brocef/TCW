# Spec — the init ignore guard probes fixed path names that a rule could collide with

## Capability changes

**None planned.** The ledger already describes the guard by its *intent*, never
by its probe: `tcw init` "turns down … one whose items the repository's ignore
rules would hide (so nothing filed there would be tracked)"
(`docs/capabilities/cli/scaffold-the-doc-trees/description.md:22-23`), and
`configure-the-work-store-location` says the same — "a store whose items the
repository's own ignore rules would hide"
(`docs/capabilities/work/configure-the-work-store-location/description.md:18-19`).
This item narrows *when the refusal misfires*; the promise it makes to a user is
unchanged, and both sentences stay true afterwards. The refusal message is not
quoted in any capability entry (checked: no ledger entry contains the string
`work store folder`).

The `implement` stage re-runs the ledger check as usual; if the reworded message
turns out to be quoted anywhere, that is a wording edit, not a new capability.

## Problem

`init` decides whether items written into a status folder would be tracked by
asking `git check-ignore --no-index` about one representative payload path built
from a **single fixed name**, `an-item`:

```python
# tcw/store/fs.py:703-704
probe = (leaf / "an-item.md" if leaf.name == "inbox"
         else leaf / "an-item" / "state.yaml")
```

and refuses the whole store when that one path is ignored
(`tcw/store/fs.py:705-709`). `git_ignored(..., no_index=True)` asks the ignore
*rules* rather than the index (`tcw/store/fs.py:330-343`), so the question is
"would a file written here be recorded", which is the right question — but it is
asked about exactly one literal name.

Consequence: a repository whose ignore rules happen to name that literal path
gets an otherwise perfectly usable store refused. A single line of `.gitignore`
reproduces it (verified below): `an-item*` makes the fixed probe ignored in
every probed leaf — `backlog/an-item/state.yaml` and `inbox/an-item.md` alike —
while every other item name in the store stays visible. The refusal then reads

> `work store folder is inside a gitignored path, so items written there would
> not be tracked: <leaf>` (`tcw/store/fs.py:707-709`)

which blames the folder, when the folder is fine and one unrelated rule is not.

What a replacement is *not* allowed to be is already settled in the source
comment at `tcw/store/fs.py:683-690`: probing the folder itself makes TCW's own
scaffolding refuse itself (`git check-ignore` matches a trailing-slash path
against a `<status>/*` rule, and `resolved_ignore_rules` writes exactly that
shape — `tcw/store/fs.py:570-581`), and probing `.gitkeep` is defeated by the
`!<status>/.gitkeep` negation those rules carry. The probe must stay a
representative *item payload* path.

## Goals

1. A `.gitignore` rule that names one literal item slug no longer refuses an
   otherwise usable store at `init`.
2. Every ignore-rule shape the guard catches today still refuses — the broad
   rules that genuinely hide items (`docs/work/`, `*`, `<status>/`, `docs/**`,
   `<status>/*` + `!<status>/.gitkeep`, `**/state.yaml`).
3. The refusal message describes the *outcome for items* rather than asserting
   the folder is inside an ignored path — one line, and it keeps the substring
   `gitignored` so the existing `pytest.raises(match="gitignored")` assertions
   (`tests/test_non_git_writes.py:610,668,685,703,719`) hold unchanged.
4. The change is small: two probes instead of one, `all(...)` instead of a
   single call. No new module, no probe-strategy abstraction, no config.

## Non-goals

- **Write-time ignore enforcement.** A configure-time guard cannot see a
  `.gitignore` written after `init`, nor one arriving with a later `git pull`.
  That ceiling is already marked in the source (`tcw/store/fs.py:696-700`) and
  tracked as a separate item,
  `2026-08-20-enforce-the-gitignore-trap-at-write-time-not-only-at-init`.
- **Catching a rule that names a real slug** (`docs/work/backlog/2026-*`). Two
  probes do not help here and neither would twenty — see Risks.
- **Changing which folders are probed.** `completed/` and `discarded/` stay
  skipped (`tcw/store/fs.py:702`); TCW ignores their contents on purpose.
- **Making the probe names configurable or exported.** They are two literals in
  one expression.
- Any change to `git_ignored`, `git_stage`, or `resolved_ignore_rules`.

## Design

Probe **two differently-named** representative payload paths per leaf and refuse
only when **both** are ignored:

```python
if component == "work" and ignore_root is not None \
        and leaf.name not in RESOLVED_STATUSES:
    probes = [leaf / f"{name}.md" if leaf.name == "inbox"
              else leaf / name / "state.yaml"
              for name in ("an-item", "some-slug")]
    if all(git_ignored(ignore_root, p, no_index=True) for p in probes):
        raise ValueError(
            f"items written in {leaf} would be gitignored, so work filed "
            f"there would not be tracked"
        )
```

(Shape, not final text — the implementer may inline it differently, but the
names, the shapes, and `all` are the decided content.)

**The two names: `an-item` and `some-slug`.**

- `an-item` is kept, so the existing tests, comment, and the unreleased
  changelog entry keep their vocabulary and the diff stays two lines.
- `some-slug` shares no substring with `an-item`, starts with a different
  letter, and has a different length, so no plausible single glob (`a*`,
  `*item*`, `*-item`, `an-item*`) matches both.
- Both are valid slug shapes (`[a-z0-9-]`, which is what `slugify` produces),
  so each still reads as "an item someone might file here" rather than as an
  exotic sentinel a reader has to decode.
- `some-slug` deliberately avoids the word `work`: a glob containing `work`
  already matches the store directory itself, so a name carrying it would blur
  which rule caused a refusal.

**The two shapes, pinned.** They differ **only** in the slug segment:

| leaf | probe A | probe B |
| --- | --- | --- |
| `inbox` | `inbox/an-item.md` | `inbox/some-slug.md` |
| any other non-resolved status | `<status>/an-item/state.yaml` | `<status>/some-slug/state.yaml` |

The file name is **not** varied for the status folders. `state.yaml` is fixed by
TCW's own layout — every item has one, and it is the item's status record — so a
rule hiding all `state.yaml` files genuinely hides the store's state and must
still refuse. Varying it (say `some-slug/spec.md`) would make `**/state.yaml`
pass under the `all(...)` rule, which is a real weakening in exchange for a
false-positive nobody has reported. For `inbox`, the item *is* a bare `.md`
file, so the slug and the file name are the same string and vary together;
the `.md` extension is likewise fixed by the layout.

**Abstraction litmus test.** No new operation, and nothing moves toward the
model. `git check-ignore` has no abstract analog — a Jira store has no ignore
rules — and this guard already lives entirely inside the filesystem adapter's
`init` as a private precondition (`tcw/store/fs.py:701-709`), reached through
`git_ignored`, a module-level filesystem-adapter helper. The change edits an
expression inside that private detail; the store interface is untouched.

**Harness compatibility.** The behavior is in the `tcw` CLI, which behaves
identically under Claude and Codex. Nothing here is carried by a skill, a hook,
or dynamic context.

## Acceptance criteria

Each of these is a `pytest` assertion in `tests/test_non_git_writes.py` (the
file that already owns this guard's tests) and each was executed as a raw
`git check-ignore --no-index` experiment first; the results are in Notes.

1. **The false refusal is gone.** In a repository whose `.gitignore` is the
   single line `an-item*`, `init(["work"], code, "demo")` succeeds and scaffolds
   the store — `docs/work/backlog/.gitkeep` exists afterwards. Against today's
   tree the same call raises `ValueError` matching `gitignored`; the new test
   must therefore fail before the change and pass after.
2. **The same holds for an external store.** With `.gitignore` = `an-item*`,
   `init(["work"], code, "demo", work_path=code / "external" / "work")`
   succeeds.
3. **Every broad rule still refuses.** `init` raises `ValueError` matching
   `gitignored` for each of these `.gitignore` contents, on the default store:
   `docs/work/`; `*`; `docs/**`; `docs/work/backlog/`;
   `docs/work/backlog/*` + `!docs/work/backlog/.gitkeep`; `**/state.yaml`.
   (Parametrise one test over the six; each was confirmed to leave *both*
   probes ignored.)
4. **The existing suite is unchanged.** All of
   `tests/test_non_git_writes.py:598,651,673,690,708,724,755` pass with no edit
   to their bodies — including
   `test_init_still_accepts_the_resolved_status_rules_it_writes_itself:724` and
   `test_init_re_runs_on_a_healthy_external_store:755`, the two that guard
   against a probe strict enough to reject TCW's own scaffolding.
5. **Nothing is written on refusal.** The refusal tests' existing
   `assert manifest(code) == before` still holds — the guard stays in the
   pre-flight loop above `write_sentinel` (`tcw/store/fs.py:701`, before
   `:710`).
6. **The message.** The refusal text contains the leaf path and the substring
   `gitignored`, and no longer contains `work store folder is inside`.
   `grep -rn "work store folder" tcw/ tests/ docs/` returns only the amended
   changelog line, if any.
7. **`pytest` is green** and `tcw validate` on this repo is clean.

## Risks

- **"Both ignored" can still be a narrow rule — accepted, with eyes open.**
  `**/state.yaml` and `*.yaml` ignore *both* status probes while saying nothing
  about the work store; `*.md` does the same for `inbox`. All three still
  refuse. This is honest rather than accidental: such a rule really does hide
  every item's status record (or every inbox entry), so a store scaffolded under
  it would file work git never records — exactly what the guard exists to stop.
  The residual risk is a project that ignores `*.yaml` for unrelated reasons and
  must now either scope that rule or negate it before `tcw init`. Judged
  acceptable; the refusal names the leaf, and the reworded message points at the
  rules rather than at the folder.
- **A rule naming a *real* slug is still not caught** (`docs/work/backlog/2026-*`
  ignores every real item and neither probe). Unchanged by this item — two
  probes cannot help, since the `all(...)` rule only ever makes the guard *less*
  likely to fire. This is the same ceiling the source comment already records
  (`tcw/store/fs.py:696-700`) and the write-time item exists to raise.
- **Contrived pairs still collide** (`*-*`, `*`). Both are rules that hide
  everything; refusing is correct.
- **Two `git check-ignore` invocations per leaf instead of one** — four extra
  subprocesses on a default `init` (four non-resolved leaves). Immaterial for a
  one-shot scaffolding command.

## Notes

**Sibling sweep (repo-wide, not narrowed).** `grep -rn "check-ignore\|git_ignored("`
over `tcw/` returns four call sites: `tcw/store/fs.py:305` (`git_stage`),
`:341` (the helper itself), `:359` (`git_mv`), and `:705` (this guard). Only
`:705` synthesises a path that does not exist — the other three ask about a real
path a caller handed them, so there is no fixed name to collide with. A second
sweep for synthetic literals (`grep -rn 'probe\|representative\|placeholder'`,
and `grep -rn 'state.yaml"'` over `tcw/`) confirms `tcw/store/fs.py:704` is the
only constructed `state.yaml` path in the codebase; every other occurrence
addresses an item that exists. **No sibling defect found.**

**Experiment log.** Raw `git check-ignore -q --no-index` against a throwaway
repo (`/tmp/tcw-probe-exp*`), one `.gitignore` per row, probes as pinned above.
`IGN` = ignored, `ok` = visible.

| `.gitignore` | `backlog/an-item/state.yaml` | `backlog/some-slug/state.yaml` | `inbox/an-item.md` | `inbox/some-slug.md` | today | two-probe |
| --- | --- | --- | --- | --- | --- | --- |
| `an-item*` | IGN | ok | IGN | ok | **refuse (false)** | **accept** |
| `an-item` | IGN | ok | ok | ok | refuse (false) | accept |
| `docs/work/backlog/an-item/` + `docs/work/inbox/an-item.md` | IGN | ok | IGN | ok | refuse (false) | accept |
| `a*` | IGN | ok | IGN | ok | refuse (false) | accept |
| `*item*` | IGN | ok | IGN | ok | refuse (false) | accept |
| `*slug*` | ok | IGN | ok | IGN | accept | accept |
| `docs/work/backlog/2026-*` | ok | ok | ok | ok | accept (miss) | accept (miss) |
| `docs/work/` | IGN | IGN | IGN | IGN | refuse | **refuse** |
| `*` | IGN | IGN | IGN | IGN | refuse | **refuse** |
| `docs/**` | IGN | IGN | IGN | IGN | refuse | **refuse** |
| `backlog/` | IGN | IGN | ok | ok | refuse | **refuse** |
| `docs/work/backlog/*` + `!…/.gitkeep` | IGN | IGN | IGN | IGN | refuse | **refuse** |
| `**/state.yaml` | IGN | IGN | ok | ok | refuse | **refuse** (narrow-intent, see Risks) |
| `*.yaml` | IGN | IGN | ok | ok | refuse | **refuse** (narrow-intent) |
| `*.md` | ok | ok | IGN | IGN | refuse | **refuse** (narrow-intent) |
| `*-*` | IGN | IGN | IGN | IGN | refuse | **refuse** |

The guard runs per leaf and refuses on the first leaf that fails, so a rule
hiding only `backlog/` still refuses the whole `init` — which is why the
`backlog/` and `**/state.yaml` rows are refusals despite leaving `inbox` alone.
Verified identically with the store at `external/work/…` (external `work.path`
shape), same results.

**Changelog.** `docs/changelogs/upcoming.md:82-91` is an *unreleased* entry that
describes the current single-probe guard ("It now probes a representative item
path"). Since it has not shipped, `implement`'s documentation-sync pass should
amend that sentence in place rather than add a second bullet contradicting it.

**Size check.** The request asked to say so if this turned out not to be small.
It is small: one expression, one `all(...)`, one message string, plus tests. No
new abstraction is warranted and none is specified.
