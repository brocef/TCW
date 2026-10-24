## Settings a project takes from its parents

A project now takes its parents' tags and Jira settings: `work.tags` and
everything under `work.jira` come down each parent link that passes `config`,
which every link does unless it says otherwise. Nothing else comes down, and
neither does which backend a project uses: every project says `backend: jira`
itself, and one that says nothing keeps its items in files. So a family of
projects that shares one Jira project writes the site, the fields and the
credential names once, in the parent, and each child writes only its own
backend and stage statuses.

A child changes what it inherits in three ways. Setting a value replaces the
parent's; a mapping merges key by key, so a child that sets only
`work.jira.project` keeps its parent's site. An `inherit: true` entry in its
tags adds to its parents' list:

    work:
      tags:
        - inherit: true
        - mobile

And `null` removes an inherited value. `tcw work tags add` in a child with no
list of its own writes that `inherit: true` entry for you, so the child keeps
following tags its parents add later, and `tcw work tags rm` refuses a tag
that comes from a parent.

## A parent that is not here, or has a mistake

A missing parent stops only a command that needs a setting it could have
given, with exit code 7 naming the setting and the project. Listing, reading,
creating and moving a filesystem project's own items never needs one; applying
or listing tags does, unless the child sets its own tags, and so does every
command on a Jira-mode project whose Jira settings come from that parent.
`tcw validate` never stops: it says the configuration inherited from that
project could not be checked, and still checks the Jira settings the child, or
a parent after the missing one, sets itself. `tcw config show` prints nothing and exits 7
rather than show settings that are not the ones commands run with.

A mistake in a parent's shared settings stops only the commands that read
that setting, naming the parent's file; `tcw validate` in the child warns
about it, and fails only in the parent.

## Personal settings from environment variables

Any setting a personal file may set can now be set from an environment
variable named after the setting and the project, in capitals, with `__`
between them:

    TCW_USER_NAME__MY_APP=Robin
    TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__CORE=MY_EMAIL
    TCW_WORK_STAGES_SPEC_PROMPT__MY_APP='[{blob: Keep it short.}, {inherit: true}]'

A list or a mapping is written as YAML. A variable naming a stage changes only
what it names, and a more specific variable wins over a broader one. A
variable stops commands in any project with exit 1 when it names no setting,
names one only the team may set, or holds a value that is not valid YAML, is
`null`, is not the kind of value the setting takes (a list for a stage's
`prompt`), breaks the rules of an `inherit` entry, or is not a valid
`user.name` or credential variable name. The rest of a value is checked only
when the project the variable names is loaded, and stops commands only there:
a binding's shape or keys, a `post` entry, and a `file:` binding that leaves
that project's folder. `tcw validate` reports each problem in the project it
stops, starting with the variable's name. Your settings for
a parent, from its personal file or a variable, reach its children through
what it passes down. `TCW_NO_PERSONAL_CONFIG=1` turns the variables off along
with the personal files. `tcw config show --origin` names the variable a value
came from.
