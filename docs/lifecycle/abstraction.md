<!-- Bound to the `spec` and `plan` stages of `tcw work`; see `tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# The abstraction litmus test

_This repository's prime directive. It applies to the `spec` and `plan` stages —
a spec decides whether an operation belongs in the model, and a plan is where
operations get named — and it is the rule the rest of the codebase cites._

## Prime directive: the abstraction litmus test

TCW ships a filesystem-native default, but the **model is storage-abstracted** so it can run against an external tracker (Jira, a wiki, a graph DB) where one is already in use. That portability is the whole reason the system is viable at enterprise scale — do not trade it away for filesystem cleverness. Before adding or changing any operation, apply this test:

> **"Could a non-filesystem store implement this operation, even if less elegantly?"**
>
> - **Yes** → it belongs in the model / the abstract store interface.
> - **No** — it only works as a filesystem trick with no abstract analog → push it into the filesystem adapter as a private detail, or redesign it.

## Abstract spine, filesystem leverage

Express behavior in the abstract vocabulary — **item · status · transition · stable ID · reference · node relation · query · body/fields/attachments** — and let the filesystem _realize_ it. Filesystem superpowers are bonuses layered on top, never load-bearing assumptions of the model.

- **Leverage freely (bonuses):** docs co-located with code (one repo / worktree / PR / diff); one atomic commit carrying code change + status/capability change together; grep/diff/PR-review legibility; atomic `mv` as transition.
- **Keep out of the model (no abstract analog):**
    - Reconstructing current state from git history — _state is the status; git is archive._
    - Globbing a store folder as an open namespace — _bound it: body + named fields + named attachments._
    - Hard-coded paths in references — _use stable IDs / paths-within-the-store; resolve through the store._
    - Parent/child as literal directory ancestry outside the node-resolution layer — _express the relation abstractly; the FS adapter derives it from nesting._
    - Worktrees and `rg`/`find` queries — _filesystem-adapter local details, not store-interface operations._
