## Fixes

- `tcw work delegate` to a connected project that keeps no board of its own now
  says so and names the projects below it that do, instead of claiming there is
  no such child. If that project's board is declared but not fetched on this
  machine, it says that instead.
