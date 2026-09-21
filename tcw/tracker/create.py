"""Making a ticket for a work item that has none.

The tracker integration ran one way until this module: `import` builds an item
from a ticket, `link` binds two things that already exist. Neither creates a
ticket, so a team with a TCW backlog could only get it into their tracker by
scripting against the tracker's own API — which is what this repository did on
2026-09-20 for 53 items, and what GitHub #43 reports at 116.

**A created ticket is not finished when it exists.** Jira puts a new issue in
whatever status the project's workflow starts in, and a project with a triage
column starts it *there* — which is the status `work.tracker.inbox-query` is
most likely to select. A ticket left where creation put it therefore comes back
through `tcw work inbox` as untriaged inbound work, offering to create a second
item for the one that just created it. Moving it out is part of creating it,
not a courtesy, and `create_and_place` refuses rather than skip that step.

**Where it stops.** This module takes a ticket from "does not exist" to "exists,
and is in the status a *backlog* item's ticket belongs in". It does not climb any
further, and that is deliberate: an item already under way needs a claim, an
assignment and a walk up the status ladder, all of which `tcw/tracker/sync.py`
already does for a bound ticket and none of which is about creation. The caller
binds and then hands over, exactly as `tcw work tracker link --sync-status`
does — which is the sequence the 2026-09-20 backfill arrived at by hand.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcw.store.base import target_status
from tcw.tracker.jira import TrackerError
from tcw.tracker.sync import _normalize


@dataclass(frozen=True)
class Created:
    """A ticket that now exists, and where it ended up.

    No `url`: the caller binds through `_tracker_link`, which re-reads the ticket
    and uses the URL the tracker itself reports. A second, locally composed one
    would be a second thing that can be wrong.
    """
    issue_id: str
    key: str
    status: str


def description_document(*, slug: str, body: str, item_url: str = "") -> dict:
    """The ticket's description: the item's own words, then where they live.

    Plain paragraphs rather than a faithful Markdown rendering. The item is the
    source of truth and the ticket is a pointer to it, so a description that
    merely reads well and says where to look is doing its whole job; converting
    headings and lists would be a second document format to keep in step.
    """
    def paragraph(text: str) -> dict:
        return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

    blocks = [paragraph(part.strip()) for part in body.split("\n\n") if part.strip()]
    if not blocks:
        blocks = [paragraph("No request or intake was written for this item.")]
    blocks.append(paragraph(f"Tracked in TCW as {slug}."))
    if item_url:
        blocks.append({"type": "paragraph", "content": [
            {"type": "text", "text": item_url,
             "marks": [{"type": "link", "attrs": {"href": item_url}}]}]})
    return {"type": "doc", "version": 1, "content": blocks}


def placement_target(config) -> str:
    """Where a created ticket belongs, or `""` when the project has not said.

    Always the **backlog** status, and it takes no item status *because* there is
    nothing to vary: a created ticket starts at the bottom whatever the item is. A ticket
    for work already under way still starts at the bottom and is walked up by
    the delivery path, because that path is what claims and assigns it; jumping
    straight to `In Progress` would leave a ticket in progress that nobody holds.
    """
    return target_status(config.statuses, "backlog", None)


def unplaceable(config) -> str | None:
    """Why creation cannot run, or `None`.

    Checked *before* anything is created. A refusal afterwards would leave a
    real ticket in a shared tracker that TCW then declined to bind — the one
    failure this whole module exists to avoid.
    """
    if config.create is None:
        return ("work.tracker.create is not configured, so there is nothing to say "
                "what a ticket should look like.")
    if not placement_target(config):
        return ("work.tracker.statuses.backlog is not set, so there is nowhere to put "
                "a created ticket. Without it the ticket stays in whatever status the "
                "tracker starts issues in, which is usually the one inbox-query "
                "selects — so it would come back as new inbound work.")
    return None


def create_and_place(client, config, *, slug: str, title: str, body: str,
                     is_epic: bool, tags, item_url: str = "",
                     on_created=None) -> Created:
    """Create the ticket for one item and move it to the backlog status.

    `on_created` is called with the key the moment the tracker reports it, before
    anything else can fail. That is what lets an interrupted run resume by
    binding rather than by creating a second ticket: the key outlives the crash.
    """
    refusal = unplaceable(config)
    if refusal:
        raise TrackerError(refusal)
    settings = config.create
    issue = client.create_issue(
        project=settings.project,
        summary=title,
        description=description_document(slug=slug, body=body, item_url=item_url),
        issue_type=settings.type_for(is_epic=is_epic, tags=tags),
        components=settings.components,
    )
    key, issue_id = str(issue.get("key", "")), str(issue.get("id", ""))
    if on_created is not None:
        on_created(key, issue_id)

    target = placement_target(config)
    status = _place(client, issue_id, key, target)
    return Created(issue_id=issue_id, key=key, status=status)


def _current_status(client, key: str) -> str:
    """The issue's status right now, read back from the tracker."""
    fields = (client.issue(key) or {}).get("fields") or {}
    return str((fields.get("status") or {}).get("name", ""))


def _place(client, issue_id: str, key: str, target: str) -> str:
    """Move a just-created ticket to `target`, and confirm it arrived.

    Three things this has to get right, each learned the hard way.

    **It may already be there.** A Jira project with no triage column creates
    issues straight into its backlog status, and Jira offers no self-transition,
    so demanding one refused *after* the ticket existed and left it bound to
    nothing. Most projects are that shape; the one this was written against is
    not, which is why the case was missed until Codex named it.

    **One hop, not a walk.** A workflow that cannot reach its own backlog column
    from its entry status in a single step is one TCW should not be guessing its
    way through, so an unreachable target is reported with what *was* offered.
    The hop is matched on destination, never on name: the real transition was
    `Accept → To Do`, and matching on name would never have fired.

    **Accepted is not applied.** `apply_transition` says only that Jira accepted
    the request — a validator can decline it silently. Believing an unmoved
    ticket is placed is the entire hazard this module exists for: it would sit
    in the entry status, which is what `inbox-query` selects, while TCW recorded
    it as filed. So the status is read back.
    """
    status = _current_status(client, key)
    if _normalize(status) == _normalize(target):
        return status

    offered = client.transitions(key)
    leads = [t for t in offered if _normalize(t.to_status) == _normalize(target)]
    if len(leads) > 1:
        # The same refusal `assess_move` makes, for the same reason: a second
        # route into one status is a different workflow path with different
        # post-functions, and TCW will not guess which. Dropping this guard here
        # would have reversed that policy for created tickets only.
        ids = ", ".join(sorted(t.id for t in leads))
        raise TrackerError(
            f"{key} offers more than one transition to '{target}' (ids {ids}); "
            f"TCW will not guess which. The ticket is in the tracker and is not "
            f"bound to any item; move it by hand.")
    if leads:
        client.apply_transition(issue_id, leads[0].id)
        landed = _current_status(client, key)
        if _normalize(landed) != _normalize(target):
            raise TrackerError(
                f"{key} was created but did not reach '{target}': it is in "
                f"'{landed}'. The transition was accepted and did not apply, so "
                f"the ticket is in the tracker and is not bound to any item; "
                f"move it by hand.")
        return landed
    names = ", ".join(f"{t.name} → {t.to_status}" for t in offered) or "none"
    raise TrackerError(
        f"{key} was created in '{status}' but could not be moved to '{target}': "
        f"the transitions offered are {names}. It is in the tracker and is not "
        f"bound to any item; move it by hand, or correct "
        f"work.tracker.statuses.backlog.")
