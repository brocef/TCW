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
from datetime import datetime, timezone
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
    modified: str = ""

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
    def check(self, identifier: str | None = None) -> list[str]:
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


@dataclass(frozen=True)
class PlanStage:
    """Storage-neutral metadata for one document declared by ``plan.md``."""
    id: str
    title: str
    depends_on: tuple[str, ...]
    effort: str = ""
    complexity: str = ""
    priority: int | None = None
    tags: tuple[str, ...] = ()
    present: bool = False
    revision: str = ""


@dataclass
class PlanStageResource:
    """A declared plan-stage document and its optimistic-lock token."""
    id: str
    content: str
    media_type: str = "text/markdown"
    revision: str = ""


@dataclass
class WorkDetail:
    """A work item with revision tokens for every editable resource."""
    item: WorkItem
    core_revision: str = ""
    artifact_revisions: dict[str, str] = field(default_factory=dict)
    sidecar_revisions: dict[str, str] = field(default_factory=dict)
    # True when the write that produced this detail created the item's request
    # where it had none — a promotion out of raw intake. Callers surface it so
    # the transition is announced rather than silent; it is always False on a
    # plain read.
    promoted: bool = False


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
    modified: str = ""

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
    def check(self, taxonomy: "TaxonomyStore | None" = None,
              identifier: str | None = None) -> list[str]:
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

WORK_STATUSES = ("backlog", "active", "review", "completed", "discarded")

# The two terminal statuses. `completed` means *shipped*; `discarded` means
# *closed without shipping*. Anything asking "is this item still open?" wants
# this tuple — anything asking "did this ship?" wants `completed` alone. The
# distinction is load-bearing: `tcw capabilities drift` reports a still-Missing
# capability only for work that actually shipped.
#
# `review` is deliberately NOT here. It means "implemented, acceptance pending",
# and verification can still reject the work (that is what the `rework` edge is
# for). Treating it as resolved would let a dependent start against work that
# may yet come back.
RESOLVED_STATUSES = ("completed", "discarded")

# The legal-transition graph lives in the *core* (phase-5-work B.1/B.3): the
# adapter only effects a move the core has already deemed legal. `drop` is
# handled separately (delete, backlog only).
LEGAL_TRANSITIONS = {
    ("backlog", "active"),                           # start
    ("active", "review"),                           # submit
    ("active", "completed"),                        # complete --resolution done
    ("active", "discarded"),                        # complete, any other resolution
    ("review", "active"),                           # rework — the one reverse edge
    ("review", "completed"),                        # complete --resolution done
    ("review", "discarded"),                        # complete, any other resolution
    ("backlog", "discarded"),                       # abandon without a throwaway start
}
WORK_RESOLUTIONS = {"done", "wontfix", "duplicate", "superseded"}


def resolution_status(resolution: str) -> str:
    """The terminal status a resolution closes into: `done` ships (`completed`),
    everything else is abandoned (`discarded`).

    Raises on an unknown resolution rather than guessing a destination. That
    matters for `check()`, which calls this on arbitrary persisted YAML: a
    silent `else: "discarded"` would make a corrupt-resolution item sitting in
    `discarded/` read as *consistent* and defeat the detector.
    """
    if resolution not in WORK_RESOLUTIONS:
        raise ValueError(f"invalid resolution '{resolution}' "
                         f"(choose: {', '.join(sorted(WORK_RESOLUTIONS))})")
    return "completed" if resolution == "done" else "discarded"
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


# ── Lifecycle policy (stage/transition bindings) ─────────────────────────────
#
# Two ladders. A **stage** produces one lifecycle artifact; a **transition** moves
# status. Nothing is both. These ids are **public API**: a user's
# `tcw-config.yaml` keys on them, so renaming one silently breaks their
# configuration. Insertions are safe; renames are not.

STAGE_IDS = ("inbox", "request", "spec", "plan", "implement", "verify", "postmortem")

# `discard` is a transition but **not** a CLI verb. Every other id here is the
# command you type; `discard` is reached as `complete --resolution <not-done>`,
# because the resolution picks the destination folder. Bindings key on the *move*
# rather than on the verb, so `complete --resolution done` fires `complete`'s
# hooks and `complete --resolution wontfix` fires `discard`'s. Keying on the verb
# instead would make one binding fire for two opposite outcomes — "we shipped it"
# and "we gave up on it" — which is exactly the distinction `discard` exists to
# preserve.
TRANSITION_IDS = ("start", "submit", "complete", "rework", "discard")


# Bound on a `generate` hook's stdout, in **raw bytes before decoding**.
# Enforced while reading rather than after, so a runaway script cannot exhaust
# memory before the check fires. Also the cap on the item `body` a hook gets.
DEFAULT_OUTPUT_CAP = 64 * 1024

# The only values `type` may hold. Named here because `Condition` validates
# against it and `create_work` checks it (`fs.py:3208`); two literals would be a
# way for a typo to be legal in one place and not the other.
WORK_TYPES = ("", "epic")

# What a binding may be, by role. `skill` is legal in a check position because it
# already is — `run_bindings` reports it to stderr without running it — and the
# back-compat table requires that unchanged. `command` in a prompt position is an
# error naming `generate`, *except* in a bare legacy stage list, which predates
# the distinction and cannot be renamed.
BINDING_KINDS = ("blob", "file", "generate", "builtin", "skill", "command")
CHECK_KINDS = frozenset({"command", "skill"})
PROMPT_KINDS = frozenset({"blob", "file", "generate", "builtin", "skill"})
ARTIFACT_KINDS = frozenset({"blob", "file", "generate", "builtin"})
LEGACY_PROMPT_KINDS = PROMPT_KINDS | {"command"}


@dataclass(frozen=True)
class Condition:
    """When a binding applies. Keys are ANDed; a list value means any-of.

    Three keys by decision, not by accident: every key added has to be validated,
    documented, and supported forever. `generate` exists so that pressure has
    somewhere to go — one unconditional generator receives the whole item and
    decides in real code.
    """
    tags: tuple[str, ...] = ()
    not_tags: tuple[str, ...] = ()
    type: str | None = None          # None = unset; "" matches a non-epic

    def matches(self, item: "WorkItem | None") -> bool:
        """With no item, a condition never matches.

        Resolution can be called without one — an artifact template for an item
        that does not exist yet. Treating "no item" as a match would fire every
        conditional binding at exactly the moment nothing is known.
        """
        if item is None:
            return False
        have = set(item.tags or ())
        if self.tags and not (have & set(self.tags)):
            return False
        if self.not_tags and (have & set(self.not_tags)):
            return False
        if self.type is not None and (item.type or "") != self.type:
            return False
        return True


@dataclass(frozen=True)
class Binding:
    """One configured hook: what it is, where its text or command comes from,
    and when it applies.

    `kind` + `value` rather than a field per kind — a field per kind is how a
    two-kind model becomes a six-kind mess. `builtin` carries an empty `value`;
    its YAML form is the literal `true`, which is a boolean and has no business
    in a string field.
    """
    kind: str = ""
    value: str = ""
    when: Condition | None = None

    @property
    def ref(self) -> str:
        """The binding's payload. Kept because seven call sites read it."""
        return self.value


@dataclass
class TransitionBindings:
    """`pre` may block the move; `post` may not."""
    pre: list[Binding] = field(default_factory=list)
    post: list[Binding] = field(default_factory=list)


@dataclass
class StageBindings:
    """A stage's checks and prompts.

    `legacy_prompt` records that the prompts arrived as a **bare list** rather
    than under `prompt:`. It is a real field and not an implementation detail:
    the two forms render differently — a legacy list groups skills ahead of
    commands, an explicit list concatenates in declaration order — and after
    parsing nothing else can tell them apart. It also decides whether `command`
    was legal in the list at all.
    """
    pre: list[Binding] = field(default_factory=list)
    prompt: list[Binding] = field(default_factory=list)
    legacy_prompt: bool = False


@dataclass
class LifecyclePolicy:
    """A node's configured bindings. Empty is the default."""
    stages: dict[str, StageBindings] = field(default_factory=dict)
    transitions: dict[str, TransitionBindings] = field(default_factory=dict)
    artifacts: dict[str, list[Binding]] = field(default_factory=dict)
    timeout: int = 300
    output_cap: int = DEFAULT_OUTPUT_CAP

    def stage(self, stage_id: str) -> list[Binding]:
        """A stage's **prompts**.

        This accessor kept its meaning through the roles rewrite, which is the
        accurate reading rather than a compatibility shim: stage bindings were
        never executed (`hooks.py:79-101` handles transitions only), so what they
        always were is what `prompt` names.
        """
        sb = self.stages.get(stage_id)
        return sb.prompt if sb else []

    def stage_checks(self, stage_id: str) -> list[Binding]:
        sb = self.stages.get(stage_id)
        return sb.pre if sb else []

    def stage_is_legacy(self, stage_id: str) -> bool:
        sb = self.stages.get(stage_id)
        return bool(sb and sb.legacy_prompt)

    def transition(self, transition_id: str) -> TransitionBindings:
        return self.transitions.get(transition_id, TransitionBindings())

    def artifact(self, name: str) -> list[Binding]:
        return self.artifacts.get(name, [])


DEFAULT_HOOK_TIMEOUT = 300


@dataclass(frozen=True)
class LifecycleStep:
    """One stage or transition, with the contract `tcw work lifecycle` reports.

    This table is the **single source of truth** for what each id is for and what
    it produces. Child-4's stage documents must agree with it, and having it in
    one machine-readable place is what makes that agreement checkable rather than
    a matter of two prose documents happening to say the same thing.
    """
    id: str
    kind: str                        # "stage" | "transition"
    objective: str
    inputs: tuple[str, ...] = ()     # lifecycle artifacts the step may read
    produces: str = ""               # the artifacts a stage writes; "" for transitions
    # The prose form of `produces`, and the only one anything renders: it is what
    # `tcw work lifecycle` prints and what `--json` ships under `produces`, so it
    # cannot move without breaking a compatibility baseline.
    produces_note: str = ""
    moves: str = ""                  # "from → to" for a transition; "" for a stage
    gates: tuple[str, ...] = ()      # what the tool refuses past


# Ordered: stages in lifecycle order, then transitions in the order they occur.
# `postmortem` is out-of-band — it holds no position in the ordering and is
# triggered by condition rather than by sequence — so it sits last among stages.
LIFECYCLE_STEPS: tuple[LifecycleStep, ...] = (
    LifecycleStep(
        id="inbox", kind="stage",
        objective="Triage a raw inbox entry into a work item.",
        produces=""),
    LifecycleStep(
        id="request", kind="stage",
        objective="Capture what is being asked for, and why.",
        produces="initial-request.md", produces_note="initial-request.md"),
    LifecycleStep(
        id="spec", kind="stage",
        objective="Decide what to build and why, before deciding how.",
        inputs=("initial-request.md",),
        produces="spec.md", produces_note="spec.md"),
    LifecycleStep(
        id="plan", kind="stage",
        objective="Decide how to build it, in ordered, checkable steps.",
        inputs=("initial-request.md", "spec.md"),
        produces="plan.md", produces_note="plan.md"),
    LifecycleStep(
        id="implement", kind="stage",
        objective="Build it, and record what actually happened.",
        inputs=("spec.md", "plan.md", "rework.md"),
        produces="outcome.md", produces_note="outcome.md"),
    LifecycleStep(
        id="verify", kind="stage",
        objective="Obtain the user's acceptance decision on the finished work.",
        inputs=("spec.md", "outcome.md"),
        produces="refined-outcome.md (accepted) or rework.md (rejected)",
        produces_note="refined-outcome.md (accepted) or rework.md (rejected)"),
    LifecycleStep(
        id="postmortem", kind="stage",
        objective="Find which stage first missed a problem. Out-of-band: legal "
                  "in review or after completion, and never changes status.",
        inputs=("initial-request.md", "spec.md", "plan.md", "outcome.md",
                "refined-outcome.md", "rework.md"),
        produces="post-mortem.md", produces_note="post-mortem.md"),
    LifecycleStep(
        id="start", kind="transition",
        objective="Begin implementation.", moves="backlog → active",
        gates=("unresolved blockers", "the initiative epic must be active")),
    LifecycleStep(
        id="submit", kind="transition",
        objective="Hand finished work to verification.", moves="active → review"),
    LifecycleStep(
        id="rework", kind="transition",
        objective="Send rejected work back for another pass.",
        moves="review → active",
        gates=("refined-outcome.md must be absent",)),
    LifecycleStep(
        id="complete", kind="transition",
        objective="Close the item as shipped.",
        moves="review | active → completed",
        gates=("unresolved blockers", "open initiative children",
               "declared capabilities reconciled", "worktree merge-back",
               "--confirm")),
    LifecycleStep(
        id="discard", kind="transition",
        objective="Close the item without shipping. Reached as "
                  "`complete --resolution <not-done>`, not a verb of its own.",
        moves="backlog | active | review → discarded",
        gates=("--confirm",)),
)

LIFECYCLE_STEPS_BY_ID = {s.id: s for s in LIFECYCLE_STEPS}

# Where each stage is legal. Contract data about the lifecycle, so it sits beside
# the table that declares what each stage is for rather than inside the verb that
# consults it — `tcw work stage` checks it, and `tcw work scaffold` will too.
#
# Two rows are worth reading twice:
#
# * `verify` includes `active` because `complete` moves from `review | active`,
#   so an item can be verified without ever having been submitted.
# * `postmortem` is `review` and `completed` — **not** `discarded`. The stage's
#   own objective says "legal in review or after completion", and the two
#   terminal statuses are deliberately distinct: `completed` means shipped,
#   `discarded` means closed without shipping. A post-mortem on work nobody did
#   is not the out-of-band review this stage is.
#
# `inbox` is empty: it runs before an item exists, so there is no status to be
# legal in and no item to resolve a stage against.
STAGE_STATUSES: dict[str, tuple[str, ...]] = {
    "inbox": (),
    "request": ("backlog",),
    "spec": ("backlog",),
    "plan": ("backlog",),
    "implement": ("active",),
    "verify": ("active", "review"),
    "postmortem": ("review", "completed"),
}


def _parse_condition(raw: Any, where: str, problems: list[str]) -> "Condition | None":
    """Parse a `when:` mapping. Every shape is validated, not just `type`'s value.

    An earlier draft checked the `type` value and let every other malformed shape
    crash at match time — `tags: bug` is the mistake everyone makes exactly once,
    and it should fail at `tcw validate` rather than by silently iterating a
    string's characters.
    """
    if not isinstance(raw, dict) or not raw:
        problems.append(f"{where}: 'when' must be a non-empty mapping with "
                        f"'tags', 'not_tags', and/or 'type'")
        return None
    unknown = set(raw) - {"tags", "not_tags", "type"}
    if unknown:
        problems.append(f"{where}: unknown 'when' key(s) {', '.join(sorted(unknown))}; "
                        f"expected 'tags', 'not_tags', or 'type'")
        return None
    lists: dict[str, tuple[str, ...]] = {}
    for key in ("tags", "not_tags"):
        if key not in raw:
            lists[key] = ()
            continue
        value = raw[key]
        if isinstance(value, str) or not isinstance(value, list):
            problems.append(f"{where}: 'when.{key}' must be a list of tags "
                            f"(write [{value}] rather than {value})"
                            if isinstance(value, str) else
                            f"{where}: 'when.{key}' must be a list of tags, "
                            f"got {type(value).__name__}")
            return None
        items = []
        for element in value:
            if not isinstance(element, str) or not element.strip():
                problems.append(f"{where}: 'when.{key}' element {element!r} must be "
                                f"a non-blank string")
                return None
            items.append(element.strip())
        lists[key] = tuple(items)
    kind = None
    if "type" in raw:
        value = raw["type"]
        if not isinstance(value, str):
            problems.append(f"{where}: 'when.type' must be a string, "
                            f"got {type(value).__name__}")
            return None
        if value not in WORK_TYPES:
            problems.append(f"{where}: 'when.type' value '{value}' is not a known "
                            f"item type; expected one of "
                            f"{', '.join(repr(t) for t in WORK_TYPES)}")
            return None
        kind = value
    return Condition(tags=lists["tags"], not_tags=lists["not_tags"], type=kind)


def _parse_binding(raw: Any, where: str, legal: "frozenset[str] | set[str]",
                   role: str, problems: list[str]) -> "Binding | None":
    """One binding: exactly one kind key, an optional `when:`.

    `legal` is the kind set the *position* allows, so the same parser serves all
    three roles and the "which kinds may appear here" rule lives in one table
    rather than in three call sites.
    """
    if not isinstance(raw, dict):
        problems.append(f"{where}: binding must be a mapping "
                        f"({{{' | '.join(sorted(legal))}}}: …), "
                        f"got {type(raw).__name__}")
        return None
    unknown = set(raw) - set(BINDING_KINDS) - {"when"}
    if unknown:
        problems.append(f"{where}: unknown binding key(s) {', '.join(sorted(unknown))}; "
                        f"expected one of {', '.join(BINDING_KINDS)}")
        return None
    declared = [k for k in BINDING_KINDS if k in raw]
    if len(declared) > 1:
        problems.append(f"{where}: binding declares {' and '.join(declared)}; "
                        f"choose one")
        return None
    if not declared:
        problems.append(f"{where}: binding declares no kind; expected one of "
                        f"{', '.join(BINDING_KINDS)}")
        return None
    kind = declared[0]
    if kind not in legal:
        hint = ""
        if kind == "command" and role in ("prompt", "artifact"):
            # The one misuse that is both likely and has a named alternative.
            hint = " — use 'generate' to run a script whose output is the text"
        problems.append(f"{where}: '{kind}' is not allowed in a {role} position; "
                        f"expected one of {', '.join(sorted(legal))}{hint}")
        return None

    value = raw[kind]
    if kind == "builtin":
        # `builtin: true` is a YAML boolean; anything else is a mistake, and the
        # value never reaches `Binding.value`, which is a str.
        if value is not True:
            problems.append(f"{where}: 'builtin' must be the value true, "
                            f"got {value!r}")
            return None
        text = ""
    else:
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{where}: binding '{kind}' must be a non-blank string")
            return None
        # `blob` is literal text: stripping it would silently edit a prompt.
        text = value if kind == "blob" else value.strip()

    when = None
    if "when" in raw:
        when = _parse_condition(raw["when"], where, problems)
        if when is None:
            return None
    return Binding(kind=kind, value=text, when=when)


def _parse_binding_list(raw: Any, where: str, problems: list[str],
                        legal: "frozenset[str] | set[str]" = CHECK_KINDS,
                        role: str = "check") -> list[Binding]:
    if not isinstance(raw, list):
        problems.append(f"{where}: expected a list of bindings, "
                        f"got {type(raw).__name__}")
        return []
    out: list[Binding] = []
    # Identity is (kind, value, when), not the value alone. The same script under
    # two different conditions is the obvious way to say "this prompt for bugs,
    # that one for features"; rejecting it would make conditions unusable.
    seen: set[tuple] = set()
    for i, entry in enumerate(raw):
        binding = _parse_binding(entry, f"{where}[{i}]", legal, role, problems)
        if binding is None:
            continue
        key = (binding.kind, binding.value, binding.when)
        if key in seen:
            problems.append(f"{where}: duplicate binding '{binding.kind}: "
                            f"{binding.ref}'")
            continue
        seen.add(key)
        out.append(binding)                            # declaration order is significant
    return out


def _check_artifact_list(bindings: list[Binding], where: str,
                         problems: list[str]) -> None:
    """First-match-wins makes some orders meaningless. Reject the obvious ones.

    Deliberately *syntactic*: an entry after an unconditional one can never run,
    and `builtin` is a fallback so it belongs last and unconditional. What this
    does **not** do is reason about whether a set of conditions is exhaustive —
    `type: epic` then `type: ""` also shadows everything after it, and detecting
    that is a solver. The initiative's spec rejects growing `when:` into a
    config language; this is the honest edge of what syntax can tell you.
    """
    blocked_by = None
    for i, b in enumerate(bindings):
        if blocked_by is not None:
            problems.append(
                f"{where}[{i}]: unreachable — entry {blocked_by} above it matches "
                f"unconditionally, and the first match wins")
            return
        if b.kind == "builtin":
            if b.when is not None:
                problems.append(f"{where}[{i}]: a 'builtin' artifact binding is the "
                                f"fallback, so it cannot carry a 'when'")
                return
            if i != len(bindings) - 1:
                problems.append(f"{where}[{i}]: a 'builtin' artifact binding must be "
                                f"last; it is the fallback and would shadow "
                                f"{len(bindings) - i - 1} entr"
                                f"{'y' if len(bindings) - i == 2 else 'ies'} below it")
                return
        if b.when is None:
            blocked_by = i


def _parse_stage(raw: Any, where: str, problems: list[str]) -> "StageBindings":
    """A stage entry: either a bare list (legacy) or a mapping of `pre`/`prompt`.

    The bare list is the shape every existing config uses, and it renders through
    the grouped renderer rather than in declaration order — so which form it
    arrived in has to be recorded, not inferred later. It also decides whether
    `command` was legal in the list: the explicit `prompt:` key rejects it and
    names `generate`, while the legacy list has always accepted it and cannot be
    renamed now.
    """
    if isinstance(raw, list):
        return StageBindings(
            prompt=_parse_binding_list(raw, where, problems,
                                       LEGACY_PROMPT_KINDS, "prompt"),
            legacy_prompt=True)
    if not isinstance(raw, dict):
        problems.append(f"{where}: expected a list of bindings, or a mapping with "
                        f"'pre' and/or 'prompt', got {type(raw).__name__}")
        return StageBindings()
    extra = set(raw) - {"pre", "prompt"}
    if extra:
        problems.append(f"{where}: unknown key(s) {', '.join(sorted(extra))}; "
                        f"expected 'pre' or 'prompt', or a bare list of bindings")
    sb = StageBindings()
    if raw.get("pre") is not None:
        sb.pre = _parse_binding_list(raw["pre"], f"{where}.pre", problems,
                                     CHECK_KINDS, "check")
    if raw.get("prompt") is not None:
        sb.prompt = _parse_binding_list(raw["prompt"], f"{where}.prompt", problems,
                                        PROMPT_KINDS, "prompt")
    return sb


def parse_lifecycle_policy(raw: Any) -> tuple[LifecyclePolicy, list[str]]:
    """Parse a `work.lifecycle` mapping into a policy plus a problem list.

    Pure: takes an already-loaded object, touches no filesystem, and never raises.
    `tcw validate` reports the problems and the adapter discards them — reading a
    policy must not break `tcw work list` just because someone mistyped a key.
    One implementation so the two can never disagree about what is legal, which
    is the drift this whole initiative exists to remove.
    """
    policy = LifecyclePolicy()
    problems: list[str] = []
    if raw is None:
        return policy, problems
    if not isinstance(raw, dict):
        return policy, [f"work.lifecycle: expected a mapping, got {type(raw).__name__}"]

    top = {"stages", "transitions", "timeout", "artifacts", "output-cap"}
    unknown = set(raw) - top
    if unknown:
        problems.append(f"work.lifecycle: unknown key(s) {', '.join(sorted(unknown))}; "
                        f"expected {', '.join(repr(k) for k in sorted(top))}")

    timeout = raw.get("timeout", DEFAULT_HOOK_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        problems.append("work.lifecycle.timeout: expected a positive integer "
                        "(seconds)")
    else:
        policy.timeout = timeout

    cap = raw.get("output-cap", DEFAULT_OUTPUT_CAP)
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        problems.append("work.lifecycle.output-cap: expected a positive integer "
                        "(bytes)")
    else:
        policy.output_cap = cap

    stages = raw.get("stages")
    if stages is not None:
        if not isinstance(stages, dict):
            problems.append(f"work.lifecycle.stages: expected a mapping, "
                            f"got {type(stages).__name__}")
        else:
            for sid, value in stages.items():
                where = f"work.lifecycle.stages.{sid}"
                if sid not in STAGE_IDS:
                    problems.append(f"{where}: unknown stage id; expected one of "
                                    f"{', '.join(STAGE_IDS)}")
                    continue
                policy.stages[sid] = _parse_stage(value, where, problems)

    artifacts = raw.get("artifacts")
    if artifacts is not None:
        if not isinstance(artifacts, dict):
            problems.append(f"work.lifecycle.artifacts: expected a mapping, "
                            f"got {type(artifacts).__name__}")
        else:
            for name, value in artifacts.items():
                where = f"work.lifecycle.artifacts.{name}"
                if name not in WORK_ARTIFACTS:
                    problems.append(f"{where}: unknown artifact; expected one of "
                                    f"{', '.join(WORK_ARTIFACTS)}")
                    continue
                bindings = _parse_binding_list(value, where, problems,
                                               ARTIFACT_KINDS, "artifact")
                _check_artifact_list(bindings, where, problems)
                policy.artifacts[name] = bindings

    transitions = raw.get("transitions")
    if transitions is not None:
        if not isinstance(transitions, dict):
            problems.append(f"work.lifecycle.transitions: expected a mapping, "
                            f"got {type(transitions).__name__}")
        else:
            for tid, value in transitions.items():
                where = f"work.lifecycle.transitions.{tid}"
                if tid not in TRANSITION_IDS:
                    problems.append(f"{where}: unknown transition id; expected one "
                                    f"of {', '.join(TRANSITION_IDS)}")
                    continue
                if not isinstance(value, dict):
                    problems.append(f"{where}: expected a mapping with 'pre' and/or "
                                    f"'post', got {type(value).__name__}")
                    continue
                extra = set(value) - {"pre", "post"}
                if extra:
                    problems.append(f"{where}: unknown key(s) "
                                    f"{', '.join(sorted(extra))}; expected 'pre' or 'post'")
                bindings = TransitionBindings()
                for phase in ("pre", "post"):
                    if value.get(phase) is not None:
                        setattr(bindings, phase, _parse_binding_list(
                            value[phase], f"{where}.{phase}", problems))
                policy.transitions[tid] = bindings

    return policy, problems


DEFAULT_DOD = ("tests pass", "docs synced", "capabilities reconciled",
               "reviewed", "version offered")
# Appended, never inserted in lifecycle position: the tuple's order drives the
# stage-letter string in `tcw work list`, so inserting would shift every
# existing item's display.
WORK_ARTIFACTS = ("initial-request", "spec", "plan", "outcome", "refined-outcome",
                  "rework", "post-mortem", "intake")

# Bounded sidecar registry — each entry declares the expected media type and
# the validation rule applied before persistence.  New sidecars are added here.
WORK_SIDECARS: dict[str, dict[str, str]] = {
    "capabilities.yaml": {
        "media_type": "application/yaml",
        "validation": "yaml_mapping",
    },
    # Generated by `tcw work reconcile`, not written by a lifecycle stage — which
    # is why it is a sidecar and not a `WORK_ARTIFACTS` name. As an artifact it
    # would carry a board letter and imply a stage it has no position in.
    # `generated` marks a sidecar a command writes rather than a person. Read
    # surfaces treat it like any other; edit surfaces must not offer to write it,
    # since the next run of the command that produces it discards the edit.
    "rollup.md": {
        "media_type": "text/markdown",
        "generated": "yes",
    },
}

# Taxonomy term fields that the abstract ``update_term`` operation may modify.
TAXONOMY_EDITABLE_FIELDS = frozenset({"name", "description", "kind", "relates_to", "vocabulary"})


class IllegalTransition(Exception):
    """A status transition not in the legal graph (the enforcement — B.3)."""


class TransitionCommitError(Exception):
    """A transition moved the item but its auto-commit was refused.

    Deliberately distinct from every other store error, because the item **did
    move** — reporting this as a failed transition would be false, and would
    invite a caller to retry a move that already happened. The status is correct
    on disk; only the commit is missing, and the operator can make it by hand.

    Raised by the FS adapter when `git_commit_result` reports a real failure (a
    held `index.lock`, no write permission, a rejecting pre-commit hook). Benign
    conditions — not a repository, nothing to commit — never raise.
    """


class MultipleMatch(Exception):
    """A slug resolves to more than one item folder (slug integrity broken)."""


class AlreadyClaimed(IllegalTransition):
    """A single-winner start lost to an existing active claim."""

    def __init__(self, slug: str, owner: str = "", started: str = ""):
        self.slug, self.owner, self.started = slug, owner, started
        who = owner or "an unknown owner"
        when = started or "an unknown time"
        super().__init__(f"{slug} is already claimed by {who} since {when}")


@dataclass
class WorkItem:
    """A unit of work; status is *where it lives*, not a stored field (A.3)."""
    slug: str
    title: str
    status: str
    created: str = ""
    modified: str = ""               # adapter-provided last-modified timestamp
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
    owner: str = ""                 # claimant identity; empty for legacy/unclaimed active work
    started: str = ""               # UTC claim timestamp


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
               priority: int | None = None, parent: str | None = None,
               intake: str = "") -> WorkItem:
        """Create an item. With `parent` (a slug), create it as a child of that
        item — an abstract node relation; the adapter realizes the nesting.

        `body` is the item's **request**; `intake` is the raw, unprocessed input
        it started from. They are separate arguments rather than one because an
        adapter must be able to tell them apart — a tracker that files intake as
        a comment and the request as a description cannot recover the distinction
        from a single field. Either may be empty, including both: an item created
        with neither has no body yet, and that is a state, not a defect."""

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
    def locate(self, slug: str) -> str | None:
        """A short, human-readable location for the item's current home, or None
        if the item does not exist. Adapters realize it however fits their backing
        store (a filesystem: the repo-relative folder path; a remote tracker: an
        issue URL or status label). Presentation only — do not parse it."""

    @abstractmethod
    def plan_stages(self, slug: str) -> list[PlanStage]:
        """Return the ordered, bounded stages declared by the item's plan."""

    @abstractmethod
    def read_plan_stage(self, slug: str, stage_id: str) -> PlanStageResource | None:
        """Read a declared stage document, or ``None`` when it is absent."""

    @abstractmethod
    def write_plan_stage(self, slug: str, stage_id: str, content: str,
                         revision: str | None = None) -> PlanStageResource:
        """Replace a declared stage document with optional stale-write protection."""

    @abstractmethod
    def delete_artifact(self, slug: str, name: str) -> None:
        """Remove a lifecycle artifact, if it is present.

        A no-op when it is absent, so callers need not probe first.  Raises
        ``ValueError`` for unknown artifact names.
        """

    @abstractmethod
    def delete_plan_stage(self, slug: str, stage_id: str,
                          revision: str | None = None) -> None:
        """Delete a declared stage document with optional stale-write protection."""

    @abstractmethod
    def plan_stage_locator(self, slug: str, stage_id: str) -> str | None:
        """Resolve a declared stage to an openable handle, if supported."""

    @abstractmethod
    def set_field(self, slug: str, key: str, value) -> None: ...

    @abstractmethod
    def _effect_transition(self, slug: str, to_status: str,
                           fields: dict | None = None) -> None:
        """Move `slug` to `to_status`, applying `fields` as part of the move.

        The fields ride the transition rather than preceding it so a transition
        that loses a race to a competing process changes nothing at all — the
        loser's `resolution` must not land on the item the winner moved. Any
        backend can honor this: a remote tracker's transition endpoint takes the
        field updates in the same call for the same reason.
        """

    @abstractmethod
    def _delete(self, slug: str) -> None: ...

    @abstractmethod
    def dod_checklist(self) -> list[str]: ...

    # -- tag registry (a node-scoped controlled vocabulary; any backend can
    #    realize a registered set + membership check) --

    @abstractmethod
    def lifecycle_policy(self) -> LifecyclePolicy:
        """The node's configured stage/transition bindings; empty when unset.

        The *policy* is storage-neutral — any backend can serve a mapping of ids
        to references. *Executing* what it declares is not: running a shell
        command is a local concern and lives in the CLI, never here.
        """

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
    def check(self, identifier: str | None = None) -> list[str]:
        """Validate the work node, optionally limited to one object. Reports items
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
                    tags: list[str] | None = None,
                    intake: str = "") -> "WorkDetail":
        """Create a work item with all fields in one atomic operation.

        * ``title`` — required, non-empty display name.
        * ``body`` — the item's request; written only when non-empty.
        * ``intake`` — the raw input the item started from; written only when
          non-empty.  Kept distinct from ``body`` so an adapter knows which it
          was handed (see ``create``).
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

    @staticmethod
    def _normalize_ref(ref: str) -> str:
        """Canonical form of a blocker ref: strip one leading `external:` label.

        Display renders an external blocker as `external: <text>`, so input has to
        accept that string back or the board's own output isn't a usable ref. A
        slug can never start with `external:` (slugify → [a-z0-9-]), so stripping
        before the slug probe is safe.
        """
        ref = ref.strip()
        if ref.lower().startswith("external:"):
            ref = ref[len("external:"):].strip()
        return ref

    def _entry_for(self, ref: str) -> dict:
        """A blocker entry: a resolvable ref → {slug}, else {external}."""
        ref = self._normalize_ref(ref)
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
        """Remove one blocker. Fails closed on a ref that matches nothing.

        Deliberately asymmetric with `add_blocker`, which is idempotent: adding a
        blocker that's already there is harmless, but silently "removing" one that
        isn't there tells the caller the item is unblocked when it still is.
        """
        item = self._require(slug)
        norm = self._normalize_ref(ref)
        kept = [e for e in item.blocked_by
                if e.get("slug") != norm and e.get("external") != norm]
        if len(kept) == len(item.blocked_by):
            raise ValueError(f"no such blocker on {slug}: {ref}")
        self.set_field(slug, "blocked_by", kept)

    def board(self, status: str | None = None) -> list[WorkItem]:
        """The board in workable order: query(status) priority-sorted, then
        topologically sorted (a blocker still precedes what it blocks)."""
        return topo_order(priority_order(self.query(status)))

    def epic_completable(self, item: WorkItem) -> bool:
        """True iff `item` is an epic that is ready to close: it is `type: epic`,
        not already resolved, has at least one initiative child, and every child
        is resolved (completed *or* discarded — a child nobody will do no longer
        holds its epic open). Built on `initiative_children` (cross-node in
        adapters that override it), so the "all resolved" signal and the
        `complete` gate share one source of truth. An empty epic is not
        completable (nothing resolved)."""
        if item.type != "epic" or item.status in RESOLVED_STATUSES:
            return False
        children = self.initiative_children(item.slug)
        return bool(children) and all(c.status in RESOLVED_STATUSES for c in children)

    def transition(self, slug: str, to_status: str,
                   fields: dict | None = None) -> WorkItem:
        """Move the item, applying `fields` as part of the move.

        Nothing is written before `_effect_transition`: on a lost race the writes
        would land in the folder the winner moved, stamping this process's data
        onto the winner's item. Clearing the claim is not negotiable, so it is
        applied *over* the caller's fields rather than under them.
        """
        item = self._require(slug)
        if (item.status, to_status) not in self.LEGAL_TRANSITIONS:
            raise IllegalTransition(f"{item.status} → {to_status} is not a legal transition")
        merged = dict(fields or {})
        if item.status == "active" or to_status == "active":
            merged.update({"owner": "", "started": ""})
        self._effect_transition(slug, to_status, merged)
        return self._require(slug)

    def unresolved_blockers(self, item: WorkItem) -> list[str]:
        """Labels of blockers that still block `item`. An entry is unresolved if
        it is external, or a slug whose item is not resolved — a *discarded*
        blocker no longer blocks, since a decision not to do it is as final as
        doing it. A slug that no longer resolves counts as resolved (silently)."""
        out: list[str] = []
        for b in item.blocked_by:
            if "external" in b:
                out.append(f"external: {b['external']}")
            elif "slug" in b:
                try:
                    blocker = self.get(b["slug"])
                except ValueError:
                    # An adapter can refuse to settle a blocker — a claim on it
                    # was abandoned. That is still a blocker, and reporting it as
                    # one keeps this item's caller reading about *this* item.
                    # Raising the blocker's error here would answer "why can't I
                    # start B?" with a message about A. Storage-neutral: any
                    # adapter may fail to resolve a reference.
                    out.append(b["slug"])
                    continue
                if blocker is not None and blocker.status not in RESOLVED_STATUSES:
                    out.append(b["slug"])
            # else: structurally malformed entry — skip (degrade, don't crash)
        return out

    def start(self, slug: str, force: bool = False, *, owner: str = "",
              take_over: bool = False) -> WorkItem:
        item = self._require(slug)
        if item.status == "active":
            if not take_over:
                raise AlreadyClaimed(slug, item.owner, item.started)
            if not owner:
                raise ValueError("takeover requires an owner")
            self.set_field(slug, "owner", owner)
            self.set_field(slug, "started", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
            return self._require(slug)
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
        result = self.transition(slug, "active")
        if owner:
            self.set_field(slug, "owner", owner)
            self.set_field(slug, "started", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
            result = self._require(slug)
        return result

    def submit(self, slug: str) -> WorkItem:
        """`active` → `review`: implementation is done, acceptance is pending.

        Carries no gate. `outcome.md` being present is a *check* the agent makes,
        not something the tool refuses past — submitting work whose outcome
        document is still unwritten is a judgment call the operator is allowed to
        make, and refusing would be the tool inventing a policy.
        """
        return self.transition(slug, "review")

    def rework(self, slug: str) -> WorkItem:
        """`review` → `active`: verification rejected the work.

        Fails closed while `refined-outcome.md` is present. That document asserts
        the work was verified and accepted; after a rejection the assertion is
        simply false, and leaving it in place would let the next reader trust it.
        TCW does not delete it — silently destroying a user's document to unblock
        a transition is the wrong shape — so the refusal names the file and the
        action instead.

        This is the *only* transition the artifact gates. `complete` from
        `review` is unaffected on either resolution: a present
        `refined-outcome.md` is the normal path into `--resolution done`, and
        abandoning verified work as `wontfix` is a legitimate decision. Only
        `rework` asserts the opposite of what the file says.
        """
        if any(a.name == "refined-outcome" and a.present
               for a in self.artifacts(slug)):
            raise ValueError(
                f"cannot rework {slug}: refined-outcome.md still asserts this "
                "work was verified. Delete it (and write rework.md describing "
                "what remains) before sending the item back."
            )
        return self.transition(slug, "active")

    def complete(self, slug: str, resolution: str, dod_ack: list[str],
                 force: bool = False) -> WorkItem:
        dest = resolution_status(resolution)          # raises on a bad resolution
        item = self._require(slug)
        # A completable epic (all children resolved) may close straight from
        # `backlog` — coordinator epics never needed their own start/active. This
        # is a scoped exception, not a global `(backlog, completed)` transition,
        # and it is `done`-only: `(backlog, discarded)` is a real transition that
        # any item may take, so it needs no exception.
        from_backlog_epic = (dest == "completed" and item.status == "backlog"
                             and self.epic_completable(item))
        if (item.status, dest) not in self.LEGAL_TRANSITIONS and not from_backlog_epic:
            raise IllegalTransition(f"cannot complete from {item.status} "
                                    f"as '{resolution}' (→ {dest})")
        if not force:
            # The epic gate applies to *both* routes: an initiative child cannot
            # start until its epic is active, so closing an epic with open
            # children strands them either way.
            if item.type == "epic":
                open_children = [i.slug for i in self.initiative_children(slug)
                                 if i.status not in RESOLVED_STATUSES]
                if open_children:
                    raise ValueError(f"Cannot complete epic {slug}; initiative "
                                     f"children are still open: "
                                     f"{', '.join(open_children)}. Complete or "
                                     f"defer them first.")
            # Blockers gate a *shipment*, not an abandonment. "Don't claim you
            # shipped this while its dependency is unfinished" says nothing
            # about giving up — being blocked indefinitely is one of the most
            # common reasons to discard something, so requiring --force there
            # would be friction on the path `discarded` exists to smooth.
            if dest == "completed":
                blockers = self.unresolved_blockers(item)
                if blockers:
                    raise ValueError("blocked by: " + ", ".join(blockers)
                                     + " (use --force to override)")
        # The resolution rides the transition rather than preceding it: written
        # first, a `complete` that then loses the move would leave its resolution
        # on the item the winner moved — an item reading `wontfix` in
        # `completed/`. `_status_resolution_problems` calls that a defect, and it
        # was reachable from here.
        #
        # `dod_ack` is deliberately not persisted. It was written to every
        # completed item as the same fixed 5-string constant — `_complete` passes
        # the whole checklist unconditionally — so it recorded nothing that could
        # ever differ. The checklist is still *printed* before `--confirm`, which
        # is the only thing it ever really did.
        #
        # The parameter stays in the signature: removing it is an interface
        # change for no gain, and a remote adapter may have somewhere to put it.
        # Items completed before this change keep their stored `dod:` unread,
        # exactly as `phase` was handled — no rewrite pass.
        fields = {"resolution": resolution}
        if from_backlog_epic:                               # bypass transition()'s own
            self._effect_transition(slug, dest, fields)     # LEGAL_TRANSITIONS check
            return self._require(slug)
        return self.transition(slug, dest, fields)

    def drop(self, slug: str) -> None:
        item = self._require(slug)
        if item.status != "backlog":
            raise IllegalTransition(f"cannot drop from {item.status} (only backlog)")
        self._delete(slug)
