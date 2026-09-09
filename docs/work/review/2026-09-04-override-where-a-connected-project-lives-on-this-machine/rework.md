# Rework — Override where a connected project lives on this machine

Rejected at `verify` on 2026-09-09. The eleven acceptance criteria are met as
written and the verification evidence in `outcome.md` stands; what sends this
back is the gap `outcome.md` flagged under *Deliberately not done*, which the
user has decided belongs to this item rather than a follow-up.

Two tasks. Neither changes the spec.

## Task R1 — `tcw provision` must refuse a broken override

**The defect.** When `TCW_PROJECT_<ID>` names a directory that exists and is not
the right project, the registry refuses it: the problem is in `check()`,
`require_valid()` raises, `get()` returns None, and the ladder does not fall
through to the `repository` declaration. But `tcw provision` decides what to
fetch from `declared_connected_projects`, a direct config read that never
consults the registry's problems — so it fetches a copy anyway. The refusal is
real everywhere except the one command that acts on the network.

That is the fail-open shape the spec argues against by name. A user who mistypes
a variable is told loudly by `tcw validate` and then watches `tcw provision`
clone a second copy of a project they already have, which is the original bug.

**Two failure shapes, and they are found at different moments.** A directory with
no `tcw-config.yaml` is known when the override is resolved. A directory holding
a node with the *wrong id* is only known after the config is read, by
`_read_config`'s existing mismatch check. Any fix has to cover both, so it cannot
live in `_resolve_override` alone.

**The approach.** After the graph loads, reconcile: an override is *satisfied*
only if the project it names ended up in the graph, under the right id, at the
overridden location. Anything else is a failed override, and the failure is
attached to the `ProjectOverride` record rather than tracked in a second
structure. `run_provision` then refuses on any failed override, before it
contacts anything.

- `ProjectOverride` gains `problem: str | None = None`. `None` means it resolved.
  Storage-neutral, like the rest of the record — a tracker adapter's override
  fails too, and the reason is a string either way.
- `FsProjectRegistry` records every override it consults, including the ones it
  refuses, and reconciles them at the end of `_load_graph`.
- `run_provision` refuses on any override carrying a problem, printing it and
  returning 1 before the component loop. This matches the rule already stated
  there for `node_problems` — *a declaration that is present and wrong refuses,
  rather than reading as "nothing declared" and reporting success* — and an
  override is a declaration, supplied by the environment.

**Deliberately narrow.** Provisioning is **not** being made to refuse on graph
problems generally. `_declared_nodes_in_graph` documents opening the registry
without `require_valid` on purpose, because a graph with an unreachable node is
the graph the command exists to complete. Only failed overrides gate it.

**Proves it:**
- `tcw provision` exits 1, prints the problem, and creates no cache entry, for
  both failure shapes — the directory with no config, and the node with the wrong
  id. Each asserts the cache is empty, since "it refused" and "it refused before
  fetching" are different claims.
- A *satisfied* override still provisions normally, and an *absent* one still
  falls through and fetches. Without these the gate could pass by refusing
  everything.
- `overrides()` reports the failed ones with their problem, and `tcw validate`
  still lists them.

## Task R2 — the wheel test reads developer-local state

**The defect, and it is not the one it looks like.** `test_the_prompts_are_in_the_built_wheel`
fails on this machine at `ea11807` as well as on this branch, so it predates the
work — but it is not a packaging bug either. `tcw/work/prompts/` holds six files
and no `inbox.md`, and git tracks exactly those six. The wheel gains a seventh
because a stale `build/lib/tcw/work/prompts/inbox.md`, dated 2026-09-02, is left
over from an older build, and `pip wheel --no-build-isolation` against the repo
reuses that staging directory.

`build/` is gitignored, so CI never has one and the test passes there. It fails
only for a developer who has built before — which makes it a test that reads
local state and reports it as a repository defect, the same class of problem the
`TCW_PROJECT_*` conftest fixture was added for.

**The approach.** Build from a clean copy of the tracked tree rather than from
the repository directory. `git ls-files` names the 744 tracked files; copy those
into `tmp_path` and build there. Untracked build artifacts cannot leak in, and
uncommitted edits to tracked files are still exercised — which a `git archive` of
`HEAD` would have silently dropped.

**Proves it:** the test passes with the stale `build/lib/tcw/work/prompts/inbox.md`
still in place, and fails if a genuinely declared package-data file is missing
from the wheel.

## Not in scope

- No change to the spec, the eleven criteria, or the capability record.
- No change to the resolution ladder itself — R1 is about a command that ignored
  a refusal, not about how the refusal is decided.
