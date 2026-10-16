## Fixed

- The Jira client no longer sends the user's credentials to a host a redirect points at. `JiraClient._request` (`tcw/tracker/jira.py`) added the basic-authentication header with `Request.add_header`, and urllib's `HTTPRedirectHandler` copies those headers onto the redirected request whatever its host. It now uses `add_unredirected_header`, so a redirected request carries no `Authorization` header; one that comes back to Jira is refused as unauthenticated (`TrackerAuthError`). A test redirects between two local servers and asserts the second receives no credentials.
