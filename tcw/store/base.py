"""Abstract store interfaces — the portable spine the CLI depends on.

Per AGENTS.md (the litmus test) the model is storage-abstracted: a tree of
named nodes with cross-links is implementable by any backend. The filesystem
adapters in `fs.py` are the only realization shipped; remote adapters stay
possible but unbuilt. Phase 2 introduces `TaxonomyStore`; capabilities and work
add their interfaces here in their phases. The shared tree-store core is
extracted in Phase 4 — not pre-abstracted here.
"""

# Defer annotation evaluation (PEP 563): the store interfaces use forward refs
# (`"TermDetail" | None`) and self-referential dataclass fields that only resolve
# lazily. Without this, importing on Python 3.11–3.13 raises at class-definition
# time. Python 3.14 defers natively (PEP 649); this keeps <3.14 working too.
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class RefError(Exception):
    """A reference could not be resolved cleanly."""


class AmbiguousRef(RefError):
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


class SidecarError(ValueError):
    """A work item's capabilities.yaml sidecar could not be read as declarations
    (malformed YAML, or a non-list delta value)."""


@dataclass(frozen=True)
class Project:
    """A registered TCW project.

    ``locator`` is deliberately opaque: filesystem adapters use a path while a
    remote adapter may use a tracker key, URL, or database handle.
    """

    id: str
    locator: Any


class ProjectRegistry(ABC):
    """Storage-neutral connected-project graph."""

    @property
    @abstractmethod
    def current(self) -> Project:
        """The project from which this registry was opened."""

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
    def check(self) -> list[str]:
        """Return graph/configuration problems; empty means valid."""


def declared_capabilities(capabilities: Any) -> dict[str, list[str]]:
    """Canonical read of a work item's ``capabilities.yaml`` into
    ``{"new": [...], "changed": [...]}`` — the work→capability back-pointers the
    DoD gate enforces.

    ``capabilities`` is the already-parsed sidecar object (``WorkItem.capabilities``):
    a mapping with ``new:``/``changed:`` lists of canonical ``namespace/path``
    strings. ``added:`` is accepted as a deprecated alias of ``new:``. A trailing
    `` # comment`` on a value is stripped (YAML strips it already; belt and
    suspenders). The reconcile list-form sidecar and any other shape declare
    nothing here. The ``_tcw_parse_error`` sentinel the FS adapter produces on bad
    YAML raises ``SidecarError`` so the gate fails closed rather than reading
    "no deltas".
    """
    out: dict[str, list[str]] = {"new": [], "changed": []}
    if not capabilities or not isinstance(capabilities, dict):
        return out
    if "_tcw_parse_error" in capabilities:
        raise SidecarError(str(capabilities["_tcw_parse_error"]))
    for key, bucket in (("new", "new"), ("added", "new"), ("changed", "changed")):
        vals = capabilities.get(key)
        if vals is None:
            continue
        if not isinstance(vals, list):
            raise SidecarError(f"capabilities.yaml '{key}:' must be a list of paths")
        for v in vals:
            ref = str(v)
            i = ref.find(" #")                       # strip a trailing " # comment"
            if i != -1:
                ref = ref[:i]
            ref = ref.strip()
            if ref and ref not in out[bucket]:        # dedup (new: + added: overlap)
                out[bucket].append(ref)
    return out


# Sentinel to distinguish "field not provided" from "set to None" in
# partial-update operations.  Omitted → unchanged; None → clear nullable.
_UNSET = object()


@dataclass
class Term:
    """A taxonomy node: a vocabulary term or feature addressed by its path.

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

    @property
    def qualified(self) -> str:
        """Slug prefixed with its origin alias (`shared/Some/Term`); bare when local."""
        return self.slug if self.origin == "local" else f"{self.origin}/{self.slug}"


class TaxonomyStore(ABC):
    """The taxonomy axis: a forest of terms, optionally federated via `extends`."""

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
        """Remove a local term. Refuse an inherited one."""

    @abstractmethod
    def search(self, query: str) -> list[Term]:
        """Substring search over names + descriptions, local + inherited."""

    @abstractmethod
    def check(self) -> list[str]:
        """Validate the taxonomy; return a list of problems (empty == clean)."""

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
class ArtifactResource:
    """A lifecycle artifact's content, media type, and revision token."""
    name: str
    content: str
    media_type: str = "text/markdown"
    revision: str = ""


@dataclass
class SidecarResource:
    """A bounded work sidecar's content, media type, and revision token."""
    name: str
    content: str
    media_type: str = ""
    revision: str = ""


@dataclass
class WorkDetail:
    """A work item with revision tokens for every editable resource."""
    item: WorkItem
    core_revision: str = ""
    artifact_revisions: dict[str, str] = field(default_factory=dict)
    sidecar_revisions: dict[str, str] = field(default_factory=dict)


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
    "Status", "Priority", "Lifecycle", "Superseded by", "Tracker", "Subject",
    "Feature", "Roles", "When", "Gaps", "Blocked by", "Planning doc",
}


class Collision(RefError):
    """A flat file and a same-named folder both claim an identifier."""


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

    @property
    def status(self) -> str | None:
        return self.fields.get("Status")

    @property
    def qualified(self) -> str:
        """Path prefixed with its origin alias (`shared/auth/login`); bare when local."""
        return self.path if self.origin == "local" else f"{self.origin}/{self.path}"


class CapabilitiesStore(ABC):
    """The capabilities axis: a bounded tree of user-story nodes, optionally
    federated via `extends`.

    Deliberately near-identical to `TaxonomyStore` — both are bounded trees of
    body + named-fields + named-attachments nodes on the shared tree-store core.
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
            body: str = "") -> Capability:
        """Create a local capability folder at `identifier` (a path). Refuse a collision."""

    @abstractmethod
    def remove(self, identifier: str) -> None:
        ...

    @abstractmethod
    def reset(self, identifier: str) -> None:
        """Drop the local override at `identifier`, re-inheriting the upstream
        capability verbatim. Raise `ValueError` when there is no override (a
        standalone local capability is not an override — use `remove`; a bare
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
    def check(self, taxonomy: "TaxonomyStore | None" = None) -> list[str]:
        """Validate identifiers, metadata vocabulary, federation, and
        (cross-component) Subject/Feature refs."""

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

WORK_STATUSES = ("backlog", "active", "completed")

# The legal-transition graph lives in the *core* (phase-5-work B.1/B.3): the
# adapter only effects a move the core has already deemed legal. `drop` is
# handled separately (delete, backlog only).
LEGAL_TRANSITIONS = {
    ("backlog", "active"),                           # start
    ("active", "completed"),                        # complete (DoD gate)
}
WORK_RESOLUTIONS = {"done", "wontfix", "duplicate", "superseded"}
WORK_LEVELS = ("low", "medium", "high", "very-high")  # effort/complexity scale
WORK_LEVEL_ALIASES = {"l": "low", "m": "medium", "h": "high", "vh": "very-high"}


def normalize_work_level(value: str) -> str:
    """Map an effort/complexity input onto a canonical ``WORK_LEVELS`` value.

    Accepts the canonical values and the case-insensitive shorthand aliases
    (``L``/``M``/``H``/``VH``); raises ``ValueError`` on anything else. Input
    normalization only — the returned value is always canonical.
    """
    v = value.strip().lower()
    if v in WORK_LEVELS:
        return v
    if v in WORK_LEVEL_ALIASES:
        return WORK_LEVEL_ALIASES[v]
    raise ValueError(
        f"invalid level '{value}'; choose from {', '.join(WORK_LEVELS)} "
        "(or shorthand L/M/H/VH)"
    )


def normalize_tag(value: str) -> str:
    """Canonicalize a work tag: lowercase-hyphenated slug (mirrors
    ``fs.slugify``), with a non-empty guard. Registration and application both
    run inputs through this so ``Bug`` and ``bug`` never diverge."""
    tag = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not tag:
        raise ValueError(f"invalid tag {value!r}: empty after normalization")
    return tag


DEFAULT_DOD = ("tests pass", "docs synced", "capabilities reconciled",
               "reviewed", "version offered")
WORK_ARTIFACTS = ("initial-request", "spec", "plan", "outcome", "refined-outcome")

# Bounded sidecar registry — each entry declares the expected media type and
# the validation rule applied before persistence.  New sidecars are added here.
WORK_SIDECARS: dict[str, dict[str, str]] = {
    "capabilities.yaml": {
        "media_type": "application/yaml",
        "validation": "yaml_mapping",
    },
}

# Taxonomy term fields that the abstract ``update_term`` operation may modify.
TAXONOMY_EDITABLE_FIELDS = frozenset({"name", "description", "kind", "relates_to", "vocabulary"})


class IllegalTransition(Exception):
    """A status transition not in the legal graph (the enforcement — B.3)."""


class MultipleMatch(Exception):
    """A slug resolves to more than one item folder (slug integrity broken)."""


@dataclass
class WorkItem:
    """A unit of work; status is *where it lives*, not a stored field (A.3)."""
    slug: str
    title: str
    status: str
    phase: str = ""
    created: str = ""
    resolution: str | None = None
    priority: int | None = None     # higher int = higher priority; None = unspecified
    effort: str = ""                # WORK_LEVELS or "" (unset); triage signal only
    complexity: str = ""            # WORK_LEVELS or "" (unset); triage signal only
    tags: list[str] = field(default_factory=list)  # node-registered filter labels
    body: str = ""
    blocked_by: list[dict] = field(default_factory=list)
    capabilities: object = None     # opaque blob in Spec 1 (B.4)
    initiative: str = ""            # cross-node back-pointer to an epic (Spec 2)
    type: str = ""                  # optional recursion sugar; only value: "epic"
    worktree: str = ""              # node-relative worktree path (start --worktree)
    branch: str = ""                # work branch name (start --worktree)
    parent: str = ""                # slug of the parent item; "" == top-level (node relation)


@dataclass
class Artifact:
    """A named lifecycle artifact associated with a work item."""
    name: str
    present: bool = False


@dataclass(frozen=True)
class InboxResource:
    """Metadata for one named resource in a raw inbox entry."""
    name: str
    size: int
    media_type: str
    readable: bool


@dataclass(frozen=True)
class InboxEntry:
    """Opaque raw-intake handle and store-provided presentation metadata."""
    ref: str
    title: str
    kind: str


@dataclass(frozen=True)
class InboxEntryDetail:
    """An inbox entry plus its readable primary content and bounded resources."""
    entry: InboxEntry
    body: str | None
    resources: tuple[InboxResource, ...]


def topo_order(items: list[WorkItem]) -> list[WorkItem]:
    """Stable topological sort: a blocker precedes what it blocks.

    An edge counts only when both endpoints are in `items`; ties keep input
    order. A residual cycle (only via hand-edited data) degrades to original
    order for the leftover nodes. ponytail: re-sort the ready set each step — a
    board holds dozens of items, so the simple version is fine.
    """
    pos = {it.slug: i for i, it in enumerate(items)}
    by_slug = {it.slug: it for it in items}
    indeg = {it.slug: 0 for it in items}
    blocks: dict[str, list[str]] = {it.slug: [] for it in items}
    for it in items:
        for b in it.blocked_by:
            bs = b.get("slug")
            if bs in by_slug and bs != it.slug:          # edge present in this set
                blocks[bs].append(it.slug)
                indeg[it.slug] += 1
    ready = sorted((s for s, d in indeg.items() if d == 0), key=pos.get)
    out: list[str] = []
    while ready:
        s = ready.pop(0)
        out.append(s)
        freed = []
        for t in blocks[s]:
            indeg[t] -= 1
            if indeg[t] == 0:
                freed.append(t)
        if freed:
            ready = sorted(ready + freed, key=pos.get)
    placed = set(out)
    out += [s for s in pos if s not in placed]           # residual cycle → input order
    return [by_slug[s] for s in out]


def priority_order(items: list[WorkItem]) -> list[WorkItem]:
    """Stable priority sort: specified priorities (higher int first) above
    unspecified, which keep their input (creation) order. A soft preference —
    `board()` feeds it into `topo_order`, so a blocker still precedes what it
    blocks. ponytail: a stable sort with a two-part key, nothing fancier."""
    return sorted(items, key=lambda it: (0, -it.priority) if it.priority is not None
                  else (1, 0))


class WorkStore(ABC):
    """The work axis: raw intake plus a three-status item state machine.

    The status vocabulary + legal-transition graph are core (above); adapters
    implement the abstract primitives and `_effect_transition`. The named
    operations (`start`/`complete`/`drop`) are concrete here so every adapter
    shares the same legality + DoD semantics (B.1). Relation operations
    (`add_blocker`/`remove_blocker`) are added in Task 2.
    """
    STATUSES = WORK_STATUSES
    LEGAL_TRANSITIONS = LEGAL_TRANSITIONS

    # -- abstract primitives every adapter implements --

    @abstractmethod
    def create(self, title: str, created: str | None = None, body: str = "",
               priority: int | None = None, parent: str | None = None) -> WorkItem:
        """Create an item. With `parent` (a slug), create it as a child of that
        item — an abstract node relation; the adapter realizes the nesting."""

    @abstractmethod
    def get(self, slug: str) -> WorkItem | None:
        """Resolve a stable id (slug) to its item, or None. Raises `MultipleMatch`."""

    @abstractmethod
    def query(self, status: str | None = None) -> list[WorkItem]: ...

    @abstractmethod
    def artifacts(self, slug: str) -> list[Artifact]:
        """The bounded lifecycle artifact set for `slug`, with presence only."""

    @abstractmethod
    def artifact_locator(self, slug: str, name: str) -> str | None:
        """Resolve an artifact to an openable handle, or None if unavailable."""

    @abstractmethod
    def set_field(self, slug: str, key: str, value) -> None: ...

    @abstractmethod
    def _effect_transition(self, slug: str, to_status: str) -> None: ...

    @abstractmethod
    def _delete(self, slug: str) -> None: ...

    @abstractmethod
    def dod_checklist(self) -> list[str]: ...

    # -- tag registry (a node-scoped controlled vocabulary; any backend can
    #    realize a registered set + membership check) --

    @abstractmethod
    def registered_tags(self) -> list[str]:
        """The node's registered tag set (sorted; empty when none registered)."""

    @abstractmethod
    def register_tags(self, tags: list[str]) -> list[str]:
        """Add `tags` (normalized, deduped) to the registry; return the full set."""

    @abstractmethod
    def unregister_tags(self, tags: list[str]) -> list[str]:
        """Remove `tags` from the registry; return the full set."""

    @abstractmethod
    def check(self) -> list[str]:
        """Validate the work node; return problems (empty = clean). Reports items
        carrying a tag no longer in the registered set."""

    @abstractmethod
    def inbox_list(self) -> list[InboxEntry]:
        """List raw intake entries by opaque store-provided reference."""

    @abstractmethod
    def inbox_show(self, ref: str) -> InboxEntryDetail:
        """Inspect one raw entry without emitting arbitrary binary content."""

    @abstractmethod
    def inbox_accept(self, ref: str, title: str | None = None) -> WorkItem:
        """Atomically consume raw intake into a new backlog work item."""

    # -- revision-bearing reads --

    @abstractmethod
    def get_detail(self, slug: str) -> "WorkDetail" | None:
        """Resolve a slug to a ``WorkDetail`` (item + revision tokens).

        Returns ``None`` for unknown slugs.  The revision map covers the
        object core (fields + body), every lifecycle artifact, and every
        bounded sidecar.
        """

    # -- composite create / update --

    @abstractmethod
    def create_work(self, title: str, *,
                    created: str | None = None,
                    body: str = "",
                    priority: int | None = None,
                    effort: str = "",
                    complexity: str = "",
                    blockers: list[str] | None = None,
                    parent: str | None = None,
                    initiative: str = "",
                    type: str = "",
                    tags: list[str] | None = None) -> "WorkDetail":
        """Create a work item with all fields in one atomic operation.

        * ``title`` — required, non-empty display name.
        * ``effort`` / ``complexity`` — must be in ``WORK_LEVELS`` (or empty).
        * ``blockers`` — list of refs to resolve; unresolvable refs become
          external entries.
        * ``parent`` — must resolve to an existing item.
        * ``type`` — only ``""`` (default) or ``"epic"`` are valid.

        All fields are validated **before** any persistence.  Returns the
        created ``WorkDetail`` with fresh revision tokens.
        """

    @abstractmethod
    def update_work(self, slug: str, *,
                    title: Any = _UNSET,
                    body: Any = _UNSET,
                    priority: Any = _UNSET,
                    effort: Any = _UNSET,
                    complexity: Any = _UNSET,
                    blockers: Any = _UNSET,
                    initiative: Any = _UNSET,
                    parent: Any = _UNSET,
                    tags: Any = _UNSET,
                    core_revision: str | None = None) -> "WorkDetail":
        """Partial-merge update for an existing work item.

        Only fields whose keyword is *not* ``_UNSET`` are changed.  Passing
        ``None`` clears a nullable field (``priority``, ``blockers``).  Empty
        strings are explicit values and are preserved.

        ``core_revision`` (when provided) must match the current core token;
        a stale token raises ``StaleRevision`` and performs no write.

        Returns the updated ``WorkDetail`` with a fresh revision.
        """

    # -- artifact read / write --

    @abstractmethod
    def read_artifact(self, slug: str, name: str) -> "ArtifactResource" | None:
        """Read a lifecycle artifact by bounded name.

        Returns ``None`` when the artifact has not been written yet.
        Raises ``ValueError`` for unknown artifact names.
        """

    @abstractmethod
    def write_artifact(self, slug: str, name: str, content: str,
                       revision: str | None = None) -> "ArtifactResource":
        """Write a lifecycle artifact.

        ``revision`` (when provided) must match the current token; stale →
        ``StaleRevision``.  Content must be plain text (Markdown).
        Returns the written ``ArtifactResource`` with a fresh revision.
        """

    # -- sidecar read / write --

    @abstractmethod
    def read_sidecar(self, slug: str, name: str) -> "SidecarResource" | None:
        """Read a bounded sidecar by registry name.

        Returns ``None`` when the sidecar has not been written yet.
        Raises ``ValueError`` for unknown sidecar names.
        """

    @abstractmethod
    def write_sidecar(self, slug: str, name: str, content: str,
                      media_type: str | None = None,
                      revision: str | None = None) -> "SidecarResource":
        """Write a bounded sidecar.

        ``name`` must be in ``WORK_SIDECARS``.  ``media_type`` defaults to
        the registry entry.  ``revision`` enforces stale-write rejection.

        Before persistence the content is validated against the registry's
        ``validation`` rule (e.g. ``yaml_mapping`` → must parse as valid YAML).
        A validation failure leaves the store unchanged and raises ``ValueError``.

        Returns the written ``SidecarResource`` with a fresh revision.
        """

    def initiative_epic(self, item: WorkItem) -> WorkItem | None:
        """Resolve `item`'s initiative epic, if any.

        Default implementation is local-store only; adapters with cross-node
        visibility can override this relation query.
        """
        return self.get(item.initiative) if item.initiative else None

    def initiative_children(self, epic_slug: str) -> list[WorkItem]:
        """Items related to `epic_slug` by `initiative:`.

        Default implementation is local-store only; adapters with cross-node
        visibility can override this relation query.
        """
        return [i for i in self.query() if i.initiative == epic_slug]

    # -- concrete operations (shared semantics) --

    def _require(self, slug: str) -> WorkItem:
        item = self.get(slug)
        if item is None:
            raise ValueError(f"no such work item: {slug}")
        return item

    def _entry_for(self, ref: str) -> dict:
        """A blocker entry: a resolvable ref → {slug}, else {external}."""
        return {"slug": ref} if self.get(ref) is not None else {"external": ref}

    @staticmethod
    def _same_entry(a: dict, b: dict) -> bool:
        """Entry identity: same slug value, or same external text; never cross."""
        if "slug" in a and "slug" in b:
            return a["slug"] == b["slug"]
        if "external" in a and "external" in b:
            return a["external"] == b["external"]
        return False

    def _reaches(self, start: str, target: str) -> bool:
        """True if `start` (transitively, via blocked_by slugs) depends on `target`."""
        seen: set[str] = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            if cur == target:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            item = self.get(cur)
            if item is None:
                continue
            stack += [b["slug"] for b in item.blocked_by if "slug" in b]
        return False

    def add_blocker(self, slug: str, ref: str) -> None:
        item = self._require(slug)
        entry = self._entry_for(ref)
        if "slug" in entry:
            if entry["slug"] == slug:
                raise ValueError("an item cannot block itself")
            if self._reaches(entry["slug"], slug):
                raise ValueError(f"{ref} → {slug} would create a blocking cycle")
        if any(self._same_entry(entry, e) for e in item.blocked_by):
            return                                       # idempotent
        self.set_field(slug, "blocked_by", item.blocked_by + [entry])

    def remove_blocker(self, slug: str, ref: str) -> None:
        item = self._require(slug)
        kept = [e for e in item.blocked_by
                if e.get("slug") != ref and e.get("external") != ref]
        if len(kept) != len(item.blocked_by):
            self.set_field(slug, "blocked_by", kept)

    def board(self, status: str | None = None) -> list[WorkItem]:
        """The board in workable order: query(status) priority-sorted, then
        topologically sorted (a blocker still precedes what it blocks)."""
        return topo_order(priority_order(self.query(status)))

    def epic_completable(self, item: WorkItem) -> bool:
        """True iff `item` is an epic that is ready to close: it is `type: epic`,
        not already completed, has at least one initiative child, and every child
        is completed. Built on `initiative_children` (cross-node in adapters that
        override it), so the "all resolved" signal and the `complete` gate share
        one source of truth. An empty epic is not completable (nothing resolved)."""
        if item.type != "epic" or item.status == "completed":
            return False
        children = self.initiative_children(item.slug)
        return bool(children) and all(c.status == "completed" for c in children)

    def transition(self, slug: str, to_status: str) -> WorkItem:
        item = self._require(slug)
        if (item.status, to_status) not in self.LEGAL_TRANSITIONS:
            raise IllegalTransition(f"{item.status} → {to_status} is not a legal transition")
        self._effect_transition(slug, to_status)
        return self._require(slug)

    def unresolved_blockers(self, item: WorkItem) -> list[str]:
        """Labels of blockers that still block `item`. An entry is unresolved if
        it is external, or a slug whose item is not completed. A slug that no
        longer resolves counts as resolved (silently)."""
        out: list[str] = []
        for b in item.blocked_by:
            if "external" in b:
                out.append(f"external: {b['external']}")
            elif "slug" in b:
                blocker = self.get(b["slug"])
                if blocker is not None and blocker.status != "completed":
                    out.append(b["slug"])
            # else: structurally malformed entry — skip (degrade, don't crash)
        return out

    def start(self, slug: str, force: bool = False) -> WorkItem:
        item = self._require(slug)
        if not force:
            if item.initiative:
                epic = self.initiative_epic(item)
                if epic is None:
                    raise ValueError(f"Cannot verify initiative epic {item.initiative} "
                                     f"for {slug}. Run from a node that can resolve "
                                     f"the epic, or use --force.")
                if epic.status != "active":
                    raise ValueError(f"Cannot start work item {slug} before epic "
                                     f"{item.initiative} is active")
            blockers = self.unresolved_blockers(item)
            if blockers:
                raise ValueError("blocked by: " + ", ".join(blockers)
                                 + " (use --force to override)")
        return self.transition(slug, "active")

    def complete(self, slug: str, resolution: str, dod_ack: list[str],
                 force: bool = False) -> WorkItem:
        if resolution not in WORK_RESOLUTIONS:
            raise ValueError(f"invalid resolution '{resolution}' "
                             f"(choose: {', '.join(sorted(WORK_RESOLUTIONS))})")
        item = self._require(slug)
        # A completable epic (all children resolved) may close straight from
        # `backlog` — coordinator epics never needed their own start/active. This
        # is a scoped exception, not a global `(backlog, completed)` transition.
        from_backlog_epic = item.status == "backlog" and self.epic_completable(item)
        if (item.status, "completed") not in self.LEGAL_TRANSITIONS and not from_backlog_epic:
            raise IllegalTransition(f"cannot complete from {item.status} (only active)")
        if not force:
            if item.type == "epic":
                open_children = [i.slug for i in self.initiative_children(slug)
                                 if i.status != "completed"]
                if open_children:
                    raise ValueError(f"Cannot complete epic {slug}; initiative "
                                     f"children are still open: "
                                     f"{', '.join(open_children)}. Complete or "
                                     f"defer them first.")
            blockers = self.unresolved_blockers(item)
            if blockers:
                raise ValueError("blocked by: " + ", ".join(blockers)
                                 + " (use --force to override)")
        self.set_field(slug, "resolution", resolution)
        self.set_field(slug, "dod", dod_ack)
        if from_backlog_epic:                            # bypass transition()'s own
            self._effect_transition(slug, "completed")   # LEGAL_TRANSITIONS check
            return self._require(slug)
        return self.transition(slug, "completed")

    def drop(self, slug: str) -> None:
        item = self._require(slug)
        if item.status != "backlog":
            raise IllegalTransition(f"cannot drop from {item.status} (only backlog)")
        self._delete(slug)
