"""The 3.x projects `tcw migrate` is tested on (TCW-116 plan, Fixtures).

Each builder writes literal TCW 3.x files into a folder, never through a TCW
4.0 writer, so what a test migrates is what 3.x wrote. The same builders are
what `tests/migrate/record_3x_listings.py` records 3.0.2's own answers from,
and `fixture_digest` is the one digest both it and
`tests/migrate/test_goldens_current.py` compute, so a golden recorded from
another version of a fixture is noticed.

F-single is one project, `app`, keeping its work in Jira, with no related
project: every conversion and report part 1 of the build order makes.
F-single-files is the same stores with the files backend. F-full places
F-single's `app` in a family of related projects: what part 2 converts.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

# Kept in one place, so a test can name what the fixture holds.
APP = "app"
JIRA_PROJECT = "APP"
SITE = "https://example.invalid"
EMAIL_VARIABLE = "TCW_JIRA__EMAIL"
TOKEN_VARIABLE = "APP_JIRA_TOKEN"

#: The `cap-…` id of each F-single capability, by id-path.
CAPABILITY_IDS = {"cli/x": "cap-1a2b3c", "cli/x/y": "cap-2b3c4d",
                  "cli/z": "cap-3c4d5e", "cli/w": "cap-4d5e6f",
                  "cli/v": "cap-5e6f70", "roles/admin": "cap-6f7081",
                  "conditions/online": "cap-708192"}

#: 4.0's `tcw validate` findings on F-single after a run that are no report's
#: prediction, as `(where, message)`: each the counterpart of a finding 3.x's
#: own `tcw validate` gave before it (`golden/f-single.json`, `validate`),
#: written by hand once (plan Decided 13). 3.x's `cli/v/resources` findings
#: have none, since TCW 4 reads that folder as the capability's resources.
F_SINGLE_A12 = [
    ("docs/capabilities/cli/w/tcw-capability.yaml",
     "app.capabilities/cli/w is incomplete: it overrides nothing, and has no Status; "
     "if it overrode an object that moved or was removed, complete it or remove it"),
]

#: A work item folder name long enough that its 4.0 value
#: `app.work/<folder>` is 256 characters, one over the limit.
LONG_FOLDER = "APP-6-" + "x" * (256 - len("app.work/") - len("APP-6-"))

_CONFIG = f"""\
# app: one project whose work is kept in Jira.
id: app
work:
  backend: jira
  jira:
    site: {SITE}
    project: {JIRA_PROJECT}
    credentials:
      email-env: {EMAIL_VARIABLE}
      token-env: {TOKEN_VARIABLE}
    fields:
      project: TCW Project
      item: TCW Item
  # No tags are registered.
  tags: null
  procedures:
    create-work:
    - generate: tcw work new Follow-up --blocks app/APP-1-a
  stages:
    inbox:
      status: Triage
    request:
      status: To Do
      prompt: &pull
      - blob: Pull first.
      - inherit: true
    spec:
      status: Specifying
      prompt:
      - blob: Write the spec.
      - blob: Say what is broken.
        when:
          not_tags:
          - bug
      post:
      - command: tcw provision
    plan:
      status: Planning
      prompt: *pull
    implement:
      status: In Progress
    review:
      status: In Review
    qa:
      status: In QA
    completed:
      status: Done
    discarded:
      status: Won't Do
"""

_LOCAL = """\
user:
  name: Ada
"""

_USER = """\
# Shared by every TCW on this machine.
work:
  stages:
    spec:
      prompt:
      - inherit: true
      - blob: My own reminder.
        when:
          not_tags:
          - docs
"""

_TAXONOMY = {
    "invoice/meta.yaml": "name: Invoice\nkind: Vocabulary\nrelatesTo: []\n",
    "invoice/description.md": "An invoice.\n",
    "invoice/line/meta.yaml": "name: Line\nkind: Vocabulary\nrelatesTo:\n- invoice\n",
    "invoice/line/description.md": "One line of an invoice.\n",
    "order/meta.yaml": "id: other\nname: Order\nkind: Vocabulary\nrelatesTo: []\n",
    "order/description.md": "An order.\n",
}

_CAPABILITIES = {
    "cli/x/meta.yaml": (
        f"id: {CAPABILITY_IDS['cli/x']}\n"
        "name: Do X\n"
        "Status: Supported\n"
        "Subject:\n- invoice\n"
        "Roles:\n- '!roles/admin'\n"
        "When:\n- conditions/online\n"
        "prependedDocs:\n- camera.md\n"),
    "cli/x/description.md": "Does X.\n",
    "cli/x/camera.md": "The camera is on.\n",
    "cli/x/y/meta.yaml": f"id: {CAPABILITY_IDS['cli/x/y']}\nname: Do Y\nStatus: Supported\n",
    "cli/x/y/description.md": "Does Y.\n",
    "cli/z/meta.yaml": f"id: {CAPABILITY_IDS['cli/z']}\nStatus: Supported\n",
    "cli/w/meta.yaml": f"id: {CAPABILITY_IDS['cli/w']}\nname: Do W\n",
    "cli/w/description.md": "Does W.\n",
    "cli/v/meta.yaml": f"id: {CAPABILITY_IDS['cli/v']}\nname: Do V\nStatus: Supported\n",
    "cli/v/description.md": "Does V.\n",
    "cli/v/resources/meta.yaml": "name: A sample, kept as a resource\n",
    # Roles and When name capabilities below `roles/` and `conditions/`.
    "roles/admin/meta.yaml": (f"id: {CAPABILITY_IDS['roles/admin']}\nname: Admin\n"
                              "Status: Supported\n"),
    "roles/admin/description.md": "Someone who runs it.\n",
    "conditions/online/meta.yaml": (f"id: {CAPABILITY_IDS['conditions/online']}\n"
                                    "name: Online\nStatus: Supported\n"),
    "conditions/online/description.md": "Connected.\n",
}

_SPEC_B = """\
# Spec

The design is in docs/work/APP-1-a/design.md, and the notes are beside it.
Shortened, it is APP-1-…/design.md or APP-1-.../design.md.

It builds on [the capability](tcw://C/cli/x). An example in code is
`[the capability](tcw://C/cli/x)`, which is left as written.
"""

_WORK_JIRA = {
    "APP-1-a/item.yaml": f"ticket: {SITE}/browse/APP-1\n",
    "APP-1-a/capabilities.yaml": ("new:\n- cli/new-thing\nchanged:\n- cli/x\n"
                                  "taxonomy:\n  new:\n  - invoice\n"),
    "APP-1-a/design.md": "# Design\n\nThe design of A.\n",
    "APP-1-a/notes/one.md": "A note.\n",
    "APP-2-b/item.yaml": f"ticket: {SITE}/browse/APP-2\n",
    "APP-2-b/spec/spec.md": _SPEC_B,
}

_WORK_FILES = {
    "2026-10-01-a/item.yaml": "title: A\nstage: request\npriority: medium\n",
    "2026-10-01-a/request/request.md": "Need A.\n",
    "2026-10-01-a/capabilities.yaml": ("new:\n- cli/new-thing\nchanged:\n- cli/x\n"
                                       "taxonomy:\n  new:\n  - invoice\n"),
    "2026-10-01-a/design.md": "# Design\n\nThe design of A.\n",
    "2026-10-02-b/item.yaml": ("title: B\nstage: request\npriority: medium\n"
                               "parent: app/2026-10-01-a\n"
                               "blocked-by:\n- app/2026-10-01-a\n"),
    "2026-10-02-b/request/request.md": "Need B.\n",
}

_README = """\
# app

The first design is docs/work/APP-1-a/design.md.
"""


def write_files(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))


def git_init(root: Path) -> None:
    for argv in (("init", "-q"), ("config", "user.email", "t@t"),
                 ("config", "user.name", "t")):
        subprocess.run(["git", "-C", str(root), *argv], check=True,
                       capture_output=True)


def user_file(config_home: Path) -> Path:
    """The user-wide personal file below `config_home`, as `XDG_CONFIG_HOME`."""
    return config_home / "tcw" / "config.yaml"


def build_f_single(root: Path, *, backend: str = "jira", config_home: Path | None = None,
                   git: bool = True) -> Path:
    """F-single at `root`: `app`, with every 3.x form part 1 converts. The
    user-wide file is written below `config_home` when one is given."""
    root.mkdir(parents=True, exist_ok=True)
    config = _CONFIG
    if backend == "files":
        config = _files_config()
    files = {"tcw-config.yaml": config, "tcw-config.local.yaml": _LOCAL,
             ".gitignore": "/tcw-config.local.yaml\n", "README.md": _README}
    files |= {f"docs/taxonomy/{k}": v for k, v in _TAXONOMY.items()}
    files |= {f"docs/capabilities/{k}": v for k, v in _CAPABILITIES.items()}
    work = _WORK_JIRA if backend == "jira" else _WORK_FILES
    files |= {f"docs/work/{k}": v for k, v in work.items()}
    write_files(root, files)
    # A 3.x term with no state file and no description: a folder alone.
    (root / "docs/taxonomy/customer").mkdir(parents=True, exist_ok=True)
    if config_home is not None:
        write_files(config_home, {"tcw/config.yaml": _USER})
    if git:
        git_init(root)
    return root


def _files_config() -> str:
    """F-single's configuration with the files backend: no `jira` block and
    no stage statuses."""
    lines, skip = [], False
    for line in _CONFIG.splitlines(keepends=True):
        if line.startswith("  backend:"):
            lines.append("  backend: filesystem\n")
            continue
        if line.startswith("  jira:"):
            skip = True
            continue
        if skip and line.startswith("    "):
            continue
        skip = False
        if line.strip().startswith("status:"):
            continue
        lines.append(line)
    text = "".join(lines)
    # A stage left with nothing under it reads as null, which 3.x refuses.
    for stage in ("inbox", "implement", "review", "qa", "completed", "discarded"):
        text = text.replace(f"    {stage}:\n", "")
    return text.replace("# app: one project whose work is kept in Jira.",
                        "# app: one project whose work is kept in files.")


def seed_tickets(fake, project: str = JIRA_PROJECT) -> dict[str, dict]:
    """F-single's tickets in the fake Jira: the 3.x values to convert, one
    already 4.0, one of another TCW project in the same Jira project, one of
    no TCW project, one whose 4.0 value would be too long, and one with no
    `TCW Item`. Returns each key's custom values, by field name."""
    from tests.work.jira.fake import FIELDS
    if project not in fake.projects:
        fake.add_project(project)
    made = {}
    for summary, values in (
            ("A", {"TCW Project": APP, "TCW Item": "app/APP-1-a"}),
            ("B", {"TCW Project": APP, "TCW Item": "app/APP-2-b"}),
            ("Gone", {"TCW Project": APP, "TCW Item": "app/APP-3-gone"}),
            ("D", {"TCW Project": APP, "TCW Item": "app.work/APP-4-d"}),
            ("Other", {"TCW Project": APP, "TCW Item": "other/APP-5-e"}),
            ("Long", {"TCW Project": APP, "TCW Item": f"app/{LONG_FOLDER}"}),
            ("No item", {"TCW Project": APP}),
            ("Lib", {"TCW Project": "lib", "TCW Item": "lib/LIB-1-l"})):
        ticket = fake.ticket(summary, project=project, status="To Do")
        for name, value in values.items():
            ticket.custom[FIELDS[name]] = value
        made[ticket.key] = values
    return made


# ---------------------------------------------------------------------------
# F-full: F-single's `app` in a family (plan, Fixtures; Steps 15-24)

LIB_URL = "https://example.invalid/lib.git"

#: The `cap-…` id of each capability of `app`'s related projects, by project
#: and id-path. An override's own folder keeps an id too, as 3.x wrote one.
FAMILY_IDS = {
    "core": {"auth/login": "cap-c0a001", "billing": "cap-c0a002",
             "cli/report": "cap-c0a003", "x/fetch": "cap-c0a004"},
    "lib": {"net/fetch": "cap-11b001"},
    "ws": {"cli/shared": "cap-5e5001"},
    "sib": {"cli/sib-only": "cap-51b001", "o/login": "cap-51b002"},
    "kid": {"k-thing": "cap-c1d001"},
    "app": {"ov/login": "cap-a99001", "core/billing": "cap-a99002",
            "cli/report": "cap-a99003", "cli/shared": "cap-a99004"},
}

_WS_CONFIG = """\
# ws: the workspace, holding app, sib and kid.
id: ws
projects:
  children:
    app:
      path: app
      # Filing into app's Jira project.
      jira:
        project: APP
    sib: sib
work:
  tags:
  - bug
  - docs
"""

_APP_FAMILY = """\
projects:
  parent:
    ws: ..
  children:
    kid: ../kid
  upstream:
    core: ../../core
    lib:
      repository:
        url: {lib}
taxonomy:
  extends:
  - core
  - kid
capabilities:
  extends:
  - core
  - ws
  - sib
""".format(lib=LIB_URL)

_SIB_CONFIG = """\
id: sib
projects:
  parent:
    ws: ..
capabilities:
  extends:
  - core
"""

_KID_CONFIG = """\
id: kid
projects:
  parent:
    app: ../app
"""

_CORE_CONFIG = """\
# core: a library app reads.
id: core
projects:
  upstream:
    lib:
      repository:
        url: {lib}
capabilities:
  extends:
  - lib
""".format(lib=LIB_URL)

_LIB_CONFIG = "id: lib\n"


def _cap(project: str, path: str, name: str, extra: str = "") -> str:
    return (f"id: {FAMILY_IDS[project][path]}\nname: {name}\nStatus: Supported\n"
            f"{extra}")


_CORE_FILES = {
    "tcw-config.yaml": _CORE_CONFIG,
    "docs/taxonomy/money/meta.yaml": "name: Money\nkind: Vocabulary\nrelatesTo: []\n",
    "docs/taxonomy/money/description.md": "Money.\n",
    "docs/capabilities/auth/login/meta.yaml": _cap(
        "core", "auth/login", "Log in", "Subject:\n- money\nprependedDocs:\n- intro.md\n"),
    "docs/capabilities/auth/login/description.md": "Logs in.\n",
    "docs/capabilities/auth/login/intro.md": "Before logging in.\n",
    "docs/capabilities/billing/meta.yaml": _cap("core", "billing", "Bill"),
    "docs/capabilities/billing/description.md": "Bills.\n",
    "docs/capabilities/cli/report/meta.yaml": _cap("core", "cli/report", "Report"),
    "docs/capabilities/cli/report/description.md": "Reports.\n",
    # core's own override of lib's capability, from a folder of its own.
    "docs/capabilities/x/fetch/meta.yaml": (
        f"id: {FAMILY_IDS['core']['x/fetch']}\noverrides: {FAMILY_IDS['lib']['net/fetch']}\n"
        "name: Fetch, as core does it\n"),
}

_LIB_FILES = {
    "tcw-config.yaml": _LIB_CONFIG,
    "docs/capabilities/net/fetch/meta.yaml": _cap("lib", "net/fetch", "Fetch"),
    "docs/capabilities/net/fetch/description.md": "Fetches.\n",
}

_WS_FILES = {
    "tcw-config.yaml": _WS_CONFIG,
    "docs/capabilities/cli/shared/meta.yaml": _cap("ws", "cli/shared", "Shared"),
    "docs/capabilities/cli/shared/description.md": "Shared by the workspace.\n",
}

_SIB_FILES = {
    "tcw-config.yaml": _SIB_CONFIG,
    "docs/capabilities/cli/sib-only/meta.yaml": _cap("sib", "cli/sib-only", "Sib only"),
    "docs/capabilities/cli/sib-only/description.md": "Only in sib.\n",
    # sib overrides core's capability: a middle project, since app reads sib.
    "docs/capabilities/o/login/meta.yaml": (
        f"id: {FAMILY_IDS['sib']['o/login']}\n"
        f"overrides: core/{FAMILY_IDS['core']['auth/login']}\nStatus: Deprecated\n"),
}

_KID_FILES = {
    "tcw-config.yaml": _KID_CONFIG,
    "docs/taxonomy/party/meta.yaml": "name: Party\nkind: Vocabulary\nrelatesTo: []\n",
    "docs/taxonomy/party/description.md": "A party.\n",
    "docs/capabilities/k-thing/meta.yaml": _cap("kid", "k-thing", "K thing"),
    "docs/capabilities/k-thing/description.md": "A thing of kid's.\n",
}

#: app's capabilities in F-full: F-single's, `cli/x` naming two inherited
#: terms, and three overrides of core's and one capability ws also has.
_APP_CAPABILITIES = dict(_CAPABILITIES) | {
    "cli/x/meta.yaml": _CAPABILITIES["cli/x/meta.yaml"].replace(
        "Subject:\n- invoice\n", "Subject:\n- invoice\n- core/money\n- party\n"),
    # By bare id, from a folder unrelated to the original's path.
    "ov/login/meta.yaml": (f"id: {FAMILY_IDS['app']['ov/login']}\n"
                           f"overrides: {FAMILY_IDS['core']['auth/login']}\n"
                           "name: Log in, as app does it\n"),
    "ov/login/description.md": "Logs in to app.\n",
    # By `<alias>/<id>`, from the `<alias>/` folder 3.x kept overrides in.
    "core/billing/meta.yaml": (f"id: {FAMILY_IDS['app']['core/billing']}\n"
                               f"overrides: core/{FAMILY_IDS['core']['billing']}\n"
                               "Status: Deprecated\n"),
    # Already at its original's path.
    "cli/report/meta.yaml": (f"id: {FAMILY_IDS['app']['cli/report']}\n"
                             f"overrides: {FAMILY_IDS['core']['cli/report']}\n"
                             "name: Report, as app does it\n"),
    "cli/shared/meta.yaml": _cap("app", "cli/shared", "Shared, as app has it"),
    "cli/shared/description.md": "app's own.\n",
}

_APP_WORK = dict(_WORK_JIRA) | {
    "APP-2-b/capabilities.yaml": ("changed:\n- core/billing\n- kid/k-thing\n"
                                  "- cli/shared\n"),
}


def app_config_in_family() -> str:
    """F-single's configuration with `app`'s place in the family and its
    work store in the workspace."""
    text = _CONFIG.replace("# app: one project whose work is kept in Jira.\nid: app\n",
                           "# app: one project of the ws family, whose work is kept "
                           "in Jira.\nid: app\n" + _APP_FAMILY)
    return text.replace("work:\n  backend: jira\n",
                        "work:\n  path: ../docs/app/work\n  backend: jira\n")


def lib_clone(cache_home: Path) -> Path:
    """Where 3.x put its clone of `lib`, below `cache_home` as `XDG_CACHE_HOME`."""
    from tcw.migrate.legacy import RepoDecl3, _cache_key_3x
    return cache_home / "tcw" / "stores" / _cache_key_3x(RepoDecl3(LIB_URL))


#: Each F-full project's folder, relative to the fixture's base folder.
F_FULL_PROJECTS = {"ws": "ws", "app": "ws/app", "sib": "ws/sib", "kid": "ws/kid",
                   "core": "core"}


def build_f_full(base: Path, *, config_home: Path | None = None,
                 cache_home: Path | None = None, git: bool = True) -> Path:
    """F-full below `base`: `ws` a git repository holding `app`, `sib` and
    `kid`; `core` its own repository beside it; `lib` named only by its
    repository, its 3.x clone below `cache_home`. Returns `app`'s folder."""
    base.mkdir(parents=True, exist_ok=True)
    ws, app = base / "ws", base / "ws" / "app"
    write_files(ws, _WS_FILES)
    write_files(base / "ws/sib", _SIB_FILES)
    write_files(base / "ws/kid", _KID_FILES)
    write_files(base / "core", _CORE_FILES)
    if cache_home is not None:
        write_files(lib_clone(cache_home), _LIB_FILES)
    files = {"tcw-config.yaml": app_config_in_family(), "tcw-config.local.yaml": _LOCAL,
             ".gitignore": "/tcw-config.local.yaml\n", "README.md": _README}
    files |= {f"docs/taxonomy/{k}": v for k, v in _TAXONOMY.items()}
    files |= {f"docs/capabilities/{k}": v for k, v in _APP_CAPABILITIES.items()}
    write_files(app, files)
    write_files(ws / "docs/app/work", _APP_WORK)
    (app / "docs/taxonomy/customer").mkdir(parents=True, exist_ok=True)
    if config_home is not None:
        write_files(config_home, {"tcw/config.yaml": _USER})
    if git:
        git_init(ws)
        git_init(base / "core")
    return app


def as_4_0_records(src: Path, dst: Path) -> Path:
    """A copy of a `docs/` folder at `dst` with every taxonomy and capability
    `meta.yaml` renamed to its TCW 4 name and the version line put first
    (plan Step 12): what this repository's records will be after TCW-118."""
    import shutil
    from tcw.project_files import version_line
    from tests.statefiles import STATE_OF
    shutil.copytree(src, dst)
    for namespace in ("taxonomy", "capabilities"):
        for meta in sorted((dst / namespace).rglob("meta.yaml")):
            text = meta.read_text(encoding="utf-8")
            (meta.parent / STATE_OF[namespace]).write_text(version_line() + text,
                                                           encoding="utf-8")
            meta.unlink()
    return dst


# ---------------------------------------------------------------------------
# Comparing trees


def snapshot(*roots: Path, files: tuple[Path, ...] = (), times: bool = True) -> dict:
    """Every path below each of `roots` (`.git/` left out) and each of `files`:
    its kind, its bytes and, with `times`, its modification time."""
    found = {}

    def add(path: Path) -> None:
        if path.is_symlink():
            found[str(path)] = ("link", os.readlink(path))
        elif path.is_dir():
            found[str(path)] = ("dir",)
        elif path.is_file():
            stat = path.stat()
            found[str(path)] = ("file", path.read_bytes(),
                                stat.st_mtime_ns if times else None)

    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d != ".git")
            for name in (*dirnames, *sorted(filenames)):
                add(Path(dirpath) / name)
    for path in files:
        add(path)
    return found


def fixture_digest(root: Path) -> str:
    """SHA-256 over each file's path relative to `root` and its bytes, in
    sorted order, `.git/` left out (Decided 3). An empty folder counts by its
    path, since 3.x lists one as a term."""
    digest = hashlib.sha256()
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        here = Path(dirpath)
        if not dirnames and not filenames and here != root:
            entries.append((here.relative_to(root).as_posix() + "/", b""))
        for name in filenames:
            path = here / name
            entries.append((path.relative_to(root).as_posix(), path.read_bytes()))
    for rel, data in sorted(entries):
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


#: Each fixture the goldens are recorded from: its builder's arguments.
# ---------------------------------------------------------------------------
# The monorepo (UC-3; criterion 46)

#: Each monorepo project's folder, relative to the fixture's base folder.
MONOREPO_PROJECTS = {"mono": "mono", "api": "mono/packages/api",
                     "web": "mono/packages/web", "jobs": "mono/packages/jobs"}

_A_JIRA = f"""\
work:
  backend: jira
  jira:
    site: {SITE}
    project: {JIRA_PROJECT}
    credentials:
      email-env: APP_EMAIL
      token-env: APP_TOKEN
    fields:
      project: TCW Project
      item: TCW Item
  stages:
    inbox:
      status: Triage
    request:
      status: To Do
    spec:
      status: Specifying
    plan:
      status: Planning
    implement:
      status: In Progress
    review:
      status: In Review
    qa:
      status: In QA
    completed:
      status: Done
    discarded:
      status: Won't Do
"""

_MONOREPO_FILES = {
    "mono/tcw-config.yaml": (
        "id: mono\nprojects:\n  children:\n    api: packages/api\n"
        "    web: packages/web\n    jobs: packages/jobs\nwork:\n  tags:\n  - bug\n"),
    "mono/docs/taxonomy/money/meta.yaml": "name: Money\nkind: Vocabulary\nrelatesTo: []\n",
    "mono/docs/taxonomy/money/description.md": "Money.\n",
    "mono/docs/taxonomy/party/meta.yaml": "name: Party\nkind: Vocabulary\nrelatesTo: []\n",
    "mono/docs/taxonomy/party/description.md": "A party.\n",
    "mono/docs/capabilities/shared/meta.yaml": (
        "id: cap-30a001\nname: Shared\nStatus: Supported\n"),
    "mono/docs/capabilities/shared/description.md": "Shared by the packages.\n",
    # api keeps its work in Jira, with only the keys 3.x requires.
    "mono/packages/api/tcw-config.yaml": (
        "id: api\nprojects:\n  parent:\n    mono: ../..\ntaxonomy:\n  extends:\n  - mono\n"
        + _A_JIRA),
    "mono/packages/api/docs/capabilities/api-thing/meta.yaml": (
        "id: cap-a00001\nname: Api thing\nStatus: Supported\nSubject:\n- mono/money\n"),
    "mono/packages/api/docs/capabilities/api-thing/description.md": "api's own.\n",
    "mono/packages/api/docs/taxonomy/route/meta.yaml": (
        "name: Route\nkind: Vocabulary\nrelatesTo: []\n"),
    "mono/packages/api/docs/taxonomy/route/description.md": "A route.\n",
    # The folder of api's items' documents, none yet.
    "mono/packages/api/docs/work/.gitkeep": "",
    # web reads api's capabilities, a sibling (E4).
    "mono/packages/web/tcw-config.yaml": (
        "id: web\nprojects:\n  parent:\n    mono: ../..\ntaxonomy:\n  extends:\n  - mono\n"
        "capabilities:\n  extends:\n  - api\n"),
    "mono/packages/web/docs/capabilities/web-thing/meta.yaml": (
        "id: cap-3eb001\nname: Web thing\nStatus: Supported\nBlocked by: api/api-thing\n"),
    "mono/packages/web/docs/capabilities/web-thing/description.md": "web's own.\n",
    "mono/packages/web/docs/taxonomy/page/meta.yaml": (
        "name: Page\nkind: Vocabulary\nrelatesTo: []\n"),
    "mono/packages/web/docs/taxonomy/page/description.md": "A page.\n",
    # jobs reads nothing through extends, and has a term the root has too (D2).
    "mono/packages/jobs/tcw-config.yaml": (
        "id: jobs\nprojects:\n  parent:\n    mono: ../..\n"),
    "mono/packages/jobs/docs/taxonomy/party/meta.yaml": (
        "name: Party, as jobs has it\nkind: Vocabulary\nrelatesTo: []\n"),
    "mono/packages/jobs/docs/taxonomy/party/description.md": "jobs' party.\n",
    "mono/packages/jobs/docs/capabilities/run/meta.yaml": (
        "id: cap-30b001\nname: Run\nStatus: Supported\n"),
    "mono/packages/jobs/docs/capabilities/run/description.md": "Runs jobs.\n",
}


def build_monorepo(base: Path, *, git: bool = True) -> dict[str, Path]:
    """The monorepo below `base`: one repository holding the root `mono` and
    its packages `api`, `web` and `jobs`. Returns each project's folder by ID."""
    write_files(base, _MONOREPO_FILES)
    if git:
        git_init(base / "mono")
    return {pid: base / rel for pid, rel in MONOREPO_PROJECTS.items()}


FIXTURES = {
    "f-single": {"backend": "jira"},
    "f-single-files": {"backend": "files"},
    "f-full": {},
    "monorepo": {},
}

#: The projects of a fixture that holds several, each 3.x's answers are
#: recorded in, by ID: its folder relative to the folder the fixture is
#: built in. A fixture not named here is one project, at that folder.
FIXTURE_PROJECTS = {"f-full": F_FULL_PROJECTS, "monorepo": MONOREPO_PROJECTS}


def build_fixture(name: str, root: Path, *, config_home: Path | None = None,
                  cache_home: Path | None = None, git: bool = False) -> Path:
    """Fixture `name` at `root`; for F-full, `root` is its base folder, and
    `lib`'s clone goes below `cache_home`."""
    if name == "f-full":
        build_f_full(root, config_home=config_home, cache_home=cache_home, git=git)
        return root
    if name == "monorepo":
        build_monorepo(root, git=git)
        return root
    return build_f_single(root, config_home=config_home, git=git, **FIXTURES[name])


def fixture_digest_of(name: str, root: Path, config_home: Path,
                      cache_home: Path | None = None) -> str:
    """The digest a golden records for fixture `name` built at `root` with its
    user-wide file below `config_home` and, for F-full, `lib`'s clone below
    `cache_home`: the folders' digests, together."""
    digest = hashlib.sha256(name.encode("utf-8"))
    folders = [root, config_home] + ([cache_home] if name == "f-full" else [])
    for folder in folders:
        digest.update(fixture_digest(folder).encode("ascii") if folder is not None
                      and folder.exists() else b"absent")
    return digest.hexdigest()
