# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw capabilities rm <path>`** (`tcw/capabilities/cli.py`). Drives the
  existing `CapabilitiesStore.remove`, which no command reached before. Prints
  `Removed capability <path>`; stages the deletion and does not commit, like
  `tcw taxonomy rm`. `rm` joins `SUBCOMMANDS`, so it is not rewritten to `show`.
- **`removed:` in a work item's `capabilities.yaml`.** `declared_capabilities`
  (`tcw/store/base.py`) returns a third list, `removed`, read with the same rules
  as `new:`/`changed:`. `capability_gate` (`tcw/work/recursion.py`) refuses a
  `removed:` path while `get_local` still finds a capability there
  (`declared (removed) but still resolves`), and no longer skips a sidecar holding
  only `removed:`. Only a local hit counts: an inherited capability at the same
  bare path is not something `rm` can delete. The epic rollup prints
  `removed <path>` rows.

## Changed

- **`FsCapabilitiesStore.remove` refuses instead of cascading.** It ran `git rm
  -rf` on the capability's folder, so a capability nested under the path was
  deleted with it, and a `Superseded by`, `Blocked by`, `Roles` or `When`
  reference to the target was left dangling. It now refuses, writing nothing:
  - any spelling other than the listed path (`routes/`, `./routes`, `Routes` on a
    case-insensitive disk), since `get` resolves those but echoes the spelling
    back as `Capability.path`;
  - a `meta.yaml` anywhere inside the folder (found with `rglob`, so dot-directories
    and unreadable nodes count), naming each;
  - a local capability or override folder whose reference field resolves to the
    target, naming each `<folder> (<field>)`. Fields are read exactly as `check`
    reads them (`_ref_problems`, `_check_globals`), and a hit is compared by
    `samefile`, so `a/b/`, `x/../a/b` and `A/B` all count.

  The inherited refusal also names `tcw capabilities reset`. The contract is
  documented on the abstract `CapabilitiesStore.remove`.
- `FsCapabilitiesStore.reset`'s refusal for a standalone local capability names
  `tcw capabilities rm` instead of the non-existent `remove` command; so do
  `skills/tcw-capabilities/SKILL.md`, `docs/guide/taxonomy-and-capabilities.md`
  and the `capabilities/reset-an-override` ledger entry. `docs/guide/work.md`,
  `skills/tcw-work/references/transitions.md` and
  `skills/tcw-work/references/procedures/audit-backlog.md` describe `removed:`.

## Fixed

- **`git_rm` read a path as a glob.** `--` ends options but git still matches a
  path as a pattern, so deleting a store folder named `a*` also deleted `abc`.
  `git_rm` now passes `--literal-pathspecs`. It is shared by
  `FsCapabilitiesStore.remove`/`reset`, `FsTaxonomyStore.remove`, and the work
  store's deletes, so all of them are fixed. The other store git calls that take
  paths (`git add`, `git mv`, `git ls-files`) are unchanged; see
  `docs/work/inbox/store-git-calls-read-a-path-as-a-glob-pattern.md`.
