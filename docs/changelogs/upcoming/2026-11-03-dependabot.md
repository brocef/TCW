## Internal

- Web development dependencies: `minimatch` now resolves to 11.0.4 everywhere
  (it was 3.1.5 and 9.0.9), through a `pnpm.overrides` entry of `^11.0.1` in
  `package.json`, because ESLint 9 and typescript-eslint 8 ask for older ranges.
  This fixes the denial of service through globparts amplification in versions
  before 11.0.1 (Dependabot alert 89).
- Web development dependencies: `vitest` moves from 4.1.11 to 4.1.12, which
  brings `@vitest/mocker` to 4.1.12. This fixes code injection through
  unauthenticated manual mock registration (Dependabot alert 88) and the Windows
  backslash path traversal that got around the redirect allowlist (Dependabot
  alert 87).
