"""Work routes.

Until the work API is rebuilt on the 3.0 backend, `GET /api/work` and
`GET /api/work/tags` answer an empty list, so today's client still loads
taxonomy and capabilities beside an empty board.
"""

from __future__ import annotations

from http import HTTPStatus

from tcw.serve.server import Request, route


def _empty(request: Request):
    return HTTPStatus.OK, []


ROUTES = [
    route("GET", r"/api/work", _empty),
    route("GET", r"/api/work/tags", _empty),
]
