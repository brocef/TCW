Split from 2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker on 2026-09-14 by the autonomous session driving the epic.

The epic's goal 4 asks that tracker status *and concise progress links* stay current as the TCW lifecycle advances. 2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker moves the ticket's status only (its spec, Design section 10). This item holds the rest: publishing short progress links or comments to a bound ticket on lifecycle moves, without copying technical artifacts into the tracker.

Open questions for its request and spec: what is stable enough to link to, given TCW does not push code branches and work.repository.url is optional; when a link is published; and how a comment is de-duplicated against the ticket's existing comments (the epic's criterion 6 says no duplicate comment).

It is a child of the epic on purpose: two advisors and a spec review agreed the split is acceptable only if the epic cannot complete without either building this or deliberately discarding it.
