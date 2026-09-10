# Spec: resolve a work store inside a project the registry already located

## Capability changes

No new capability. Three existing ones are **amended**, and one of the three is
a correction rather than an extension.

| Capability | Change | Why |
| --- | --- | --- |
| `cli/point-tcw-at-a-project-i-already-have` (`cap-75c7e9`) | Amend | It says "every command that resolves the graph honours the same variable, because it is read when the graph is loaded". True, and store resolution is not graph resolution — so the variable does not reach it. After this item, a store declared in a repository the graph has already located is found there. |
| `cli/validate-a-node` (`cap-2bd014`) | **Correct** | It already claims validation "tells a store's three failure modes apart in different words". `tcw validate` does not do this when a broken `<component>.path` and an unprovisioned declaration are both present: it reports the declaration only. The claim is standing and reality does not meet it. |
| `cli/provision-declared-stores` (`cap-28abaf`) | Amend | It says a store that already resolves "is reported as already available and no network call is made". That is true of whatever the resolution ladder can resolve, so the ladder gaining a rung widens it for free. The wording gains nothing new to promise; it is listed because the set of stores it covers changes. |

No status flips. All three stay `Supported`; `cli/validate-a-node` is
`Supported` today on a claim it does not meet, which is the defect.

Untouched deliberately: `work/publish-store-writes-to-the-remote` (`cap-4d7a13`)
already states the rule this item must not break — "only a store TCW fetched for
me publishes". A store found through the new rung was not fetched, so the
existing wording covers it and needs no change. That is a constraint on the
design, recorded in Goals, not a ledger delta.

Taxonomy: no new Vocabulary or Feature. The work sits under the existing Feature
`provisioned-component-stores`, whose vocabulary is already `store`, `node`,
`store/home-repository`.

## Problem

**Two mechanisms answer "where is this on my machine", and only one of them can
be corrected per machine.**

The project registry resolves a connected project through a four-rung ladder in
`tcw/store/project.py:449` (`_target_path`): the `TCW_PROJECT_<ID>` override
first (`_override_path`, `tcw/store/project.py:493`), then the declared locator,
then a provisioned checkout, then the locator again as a record of what the user
wrote. Its docstring names the rule: *a locator that is here always wins, and a
declaration answers only when it cannot*.

Component-store resolution runs a separate ladder in
`tcw/store/fs.py:2939` (`resolve_store`), and it never consults the registry:

| Rung | Line | What it tries |
| --- | --- | --- |
| 1 | `tcw/store/fs.py:3016` | the configured `<component>.path`, re-anchored to the node root |
| 2 | `tcw/store/fs.py:3028` | `provisioned_store_root(...)` — a declared `checkout:`, else an XDG cache directory |
| 3 | `tcw/store/fs.py:3038` | `StoreNotProvisioned` |

Rung 1 is a path written in a file every machine shares. Rung 2 is a fresh
clone. There is no rung that says *this repository is already on this disk, and
the registry knows where*. So a workspace cloned flat rather than nested — which
is what a cloud session produces — falls off rung 1 and clones a second copy of
a repository the same command located by environment variable a few
milliseconds earlier. Issue #31 shows both answers inside one `tcw provision`
output: one project reported "already available", and on the line above it, the
same repository being cloned.

The second copy is not merely wasteful. It is a *detached* copy, and three
consequences follow, the third being the serious one:

- reads come from the declared `ref` rather than the branch the workspace is on;
- rung 1 still fails afterwards, so the cache copy wins every later command;
- rung 2 is the only rung that passes `declaration=` into `_open_at`
  (`tcw/store/fs.py:3028`), and `publishes` is `self.declaration is not None and
  self.publish_transitions()` (`tcw/store/fs.py:4877`). A store reached that way
  publishes. So `tcw work start` would commit and push a transition to the
  declared ref instead of landing it on the working branch.

**The precedent already exists one hop away.** Node provisioning solved exactly
this in `tcw/cli.py:229` (`_provision_nodes`), whose comment reads: *"A project
that is already here always wins" is the rule the whole feature rests on, and
the walk is the one place it was not applied … Taking that at face value
re-cloned repositories the user already had.* Its `resolved_outside` helper
(`tcw/cli.py:273`) asks the registry before planning a clone. The component-store
loop in the same file (`tcw/cli.py:158-160`) constructs an `FsStoreProvisioner`
with no such question.

### The second, absorbed problem

When rung 1 fails, the reason is discarded. `tcw/store/fs.py:3021` catches
`StoreLocationUnusable` and falls through with a bare `pass`, so rung 3's
message at `tcw/store/fs.py:3038` is the only thing the user ever sees.

The fall-through itself is correct — a declaration exists precisely so an
unusable local store is not the end of the story. What is lost is *why*.

For `tcw work list` the message is incomplete but still actionable. For
`tcw validate`, whose entire job is enumerating a node's configuration problems,
it is wrong: there are two problems and one is reported. `_run_check`
(`tcw/validate.py:129`) turns any `ValueError` from `open` into exactly one
string, so the count is one as well.

Reproduced on `main` at v2.0.1 during this spec. A node whose `work.path` names a
directory containing only `backlog/`, alongside an unreachable declaration:

```
$ tcw work list
tcw work: …/tcw-config.yaml: the work store is declared in
https://example.invalid/nowhere.git but has not been provisioned here; run
`tcw provision` to obtain it

$ tcw validate
work check: …/tcw-config.yaml: the work store is declared in
https://example.invalid/nowhere.git but has not been provisioned here; run
`tcw provision` to obtain it
1 problem(s).
```

`work.path` is broken and nothing says so.

## Goals

1. A component store declared in a repository that a reachable project already
   occupies resolves **inside that project**, not in a fresh clone.
2. That rung sits **above** the provisioned checkout and **below** the
   configured path, so nothing changes on a machine where the configured path
   already works.
3. A store found that way **does not publish**. It is on the user's own disk.
4. It applies to **all three components**, because the ladder is one function
   for one contract.
5. `tcw provision` does not clone a repository the registry already locates, and
   says so, exactly as it already does for connected projects.
6. When the configured path is present and unusable, **both** problems are
   reported: the not-provisioned message carries the reason the configured path
   failed, and `tcw validate` counts them as two problems.
7. A configured path that is simply **absent** stays silent when a declaration
   is present. That is the normal case the declaration exists for.

## Non-goals

- **Changing the project registry.** It already resolves correctly and already
  honours the override. This item is about a second mechanism learning to ask
  it.
- **Removing the cache rung.** A repository genuinely not on this disk still
  gets cloned. The rung just stops being reached when a copy is present.
- **Contacting the network to decide.** The new rung reads the registry and the
  filesystem. No `git ls-remote`, no fetch.
- **Reading a checkout's actual git remote** to decide whether it is the declared
  repository. The declaration-to-declaration comparison is what the registry
  itself already holds; inspecting `.git/config` is a different mechanism with
  different failure modes and is not in scope.
- **Honouring the declared `ref`.** Decided at `request`: a local checkout wins
  whatever branch it is on, silently, exactly as rung 1 does today.
- **Any change to `tcw work`, `tcw taxonomy` or `tcw capabilities` verbs.** The
  ladder is below all of them.

## Design

### 1. A new rung between the configured path and the cache

`resolve_store` (`tcw/store/fs.py:2939`) gains one rung, tried after rung 1
raises `StoreLocationUnusable` and before rung 2:

> **Rung 1.5.** Open the project registry for this node. If any project in the
> graph is a checkout of the repository the declaration names, resolve the store
> at that project's location joined with the declaration's `path`. Use it if it
> opens.

The join is exactly the one the report proposes:

```
<locator of the project whose repository.url matches <component>.repository.url>
  / <component>.repository.path
```

Three properties the implementation must hold:

- **It is called with `declaration=None`.** That single argument is the whole of
  requirement 3: `publishes` reads nothing else (`tcw/store/fs.py:4877`). Rung 1
  already omits it for the same reason, documented at `tcw/store/fs.py:4866`.
- **It opens the registry without `require_valid()`.** A graph problem must not
  become a store error on a rung that is only a fallback. `run_provision`
  already takes this shape at `tcw/cli.py:120-124`, and `_provision_nodes` at
  `tcw/cli.py:267-270`.
- **`StoreLocationUnusable` from this rung falls through to rung 2**, matching
  rungs 1 and 2. Anything else surfaces, matching the rule already stated in the
  `resolve_store` docstring at `tcw/store/fs.py:2955`.

### 2. Where the matching lives

The declaration's fields are documented as adapter-private —
`RepositoryDeclaration` (`tcw/store/base.py:870`) says "nothing above the adapter
is entitled to read these fields" — and `Project.locator` is opaque above the
adapter for the same reason.

**Both readers here are the filesystem adapter reading its own values.**
`resolve_store` lives in `tcw/store/fs.py`; the registry it asks is
`FsProjectRegistry`, already imported at `tcw/store/fs.py:59`. So the lookup
belongs on `FsProjectRegistry` as an adapter-private method, and **nothing is
added to the abstract `ProjectRegistry` interface**.

This is the prime directive's answer, not an evasion of it. *Could a
non-filesystem store implement "which reachable project comes from this
source"?* Yes — a tracker-backed registry would compare its own locators. The
operation is portable; only the URL comparison and the path join are filesystem
particulars, and they stay in the filesystem adapter where the equivalent
particulars for connected projects already live.

A reachable project's own declaration is reachable today only through the
`ConnectedProject` entries on the edges pointing at it — `_Config.parent` and
`_Config.children` (`tcw/store/project.py:124-130`), each holding a
`ConnectedProject` (`tcw/store/base.py:891`) with its `repository`. The new
method walks those, which is why it is a registry method rather than something
`resolve_store` assembles from the public API.

### 3. URL comparison is its own function, and `_cache_key` is not touched

`_cache_key` (`tcw/store/checkouts.py:32`) contains text handling that looks like
the normalization this item needs: it strips a trailing slash, strips a `.git`
suffix, and drops a `git@` user part while splitting on `/` and `:`.

**It is not reused, and `_cache_key` is not modified.** An earlier draft of this
spec proposed extracting it and calling it from both places, on the reasoning
that one answer to "same repository?" beats two. That reasoning does not survive
reading what `_cache_key` does with the result. Its normalized text feeds only
the readable half of the directory name. The half that decides identity is a
digest of the **raw** url (`tcw/store/checkouts.py:52-53`), so today
`host/owner/repo` and `host/owner/repo.git` get two different cache directories.

The two callers therefore hold opposite policies. Cache naming keeps two
spellings apart; this item's lookup must treat them as one. A helper shared
between them would be a helper whose meaning depends on who calls it, and the
place that would surface is an implementer routing the digest through it and
silently renaming every provisioned directory on every machine.

So: a new `normalized_url(url: str) -> str` in `tcw/store/checkouts.py`, whose
docstring states the identity contract, used by the new rung alone.

**What is given up.** Two normalizations can drift. That drift is not itself a
defect, because differing cache directory names for one repository are already
the shipped behaviour. It becomes one only if some later code assumes a single
cache directory per identity and deletes what it takes for a duplicate. Nothing
does that today, and the cost of the alternative is a change that can corrupt
existing installs in a way no test on the new code would catch.

### 4. `tcw provision` needs no change

Checked rather than assumed, and the first draft of this spec had it wrong.

`run_provision`'s component loop already asks whether the component's store
resolves, at `tcw/cli.py:161-172`: when the provisioned copy is absent it calls
`STORE_CLASSES[component].open(node_root)` and, on success, prints
`"  <component>: already available at <root>"` and skips to the next component
without contacting anything.

That call goes through `resolve_store`. So the new rung propagates: a store the
rung resolves makes `open` succeed, and the loop reports it as already available
for the same reason it already does for a usable `<component>.path`. The
existing test `test_provision_reports_a_local_store_without_contacting_the_remote`
(`tests/test_store_provisioning.py:393`) pins that behaviour for the rung-1 case.

**No production change is planned here.** Requirement 5 is met by §1 alone, and
criterion 7 exists to prove that rather than to drive an edit.

One pre-existing limit, out of scope: `declared_available =
provisioner.is_available()` runs first (`tcw/cli.py:161`), so a machine that
already has a stale cache clone from before this change still takes the
provisioned branch. That is equally true of a usable `<component>.path` today,
so it is not a defect this item introduces or is asked to fix.

### 5. Carrying the failed rung's reason

Rung 1's `StoreLocationUnusable` is captured instead of discarded, and rung 3's
`StoreNotProvisioned` (`tcw/store/fs.py:3038`) appends a clause naming it.

**Only when the configured path is present.** `FsWorkStore._open_at`
(`tcw/store/fs.py:3365`) raises the same "work.path is not a directory" for a
path that does not exist and for one that exists as a file, so presence has to
be tested rather than inferred from the message. An absent path with a
declaration present is the normal case and stays silent, per requirement 7.

The distinction is drawn once, in `resolve_store`, and the tree stores inherit
it — they share the ladder.

### 6. `tcw validate` counts two problems as two

`_run_check` (`tcw/validate.py:129`) returns a single string for any `ValueError`
raised by `open`. A compound message would still count as one problem, and the
requirement is that two problems are two.

So the configured path is checked **independently of resolution**: when a
`<component>.path` is configured, names something that exists, and does not hold
the component's layout, that is its own entry in the returned list, whether or
not a declaration also exists and whether or not the store eventually opened.

Independent of resolution is the load-bearing phrase. Checking it only on the
failure path would miss the case where the declaration successfully answers and
the broken configured path is never reported at all.

### 7. Sweep for sibling defects

Repo-wide, for the pattern *resolves a location from a declaration without asking
the registry whether it is already here*. Every call site of
`provisioned_root`/`checkout_root` (`tcw/store/checkouts.py:56,79`) was read.

| Site | Verdict |
| --- | --- |
| `resolve_store` rung 2, `tcw/store/fs.py:3028` | **The reported defect.** Fixed by §1. |
| `run_provision` component loop, `tcw/cli.py:158-172` | **Not a defect.** It already asks the resolution ladder before provisioning (`tcw/cli.py:163-172`) and inherits the new rung. See §4. |
| `FsStoreProvisioner.describe`, `tcw/store/fs.py:3121` | Consequence of the above, not separate. Correct once the caller stops reaching it. |
| `FsStoreProvisioner.is_available` / `ensure_available`, `tcw/store/fs.py:3123,3141` | **Not a defect.** These answer "is the provisioned copy there", which is their contract. The question about the registry belongs to the caller, which is where `_provision_nodes` puts it. |
| `_target_path`, `tcw/store/project.py:477` | **Not a defect.** This is the ladder that already does it right. |

The sweep found **no** sibling defect. Every other site that turns a declaration into a path either already consults the ladder or is contractually about the provisioned copy alone. The whole production change is therefore in `resolve_store` and the two diagnostic paths that read its outcome.

## Acceptance criteria

Each is checkable by someone else without asking what was meant.

1. **The reported case resolves locally.** Given a node whose `work.path` does
   not resolve, whose `work.repository.url` names a repository, and where a
   reachable project in the graph is a checkout of that repository, `tcw work
   list` reads the store inside that project. Checked by building the flat
   workspace from issue #31 with the three `TCW_PROJECT_*` variables set, and
   asserting the store path is under the project location, not under the cache.
2. **The configured path still wins.** In a workspace where `work.path` resolves
   to a valid store and a `repository` is also declared, the resolved store is
   the configured one and no registry lookup changes it. An existing test
   asserting rung-1 precedence must still pass unmodified.
3. **A store found through the new rung does not publish.** Its `publishes`
   property is `False`, and a `tcw work start` against it commits without
   pushing. Distinguished from rung 2, whose `publishes` stays `True`.
4. **The cache is not reached when a copy is present.** In the case from
   criterion 1, no directory is created under the cache root, verified with
   `XDG_CACHE_HOME` pointed at an empty temporary directory that is asserted
   empty afterwards.
5. **All three components.** Criterion 1 holds with `taxonomy.repository` and
   with `capabilities.repository` in place of `work.repository`.
6. **A ref mismatch does not stop it.** Criterion 1 holds when the located
   project's checkout is on a branch other than the declaration's `ref`, with no
   warning and no failure.
7. **`tcw provision` reports already-available.** In the case from criterion 1,
   `tcw provision` prints `already available at` for the component, makes no
   `git clone` or `git fetch` call, and exits 0. Checked with the existing
   `_count_git` counter in `tests/test_store_provisioning.py`. This criterion
   proves §1 propagates; it drives no production edit of its own.
8. **Two problems are two problems.** For a node with `work.path` naming a
   directory that exists and lacks the layout, plus an unprovisioned
   declaration, `tcw validate` prints a line naming the unusable `work.path`,
   prints the not-provisioned line, and reports `2 problem(s).` Today it prints
   one line and reports `1 problem(s).`
9. **The error message carries the reason.** In the same case, `tcw work list`
   names both the declaration and the unusable configured path in one message.
10. **An absent path stays silent.** For a node with `work.path` naming a
    directory that does not exist, plus a declaration, `tcw validate` reports
    only the not-provisioned problem and counts one. No line mentions the
    configured path.
11. **Cache keys are unchanged.** `tcw/store/checkouts.py` shows no modification
    to `_cache_key` in the diff, and a test asserting literal expected key
    strings for a fixed set of declarations passes. The test is kept even though
    the function is untouched, because it is the only thing that would catch a
    later change routing the digest through `normalized_url`.
12. **Nothing regresses.** The full `pytest` suite passes.

## Risks

- **Cost on the common path.** Opening the registry walks the graph and probes
  the disk. It is only reached when rung 1 has already failed *and* a
  declaration exists, which is a rare path, and a node with no declaration takes
  rung 4 and never gets near it. Criterion 2 pins that the common path is
  untouched. Should this prove wrong, the registry is opened once per
  `resolve_store` call and can be memoised.
- **Import cycle.** None. `tcw/store/project.py` imports neither `fs` nor any
  store, and `fs.py` already imports `FsProjectRegistry` at line 59. Verified by
  reading the imports of both modules.
- **A false URL match.** Two declarations normalizing to one URL would resolve a
  store inside the wrong project. Bounded by what the rung does on a match: it
  opens a store at that location and falls through when none is there, so a
  wrong match usually resolves to nothing rather than to the wrong store. The
  case that would bite is two genuinely different repositories whose URLs
  normalize alike, which needs a normalization more aggressive than stripping a
  suffix and a user part.
- **A registry that raises.** A malformed graph must not turn a working
  fallback into an error. Handled by not calling `require_valid()` and by
  falling through on failure, which is the shape `run_provision` already uses at
  `tcw/cli.py:120-124`.
- **Renaming existing cache directories.** Orphaning every provisioned store on
  every user's machine is the worst thing this change could do, and the only
  route to it was extracting from `_cache_key`. Design §3 closes that route by
  not touching the function. Criterion 11 stays as a guard against a later
  change reopening it.
- **Criterion 8 changes `tcw validate`'s problem count**, which is a number
  other tooling may gate on. It is the point of the change, and the count moves
  only for a node that genuinely has two problems.

## Notes

- Harness compatibility: this is entirely CLI behaviour in `tcw`, which behaves
  identically under Claude and Codex. No skill, command, or hook carries any
  part of the requirement. Nothing here is Claude-only.
- Every `file:line` citation above was resolved against the working tree at
  commit `db80623`. Section 4 and the `run_provision` row of the sweep were
  corrected at the `plan` stage: the first draft called the component loop a
  sibling defect, and reading `tcw/cli.py:161-172` showed it already consults
  the ladder. Design §3 was corrected after planning too: the first draft reused
  `_cache_key`'s normalization, and the two callers turn out to hold opposite
  policies about whether two spellings are one repository. The absorbed item's own quotation of `except ValueError` is
  stale — the ladder now catches `StoreLocationUnusable`
  (`tcw/store/base.py:54`) — and the Problem section quotes the current code
  rather than the item's.
- Criteria 1 through 11 are new behaviour and were not run against the tree;
  criterion 8's *current* output was run and is quoted in Problem. Criterion 12
  is the existing suite.
- The `ref` question was decided at `request` rather than here, along with the
  all-three-components scope and the both-surfaces diagnostic scope. This spec
  does not reopen them.
