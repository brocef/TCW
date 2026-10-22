# Spec — TCW 4.0: changes only in the owning project, and moving or renaming objects

Child 9 of 13 of TCW-99. It carries out these sections of the TCW-99 design
(`docs/work/TCW-99-…/design.md`): "Only the active project can be changed"
(including `tcw -C`, added to the design on 2026-10-21), "Moving and renaming
an object", and the parts of "What any store must support" that sort these
operations into the model and the deployment layer. It absorbs TCW-27 (a
rename command for taxonomy and capabilities) and settles TCW-87 (following
renamed identifiers). Built on the `v4` branch.

The children land in the order TCW-106, TCW-107, TCW-110, TCW-108, TCW-111,
TCW-109, TCW-112, this item, then TCW-113 (decided by the dispatching session,
2026-10-22; TCW-112 and TCW-113's blocker links on Jira record it). So this
item builds on all of the first seven: the
`.tcw/` folder (TCW-106), finding a project's folder from its ID
(`project_folder`, TCW-107 Design 2.12), parent links between projects
(TCW-108), full identifiers, their parser, and `tcw://` addresses (TCW-110),
state files, organising folders, the walk and nested work items (TCW-111),
inherited configuration (TCW-109), and overrides by path (TCW-112). TCW-109
and TCW-112 are being specified at the same time as this item; what this
item needs from them is named in Design 10, and TCW-112's spec already
answers it (TCW-112 Design 2.7 and 4.2).

File and line references are to commit `67c4c15a` on `v4`, where only TCW-106
has landed in code; the plan re-checks them against what the earlier children
finally land.

Words used throughout:

- The **active project** is the project the command runs in: the nearest
  folder enclosing the current folder that holds `.tcw/tcw-config.yaml`
  (TCW-99 requirement 7). `tcw -C` (Design 4) changes the current folder
  first.
- An object's **owner** is the project that declares it (TCW-110 Design 1.4),
  wherever its files are stored. An object is **another project's** when its
  owner is not the active project.
- A **full identifier** is `<project>.<namespace>/<id-path>` (TCW-110 Design
  1.1); its **id-path** is the object's folder path under its store's root,
  organising folders included (TCW-111 Design 4.1).
- A **reference** is a full identifier TCW stores in a record so that one
  object names another: a field such as `parent` or `Subject`, an entry in an
  item's `capabilities.yaml`, the Jira `TCW Item` field, a Jira item's
  recorded parent or blocker (Design 3.3), or a `tcw://` link in a Markdown
  file (TCW-110 Design 5.1). A **mention** is any other text
  that happens to contain an identifier, such as prose or a code example.
- **The walk** is TCW-111's one function that lists every object folder in a
  store (TCW-111 Design 2.5).

## Capability changes

- **New** `cli/change-objects-only-in-the-project-that-owns-them`: every
  command and web route that creates, changes or deletes an object refuses
  one that another project owns (exit 3, nothing written), naming the folder
  to run the command in, or saying that project is not on this machine. A
  reference to another project's object (a parent, a blocker, a link) is
  still allowed, because it belongs to the record that holds it.
- **New** `cli/run-a-command-as-if-started-in-another-folder`:
  `tcw -C <folder or tcw://<id>[.<namespace>].path/…> <command>` runs any
  command as if it had been started in that folder, as `git -C` does.
- **New** `work/move-a-work-item`: `tcw work move <item> --into <id-path>`
  or `--top` puts an item's folder in another place in the work store, with
  every item nested in it, and rewrites this project's references.
- **New** `taxonomy/rename-or-move-a-term`, `capabilities/rename-or-move-a-capability`:
  `rename` and `move` for terms and capabilities, with the same rules.
- **Changed** `work/rename-a-work-item`: an item with items nested in its
  folder can be renamed; every identifier that changes is printed, and this
  project's references and each moved ticket's `TCW Item` are rewritten.
- **Changed** `work/decompose-a-work-item-into-children`: a part in another
  project is made from that project, with `--parent <full identifier>`,
  usually through `tcw -C`.
- **Changed** `work/manage-blocking-relations`: `tcw work edit --blocks` is
  removed, for a target in any project, the active one included;
  `--blocked-by` on the blocked item does the same.
- **Changed** `work/keep-work-items-in-jira`: a rename or move sets the
  `TCW Item` of every ticket whose folder moved, and stops in a way that can
  be finished by running the same command again. A parent or blocker that is
  not a ticket on the same Jira site (an item of a files-backend project, or a
  ticket on another site) is kept, recorded in the item's state file by its
  full identifier, instead of being refused as today; one on the same site is
  a Jira issue link, as today.
- **Changed** `work/open-a-work-item`: its sentence about `--project <id>`
  filing into another project goes; `--parent` may name an item of any
  project TCW can locate, in either backend.
- **Changed** `work/tell-tcw-who-i-am`: its sentence that `--assign-me` with
  `new --project` is a usage error goes, since `--project` itself is refused.
- **Changed** `work/manage-the-work-inbox`,
  `work/configure-the-work-store-location`: they no longer describe filing
  into another project's inbox.
- **Changed** `cli/list-connected-projects`: rows no longer carry
  `read-only`, since every project but the active one is read-only.
- **Changed** `cli/reference-a-tcw-object`: a move or rename rewrites the
  active project's own links to every identifier it changed.
- **Changed** `capabilities/override-inherited`: an override cannot be moved
  or renamed away from its original's path.
- **Changed** `web/editing`: the create form no longer offers another project,
  and the "Blocks (add)" section is removed.
- **Changed** `skills/work`: its sentence that filing into another project
  is done with `tcw work new --project` goes; a part for another project is
  made there, through `tcw -C` (Design 9.5).
- **Removed** `work/delegate-a-work-item-to-another-project`.
- **Taxonomy:** new `owning-project`; changed `reference`, `project`.

## Problem

TCW 3.x lets a command change another project's records in two ways, and
gives no way to reorganise a store's objects without breaking the references
to them.

1. **Two commands write into another project.** `tcw work new --project <id>`
   creates an item in another project's store or Jira inbox
   (`tcw/work/cli.py:192-222`, calling `delegate`, `tcw/work/open.py:162-187`,
   and for Jira `delegate_to_jira`, `tcw/work/jira/tickets.py:323-389`), and
   `tcw work edit --blocks` adds this item to another project's item's
   `blocked-by` (`tcw/work/cli.py:339`, `:351-358`, through `blocks_target`,
   `:167-176`, and `open_for_update`, `tcw/work/open.py:190-199`). The module
   says so: "`delegate` and `open_for_update` are the only two ways a command
   writes into another project" (`tcw/work/open.py:5-6`). The web app has the
   same two paths: `POST /api/work` with another `project`
   (`tcw/serve/work.py:483-494`) and `POST /api/work/<item>/blocks`
   (`tcw/serve/work.py:441-462`, route at `:591`). TCW-99 drops both, because
   each changes a record another project owns.
2. **What replaces them does not exist.** Filing a part takes three steps
   today (the plan stage prompt's step 6, `tcw/work/prompts/plan.md:38-46`):
   file with `--project` (which refuses every property flag but `--priority`,
   `tcw/work/cli.py:200-204`), record the other project's changes in its
   version control (a filing is refused while that store has uncommitted
   changes, `_check_target`, `tcw/work/open.py:155-158`), then set `--parent`
   from inside that project. Agents were taught this flow in 3.0.1 and 3.0.2.
   There is no way to run a command as another project without changing
   folder first; every command reads its project from the current folder
   (`find_project_root`, `tcw/store/fs.py:296`; `tcw/project_files.py:74`).
3. **The other writers refuse only partly, and say little.** Work commands
   refuse another project's item with `belongs to project '<id>'; run the
   command in that project` (`_own`, `tcw/work/cli.py:69-74`), which does not
   say where that project is. The web app refuses an inherited taxonomy entry
   or capability (`tcw/serve/records.py:117-118`, `:193-194`) but has no one
   check that every write route goes through. TCW-108 adds an interim rule
   until this item (TCW-108 Design 7.1), and a `read-only` field in
   `tcw projects list --json` and the web app's `readOnly` that describe it
   (TCW-108 Design 8.2, 8.5).
4. **Renaming covers one namespace and one level.** `tcw work rename`
   renames one item's folder, rewrites `parent` and `blocked-by` in the other
   items of the files backend (`FsWorkBackend.rename`,
   `tcw/work/fs_backend.py:424-477`) or one ticket's `TCW Item` in Jira
   (`JiraBackend.rename`, `tcw/work/jira/backend.py:870-909`), and lists the
   lines that still mention the old folder name (`report_mentions`,
   `tcw/work/fs_backend.py:211-223`). TCW-111 refuses it for an item that has
   items nested in its folder, saying the rename waits for this item
   (TCW-111 Design 5, row 7). Taxonomy and capabilities have no rename at all
   (`tcw/taxonomy/cli.py:141-197` and `tcw/capabilities/cli.py:225-310`
   register no such command; TCW-27 records two renames done by hand as
   `add`, `set`, copy and `rm`). Nothing moves an object into another folder,
   which TCW-111 leaves as the fix for an object nested in the wrong folder
   (TCW-111 Design 3.4) and TCW-110 leaves as the fix for a folder whose name
   breaks the identifier grammar (TCW-110 Design 1.6).
5. **References to a moved object are only partly followed.** The files
   backend's rename rewrites only `parent` and `blocked-by`. It does not
   rewrite `tcw://` links in Markdown, which `tcw validate` checks
   (`_LINK_RE`, `tcw/validate.py:49`, read at `:329-335`), entries of items'
   `capabilities.yaml`, or the references between terms and capabilities
   (TCW-110 Design 5.1's table). And it moves the folder before it rewrites
   (`tcw/work/fs_backend.py:452`, then `:455-472`), so a stop between the two
   leaves references that no run of the command can find again.
6. **A Jira item cannot name a parent or blocker outside its Jira site.**
   `ticket_key` refuses any parent or blocker that is not a ticket on the
   item's own site (`tcw/work/jira/backend.py:578-588`), so a Jira project's
   part cannot name an epic kept in a files-backend project or on another
   Jira site. The user keeps real setups linked across backends in exactly
   these two ways (Notes, decided 2026-10-22), and `docs/use-cases.md` S-3
   requires a filing that crosses backends to work.

## Goals

1. Only the active project's objects are created, changed or deleted, by
   every command and every web route, through one check, whose refusal names
   where to run the command instead.
2. `tcw work new --project` and `tcw work edit --blocks` are gone; each step
   of the flow they served has a named replacement.
3. `tcw -C <folder or address>` runs any command as if started in that
   folder.
4. Each namespace has `rename` and `move`, which change an object's full
   identifier and that of every object nested in its folder.
5. A move or rename rewrites every reference the active project holds to an
   identifier it changed, in files and in Jira's `TCW Item`, lists the
   mentions it did not rewrite, and prints every identifier it changed.
6. A move or rename, in either backend and any namespace, that stops partway
   says what was done and is finished by running the same command again;
   when it stopped because another command is moving the same item, it says
   how to check the result instead (Design 5.8).
7. A work item in Jira can name a parent or blocker in any project TCW can
   locate, whatever its backend or Jira site.

## Non-goals

- **Rewriting other projects' references** (the request's "Out of scope").
  They fail `tcw validate` there until fixed there (TCW-110 Design 6.4). The
  command prints every identifier it changed so they can be passed on.
- **Following an old identifier.** TCW keeps no record of old identifiers and
  never reads an old one as its new one. This settles TCW-87, which asked that
  a renamed slug keep working in the web app, the tracker commands and links,
  through a 2.x `renames.yaml` that 3.x no longer has: the design's choice
  that an identifier says where its object is (TCW-99 "Full identifiers")
  means an old identifier names nothing, and the person is told so.
- **Moving an object into another project.** An object belongs to the project
  that declares it; moving it to another project would be deleting it here and
  creating it there, two writes in two projects. Not offered.
- **Moving or renaming from the web app.** The CLI may do more than the web
  app; the rule is only that the web app shows nothing the CLI cannot
  (TCW-99 principle 4).
- **Views of other projects' objects, and the web app's display of them as
  read-only** (TCW-113). This item makes every web write route refuse an
  object another project owns (Design 1.4); showing such objects without edit
  controls is TCW-113's.
- **`tcw project path <id>` and `tcw project provision <id>`** (TCW-115). The
  refusal of Design 1.3 names the folder itself, so it needs neither.
- **Guides, skills, `docs/use-cases.md` and the migration guide** (TCW-117).
  This item changes the text shipped with the CLI (the plan stage prompt
  and the `audit-backlog` procedure, Design 9) and, in the documents, only
  the passages that write a removed option as a `tcw` command, each only
  as far as it takes to name a command that exists (Design 9.5). Teaching
  the 4.0 flow is TCW-117's.
- **Migrating 3.x data** (TCW-116), including tickets whose `TCW Item` still
  holds a 3.x value: a move that would set one is refused until it is
  migrated (Design 7.3).

## Design

### 1. Only the owning project changes anything

1.1. **The rule.** A command or web route that creates, changes or deletes an
object acts only on objects whose owner is the active project. Before it
writes anything, it passes each object it would write to one function, the
**ownership check**, which refuses (`Refused`, exit 3, nothing written) when
the owner is another project. Every writer calls this one function; none
compares project IDs itself. It replaces `_own` (`tcw/work/cli.py:69-74`)
and the refusals of another project's object that TCW-110's
`find_tree_writable` made (TCW-110 plan, Step 6) and that TCW-112's plan
moves into the stores' `override_target` and `removal_target`, which
become calls of it.

**The check comes before the lookup.** When the text naming the object
names a project (a full identifier, or a ticket key given as
`<project>.work/<KEY>`; TCW-110 Design 3.1), the check is made on that
project before anything of it is opened, read or looked up: before its
backend is opened (`open_project`, `tcw/work/open.py:86-97`, which raises
exit 4 or 5 today), before `find_tree` reads its store, and before
TCW-110's not-found hint. So a write naming another project's object exits
3 whether or not that project can be read, and whether or not it holds
the object. Text that names no project (an id-path or a bare ticket key)
is looked up in the active project's stores, and the object found is then
checked; that is how an id-path that the inherited view resolves to another
project's object is refused (1.5). The one exception, overriding an
inherited object (1.5), is decided in TCW-112's order (its plan, choice
9): an identifier of a project that is not one of the active project's
sources for that namespace is refused before anything is read, so it exits
3 even with an ancestor missing; only for a source's identifier is the
active project's inherited view consulted (whether the identifier is in
its id-path's chain, TCW-112 Design 2.7), which needs the ancestors'
content and stops with TCW-108's exit 7 when an ancestor is not on this
machine; TCW-112 places both refusals in the two
store methods that choose a write's target (`override_target` for `set`
and `reset`, `removal_target` for `rm`), and this item makes each of them a
call of the ownership check.

1.2. **The writers.** Every one of these calls the ownership check:

| Namespace | CLI | Web routes |
| --- | --- | --- |
| work | `edit`, `advance`, `discard`, `comment`, `rename`, `move` | `PATCH /api/work/<item>`, `POST /api/work/<item>/comments`, `PUT` and `POST /api/work/<item>/files…`, `PUT /api/work/<item>/declaration` (`tcw/serve/work.py:585-594`, `tcw/serve/files.py:359-363`) |
| taxonomy | `rm`, `rename`, `move` | `PATCH /api/taxonomy/<key>` (`tcw/serve/records.py:247-248`) |
| capabilities | `set`, `reset`, `rm`, `rename`, `move` | `PATCH /api/capabilities/<key>` (`tcw/serve/records.py:251-252`) |

**Creators make no call.** These make a new object, and the object they
make is always the active project's: `tcw work new`, `tcw work tickets
adopt`, `tcw taxonomy add`, `tcw capabilities add`, `POST /api/work`,
`POST /api/tickets/<key>/adopt`, `POST /api/taxonomy` and `POST
/api/capabilities`. Each writes only into the active project's own store
(`add` takes an id-path, never another project's identifier, TCW-110 plan
Step 6; `adopt` refuses a ticket that already names an item,
`tcw/work/jira/tickets.py:146`). A call of the ownership check there could
never refuse, and a test of a call that can never refuse proves nothing,
so none is made. The sweep (Design 11) lists them as creators, each with
the reason it writes only the active project's store; the router's table
still marks the four web creators as writes (1.4), answering that they
name no existing object. A parent or blocker a creator records is a
reference (1.7), not a write to the item it names.

A `generate:` binding or a hook writes into the moving item's own folder,
which the move already checked. The plan's sweep (Design 11) lists every
write site and the call that checks it.

1.3. **What the refusal says.** One message shape, built by the ownership
check: `<full id> belongs to project '<owner>'`, then the caller's reason
when it gives one, then where to go:

- the reason is optional and starts with `, and`; today only TCW-112's `set`
  gives one: `, and '<active>' does not inherit it, so it cannot be
  overridden here` (TCW-112 Design 4.2);
- when `project_folder` (TCW-107 Design 2.12, on the command's one registry,
  TCW-110 Design 6.1) finds the owner's folder: `; run the command there:
  tcw -C <folder> …` with the folder as an absolute path;
- when it is not on this machine, or nothing names it (unknown):
  `; project '<owner>' is not on this machine`, followed by
  ` (<repository>)` when its manifest entry names one;
- for a graph problem (for example two folders that both declare
  `<owner>`): `; project '<owner>' cannot be located: <the problem's own
  message>`, since saying it is not on this machine would be false when
  there are two copies of it here.

Looking for the folder never changes the outcome: the command exits 3 with
nothing written whichever answer `project_folder` gives, as TCW-110's
not-found hint never changes its exit (TCW-110 Design 3.4). The search is
made only to word the message, after the check has decided to refuse
(1.1), and every error it raises is caught there.

This shape replaces the two refusals TCW-112 words for another project's
object, whose tail `; change it in '<Q>'` says nothing about where `<Q>` is:
`set`'s (TCW-112 Design 4.2) keeps its reason and takes 1.3's tail, and
`rm`'s `cannot remove <full id>: it belongs to project '<Q>'; change it in
'<Q>'` (TCW-112 Design 4.4) becomes 1.3's message with no reason. Both
still exit 3. So after this item one function words every refusal of
another project's object, and TCW-112's tests of those two messages change
to 1.3's text.

1.4. **The web app.** Every write route of 1.2 calls the ownership check
before it reads the request's body further, and answers a refusal with the
server's read-only answer (`read_only`, 403, `tcw/serve/server.py:61-62`,
already used at `tcw/serve/records.py:118`) carrying 1.3's message. Today the work routes can
name only the served project's items (`item_folder`, `tcw/serve/work.py:237-246`),
so the check refuses nothing new there; it is there so that TCW-113's views of
other projects' objects cannot reach a write.

The check is made where a test can see it: the server's route table marks
each route as a write or a read, and for every route marked a write the
router calls the ownership check on each existing object the route names,
before the route's own code runs. A creator of 1.2 is marked a write that
names no existing object, so the router makes no call for it. A route's own
code never calls the check. So AC 4's unit test reads the table, and a new
write route gets the check by being marked one.

The web app's `PATCH` of an inherited capability is refused, as today
(TCW-112 Design 4.5 keeps the web refusal; only the CLI's `set` writes an
override). Its message is 1.3's, followed by today's hint, which is kept
because it names the one command that can make the change here:
`; or override it in this project with tcw capabilities set <id-path>
--field <name>=<value>` (`tcw/serve/records.py:193-196`). A term has no such
hint, as today.

1.5. **Inherited objects and overrides.** Overriding an inherited object is
allowed, because the override is a new object the active project owns
(TCW-99 "Only the active project can be changed"; TCW-112 makes it an object
at the same path). So `tcw capabilities set <inherited>` writes the active
project's override and passes the check as an object of the active project.
Every other write that names an inherited object, or any object of a project
the active project does not inherit from, is refused: `rm`, `rename`, `move`,
and `set` of a capability the active project does not inherit.

1.6. **A planning workspace holding another project's store** (UC-4). The
items in `<workspace>/docs/app/work` are owned by `app` (TCW-110 Design 1.4),
and the workspace's own stores may not coincide with or contain that folder
(TCW-110 Design 7.4). So from the workspace's folder every write to an
`app.work/…` item is refused by 1.1, naming `app`'s folder, and
`tcw -C tcw://app.path/ …` runs it as `app`, whose store is that folder.

1.7. **The stated exception: a blocker, or a parent, in another project.** An
item's `parent` and `blocked-by` are the item's own record, so naming an item
of another project in them is a write of the active project only, and is
allowed. In Jira each is an issue link, which Jira also shows on the other
ticket; that is not a change to the other item's record (TCW-99, decided
2026-10-21). How a Jira item keeps one that Jira cannot link is Design 3.3;
that record is the item's own too.

1.8. **TCW-108's interim rule goes.** TCW-108 Design 7.1 (a project reached
through links both sides declare is writable, any other is read-only) has no
caller once Design 2 removes the two commands it governed, and is removed,
with whatever it alone uses. The `read-only` field of each row of
`tcw projects list --json` (TCW-108 Design 8.2) and the web app's `readOnly`
(TCW-108 Design 8.5) would now be true for every row but the active project's,
so they are removed rather than kept saying nothing: the create form that read
`readOnly` no longer offers other projects (Design 2.3).

`read_only_reason` (`tcw/store/project.py:356`, as TCW-108 Step 7 leaves it)
has one caller that is not about writing: `tcw provision` follows the
declarations of only the family members it returns no reason for
(`_connected_declarations`, `tcw/cli.py:222`). That use stays, unchanged in
behaviour, under a name that says what it decides there,
`reached_by_both_sides(project_id) -> bool`, and the interface method of
`tcw/store/base.py:223` is renamed with it. Whether provisioning should
keep that rule is TCW-115's, which replaces `tcw provision`. The write
refusal that used it (`_check_declared`) goes with Design 2.

### 2. Removing filing into another project

2.1. **`tcw work new --project <id>`** is refused as a usage error (exit 2),
before piped input is read and before anything is opened, as its own checks
are today (`tcw/work/cli.py:193`):
`work new --project is removed in TCW 4: an item is created in its own project; run
tcw -C <that project's folder or tcw://<id>.path/> work new "<title>" --parent <full id>`.
The message names `work new`, because TCW-113 brings `--project` back as a
filter of the list and show commands (TCW-99 design, "Choosing what a list
or show command covers").

2.2. **`tcw work edit --blocks <target>`** is refused the same way:
`work edit --blocks is removed in TCW 4: record it on the blocked item instead:
tcw -C <its project's folder> work edit <target> --blocked-by <this item>`.
That includes a target in the active project, for which the message omits
`-C`. The option is removed entirely, the user's decision of 2026-10-22
(Notes): the design's reason for dropping it ("because each one changes
another project") does not cover a target in the active project, which
changes only the active project, and the user chose removal anyway, so
that the option does not work for some targets and refuse others, and the
web "Blocks (add)" form goes with it.

Both options are kept in the parser only to give these messages, and are
hidden from `--help`. Their values are read only to word the message:
`--project`'s ID and the title fill 2.1's command, and `--blocks`'s target
decides whether 2.2's message has `-C` and which folder it names (the
folder `project_folder` gives, or `tcw://<id>.path/` when it gives none;
looking it up never changes the exit, as in 1.3). Nothing else is done
with them. They are removed outright in a later major version.

2.3. **The web app.** `POST /api/work` with a `project` other than the served
project is a usage error naming `tcw -C`. `POST /api/work/<item>/blocks` is
removed (no route; 404). The client's create form loses its project selector
(`web/client/src/ui/work-forms.tsx:583-591`), and the item page loses the
"Blocks (add)" section (`BlocksForm`, `web/client/src/ui/work-forms.tsx:330`,
used at `web/client/src/ui/app.tsx:1285`); the item page still lists what an
item blocks, which is computed from the other items. In a Jira project the
create and edit forms refuse a blocker in another project today
(`crossProject: refuse`, `web/client/src/ui/work-forms.tsx:594-606`, "in
Jira mode a blocker must be one of this project's items"); since the
backend now keeps such a blocker (Design 3.3), the forms accept it with the
same other-project warning they show for a parent, and the server's answer
carries Design 3.3's note. The bundle is rebuilt.

2.4. **The code that only served them is removed:** `delegate`,
`open_for_update`, `_check_declared`, `_check_target`, `_uncommitted_in` and
`uncommitted_changes` (`tcw/work/open.py:106-207`); `blocks_target`
(`tcw/work/cli.py:167-176`); `delegate_to_jira`, `_Connection`,
`_remote_metadata` and `_cannot_make_item` (`tcw/work/jira/tickets.py:311-458`);
the server's `delegate` service (`tcw/serve/services.py:34-37`, `:86`); and
TCW-111's 255-character fitting for delegation (TCW-111 Design 4.2), which
goes with it (TCW-111's handoff, 1). With `uncommitted_changes` goes TCW's
only check of a working tree for uncommitted changes; the git reads TCW still
makes are finding a repository's root and recognising a linked worktree.

### 3. A part in another project

3.1. **The flow.** A part is created in its own project, naming its epic by
full identifier: from that project's folder,
`tcw work new "<title>" --parent <epic's full id>`, or from anywhere,
`tcw -C <its folder or tcw://<id>.path/> work new "<title>" --parent <epic's full id>`.
Because the command runs as the part's project, every property flag is
available, its intake decides the stage, and its hooks and personal settings
apply. It also means `--parent` is resolved from the part's project, so that
project must be able to locate the epic's (TCW-107's manifest and search
rules, TCW-110 Design 6.1); in 3.x the filing ran from the epic's side and
needed no such link. When it cannot, the files backend still records the
value (3.2), and a Jira project stops with TCW-110 Design 6.1's exit for that
outcome (3.3). The replacement for each step of today's flow, which the
migration guide shows (TCW-117):

| # | 3.x step | 4.0 |
| - | -------- | --- |
| a | `tcw work new "<t>" --project <id>` | `tcw -C tcw://<id>.path/ work new "<t>" --parent <epic>` |
| b | a ticket key printed instead of a slug: no item exists there yet | does not happen: the command runs in the part's project, which makes its item as any `new` does |
| c | record the other project's changes before filing there again, or the next filing is refused or stays in the Jira inbox | not required by TCW; record changes the way that project does (TCW-99 requirement 2) |
| d | from inside that project, `tcw work edit <part> --parent <epic>` | part of step a |
| e | from inside that project, `tcw work edit <part> --blocked-by <ref>` | `tcw -C tcw://<id>.path/ work edit <part> --blocked-by <ref>`, or `--blocked-by` on step a |
| f | `tcw work edit <a> --blocks <b>` | `tcw -C <b's project folder> work edit <b> --blocked-by <a>` |

3.2. **Files backend.** A `parent` or `blocked-by` naming an item of any
project TCW can locate is stored in the item's state file, as today; its
cycle check covers only the item's own project, as today
(`validate_changes`, `tcw/work/model.py:188-233`).

3.3. **Jira: a parent or blocker Jira cannot link is kept as a recorded
reference** (the question TCW-99 left to this spec, decided by the user on
2026-10-22, Notes). A Jira item's parent and blockers are issue links, which
Jira makes only between tickets on one site; today `ticket_key` refuses any
other (`Refused`, exit 3, `<what> <id> is not a Jira ticket on <site>; Jira
links only tickets on one site`, `tcw/work/jira/backend.py:578-588`), and
Jira holds the link by ticket key (`_items`, `:360-381`, resolving each
parent and blocker key to an item). That refusal goes. Each value has
exactly one place, decided by what it names:

- **a ticket on the item's own Jira site** (any Jira project and any TCW
  project on that site, UC-5 included): a Jira issue link, as today. The
  state file never holds it.
- **anything else** (an item of a files-backend project, or a ticket on
  another Jira site): a **recorded reference**, the named item's full
  identifier, in the item's state file under `parent` or `blocked-by`, the
  same keys and the same form as a files-backend state file
  (TCW-110 Design 5.1). The ticket gets no link for it.

Which case a value is in is decided without the network: the named item's
project is located by `project_folder` on the command's one registry
(TCW-110 Design 6.1), and its configuration, read as a project read for
itself (TCW-109: its own sources folded, with no personal file, on the
command's registry), says its backend and, for Jira, its site. Two sites
are the same when their hosts are equal ignoring letter case (a site is
`https://<host>` with no trailing slash, as TCW's configuration check
requires); today's comparison of the whole text (`tcw/work/jira/backend.py:584`)
would call `https://Acme.atlassian.net` another site. When that project
cannot be located, the write stops with TCW-110 Design 6.1's exit for the
outcome (5 not on this machine, 1 unknown or a graph problem) and nothing
is written, because TCW cannot tell which place the value belongs in. When
it is located but its `work.jira` is undecided because the ancestor it
inherits that key from is not on this machine (TCW-109), the write stops
with exit 7 and TCW-109's message, and nothing is written, for the same
reason. The files backend's write of a parent in a project it cannot
locate is unchanged (3.2).

**The state file.** TCW-111 Design 1.2's rule for a Jira item's state file,
exactly `tcw-version` and `ticket` and optionally `id`, becomes: those, plus
`parent` (one full identifier) and `blocked-by` (a list of them), each
present only while it holds a recorded reference. `_item_file_problems`
(`tcw/work/jira/backend.py:146-167`, as TCW-111 leaves it) accepts them.
Both land in 4.0.0, so no released file has the narrower form and nothing
migrates.

**Writing.** `tcw work new` and `tcw work edit` in a Jira project, and the
web routes that call them, send each value to its place:

- `new --parent <recorded>`: the ticket is created with no parent link and
  the project's default issue type (`meta.issue_type`, as for an item with
  no parent, since `child_issue_type`, `:598-615`, needs the parent's level
  in this site's hierarchy), and the state file written for it holds
  `parent`. Recorded blockers go into the same write. A created ticket whose
  state file could not be written is TCW-111's existing stop
  (`tcw work tickets adopt <KEY>`), and its message adds the recorded values
  to set again with `tcw work edit`.
- `edit --parent <recorded>`: any Jira parent link the ticket has is removed
  first, then the state file's `parent` is written. `edit --parent <ticket on
  this site>`: the link is made first, then any recorded `parent` is removed.
  `--parent none` removes whichever is there. Blockers likewise, per value.
  Jira is written first, as everywhere in this backend, and a stop between
  the two writes is finished by running the same command again, which finds
  the Jira part done.
- On every such write, standard error says what Jira will not show:
  `<item>'s parent <full id> is not a ticket on <site>, so it is recorded in
  <state file> and Jira shows no link for it` (`blocker` for a blocker),
  once per recorded value written. This is what S-3 asks a filing that
  crosses backends to say. The web routes that create or edit an item
  (`POST /api/work`, `PATCH /api/work/<item>`) give the same sentence as a
  warning in their answer, as they give `checked_reference`'s warning
  today (`tcw/serve/work.py:365-376`), since the server's standard error
  (`tcw/serve/services.py:20-26`) is not seen by the person using the page.

The cycle check is the files backend's: only within the item's own project
(3.2); a recorded reference names another project's item, so it is never
followed.

**Reading.** The Jira backend's `read`, `list` and `show` give an item's
`parent` and `blocked-by` as one value each, from both places: the
resolved Jira links (as today) and the recorded references (read from the
state file in the folder scan, no network). `tcw work list --parent <X>` in
a Jira project uses today's JQL when `<X>` is a ticket on this site
(`:452-456`); otherwise it runs today's search without the parent clause and
keeps the tickets whose folder's state file records `<X>`, where today it
answers nothing (`:456`). A reader that needs the named
item itself, such as `tcw validate` and `show`, resolves the full identifier
through `project_folder` and the owner's backend, as for every reference
(TCW-110 Design 6.2): a files owner reads the folder, a Jira owner is
checked by its folder scan, so no network is needed. TCW-111 Design 3.2's
check of an item's folder against its `parent` reads a recorded parent from
the state file, so for such an item it runs without `--remote`; an item
whose parent is a Jira link is still checked only under `--remote`, as
TCW-111 says.

**What `tcw validate` checks** of a recorded reference, beside TCW-110
Design 6.4's form and 3.x checks:

- that it names an item: through `reference_problems`
  (`tcw/work/references.py:28-61`), which reads the item's `parent` and
  `blocked-by` and so covers recorded references once the backend returns
  them: naming no item is a warning, a project not on this machine is "could
  not check", as for every work reference (TCW-111 Design 2.6 l);
- that it is in the right place: a recorded reference naming a ticket on the
  item's own site is an error, `<state file>: parent <full id> is a ticket on
  <site>; run tcw work edit <item> --parent <full id> to make it a Jira
  link`, since that value belongs on the ticket (no network: the named
  project's configuration says its site);
- with `--remote` only: a ticket that has a Jira parent link while its state
  file also records a `parent` is an error naming both, since the item then
  has two answers; the same command as above, run again, leaves one.

**What a move does to such links** (Design 5 to 7): a recorded reference
always names another project's item, since an item of this project is
always on this project's own site, so a move in this project never finds
one to rewrite. When the item holding it moves, its state file moves with
its folder, unchanged. When the item it names is moved in its own project,
that project's move rewrites nothing here (Non-goals); this project's
`tcw validate` then warns that it names no item, and the other project's
move printed the new identifier to pass on. That is the same as every
reference into another project, in either backend.

**Use case S-3.** A filing that crosses backends now works: a Jira part
under a files-backend epic, a files part under a Jira epic (already allowed,
3.2), and a part on one Jira site under an epic on another. What it leaves
unfinished, the Jira link, it says on every write. The cost, recorded in
Risks: Jira's own views, JQL searches and boards outside TCW do not show a
recorded parent; TCW's `list --parent`, `show` and the web board do.

### 4. `tcw -C`

4.1. **Form.** `tcw -C <target> <command…>`, given before the command group,
for every command. It may be given more than once; each target is read from
the folder the one before it chose, as `git -C` does.

4.2. **A folder path.** A target that does not start with `tcw://` is a path,
relative to the current folder (the folder the previous `-C` chose) or
absolute. It must name an existing folder; otherwise the command is a usage
error (exit 2), `cannot run in <target>: no such folder`, before anything is
read. No project is needed at the starting folder.

4.3. **An address.** A target starting with `tcw://` must be a folder address
(TCW-110 Design 2.1): `tcw://<id>.path/<rest>` or
`tcw://<id>.<namespace>.path/<rest>`. An object address (`tcw://app.work/x`)
is a usage error (exit 2) naming the `.path` form, as a store location refuses
one (TCW-110 Design 7.1). The folder is found by TCW-110 Design 7.2, with
`named_by` the root of the project active in the current folder; each outcome
of `project_folder` gives TCW-110 Design 6.1's exit: not on this machine,
exit 5 naming the project and, when its entry gives one, the repository; an
unknown ID or a graph problem, exit 1 with that message. With no project
active in the current folder there is nothing to locate the ID from: exit 1,
`tcw -C <address> needs a TCW project here to find '<id>' from; give the
folder's path instead`. The project active in the current folder is read
for this as any command reads it, so a 3.x project there gets TCW-106's
refusal (`refuse_legacy_project`) and a configuration problem there stops
the command as it would any other; a path (4.2) reads nothing at the
starting folder and so avoids both. A resolved folder that does not exist
is 4.2's usage error.

4.4. **An address runs as the project it names.** After the folder is chosen,
the project active there must be the address's `<id>`. Otherwise the command
is a usage error (exit 2) and runs nothing:
`<address> is a folder of project '<active>', so the command would run as
'<active>', not '<id>'; give tcw://<id>.path/ to run as '<id>'`, or, when no
project is active there, `<address> is <folder>, which is in no TCW project;
give tcw://<id>.path/ to run as '<id>'`. The first happens
when an address names a folder inside another project, for example
`tcw://app.work.path/` in UC-4, whose folder lies inside the workspace. A
plain path (4.2) is not checked: it runs as whatever project is there, which
is what "as if started there" means.

4.5. **Everything runs as there.** Once the folder is chosen (for an address,
from the starting project, 4.3), `tcw` changes its current folder to it
before anything of the command runs, before TCW-106's refusal of a 3.x project
(`refuse_legacy_project`, `tcw/cli.py:649`) and before the configuration is
read (`tcw/cli.py:658-661`). So the active project, its configuration, the
personal files and environment variables that apply to it (TCW-109), its
stages, checks and hooks, relative paths given as arguments, and the paths
printed relative to the current folder (`shown`, `tcw/output.py:26-28`) are
exactly those of a command started there. When `tcw.cli.main` is called within
another Python program (the suite, the eval harness), it changes the folder
back before it returns.

4.6. **Only this machine.** `-C` reads folders on this machine and nothing
else: no network, and no git process other than read-only `git rev-parse`.
The exception is not `-C`'s own: every lookup of a project's folder builds
a project registry, and building one probes, once per folder per process,
whether the folder is a linked git worktree (`worktree_anchors` and
`_git_lines`, `tcw/store/project.py:67-79`, `:119-158`, 3.x code; a primary
checkout costs two `git rev-parse` runs, and a folder that is no
repository still starts one). The same rule is already the one the web
app's process test applies (`_allowed`, `tests/serve/test_no_process.py:77-91`),
and the criteria that check processes (AC 9, AC 25) use it. (In a git
submodule the probe also reads one value with `git config --get`, which
is read-only too; no fixture here is a submodule.) It belongs to the
deployment layer (TCW-99 "What any store must support"), since it is
about folders on disk.

### 5. Moving and renaming an object

5.1. **The commands.** In each namespace:

| Namespace | Rename | Move |
| --- | --- | --- |
| work | `tcw work rename <item> <words>` (exists) | `tcw work move <item> (--into <id-path> \| --top)` |
| taxonomy | `tcw taxonomy rename <term> <name>` | `tcw taxonomy move <term> (--into <id-path> \| --top)` |
| capabilities | `tcw capabilities rename <capability> <name>` | `tcw capabilities move <capability> (--into <id-path> \| --top)` |

A **rename** changes only the last part of the object's id-path; a **move**
changes only the folders above it. Doing both is two commands.

- A work item's new last part keeps its date or ticket key, and `<words>`
  follows today's rules (`tcw/work/fs_backend.py:424-438`,
  `tcw/work/jira/backend.py:872-882`), its length bounded by 4.3 of TCW-111.
- A term's or capability's `<name>` is one id-part (TCW-110 Design 1.1), not
  a reserved name (TCW-111 Design 2.4); otherwise exit 2 before anything is
  read.
- The object's title or `name` field does not change, as a work item's title
  does not today (`docs/lifecycle/abstraction.md:55-56`).
- The object argument accepts the forms of TCW-110 Design 3.1, and 5.5 below.

5.2. **What changes.** The object's full identifier, and the full identifier
of every object the walk finds below its folder (nested items, terms or
capabilities), each of which keeps its id-path below the moved folder. Every
other thing in the folder (fixed files, `resources/`, hidden folders, and
whatever the walk does not enter) moves with it and is not otherwise changed.
A move or rename never changes any object's `parent`, as changing a parent
never moves a folder (TCW-111 Design 3.4). When an object's folder ends up
inside an object that is not its `parent`, the command prints TCW-111 Design
3.2's warning on standard error and still succeeds; moving it to the top, or
into its parent's folder, is how that warning is cleared.

A **rename** also rewrites the renamed object's own `id:` when its state
file holds one equal to the old last part (TCW-111 Design 1.3 lets a
person write it, and row 2.6 k makes an `id` that differs from the folder's
name an error, so leaving it would make `tcw validate` fail after every such
rename). Only the renamed object's own `id` can change: a move changes no
object's last part, and a rename changes no nested object's. An `id` that
already differs from the old last part, such as a capability's 3.x
`cap-…` value that TCW-116 removes, is left as it is; `tcw validate`
reports it as before. A Jira item's state file may hold `id` too (TCW-111
Design 1.2), and the same rule applies to it.

5.3. **Where `move` puts it.** Exactly one of `--into` and `--top`;
otherwise exit 2.

- `--top`: the store's root.
- `--into <P>`: `<P>` is an id-path in the active project's store of the same
  namespace (a full identifier of the active project's is accepted too). It is
  either an existing object, so the moved object's folder goes inside that
  object's folder, or an organising folder (TCW-111 Design 2.3), existing or
  not. Each missing folder of `<P>` is created as an organising folder, which
  is allowed only where an organising folder may be: directly in the store's
  root or in another organising folder. Each new part follows TCW-110 Design
  1.1 and is not reserved.

Refused as usage errors (exit 2), before anything changes: `<P>` is the
object itself or lies below it; `<P>` is or lies inside a fixed folder or the
`resources/` of an object (TCW-111 Design 2.1); a missing part of `<P>` would
lie inside an object's folder (it would be TCW-111 Design 2.6 b's misplaced
folder); a part breaks the grammar or is reserved. A `<P>` owned by another
project is refused by 1.1 (exit 3). The missing organising folders of `<P>`
are created immediately before the folder moves, its last write (5.8,
step 2.4); when that move fails, each one this run created is removed again if it
is still empty, so a stop leaves none behind for TCW-111 Design 2.6 e to
report. After moving, each folder the move left
completely empty above the old place is removed, up to the store's root or the
first folder that still holds anything, and named on standard error; a folder
holding anything at all, hidden files included, is never removed.

5.4. **Checks before anything changes.** In this order; the first that fails
stops the command, and nothing has been written:

- a. The object is found (exit 4) and the active project owns it (1.1, exit 3).
- b. The new name (5.1) or the destination (5.3) is allowed (exit 2).
- c. The new folder is free: no entry of the folder it goes into has its name,
  compared ignoring letter case, so that a disk that ignores case cannot merge
  two folders (exit 3, `<path> already exists`, today's message).
  A new identifier equal to the old one is refused (exit 3,
  `<full id> already has that name`, today's Jira message,
  `tcw/work/jira/backend.py:885-886`). So a rename that changes only letter
  case is refused with `already exists`, deliberately: on a disk that
  ignores case it would be a rename of a folder onto itself. It is done in
  two renames, through another name.
- d. No changed identifier is longer than 255 characters (TCW-111 Design
  4.2): exit 2 naming the longest new identifier and its length. Nested
  identifiers grow with their parent's, so they are checked too.
- e. Every record that could hold a reference can be read: every object's
  state file in the active project's three stores, and every item's
  `capabilities.yaml`. Otherwise exit 1, naming each unreadable one, as the
  files backend's rename does today for items
  (`tcw/work/fs_backend.py:444-447`).
- f. Each reference rewrite (Design 6) would still be valid for its field:
  `Roles` takes only `roles/` capabilities and `When` only `conditions/` ones
  (`_check_globals`, `tcw/store/fs.py:2958-2968`). A move that would take a
  named capability out of that group is refused (exit 3), naming the field
  and the record that names it.
- g. Taxonomy and capabilities: the object is not an override of an inherited
  object, and no changed id-path is the path of an inherited object (TCW-112;
  Design 10.2). Either is refused (exit 3), naming the inherited object's
  full identifier: moving an override away would turn it into a separate,
  incomplete object, and moving onto an inherited path would silently make
  it an override; the commands that write overrides (`tcw capabilities set`
  on an inherited capability) are how one is made. When an ancestor whose
  content is needed for this check is not on this machine, the command stops
  with TCW-108's exit 7, as any command that needs something inherited does.
  This reads the design's "Commands that need only the project's own
  records still work: listing, reading and moving its own items" (TCW-99
  design, "A related project that is not on this machine") as being about
  work items,
  deliberately: a term or capability move needs the inherited paths to know
  whether it would make or break an override, so a fresh clone or CI without
  the ancestor cannot rename its own capability, while a work move needs no
  other project, unless the project's own `work.jira` comes from an
  ancestor that is not on this machine, which stops every command in that
  project, a move included, with exit 7 (TCW-109).
- h. Work in Jira: the ticket check of 7.3, step 1.

5.5. **A folder whose name breaks the grammar** (TCW-110 Design 1.6) is the
one source that `rename` and `move` accept although the identifier parser
refuses its text: when the text given as the object does not parse, and an
object folder of the active project's store exists at exactly that path,
spelt as given, and is one the walk lists, it is the object. Its new name or
destination must follow the grammar. This is how TCW-110's "only a rename by
hand fixes such a folder" is answered. Every other command still refuses the
text, as TCW-110 says.

5.6. **What it prints.** On standard output, one line per identifier it
changed, `<old full id> -> <new full id>`, the moved object first and then
the nested ones in the walk's order. With `--json`:
`{"schema": 2, "moved": [{"from": "<old>", "to": "<new>"}, …]}`. On standard
error: each ticket set (7.3); each file whose references were rewritten
(Design 6); each folder moved and each folder created or removed (5.3); each
mention not rewritten (6.4); and one closing line,
`references in other projects are not rewritten; tcw validate there reports
them: pass on the identifiers above`. The identifiers change only when the
folder moves, the last write (5.8), so a command that stops before it prints
nothing on standard output, and its message (5.8) names what it wrote.

5.7. **No hooks, no git.** A move or rename is not a stage move, so it runs
no checks or hooks, as `rename` runs none today, and TCW commits nothing.
The only processes it starts are 4.6's read-only `git rev-parse` probes.

5.8. **The order, and stopping halfway.** Every move and rename, in every
namespace and both work backends, runs in one order, so that a stop at any
point leaves the object at its old place, where running the same command
again finds it:

1. **Check** (5.4 a to g), writing nothing. Model code.
2. **The backend's or tree store's `move`** (7.1, Design 8), which, in this
   order:
   1. makes its own checks, writing nothing: for Jira, 7.3's read of every
      moved ticket; for the files backend, that every item's state file can
      be read (5.4 e, today's check, `tcw/work/fs_backend.py:444-447`);
   2. writes what it owns that names a moved object: Jira, each moved
      ticket's `TCW Item` (7.3), the moved item's first; the files backend,
      `parent` and `blocked-by` in every item's state file and a renamed
      item's own `id` (7.2); a tree store, nothing;
   3. calls back the model, which rewrites the repository's references that
      name a changed identifier (Design 6) and a renamed term's or
      capability's own `id` (5.2);
   4. moves the folder: creates the missing organising folders of `--into`
      (5.3), then one `os.rename` of the object's folder, which carries every
      nested folder.
3. **Tidy and report**: remove the folders the move left empty (5.3), list
   the mentions (6.4), print the identifiers (5.6).

The tickets come first because they are the one part another clone shares:
two people moving the same item from two clones meet at its first ticket,
and the second stops there before writing anything in its own clone (7.3).
Every write before the folder writes only values that name the new
identifiers, and skips a value that already does, so a re-run repeats
nothing: a ticket already set and a reference already rewritten are counted
as done. The folder's move is the one write after which a re-run cannot find
the object, and it comes last. A failure in step 3 does not undo the move:
an empty folder is left, or the mentions are not listed, and the command
exits 0 with a warning on standard error.

Nothing that was written is set back. A set-back needs the same Jira or
disk that has just failed, and it can overwrite another run that has
finished meanwhile (7.3); finishing needs neither. This replaces today's
Jira rename, which sets its one ticket back when the folder cannot be moved
(`tcw/work/jira/backend.py:894-904`). Whenever the command stops in step 2,
it exits 1 (5 when Jira could not be reached, 3 when a ticket was
found changed by someone else, 7.3, and 4 when a ticket or the source folder
has gone), and standard error says, whichever run did each part:

- every ticket that now holds the new `TCW Item`, set by this run or an
  earlier one (in 7.3's step 1 an earlier run's are the ones counted as
  done), and every ticket still to be set;
- every file rewritten so far, by this run or an earlier one, with each
  field or link changed (an earlier run's are the references that already
  name a new identifier, which nothing else can hold while the object is
  still at its old place);
- where the folder is: `the folder is still at <old path>` when it is
  there, checked when the message is built; otherwise `the folder is no
  longer at <old path>; another command may have moved it`, because a
  second command in the same clone can have moved it first;
- what to do next, which depends on why it stopped:
  - for every stop except the two below: `run the same command again to
    finish the move: tcw … <the command as given>`;
  - when a ticket was found holding a value that is neither the old nor the
    new identifier (exit 3, 7.3 step 2), another command is moving the same
    item, and running this one again would only be refused at that ticket.
    So the message instead names the tickets this run set, which now
    disagree with the other command's, and says: `wait for the other
    command to finish (if it ran in another clone, pull its commit into
    this one); then run tcw validate --remote, and in Jira set each ticket
    it reports to the identifier its folder now has. To keep this
    command's result instead, run this command again naming the item at
    its new place`. The tickets that need correcting are this run's: two
    runs cannot leave a ticket naming neither command's identifiers, since
    each run sets a ticket only to its own, so the run that finished has
    set every ticket after the clash, and moved the folder, and only the
    tickets this run set before it stop agreeing with the folder. The
    second way out finishes cleanly: run on the item at the other
    command's place, with this command's words, its 7.3 step 1 counts the
    tickets this run set as done (they hold its new value), sets the rest,
    rewrites the references naming the other command's identifiers, and
    moves the folder;
  - when the folder is no longer at its old place (exit 4): `run tcw
    validate to see what names it` (`tcw validate --remote` in a Jira
    project), since a re-run would not find it.

To abandon a move instead, the person finishes it and then moves or renames
the object back; there is no separate command, because the reverse move
does exactly that. When finishing is impossible because something else now
occupies the destination, the re-run is refused by 5.4 c, naming it; the
person frees the destination, by moving or renaming what is there, and runs
the command again.

### 6. Rewriting references

6.1. **What is rewritten.** Every reference held by the active project whose
full identifier is one this command changed is replaced with the new one. In
two parts, by who owns the fact (`docs/lifecycle/abstraction.md`, the second
question):

- **References a work backend holds** are rewritten by the backend's move
  (Design 7): in the files backend, `parent` and `blocked-by` in every item's
  state file, as today, now for every changed identifier; in Jira, the
  `TCW Item` field of each moved ticket. A Jira item's parent and blockers are
  issue links held by ticket key, which no move changes; its recorded
  references (Design 3.3) always name another project's item, so no move in
  this project matches one.
- **References kept in the repository**, in both modes: every stored
  reference of TCW-110 Design 5.1 in the active project's taxonomy and
  capabilities state files (`relatesTo`, `vocabulary`; `Subject`, `Feature`,
  `Superseded by`, `Blocked by`, `Roles` and `When`, keeping their `!`) and
  their `parent` (TCW-111 Design 3.1); every entry of every item's
  `capabilities.yaml` (under `new`, `changed`, `removed` and `taxonomy`); and
  every `tcw://` object link in a Markdown file in the active project's three
  stores, `resources/` included (TCW-111 Design 2.2).

A move in one namespace rewrites references in all of these, since a link in
a work item's spec can name a capability, and an item's `capabilities.yaml`
names terms and capabilities.

6.2. **Matching.** A reference is compared as a parsed full identifier, never
as text: it is rewritten when it equals an old identifier exactly (TCW-110
Design 1.1's case rule). So renaming `demo.work/2026-10-22-old` leaves
`demo.work/2026-10-22-old-two` alone. A link keeps its text and everything
around the address; only the address changes. A Markdown link inside code
(a fenced block or an inline code span) is not a reference: `tcw validate`
skips it (`_strip_code`, `tcw/validate.py:70-72`, used at `:333`), and so does
the rewrite. `_strip_code` deletes the code it finds, which loses each
link's position in the text, so the rewrite and `tcw validate` share a
variant that reports where the code spans are and keeps every byte, and
`_strip_code`'s callers move onto it.

6.3. **One list of reference fields, built here.** TCW-110 Design 5.1 lists
the reference fields as a table in its spec, and TCW-110's plan points about
fifteen separate checkers at the new identifiers one by one
(`TCW-110…/plan/plan.md:857-871`, the stored-reference callers in `tcw/store/fs.py`:
`_ref_problem`, `_require_ref`, `_resolve_vocab_ref`, `_referrers` and
`_capability_referrers` for taxonomy; `_validate_fields`, `_ref_problems`,
`_ref_error`, `_check_globals`, `_term_refs`, `_check_subject`,
`_check_feature` and `_referrers` for capabilities); it builds no single
definition. This item builds it: one module-level definition of every
stored reference field, giving for each the record it is kept in (a store's
state file, an item's `capabilities.yaml`, a Markdown link), the field's
name, whether it holds one value or a list, the namespace it names, any
group it is limited to (`roles/` for `Roles`, `conditions/` for `When`), and
whether a value may carry `!`. The rows are TCW-110 Design 5.1's table, the
`parent` of terms and capabilities (TCW-111 Design 3.1), and the Jira state
file's recorded `parent` and `blocked-by` (Design 3.3).

The plan moves every one of those checkers, the work references check
(`reference_problems`, `tcw/work/references.py:28-61`), the records gate's
reading of `capabilities.yaml` (`tcw/work/gates.py:331-380`) and TCW-112's
`reset` refusal list (TCW-112 Design 4.3) onto the definition, so each reads
which fields to look at from it. The rewrite (6.1), the 5.4 f check and
`tcw validate` all read the same rows: a field that is checked is a field
that is rewritten, and one added later joins both by being added to the
definition. That includes the files backend's own rewrite (7.2): it reads
which keys of an item's state file to rewrite from the definition's
work-item rows, not from the item model's `parent` and `blocked_by`
attributes, so a work-item reference field added to the definition is
rewritten by a move as well as checked.

The rewrite matches by field, never by value alone: in a YAML record it
replaces a value only where it sits at a field the definition names for
that record (for `capabilities.yaml`, the entries under `new`, `changed`,
`removed` and `taxonomy`'s three lists; for a state file, its reference
keys). A value equal to an old identifier at any other key (a `name`, a
free-text field, a key the definition does not name) is a mention (6.4),
listed and left unchanged. A checker's own rule about a value (for example that `Subject`
names vocabulary) stays in the checker; only the list of where references
are is shared.

6.4. **Mentions are listed, not rewritten.** After rewriting, every line of a
text file in the active project's three stores that still contains an old
full identifier, or an old id-path as a whole sequence of parts (bounded by
characters that cannot be part of an id-part, so another object with the same
last part is not reported, TCW-111 Design 7.2), is printed on standard error
as `<file>:<line>: names <old>, not rewritten`, as `report_mentions` does for
the work store today (`tcw/work/fs_backend.py:211-223`). This replaces each
backend's own call of it. A file that is not valid UTF-8 is skipped, as today.

6.5. **Not rewritten, and not read:** other projects' files and tickets (the
request's out of scope); a Jira ticket's text, its request and comments,
which are the person's words and would cost a request per ticket; `.path`
folder addresses, which name folders and are not checked against TCW's
objects (TCW-99 "Full identifiers"); configuration files, which hold no
object references (the sweep, Design 11, confirms it); and every file outside
the three stores, which TCW does not own (`docs/use-cases.md`, S-10).

6.6. **How a record is written.** Only the changed values are replaced; other
keys, their order and `tcw-version` are kept (TCW-111 Design 1.4). A
`capabilities.yaml` or Markdown file is rewritten in place, every other byte
unchanged. Every rewritten file is replaced in one step (written beside it,
then put in its place, as `_atomic_write_all` does, `tcw/store/fs.py:1149`),
so a failure partway through a write never leaves half of a person's file.

### 7. The work backend's move

7.1. **The operation.** The backend operation **rename**
(`tcw/work/backend.py:95`) becomes **move**:
`move(id_path, new_id_path, before_folder) -> list[(old, new)]`. It changes
an item's id-path, keeping the date or key of its last part (a usage error
otherwise), and every item whose id-path starts with `<id_path>/` changes
with it. It runs Design 5.8 step 2 in that order, calling `before_folder`
(the model's rewrite of the repository's references) after writing what it
owns and before moving the folder, and returns the pairs of full
identifiers it changed, the item first. A store that is not a folder of
files does the same: it writes its own references, calls `before_folder`,
then changes the id-path prefix of its records. There are still twelve
operations. `tcw work rename` and `tcw work move` both call it. TCW-111's
refusal of an item with items nested in it (TCW-111 Design 5, row 7) is
removed.

7.2. **Files backend.** It checks that every item's state file can be read,
as today (`tcw/work/fs_backend.py:444-447`); rewrites every work-item
reference field of Design 6.3's definition (today `parent` and
`blocked-by`) naming any changed identifier in every item's state file, and
a renamed item's own `id` (5.2); calls `before_folder`; then makes one
`os.rename` of the item's folder (today's call, `:452`, which now comes
last), carrying every nested folder. A state file it cannot rewrite stops
the command before the folder moves, with 5.8's message naming that file;
today the move stands and the item is named after the fact (`:455-472`).

7.3. **Jira.** In this order, within 5.8 step 2:

1. **Read.** One search for every moved item's ticket by key, reading
   `TCW Item`, before anything is written; the search is paged as every
   search of this backend is, so an epic with more nested items than one
   page of results holds is read whole. For each ticket:
   - the old value: to be set;
   - already the new value: counted as done, not edited again (an earlier
     run set it);
   - a TCW 3.x value (`<project>/<folder>`, TCW-110 Design 5.2): the move is
     **refused** before any change (exit 3), naming every such key and
     `run 'tcw migrate' in this project first`. These tickets exist only
     while a `tcw migrate` has stopped partway, and running it again
     finishes it; moving a folder while its ticket still holds the old form
     would leave a ticket that names a folder that is no longer there;
   - any other value: refused before any change (exit 3), naming the key,
     the value and `tcw validate --remote`;
   - no ticket answered for a key (deleted, or not visible to this
     account): refused before any change (exit 4), with today's message for
     a missing ticket (`Jira has no ticket <KEY>, or this account cannot see
     it`, `_issue`, `tcw/work/jira/backend.py:344-350`), naming the item.
2. **Set.** For each ticket to be set, the moved item's first, then the
   nested ones in the walk's order: read that ticket's `TCW Item` again,
   and set it only when it still holds the old value. When it already holds
   the new value it is counted as done. When it holds anything else, or the
   ticket has gone, the command stops (exit 3, or 4 for a ticket gone) with
   5.8's message, adding `<KEY>'s TCW Item is now <value>: another command
   may be moving this item`. For that exit 3 the message ends with 5.8's
   advice for a clash with another command (wait, run `tcw validate
   --remote`, set each ticket it reports to its folder's identifier, or run
   this command again on the item at its new place), never with "run the
   same command again".
3. `before_folder`, then the folder (5.8 step 2.3 and 2.4).

A Jira edit that fails in step 2 stops the command with 5.8's message (exit
1, or 5 when Jira could not be reached). A folder move that fails stops it
the same way, with every ticket set and every file rewritten named. For
every stop but the clash with another command, running the same command
again finishes the move: its step 1 counts the tickets
already set as done, the rewrite finds nothing left to change, and the
folder moves. Nothing is done twice (`docs/use-cases.md`, S-8).

**Two runs at once** (`docs/use-cases.md`, S-7: "the second move must
notice the item has moved, not overwrite it"). The read before each edit
is what notices: a second run that read the tickets before the first run
set them finds the first run's value at its first edit, which is the moved
item's ticket, and stops before writing anything, in Jira or in its own
clone. What it cannot close is the moment between that read and the edit,
which Jira's edit API gives no way to make conditional; Risks records it.
No run ever sets a ticket back (5.8), so a run that fails can no longer
undo one that succeeded, which today's set-back could.

What two runs at once can and cannot do, traced from the order above:

- a second run of the **same** command, started partway through the
  first, meets only the first run's values, counts them as done, and the
  two end in the same place;
- a second run of a **different** command (a rename of the same item to
  another name, say) stops at its first ticket, unless its read and its
  edit of that ticket both fall between the first run's read and edit of
  the same ticket. Only then can tickets end up naming different runs'
  identifiers. The tickets out of step are the ones the stopped run set
  before the clash; the run that went on set the others and moved the
  folder. So 5.8's message for that stop tells the person to wait for the
  other command, run `tcw validate --remote` and set each ticket it
  reports to the identifier its folder now has, or else to run the
  stopped command again on the item at its new place, rather than to run
  the same command again;
- no run loops: each ticket is read in step 1, read again just before its
  edit, and edited at most once.

The order keeps today's rename's order, Jira before the folder, and extends
it to the repository: the folder is the last thing written, because a
re-run finds the object only at its old place. Moving the folder first would
leave tickets and references naming a folder that no longer exists, with no
command to finish: the source would be gone, so running the move again could
not find it.

7.4. **`tcw validate --remote`** already compares each folder with its ticket
(TCW-111 Design 6.5); it is how a person checks a move that stopped.

### 8. The tree stores' move

Each tree store's interface (`TaxonomyStore`, `CapabilitiesStore`,
`tcw/store/base.py`) gains `move(id_path, new_id_path, before_folder) ->
list[(old, new)]`, the same shape as the work backend's (7.1), returning the
pairs it changed, the object first. The files store calls `before_folder`,
then makes one `os.rename` of the object's folder.

The references that terms and capabilities hold (`relatesTo`, `vocabulary`,
`Subject`, `Feature`, `Superseded by`, `Blocked by`, `Roles`, `When`,
`parent`) are kept in the tree stores' state files, which are repository
files in both modes (`docs/lifecycle/abstraction.md:14-17`: "The technical
record (…, taxonomy and capabilities) is files in the repository in both
modes"). So they are
rewritten by Design 6's model code through `before_folder`, with every other
repository reference, not by the store. A tree store kept somewhere other
than files would be a change to that rule, which belongs to the item that
makes such a store, not to this one.

### 9. Shipped text and documents

9.1. **The plan stage prompt**, step 6 (`tcw/work/prompts/plan.md:38-46`),
which TCW-111 also changes (it adds `--nest` to the first sentence). The
combined paragraph reads: split here with
`tcw work new "<title>" --parent <slug> --nest` per part, its request on
stdin; a part for another project is made in that project:
`tcw -C tcw://<id>.path/ work new "<title>" --parent <slug> --nest` (`--nest`
then makes it at the top of that project's store and says so); set
`--blocked-by` the same way; when Jira cannot link the parent (an epic kept
in files, or on another Jira site), TCW records it in the part's folder and
says so, and Jira itself does not show it.
The sentences about a ticket key printed instead of a slug, about setting
`--parent` afterwards from inside the other project, and about recording
TCW's uncommitted changes before filing again are removed. The combined
change is reviewed once both items have landed (TCW-111 Risks).

9.2. **The `audit-backlog` procedure** (`tcw/work/procedures/audit-backlog.md:27-29`),
shipped with the CLI and printed by `tcw work procedure audit-backlog`:
"Recommend `tcw work new "<title>" --project <id>` for each part there" becomes
"Recommend creating each part in its own project, with
`tcw -C tcw://<id>.path/ work new "<title>" --parent <slug>`".

9.3. **`docs/lifecycle/abstraction.md`:** the **rename** entry of the
interface list (`:55-56`, as TCW-111 leaves it) becomes **move**: "change an
item's id-path, keeping the date or ticket key of its last part; every item
nested in its folder moves with it. The item's title does not change." The
list of git reads TCW makes (`:101-104`) loses "checking a work store for
uncommitted changes before creating an item in another project" (Design 2.4).

9.4. **Command help and contracts:** `tcw work rename`'s `prints=` string
says it prints one `<old> -> <new>` line per changed identifier; the new
commands have contracts and examples like their neighbours'.

9.5. **The passages that write a removed option as a command.** The suite
checks every flag that a live Markdown file writes in a `tcw …` command
against that command's `--help` (`tests/test_documented_cli_surface.py`,
`_check`). Hiding `--project` and `--blocks` from `--help` (2.2) fails
that check for every live document that still writes `tcw work new …
--project` or `tcw work edit … --blocks`: about seventeen passages in the
skills, the guides, `docs/use-cases.md`, this repository's capability
ledger and the shipped prompt and procedure (the plan lists each). Two
ways out were weighed: keep the options visible in `--help` until TCW-117
rewrites those documents, or change the passages here. Keeping them
visible would make the check pass only because the documents describe an
option that still parses, while it no longer does what they say: the check
would be green over documents that are wrong. So this item changes each
passage, only as far as it takes to name a command that works (the part
made from its own project with `tcw -C … work new "<title>" --parent
<epic>`, a blocker recorded with `--blocked-by` on the blocked item), and
adds nothing else. The full rewrite of those documents for 4.0 stays with
TCW-117, which the handoff tells which passages were changed. The
capability ledger's record of the removed capability is deleted with the
options, since a removed capability is deleted from the ledger
(`tcw/work/gates.py:172`), and the four records that link to it lose the
link.

### 10. Interfaces this item needs from the items before it

10.1. **TCW-111:** the walk, `is item folder` at any depth, the
255-character check in the identifier parser, the reserved names, the 3.2
disagreement warning as a function the CLI can call, and the Jira state
file's check (`_item_file_problems`, TCW-111 Design 1.2), which Design 3.3
widens.

10.2. **TCW-112:** "what is inherited at a path" (TCW-112 Design 2.7): for
the active project and one namespace, the full identifier of the inherited
object at an id-path, or none, raising `InheritedUnavailable` (TCW-108's
exit 7) when the view cannot be built. Design 5.4 g calls it for the
object's own path (is it an override?) and for each new path. And
`tcw capabilities set` on an inherited capability writes the active
project's own object at the same id-path (TCW-112 Design 4.2), which 1.5
relies on. Both are in TCW-112's spec; nothing more is asked of it. Design
1.3 rewords two of its refusals, which its plan places in
`override_target` and `removal_target`.

10.3. **TCW-109:** configuration read for the active project as usual, and
another project read for itself (its own sources folded, no personal file,
on the command's registry; TCW-109 Design 5.2), with exit 7 when a key it
needs is undecided (TCW-109 Design 3). Design 3.3 reads the named project's
backend and site that way. Design 4.5 relies on the variables and personal
files that apply being chosen by the active project's ID and folder, which
TCW-109's request states.

10.4. **TCW-110 and TCW-107:** `project_folder` and its outcomes, the
address parser and folder-address resolution (TCW-110 Design 7.2), and
TCW-110 Design 5.1's table of reference fields, which Design 6.3 turns into
the one definition this item builds (TCW-110 builds none).

### 11. The sweep

Repository-wide over `tcw/`, `web/client/src/`, `scripts/` and `evals/`:

- every write site of 1.2, each listed with its call of the ownership check,
  and every creator of 1.2, listed as a creator with the reason it writes
  only the active project's store; every `slug.project != …` comparison
  used to refuse a write (`_own`, `tcw/work/cli.py:71`;
  `tcw/serve/work.py:454`, `:484`);
- every caller of `delegate`, `open_for_update`, `blocks_target`,
  `delegate_to_jira`, `uncommitted_changes`, `read_only_reason` (as TCW-108
  leaves it; its provisioning caller is renamed, 1.8) and the server's
  `delegate` service; every reader of
  `args.project` in `_new` and `args.blocks` in `_edit`; every reader of the
  `read-only` and `readOnly` fields;
- every caller of a backend's `rename` and of `report_mentions`;
- every reader of a reference field, each moved onto Design 6.3's one
  definition (the checkers 6.3 names, and any the sweep finds beside them);
- every reader and writer of a Jira item's `parent` and `blocked-by`
  (`ticket_key`, `_parent`, `_items`, `list`'s parent clause, `create`,
  `update`, and the web routes that call them), each taking Design 3.3's
  two places;
- every read of the current folder (`Path.cwd()`, `os.getcwd()`: ten sites
  in `tcw/` today), each confirmed to run after Design 4.5's change of folder;
- every configuration key, confirmed to hold no object reference (6.5).

The plan lists each site.

## Abstraction litmus test

| Operation | Layer | Verdict |
| --- | --- | --- |
| The ownership check (Design 1) | model | "Is this object's owner the active project?" compares two project IDs that every store has; a database keeps the owner as a column. Passes. |
| One definition of the reference fields (Design 6.3) | model | A list of which fields of which records hold references; any store has the same fields. Passes. |
| Work backend **move**, replacing **rename** (Design 7.1) | model, backend interface | "Change this record's id-path, and every record whose id-path starts with it followed by `/`" is a prefix update any store can make; Jira makes it as one `TCW Item` edit per ticket, each after a read of that ticket. The `before_folder` call is a point in the operation, not a filesystem detail: a store that is not files calls it before its prefix update. Still twelve operations. Passes. |
| Tree stores' **move** (Design 8) | model, store interface | The same prefix update on terms or capabilities. Passes. |
| Rewriting the backend's own references (Design 6.1, first part) | model, inside each backend | The backend owns `parent` and `blocked-by`, so it rewrites them: the files backend in its state files, Jira not at all, since its links are held by key and its recorded references (Design 3.3) always name another project's item. Passes. |
| Rewriting repository references (Design 6.1, second part; 6.2-6.4) | repository | Tree-store state files, `capabilities.yaml` and Markdown are repository files in both modes (`docs/lifecycle/abstraction.md:14-17`, Design 8); reading and writing them is not a backend fact (the second question). Passes. |
| Keeping a parent or blocker Jira cannot link, as a recorded reference (Design 3.3) | model, inside the Jira backend | The Jira backend owns the item's parent; it keeps it in the one place it can (a Jira link on its site, its state file otherwise), never both, so there is one answer. A non-file store would keep the reference as a column of the item's record. Deciding which place needs only the named project's configuration, no network. Passes. |
| `tcw -C` (Design 4) | deployment | About folders on disk and the process's current folder (TCW-99 "What any store must support"). A store that is not a folder of files is not involved. |
| Organising folders made or removed by `move` (Design 5.3) | deployment | TCW-111 places organising folders in the deployment layer; another store groups objects by the id-path string alone. |

## Use cases

- **UC-1 (a single project).** No configuration is added. `rename` gains
  nested items and prints `<old> -> <new>` lines instead of one identifier;
  `move` and the taxonomy and capabilities commands are new; nothing else
  changes. Nothing in UC-1 used `--project` or a cross-project `--blocks`.
  The same-project `--blocks` is refused, naming `--blocked-by` on the other
  item (Design 2.2, the user's decision).
- **UC-2 and UC-7 (a library others read; a public library).** A reader can
  never write the library's records: every write naming one is refused
  (Design 1.1), and overriding an inherited capability writes the reader's own
  object (1.5). The refusal names the library's folder on this machine, which
  appears only in the reader's own terminal; nothing is written into the
  library. A library that renames an object prints the changed identifiers;
  its readers' references fail their `tcw validate` until they update them,
  and a reader's override of a moved object is reported there as incomplete
  (TCW-112).
- **UC-3 (a monorepo).** An epic in the root with parts in the children: each
  part is made from its child project, `tcw -C apps/server work new "<t>"
  --parent app.work/<epic>` from the root, or `--parent` from inside the child
  (Design 3.1). Hooks are the child's own, because the command runs as the
  child. A move in one project of the monorepo rewrites only that project's
  records; the others' references are theirs.
- **UC-4 (a planning workspace).** The workspace cannot change `app`'s items,
  though their folders sit in its repository (Design 1.6); the refusal names
  `app`'s folder, and `tcw -C tcw://app.path/` runs the command as `app`.
  `tcw -C tcw://app.work.path/` is refused, since that folder is the
  workspace's (Design 4.4). The accepted cost (TCW-99): the planner needs each
  code project checked out. Filing no longer writes into a third repository,
  so the "left uncommitted" reporting and the refusal of a store with
  uncommitted changes (UC-4's requirements) go with it. Tested with two real
  git repositories (AC 3, 9).
- **UC-5 (a shared Jira project).** One Jira site, so a part's parent link to
  an epic of another TCW project in the same Jira project is made as today
  (Design 3.3). A move sets only the moved tickets' `TCW Item`, all of the
  active project's; a ticket of another TCW project is never edited, because
  only the active project's items move. A move that would set a ticket still
  holding a 3.x value is refused, naming `tcw migrate` (7.3). Parents and
  blockers between the TCW projects of one Jira project stay Jira links.
- **UC-6 (a project not on this machine).** A refusal naming it says it is
  not here (1.3); `tcw -C tcw://<it>.path/` exits 5 (4.3). A move of a term or
  capability whose inheritance check needs a missing ancestor exits 7 (5.4 g);
  a work move needs no other project, unless the project's own `work.jira`
  comes from an ancestor that is not on this machine, which stops every
  command in that project with exit 7 (TCW-109). A Jira write naming a
  parent in a project whose `work.jira` is undecided for the same reason
  also exits 7 (3.3).
- **UC-8 (several families).** `-C` with an address locates by TCW-107's rules
  from the project active where the command starts, so a second family with
  the same IDs elsewhere on disk is never reached unless those rules reach it;
  a plain path is exactly the folder given.
- **S-3 (backends).** Both backends implement `move`; Jira's references are
  issue links by key, so only `TCW Item` changes (Design 6.1, 7.3). "A
  filing that crosses backends must work, and must say what it left
  unfinished" is met: a part in a Jira project can name an epic kept in
  files or on another Jira site, recorded in its state file, and every such
  write says Jira shows no link for it (Design 3.3); a files part under a
  Jira epic already worked (3.2).
- **S-4 (worktrees, clones).** `-C` into a worktree runs as that worktree's
  project, by TCW-107's worktree rules. A rename in one clone and a nested
  create in another meet on merge as TCW-111 S-7 describes; the repair is now
  `tcw work move <old folder>/<part> --into <new epic>` and
  `tcw work edit <part> --parent <new epic>` (AC 14).
- **S-6 (unattended runs).** Every refusal and stop names the command to run
  next, so an agent needs no person: `tcw -C <folder> …` for 1.3, the same
  command again for every stop of a move (5.8), `tcw migrate` for a 3.x
  ticket (7.3). The one stop that needs a person is two different commands
  moving the same Jira item at the same moment (7.3), which the message
  says, naming `tcw validate --remote`.
- **S-7 (several people at once).** Two moves of the same item from two
  clones meet at its first ticket, and the second stops before writing
  anything (7.3); no run sets a ticket back over another's (5.8). The
  moment between a ticket's read and its edit stays open (Risks); when two
  different commands meet in it, the stop says to wait for the other
  command, run `tcw validate --remote` and set each ticket it reports to
  its folder's identifier, not to run the same command again (5.8).
- **S-8 (partial failure).** Every move, in both backends and every
  namespace, writes the folder last, so a stop leaves the object where a
  re-run finds it; the stop names every ticket and file already written,
  whichever run wrote it, and the command that finishes; the re-run repeats
  no edit (5.8, 7.3).
- **S-9 (upgrades).** `--project` and `--blocks` are refused with their
  replacement named (Design 2), rather than as unknown options. A move that
  meets a 3.x `TCW Item` value is refused until `tcw migrate` has converted
  it (7.3).
- **S-10 (things TCW does not own).** References are rewritten and mentions
  listed only inside the active project's three stores (6.5).
- **S-11 (version control).** TCW stops checking a working tree for
  uncommitted changes (2.4); no command here changes git, and the only git
  it reads is the read-only `git rev-parse` of finding a repository's root
  and recognising a linked worktree (4.6).

Checklist: 1 (where it looks) only the active project's stores, and
`project_folder` for a refusal's message and `-C`; 2 (whose things) only the
active project's records, which is this item's rule; 3 (reading across
projects) only to locate a folder for a message or for `-C`, and TCW-112's
inherited-path check; 4 (backends) the litmus table, Design 7; 5 (who is
present) nothing asks a person (S-6 above); 6 (harness) everything is in the
CLI, and the shipped prompt and procedure text names CLI commands only;
7 (stopping halfway) S-8 above, Design 5.8; 8 (single project) UC-1 above; 9 (older and
newer TCW) S-9 above; 10 (testing the setup claimed) AC 3 and 9 use two git
repositories, AC 7, 12, 13 and 27 the suite's Jira fake, AC 2 and 17 two projects
linked by `parents:`.

## Acceptance criteria

Each criterion runs against fixtures built with the suite's 4.0 project
helper, in a project `demo` unless it says otherwise. "Two projects side by
side" means two git repositories in sibling folders, each a 4.0 project, the
second found by TCW-107's search of the folders next to the first. "Prints"
means standard output; "says" means standard error.

1. **Work writes to another project are refused.** Two projects side by side,
   `app` and `core`, `core` holding a files-backend item `<c>`. In `app`, each
   of `tcw work edit core.work/<c> --priority high`,
   `tcw work advance core.work/<c>`, `tcw work discard core.work/<c> --reason x`,
   `tcw work comment core.work/<c>` (text on standard input),
   `tcw work rename core.work/<c> other` and `tcw work move core.work/<c> --top`
   exits 3, says `belongs to project 'core'`, core's folder as an absolute
   path and `tcw -C`, and every file under `core` is byte-for-byte unchanged.
   With `core`'s folder removed and `app`'s manifest placing `core` at
   `../core` with a repository URL, the same commands exit 3 and say
   `project 'core' is not on this machine` and the URL. With `core` removed
   from the manifest too, so that nothing names it (unknown), and again with
   two folders both declaring `core` beside `app` (a graph problem),
   `tcw work edit core.work/<c> --priority high` exits 3 and says `belongs
   to project 'core'`, with `is not on this machine` when nothing names it
   and `cannot be located:` followed by the graph problem's message for the
   two folders: locating never changes the exit. In each of the three
   variants no backend of `core` is opened (a test makes `open_project`
   fail if called), so the check comes before the lookup.
2. **Tree writes to another project are refused; an override is allowed.**
   `app` with parent project `core` passing taxonomy and capabilities,
   `core` holding term `t` and capability `cli/x`. In `app`:
   `tcw taxonomy rm core.taxonomy/t`, `tcw taxonomy rename core.taxonomy/t u`,
   `tcw capabilities rm core.capabilities/cli/x` and
   `tcw capabilities move core.capabilities/cli/x --top` each exit 3 naming
   `core`'s folder, and with `core`'s folder removed (its manifest entry
   kept) `tcw capabilities rm core.capabilities/cli/x` and `tcw taxonomy rm
   core.taxonomy/t` still exit 3 and say `is not on this machine`; `tcw capabilities set core.capabilities/cli/x --status
   Supported` exits 0, writes `app`'s own `cli/x` object (TCW-112), and leaves
   `core`'s files unchanged. In a third project `other` beside them that names
   no parent, `tcw capabilities set core.capabilities/cli/x --status Supported`
   exits 3 naming `core`'s folder, and still exits 3 with `core`'s folder
   removed, since `core` is not one of `other`'s sources and is refused
   before anything is read (TCW-112's order). The messages have Design 1.3's one shape:
   `rm`'s contains `core.capabilities/cli/x belongs to project 'core'; run
   the command there: tcw -C`, `other`'s `set` contains `belongs to project
   'core', and 'other' does not inherit it, so it cannot be overridden here;
   run the command there: tcw -C`, and neither contains `change it in`.
3. **A planning workspace.** Two projects side by side, `workspace` and `app`,
   `app` with `work.path: tcw://workspace.path/docs/app/work` and an item `<a>`.
   In `workspace`, `tcw work comment app.work/<a>`, `tcw work edit app.work/<a>
   --priority low` and `tcw work advance app.work/<a>` exit 3 naming `app`'s
   folder, and nothing under `<workspace>/docs/app/work` changes. Then, from
   `workspace`, `tcw -C tcw://app.path/ work comment app.work/<a>` exits 0 and
   a new comment file appears under `<workspace>/docs/app/work/<a>/comments/`.
4. **The web app.** Served from `app` (with parent `core` as in AC 2):
   `POST /api/work` with `project: core` answers a usage error whose message
   contains `tcw -C`, and creates nothing; `POST /api/work/<item>/blocks`
   answers 404; `PATCH /api/capabilities/<core.capabilities/cli/x, encoded>`
   answers 403 with the error kind `read-only` and a message containing
   `belongs to project 'core'` and `tcw capabilities set`. A unit test reads
   the server's route table and finds every route of Design 1.2's table
   marked a write and no other route marked one; a second test registers a
   write route whose code would write a file, sends it a request naming
   `core.capabilities/cli/x`, and finds the answer 403 and the file
   unwritten, so the router, not the route, makes the check. Client unit tests: the create
   form shows no project selector; the item page has no "Blocks (add)"
   section and still lists the item's `blocks`; in Jira mode the create
   form and the edit form accept a blocker in another project, showing the
   other-project warning, where today they refuse it.
5. **The removed options.** `tcw work new 'x' --project core` exits 2, says
   `work new --project is removed`, `tcw -C` and `--parent`, creates nothing in either
   project, and returns without reading standard input (a test pipes a stream
   that never closes). `tcw work edit <a> --blocks <b>`, with `<b>` in the
   same project, exits 2, says `work edit --blocks is removed` and
   `--blocked-by`, does not contain `tcw -C`, and changes neither item; with
   `<b>` in another project the message also contains `tcw -C`.
   `tcw work new --help` and `tcw work edit --help` mention neither option.
6. **A part in another project, files backend.** Two projects side by side,
   `planning` (epic `<e>`, item `<o>`) and `app`. From `planning`:
   `tcw -C ../app work new 'Add export' --parent planning.work/<e> --blocked-by planning.work/<o> --priority high`
   exits 0, prints `app.work/<date>-add-export`, and that item's state file in
   `app`'s store holds `parent: planning.work/<e>`, `blocked-by:
   [planning.work/<o>]` and `priority: high`; with `--nest` added for a second
   part, the command exits 0, says `not nested:`, and makes the folder at the
   top of `app`'s store. `planning`'s files are unchanged.
7. **Jira parents and blockers Jira cannot link are recorded.** With the
   suite's Jira fake: `app` on site A, `far` on site B, and `files` a
   files-backend project, all side by side, each with an item (`far`'s is
   `far.work/<FK>-…`, `files`'s is `files.work/<f>`). In `app`:
   - `tcw work new 'x' --parent files.work/<f> --blocked-by far.work/<FK>-…`
     exits 0; the fake records one create with no parent and no issue link,
     of the project's default issue type; the new folder's state file holds
     exactly `tcw-version`, `ticket`, `parent: files.work/<f>` and
     `blocked-by: [far.work/<FK>-…]`; standard error says `is not a ticket
     on` and `Jira shows no link for it` for each; `tcw work show` of the new
     item prints both values, and `tcw work list --parent files.work/<f>`
     prints the new item;
   - `tcw work edit <a> --parent far.work/<FK>-…` on an item `<a>` whose
     ticket has a Jira parent link to a ticket on site A: the fake records the
     link's removal, then the state file holds `parent: far.work/<FK>-…`;
     `tcw work edit <a> --parent <ticket on site A>` then makes the link and
     leaves no `parent` in the state file; `--parent none` leaves neither;
   - a parent that is a ticket of another TCW project on site A is linked as
     today and the state file holds no `parent`;
   - with `files`'s folder removed and the manifest placing it at `../files`,
     `tcw work new 'y' --parent files.work/<f>` exits 5, naming `files`, and
     the fake records no create;
   - with the fake's network refusing after the link's removal in the second
     bullet, the command stops (exit 5) with the state file unchanged; running
     it again with the fake healthy writes the state file and records no
     second removal;
   - a fourth project `inh` beside them, in Jira mode, whose `work.jira` it
     inherits from a parent project that is not on this machine, holding an
     item folder `inh.work/<IK>-…`: `tcw work new 'z' --parent
     inh.work/<IK>-…` in `app` exits 7 and the fake records no create;
   - a fifth project `caps`, on site A but with its site written with the
     host in capital letters: a parent that is one of its tickets is linked
     as on site A, with no `parent` in the state file;
   - served from `app`, `POST /api/work` with `parent: files.work/<f>`
     answers success with a warning containing `Jira shows no link for it`.
8. **`-C` with a path.** From an empty folder that is no project,
   `tcw -C <path to demo> work list` prints what `tcw work list` prints in
   `demo`. `tcw -C a -C b work list` runs in `a/b`. `tcw -C missing work list`
   exits 2 and says `no such folder`. A test calling `tcw.cli.main(["-C", …])`
   in-process finds `os.getcwd()` unchanged afterwards.
9. **`-C` with an address.** Two projects side by side, `workspace` and `app`
   as in AC 3. From `workspace`: `tcw -C tcw://app.path/ work list` prints
   `app`'s items; `tcw -C tcw://app.work/x work list` exits 2 naming `.path`;
   `tcw -C tcw://app.work.path/ work list` exits 2 and says `is a folder of
   project 'workspace'` and `tcw://app.path/`; with a manifest entry placing
   `gone` at `../gone`, which does not exist, `tcw -C tcw://gone.path/ work
   list` exits 5 naming `gone`; `tcw -C tcw://cor.path/ work list`, naming a
   project nothing declares or finds, exits 1 and says `check the spelling`.
   From a folder that is no project, `tcw -C tcw://app.path/ work list` exits 1
   and says `give the folder's path instead`. With a third project
   `lone` beside them whose `work.path` is `../board`, a folder outside every
   project, `tcw -C tcw://lone.work.path/ work list` from `lone` exits 2 and
   says `which is in no TCW project`. From a folder holding a 3.x project
   (a `tcw-config.yaml` at its root and no `.tcw/`), `tcw -C tcw://app.path/
   work list` exits 1 with TCW-106's 3.x refusal, and `tcw -C <path to app>
   work list` from the same folder exits 0. None of these commands starts a
   process other than read-only `git rev-parse` (Design 4.6): a test records
   every call of `subprocess.run` and `subprocess.Popen` and finds each one
   allowed by the rule of `_allowed` in `tests/serve/test_no_process.py`
   with `status` left out.
10. **`-C` runs entirely as that project.** With `user.name: Alice` in `app`'s
    `.tcw/tcw-config.local.yaml` and `user.name: Bob` in `workspace`'s, from
    `workspace`, `tcw -C tcw://app.path/ work new 'x' --assign-me` makes an
    item assigned to `Alice`. A `pre` check bound in `app` to the next stage
    runs on `tcw -C tcw://app.path/ work advance <a>` with `TCW_PROJECT_ROOT`
    equal to `app`'s root, and a `pre` check bound in `workspace` does not run.
    From `workspace`, with an empty folder `fresh/` inside it,
    `tcw -C fresh init --id fresh --work-path board` creates
    `fresh/.tcw/tcw-config.yaml` and `fresh/board/`, and no `board/` in
    `workspace`: a relative argument is read from the folder `-C` chose.
11. **Renaming an item with nested items, files backend.** Epic
    `<date>-old-words` holding part `P`, which holds part `Q`; `P`'s `parent`
    is the epic and `Q`'s is `P`; item `R` has `blocked-by: [<P's id>]`; `R`'s
    `spec/spec.md` holds a link `[p](tcw://demo.work/<date>-old-words/P)`, the
    same link inside a fenced code block, a link to
    `tcw://demo.work/<date>-old-words-two`, and the text
    `demo.work/<date>-old-words/P` in prose. `tcw work rename <date>-old-words
    new-words` exits 0 and prints exactly three lines, the epic's, then `P`'s,
    then `Q`'s, each `<old> -> <new>`; `P`'s and `Q`'s `parent` and `R`'s
    `blocked-by` hold the new identifiers; the first link is rewritten; the
    link in code, the `-two` link and the prose are unchanged; standard error
    names the prose line and the code line as not rewritten, does not name the
    `-two` link, and contains `references in other projects are not
    rewritten`. `tcw validate` passes. `--json` prints `"schema": 2` and the
    three pairs under `moved`. From the same starting state with the epic's
    state file holding `id: <date>-old-words`, the rename leaves it holding
    `id: <date>-new-words`, and `P`'s state file, holding `id: P`, unchanged.
    From the same starting state with `R`'s state file made unwritable: exit
    1, nothing on standard output, standard error names `R`'s state file,
    the files already rewritten and `run the same command again`, and the
    epic's folder is still at `<date>-old-words`; with `R`'s file writable
    again, the same command exits 0, prints the three lines, and leaves every
    file as the first run of this criterion did.
12. **Renaming an item with nested items, Jira.** With the Jira fake, epic
    `EK` holding `PK` holding `QK`, each ticket's `TCW Item` its full
    identifier, and an item `R` whose `spec/spec.md` links `PK`'s full
    identifier. `tcw work rename <EK-folder> new` reads the three tickets in
    one search, then edits them in the order `EK`, `PK`, `QK`, each after a
    read of that ticket, then rewrites `R`'s link, then moves the folder;
    each `TCW Item` is the new identifier. Then, each from the same starting
    state:
    - the fake failing the second edit: exit 1, nothing on standard output;
      standard error names `EK` as holding the new value and `PK` and `QK` as
      still to be set, says the folder is still at the old place and `run the
      same command again`; no ticket is set back (the fake records no second
      edit of `EK`), `R`'s link is unchanged, the folder unmoved. Running the
      same command again with the fake failing the third edit: exit 1, and
      the message names `EK` (set by the first run) and `PK` (set by this
      one) as holding the new value and `QK` as still to be set. A third run
      with the fake healthy exits 0, the fake records an edit of `QK` only,
      `R`'s link is rewritten, and the folder moves;
    - the folder's `os.rename` failing (the test patches it): exit 1, every
      ticket keeps its new value, `R`'s link holds the new identifier, the
      message names the three tickets and `R`'s file; with `os.rename`
      restored the same command exits 0 and the fake records no edit;
    - `QK`'s `TCW Item` holding a 3.x value: exit 3 before any edit, the
      fake records none, nothing in the repository changes, and the message
      names `QK` and `tcw migrate`;
    - `PK`'s `TCW Item` holding another 4.0 identifier: exit 3, no edit, the
      folder unmoved, and the message names `PK` and `tcw validate --remote`;
    - the fake answering no ticket for `PK`: exit 4 before any edit, saying
      `Jira has no ticket PK`;
    - two runs at once: the fake changing `EK`'s `TCW Item` to another value
      after the first search, when it answers the read of `EK` that comes
      just before `EK`'s edit (so that read sees the other value): exit 3,
      the fake records no edit, `R`'s file and the folder are unchanged, and
      the message names `EK`, its new value, `another command may be moving
      this item` and `tcw validate --remote`, and does not contain `run the
      same command again`;
    - the same with `PK`'s value changed instead, so that `EK` was set by
      this run first: exit 3, and the message names `EK` as set by this run,
      contains `pull its commit`, `tcw validate --remote` and `in Jira set
      each ticket it reports to the identifier its folder now has`, and
      does not contain `run the same command again`;
    - the second way out of that stop: from the state it leaves after the
      other command finished (`EK` holding this run's identifier, `PK` and
      `QK` the other command's, the folder at the other command's place),
      running this command again on the item at that place exits 0, every
      ticket's `TCW Item` names this command's identifiers, and the folder
      is at this command's place;
    - the folder's `os.rename` failing because the folder is already gone
      (the test removes it first): exit 4, and the message says `is no
      longer at`, not `still at`.
13. **Moving work items.** Files backend, and the same with the Jira fake
    where noted. An epic `<e>`, items `<a>` and `<b>` at the top, `<a>`'s
    `parent` is `<e>`:
    - `tcw work move <a> --into <e>` puts `<a>` inside `<e>`'s folder and
      prints one line; `tcw validate` has no folder-and-parent warning; with
      the Jira fake, `<a>`'s ticket's `TCW Item` is the new identifier;
    - `tcw work move <e>/<a> --top` moves it back;
    - `tcw work move <b> --into <e>` succeeds and says TCW-111 Design 3.2's
      warning, `parent: decides`; `<b>`'s `parent` is unchanged;
    - `tcw work move <b> --into 2026/q4` creates organising folders `2026/` and
      `2026/q4/`; moving it back with `--top` removes both, which are empty,
      and names them; with the item folder's `os.rename` made to fail (the
      test patches it), `tcw work move <b> --into 2026/q4` exits 1 and
      neither `2026/q4/` nor `2026/` is left;
    - each of `--into <e>/drafts` (a missing folder inside an object),
      `--into <e>/plan` (a fixed folder), `--into resources`, `--into <a>` for
      `<a>` itself, and both or neither of `--into` and `--top` exits 2 and
      changes nothing;
    - with a folder named like `<b>` in a different letter case already inside
      `<e>`, `tcw work move <b> --into <e>` exits 3.
14. **Repairing a rename and a nested create that met on merge** (TCW-111
    AC 16a's layout). `tcw work move <date>-old-words/<part> --into
    <date>-new-words` exits 0 and removes the emptied `<date>-old-words/`;
    after `tcw work edit <date>-new-words/<part> --parent <date>-new-words`,
    `tcw validate` passes.
15. **Taxonomy rename and move.** Term `invoice` holding term `invoice/refund`
    (whose `parent` is `demo.taxonomy/invoice`); term `pay` with `relatesTo:
    [demo.taxonomy/invoice]` and `vocabulary: [demo.taxonomy/invoice/refund]`;
    a capability with `Subject: [demo.taxonomy/invoice/refund]`; an item's
    `capabilities.yaml` with `taxonomy: {changed: [demo.taxonomy/invoice]}`;
    a capability description linking `tcw://demo.taxonomy/invoice/refund`.
    `tcw taxonomy rename invoice bill` prints two lines and rewrites every one
    of those references, and every other line of each file it rewrote is
    unchanged; `tcw taxonomy show bill` prints the same `name` as before. Then `tcw taxonomy move bill/refund --top` prints one line,
    rewrites the references to `refund`, leaves `refund`'s `parent` as
    `demo.taxonomy/bill`, and says no warning (an object at the top has no
    folder parent). `tcw validate` passes after each. With `invoice`'s state
    file holding `id: invoice`, the rename leaves `id: bill`. With the
    folder's `os.rename` made to fail, `tcw taxonomy rename invoice bill` exits 1,
    the references already name `bill`, the folder is still `invoice`, and
    the message says `run the same command again`; doing so exits 0, moves
    the folder, and rewrites nothing further.
16. **Capabilities rename and move.** Capability `cli/x` holding `cli/x/z`;
    `cli/y` with `Superseded by: demo.capabilities/cli/x` and `Blocked by:
    demo.capabilities/cli/x/z`; `roles/admin`, named by `cli/y`'s
    `Roles: ['!demo.capabilities/roles/admin']`. `tcw capabilities rename cli/x w`
    prints two lines and rewrites both fields; `tcw capabilities rename
    roles/admin owner` rewrites `Roles` to `['!demo.capabilities/roles/owner']`;
    `tcw capabilities move roles/owner --into cli` exits 3 naming `Roles` and
    `cli/y`, and changes nothing. `tcw validate` passes after each success.
17. **Overrides cannot be moved, nor made by a move.** `app` with parent
    project `core`, `core` holding `cli/x` and `cli/v`, `app` holding its
    override `cli/x` and its own `cli/y`: `tcw capabilities move cli/x --into
    work` and `tcw capabilities rename cli/y v` each exit 3 naming
    `core.capabilities/cli/x` or `core.capabilities/cli/v`, and change nothing.
    With `core`'s folder removed, `tcw capabilities rename cli/y v` exits 7.
18. **Length.** A files-backend epic holding a part whose full identifier is
    250 characters: a rename of the epic that would make the part's identifier
    256 characters exits 2 naming the part's new identifier and 255, and moves
    nothing; with the Jira fake, the same exits 2 and the fake records no edit.
19. **Unreadable records stop a move.** With one capability's state file
    holding an unparsable `tcw-version` (TCW-106 Design 3.4 row a),
    `tcw taxonomy rename invoice bill` exits 1 naming that file and moves
    nothing; with an item whose `capabilities.yaml` is not valid YAML,
    `tcw capabilities rename cli/x w` exits 1 naming it.
20. **A folder whose name breaks the grammar.** With a capability folder
    `cli/has.dot`, `tcw capabilities rename cli/has.dot has-dot` exits 0 and
    prints `demo.capabilities/cli/has.dot -> demo.capabilities/cli/has-dot`;
    `tcw capabilities show cli/has.dot` still exits 2 (TCW-110 AC 18);
    `tcw capabilities rename cli/x has.dot` exits 2 and changes nothing.
21. **Other projects' references are left, and reported there.** Two projects
    side by side, `app` linking `[x](tcw://core.capabilities/cli/x)` in a
    capability description. In `core`, `tcw capabilities rename cli/x y`
    exits 0, prints `core.capabilities/cli/x -> core.capabilities/cli/y`, and
    `app`'s file is byte-for-byte unchanged; `tcw validate` in `app` then exits
    1 reporting the link.
22. **`tcw projects list --json`** has no `read-only` key in any row, and the web app's project answer has no
    `readOnly`.
23. **Shipped text.** `tcw work stage prompt plan <item>` contains
    `tcw -C tcw://<id>.path/ work new`, `--parent <slug> --nest` and
    `TCW records it in the part's folder`, and does not contain `--project`,
    `uncommitted` or `only a ticket on its own site`; `tcw work procedure audit-backlog`
    contains `tcw -C` and not `--project`; `docs/lifecycle/abstraction.md`'s
    interface list has a **move** entry and no **rename** entry, and does not
    contain `uncommitted changes before creating an item in another project`.
    `tests/test_documented_cli_surface.py` passes with `--project` and
    `--blocks` hidden from `--help`: no live document writes either in a
    `tcw` command (Design 9.5), and `docs/capabilities/work/delegate-a-work-item-to-another-project/`
    no longer exists.
24. **The sweep.** After the change, a search under `tcw/`, `web/client/src/`,
    `scripts/` and `evals/` finds no definition or call of `delegate`,
    `open_for_update`, `blocks_target`, `delegate_to_jira`,
    `uncommitted_changes`, `_cannot_make_item` or a backend method `rename`,
    no route ending `/blocks`, and no message `Jira links only tickets on one
    site`; every write site in the plan's list calls
    the ownership check, and a reviewer checks the list against a fresh
    search.
25. **No hooks and no git in a move.** In `demo`, with a `post` hook and a
    `pre` check bound to every stage, and a test recording every call of
    `subprocess.run` and `subprocess.Popen`: `tcw work rename`, `tcw work
    move`, `tcw taxonomy rename` and `tcw capabilities move` each exit 0,
    start no hook or check process, and start no process at all other than
    read-only `git rev-parse` (Design 4.6, by AC 9's rule).
26. **One definition of the reference fields.** A unit test finds that the
    definition of Design 6.3 holds exactly the rows of TCW-110 Design 5.1's
    table, the `parent` of terms and capabilities, and the Jira state file's
    `parent` and `blocked-by`. For each row, a fixture record holding that
    field: with a value naming no object, `tcw validate` reports that file
    and field; with a value naming an object that is then renamed, the
    rename rewrites it. A record holding the old identifier at a field the
    definition does not name (a capability's `name`, a key of
    `capabilities.yaml` other than its lists) keeps it after the rename, and
    the rename lists it as a mention. A second test adds a row to the
    definition naming a field of a fixture record that held the old
    identifier unchanged in the first run, and finds both `tcw validate` and
    a rename reading it, with no other change: the rename now rewrites it.
27. **`tcw validate` of recorded references.** In AC 7's `app`: a recorded
    `parent` naming `files.work/<f>` passes; one naming an item `files` does
    not have is a warning naming it; with `files`'s folder removed (its
    manifest entry kept) it is "could not check"; a recorded `parent` naming
    a ticket of a TCW project on site A is an error saying `make it a Jira
    link`; with the fake giving that item's ticket a Jira parent link while
    its state file records a `parent`, `tcw validate --remote` reports an
    error naming both, and `tcw validate` without `--remote` makes no request
    to the fake.
28. **The suite, as CI runs it**: bare `pytest` after `pip install -e
    '.[dev]'`, and `pnpm install --frozen-lockfile` then `pnpm check:build`,
    pass on `v4`; the web client's unit tests, type check and lint pass too.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1.1 one ownership check, exit 3, nothing written; the check before the lookup | 1 (no backend of `core` opened), 2 (`core` removed), 3, 24 |
| 1.2 every writer, CLI and web; creators make no call | 1 (work CLI), 2 (tree CLI), 4 (web routes), 24 (the list, creators listed as creators) |
| 1.3 one message shape, a reason clause, the three tails; TCW-112's two refusals reworded; locating never changes the exit | 1 (found, not on this machine, unknown, graph problem with its own message), 2 (the shape, `rm` and `set`; `rm` with `core` removed) |
| 1.4 web write routes refuse; the router makes the check; the inherited capability's hint | 4 |
| 1.5 overriding is allowed; other inherited writes refused | 2, 17 |
| 1.6 planning workspace | 3 |
| 1.7 a parent or blocker in another project is allowed | 6, 7 |
| 1.8 TCW-108's interim rule, `read-only`, `readOnly` removed; provisioning's use renamed | 22, 24; the renamed provisioning test is unchanged in behaviour, so 28 (its existing tests pass) |
| 2.1 `new --project` refused before reading input; message names `work new` | 5 |
| 2.2 `edit --blocks` refused, same project and other; values read only for the message | 5 |
| 2.3 web: create into another project, `/blocks`, client form; Jira-mode blocker accepted | 4 |
| 2.4 code removed; no uncommitted-changes check | 24 |
| 3.1 the flow and its replacement table; the part's project must locate the epic's | 6 (steps a, d, e), 7 (a Jira part whose epic's project is not here, exit 5); steps b, c, f: n/a, they describe what no longer happens or point at 2.2, tested by 5 and by the removal of `_check_target` (`tcw/work/open.py:139-159`, 24) |
| 3.2 files backend stores any project's parent | 6 |
| 3.3 Jira: same-site values are links, others recorded; sites compared by host ignoring case; the owner's configuration read for itself, exit 7 when undecided; the state file's keys; writing, with Jira first and the message, also in the web answer; reading and `list --parent`; validate's checks; a move rewrites none | 7 (writing, reading, the stop and re-run, exit 7, the site's letter case, the web warning), 27 (validate), 26 (the rows), 12 (a move edits only `TCW Item`) |
| 4.1 form, repeatable | 8 |
| 4.2 a path; missing folder | 8 |
| 4.3 an address; object address; each outcome; no project here; a 3.x project at the start | 9 |
| 4.4 an address runs as its project; a folder in no project | 9 |
| 4.5 everything runs as there; in-process folder restored | 8 (restored), 10 |
| 4.6 no network, no git but read-only `git rev-parse` | 9 (every process allowed by the rule); no network: 8 and 9 run with no Jira fake and reach no site |
| 5.1 the six commands; name rules; title kept | 11, 13, 15, 16 |
| 5.2 nested objects change; `parent` never changes; 3.2 warning; a rename's own `id` | 11, 13, 15 |
| 5.3 destinations; organising folders made and removed, also on a stop; refusals | 13, 14 |
| 5.4 a owned | 1, 2 |
| 5.4 b name or destination allowed | 13 |
| 5.4 c folder free, ignoring case; same name refused | 13 |
| 5.4 d 255 characters, nested included | 18 |
| 5.4 e unreadable records | 19 |
| 5.4 f field rules (`Roles`, `When`) | 16 |
| 5.4 g overrides; exit 7; a work move's exception for an inherited `work.jira` | 17; the exception is TCW-109's own exit 7, tested there (TCW-109 AC 14, a missing parent in Jira mode) |
| 5.4 h Jira ticket check | 12 |
| 5.5 a source whose name breaks the grammar | 20 |
| 5.6 output, `--json`, closing line; nothing printed on a stop | 11, 12, 21 |
| 5.7 no hooks, no git but read-only `git rev-parse` | 25 |
| 5.8 one order, folder last; nothing set back; the stop message names every run's writes and where the folder is; a re-run finishes; a clash with another command gives other advice | 11 (files), 12 (Jira, the clash, the folder already gone), 15 (taxonomy) |
| 6.1 backend references and repository references, every field | 11, 15, 16, 26 |
| 6.2 exact matching; links in code skipped | 11 |
| 6.3 one definition of the fields, built here; the checkers and the files backend's rewrite read it; matched by field, not by value | 26 (a row added is checked and rewritten; a value at an unnamed field is left and listed) |
| 6.4 mentions listed | 11 |
| 6.5 other projects untouched | 21 |
| 6.6 only changed values written; each file replaced in one step | 15 (every other line unchanged), 11 (the link's text and the other links unchanged); the one-step write is a plan-level test (the stop helper's failures, plan Step 16) |
| 7.1 backend `move` replaces `rename`; `before_folder`; twelve operations | 11, 12, 24 |
| 7.2 files backend, references before the folder | 11, 13 |
| 7.3 Jira read, paged; 3.x, other value and missing ticket refused; a read before each edit; two runs; re-run | 12; paging is a plan-level test (plan Step 17) |
| 7.4 `--remote` | n/a: unchanged here; the comparison is `tcw/work/jira/remote.py:415-421`, which TCW-111 Design 6.5 extends and TCW-111 AC 10 tests |
| 8 tree stores' `move` | 15, 16 |
| 9.1 plan stage prompt | 23 |
| 9.2 `audit-backlog` | 23 |
| 9.3 `abstraction.md` | 23 |
| 9.4 help and contracts | 5 (`--help`), 28 (`tests/test_cli_help_standard.py` covers every command's contract) |
| 9.5 the passages that write a removed option, changed; the removed capability's record deleted | 23 |
| 10 interfaces from earlier items | 2, 15, 17 (TCW-112), 9 (TCW-107, TCW-110), 10 (TCW-109) |
| 11 the sweep | 24 |

## Risks

- **The ownership check's list of writers drifts.** A writer added later
  that forgets the check writes into another project. AC 4's test over the
  route table, and the plan's list of CLI write sites, are the guard; the plan
  makes the check part of the shared code each writer already calls (opening
  a backend for update, or a tree store's write target), so a new writer gets
  it without asking.
- **Many Jira requests per move.** A move of an epic with many nested parts
  makes one read and one `TCW Item` edit per ticket, after one search. The
  5.8 order makes a stop recoverable, but a long run can still stop; the
  message names the tickets, and a re-run finishes.
- **Two runs at once can still meet between a read and an edit** (7.3). The
  read before each edit makes a second run stop at its first ticket, but
  Jira's edit cannot be made conditional on the value read, so two runs
  whose read and edit of the first ticket fall in the same moment can both
  go on. `tcw validate --remote` then reports the tickets and folders that
  disagree.
- **A move no longer sets anything back** (5.8). Today a Jira rename whose
  folder move fails sets its ticket back; now the ticket keeps the new value
  until a re-run finishes the move. The message says so and names the
  command.
- **`--blocks` within one project is lost** (Design 2.2, the user's
  decision). The replacement is one command on the other item.
- **A recorded parent is invisible to Jira** (Design 3.3). A Jira part whose
  epic is in files or on another site shows no parent in Jira's own views,
  boards and JQL; only TCW's `show`, `list --parent` and the web app show
  it. Every write that records one says so.
- **The reference-field definition touches every checker** (Design 6.3).
  Moving about fifteen checkers onto one definition changes code TCW-110 has
  just changed; the plan moves one checker at a time and keeps each
  checker's existing tests green before the next.
- **Test churn.** The delegation tests (`tests/work/jira/test_jira_delegation.py`,
  `tests/work/test_open.py`, parts of `tests/work/test_cli_items.py`,
  `tests/test_upstream_projects.py`, `tests/test_projects_list.py`) and the
  web form's tests go or change; `tests/test_shipped_prompts.py:332-337` and
  `tests/test_shipped_text.py:338` pin the old step 6 text. The plan lists
  each, and reads each failure before changing an assertion.
- **The current folder is process-wide.** Design 4.5 changes it for the whole
  process. `tcw serve` started with `-C` serves from that folder, as intended;
  code that runs `main` in-process (the suite, the eval harness) gets its
  folder back (4.5).
- **Rewriting Markdown in place.** A link rewrite changes a file a person
  wrote. Only the address inside `](tcw://…)` outside code changes, compared
  by parsed identifier (6.2); the plan tests that every other byte is kept.
- **This repository's own records** keep their 3.x forms until TCW-116, and
  its lifecycle is driven by the `tcw` first on `PATH` (TCW-110 Notes,
  decided 2026-10-22), which still has `--project`. Nothing here changes
  that.

Handoffs, which the dispatching session records on each ticket when this
spec is accepted:

- **TCW-108 (a note, no work):** its handoff is answered: Design 7.1's interim
  rule, `read-only` (8.2) and `readOnly` (8.5) are removed (Design 1.8).
- **TCW-111 (a note):** each of its four handoffs is answered: (1) the
  delegation length fitting goes with `--project` (2.4); (2) this item lands
  in 4.0, so TCW-111's release note need not mention the refused rename; if
  this item is ever moved out of 4.0, its own `upcoming/` entry must say that
  renaming an item with nested items is refused; (3) mentions are searched by
  old id-path (6.4); (4) a move never deletes, so it uses the walk to find the
  identifiers that change and moves everything else in the folder unchanged
  (5.2), with no need of `removal_blockers`. The rename refusal of its Design
  5 row 7 and its AC 16's first part are replaced here. Step 6 of the plan
  prompt is combined as Design 9.1 writes it. Its Design 1.2 rule that a Jira
  item's state file holds exactly `tcw-version`, `ticket` and optionally
  `id` is widened here to allow recorded `parent` and `blocked-by` (Design
  3.3); TCW-111 needs no change, since both land in 4.0.0.
- **TCW-110 (a note):** `tcw -C` uses its address parser and folder
  resolution (4.3); a folder whose name breaks the grammar is renamed with
  `rename` or `move` (5.5), answering Design 1.6. Its Design 5.1 table
  becomes one definition in code here (6.3), with one more row, the Jira
  state file's recorded `parent` and `blocked-by` (3.3).
- **TCW-112 (a note, and two corrections for its spec):** its Design 2.7 and
  4.2 answer what this item needs (Design 10.2), and nothing more is asked.
  Design 1.3 here rewords two of its refusals, `set`'s for a capability the
  active project does not inherit and `rm`'s for another project's object,
  into the ownership check's one shape, so their tests change once this item
  lands. Its revised plan puts both refusals in `override_target` and
  `removal_target`, and `find_tree_writable` refuses nothing itself; this
  item makes those two refusals calls of the ownership check, and Design
  1.1's "the check comes before the lookup" holds because
  `removal_target` refuses another project's full identifier before
  reading anything. Two things in its spec to correct: its handoff's "a move of an
  override is a move of an ordinary object" disagrees with Design 5.4 g
  here, which refuses moving an override away from its original's path and
  moving an object onto an inherited path; and its AC 33 expects a `PATCH`
  of an inherited capability to answer 409 "as today", while today's code
  answers 403 (`read_only`, `tcw/serve/records.py:193-196`), which AC 4 here
  also expects.
- **TCW-113:** lands after this item (the order above; its blocker link on
  Jira records it). Every web write route has the ownership check, made by
  the router for every route marked a write (1.4); the client's display of
  other projects' objects as read-only is TCW-113's, and can rely on the
  server refusing a write. A write route TCW-113 adds is marked a write in
  the route table, and so gets the check.
- **TCW-115:** `tcw project list --json` carries no `read-only` (TCW-108's
  handoff to TCW-115 named it; Design 1.8 removes it). The refusal of Design
  1.3 may add `tcw project provision <id>` for a project not on this machine
  once that command exists. `tcw provision`'s choice of which family
  members' declarations to follow keeps TCW-108's two-sided-link test, now
  named `reached_by_both_sides` (Design 1.8); whether provisioning keeps
  that rule is TCW-115's to decide when it replaces the command.
- **TCW-116 (a note, no work):** a move is refused while any of its tickets
  holds a 3.x `TCW Item` (7.3), so no folder moves away from what its 3.x
  value names, and migration can keep converting a value by the folder it
  names.
- **TCW-117:** the migration guide shows Design 3.1's table, step for step,
  and the `--blocks` replacement. Design 9.5 has already changed, only as
  far as naming a working command, every passage that wrote a removed option
  as a `tcw` command (the plan's Step 7 lists them); TCW-117 rewrites them
  for 4.0 as it does the rest. The skills and guides that teach
  `--project` or `--blocks` change (`skills/work/SKILL.md:94`, `:107-112`;
  `skills/work/references/commands.md:11`, `:19`;
  `skills/configure/references/projects.md:170`, `:199`;
  `skills/capabilities/SKILL.md:153`, `:181`, whose "ask another project for
  wording" flow becomes `tcw -C` into that project when it is on this machine,
  and that project's own issue tracker otherwise, as UC-7 asks;
  `docs/guide/jira.md:235`, `docs/guide/cli.md:150`, `docs/guide/work.md:332`,
  `:351`, `docs/guide/multi-repo.md:141-187`, `README.md:608`); the work
  skill teaches `tcw work move` and `rename` for nested items; the Jira
  guide (`docs/guide/jira.md`) says that a parent or blocker Jira cannot
  link is recorded in the item's folder and is not shown by Jira itself
  (Design 3.3); and `docs/use-cases.md` UC-3 and UC-4's requirements about
  cross-project filing are rewritten. S-3's requirement that a filing across
  backends works stands, and is met (Design 3.3).

## Notes

### Decided by the user, 2026-10-22

1. **A cross-backend parent is kept, not refused** (Design 3.3). Some of the
   user's real setups link work items across backends: a files-backend
   project's items under a Jira epic, and tickets on two Jira sites. So a
   Jira item keeps a parent, or a blocker, that Jira cannot link, as a
   recorded reference in its state file by the named item's full
   identifier; a value Jira can link stays a Jira link, so each value has
   one place. This reverses the first draft's refusal. Its three reasons are
   answered: two answers cannot arise, because the place is decided by what
   is named and `tcw validate` reports a value in the wrong place; the
   widened state file lands in 4.0.0 with TCW-111's, so nothing migrates;
   and the third, that refusing is today's behaviour, weighs nothing against
   setups the user already has. Blockers are included with
   parents because they are the same kind of field, kept by the same code,
   and the user's setups name blockers across the same boundary.
2. **`--blocks` is removed entirely, including within one project** (Design
   2.2). The design's reason, "because each one changes another project",
   does not cover a target in the active project. The user chose removal
   anyway: one command on the other item replaces it, and an option that
   works for some targets and refuses others is harder to teach.

### Decided by the dispatching session, 2026-10-22

3. **The landing order is TCW-106, TCW-107, TCW-110, TCW-108, TCW-111,
   TCW-109, TCW-112, TCW-114, then TCW-113.** TCW-112 is recorded on Jira as
   a blocker of this item, since Design 5.4 g and 1.5 need its Design 2.7
   and 4.2; TCW-113 is blocked by this item, since its views of other
   projects' objects rely on the server refusing their writes (1.4).

### Decisions the design left to this spec

1. **A Jira part whose parent Jira cannot link keeps it as a recorded
   reference** (Design 3.3), the user's decision above. This is the question
   the design named.
2. **`move` and `rename` are separate, in every namespace** (5.1): rename
   changes only the last part, move only the folders above it, so neither
   command can change both by accident, and the work item's date or key rule
   applies only to rename. TCW-27 proposed one `mv <old> <new>`; two commands
   keep the work item's rules simple and give all three namespaces one shape.
3. **A move never changes `parent`** (5.2), the mirror of TCW-111 Design 3.4,
   so the CLI never decides a relationship from where a folder is put
   (TCW-99 principle 1). The warning names the fix.
4. **An override cannot be moved, and a move cannot make one** (5.4 g). The
   design says an override is matched by path; a move would silently change
   whether an object is one. Refusing can be relaxed later.
5. **An address given to `-C` runs as the project it names** (4.4), from the
   design's "the command runs entirely as that project". A plain path runs as
   whatever is there.
6. **References rewritten are those `tcw validate` checks** (6.1, 6.3), in the
   active project's three stores; prose and code are listed as mentions, never
   rewritten (6.4), as `tcw work rename` already does.
7. **Everything that names the moved objects first, the folder last, and
   nothing set back** (5.8): Jira tickets, then the backend's and the
   repository's references, then the folder, in every namespace and both
   backends; a stop is finished by running the same command again. Today's
   rename moves a files item's folder before rewriting, and sets a Jira
   ticket back when its folder cannot move; both change, because a re-run
   finds an object only at its old place, and a set-back can overwrite a
   run that has finished. The design's "local files first, Jira last" is for
   `tcw migrate`, whose re-run can always find its input; a move's re-run
   could not find a folder that has already moved.
8. **A ticket still holding a 3.x `TCW Item` stops a move before any
   change** (7.3), naming `tcw migrate`. TCW-110 Design 5.2's decision that
   such tickets are left out is about listing them; for a write, leaving one
   out would move a folder its ticket still names. Such tickets exist only
   while a migration has stopped, which running it again finishes. Refusing
   can be relaxed later; tickets left out of step could not be taken back.
9. **The removed options give a message, not "unrecognized arguments"**
   (Design 2), because agents were taught them in 3.0.1 and 3.0.2, and the
   message is how such an agent learns the one change.
10. **Empty folders a move leaves behind are removed** (5.3), so a repair such
    as AC 14 does not leave a folder that TCW-111's validate reports; only a
    completely empty folder is removed.
11. **Moving into another project is not offered** (Non-goals): it would be
    two writes in two projects.
12. **Two runs at once are caught by a read of each ticket just before it
    is edited** (7.3), rather than a lock. A lock file would hold on one
    machine only, while S-7's two people work from two clones against one
    board, and a lock left by a stopped run would block every later one. The
    read costs one request per ticket.
13. **`-C`'s address resolution reads the starting project as any command
    does** (4.3), so a 3.x project or a configuration problem there stops
    it; a path reads nothing there.

### Questions for TCW-99

None remain. The two the first draft asked (`--blocks` within one project,
and where TCW-113 lands) are decided above.

### Revised after the plan review (2026-10-22)

The plan's adversarial review returned NOT DONE, and four of its findings
were spec issues; each was checked against the repository first.

- **The process rule** (Design 4.6, 5.7, AC 9, AC 25): TCW-107's
  linked-worktree probe is 3.x code that starts `git rev-parse` on every
  registry built, so "no git process" could not pass. The rule is now "no
  process other than read-only `git rev-parse`", the rule the web app's
  process test already applies.
- **A work move and an inherited `work.jira`** (5.4 g, UC-6), and what the
  Jira backend does when the named project's `work.jira` is undecided (3.3,
  exit 7). Sites are compared by host, ignoring case.
- **The removed options' values** are read only to word their messages
  (2.2), and the Jira-mode web forms now accept a blocker in another project
  (2.3, AC 4).
- **Creators make no ownership call** (1.2), decided by the dispatching
  session on the review's recommendation: a call that can never refuse
  proves nothing, and the sweep lists the creators instead.
- **The check comes before the lookup** (1.1), so AC 1's "locating never
  changes the exit" can hold, and a graph problem is named as one (1.3).
- **The documents** (9.5): the passages that write a removed option as a
  command are changed here, because hiding the options otherwise fails the
  documented-command check; the reason for not keeping the options visible
  instead is given there.
- **The stop after a clash with another command** (5.8, 7.3) no longer
  says to run the same command again, which would only be refused; and the
  message says where the folder is only after checking.
- **Matching by field** (6.3) and the files backend's rewrite reading the
  definition (6.3, 7.2); one-step file writes (6.6); a paged search (7.3);
  the web answer carrying the recorded-reference note (3.3);
  `read_only_reason`'s provisioning caller kept under a new name (1.8).

Decided by the dispatching session: the item is not split. TCW-113 lands
after it in any case, and the move and rewrite parts get their own care in
the plan's tests instead (by field, a check that every changed file is
explained, folder creation and capabilities in the stop runs).

### Revised after the spec review (2026-10-22)

The adversarial review's findings, each checked against the repository
before it was acted on: the order of a move (folder last, nothing set
back, 5.8), the stop message naming every run's writes, the one definition
of reference fields built here (6.3), 3.x tickets refused (7.3), a rename's
`id:` (5.2), one refusal shape with TCW-112's (1.3), a missing ticket and
two runs at once (7.3), organising folders on a stop (5.3), abandoning a
move (5.8), a test for 5.7 (AC 25) and for every `project_folder` outcome
(AC 1), the router's check (1.4), the tree stores' references as repository
files (Design 8), `-C` from a 3.x or projectless folder (4.3, 4.4), the
`--parent` precondition (3.1), the code-span variant (6.2), case-only
renames (5.4 c), and the reading of the design's "moving its own items"
(5.4 g). Two citations were corrected (`find_project_root` at
`tcw/store/fs.py:296`; `read_only` at `tcw/serve/server.py:61-62`), and two
capability declarations added (`work/open-a-work-item`,
`work/tell-tcw-who-i-am`).
