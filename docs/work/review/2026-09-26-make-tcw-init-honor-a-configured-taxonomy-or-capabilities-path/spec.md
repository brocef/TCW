# Spec — Make tcw init honor a configured taxonomy or capabilities path

## Capability changes

None. `tcw init` / `tcw <component> init` exists; this makes it scaffold where the
configuration says.

## Reproduction

Scratch node `q6` (`tcw init work --id q6`), then `taxonomy: {path:
knowledge/terms}` appended to `tcw-config.yaml`; released CLI:

- `tcw taxonomy list` → "no tcw taxonomy node here — run `tcw init` in the
  project folder."
- `tcw taxonomy init` → creates `docs/taxonomy`; `knowledge/terms` stays absent;
  the config is unchanged.
- `tcw taxonomy list` → the same advice again.

## Problem

`init` (`tcw/store/fs.py:1055`) reads a location back from the configuration
only for `work` (fs.py:1082–1092); for any other component the plan falls to
`root / "docs" / c` (fs.py:1157–1159). The readers resolve a tree store through
`resolve_store` → `_local_root` (fs.py:1781), which anchors a relative
`<component>.path` with `anchor_configured_path` — so even a naive read-back in
`init` (`root / configured`) would build somewhere else from where readers look
when the node is a linked worktree and the path leaves the checkout.

Two hazards the fix must not introduce (both advisors raised them):

- A tree store's local location always wins (`resolve_store` rule 1). Scaffolding
  an empty local tree for a component that declares `<component>.repository`
  would hide the provisioned store from then on. This is true today for the
  default `docs/<component>`.
- A configured path must stay as written (`read_from_config`, fs.py:1080).

**Sibling sweep:** `work` has the same anchoring drift (it builds
`root / configured`); left alone — changing where `tcw work init` builds is a
separate decision with its own worktree tests.

## Goals

1. `tcw init` / `tcw <c> init` for `taxonomy` or `capabilities` scaffolds at the
   configured `<c>.path`, placed exactly where `_local_root` resolves it, and does
   not write the path back.
2. After it, the component's commands find the store.
3. `init` refuses to scaffold a tree component whose `<c>.repository` is
   declared while the store is absent locally, naming `tcw provision`.
4. A non-string or empty `<c>.path` is refused, as `work.path` already is.

## Non-goals

- Replacing "run `tcw init`" with the underlying reason (would change
  `find_node`'s contract); with goal 1 the advice becomes correct.
- `work`'s anchoring drift.
- An inside-a-repository check for tree stores.

## Design

- In `init`, read back `<c>.path` for every component in `components` that was
  not given a path (generalizing the `work` block), validating it the same way,
  and recording it in `read_from_config`.
- The plan's `base` for a tree component is `STORE_CLASSES[c]._local_root(root,
  configured_text)` — the readers' own rule — rather than `root / configured`.
  `work` keeps its current computation.
- Before any write: for a tree component with a `repository` declaration in the
  existing configuration whose `base` does not exist, raise `ValueError`
  "<c> declares a repository; run `tcw provision` rather than scaffolding an
  empty local store".

## Abstraction litmus test

No store-interface operation changes; `init` is the filesystem adapter's
scaffolding.

## Acceptance criteria

1. The reproduction, run with the fix: `tcw taxonomy init` creates
   `knowledge/terms`, not `docs/taxonomy`; `tcw taxonomy list` exits 0; the
   config still reads `path: knowledge/terms`.
2. The same for `capabilities` with `capabilities: {path: ledger}`.
3. `tcw init taxonomy capabilities --id x` on a fresh node with both paths
   configured creates both at their configured locations.
4. `taxonomy: {path: 7}` → `init` exits 1 naming `taxonomy.path`.
5. `taxonomy: {repository: {url: …}}` with no local store → `tcw taxonomy init`
   exits 1 naming `tcw provision`, and creates nothing.
6. The full test suite passes.

## Risks

- Criterion 5 changes behaviour for anyone who deliberately ran `init` on a
  component with a declared repository to get an empty local copy. That copy
  would have hidden the declared store; the refusal names the command that
  fetches it.

## Notes

- Advisors, 2026-09-29: Codex — option 1 with a repository guard and the
  readers' anchoring. Opus — the same, plus passing the underlying reason through
  instead of "run `tcw init`" (option 2) and an inside-a-repository check;
  both deferred as non-goals above, the first because it changes `find_node`'s
  return contract.
