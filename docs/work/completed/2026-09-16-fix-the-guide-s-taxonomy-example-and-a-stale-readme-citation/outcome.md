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
4. **Code review fixes** — `docs/guide/work.md:236` registers `cli` as well, so
   `--tags bug,cli` at `:239` runs; the guide's multi-valued example uses
   `Subject=invoice,user`, which reads more naturally for downloading an invoice.
   Spec gains problem 3 and criterion 5; changelog entry extended.

## Evidence

- Criterion 1: every `tcw taxonomy` line of the taxonomy block (except `extends`)
  and every `tcw capabilities` line of the 70-87 block — 24 commands — run in file
  order in a fresh `git init` + `tcw init --id demo` directory, each with standard
  input closed: all exit 0. The same run against `HEAD~` of the guide fails four:
  `Permission -p admin`, `--vocab user`, `show admin/permission`, and
  `Subject=invoice,billing`.
- Criteria 2-3: `git grep -n README tcw/` no longer returns either comment.
- Criterion 5: `tags add bug cli tech-debt`, `tags rm tech-debt`, `new "Login crash" --tags bug,cli` and `list --tags bug,cli` all exit 0 in a fresh project; before the fix `new` refused with "unregistered tag 'cli'".
- Criterion 1 re-run after the `Subject` change: 24 of 24 exit 0.
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
  are recorded in the spec. **That sweep was not repo-wide**, although this
  section first said nothing else was found: it ran taxonomy and capabilities
  examples only. Code review found a fourth refusal of the same kind in
  `docs/guide/work.md` (an unregistered tag), now fixed. The reviewer also ran the
  other guides' concrete examples and found nothing further; `work.md:279`
  (`--blocks downstream-slug`) refuses but sits in a placeholder reference block,
  which the spec leaves out.

## Autonomous decisions

Run unattended under `autonomous-work`; these replace the human checkpoints.

- **Compress the plan?** No advisor consulted — a two-edit change with no open
  question. Chose a short plan written on `main`, no worktree.
- **Widen scope to the sibling defects the spec sweep found** (`--vocab user`,
  `Subject=…,billing`, the `fs.py:290` citation)? No advisor consulted: the spec
  stage's rule makes the sibling sweep repo-wide by default, and all three are the
  same one-line kind. Included.
- **Code review, finding: `docs/guide/work.md:239` registers no `cli` tag.**
  Accepted after reproducing it; folded in as the same defect class.
- **Code review, finding: `outcome.md` overstated the sweep.** Accepted; corrected.
- **Code review, suggestion: `Subject=invoice,user`.** Accepted — reads naturally,
  and `-p` already shows the path form.
- **Code review, note: `work.md:279` `--blocks downstream-slug` refuses.** Rejected
  for this item: that block is placeholder syntax (`$slug`, `some-slug`), which the
  spec leaves out.
- **Verify decision:** accept. `tcw-verifier` reported all four criteria met on
  `c4652143`; criterion 5 and the re-run of criterion 1 after the review fixes were
  checked by hand (see Evidence). The review fixes touch only guide text, so the
  3605-test run at `8822ca20` still stands for code.
