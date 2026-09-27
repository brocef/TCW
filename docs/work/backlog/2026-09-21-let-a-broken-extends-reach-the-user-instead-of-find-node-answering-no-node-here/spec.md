# Spec: let a broken extends reach the user instead of find_node answering no node here

## Capability changes

None. Error reporting for existing commands only.

## Problem

`find_node` (`tcw/store/fs.py:210-244`) opens the component's store, re-raises
`StoreNotProvisioned` and `StoreDeclarationError` (`:228-237`), and turns every
other `ValueError` into `None` (`:238-239`). Its callers print "no tcw
<component> node here — run `tcw init`" (`tcw/taxonomy/cli.py:21-25`,
`tcw/capabilities/cli.py:23-27`, `tcw/work/cli.py:115-122`).

Opening a tree store raises a plain `ValueError` for a federation error:
an unreachable project in `extends` (`fs.py:1382-1386`) and a store extending
itself (`fs.py:1391`). Also plain: `<component>.path must be a non-empty path
string` (`fs.py:3473`) and a malformed config file. All of these currently read
as "no node here".

`resolve_store` (`fs.py:3430-3470`) defines `StoreLocationUnusable` (a
`ValueError` subclass, `tcw/store/base.py:57`) as the one error meaning "there is
no store at this location". It is what the genuine "no store here" case raises:
a node with no `docs/work` and nothing configured (work store, rule 4). A tree
store with nothing configured opens without error and `find_node` answers None
from `store.root.is_dir()` (`fs.py:244`).

## Goals

1. `find_node` answers `None` only for `StoreLocationUnusable` (and, unchanged,
   for a tree store whose resolved root is not a directory).
2. Every other `ValueError` from opening reaches the user with its own message,
   printed by `main` (`tcw/cli.py:535-536`) as `tcw: <message>`, exit 1.

## Non-goals

- A configured `taxonomy.path` / `capabilities.path` that does not exist still
  raises `StoreLocationUnusable` and still gets "run `tcw init`", which cannot fix
  it because `init` does not read configured tree paths. Both advisors judged
  that a separate problem (a missing location with wrong advice, not a hidden
  error); filed as a follow-up item.
- Federation cycles between different projects are recorded and reported by
  `check()`, not raised while opening; unchanged.

## Design

Change `except ValueError: return None` to `except StoreLocationUnusable:
return None`. The explicit re-raise for the two provisioning errors becomes
redundant but stays as documentation of why they must not be flattened.

## Acceptance criteria

1. In a node with `taxonomy.extends: [ghost]`, `tcw taxonomy list` exits 1 and
   stderr contains `ghost` and does **not** contain "no tcw taxonomy node here".
   Same for capabilities.
2. A node whose store extends itself: the command's stderr says "cannot extend
   itself" and not "no tcw … node here".
3. A node with no taxonomy (nothing configured, no folder) still prints "no tcw
   taxonomy node here"; a node with no work store still prints "no tcw work node
   here"; `tcw work procedure prompt <id>` in a node with no work store still
   prints the built-in text.
4. `tests/test_legacy_store_config.py`'s check-command assertion is tightened to
   assert the real message (the gap it documents at lines 311-314 is closed).
5. Full suite passes.

## Risks

- A node with `work.path: ""` running `tcw work procedure prompt` used to fall
  back silently to the built-in text; it now fails with the configuration
  error. The comment at `tcw/work/cli.py:2000-2003` asks for exactly that.
