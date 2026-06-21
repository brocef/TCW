# CLI — capabilities

## Scaffold the doc trees
**Status:** Supported
**Subject:** node

As a user, I run `tcw init [taxonomy|capabilities|work]` inside a git repo to scaffold the `docs/<component>/` trees (all three by default), or the per-component mirror `tcw <component> init` (e.g. `tcw work init`) to scaffold just one. Either form refuses outside a git work-tree and reports each directory it created.

## Check the installed version
**Status:** Supported
**Subject:** cli

As a user, I run `tcw --version` to print the installed `tcw` version.

## Use shorthand to read an item
**Status:** Supported
**Subject:** cli

As a user, I type `tcw taxonomy <path>` or `tcw capabilities <id>` and it resolves to the `show` subcommand, so reading an item is one word shorter.
