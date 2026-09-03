# Spec — Connected-project entries declare where they come from

## Capability changes

- **new** — `cli/declare-a-connected-projects-home-repository`. The user-facing
  ability this item adds, and the sibling of the two that already exist for
  stores (`work/declare-the-work-stores-home-repository`,
  `capabilities/declare-the-capabilities-stores-home-repository`). Seeded
  `Missing` at planning; flipped by `complete`.
- **changed** — `cli/provision-declared-stores` (`Supported`). It currently
  describes obtaining *stores*, one per component. It will also obtain nodes, and
  will follow a declaration found in a node it just obtained, which its present
  wording does not cover.
- **changed** — `cli/host-multiple-projects-in-one-repo` (`cap-0fe6cc`,
  `Supported`). A `connected-projects` entry gains a second form. Already listed
  as changed by the blocking item; both edits land on the same body and must be
  reconciled rather than written twice.

## Problem

A `connected-projects` entry can only be a path. `_relation`
(`tcw/store/project.py:294-312`) accepts a string and nothing else:

    if not isinstance(locator, str) or not locator.strip():
        self._problem(path, f"locator for '{valid_id}' must be a nonempty string")

and `_target_path` (`:313`) resolves it against the filesystem. A path is a fact
about one machine, which is precisely the problem `work.repository` was added to
solve for stores — and the solution is already general. `RepositoryDeclaration`
(`tcw/store/base.py:708-725`) is described in its own docstring as "node
configuration and an adapter locator, exactly as a store path is", and
`parse_repository_declaration` (`tcw/store/base.py:1191`) takes a `where` label
specifically "so one implementation serves every component rather than three that
drift". Nothing about either is component-shaped.

What is missing is that a *node* has no way to say it. The gap shows up wherever
a project id is resolved rather than a store path — most sharply in `extends`,
which resolves through `connected-projects` (`tcw/store/fs.py:966-974`) and
therefore cannot be answered by any store declaration. In `proposit-app` every
node's taxonomy extends `proposit-core`, which lives in a repository a code-only
checkout never has.

The machinery to obtain one already exists and is component-generic in
everything but its entry points: `checkout_root` (`tcw/store/fs.py:2694`) and
`_cache_key` (`:2629`) key a working copy on `(url, ref)`, and
`FsStoreProvisioner` (`:2852`) clones into a staging directory and renames it
into place. `run_provision` (`tcw/cli.py:90-153`) iterates components only,
because `declared_repository` (`tcw/store/fs.py:2833`) reads
`<component>.repository` and nothing else.

## Goals

- A `connected-projects` entry accepts a mapping with `path` and/or `repository`
  in addition to today's bare string.
- The declaration is a fallback, never an override: a node present at the
  locator is used and nothing is contacted. This is the rule `resolve_store`
  already states (`tcw/store/fs.py:2752-2756`) and the reason one configuration
  can serve a machine that has the repository and one that does not.
- `tcw provision` obtains declared nodes, and follows declarations found inside a
  node it has just obtained.
- One working copy serves every node and component naming the same `(url, ref)`.
- A bare string keeps working, unchanged, forever.
- Nothing reaches the network except `tcw provision`.

## Non-goals

- **Tolerating an absent node.** That is
  [Unreachable connected projects degrade](tcw://W/2026-09-03-unreachable-connected-projects-degrade-instead-of-failing-every-command),
  which blocks this item. This one supplies a node; it does not make its absence
  survivable, and without the blocking item a declared-but-unprovisioned node
  still fails every command.
- **Lazy fetching.** Decided against below, and stated here so it does not drift
  back in.
- **Publishing to a provisioned node.** A provisioned *store* publishes its
  transitions (`tcw/store/fs.py:4119`); a provisioned node is a checkout that
  exists so its configuration and trees can be read. Any write inside it is that
  component's business and follows that component's existing rules.
- Consumer-side configuration in `proposit-app` and `proposit-orchestration`.

## Design

**Entry shape.** `_relation` accepts either form:

    connected-projects:
      parent:
        proposit-app: ../../..              # unchanged
      children:
        proposit-core:
          path: proposit-core               # optional
          repository:
            url: https://github.com/Proposit-App/proposit-core.git
            ref: main                       # optional
            path: ""                        # optional: the node within the repo
            checkout: ~/src/proposit-core   # optional

`repository` is parsed by `parse_repository_declaration` unchanged, with
`where` = `connected-projects.<parent|children>.<id>.repository`. It already
fails closed on a bad declaration and bounds `path` to the repository root, which
is exactly the containment this needs, since the value is joined onto a directory
TCW created. An entry with neither `path` nor `repository` is an error; a mapping
with an unknown key is an error.

**Resolution ladder for a node**, mirroring `resolve_store`:

1. the locator, when a `tcw-config.yaml` is present there;
2. else the provisioned checkout — `checkout_root(node_root, declaration)` plus
   `repository.path` — when a `tcw-config.yaml` is present there;
3. else unreachable, in the blocking item's sense, with the declaration named.

Rule 1 first is what keeps every existing machine unchanged and is not
negotiable: a checkout that has the node keeps using it.

**Where the ladder lives.** `_target_path` currently returns a path from a
string. It grows to take the parsed entry and apply the ladder, keeping the
worktree re-anchoring rules it already implements — those apply to the locator
half and are unaffected by the declaration.

**Provisioning walks the graph.** `run_provision` gains a node pass beside its
component pass: read the current node's `connected-projects`, obtain any entry
that is declared and not present, and repeat for each node obtained, since a node
just cloned may declare others. Termination is by `(url, ref)` and by resolved
path — the same key the working-copy cache already uses — so a cycle in
declarations cannot loop. `--dry-run` prints the whole plan, including the
transitive part, before contacting anything.

This is what makes declarations follow the graph rather than being centralized:
`proposit-app` declares only the orchestration node, and `proposit-core`'s url
lives on the orchestration node's own child entry, where it belongs.

**Eager, never lazy — and this is the answer to the request's open question.**
The alternative was fetching a node when something needs it. It is refused
because `cli/provision-declared-stores` already promises the opposite, in the
ledger, as a property users rely on: "Provisioning only ever happens because I
asked for it. No other `tcw` command reaches the network on a project's behalf."
A `tcw work list` that clones two repositories because a taxonomy config
mentioned them would break that promise for every existing user in order to save
one command in a session-start script. The cost the requester was worried about
is addressed instead by sharing one working copy per `(url, ref)` and by
`--dry-run`.

**Litmus test.** "Where does this project come from" is not a filesystem
question. A tracker-backed adapter reads the same slot as a workspace key or a
project URL, and `RepositoryDeclaration`'s docstring already says so: nothing
above the adapter is entitled to read its fields. The abstract vocabulary gains
nothing new — a node relation is still a node relation — and only the filesystem
adapter learns that a locator may be accompanied by instructions for obtaining
it. `StoreProvisioner`'s abstract verb is already "make yourself usable", not
"clone" (`tcw/store/base.py:751-762`).

**Harness.** CLI and adapter only; identical under Claude and Codex. A
session-start script calls `tcw provision`, which is a CLI command, not a hook.

## Acceptance criteria

1. A `connected-projects` entry given as a bare string resolves exactly as it
   does today, in every existing test.
2. An entry given as `{path: ..., repository: {...}}` whose `path` is present
   resolves to that path, and `tcw provision --dry-run` reports it as already
   available without naming a remote to contact.
3. The same entry with its `path` absent resolves to the provisioned checkout
   once `tcw provision` has run, and the node appears in `tcw work nodes`.
4. Before `tcw provision` has run, that node is reported as declared but not
   reachable — not as a missing node — and the message names the declared url.
5. `tcw provision` prints each remote before contacting it, and `--dry-run`
   contacts nothing.
6. A node obtained by provisioning that itself declares a connected project
   causes that second node to be obtained in the same run, and `--dry-run` lists
   both.
7. Two entries naming the same `(url, ref)` produce one working copy.
8. Running `tcw provision` twice does nothing the second time.
9. A malformed `repository` block under a `connected-projects` entry names the
   offending config line, in the same words a malformed `work.repository` does,
   and does not fall back to reporting the node as absent.
10. A `checkout` directory already holding a different repository is refused
    before any fetch, as it is for a store today.
11. In a `proposit-app` checkout with no other repository, `tcw provision`
    followed by `tcw validate` in `apps/server` reports no unreachable
    `proposit-core`.

## Risks

- **A cloned repository's configuration can cause another clone.** Transitive
  provisioning means a config in a repository the user chose can name a
  repository they did not. Today every contacted url is in a file the user has in
  front of them. Mitigations: print every remote before contacting it, including
  the transitive ones; make `--dry-run` show the full plan; and keep the
  existing refusal to write into a `checkout` holding something else. The plan
  must decide whether a transitively discovered declaration needs anything
  stronger than reporting — this is the one place where "the config is trusted
  like a Makefile" is weaker than it is elsewhere, because the second config is
  not one the user checked out.
- **Two spec items edit one capability body.** `cli/host-multiple-projects-in-one-repo`
  is changed by the blocking item too. Whichever lands second must read the other's
  edit rather than reapplying its own.
- **Entry shape is a config surface that cannot be taken back.** Once a mapping
  form ships, every future reader must accept both. Keeping the mapping's keys to
  `path` and `repository`, and delegating `repository` wholly to the existing
  parser, is what keeps that surface small.
- **A stale provisioned node.** `--refresh` brings a working copy to the declared
  ref for stores; a node's checkout has the same staleness, and the plan should
  say whether `--refresh` covers nodes too rather than leaving it implicit.

## Notes

The design was validated in session against real checkouts rather than fixtures:
`apps/server`'s parent pointed at a provisioned orchestration clone, and that
clone's `proposit-core` child pointed at a real `proposit-core` clone, over a
prototype of the blocking item. `tcw work nodes` reported the parent, and the
`extends project 'proposit-core' is not reachable` problem was gone. The output
is in `intake.md`.

`PROVISION_COMPONENTS` (`tcw/cli.py:30`) carries a comment recording that the
verb was deliberately narrowed to `work` while only one adapter was honest, and
widened "together with the adapters that make the other two values honest, never
ahead of them". Nodes should be added on the same terms: the pass ships when it
can actually obtain a node, not before.
