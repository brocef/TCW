# Fix work inbox accept's entry resolution and initiative stamp — Specification

## Capability changes

No capability-ledger record changes are required. This is a correction to the existing work-inbox and cross-node delegation behavior, not a new user capability.

## Problem

`tcw work inbox list` exposes each entry's storage reference and derived title, but `inbox_accept` resolves only the exact reference passed to the store. A standalone Markdown entry therefore appears as `name.md | file | name`, while accepting `name` fails even though the command printed it as an identifier (`tcw/work/cli.py:250-255`, `tcw/store/fs.py:2708-2757`).

Delegation writes a closed frontmatter vocabulary containing `from` and optional `initiative` (`tcw/work/recursion.py:218-226`). Acceptance currently treats the whole Markdown file as opaque body text and creates the work item without extracting `initiative`, silently breaking the back-pointer used by epic reconciliation (`tcw/store/fs.py:2737-2825`, `tcw/work/recursion.py:71-80`).

### Folded in: `delegate --help` names the wrong identifier

Found 2026-08-13 while declaring the cross-node capabilities, and folded into this item rather than filed separately because it is the same defect in the same subsystem: the CLI advertising one identifier form while resolving another.

`tcw work delegate`'s first argument is documented as `child node path (relative to this node)` (`tcw/work/cli.py`, the `pdg.add_argument("child", …)` help string). It is not a path. `delegate` builds `{registered_project_id(node_root, c): c for c in child_nodes(node_root)}` and matches the **canonical project ID** (`tcw/work/recursion.py:239-249`). Verified on a fixture where directory name and project ID differ:

```
'sub-dir-name'   -> ValueError: no child node 'sub-dir-name'. children: canonical-id
'canonical-id'   -> OK  …/sub-dir-name/docs/work/inbox
```

The existing tests cannot catch it: `mk_node` in `tests/test_recursion.py` derives the project ID from the directory name, so the two always coincide.

Unlike the inbox case, the **code is right and the documentation is wrong**. IDs are identity and paths are adapter locators, so accepting a path here would be the defect. The fix is the help string plus a test whose ID and directory name differ.

## Goals

- Let `inbox accept` consume a standalone file by its exact reference, its filename without `.md`, or its unique derived title/slug as shown by `inbox list`.
- Preserve a valid, non-empty delegated `initiative` value in the accepted item's `state.yaml`.
- Keep folder-entry addressing and attachment ingestion unchanged.
- Fail explicitly when a relaxed identifier is ambiguous rather than choosing an entry by iteration order.
- Correct `tcw work delegate`'s argument help so it names the canonical project ID it actually resolves, and pin it with a test whose project ID and directory name differ.

## Non-goals

- General aliases or fuzzy matching for inbox entries.
- An `--initiative` override on `inbox accept`.
- A general warning system for unknown frontmatter. TCW's own writer emits only `from` and `initiative`.
- Validation of the initiative against another node during acceptance; cross-node references are intentionally loose.
- Changes to the broader intake unification proposed by the lifecycle epic.
- Making `delegate` accept a filesystem path. IDs are identity; the code is correct and only its help string is wrong.
- Auditing every other CLI help string for the same class of drift. Out of scope here; worth its own pass.

## Design

### Resolve an entry once in the filesystem adapter

Add a private resolver used by `inbox_show` and `inbox_accept`, keeping the abstract store vocabulary as an entry reference rather than exposing filenames as model semantics. Resolution proceeds in this order:

1. exact entry reference;
2. for a bare input, `<input>.md`;
3. a unique match on the `InboxEntry.title` value returned by `inbox_list`.

Exact reference wins even if a relaxed candidate would collide. Zero matches retains `no such inbox entry`; multiple title matches raise an ambiguity error naming the candidates. Folder references remain exact unless their listed title uniquely matches, and no recursive filesystem search becomes part of the interface.

Use the same resolver for `show` and `accept` so sibling inbox commands accept the same identifiers. The CLI remains a thin caller (`tcw/work/cli.py:258-296`).

### Carry the initiative through acceptance

Add a focused frontmatter parser at the inbox-ingestion boundary; the current implementation has no parser to reuse. Preserve the original Markdown unchanged in `## Inbox contents`, while separately normalizing `initiative` as a string: absent, null, or whitespace-only means no initiative; a scalar non-empty value is written into the accepted item's state. Reject structured YAML values with a clear invalid-frontmatter error rather than serializing a list or mapping into state.

`from` remains provenance in the generated request body. The accepted inbox source is consumed only after work-item creation succeeds, preserving the current failure behavior.

### Compatibility and sequencing

This change lands before the lifecycle-polymorphism epic because both alter intake. The later epic must preserve the identifier resolver and initiative propagation when it replaces the current request-document synthesis.

## Acceptance criteria

- Given `inbox/foo.md`, `inbox list` prints `foo.md | file | foo`, and both `inbox show foo` and `inbox accept foo` resolve that file.
- Exact `foo.md` addressing continues to work.
- **Corrected 2026-08-13 during implementation.** This criterion previously read: "If a folder and a Markdown file produce the same listed title, accepting that title fails with an ambiguity error." That contradicts the Design's own first rule — a folder named `example` *is* the exact reference `example`, and the Design says "Exact reference wins even if a relaxed candidate would collide." Both cannot hold. Resolved toward the Design, because the alternative makes a folder unaddressable by its own name the moment someone drops `example.md` beside it, and because the ref is the first column `inbox list` prints. The criteria are therefore:
    - Given `inbox/example/` and `inbox/example.md`, `accept example` resolves the **folder** (exact reference), and `accept example.md` resolves the file. Neither is an error.
    - Ambiguity is reserved for an input that is *not* an exact reference and has no `<input>.md`, yet matches several listed titles — e.g. `example.txt` and `example.rst` with input `example`. That fails with an ambiguity error naming the candidates and consumes nothing.
- Accepting a delegated entry with `initiative: epic-slug` creates a backlog item whose `initiative` is `epic-slug` and whose state serializes that field.
- Missing or blank initiative frontmatter creates the same item shape as today.
- A non-scalar initiative fails before creating an item or consuming the inbox entry.
- Existing folder, binary-file, attachment, CLI, and cross-node recursion tests remain green.
- `tcw work delegate --help` describes its first argument as a canonical project ID, with no mention of a path.
- A test in which a child's project ID and directory name differ asserts that the ID resolves and the directory name is refused with the valid IDs named.

## Risks

- Relaxed lookup can introduce collisions. Exact-first ordering and explicit ambiguity make collisions safe and deterministic.
- Intake code is also in scope for the lifecycle epic. Landing first and recording regression tests prevents the rewrite from losing these guarantees.
- Treating arbitrary frontmatter as trusted state would widen the model accidentally. Only `initiative` is propagated.
- The `delegate` regression is only meaningful if its fixture breaks the ID/directory-name coincidence that `mk_node` creates. A test reusing `mk_node` unchanged would pass against the unfixed code and prove nothing.
