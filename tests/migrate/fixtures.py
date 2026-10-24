"""The 3.x projects `tcw migrate` is tested on (TCW-116 plan, Fixtures).

Each builder writes literal TCW 3.x files into a folder, never through a TCW
4.0 writer, so what a test migrates is what 3.x wrote. The same builders are
what `tests/migrate/record_3x_listings.py` records 3.0.2's own answers from,
and `fixture_digest` is the one digest both it and
`tests/migrate/test_goldens_current.py` compute, so a golden recorded from
another version of a fixture is noticed.

F-single is one project, `app`, keeping its work in Jira, with no related
project: every conversion and report part 1 of the build order makes.
F-single-files is the same stores with the files backend.
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
FIXTURES = {
    "f-single": {"backend": "jira"},
    "f-single-files": {"backend": "files"},
}


def build_fixture(name: str, root: Path, *, config_home: Path | None = None,
                  git: bool = False) -> Path:
    return build_f_single(root, config_home=config_home, git=git, **FIXTURES[name])


def fixture_digest_of(name: str, root: Path, config_home: Path) -> str:
    """The digest a golden records for fixture `name` built at `root` with its
    user-wide file below `config_home`: both folders' digests, together."""
    digest = hashlib.sha256(name.encode("utf-8"))
    for folder in (root, config_home):
        digest.update(fixture_digest(folder).encode("ascii") if folder.exists()
                      else b"absent")
    return digest.hexdigest()
