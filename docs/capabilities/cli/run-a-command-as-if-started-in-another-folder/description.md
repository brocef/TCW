As a user, I put `-C <folder>` before any command, as in `tcw -C <folder> work list`, to run it as if I had
started it in that folder, as `git -C` does: the project found from there is
the active project, with its own configuration, checks and hooks. `-C` may be
given more than once, each relative to the one before. In place of a folder I
can give a folder address, `tcw://<id>.path/<folder>` or
`tcw://<id>.<namespace>.path/<folder>`, which TCW resolves from the project I
am in; an object's address is refused, naming the path form. A folder that is
not there is a usage error (exit 2) before anything is read.

This is how a part of an epic is made in another project:
`tcw -C tcw://<id>.path/ work new "<title>" --parent <epic>`. It replaces
TCW 3.x's filing into another project with `--project`, whose capability record
is removed.
