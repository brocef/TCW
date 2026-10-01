# TCW-77 — Web viewer: a single-process document reader and editor with autocomplete everywhere

Imported on 2026-10-01 from [TCW-77](https://proposit.atlassian.net/browse/TCW-77) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). Builds on TCW-69, TCW-70 and TCW-71. Revised after an adversarial review.

h1. What this delivers

{{tcw serve}} becomes a focused local web app for *reading and editing the documents in the TCW structure and creating new TCW objects*, across taxonomy, capabilities and work. It has nothing to do with the work lifecycle. It runs as one Python process with no Node.js at runtime, and every field whose value is a reference or comes from a known set offers autocomplete.

h1. The rule for Jira mode

*The viewer edits what is on disk. What lives in Jira is shown read-only, with an "Open in Jira" link to the ticket, where the user edits it.* In Jira mode that covers:

* the request (the ticket body);
* comments;
* status;
* the item's properties: title, priority, effort, complexity, tags, assignee, parent and links.

Creating and adopting items still work in Jira mode. They create TCW objects through the same operations as the CLI.

h1. The command

* {{tcw serve [--port <n>] [--no-open]}} binds {{127.0.0.1}} and prints the URL on stdout. Exit codes follow TCW-73 (e.g. 1 for a port already in use).
* This ticket owns the {{tcw serve}} command, the rewrite of {{docs/guide/web-viewer.md}}, and the capability records describing the viewer.

h1. Architecture

* *One Python process.* Python's built-in threaded HTTP server serves the prebuilt React client (with single-page-app route fallback) and a small JSON API.
* The Node/Fastify server and the Node 22 runtime requirement are removed. Node and pnpm remain contributor tools for building the client and running the browser tests. CI checks that the committed client bundle matches its source.
* *The API calls the same backend operations as the CLI* (TCW-69): create, read, list, update properties (filesystem mode), comment (filesystem mode), and adopt (Jira mode), plus the shared artifact layout. The viewer has no logic of its own. Anything the viewer can do, the CLI can do too.
* It serves one project. Entries inherited through {{extends}} are shown (marked as inherited) and offered in autocomplete. Child projects' boards are not combined, and references to other projects show as labelled links.

h1. Security

The server keeps every protection the Fastify layer gave:

* loopback binding;
* a loopback {{Host}}/{{Origin}} check on *every* {{/api}} request, including reads, to block DNS rebinding;
* a JSON content-type requirement on writes;
* a 1 MiB body cap;
* a {{default-src 'self'}} content security policy.

In Jira mode the process holds the Jira credentials. They are used only server-side and never sent to the browser.

h1. What it does

* *Reads and edits* the markdown documents on disk in an item folder: stage documents, rounds and handoffs. It also edits taxonomy and capability records, using the existing editor-plus-preview. Round files are editable like any file; whatever is saved is what the gates read.
* *Creates missing documents*, but only for enabled stages: a stage document, the next {{round-N}} (the same path as {{tcw work path <slug> <stage> --next}}), or a handoff.
* *Filesystem mode:*
** the request ({{request/request.md}}) and item properties are editable;
** comments are add-only, through the same operation as {{tcw work comment}}, because they carry forced-move and discard reasons.
* *Jira mode:* request, comments, status and properties are read-only, with the "Open in Jira" link.
* *Creates* work items (title, properties, request text, and {{--project}} / {{--stage inbox}} where they apply), taxonomy entries and capabilities. In Jira mode it lists inbox tickets and adopts them, as {{tcw work tickets}} does.
* {{spec/capabilities.yaml}} is edited through a small form (new / changed / removed lists with capability-path autocomplete) instead of raw YAML. The form follows the schema TCW-69 settles.
* *Validation on save* runs the same object-level rules {{validate}} applies to that object, offline. A notice reports problems; it never undoes the save.

h1. Jira mode at runtime

* The board loads with one batched query, as {{list}} does.
* If Jira is unreachable, files on disk stay readable and editable. Jira-owned content shows as unavailable, with a retry.
* Items with no stage (an unmapped status) appear under their own filter value.

h1. What it no longer does

* No lifecycle actions: no advance, discard, start, complete or drop, and no Definition-of-Done checklist. The stage is shown but not editable.
* Combining child projects' boards is removed.
* Removed fields:
** the work item "initiative" field;
** the capability "planning doc" field;
** the capability "tracker" field. Work items point at capabilities through {{spec/capabilities.yaml}}, not the other way.

h1. Autocomplete everywhere

Every editable field either autocompletes or is a fixed choice. In Jira mode the work-item property fields appear only on the create form; after that they are read-only.

||Field||Options offered||Entering something else||
|Work: parent|items in this project|refused|
|Work: blocked-by, blocks|filesystem mode: items in this project and in connected projects found locally; Jira mode (create form): tickets that have a TCW Item|filesystem mode: a full slug for another project is allowed, with a warning; Jira mode: refused|
|Work: tags|the tag registry, as chips|refused|
|Work: assignee|Jira mode (create form): assignable users; filesystem mode: names already used, plus {{user.name}}|filesystem mode: allowed (free text)|
|Work: priority, effort, complexity|fixed scales|select only|
|New item: target project, stage|connected projects; {{inbox}} (filesystem mode)|refused|
|Filters: stage, tags, assignee|stages (plus "no stage" in Jira mode); tag registry; known assignees|—|
|Taxonomy: parent path, relates, a feature's vocabulary|existing entries, including inherited (vocabulary only, for features)|refused|
|Taxonomy: kind|Vocabulary / Feature|select only|
|Capability: path|existing path segments|new segments allowed|
|Capability: feature, subject|taxonomy features; vocabulary|refused|
|Capability: roles, when|existing role and condition capabilities, with {{!}} to negate|refused|
|Capability: blocked-by, superseded-by|existing capabilities|refused|
|Capability: status, priority, lifecycle|their fixed sets|select only|
|Capability: name, gaps|free text|—|
|Markdown editor: typing {{tcw://}}|any object in the three areas|it still saves; the link shows as unresolved|
|{{spec/capabilities.yaml}} form|capability paths|{{new}} paths may be new; {{changed}} and {{removed}} must exist|

h1. Kept

* Validation-on-save notices and stale-edit protection (409) for files on disk.
* Deep-linkable URLs, the collapsible tree, and the light/dark setting.
* *Filters:* by stage, hiding finished items by default as {{list}} does; plus tags and assignee.

h1. Tests

* The Playwright suite drives the UI against fixture projects built with the CLI.
* Tests for removed lifecycle controls are deleted.
* Jira mode is tested against a stubbed Jira API, including that Jira-owned content is read-only.
* The suite stays a contributor tool that needs Node.
