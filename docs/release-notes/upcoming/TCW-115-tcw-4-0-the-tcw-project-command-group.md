## Project commands move into `tcw project`

Everything about the project itself is now one command group, `tcw project`,
beside `tcw taxonomy`, `tcw capabilities` and `tcw work`:

| Before | Now |
| --- | --- |
| `tcw init` | `tcw project new` |
| `tcw projects list` | `tcw project list` |
| `tcw config show` | `tcw project config` |
| `tcw provision` | `tcw project provision` |

The old commands are gone. Typing one stops with a usage error (exit 2) that
names the command to use instead. Every message, help text and suggestion now
names the new commands, and a mistyped command offers a command that exists
where you typed it before the same word elsewhere, so `tcw work info` still
suggests `tcw work show`.

Two new commands join them. `tcw project path <id>` prints the folder of a
project on this machine, or says it is not here and how to fetch it.
`tcw project info` shows how the current project is put together: its parents
and children, the order its ancestors are read in, where each setting comes
from, where its stores are, and what it overrides, with `--json` for scripts.

`tcw project config --origin` now labels each value with the project, the
layer and the file it came from, such as `# core, project
/home/me/core/.tcw/tcw-config.yaml`, or `# app, environment TCW_USER_NAME__APP`,
or `# built-in`.

## `tcw project provision` fetches connected projects

`tcw project provision` fetches the projects your project is connected to that
are not on this machine, each from the repository its manifest entry gives and
into the folder that entry names, then the projects those name, in turn.
`tcw project provision <id>` fetches one project and the ancestors it needs;
`--component` fetches only stores and never a project; `--dry-run` shows what
the first round would fetch and contacts nothing.

It never overwrites anything. A folder that already holds files, or holds only
`.git` (a clone that stopped part way), is refused before any remote is
contacted, and each clone is made beside its destination, checked, and only
then moved into place, so a failure leaves nothing behind.

A manifest that is not your project's own, such as one in a parent you just
fetched, may place a clone only directly beside that project's repository,
never at or above your home folder and never inside a hidden folder below it.
This keeps a repository you have not read from choosing where on your disk
something is written. When a manifest asks for more, the command says so and
tells you how to place the project yourself.

A store whose `ref` names no branch, tag or commit now fails, where before it
could be read as a file name.
