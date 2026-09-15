# Plan — Project a work item as JSON

Tasks in dependency order. Each is one commit unless it says otherwise.

## Ordering constraint that shapes everything else

**Task 1 must land before `_show` is touched, in its own commit.** Criterion 7
requires the non-`--json` output to be checked against baselines captured from
the CLI *before* the change, and a baseline authored during implementation is not
a baseline — it is the implementer writing down what the code now does. Capturing
first, in a separate commit, is what makes the check independent. Every other
ordering here is convenience; this one is the criterion.

## Tasks

### 1. Capture the pre-change `show` baselines

Build four items in a scratch node and record `tcw work show`'s exact stdout for
each: one with a request, one intake-only, one with neither, and one with
blockers, an owner, effort/complexity, and tags. Commit them as fixture data
under `tests/fixtures/show_baseline/`.

Nothing else changes in this commit, so the fixtures are provably from the old
binary. — criterion 7

### 2. `tcw/work/projection.py`: the walker

`_json_safe(value)` alone, with no DTO around it yet: passthrough scalars,
non-finite floats to `str`, `bytes` to base64, mappings with a collision raise,
lists/tuples to arrays, `set` sorted with `key=str`, cycle detection by container
`id()`, everything else to `str`.

Tested against real `yaml.safe_load` output for every shape, not against
hand-built Python values — the point is what the loader actually produces.
— criteria 5, 6

### 3. `WORK_ITEM_SCHEMA` and `SCHEMA_VERSION`

The JSON Schema document: closed, every property required, `blocked_by` declared
for both the `slug` and `external` forms, `artifacts` pinned to `WORK_ARTIFACTS`.

Its test is criterion 3 — set equality against `fields(WorkItem)` plus `schema`
and `artifacts` — and that assertion is written **in this commit**, before
anything emits the document, so the schema is checked against the model rather
than against the projection that was written to satisfy it.
— criteria 2, 3

### 4. `work_item_json`

Assemble the DTO from `WorkItem` and a `Sequence[Artifact]`, running
`capabilities` and `blocked_by` through the walker. Pure; no store, no I/O.

Validate the emitted document against `WORK_ITEM_SCHEMA` in the test with
`jsonschema`. Add `jsonschema` to the `dev` extra in `pyproject.toml` in this
commit — runtime `dependencies` stays `["PyYAML>=6"]`.
— criteria 1, 4

### 5. `tcw work show --json`

The flag, `json.dumps(dto, indent=2, sort_keys=True, allow_nan=False)`, and the
error boundary: projection or encoding failure caught at the CLI, named on
stderr, exit 1, nothing on stdout.

The non-`--json` branch is not restructured. Run task 1's baselines here.
— criteria 1, 7, 11

### 6. Move `serve`'s five work-item call sites

`serve/__init__.py:632`, `:789`, `:820`, `:843`, `:994` → `work_item_json`.
`_jsonable`/`_json_bytes` stay for taxonomy and capabilities.

Criterion 8's test walks each response for item objects and asserts `schema` on
every one, so a missed call site fails here rather than in a browser. Criterion 9
pins the detail payload's key set.
— criteria 8, 9

### 7. Run the web suites

`pnpm test` and `pnpm test:e2e` unmodified against the new payload. If either
fails, the superset assumption was wrong and that is a finding, not a fixture to
edit. — criterion 10

### 8. Documentation Sync

Predicted triggers, all expected to fire:

- **`README.md` [Public-API]** — `--json` in the command table, and a short
  description of the document with its `schema` key.
- **`docs/release-notes/upcoming.md` [Public-API]** — reading a work item as
  JSON, in plain language. Names the `set` rendering change.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — the module, the schema,
  the `serve` migration, the `dev` extra, the collision refusal.
- **`skills/tcw-work/references/commands.md` [Skill-Driven-Component]** —
  `--json` alongside `show`. The router itself has a line budget and does not
  need to mention this.

### 9. Capability ledger

`work/read-a-work-item` is **changed**; update its description and declare it in
`capabilities.yaml`. No new capability: reading an item as JSON is the same
capability in another format, not a different thing a user can do.

## What could go wrong

- **The web suites fail on the superset.** Then the "same field names, plus two"
  assumption is false somewhere and task 6 needs a different shape. This is why
  task 7 is a task and not an afterthought.
- **Criterion 3 fails immediately** on fields nobody meant to publish —
  `worktree` and `branch` are filesystem-flavored. They are `WorkItem` fields and
  `serve` already ships them, so they are declared rather than filtered; filtering
  would be a second contract.
- **The collision refusal fires on a real repository.** It should not — capability
  blobs are string-keyed mappings — but if it does, it fires here first, on this
  repo's own items, which is the cheapest place to find out.
