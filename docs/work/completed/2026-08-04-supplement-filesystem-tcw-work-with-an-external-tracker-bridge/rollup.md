<!-- tcw:rollup -->
### Rollup: 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge

| node | slug | status | blocked-by |
|---|---|---|---|
| . | 2026-09-12-configure-an-external-tracker-and-read-its-tickets | completed | - |
| . | 2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item | completed | 2026-09-12-configure-an-external-tracker-and-read-its-tickets |
| . | 2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app | completed | 2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item |
| . | 2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket | completed | - |
| . | 2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker | completed | 2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item, 2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket |
| . | 2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes | completed | 2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker |
| . | 2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket | completed | 2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker |

**Capability deltas:**
- ./2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes: changed work/require-tracker-backed-work
- ./2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes: changed work/open-a-work-item
- ./2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes: changed work/start-a-work-item
- ./2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes: changed work/drop-a-work-item
- ./2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes: changed work/manage-external-tracker-intake
- ./2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes: changed work/synchronize-external-tracker-work
- ./2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app: changed work/read-a-work-item
- ./2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app: changed work/view-the-board
- ./2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app: changed work/manage-external-tracker-intake
- ./2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker: changed work/synchronize-external-tracker-work
- ./2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker: changed work/manage-external-tracker-intake
- ./2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker: changed work/start-a-work-item
- ./2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker: changed work/read-a-work-item
- ./2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker: changed work/view-the-board
- ./2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket: changed work/manage-external-tracker-intake
- ./2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket: changed work/synchronize-external-tracker-work

**Ready to close:** all 7 children resolved — run `tcw work complete 2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge --resolution done --confirm`
<!-- /tcw:rollup -->
