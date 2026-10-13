As a user or agent, I run `tcw work show <slug>` to read everything about an item in one go. I name it by its full slug (`<project-id>/<folder>`), by its folder name alone, or, when the project keeps its items in Jira, by its ticket key — matched exactly.

The text form prints, in order: one `key: value` line per field of the item's record — its slug, title, stage, created date, priority, effort, complexity, tags, assignee, parent, what blocks it and what it blocks, its children, and its folder; then a blank line and `request:` followed by what the item asks for, indented by two spaces (or `request: none`); then, when there are any, a blank line and `comments:`, followed by every comment, newest first, each as a line `- <time> <author>` with its text indented below. An agent that wants only the latest comment reads up to the second `- ` line. In Jira mode people are shown by display name.

`--json` prints `{"schema": 1, "item": {...}, "request": ..., "comments": [...]}`: the record (the same shape each entry of `tcw work list --json` takes under `"items"`), the request text or `null`, and the comments newest first, each with `at`, `author` and `text`. In Jira mode it carries account IDs rather than display names. An item from another project is read through that project.

An item whose `item.yaml` cannot be read — not valid YAML, an unknown key, a missing title, a value of the wrong kind — makes `show` exit 1 naming the file and the key. One unreadable item does not stop me reading another: `show` still prints the readable item, works out its blocks and children from the items it can read, and says on stderr which files it could not.

`tcw work path <slug>` prints the item's folder; `tcw work path <slug> <stage>` prints the stage's document or folder in it; `--next` names the next numbered round of a stage that loops, and `--handoff` the path for a note to whoever resumes the stage. None of them writes anything. `tcw work path` with no slug prints the work store's folder.

Errors keep stdout empty and exit non-zero — 4 for an item that does not exist — so piping into `jq` fails cleanly rather than on a fragment.
