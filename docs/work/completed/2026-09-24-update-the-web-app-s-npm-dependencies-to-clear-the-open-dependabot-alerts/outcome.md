# Outcome

Done overnight on 2026-09-24, with the user's permission to make clear, obvious
fixes. The request, spec and plan stages were skipped: the change is version bumps
and one test-type fix, and the intake says what it is.

## What changed

- `f81602ed`: every package with an open alert was raised to a patched release
  in its current major version. The lockfile was refreshed, and the bundle in
  `tcw/serve/dist` was rebuilt, because fastify and react-router are bundled into
  it. The new versions:
  - fastify 5.12.5
  - react-router 7.18.4
  - vite 7.3.6
  - vitest 3.2.7
  - @playwright/test 1.55.1
  - transitive packages: fast-uri 3.1.8 / 4.2.1, js-yaml 4.3.2, browserslist
    4.29.1, postcss 8.5.28
- `0f5b8a15`: vitest was moved to 4.1.11. The medium-severity alert on vitest
  and @vitest/mocker has no fix in the 3.x line. This is a major-version bump,
  but only of a development tool: the shipped bundle is unchanged. One test's mock
  type needed changing. Reverting this one commit puts vitest back on 3.2.7 if
  it is unwanted.
- `a3321d8d`: changelog and release-note entries.
- `prettier` rose from `^3.9.6` to `^3.9.9` as a side effect of `pnpm update`.

## Checks

These were run locally, on Node 24.17:

- `tsc --noEmit` passes, and so does `pnpm lint`.
- vitest passes: 67 of 67.
- `pnpm check:build` passes: the committed bundle matches a fresh build.
- The Python tests matching `serve`, `web` or `dist` pass: 234 of 234.
- The rest of the Python suite was not rerun, since this change touches no
  Python code.

`pnpm prettify:check` fails on 308 files both before and after this change.
That is the existing item "Make pnpm prettify:check pass on a clean checkout"
(TCW-42).

Playwright end-to-end, with screenshot comparison off:

- 12 of 14 tests pass.
- The other two fail the same way on the previous commit, so this change did not
  cause them. The previous commit is `c1167317`, with its lockfile and bundle.
  - "searches references and surfaces targeted validation warnings" fails on a
    `toContainText`.
  - "edits lifecycle artifacts and preserves a draft across a stale write" gets
    `# spec` back where `Updated specification` was expected.
- With screenshots on, the theme test's screenshot comparison sometimes passes
  and sometimes fails, on either version.
- CI does not run these tests.

Getting a browser for Playwright 1.55.1 needed a workaround.
`playwright install chromium` downloads, then hangs while unpacking under
Node 24. The headless shell was fetched with curl into
`~/Library/Caches/ms-playwright/chromium_headless_shell-1193` instead.

## Left open

- Open Dependabot PRs overlap this change: #60–#64 and #48–#55.
  - Dependabot closes a security PR once its alert is fixed on `main`.
  - Close the rest by hand, or let their next rebase show them as empty.
- The major bumps Dependabot proposes do not fix any alert:
  - vitest 5 (#54)
  - eslint-plugin-react-hooks 7 (#53)
  - globals 17 (#52)
- Whether to fix or drop the two failing end-to-end tests, and the unstable
  screenshot, is a separate question.
