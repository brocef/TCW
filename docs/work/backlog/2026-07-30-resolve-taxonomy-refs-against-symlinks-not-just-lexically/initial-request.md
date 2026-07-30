# Resolve taxonomy refs against symlinks, not just lexically

## Origin

Found during the `verify` stage of
`2026-07-30-validate-taxonomy-vocab-refs-at-write-time-and-define-bare-slug-resolution`
(2026-07-30), by the read-only verifier agent attacking that item's traversal fix
with ~25 ref shapes. Independently reproduced in the coordinating session before
filing.

That item bounded taxonomy refs to the store root by routing them through
`_safe_store_id`, which closed every **syntactic** escape — `..` at any depth,
absolute paths, backslashes, empty segments, URL- and double-encoded variants,
and the `extends` alias branch — on both the read and delete paths, via CLI and
HTTP. This is the residue it did not cover, and deliberately did not claim to:
its Design §3 is about ref *syntax*.

## Problem

`_safe_store_id` is a **lexical** guard. It never calls `resolve()`. So a
directory symlink planted inside `docs/taxonomy/` reads outside the store:

```
$ ln -s ../../capabilities/victim docs/taxonomy/alpha/link2
$ tcw taxonomy show alpha/link2/inner
Inner  (alpha/link2/inner, local)
kind: Vocabulary

SECRET BODY
exit=0
```

`--vocab alpha/link2/inner` is likewise accepted and stored, so a ref pointing
outside the taxonomy store passes write-time validation and `check`.

**The delete path does not escape.** `git rm` refuses to cross a symlink
(`fatal: pathspec '…' is beyond a symbolic link`), and the target survives:

```
$ tcw taxonomy rm alpha/link2/inner
… subprocess.CalledProcessError … returned non-zero exit status 128
$ ls docs/capabilities/victim/inner/
description.md  meta.yaml          # intact
```

Removing the symlink itself removes only the link, leaving the target directory
and its contents in place — verified.

**Second, smaller defect on the same path:** that failure surfaces as a full
`CalledProcessError` stack trace rather than an error message, because
`tcw/taxonomy/cli.py:118` catches `ValueError` only while `git_rm`
(`tcw/store/fs.py:267`) raises `CalledProcessError`. Cosmetic — no deletion
occurs — and **pre-existing**: a symlinked store root fails the same way on `add`,
and did so before the bounding fix landed.

## Product changes

None yet decided. `tcw taxonomy show`/`rm` and `--vocab` would refuse a ref that
traverses a symlink out of the store; whether that is a user-visible restriction
worth a release note depends on whether symlinked stores are a supported shape
(see Open for the spec).

## Technical changes

Not decided — the spec's job. The candidate is a containment check that compares
the resolved path against the resolved store root, somewhere on the
`get_local` path.

## Severity: low, and the reasoning matters

Rated low rather than critical, deliberately:

- **Read-only in effect.** No deletion escapes the store.
- **It requires repo write access** to plant the symlink. The defect that was
  fixed needed only a CLI argument or an HTTP request body — anyone who can
  create a symlink in `docs/taxonomy/` can already read `docs/capabilities/`
  directly.
- It is not a regression; the behavior predates the bounding fix.

It is filed rather than dismissed because "refs are bounded to the store" is now
a stated property of the system, and this is the one case where that statement is
not literally true. An unrecorded exception to a security property is how the
property quietly stops being believed.

## Open for the spec

- **Whether to resolve at all.** `Path.resolve()` on every ref adds a syscall to
  the hottest resolution path in the taxonomy store; the guard is currently pure
  string work. Measure before assuming it is free.
- **Where the check belongs.** `_safe_store_id` is shared with other stores
  (`fs.py:553-566`); making it filesystem-aware changes it for every caller. A
  separate containment check inside `get_local` may be the narrower move.
- **Whether legitimate symlinks inside a store should be supported.** Federation
  already exists as the sanctioned way to reference another project's taxonomy
  (`extends`), which argues for refusing symlink traversal outright rather than
  resolving and re-checking. But a symlinked `docs/` or store root is a real
  deployment shape, and it already fails at `git add` today — decide whether that
  is acceptable or its own bug.
- **The `CalledProcessError` leak** is separable and could ship on its own: catch
  it in the taxonomy CLI and render an error. Decide whether it belongs here.

## Meta changes

Litmus test: a containment check is a filesystem-adapter private detail — a
remote store has no paths to contain — so it belongs in `FsTaxonomyStore`, not on
the abstract interface. Same placement as the lexical guard it extends.

## Notes

`tcw taxonomy check` accepts a ref through a planted symlink today, so an
affected taxonomy reports clean. Any fix should decide what `check` says about an
existing ref of this shape — reporting it dangling would be consistent with how
the bounding fix treats syntactic escapes.

Also observed while grounding this, and **not** part of it: the leaf-slug
fallback scans every directory under the store, including ones with no
`meta.yaml`, so `--vocab assets` resolves to `alpha/assets` for a bare asset
folder. Pre-existing `get_local`/`_term` behavior (`(root/slug).is_dir()` with no
`meta.yaml` requirement) — `--vocab alpha/assets` was accepted before the change
too. Not an escape and not a regression; recorded so it is not rediscovered as
new.
