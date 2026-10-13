"""Every check returns `Finding` values (TCW-73 Design 6.3; AC 27).

The registry's, the taxonomy's and the capabilities' `check()` and
`validate()` each return only `Finding`s, over one fixture holding a problem
for each; and the web viewer, which shows them as text, renders each as
`<severity>: <where>: <message>`.
"""

import re
from http import HTTPStatus

import yaml

from tcw.findings import Finding
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
from tcw.store.project import FsProjectRegistry
from tcw.validate import validate
from tests.test_serve_write import _node, _req, _seed, _start_server

RENDERED = re.compile(r"(error|warning|unresolved): \S.*: \S.*")


def broken(tmp_path):
    """A project with a taxonomy problem, a capabilities problem and a
    `tcw://` link that resolves to nothing."""
    root = _node(tmp_path)
    term = root / "docs" / "taxonomy" / "search"
    term.mkdir(parents=True)
    (term / "meta.yaml").write_text("name: search\nkind: Feature\nrelatesTo: []\n")
    (term / "description.md").write_text("[gone](tcw://T/nowhere)\n")
    FsCapabilitiesStore.open(root).add("half", status="Partial")
    return root


def only_findings(values) -> list[Finding]:
    values = list(values)
    assert values and all(type(v) is Finding for v in values), values
    return values


def test_the_taxonomy_check(tmp_path):
    [finding] = only_findings(FsTaxonomyStore.open(broken(tmp_path)).check())
    assert (finding.severity, finding.where) == ("error", "docs/taxonomy/search")
    assert "vocabulary" in finding.message


def test_the_capabilities_check(tmp_path):
    [finding] = only_findings(FsCapabilitiesStore.open(broken(tmp_path)).check())
    assert finding == Finding("error", "docs/capabilities/half", "Partial requires Gaps")


def test_the_registry_check(tmp_path):
    root = _node(tmp_path)
    config = yaml.safe_load((root / "tcw-config.yaml").read_text())
    config["connected-projects"] = {"cousins": {}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config))
    [finding] = only_findings(FsProjectRegistry.open(root).check())
    assert finding.where.endswith("tcw-config.yaml")
    assert "cousins" in finding.message


def test_validate(tmp_path):
    findings = only_findings(validate(broken(tmp_path)))
    assert {f.where for f in findings} >= {"docs/taxonomy/search",
                                          "docs/capabilities/half",
                                          "docs/taxonomy/search/description.md"}
    assert all(RENDERED.fullmatch(str(f)) for f in findings), findings


def test_a_viewer_save_reports_its_findings_as_text(tmp_path):
    root = _node(tmp_path)
    _seed(root)
    httpd, base = _start_server(root)
    try:
        status, body = _req(base, "POST", "/api/capabilities", {
            "path": "half", "name": "Half done", "status": "Partial"})
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert status == HTTPStatus.CREATED
    assert body["warnings"] == ["error: docs/capabilities/half: Partial requires Gaps"]
