## Personal configuration, and telling TCW who you are

You can now shape TCW to the way you work without changing what your team
gets. Two files hold your own settings, and neither is shared:

- **`~/.config/tcw/config.yaml`** (or `$XDG_CONFIG_HOME/tcw/config.yaml`)
  applies to every project you work in.
- **`tcw-config.local.yaml`**, beside a project's `tcw-config.yaml`, applies
  to that project only. `tcw init` adds `/tcw-config.local.yaml` to the
  project's `.gitignore`, and `tcw validate` warns if the file is tracked by
  version control anyway.

TCW reads its own defaults, then `tcw-config.yaml`, then the user-wide file,
then the local file; a later file wins.

- **What your files may set:** `user.name`, a stage's `prompt` and `post`
  lists, a procedure's list, and the names of the environment variables
  holding your Jira credentials. Anything else belongs to the team: a personal
  file that sets it is an error naming the file and the key, and every command
  stops on it until it is removed. Set `TCW_NO_PERSONAL_CONFIG=1` to run with
  neither file.
- **Add to a list instead of replacing it** with an `inherit: true` entry,
  which stands for the list the file below produced. `[{blob: "my note"},
  {inherit: true}]` puts your note above the team's instructions and keeps
  them.
- **`inherit: true` replaces `builtin: true`** in `tcw-config.yaml` too, where
  it stands for TCW's own text. Writing `builtin: true` is now an error that
  points to the migration guide.
- **`tcw config show`** prints the configuration a command actually runs
  with, all files merged. `tcw config show --origin` names the file each value
  came from and lists anything your files set that was not used; it still
  prints when something is wrong, so you can find the line to fix. A value
  under a key ending in `-env` that does not look like a variable's name is
  printed as `(value not shown)`, in case a token was pasted there.
- **Who you are.** Set `user.name` in either personal file; in a Jira project
  you are the account your credentials belong to. `tcw work list --mine` lists
  the items assigned to you, and `--assign-me` on `tcw work new` and
  `tcw work edit` assigns one to you. `TCW_WORK_OWNER` and your version
  control name are no longer read for this.
- **Your own files and scripts.** A `file:` path is read relative to the file
  that names it, and a command or script from any file runs with
  `TCW_CONFIG_DIR` set to that file's folder. When your files changed a
  stage's or procedure's text, `tcw work stage prompt` and `tcw work
  procedure` say so on stderr, and a failed `post` command names the file it
  came from.
