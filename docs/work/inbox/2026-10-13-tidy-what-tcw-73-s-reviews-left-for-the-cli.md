# Tidy what TCW-73's reviews left for the CLI

Separate-change findings from TCW-73's verify review (2026-10-13). Each was
already true before TCW-73; none blocks the epic.

1. **`tcw capabilities reset` deletes local capabilities nested inside the
   override folder.** Inherit `auth/login`, override it, add
   `auth/login/nested`, then `reset auth/login`: the nested local capability is
   removed with no refusal. `reset` calls `_rm` on the override folder with no
   nested or referrer check (`tcw/store/fs.py`, `reset`). It should refuse as
   `rm` does.
2. **`--slug` is not checked.** `tcw taxonomy add --slug 'A B'` creates a
   folder named `A B` and exits 0. TCW-73's Design 4 lists a malformed slug as
   a usage error (exit 2).
3. **The scan for git commands that change state is incomplete**
   (`tests/work/test_git_write_scan.py`). Its verb list lacks `switch`,
   `restore`, `rebase`, `cherry-pick`, `update-ref`, `update-index`, `init`
   and `branch`; a `-c key=value` option would be read as the verb; the
   `FsStoreProvisioner: checkout` allowance covers the whole class rather than
   `_obtain`; and nothing checks that `status` keeps `--no-optional-locks`.
   Nothing in the code uses any of these gaps today.
4. **`tcw provision` can still ask for a password.** Git asks for HTTPS
   credentials and SSH passphrases on the terminal, not on standard input, so
   a private remote can prompt even though standard input is closed. Setting
   `GIT_TERMINAL_PROMPT=0` (and `BatchMode=yes` for ssh) in the environment
   `_git` passes would stop it. Suspected from reading the code, not run.
5. **This repository's implement-stage instructions name code that no longer
   exists.** `docs/lifecycle/implementation.md` names `descendant_nodes` and the
   2.x `--include-descendants` flag. The text is composed into
   `tcw work stage prompt implement`.
6. **`tests/test_upstream_projects.py` runs whatever `tcw` is first on PATH.**
   With the shared pyenv shim first, ten tests fail with a 2.x message. It
   should run the `tcw` of the interpreter under test (`sys.executable -m tcw`
   or the same folder's script).

7. **`list` and `rm` disagree about a sub-folder with no `meta.yaml`.**
   `_local_slugs` (`tcw/store/fs.py`) counts any readable folder as a term, so
   `taxonomy list` shows `invoice/sub`; but `rm invoice` treats it as part of
   `invoice` and deletes it (naming each file) when nothing refers to it.
   TCW-73 Design 8.2 defines a nested term by its `meta.yaml`, so `list`
   should probably agree.
8. **The retired-key message names a bare `tcw-config.yaml`.** Run from a
   sub-folder such as `p/docs`, `refuse_retired_config` names a file that is
   not in the current directory. It should name the path from the project root.
9. **`tcw work list` does not notice a child project's retired key.** The
   parent's own key is refused by every command, and `projects list`,
   `provision`, `taxonomy list` and `validate` refuse a child's; `work list`
   never opens the registry, so it exits 0.

Already assigned elsewhere, listed so they are not lost: `tcw serve` prints
`Serving TCW at <url>` rather than only the URL and never flushes standard
output, so a piped URL arrives only when the server exits (TCW-77); the
`review` and `qa` built-in prompts (TCW-74).
