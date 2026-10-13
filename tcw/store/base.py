"""Abstract store interfaces — the portable spine the CLI depends on.

Per `docs/lifecycle/abstraction.md` (the litmus test) the model is storage-abstracted: a tree of
named entries with cross-links is implementable by any backend. The filesystem
adapters in `fs.py` are the only realization shipped; remote adapters stay
possible but unbuilt. The work axis has its own interface,
`tcw.work.backend.WorkBackend`.
"""

# Defer annotation evaluation (PEP 563): the store interfaces use forward refs
# (`"TermDetail" | None`) and self-referential dataclass fields that only resolve
# lazily. Without this, importing on Python 3.11–3.13 raises at class-definition
# time. Python 3.14 defers natively (PEP 649); this keeps <3.14 working too.
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from tcw.errors import NotFound, UsageError
from tcw.findings import Finding


class RefError(NotFound):
    """A reference could not be resolved cleanly."""


class AmbiguousRef(UsageError, RefError):
    """A bare reference matches more than one namespace — author must qualify.

    Carries its own message: callers print `str(e)`, and the bare ref alone
    ("x/thing") reads as noise rather than an explanation.
    """

    def __init__(self, ref: str):
        self.ref = ref
        super().__init__(f"ambiguous ref '{ref}' — qualify it with an alias prefix")


class StaleRevision(Exception):
    """A write was rejected because the provided revision token no longer matches.

    The editable resource was modified (by another editor or CLI) since the caller
    last read it. The caller should re-read the current version and re-apply edits.
    """


class StoreLocationUnusable(ValueError):
    """A candidate location does not hold a usable store — it is absent, it is
    not a directory, or it lacks the component's layout.

    The distinction the resolution ladder needs, and could not make before it
    existed. Rules 1 and 2 try a location and fall through when it does not work
    out, which is right for "there is no store there" and wrong for every other
    reason a store fails to open: a federation error in a project that also declares
    a repository was reported as "not provisioned; run `tcw provision`", which
    then succeeded and left the store just as unopenable, because the real error
    had been swallowed two rules earlier.

    Storage-neutral: "the place I was told to look does not hold one of these"
    is a question any adapter answers — a missing table, a project id the tracker
    does not have — and it is categorically different from "the thing I found
    there is misconfigured".

    A `ValueError` for the same reason as its siblings: every existing
    `except ValueError` around a store `open()` keeps working unchanged.
    """


class StoreDeclarationError(ValueError):
    """A store's configured location is *wrong* — the configuration itself is
    the problem, and the message names the line to fix.

    Originally scoped to a wrongly declared home repository, and widened to what
    it always meant: any configured location the adapter can see is there and
    cannot use. A `work.path` naming a complete store outside any repository is
    the same kind of fact as a `repository` block missing its url — present, and
    unusable as written — and it must reach the reader for the same reason.

    A sibling of `StoreNotProvisioned`, and a `ValueError` for the same reason:
    every existing `except ValueError` around a store keeps working, including
    `_has_work_store`, which must answer False for a misconfigured *other* project
    rather than failing a whole topology listing.

    It exists because `find_component_project` cannot otherwise tell "this config is wrong"
    from "this is not a project", and flattening the first to the second is what
    answered a typo'd `repository` block with "run `tcw init`" — the one command
    that would scaffold a second, empty store beside the real one.
    """


class StoreNotProvisioned(ValueError):
    """A store is *declared* but not available here — nothing is wrong with the
    configuration, the store simply has not been obtained on this machine yet.

    A `ValueError` on purpose. Every existing `except ValueError` around a store
    `open()` keeps working unchanged, so this cannot silently break a caller; the
    sites that should now say more are the ones updated deliberately. What
    separates it from a misconfiguration is that it is *actionable* — the message
    carries what to run — and `str(e)` is the whole of it, so callers print it
    rather than composing their own.

    Not filesystem-specific: "declared but not available here" is a state a
    tracker-backed adapter reaches too, when credentials are absent or the
    service is unreachable.
    """


@dataclass(frozen=True)
class Project:
    """A registered TCW project.

    ``locator`` is deliberately opaque: filesystem adapters use a path while a
    remote adapter may use a tracker key, URL, or database handle.
    """

    id: str
    locator: Any


@dataclass(frozen=True)
class UnreachableProject:
    """A connected project that is declared here but not available here.

    **Not a configuration error.** The declaration is well formed and names a
    project this store simply cannot reach from this machine — a repository that
    was never cloned, a tracker project the caller has no access to. Telling that
    apart from a malformed declaration is the whole reason this type exists:
    fail-closed is right for a declaration that is wrong, and wrong for one that
    is merely unanswerable here.

    ``locator`` is opaque exactly as ``Project.locator`` is, and ``declared_in``
    names the configuration that carried the declaration. Both are presentation
    only — nothing above the adapter may parse them.
    """

    id: str
    locator: Any
    declared_in: Any = ""
    declaration: "RepositoryDeclaration | None" = None


@dataclass(frozen=True)
class ProjectOverride:
    """A locator the caller supplied, standing in place of the declared one.

    **Not a defect and not a declaration.** It is a third thing: a statement
    made by the machine running the command, about where a project sits *here*,
    that no file another machine reads can carry. The declared locator is a fact
    about one machine written into a file every machine shares, which is exactly
    the case it cannot express.

    ``source`` names whatever supplied the value — an environment variable, for
    the filesystem adapter — so a message can say where to go and change it.
    ``locator`` is opaque exactly as ``Project.locator`` is: a path here, a
    tracker key elsewhere, and nothing above the adapter may parse either.

    Reported rather than silent, always. An override that resolves a graph
    nobody else can resolve is the inverse of works-on-my-machine, and the only
    thing standing between it and a debugging trap is that every command that
    reports graph state says which overrides are in effect.

    ``problem`` is ``None`` when the override did what it said — the project it
    names is in the graph, under the right id, where it pointed. Anything else
    fills it in: the location is not a project at all, or is a different one.
    Carried on the record rather than in a second structure beside it, because
    the two failures are discovered at different moments — one when the override
    is resolved, one only after the target's configuration is read — and a caller
    that has to consult two places to learn "did this work" will consult one.
    """

    id: str
    source: str
    locator: Any
    problem: str | None = None
    # It worked, and still may not be what was meant: set when the project it
    # delivered disagrees with where the rest of the graph was read from. Never
    # a problem, and never fatal — the override is followed as stated.
    warning: str | None = None


class ProjectRegistry(ABC):
    """Storage-neutral connected-project graph."""

    @property
    @abstractmethod
    def current(self) -> Project:
        """The project from which this registry was opened."""

    def declared_parent_id(self, project_id: str | None = None) -> str | None:
        """The id of the declared parent, whether or not this store can reach it.

        `parent()` answers with a `Project`, so it can only answer for a project
        this store actually has — which made every "declared but not here"
        relation indistinguishable from "never declared", the one thing
        `UnreachableProject` exists to prevent. The id is known from the
        declaration alone, so it is answerable either way.

        The default is the reachable answer, which is correct for a store that
        always sees the whole graph.
        """
        parent = self.parent(project_id)
        return None if parent is None else parent.id

    def declared_child_ids(self, project_id: str | None = None) -> list[str]:
        """The ids of the declared children, reachable or not. See
        `declared_parent_id`."""
        return [child.id for child in self.children(project_id)]

    def declared_upstream_ids(self, project_id: str | None = None) -> list[str]:
        """The ids of the declared upstream projects, reachable or not.

        An upstream is a project this one reads from — its taxonomy, its
        capabilities, its work items by reference — and never writes to, and
        which does not name this project back. It is neither parent nor child,
        so no walk over those relations reaches it. A registry that keeps no
        such relation has none."""
        return []

    def read_only_reason(self, project_id: str,
                         from_id: str | None = None) -> str | None:
        """Why `from_id` (default: the current project) may not write to
        `project_id`, or None when it may.

        **The one place the write rule lives.** A project is writable from a
        project only when the project reaches it by `parent` and `children`
        connections alone, each followed as declared by the project it starts
        from. Anything else the graph holds was reached across an upstream
        connection and is read-only there — however many projects declare it, and
        from whichever side of the family it is named. A registry with no
        upstream relation has nothing read-only."""
        return None

    def warnings(self) -> list[str]:
        """Graph facts worth saying that are neither defects nor unreachable
        projects — printed by `tcw validate`, never fatal."""
        return []

    def overrides(self) -> list["ProjectOverride"]:
        """The locators the caller supplied for this graph, in place of declared ones.

        Empty by default, and concrete rather than abstract on purpose: a store
        with no override mechanism has none to report, and that is a correct
        answer rather than a gap. Every existing adapter is right without
        changing, so a caller may always ask.

        Storage-neutral despite the filesystem adapter's answer being a path.
        The question — *did the caller say where this project is, rather than
        the configuration?* — is one a tracker-backed registry answers too, by
        reading the same environment for a project key instead of a directory.
        Only the value is a filesystem particular, and it stays opaque here for
        the same reason ``Project.locator`` does.

        Only overrides that took **effect** belong here. One naming a project
        this graph never consults is not in force, and listing it would say the
        graph depends on something it does not.

        Includes the ones that took effect and *failed* — an override that
        stopped the ladder and produced nothing is in force in the way that
        matters, and it is the entry a caller has to see. Its ``problem`` says
        which.
        """
        return []

    @abstractmethod
    def get(self, project_id: str) -> Project | None:
        """Return a connected project by canonical ID."""

    @abstractmethod
    def parent(self, project_id: str | None = None) -> Project | None:
        """Return the direct parent of a project, if any."""

    @abstractmethod
    def children(self, project_id: str | None = None) -> list[Project]:
        """Return the direct children of a project."""

    @abstractmethod
    def ancestors(self, project_id: str | None = None) -> list[Project]:
        """Return direct parent first, then the remaining ancestors."""

    @abstractmethod
    def descendants(self, project_id: str | None = None) -> list[Project]:
        """Return every descendant in deterministic depth-first order."""

    @abstractmethod
    def projects(self) -> list["Project"]:
        """Every project in the graph, the current one included.

        Deliberately not `current + ancestors + descendants`: a graph is not a
        line, and that triple omits a sibling, a sibling of an ancestor, and
        anything else reached by a shape nobody enumerated. A caller asking
        "what does this checkout have" wants the set, and reconstructing it from
        relations is how the set silently loses a member.
        """

    @abstractmethod
    def check(self) -> "list[Finding]":
        """Return graph/configuration problems as error findings, each
        `where` the config file that holds it; empty means valid.

        Problems only. A project that is declared but not reachable here is not
        one — see ``unreachable``.
        """

    @abstractmethod
    def unreachable(self) -> list["UnreachableProject"]:
        """Return the declared projects this store cannot reach from here.

        Deliberately separate from ``check``: these are not defects to fix, and a
        caller that treats them as such refuses to run in exactly the checkouts
        this distinction exists to serve. Callers that need the graph complete
        report them; callers that do not, ignore them.
        """


# Sentinel to distinguish "field not provided" from "set to None" in
# partial-update operations.  Omitted → unchanged; None → clear nullable.
_UNSET = object()


@dataclass
class Term:
    """A taxonomy entry: a vocabulary term or feature addressed by its path.

    `slug` is the identity (path from the taxonomy root, e.g. `admin/permission`).
    `origin` is `"local"` or the `extends` alias the term was resolved through.
    """
    slug: str
    name: str
    description: str = ""
    kind: str = "Vocabulary"
    relates_to: list[str] = field(default_factory=list)
    vocabulary: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    origin: str = "local"
    modified: str = ""

    @property
    def qualified(self) -> str:
        """Slug prefixed with its origin alias (`shared/Some/Term`); bare when local."""
        return self.slug if self.origin == "local" else f"{self.origin}/{self.slug}"


class TaxonomyStore(ABC):
    """The taxonomy axis: a forest of terms, optionally federated via `extends`.

    Errors, by the class `tcw` turns into its exit code (TCW-73 Design 4):
    `NotFound` (4) when the entry or `extends` ID named does not exist;
    `UsageError` (2) when the input itself is wrong (a bad ID or path, a kind,
    Status or field outside the list, a reference that does not resolve or is
    ambiguous, a project nothing registers); `Refused` (3) when the input is
    fine but the store's state forbids it (the name is taken, the entry is
    inherited, has nested entries or is still referenced, the `extends` entry
    already exists); `BackendError` (1) for a fault reading back what was
    written. An adapter for another kind of store raises the same classes.
    """

    @abstractmethod
    def list_all(self, local_only: bool = False) -> list[Term]:
        """All terms (local + inherited), each flagged by `origin`."""

    @abstractmethod
    def get(self, ref: str) -> Term | None:
        """Resolve a reference (B.6) to a term, or None if it resolves to nothing.

        Raises `AmbiguousRef` when a bare ref matches multiple extended taxonomies.
        """

    @abstractmethod
    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "", kind: str = "Vocabulary",
            vocabulary: list[str] | None = None) -> Term:
        """Create a local term under `parent` (root by default). Refuse a collision."""

    @abstractmethod
    def remove(self, ref: str) -> None:
        """Remove a local term, writing nothing when refused. Raise `ValueError`
        when nothing resolves, the term is inherited, another term is nested under
        it, another local term's `relatesTo` or `vocabulary` still resolves to it,
        or a local capability's `Subject` or `Feature` does — including when the
        project's capabilities cannot be read, since that cannot then be known.
        Refusing rather than cascading is the contract, as for capabilities.
        Never reports success for a term that still exists afterwards."""

    @abstractmethod
    def search(self, query: str) -> list[Term]:
        """Substring search over names + descriptions, local + inherited."""

    @abstractmethod
    def check(self, identifier: str | None = None) -> "list[Finding]":
        """Validate the taxonomy, optionally limited to one object."""

    @abstractmethod
    def extends_add(self, project_id: str) -> None:
        """Explicitly inherit the taxonomy of a connected project."""

    @abstractmethod
    def extends_remove(self, project_id: str) -> None:
        """Drop an inherited project ID. Refuse if it isn't present."""

    @abstractmethod
    def get_term_detail(self, ref: str) -> "TermDetail" | None:
        """Resolve a reference to its term plus a core revision token.

        Returns ``None`` when the ref resolves to nothing (same as ``get``).
        Raises ``AmbiguousRef`` on collisions.
        """

    @abstractmethod
    def update_term(self, ref: str, *,
                    name: Any = _UNSET,
                    description: Any = _UNSET,
                    relates_to: Any = _UNSET,
                    vocabulary: Any = _UNSET,
                    kind: Any = _UNSET,
                    core_revision: str | None = None) -> "TermDetail":
        """Partial-merge update for an existing local term.

        Only keys that are *not* ``_UNSET`` are changed.  Passing ``None``
        clears a field to its default (empty string / empty list).  Empty
        strings are explicit values and are preserved.  Refers to
        ``TAXONOMY_EDITABLE_FIELDS`` for the allowed set.

        ``core_revision`` (when provided) must match the current token; a
        stale token raises ``StaleRevision`` and performs no write.

        Returns the updated ``TermDetail`` with a fresh revision.
        """


# ── Revision-bearing resource types ──────────────────────────────────────────


@dataclass
class TermDetail:
    """A taxonomy term with its core revision token."""
    term: Term
    core_revision: str = ""


@dataclass
class CapabilityDetail:
    """A single capability entry with its core revision token."""
    capability: Capability
    core_revision: str = ""


# ── Capabilities (Phase 3) ───────────────────────────────────────────────────

# The locked vocabulary `check` validates (phase-3-capabilities A.4). `Planning
# doc` is included: A.8 / the work spec use it as the capability→work forward
# pointer, so it must be recognized (reconciles the A.4 table omission).
CAP_STATUSES = {"Supported", "Partial", "Missing", "Blocked", "Omitted"}
CAP_PRIORITIES = {"P0", "P1", "P2", "P3"}
CAP_LIFECYCLES = {"Experimental", "Stable", "Deprecated"}
CAP_FIELDS = {
    "Status", "Priority", "Lifecycle", "Superseded by", "Subject",
    "Feature", "Roles", "When", "Gaps", "Blocked by",
}
# Fields 2.x accepted that 3.0 retired (TCW-73 Design 8.6): both pointed from
# the ledger into the work axis, which now links the other way, through each
# work item's `capabilities.yaml`. A record still carrying one is a check error
# naming the migration guide.
RETIRED_CAP_FIELDS = {"Planning doc", "Tracker"}
# The 2.x name of the `projects` key in `tcw-config.yaml` (TCW-73 Design 9.3):
# a config error naming the migration guide, never read.
RETIRED_PROJECTS_KEY = "connected-projects"
MIGRATION_GUIDE = "docs/migration-guide-2.8-to-3.0.0.md"  # removed keys and fields


@dataclass
class Capability:
    """A single user-story capability, addressed by its folder path.

    `path` is the identity (path from the capabilities root, e.g.
    `auth/providers/github`). `id` is an opaque, immutable stable id — the
    durable key an override or a `tcw://` reference points at. `origin` is
    `"local"` or the `extends` alias the capability was resolved through.
    `fields` holds the locked metadata vocabulary (`CAP_FIELDS`); `Subject` may
    be a list of taxonomy slugs.
    """
    path: str
    name: str
    id: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    origin: str = "local"
    modified: str = ""

    @property
    def status(self) -> str | None:
        return self.fields.get("Status")

    @property
    def qualified(self) -> str:
        """Path prefixed with its origin alias (`shared/auth/login`); bare when local."""
        return self.path if self.origin == "local" else f"{self.origin}/{self.path}"


class CapabilitiesStore(ABC):
    """The capabilities axis: a bounded tree of user-story entries, optionally
    federated via `extends`.

    Deliberately near-identical to `TaxonomyStore` — both are bounded trees of
    body + named-fields + named-attachments entries on the shared tree-store core.

    Errors, by the class `tcw` turns into its exit code (TCW-73 Design 4):
    `NotFound` (4) when the entry or `extends` ID named does not exist;
    `UsageError` (2) when the input itself is wrong (a bad ID or path, a kind,
    Status or field outside the list, a reference that does not resolve or is
    ambiguous, a project nothing registers); `Refused` (3) when the input is
    fine but the store's state forbids it (the name is taken, the entry is
    inherited, has nested entries or is still referenced, the `extends` entry
    already exists); `BackendError` (1) for a fault reading back what was
    written. An adapter for another kind of store raises the same classes.
    """

    @abstractmethod
    def list_all(self, status: str | None = None, namespace: str | None = None,
                 local_only: bool = False) -> list[Capability]:
        """All capabilities (local + inherited), each flagged by `origin`."""

    @abstractmethod
    def get(self, identifier: str) -> Capability | None:
        """Resolve a path (A.6) to its capability, or None. Raises `AmbiguousRef`
        when a bare ref matches multiple extended stores."""

    @abstractmethod
    def add(self, identifier: str, name: str | None = None, status: str = "Missing",
            body: str = "", fields: dict[str, Any] | None = None) -> Capability:
        """Create a local capability folder at `identifier` (a path). Refuse a
        collision. `fields` are validated as `set` validates them, before
        anything is written, so a create carrying a bad field writes nothing."""

    @abstractmethod
    def remove(self, identifier: str) -> None:
        """Delete the local capability at `identifier`, writing nothing when
        refused. Raise `AmbiguousRef` when a bare ref matches multiple extended
        stores, and `ValueError` when:

        - nothing resolves;
        - the capability is inherited, overridden locally or not (an override
          is dropped with `reset`, never with `remove`);
        - another capability or override is nested under its path;
        - another local capability or override still references it through
          `Superseded by`, `Blocked by`, `Roles` or `When`.

        Refusing rather than cascading is the contract: a delete never takes a
        second capability with it or leaves a reference pointing at nothing.
        Never mutates an extended store."""

    @abstractmethod
    def reset(self, identifier: str) -> None:
        """Drop the local override at `identifier`, re-inheriting the upstream
        capability verbatim. Raise `ValueError` when there is no override (a
        standalone local capability is not an override — the `remove` operation,
        driven by `tcw capabilities rm`, deletes it; a bare
        inherited path has nothing to drop), or `AmbiguousRef` when a bare ref
        matches multiple extended stores. Never mutates an extended store."""

    @abstractmethod
    def set(self, identifier: str, fields: dict[str, Any]) -> Capability:
        """Update/insert metadata fields on the capability at `identifier`;
        return it. Keys must be in CAP_FIELDS; a Status value must be in
        CAP_STATUSES. `Subject` accepts a list (or a comma string). Other
        field-value semantics are `check`'s job (Spec 3)."""

    @abstractmethod
    def search(self, query: str) -> list[Capability]:
        ...

    @abstractmethod
    def unreviewed_inherited(self) -> list["Capability"]:
        """Inherited capabilities whose Status is the master's default — never
        locally ruled on (no local override that sets Status). The 'unreviewed'
        half of drift: distinguishes an echoed master default from a local
        decision. Empty when nothing is federated."""

    @abstractmethod
    def check(self, taxonomy: "TaxonomyStore | None" = None,
              identifier: str | None = None) -> "list[Finding]":
        """Validate identifiers, metadata vocabulary, federation, and
        (cross-component) Subject/Feature refs, as error findings."""

    @abstractmethod
    def get_capability_detail(self, identifier: str) -> "CapabilityDetail" | None:
        """Resolve a path to its capability plus a revision token.
        Returns ``None`` for dangling identifiers."""

    @abstractmethod
    def update_capability(self, identifier: str, *,
                          body: Any = _UNSET,
                          fields: Any = _UNSET,
                          core_revision: str | None = None) -> "CapabilityDetail":
        """Partial-merge update for an existing capability.

        ``body``: ``None`` clears to empty string; any string sets it.
        ``fields``: a dict of ``{key: value}`` pairs to merge into the
        capability's metadata (keys validated against ``CAP_FIELDS``).
        ``core_revision`` enforces stale-write rejection.

        Returns the updated ``CapabilityDetail`` with a fresh revision.
        """

    @abstractmethod
    def extends_add(self, project_id: str) -> None:
        """Explicitly inherit capabilities from a connected project."""

    @abstractmethod
    def extends_remove(self, project_id: str) -> None:
        """Drop an inherited project ID. Refuse if it isn't present."""


# ── Work (Phase 5) ───────────────────────────────────────────────────────────


def normalize_tag(value: str) -> str:
    """Canonicalize a work tag: lowercase-hyphenated slug (mirrors
    ``fs.slugify``), with a non-empty guard. Registration and application both
    run inputs through this so ``Bug`` and ``bug`` never diverge."""
    tag = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not tag:
        raise ValueError(f"invalid tag {value!r}: empty after normalization")
    return tag


# ── Lifecycle policy (stage/transition bindings) ─────────────────────────────
#
# Two ladders. A **stage** produces one lifecycle artifact; a **transition** moves
# status. Nothing is both. These ids are **public API**: a user's
# `tcw-config.yaml` keys on them, so renaming one silently breaks their
# configuration. Insertions are safe; renames are not.


# Procedures: instruction text TCW ships that is not a lifecycle stage, which a
# project may replace under `work.procedures`. Public API like `STAGE_IDS`, and
# deliberately **not** skill names: skills get renamed, and a project's
# configuration must not break when one is. A project replaces a procedure's
# text; it cannot add a procedure.
PROCEDURE_IDS = ("unattended-work", "triage-issues", "documentation-sync",
                 "post-mortem", "create-work", "audit-backlog",
                 "consolidate-plans", "decompose", "delegation", "search")


# Bound on a `generate` hook's stdout, in **raw bytes before decoding**.
# Enforced while reading rather than after, so a runaway script cannot exhaust
# memory before the check fires. Also the cap on the item `body` a hook gets.
DEFAULT_OUTPUT_CAP = 64 * 1024


@dataclass(frozen=True)
class DocEntry:
    """One `work.documentation` entry: a document, when it must be updated, and
    what to write in it.

    Project configuration, not store content — a tracker-backed project has these
    exactly as a filesystem project does, the same way `work.tags` and
    `work.lifecycle` already do.
    """
    path: str
    trigger: str
    description: str


@dataclass(frozen=True)
class RepositoryDeclaration:
    """Where a component store comes from, as the project records it.

    Project configuration and an **adapter locator**, exactly as a store path is —
    the project registry already states the rule that canonical IDs are identity
    and filesystem locations are locators only. A tracker-backed adapter would
    read a different locator from the same slot; nothing above the adapter is
    entitled to read these fields.

    `path` is the store's location *within* the declared repository, and stays a
    POSIX-style relative string here rather than becoming a `Path`: this object
    is parsed from YAML and compared in tests, and the adapter that joins it is
    the only code that needs it to be a path at all.
    """
    url: str
    ref: str | None = None
    path: str = ""
    checkout: str | None = None


@dataclass(frozen=True)
class ConnectedProject:
    """One `projects` entry: where a project is, and where it comes from.

    Both halves are optional individually and one of them is required. `locator`
    is the adapter locator the entry has always been — a path, for the filesystem
    adapter. `repository` says how a machine that does not have the project can
    obtain it, and is exactly the declaration a component store takes, because
    "where does this come from" is the same question either way.

    The two are a ladder, not alternatives: the locator answers when it can, and
    the declaration answers only when it cannot. A project already here is never
    fetched.
    """

    id: str
    locator: str | None = None
    repository: "RepositoryDeclaration | None" = None
    # The entry's optional `jira` block, kept unparsed: the store layer imports
    # nothing from `tcw.work`, and the Jira backend checks its shape when
    # delegation reads it (TCW-71).
    jira: Any = field(default=None, compare=False, hash=False)


@dataclass(frozen=True)
class ProvisionResult:
    """What one provisioning attempt did.

    `location` is a short human-readable handle: presentation only, do not
    parse it. `action` is the closed vocabulary a
    caller may branch on.
    """
    action: str                 # one of PROVISION_ACTIONS
    available: bool
    location: str = ""
    detail: str = ""


PROVISION_ACTIONS = (
    "undeclared",        # nothing declared; there was nothing to do
    "available",         # already usable here; nothing was contacted
    "obtained",          # newly made available
    "planned",           # dry run: this is what would have happened
)


class StoreProvisioner(ABC):
    """Making a declared store usable *here*.

    The abstract verb is "make yourself usable", not "clone": a tracker-backed
    adapter answers `is_available` by checking credentials and reachability, and
    an adapter that needs nothing implements `ensure_available` as a no-op —
    which is a legitimate implementation, not a stub.

    No signature names a URL, a ref, or a directory. Those are the filesystem
    adapter's private business, and a store-interface method that mentioned one
    would have moved the seam into the wrong layer.
    """

    @abstractmethod
    def describe(self) -> str:
        """A short, human-readable account of where the store is declared to come
        from. Presentation only — do not parse it."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the store can be used here right now, without contacting
        anything."""

    @abstractmethod
    def ensure_available(self, *, dry_run: bool = False) -> ProvisionResult:
        """Make the store usable here, and report what that took.

        Idempotent: an already-usable store returns `available` and contacts
        nothing, which is what lets a caller run this unconditionally. Keeping
        an available store up to date is the project's own business, not
        TCW's (TCW-73 Design 8.4). `dry_run` reports the plan and contacts
        nothing.
        """


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def parse_repository_declaration(
    raw: Any, where: str
) -> tuple["RepositoryDeclaration | None", list[str]]:
    """Parse a `<component>.repository` mapping into a declaration plus problems.

    Mirrors `parse_lifecycle_policy` and `parse_documentation_entries`: pure,
    touches no filesystem, never raises. `where` is the config path to quote in
    problems (`work.repository`), so one implementation serves every component
    rather than three that drift.

    Returns `(None, problems)` when the declaration cannot be trusted — unlike
    the documentation parser, which keeps the entries that parsed. The difference
    is what a half-read value would do: a mistyped documentation entry costs one
    row in a table, while a mistyped repository would send a fetch somewhere
    nobody asked for. This one fails closed.
    """
    problems: list[str] = []
    if raw is None:
        return None, problems
    if not isinstance(raw, dict):
        return None, [f"{where}: expected a mapping, got {type(raw).__name__}"]

    known = {"url", "ref", "path", "checkout"}
    unknown = set(raw) - known
    if unknown:
        problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                        f"expected {', '.join(repr(k) for k in sorted(known))}")

    url = raw.get("url")
    if not isinstance(url, str) or not url.strip():
        problems.append(f"{where}.url: expected a non-empty string")

    def _optional_string(key: str) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{where}.{key}: expected a non-empty string")
            return None
        return value.strip()

    ref = _optional_string("ref")
    checkout = _optional_string("checkout")

    # `path` is bounded rather than merely typed: it is joined onto a directory
    # this code created, so the containment rule the stores already enforce for
    # their own identifiers applies here too — syntactically, before any join.
    store_path = ""
    raw_path = raw.get("path")
    if raw_path is not None:
        if not isinstance(raw_path, str) or not raw_path.strip():
            problems.append(f"{where}.path: expected a non-empty string")
        else:
            candidate = raw_path.strip()
            parts = PurePosixPath(candidate).parts
            if candidate.startswith("/") or (len(candidate) > 1 and candidate[1] == ":"):
                problems.append(f"{where}.path: must be relative to the repository root, "
                                f"got {candidate!r}")
            elif ".." in parts:
                problems.append(f"{where}.path: must not leave the repository root, "
                                f"got {candidate!r}")
            else:
                store_path = PurePosixPath(candidate).as_posix().strip("/")

    if problems:
        return None, problems
    return RepositoryDeclaration(url=url.strip(), ref=ref, path=store_path,
                                 checkout=checkout), problems


def parse_connected_entry(
    project_id: str, raw: Any, where: str
) -> tuple["ConnectedProject | None", list[str]]:
    """Parse one `projects` entry into a `ConnectedProject` plus problems.

    Two accepted forms, and the first must never stop working:

        child-id: ../child                      # a bare locator, as always
        child-id:
            path: ../child                      # optional
            repository: {url: ..., ref: ...}    # optional

    Pure, filesystem-free, and fails closed like `parse_repository_declaration`
    — which it delegates the `repository` half to wholesale, so a malformed
    declaration reads the same here as it does under `work.repository` rather
    than growing a second vocabulary of error messages.

    An entry naming neither is refused. It would be a project that cannot be
    found and cannot be obtained, which is not a state worth representing.
    """
    problems: list[str] = []
    if isinstance(raw, str):
        if not raw.strip():
            return None, [f"{where}: locator must be a nonempty string"]
        return ConnectedProject(id=project_id, locator=raw), problems
    if not isinstance(raw, dict):
        return None, [f"{where}: expected a locator string or a mapping, "
                      f"got {type(raw).__name__}"]

    known = {"path", "repository", "jira"}
    unknown = set(raw) - known
    if unknown:
        problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                        f"expected {', '.join(repr(k) for k in sorted(known))}")

    locator = raw.get("path")
    if locator is not None and (not isinstance(locator, str) or not locator.strip()):
        problems.append(f"{where}.path: expected a non-empty string")
        locator = None

    declaration = None
    if "repository" in raw:
        declaration, declaration_problems = parse_repository_declaration(
            raw.get("repository"), f"{where}.repository")
        problems.extend(declaration_problems)

    if locator is None and declaration is None and not problems:
        problems.append(f"{where}: needs 'path', 'repository', or both")
    if problems:
        return None, problems
    return ConnectedProject(id=project_id, locator=locator,
                            repository=declaration, jira=raw.get("jira")), problems


def parse_documentation_entries(raw: Any) -> tuple[list["DocEntry"], list[str]]:
    """Parse a `work.documentation` list into entries plus a problem list.

    Mirrors `parse_lifecycle_policy`: pure, touches no filesystem, never raises,
    and returns problems advisorily so `tcw validate` can report them while the
    adapter discards them. A typo in one entry must not blank a project's whole
    documentation gate, so entries that parse are kept alongside the problems.

    **Shape only, deliberately.** The trigger vocabulary is explicitly open —
    `skills/documentation-sync/SKILL.md` says "Treat any such project-defined
    trigger as authoritative for that project" — so a trigger is checked for
    whitespace (which catches `Public API` and a dropped bracket) and nothing
    else. `path` is likewise **not** required to exist: an entry routinely names
    a file the project intends to create, and this repository's own entry is the
    pattern `skills/<component>/SKILL.md`, which resolves to no file at all.

    **Identity is `(path, trigger)`, not the path alone** — the same call
    `_parse_bindings` makes for `(kind, value, when)`. One file large enough
    that its sections answer to different triggers needs one entry per trigger:
    a CLI-surface change fires the first, a validation-rule change touching no
    CLI surface fires only the second. Keying on the path alone made the config
    form less expressive than the Markdown section it replaced.
    """
    entries: list[DocEntry] = []
    problems: list[str] = []
    if raw is None:
        return entries, problems
    if not isinstance(raw, list):
        return entries, [f"work.documentation: expected a list, "
                         f"got {type(raw).__name__}"]

    seen: dict[tuple[str, str], int] = {}
    for index, item in enumerate(raw):
        where = f"work.documentation entry {index}"
        if not isinstance(item, dict):
            problems.append(f"{where}: expected a mapping, "
                            f"got {type(item).__name__}")
            continue

        unknown = set(item) - {"path", "trigger", "description"}
        if unknown:
            problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                            f"expected 'path', 'trigger', 'description'")

        values: dict[str, str] = {}
        for key in ("path", "trigger", "description"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{where}: '{key}' is required and must be a "
                                f"non-empty string")
            else:
                values[key] = value.strip()
        if len(values) != 3:
            continue

        path, trigger = values["path"], values["trigger"]
        if "\n" in path:
            problems.append(f"{where}: 'path' must not contain a newline")
            continue
        if "\n" in trigger:
            problems.append(f"{where}: 'trigger' must not contain a newline")
            continue
        if PurePosixPath(path).is_absolute() or path.startswith("/"):
            problems.append(f"{where}: 'path' must be relative to the project, "
                            f"got an absolute path")
            continue
        if any(part == ".." for part in PurePosixPath(path).parts):
            problems.append(f"{where}: 'path' must not escape the project")
            continue
        if any(character.isspace() for character in trigger):
            problems.append(f"{where}: 'trigger' must not contain whitespace "
                            f"(got {trigger!r}) — a trigger is one bracketed name")
            continue

        if (path, trigger) in seen:
            problems.append(f"{where}: duplicate 'path' {path!r} under trigger "
                            f"{trigger!r}, already declared by entry "
                            f"{seen[(path, trigger)]}")
            continue
        seen[(path, trigger)] = index
        entries.append(DocEntry(path=path, trigger=trigger,
                                description=values["description"]))

    return entries, problems


# Taxonomy term fields that the abstract ``update_term`` operation may modify.
TAXONOMY_EDITABLE_FIELDS = frozenset({"name", "description", "kind", "relates_to", "vocabulary"})


class IllegalTransition(Exception):
    """A status transition not in the legal graph (the enforcement — B.3)."""


class MultipleMatch(Exception):
    """A slug resolves to more than one item folder (slug integrity broken)."""


