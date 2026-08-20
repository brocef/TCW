# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Running outside a Git repository tells you so, and changes nothing

TCW has always needed Git to write and never needed it to read. But only
`tcw init` said so. Every other write — `tcw work new`, `tcw work start`,
`tcw taxonomy add`, `tcw capabilities set`, and the rest — printed a Python
traceback instead, and several of them printed it *after* half the work was
done: `tcw work new` left an item folder holding nothing but its state file,
`tcw taxonomy add` left the whole term, and `tcw work start` moved the item into
`active/` and then failed, so the item had moved and nothing told you.

Now every write says the same sentence, exits the same way, and leaves the
project exactly as it found it:

    tcw work new: not inside a git repository. Run `git init` first.

Reading is unaffected — `tcw work list`, `tcw work show`, `tcw validate`,
`tcw taxonomy show` and the rest print exactly what they always printed.

Two smaller things came with it. `tcw work delegate` and `tcw work escalate`
used to appear to work outside a repository, dropping a request into the other
project's inbox that nothing tracked and that project could never accept; they
now refuse up front. And when Git itself fails for some other reason — a lock
left behind by another process, a hook that says no — you get one line naming
the command that failed instead of a stack trace.

In the local web app, a save the store refuses now comes back as that refusal
in plain words, rather than a server error, and nothing is written.

If your work store lives in a different repository from your code — the
`work.path` setting — three commands used to get this half right, because they
write to *both* repositories and only checked one. Starting an item with
`--worktree` would move it to active and edit your `.gitignore` before failing;
completing a worktree item whose code repository had gone missing would report
success while quietly skipping the merge-back, leaving the work branch
unmerged; and pointing `tcw init --work-path` at a folder outside any repository
would build the entire store and rewrite your config before telling you no. All
three now check first, and the two that refuse leave nothing behind. Starting
*without* `--worktree` is unchanged: it only needs the work store's repository,
and so is completing with `--already-integrated`, which says the merge-back
already happened and so has none to protect.

`tcw init --work-path` also got stricter about the stores it accepts, and every
refusal now happens before anything is written. It turns down a store your
`.gitignore` excludes — every item you filed there would be real on disk and
invisible to Git — whether the rule was there first or added after the store was
created; a store behind a broken symlink; a status folder that is really a file;
and a `docs/work` that is a symlink to somewhere else. A malformed
`tcw-config.yaml` now gets a plain message instead of a stack trace.

## Stage instructions name the file your item actually has

When you ask `tcw work stage spec` or `tcw work stage plan` what to do, the
instructions used to tell you to read `initial-request.md` — a file many items
do not have. An item created by piping text into `tcw work new`, or accepted
from the inbox, starts life with its raw arrival in `intake.md`, and the request
only gets written when you run the `request` stage.

Now the instructions name whichever one the item really has, and explain the
difference: the intake is what arrived, kept word for word, and the request is
the written-up version. On an item that has only an intake, the instructions say
to read that as the request instead of drawing conclusions from the missing
request. On an item with neither, they name no file at all rather than sending
you after one.

The post-mortem instructions read the intake too — on an item that came from the
inbox it is the earliest thing in the item's history, which is usually where a
post-mortem is headed.

The guides that ship with the plugin carried the same assumption and have been
corrected. The most visible one: issue triage used to write the request for you
at the moment it accepted an issue, which made every triaged item look like a
stage had run that had not. Triage now files the reporter's words as intake and
leaves the request to the stage that writes it.

If you script against `tcw work lifecycle` — or its `--json` — note that the
`spec`, `plan`, and `postmortem` stages now list `intake.md` alongside
`initial-request.md` in their inputs. Inputs are what a stage *may* read, not a
checklist, so a stage naming one of them and listing both is the intended shape.

