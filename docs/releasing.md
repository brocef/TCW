# Releasing TCW

How this repository publishes itself. Not needed to _use_ TCW.

Releases publish themselves. `scripts/cut_version.py` bumps every
version-bearing file, rotates the changelog and release-note working files,
commits, and tags; pushing that tag is what ships it:

```sh
python scripts/cut_version.py <patch|minor|major|X.Y.Z>
git push origin main --tags
```

The `v*` tag triggers `.github/workflows/release.yml`, which runs the full test
suite, checks that the tag matches the version in `pyproject.toml`, builds, and
uploads to PyPI. There is no API token — PyPI mints a short-lived credential
from GitHub's OIDC claim ("Trusted Publishing"), which is why the workflow
declares `id-token: write` and `environment: pypi`.

Two things are configured once, outside the repo, and must match the workflow
exactly or the upload fails authentication:

| Where                            | Setting                                                                                         |
| -------------------------------- | ----------------------------------------------------------------------------------------------- |
| pypi.org → Publishing            | project `tcw-cli`, owner `brocef`, repository `TCW`, workflow `release.yml`, environment `pypi` |
| GitHub → Settings → Environments | an environment named `pypi`                                                                     |

**A version can only be uploaded to PyPI once.** If the workflow fails _after_ a
successful upload, that version number is spent — recover with a patch bump, not
by re-running the job.
