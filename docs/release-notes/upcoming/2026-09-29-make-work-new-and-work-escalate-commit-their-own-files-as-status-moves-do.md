## Improvements

- **Creating work now commits it**, the way moving it always has.
  - `tcw work new`, `tcw work inbox accept`, and items filed from the web app
    each make one commit holding just the new item.
  - `tcw work escalate` and `tcw work delegate` commit the request in the
    project that receives it.
  - Nothing else in your working tree is swept in, so a staged file of yours
    stays staged.
  - If a commit is refused, the item is still created and you are told to
    commit it yourself.
  - `work.auto-commit-transitions: false` turns this off, as it does for
    transitions.
