# Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

A TCW project should have **one** config file, not three.

Today it can have three: the node-root `tcw-config.yaml`, plus a config file
inside each tree store — `config.yaml` in the taxonomy store and `.config.yaml`
in the capabilities store. Brian sees no reason a TCW project needs more than
one config, and asked that the two per-store files be migrated into
`tcw-config.yaml`.

In his words, on 2026-09-19:

> I want to migrate the `config.yaml` files in the taxonomy and capabilities
> folders into the root `tcw-config.yaml`. I see no reason why we'd need more
> than one config per TCW project.

## What the requester decided

Two questions were put to him during this stage, because each changes what the
work is rather than how it is done.

**Inheritance belongs to the project, not to the store.** A tree store may sit
outside the project and be shared by more than one project, and `extends` — the
only key those per-store files hold — currently travels with the store, so
every project reading it inherits the same ancestors. After this change it
travels with the project: each project declares its own `extends` in its own
`tcw-config.yaml`, and two projects sharing one store may inherit differently.
That is the intended outcome, not a side effect to be worked around.

**An existing per-store config may simply stop working.** Asked what should
happen to a project that upgrades with `docs/taxonomy/config.yaml` or
`docs/capabilities/.config.yaml` still on disk, he chose the plainest answer:
the old file is ignored, with no warning, no refusal and no automatic
migration. Such a project loses its inherited terms until someone moves the key
by hand.

This was put to him twice. This repository has a standing rule that new TCW may
drop support for old TCW reading new data, but must still read old *files*; the
choice contradicts it. He confirmed the choice and set the rule aside for this
item. Treat the override as settled and do not reopen it at `spec`.

## Out of scope

- The `work` store. Only the taxonomy and capabilities per-store configs were
  named, and the work store has no config file of its own.
- Changing what inheritance *does*, or how `extends` resolves. This is about
  where the key is written and read, not about federation behavior.
- Remote or URL-based `extends` locators — that was a separate idea, since
  discarded.

## Notes

- The requester was asked for reference material and said what is already in
  the repository is enough. The `## References` section below is therefore the
  material found during intake rather than material he supplied.
- The request is small enough to be one item. The per-store configs hold
  exactly one key between them, and no other configuration lives in either
  file.

## References

- `tcw/store/fs.py` — `FsTaxonomyStore.CONFIG_NAME` (line 1864) and
  `FsCapabilitiesStore.CONFIG_NAME` (line 2357) name the two files; `extends`
  is written by `extends_add`/`extends_remove` and read by `_extends_ids`
  (line 1235) through `_extended_component_stores` (line 1306). This is the
  whole read/write surface the change has to move.
- `skills/configure/references/projects.md:88-97` — the documented rule today,
  which states outright that neither `extends` list lives in `tcw-config.yaml`.
  This change makes that paragraph false, so it must be rewritten.
- `skills/configure/references/stores.md` — the existing `taxonomy:` and
  `capabilities:` sections of `tcw-config.yaml` (`path`, `repository`) that the
  migrated key would join, and the shared-store case behind the first decision
  above.
- `tcw/store/fs.py:1154` (`OWNED_YAML_NAMES`) and `tcw/store/fs.py:1841`
  (`_TAX_RESERVED`) — two registries that name the old filenames and will need
  revisiting.
- Roughly 25 references to the two filenames across about ten files under
  `tests/`, plus `evals/seed_fixture.py` and
  `tests/fixtures/lifecycle_baseline/capture.py` — the size of the change
  outside `tcw/`.
