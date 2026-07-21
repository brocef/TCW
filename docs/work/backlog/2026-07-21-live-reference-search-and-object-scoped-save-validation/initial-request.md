# Live reference search and object-scoped save validation

## Product changes

- Add live, accessible object search to structured reference fields in the local web editor while preserving free-form entry and canonical stored identifiers.
- Validate each created or saved TCW object immediately with the same rules used by `tcw validate`, surfacing findings as post-save warnings without turning a committed mutation into a failed save.
- Keep `web/editing` Supported and update its description to cover reference search and immediate validation.

## Technical changes

- Rank candidates already loaded by the React client; do not add a search endpoint.
- Add a storage-neutral `ValidationTarget` selector and object-scoped component checks, preserving full-node and path-scoped validation and the public CLI.
- Validate every web create, structured edit, lifecycle artifact save, and sidecar save against the canonical object returned or resolved by the mutation.
- Rebuild committed browser assets and cover search, accessibility, scoped validation, warning behavior, and browser flows.

## Meta changes

- Track the product change against `web/editing`; the existing `local-web-app` Feature remains sufficient.
- Update the README web-editor documentation, upcoming release notes, and technical changelog.
- Preserve request payloads, stored identifiers, URLs, and public CLI behavior.

