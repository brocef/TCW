<!-- Bound to the `spec` and `plan` stages of `tcw work`; see `tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# The abstraction litmus test

_This repository's prime directive. It applies to the `spec` and `plan` stages —
a spec decides whether an operation belongs in the model, and a plan is where
operations get named — and it is the rule the rest of the codebase cites._

## Prime directive: the abstraction litmus test

TCW's model sits on a small **backend interface** of twelve operations, which
the filesystem backend and the Jira backend both implement. A **backend** is
where a work item's own facts are kept: its properties, its stage, its request
and its comments. The technical record (stage documents, rounds, handoffs, the
declared record changes, taxonomy and capabilities) is files in the
repository in both modes, so the model may read item folders directly. What a
backend owns, it reaches only through the interface.

That split is what lets one model serve a team that keeps its work in files
and a team that keeps it in Jira. Do not trade it away for filesystem
cleverness. Before adding or changing any operation, ask two questions.

The first governs **operations on what a backend owns**:

> **"Could a non-filesystem store implement this operation, even if less elegantly?"**
>
> - **Yes** → it belongs in the model and the backend interface.
> - **No** — it only works as a filesystem trick with no equivalent elsewhere →
>   keep it inside the filesystem backend as a private detail, or redesign it.

The second governs everything else:

> **"Who owns this fact: the backend, or the repository?"**
>
> - **The backend** → reach it through the interface, and apply the first
>   question.
> - **The repository** → it may be read as a file in both modes. This is not a
>   failure of the first question, because it is true in both backends.

## The backend interface

The interface lives in `tcw/work/backend.py`, which holds the exact
signatures. In plain words, a backend can:

- **create**: make a new item, with its folder, at a given stage, with its
  properties and its request.
- **read**: return one item by its folder name, or report that there is none.
- **list**: return the items that match a query.
- **update**: change an item's properties.
- **set stage**: move an item to a stage, recording a note saying why as part
  of the same move where the backend allows it. It runs no checks and no
  hooks; that is the job of the code that calls it.
- **comment**: add a comment to an item.
- **rename**: change an item's title and the words of its folder name.
- **lookup**: turn a name only this backend uses, such as a Jira key, into the
  item's folder name.
- **read request**: return the item's request, the text saying what it asks
  for.
- **read comments**: return the item's comments, newest first.
- **current user**: name the person running the command, in the form the
  backend uses for an item's assignee.
- **is item folder**: say whether a folder under the work path is one of this
  backend's items, reading the work path alone and never the network.

A backend reports honestly what it cannot map. An item can carry the keys of
linked tickets that have no item of their own, listed as **untracked** rather
than dropped, and a property such as priority can be empty when the backend
has no place to keep it.

## Abstract spine, filesystem leverage

Express behavior in the model's vocabulary — **item · stage · move
(`advance`) · slug · reference · project relation · query · properties ·
request · comments · the item folder's named files** — and let each backend
realize it. What the filesystem makes easy is a bonus layered on top, never an
assumption the model depends on.

- **Use freely:**
    - documents next to the code they describe;
    - one commit carrying a code change and a records change together, made
      by the project, not by TCW;
    - search, comparison and review with ordinary tools.
- **Keep out of the model:**
    - reconstructing an item's state from version history — _the stage is a
      property; history is an archive;_
    - inferring a stage from a folder's location or from which documents
      exist — _the stage is a property; the "stage ahead of its documents"
      check only warns;_
    - stage names outside the stage table;
    - treating an item folder as an open set of files — _it is bounded: stage
      folders, `<stage>.md`, `round-N.md`, handoffs, `comments/`,
      `capabilities.yaml` and `item.yaml`;_
    - hard-coded paths in references — _use slugs and paths within the store,
      resolved through the store;_
    - project relations read from directory nesting outside the layer that
      resolves projects;
    - **any operation that changes git state.** TCW never changes git state:
      committing, pulling and pushing belong to the project's own prompts and
      hooks. The git reads TCW does make (finding the repository's root,
      checking a work store for uncommitted changes before creating an item in
      another project, recognizing a linked worktree) sit in the code that
      resolves projects and creates items in them, not in the model.
