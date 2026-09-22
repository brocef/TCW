# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Strict mode needs one more setting

- **Breaking change for projects that set `strict: true`.** Strict mode now needs
  `work.tracker.exclusive-claim-transition`. Until it is set, `tcw validate`
  reports it missing, and every command strict mode checks refuses and tells you to
  run `tcw validate`. Projects that do not use strict mode are not affected.
- **Why.** Strict mode promises that only one person can take a ticket. A claim
  keeps that promise only by applying a transition your workflow will not apply to
  a ticket someone has already taken, so strict mode now insists you name one.
- **What to set.** The transition your workflow uses to take a ticket into work,
  one it will not apply to a ticket already taken:

  ```yaml
  work:
    tracker:
      strict: true
      exclusive-claim-transition: Start Progress
  ```
- **What it costs.** With it set, `tcw work tracker claim` applies that transition,
  so claiming a ticket moves it.
