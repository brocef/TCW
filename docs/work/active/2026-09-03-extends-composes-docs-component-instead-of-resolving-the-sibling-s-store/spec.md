# Spec — `extends` composes `docs/<component>` instead of resolving the sibling's store

## Capability changes

None. `capabilities/federate` describes extending another project's tree and says
nothing about where that tree sits; this makes an existing claim true in a case
it already covered rather than changing what a user can do. If implementation
finds wording that asserts the composed path, add it then.

## Problem

`_extended_component_roots` builds the extended node's store path by string
composition (`tcw/store/fs.py`):

    target = Path(project.locator) / "docs" / component
    if not target.is_dir():
        raise ValueError(f"project '{project_id}' has no docs/{component}/")

Every other read of a component store goes through `resolve_store`, whose ladder
is: the configured `<component>.path`, else the declared repository's provisioned
location, else a documented refusal. This one call site skips all of it.

Two consequences, both silent:

- **A sibling that configures `taxonomy.path` or `capabilities.path` cannot be
  extended from.** `tcw init --taxonomy-path` and `--capabilities-path` exist
  precisely to move those trees, and the error a user gets says the project has
  no `docs/<component>/` — which is true of the composed path and false of the
  project.
- **A sibling whose tree is *declared* but not provisioned here reads as having
  no tree**, rather than as one `tcw provision` would obtain. That is the exact
  confusion the store resolution ladder was built to end, and it is reintroduced
  here.

The same file already states the rule this breaks: a store path is never composed
from a node root, because the store may live in another repository.

`FsTaxonomyStore` and `FsCapabilitiesStore` both carry `COMPONENT`, and
`STORE_CLASSES` maps a component name to its class, so the resolution this needs
is one lookup away.

## Goals

- `extends` resolves the extended node's store through `resolve_store`.
- A declared-but-unprovisioned sibling tree is reported as unprovisioned, naming
  the remote and the command, exactly as a local store's absence is.
- A sibling that genuinely has no such component still says so, in words that
  name the project rather than a path the user never wrote.
- Self-extension is still refused, and still by node identity rather than by
  comparing composed paths.

## Non-goals

- Reachability of the project itself — the item this was found from.
- Provisioning anything as a side effect of `extends`. Resolution answers where
  the store is; it never fetches.
- Any change to federation semantics: what is inherited, overridden, or how
  bodies compose.

## Design

Replace the composition with the component's own store resolution: look the class
up in `STORE_CLASSES`, open it at the extended node's root, and take its `root`.
That is one line of intent, and it inherits every rung of the ladder plus the
messages that go with each — including `StoreNotProvisioned`, which already says
which remote and which command.

Two failures then need translating rather than passing through raw, because the
reader is standing in a *different* node than the one that failed: a store that
cannot be opened at all becomes "project '<id>' has no <component> component",
and an unprovisioned one keeps its own message with the project id prefixed. The
existing self-extension check moves ahead of the resolution — it is about node
identity and should not depend on a store opening.

**Litmus test.** This removes a filesystem shortcut rather than adding an
operation: "where is this project's component store" is already a store-interface
question with an answer, and the fix is to ask it instead of guessing. Strictly
in the direction the prime directive points.

**Harness.** Adapter-internal; identical under both.

## Acceptance criteria

1. A node extending a sibling whose `taxonomy.path` points elsewhere resolves the
   sibling's terms, and the terms are read from the configured location.
2. The same for `capabilities.path`.
3. A node extending a sibling that keeps its tree at the default location behaves
   exactly as before — asserted by the existing federation tests passing
   unchanged.
4. A sibling whose tree is declared with a `repository` and not provisioned here
   produces a message naming the remote and `tcw provision`, not one claiming the
   project has no such component.
5. A sibling with no component at all produces a message naming the project and
   the component.
6. A node extending itself is still refused.

## Risks

- **The error surface widens.** `resolve_store` can raise for reasons the
  composed path never could — a malformed declaration, for instance. Each needs
  to arrive as a sentence about the *sibling*, or a user will read it as a fault
  in their own node.
- **`extends` is on a read path** that `tcw validate` walks over many links, and
  `resolve_store` reads a config file per call where the old code did one
  `is_dir()`. Federation roots are resolved once per store open, not per entry,
  so the multiplier is small — but it is not zero and the plan should say so
  rather than discover it.

## Notes

Nothing in this repository or in `proposit-app` configures a non-default tree
path today, so this is a latent defect. It is worth fixing anyway because the
failure is silent and its message actively misleads — and because the next
person to run `tcw init --taxonomy-path` will hit it with no way to guess why.
