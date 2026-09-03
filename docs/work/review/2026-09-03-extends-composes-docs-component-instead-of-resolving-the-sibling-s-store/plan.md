# Plan — `extends` composes `docs/<component>` instead of resolving the sibling's store

## Tasks

### 1. Resolve the sibling's store

**Modifies** `tcw/store/fs.py`.

In `_extended_component_roots`, move the self-extension check ahead of the store
work — it is about node identity — then replace the composed path with
`STORE_CLASSES[component].open(Path(project.locator)).root`.

Translate the two failures for a reader standing in a different node:

- `StoreNotProvisioned` → re-raise with the project id prefixed, keeping the
  remote and the `tcw provision` instruction the original carries.
- any other `ValueError` → `project '<id>' has no <component> component`, which
  names the project rather than a path the user never wrote.

**Proves it:** `tests/test_capabilities_federation.py` and a taxonomy equivalent —
a sibling with `capabilities.path`/`taxonomy.path` pointing outside `docs/` is
extended successfully and its entries are read from the configured location; a
sibling with no component reports the new wording; a sibling with a `repository`
declaration and nothing provisioned reports the remote and `tcw provision`; a
node extending itself is still refused.

### 2. Confirm the default path is untouched

**Modifies** nothing.

Run the existing federation suites unchanged. Criterion 3 is that they pass with
no edits — if any needs one, the change is not behavior-preserving and the task
is to find out why rather than to update the test.

**Proves it:** `tests/test_capabilities_federation.py`,
`tests/test_capabilities_reset.py`, and the taxonomy federation tests, all green
without modification.

### 3. Documentation Sync

- **`README.md`** — [Public-API]. Fires only if it states where an extended
  tree is looked for. Check the federation section; if it says `docs/<component>`
  of the other project, correct it to "that project's configured store".
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Fixed: `extends`
  resolves the extended project's store rather than composing `docs/<component>`,
  so a configured or declared tree is found and an unprovisioned one says so.
- **`docs/release-notes/upcoming.md`** — [Public-API]. Fires, briefly: extending
  a project that keeps its taxonomy or capabilities somewhere other than the
  default now works.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component]. Check
  `tcw-capabilities` and `tcw-taxonomy` for wording that says an extended tree
  lives at `docs/<component>/`.
- **Capabilities** — none declared. If the `capabilities/federate` body asserts
  the composed path, add it to `capabilities.yaml` then.

## Verification

What the suite cannot check:

- **That the new messages read as being about the sibling.** Trigger each by hand
  in a scratch node and read them as a user standing in the extending project
  would. The spec's first risk is that a message about the other node reads as a
  fault in your own, and only a person can judge that.
- **The read-path cost.** `resolve_store` reads a config file where the old code
  did one `is_dir()`. Time `tcw validate` on this repository before and after; it
  walks many links and is the place any per-call cost would show.

## Notes

Small and self-contained: one function, one substitution, plus the message
translation that makes the substitution safe to read. The risk is entirely in the
error surface, which is why task 1's test list is mostly failure cases.
