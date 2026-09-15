# Resolve a work store inside a project the registry already located

## What is being asked for

A node's **location** and a node's **store** are resolved by two mechanisms that
never consult each other, and only one of them honours the per-machine override.

The project registry has an override rung: `TCW_PROJECT_<ID>` states where a
project sits on this machine, which is the fact no checked-in configuration can
carry. Component-store resolution has no such rung. Its ladder is the configured
`<component>.path`, then a provisioned checkout, then failure — and neither rung
asks the registry anything.

So when the configured relative path does not resolve, because the workspace is
laid out differently from what that path assumes, TCW clones a second copy of a
repository it located by environment variable milliseconds earlier. The two
answers disagree inside a single command's output: `tcw provision` reports one
project as "already available" on one line and clones the same repository on the
line above it.

**The ask:** before falling back to a provisioned checkout, ask the project
registry whether any reachable project comes from the repository the declaration
names, and if one does, resolve the store inside it.

Everything needed is already held. A connected project's `repository` is
described in its own docstring as "exactly the declaration a component store
takes, because 'where does this come from' is the same question either way", and
the resolved project's locator says where that project landed on this machine,
environment override included.

## What is also being asked for, folded in

A second defect in the same ladder, absorbed from backlog item
`2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared`.

When the configured path names a directory that exists but is not a valid store,
and a declaration is also present, only the declaration is reported. There are
two configuration problems and one is told. `tcw validate`, whose whole job is
enumerating a node's configuration problems, reports one of two.

Both requests are about the same ladder. One adds a rung to it; the other is
about what the ladder says when a rung fails. Specifying them apart would mean
writing the same ladder down twice.

## Why it matters

- A workspace can be checked out in any layout without editing a checked-in
  config, creating a symlink, or hardcoding a machine-specific absolute path.
  Escaping that last one is what issue #26 was filed for; this closes the gap
  for a workspace whose *sibling arrangement*, rather than its worktree, differs.
- Cloud sessions, continuous integration, and containers get correct boards from
  environment variables alone, which is the mechanism already designated for
  this kind of per-machine fact.
- It removes a path that is silently wrong rather than loudly broken. The remedy
  the current error message recommends produces a store that reads the declared
  ref rather than the branch the workspace is on, and that *publishes* — so a
  `tcw work start` would commit and push a transition to `main` instead of
  landing it on the working branch.
- Nothing is spent re-cloning a repository the session already has, and there is
  one fewer copy to drift.

## Decisions the requester has already made

Asked and answered during this stage, so `spec` does not have to reopen them:

1. **The new rung applies to all three components**, not to work alone. The
   ladder is shared deliberately — its docstring says "one function for every
   component, because the ladder is the contract and three copies of a contract
   drift" — and a taxonomy or capabilities store declared in a sibling
   repository has the identical problem.
2. **A local checkout wins regardless of the declared ref**, silently, exactly
   as the configured-path rung does today. A checkout the user is standing in is
   the answer, whatever branch it is on.
3. **Both diagnostic shapes from the absorbed item are in scope.** The failed
   rung's reason is carried into the not-provisioned error for the command
   surface, *and* `tcw validate` checks the configured path independently so
   that two problems are listed as two problems.

## Constraints

- **Local before remote**, as everywhere else in TCW. The new rung sits above
  the provisioned checkout, so a repository already on disk is never re-cloned.
  This is the same ladder a connected project already documents: the locator
  answers when it can, the declaration only when it cannot.
- **A store found this way must not publish.** It is on the user's own disk and
  they push it themselves, which is the reasoning already given for excluding a
  store found at a configured local path.
- Matching a declaration to a project needs URL comparison that survives a
  `.git` suffix and the `git@host:owner/repo` versus `https://host/owner/repo`
  spelling.
- **"The configured path does not exist at all" must stay silent.** With a
  declaration present that is the normal case the feature exists for, and
  reporting it would make every provisioned node noisy. This distinction was the
  substance of the absorbed item.

## Out of scope

- Changing how `tcw provision` obtains a repository that genuinely is not here.
  The cache rung stays; it just stops being reached when a copy is already on
  disk.
- Any change to how the project registry itself resolves locations. That
  mechanism works and already honours the override; this item is about a second
  mechanism learning to ask it.

## Notes

- Reference material: asked; none provided beyond the two documents already
  attached to this item.
- **The absorbed item's code quotation is out of date, but its symptom is not.**
  It quotes a bare `except ValueError` around rung 1; the ladder now catches
  `StoreLocationUnusable`. The behaviour it reports still reproduces on `main`
  at v2.0.1 — a configured path holding only `backlog/`, alongside an
  unreachable declaration, is reported by both `tcw work list` and
  `tcw validate` as nothing but "has not been provisioned here". Verified by
  hand during this stage.
- The report was filed by the maintainer against their own project, so the
  requester and the implementer are the same person. The issue text is preserved
  verbatim in `intake.md` regardless.
- One interaction worth flagging to `spec`: a project locator is documented as
  opaque, and nothing above the storage adapter may parse it. The join this item
  asks for is a path join. It is legal because the ladder being changed lives in
  the filesystem adapter and is reading its own locator, but the spec should say
  so rather than leave it looking like a violation.

## References

- GitHub issue [#31](https://github.com/brocef/TCW/issues/31) — the report this
  item came from, quoted in full in `intake.md`, including the workspace layout
  and configuration that reproduce it.
- Discarded item
  `2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared`
  (resolution `superseded`) — the absorbed second defect. Its request document
  is quoted in full in `intake.md`; nothing else tracks it.
- GitHub issue [#26](https://github.com/brocef/TCW/issues/26) and the completed
  item `2026-09-04-override-where-a-connected-project-lives-on-this-machine` —
  the override rung this item wants store resolution to reach. Read it for the
  reasoning about what a per-machine fact is and why no shared file can hold one.
