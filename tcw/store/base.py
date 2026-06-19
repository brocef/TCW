"""Abstract store interfaces — the portable spine the CLI depends on.

Per AGENTS.md (the litmus test) the model is storage-abstracted: a tree of
named nodes with cross-links is implementable by any backend. The filesystem
adapters in `fs.py` are the only realization shipped; remote adapters stay
possible but unbuilt. Phase 2 introduces `TaxonomyStore`; capabilities and work
add their interfaces here in their phases. The shared tree-store core is
extracted in Phase 4 — not pre-abstracted here.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class RefError(Exception):
    """A reference could not be resolved cleanly."""


class AmbiguousRef(RefError):
    """A bare reference matches more than one namespace — author must qualify."""


@dataclass
class Term:
    """A taxonomy node: a domain entity/concept addressed by its path.

    `slug` is the identity (path from the taxonomy root, e.g. `admin/permission`).
    `origin` is `"local"` or the `extends` alias the term was resolved through.
    """
    slug: str
    name: str
    description: str = ""
    relates_to: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    origin: str = "local"

    @property
    def qualified(self) -> str:
        """Slug prefixed with its origin alias (`shared/Some/Term`); bare when local."""
        return self.slug if self.origin == "local" else f"{self.origin}/{self.slug}"


class TaxonomyStore(ABC):
    """The taxonomy axis: a forest of terms, optionally federated via `extends`."""

    @abstractmethod
    def list(self, local_only: bool = False) -> list[Term]:
        """All terms (local + inherited), each flagged by `origin`."""

    @abstractmethod
    def get(self, ref: str) -> Term | None:
        """Resolve a reference (B.6) to a term, or None if it resolves to nothing.

        Raises `AmbiguousRef` when a bare ref matches multiple extended taxonomies.
        """

    @abstractmethod
    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "") -> Term:
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


# ── Capabilities (Phase 3) ───────────────────────────────────────────────────

# The locked vocabulary `check` validates (phase-3-capabilities A.4). `Planning
# doc` is included: A.8 / the work spec use it as the capability→work forward
# pointer, so it must be recognized (reconciles the A.4 table omission).
CAP_STATUSES = {"Supported", "Partial", "Missing", "Blocked", "Omitted"}
CAP_PRIORITIES = {"P0", "P1", "P2", "P3"}
CAP_LIFECYCLES = {"Experimental", "Stable", "Deprecated"}
CAP_FIELDS = {
    "Status", "Priority", "Lifecycle", "Superseded by", "Tracker", "Subject",
    "Roles", "When", "Gaps", "Blocked by", "Planning doc",
}


class Collision(RefError):
    """A flat file and a same-named folder both claim an identifier."""


@dataclass
class Capability:
    """One `## name` user story within a capability file."""
    file_id: str                 # owning file identifier (e.g. "routes/login")
    name: str                    # the heading text
    heading_slug: str            # GitHub-flavored anchor
    fields: dict[str, str] = field(default_factory=dict)
    body: str = ""

    @property
    def status(self) -> str | None:
        return self.fields.get("Status")

    @property
    def ref(self) -> str:
        return f"{self.file_id}#{self.heading_slug}"


@dataclass
class CapabilityFile:
    """A resolved capability file: its title + the capabilities it holds."""
    identifier: str
    title: str
    capabilities: list[Capability] = field(default_factory=list)


class CapabilitiesStore(ABC):
    """The capabilities axis: a bounded tree of user-story files (A.5).

    Deliberately near-identical to `TaxonomyStore` — both are bounded trees of
    body + named-fields + named-attachments nodes (the Phase-4 shared-core basis).
    """

    @abstractmethod
    def list(self, status: str | None = None, namespace: str | None = None) -> list[Capability]:
        ...

    @abstractmethod
    def get(self, identifier: str) -> CapabilityFile | None:
        """Resolve an identifier (A.6) to its file. Raises `Collision` on flat/folder clash."""

    @abstractmethod
    def add(self, identifier: str, name: str | None = None, status: str = "Missing",
            body: str = "", folder: bool = False) -> CapabilityFile:
        ...

    @abstractmethod
    def remove(self, identifier: str) -> None:
        ...

    @abstractmethod
    def search(self, query: str) -> list[Capability]:
        ...

    @abstractmethod
    def check(self, taxonomy: "TaxonomyStore | None" = None) -> list[str]:
        """Validate identifiers, metadata vocabulary, and (cross-component) Subject refs."""


# ── Work (Phase 5) ───────────────────────────────────────────────────────────

WORK_STATUSES = ("inbox", "backlog", "active", "completed")

# The legal-transition graph lives in the *core* (phase-5-work B.1/B.3): the
# adapter only effects a move the core has already deemed legal. `drop` is
# handled separately (delete, inbox|backlog only).
LEGAL_TRANSITIONS = {
    ("inbox", "active"), ("backlog", "active"),     # start
    ("active", "completed"),                        # complete (DoD gate)
}
WORK_RESOLUTIONS = {"done", "wontfix", "duplicate", "superseded"}
DEFAULT_DOD = ("tests pass", "docs synced", "capabilities reconciled",
               "reviewed", "version offered")


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
    body: str = ""
    blocked_by: list[dict] = field(default_factory=list)
    capabilities: object = None     # opaque blob in Spec 1 (B.4)


class WorkStore(ABC):
    """The work axis: items moving through a four-status state machine.

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
    def create(self, title: str, created: str | None = None, body: str = "") -> WorkItem: ...

    @abstractmethod
    def get(self, slug: str) -> WorkItem | None:
        """Resolve a stable id (slug) to its item, or None. Raises `MultipleMatch`."""

    @abstractmethod
    def query(self, status: str | None = None) -> list[WorkItem]: ...

    @abstractmethod
    def set_field(self, slug: str, key: str, value) -> None: ...

    @abstractmethod
    def _effect_transition(self, slug: str, to_status: str) -> None: ...

    @abstractmethod
    def _delete(self, slug: str) -> None: ...

    @abstractmethod
    def dod_checklist(self) -> list[str]: ...

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

    def transition(self, slug: str, to_status: str) -> WorkItem:
        item = self._require(slug)
        if (item.status, to_status) not in self.LEGAL_TRANSITIONS:
            raise IllegalTransition(f"{item.status} → {to_status} is not a legal transition")
        self._effect_transition(slug, to_status)
        return self._require(slug)

    def start(self, slug: str) -> WorkItem:
        return self.transition(slug, "active")

    def complete(self, slug: str, resolution: str, dod_ack: list[str]) -> WorkItem:
        if resolution not in WORK_RESOLUTIONS:
            raise ValueError(f"invalid resolution '{resolution}' "
                             f"(choose: {', '.join(sorted(WORK_RESOLUTIONS))})")
        item = self._require(slug)
        if (item.status, "completed") not in self.LEGAL_TRANSITIONS:
            raise IllegalTransition(f"cannot complete from {item.status} (only active)")
        self.set_field(slug, "resolution", resolution)
        self.set_field(slug, "dod", dod_ack)
        return self.transition(slug, "completed")

    def drop(self, slug: str) -> None:
        item = self._require(slug)
        if item.status not in ("inbox", "backlog"):
            raise IllegalTransition(f"cannot drop from {item.status} (only inbox/backlog)")
        self._delete(slug)
