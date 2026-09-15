# Upgrade tcw serve to Fastify and React

Replace the browser-facing implementation behind `tcw serve` with a packaged
Fastify server and a Vite-built React client while preserving the command and
browser behavior users already rely on.

## Agreed direction

- Keep `tcw serve`, `--port`, and `--no-open` as the public command surface.
- Require Node.js 22.12 or newer for `tcw serve`; all other TCW commands remain
  Python-only.
- Run the existing Python API behavior in a private loopback sidecar and make
  Fastify the only browser-facing listener.
- Authenticate every sidecar request with a per-process random token passed to
  the packaged Node child through TCW-specific environment variables.
- Rebuild the client with Vite, TypeScript, React, and React Router Data Mode.
- Preserve the existing three-pane design and all browsing, editing, routing,
  filtering, revision-token, validation, and lifecycle workflows before making
  any visual or product redesign.
- Keep the application fully offline. Commit deterministic frontend/server
  build output as Python package data so installed users need Python and Node,
  but not pnpm, `node_modules`, or a build step.

## Compatibility constraints

- Keep all existing `/api/*` paths, JSON envelopes, status codes, revision
  behavior, size limits, and write semantics compatible.
- Do not change the abstract TCW store interfaces or duplicate their business
  logic in TypeScript.
- Preserve loopback binding, strict CSP, and Host/Origin protections.
- Retain the 1 MiB request limit.

## Scope boundaries

- This is a parity-first implementation migration, not a visual redesign or a
  hosted/multi-user server mode.
- Next.js is out of scope; its integrated rendering/runtime surface is not
  needed for this local client-rendered app.
- The existing `local-web-app` taxonomy Feature remains unchanged.
- The `web/editing` capability is an acceptance surface but does not itself
  change. The `web` capability changes only to document the Node runtime
  prerequisite.
- The separate rich Markdown editor backlog item remains out of scope.
- The existing live-browser-test backlog item should be absorbed by the new
  Playwright parity suite and proposed as superseded during closeout.

## Lifecycle boundary

Create and checkpoint the request, specification, and implementation plan, then
leave this item in backlog. Do not start implementation or cut a release as part
of this planning pass.

