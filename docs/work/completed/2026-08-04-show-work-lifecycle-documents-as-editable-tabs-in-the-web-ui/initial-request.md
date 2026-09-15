# Show work lifecycle documents as editable tabs in the web UI

When viewing a work item in the local web app, the work content area currently
shows only the initial request. The specification and implementation plan are
secondary artifact actions that open the files in the operating system's
default Markdown editor. This makes the item's core planning documents less
visible and sends the user out of the web workflow to inspect them.

Make the work content area provide first-class viewing and editing for the three
planning documents through tabs labeled exactly:

- Initial Request
- Spec
- Implementation Plan

Each tab should present its document in the web UI and support editing there in
the same way that the initial request is edited today. The initial request
should remain the initially selected view when a work item is opened.

This request is about the work-detail experience. It should reuse TCW's
existing lifecycle-artifact storage and web editing behavior rather than
changing the lifecycle model or requiring an external Markdown editor.

## Notes

- The requested tab labels and ordering come directly from the requester.
- No external reference material was supplied with the request.
