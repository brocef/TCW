# Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

A TCW project can currently hold three config files: the node-root
`tcw-config.yaml`, plus a config file inside each tree store — `config.yaml` in
the taxonomy store and `.config.yaml` (a dotfile) in the capabilities store.
There is no apparent reason a project needs more than one config file, and the
split makes the configuration surface harder to find and to explain.

Move what those files hold into `tcw-config.yaml`, under the `taxonomy:` and
`capabilities:` sections that already exist there for `path` and `repository`,
and stop writing the per-store files.

## What is actually in scope

The per-store configs hold exactly one key: `extends`, a list of registered
project IDs the component inherits from.

- `FsTaxonomyStore.CONFIG_NAME = "config.yaml"` — `tcw/store/fs.py:1864`
- `FsCapabilitiesStore.CONFIG_NAME = ".config.yaml"` — `tcw/store/fs.py:2357`
- Written only by `extends_add` / `extends_remove` (`tcw/store/fs.py:2076-2110`
  and `2809-2838`), reached from `tcw taxonomy extends add|rm` and
  `tcw capabilities extends`.
- Read only by `_extends_ids` (`tcw/store/fs.py:1235`) via
  `_extended_component_stores` (`tcw/store/fs.py:1306`).
- Both names are listed in `OWNED_YAML_NAMES` (`tcw/store/fs.py:1154`) and
  taxonomy's is in `_TAX_RESERVED` (`tcw/store/fs.py:1841`); both are validated
  by each store's `check()`.

## The question the spec has to settle

This is a behavior change, not only a file move. A tree store may live in a
different Git repository and be shared between projects
(`taxonomy.repository` / `capabilities.repository`). Today `extends` travels
**with the store**, so every project reading that store inherits the same
ancestors. Moved to `tcw-config.yaml`, `extends` travels **with the project**,
and each project declares its own inheritance. Decide which is intended and say
so, because it changes what a shared store means.

Also to settle: what a project holding an old per-store config should do on the
next upgrade. The precedent in this code is to fail closed with a message
naming the new location rather than migrating silently — see the legacy
`extends` map refusal at `tcw/store/fs.py:1239` — paired with a migration guide
under `docs/`.

## Origin

A direct chat request from Brian on 2026-09-19: "I want to migrate the
`config.yaml` files in the taxonomy and capabilities folders into the root
`tcw-config.yaml`. I see no reason why we'd need more than one config per TCW
project."

## References

- `skills/configure/references/projects.md:88-97` — the current documented rule,
  which states outright that neither `extends` list "lives in `tcw-config.yaml`".
  This item makes that paragraph wrong, so it has to be rewritten.
- `skills/configure/references/stores.md` — `<component>.path` and
  `<component>.repository`, the existing `taxonomy:`/`capabilities:` sections
  the migrated key would join, and the shared-store case that raises the
  question above.
- `docs/migration-guide-1.X-to-2.0.0.md` and its siblings — the shape a
  migration note for this has taken before.
- `2026-06-19-remote-extends-for-taxonomy` (discarded) — closed, not a match;
  it was about remote Git locators for `extends`, but it is the nearest prior
  thinking about this key.
- Roughly 25 references to these filenames across about 10 files under `tests/`,
  plus `evals/seed_fixture.py` and `tests/fixtures/lifecycle_baseline/capture.py`,
  which size the change.

No blockers: nothing tracked or in the inbox touches these files, and the
`extends` key is independent of the tracker and lifecycle work now in flight.
