"""Host and Origin on every request, JSON writes, the body cap and the content
security policy (TCW-77 criterion 4, except the Jira credential marker, which
is in `test_work_write.py`)."""

from __future__ import annotations

import pytest

from tcw.serve.server import MAX_BODY_BYTES, from_loopback

POLICY = "default-src 'self'"


def assert_forbidden(answer):
    assert answer.status == 403, answer.body
    assert answer.json["code"] == "forbidden"
    assert answer.headers["content-security-policy"] == POLICY


def test_a_foreign_host_is_refused(fs):
    assert_forbidden(fs.get("/api/work", host="evil.example"))


def test_a_foreign_origin_is_refused(fs):
    assert_forbidden(fs.get("/api/work", origin="http://evil.example"))


def test_no_host_and_no_origin_is_refused(fs):
    assert_forbidden(fs.get("/api/work", host=None))


def test_no_host_with_a_loopback_origin_is_refused(fs):
    assert_forbidden(fs.get("/api/work", host=None,
                            origin=f"http://127.0.0.1:{fs.port}"))


def test_static_files_check_the_host_too(fs):
    assert_forbidden(fs.get("/", host="evil.example"))


@pytest.mark.parametrize("host", ["127.0.0.1:{port}", "localhost:{port}", "[::1]:{port}",
                                  "localhost", "127.0.0.1"])
def test_loopback_hosts_are_answered(fs, host):
    answer = fs.get("/api/taxonomy", host=host.format(port=fs.port),
                    origin=f"http://localhost:{fs.port}")
    assert answer.status != 403, answer.body


@pytest.mark.parametrize(("host", "origin", "ok"), [
    ("127.0.0.1:1", None, True),
    ("localhost", "http://[::1]:5", True),
    ("127.0.0.1.evil.example", None, False),
    ("evil.example:127", None, False),
    ("127.0.0.1:1", "null", False),
    ("127.0.0.1:1", "http://127.0.0.1.evil.example", False),
    ("127.0.0.1:1", "file://", False),
    (None, "http://127.0.0.1:1", False),
    ("", None, False),
])
def test_the_loopback_rule(host, origin, ok):
    assert from_loopback(host, origin) is ok


def test_a_write_that_is_not_json_is_refused_and_creates_nothing(fs):
    before = sorted((fs.root / "docs" / "work").iterdir())
    answer = fs.request("POST", "/api/work", raw=b'{"title": "x"}',
                        content_type="text/plain")
    assert answer.status == 400 and answer.json["code"] == "usage"
    assert sorted((fs.root / "docs" / "work").iterdir()) == before


def test_a_write_with_no_content_type_is_refused(records):
    answer = records.request("POST", "/api/taxonomy", raw=b'{"name": "x"}',
                             content_type=None)
    assert answer.status == 400
    assert not (records.root / "docs" / "taxonomy" / "x").exists()


def test_a_body_over_one_mebibyte_is_refused_and_creates_nothing(fs):
    before = sorted((fs.root / "docs" / "work").iterdir())
    body = b'{"title": "' + b"x" * MAX_BODY_BYTES + b'"}'
    answer = fs.request("POST", "/api/work", raw=body)
    assert answer.status == 413 and answer.json["code"] == "too-large"
    assert sorted((fs.root / "docs" / "work").iterdir()) == before


def test_a_declared_length_over_the_cap_is_refused_before_reading(fs):
    answer = fs.request("POST", "/api/taxonomy", raw=b'{"name": "x"}',
                        headers={"Content-Length": str(3 * MAX_BODY_BYTES)})
    assert answer.status == 413


@pytest.mark.parametrize("raw", [b"{not json}", b"", b'["a list"]'])
def test_malformed_bodies_are_usage_errors(records, raw):
    answer = records.request("POST", "/api/taxonomy", raw=raw)
    assert answer.status == 400 and answer.json["code"] == "usage"


def test_a_malformed_content_length_is_a_usage_error(records):
    answer = records.request("POST", "/api/taxonomy", raw=b'{"name": "x"}',
                             headers={"Content-Length": "many"})
    assert answer.status == 400


@pytest.mark.parametrize(("method", "path", "body", "host", "status"), [
    ("GET", "/", None, None, 200),
    ("GET", "/api/taxonomy", None, None, 200),
    ("GET", "/api/nope", None, None, 404),
    ("GET", "/api/work", None, "evil.example", 403),
    ("DELETE", "/api/taxonomy/admin", None, None, 404),
    ("POST", "/api/taxonomy", {}, None, 400),
])
def test_every_answer_carries_the_policy(records, method, path, body, host, status):
    extra = {"host": host} if host else {}
    answer = records.request(method, path, **extra) if body is None else \
        records.request(method, path, body, **extra)
    assert answer.status == status
    assert answer.headers["content-security-policy"] == POLICY


def test_the_api_has_no_delete(records):
    answer = records.request("DELETE", "/api/taxonomy/admin")
    assert answer.status == 404
    assert (records.root / "docs" / "taxonomy" / "admin").is_dir()
