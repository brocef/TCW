# Outcome: Fix the guide's taxonomy example and a stale README citation

## What shipped

1. **The guide's examples run** — `756c2ff8`.
   `docs/guide/taxonomy-and-capabilities.md` adds `tcw taxonomy add Admin "Running
   the service."` before `Permission -p admin`, `tcw taxonomy add User "A person who
   signs in."` before the `--vocab user` feature, and changes the multi-valued
   example to `Subject=invoice,admin/permission`.
2. **Two comments cite the guides** — `8822ca20`. `tcw/store/fs.py`'s retention
   comment names `docs/guide/work.md`, "What happens to resolved work"; the
   `unreachable_parent` docstring names `docs/guide/multi-repo.md`.
3. **Documentation Sync** — `134fe549`. `docs/changelogs/upcoming.md` gains a
   `Fixed` line for the guide and an `Internal` line for the comments. Release
   notes, README, `jira.md`, skills and `configure` references: no trigger fired.

## Evidence

- Criterion 1: every `tcw taxonomy` line of the taxonomy block (except `extends`)
  and every `tcw capabilities` line of the 70-87 block — 24 commands — run in file
  order in a fresh `git init` + `tcw init --id demo` directory, each with standard
  input closed: all exit 0. The same run against `HEAD~` of the guide fails four:
  `Permission -p admin`, `--vocab user`, `show admin/permission`, and
  `Subject=invoice,billing`.
- Criteria 2-3: `git grep -n README tcw/` no longer returns either comment.
- Criterion 4: the README's taxonomy block (`README.md:306-309`) runs cleanly,
  unchanged.
- `pytest -q -x`: 3605 passed in 966s.

## What the plan or spec got wrong

- **My first run of criterion 1 was false evidence.** It read commands from a
  file in a `while read` loop, and `tcw taxonomy add Permission -p admin` has no
  description argument, so it read its description from standard input and
  consumed the rest of the file. The loop reported success after three commands.
  Found because the capability the block creates was missing afterwards. The
  plan's proof step did not say to close standard input; the evidence above is
  from the corrected run.
- The spec's scope grew during the sibling sweep from one broken line and one
  comment (the request) to three broken lines and two comments. Both additions
  are recorded in the spec; nothing else was found in the repo-wide sweep.
