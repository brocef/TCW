# Spec — Override where a connected project lives on this machine

## Capability changes

One addition to the `cli` namespace, planned only — no ledger record is written
at this stage:

- **`cli/point-tcw-at-a-project-i-already-have`** (new, `Status: Supported` on
  completion). `Feature: provisioned-component-stores`, `Subject: node`,
  `store/home-repository`, `cli`. It sits beside
  `cli/declare-a-connected-projects-home-repository` (`cap-596612`) and is its
  complement: that one says where a project *comes from* when this machine
  lacks it, this one says where it *is* when the config's locator is wrong here.

No existing capability's `Status` changes.
`cli/declare-a-connected-projects-home-repository` keeps its promise verbatim —
"a node that is already here always wins" — and this change makes that sentence
true of one more machine rather than altering it. `cli/validate-a-node` gains a
line of reporting (see Design), which its description already covers in general
terms.

## Problem

A locator in `connected-projects` is a fact about one machine. That premise is
the entire reason `repository` declarations exist, and `_target_path`
(`tcw/store/project.py:402-434`) is built on it: the locator wins when it
resolves, the declaration answers when it does not.

There is no third case, and there needs to be. When a machine holds the project
but at a path the config does not name, TCW has no way to be told so. It sees an
unresolvable locator, falls through to `repository`, and fetches a second copy of
something already on disk.

Observed on the real repositories after v1.3.0 shipped, with the Proposit
workspace laid out as flat siblings rather than nested:

```
…/stores/…-proposit-core-…/tcw-config.yaml: duplicate project id 'proposit-core'
    also used by /home/user/proposit-core/tcw-config.yaml
…/stores/…-proposit-orchestration-…/tcw-config.yaml: child locator for
    'proposit-core' does not point back to /home/user/proposit-core
```

The duplicate is the symptom; the cause is that the second copy was fetched at
all. Two further cases are the same shape and equally inexpressible today:
pointing a checkout at a local clone of a dependency instead of a fetched one
(what `go mod replace` and `cargo patch` exist for), and CI where the runner
checks repositories out to paths nobody wrote in a config.

Fixing this in the config is not available: alternative paths in the shared file
put the machine fact back in the file every checkout reads, which is what this
whole feature removed.

## Goals

1. A machine can state where a project actually is, without editing any file
   that another machine reads.
2. That statement wins over both the declared locator and the `repository`
   declaration, so it can correct the case where the locator is the thing that
   is wrong.
3. An override may name a project this machine does not happen to have, and
   that is not an error — so one set of variables can be configured once for an
   environment and used by sessions that hold different subsets of the graph.
4. A statement that is *present and wrong* — naming a directory that exists but
   is not a node, or is a node with a different id — fails loudly and names what
   it found.
5. `tcw validate` reports which overrides are in effect, so a graph that
   resolves only because of one is never silently mysterious.
6. Nothing changes for a machine that sets no override. The rung is absent, not
   empty.

## Non-goals

- **A persistent per-machine config file** (`~/.config/tcw/projects.yaml` or
  similar). It is the better ergonomics for a permanently mismatched workstation
  — no re-export per shell, greppable when you are confused — and it is a second
  configuration surface with its own precedence question. Env alone is the
  smaller change and tells us whether the file is worth building. If it is, it
  slots in as a rung *below* env, and this spec deliberately leaves that room.
- **Overriding a component store's location** (`work.path`, `taxonomy.path`).
  Adjacent enough to drift in, and a different question: those already have a
  per-node config key, and `resolve_store` (`tcw/store/fs.py:2939-2951`) has its
  own four-rule ladder. If it turns out to be wanted, it is its own item.
- **Making `tcw provision` recognise an on-disk copy it cannot reach through the
  graph.** That is the same symptom by another route and cannot work: a project
  unreachable through `connected-projects` is not in the registry to be
  recognised. The override *is* the mechanism that makes it reachable.
- **Changing how the duplicate-id or reciprocity checks behave.** With the
  override in place the second copy is never fetched, so those stop firing for
  this cause. They remain correct for their own.

## Design

### The rung

`_target_path` gains a rung above its existing two. Its ladder becomes:

0. an override for this project id, if the environment supplies one;
1. the declared locator, if it resolves here;
2. the declared `repository`'s provisioned location;
3. the locator again, as the value the unreachable record names.

Rule 0 must be first, and that is the load-bearing decision. Anything lower
cannot fix the motivating case, because the declared locator is precisely the
thing that is wrong there. It is also the honest ordering: an override is the
most specific statement available — *I am telling you where this is on this
machine* — and the ladder's existing rule is that the more specific answer wins.

The docstring's current promise ("a locator that is here always wins, and a
declaration answers only when it cannot") is extended rather than contradicted:
the override is a locator, supplied by the machine instead of the file.

### Naming

`TCW_PROJECT_<ID>`, with the id uppercased and `-` replaced by `_`:
`proposit-core` → `TCW_PROJECT_PROPOSIT_CORE`.

The mapping is injective, and it is worth writing down because nothing else in
the codebase makes it obvious. `PROJECT_ID_PATTERN`
(`tcw/store/project.py:21`) is `^[a-z0-9]+(?:-[a-z0-9]+)*$`, so an id can
contain no underscore and no uppercase; `-`→`_` therefore cannot collide with a
pre-existing underscore, and case-folding cannot merge two distinct ids.
Verified against the pattern: `a_b`, `A-b`, `a--b`, `-a` and `a-` are all
rejected as ids.

The `TCW_PROJECT_` prefix also cannot collide with `TCW_WORK_OWNER`
(`tcw/work/cli.py:762`), the existing precedent for this shape — an env var
supplying a machine fact the config cannot carry, read as one rung of an ordered
fallback.

### Where the question lives

The abstract question is *"does the caller have an override locator for this
project?"*, and `Project.locator` is already opaque above the adapter. A
tracker-backed registry answers the same question by reading the same variable
as a project key rather than a directory. So the question belongs on
`ProjectRegistry` (`tcw/store/base.py:149`), alongside `declared_parent_id`;
the fact that the value is a filesystem path stays inside `FsProjectRegistry`,
which is the only thing that resolves it.

This is the litmus test applied rather than assumed: an env-var lookup is not a
filesystem trick, and the value it yields is one.

### Absent is not wrong

An override splits into two cases, and the split is not a new judgement — it is
the one `_read_config` already makes for every locator
(`tcw/store/project.py:308-315`):

- **The path does not exist.** Not a defect. It means this machine does not have
  that project, which is the same thing an unresolvable locator means, and the
  ladder carries on to the `repository` declaration. This is what lets one set
  of variables be configured once for an environment (see below) and used by
  sessions holding different subsets of the graph.
- **The path exists and is wrong** — no `tcw-config.yaml`, or a node whose `id`
  is not the project being overridden. A **problem**, reported and fatal to
  `require_valid()`.

The second half is the decision most likely to be got wrong in the other
direction. A mistyped `TCW_PROJECT_PROPOSIT_CORE` pointing at a real directory
that is not that project, silently ignored, produces "my override does nothing"
with nothing to read — the fail-open shape three adversarial review passes
removed from this codebase in the run that shipped v1.3.0.

An id mismatch names both ids, because the likely cause is pointing at the wrong
sibling in a workspace of similar directories — and in this project's own
workspace those two directories are genuinely easy to swap (see the table
below).

### Configuring an environment preemptively

The case this makes possible, and arguably the main one. A Claude Code cloud
environment clones each attached repository as a sibling under the session's
base working directory — observed in this session:

    /home/user/proposit-app  /home/user/proposit-core  /home/user/proposit-orchestration

That layout is knowable ahead of time, so the variables can be set once in the
environment's configuration rather than by any session. A session that attaches
all three resolves the whole graph locally and fetches nothing; one that
attaches only `proposit-app` finds the other two overrides pointing at absent
paths, falls through to their `repository` declarations, and provisions exactly
as it does today. Neither session needs to know which case it is in.

**The variable names follow node ids, not repository names**, and for this
workspace the two are crossed in a way that will cost somebody an hour:

| Directory                        | Node id            | Variable                       |
| -------------------------------- | ------------------ | ------------------------------ |
| `.../proposit-core`              | `proposit-core`    | `TCW_PROJECT_PROPOSIT_CORE`    |
| `.../proposit-orchestration`     | `proposit-app`     | `TCW_PROJECT_PROPOSIT_APP`     |
| `.../proposit-app`               | `proposit-app-repo`| `TCW_PROJECT_PROPOSIT_APP_REPO`|

`proposit-orchestration` is the node named `proposit-app`; the repository named
`proposit-app` is the node `proposit-app-repo`. The id-mismatch refusal above is
what turns getting this backwards into a message rather than a mystery.

### Reporting

`tcw validate` prints active overrides beside the `misdirected()` line it
already prints (`tcw/cli.py:396-399`), non-fatal and uncounted, in the same
"declared there, found here" register:

```
connected project 'proposit-core' is overridden by TCW_PROJECT_PROPOSIT_CORE
    to /home/you/proposit-core
```

Without it, an override produces inverted works-on-my-machine: someone's
environment makes the graph resolve and no other reader can tell why.

## Acceptance criteria

1. With `TCW_PROJECT_<ID>` set to a valid node directory whose `id` matches,
   `FsProjectRegistry.open(...).get("<id>")` returns a `Project` whose locator
   is the override, **even when the config's own locator resolves to a different
   existing node**. (Rule 0 beats rule 1, not just rule 2.)
2. With the same variable set, `tcw provision` does not fetch that project: no
   cache directory is created for it, and the run reports it available.
3. In the flat-sibling reproduction from the intake, setting the override for
   `proposit-core` makes `tcw validate` report zero graph problems, where it
   reports two without it.
4. `TCW_PROJECT_<ID>` naming a path that **does not exist** is not a problem:
   `check()` stays empty, and the ladder falls through to the `repository`
   declaration, so `tcw provision` obtains the project exactly as it does with
   no variable set.
5. `TCW_PROJECT_<ID>` naming a directory that **exists** with no
   `tcw-config.yaml` makes `check()` return a problem naming the variable and
   the path, and `require_valid()` raise. It does not fall through.
6. `TCW_PROJECT_<ID>` naming a node whose `id` is different makes `check()`
   return a problem naming **both** the expected and the found id.
7. One environment-wide set of variables serves both session shapes: with all
   three Proposit directories present, `tcw provision` creates no cache entries;
   with only `proposit-app` present and the same three variables set, it
   provisions the other two and every node reports `validate OK`.
8. With no `TCW_PROJECT_*` variable set, `FsProjectRegistry` produces byte-identical
   `check()`, `unreachable()` and `misdirected()` output to v1.3.0 for the
   Proposit workspace in its nested layout, and creates no cache entries.
9. `tcw validate` prints one line per active override, exits 0 when the graph is
   otherwise clean, and does not count overrides among its problem total.
10. An id whose env-var form is ambiguous cannot exist: a test asserts
   `validate_project_id` rejects every input that would make the
   uppercase-and-underscore mapping non-injective (`a_b`, `A-b`).
11. `tcw provision`, `tcw work list`, `tcw validate` and `tcw taxonomy list` all
   honour the same override — it is applied in graph loading, not in one command.

## Risks

- **Rule 0 is a big hammer.** An override left exported in a shell profile
  silently redirects every project of that id in every workspace on the machine.
  Criterion 7 is the mitigation and is not optional: if `tcw validate` does not
  say an override is in effect, this is a debugging trap rather than a feature.
- **Env vars do not survive a shell.** Less of a concern than it first looked:
  the strongest use is an environment's own configuration, which persists by
  construction. It remains real for a workstation, where the honest answer may
  still be the config file listed under Non-goals.
- **A preemptive set of variables is invisible to the session using it.** Set in
  an environment's configuration, they are not in any file the checkout holds,
  so a graph that resolves for a reason nobody in the repository can see is
  exactly the debugging trap criterion 9 exists to close. That reporting is more
  load-bearing under this use than under the original one.
- **The absent-path fall-through is a real fail-open, chosen deliberately.** A
  variable pointing at a path that is simply mistyped — a transposition, a wrong
  base directory — behaves identically to one naming a project this machine does
  not have: silently nothing. The alternative refuses every preemptively
  configured environment whose session holds a subset, which is worse. Criterion
  9's reporting is what makes the difference visible: an override that took
  effect is listed, so one that is silently doing nothing is conspicuous by its
  absence from that list.
- **A second way to say the same thing.** Two mechanisms now answer "where is
  this project" — the config's locator and the environment — and a reader
  debugging a graph has to know both. Reporting (criterion 7) is what keeps that
  cost bounded.
- **Scope of the sweep.** The repo-wide sweep this stage asks for found one
  sibling of this defect: `resolve_store`'s ladder has the same missing rung for
  component stores. It is deliberately Non-goal'd rather than folded in, because
  a component store already has a per-node config key for its location and the
  cases are not symmetric — but it is the first place to look if this pattern
  proves out.

## Notes

- **Assumption, not established:** that a Claude Code cloud environment always
  clones attached repositories as flat siblings under one base directory. It is
  what this session shows and what `add_repo` describes, but it is not a
  documented guarantee, and the preemptive configuration above depends on it. If
  it ever stops holding, the failure is benign — the paths become absent, the
  overrides fall through, and provisioning resumes — which is a further argument
  for the absent-is-not-wrong rule.
- **Assumption, not established:** that the real Proposit workstation will never
  want this, because its layout matches its configs. Verified only that the
  nested layout validates clean with zero fetches; whether the user's actual
  machine is nested was inferred from `AGENTS.md`, not observed.
- The duplicate-id and non-reciprocity errors quoted in the intake are correct
  behaviour reporting a real inconsistency. This spec removes their *cause* in
  this scenario; it does not touch the checks.
- Harness compatibility is unaffected: an environment variable read by the `tcw`
  CLI behaves identically under Claude and Codex, which is exactly why the
  guarantee belongs in the CLI rather than in a hook.
