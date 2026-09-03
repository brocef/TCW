# Spec — Unreachable connected projects degrade instead of failing every command

## Capability changes

- **changed** — `cli/host-multiple-projects-in-one-repo` (`cap-0fe6cc`, Supported).
  Its body states that connections "fail closed when either side is missing or
  inconsistent". After this change, *missing* and *inconsistent* stop being the
  same thing: a locator whose target is not present here degrades, while an
  inconsistent declaration between two present nodes still fails closed. The
  wording is the capability's contract with the user and has to move with the
  behavior.

No new or removed capabilities. Recorded in `capabilities.yaml`.

## Problem

`FsProjectRegistry` treats "this locator names a directory that is not here" as
a configuration error, and the error is fatal to every command.

`_read_config` records it as a problem (`tcw/store/project.py:246`):

    if not path.is_file():
        self._problem(path, "registered target has no tcw-config.yaml")

`require_valid` raises on any problem (`tcw/store/project.py:187-190`), and
`find_node` calls it before opening any store at all (`tcw/store/fs.py:199`), so
the failure precedes every component:

    $ tcw work list            # in apps/server of a cloud proposit-app checkout
    tcw: /home/user/tcw-config.yaml: registered target has no tcw-config.yaml

There are 13 `require_valid()` call sites across `tcw/store/fs.py`,
`tcw/cli.py:213` and `tcw/validate.py:152`, so this is not one command's
behavior — it is the graph's.

**The consequence is not confined to the absent node.** `_extended_component_roots`
resolves `extends` by project id through the same registry
(`tcw/store/fs.py:966-974`), so federation between two nodes that are both
present fails whenever their only declared route runs through a node that is
not. In `proposit-app`, `apps/server` and `packages/shared` each declare only
their parent, so with the whole monorepo checked out:

    taxonomy check: .../apps/server/docs/taxonomy/config.yaml: extends project
      'proposit-shared' is not reachable through connected-projects

`packages/shared/tcw-config.yaml` is present. Seven `tcw://C/…` capability
references fail in the same run for the same reason.

Reciprocity has the same defect in a second form. `_validate_reciprocity`
compares the counterpart's locator against the config path
(`tcw/store/project.py:365,386`) and reports

    child locator for 'proposit-server' does not point back to <path>

when the parent names its children at paths that exist only on the machine that
wrote them. The comparison is between a path that is here and a path that is
not, which cannot decide anything about whether the two nodes agree.

## Goals

- A `connected-projects` locator whose target is absent leaves the graph usable:
  the node is not in it, and commands that do not need it succeed.
- Malformed configuration still fails: unparseable YAML, a missing or invalid
  `id`, a duplicate id, a cycle, an unknown `connected-projects` key, a
  registered key that disagrees with a reachable target's id.
- An unreachable locator cannot disprove reciprocity. Only a counterpart that is
  *present* and points elsewhere is a non-reciprocal declaration.
- `tcw validate` still surfaces the dropped edges, reported as unreachable here
  rather than as errors, and does not fail the run for them alone.
- A command that needs an absent node names it and says it is declared but not
  reachable in this checkout — never "no tcw node here", which sends the user to
  `tcw init` and scaffolds a second store beside the real one. This is the
  distinction `StoreNotProvisioned` already draws for stores
  (`tcw/store/fs.py:201-212`).

## Non-goals

- **Obtaining an absent node.** Declaring where a node comes from, and fetching
  it, is [Connected-project entries declare where they come from](tcw://W/2026-09-03-connected-project-entries-declare-where-they-come-from-so-tcw-provision-can-obtain-a-node),
  which is blocked on this item.
- **Any consumer-side configuration.** The `proposit-app` root node, the
  `work.repository` blocks and the session hook belong to those nodes.
- **`_extended_component_roots` reading a sibling's configured component path.**
  A sibling defect found by the sweep, recorded in Notes, and deliberately not
  fixed here.
- Changing what `tcw validate` exits with in general. Only the classification of
  these particular problems moves.

## Design

**Two kinds of problem, not one.** `FsProjectRegistry` accumulates a single
`_problems` list today. Split the accumulation: *errors* keep today's meaning and
still raise from `require_valid`; *unreachable* edges are recorded separately and
never raise. `check()` keeps returning everything so no caller loses information,
and a second accessor exposes the unreachable set for `tcw validate` to label.

Exactly one condition moves into the new category: `_read_config`'s
"registered target has no `tcw-config.yaml`". A target that exists but does not
parse, or parses to something invalid, stays an error — it is present and wrong,
which is the case the fail-closed rule was written for.

**A dropped edge is dropped, not remembered as half a node.** `_visit` returns
`None` for the unreachable target and the graph simply does not contain that id.
Callers that ask for it — `registry.get(project_id)` — already handle `None`;
what changes is the message they produce, which must name the declared-but-absent
node rather than implying it was never declared.

**Reciprocity is evaluated only between two present configs.** The existing loops
already skip a counterpart missing from the cache (`if child is None: continue`,
`tcw/store/project.py:355`). The remaining case is the mirror: the *current*
node's parent is present, and that parent's child locator resolves to a path that
is not here. When the counterpart path is absent, the ids agreeing is the
strongest evidence available, and it is sufficient — a declaration cannot be
required to name a path on a machine it was not written on.

**Litmus test.** "A node this store cannot reach" is not a filesystem trick: a
tracker-backed adapter answers it for a project it lacks credentials or scope
for, and answers it the same way — the id is known, the object is not available
here. The abstract vocabulary already has the concepts; only `ProjectRegistry`'s
problem reporting needs the second category, and it is expressed in ids, not
paths. The filesystem adapter keeps the part that is genuinely its own: what
"not present" means (no sentinel file at the locator).

**Harness.** Entirely inside the CLI and its store adapter, so Claude and Codex
get identical behavior. No hook, no injected context, no skill.

## Acceptance criteria

1. In a checkout of `proposit-app` containing no orchestration repository,
   `tcw work list` in `apps/server` prints the board rather than
   `registered target has no tcw-config.yaml`.
2. In the same checkout, `tcw work nodes` prints the node's own id and reports
   the parent as declared but not reachable, naming `proposit-app`.
3. In the same checkout with a `packages/shared` sibling edge declared,
   `tcw validate` reports no `extends project 'proposit-shared' is not
   reachable` problem.
4. A node whose parent's config is present but names a *different* reachable
   path for the child still fails with the existing non-reciprocal message.
5. A `tcw-config.yaml` at a reachable locator that does not parse, has no `id`,
   has an invalid `id`, or duplicates another node's `id` still fails
   `require_valid` with today's message.
6. A cycle among reachable nodes still fails.
7. `tcw validate` in a checkout with one absent parent exits 0 for that reason
   alone, and its output names the absent node and the locator that named it.
8. `tcw validate --json` (or `check()`) distinguishes an unreachable edge from an
   error, so a caller can tell them apart without parsing prose.
9. No command reports "no tcw <component> node here" for a node whose config is
   present and whose only defect is an absent connected project.

## Risks

- **A real typo now reads as a machine fact.** A locator with a misspelled
  directory becomes "not reachable here" instead of an error. Mitigated by
  `tcw validate` still reporting it, by name, every time — but it is a genuine
  loss of immediacy, and the reporting has to be prominent enough to survive it.
  This is the trade the request asks for and it should be stated plainly in the
  capability wording rather than buried.
- **Silent partial graphs.** An operation that would have spanned the absent node
  now returns a smaller answer instead of failing. Every caller that enumerates
  the graph — `ancestors`, `descendants`, `children`, `reconcile`, `validate`'s
  duplicate-work-root check (`tcw/validate.py:154`) — needs a decision about
  whether a smaller answer is acceptable or must be reported. The sweep in
  Notes lists them; the plan must name each one rather than assume.
- **Reciprocity weakens by exactly one case.** Two nodes could now disagree about
  each other's location without being caught, on a machine where neither path is
  present. The failure only becomes visible on a machine that has both, where the
  check still runs.

## Notes

The reproductions and the prototype in `intake.md` were run in a cloud session
against real checkouts. The prototype patched `_read_config` and `_problem`; the
shape above is what that prototype implies, not the prototype itself.

**Sibling defect found by the required sweep, out of scope here.**
`_extended_component_roots` composes `Path(project.locator) / "docs" / component`
(`tcw/store/fs.py:977`) rather than resolving the sibling's store through
`resolve_store`. A node that configures `taxonomy.path` or `capabilities.path`
elsewhere — which `tcw init --taxonomy-path` exists to do — cannot be extended
from, and the error says it has no `docs/<component>/`. It is the same class of
defect as this item (a path composed instead of resolved) but a different code
path with a different fix, so it wants its own item.

Sweep coverage: every `require_valid()` call site was read
(`tcw/cli.py:213`, `tcw/validate.py:152`, `tcw/store/fs.py:199,223,233,243,273,356,381,968,1596,2284`).
The graph-enumerating callers are the ones the plan must decide for.
