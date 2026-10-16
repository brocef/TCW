## Fixes

- **A note that may already be on the ticket is not suggested twice.** When a
  move in a Jira project records its note as a separate comment and the
  connection fails while posting it, TCW now reads the ticket's newest
  comments first. If the note is there, nothing is reported. If the comments
  cannot be read either, the message says the note may have been posted and
  to check with `tcw work show <slug>` before adding it with
  `tcw work comment`. Only a comment that arrived after the note was sent
  counts, so an older note with the same words (the same move, made before)
  no longer hides one that never arrived.
- **Your Jira token is sent to your Jira site only.** If the site answered a
  request with a redirect to another address, the token went along with the
  redirected request. It no longer does. If the redirected request is then
  refused, the message says Jira redirected it to that address and that
  `work.jira.site` should be the address Jira answers at, rather than blaming
  your credentials.
- **`tcw provision` with a `tcw-config.yaml` it cannot read** now reports the
  error, naming the file, and exits with code 1. It used to say "Nothing to
  provision" and succeed.
- **`tcw work new --project <id> --stage inbox`** is refused (exit code 2):
  `--stage` was dropped without a word. An item created in another project
  starts where that project's intake puts it: its inbox, or, in a Jira
  project, as a ticket waiting in Jira for `tcw work tickets adopt`.
- **A Jira site address that is not a Jira site** is now reported as that
  (exit code 1, asking you to check `work.jira.site`) instead of "not found".
  A ticket or project that does not exist is still exit code 4.
- **A `tcw-config.yaml` that is not valid UTF-8 text** is reported naming the
  file and the byte, by `tcw provision` and `tcw init` as by the other
  commands, instead of in Python's own words, which named no file.
- **A configuration key written as a list or a mapping**, such as `? [a]`,
  is now an error that names the file and line, instead of a crash.
- **Both bad Jira credential settings are reported**, when `email-env` and
  `token-env` are both wrong, not only the first.
- **`tcw config show` writes binary, set, ordered-map and pairs values
  correctly**, each reading back as the same value. A value it cannot write
  that way is reported as an error naming its key, instead of being printed
  wrong.
- **`tcw work new --stage inbox` in a Jira project** is refused at once, without
  waiting for text on standard input.
- **The retired `connected-projects` key** is reported with the path to the
  file from the folder you ran the command in, such as `../tcw-config.yaml`.
- **The work commands now check the whole project graph**, as `tcw taxonomy`
  does: `tcw work list` refuses when a child project's `tcw-config.yaml` still
  uses a retired key, naming that file. A child project that is declared but
  not on this machine still does not stop it.
- **The refusal for a work store outside git** reads "the work store of
  project '<id>' is not in a git repository".

## Changes in what commands accept

- **`tcw taxonomy add --slug`** must already be a slug: lowercase letters and
  digits in words joined by single hyphens. A space, a capital letter or a
  `/` is a usage error (exit code 2) and nothing is created; to nest an entry,
  use `--parent`. The web viewer refuses the same slugs when it creates a
  term.
- **`tcw capabilities reset`** refuses (exit code 3) when a capability sits in
  a folder under the override's, instead of deleting it with the override.
  The message names each one; remove local ones with `tcw capabilities rm`
  and nested overrides with `tcw capabilities reset` first.
- **`tcw provision` does not ask for anything** while it clones: no
  password, no ssh passphrase, no question about trusting a new server. Where
  an answer would be needed the clone fails with git's reason. A private
  repository needs a credential helper that already holds its credentials,
  or an ssh key loaded in an ssh agent. The exception is an ssh command you
  have set yourself (`GIT_SSH_COMMAND`, `GIT_SSH`, or `core.sshCommand` in your
  global or system git config or given on the git command line, not the
  current repository's own setting): TCW leaves it alone, so ssh may still ask.
- **Offline `tcw validate` in a Jira project** now reads each item folder's
  `capabilities.yaml` and reports one that cannot be read or is malformed.
  With `--remote` it is reported once, not twice. Checking a single item,
  and saving a file in the web viewer, report it too, whatever the item's
  stage. A `qa` folder's rounds,
  which Jira keeps, now get only the "this folder is ignored" warning.

## Unattended work

- **At the request stage, an unattended run does not ask the advisors** what
  the requester wants, since that is not theirs to know. It writes the
  request from the evidence available and marks each assumption it made.
  Where the backend keeps the request, as Jira does, it posts its questions
  with `tcw work comment` instead and leaves the request's text alone. The
  unattended-work procedure has a row for this, and the autonomous-work
  skill states the same rule.

## The web viewer

- **Saving a taxonomy term or a capability needs its revision.** A save that
  does not say which version it was edited from is refused, so it can never
  overwrite someone else's change unseen. The viewer's own page always sends
  it.
- **An item's files stay inside the item's folder.** When a stage folder or
  `capabilities.yaml` is a link that leads outside the item folder, the
  viewer neither reads nor writes through it. On the item's page, a document
  or declaration reached through such a link is shown as not written, and
  rounds and handoffs reached that way are left out, so they decide no
  verdict.
- **The "stale write" banner** no longer makes the browser warn about its
  layout.
