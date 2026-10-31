# Implement round 4 — TCW-110

Answers the qa rejection of 2026-10-23 (qa run at `3e6868fc`). Built on the
branch `tcw110-fix`, made from `3e6868fc`, in the worktree
`.claude/worktrees/qa-110`, with the code under test run from its own virtual
environment (`.venv/bin/pytest`, `.venv/bin/tcw`). Hand runs of `tcw` and the
end-to-end runs were given their own `HOME`, `XDG_CONFIG_HOME`,
`XDG_CACHE_HOME` and `TMPDIR` under the scratchpad, with every `TCW_*`
variable unset. It gives no verdict.

## What was done, for each item the rejection asked for

- **The end-to-end tests name objects by full identifier** (plan Steps 4 and
  10). `web/e2e/parity.spec.ts` gains a constant `PROJECT`
  (`playwright-project`), used by `tcw init --id` and by every expected
  identifier:
    - the Feature field, after a suggestion is picked, holds
      `playwright-project.taxonomy/use-feature` (was `use-feature`, the qa
      failure at line 289), and the saved capability's `fields.Feature` is
      the same full identifier (was line 311);
    - the stage line's move hint is read from the board row's `full-id`
      (was `item.slug`, which the row no longer carries, line 392);
    - a link picked after typing `tcw://` is `tcw://playwright-project.work/<date>-…`,
      and the list offers `tcw://playwright-project.taxonomy/react-vocabulary`
      and `tcw://playwright-project.capabilities/react/native-client` (were
      `tcw://W/`, `tcw://T/`, `tcw://C/`, lines 497-498);
    - one more 3.x form the qa run never reached: the Blocked by field is
      given `other-project.work/2026-01-01-x` (was `other-project/2026-01-01-x`,
      which the client no longer reads as another project's item, so the
      warning the test expects never appeared).

    No other 3.x form is left under `web/e2e`: `jira.spec.ts` names items
    only by folder and the page's own text, and the `/work/<folder>` routes
    are folders by design (AC 20a). The `slug` fields left in
    `parity.spec.ts` (lines 242 and 252) and the taxonomy form's "Slug"
    field are the name a new taxonomy entry is created under, which the plan
    says need no change.

- **(a) `jira.spec.ts:92`, "This project's backend keeps the" not found.**
  The test was wrong. The client writes that sentence ("This project's
  backend keeps the request record.") inside the Request tab, and the stage
  tabs open on the item's own stage, which for the fixture's item is `spec`;
  a tab that is not chosen is not drawn, so the text was never on the page.
  The client's choice is the documented one (`WorkDocumentTabs`: the tabs
  open on the current stage). The test now chooses the Request tab, then
  checks the sentence and that the panel's "Open in Jira" link goes to the
  site.

- **(b) `parity.spec.ts:346`, "Tagged item" heading not found.** Two causes,
  one behind the other:
    - The setup appended `work.tags` to a root `tcw-config.yaml`, which
      TCW 4 does not read, so the `ui` tag was refused. It now appends to
      `.tcw/tcw-config.yaml`, which `tcw init` writes holding only
      `tcw-version` and `id`.
    - With the tag accepted the item was made, but the page stayed on
      "Select an entry.": a client defect. After a new item saved, the page
      asked "You have unsaved changes. Leave without saving?", because the
      form's unsaved flag, cleared just before, had not yet reached the
      `navigateTo` that the save called; a browser test dismisses the
      question, so the page never opened the item, and a person was asked
      to discard what was already saved. `navigateTo` (`web/client/src/ui/app.tsx`)
      takes a third argument, `saved`, which skips the question, and the new
      item form's `onCreated` passes it. Test:
      `a saved new item opens its page without asking about unsaved changes`
      (`web/client/src/ui/app.test.tsx`).

- **(c) The screenshot baselines.** Regenerated with
  `--update-snapshots -g "applies and persists light"`, the one test that
  takes screenshots, after every other fix. All three images it keeps
  changed (`shell-system-dark`, `shell-explicit-light`,
  `settings-responsive`); the old ones showed the 3.x shell (a "Status"
  filter, "+ Create Work", a fixture item). Each new image was looked at: the
  heading `TCW · playwright-project`, the Stage (9), Tags and Assignee
  filters, "+ New item", "No work entries.", in dark, in light, and at
  720 pixels wide with the Appearance menu open on System.

- **`tcw init --work-path TCW://…` in capitals.** `run_init`
  (`tcw/cli.py`) matches the `tcw:` scheme in any case (`casefold()`), as
  URL schemes are matched. By hand, `tcw init --id rr --work-path TCW://ws.path/board`
  exits 2 with the same refusal as the lower-case form and writes nothing.
  Test: `test_init_refuses_a_store_location_given_as_an_address`
  (`tests/work/test_init_provision.py`) runs `tcw://`, `TCW://` and `Tcw://`
  for each of the three path options; before the change it failed on
  `TCW://` for all three (`3 failed`, exit 0 and `wrote .tcw/tcw-config.yaml`),
  after it `7 passed`.

## Found on the way, fixed in this round

Once the tests above passed, three more failures appeared in tests the qa
run had not reached; each was run until it was understood.

- **`jira.spec.ts:129`**, files stay editable while Jira is down: after
  saving the spec, the page came back on the Request tab. With Jira
  unreachable the item's stage is unknown, so the tabs open on the first
  one, and the item page is drawn afresh when the editor closes. A client
  defect, the same with Jira reachable whenever the file edited is not the
  current stage's: the page came back on a tab other than the one the file
  was opened from. The app now remembers the stage of the file last opened
  in the editor (`fileStage`, cleared by `navigateTo`), and `WorkPage` opens
  that stage's tab (`TWorkPageEditing.openStage`). Test:
  `coming back from a stage file's editor shows that stage's tab`
  (`app.test.tsx`). Both new client tests fail against `3e6868fc`'s
  `app.tsx` and `work-views.tsx` and pass with the change.
- **`parity.spec.ts`, "edits properties"**: the priority scale now has
  `highest`, so the option named "high" matched two; the test asks for the
  exact name.
- **Three races in `parity.spec.ts`**, each failing about one run in three:
    - clearing the tag filter clicked a checkbox in a menu Escape had just
      closed; the test opens the menu again, clears the tag, and checks the
      board shows both items;
    - the declaration test read `capabilities.yaml` once the draft showed
      the entry, which it does before the save lands (the Save button reads
      "Saving..." meanwhile); it now waits for the form's note to go;
    - after a `tcw://` link is picked, the client moves the caret after it
      in the next animation frame, and typing that began first was split
      by the move (the failing run's editor held
      `…-plain-itemeact and tcw://r`); the test waits one animation frame
      before typing on.

## Checks run

- End-to-end, the whole suite with no flags, from the qa-110 root,
  `PATH=$PWD/.venv/bin:$PATH pnpm test:e2e --output=<scratch>` at
  `0221e22c`, run three times: `15 passed (11.0s)`, `15 passed (11.3s)`,
  `15 passed (11.5s)`, nothing failed and nothing "did not run". Before the
  three race fixes, six runs had two failures among them on the link test
  and one on the declaration test; after them, eight runs ignoring
  screenshots and the three above all passed.
- `pnpm test`: 15 files, `189 passed` (187 before, plus the two new tests).
- `pnpm exec tsc --noEmit`, `pnpm lint` and `pnpm check:build` pass at
  `0221e22c`; `pnpm exec prettier --check` passes over every TypeScript file
  this round changed.
- `tests/work/test_init_provision.py`, `tests/test_store_addresses.py`,
  `tests/test_init_configured_tree_path.py`: `56 passed in 9.56s`.

## Not done

- The full Python suite is the dispatching session's to run.
- Two qa observations were not asked for and are left as they are: a work
  item's page heading and Parent link show the folder while a capability's
  heading shows its full identifier, and the QA plan's
  `capabilities add … --name Export` and bare-list `projects:` are out of
  date.
- `store_location_problem` (`tcw/config.py`) still recognises only a
  lower-case `tcw://` in a configuration file; a `TCW://…` value there is
  read as a relative folder. The rejection asked only for `init`.

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it, at `b55205a9`
(2026-10-23), on the `tcw110-fix` branch: `5759 passed, 114 skipped in 589.80s`.
