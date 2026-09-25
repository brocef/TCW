# Update the web app's npm dependencies to clear the open Dependabot alerts

GitHub reports 72 open Dependabot alerts on `main` (2 critical, 38 high, 26 moderate,
6 low). All of them are npm packages behind `tcw serve`'s web app: direct ones
(vitest, vite, fastify, react-router) and transitive ones (fast-uri, js-yaml,
browserslist, playwright, postcss, @vitest/mocker). fastify and react-router are
bundled into the committed `tcw/serve/dist/`, so their fixes reach users only
through a rebuilt bundle and a release.

Raise each package to its first patched version within its current major
version, rebuild the bundle, and leave any fix that needs a new major version
(vitest 3 → 4) as a separate decision.

## Origin

The Dependabot summary GitHub printed when v2.6.1 was pushed on 2026-09-24; the
user asked for as many of the alerts as possible to be fixed.

## References

- https://github.com/brocef/TCW/security/dependabot — the alert list
- Open Dependabot PRs #60–#64 and #48–#55 — overlap with this change and can be closed once it lands
