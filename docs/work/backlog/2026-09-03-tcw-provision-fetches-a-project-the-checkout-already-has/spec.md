# Spec — `tcw provision` fetches a project the checkout already has

## Capability changes

- **changed** — `cli/provision-declared-stores`. Its body says running the
  command again does nothing because a store that already resolves is reported
  as already available. That promise now has to cover projects as well as
  stores, and today it does not.

## Problem

`_provision_nodes` in `tcw/cli.py` obtains every declaration it meets. Its only
guard is the resolved checkout path, which stops it revisiting the *same*
declaration twice — not from acting on a declaration for a project it can
already reach by another route.

Reproduced with the finished Proposit configuration, standing in
`proposit-app/apps/server`:

    → proposit-app-repo: https://github.com/Proposit-App/proposit-app.git at main → …
      proposit-app-repo: would obtain into …-proposit-app-7df9029374a6

`proposit-app-repo` is the current node's own parent, present at `../..`. The
orchestration node names where it comes from — correctly, because a session
starting from *orchestration* would need it — and the walk takes that at face
value.

The declaration is right and the walk is wrong. `resolve_store` and
`_target_path` both put the local answer first; this one code path does not.

## Goals

- A declaration whose project id is already reachable from this checkout is
  skipped and reported as already available.
- Identity is the project id. Two nodes for one id is the state this prevents.
- An absent project is still obtained, transitively, unchanged.

## Non-goals

- Deciding *which* copy wins when a project is both present and declared: the
  present one does, everywhere else in TCW, and this only makes that true here.
- `--refresh`, which is an explicit instruction to contact the remote for a copy
  you already have and must keep working.

## Design

Collect the ids reachable from the starting node — `registry.current`, its
ancestors and its descendants — before the walk, and add each obtained node's
own id as it is obtained. Skip a queued declaration whose id is in that set,
printing the same "already available" line a resolved store prints.

Seeded from the *starting* registry rather than recomputed per hop: the question
is "does this checkout have that project", and the checkout does not change while
the command runs.

`--refresh` bypasses the skip, since it is the one case where contacting the
remote for a project you have is what was asked for.

**Litmus test.** "Is this project already available to me" is a registry
question, answered in ids. No path comparison and nothing filesystem-specific.

## Acceptance criteria

1. Standing in a node whose ancestor declares a repository for a project already
   reachable here, `tcw provision` does not clone it and reports it as already
   available.
2. `tcw provision --dry-run` in that graph lists it as already available too,
   rather than planning an obtain.
3. A genuinely absent declared project is still obtained, in the same run.
4. `tcw provision --refresh` still contacts the remote for a present project.
5. One cache directory exists for the repository afterwards, not two.

## Risks

- **A project reachable only through an unreachable hop.** If an id is in the
  registry but its node is not actually openable, skipping the fetch would leave
  it unusable. The reachable set comes from the registry, which by construction
  contains only nodes it could open — an unreachable one is recorded separately
  and is not in `ancestors()`/`descendants()`.
- **Ids that clash across repositories** would make the skip wrong. The registry
  already rejects duplicate ids, so this inherits that guarantee rather than
  adding an assumption.
