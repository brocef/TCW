# Live reference search and object-scoped save validation

## Capability changes

- Change `web/editing` while keeping it `Supported`: structured reference fields offer live, accessible object search, and every saved object is immediately validated with TCW's standard rules.
- Record `web/editing` under `changed:` in this item's `capabilities.yaml`.
- Keep the existing `local-web-app` Feature; no taxonomy change is needed.

## Problem

The React editor currently requires users to know and type reference identifiers, and post-write validation is inconsistent: Taxonomy and Capability writes run broad component checks while Work and resource saves do not surface validation findings. Broad checks can attribute unrelated defects to a successful save.

## Goals

- Search already-loaded Work, Taxonomy, and Capability objects from every structured reference field.
- Keep free-form entry and store canonical identifiers.
- Provide keyboard, pointer, and screen-reader-compatible selection behavior.
- Validate exactly the object that a successful mutation created or changed, including its bounded resources, and return findings as post-save warnings.
- Preserve full-node/path validation and the public `tcw validate [path]` CLI.

## Non-goals

- No search or validation HTTP endpoint.
- No transactional rollback for validation findings.
- No request-payload, URL, stored-reference, or public CLI changes.
- No taxonomy Feature or skill-workflow change.

## Reference search behavior

Match trimmed text case-insensitively against display name and identifier. An unmatched field contributes zero:

`score = ((queryLength / nameLength) * 1 + (queryLength / identifierLength) * 2) / 3`

Sort descending by score, then display name and identifier, and return at most 10 results. Display both fields and bold every matching substring. Up/Down navigates, Enter selects, Escape closes, and pointer selection must avoid blur races.

Single fields write the canonical identifier. Multi fields append non-duplicate chips, clear their query, and retain focus. Enter commits raw multi-value text when no result is active. A leading `!` in Capability `When` searches the underlying condition and is preserved.

Candidate scopes are centralized:

| Field | Candidates | Cardinality |
|---|---|---|
| Work Parent | Work excluding current item and descendants | Single |
| Work Initiative | Work items with `type: epic` | Single |
| Work Blockers | Work excluding current item and duplicates | Multiple |
| Taxonomy Parent | Taxonomy entries | Single |
| Taxonomy Relates to | Taxonomy excluding current entry and duplicates | Multiple |
| Taxonomy Vocabulary | Taxonomy entries of kind `Vocabulary` | Multiple |
| Capability Feature | Taxonomy entries of kind `Feature` | Single |
| Capability Subject | All Taxonomy entries | Multiple |
| Capability Roles | Capabilities under `roles/` | Multiple |
| Capability When | Capabilities under `conditions/` | Multiple |
| Capability Blocked by | Capabilities excluding current entry | Single/free-form |
| Capability Planning doc | Work items | Single |
| Capability Superseded by | Capabilities excluding current entry | Single |

## Object-scoped validation

Add frozen `ValidationTarget(axis, ref)` and an optional keyword-only `target` argument to `tcw.validate.validate`. Reject simultaneous `path` and `target`. The target is an abstract object reference; filesystem adapters privately resolve its metadata, body, artifacts, and bounded sidecars.

Each abstract store `check()` accepts an optional object identifier. Per-object checks cover the selected object's existing semantic rules: Taxonomy kind/vocabulary/relations/collisions/reachable cycles; Capability fields, required associations/references/override target/attachments; and Work tags plus existing Work checks. Authored YAML and `tcw://` references are scoped to the target's bounded resources. Incoming references and unrelated invalid objects are excluded.

Always validate the project graph first and return graph problems before target resolution. Missing targets produce an explicit problem and never fall back to full validation.

After every successful web create, structured edit, artifact save, or sidecar save, validate the canonical returned/resolved object. Descendant Work saves use the resolved descendant node and bare identifier. Findings use the existing optional `warnings` response field. Validation exceptions after mutation become a `validation could not complete` warning so a committed save is never reported as failed.

## Client behavior

Persistent accessible UI state says `Saved with validation issues` and a toast reports the problem count. A later clean save clears stale warnings. Warnings remain distinct from request errors and 409 conflicts. New internal TypeScript types use the repository's `T` prefix, and Work's client type exposes its existing optional `type` field.

## Acceptance criteria

- Search ranking, limits, highlighting, filtering, keyboard/pointer behavior, free text, negated conditions, and canonical identifiers are covered by unit/component/browser tests.
- Full, path, and target validation modes are covered across all axes, including missing targets, graph failures, inherited/qualified references, Work resources, and unrelated broken objects.
- Every server mutation category returns targeted warnings, clears them on a clean save, and survives post-commit validation exceptions.
- Committed browser assets are rebuilt deterministically; Python, typecheck, lint, Vitest, Playwright, component checks, node validation, and diff hygiene pass.
- README, capability description, release notes, and changelog describe the shipped behavior.
