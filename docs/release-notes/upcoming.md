# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

- **`tcw work new` no longer hangs when it is run by a script.** If the program
  that started `tcw` left its own input open — a shell wrapper, a CI job, a
  git hook — `tcw` used to wait forever for input that was never coming, and a
  batch of commands that each take a fraction of a second would simply never
  finish. It now creates the work item without intake and says so. The same fix
  covers `tcw work delegate`, `tcw work escalate`, `tcw taxonomy add`, and
  `tcw capabilities add`.
- **Piping text in still works exactly as before**, including when the program
  producing that text is slow to start. What changed is that if the text starts
  arriving and then stops partway, the command now stops with an error instead
  of quietly keeping the half it received — a partial document saved as the
  item's raw intake looks identical to one you wrote on purpose. Set
  `TCW_STDIN_TIMEOUT` to a number of seconds to wait longer, or `0` to never
  wait at all.
- **A lifecycle hook can no longer stall a transition by reading input it was
  never given.** Hooks now run with their input closed, so a hook that happens
  to read from stdin finishes immediately instead of consuming the text you
  piped in, or timing out and aborting the transition.

## New

- **Your project can now declare which documents must be kept in step with code
  changes**, in `tcw-config.yaml` rather than as a section of prose in your agent
  guide. Each entry names a file, when it needs updating, and what to write
  there. TCW checks the list for mistakes, and the planning and implementation
  steps now show the list to your agent directly instead of relying on it to go
  and find one.
- **`tcw work docs`** prints that list. It changes nothing and is safe to run any
  time; `--json` gives the machine-readable form.
- **If you declare nothing, nothing changes.** The planning and implementation
  instructions read exactly as before, word for word.

