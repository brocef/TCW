# Fix work inbox accept's entry resolution and initiative stamp — Specification

## Capability changes

No capability-ledger record changes are required. This is a correction to the existing work-inbox and cross-node delegation behavior, not a new user capability.

## Problem

`tcw work inbox list` exposes each entry's storage reference and derived title, but `inbox_accept` resolves only the exact reference passed to the store. A standalone Markdown entry therefore appears as `name.md | file | name`, while accepting `name` fails even though the command printed it as an identifier (`tcw/work/cli.py:250-255`, `tcw/store/fs.py:2708-2757`).

Delegation writes a closed frontmatter vocabulary containing `from` and optional `initiative` (`tcw/work/recursion.py:218-226`). Acceptance currently treats the whole Markdown file as opaque body text and creates the work item without extracting `initiative`, silently breaking the back-pointer used by epic reconciliation (`tcw/store/fs.py:2737-2825`, `tcw/work/recursion.py:71-80`).

## Goals

- Let `inbox accept` consume a standalone file by its exact reference, its filename without `.md`, or its unique derived title/slug as shown by `inbox list`.
- Preserve a valid, non-empty delegated `initiative` value in the accepted item's `state.yaml`.
- Keep folder-entry addressing and attachment ingestion unchanged.
- Fail explicitly when a relaxed identifier is ambiguous rather than choosing an entry by iteration order.

## Non-goals

- General aliases or fuzzy matching for inbox entries.
- An `--initiative` override on `inbox accept`.
- A general warning system for unknown frontmatter. TCW's own writer emits only `from` and `initiative`.
- Validation of the initiative against another node during acceptance; cross-node references are intentionally loose.
- Changes to the broader intake unification proposed by the lifecycle epic.

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
- If a folder and a Markdown file produce the same listed title, accepting that title fails with an ambiguity error and consumes neither entry; either exact reference still works.
- Accepting a delegated entry with `initiative: epic-slug` creates a backlog item whose `initiative` is `epic-slug` and whose state serializes that field.
- Missing or blank initiative frontmatter creates the same item shape as today.
- A non-scalar initiative fails before creating an item or consuming the inbox entry.
- Existing folder, binary-file, attachment, CLI, and cross-node recursion tests remain green.

## Risks

- Relaxed lookup can introduce collisions. Exact-first ordering and explicit ambiguity make collisions safe and deterministic.
- Intake code is also in scope for the lifecycle epic. Landing first and recording regression tests prevents the rewrite from losing these guarantees.
- Treating arbitrary frontmatter as trusted state would widen the model accidentally. Only `initiative` is propagated.
