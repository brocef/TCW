# Tracker sync for capabilities

## Product changes

## Technical changes

## Meta changes

Potential capability-metadata synchronization with an external tracker. This is
a theoretical placeholder, not implementation-ready work.

**Activation condition:** a concrete consumer requests this integration and can
name the first provider, the records to synchronize, and which system owns each
field. Do not write a specification or start implementation before that exists.

The first specification must cover one provider and define:

- sync direction and field-level authority;
- the `Tracker` field's cardinality and reference syntax;
- provider configuration, authentication, and permission boundaries;
- conflict, drift, retry, idempotency, and partial-failure behavior;
- observable acceptance criteria for the concrete consumer.

Additional Jira, GitHub, or Linear adapters remain later extensions, not part of
the first delivery by default.

**Format note (refreshed 2026-07-23):** the original request said `**Tracker:**`,
the Markdown-bold field syntax from phase-3. Capabilities are now folder nodes and
the field lives as a `Tracker` key in `meta.yaml` (still a recognized field —
`tcw/store/base.py`). The historical `<shortname>:<id>` convention is an input
to reconsider, not a settled contract: the current store recognizes the field
name but does not parse or validate that syntax.

Spec: docs/plan/phase-6-beyond.md; phase-3-capabilities Part C #4.
