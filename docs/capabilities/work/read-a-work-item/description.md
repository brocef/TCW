As a user, I run `tcw work show <slug>` to read an item's record: its slug, title, stage, created date, priority, effort, complexity, tags, assignee, parent, what blocks it and what it blocks, its children, and its folder. The slug may be the full `<project-id>/<folder>` or just the folder name, matched exactly. Plain `show` prints one `key: value` line per field; `--json` prints the same record as JSON, the same shape each entry of `tcw work list --json` takes. An item from another project is read through that project.

An item whose `item.yaml` cannot be read — not valid YAML, an unknown key, a missing title, a value of the wrong kind — makes `show` exit 1 naming the file and the key. One unreadable item does not stop me reading another: `show` still prints the readable item, works out its blocks and children from the items it can read, and says on stderr which file it could not.

`tcw work path <slug>` prints the item's folder; `tcw work path <slug> <stage>` prints the stage's document or folder in it; `--next` names the next numbered round of a stage that loops, and `--handoff` the path for a note to whoever resumes the stage. None of them writes anything. `tcw work path` with no slug prints the work store's folder.

Errors keep stdout empty and exit non-zero — 4 for an item that does not exist — so piping into `jq` fails cleanly rather than on a fragment.
