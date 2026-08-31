# Spec — Generalize the store declaration to taxonomy and capabilities

## Capability changes

**New**

- `taxonomy/configure-the-taxonomy-store-location` — keep the taxonomy tree
  somewhere other than `docs/taxonomy`, via `taxonomy.path`.
- `capabilities/configure-the-capabilities-store-location` — the same for
  `capabilities.path`.
- `taxonomy/declare-the-taxonomy-stores-home-repository` — a `repository` block
  beside `taxonomy.path`.
- `capabilities/declare-the-capabilities-stores-home-repository` — likewise.

**Changed**

- `cli/provision-declared-stores` — `--component` grows `taxonomy` and
  `capabilities`; the local-store precedence rule becomes per-component.
- `cli/locate-tcw-storage-folders` — `tcw taxonomy path` and
  `tcw capabilities path` follow a configured location and report a declared but
  unprovisioned store.
- `cli/validate-a-node` — the three store failure modes are reported for all
  three components, not only work.
- `cli/initialize-a-tcw-node` — `tcw init` grows `--taxonomy-path` and
  `--capabilities-path` beside `--work-path`.

**Taxonomy**

`configurable-work-store-location` is **renamed** to
`configurable-component-store-location` and its description widened to all three
trees; `work/configure-the-work-store-location` re-points at the new slug. This
was decided with the requester (see `initial-request.md`). It matches
`provisioned-component-stores`, which child A already registered
component-generically. The rename lands *before* any capability names it, because
`tcw capabilities set` refuses a `Feature=` that does not resolve.

## Problem

Two gaps, one behind the other.

**Taxonomy and capabilities cannot be relocated at all.** `FsTreeStore.open` is
one line and reads no configuration:

```python
# tcw/store/fs.py:1044-1045
@classmethod
def open(cls, node_root: Path):
    return cls(node_root / "docs" / cls.COMPONENT)
```

`FsWorkStore.open` (`tcw/store/fs.py:2720-2775`) is by now a four-rule resolution
ladder over `work.path` and `work.repository`. The two components diverged, and
`FsTaxonomyStore` (1250) and `FsCapabilitiesStore` (1705) inherit the one-line
version.

**So the declaration cannot reach them.** Child A's mechanism is complete and
component-generic where it counts — `declared_repository(node_root, component)`
(`tcw/store/fs.py:2591-2606`) already reads `<component>.repository` for any
component — but three things are still work-shaped:

1. `PROVISION_COMPONENTS = ("work",)` (`tcw/cli.py:26`). Child A narrowed this
   deliberately after a review found the wider tuple cloning a taxonomy
   declaration and then rejecting it for missing work statuses.
2. `run_provision`'s local-store precedence check calls `FsWorkStore.open`
   (`tcw/cli.py:126`) from **inside a loop over components**. It is correct for
   the single-element tuple it ships with, and asks the wrong store the moment
   the tuple widens.
3. `FsStoreProvisioner` carries `self.component` for its *messages only*
   (`tcw/store/fs.py:2534, 2541-2545`). Every layout decision routes through the
   module-level `_is_store_layout` / `STORE_LAYOUT = ("inbox", *WORK_STATUSES)`
   (`2435`, `2498-2501`), and the refusal at `2604` says "has no work store" in
   so many words.

### The hard part: a tree store does not identify itself

A work store is self-describing — six named folders, and `_is_store_layout` reads
them. That predicate is what makes child A's guarantees real: `is_available()`
distinguishes a provisioned store from an empty directory (`2550-2558`), and
`_obtain` validates the layout *before* renaming the staging clone into place, so
a failure leaves nothing behind.

A tree store has no such layout. `init` creates the component directory and
nothing else — `[base]` for taxonomy and capabilities against
`[base/inbox, *base/<status>]` for work (`tcw/store/fs.py:741-743`). `CONFIG_NAME`
(`config.yaml`, `.config.yaml`) is loaded with `load_yaml` and is optional in
practice: neither `docs/taxonomy/` nor `docs/capabilities/` in this repository has
one. The only file `init` reliably leaves is `.gitkeep`, which is a git artifact
for tracking empty directories and carries no abstract meaning.

So "is this directory a taxonomy store?" has a weaker answer than the work store's,
and the spec has to say what that answer is rather than let the code discover it.

## Goals

1. All three component trees resolve through one ladder: a configured local
   location, else a declared home repository provisioned here, else an actionable
   refusal.
2. `tcw provision` obtains a declared taxonomy or capabilities store, with child
   A's guarantees intact — explicit-only network access, the remote named before
   it is contacted, an idempotent second run, and a failure that leaves nothing
   behind.
3. A project that configures nothing behaves **exactly** as it does today.

## Non-goals

- Redesigning the provisioning verb. `--dry-run`, `--refresh`, the failure
  semantics, and checkout placement are child A's and are consumed unchanged.
- Publishing writes back to a remote — child C.
- Giving tree stores a work-store-like status layout, or requiring a config file
  in stores that do not have one today.
- Federation and `extends` behaviour, which resolve through the store and are
  unaffected by where the store sits.

## Design

### One locator, three components

`FsTreeStore.open` gains the same four rules `FsWorkStore.open` runs, reading
`<component>.path` and `<component>.repository`:

1. the local store — `<component>.path`, else `docs/<component>` — when usable;
2. else the declared home repository's provisioned location, when usable;
3. else `StoreNotProvisioned`, when a home repository is declared;
4. else today's behaviour, unchanged and unguarded.

Rule 4 is the back-compatibility contract and is load-bearing: a node with no
`path` and no `repository` must not acquire a new failure mode. Concretely, rule 4
returns `cls(node_root / "docs" / cls.COMPONENT)` whether or not that directory
exists, exactly as the current one line does — a project with no
`docs/taxonomy/` gets the same behaviour it gets today, not a new refusal.

The ladder is shared rather than copied. `FsWorkStore.open`'s body is the
prototype; the differences between the two are the config section name and the
"usable" predicate, so those become the parameters and the ladder becomes one
function both call.

### What "usable" means for a tree store

**A tree store is usable when its root is an existing, readable directory.** No
marker file, no required entries.

This is deliberately weaker than the work store's check and the spec says so
rather than pretending otherwise. It is the strongest claim available without
inventing a marker that existing stores do not carry, and inventing one would
break rule 4 for every project that has a taxonomy tree today.

Two consequences, both accepted:

- A declared repository that clones fine but whose `repository.path` names an
  empty directory is reported as provisioned. The store then opens and lists
  nothing — indistinguishable from an empty taxonomy, which it genuinely is.
- A `repository.path` that names a directory holding *unrelated* content is
  likewise accepted. The work store would have caught this; the tree store
  cannot, and no test will claim it does.

What is **not** weakened: `repository.path` must resolve to an existing directory
inside the clone before the staging checkout is renamed into place. That is the
check that keeps criterion 7 true, and it is available for every component.

### Per-component knowledge, in the component

The provisioner stops consulting a module-level work-store predicate and asks the
component instead. `FsStoreProvisioner.__init__` already takes `component`; it
gains a resolved store-layout predicate for that component, so
`_is_store_layout`'s work-store definition becomes the work component's answer
rather than the only answer. The refusal text at `tcw/store/fs.py:2604` stops
saying "work store".

### The three work-shaped call sites

- `PROVISION_COMPONENTS` becomes `COMPONENTS`, and `--component`'s help stops
  saying "currently: work". This widens **with** the adapters, never before them.
- `run_provision`'s precedence check (`tcw/cli.py:126`) resolves the store for
  *the component being provisioned* instead of always the work store.
- `tcw init` grows `--taxonomy-path` and `--capabilities-path`; `init`'s
  `work_path` parameter generalizes to a per-component mapping.

### Validation

`tcw/validate.py` reports all three of a store's failure modes — a configured path
that is wrong, a declaration that is unprovisioned, a declaration that is
malformed — for each of the three components, in the words child A established.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| Resolve a component store through a configured location, else a declaration, else refuse | **Model.** "Make the store for this component available to me" is a question any backing store answers. A tracker-backed store resolves an endpoint and credentials instead of a path; the ladder's shape survives. |
| `StoreProvisioner.describe` / `is_available` / `ensure_available` for two more components | **Store interface, unchanged.** Child A's signatures name no URL, ref, or directory and none is added. A tracker store answering `is_available() -> True` remains a legitimate implementation. |
| "Is this root a usable store for component X?" | **Filesystem-adapter private detail.** The abstract question is `is_available()`, which already exists. Whether the answer is six folder names, a readable directory, or an authenticated API probe is the adapter's business, which is exactly why the predicate moves *into* the component rather than staying a module-level constant. |
| `<component>.path` and `<component>.repository` config keys | **Model-adjacent, and correctly so.** These are node configuration read before any store exists — `declared_repository` is deliberately not a store method for that reason (`tcw/store/fs.py:2591-2598`). A tracker adapter reads its own keys from the same config. |
| Renaming staging into place, `.git` probes, checkout directories | **Filesystem-adapter private detail**, unchanged from child A and not re-derived here. |
| Widening `--component` | **No new operation.** A CLI argument gains two legal values. |

No operation in this item requires the store to be a filesystem. The one place
the filesystem shows through — what "usable" means — is precisely where the
litmus test says it belongs: inside the adapter, behind an abstract predicate.

## Acceptance criteria

Each is stated as a **property**, with examples as illustration rather than as
the specification. Three of the five review passes on child A found the same
defect shape — a criterion written as an enumeration was tested to its
enumeration, and the property it illustrated went unchecked.

1. **A declared, unprovisioned tree store is reported as such by every command
   that needs it, never as an absent component.** No `tcw` command answers such a
   node with "no tcw node here", `run tcw init`, or an empty listing; each names
   the declared remote and `tcw provision`. Asserted across the taxonomy and
   capabilities command surfaces, not at one call site. _Illustrative:_
   `tcw taxonomy list`, `tcw taxonomy path`, `tcw capabilities list`,
   `tcw capabilities show <path>`, `tcw capabilities drift`.
2. **After provisioning, a declared tree store is indistinguishable from a local
   one.** Every read that worked against `docs/<component>` works against the
   provisioned location, including federation through `extends` and `tcw://`
   reference resolution. _Illustrative:_ `tcw taxonomy list` prints the terms,
   `tcw taxonomy path` prints the provisioned absolute path.
3. **Provisioning is idempotent and contacts nothing it does not need to.** A
   second run of any provisioning invocation performs zero Git subprocess calls
   and exits 0, asserted by intercepting the adapter's Git invocation rather than
   by timing.
4. **A configured local store always wins over a declaration, for every
   component.** With both a usable `<component>.path` and a `repository` block,
   resolution and plain `tcw provision` both use the local store and make no
   network call. Asserted per component, because the code path that got this
   wrong in child A was a single hard-coded `FsWorkStore.open` inside a loop over
   components.
5. **`tcw provision` treats each declared component independently.** Provisioning
   a node declaring two or three components resolves, reports, and fails each on
   its own; one component's failure neither suppresses nor corrupts another's
   result, and `--component` selects exactly what it names.
6. **A node that configures nothing behaves exactly as it does today.** No new
   refusal, no new required file, no new output, for a project with neither
   `<component>.path` nor `<component>.repository` — including one whose
   `docs/taxonomy/` does not exist at all. Asserted by the existing suites passing
   unmodified: no test outside the provisioning module is rewritten to accommodate
   this work.
7. **A provisioning failure leaves nothing behind, for every component.** No
   directory at the target after any refusal — unreachable remote, unknown ref, or
   a `repository.path` naming nothing in the clone. Stated as the property; the
   three named cases are examples of it.
8. **Only `tcw provision` reaches the network, still.** No command added or
   changed by this item performs a Git network operation, enforced in the shape of
   the package-wide rule in `tests/test_subprocess_stdin.py`.
9. **A malformed `<component>.repository` names the offending configuration line,
   for every component**, from every command and not only `tcw validate`, and
   never falls back to reporting the component as absent.
10. **The taxonomy Feature rename leaves no dangling reference.** `tcw validate`
    and `tcw capabilities check` both pass, and no capability references the old
    slug.
11. **Every criterion is reproducible from a bare shell**, with no Claude hook and
    no slash command involved.

## Risks

- **Rule 4 is the whole back-compatibility story, and it is easy to tighten by
  accident.** Any "usable" check that leaks into the undeclared path breaks every
  existing project. Criterion 6 exists to catch that and is the one to run first.
- **The weak tree-store predicate is a real reduction in what provisioning can
  promise.** It is accepted deliberately and documented in the capability bodies;
  the risk is that a later reader assumes work-store-strength guarantees apply.
- **Sharing the ladder between `FsWorkStore` and `FsTreeStore` touches the work
  store's most-reviewed code path.** Child A's 74 provisioning cases plus
  `test_external_work_store.py`'s 82 are the regression net; a shared ladder that
  makes any of them fail is the wrong refactor, not a test to update.
- **`tcw capabilities set` refuses an unresolvable `Feature=`**, so the taxonomy
  rename must land before the capability writes. The reverse order fails closed,
  which is the safe direction, but it will stall the work if sequenced wrongly.
- **This item edits the store layer the `tcw` CLI itself runs on.** A broken
  intermediate state disables the very commands that record the work. Transitions
  should be taken before risky edits, not after.

## Notes

- `declared_repository` was written component-generic by child A and needs no
  change here — the one piece of that work that anticipated this item correctly.
- The `--component work` narrowing child A applied was correct and is being
  reversed only because the adapters that make the other values honest arrive in
  the same change. Widening the tuple without them would reintroduce exactly the
  defect that review caught.
