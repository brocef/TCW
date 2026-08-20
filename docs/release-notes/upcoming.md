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
created, and whether it covers the whole store, one status folder inside it, or
just the items in that folder — and it checks the default `docs/work` location
too, not only a store you point elsewhere; a store behind a broken symlink; a status folder that is really a file; and a
`docs/work` that is a symlink to somewhere else. A `work.path` that is not text
at all now says so instead of quietly falling back to the default location, and a
`tcw-config.yaml` that is not a mapping gets a plain message instead of a stack
trace.

## An item Git will not record now says so

`tcw init` turns down a work store your `.gitignore` would hide. That check
happens when you set the store up, so it never saw a rule added afterwards — one
you wrote by hand, one naming a single item, or one that arrived with a
`git pull`. In any of those, filing work appeared to succeed: the item was on
disk, `tcw work list` showed it, and Git had never heard of it. A colleague
cloning the project got nothing.

Now the write says so:

    tcw: a .gitignore rule hides docs/work/backlog/2026-08-20-secret-plan; it is
    on disk but git will not record it. Remove the rule, or run `git add -f` on it.

The item is still written and the command still succeeds — this is a warning,
not a refusal. Ignoring a status folder can be a deliberate choice, and refusing
would break the projects that made it.

The same warning now covers a case that was quieter and worse. Moving an item
into a status folder you have ignored — running `tcw work submit` where
`review/` is ignored, say — takes the item *out* of Git, and records that
removal in a commit whose message says the item moved. If you had that setup,
items were leaving version control on every transition and nothing told you.

`completed/` and `discarded/` stay quiet. TCW ignores those itself, on purpose —
that is how resolved work leaves the tracked tree — so there is nothing to warn
about, and a line on every `tcw work complete` is one you would learn to skip.

One thing to expect: a single command can print the warning twice, naming a
folder and a file inside it. Both lines are true, and it only happens when
something really is hidden.

## Bad capability references are caught when you set them

Setting a capability field that points at something that does not exist used to
succeed. `tcw capabilities set billing/invoices --field Subject=no-such-term`
exited 0 and wrote the value; you found out later, if you ran
`tcw capabilities check`. Now the write is refused, with the same wording
`check` would have given you, and nothing is written.

**This is a behaviour change.** A script that set a batch of fields loosely and
checked at the end will now stop at the first bad one. It also covers more
fields than you might expect — `Subject`, `Feature`, `Superseded by`,
`Blocked by`, `Roles` and `When`, six in all — so a script setting `Roles` or
`When` is affected too. When a single write has several bad references, all of
them are named in one message rather than one per attempt.

One ordering consequence worth knowing: the taxonomy Feature has to exist
before the capability that names it, and a `roles/…` capability before the
capability that lists it. That was always the intent; it just was not enforced.

Capabilities that already hold a bad reference are not stuck. Only the
references a write actually supplies are checked, so
`tcw capabilities set <path> --status Omitted` — the repair route completing a
work item recommends — keeps working.

On a project with no taxonomy, `Subject` and `Feature` have nothing to resolve
against and still pass; the other four are checked everywhere.

In the local web app, creating a capability with a bad field no longer leaves a
half-created capability behind, and a bad field on save comes back as a refusal
rather than a warning after the fact.

## Entries stay inside their own project

A term, capability or work item reached through a symlink inside
`docs/taxonomy/`, `docs/capabilities/` or `docs/work/` is no longer found,
listed, or written to. Before this, a symlink placed in one of those folders
pointed TCW at whatever was on the other end: `tcw taxonomy show` and
`tcw capabilities show` printed it, `tcw capabilities check` called it clean,
and — the part the original report missed — writes went through too.
`tcw taxonomy add --parent`, `tcw capabilities set`, and creating an override of
an inherited capability all created or changed files *outside* the project
folder. Only the Git step failed, and it failed after the file was already
written.

The same now applies one level down, to the files inside an entry. An entry
whose `meta.yaml`, `description.md`, or a listed attachment is a symlink
pointing out is not read; a work item's spec, plan or other artifact behaves the
same way. Previously an otherwise ordinary-looking entry could serve content
from anywhere on disk.

If you have a symlink inside one of these folders today, the entry behind it
will stop appearing. Nothing supported is lost: writing through one already
failed, and Git cannot track a file through a symlink anyway. To reference
another project's taxonomy or capabilities, use `tcw taxonomy extends` /
`tcw capabilities extends`, which is what that is for.

One related crash is fixed while we were here: adding a term or capability whose
name collided with a broken symlink printed a Python stack trace instead of
saying the name was taken.

## Accepting an inbox request names it after its own heading

Accepting a request used to name the item after the *file* the request arrived
in, date and all — so a request filed as `2026-08-19-another-raw-request.md`
became an item called `2026-08-19-another-raw-request`, filed under a slug with
the date in it twice. Passing `--title` was the only way to get a readable name,
and requests sent between projects with `tcw work delegate` and
`tcw work escalate` hit it every time.

Now the request's own `# ` heading names the item. If it has no heading, the
filename is still used, but without the leading date — one date, in the slug,
where it belongs. (A request filed under nothing but a date keeps it: there
would be no name left otherwise.) Passing `--title` still wins over both, so nothing you already
do stops working; you just no longer have to.

If you write requests by hand, the first line is now worth getting right; the
optional template in `docs/work-inbox-template.md` shows the shape.

## Unusual titles no longer break `tcw work new`

A title with no Latin letters in it — `tcw work new "東京"` — produced an item
whose folder name was just the date with nothing after it, and every such item
collided with the last one. A very long title failed outright with a filename
error, after printing a stack trace. Both now work: the folder name falls back
to `untitled` when there is nothing to build one from, and is shortened when it
would be too long. The title you typed is kept in full either way.

Relatedly, the local web app's "new item" call used to accept any text at all as
the creation date, which then became part of the item's folder name; it now says
no to anything that is not a date.

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

