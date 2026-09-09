Filed out of the decision to make a `work.path` outside any Git repository a
`StoreDeclarationError` rather than something the resolution ladder falls through
on. That change is right — a store that is present and unusable must not be
silently replaced by a declared one — but it leaves a real inconsistency, and the
counter-argument is worth keeping rather than discarding.

**The contract it strains.** `docs/release-notes/v1.0.1.md` states plainly that
TCW "has always needed Git to write and never needed it to read". Under the
current behaviour a user whose `work.path` sits outside a repository cannot even
`tcw work list` — a pure read the product promises works anywhere.

**The inconsistency.** The *non-external* default `docs/work` already behaves the
promised way: in a non-git directory it opens, reads fine, and refuses mutations
through `_require_repository` with "not inside a git repository. Run `git init`
first." Only the external `work.path` case refuses at open time. The same
condition therefore has two different answers depending on which of the two ways
the store was located.

**Why it is not a one-liner.** `_open_at` falls back to
`store_git_root=node_root` when `git_root(root)` is None. Simply removing the
open-time check would let `_require_repository` inspect the *node's* repository,
pass, and hand `git_stage` a path outside it — the half-written-then-traceback
failure v1.0.1 was written to eliminate. Doing it safely means allowing
`store_git_root: Path | None` and making `_require_repository` the single place
that decides, which touches every write path.

**Also worth deciding here.** `tcw init` currently refuses to create this
configuration at all. If reads are to work, is that refusal still right, or
should it warn and proceed?

Related: `2026-09-01-a-broken-work-path-is-hidden-when-a-repository-is-also-declared`
proposes carrying rule 1's reason into rule 3's message for the cases that do
legitimately fall through. That is the complementary half — this item is about the
cases that should not fall through at all but should still be readable.
