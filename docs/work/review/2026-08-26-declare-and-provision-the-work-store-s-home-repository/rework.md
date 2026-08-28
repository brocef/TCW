# Rework — external review of PR #23

Two findings from a Codex review of
[PR #23](https://github.com/brocef/TCW/pull/23). Both were verified against the
code, reproduced as failing tests, and fixed. Both were real.

## Finding 1 — a repository with no store at the declared path was left behind

`_obtain` renamed the staging clone into the target and *then* `ensure_available`
checked the store layout. A repository that cloned fine but carried no store at
`repository.path` therefore raised **after** publishing the checkout, leaving a
directory at the target.

Worse than the stated contract being wrong: a re-run then found
`checkout.exists()` and took the **refresh** branch, on a checkout that was never
usable.

`test_a_repository_without_a_store_at_the_declared_path_is_refused` asserted the
error but never asserted the absence — which is exactly the assertion that would
have caught this. Fixed by moving the layout check inside `_obtain`, before the
rename, so everything that can refuse runs before anything is published. The
post-refresh check stays, because a pre-existing checkout is the user's and a bad
layout there is reported without deleting anything.

## Finding 2 — refresh could contact a remote other than the one printed

`checkout.exists()` alone routed into `_refresh`, which fetches *that checkout's*
`origin`. A declared `checkout` is an arbitrary user-chosen directory, so it can
hold an unrelated repository — and then `tcw provision` printed the declared URL
and contacted a different one. That is precisely the guarantee the explicit-verb
design exists to provide, so this was the more serious of the two.

The reproduction confirmed the ordering: the unrelated remote was fetched, and
the command failed only later, on the layout check.

Fixed with `_require_declared_checkout`, run **before any network call**: it
refuses a directory that is not a git repository, and one whose `origin` does not
match the declaration. Comparison normalizes only a trailing slash and a `.git`
suffix — deciding that an `ssh` and an `https` spelling name one repository is
not something this can know, so the error says so and names the fix.

## Also corrected

The PR body and the README claimed a failure "leaves no half-fetched store
behind" without qualification. That was broader than what held even after the
fix — a *refresh* against a pre-existing checkout deliberately does not delete
it. Both now say what is actually true.

## Tests added

- `test_a_repository_without_a_store_leaves_no_checkout_behind`
- `test_an_occupied_checkout_is_not_fetched_without_checking_its_origin` — asserts
  no `fetch` reached the wrong remote, not merely that the call failed
- `test_an_occupied_checkout_that_is_not_a_repository_is_refused`

62 cases in `tests/test_store_provisioning.py`, all green.

## What this says about the original pass

Both defects sit in the same place: **the order of publish and validate**, and
**what `exists()` is taken to prove**. The spec named "leaves nothing behind" as
acceptance criterion 7 but enumerated only the unknown-ref and unreachable-remote
cases, so the tests followed the enumeration rather than the property. A criterion
stated as a property, with the enumeration as examples, would have been checked
against every failure path instead of two of them.

## Second review — incomplete component boundary and availability checks

A second review of the updated PR found four more blockers:

1. `tcw provision --component` accepted taxonomy and capabilities even though
   `FsStoreProvisioner` only knew the work-store layout. A taxonomy declaration
   was cloned and then rejected for missing work statuses. Child A must expose
   only `work`; child B adds the other values with their adapters.
2. The resolution ladder called a folder with the work status names "usable"
   before checking that an external store was inside a Git repository. Such a
   local `work.path` blocked fallback to an already-provisioned valid store.
3. When the local store was absent, `FsWorkStore.open` discarded a malformed
   repository declaration and `tcw validate` reported only the dead local path,
   losing the actionable configuration problem required by criterion 10.
4. Version `1.1.0` was cut while this item was still in review and both new
   capabilities were still `Missing`. Release work belongs after acceptance and
   completion, so the cut must be reverted and its entries restored to the
   upcoming files.

The first three have failing regression tests before implementation. The fourth
is enforced by restoring the five version sources and the upcoming release
documents to their pre-cut state while preserving the feature and rework entries.

## Independent completion review — local-store precedence in the command

The independent review of the fixes found that criterion 5 held in
`FsWorkStore.open` but not in the `tcw provision` command. With both a usable
local `work.path` and a repository declaration, plain provisioning still built a
declaration provisioner and could clone or fetch the declared repository. The
local store is first in the resolution ladder, so the command must report that
resolved store as already available and perform no clone or fetch. Explicit
`--refresh` remains the opt-in path that contacts the declaration.
