# Make the plugin installable in Pi

Make TCW installable through Pi using its official package format. Preserve Claude Code and Codex compatibility. The user reports no expected blockers.

## Why

- **Without it:** Pi users have no documented supported installation path for TCW.
- **With it:** Pi users can install the shared skills with Pi's package manager.
- **Cost and risk:** Small packaging and documentation change; resource declarations or harness assumptions could break discovery.
- **Alternatives:** Local skill paths load but do not provide a documented Git package workflow.

## Origin

User request in chat, 2026-10-07, confirmed official format and compatibility requirements.

## References

- https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md — official format selected by the user.
