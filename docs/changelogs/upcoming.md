# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Changed

- Web app npm dependencies raised to clear every open Dependabot alert: fastify
  5.6.1 → 5.12.5 and react-router 7.9.1 → 7.18.4 (both bundled into
  `tcw/serve/dist`, which is rebuilt); vite 7.1.4 → 7.3.6, vitest 3.2.4 → 4.1.11
  and @playwright/test 1.55.0 → 1.55.1 (development only). The lockfile refresh
  also moves the transitive fast-uri, js-yaml, browserslist and postcss to patched
  versions. `work-document-tabs.test.tsx` types its mock as
  `Mock<ComponentProps<typeof WorkDocumentTabs>["onReadArtifact"]>`, which
  vitest 4 requires.
