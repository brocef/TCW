# Plan — Make every procedural skill in TCW overridable by the project that uses it

A coordination plan. The epic implements nothing; the six children do the work.
Tasks 1–6 open the children, task 7 wires the dependency order, and the
checkpoints say when this session's coordination runs.

## Before task 1

The epic is blocked by
`2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`,
so nothing here starts until that is merged to `main`. Opening the children is
not starting them and may happen now; `tcw work start` on the epic, and
therefore on any child, refuses until the blocker resolves.

On the day the epic starts, re-read the merged tree for the three things the
spec assumes: that `skills/tcw-work/SKILL.md` names no stage document, that the
four `tcw-commands-*` skills invoke `tcw-work-stage`, and that
`tcw work stage validate` and its harness detection exist. If any is absent, the
spec's Rule 2 exclusion and the injection fallback design must be revisited
before task 3.

## File ownership

Each child owns the files below it and no other child edits them, so the six can
land in any order. Shared files are named in task 7.

| Child | Owns |
| --- | --- |
| 1 rules + marker | a new rules document under `skills/`; the `dynamic_skill` key in all 16 `skills/*/SKILL.md` frontmatters; its test |
| 2 mechanism | `tcw/store/base.py`, `tcw/work/resolve.py`, `tcw/work/cli.py`, `tcw/work/procedures/*`, `skills/tcw-configure/references/work.md`, `skills/tcw-work/SKILL.md`, `skills/tcw-work/references/commands.md` |
| 3 exemplar | `skills/tcw-extras-autonomous-work/SKILL.md` |
| 4 procedures | `skills/tcw-work/references/procedures/*.md` |
| 5 triage + postmortem | `skills/tcw-extras-triage-issues/SKILL.md`, `skills/tcw-post-mortem/SKILL.md`, `agents/tcw-post-mortem.md` |
| 6 docsync + create | `skills/documentation-sync/**`, `skills/tcw-work-create/**` |

Child 1 touches every `SKILL.md` frontmatter, which is why it edits frontmatter
only — never a body — and why children 3–6 must not add or change the marker
themselves.

## Tasks

### 1. Open the rules and marker child

```sh
tcw work new "State the two rules for an overridable skill and mark every skill with its verdict" \
  --initiative 2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it \
  --tag skills --tag docs
```

Body: the two rules as `spec.md` states them, the requester's classification, the
list of documents the spec leaves unclassified (`agents/*`,
`skills/tcw-work/references/lifecycle/*`, the six other files under
`skills/tcw-work/references/`, and the reference directories of already-classified
skills), and the marker proposal. Its spec resolves the unclassified list against
the two rules and records a verdict with a reason for each.

Covers acceptance criteria 1, 2 and 3.

### 2. Open the mechanism child

```sh
tcw work new "Compose a procedure's instructions from project bindings the way a stage's are composed" \
  --initiative 2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it \
  --tag cli --tag work --tag skills
```

Body: `PROCEDURE_IDS` beside `STAGE_IDS` (`tcw/store/base.py:932`);
`tcw/work/procedures/<id>.md` beside `tcw/work/prompts/`, loaded by
`load_builtins()` (`tcw/work/resolve.py:48-86`) with the same missing-file and
empty-file refusals; `work.procedures` as a sibling of `work.lifecycle`, added to
the validated key set the way `tcw/store/base.py:2267` does it for lifecycle; a
`procedure()` accessor on `LifecyclePolicy` (`tcw/store/base.py:1560-1590`)
returning `[]` by default; resolution through the existing `_resolve_one`
(`tcw/work/resolve.py:188-209`) and the `or [Binding(kind="builtin")]` floor
(`:445`); and a read-only CLI verb serving it, whose output adapts to the harness
using the detection the routing item lands.

Covers acceptance criteria 4, 5, 6 and 7.

### 3. Open the exemplar child

```sh
tcw work new "Stop tcw-extras-autonomous-work mandating a specific advisor, closeout and version policy" \
  --initiative 2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it \
  --tag skills --tag tech-debt
```

Body: the eight mandates named in `spec.md`'s Problem §2 with their line numbers;
the requirement that the body state what an advisor must be and how many are
wanted; today's text shipped as the `builtin` default so behaviour is unchanged;
`allowed-tools:` and `compatibility:` frontmatter declaring what the default
needs; and the manual fallback block modelled on
`skills/tcw-work-stage/SKILL.md:41-49`.

Covers acceptance criteria 8, 9, 10 and 11 for this skill.

### 4. Open the procedures child

```sh
tcw work new "Compose the five tcw-work procedure documents from project bindings" \
  --initiative 2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it \
  --tag skills --tag work
```

Body: `audit-backlog.md`, `consolidate-plans.md`, `decompose.md`,
`delegation.md` and `search.md`, each with its current contents as the default.
`delegation.md` is the one to write first, because it states the doctrine the
whole initiative cites and converting it is the proof the doctrine survives its
own treatment.

Covers acceptance criteria 8 and 11 for these five.

### 5. Open the triage and post-mortem child

```sh
tcw work new "Compose tcw-extras-triage-issues and tcw-post-mortem from project bindings" \
  --initiative 2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it \
  --tag skills --tag work
```

Body: both skills, plus the forge question the spec raises — `gh` is hard-required
at `skills/tcw-extras-triage-issues/SKILL.md:38-46` ("Do not fall back to
scraping the web UI") and honestly declared at `:8`, while the tracker axis is
abstracted behind `work.tracker`. The child decides whether the forge becomes a
binding or stays declared-and-required, and records why. For `tcw-post-mortem`,
the stage ladder it reasons over is fixed under Rule 1 and only the conduct moves;
`agents/tcw-post-mortem.md` is updated to match whatever the skill becomes.

Covers acceptance criteria 8 and 11 for these two.

### 6. Open the documentation-sync and work-create child

```sh
tcw work new "Compose documentation-sync and tcw-work-create from project bindings" \
  --initiative 2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it \
  --tag skills --tag docs
```

Body: both skills and their `references/`. Two constraints the child must carry:
the board invariants in `tcw-work-create` — one outcome per idea, the overlap
search before creating — stay in the fixed part, because an override that can
disable them turns a rule into a suggestion; and if
`2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
has landed, `documentation-sync`'s version-cut path reuses its config rather than
gaining a second one.

Covers acceptance criteria 8 and 11 for these two.

### 7. Wire the order

```sh
for c in <child-3> <child-4> <child-5> <child-6>; do
  tcw work edit "$c" --blocked-by <child-1> --blocked-by <child-2>
done
tcw work edit <child-1> --blocked-by 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments
tcw work edit <child-2> --blocked-by 2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments
```

Children 3–6 are **not** blocked by each other. They are parallel by
construction, and `epic-deltas.md` calls a false blocker "a lie the tool will
enforce". Child 1 does not block child 2, and vice versa: the mechanism's shape
does not depend on which skills use it.

Substitute the slugs `tcw work new` prints; do not guess them from the titles.

## Coordination checkpoints

- **Before the first child starts:** `tcw work start` on the epic — an initiative
  child cannot start until its epic is active.
- **After children 1 and 2 land:** `tcw work reconcile <epic>`, then confirm the
  four conversion children are reported ready. This is the only real gate in the
  plan; if the mechanism's verb or config key changed shape during child 2, each
  conversion child's spec is written against what actually shipped, not against
  this plan.
- **After each conversion child lands:** `tcw work reconcile <epic>`, and re-run
  the marker test from child 1 — a conversion that edits frontmatter is the one
  way the two can collide.
- **Before closeout:** a final `tcw work reconcile <epic>`, then acceptance
  criteria 12, 13 and 14 checked on the merged tree.

## Documentation Sync

Evaluated for the initiative; each entry is answered by the child that fires it,
in that child's own plan, and re-checked at the closeout checkpoint.

- **`README.md` — [Public-API]** — fires, in child 2. A new CLI verb and a new
  `work.procedures` key are public surface. Nothing in children 1 and 3–6 changes
  the CLI, so they do not fire it.
- **`docs/release-notes/upcoming.md` — [Public-API]** — fires, in child 2 for the
  verb and the key, and in children 3–6 for the user-visible fact that a
  procedure's text can now be replaced. Written once per child, accumulated, not
  cut: no child cuts a version.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change]** — fires in every child.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component]** — fires in child 2:
  `tcw-work` drives the work component and gains a verb, so
  `skills/tcw-work/SKILL.md` and `references/commands.md` are updated there. Note
  the 60-line budget on that skill (`tests/test_skill_lifecycle_parity.py:50`),
  which the routing item leaves at its limit — child 2 extracts rather than grows.
- **`skills/tcw-configure/references/<document>.md` — [Configuration-Key-Change]**
  — fires in child 2. `work.procedures` is a new key in `tcw-config.yaml`, so its
  "how to declare it" text goes in `skills/tcw-configure/references/work.md`, not
  in the component's own skill.
- **`docs/guide/jira.md` — [Tracker-Change]** — does not fire. Nothing here
  touches a `tcw work tracker` command, a lifecycle command's effect on a bound
  ticket, or a `work.tracker` key.

## Verification

What the suite cannot check, and who checks it.

- **That a converted skill still works as a skill.** A test can assert a file
  contains no named binary; it cannot assert an agent reading the composed result
  can run the procedure. Each conversion child exercises its skill end to end in
  a real session before submitting, and records the transcript's outcome. For
  child 3 that means an actual unattended run against a real backlog item.
- **That the default is genuinely unchanged.** Criterion 10 is a behavioural
  claim. The check is to resolve the procedure in a checkout with no
  `work.procedures` configured and diff the output against the pre-conversion
  `SKILL.md` body. A child that cannot produce a clean diff says what changed and
  why, rather than asserting equivalence.
- **That a Codex reader gets the same instructions.** Injection is Claude-only.
  Each conversion child runs its skill under Codex, confirms the fallback block
  names the commands to run by hand, and records what that session saw — the same
  evidence the routing item's criterion 11 demands for its harness notice.
- **That the rules document is actually reachable.** Criterion 1 says an author
  meets it without being told. A test can assert a link exists; whether a reader
  arrives there is judged by child 1 walking the route from a fresh reading of
  `tcw-work/SKILL.md`.
- **The classification itself.** Rule 1 is a judgment, not a computation. The
  verdicts in child 1 are reviewed by the user before the conversions start,
  because every later child inherits them.

## Notes

- The six `tcw work new` bodies are written out in each task above rather than
  left to the dispatching session, so a child opened weeks from now carries the
  same scope this plan agreed.
- `tcw work new --initiative` is the right relation here, not `--parent`: the
  children start and complete independently over time, and `reconcile` follows
  `--initiative` only (`epic-deltas.md`, "Choosing the child relation").
- No `delegate` and no `escalate`: one node, one repository.
- Child 2 is the long pole and the only one touching `tcw/`. While it is active,
  this repository's own guidance forbids driving the lifecycle with the `tcw`
  CLI, so that child maintains `docs/work/` by hand and says so in its outcome.
