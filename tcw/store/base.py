"""Abstract store interfaces — the portable spine the CLI depends on.

Per AGENTS.md (the litmus test) the model is storage-abstracted: a tree of
named nodes with cross-links is implementable by any backend. The filesystem
adapters in `fs.py` are the only realization shipped; remote adapters stay
possible but unbuilt. Phase 2 introduces `TaxonomyStore`; capabilities and work
add their interfaces here in their phases. The shared tree-store core is
extracted in Phase 4 — not pre-abstracted here.
"""
from __future__ import annotations

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
