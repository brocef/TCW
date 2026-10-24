As a user, I can move a project from TCW 3.x to TCW 4 with one command, and
see everything it will change before it changes anything.

`tcw migrate`, run in the project's folder, converts the active project in
place: its configuration moves into `.tcw/`, each object's state file takes
its TCW 4 name, every reference the project's files make to its own objects
is written as a full identifier, and, when its work is kept in Jira, the
`TCW Item` of each of its tickets is converted last, after every file. It
needs no argument, and runs in a 3.x project, which every other command
refuses.

`tcw migrate --dry-run` lists every file and ticket it would change, every
report of what needs attention or reads differently in TCW 4, and every
blocker, and changes nothing. `tcw migrate --no-jira` converts the files
only: it never contacts Jira, and says what the Jira step would do, so a
later `tcw migrate` converts the tickets.

A blocker, such as a file TCW 4 would refuse as planned, refuses the whole
run before anything is written. A run that stops partway is finished by
running it again; a run with nothing left to do changes nothing and says
so.
