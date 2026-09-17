# Spec: Make tcw taxonomy rm refuse nested terms and live references

## Capability changes

- **changed:** `taxonomy/remove-a-local-term` — `rm` refuses a term with terms
  nested under it, or one another local term still names in `relatesTo` or a
  Feature's `vocabulary`, deleting nothing and naming what is in the way. Today it
  "warns if other terms still relate to it".

## Problem

`FsTaxonomyStore.remove` (`tcw/store/fs.py:1952-1959`) resolves the term, refuses an
inherited one, then `self._rm(self.root / term.slug)` — a `git rm -rf` of the whole
folder. Because a term's slug is its folder path (`_local_slugs`, `:1853-1859`,
lists every readable directory), `rm admin` also deletes `admin/permission` and
reports only `Removed term admin` (`tcw/taxonomy/cli.py:104-125`). The CLI computes
`relators` (`fs.py:1998-2001`) before removing and prints a warning afterwards; the
term is gone either way.

`tcw taxonomy check` (`fs.py:2083-2095`) reports a dangling `relatesTo` ref **and** a
dangling Feature `vocabulary` ref, so either kind of reference makes `check` fail
right after `rm` reported success. The request names `relatesTo`; `vocabulary` is the
same defect in the same store (sibling sweep).

`relators` also matches by leaf: `r.rsplit("/", 1)[-1] == slug` compares a
reference's last segment with a full path, so removing top-level `permission` is
"related" to by a ref to `other/permission`, and a nested target is never matched by
leaf at all.

`FsCapabilitiesStore.remove` (`fs.py:2492-2519`) is the behaviour to match: exact
listed path only, refuse nested entries found by walking the folder itself, refuse
live references resolved and compared by folder identity (`_referrers`,
`:2521-2570`), then delete.

## Goals

- `rm` deletes nothing and exits 1 when the term has nested terms or local
  references, and the message names them.
- The refusal lives in the store, so every caller (CLI, web app) gets it.
- References are compared by what they resolve to, not by spelling.

## Non-goals

- References from the capabilities store (`Subject`, `Feature`), which name taxonomy
  terms from another component the taxonomy store has no handle on;
  `tcw capabilities check` reports them. Filed as a follow-up.
- References from inherited taxonomies or other projects: only local terms are
  read, as `check` does and as capabilities' `_referrers` does.
- A `--force` or cascade option.

## Design

`FsTaxonomyStore.remove(ref)`:

1. Resolve with `get`; `None` → "no such term". Inherited → the existing refusal.
   A local term whose `slug` is not in `_local_slugs()` (a different spelling or
   case resolved by the disk) → "no such term", as capabilities does.
2. **Nested:** walk the term's folder itself for any subdirectory (not the filtered
   listing: `git rm -rf` removes unreadable and dot-directories too). Any →
   `ValueError("cannot remove '<slug>': nested under it: <paths> (remove those first)")`.
3. **Referrers:** for every other local term, resolve each `relatesTo` and
   `vocabulary` ref through `get` (skipping `AmbiguousRef`, as `_referrers` skips
   `RefError`); a hit whose origin is local and whose folder is the same file as the
   target's → `"<term> (relatesTo)"` / `"<term> (vocabulary)"`. Any →
   `ValueError("cannot remove '<slug>': still referenced by <list> (repoint or clear those first)")`.
   A term's reference to itself does not count.
4. Otherwise `_rm`.

`TaxonomyStore.remove`'s docstring (`tcw/store/base.py:540-541`) states the contract.
The CLI loses its `relators` call and warning; `relators` is deleted (no other
caller). Litmus test: nested terms and references are store-level relations any
backend can query — yes.

## Acceptance criteria

1. `tcw taxonomy add Admin`, `tcw taxonomy add Permission -p admin`, then
   `tcw taxonomy rm admin` exits 1, stderr names `admin/permission`, and both
   terms still `show`.
2. A term named in another term's `relatesTo` is refused, naming
   `<referrer> (relatesTo)`; `check` still passes afterwards.
3. A vocabulary term a Feature names is refused, naming `<feature> (vocabulary)`.
4. Removing top-level `permission` is **not** refused by a ref to
   `admin/permission`.
5. A term relating to itself can be removed.
6. `rm` with a case-variant spelling (`Admin` for `admin`) is "no such term" and
   deletes nothing (skipped where the filesystem is case-sensitive).
7. A leaf term with no references is still removed (existing `test_rm_local`).
8. The full suite passes.

## Risks

- A behaviour change to a shipped command: a script that relied on cascade deletes
  now exits 1. Release notes say so, as the request requires.
