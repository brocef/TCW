# Outcome

Commit `36475443` changes only `web/e2e/parity.spec.ts` and one screenshot
baseline. The app code is unchanged; every failure was the test being out of
date or racing the page.

- **References test.** It expected a dangling "Superseded by" to save with a
  warning, but `c73abdb7` made that write a refusal. It now expects the refusal,
  clears the field, and saves.
- **Stale-write test.** It read the saved spec back straight after clicking Save
  and got the old content. With a 2-second pause, the spec check passed and the
  plan check failed the same way. The spec, plan and sidecar read-backs now use
  `expect.poll`.
- **`lifecycle-dialog` screenshot.** The baseline still showed the
  "version offered" checkbox, which `4cfdcaab` removed on purpose. Only that
  baseline was regenerated; `--update-snapshots` changed no other image.
- **Theme test screenshot.**
  - On slow runs the screenshot showed the real "Modified at" time. The helper
    had overwritten the times before the work list rendered.
  - The test now waits for `time.modified-at` before both page-load screenshots.
  - The proof: with `/api/work` delayed 1.5 s in the test, it passes with the
    wait and fails without it.
  - A version that kept rewriting the time with a MutationObserver was tried and
    dropped. It still failed with the delay, because the screenshot came before
    the list existed at all.

Checks:

- Full `pnpm test:e2e` passes: 14 of 14, in 3 runs after the final change.
- Typecheck and lint pass.
- The file passes prettier.

CI still does not run these tests.
