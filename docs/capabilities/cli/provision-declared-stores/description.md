As a developer arriving in a fresh checkout, I can run one explicit command,
`tcw project provision`, to obtain what this project declares but does not have
here. With no argument it works in two passes. The stores pass obtains the
component stores, `work`, `taxonomy` and `capabilities`, whose home repository
the project declares and which are not here. The projects pass then fetches the
projects of this project's family that are not on this machine, as [Fetch a
project that is not on this machine](tcw://C/cli/fetch-a-project-that-is-not-on-this-machine)
describes. It reports on standard error what it is about to contact before
contacting it, fetches each store into the location the declaration names or a
per-machine cache, and says where each store landed. It prints nothing on
standard output. TCW 3.x's name for it, *tcw provision*, is not a command:
typed, it is a usage error (exit 2) whose message names `tcw project provision`,
as [the 3.x to 4.0 migration guide](../../../migration-guide-3.X-to-4.0.0.md) says.

`--component <axis>` limits it to that store (repeat it for more than one), and
then it fetches no project and contacts no project's remote: a run that names a
store reaches only that store's repository. `tcw project provision <id>` is the
other way round: it fetches project `<id>` and the projects it inherits from
that are missing, and no store. Naming a project and `--component` together is
a usage error (exit 2).

Before anything is contacted it refuses, with exit 1, a `.tcw/tcw-config.yaml`
it cannot read, a `TCW_PROJECT_<ID>` variable that is set and wrong, and a
malformed `repository` declaration, named by its key. Without `--component` it
also refuses a problem in the links between projects, such as a manifest that
cannot be read or one ID found in two folders, naming the file; a project that
is merely not on this machine is not such a problem.

Each store is resolved, reported, and failed on its own, so one store's failure
neither suppresses nor corrupts another's result, and it does not stop the run:
the other stores are still obtained and, without `--component`, the projects
pass still follows. Its last line then says, when anything failed, how many
stores and projects were fetched and how many failed, that what was fetched
stays, and that running the command again fetches the rest. Either way a
failure makes the exit code 1.

A declaration's `ref` may name a branch, a tag or a commit. The store's
repository is cloned and then that `ref` is checked out, so a `ref` that names
none of these fails the store with git's reason rather than being read as the
name of a file. The URL is given to git after `--`, so it is never read as one
of git's options.

When a command in one project reads the taxonomy or capabilities store of a
parent it inherits from, and that store is declared with a home repository but
not fetched, the message names the command that fetches *that* store, run in
its own project: `tcw -C <folder> project provision --component <axis>`, with
that project's folder written out. Running `tcw project provision` here would
fetch this project's stores, not that one's. For this project's own store the
message is `tcw project provision --component <axis>`.

Obtaining a missing copy is all it does. No `tcw` command pulls, pushes or
updates a provisioned copy: bringing one up to date, and committing and pushing
what I change in it, are mine to do (or my project's own hooks').

Running it again does nothing: a store that already resolves is reported as
already available and no network call is made. **That covers whatever
resolution can reach**, which includes a store sitting inside a project I
already have here, matched against the manifest entries that give that
project's repository — so a workspace laid out differently from the way its
configuration describes it does not clone a second copy of a repository it is
standing next to. `--dry-run` shows me the plan without contacting anything.

Provisioning only ever happens because I asked for it. No other `tcw` command
reaches the network on a project's behalf (apart from a project that keeps its
work items in Jira, which reaches Jira), so a repository I have merely checked
out never fetches from a remote its config chose until I run this command. Nor
does it contact a remote other than the one it showed me: if the place a store
would be fetched into is already occupied by something else, I am told what is
there and nothing is contacted at all.

It does not ask me anything while it clones: not for a password or token, not
for an ssh key's passphrase, and not whether to trust a server it has not met.
Where git or ssh would need an answer, the clone fails instead and I am told
git's reason. So a private repository needs credentials git can use without
asking, from a credential helper or an ssh key loaded in an ssh agent. The
exception is an ssh command I have set myself (`GIT_SSH_COMMAND`, `GIT_SSH`, or
`core.sshCommand` in my global or system git config or given on the git
command line, not the current repository's own setting): it is used as it is,
so ssh may still ask.

Every git command TCW runs ignores git's location variables, the environment
variables that tell git which repository to act on (`GIT_DIR`, `GIT_WORK_TREE`,
`GIT_INDEX_FILE` and the others of that kind). Git sets some of them while it
runs a hook, so running this command from inside a git hook still clones and
checks out in the store's own folder: it neither moves the hook's repository to
the store's `ref` nor writes into that repository's index. Git's configuration
variables are kept, since settings I give git that way are mine.

A failure — unreachable remote, unknown ref, refused authentication, or a
repository that turns out not to carry the store where the declaration says —
tells me the cause, counts as a failure of the run, and leaves nothing new
behind. A working copy I already had is never deleted on my behalf.
