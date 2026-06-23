# CLI — capabilities

## Scaffold the doc trees
**Status:** Supported
**Subject:** node

As a user, I run `tcw init [taxonomy|capabilities|work]` to scaffold the `docs/<component>/` trees (all three by default) in the **current directory** and mark it a TCW node by writing a `tcw-config.yaml` marker, or the per-component mirror `tcw <component> init` (e.g. `tcw work init`) to scaffold just one. So `cd project-b && tcw init` makes `project-b/` its own node. Either form refuses outside a git repo and reports each directory it created.

## Check the installed version
**Status:** Supported
**Subject:** cli

As a user, I run `tcw --version` to print the installed `tcw` version.

## Use shorthand to read an item
**Status:** Supported
**Subject:** cli

As a user, I type `tcw taxonomy <path>` or `tcw capabilities <id>` and it resolves to the `show` subcommand, so reading an item is one word shorter.
