# Spec — An unreachable edge is reported for a project the graph resolved anyway

## Capability changes

- **changed** — `cli/host-multiple-projects-in-one-repo`. Its body now promises
  that `tcw validate` "names the connection it could not follow every run so a
  mistyped locator is still findable". That is the right promise and this makes
  it honest: today it also names connections that were followed by another route.

## Problem

`FsProjectRegistry._unreachable` is a list of *edges*. `_read_config` appends one
whenever a locator names a path with no sentinel, and nothing later removes it if
the same project arrives through a different config.

That happens constantly in a reciprocal graph. Every connection is declared twice
— once by each side — and in a multi-repository workspace the two sides are
written against different machines. In the Proposit graph, standing in
`apps/server` with orchestration and core provisioned:

- `proposit-core`'s config declares its parent at `..`, which resolves inside the
  provisioning cache and is not there. `proposit-app` is nevertheless in the
  graph, reached from the current node's own ancestry.
- the orchestration node declares its `proposit-app-repo` child at
  `proposit-app`, which does not exist inside a cache clone. `proposit-app-repo`
  is the repository the command is running inside.

Both are reported, and the second tells the user to `tcw provision` a repository
they are standing in.

## Goals

- `unreachable()` reports only projects that are not in the graph.
- A genuinely absent project is reported exactly as it is today.
- `unreachable_project(id)` answers `None` for an id that resolved, so the
  "declared but not reachable" message sites cannot fire for a project the caller
  can reach.

## Non-goals

- Recording *which* locator failed. It is per-edge information that no message
  currently uses, and keeping it as a separate diagnostic is a different item.
- Anything about reciprocity, which already ignores absent counterparts.

## Design

Filter at the accessor rather than at the point of record: `unreachable()`
returns the recorded edges whose id is not in `_by_id`. Recording stays cheap and
order-independent — an edge can be recorded before the route that resolves the
project is walked, and a filter at read time does not care which order they came
in.

`unreachable_project` reads through the same filter, so every message site
inherits the fix without changing.

**Litmus test.** "Is this project in the graph" is a registry question in ids.
Nothing filesystem-specific.

## Acceptance criteria

1. A graph where one config's locator for a project fails and another resolves it
   reports nothing unreachable for that project.
2. A project no config resolves is still reported, with today's wording.
3. `unreachable_project(id)` is `None` for the first case and non-`None` for the
   second.
4. `tcw validate` in the Proposit cloud-shaped checkout reports neither
   `proposit-app` nor `proposit-app-repo`.
5. The existing unreachable tests pass unchanged.

## Risks

- **A real typo that another route papers over** becomes invisible. That is the
  correct trade: the project is reachable, so nothing the user does is broken by
  it, and reporting it would train them to ignore the message that matters. A
  per-edge diagnostic is the non-goal above.
