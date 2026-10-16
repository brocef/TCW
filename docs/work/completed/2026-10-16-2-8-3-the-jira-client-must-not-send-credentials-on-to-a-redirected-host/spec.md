# Spec — 2.8.3: the Jira client must not send credentials on to a redirected host

A patch to the released 2.8.x line. Every file and line named here was read on
`main` at `8dbfb8a0`.

## Capability changes

None. No capability is added, removed or changed: what the tracker commands do
for a user is the same, and no capability record describes how the client
builds its requests.

## Problem

`JiraClient._request` (`tcw/tracker/jira.py:152`) adds the basic-authentication
header with `request.add_header("Authorization", …)` and then calls
`urllib.request.urlopen`. When the answer is a redirect, urllib's
`HTTPRedirectHandler.redirect_request` builds the new request with a copy of
`req.headers` (every header added with `add_header`, less the content headers),
whatever host the redirect points at. So a redirect from the Jira site, or from
anything between it and the user, to another host receives the user's email
address and API token.

`_request` is the only place in `tcw/` that sends credentials: a search of
`tcw/` for `Authorization`, `add_header` and `urlopen` finds only this function.

## Design

Add the header with `request.add_unredirected_header("Authorization", …)`.
urllib sends an unredirected header on the request it was added to and never
copies it onto a redirect. A redirected request therefore arrives without
credentials: another host learns nothing secret, and one that leads back to Jira
is refused as unauthenticated (`TrackerAuthError`) rather than leaking.

This also drops the header on a redirect to the same host. The REST calls this
client makes are not expected to be redirected, and a project whose `base_url`
redirects (for example `http://` to `https://`) gets an authentication error
that points at the configuration instead of silently working; that trade is
accepted.

## Acceptance criteria

1. The request to the configured tracker carries the `Authorization` header.
2. A request that follows a redirect to another host carries no
   `Authorization` header.
3. A test proves 1 and 2 against two real local HTTP servers (localhost only),
   and goes red when the fix is reverted to `add_header`.
4. The full suite passes under bare `pytest`, as CI runs it.
5. Changelog and release-notes entries are added under `upcoming/`.
