As a user, I run `tcw taxonomy list` to see every entry's qualified path, one per line, local and inherited alike; `--local` leaves out inherited entries. `--json` prints `{"schema": 1, "terms": [...]}`, giving each entry's path, name, kind (`Vocabulary` or `Feature`) and origin (`local` or the project it is inherited from).

Only a folder holding `tcw-taxonomy.yaml` is a term; a folder with none groups terms and is never listed.
